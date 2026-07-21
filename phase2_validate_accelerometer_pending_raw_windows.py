from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from download_accelerometer_24h_pilot import ms_to_local
from main import connect_sensordata_db


ROOT = Path(__file__).parent
PENDING_PATH = (
    ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_all_patient_data_window_frame/accelerometer_pending_raw_validation_metadata_windows.csv"
)
DEVICE_QC_PATH = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_device_window.csv"
OUT_DIR = (
    ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_pending_raw_validation"
)
TABLE_NAME = "accelerometer"
MINUTE_MS = 60 * 1000
DAY_MS = 24 * 60 * 60 * 1000


def as_int_ms(value: Any) -> int | None:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return int(parsed)


def load_pending_windows(path: Path, limit: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].astype(str).str.zfill(3)
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


def validate_pending_row(cur, row: pd.Series, sample_limit: int, probe_minutes: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    subject_id = str(row["Subject_ID_D"]).zfill(3)
    device_id = str(row["selected_device_id"]).strip()
    metadata_start_ms = as_int_ms(row.get("metadata_window_start_ms"))
    metadata_end_ms = as_int_ms(row.get("metadata_window_end_ms"))
    if metadata_start_ms is None or metadata_end_ms is None:
        # The pending CSV stores local strings only in early versions; recover from the all-patient frame is avoided here.
        return {
            **row.to_dict(),
            "raw_validation_status": "error_missing_metadata_epoch_ms",
            "raw_rows_count_status": "not_checked",
        }, []

    probe_width_ms = probe_minutes * MINUTE_MS
    probe_rows: list[dict[str, Any]] = []
    day_index = 0
    anchor_ms = metadata_start_ms
    while anchor_ms < metadata_end_ms:
        probe_start_ms = max(metadata_start_ms, anchor_ms - 5 * MINUTE_MS)
        probe_end_ms = min(metadata_end_ms, probe_start_ms + probe_width_ms)
        result = probe_raw_window(cur, device_id, probe_start_ms, probe_end_ms, sample_limit)
        probe_row = {
            "Subject_ID_D": subject_id,
            "device_id": device_id,
            "day_probe_index": day_index,
            "metadata_window_start_ms": metadata_start_ms,
            "metadata_window_end_ms": metadata_end_ms,
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
            window_end_ms = window_start_ms + DAY_MS
            return {
                **row.to_dict(),
                "raw_validation_status": "raw_window_found_from_pending_metadata_probe",
                "raw_validation_device_id": device_id,
                "raw_validation_probe_day_index": day_index,
                "raw_probe_sampled_rows": result["sampled_rows"],
                "raw_probe_hit_sample_limit": result["hit_sample_limit"],
                "candidate_raw_24h_window_start_ms": window_start_ms,
                "candidate_raw_24h_window_end_ms": window_end_ms,
                "candidate_raw_24h_window_start_local": ms_to_local(window_start_ms),
                "candidate_raw_24h_window_end_local": ms_to_local(window_end_ms),
                "raw_rows_in_24h": "",
                "raw_rows_count_status": "deferred_exact_24h_count",
            }, probe_rows
        day_index += 1
        anchor_ms += DAY_MS

    return {
        **row.to_dict(),
        "raw_validation_status": "missing_no_raw_rows_in_bounded_daily_probes",
        "raw_validation_device_id": device_id,
        "raw_validation_probe_day_index": "",
        "raw_probe_sampled_rows": 0,
        "raw_probe_hit_sample_limit": False,
        "candidate_raw_24h_window_start_ms": "",
        "candidate_raw_24h_window_end_ms": "",
        "candidate_raw_24h_window_start_local": "",
        "candidate_raw_24h_window_end_local": "",
        "raw_rows_in_24h": "",
        "raw_rows_count_status": "not_applicable_no_raw_probe_hit",
    }, probe_rows


def write_outputs(patient_rows: list[dict[str, Any]], probe_rows: list[dict[str, Any]], out_dir: Path) -> None:
    patient_df = pd.DataFrame(patient_rows)
    probe_df = pd.DataFrame(probe_rows)
    patient_csv = out_dir / "accelerometer_pending_raw_validation_patient_windows.csv"
    probe_csv = out_dir / "accelerometer_pending_raw_validation_probes.csv"
    readme_path = out_dir / "README_accelerometer_pending_raw_validation.md"
    patient_df.to_csv(patient_csv, index=False)
    probe_df.to_csv(probe_csv, index=False)
    status_counts = patient_df["raw_validation_status"].value_counts().to_dict() if "raw_validation_status" in patient_df else {}
    status_text = "\n".join(f"- `{key}`: {value}" for key, value in status_counts.items())
    readme_path.write_text(
        f"""# Pending Accelerometer Raw Window Validation

Date: 2026-07-21

Purpose:

- Validate the 67 pending `sensor_accelerometer` metadata windows against raw `accelerometer`.
- Use bounded 20-minute raw probes, repeated once per day across each metadata week.
- Record a candidate 24-hour raw window only when raw rows are found.

Outputs:

- Patient validation table: `{patient_csv}`
- Probe detail table: `{probe_csv}`

Patient rows: {len(patient_df)}
Probe rows: {len(probe_df)}

Raw validation status counts:

{status_text}

Interpretation:

- `raw_window_found_from_pending_metadata_probe`: raw accelerometer rows were found; the row has a validated candidate 24h raw window.
- `missing_no_raw_rows_in_bounded_daily_probes`: no raw rows were found in daily bounded probes across the metadata window.
- Exact 24h raw row counts are deferred to extraction.
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate pending sensor_accelerometer metadata windows against raw accelerometer.")
    parser.add_argument("--pending-csv", type=Path, default=PENDING_PATH)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--limit-patients", type=int)
    parser.add_argument("--sample-limit", type=int, default=1000)
    parser.add_argument("--probe-minutes", type=int, default=20)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pending = load_pending_windows(args.pending_csv, args.limit_patients)
    patient_rows: list[dict[str, Any]] = []
    probe_rows: list[dict[str, Any]] = []

    conn = connect_sensordata_db()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            for idx, (_, row) in enumerate(pending.iterrows(), start=1):
                subject_id = str(row["Subject_ID_D"]).zfill(3)
                print(f"validating {idx}/{len(pending)} Subject_ID_D={subject_id} global_T1={row.get('global_T1', '')}", flush=True)
                patient_row, row_probes = validate_pending_row(cur, row, args.sample_limit, args.probe_minutes)
                patient_rows.append(patient_row)
                probe_rows.extend(row_probes)
                write_outputs(patient_rows, probe_rows, args.out_dir)
        finally:
            cur.close()
    finally:
        conn.close()

    write_outputs(patient_rows, probe_rows, args.out_dir)
    print("accelerometer_pending_raw_validation_complete")
    print(f"patient_csv: {args.out_dir / 'accelerometer_pending_raw_validation_patient_windows.csv'}")
    print(f"probe_csv: {args.out_dir / 'accelerometer_pending_raw_validation_probes.csv'}")
    if patient_rows:
        print(pd.DataFrame(patient_rows)["raw_validation_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
