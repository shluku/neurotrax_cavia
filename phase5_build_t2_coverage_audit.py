"""Clean Phase 5 T2 outputs and build coverage-based exploratory feature sets."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from phase5_extract_selected_features_all_t2_patients import (
    ALL_SUPPORTED_TABLES,
    COGNITIVE_COLUMNS,
    load_t2_patients,
    normalize_subject_id_d,
)


ROOT = Path(__file__).parent
OUT_DIR = ROOT / "output/analysis_candidates/phase5_t2_feature_extraction"
SELECTED_PATH = ROOT / "phase2_selected_features.csv"
METADATA_PATH = OUT_DIR.parent / "phase4_t1_baseline/phase4_t1_baseline_feature_metadata.csv"
LONG_PATH = OUT_DIR / "phase5_t2_selected_features_long.csv"
WIDE_PATH = OUT_DIR / "phase5_t2_selected_features_wide.csv"
STATUS_PATH = OUT_DIR / "phase5_t2_selected_features_patient_table_status.csv"
COVERAGE_PATH = OUT_DIR / "phase5_t2_selected_features_coverage.csv"
CHECKPOINT_PATH = OUT_DIR / "phase5_t2_selected_features_checkpoint.jsonl"

FEATURE_SUMMARY_PATH = OUT_DIR / "phase5_t2_feature_coverage_summary.csv"
TABLE_SUMMARY_PATH = OUT_DIR / "phase5_t2_table_coverage_summary.csv"
PATIENT_MATRIX_PATH = OUT_DIR / "phase5_t2_patient_feature_coverage_matrix.csv"
WORKING_FEATURES_PATH = OUT_DIR / "phase5_t2_working_features_10pct.csv"
SENSITIVITY_FEATURES_PATH = OUT_DIR / "phase5_t2_sensitivity_features_below_10pct.csv"
AUDIT_README_PATH = OUT_DIR / "README_phase5_t2_coverage_audit.md"


def clean_subject_id(value: object) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return normalize_subject_id_d(text)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    frame = pd.read_csv(path, dtype=str)
    if "Subject_ID_D" in frame.columns:
        frame["Subject_ID_D"] = frame["Subject_ID_D"].map(clean_subject_id)
    return frame


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    patients = load_t2_patients()
    selected = pd.read_csv(SELECTED_PATH, dtype=str)
    selected = selected[selected["source_table"].isin(ALL_SUPPORTED_TABLES)].copy()
    selected = selected.drop_duplicates("feature_name")
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    metadata = metadata.drop_duplicates("feature_name")

    status = read_csv(STATUS_PATH)
    status = status[status["table_name"].isin(ALL_SUPPORTED_TABLES)].copy()
    status = status.drop_duplicates(["Subject_ID_D", "table_name"], keep="last")
    status.to_csv(STATUS_PATH, index=False)

    long = read_csv(LONG_PATH)
    long = long[long["table_name"].isin(ALL_SUPPORTED_TABLES)].copy()
    long = long.drop_duplicates(["Subject_ID_D", "table_name", "feature_name"], keep="last")
    long = long[long["feature_name"].isin(selected["feature_name"])].copy()
    long.to_csv(LONG_PATH, index=False)

    coverage = read_csv(COVERAGE_PATH)
    coverage = coverage[coverage["table_name"].isin(ALL_SUPPORTED_TABLES)].copy()
    coverage_keys = [column for column in ["Subject_ID_D", "table_name", "device_id"] if column in coverage.columns]
    if coverage_keys:
        coverage = coverage.drop_duplicates(coverage_keys, keep="last")
    coverage.to_csv(COVERAGE_PATH, index=False)

    base_cols = [column for column in COGNITIVE_COLUMNS if column in patients.columns]
    base = patients[base_cols].drop_duplicates("Subject_ID_D")
    if long.empty:
        wide = base.copy()
    else:
        values = long.copy()
        values["feature_value"] = pd.to_numeric(values["feature_value"], errors="coerce")
        pivot = values.pivot_table(index="Subject_ID_D", columns="feature_name", values="feature_value", aggfunc="first").reset_index()
        pivot.columns.name = None
        wide = base.merge(pivot, on="Subject_ID_D", how="left")
    for feature_name in selected["feature_name"]:
        if feature_name not in wide.columns:
            wide[feature_name] = pd.NA
    wide.to_csv(WIDE_PATH, index=False)

    # Rebuild checkpoint states after removing light and duplicate rows.
    table_names = set(ALL_SUPPORTED_TABLES)
    checkpoint_records = []
    for index, subject_id in enumerate(patients["Subject_ID_D"], start=1):
        subject_status = status[status["Subject_ID_D"].eq(subject_id)]
        statuses = set(subject_status.get("table_status", pd.Series(dtype=str)).astype(str))
        state = "completed" if len(subject_status) == len(table_names) and not statuses.intersection({"error", "retryable_error"}) else "needs_retry"
        checkpoint_records.append({"Subject_ID_D": subject_id, "patient_index": index, "status": state})
    CHECKPOINT_PATH.write_text("\n".join(json.dumps(record) for record in checkpoint_records) + "\n", encoding="utf-8")

    feature_rows = []
    for _, feature in selected.iterrows():
        name = str(feature["feature_name"])
        observed = wide[name].notna().sum() if name in wide.columns else 0
        coverage_pct = 100 * observed / len(wide) if len(wide) else 0.0
        recommendation = metadata.loc[metadata["feature_name"].eq(name), "primary_model_recommendation"]
        recommendation = str(recommendation.iloc[0]) if not recommendation.empty else ""
        if coverage_pct < 10:
            role = "sensitivity_only_below_10pct"
        elif recommendation == "include_primary":
            role = "primary_eligible_10pct"
        else:
            role = "support_eligible_10pct"
        feature_rows.append(
            {
                "source_table": feature["source_table"],
                "feature_name": name,
                "primary_model_recommendation_t1": recommendation,
                "observed_patients_t2": int(observed),
                "t2_coverage_percent": round(coverage_pct, 2),
                "t2_missingness_percent": round(100 - coverage_pct, 2),
                "t2_analysis_role": role,
            }
        )
    feature_summary = pd.DataFrame(feature_rows).sort_values(["t2_analysis_role", "t2_coverage_percent", "feature_name"])
    feature_summary.to_csv(FEATURE_SUMMARY_PATH, index=False)
    feature_summary[feature_summary["t2_coverage_percent"].ge(10)].to_csv(WORKING_FEATURES_PATH, index=False)
    feature_summary[feature_summary["t2_coverage_percent"].lt(10)].to_csv(SENSITIVITY_FEATURES_PATH, index=False)

    table_summary = (
        status.groupby("table_name", dropna=False)["table_status"]
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )
    for column in ["calculated", "missing_no_pre_t2_window", "retryable_error", "error"]:
        if column not in table_summary.columns:
            table_summary[column] = 0
    table_summary["patient_count"] = len(patients)
    table_summary["calculated_percent"] = (100 * table_summary["calculated"] / len(patients)).round(2)
    table_summary["no_window_percent"] = (100 * table_summary["missing_no_pre_t2_window"] / len(patients)).round(2)
    table_summary.to_csv(TABLE_SUMMARY_PATH, index=False)

    matrix = pd.DataFrame({"Subject_ID_D": wide["Subject_ID_D"]})
    for name in selected["feature_name"]:
        matrix[name] = wide[name].notna().astype(int)
    matrix.to_csv(PATIENT_MATRIX_PATH, index=False)
    AUDIT_README_PATH.write_text(
        "# Phase 5 T2 Coverage Audit\n\n"
        f"T2 patients: `{len(wide)}`. Active tables: `{len(ALL_SUPPORTED_TABLES)}`. Active selected features: `{len(selected)}`.\n\n"
        "The light table is excluded from this active audit because repeated database disconnects made its current output unreliable. "
        "Features with at least 10% patient coverage are placed in the working exploratory set; features below 10% are retained as sensitivity-only. "
        "This threshold is a POC screening rule, not a clinical validity threshold.\n",
        encoding="utf-8",
    )
    print(f"t2_patients: {len(wide)}")
    print(f"active_tables: {len(ALL_SUPPORTED_TABLES)}")
    print(f"active_features: {len(selected)}")
    print(f"working_features_10pct: {int(feature_summary['t2_coverage_percent'].ge(10).sum())}")
    print(f"sensitivity_features_below_10pct: {int(feature_summary['t2_coverage_percent'].lt(10).sum())}")
    print(f"mean_t2_missingness_percent: {feature_summary['t2_missingness_percent'].mean():.2f}")


if __name__ == "__main__":
    main()
