from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db
from phase2_extract_barometer_adjusted_first_available_7d_selected_features import (
    SELECTED_FEATURES_PATH,
    TABLE_NAME,
    WINDOW_DAYS,
    compute_barometer_signal_features,
    fetch_rows,
)
from phase2_extract_selected_features_all_t1_patients import (
    COGNITIVE_COLUMNS,
    EXCLUDED_COHORT_SUBJECT_IDS,
    OUT_DIR,
    feature_status,
    is_retryable_db_error,
    load_device_map_strict,
    load_t1_patients,
)
from phase2_sample_barometer_first_available_week_for_feature_review import (
    count_rows,
    first_available_ts_after_t1,
)
from phase2_sample_table_exploratory_t1_week_for_feature_review import TZ, ms_to_local


RUN_OUT_DIR = OUT_DIR / "table_runs" / TABLE_NAME
LONG_PATH = RUN_OUT_DIR / f"phase2_all_t1_selected_features_long_{TABLE_NAME}.csv"
WIDE_PATH = RUN_OUT_DIR / f"phase2_all_t1_selected_features_wide_{TABLE_NAME}.csv"
COVERAGE_PATH = RUN_OUT_DIR / f"phase2_all_t1_selected_features_coverage_{TABLE_NAME}.csv"
STATUS_PATH = RUN_OUT_DIR / f"phase2_all_t1_selected_features_patient_table_status_{TABLE_NAME}.csv"
QC_PATH = RUN_OUT_DIR / f"phase2_all_t1_selected_features_signal_qc_{TABLE_NAME}.csv"
TRANSITIONS_PATH = RUN_OUT_DIR / f"phase2_all_t1_selected_features_detected_transitions_{TABLE_NAME}.csv"
README_PATH = RUN_OUT_DIR / f"README_phase2_all_t1_selected_features_{TABLE_NAME}.md"
MIN_ROWS = 20


def local_to_ms(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def selected_adjusted_window_for_patient(conn, patient: pd.Series, device_ids: list[str]) -> dict[str, Any]:
    t1_date = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize(TZ)
    t1_start_ms = local_to_ms(t1_date)
    coverage_rows: list[dict[str, Any]] = []
    candidates = []

    for device_id in device_ids:
        first_ts = first_available_ts_after_t1(conn, "`barometer`", device_id, t1_start_ms)
        if first_ts is None:
            coverage_rows.append(
                {
                    "table_name": TABLE_NAME,
                    "Subject_ID_D": patient["Subject_ID_D"],
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
                "Subject_ID_D": patient["Subject_ID_D"],
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
    if not valid:
        return {"coverage_rows": coverage_rows}

    first_ts, n_rows, device_id, days_after_t1, start_ms, end_ms = sorted(valid, key=lambda item: item[0])[0]
    return {
        "window_rule": "adjusted_first_available_7d_after_T1",
        "start_ms": start_ms,
        "end_ms": end_ms,
        "start_local": ms_to_local(start_ms),
        "end_local": ms_to_local(end_ms),
        "device_id": device_id,
        "days_first_available_after_T1": days_after_t1,
        "n_rows": n_rows,
        "coverage_rows": coverage_rows,
    }


def build_readme(patient_count: int) -> str:
    return f"""# Phase 3 Barometer Adjusted First-Available 7-Day Signal Extraction

This table-run applies selected `barometer` signal features to all T1 patients except Subject_ID_D `001`.

This is not the standard T1-week Phase 3 acquisition rule.

Adjusted rule:

1. For each patient and mapped device, find the first `barometer` timestamp at or after T1.
2. Require at least {MIN_ROWS} rows in the first 7 days from that timestamp.
3. Fetch only that bounded 7-day window.
4. Calculate selected pressure and vertical-context signal features using the documented Phase 2B thresholds.

Selected signal features:

- `barometer_pressure_range`
- `barometer_pressure_sd`
- `barometer_large_vertical_shift_count`
- `barometer_estimated_elevation_change_m`
- `barometer_upward_transition_count`
- `barometer_downward_transition_count`

Interpretation:

- This is delayed adjusted first-available data, not T1 baseline data.
- Barometer pressure can reflect altitude, weather, phone hardware, and sampling conditions.
- These are exploratory vertical-context support features, not posture markers and not diagnostic markers.
- Missing data remains missing and is not converted to zero activity.

Patients processed: {patient_count}
"""


def main() -> None:
    RUN_OUT_DIR.mkdir(parents=True, exist_ok=True)
    selected = pd.read_csv(SELECTED_FEATURES_PATH, dtype=str)
    selected_for_table = selected[selected["source_table"].eq(TABLE_NAME)].copy()
    patients = load_t1_patients()
    patients = patients[~patients["Subject_ID_D"].isin(EXCLUDED_COHORT_SUBJECT_IDS)].copy()
    device_map = load_device_map_strict()

    long_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    qc_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []

    conn = connect_sensordata_db()
    try:
        for patient_index, (_, patient) in enumerate(patients.iterrows(), start=1):
            subject_id = patient["Subject_ID_D"]
            device_ids = device_map.get(subject_id, [])
            print(f"patient {patient_index}/{len(patients)} Subject_ID_D={subject_id} devices={len(device_ids)}", flush=True)

            table_status = "not_started"
            window: dict[str, Any] = {}
            rows: list[dict[str, Any]] = []
            device_ids_used: list[str] = []
            features: dict[str, Any] = {}
            error_message = ""
            qc: dict[str, Any] = {}

            if not device_ids:
                table_status = "missing_no_mapped_device"
            else:
                for attempt in range(3):
                    try:
                        window = selected_adjusted_window_for_patient(conn, patient, device_ids)
                        if "start_ms" not in window:
                            table_status = "missing_no_adjusted_first_available_barometer_20row_window_after_T1"
                        else:
                            rows = fetch_rows(conn, window["device_id"], int(window["start_ms"]), int(window["end_ms"]))
                            if rows:
                                device_ids_used = [window["device_id"]]
                                features, _timeseries, transitions, qc = compute_barometer_signal_features(rows)
                                table_status = "calculated" if features.get("feature_status") == "calculated" else str(features.get("feature_status"))
                                qc.update(
                                    {
                                        "Subject_ID_D": subject_id,
                                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                                        "global_T1": patient.get("global_T1", ""),
                                        "T1_date_iso": patient.get("T1_date_iso", ""),
                                        "device_id": window["device_id"],
                                        "window_start_local": window["start_local"],
                                        "window_end_local": window["end_local"],
                                        "days_first_available_after_T1": window["days_first_available_after_T1"],
                                    }
                                )
                                qc_rows.append(qc)
                                if not transitions.empty:
                                    transitions = transitions.copy()
                                    transitions.insert(0, "Subject_ID_D", subject_id)
                                    transitions.insert(1, "Subject_ID_N", patient.get("Subject_ID_N", ""))
                                    transitions.insert(2, "device_id", window["device_id"])
                                    transition_rows.extend(transitions.to_dict("records"))
                            else:
                                table_status = "missing_window_selected_but_no_rows_fetched"
                        coverage_rows.extend(window.get("coverage_rows", []))
                        error_message = ""
                        break
                    except Exception as exc:
                        error_message = str(exc)
                        if attempt < 2 and is_retryable_db_error(exc):
                            print(
                                f"    retrying_after_db_connection_error attempt={attempt + 1} error={error_message}",
                                flush=True,
                            )
                            try:
                                conn.close()
                            except Exception:
                                pass
                            conn = connect_sensordata_db()
                            continue
                        table_status = "error"
                        break

            computed_feature_status = str(features.get("feature_status", table_status))
            status_rows.append(
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "table_name": TABLE_NAME,
                    "table_status": table_status,
                    "feature_status": computed_feature_status,
                    "device_ids_available": ";".join(device_ids),
                    "device_ids_used": ";".join(device_ids_used),
                    "window_rule": window.get("window_rule", ""),
                    "window_start_ms": window.get("start_ms", pd.NA),
                    "window_end_ms": window.get("end_ms", pd.NA),
                    "window_start_local": window.get("start_local", ""),
                    "window_end_local": window.get("end_local", ""),
                    "rows_in_window": len(rows),
                    "error_message": error_message,
                }
            )

            for _, feature in selected_for_table.iterrows():
                feature_name = str(feature["feature_name"])
                value = features.get(feature_name, pd.NA)
                value_numeric = pd.to_numeric(value, errors="coerce")
                long_rows.append(
                    {
                        "Subject_ID_D": subject_id,
                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                        "global_T1": patient.get("global_T1", ""),
                        "global_T2": patient.get("global_T2", ""),
                        "global_delta": patient.get("global_delta", ""),
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                        "T2_date_iso": patient.get("T2_date_iso", ""),
                        "table_name": TABLE_NAME,
                        "feature_name": feature_name,
                        "feature_family": feature.get("feature_family", ""),
                        "feature_value": value_numeric if not pd.isna(value_numeric) else pd.NA,
                        "feature_status": feature_status(value, table_status, computed_feature_status),
                        "window_rule": window.get("window_rule", ""),
                        "window_start_local": window.get("start_local", ""),
                        "window_end_local": window.get("end_local", ""),
                        "rows_in_window": len(rows),
                        "device_ids_used": ";".join(device_ids_used),
                        "calculation_context": "all_t1_patients_barometer_adjusted_first_available_7d_signal_analysis_after_T1",
                        "error_message": error_message,
                    }
                )
    finally:
        conn.close()

    long_df = pd.DataFrame(long_rows)
    status_df = pd.DataFrame(status_rows)
    coverage_df = pd.DataFrame(coverage_rows)
    qc_df = pd.DataFrame(qc_rows)
    transitions_df = pd.DataFrame(transition_rows)

    long_df.to_csv(LONG_PATH, index=False)
    status_df.to_csv(STATUS_PATH, index=False)
    coverage_df.to_csv(COVERAGE_PATH, index=False)
    qc_df.to_csv(QC_PATH, index=False)
    transitions_df.to_csv(TRANSITIONS_PATH, index=False)

    base_cols = [col for col in COGNITIVE_COLUMNS if col in patients.columns]
    base = patients[base_cols].drop_duplicates(subset=["Subject_ID_D"]).copy()
    values = long_df.copy()
    values["feature_value"] = pd.to_numeric(values["feature_value"], errors="coerce")
    pivot = values.pivot_table(
        index="Subject_ID_D",
        columns="feature_name",
        values="feature_value",
        aggfunc="first",
        dropna=False,
    ).reset_index()
    pivot.columns.name = None
    wide = base.merge(pivot, on="Subject_ID_D", how="left")
    wide.to_csv(WIDE_PATH, index=False)

    README_PATH.write_text(build_readme(len(patients)), encoding="utf-8")

    calculated = long_df[long_df["feature_status"] == "calculated"] if not long_df.empty else long_df
    print("generated files:")
    print(f"- {LONG_PATH}")
    print(f"- {WIDE_PATH}")
    print(f"- {COVERAGE_PATH}")
    print(f"- {STATUS_PATH}")
    print(f"- {QC_PATH}")
    print(f"- {TRANSITIONS_PATH}")
    print(f"- {README_PATH}")
    print(f"patients_processed: {len(patients)}")
    print("tables_processed: 1")
    print(f"feature_rows: {len(long_df)}")
    print(f"calculated_feature_rows: {len(calculated)}")
    print(f"wide_shape: {wide.shape[0]} rows x {wide.shape[1]} columns")
    if not status_df.empty:
        print("table_status_counts:")
        print(status_df["table_status"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
