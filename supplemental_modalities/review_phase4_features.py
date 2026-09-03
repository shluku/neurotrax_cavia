"""Build an auditable review table for Phase 4 proximity/light features."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import OUTPUT_ROOT


OUTPUT_DIR = OUTPUT_ROOT / "phase4_24h_t1"

FEATURE_GROUPS = {
    "proximity_raw_rows_in_window": "coverage_qc",
    "proximity_valid_numeric_rows": "coverage_qc",
    "proximity_json_parse_errors": "coverage_qc",
    "proximity_duplicate_adjacent_rows": "coverage_qc",
    "proximity_observed_span_hours": "coverage_qc",
    "proximity_active_hour_count": "coverage_qc",
    "proximity_median_value": "behavioral_distribution",
    "proximity_iqr_value": "behavioral_distribution",
    "proximity_near_sample_fraction": "behavioral_contact_state",
    "proximity_near_transition_count": "behavioral_contact_state",
    "proximity_near_bout_count": "behavioral_contact_state",
    "proximity_median_interval_ms": "temporal_sampling",
    "proximity_p95_interval_ms": "temporal_sampling",
    "proximity_device_count": "coverage_qc",
    "light_raw_rows_in_window": "coverage_qc",
    "light_valid_lux_rows": "coverage_qc",
    "light_observed_span_hours": "coverage_qc",
    "light_active_hour_count": "coverage_qc",
    "median_light_lux": "behavioral_light_exposure",
    "percent_dark_samples": "behavioral_light_exposure",
    "night_mean_light_lux": "behavioral_light_exposure",
    "light_lux_iqr": "behavioral_light_exposure",
    "light_median_interval_ms": "temporal_sampling",
    "light_p95_interval_ms": "temporal_sampling",
    "light_device_count": "coverage_qc",
}

RECOMMENDED_FEATURES = {
    "proximity": {
        "proximity_median_value",
        "proximity_iqr_value",
        "proximity_near_sample_fraction",
        "proximity_near_transition_count",
        "proximity_near_bout_count",
    },
    "light": {
        "median_light_lux",
        "percent_dark_samples",
        "night_mean_light_lux",
        "light_lux_iqr",
    },
}


def feature_review_table() -> pd.DataFrame:
    metadata = pd.read_csv(OUTPUT_DIR / "supplemental_phase4_24h_feature_metadata.csv")
    rows: list[dict[str, object]] = []
    for modality in ["proximity", "light"]:
        wide = pd.read_csv(OUTPUT_DIR / f"{modality}_features_wide.csv")
        source = wide.copy()
        for _, meta in metadata[metadata["modality"].eq(modality)].iterrows():
            name = str(meta["feature_name"])
            values = pd.to_numeric(source.get(name), errors="coerce")
            valid = values.dropna()
            paired = pd.DataFrame({"feature": values, "global_T1": pd.to_numeric(source.get("global_T1"), errors="coerce")}).dropna()
            spearman = paired["feature"].corr(paired["global_T1"], method="spearman") if len(paired) >= 5 else pd.NA
            pearson = paired["feature"].corr(paired["global_T1"], method="pearson") if len(paired) >= 5 else pd.NA
            group = FEATURE_GROUPS.get(name, "unclassified")
            rows.append(
                {
                    "modality": modality,
                    "feature_name": name,
                    "feature_group": group,
                    "exploratory_role": "coverage_sensitivity_only" if group == "coverage_qc" else "candidate_behavioral_feature",
                    "recommended_for_review": name in RECOMMENDED_FEATURES[modality],
                    "patients_with_value": int(valid.shape[0]),
                    "coverage_percent": 100 * valid.shape[0] / len(source) if len(source) else pd.NA,
                    "median": valid.median() if not valid.empty else pd.NA,
                    "iqr": valid.quantile(0.75) - valid.quantile(0.25) if not valid.empty else pd.NA,
                    "minimum": valid.min() if not valid.empty else pd.NA,
                    "maximum": valid.max() if not valid.empty else pd.NA,
                    "unique_values": int(valid.nunique()) if not valid.empty else 0,
                    "paired_global_T1_n": int(len(paired)),
                    "exploratory_spearman_global_T1": spearman,
                    "exploratory_pearson_global_T1": pearson,
                    "review_status": meta.get("review_status", ""),
                    "feature_definition": meta.get("feature_definition", ""),
                    "review_note": (
                        "Use only as a sensitivity covariate; it may reflect measurement opportunity."
                        if group == "coverage_qc"
                        else "Exploratory candidate; association is descriptive and not cross-validated."
                    ),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    output = OUTPUT_DIR / "phase4_supplemental_feature_review.csv"
    table = feature_review_table()
    table.to_csv(output, index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
