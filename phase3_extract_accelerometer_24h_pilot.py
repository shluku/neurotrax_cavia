from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from analyze_accelerometer_24h_local_pilot import (
    CHUNK_MINUTES,
    OUT_DIR as LOCAL_ANALYSIS_DIR,
    analyze_chunk,
    build_bandpass_feature_summary,
    build_bandpass_hourly_summary,
    build_threshold_sensitivity,
    chunk_iter,
    load_signal_data,
    summarize_features,
)
from download_accelerometer_24h_pilot import ms_to_local, parse_data, signal_fields
from main import connect_sensordata_db


ROOT = Path(__file__).parent
QC_PATH = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_patient.csv"
EXISTING_041_MANIFEST = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot/accelerometer_24h_pilot_manifest.csv"
OUT_DIR = (
    ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot"
)
TEMP_DIR = OUT_DIR / "_temporary_local_signal_files"
EXCLUDED_SUBJECTS = {"001"}
TABLE_NAME = "accelerometer"
MAX_INITIAL_EMPTY_CHUNKS = 12


FEATURE_NAMES = [
    "accelerometer_total_rows_loaded",
    "accelerometer_exact_duplicate_rows_removed",
    "accelerometer_valid_signal_minutes",
    "accelerometer_valid_chunk_count",
    "accelerometer_median_sampling_interval_ms",
    "accelerometer_gap_burden_fraction",
    "accelerometer_dynamic_magnitude_mean",
    "accelerometer_dynamic_magnitude_sd",
    "accelerometer_still_phone_minutes",
    "accelerometer_stillness_fraction",
    "accelerometer_phone_handling_minutes",
    "accelerometer_walking_like_minutes",
    "accelerometer_shaking_like_minutes",
    "accelerometer_high_motion_chunk_fraction",
    "accelerometer_tremor_band_power_mean",
    "accelerometer_day_motion_minutes",
    "accelerometer_night_motion_minutes",
    "accelerometer_day_night_motion_ratio",
    "accelerometer_hourly_motion_entropy",
]


def local_to_ms(value: pd.Timestamp) -> int:
    if value.tzinfo is None:
        value = value.tz_localize("Asia/Jerusalem")
    return int(value.tz_convert("UTC").timestamp() * 1000)


def local_string_to_ms(value: Any) -> int | None:
    if pd.isna(value) or not str(value).strip():
        return None
    ts = pd.to_datetime(str(value), errors="coerce")
    if pd.isna(ts):
        return None
    if ts.tzinfo is None:
        ts = ts.tz_localize("Asia/Jerusalem")
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def load_ranked_patients(limit: int) -> pd.DataFrame:
    df = pd.read_csv(QC_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].astype(str).str.zfill(3)
    df["global_T1_num"] = pd.to_numeric(df["global_T1"], errors="coerce")
    df = df.dropna(subset=["Subject_ID_D", "global_T1_num", "T1_date_iso", "selected_device_id"]).copy()
    df = df[~df["Subject_ID_D"].isin(EXCLUDED_SUBJECTS)].copy()
    df = df[df["has_sensor_accelerometer_metadata_after_T1"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    df = df[df["selected_device_id"].astype(str).str.strip().ne("")]
    ranked = df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True]).copy()
    if limit > 0:
        ranked = ranked.head(limit).copy()
    return ranked


def first_existing_raw_row(conn, device_id: str, start_ms: int, end_ms: int) -> int | None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT timestamp
            FROM `accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        cur.close()


def fetch_chunk(conn, device_id: str, start_ms: int, end_ms: int, batch_rows: int):
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT _id, timestamp, device_id, data
            FROM `accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        while True:
            rows = cur.fetchmany(batch_rows)
            if not rows:
                break
            yield rows
    finally:
        cur.close()


def write_signal_file(conn, patient: pd.Series, start_ms: int, end_ms: int, batch_rows: int) -> tuple[Path, list[dict[str, Any]], int]:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    subject_id = str(patient["Subject_ID_D"])
    device_id = str(patient["selected_device_id"]).strip()
    out_path = TEMP_DIR / f"accelerometer_24h_subject_{subject_id}_device_{device_id[:8]}_{start_ms}_{end_ms}_signal.csv.gz"
    fieldnames = ["_id", "timestamp", "local_datetime", "device_id", "x", "y", "z", "accuracy", "label", "magnitude"]
    chunk_log: list[dict[str, Any]] = []
    total_rows = 0
    chunk_ms = CHUNK_MINUTES * 60 * 1000

    with gzip.open(out_path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        t = start_ms
        consecutive_initial_empty_chunks = 0
        while t < end_ms:
            t_next = min(t + chunk_ms, end_ms)
            chunk_count = 0
            status = "ok"
            error_message = ""
            try:
                for batch in fetch_chunk(conn, device_id, t, t_next, batch_rows):
                    for row in batch:
                        data = parse_data(row.get("data"))
                        writer.writerow(
                            {
                                "_id": row.get("_id", ""),
                                "timestamp": row.get("timestamp", ""),
                                "local_datetime": ms_to_local(row.get("timestamp")),
                                "device_id": row.get("device_id", ""),
                                **signal_fields(data),
                            }
                        )
                        chunk_count += 1
                total_rows += chunk_count
                if total_rows == 0 and chunk_count == 0:
                    consecutive_initial_empty_chunks += 1
                else:
                    consecutive_initial_empty_chunks = 0
            except Exception as exc:  # noqa: BLE001
                status = "error"
                error_message = str(exc)
            if total_rows == 0 and consecutive_initial_empty_chunks >= MAX_INITIAL_EMPTY_CHUNKS and status == "ok":
                status = "initial_anchor_no_rows"
                error_message = f"Stopped after {MAX_INITIAL_EMPTY_CHUNKS} consecutive empty initial chunks."
            chunk_log.append(
                {
                    "Subject_ID_D": subject_id,
                    "device_id": device_id,
                    "chunk_start_ms": t,
                    "chunk_end_ms": t_next,
                    "chunk_start_local": ms_to_local(t),
                    "chunk_end_local": ms_to_local(t_next),
                    "rows_downloaded": chunk_count,
                    "cumulative_rows_downloaded": total_rows,
                    "status": status,
                    "error_message": error_message,
                }
            )
            print(f"  chunk {ms_to_local(t)} -> {ms_to_local(t_next)} rows={chunk_count:,} status={status}", flush=True)
            if status in {"error", "initial_anchor_no_rows"}:
                break
            t = t_next
    return out_path, chunk_log, total_rows


def existing_041_signal_path(patient: pd.Series) -> tuple[Path | None, dict[str, Any] | None]:
    if str(patient["Subject_ID_D"]) != "041" or not EXISTING_041_MANIFEST.exists():
        return None, None
    manifest = pd.read_csv(EXISTING_041_MANIFEST, dtype=str)
    if manifest.empty:
        return None, None
    row = manifest.iloc[0].to_dict()
    path = Path(str(row.get("signal_path", "")))
    return (path, row) if path.exists() else (None, None)


def analyze_signal_file(signal_path: Path, manifest: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = load_signal_data(signal_path)
    duplicate_rows = int(df.attrs.get("dropped_exact_duplicate_rows", 0))
    start_ms = int(float(manifest["candidate_window_start_ms"]))
    end_ms = int(float(manifest["candidate_window_end_ms"]))
    chunk_df = pd.DataFrame([analyze_chunk(i, start, end, chunk) for i, start, end, chunk in chunk_iter(df, start_ms, end_ms)])
    features_df = summarize_features(chunk_df, manifest, len(df), duplicate_rows)
    thresholds_df = build_threshold_sensitivity(chunk_df)
    bandpass_df = build_bandpass_feature_summary(chunk_df)
    bandpass_hourly_df = build_bandpass_hourly_summary(chunk_df)
    return features_df, chunk_df, thresholds_df, bandpass_df, bandpass_hourly_df


def feature_long_rows(features_df: pd.DataFrame, table_status: str, status_row: dict[str, Any]) -> list[dict[str, Any]]:
    if features_df.empty:
        return []
    row = features_df.iloc[0].to_dict()
    out = []
    for feature_name in FEATURE_NAMES:
        value = row.get(feature_name, pd.NA)
        out.append(
            {
                "Subject_ID_D": row.get("Subject_ID_D", status_row.get("Subject_ID_D", "")),
                "Subject_ID_N": row.get("Subject_ID_N", status_row.get("Subject_ID_N", "")),
                "global_T1": row.get("global_T1", status_row.get("global_T1", "")),
                "T1_date_iso": row.get("T1_date_iso", status_row.get("T1_date_iso", "")),
                "source_table": TABLE_NAME,
                "feature_name": feature_name,
                "feature_value": value,
                "feature_status": "calculated" if table_status == "calculated" and not pd.isna(value) else table_status,
                "window_start_local": status_row.get("window_start_local", ""),
                "window_end_local": status_row.get("window_end_local", ""),
                "device_ids_used": status_row.get("device_id", ""),
                "protocol_variant": "accelerometer_special_phase3_24h_first_raw_in_T1_week",
            }
        )
    return out


def build_readme(limit: int, status_df: pd.DataFrame, anchor_source: str) -> str:
    calculated = int(status_df["table_status"].eq("calculated").sum()) if not status_df.empty else 0
    return f"""# Accelerometer Special Phase 3 24h Pilot

This folder contains a pilot implementation of the accelerometer-specific Phase 3 pipeline.

Scope:

- Table: `accelerometer`
- Candidate patients allowed: `{limit}`
- Excluded patient: `001`
- Ranking: descending T1 global score among patients with `sensor_accelerometer` metadata
- SQL rule: one `device_id`, bounded timestamp window, 5-minute chunks
- Local rule: download temporary per-patient signal file, analyze locally, then delete temporary file unless `--keep-temp` is used
- Anchor source: `{anchor_source}`

Window rule:

1. Default pilot mode uses the known `sensor_accelerometer` metadata timestamp as the raw `accelerometer` anchor.
2. Optional `raw-first-in-T1-week` mode searches for the first raw `accelerometer` row in the first week from T1.
3. Start a 24-hour window at the selected anchor timestamp.
3. Download only that bounded 24-hour window in 5-minute chunks.
4. If the anchor produces only empty initial chunks, stop that patient early and continue down the ranked list.
5. Analyze locally with duplicate removal, sampling QC, magnitude/dynamic magnitude, state summaries, threshold sensitivity, and bandpass summaries.

Calculated patients in this pilot: `{calculated}`

Important:

- Missing raw data remains missing, not no movement.
- Frequency-band features include sampling feasibility checks.
- Shaking/tremor-like bands are only interpretable when the observed sampling rate can support those frequencies.
- Outputs are isolated table-run files and have not been merged into the shared Phase 3 matrix.

Generated files:

- `phase3_accelerometer_24h_pilot_features_wide.csv`
- `phase3_accelerometer_24h_pilot_features_long.csv`
- `phase3_accelerometer_24h_pilot_patient_status.csv`
- `phase3_accelerometer_24h_pilot_download_chunk_log.csv`
- `phase3_accelerometer_24h_pilot_chunk_summary.csv`
- `phase3_accelerometer_24h_pilot_threshold_sensitivity.csv`
- `phase3_accelerometer_24h_pilot_bandpass_summary.csv`
- `phase3_accelerometer_24h_pilot_bandpass_hourly_summary.csv`
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Special Phase 3 accelerometer 24h pilot for top-ranked T1 patients.")
    parser.add_argument("--limit-patients", type=int, default=3)
    parser.add_argument("--target-calculated", type=int, default=3)
    parser.add_argument("--batch-rows", type=int, default=10000)
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument(
        "--anchor-source",
        choices=["sensor-metadata", "raw-first-in-T1-week"],
        default="sensor-metadata",
        help="Default avoids slow raw-table discovery by anchoring to sensor_accelerometer metadata.",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    patients = load_ranked_patients(args.limit_patients)
    feature_wide_rows: list[dict[str, Any]] = []
    feature_long: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    download_chunks: list[dict[str, Any]] = []
    all_chunks: list[pd.DataFrame] = []
    all_thresholds: list[pd.DataFrame] = []
    all_bandpass: list[pd.DataFrame] = []
    all_bandpass_hourly: list[pd.DataFrame] = []

    conn = connect_sensordata_db()
    try:
        for idx, (_, patient) in enumerate(patients.iterrows(), start=1):
            if sum(1 for row in status_rows if row.get("table_status") == "calculated") >= args.target_calculated:
                break
            subject_id = str(patient["Subject_ID_D"])
            device_id = str(patient["selected_device_id"]).strip()
            print(f"patient {idx}/{len(patients)} Subject_ID_D={subject_id} device={device_id}", flush=True)
            status_row: dict[str, Any] = {
                "Subject_ID_D": subject_id,
                "Subject_ID_N": patient.get("Subject_ID_N", ""),
                "global_T1": patient.get("global_T1", ""),
                "T1_date_iso": patient.get("T1_date_iso", ""),
                "device_id": device_id,
                "source_table": TABLE_NAME,
                "protocol_variant": f"accelerometer_special_phase3_24h_{args.anchor_source}",
            }
            signal_path, existing_manifest = existing_041_signal_path(patient)
            temp_path: Path | None = None
            try:
                if signal_path and existing_manifest:
                    manifest = {
                        **existing_manifest,
                        "Subject_ID_D": subject_id,
                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                        "global_T1": patient.get("global_T1", ""),
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                    }
                    status_row.update(
                        {
                            "table_status": "calculated",
                            "window_start_local": manifest.get("candidate_window_start_local", ""),
                            "window_end_local": manifest.get("candidate_window_end_local", ""),
                            "raw_rows_downloaded": manifest.get("downloaded_rows", ""),
                            "download_source": "reused_existing_local_24h_pilot",
                        }
                    )
                else:
                    t1 = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize("Asia/Jerusalem")
                    if args.anchor_source == "raw-first-in-T1-week":
                        week_start_ms = local_to_ms(t1)
                        week_end_ms = local_to_ms(t1 + pd.Timedelta(days=7))
                        first_ts = first_existing_raw_row(conn, device_id, week_start_ms, week_end_ms)
                        status_row["first_raw_in_T1_week_local"] = ms_to_local(first_ts)
                        if first_ts is None:
                            status_row.update({"table_status": "missing_no_raw_accelerometer_in_T1_week", "error_message": ""})
                            status_rows.append(status_row)
                            print("  no raw accelerometer in T1 week", flush=True)
                            continue
                        start_ms = int(first_ts)
                    else:
                        start_ms = local_string_to_ms(patient.get("window_start_local"))
                        if start_ms is None:
                            status_row.update({"table_status": "missing_no_sensor_metadata_anchor", "error_message": ""})
                            status_rows.append(status_row)
                            print("  no sensor metadata anchor", flush=True)
                            continue
                    end_ms = start_ms + 24 * 60 * 60 * 1000
                    days_after_t1 = (pd.to_datetime(start_ms, unit="ms", utc=True).tz_convert("Asia/Jerusalem") - t1).total_seconds() / 86400
                    manifest = {
                        "Subject_ID_D": subject_id,
                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                        "global_T1": patient.get("global_T1", ""),
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                        "device_id": device_id,
                        "candidate_window_start_ms": start_ms,
                        "candidate_window_end_ms": end_ms,
                        "candidate_window_start_local": ms_to_local(start_ms),
                        "candidate_window_end_local": ms_to_local(end_ms),
                    }
                    status_row["anchor_days_after_T1"] = days_after_t1
                    signal_path, chunk_log, downloaded_rows = write_signal_file(conn, patient, start_ms, end_ms, args.batch_rows)
                    temp_path = signal_path
                    download_chunks.extend(chunk_log)
                    if downloaded_rows == 0:
                        status_row.update(
                            {
                                "table_status": "missing_no_raw_rows_at_accelerometer_anchor",
                                "window_start_local": manifest["candidate_window_start_local"],
                                "window_end_local": manifest["candidate_window_end_local"],
                                "raw_rows_downloaded": downloaded_rows,
                                "download_source": f"temporary_local_download_{args.anchor_source}",
                                "error_message": "No raw rows found in initial anchor chunks.",
                            }
                        )
                        status_rows.append(status_row)
                        continue
                    if any(row["status"] == "error" for row in chunk_log):
                        status_row.update(
                            {
                                "table_status": "download_error",
                                "window_start_local": manifest["candidate_window_start_local"],
                                "window_end_local": manifest["candidate_window_end_local"],
                                "raw_rows_downloaded": downloaded_rows,
                                "download_source": "temporary_local_download",
                                "error_message": "; ".join(row["error_message"] for row in chunk_log if row["error_message"]),
                            }
                        )
                        status_rows.append(status_row)
                        continue
                    status_row.update(
                        {
                            "table_status": "calculated",
                            "window_start_local": manifest["candidate_window_start_local"],
                            "window_end_local": manifest["candidate_window_end_local"],
                            "raw_rows_downloaded": downloaded_rows,
                            "download_source": f"temporary_local_download_{args.anchor_source}",
                        }
                    )

                features, chunks, thresholds, bandpass, bandpass_hourly = analyze_signal_file(signal_path, manifest)
                status_row["rows_after_numeric_and_duplicate_qc"] = int(features.iloc[0]["accelerometer_total_rows_loaded"])
                status_row["duplicates_removed"] = int(features.iloc[0]["accelerometer_exact_duplicate_rows_removed"])
                status_row["valid_signal_minutes"] = float(features.iloc[0]["accelerometer_valid_signal_minutes"])
                feature_wide_rows.append(features.iloc[0].to_dict())
                feature_long.extend(feature_long_rows(features, status_row["table_status"], status_row))
                for frame in [chunks, thresholds, bandpass, bandpass_hourly]:
                    frame.insert(0, "Subject_ID_D", subject_id)
                    frame.insert(1, "device_id", device_id)
                all_chunks.append(chunks)
                all_thresholds.append(thresholds)
                all_bandpass.append(bandpass)
                all_bandpass_hourly.append(bandpass_hourly)
                status_rows.append(status_row)
            except Exception as exc:  # noqa: BLE001
                status_row.update({"table_status": "error", "error_message": str(exc)})
                status_rows.append(status_row)
            finally:
                if temp_path and temp_path.exists() and not args.keep_temp:
                    temp_path.unlink()
    finally:
        conn.close()

    feature_wide_df = pd.DataFrame(feature_wide_rows)
    feature_long_df = pd.DataFrame(feature_long)
    status_df = pd.DataFrame(status_rows)
    download_df = pd.DataFrame(download_chunks)
    chunks_df = pd.concat(all_chunks, ignore_index=True) if all_chunks else pd.DataFrame()
    thresholds_df = pd.concat(all_thresholds, ignore_index=True) if all_thresholds else pd.DataFrame()
    bandpass_df = pd.concat(all_bandpass, ignore_index=True) if all_bandpass else pd.DataFrame()
    bandpass_hourly_df = pd.concat(all_bandpass_hourly, ignore_index=True) if all_bandpass_hourly else pd.DataFrame()

    paths = {
        "wide": OUT_DIR / "phase3_accelerometer_24h_pilot_features_wide.csv",
        "long": OUT_DIR / "phase3_accelerometer_24h_pilot_features_long.csv",
        "status": OUT_DIR / "phase3_accelerometer_24h_pilot_patient_status.csv",
        "download": OUT_DIR / "phase3_accelerometer_24h_pilot_download_chunk_log.csv",
        "chunks": OUT_DIR / "phase3_accelerometer_24h_pilot_chunk_summary.csv",
        "thresholds": OUT_DIR / "phase3_accelerometer_24h_pilot_threshold_sensitivity.csv",
        "bandpass": OUT_DIR / "phase3_accelerometer_24h_pilot_bandpass_summary.csv",
        "bandpass_hourly": OUT_DIR / "phase3_accelerometer_24h_pilot_bandpass_hourly_summary.csv",
        "readme": OUT_DIR / "README_phase3_accelerometer_24h_pilot.md",
    }
    feature_wide_df.to_csv(paths["wide"], index=False)
    feature_long_df.to_csv(paths["long"], index=False)
    status_df.to_csv(paths["status"], index=False)
    download_df.to_csv(paths["download"], index=False)
    chunks_df.to_csv(paths["chunks"], index=False)
    thresholds_df.to_csv(paths["thresholds"], index=False)
    bandpass_df.to_csv(paths["bandpass"], index=False)
    bandpass_hourly_df.to_csv(paths["bandpass_hourly"], index=False)
    paths["readme"].write_text(build_readme(len(patients), status_df, args.anchor_source), encoding="utf-8")

    print("accelerometer_phase3_pilot_complete")
    print(f"candidate_patients_allowed: {len(patients)}")
    print(f"patients_attempted: {len(status_df)}")
    print(f"patients_calculated: {int(status_df['table_status'].eq('calculated').sum()) if not status_df.empty else 0}")
    print("status:")
    print(status_df[["Subject_ID_D", "global_T1", "table_status", "window_start_local", "raw_rows_downloaded"]].to_string(index=False))
    print("generated_files:")
    for path in paths.values():
        print(path)


if __name__ == "__main__":
    main()
