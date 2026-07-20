from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from analyze_accelerometer_24h_local_pilot import (
    BANDS,
    CHUNK_MINUTES,
    analyze_chunk,
    build_bandpass_feature_summary,
    build_bandpass_hourly_summary,
    build_threshold_sensitivity,
    summarize_features,
)
from download_accelerometer_24h_pilot import ms_to_local, parse_data, signal_fields
from main import connect_sensordata_db
from phase3_extract_accelerometer_24h_pilot import FEATURE_NAMES, local_string_to_ms


ROOT = Path(__file__).parent
QC_PATH = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_patient.csv"
EXISTING_041_MANIFEST = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot/accelerometer_24h_pilot_manifest.csv"
EXISTING_041_SIGNAL = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot"
DEFAULT_OUT_DIR = (
    ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_all_t1_streaming"
)
EXCLUDED_SUBJECTS = {"001"}
TABLE_NAME = "accelerometer"
MAX_INITIAL_EMPTY_CHUNKS = 12


def append_csv(df: pd.DataFrame, path: Path) -> None:
    if df.empty:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, mode="a", index=False, header=not path.exists())


def write_jsonl(row: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_completed_subjects(status_path: Path) -> set[str]:
    if not status_path.exists():
        return set()
    status = pd.read_csv(status_path, dtype=str)
    if status.empty or "Subject_ID_D" not in status.columns:
        return set()
    return set(status["Subject_ID_D"].astype(str).str.zfill(3))


def load_ranked_patients(limit: int = 0) -> pd.DataFrame:
    df = pd.read_csv(QC_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].astype(str).str.zfill(3)
    df["global_T1_num"] = pd.to_numeric(df["global_T1"], errors="coerce")
    df = df.dropna(subset=["Subject_ID_D", "global_T1_num", "T1_date_iso", "selected_device_id"]).copy()
    df = df[~df["Subject_ID_D"].isin(EXCLUDED_SUBJECTS)].copy()
    df = df[df["has_sensor_accelerometer_metadata_after_T1"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    df = df[df["selected_device_id"].astype(str).str.strip().ne("")]
    df = df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True]).copy()
    if limit > 0:
        df = df.head(limit).copy()
    return df


def fetch_chunk_rows(conn, device_id: str, start_ms: int, end_ms: int, batch_rows: int) -> tuple[pd.DataFrame, int]:
    cur = conn.cursor(dictionary=True)
    signal_rows: list[dict[str, Any]] = []
    raw_rows = 0
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
            raw_rows += len(rows)
            for row in rows:
                data = parse_data(row.get("data"))
                fields = signal_fields(data)
                signal_rows.append(
                    {
                        "timestamp": row.get("timestamp", ""),
                        "local_datetime": ms_to_local(row.get("timestamp")),
                        "device_id": row.get("device_id", ""),
                        **fields,
                    }
                )
    finally:
        cur.close()

    df = pd.DataFrame(signal_rows)
    if df.empty:
        return df, raw_rows
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    for col in ["x", "y", "z", "magnitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["timestamp", "x", "y", "z", "magnitude"]).copy()
    if df.empty:
        return df, raw_rows
    df["timestamp"] = df["timestamp"].astype("int64")
    df = df.sort_values("timestamp")
    df["dt_utc"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["dt_local"] = df["dt_utc"].dt.tz_convert("Asia/Jerusalem")
    return df, raw_rows


def analyze_streaming_patient(conn, patient: pd.Series, paths: dict[str, Path], batch_rows: int, max_chunks: int = 0) -> dict[str, Any]:
    subject_id = str(patient["Subject_ID_D"])
    device_id = str(patient["selected_device_id"]).strip()
    start_ms = local_string_to_ms(patient.get("window_start_local"))
    status_row: dict[str, Any] = {
        "Subject_ID_D": subject_id,
        "Subject_ID_N": patient.get("Subject_ID_N", ""),
        "global_T1": patient.get("global_T1", ""),
        "T1_date_iso": patient.get("T1_date_iso", ""),
        "device_id": device_id,
        "source_table": TABLE_NAME,
        "protocol_variant": "accelerometer_special_phase3_24h_streaming_sensor_metadata_anchor",
        "anchor_source": "sensor_accelerometer.window_start_local",
    }
    if start_ms is None:
        status_row.update({"table_status": "missing_no_sensor_metadata_anchor"})
        append_csv(pd.DataFrame([status_row]), paths["status"])
        return status_row

    end_ms = start_ms + 24 * 60 * 60 * 1000
    status_row.update(
        {
            "window_start_ms": start_ms,
            "window_end_ms": end_ms,
            "window_start_local": ms_to_local(start_ms),
            "window_end_local": ms_to_local(end_ms),
        }
    )

    chunk_rows: list[dict[str, Any]] = []
    download_rows: list[dict[str, Any]] = []
    total_raw_rows = 0
    total_clean_rows = 0
    total_duplicate_rows = 0
    consecutive_initial_empty_chunks = 0
    chunk_ms = CHUNK_MINUTES * 60 * 1000
    t = start_ms
    chunk_index = 0
    while t < end_ms:
        t_next = min(t + chunk_ms, end_ms)
        chunk_status = "ok"
        error_message = ""
        raw_rows = 0
        try:
            chunk_df, raw_rows = fetch_chunk_rows(conn, device_id, t, t_next, batch_rows)
            before = len(chunk_df)
            if not chunk_df.empty:
                chunk_df = chunk_df.drop_duplicates(subset=["timestamp", "x", "y", "z"], keep="first").copy()
            duplicate_rows = before - len(chunk_df)
            total_raw_rows += raw_rows
            total_clean_rows += len(chunk_df)
            total_duplicate_rows += duplicate_rows
            if total_raw_rows == 0 and raw_rows == 0:
                consecutive_initial_empty_chunks += 1
            else:
                consecutive_initial_empty_chunks = 0
            if total_raw_rows == 0 and consecutive_initial_empty_chunks >= MAX_INITIAL_EMPTY_CHUNKS:
                chunk_status = "initial_anchor_no_rows"
            analysis_row = analyze_chunk(chunk_index, t, t_next, chunk_df)
            analysis_row.update({"Subject_ID_D": subject_id, "device_id": device_id, "raw_rows_downloaded": raw_rows})
            chunk_rows.append(analysis_row)
        except Exception as exc:  # noqa: BLE001
            chunk_status = "error"
            error_message = str(exc)

        log_row = {
            "Subject_ID_D": subject_id,
            "device_id": device_id,
            "chunk_index": chunk_index,
            "chunk_start_ms": t,
            "chunk_end_ms": t_next,
            "chunk_start_local": ms_to_local(t),
            "chunk_end_local": ms_to_local(t_next),
            "raw_rows_downloaded": raw_rows,
            "cumulative_raw_rows_downloaded": total_raw_rows,
            "status": chunk_status,
            "error_message": error_message,
        }
        download_rows.append(log_row)
        append_csv(pd.DataFrame([log_row]), paths["download"])
        print(
            f"patient={subject_id} chunk={chunk_index:03d} {ms_to_local(t)} rows={log_row['raw_rows_downloaded']:,} status={chunk_status}",
            flush=True,
        )
        if chunk_status in {"error", "initial_anchor_no_rows"}:
            break
        t = t_next
        chunk_index += 1
        if max_chunks > 0 and chunk_index >= max_chunks:
            break

    if total_raw_rows == 0:
        status_row.update(
            {
                "table_status": "missing_no_raw_rows_at_accelerometer_anchor",
                "raw_rows_downloaded": 0,
                "rows_after_numeric_and_duplicate_qc": 0,
                "duplicates_removed": 0,
                "valid_signal_minutes": 0,
                "error_message": "No raw rows found in initial anchor chunks.",
            }
        )
        append_csv(pd.DataFrame([status_row]), paths["status"])
        return status_row

    chunk_df = pd.DataFrame(chunk_rows)
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
    features_df = summarize_features(chunk_df, manifest, total_clean_rows, total_duplicate_rows)
    thresholds_df = build_threshold_sensitivity(chunk_df)
    bandpass_df = build_bandpass_feature_summary(chunk_df)
    bandpass_hourly_df = build_bandpass_hourly_summary(chunk_df)

    for frame in [features_df, thresholds_df, bandpass_df, bandpass_hourly_df]:
        if not frame.empty and "Subject_ID_D" not in frame.columns:
            frame.insert(0, "Subject_ID_D", subject_id)
        if not frame.empty and "device_id" not in frame.columns:
            frame.insert(1, "device_id", device_id)

    long_rows = []
    feature_row = features_df.iloc[0].to_dict() if not features_df.empty else {}
    for feature_name in FEATURE_NAMES:
        value = feature_row.get(feature_name, np.nan)
        long_rows.append(
            {
                "Subject_ID_D": subject_id,
                "Subject_ID_N": patient.get("Subject_ID_N", ""),
                "global_T1": patient.get("global_T1", ""),
                "T1_date_iso": patient.get("T1_date_iso", ""),
                "source_table": TABLE_NAME,
                "feature_name": feature_name,
                "feature_value": value,
                "feature_status": "calculated" if not pd.isna(value) else "insufficient_data_feature_missing",
                "window_start_local": ms_to_local(start_ms),
                "window_end_local": ms_to_local(end_ms),
                "device_ids_used": device_id,
                "protocol_variant": "accelerometer_special_phase3_24h_streaming_sensor_metadata_anchor",
            }
        )

    append_csv(features_df, paths["wide"])
    append_csv(pd.DataFrame(long_rows), paths["long"])
    append_csv(chunk_df, paths["chunks"])
    append_csv(thresholds_df, paths["thresholds"])
    append_csv(bandpass_df, paths["bandpass"])
    append_csv(bandpass_hourly_df, paths["bandpass_hourly"])

    status_row.update(
        {
            "table_status": "calculated",
            "raw_rows_downloaded": total_raw_rows,
            "rows_after_numeric_and_duplicate_qc": total_clean_rows,
            "duplicates_removed": total_duplicate_rows,
            "valid_signal_minutes": feature_row.get("accelerometer_valid_signal_minutes", np.nan),
            "error_message": "",
        }
    )
    append_csv(pd.DataFrame([status_row]), paths["status"])
    write_jsonl(status_row, paths["checkpoint"])
    return status_row


def build_readme() -> str:
    return """# Accelerometer Special Phase 3 All-T1 Streaming Run

This is the production-style accelerometer Phase 3 implementation.

Key design:

- Does not save full raw 24-hour files.
- Streams each patient in 5-minute SQL chunks.
- SQL is always filtered by `device_id` and timestamp bounds.
- Each chunk is parsed, duplicate-cleaned, analyzed, and discarded from memory.
- Outputs are appended after each patient/chunk so the run is resumable.
- Patient `001` is excluded.

Anchor rule:

- Uses the `sensor_accelerometer` metadata anchor timestamp from the QC table.
- Runs a 24-hour window from that anchor.
- If the first 12 chunks are empty, the patient is marked missing at that anchor and skipped.

Interpretation:

- These are phone-state exploratory features, not diagnostic markers.
- Missing data remains missing.
- Frequency features include sampling feasibility checks.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Streaming all-T1 Phase 3 accelerometer feature extraction.")
    parser.add_argument("--limit-patients", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--batch-rows", type=int, default=10000)
    parser.add_argument("--max-chunks", type=int, default=0, help="Debug cap per patient; 0 means full 24h.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "wide": out_dir / "phase3_accelerometer_24h_all_t1_streaming_features_wide.csv",
        "long": out_dir / "phase3_accelerometer_24h_all_t1_streaming_features_long.csv",
        "status": out_dir / "phase3_accelerometer_24h_all_t1_streaming_patient_status.csv",
        "download": out_dir / "phase3_accelerometer_24h_all_t1_streaming_download_chunk_log.csv",
        "chunks": out_dir / "phase3_accelerometer_24h_all_t1_streaming_chunk_summary.csv",
        "thresholds": out_dir / "phase3_accelerometer_24h_all_t1_streaming_threshold_sensitivity.csv",
        "bandpass": out_dir / "phase3_accelerometer_24h_all_t1_streaming_bandpass_summary.csv",
        "bandpass_hourly": out_dir / "phase3_accelerometer_24h_all_t1_streaming_bandpass_hourly_summary.csv",
        "checkpoint": out_dir / "phase3_accelerometer_24h_all_t1_streaming_checkpoint.jsonl",
        "readme": out_dir / "README_phase3_accelerometer_24h_all_t1_streaming.md",
    }
    paths["readme"].write_text(build_readme(), encoding="utf-8")

    completed = load_completed_subjects(paths["status"]) if args.resume else set()
    patients = load_ranked_patients(args.limit_patients)
    if completed:
        patients = patients[~patients["Subject_ID_D"].isin(completed)].copy()

    print(f"accelerometer_streaming_start candidates={len(patients)} resume={args.resume}", flush=True)
    conn = connect_sensordata_db()
    try:
        for idx, (_, patient) in enumerate(patients.iterrows(), start=1):
            subject_id = str(patient["Subject_ID_D"])
            print(f"patient {idx}/{len(patients)} Subject_ID_D={subject_id} global_T1={patient.get('global_T1', '')}", flush=True)
            try:
                analyze_streaming_patient(conn, patient, paths, args.batch_rows, args.max_chunks)
            except Exception as exc:  # noqa: BLE001
                status_row = {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": patient.get("selected_device_id", ""),
                    "source_table": TABLE_NAME,
                    "protocol_variant": "accelerometer_special_phase3_24h_streaming_sensor_metadata_anchor",
                    "table_status": "error",
                    "error_message": str(exc),
                }
                append_csv(pd.DataFrame([status_row]), paths["status"])
                write_jsonl(status_row, paths["checkpoint"])
                try:
                    conn.close()
                except Exception:
                    pass
                conn = connect_sensordata_db()
    finally:
        conn.close()

    status = pd.read_csv(paths["status"], dtype=str) if paths["status"].exists() else pd.DataFrame()
    calculated = int(status["table_status"].eq("calculated").sum()) if not status.empty else 0
    print("accelerometer_streaming_complete", flush=True)
    print(f"status_rows: {len(status)}", flush=True)
    print(f"calculated_patients: {calculated}", flush=True)
    print(f"out_dir: {out_dir}", flush=True)


if __name__ == "__main__":
    main()
