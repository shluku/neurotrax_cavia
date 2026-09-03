"""Exploratory USML analysis of the top five Ridge-ranked digital features.

This is a separate analysis. It does not alter the 41-feature unsupervised
analysis, supervised model outputs, or any source data. The five features are
selected from the midpoint/all-available T1 Ridge coefficient summary, with
missingness-indicator terms excluded and membership restricted to real features
in the fixed 41-feature USML panel.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from unsupervised_phenotyping import (
    CLUSTER_K_VALUES,
    MAX_PCS,
    N_RESAMPLES,
    N_SEEDS,
    PATIENT_FEATURE_COVERAGE_THRESHOLD,
    RANDOM_STATE,
    _cluster_feature_profiles,
    _cluster_quality,
    _format_median_iqr,
    _prepare_feature_matrix,
)
from unsupervised_phenotyping_posthoc import (
    COGNITIVE_OUTCOMES,
    DATASET_PATH as POSTHOC_DATASET_PATH,
    ID_COLUMN,
    _cognitive_frame,
    _followup_informed_baseline_frame,
    _normalize_id,
    _technical_patient_table,
    _write_comparison,
    _write_technical,
)


ROOT = Path(__file__).parent
BASE_DIR = ROOT / "output/analysis_candidates/phase11_t1_baseline"
SPAN_DIR = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline"
UNSUPERVISED_DIR = ROOT / "output/analysis_candidates/unsupervised_phenotyping_median_span"
PANEL_DIR = UNSUPERVISED_DIR / "usable_catalog_50pct"
OUTPUT_DIR = UNSUPERVISED_DIR / "top5_ridge_usml"

DATASET_PATH = POSTHOC_DATASET_PATH
METADATA_PATH = BASE_DIR / "phase11_t1_baseline_feature_metadata.csv"
RIDGE_SUMMARY_PATH = BASE_DIR / "model_t1_ridge/phase4_t1_ridge_coefficient_summary.csv"
STATUS_PATH = SPAN_DIR / "phase11_midpoint_t1_baseline_patient_table_status.csv"
COVERAGE_PATH = SPAN_DIR / "phase11_midpoint_t1_baseline_coverage.csv"
ORIGINAL_SCORES_PATH = PANEL_DIR / "pca_patient_scores.csv"
PANEL_INVENTORY_PATH = PANEL_DIR / "feature_inventory.csv"
ORIGINAL_LOADINGS_PATH = PANEL_DIR / "pca_loadings.csv"

TOP_N = 5
PANEL_NAME = "top5_ridge_real_features"


def _select_top_features() -> tuple[pd.DataFrame, pd.DataFrame]:
    ridge = pd.read_csv(RIDGE_SUMMARY_PATH)
    panel_inventory = pd.read_csv(PANEL_INVENTORY_PATH)
    panel_inventory = panel_inventory[panel_inventory["selected_for_panel"].astype(str).str.lower().eq("true")].copy()
    panel_features = set(panel_inventory["feature_name"].astype(str))
    eligible = ridge[
        ridge["feature_scope"].astype(str).eq("all_available")
        & ridge["term_name"].astype(str).isin(panel_features)
        & ~ridge["term_name"].astype(str).str.startswith("missingindicator_")
    ].copy()
    eligible = eligible.sort_values(["absolute_mean_coefficient", "term_name"], ascending=[False, True]).reset_index(drop=True)
    selected = eligible.head(TOP_N).copy()
    selected.insert(0, "ridge_rank_among_real_panel_features", np.arange(1, len(selected) + 1))
    selected = selected.rename(columns={"term_name": "feature_name"})
    selected = selected.merge(panel_inventory, on="feature_name", how="left", suffixes=("", "_panel"))
    return selected, eligible


def _load_feature_metadata(features: pd.DataFrame) -> pd.DataFrame:
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    metadata = metadata.drop_duplicates("feature_name")
    columns = [column for column in ["feature_name", "source_table", "feature_family", "short_description"] if column in metadata.columns]
    result = features.merge(metadata[columns], on="feature_name", how="left", suffixes=("", "_metadata"))
    for column in ["source_table", "feature_family", "short_description"]:
        metadata_column = f"{column}_metadata"
        if metadata_column in result.columns:
            result[column] = result[column].fillna(result[metadata_column]) if column in result.columns else result[metadata_column]
            result.drop(columns=[metadata_column], inplace=True)
    return result


def _choose_cluster_solution(scores: np.ndarray, quality: pd.DataFrame) -> tuple[int, str]:
    eligible = quality[quality["min_cluster_n_reference"].ge(5)]
    if not eligible.empty:
        selected = eligible.sort_values(["mean_silhouette", "mean_subsample_ari_vs_reference"], ascending=False).iloc[0]
        return int(selected["k"]), "Candidate selected with every cluster containing at least five patients."
    selected = quality.sort_values(
        ["min_cluster_n_reference", "mean_silhouette", "mean_subsample_ari_vs_reference"],
        ascending=[False, False, False],
    ).iloc[0]
    return int(selected["k"]), "Reference partition only: every candidate contains a cluster smaller than five patients."


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    selected, eligible = _select_top_features()
    if len(selected) < TOP_N:
        raise RuntimeError(f"Only {len(selected)} real Ridge-ranked features were available in the fixed USML panel.")
    selected.to_csv(OUTPUT_DIR / "top5_ridge_feature_selection.csv", index=False)
    eligible.to_csv(OUTPUT_DIR / "ridge_feature_ranking_eligible_real_panel.csv", index=False)
    selected_metadata = _load_feature_metadata(selected)
    selected_metadata.to_csv(OUTPUT_DIR / "top5_ridge_feature_metadata.csv", index=False)

    dataset = pd.read_csv(DATASET_PATH, dtype={ID_COLUMN: str, "Subject_ID_N": str})
    dataset[ID_COLUMN] = _normalize_id(dataset[ID_COLUMN])
    features = selected["feature_name"].astype(str).tolist()
    raw_source = dataset[features].apply(pd.to_numeric, errors="coerce")
    patient_feature_coverage = raw_source.notna().mean(axis=1)
    included = patient_feature_coverage.ge(PATIENT_FEATURE_COVERAGE_THRESHOLD)
    if int(included.sum()) < 12:
        raise RuntimeError("The top-five panel has fewer than 12 patients with at least 50% feature availability.")
    raw = raw_source.loc[included].reset_index(drop=True)
    cohort = dataset.loc[included].reset_index(drop=True)
    scaled, transform_table, transformed = _prepare_feature_matrix(raw)
    transform_table.to_csv(OUTPUT_DIR / "top5_ridge_feature_transformations.csv", index=False)

    n_pcs = min(MAX_PCS, scaled.shape[0] - 1, scaled.shape[1])
    pca = PCA(n_components=n_pcs, random_state=RANDOM_STATE)
    coordinates = pca.fit_transform(scaled)
    pc_columns = [f"PC{i}" for i in range(1, n_pcs + 1)]
    variance = pd.DataFrame(
        {
            "component": pc_columns,
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "explained_variance_percent": pca.explained_variance_ratio_ * 100,
            "cumulative_explained_variance_percent": np.cumsum(pca.explained_variance_ratio_) * 100,
        }
    )
    variance.to_csv(OUTPUT_DIR / "pca_variance.csv", index=False)

    loadings = pd.DataFrame(pca.components_.T, columns=pc_columns)
    loadings.insert(0, "feature_name", features)
    loadings["maximum_absolute_loading"] = loadings[pc_columns].abs().max(axis=1)
    loadings = loadings.merge(selected_metadata[["feature_name", "source_table", "feature_family"]], on="feature_name", how="left")
    loadings = loadings.sort_values("maximum_absolute_loading", ascending=False)
    loadings.to_csv(OUTPUT_DIR / "pca_loadings.csv", index=False)

    quality = pd.DataFrame([_cluster_quality(coordinates, k) for k in CLUSTER_K_VALUES])
    selected_k, solution_status = _choose_cluster_solution(coordinates, quality)
    quality["selected_solution"] = quality["k"].eq(selected_k)
    quality.to_csv(OUTPUT_DIR / "cluster_quality.csv", index=False)
    final_model = KMeans(n_clusters=selected_k, n_init=100, random_state=RANDOM_STATE)
    labels = final_model.fit_predict(coordinates)

    audit_columns = [
        "baseline_feature_missing_count",
        "baseline_feature_missing_fraction",
        "baseline_table_coverage_fraction",
    ]
    score_columns = [ID_COLUMN, "global_T1", "memory_T1", "ef_T1", "processing_speed_T1", "attention_T1", "motor_T1"]
    score_columns = [column for column in score_columns if column in cohort.columns]
    scores = cohort[score_columns].copy()
    scores["patient_feature_coverage_fraction"] = patient_feature_coverage.loc[included].to_numpy()
    for column in audit_columns:
        if column in cohort.columns:
            scores[column] = cohort[column].to_numpy()
    scores["cluster_k"] = selected_k
    scores["cluster_label"] = labels
    for index, column in enumerate(pc_columns):
        scores[column] = coordinates[:, index]
    scores.to_csv(OUTPUT_DIR / "pca_patient_scores.csv", index=False)

    feature_profiles = _cluster_feature_profiles(raw, scaled, labels, selected_metadata)
    feature_profiles.to_csv(OUTPUT_DIR / "cluster_feature_profiles.csv", index=False)
    profile_rows: list[dict[str, object]] = []
    for cluster in sorted(np.unique(labels)):
        group = cohort.loc[labels == cluster]
        row: dict[str, object] = {
            "cluster_k": selected_k,
            "cluster_label": int(cluster),
            "n_patients": int(len(group)),
            "patient_feature_coverage_mean_percent": float(patient_feature_coverage.loc[included].iloc[labels == cluster].mean() * 100),
            "global_T1_median_iqr": _format_median_iqr(group.get("global_T1", pd.Series(dtype=float))),
            "memory_T1_median_iqr": _format_median_iqr(group.get("memory_T1", pd.Series(dtype=float))),
            "executive_function_T1_median_iqr": _format_median_iqr(group.get("ef_T1", pd.Series(dtype=float))),
            "processing_speed_T1_median_iqr": _format_median_iqr(group.get("processing_speed_T1", pd.Series(dtype=float))),
            "attention_T1_median_iqr": _format_median_iqr(group.get("attention_T1", pd.Series(dtype=float))),
            "motor_T1_median_iqr": _format_median_iqr(group.get("motor_T1", pd.Series(dtype=float))),
        }
        profile_rows.append(row)
    pd.DataFrame(profile_rows).to_csv(OUTPUT_DIR / "cluster_profiles.csv", index=False)

    audit = dataset[[ID_COLUMN] + [column for column in ["global_T1"] + audit_columns if column in dataset.columns]].copy()
    audit["panel_feature_count"] = len(features)
    audit["panel_feature_observed_count"] = raw_source.notna().sum(axis=1).to_numpy()
    audit["panel_feature_coverage_fraction"] = patient_feature_coverage.to_numpy()
    audit["included_in_pca_and_clustering"] = included.to_numpy()
    audit.to_csv(OUTPUT_DIR / "patient_cohort_audit.csv", index=False)

    feature_comparison_frame = scores.merge(dataset, on=ID_COLUMN, how="left", suffixes=("", "_dataset"))
    feature_comparison = _write_comparison(feature_comparison_frame, selected_metadata, loadings)
    feature_comparison.to_csv(OUTPUT_DIR / "cluster_feature_comparison.csv", index=False)

    status = pd.read_csv(STATUS_PATH, dtype={ID_COLUMN: str})
    coverage = pd.read_csv(COVERAGE_PATH, dtype={ID_COLUMN: str})
    technical = _technical_patient_table(status, coverage)
    technical[ID_COLUMN] = _normalize_id(technical[ID_COLUMN])
    technical = technical.merge(scores[[ID_COLUMN, "cluster_label"]], on=ID_COLUMN, how="inner")
    technical = technical.merge(feature_comparison_frame[[ID_COLUMN, "patient_feature_coverage_fraction"]], on=ID_COLUMN, how="left")
    cohort_audit = dataset[[ID_COLUMN] + [column for column in audit_columns if column in dataset.columns]].copy()
    technical = technical.merge(cohort_audit, on=ID_COLUMN, how="left")
    technical["patient_feature_coverage_percent"] = _numeric_or_nan(technical["patient_feature_coverage_fraction"]) * 100
    technical["baseline_feature_missing_percent"] = _numeric_or_nan(technical.get("baseline_feature_missing_fraction")) * 100
    technical["baseline_table_coverage_percent"] = _numeric_or_nan(technical.get("baseline_table_coverage_fraction")) * 100
    technical.drop(columns=["patient_feature_coverage_fraction", "baseline_feature_missing_fraction", "baseline_table_coverage_fraction"], inplace=True, errors="ignore")
    technical.to_csv(OUTPUT_DIR / "technical_patient_audit.csv", index=False)
    technical_comparison, technical_inventory = _write_technical(feature_comparison_frame, technical)
    technical_comparison.to_csv(OUTPUT_DIR / "technical_confounding_comparison.csv", index=False)
    technical_inventory.to_csv(OUTPUT_DIR / "technical_variable_inventory.csv", index=False)

    cognitive_points, cognitive_summary = _cognitive_frame(dataset, scores)
    cognitive_points.to_csv(OUTPUT_DIR / "cognitive_overlay_points.csv", index=False)
    cognitive_summary.to_csv(OUTPUT_DIR / "cognitive_overlay_summary.csv", index=False)
    informed_points, informed_summary = _followup_informed_baseline_frame(dataset, scores)
    informed_points.to_csv(OUTPUT_DIR / "followup_informed_baseline_points.csv", index=False)
    informed_summary.to_csv(OUTPUT_DIR / "followup_informed_baseline_summary.csv", index=False)
    summary_columns = [
        "outcome", "outcome_column", "outcome_type", "n", "correlation_pc1", "correlation_pc2",
        "cluster_0_mean", "cluster_0_median_iqr", "cluster_1_mean", "cluster_1_median_iqr",
        "cluster_difference_cluster_1_minus_0", "standardized_difference_cluster_1_minus_0",
        "exploratory_p_value", "exploratory_q_value_fdr_bh", "interpretation_note",
    ]
    cognitive_summary[[column for column in summary_columns if column in cognitive_summary.columns]].to_csv(
        OUTPUT_DIR / "unsupervised_posthoc_summary.csv", index=False
    )

    run_record = {
        "analysis_name": PANEL_NAME,
        "original_outputs_changed": False,
        "ridge_ranking_source": str(RIDGE_SUMMARY_PATH.relative_to(ROOT)),
        "ridge_scope_used": "all_available",
        "selection_rule": "largest absolute mean Ridge coefficient, excluding missingness indicators and restricting to real features in the fixed 41-feature USML panel",
        "selected_features": selected["feature_name"].tolist(),
        "selected_feature_coefficients": selected[["feature_name", "coefficient_mean", "coefficient_positive_fraction", "absolute_mean_coefficient"]].to_dict("records"),
        "source_patients": int(len(dataset)),
        "analyzed_patients": int(included.sum()),
        "excluded_patients_for_panel_availability": int((~included).sum()),
        "selected_k": selected_k,
        "solution_status": solution_status,
        "pc1_pc2_explained_variance_percent": float(variance.head(2)["explained_variance_percent"].sum()),
        "mean_silhouette_selected_k": float(quality.loc[quality["k"].eq(selected_k), "mean_silhouette"].iloc[0]),
        "mean_subsample_ari_selected_k": float(quality.loc[quality["k"].eq(selected_k), "mean_subsample_ari_vs_reference"].iloc[0]),
        "technical_variables_used_to_define_clusters": False,
        "cognitive_variables_used_to_define_clusters": False,
        "exploratory_p_values_only": True,
    }
    (OUTPUT_DIR / "top5_ridge_usml_run_record.json").write_text(json.dumps(run_record, indent=2), encoding="utf-8")

    readme = f"""# Top-five Ridge feature USML analysis

This is a separate exploratory unsupervised analysis using the five strongest real features from the midpoint/all-available T1 Ridge coefficient summary. Missingness-indicator terms were excluded, and selected terms had to be present in the fixed 41-feature USML panel.

## Selected features

{', '.join(selected['feature_name'].tolist())}

## Design

- Patient inclusion requires at least 50% of the five selected feature values to be observed.
- Features use the same log1p-if-skewed transformation, median imputation, and robust scaling as the original USML pipeline.
- PCA and K-means clustering are unsupervised; cognitive outcomes and technical variables are not used to define them.
- Candidate k=2, 3, and 4 solutions are audited using silhouette and repeated subsample ARI. The displayed solution is selected using the same minimum-cluster-size rule as the original USML run.
- Feature, technical, cognitive, and follow-up-informed post-hoc outputs are written separately from the original USML outputs.

## Interpretation boundary

Ridge coefficient ranking is outcome-informed, so this five-feature USML run is hypothesis-generating and not independent validation. A visually separated cluster or a strong coefficient does not establish a clinical phenotype. All post-hoc p-values are exploratory.
"""
    (OUTPUT_DIR / "README_top5_ridge_usml.md").write_text(readme, encoding="utf-8")
    print(json.dumps(run_record, indent=2))
    print(f"outputs: {OUTPUT_DIR}")


def _numeric_or_nan(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(series, errors="coerce")


if __name__ == "__main__":
    main()
