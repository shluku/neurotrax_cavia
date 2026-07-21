from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from download_accelerometer_24h_pilot import ms_to_local
from main import connect_sensordata_db


ROOT = Path(__file__).parent
WINDOW_FRAME_PATH = (
    ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_all_patient_data_window_frame/accelerometer_all_patient_data_window_frame.csv"
)
COGNITIVE_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
DEVICE_QC_PATH = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_device_window.csv"
OUT_DIR = (
    ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_no_raw_38_weekly_t1_t2_probe"
)
TABLE_NAME = "accelerometer"
MINUTE_MS = 60 * 1000
DAY_MS = 24 * 60 * 60 * 1000
WEEK_MS = 7 * DAY_MS


def as_int_ms(value: Any) -> int | None:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return int(parsed)


def load_no_raw_patients(limit: int | None = None) -> pd.DataFrame:
    frame = pd.read_csv(WINDOW_FRAME_PATH, dtype=str)
    frame["Subject_ID_D"] = frame["Subject_ID_D"].astype(str).str.zfill(3)
    frame = frame[frame["data_window_status"].eq("no_raw_rows_in_validated_metadata_window")].copy()

    cognitive = pd.read_csv(COGNITIVE_PATH, dtype=str)
    cognitive["Subject_ID_D"] = cognitive["Subject_ID_D"].astype(str).str.zfill(3)
    fallback_t2_end_ms = pd.to_numeric(cognitive["T2_end_ms"], errors="coerce").max()
    cognitive = cognitive[["Subject_ID_D", "T2_date_iso", "T1_start_ms", "T2_start_ms", "T2_end_ms"]].copy()

    df = frame.merge(cognitive, on="Subject_ID_D", how="left")
    device_qc = pd.read_csv(DEVICE_QC_PATH, dtype=str)
    device_qc["Subject_ID_D"] = device_qc["Subject_ID_D"].astype(str).str.zfill(3)
    device_qc = device_qc[device_qc["has_metadata_after_T1"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    device_qc["days_first_available_num"] = pd.to_numeric(device_qc["days_first_available_after_T1"], errors="coerce")
    device_qc["n_rows_num"] = pd.to_numeric(device_qc["n_rows"], errors="coerce").fillna(0)
    device_qc = device_qc.sort_values(
        ["Subject_ID_D", "device_id", "days_first_available_num", "window_start_ms", "n_rows_num"],
        ascending=[True, True, True, True, False],
    )
    selected_windows = device_qc.drop_duplicates(["Subject_ID_D", "device_id"], keep="first")[
        ["Subject_ID_D", "device_id", "window_start_ms", "window_end_ms"]
    ].rename(
        columns={
            "device_id": "selected_device_id",
            "window_start_ms": "metadata_window_start_ms",
            "window_end_ms": "metadata_window_end_ms",
        }
    )
    df = df.merge(selected_windows, on=["Subject_ID_D", "selected_device_id"], how="left")
    df["study_span_end_bound_source"] = "T2_end_ms"
    missing_t2 = pd.to_numeric(df["T2_end_ms"], errors="coerce").isna()
    df.loc[missing_t2, "T2_end_ms"] = str(int(fallback_t2_end_ms)) if pd.notna(fallback_t2_end_ms) else ""
    df.loc[missing_t2, "study_span_end_bound_source"] = "cohort_max_T2_end_ms_fallback"
    df["global_T1_num"] = pd.to_numeric(df["global_T1"], errors="coerce")
    df = df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True]).drop(columns=["global_T1_num"])
    if limit is not None:
        df = df.head(limit).copy()
    return df


def probe_raw_window(cur, device_id: str, start_ms: int, end_ms: int, sample_limit: int) -> dict[str, Any]:
    cur.execute(
        f"""
        SELECT timestamp
        FROM `{TABLE_NAME}`
        WHERE timestamp >= %s
          AND timestamp < %s
          AND device_id = %s
        ORDER BY timestamp ASC
        LIMIT {int(sample_limit)}
        """,
        (int(start_ms), int(end_ms), device_id),
    )
    timestamps = [as_int_ms(row.get("timestamp")) for row in cur.fetchall()]
    timestamps = [value for value in timestamps if value is not None]
    first_ts = timestamps[0] if timestamps else None
    last_ts = timestamps[-1] if timestamps else None
    return {
        "hit": first_ts is not None,
        "sampled_rows": len(timestamps),
        "hit_sample_limit": len(timestamps) >= sample_limit,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "first_local": ms_to_local(first_ts),
        "last_local": ms_to_local(last_ts),
    }


def latest_weekly_anchor(metadata_start_ms: int, span_end_ms: int) -> int:
    if span_end_ms <= metadata_start_ms:
        return metadata_start_ms
    steps = (span_end_ms - metadata_start_ms) // WEEK_MS
    return metadata_start_ms + steps * WEEK_MS


def validate_patient(cur, row: pd.Series, sample_limit: int, probe_minutes: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    subject_id = str(row["Subject_ID_D"]).zfill(3)
    device_id = str(row["selected_device_id"]).strip()
    t1_start_ms = as_int_ms(row.get("T1_start_ms"))
    t2_end_ms = as_int_ms(row.get("T2_end_ms")) or as_int_ms(row.get("T2_start_ms"))
    metadata_start_ms = as_int_ms(row.get("metadata_window_start_ms"))
    if t1_start_ms is None or t2_end_ms is None or metadata_start_ms is None:
        return {
            **row.to_dict(),
            "broad_raw_validation_status": "error_missing_t1_t2_or_metadata_epoch_ms",
            "broad_probe_count": 0,
        }, []

    probe_width_ms = probe_minutes * MINUTE_MS
    anchor_ms = latest_weekly_anchor(metadata_start_ms, t2_end_ms)
    probe_rows: list[dict[str, Any]] = []
    backward_week_index = 0

    while anchor_ms >= t1_start_ms:
        probe_start_ms = max(t1_start_ms, anchor_ms - 5 * MINUTE_MS)
        probe_end_ms = min(t2_end_ms, probe_start_ms + probe_width_ms)
        if probe_start_ms >= probe_end_ms:
            anchor_ms -= WEEK_MS
            backward_week_index += 1
            continue
        result = probe_raw_window(cur, device_id, probe_start_ms, probe_end_ms, sample_limit)
        probe_row = {
            "Subject_ID_D": subject_id,
            "device_id": device_id,
            "backward_week_index": backward_week_index,
            "T1_date_iso": row.get("T1_date_iso", ""),
            "T2_date_iso": row.get("T2_date_iso", ""),
            "study_span_end_bound_source": row.get("study_span_end_bound_source", ""),
            "metadata_window_start_local": row.get("metadata_window_start_local", ""),
            "metadata_window_end_local": row.get("metadata_window_end_local", ""),
            "probe_start_ms": probe_start_ms,
            "probe_end_ms": probe_end_ms,
            "probe_start_local": ms_to_local(probe_start_ms),
            "probe_end_local": ms_to_local(probe_end_ms),
            "sample_limit": sample_limit,
            "sampled_rows": result["sampled_rows"],
            "hit": result["hit"],
            "hit_sample_limit": result["hit_sample_limit"],
            "first_raw_ts": result["first_ts"] or "",
            "first_raw_local": result["first_local"],
            "last_raw_ts": result["last_ts"] or "",
            "last_raw_local": result["last_local"],
        }
        probe_rows.append(probe_row)
        if result["hit"]:
            window_start_ms = int(result["first_ts"])
            return {
                **row.to_dict(),
                "broad_raw_validation_status": "raw_window_found_from_weekly_t1_t2_probe",
                "broad_probe_count": len(probe_rows),
                "broad_probe_backward_week_index": backward_week_index,
                "broad_raw_probe_sampled_rows": result["sampled_rows"],
                "broad_raw_probe_hit_sample_limit": result["hit_sample_limit"],
                "candidate_raw_24h_window_start_ms": window_start_ms,
                "candidate_raw_24h_window_end_ms": window_start_ms + DAY_MS,
                "candidate_raw_24h_window_start_local": ms_to_local(window_start_ms),
                "candidate_raw_24h_window_end_local": ms_to_local(window_start_ms + DAY_MS),
            }, probe_rows
        anchor_ms -= WEEK_MS
        backward_week_index += 1

    return {
        **row.to_dict(),
        "broad_raw_validation_status": "missing_no_raw_rows_in_weekly_t1_t2_probes",
        "broad_probe_count": len(probe_rows),
        "broad_probe_backward_week_index": "",
        "broad_raw_probe_sampled_rows": 0,
        "broad_raw_probe_hit_sample_limit": False,
        "candidate_raw_24h_window_start_ms": "",
        "candidate_raw_24h_window_end_ms": "",
        "candidate_raw_24h_window_start_local": "",
        "candidate_raw_24h_window_end_local": "",
    }, probe_rows


def write_outputs(patient_rows: list[dict[str, Any]], probe_rows: list[dict[str, Any]], out_dir: Path) -> None:
    patient_df = pd.DataFrame(patient_rows)
    probe_df = pd.DataFrame(probe_rows)
    patient_csv = out_dir / "accelerometer_no_raw_38_weekly_t1_t2_patient_windows.csv"
    probe_csv = out_dir / "accelerometer_no_raw_38_weekly_t1_t2_probes.csv"
    readme_path = out_dir / "README_accelerometer_no_raw_38_weekly_t1_t2_probe.md"
    patient_df.to_csv(patient_csv, index=False)
    probe_df.to_csv(probe_csv, index=False)
    status_counts = patient_df["broad_raw_validation_status"].value_counts().to_dict() if "broad_raw_validation_status" in patient_df else {}
    status_text = "\n".join(f"- `{key}`: {value}" for key, value in status_counts.items())
    readme_path.write_text(
        f"""# Accelerometer 38 No-Raw Weekly T1-T2 Probe

Date: 2026-07-21

Purpose:

- Re-check patients that had `sensor_accelerometer` metadata but no raw rows in the selected metadata week.
- Probe raw `accelerometer` across each patient's broader T1-to-T2 study span.
- Use short bounded probes aligned to the metadata time-of-day, jumping backward weekly from near T2.
- If a patient has no T2 date, use the cohort's latest available T2 end timestamp as a fallback upper bound.

Outputs:

- Patient validation table: `{patient_csv}`
- Probe detail table: `{probe_csv}`

Patient rows: {len(patient_df)}
Probe rows: {len(probe_df)}

Raw validation status counts:

{status_text}

Interpretation:

- `raw_window_found_from_weekly_t1_t2_probe`: raw accelerometer rows were found in a weekly T1-to-T2 probe.
- `missing_no_raw_rows_in_weekly_t1_t2_probes`: no raw rows were found in the weekly T1-to-T2 probe series.
- This is still a bounded probe strategy, not a continuous full raw-table scan.
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Broad weekly T1-T2 raw accelerometer probe for 38 no-raw metadata-window patients.")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--limit-patients", type=int)
    parser.add_argument("--sample-limit", type=int, default=10)
    parser.add_argument("--probe-minutes", type=int, default=20)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    patients = load_no_raw_patients(args.limit_patients)
    patient_rows: list[dict[str, Any]] = []
    probe_rows: list[dict[str, Any]] = []

    conn = connect_sensordata_db()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            for idx, (_, row) in enumerate(patients.iterrows(), start=1):
                subject_id = str(row["Subject_ID_D"]).zfill(3)
                print(f"probing {idx}/{len(patients)} Subject_ID_D={subject_id} global_T1={row.get('global_T1', '')}", flush=True)
                patient_row, row_probes = validate_patient(cur, row, args.sample_limit, args.probe_minutes)
                patient_rows.append(patient_row)
                probe_rows.extend(row_probes)
                write_outputs(patient_rows, probe_rows, args.out_dir)
        finally:
            cur.close()
    finally:
        conn.close()

    write_outputs(patient_rows, probe_rows, args.out_dir)
    print("accelerometer_no_raw_38_weekly_t1_t2_probe_complete")
    print(f"patient_csv: {args.out_dir / 'accelerometer_no_raw_38_weekly_t1_t2_patient_windows.csv'}")
    print(f"probe_csv: {args.out_dir / 'accelerometer_no_raw_38_weekly_t1_t2_probes.csv'}")
    if patient_rows:
        print(pd.DataFrame(patient_rows)["broad_raw_validation_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
