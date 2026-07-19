from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt

from main import connect_sensordata_db
from phase2_sample_barometer_first_available_week_for_feature_review import (
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
FEATURES_PATH = OUT_DIR / "phase2_adjusted_first_available_7d_selected_features_barometer.csv"
COVERAGE_PATH = OUT_DIR / "phase2_adjusted_first_available_7d_coverage_scan_barometer.csv"
SIGNAL_QC_PATH = OUT_DIR / "phase2_adjusted_first_available_7d_barometer_signal_qc.csv"
TRANSITIONS_PATH = OUT_DIR / "phase2_adjusted_first_available_7d_barometer_detected_transitions.csv"
TIMESERIES_PATH = OUT_DIR / "phase2_adjusted_first_available_7d_barometer_signal_timeseries.csv"
README_PATH = OUT_DIR / "README_phase2_adjusted_first_available_7d_barometer_signal_features.md"
SELECTED_FEATURES_PATH = ROOT / "phase2_selected_features.csv"

WINDOW_DAYS = 7
MIN_ROWS = 20
EXCLUDED_EXPLORATORY_SUBJECTS = {"001"}

PRESSURE_MIN_HPA = 300.0
PRESSURE_MAX_HPA = 1100.0
RESAMPLE_RULE = "1s"
SHORT_GAP_INTERPOLATE_LIMIT_SECONDS = 5
ROLLING_MEDIAN_SECONDS = 10
BUTTERWORTH_ORDER = 2
BUTTERWORTH_CUTOFF_HZ = 0.05
BUTTERWORTH_FS_HZ = 1.0
MIN_BUTTERWORTH_SEGMENT_SECONDS = 30
ELEVATION_METERS_PER_HPA = 8.3
LARGE_VERTICAL_SHIFT_THRESHOLD_M = 3.0
MIN_TRANSITION_DURATION_SECONDS = 10
TRANSITION_REFRACTORY_SECONDS = 30


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
            FROM `barometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        rows: list[dict[str, Any]] = []
        while True:
            batch = cur.fetchmany(10000)
            if not batch:
                break
            rows.extend(batch)
        return rows
    finally:
        cur.close()


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
            first_ts = first_available_ts_after_t1(conn, "`barometer`", device_id, t1_start_ms)
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
            row = count_rows(conn, "`barometer`", device_id, start_ms, end_ms)
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


def parse_pressure_rows(rows: list[dict[str, Any]]) -> tuple[pd.DataFrame, int]:
    parsed_rows: list[dict[str, Any]] = []
    parse_errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        pressure = numeric(obj.get("double_values_0"))
        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if pressure is None or pd.isna(timestamp):
            continue
        parsed_rows.append(
            {
                "_id": row.get("_id"),
                "timestamp": int(timestamp),
                "local_datetime": ms_to_local(timestamp),
                "pressure_hpa": pressure,
            }
        )
    return pd.DataFrame(parsed_rows), parse_errors


def butterworth_or_rolling(series: pd.Series) -> tuple[pd.Series, str]:
    rolling = series.rolling(ROLLING_MEDIAN_SECONDS, min_periods=1, center=True).median()
    smoothed = pd.Series(np.nan, index=rolling.index, dtype="float64")
    method_parts: list[str] = []
    sos = butter(BUTTERWORTH_ORDER, BUTTERWORTH_CUTOFF_HZ, btype="lowpass", fs=BUTTERWORTH_FS_HZ, output="sos")

    valid_group = rolling.notna().ne(rolling.notna().shift()).cumsum()
    for _, segment in rolling.groupby(valid_group):
        segment = segment.dropna()
        if segment.empty:
            continue
        if len(segment) >= MIN_BUTTERWORTH_SEGMENT_SECONDS:
            try:
                smoothed.loc[segment.index] = sosfiltfilt(sos, segment.to_numpy(dtype="float64"))
                method_parts.append("butterworth")
            except Exception:
                smoothed.loc[segment.index] = segment
                method_parts.append("rolling_median_fallback")
        else:
            smoothed.loc[segment.index] = segment
            method_parts.append("rolling_median_short_segment")
    method = "+".join(sorted(set(method_parts))) if method_parts else "no_valid_signal"
    return smoothed, method


def detect_transitions(signal: pd.Series) -> list[dict[str, Any]]:
    valid = signal.dropna()
    if valid.empty:
        return []
    transitions: list[dict[str, Any]] = []
    anchor_time = valid.index[0]
    anchor_elevation = float(valid.iloc[0])
    last_transition_time: pd.Timestamp | None = None

    for current_time, current_value in valid.iloc[1:].items():
        current_elevation = float(current_value)
        delta = current_elevation - anchor_elevation
        elapsed = (current_time - anchor_time).total_seconds()
        if elapsed < MIN_TRANSITION_DURATION_SECONDS:
            continue
        if abs(delta) < LARGE_VERTICAL_SHIFT_THRESHOLD_M:
            continue
        if last_transition_time is not None:
            since_last = (current_time - last_transition_time).total_seconds()
            if since_last < TRANSITION_REFRACTORY_SECONDS:
                continue
        transitions.append(
            {
                "transition_index": len(transitions) + 1,
                "start_local": anchor_time.tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z"),
                "end_local": current_time.tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z"),
                "duration_seconds": elapsed,
                "elevation_delta_m": delta,
                "direction": "upward" if delta > 0 else "downward",
            }
        )
        anchor_time = current_time
        anchor_elevation = current_elevation
        last_transition_time = current_time
    return transitions


def compute_barometer_signal_features(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    parsed, parse_errors = parse_pressure_rows(rows)
    qc: dict[str, Any] = {
        "raw_rows": len(rows),
        "parsed_pressure_rows": len(parsed),
        "json_parse_errors": parse_errors,
        "pressure_min_threshold_hpa": PRESSURE_MIN_HPA,
        "pressure_max_threshold_hpa": PRESSURE_MAX_HPA,
        "resample_rule": RESAMPLE_RULE,
        "short_gap_interpolate_limit_seconds": SHORT_GAP_INTERPOLATE_LIMIT_SECONDS,
        "rolling_median_seconds": ROLLING_MEDIAN_SECONDS,
        "butterworth_order": BUTTERWORTH_ORDER,
        "butterworth_cutoff_hz": BUTTERWORTH_CUTOFF_HZ,
        "large_vertical_shift_threshold_m": LARGE_VERTICAL_SHIFT_THRESHOLD_M,
        "min_transition_duration_seconds": MIN_TRANSITION_DURATION_SECONDS,
        "transition_refractory_seconds": TRANSITION_REFRACTORY_SECONDS,
        "elevation_meters_per_hpa": ELEVATION_METERS_PER_HPA,
    }
    if parsed.empty:
        features = {
            "barometer_pressure_range": pd.NA,
            "barometer_pressure_sd": pd.NA,
            "barometer_large_vertical_shift_count": pd.NA,
            "barometer_estimated_elevation_change_m": pd.NA,
            "barometer_upward_transition_count": pd.NA,
            "barometer_downward_transition_count": pd.NA,
            "feature_status": "insufficient_data_no_valid_pressure",
        }
        return features, pd.DataFrame(), pd.DataFrame(), qc

    clean = parsed[
        parsed["pressure_hpa"].between(PRESSURE_MIN_HPA, PRESSURE_MAX_HPA, inclusive="both")
    ].copy()
    qc["clean_pressure_rows"] = len(clean)
    qc["removed_pressure_outlier_rows"] = len(parsed) - len(clean)
    if clean.empty:
        features = {
            "barometer_pressure_range": pd.NA,
            "barometer_pressure_sd": pd.NA,
            "barometer_large_vertical_shift_count": pd.NA,
            "barometer_estimated_elevation_change_m": pd.NA,
            "barometer_upward_transition_count": pd.NA,
            "barometer_downward_transition_count": pd.NA,
            "feature_status": "insufficient_data_all_pressure_out_of_range",
        }
        return features, pd.DataFrame(), pd.DataFrame(), qc

    dt = pd.to_datetime(clean["timestamp"], unit="ms", utc=True)
    clean = clean.assign(datetime_utc=dt).sort_values("datetime_utc")
    pressure_series = clean.set_index("datetime_utc")["pressure_hpa"].astype("float64")
    pressure_series = pressure_series.groupby(level=0).mean()
    resampled = pressure_series.resample(RESAMPLE_RULE).median()
    interpolated = resampled.interpolate(
        method="time",
        limit=SHORT_GAP_INTERPOLATE_LIMIT_SECONDS,
        limit_area="inside",
    )
    smoothed_pressure, smoothing_method = butterworth_or_rolling(interpolated)

    baseline_pressure = smoothed_pressure.dropna().iloc[0] if smoothed_pressure.notna().any() else np.nan
    elevation_relative_m = -ELEVATION_METERS_PER_HPA * (smoothed_pressure - baseline_pressure)
    transitions = detect_transitions(elevation_relative_m)
    transitions_df = pd.DataFrame(transitions)

    timeseries = pd.DataFrame(
        {
            "datetime_utc": resampled.index,
            "local_datetime": [idx.tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z") for idx in resampled.index],
            "pressure_hpa_resampled": resampled.to_numpy(),
            "pressure_hpa_interpolated": interpolated.to_numpy(),
            "pressure_hpa_smoothed": smoothed_pressure.to_numpy(),
            "elevation_relative_m": elevation_relative_m.to_numpy(),
        }
    )
    pressure_range = float(clean["pressure_hpa"].max() - clean["pressure_hpa"].min())
    pressure_sd = float(clean["pressure_hpa"].std(ddof=1)) if len(clean) > 1 else 0.0
    upward_count = int((transitions_df.get("direction", pd.Series(dtype=str)) == "upward").sum()) if not transitions_df.empty else 0
    downward_count = int((transitions_df.get("direction", pd.Series(dtype=str)) == "downward").sum()) if not transitions_df.empty else 0
    estimated_elevation_change_m = (
        float(transitions_df["elevation_delta_m"].abs().sum()) if not transitions_df.empty else 0.0
    )
    features = {
        "barometer_pressure_range": pressure_range,
        "barometer_pressure_sd": pressure_sd,
        "barometer_large_vertical_shift_count": int(len(transitions_df)),
        "barometer_estimated_elevation_change_m": estimated_elevation_change_m,
        "barometer_upward_transition_count": upward_count,
        "barometer_downward_transition_count": downward_count,
        "feature_status": "calculated",
    }
    qc.update(
        {
            "signal_start_local": clean["datetime_utc"].min().tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z"),
            "signal_end_local": clean["datetime_utc"].max().tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z"),
            "observed_duration_seconds": (
                clean["datetime_utc"].max() - clean["datetime_utc"].min()
            ).total_seconds(),
            "resampled_points": len(resampled),
            "smoothed_valid_points": int(smoothed_pressure.notna().sum()),
            "smoothing_method": smoothing_method,
        }
    )
    return features, timeseries, transitions_df, qc


def write_readme(window: dict[str, Any] | None, qc: dict[str, Any]) -> None:
    window_text = "No adjusted first-available barometer window was found."
    if window:
        window_text = f"""Selected window:

- Subject_ID_D: `{window['Subject_ID_D']}`
- Subject_ID_N: `{window['Subject_ID_N']}`
- global_T1: `{window['global_T1']}`
- T1_date_iso: `{window['T1_date_iso']}`
- device_id: `{window['device_id']}`
- window_rule: `{window['window_rule']}`
- window_start_local: `{window['start_local']}`
- window_end_local: `{window['end_local']}`
- rows in window: `{window['n_rows_in_window']}`
- days_first_available_after_T1: `{window['days_first_available_after_T1']}`
"""
    README_PATH.write_text(
        f"""# Barometer Adjusted First-Available 7-Day Signal Features

This adjusted Phase 2B extraction calculates selected `barometer` signal features for the first ranked patient/device with at least `{MIN_ROWS}` rows in the first available 7-day window after T1.

{window_text}

Signal processing thresholds and constants:

- pressure source: `data.double_values_0`
- pressure accepted range: `{PRESSURE_MIN_HPA}` to `{PRESSURE_MAX_HPA}` hPa
- resampling grid: `{RESAMPLE_RULE}`
- short-gap interpolation limit: `{SHORT_GAP_INTERPOLATE_LIMIT_SECONDS}` seconds
- first smoothing step: centered rolling median, `{ROLLING_MEDIAN_SECONDS}` seconds
- second smoothing step: Butterworth low-pass when segment length permits
- Butterworth order: `{BUTTERWORTH_ORDER}`
- Butterworth cutoff: `{BUTTERWORTH_CUTOFF_HZ}` Hz
- Butterworth sampling frequency: `{BUTTERWORTH_FS_HZ}` Hz
- minimum Butterworth segment length: `{MIN_BUTTERWORTH_SEGMENT_SECONDS}` seconds
- pressure-to-elevation approximation: `-8.3 * pressure_delta_hPa`
- large vertical shift threshold: `{LARGE_VERTICAL_SHIFT_THRESHOLD_M}` meters
- minimum transition duration: `{MIN_TRANSITION_DURATION_SECONDS}` seconds
- transition refractory/collapse window: `{TRANSITION_REFRACTORY_SECONDS}` seconds

Selected features:

- `barometer_pressure_range`
- `barometer_pressure_sd`
- `barometer_large_vertical_shift_count`
- `barometer_estimated_elevation_change_m`
- `barometer_upward_transition_count`
- `barometer_downward_transition_count`

Interpretation limits:

- This is a delayed adjusted first-available window, not a T1 baseline week.
- Barometer pressure can reflect altitude, weather, device hardware, and sampling conditions.
- These are exploratory vertical-context support features, not posture features and not diagnostic markers.
- Missing data remains missing and must not be converted to zero.

QC summary:

{pd.Series(qc).to_string()}
""",
        encoding="utf-8",
    )


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
        features, timeseries, transitions, qc = compute_barometer_signal_features(rows)
        qc.update(
            {
                "Subject_ID_D": window["Subject_ID_D"],
                "Subject_ID_N": window["Subject_ID_N"],
                "device_id": window["device_id"],
                "global_T1": window["global_T1"],
                "T1_date_iso": window["T1_date_iso"],
                "window_start_local": window["start_local"],
                "window_end_local": window["end_local"],
                "days_first_available_after_T1": window["days_first_available_after_T1"],
            }
        )
        out_rows = []
        for feature_name in selected_features:
            value = features.get(feature_name, pd.NA)
            status = "calculated" if pd.notna(value) else features.get("feature_status", "insufficient_data_feature_missing")
            out_rows.append(
                {
                    "table_name": TABLE_NAME,
                    "feature_name": feature_name,
                    "feature_value": value,
                    "calculation_context": "adjusted_first_available_7d_barometer_signal_analysis",
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
        timeseries.to_csv(TIMESERIES_PATH, index=False)
        transitions.to_csv(TRANSITIONS_PATH, index=False)
        pd.DataFrame([qc]).to_csv(SIGNAL_QC_PATH, index=False)
    else:
        qc = {"feature_status": "no_adjusted_first_available_window"}
        out_rows = [
            {
                "table_name": TABLE_NAME,
                "feature_name": feature_name,
                "feature_value": pd.NA,
                "calculation_context": "adjusted_first_available_7d_barometer_signal_analysis",
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
        pd.DataFrame().to_csv(TIMESERIES_PATH, index=False)
        pd.DataFrame().to_csv(TRANSITIONS_PATH, index=False)
        pd.DataFrame([qc]).to_csv(SIGNAL_QC_PATH, index=False)

    pd.DataFrame(out_rows).to_csv(FEATURES_PATH, index=False)
    pd.DataFrame(coverage_rows).to_csv(COVERAGE_PATH, index=False)
    write_readme(window, qc)

    print(f"adjusted_barometer_feature_rows: {len(out_rows)}")
    print(FEATURES_PATH)
    print(pd.DataFrame(out_rows).to_string(index=False))
    print("generated files:")
    for path in [FEATURES_PATH, COVERAGE_PATH, SIGNAL_QC_PATH, TRANSITIONS_PATH, TIMESERIES_PATH, README_PATH]:
        print(f"- {path}")


if __name__ == "__main__":
    main()
