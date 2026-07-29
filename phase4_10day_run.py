"""Build and run the Phase 4 baseline workflow on Phase 7 10-day T1 data."""

from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
PHASE7_T1_WIDE = ROOT / "output/analysis_candidates/phase7_10day_window/t1/phase7_t1_10day_features_wide.csv"
SELECTED_PATH = ROOT / "phase2_selected_features.csv"
OLD_METADATA = ROOT / "output/analysis_candidates/phase4_t1_baseline/phase4_t1_baseline_feature_metadata.csv"
PHASE7_STATUS = ROOT / "output/analysis_candidates/phase7_10day_window/t1/phase7_t1_10day_patient_table_status.csv"
DATA_DIR = ROOT / "output/analysis_candidates/phase4_10day_t1_baseline"
DATASET_PATH = DATA_DIR / "phase4_10day_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_10day_t1_baseline_feature_metadata.csv"
MISSINGNESS_PATH = DATA_DIR / "phase4_10day_t1_baseline_missingness_summary.csv"
TABLE_COVERAGE_PATH = DATA_DIR / "phase4_10day_t1_baseline_table_coverage.csv"
README_PATH = DATA_DIR / "README_phase4_10day_t1_baseline.md"


MODEL_MODULES = [
    ("phase4_model_t1_ridge", "model_t1_ridge"),
    ("phase4_t1_score_calibration", "model_t1_ridge"),
    ("phase4_model_t1_gradient_weighted", "model_t1_gradient_weighted"),
    ("phase4_model_t1_slope_selected", "model_t1_slope_selected"),
    ("phase4_model_t1_direction_constrained", "model_t1_direction_constrained"),
    ("phase4_model_t1_alternative_models", "model_t1_alternatives"),
    ("phase4_model_t1_cognitive_domains", "model_t1_cognitive_domains"),
    ("phase4_model_t1_cognitive_domain_groups", "model_t1_cognitive_domain_groups"),
    ("phase4_cluster_t1_baseline", "cluster_t1_baseline"),
    ("phase4_cluster_audit", "cluster_t1_baseline"),
    ("phase4_cluster_profiles", "cluster_t1_baseline"),
]


def build_dataset() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(PHASE7_T1_WIDE, dtype=str)
    selected = pd.read_csv(SELECTED_PATH, dtype=str)
    selected = selected[selected["source_table"].ne("light")]
    metadata = pd.read_csv(OLD_METADATA, dtype=str)
    feature_names = [feature for feature in selected["feature_name"].dropna().unique()]
    for feature in feature_names:
        if feature not in dataset.columns:
            dataset[feature] = pd.NA
    dataset["baseline_feature_missing_count"] = dataset[feature_names].apply(pd.to_numeric, errors="coerce").isna().sum(axis=1)
    dataset["baseline_feature_missing_fraction"] = dataset["baseline_feature_missing_count"] / len(feature_names)
    status = pd.read_csv(PHASE7_STATUS, dtype=str)
    table_coverage = (
        status.assign(calculated=status["table_status"].eq("calculated"))
        .groupby("Subject_ID_D", dropna=False)["calculated"]
        .mean()
        .rename("baseline_table_coverage_fraction")
    )
    dataset = dataset.merge(table_coverage, left_on="Subject_ID_D", right_index=True, how="left")
    dataset["baseline_table_coverage_fraction"] = dataset["baseline_table_coverage_fraction"].fillna(0)
    dataset.to_csv(DATASET_PATH, index=False)

    new_metadata = metadata[metadata["feature_name"].isin(feature_names) & metadata["source_table"].ne("light")].copy()
    coverage = dataset[feature_names].apply(pd.to_numeric, errors="coerce").notna().mean().mul(100)
    new_metadata["missing_percent"] = new_metadata["feature_name"].map(lambda feature: round(100 - coverage.get(feature, 0), 2))
    new_metadata["acquisition_window_class"] = "t1_10day_first_available"
    new_metadata["source_column"] = new_metadata["feature_name"]
    new_metadata.to_csv(METADATA_PATH, index=False)
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
        "# Phase 4 10-Day T1 Baseline Digital Phenotype\n\n"
        "This is the Phase 4 baseline workflow applied to the Phase 7 availability-anchored 10-day T1 feature table. "
        "The original Phase 4 24-hour outputs are unchanged. The same selected features, primary recommendations, model families, and exploratory interpretation boundaries are retained.\n",
        encoding="utf-8",
    )


def redirect_module(module: object, model_dir: Path) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    if hasattr(module, "DATA_DIR"):
        module.DATA_DIR = DATA_DIR
    if hasattr(module, "CLUSTER_DIR"):
        module.CLUSTER_DIR = model_dir
    if hasattr(module, "MODEL_DIR"):
        module.MODEL_DIR = DATA_DIR / "model_t1_ridge"
    if hasattr(module, "DATASET_PATH"):
        module.DATASET_PATH = DATASET_PATH
    if hasattr(module, "METADATA_PATH"):
        module.METADATA_PATH = METADATA_PATH
    for name, value in list(vars(module).items()):
        if name == "DEVICE_MAP_PATH":
            setattr(module, name, ROOT / "output/label_device_map.csv")
        elif name.endswith("_PATH") and isinstance(value, Path) and name not in {"DATASET_PATH", "METADATA_PATH"}:
            base_dir = module.MODEL_DIR if hasattr(module, "MODEL_DIR") and name.startswith(("PREDICTIONS", "COEFFICIENT", "CALIBRATION", "README")) else model_dir
            setattr(module, name, base_dir / value.name)
    if hasattr(module, "OUT_DIR"):
        module.OUT_DIR = model_dir


def run_models() -> None:
    for module_name, directory_name in MODEL_MODULES:
        module = importlib.import_module(module_name)
        redirect_module(module, DATA_DIR / directory_name)
        print(f"running {module_name}", flush=True)
        module.main()


def main() -> None:
    build_dataset()
    run_models()
    print(f"Phase 4 10-day outputs: {DATA_DIR}")


if __name__ == "__main__":
    main()
