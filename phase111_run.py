"""Build and run the first Phase 111 full-interval Ridge phenotype models."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
FULL_WIDE = ROOT / "output/analysis_candidates/phase111_full_t1_t2_interval/phase111_full_t1_t2_interval_features_wide.csv"
FULL_STATUS = ROOT / "output/analysis_candidates/phase111_full_t1_t2_interval/phase111_full_t1_t2_interval_patient_table_status.csv"
SELECTED_PATH = ROOT / "phase2_selected_features.csv"
OLD_METADATA = ROOT / "output/analysis_candidates/phase4_t1_baseline/phase4_t1_baseline_feature_metadata.csv"
DATA_DIR = ROOT / "output/analysis_candidates/phase111_t1_t2_all_interval"
DATASET_PATH = DATA_DIR / "phase111_t1_t2_all_interval_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase111_t1_t2_all_interval_feature_metadata.csv"
MISSINGNESS_PATH = DATA_DIR / "phase111_t1_t2_all_interval_missingness_summary.csv"
TABLE_COVERAGE_PATH = DATA_DIR / "phase111_t1_t2_all_interval_table_coverage.csv"
README_PATH = DATA_DIR / "README_phase111_t1_t2_all_interval.md"

DEFERRED_TABLES = {"barometer", "light", "bluetooth", "sensor_linear_accelerometer"}
TARGETS = {
    "Global": ("global_T1", "global_T2", "phase111_target_global"),
    "Memory": ("memory_T1", "memory_T2", "phase111_target_memory"),
    "Executive function": ("ef_T1", "ef_T2", "phase111_target_executive_function"),
    "Processing speed": ("processing_speed_T1", "processing_speed_T2", "phase111_target_processing_speed"),
    "Attention": ("attention_T1", "attention_T2", "phase111_target_attention"),
    "Motor": ("motor_T1", "motor_T2", "phase111_target_motor"),
}


def build_dataset() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(FULL_WIDE, dtype=str)
    selected = pd.read_csv(SELECTED_PATH, dtype=str)
    selected = selected[~selected["source_table"].isin(DEFERRED_TABLES)].copy()
    feature_names = selected["feature_name"].dropna().unique().tolist()
    for feature in feature_names:
        if feature not in dataset.columns:
            dataset[feature] = pd.NA

    for _, (t1_column, t2_column, target_column) in TARGETS.items():
        t1 = pd.to_numeric(dataset.get(t1_column, pd.Series(index=dataset.index)), errors="coerce")
        t2 = pd.to_numeric(dataset.get(t2_column, pd.Series(index=dataset.index)), errors="coerce")
        dataset[target_column] = pd.concat([t1, t2], axis=1).mean(axis=1, skipna=True)
        source = pd.Series("missing", index=dataset.index, dtype="string")
        source.loc[t1.notna() & t2.notna()] = "mean_of_T1_and_T2"
        source.loc[t1.notna() & t2.isna()] = "T1_only_no_valid_T2"
        source.loc[t1.isna() & t2.notna()] = "T2_only_unexpected"
        dataset[f"{target_column}_source"] = source

    dataset["baseline_feature_missing_count"] = dataset[feature_names].apply(pd.to_numeric, errors="coerce").isna().sum(axis=1)
    dataset["baseline_feature_missing_fraction"] = dataset["baseline_feature_missing_count"] / len(feature_names)
    status = pd.read_csv(FULL_STATUS, dtype=str)
    table_coverage = (
        status.assign(calculated=status["table_status"].eq("calculated"))
        .groupby("Subject_ID_D", dropna=False)["calculated"]
        .mean()
        .rename("baseline_table_coverage_fraction")
    )
    dataset = dataset.merge(table_coverage, left_on="Subject_ID_D", right_index=True, how="left")
    dataset["baseline_table_coverage_fraction"] = dataset["baseline_table_coverage_fraction"].fillna(0)
    dataset.to_csv(DATASET_PATH, index=False)

    metadata = pd.read_csv(OLD_METADATA, dtype=str)
    metadata = metadata[
        metadata["feature_name"].isin(feature_names)
        & ~metadata["source_table"].isin(DEFERRED_TABLES)
    ].copy()
    coverage = dataset[feature_names].apply(pd.to_numeric, errors="coerce").notna().mean().mul(100)
    metadata["missing_percent"] = metadata["feature_name"].map(lambda feature: round(100 - coverage.get(feature, 0), 2))
    metadata["acquisition_window_class"] = "t1_to_t2_all_available_or_t1_plus_123d_fallback"
    metadata["source_column"] = metadata["feature_name"]
    metadata.to_csv(METADATA_PATH, index=False)
    pd.DataFrame(
        {
            "feature_name": feature_names,
            "n_patients": [int(dataset[feature].notna().sum()) for feature in feature_names],
            "missing_percent": [round(100 - coverage[feature], 2) for feature in feature_names],
        }
    ).to_csv(MISSINGNESS_PATH, index=False)

    table_summary = status.groupby("table_name", dropna=False)["table_status"].value_counts().unstack(fill_value=0).reset_index()
    table_summary["patient_count"] = dataset["Subject_ID_D"].nunique()
    table_summary["calculated_percent"] = (100 * table_summary.get("calculated", 0) / table_summary["patient_count"]).round(2)
    table_summary.to_csv(TABLE_COVERAGE_PATH, index=False)
    README_PATH.write_text(
        "# Phase 111 Full T1-to-T2 Interval Baseline Ridge\n\n"
        "Phase 111 uses all active-feature data in `[T1, T2)` when T2 exists. Patients without valid T2 use `[T1, T1+123 days)`. "
        "The target is the mean of observed T1 and T2 scores, or T1 alone when T2 is unavailable. "
        "The standard median of two observations is identical to this mean.\n\n"
        "This first run uses only cross-validated Ridge versus the fold-local mean baseline. "
        "Light, barometer, Bluetooth-proximity, and sensor-linear-accelerometer features remain deferred.\n",
        encoding="utf-8",
    )


def main() -> None:
    build_dataset()
    from phase111_model_ridge import main as run_ridge

    run_ridge()
    print(f"Phase 111 outputs: {DATA_DIR}")


if __name__ == "__main__":
    main()
