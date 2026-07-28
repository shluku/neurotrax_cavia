from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from download_accelerometer_24h_pilot import ms_to_local
from main import connect_sensordata_db


ROOT = Path(__file__).parent
QC_PATH = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_patient.csv"
OUT_DIR = (
    ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_top10_first_post_t1_24h"
)
EXCLUDED_SUBJECTS = {"001"}
TABLE_NAME = "accelerometer"
DAY_MS = 24 * 60 * 60 * 1000


def local_date_start_ms(date_value: Any) -> int | None:
    if pd.isna(date_value) or not str(date_value).strip():
        return None
    ts = pd.to_datetime(str(date_value), errors="coerce")
    if pd.isna(ts):
        return None
    if ts.tzinfo is None:
        ts = ts.tz_localize("Asia/Jerusalem")
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def load_top_patients(limit: int) -> pd.DataFrame:
    df = pd.read_csv(QC_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].astype(str).str.zfill(3)
    df["global_T1_num"] = pd.to_numeric(df["global_T1"], errors="coerce")
    df = df.dropna(subset=["Subject_ID_D", "global_T1_num", "T1_date_iso", "selected_device_id"]).copy()
    df = df[~df["Subject_ID_D"].isin(EXCLUDED_SUBJECTS)].copy()
    df = df[df["has_sensor_accelerometer_metadata_after_T1"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    df = df[df["selected_device_id"].astype(str).str.strip().ne("")]
    df = df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True]).head(limit).copy()
    return df


def fetch_one_dict(cur, query: str, params: tuple[Any, ...]) -> dict[str, Any]:
    cur.execute(query, params)
    row = cur.fetchone()
    return dict(row) if row else {}


def find_first_raw_post_t1(cur, device_id: str, t1_start_ms: int, max_search_days: int) -> tuple[int | None, int | None]:
    for day_index in range(max_search_days + 1):
        day_start = t1_start_ms + day_index * DAY_MS
        day_end = day_start + DAY_MS
        cur.execute(
            f"""
            SELECT timestamp AS first_raw_post_t1_ms
            FROM `{TABLE_NAME}`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (device_id, int(day_start), int(day_end)),
        )
        row = cur.fetchone()
        if row and row.get("first_raw_post_t1_ms") is not None:
            return int(row["first_raw_post_t1_ms"]), day_index
    return None, None


def fetch_timestamp_limit(cur, device_id: str, start_ms: int, end_ms: int, limit: int) -> list[int]:
    cur.execute(
        f"""
        SELECT timestamp
        FROM `{TABLE_NAME}`
        WHERE device_id = %s
          AND timestamp >= %s
          AND timestamp < %s
        ORDER BY timestamp ASC
        LIMIT {int(limit)}
        """,
        (device_id, int(start_ms), int(end_ms)),
    )
    return [int(row["timestamp"]) for row in cur.fetchall() if row.get("timestamp") is not None]


def fetch_first_last_in_window(cur, device_id: str, start_ms: int, end_ms: int) -> tuple[int | None, int | None]:
    cur.execute(
        f"""
        SELECT timestamp
        FROM `{TABLE_NAME}`
        WHERE device_id = %s
          AND timestamp >= %s
          AND timestamp < %s
        ORDER BY timestamp ASC
        LIMIT 1
        """,
        (device_id, int(start_ms), int(end_ms)),
    )
    first_row = cur.fetchone()
    cur.execute(
        f"""
        SELECT timestamp
        FROM `{TABLE_NAME}`
        WHERE device_id = %s
          AND timestamp >= %s
          AND timestamp < %s
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (device_id, int(start_ms), int(end_ms)),
    )
    last_row = cur.fetchone()
    first = int(first_row["timestamp"]) if first_row and first_row.get("timestamp") is not None else None
    last = int(last_row["timestamp"]) if last_row and last_row.get("timestamp") is not None else None
    return first, last


def aggregate_24h_by_hour(cur, device_id: str, start_ms: int, sample_limit_per_hour: int) -> dict[str, Any]:
    end_ms = start_ms + DAY_MS
    first_sample_ms, last_sample_ms = fetch_first_last_in_window(cur, device_id, start_ms, end_ms)
    active_hours = 0
    observed_sample_rows = 0
    estimated_rows = 0.0
    median_interval_values: list[float] = []
    hourly_rows: list[dict[str, Any]] = []
    hour_ms = 60 * 60 * 1000
    for hour_index in range(24):
        hour_start = start_ms + hour_index * hour_ms
        hour_end = hour_start + hour_ms
        timestamps = fetch_timestamp_limit(cur, device_id, hour_start, hour_end, sample_limit_per_hour)
        sample_rows = len(timestamps)
        observed_sample_rows += sample_rows
        hour_has_rows = sample_rows > 0
        hour_estimated_rows = float(sample_rows)
        median_interval_ms = None
        if sample_rows >= 2:
            intervals = pd.Series(timestamps).diff().dropna()
            intervals = intervals[intervals > 0]
            if not intervals.empty:
                median_interval_ms = float(intervals.median())
                median_interval_values.append(median_interval_ms)
                hour_span_ms = max(timestamps[-1] - timestamps[0], 0)
                if sample_rows >= sample_limit_per_hour and hour_span_ms > 0:
                    estimated_full_span_rows = hour_ms / median_interval_ms if median_interval_ms > 0 else sample_rows
                    hour_estimated_rows = max(float(sample_rows), float(estimated_full_span_rows))
        estimated_rows += hour_estimated_rows
        if hour_has_rows:
            active_hours += 1
        hourly_rows.append(
            {
                "hour_index": hour_index,
                "hour_start_ms": hour_start,
                "hour_end_ms": hour_end,
                "hour_start_local": ms_to_local(hour_start),
                "hour_end_local": ms_to_local(hour_end),
                "has_rows": hour_has_rows,
                "sampled_rows_for_probe": sample_rows,
                "median_interval_ms_in_probe": median_interval_ms,
                "estimated_rows_for_hour": round(hour_estimated_rows),
            }
        )
    median_sampling_interval_ms = float(pd.Series(median_interval_values).median()) if median_interval_values else None
    return {
        "raw_rows_in_24h": "",
        "raw_rows_count_status": "deferred_exact_count_too_expensive",
        "estimated_raw_rows_in_24h_from_probe": round(estimated_rows),
        "observed_probe_rows_in_24h": observed_sample_rows,
        "first_sample_in_window_ms": first_sample_ms,
        "last_sample_in_window_ms": last_sample_ms,
        "active_hour_bins_in_24h": active_hours,
        "sample_limit_per_hour": sample_limit_per_hour,
        "median_sampling_interval_ms_in_probe": median_sampling_interval_ms,
        "hourly_rows": hourly_rows,
    }


def validate_patient_window(conn, patient: pd.Series) -> dict[str, Any]:
    subject_id = str(patient["Subject_ID_D"])
    device_id = str(patient["selected_device_id"]).strip()
    t1_start_ms = local_date_start_ms(patient["T1_date_iso"])
    base_row: dict[str, Any] = {
        "Subject_ID_D": subject_id,
        "Subject_ID_N": patient.get("Subject_ID_N", ""),
        "global_T1": patient.get("global_T1", ""),
        "T1_date_iso": patient.get("T1_date_iso", ""),
        "device_id": device_id,
        "metadata_anchor_start_local": patient.get("window_start_local", ""),
        "metadata_anchor_end_local": patient.get("window_end_local", ""),
        "metadata_days_first_available_after_T1": patient.get("days_first_available_after_T1", ""),
        "t1_local_day_start_ms": t1_start_ms,
        "t1_local_day_start_local": ms_to_local(t1_start_ms) if t1_start_ms is not None else "",
    }
    if t1_start_ms is None:
        base_row.update({"window_status": "missing_or_unparseable_t1_date"})
        return base_row

    cur = conn.cursor(dictionary=True)
    try:
        first_ms, first_search_day_index = find_first_raw_post_t1(
            cur,
            device_id=device_id,
            t1_start_ms=t1_start_ms,
            max_search_days=120,
        )
        if first_ms is None:
            base_row.update({"window_status": "missing_no_raw_rows_post_t1_within_120_days"})
            return base_row
        end_ms = first_ms + DAY_MS
        aggregate = aggregate_24h_by_hour(cur, device_id, first_ms, sample_limit_per_hour=1000)
    finally:
        cur.close()

    estimated_raw_rows = int(aggregate.get("estimated_raw_rows_in_24h_from_probe") or 0)
    observed_probe_rows = int(aggregate.get("observed_probe_rows_in_24h") or 0)
    active_hours = int(aggregate.get("active_hour_bins_in_24h") or 0)
    last_sample_ms = aggregate.get("last_sample_in_window_ms")
    observed_span_hours = (
        (int(last_sample_ms) - first_ms) / 3600000
        if last_sample_ms is not None and observed_probe_rows > 0
        else 0.0
    )
    delay_days = (first_ms - t1_start_ms) / DAY_MS

    if observed_probe_rows <= 0:
        quality = "missing_no_rows_in_candidate_24h"
    elif estimated_raw_rows < 1000:
        quality = "very_sparse_raw_window"
    elif active_hours < 6:
        quality = "limited_hour_coverage"
    else:
        quality = "valid_raw_24h_window_candidate"

    base_row.update(
        {
            "window_status": "raw_window_found",
            "window_quality": quality,
            "first_raw_search_day_index_from_t1": first_search_day_index,
            "first_raw_post_t1_ms": first_ms,
            "first_raw_post_t1_local": ms_to_local(first_ms),
            "delay_from_t1_local_day_start_days": round(delay_days, 4),
            "candidate_window_start_ms": first_ms,
            "candidate_window_end_ms": end_ms,
            "candidate_window_start_local": ms_to_local(first_ms),
            "candidate_window_end_local": ms_to_local(end_ms),
            "raw_rows_in_24h": aggregate.get("raw_rows_in_24h", ""),
            "raw_rows_count_status": aggregate.get("raw_rows_count_status", ""),
            "estimated_raw_rows_in_24h_from_probe": estimated_raw_rows,
            "observed_probe_rows_in_24h": observed_probe_rows,
            "sample_limit_per_hour": aggregate.get("sample_limit_per_hour", ""),
            "first_sample_in_window_ms": aggregate.get("first_sample_in_window_ms", ""),
            "first_sample_in_window_local": ms_to_local(aggregate.get("first_sample_in_window_ms")),
            "last_sample_in_window_ms": last_sample_ms or "",
            "last_sample_in_window_local": ms_to_local(last_sample_ms),
            "observed_span_hours_in_window": round(observed_span_hours, 4),
            "active_hour_bins_in_24h": active_hours,
            "median_sampling_interval_ms_in_probe": aggregate.get("median_sampling_interval_ms_in_probe", ""),
        }
    )
    return base_row


def build_readme(result: pd.DataFrame, output_csv: Path) -> str:
    quality_counts = result["window_quality"].fillna(result["window_status"]).value_counts().to_dict()
    quality_text = "\n".join(f"- `{key}`: {value}" for key, value in quality_counts.items())
    return f"""# Accelerometer Top-10 First Post-T1 24h Window Validation

Date: 2026-07-21

Purpose:

- Validate whether the top 10 patients by `global_T1` have a usable raw `accelerometer` 24-hour window.
- Do not extract raw signal files.
- Do not compute accelerometer behavioral features yet.
- Only find and count the first available raw 24-hour window after T1.

Window rule:

- Rank patients by descending `global_T1`.
- Require `sensor_accelerometer` metadata after T1 and a non-empty `selected_device_id`.
- Exclude subject `001`.
- Convert `T1_date_iso` to local Asia/Jerusalem midnight.
- Find the first raw `accelerometer.timestamp` for the selected device at or after that T1 local day start.
- Define the candidate window as that first raw timestamp through the next 24 hours.

Output table:

`{output_csv}`

Rows written: {len(result)}

Window quality counts:

{quality_text}

Important interpretation:

- This pilot validates candidate windows, not clinical movement features.
- A patient can have sensor metadata after T1 but no raw accelerometer rows at the metadata anchor.
- For this pilot, the window is allowed to start late after T1. The delay is reported in `delay_from_t1_local_day_start_days`.
- `raw_rows_in_24h` is raw SQL row count, before x/y/z parsing and duplicate QC.
- Counts are computed as 24 bounded one-hour SQL queries to avoid open-ended scans on the very large raw table.
- This pilot does not compute distinct timestamp or exact x/y/z duplicate counts; those belong in the later signal-analysis phase.
- Use `window_quality` to choose which patients are safe for the next raw-signal analysis pilot.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate first post-T1 24h raw accelerometer windows for top T1 patients.")
    parser.add_argument("--limit-patients", type=int, default=10)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.out_dir / "accelerometer_top10_first_post_t1_24h_window_validation.csv"
    readme_path = args.out_dir / "README_accelerometer_top10_first_post_t1_24h_window_validation.md"

    patients = load_top_patients(args.limit_patients)
    rows: list[dict[str, Any]] = []
    conn = connect_sensordata_db()
    try:
        for idx, (_, patient) in enumerate(patients.iterrows(), start=1):
            subject_id = str(patient["Subject_ID_D"])
            print(f"validating {idx}/{len(patients)} Subject_ID_D={subject_id} global_T1={patient.get('global_T1', '')}", flush=True)
            rows.append(validate_patient_window(conn, patient))
    finally:
        conn.close()

    result = pd.DataFrame(rows)
    result.to_csv(output_csv, index=False)
    readme_path.write_text(build_readme(result, output_csv), encoding="utf-8")

    print("accelerometer_top10_window_validation_complete")
    print(f"rows: {len(result)}")
    print(f"output_csv: {output_csv}")
    print(f"readme: {readme_path}")
    if "window_quality" in result.columns:
        print("window_quality_counts:")
        print(result["window_quality"].fillna(result["window_status"]).value_counts().to_string())


if __name__ == "__main__":
    main()
