"""Run the independent Phase 6 decline workflow on Phase 4/7 10-day data."""

from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
T1_METADATA = ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/phase4_10day_t1_baseline_feature_metadata.csv"
T1_PATH = ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/phase4_10day_t1_baseline_patient_dataset.csv"
T2_PATH = ROOT / "output/analysis_candidates/phase7_10day_window/t2/phase7_t2_10day_features_wide.csv"
T1_CALIBRATION = ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/model_t1_ridge/phase4_t1_score_calibration_by_patient.csv"
T1_DOMAIN = ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/model_t1_cognitive_domain_groups/phase4_t1_cognitive_domain_group_patient_predictions.csv"
TAXONOMY = ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/model_t1_cognitive_domain_groups/phase4_cognitive_domain_feature_taxonomy.csv"
OUT_DIR = ROOT / "output/analysis_candidates/phase6_10day_t1_t2_decline"
SUMMARY_PATH = OUT_DIR / "phase6_10day_t2_feature_coverage_summary.csv"


def build_t2_summary() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t2 = pd.read_csv(T2_PATH, dtype=str)
    metadata = pd.read_csv(T1_METADATA, dtype=str)
    features = metadata["feature_name"].dropna().unique().tolist()
    coverage = t2.reindex(columns=features).apply(pd.to_numeric, errors="coerce").notna().mean().mul(100)
    rows = []
    for _, row in metadata.iterrows():
        feature = row["feature_name"]
        pct = float(coverage.get(feature, 0.0))
        if pct < 10:
            role = "sensitivity_only_below_10pct"
        elif row["primary_model_recommendation"] == "include_primary":
            role = "primary_eligible_10pct"
        else:
            role = "support_eligible_10pct"
        rows.append(
            {
                "feature_name": feature,
                "source_table": row["source_table"],
                "t2_coverage_percent": round(pct, 2),
                "t2_missingness_percent": round(100 - pct, 2),
                "t2_analysis_role": role,
            }
        )
    pd.DataFrame(rows).to_csv(SUMMARY_PATH, index=False)


def redirect(module: object) -> None:
    module.T1_PATH = T1_PATH
    module.T2_PATH = T2_PATH
    module.FEATURE_SUMMARY_PATH = SUMMARY_PATH
    module.T1_CALIBRATION_PATH = T1_CALIBRATION
    module.T1_DOMAIN_PATH = T1_DOMAIN
    module.TAXONOMY_PATH = TAXONOMY
    module.OUT_DIR = OUT_DIR
    for name, value in list(vars(module).items()):
        if name.endswith("_PATH") and isinstance(value, Path) and name not in {
            "T1_PATH", "T2_PATH", "FEATURE_SUMMARY_PATH", "T1_CALIBRATION_PATH", "T1_DOMAIN_PATH", "TAXONOMY_PATH"
        }:
            setattr(module, name, OUT_DIR / value.name.replace("phase6_t1_t2_decline", "phase6_10day_t1_t2_decline"))


def main() -> None:
    build_t2_summary()
    module = importlib.import_module("phase6_model_t1_t2_independent")
    redirect(module)
    module.main()
    print(f"Phase 6 10-day outputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
