from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db
from phase2_extract_exploratory_t1_week_24h_selected_features import (
    COGNITIVE_CANDIDATES_PATH,
    LABEL_DEVICE_MAP_PATH,
    ROOT,
    SAFE_TABLES,
    SELECTED_FEATURES_PATH,
    compute_features,
    fetch_light_lux_values,
    fetch_rows,
    normalize_subject_id_d,
    selected_window_for_patient,
)


OUT_DIR = ROOT / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features"
LONG_PATH = OUT_DIR / "phase2_all_t1_selected_features_long.csv"
WIDE_PATH = OUT_DIR / "phase2_all_t1_selected_features_wide.csv"
COVERAGE_PATH = OUT_DIR / "phase2_all_t1_selected_features_coverage.csv"
STATUS_PATH = OUT_DIR / "phase2_all_t1_selected_features_patient_table_status.csv"
README_PATH = OUT_DIR / "README_phase2_all_t1_selected_features.md"
EXCLUDED_COHORT_SUBJECT_IDS = {"001"}

COGNITIVE_COLUMNS = [
    "Subject_ID_N",
    "Subject_ID_D",
    "age",
    "Gender (1=M, 2=F)",
    "Education (years)",
    "T1_date_iso",
    "T2_date_iso",
    "global_T1",
    "global_T2",
    "global_delta",
    "memory_T1",
    "memory_T2",
    "memory_delta",
    "ef_T1",
    "ef_T2",
    "ef_delta",
    "attention_T1",
    "attention_T2",
    "attention_delta",
    "processing_speed_T1",
    "processing_speed_T2",
    "processing_speed_delta",
    "verbal_T1",
    "verbal_T2",
    "verbal_delta",
    "motor_T1",
    "motor_T2",
    "motor_delta",
    "iq_T1",
    "iq_T2",
    "iq_delta",
]


def load_t1_patients() -> pd.DataFrame:
    df = pd.read_csv(COGNITIVE_CANDIDATES_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id_d)
    df["Subject_ID_D"] = df["Subject_ID_D"].replace({"nan": pd.NA, "NaN": pd.NA, "None": pd.NA, "": pd.NA})
    df["global_T1_num"] = pd.to_numeric(df["global_T1"], errors="coerce")
    df = df.dropna(subset=["Subject_ID_D", "T1_date_iso"]).copy()
    return df.sort_values(["Subject_ID_D"], ascending=True)


def load_device_map_strict() -> dict[str, list[str]]:
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    out: dict[str, list[str]] = {}
    exact_label_seen: set[str] = set()
    for _, row in label_map.iterrows():
        raw_label = "" if pd.isna(row.get("label")) else str(row.get("label")).strip()
        subject_id = normalize_subject_id_d(raw_label)
        if not subject_id or subject_id.lower() in {"nan", "none"}:
            continue
        is_exact_three_digit_label = raw_label.isdigit() and len(raw_label) == 3
        if subject_id in exact_label_seen and not is_exact_three_digit_label:
            continue
        raw = "" if pd.isna(row.get("device_ids")) else str(row.get("device_ids"))
        device_ids = []
        for value in raw.split(";"):
            device_id = value.strip()
            if device_id and device_id.lower() not in {"nan", "none"}:
                device_ids.append(device_id)
        out[subject_id] = sorted(set(device_ids))
        if is_exact_three_digit_label:
            exact_label_seen.add(subject_id)
    return out


def selected_tables(selected: pd.DataFrame, only_table: str | None) -> list[str]:
    tables = [table for table in selected["source_table"].dropna().unique().tolist() if table in SAFE_TABLES]
    if only_table:
        return [only_table]
    return tables


def fetch_table_rows(conn, table_name: str, device_ids: list[str], start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    device_ids_with_rows = set()
    for device_id in device_ids:
        if table_name == "light":
            device_rows = fetch_light_lux_values(conn, device_id, start_ms, end_ms)
        else:
            device_rows = fetch_rows(conn, table_name, device_id, start_ms, end_ms)
        if device_rows:
            device_ids_with_rows.add(device_id)
        rows.extend(device_rows)
    rows = sorted(rows, key=lambda row: (int(row["timestamp"]), str(row.get("device_id", ""))))
    return rows, sorted(device_ids_with_rows)


def feature_status(value: Any, table_status: str, computed_status: str) -> str:
    if table_status != "calculated":
        return table_status
    if pd.isna(value):
        return computed_status if computed_status else "insufficient_data_feature_missing"
    return "calculated"


def is_retryable_db_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "lost connection" in message
        or "mysql connection not available" in message
        or "server has gone away" in message
    )


def build_readme(tables: list[str], patient_count: int) -> str:
    return f"""# Phase 2 All-T1 Selected Feature Extraction

This folder contains the first bounded cohort-level extraction of the currently selected Phase 2 SensorDB features.

## Scope

- Patients: all NeuroTrax candidates with a T1 date in `output/analysis_candidates/cognitive_candidates_all.csv`.
- Tables: {", ".join(tables)}.
- Selected features: the manually selected features in `phase2_selected_features.csv`.
- Window rule: exploratory T1-week 24-hour protocol.

## Window Rule

For each patient, table, and mapped device:

1. Try the local 24-hour window starting on the day after T1.
2. If no rows exist there, search for the first timestamp that can support a complete 24-hour span inside the first week after T1.
3. If no complete span exists in that week, mark the table/features as missing for that patient.

Missing data remains missing. It is not converted to zero activity.

## Outputs

- `phase2_all_t1_selected_features_long.csv`: one row per patient-table-feature.
- `phase2_all_t1_selected_features_wide.csv`: one row per patient with selected features as columns.
- `phase2_all_t1_selected_features_coverage.csv`: bounded coverage checks used to choose windows.
- `phase2_all_t1_selected_features_patient_table_status.csv`: one row per patient-table with window and row-count status.

## Interpretation

These are exploratory digital biomarker candidates, not diagnostic features and not confirmatory findings. Raw privacy-sensitive content is not saved; keyboard/message/location calculations output aggregate values only.

## Run Summary Placeholder

This README was generated for {patient_count} T1 patients. See the CSV outputs for actual coverage and feature availability.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply selected Phase 2 T1-week 24h features to all T1 patients.")
    parser.add_argument("--table", choices=sorted(SAFE_TABLES), help="Run only one selected table.")
    parser.add_argument("--subject-id", help="Run only one Subject_ID_D.")
    parser.add_argument("--max-patients", type=int, default=0, help="Optional cap for pilot runs; 0 means all.")
    parser.add_argument("--hours", type=int, default=24, help="Window length in hours. Protocol default is 24.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.table:
        run_out_dir = OUT_DIR / "table_runs" / args.table
        run_out_dir.mkdir(parents=True, exist_ok=True)
        long_path = run_out_dir / f"phase2_all_t1_selected_features_long_{args.table}.csv"
        wide_path = run_out_dir / f"phase2_all_t1_selected_features_wide_{args.table}.csv"
        coverage_path = run_out_dir / f"phase2_all_t1_selected_features_coverage_{args.table}.csv"
        status_path = run_out_dir / f"phase2_all_t1_selected_features_patient_table_status_{args.table}.csv"
        readme_path = run_out_dir / f"README_phase2_all_t1_selected_features_{args.table}.md"
    else:
        long_path = LONG_PATH
        wide_path = WIDE_PATH
        coverage_path = COVERAGE_PATH
        status_path = STATUS_PATH
        readme_path = README_PATH

    selected = pd.read_csv(SELECTED_FEATURES_PATH, dtype=str)
    selected = selected[selected["source_table"].isin(SAFE_TABLES)].copy()
    tables = selected_tables(selected, args.table)
    patients = load_t1_patients()
    if args.subject_id:
        subject_id = normalize_subject_id_d(args.subject_id)
        patients = patients[patients["Subject_ID_D"] == subject_id].copy()
    else:
        patients = patients[~patients["Subject_ID_D"].isin(EXCLUDED_COHORT_SUBJECT_IDS)].copy()
    if args.max_patients > 0:
        patients = patients.head(args.max_patients).copy()

    device_map = load_device_map_strict()
    long_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []

    conn = connect_sensordata_db()
    try:
        for patient_index, (_, patient) in enumerate(patients.iterrows(), start=1):
            subject_id = patient["Subject_ID_D"]
            device_ids = device_map.get(subject_id, [])
            print(f"patient {patient_index}/{len(patients)} Subject_ID_D={subject_id} devices={len(device_ids)}", flush=True)

            for table_name in tables:
                print(f"  table={table_name}", flush=True)
                selected_for_table = selected[selected["source_table"].astype(str) == table_name]
                table_status = "not_started"
                window = {}
                rows: list[dict[str, Any]] = []
                device_ids_used: list[str] = []
                features: dict[str, Any] = {}
                error_message = ""

                if not device_ids:
                    table_status = "missing_no_mapped_device"
                else:
                    for attempt in range(3):
                        try:
                            window = selected_window_for_patient(conn, table_name, patient, device_ids, hours=args.hours)
                            if "start_ms" not in window:
                                table_status = "missing_no_protocol_valid_24h_window_in_T1_week"
                            else:
                                rows, device_ids_used = fetch_table_rows(
                                    conn,
                                    table_name,
                                    device_ids,
                                    int(window["start_ms"]),
                                    int(window["end_ms"]),
                                )
                                if rows:
                                    features = compute_features(table_name, rows)
                                    table_status = "calculated"
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
                        "table_name": table_name,
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
                            "table_name": table_name,
                            "feature_name": feature_name,
                            "feature_family": feature.get("feature_family", ""),
                            "feature_value": value_numeric if not pd.isna(value_numeric) else pd.NA,
                            "feature_status": feature_status(value, table_status, computed_feature_status),
                            "window_rule": window.get("window_rule", ""),
                            "window_start_local": window.get("start_local", ""),
                            "window_end_local": window.get("end_local", ""),
                            "rows_in_window": len(rows),
                            "device_ids_used": ";".join(device_ids_used),
                            "calculation_context": "all_t1_patients_selected_features_T1_week_first_valid_24h",
                            "error_message": error_message,
                        }
                    )
    finally:
        conn.close()

    long_df = pd.DataFrame(long_rows)
    status_df = pd.DataFrame(status_rows)
    coverage_df = pd.DataFrame(coverage_rows)

    long_df.to_csv(long_path, index=False)
    status_df.to_csv(status_path, index=False)
    coverage_df.to_csv(coverage_path, index=False)

    base_cols = [col for col in COGNITIVE_COLUMNS if col in patients.columns]
    base = patients[base_cols].drop_duplicates(subset=["Subject_ID_D"]).copy()
    if long_df.empty:
        wide = base
    else:
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
    wide.to_csv(wide_path, index=False)

    readme_path.write_text(build_readme(tables, len(patients)), encoding="utf-8")

    calculated = long_df[long_df["feature_status"] == "calculated"] if not long_df.empty else long_df
    print("generated files:")
    print(f"- {long_path}")
    print(f"- {wide_path}")
    print(f"- {coverage_path}")
    print(f"- {status_path}")
    print(f"- {readme_path}")
    print(f"patients_processed: {len(patients)}")
    print(f"tables_processed: {len(tables)}")
    print(f"feature_rows: {len(long_df)}")
    print(f"calculated_feature_rows: {len(calculated)}")
    print(f"wide_shape: {wide.shape[0]} rows x {wide.shape[1]} columns")
    if not status_df.empty:
        print("table_status_counts:")
        print(status_df["table_status"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
