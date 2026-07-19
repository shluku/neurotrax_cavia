from __future__ import annotations

import pandas as pd

from main import connect_sensordata_db
from phase2_extract_exploratory_t1_week_24h_selected_features import (
    ROOT,
    SAFE_TABLES,
    SELECTED_FEATURES_PATH,
    TZ,
    compute_bluetooth,
    fetch_rows,
    local_to_ms,
)
from phase2_extract_selected_features_all_t1_patients import load_device_map_strict, load_t1_patients


TABLE_NAME = "bluetooth"
OUT_DIR = ROOT / "output/analysis_candidates/phase3_rd/bluetooth_t1_30day_any_data_pilot"
LONG_PATH = OUT_DIR / "phase3_rd_bluetooth_t1_30day_any_data_long.csv"
WIDE_PATH = OUT_DIR / "phase3_rd_bluetooth_t1_30day_any_data_wide.csv"
STATUS_PATH = OUT_DIR / "phase3_rd_bluetooth_t1_30day_any_data_status.csv"
README_PATH = OUT_DIR / "README_phase3_rd_bluetooth_t1_30day_any_data.md"


def t1_30day_window(patient: pd.Series) -> dict:
    t1_date = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize(TZ)
    window_start = t1_date
    window_end = window_start + pd.Timedelta(days=30)
    return {
        "window_rule": "rd_t1_30day_any_bluetooth_data",
        "window_start_ms": local_to_ms(window_start),
        "window_end_ms": local_to_ms(window_end),
        "window_start_local": window_start.strftime("%Y-%m-%d %H:%M:%S%z"),
        "window_end_local": window_end.strftime("%Y-%m-%d %H:%M:%S%z"),
    }


def selected_bluetooth_features() -> pd.DataFrame:
    selected = pd.read_csv(SELECTED_FEATURES_PATH, dtype=str)
    return selected[selected["source_table"].astype(str) == TABLE_NAME].copy()


def build_readme() -> str:
    return """# Phase 3 R&D: Bluetooth T1 30-Day Any-Data Pilot

This is a research-and-development pilot, separate from the strict Phase 3 implementation output.

## Question

Does `bluetooth` coverage improve if we use the first 30 days after T1 and calculate selected Bluetooth features whenever any Bluetooth rows exist?

## Rule Tested

- Table: `bluetooth`
- Window: T1 local midnight through 30 days after T1
- Requirement: at least one row in that 30-day window
- No full T1-to-T2 query
- Always filtered by `device_id` and timestamp
- Missing remains missing; no rows are not converted to zero Bluetooth activity

## Features

- `unique_bluetooth_addresses`
- `bluetooth_address_diversity_ratio`

## Interpretation

This is not yet the final clinical protocol. It is an R&D comparison to evaluate whether sparse/context tables need a longer acquisition window.
"""


def main() -> None:
    if TABLE_NAME not in SAFE_TABLES:
        raise ValueError(f"Unsafe table name: {TABLE_NAME}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    patients = load_t1_patients()
    device_map = load_device_map_strict()
    selected = selected_bluetooth_features()

    long_rows = []
    status_rows = []
    conn = connect_sensordata_db()
    try:
        for index, (_, patient) in enumerate(patients.iterrows(), start=1):
            subject_id = str(patient["Subject_ID_D"])
            device_ids = device_map.get(subject_id, [])
            window = t1_30day_window(patient)
            print(f"patient {index}/{len(patients)} Subject_ID_D={subject_id} devices={len(device_ids)}", flush=True)

            rows = []
            device_ids_used = set()
            error_message = ""
            table_status = "not_started"
            features = {}

            if not device_ids:
                table_status = "missing_no_mapped_device"
            else:
                try:
                    for device_id in device_ids:
                        device_rows = fetch_rows(
                            conn,
                            TABLE_NAME,
                            device_id,
                            int(window["window_start_ms"]),
                            int(window["window_end_ms"]),
                        )
                        if device_rows:
                            device_ids_used.add(device_id)
                        rows.extend(device_rows)
                    rows = sorted(rows, key=lambda row: (int(row["timestamp"]), str(row.get("device_id", ""))))
                    if rows:
                        features = compute_bluetooth(rows)
                        table_status = "calculated"
                    else:
                        table_status = "missing_no_bluetooth_rows_in_t1_30day"
                except Exception as exc:
                    table_status = "error"
                    error_message = str(exc)

            feature_status = str(features.get("feature_status", table_status))
            status_rows.append(
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "table_name": TABLE_NAME,
                    "table_status": table_status,
                    "feature_status": feature_status,
                    "device_ids_available": ";".join(device_ids),
                    "device_ids_used": ";".join(sorted(device_ids_used)),
                    **window,
                    "rows_in_window": len(rows),
                    "error_message": error_message,
                }
            )

            for _, feature in selected.iterrows():
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
                        "feature_status": "calculated" if table_status == "calculated" and not pd.isna(value_numeric) else table_status,
                        "window_rule": window["window_rule"],
                        "window_start_local": window["window_start_local"],
                        "window_end_local": window["window_end_local"],
                        "rows_in_window": len(rows),
                        "device_ids_used": ";".join(sorted(device_ids_used)),
                        "calculation_context": "phase3_rd_bluetooth_t1_30day_any_data",
                        "error_message": error_message,
                    }
                )
    finally:
        conn.close()

    long_df = pd.DataFrame(long_rows)
    status_df = pd.DataFrame(status_rows)
    wide = patients[
        [
            "Subject_ID_N",
            "Subject_ID_D",
            "T1_date_iso",
            "T2_date_iso",
            "global_T1",
            "global_T2",
            "global_delta",
        ]
    ].copy()
    if not long_df.empty:
        pivot = long_df.pivot_table(
            index="Subject_ID_D",
            columns="feature_name",
            values="feature_value",
            aggfunc="first",
            dropna=False,
        ).reset_index()
        pivot.columns.name = None
        wide = wide.merge(pivot, on="Subject_ID_D", how="left")

    long_df.to_csv(LONG_PATH, index=False)
    status_df.to_csv(STATUS_PATH, index=False)
    wide.to_csv(WIDE_PATH, index=False)
    README_PATH.write_text(build_readme(), encoding="utf-8")

    calculated_patients = int(status_df["table_status"].eq("calculated").sum()) if not status_df.empty else 0
    calculated_feature_rows = int(long_df["feature_status"].eq("calculated").sum()) if not long_df.empty else 0
    print("generated files:")
    print(f"- {LONG_PATH}")
    print(f"- {WIDE_PATH}")
    print(f"- {STATUS_PATH}")
    print(f"- {README_PATH}")
    print(f"patients_processed: {len(patients)}")
    print(f"patients_with_bluetooth_in_t1_30day: {calculated_patients}")
    print(f"feature_rows: {len(long_df)}")
    print(f"calculated_feature_rows: {calculated_feature_rows}")
    print("table_status_counts:")
    print(status_df["table_status"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
