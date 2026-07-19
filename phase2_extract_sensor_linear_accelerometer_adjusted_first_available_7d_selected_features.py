from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db
from phase2_sample_sensor_linear_accelerometer_first_available_week_for_feature_review import (
    TABLE_NAME,
    count_rows,
    first_available_ts_after_t1,
)
from phase2_sample_table_exploratory_t1_week_for_feature_review import (
    TZ,
    load_device_map,
    load_ranked_patients,
    ms_to_local,
    parse_json,
)


ROOT = Path(__file__).parent
OUT_DIR = ROOT / "output/analysis_candidates/phase2_feature_extraction/adjusted_first_available_7d"
FEATURES_PATH = OUT_DIR / "phase2_adjusted_first_available_7d_selected_features_sensor_linear_accelerometer.csv"
COVERAGE_PATH = OUT_DIR / "phase2_adjusted_first_available_7d_coverage_scan_sensor_linear_accelerometer.csv"
SELECTED_FEATURES_PATH = ROOT / "phase2_selected_features.csv"
WINDOW_DAYS = 7
MIN_ROWS = 20
EXCLUDED_EXPLORATORY_SUBJECTS = {"001"}


def local_to_ms(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def numeric(value: Any) -> float | None:
    out = pd.to_numeric(value, errors="coerce")
    if pd.isna(out):
        return None
    return float(out)


def fetch_rows(conn, device_id: str, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
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
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        return cur.fetchall()
    finally:
        cur.close()


def median_or_na(values: list[float]) -> float | pd._libs.missing.NAType:
    if not values:
        return pd.NA
    return float(pd.Series(values, dtype="float64").median())


def compute_sensor_linear_accelerometer(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active_hours: set[str] = set()
    resolution_values: list[float] = []
    max_range_values: list[float] = []
    power_values: list[float] = []
    minimum_delay_values: list[float] = []
    parse_errors = 0

    for row in rows:
        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if pd.notna(timestamp):
            local_hour = pd.to_datetime(int(timestamp), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H")
            active_hours.add(local_hour)
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        resolution = numeric(obj.get("double_sensor_resolution"))
        max_range = numeric(obj.get("double_sensor_maximum_range"))
        power = numeric(obj.get("double_sensor_power_ma"))
        minimum_delay = numeric(obj.get("double_sensor_minimum_delay"))
        if resolution is not None:
            resolution_values.append(resolution)
        if max_range is not None:
            max_range_values.append(max_range)
        if power is not None:
            power_values.append(power)
        if minimum_delay is not None:
            minimum_delay_values.append(minimum_delay)

    return {
        "sensor_linear_accelerometer_event_count": len(rows) if rows else pd.NA,
        "sensor_linear_accelerometer_active_hour_count": len(active_hours) if rows else pd.NA,
        "sensor_linear_accelerometer_minimum_delay_us": median_or_na(minimum_delay_values),
        "sensor_linear_accelerometer_resolution": median_or_na(resolution_values),
        "sensor_linear_accelerometer_maximum_range": median_or_na(max_range_values),
        "sensor_linear_accelerometer_power_ma": median_or_na(power_values),
        "sensor_linear_accelerometer_valid_metadata_rows": len(resolution_values),
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if rows else "insufficient_data_no_rows",
    }


def selected_window(conn) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    ranked = load_ranked_patients()
    ranked = ranked[~ranked["Subject_ID_D"].isin(EXCLUDED_EXPLORATORY_SUBJECTS)].copy()
    device_map = load_device_map()
    coverage_rows: list[dict[str, Any]] = []

    for _, patient in ranked.iterrows():
        subject_id = str(patient["Subject_ID_D"])
        device_ids = device_map.get(subject_id, [])
        if not device_ids:
            continue
        t1_date = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize(TZ)
        t1_start_ms = local_to_ms(t1_date)
        print(f"patient={subject_id} global_T1={patient.get('global_T1', '')} devices={len(device_ids)}", flush=True)
        candidates = []
        for device_id in device_ids:
            first_ts = first_available_ts_after_t1(conn, "`sensor_linear_accelerometer`", device_id, t1_start_ms)
            if first_ts is None:
                coverage_rows.append(
                    {
                        "table_name": TABLE_NAME,
                        "Subject_ID_D": subject_id,
                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                        "global_T1": patient.get("global_T1", ""),
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                        "device_id": device_id,
                        "window_rule": "adjusted_first_available_7d_after_T1_lookup",
                        "n_rows": 0,
                    }
                )
                continue
            start_ms = first_ts
            end_ms = int((pd.to_datetime(first_ts, unit="ms", utc=True) + pd.Timedelta(days=WINDOW_DAYS)).timestamp() * 1000)
            row = count_rows(conn, "`sensor_linear_accelerometer`", device_id, start_ms, end_ms)
            n_rows = int(row.get("n_rows") or 0)
            days_after_t1 = (
                pd.to_datetime(first_ts, unit="ms", utc=True).tz_convert(TZ).normalize() - t1_date.normalize()
            ).days
            coverage_rows.append(
                {
                    "table_name": TABLE_NAME,
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": device_id,
                    "window_rule": "adjusted_first_available_7d_after_T1",
                    "days_first_available_after_T1": days_after_t1,
                    "window_start_ms": start_ms,
                    "window_end_ms": end_ms,
                    "window_start_local": ms_to_local(start_ms),
                    "window_end_local": ms_to_local(end_ms),
                    "n_rows": n_rows,
                    "first_ts": row.get("first_ts"),
                    "last_ts": row.get("last_ts"),
                    "first_local": ms_to_local(row.get("first_ts")),
                    "last_local": ms_to_local(row.get("last_ts")),
                }
            )
            candidates.append((first_ts, n_rows, device_id, days_after_t1, start_ms, end_ms))
        valid = [candidate for candidate in candidates if candidate[1] >= MIN_ROWS]
        if valid:
            first_ts, n_rows, device_id, days_after_t1, start_ms, end_ms = sorted(valid, key=lambda item: item[0])[0]
            return (
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": device_id,
                    "window_rule": "adjusted_first_available_7d_after_T1",
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "start_local": ms_to_local(start_ms),
                    "end_local": ms_to_local(end_ms),
                    "n_rows_in_window": n_rows,
                    "days_first_available_after_T1": days_after_t1,
                },
                coverage_rows,
            )
    return None, coverage_rows


def main() -> None:
    selected = pd.read_csv(SELECTED_FEATURES_PATH, dtype=str)
    selected_features = selected[selected["source_table"].eq(TABLE_NAME)]["feature_name"].tolist()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = connect_sensordata_db()
    try:
        window, coverage_rows = selected_window(conn)
        rows = fetch_rows(conn, window["device_id"], window["start_ms"], window["end_ms"]) if window else []
    finally:
        conn.close()

    if window:
        features = compute_sensor_linear_accelerometer(rows)
        out_rows = []
        for feature_name in selected_features:
            value = features.get(feature_name, pd.NA)
            status = "calculated" if pd.notna(value) else features.get("feature_status", "insufficient_data_feature_missing")
            out_rows.append(
                {
                    "table_name": TABLE_NAME,
                    "feature_name": feature_name,
                    "feature_value": value,
                    "calculation_context": "adjusted_first_available_7d_sensor_linear_accelerometer_only",
                    "Subject_ID_D": window["Subject_ID_D"],
                    "Subject_ID_N": window["Subject_ID_N"],
                    "device_id_used": window["device_id"],
                    "global_T1": window["global_T1"],
                    "T1_date_iso": window["T1_date_iso"],
                    "window_rule": window["window_rule"],
                    "window_start_local": window["start_local"],
                    "window_end_local": window["end_local"],
                    "days_first_available_after_T1": window["days_first_available_after_T1"],
                    "feature_status": status,
                    "source_file": str(FEATURES_PATH.relative_to(ROOT)),
                }
            )
    else:
        out_rows = [
            {
                "table_name": TABLE_NAME,
                "feature_name": feature_name,
                "feature_value": pd.NA,
                "calculation_context": "adjusted_first_available_7d_sensor_linear_accelerometer_only",
                "Subject_ID_D": "",
                "Subject_ID_N": "",
                "device_id_used": "",
                "global_T1": "",
                "T1_date_iso": "",
                "window_rule": "no_adjusted_first_available_window",
                "window_start_local": "",
                "window_end_local": "",
                "days_first_available_after_T1": "",
                "feature_status": "no_adjusted_first_available_window",
                "source_file": str(FEATURES_PATH.relative_to(ROOT)),
            }
            for feature_name in selected_features
        ]

    pd.DataFrame(out_rows).to_csv(FEATURES_PATH, index=False)
    pd.DataFrame(coverage_rows).to_csv(COVERAGE_PATH, index=False)

    print(f"adjusted_feature_rows: {len(out_rows)}")
    print(FEATURES_PATH)
    print(pd.DataFrame(out_rows).to_string(index=False))
    print("generated files:")
    print(f"- {FEATURES_PATH}")
    print(f"- {COVERAGE_PATH}")


if __name__ == "__main__":
    main()
