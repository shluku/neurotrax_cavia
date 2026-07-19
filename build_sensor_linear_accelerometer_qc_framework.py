from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db
from phase2_extract_selected_features_all_t1_patients import (
    EXCLUDED_COHORT_SUBJECT_IDS,
    load_device_map_strict,
    load_t1_patients,
)
from phase2_sample_sensor_linear_accelerometer_first_available_week_for_feature_review import (
    count_rows,
    first_available_ts_after_t1,
)
from phase2_sample_table_exploratory_t1_week_for_feature_review import TZ, ms_to_local, parse_json


ROOT = Path(__file__).parent
TABLE_NAME = "sensor_linear_accelerometer"
OUT_DIR = ROOT / "output/analysis_candidates/phase2_accelerometer_framework"
PATIENT_QC_PATH = OUT_DIR / "sensor_linear_accelerometer_qc_by_patient.csv"
DEVICE_QC_PATH = OUT_DIR / "sensor_linear_accelerometer_qc_by_device_window.csv"
README_PATH = OUT_DIR / "README_accelerometer_framework.md"
WINDOW_DAYS = 7
MAX_FETCH_ROWS_PER_DEVICE_WINDOW = 10000


def local_to_ms(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def numeric(value: Any) -> float | None:
    out = pd.to_numeric(value, errors="coerce")
    if pd.isna(out):
        return None
    return float(out)


def median_or_na(values: list[float]) -> float | pd._libs.missing.NAType:
    if not values:
        return pd.NA
    return float(pd.Series(values, dtype="float64").median())


def p95_or_na(values: list[float]) -> float | pd._libs.missing.NAType:
    if not values:
        return pd.NA
    return float(pd.Series(values, dtype="float64").quantile(0.95))


def joined_counter(values: list[str]) -> str:
    cleaned = [str(value) for value in values if str(value).strip() and str(value).lower() not in {"nan", "none"}]
    if not cleaned:
        return ""
    counts = Counter(cleaned)
    return "; ".join(f"{key}:{value}" for key, value in sorted(counts.items()))


def fetch_rows(conn, device_id: str, start_ms: int, end_ms: int, limit: int) -> list[dict[str, Any]]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT _id, timestamp, device_id, data
            FROM `sensor_linear_accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT %s
            """,
            (device_id, int(start_ms), int(end_ms), int(limit)),
        )
        return cur.fetchall()
    finally:
        cur.close()


def summarize_rows(rows: list[dict[str, Any]], n_rows_total: int) -> dict[str, Any]:
    timestamps = sorted(
        int(ts)
        for ts in pd.to_numeric([row.get("timestamp") for row in rows], errors="coerce")
        if pd.notna(ts)
    )
    intervals_sec = [
        (timestamps[index] - timestamps[index - 1]) / 1000.0
        for index in range(1, len(timestamps))
        if timestamps[index] >= timestamps[index - 1]
    ]

    active_days = set()
    active_hours = set()
    for ts in timestamps:
        local = pd.to_datetime(ts, unit="ms", utc=True).tz_convert(TZ)
        active_days.add(local.strftime("%Y-%m-%d"))
        active_hours.add(local.strftime("%Y-%m-%d %H"))

    sensor_names: list[str] = []
    sensor_vendors: list[str] = []
    sensor_types: list[str] = []
    sensor_versions: list[str] = []
    resolution_values: list[float] = []
    max_range_values: list[float] = []
    power_values: list[float] = []
    minimum_delay_values: list[float] = []
    parse_errors = 0

    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        sensor_names.append(str(obj.get("sensor_name", "")))
        sensor_vendors.append(str(obj.get("sensor_vendor", "")))
        sensor_types.append(str(obj.get("sensor_type", "")))
        sensor_versions.append(str(obj.get("sensor_version", "")))
        for key, target in [
            ("double_sensor_resolution", resolution_values),
            ("double_sensor_maximum_range", max_range_values),
            ("double_sensor_power_ma", power_values),
            ("double_sensor_minimum_delay", minimum_delay_values),
        ]:
            value = numeric(obj.get(key))
            if value is not None:
                target.append(value)

    min_delay_us = median_or_na(minimum_delay_values)
    implied_max_hz = pd.NA
    if pd.notna(min_delay_us) and float(min_delay_us) > 0:
        implied_max_hz = 1_000_000.0 / float(min_delay_us)

    observed_span_hours = pd.NA
    if len(timestamps) >= 2:
        observed_span_hours = (timestamps[-1] - timestamps[0]) / 1000.0 / 3600.0

    if n_rows_total == 0:
        qc_level = "no_metadata_after_T1"
    elif n_rows_total < 2:
        qc_level = "very_sparse_metadata"
    elif len(active_hours) < 2:
        qc_level = "sparse_metadata"
    else:
        qc_level = "metadata_available_for_device_context"

    return {
        "n_rows_fetched_for_qc": len(rows),
        "fetch_was_capped": n_rows_total > len(rows),
        "first_fetched_local": ms_to_local(timestamps[0]) if timestamps else "",
        "last_fetched_local": ms_to_local(timestamps[-1]) if timestamps else "",
        "observed_span_hours_fetched": observed_span_hours,
        "active_day_count_fetched": len(active_days) if timestamps else 0,
        "active_hour_count_fetched": len(active_hours) if timestamps else 0,
        "median_interval_sec_fetched": median_or_na(intervals_sec),
        "p95_interval_sec_fetched": p95_or_na(intervals_sec),
        "max_gap_sec_fetched": max(intervals_sec) if intervals_sec else pd.NA,
        "gaps_gt_5min_count_fetched": sum(value > 300 for value in intervals_sec),
        "gaps_gt_1h_count_fetched": sum(value > 3600 for value in intervals_sec),
        "sensor_name_counts": joined_counter(sensor_names),
        "sensor_vendor_counts": joined_counter(sensor_vendors),
        "sensor_type_counts": joined_counter(sensor_types),
        "sensor_version_counts": joined_counter(sensor_versions),
        "minimum_delay_us_median": min_delay_us,
        "implied_max_sampling_hz_from_minimum_delay": implied_max_hz,
        "resolution_median": median_or_na(resolution_values),
        "maximum_range_median": median_or_na(max_range_values),
        "power_ma_median": median_or_na(power_values),
        "metadata_parse_error_count": parse_errors,
        "qc_readiness_level": qc_level,
    }


def build_readme(patient_count: int, rows_with_metadata: int) -> str:
    return f"""# Accelerometer Framework: Sensor Linear Accelerometer QC

This folder starts the accelerometer workstream.

Order of work:

1. Use `sensor_linear_accelerometer` as the metadata/QC layer.
2. Use the QC results to decide whether and how to analyze `linear_accelerometer`.
3. Only later define model-facing movement biomarkers from raw x/y/z linear acceleration.

What this script did:

- Used mapped T1 patients only.
- Excluded Subject_ID_D `001`.
- For each mapped device, searched for the first `sensor_linear_accelerometer` timestamp at or after T1.
- Built a bounded 7-day window from that first available timestamp.
- Queried only that bounded device/time window.
- Did not query full patient windows.
- Did not extract raw movement features from `linear_accelerometer`.

Why `sensor_linear_accelerometer` comes first:

- It describes the Android sensor metadata for linear acceleration.
- It helps document sensor vendor, type, resolution, maximum range, power, and minimum delay.
- It supports sampling/readiness planning before high-frequency motion analysis.

Important interpretation:

- These are metadata and data-readiness summaries.
- They are not patient behavior features.
- Missing metadata is missing metadata, not no movement.
- `linear_accelerometer` phone motion is not the same as body movement.

Current run:

- Patients checked: `{patient_count}`
- Patients with any post-T1 `sensor_linear_accelerometer` metadata: `{rows_with_metadata}`

Generated files:

- `sensor_linear_accelerometer_qc_by_patient.csv`
- `sensor_linear_accelerometer_qc_by_device_window.csv`
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    patients = load_t1_patients()
    patients = patients[~patients["Subject_ID_D"].isin(EXCLUDED_COHORT_SUBJECT_IDS)].copy()
    device_map = load_device_map_strict()
    device_rows: list[dict[str, Any]] = []
    patient_rows: list[dict[str, Any]] = []

    conn = connect_sensordata_db()
    try:
        for patient_index, (_, patient) in enumerate(patients.iterrows(), start=1):
            subject_id = str(patient["Subject_ID_D"])
            device_ids = device_map.get(subject_id, [])
            t1_date = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize(TZ)
            t1_start_ms = local_to_ms(t1_date)
            print(f"patient {patient_index}/{len(patients)} Subject_ID_D={subject_id} devices={len(device_ids)}", flush=True)

            candidates: list[dict[str, Any]] = []
            for device_id in device_ids:
                base = {
                    "table_name": TABLE_NAME,
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": device_id,
                }
                first_ts = first_available_ts_after_t1(conn, f"`{TABLE_NAME}`", device_id, t1_start_ms)
                if first_ts is None:
                    row = {
                        **base,
                        "has_metadata_after_T1": False,
                        "window_rule": "adjusted_first_available_7d_after_T1_lookup",
                        "n_rows": 0,
                        "qc_readiness_level": "no_metadata_after_T1",
                    }
                    device_rows.append(row)
                    continue

                start_ms = int(first_ts)
                end_ms = int((pd.to_datetime(start_ms, unit="ms", utc=True) + pd.Timedelta(days=WINDOW_DAYS)).timestamp() * 1000)
                coverage = count_rows(conn, f"`{TABLE_NAME}`", device_id, start_ms, end_ms)
                n_rows = int(coverage.get("n_rows") or 0)
                rows = fetch_rows(conn, device_id, start_ms, end_ms, MAX_FETCH_ROWS_PER_DEVICE_WINDOW) if n_rows else []
                summary = summarize_rows(rows, n_rows)
                days_after_t1 = (
                    pd.to_datetime(start_ms, unit="ms", utc=True).tz_convert(TZ).normalize() - t1_date.normalize()
                ).days
                row = {
                    **base,
                    "has_metadata_after_T1": True,
                    "window_rule": "adjusted_first_available_7d_after_T1",
                    "days_first_available_after_T1": days_after_t1,
                    "window_start_ms": start_ms,
                    "window_end_ms": end_ms,
                    "window_start_local": ms_to_local(start_ms),
                    "window_end_local": ms_to_local(end_ms),
                    "n_rows": n_rows,
                    "first_ts": coverage.get("first_ts"),
                    "last_ts": coverage.get("last_ts"),
                    "first_local": ms_to_local(coverage.get("first_ts")),
                    "last_local": ms_to_local(coverage.get("last_ts")),
                    **summary,
                }
                device_rows.append(row)
                candidates.append(row)

            selected = sorted(candidates, key=lambda item: (item.get("window_start_ms") or 10**30, -int(item.get("n_rows") or 0)))
            selected_row = selected[0] if selected else {}
            patient_rows.append(
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "n_mapped_devices": len(device_ids),
                    "has_sensor_linear_accelerometer_metadata_after_T1": bool(selected_row),
                    "selected_device_id": selected_row.get("device_id", ""),
                    "days_first_available_after_T1": selected_row.get("days_first_available_after_T1", pd.NA),
                    "window_start_local": selected_row.get("window_start_local", ""),
                    "window_end_local": selected_row.get("window_end_local", ""),
                    "n_rows": selected_row.get("n_rows", 0),
                    "active_day_count_fetched": selected_row.get("active_day_count_fetched", 0),
                    "active_hour_count_fetched": selected_row.get("active_hour_count_fetched", 0),
                    "observed_span_hours_fetched": selected_row.get("observed_span_hours_fetched", pd.NA),
                    "median_interval_sec_fetched": selected_row.get("median_interval_sec_fetched", pd.NA),
                    "p95_interval_sec_fetched": selected_row.get("p95_interval_sec_fetched", pd.NA),
                    "max_gap_sec_fetched": selected_row.get("max_gap_sec_fetched", pd.NA),
                    "sensor_name_counts": selected_row.get("sensor_name_counts", ""),
                    "sensor_vendor_counts": selected_row.get("sensor_vendor_counts", ""),
                    "minimum_delay_us_median": selected_row.get("minimum_delay_us_median", pd.NA),
                    "implied_max_sampling_hz_from_minimum_delay": selected_row.get(
                        "implied_max_sampling_hz_from_minimum_delay", pd.NA
                    ),
                    "resolution_median": selected_row.get("resolution_median", pd.NA),
                    "maximum_range_median": selected_row.get("maximum_range_median", pd.NA),
                    "power_ma_median": selected_row.get("power_ma_median", pd.NA),
                    "qc_readiness_level": selected_row.get("qc_readiness_level", "no_metadata_after_T1"),
                    "interpretation": "sensor metadata/QC only; not a behavioral movement feature",
                }
            )
    finally:
        conn.close()

    patient_df = pd.DataFrame(patient_rows)
    device_df = pd.DataFrame(device_rows)
    patient_df.to_csv(PATIENT_QC_PATH, index=False)
    device_df.to_csv(DEVICE_QC_PATH, index=False)
    README_PATH.write_text(
        build_readme(
            patient_count=len(patient_df),
            rows_with_metadata=int(patient_df["has_sensor_linear_accelerometer_metadata_after_T1"].sum())
            if not patient_df.empty
            else 0,
        ),
        encoding="utf-8",
    )

    print(f"patients_checked: {len(patient_df)}")
    print(
        "patients_with_sensor_linear_accelerometer_metadata_after_T1: "
        f"{int(patient_df['has_sensor_linear_accelerometer_metadata_after_T1'].sum()) if not patient_df.empty else 0}"
    )
    print("qc_readiness_distribution:")
    print(patient_df["qc_readiness_level"].value_counts(dropna=False).to_string() if not patient_df.empty else "none")
    print("generated_files:")
    for path in [PATIENT_QC_PATH, DEVICE_QC_PATH, README_PATH]:
        print(path)


if __name__ == "__main__":
    main()
