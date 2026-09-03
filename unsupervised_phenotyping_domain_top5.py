"""Domain-specific Ridge-informed USML for the median-span T1 cohort.

This is a new exploratory analysis. It estimates a separate Ridge coefficient
profile for each baseline cognitive outcome, selects that outcome's five
strongest real features, and then runs a separate PCA/K-means audit on those
five features. Cognitive outcomes and technical variables are not used to
define the PCA coordinates or cluster labels after feature selection.

The feature ranking is outcome-informed, so these representations are useful
for hypothesis generation and visualization, not independent validation.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

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
    ID_COLUMN,
    _normalize_id,
    _technical_patient_table,
)


ROOT = Path(__file__).parent
BASE_DIR = ROOT / "output/analysis_candidates/phase11_t1_baseline"
SPAN_DIR = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline"
UNSUPERVISED_DIR = ROOT / "output/analysis_candidates/unsupervised_phenotyping_median_span"
PANEL_DIR = UNSUPERVISED_DIR / "usable_catalog_50pct"
OUTPUT_DIR = UNSUPERVISED_DIR / "domain_specific_ridge_usml"

DATASET_PATH = BASE_DIR / "phase11_t1_baseline_patient_dataset.csv"
METADATA_PATH = BASE_DIR / "phase11_t1_baseline_feature_metadata.csv"
STATUS_PATH = SPAN_DIR / "phase11_midpoint_t1_baseline_patient_table_status.csv"
COVERAGE_PATH = SPAN_DIR / "phase11_midpoint_t1_baseline_coverage.csv"
PANEL_INVENTORY_PATH = PANEL_DIR / "feature_inventory.csv"

TOP_N = 5
N_SPLITS = 5
N_REPEATS = 20
ALPHAS = np.logspace(-3, 4, 30)
PANEL_NAME = "domain_specific_ridge_top5_usml"

DOMAIN_TARGETS = {
    "Global": "global_T1",
    "Memory": "memory_T1",
    "Executive function": "ef_T1",
    "Processing speed": "processing_speed_T1",
    "Attention": "attention_T1",
    "Motor": "motor_T1",
}

T1_T2_PAIRS = {
    "Global": ("global_T1", "global_T2"),
    "Memory": ("memory_T1", "memory_T2"),
    "Executive function": ("ef_T1", "ef_T2"),
    "Processing speed": ("processing_speed_T1", "processing_speed_T2"),
    "Attention": ("attention_T1", "attention_T2"),
    "Motor": ("motor_T1", "motor_T2"),
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _numeric(series: object, index: pd.Index | None = None) -> pd.Series:
    if isinstance(series, pd.Series):
        return pd.to_numeric(series, errors="coerce")
    return pd.Series(np.nan, index=index, dtype=float)


def _build_ridge_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scaler", StandardScaler()),
            (
                "ridge",
                RidgeCV(
                    alphas=ALPHAS,
                    cv=KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE),
                    scoring="neg_root_mean_squared_error",
                ),
            ),
        ]
    )


def _all_available_features(metadata: pd.DataFrame, dataset: pd.DataFrame) -> list[str]:
    observed = metadata[
        metadata["primary_model_recommendation"].astype(str).ne("exclude_no_observed_data")
    ].copy()
    t1_week = observed.loc[
        observed["window_class"].astype(str).eq("t1_week_first_valid_24h"), "feature_name"
    ].tolist()
    adjusted = observed.loc[
        observed["window_class"].astype(str).eq("adjusted_first_available_7d"), "feature_name"
    ].tolist()
    return list(dict.fromkeys(feature for feature in t1_week + adjusted if feature in dataset.columns))


def _ridge_coefficient_profiles(
    dataset: pd.DataFrame,
    feature_names: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fold_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    X_all = dataset[feature_names].apply(pd.to_numeric, errors="coerce")

    for domain, target_name in DOMAIN_TARGETS.items():
        target = _numeric(dataset.get(target_name), dataset.index)
        valid = target.notna()
        X = X_all.loc[valid].reset_index(drop=True)
        y = target.loc[valid].to_numpy(dtype=float)
        outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
        for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
            repeat = split_index // N_SPLITS + 1
            fold = split_index % N_SPLITS + 1
            model = _build_ridge_pipeline()
            model.fit(X.iloc[train_idx], y[train_idx])
            names = model.named_steps["imputer"].get_feature_names_out(feature_names)
            coefficients = model.named_steps["ridge"].coef_
            for term_name, coefficient in zip(names, coefficients):
                fold_rows.append(
                    {
                        "domain": domain,
                        "target": target_name,
                        "repeat": repeat,
                        "fold": fold,
                        "term_name": str(term_name),
                        "coefficient": float(coefficient),
                        "ridge_alpha": float(model.named_steps["ridge"].alpha_),
                        "n_target_patients": int(valid.sum()),
                    }
                )

        domain_folds = pd.DataFrame(fold_rows)
        domain_folds = domain_folds[domain_folds["domain"].eq(domain)]
        for term_name, group in domain_folds.groupby("term_name", sort=True):
            coefficients = pd.to_numeric(group["coefficient"], errors="coerce").dropna()
            summary_rows.append(
                {
                    "domain": domain,
                    "target": target_name,
                    "term_name": term_name,
                    "n_folds": int(len(coefficients)),
                    "coefficient_mean": float(coefficients.mean()),
                    "coefficient_median": float(coefficients.median()),
                    "coefficient_sd": float(coefficients.std(ddof=1)) if len(coefficients) > 1 else np.nan,
                    "absolute_mean_coefficient": float(coefficients.mean().__abs__()),
                    "mean_absolute_coefficient": float(coefficients.abs().mean()),
                    "coefficient_positive_fraction": float((coefficients > 0).mean()),
                    "coefficient_negative_fraction": float((coefficients < 0).mean()),
                    "coefficient_direction_stability": float(max((coefficients > 0).mean(), (coefficients < 0).mean())),
                }
            )
    return pd.DataFrame(fold_rows), pd.DataFrame(summary_rows)


def _select_domain_features(
    coefficient_summary: pd.DataFrame,
    metadata: pd.DataFrame,
    panel_inventory: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    panel_features = set(
        panel_inventory.loc[
            panel_inventory["selected_for_panel"].astype(str).str.lower().eq("true"), "feature_name"
        ].astype(str)
    )
    real = coefficient_summary[
        coefficient_summary["term_name"].astype(str).isin(panel_features)
        & ~coefficient_summary["term_name"].astype(str).str.startswith("missingindicator_")
    ].copy()
    real = real.merge(metadata, left_on="term_name", right_on="feature_name", how="left", suffixes=("", "_metadata"))
    real = real.sort_values(
        ["domain", "absolute_mean_coefficient", "coefficient_direction_stability", "term_name"],
        ascending=[True, False, False, True],
    ).reset_index(drop=True)
    real["ridge_rank_among_real_panel_features"] = real.groupby("domain").cumcount() + 1
    selected = real[real["ridge_rank_among_real_panel_features"].le(TOP_N)].copy()
    selected["feature_name"] = selected["term_name"]
    selected["selected_for_domain_panel"] = True
    return selected, real


def _standardized_difference(left: pd.Series, right: pd.Series) -> float:
    left = _numeric(left).dropna()
    right = _numeric(right).dropna()
    if len(left) < 2 or len(right) < 2:
        return np.nan
    pooled = ((len(left) - 1) * left.var(ddof=1) + (len(right) - 1) * right.var(ddof=1)) / (len(left) + len(right) - 2)
    return float((right.mean() - left.mean()) / math.sqrt(pooled)) if pooled > 0 else np.nan


def _p_value(left: pd.Series, right: pd.Series) -> float:
    left = _numeric(left).dropna()
    right = _numeric(right).dropna()
    if len(left) < 3 or len(right) < 3:
        return np.nan
    try:
        return float(mannwhitneyu(left, right, alternative="two-sided").pvalue)
    except ValueError:
        return np.nan


def _cluster_stat_row(frame: pd.DataFrame, variable: str, cluster: int) -> dict[str, object]:
    values = _numeric(frame.loc[frame["cluster_label"].eq(cluster), variable]).dropna()
    return {
        f"cluster_{cluster}_n": int(len(values)),
        f"cluster_{cluster}_mean": float(values.mean()) if not values.empty else np.nan,
        f"cluster_{cluster}_median": float(values.median()) if not values.empty else np.nan,
        f"cluster_{cluster}_median_iqr": _format_median_iqr(values),
    }


def _feature_comparison(
    frame: pd.DataFrame,
    selected_metadata: pd.DataFrame,
    loadings: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    clusters = sorted(pd.to_numeric(frame["cluster_label"], errors="coerce").dropna().astype(int).unique())
    loadings_lookup = loadings.set_index("feature_name") if not loadings.empty else pd.DataFrame()
    for _, meta in selected_metadata.iterrows():
        feature = str(meta["feature_name"])
        row: dict[str, object] = {
            "feature_name": feature,
            "source_table": meta.get("source_table", ""),
            "feature_family": meta.get("feature_family", ""),
            "short_description": meta.get("short_description", ""),
            "source_patient_coverage_percent": meta.get("source_patient_coverage_percent", np.nan),
            "feature_group": meta.get("feature_family", ""),
            "all_cluster_medians_iqr": " | ".join(
                f"Cluster {cluster}: {_format_median_iqr(frame.loc[frame['cluster_label'].eq(cluster), feature])}"
                for cluster in clusters
            ),
        }
        for cluster in clusters:
            row.update(_cluster_stat_row(frame, feature, cluster))
        if 0 in clusters and 1 in clusters:
            left = frame.loc[frame["cluster_label"].eq(0), feature]
            right = frame.loc[frame["cluster_label"].eq(1), feature]
            row.update(
                {
                    "cluster_1_minus_0_mean_difference": float(_numeric(right).mean() - _numeric(left).mean()),
                    "standardized_difference_cluster_1_minus_0": _standardized_difference(left, right),
                    "exploratory_p_value_cluster_0_vs_1": _p_value(left, right),
                }
            )
        if feature in loadings_lookup.index:
            loading = loadings_lookup.loc[feature]
            row.update(
                {
                    "pca_loading_pc1": loading.get("PC1", np.nan),
                    "pca_loading_pc2": loading.get("PC2", np.nan),
                    "pca_max_abs_loading": loading.get("maximum_absolute_loading", np.nan),
                }
            )
        rows.append(row)
    result = pd.DataFrame(rows)
    if "standardized_difference_cluster_1_minus_0" in result:
        result["absolute_standardized_difference_cluster_1_minus_0"] = result["standardized_difference_cluster_1_minus_0"].abs()
        result = result.sort_values("absolute_standardized_difference_cluster_1_minus_0", ascending=False)
    return result


def _technical_comparison(technical: pd.DataFrame) -> pd.DataFrame:
    variables = [
        "patient_feature_coverage_percent",
        "baseline_feature_missing_percent",
        "baseline_feature_missing_count",
        "baseline_table_coverage_percent",
        "recorded_table_count",
        "tables_without_data",
        "total_rows_in_window",
        "mean_rows_per_calculated_table",
        "n_devices_available",
        "n_devices_used",
        "configured_endpoint_interval_days",
        "observed_timestamp_span_days",
        "coverage_rows_across_devices",
    ]
    rows: list[dict[str, object]] = []
    clusters = sorted(pd.to_numeric(technical["cluster_label"], errors="coerce").dropna().astype(int).unique())
    descriptions = {
        "patient_feature_coverage_percent": "Observed fraction of the five domain-selected feature values.",
        "baseline_feature_missing_percent": "Missingness across the full extracted baseline feature catalog.",
        "baseline_feature_missing_count": "Count of missing extracted baseline feature values.",
        "baseline_table_coverage_percent": "Fraction of baseline tables with a calculated feature value.",
        "recorded_table_count": "Number of tables with a calculated result in the midpoint span.",
        "tables_without_data": "Number of source tables with no rows in the midpoint span.",
        "total_rows_in_window": "Total source rows across calculated tables; a collection-intensity proxy.",
        "mean_rows_per_calculated_table": "Mean source rows per calculated table.",
        "n_devices_available": "Number of distinct available device identifiers.",
        "n_devices_used": "Number of distinct device identifiers used by calculated tables.",
        "configured_endpoint_interval_days": "Configured endpoint interval, not recorded days.",
        "observed_timestamp_span_days": "Earliest-to-latest observed timestamp span, not continuous recording.",
        "coverage_rows_across_devices": "Rows reported in the coverage audit across devices.",
    }
    for variable in variables:
        if variable not in technical.columns:
            continue
        values = _numeric(technical[variable])
        row: dict[str, object] = {"variable": variable, "description": descriptions.get(variable, variable), "available": values.notna().any()}
        for cluster in clusters:
            row.update(_cluster_stat_row(technical, variable, cluster))
        if 0 in clusters and 1 in clusters:
            left = technical.loc[technical["cluster_label"].eq(0), variable]
            right = technical.loc[technical["cluster_label"].eq(1), variable]
            row["standardized_difference_cluster_1_minus_0"] = _standardized_difference(left, right)
            row["exploratory_p_value_cluster_0_vs_1"] = _p_value(left, right)
        rows.append(row)
    result = pd.DataFrame(rows)
    if not result.empty and "standardized_difference_cluster_1_minus_0" in result:
        result["absolute_standardized_difference_cluster_1_minus_0"] = result["standardized_difference_cluster_1_minus_0"].abs()
        result = result.sort_values("absolute_standardized_difference_cluster_1_minus_0", ascending=False)
    return result


def _cognitive_overlay(dataset: pd.DataFrame, scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = scores.merge(dataset, on=ID_COLUMN, how="left", suffixes=("", "_dataset"))
    outcomes: list[tuple[str, str, str]] = []
    delta_columns: dict[str, pd.Series] = {}
    for domain, (t1, t2) in T1_T2_PAIRS.items():
        outcomes.append((f"{domain} T1", t1, "baseline"))
        outcomes.append((f"{domain} T2", t2, "follow-up"))
        delta = f"{_slug(domain)}_delta"
        delta_columns[delta] = _numeric(merged.get(t2, pd.Series(np.nan, index=merged.index))) - _numeric(merged.get(t1, pd.Series(np.nan, index=merged.index)))
        outcomes.append((f"{domain} T2-T1 delta", delta, "change"))
    if delta_columns:
        merged = pd.concat([merged, pd.DataFrame(delta_columns, index=merged.index)], axis=1)

    points: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    for label, column, outcome_type in outcomes:
        if column not in merged.columns:
            continue
        subset = merged[[ID_COLUMN, "cluster_label", "PC1", "PC2", column]].copy()
        subset["outcome_value"] = _numeric(subset[column])
        subset = subset.dropna(subset=["outcome_value", "PC1", "PC2", "cluster_label"])
        subset["outcome"] = label
        subset["outcome_column"] = column
        subset["outcome_type"] = outcome_type
        points.append(subset[[ID_COLUMN, "cluster_label", "PC1", "PC2", "outcome", "outcome_column", "outcome_type", "outcome_value"]])
        left = subset.loc[subset["cluster_label"].eq(0), "outcome_value"]
        right = subset.loc[subset["cluster_label"].eq(1), "outcome_value"]
        summaries.append(
            {
                "outcome": label,
                "outcome_column": column,
                "outcome_type": outcome_type,
                "n": int(len(subset)),
                "correlation_pc1": float(subset["PC1"].corr(subset["outcome_value"])) if len(subset) >= 3 else np.nan,
                "correlation_pc2": float(subset["PC2"].corr(subset["outcome_value"])) if len(subset) >= 3 else np.nan,
                "cluster_0_n": int(len(left)),
                "cluster_1_n": int(len(right)),
                "cluster_0_mean": float(left.mean()) if not left.empty else np.nan,
                "cluster_1_mean": float(right.mean()) if not right.empty else np.nan,
                "cluster_0_median_iqr": _format_median_iqr(left),
                "cluster_1_median_iqr": _format_median_iqr(right),
                "cluster_difference_cluster_1_minus_0": float(right.mean() - left.mean()) if not left.empty and not right.empty else np.nan,
                "standardized_difference_cluster_1_minus_0": _standardized_difference(left, right),
                "exploratory_p_value_cluster_0_vs_1": _p_value(left, right),
                "interpretation_note": "Negative delta means lower T2 than T1; all outcome comparisons are exploratory.",
            }
        )
    return (
        pd.concat(points, ignore_index=True) if points else pd.DataFrame(),
        pd.DataFrame(summaries),
    )


def _choose_cluster_solution(quality: pd.DataFrame) -> tuple[int, str]:
    eligible = quality[quality["min_cluster_n_reference"].ge(5)]
    if not eligible.empty:
        selected = eligible.sort_values(
            ["mean_silhouette", "mean_subsample_ari_vs_reference"], ascending=False
        ).iloc[0]
        return int(selected["k"]), "Selected among candidates with every cluster containing at least five patients."
    selected = quality.sort_values(
        ["min_cluster_n_reference", "mean_silhouette", "mean_subsample_ari_vs_reference"],
        ascending=[False, False, False],
    ).iloc[0]
    return int(selected["k"]), "Reference partition only: every candidate contains a cluster smaller than five patients."


def _technical_patient_frame(
    dataset: pd.DataFrame,
    scores: pd.DataFrame,
    patient_feature_coverage: pd.Series,
) -> pd.DataFrame:
    status = pd.read_csv(STATUS_PATH, dtype={ID_COLUMN: str})
    coverage = pd.read_csv(COVERAGE_PATH, dtype={ID_COLUMN: str})
    technical = _technical_patient_table(status, coverage)
    technical[ID_COLUMN] = _normalize_id(technical[ID_COLUMN])
    technical = technical.merge(scores[[ID_COLUMN, "cluster_label"]], on=ID_COLUMN, how="inner")
    audit_columns = [
        "baseline_feature_missing_count",
        "baseline_feature_missing_fraction",
        "baseline_table_coverage_fraction",
    ]
    audit = dataset[[ID_COLUMN] + [column for column in audit_columns if column in dataset.columns]].copy()
    audit[ID_COLUMN] = _normalize_id(audit[ID_COLUMN])
    technical = technical.merge(audit, on=ID_COLUMN, how="left")
    coverage_frame = pd.DataFrame({ID_COLUMN: dataset[ID_COLUMN], "patient_feature_coverage_fraction": patient_feature_coverage.to_numpy()})
    coverage_frame[ID_COLUMN] = _normalize_id(coverage_frame[ID_COLUMN])
    technical = technical.merge(coverage_frame, on=ID_COLUMN, how="left")
    technical["patient_feature_coverage_percent"] = _numeric(technical["patient_feature_coverage_fraction"]) * 100
    technical["baseline_feature_missing_percent"] = _numeric(technical.get("baseline_feature_missing_fraction")) * 100
    technical["baseline_table_coverage_percent"] = _numeric(technical.get("baseline_table_coverage_fraction")) * 100
    return technical


def _run_domain_pca(
    domain: str,
    selected: pd.DataFrame,
    dataset: pd.DataFrame,
) -> dict[str, object]:
    domain_dir = OUTPUT_DIR / _slug(domain)
    domain_dir.mkdir(parents=True, exist_ok=True)
    selected_domain = selected[selected["domain"].eq(domain)].copy()
    features = selected_domain["feature_name"].astype(str).tolist()
    if len(features) != TOP_N:
        raise RuntimeError(f"{domain} has {len(features)} selected features; expected {TOP_N}.")
    selected_domain.to_csv(domain_dir / "feature_selection.csv", index=False)

    raw_source = dataset[features].apply(pd.to_numeric, errors="coerce")
    patient_feature_coverage = raw_source.notna().mean(axis=1)
    included = patient_feature_coverage.ge(PATIENT_FEATURE_COVERAGE_THRESHOLD)
    if int(included.sum()) < 12:
        raise RuntimeError(f"{domain} has fewer than 12 patients with at least 50% feature availability.")
    raw = raw_source.loc[included].reset_index(drop=True)
    cohort = dataset.loc[included].reset_index(drop=True)
    scaled, transform_table, _ = _prepare_feature_matrix(raw)
    transform_table.to_csv(domain_dir / "feature_transformations.csv", index=False)

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
    variance.to_csv(domain_dir / "pca_variance.csv", index=False)
    loadings = pd.DataFrame(pca.components_.T, columns=pc_columns)
    loadings.insert(0, "feature_name", features)
    loadings["maximum_absolute_loading"] = loadings[pc_columns].abs().max(axis=1)
    loadings.to_csv(domain_dir / "pca_loadings.csv", index=False)

    quality = pd.DataFrame([_cluster_quality(coordinates, k) for k in CLUSTER_K_VALUES])
    selected_k, solution_status = _choose_cluster_solution(quality)
    quality["selected_solution"] = quality["k"].eq(selected_k)
    quality.to_csv(domain_dir / "cluster_quality.csv", index=False)
    labels = KMeans(n_clusters=selected_k, n_init=100, random_state=RANDOM_STATE).fit_predict(coordinates)

    flattened_score_columns = []
    for pair in T1_T2_PAIRS.values():
        flattened_score_columns.extend(pair)
    score_columns = [ID_COLUMN, "Subject_ID_N"] + list(dict.fromkeys(flattened_score_columns))
    score_columns = [column for column in score_columns if column in cohort.columns]
    scores = cohort[score_columns].copy()
    scores[ID_COLUMN] = _normalize_id(scores[ID_COLUMN])
    scores["patient_feature_coverage_fraction"] = patient_feature_coverage.loc[included].to_numpy()
    scores["cluster_k"] = selected_k
    scores["cluster_label"] = labels
    for index, column in enumerate(pc_columns):
        scores[column] = coordinates[:, index]
    scores.to_csv(domain_dir / "pca_patient_scores.csv", index=False)

    selected_metadata = selected_domain.copy()
    selected_metadata["source_patient_coverage_percent"] = raw_source[features].notna().mean().reindex(features).to_numpy() * 100
    feature_profiles = _cluster_feature_profiles(raw, scaled, labels, selected_metadata)
    feature_profiles.to_csv(domain_dir / "cluster_feature_profiles.csv", index=False)
    profile_rows: list[dict[str, object]] = []
    for cluster in sorted(np.unique(labels)):
        group = cohort.loc[labels == cluster]
        row: dict[str, object] = {
            "domain": domain,
            "cluster_k": selected_k,
            "cluster_label": int(cluster),
            "n_patients": int(len(group)),
            "patient_feature_coverage_mean_percent": float(patient_feature_coverage.loc[included].iloc[labels == cluster].mean() * 100),
        }
        for outcome_domain, (t1, _) in T1_T2_PAIRS.items():
            row[f"{_slug(outcome_domain)}_T1_median_iqr"] = _format_median_iqr(group.get(t1, pd.Series(dtype=float)))
        profile_rows.append(row)
    pd.DataFrame(profile_rows).to_csv(domain_dir / "cluster_profiles.csv", index=False)

    score_frame = scores.copy()
    score_frame["cluster_label"] = labels
    feature_comparison = _feature_comparison(score_frame.join(raw), selected_metadata, loadings)
    feature_comparison.to_csv(domain_dir / "cluster_feature_comparison.csv", index=False)

    audit = dataset[[ID_COLUMN] + [column for column in ["global_T1"] if column in dataset.columns]].copy()
    audit[ID_COLUMN] = _normalize_id(audit[ID_COLUMN])
    audit["domain"] = domain
    audit["panel_feature_count"] = len(features)
    audit["panel_feature_observed_count"] = raw_source.notna().sum(axis=1).to_numpy()
    audit["panel_feature_coverage_fraction"] = patient_feature_coverage.to_numpy()
    audit["included_in_pca_and_clustering"] = included.to_numpy()
    audit.to_csv(domain_dir / "patient_cohort_audit.csv", index=False)

    technical = _technical_patient_frame(dataset, scores, patient_feature_coverage)
    technical.to_csv(domain_dir / "technical_patient_audit.csv", index=False)
    technical_comparison = _technical_comparison(technical)
    technical_comparison.to_csv(domain_dir / "technical_confounding_comparison.csv", index=False)

    cognitive_points, cognitive_summary = _cognitive_overlay(dataset, scores)
    cognitive_points.to_csv(domain_dir / "cognitive_overlay_points.csv", index=False)
    cognitive_summary.to_csv(domain_dir / "cognitive_overlay_summary.csv", index=False)

    selected_quality = quality.loc[quality["k"].eq(selected_k)].iloc[0]
    domain_summary = {
        "domain": domain,
        "target": DOMAIN_TARGETS[domain],
        "top_five_features": ";".join(features),
        "source_patients": int(len(dataset)),
        "target_patients": int(_numeric(dataset[DOMAIN_TARGETS[domain]]).notna().sum()),
        "analyzed_patients": int(included.sum()),
        "excluded_for_panel_availability": int((~included).sum()),
        "selected_k": selected_k,
        "solution_status": solution_status,
        "pc1_pc2_explained_variance_percent": float(variance.head(2)["explained_variance_percent"].sum()),
        "mean_silhouette_selected_k": float(selected_quality["mean_silhouette"]),
        "mean_subsample_ari_selected_k": float(selected_quality["mean_subsample_ari_vs_reference"]),
        "technical_variables_used_to_define_clusters": False,
        "cognitive_variables_used_to_define_pca_or_clusters": False,
        "feature_selection_is_outcome_informed": True,
    }
    (domain_dir / "domain_run_record.json").write_text(json.dumps(domain_summary, indent=2), encoding="utf-8")
    return domain_summary


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={ID_COLUMN: str, "Subject_ID_N": str})
    dataset[ID_COLUMN] = _normalize_id(dataset[ID_COLUMN])
    metadata = pd.read_csv(METADATA_PATH, dtype=str).drop_duplicates("feature_name")
    panel_inventory = pd.read_csv(PANEL_INVENTORY_PATH)
    all_features = _all_available_features(metadata, dataset)
    if len(all_features) < TOP_N:
        raise RuntimeError(f"Only {len(all_features)} all-available features are present in the Phase 11 dataset.")

    fold_coefficients, coefficient_summary = _ridge_coefficient_profiles(dataset, all_features)
    fold_coefficients.to_csv(OUTPUT_DIR / "ridge_coefficient_folds.csv", index=False)
    coefficient_summary.to_csv(OUTPUT_DIR / "ridge_coefficient_summary.csv", index=False)
    selected, eligible = _select_domain_features(coefficient_summary, metadata, panel_inventory)
    if selected.groupby("domain").size().min() < TOP_N:
        raise RuntimeError("At least one domain has fewer than five eligible real features in the fixed USML panel.")
    selected.to_csv(OUTPUT_DIR / "domain_feature_selection.csv", index=False)
    eligible.to_csv(OUTPUT_DIR / "domain_feature_ranking_eligible_real_panel.csv", index=False)

    summaries = [_run_domain_pca(domain, selected, dataset) for domain in DOMAIN_TARGETS]
    summary = pd.DataFrame(summaries)
    summary.to_csv(OUTPUT_DIR / "domain_summary.csv", index=False)
    run_record = {
        "analysis_name": PANEL_NAME,
        "original_outputs_changed": False,
        "source_dataset": str(DATASET_PATH.relative_to(ROOT)),
        "feature_ranking_candidates": "all observed T1-week and adjusted-window features except excluded/zero-observed features",
        "feature_ranking_restriction": "real features present in the fixed 41-feature USML panel; missingness indicators excluded",
        "domains": list(DOMAIN_TARGETS),
        "top_n": TOP_N,
        "ridge_outer_cv": f"{N_SPLITS}-fold repeated {N_REPEATS} times",
        "preprocessing": "fold-local median imputation with indicators, standardization, inner-CV Ridge alpha selection",
        "pca_patient_coverage_threshold_percent": PATIENT_FEATURE_COVERAGE_THRESHOLD * 100,
        "technical_variables_used_to_define_clusters": False,
        "cognitive_variables_used_to_define_pca_or_clusters": False,
        "feature_selection_is_outcome_informed": True,
        "exploratory_only": True,
    }
    (OUTPUT_DIR / "domain_specific_ridge_usml_run_record.json").write_text(json.dumps(run_record, indent=2), encoding="utf-8")
    readme = """# Domain-specific Ridge-informed USML

This separate exploratory analysis asks whether each baseline cognitive domain has a different digital-feature structure.

## Workflow

1. Fit a separate Ridge model for Global, Memory, Executive function, Processing speed, Attention, and Motor T1 scores.
2. Use repeated 5-fold cross-validation repeated 20 times, with fold-local median imputation, missingness indicators, standardization, and inner-CV alpha selection.
3. Rank real features by the absolute mean coefficient across the 100 outer folds for each domain. Missingness-indicator terms are excluded from the final panels, and a feature must belong to the fixed 41-feature USML panel.
4. Select the strongest five features independently for each domain. The same feature can appear in more than one domain panel.
5. Run a new PCA and exploratory K-means audit for each five-feature panel. Patient inclusion requires at least 50% of the five values to be observed.
6. Compare cluster feature profiles, technical collection variables, baseline cognitive scores, follow-up scores, and T2-minus-T1 changes only after the domain-specific PCA and clustering are complete.

## Interpretation boundary

The feature-ranking step uses the cognitive outcome, so the resulting PCA/clustering maps are outcome-informed and hypothesis-generating. They are not independent validation of a clinical phenotype. Cognitive and technical variables do not enter the PCA or K-means calculations. All p-values and cognitive overlays are exploratory, and cluster stability should be interpreted together with coverage and technical audits.

Each domain directory contains its own feature selection, PCA coordinates/loadings, cluster quality/profile tables, technical audit, and cognitive overlay outputs. The original USML, coverage-adjusted USML, and global top-five outputs are unchanged.
"""
    (OUTPUT_DIR / "README_domain_specific_ridge_usml.md").write_text(readme, encoding="utf-8")
    print(summary[["domain", "top_five_features", "analyzed_patients", "selected_k", "pc1_pc2_explained_variance_percent", "mean_silhouette_selected_k", "mean_subsample_ari_selected_k"]].to_string(index=False))
    print(f"outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
