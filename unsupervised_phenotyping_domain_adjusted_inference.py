"""Pre-specified coverage-adjusted inference for Motor and Attention USML.

This is a separate sensitivity analysis. It does not change the original
USML or domain-specific Ridge USML outputs. The analysis first residualizes
candidate digital features against fixed collection-intensity variables, then
selects five features for Motor and Attention with the existing repeated-CV
Ridge coefficient rule. A permutation reruns feature selection, PCA, and
fixed-k clustering for every shuffled outcome, so the calibrated p-value
includes outcome-informed feature selection. Bootstrap intervals quantify
sampling variability conditional on the observed adjusted five-feature panel.
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
from sklearn.metrics import silhouette_score
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from unsupervised_phenotyping import (
    N_RESAMPLES,
    N_SEEDS,
    PATIENT_FEATURE_COVERAGE_THRESHOLD,
    RANDOM_STATE,
    _cluster_quality,
    _format_median_iqr,
    _prepare_feature_matrix,
)
from unsupervised_phenotyping_domain_top5 import (
    DOMAIN_TARGETS,
    T1_T2_PAIRS,
    _all_available_features,
    _cognitive_overlay,
    _numeric,
    _select_domain_features,
    _technical_comparison,
)
from unsupervised_phenotyping_posthoc import ID_COLUMN, _normalize_id, _technical_patient_table


ROOT = Path(__file__).parent
BASE_DIR = ROOT / "output/analysis_candidates/phase11_t1_baseline"
SPAN_DIR = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline"
UNSUPERVISED_DIR = ROOT / "output/analysis_candidates/unsupervised_phenotyping_median_span"
PANEL_DIR = UNSUPERVISED_DIR / "usable_catalog_50pct"
OUTPUT_DIR = UNSUPERVISED_DIR / "domain_specific_adjusted_inference"

DATASET_PATH = BASE_DIR / "phase11_t1_baseline_patient_dataset.csv"
METADATA_PATH = BASE_DIR / "phase11_t1_baseline_feature_metadata.csv"
STATUS_PATH = SPAN_DIR / "phase11_midpoint_t1_baseline_patient_table_status.csv"
COVERAGE_PATH = SPAN_DIR / "phase11_midpoint_t1_baseline_coverage.csv"
PANEL_INVENTORY_PATH = PANEL_DIR / "feature_inventory.csv"

DOMAINS = {"Motor": "motor_T1", "Attention": "attention_T1"}
TOP_N = 5
N_SPLITS = 5
N_REPEATS = 20
N_PERMUTATIONS = 100
N_BOOTSTRAPS = 1000
ALPHAS = np.logspace(-3, 4, 30)
INFERENCE_RANDOM_STATE = 20260830
PERMUTATION_REPEATS = N_REPEATS

TECHNICAL_COLUMNS = [
    "observed_timestamp_span_days",
    "total_rows_in_window",
    "recorded_table_count",
    "baseline_feature_missing_percent",
    "baseline_table_coverage_percent",
    "candidate_feature_coverage_percent",
]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _is_fraction_like(feature: str) -> bool:
    lowered = feature.lower()
    return any(token in lowered for token in ("fraction", "ratio", "diversity"))


def _is_volume_like(feature: str) -> bool:
    lowered = feature.lower()
    if _is_fraction_like(feature):
        return False
    return (
        lowered.endswith("_count")
        or lowered.startswith("unique_")
        or "event_count" in lowered
        or "transition_count" in lowered
        or lowered.endswith("_distance_km")
        or lowered.endswith("_duration_seconds")
    )


def _build_ridge_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scaler", StandardScaler()),
            (
                "ridge",
                RidgeCV(
                    alphas=ALPHAS,
                    cv=KFold(n_splits=4, shuffle=True, random_state=INFERENCE_RANDOM_STATE),
                    scoring="neg_root_mean_squared_error",
                ),
            ),
        ]
    )


def _technical_frame(dataset: pd.DataFrame, candidate_features: list[str]) -> pd.DataFrame:
    status = pd.read_csv(STATUS_PATH, dtype={ID_COLUMN: str})
    coverage = pd.read_csv(COVERAGE_PATH, dtype={ID_COLUMN: str})
    technical = _technical_patient_table(status, coverage)
    technical[ID_COLUMN] = _normalize_id(technical[ID_COLUMN])
    audit_columns = [
        "baseline_feature_missing_count",
        "baseline_feature_missing_fraction",
        "baseline_table_coverage_fraction",
    ]
    audit = dataset[[ID_COLUMN] + [column for column in audit_columns if column in dataset.columns]].copy()
    audit[ID_COLUMN] = _normalize_id(audit[ID_COLUMN])
    technical = technical.merge(audit, on=ID_COLUMN, how="left")
    coverage_fraction = dataset[candidate_features].apply(pd.to_numeric, errors="coerce").notna().mean(axis=1)
    feature_coverage = pd.DataFrame(
        {ID_COLUMN: _normalize_id(dataset[ID_COLUMN]), "candidate_feature_coverage_percent": coverage_fraction.to_numpy() * 100}
    )
    technical = technical.merge(feature_coverage, on=ID_COLUMN, how="left")
    technical["baseline_feature_missing_percent"] = _numeric(technical.get("baseline_feature_missing_fraction")) * 100
    technical["baseline_table_coverage_percent"] = _numeric(technical.get("baseline_table_coverage_fraction")) * 100
    return technical


def _technical_design(technical: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    parts = [np.ones(len(technical), dtype=float)]
    used = []
    for column in TECHNICAL_COLUMNS:
        values = _numeric(technical.get(column, pd.Series(np.nan, index=technical.index)))
        values = values.replace([np.inf, -np.inf], np.nan)
        values = values.fillna(values.median()).fillna(0.0)
        if column in {"observed_timestamp_span_days", "total_rows_in_window", "recorded_table_count"}:
            values = np.log1p(values.clip(lower=0))
        scale = values.std(ddof=0)
        if not np.isfinite(scale) or scale == 0:
            continue
        parts.append(((values - values.mean()) / scale).to_numpy(dtype=float))
        used.append(column)
    return np.column_stack(parts), used


def _adjust_features(
    dataset: pd.DataFrame,
    technical: pd.DataFrame,
    candidate_features: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Exposure-normalize volume features, then residualize observed values."""
    raw = dataset[candidate_features].apply(pd.to_numeric, errors="coerce").copy()
    technical = technical.set_index(ID_COLUMN).reindex(_normalize_id(dataset[ID_COLUMN])).reset_index()
    exposure = _numeric(technical["observed_timestamp_span_days"])
    exposure = exposure.where(exposure.gt(0), _numeric(technical.get("configured_endpoint_interval_days")))
    exposure = exposure.where(exposure.gt(0), 1.0).fillna(1.0)
    design, technical_used = _technical_design(technical)
    adjusted = pd.DataFrame(index=raw.index)
    rows: list[dict[str, object]] = []
    for feature in candidate_features:
        values = raw[feature].copy()
        exposure_normalized = False
        if _is_volume_like(feature):
            values = values / exposure.to_numpy()
            exposure_normalized = True
        valid = values.dropna()
        transformed = values.copy()
        transformation = "none"
        if (
            not valid.empty
            and (valid >= 0).all()
            and not _is_fraction_like(feature)
            and valid.nunique() > 1
            and abs(float(valid.skew())) > 1.5
        ):
            transformed = np.log1p(values)
            transformation = "log1p_nonnegative_skewed"
        observed = transformed.notna().to_numpy()
        residuals = transformed.copy()
        if observed.sum() >= len(technical_used) + 3:
            coefficients, *_ = np.linalg.lstsq(design[observed], transformed.to_numpy(dtype=float)[observed], rcond=None)
            residuals.loc[observed] = transformed.to_numpy(dtype=float)[observed] - design[observed] @ coefficients
            residualized = True
        else:
            residualized = False
        adjusted[feature] = residuals
        rows.append(
            {
                "feature_name": feature,
                "source_patient_missing_percent": float(values.isna().mean() * 100),
                "exposure_normalized": exposure_normalized,
                "transformation": transformation,
                "technical_residualized": residualized,
                "technical_variables_used": ";".join(technical_used),
            }
        )
    return adjusted, pd.DataFrame(rows)


def _coefficient_summary(X: pd.DataFrame, y: pd.Series, domain: str, repeats: int = N_REPEATS) -> pd.DataFrame:
    valid = y.notna()
    X = X.loc[valid].reset_index(drop=True)
    y_array = y.loc[valid].to_numpy(dtype=float)
    outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=repeats, random_state=INFERENCE_RANDOM_STATE)
    rows: list[dict[str, object]] = []
    for split_index, (train_idx, _) in enumerate(outer.split(X)):
        repeat = split_index // N_SPLITS + 1
        fold = split_index % N_SPLITS + 1
        model = _build_ridge_pipeline()
        model.fit(X.iloc[train_idx], y_array[train_idx])
        names = model.named_steps["imputer"].get_feature_names_out(X.columns.tolist())
        for term_name, coefficient in zip(names, model.named_steps["ridge"].coef_):
            rows.append(
                {
                    "domain": domain,
                    "target": DOMAINS[domain],
                    "repeat": repeat,
                    "fold": fold,
                    "term_name": str(term_name),
                    "coefficient": float(coefficient),
                    "ridge_alpha": float(model.named_steps["ridge"].alpha_),
                }
            )
    folds = pd.DataFrame(rows)
    summary_rows: list[dict[str, object]] = []
    for term_name, group in folds.groupby("term_name", sort=True):
        coefficients = pd.to_numeric(group["coefficient"], errors="coerce").dropna()
        positive = float((coefficients > 0).mean())
        negative = float((coefficients < 0).mean())
        summary_rows.append(
            {
                "domain": domain,
                "target": DOMAINS[domain],
                "term_name": term_name,
                "n_folds": len(coefficients),
                "coefficient_mean": float(coefficients.mean()),
                "coefficient_median": float(coefficients.median()),
                "coefficient_sd": float(coefficients.std(ddof=1)) if len(coefficients) > 1 else np.nan,
                "absolute_mean_coefficient": float(abs(coefficients.mean())),
                "mean_absolute_coefficient": float(coefficients.abs().mean()),
                "coefficient_positive_fraction": positive,
                "coefficient_negative_fraction": negative,
                "coefficient_direction_stability": max(positive, negative),
            }
        )
    return pd.DataFrame(summary_rows)


def _select_features(summary: pd.DataFrame, metadata: pd.DataFrame, inventory: pd.DataFrame, domain: str) -> pd.DataFrame:
    panel = set(inventory.loc[inventory["selected_for_panel"].astype(str).str.lower().eq("true"), "feature_name"].astype(str))
    eligible = summary[
        summary["domain"].eq(domain)
        & summary["term_name"].astype(str).isin(panel)
        & ~summary["term_name"].astype(str).str.startswith("missingindicator_")
    ].copy()
    eligible = eligible.merge(metadata, left_on="term_name", right_on="feature_name", how="left", suffixes=("", "_metadata"))
    eligible = eligible.sort_values(
        ["absolute_mean_coefficient", "coefficient_direction_stability", "term_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    eligible["ridge_rank_among_real_panel_features"] = np.arange(1, len(eligible) + 1)
    selected = eligible.head(TOP_N).copy()
    selected["feature_name"] = selected["term_name"]
    selected["selected_for_adjusted_domain_panel"] = True
    return selected


def _cluster_statistics(y: pd.Series, coordinates: np.ndarray, labels: np.ndarray) -> dict[str, object]:
    y = _numeric(y).reset_index(drop=True)
    frame = pd.DataFrame({"y": y, "PC1": coordinates[:, 0], "PC2": coordinates[:, 1], "cluster": labels})
    frame = frame.dropna(subset=["y", "PC1", "PC2"])
    left = frame.loc[frame["cluster"].eq(0), "y"]
    right = frame.loc[frame["cluster"].eq(1), "y"]
    pooled = ((len(left) - 1) * left.var(ddof=1) + (len(right) - 1) * right.var(ddof=1)) / (len(left) + len(right) - 2) if len(left) > 1 and len(right) > 1 else np.nan
    d = (right.mean() - left.mean()) / math.sqrt(pooled) if np.isfinite(pooled) and pooled > 0 else np.nan
    try:
        mw = float(mannwhitneyu(left, right, alternative="two-sided").pvalue) if len(left) >= 3 and len(right) >= 3 else np.nan
    except ValueError:
        mw = np.nan
    return {
        "n": int(len(frame)),
        "cluster_0_n": int(len(left)),
        "cluster_1_n": int(len(right)),
        "cluster_0_mean": float(left.mean()) if not left.empty else np.nan,
        "cluster_1_mean": float(right.mean()) if not right.empty else np.nan,
        "cluster_0_median_iqr": _format_median_iqr(left),
        "cluster_1_median_iqr": _format_median_iqr(right),
        "cluster_difference_cluster_1_minus_0": float(right.mean() - left.mean()) if not left.empty and not right.empty else np.nan,
        "standardized_difference_cluster_1_minus_0": float(d) if np.isfinite(d) else np.nan,
        "absolute_standardized_difference": float(abs(d)) if np.isfinite(d) else np.nan,
        "mann_whitney_exploratory_p_value": mw,
        "correlation_pc1": float(frame["PC1"].corr(frame["y"])) if len(frame) >= 3 else np.nan,
        "correlation_pc2": float(frame["PC2"].corr(frame["y"])) if len(frame) >= 3 else np.nan,
    }


def _fit_panel(adjusted: pd.DataFrame, dataset: pd.DataFrame, features: list[str], target: pd.Series) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, pd.DataFrame, dict[str, object]]:
    raw = adjusted[features].apply(pd.to_numeric, errors="coerce")
    availability = raw.notna().mean(axis=1)
    included = availability.ge(PATIENT_FEATURE_COVERAGE_THRESHOLD)
    raw_included = raw.loc[included].reset_index(drop=True)
    y = _numeric(target.loc[included]).reset_index(drop=True)
    scaled, transformations, _ = _prepare_feature_matrix(raw_included)
    pca = PCA(n_components=min(5, scaled.shape[0] - 1, scaled.shape[1]), random_state=INFERENCE_RANDOM_STATE)
    coordinates = pca.fit_transform(scaled)
    labels = KMeans(n_clusters=2, n_init=100, random_state=INFERENCE_RANDOM_STATE).fit_predict(coordinates)
    scores = dataset.loc[included, [ID_COLUMN, "Subject_ID_N"] + [column for pair in T1_T2_PAIRS.values() for column in pair if column in dataset.columns]].reset_index(drop=True).copy()
    scores[ID_COLUMN] = _normalize_id(scores[ID_COLUMN])
    scores["patient_feature_coverage_fraction"] = availability.loc[included].to_numpy()
    scores["cluster_label"] = labels
    scores["cluster_k"] = 2
    for index in range(coordinates.shape[1]):
        scores[f"PC{index + 1}"] = coordinates[:, index]
    quality = pd.DataFrame([_cluster_quality(coordinates, 2)])
    stats = _cluster_statistics(y, coordinates, labels)
    stats["source_patients"] = int(len(dataset))
    stats["analyzed_patients"] = int(included.sum())
    stats["excluded_for_panel_availability"] = int((~included).sum())
    stats["pc1_pc2_explained_variance_percent"] = float(pca.explained_variance_ratio_[:2].sum() * 100)
    stats["silhouette"] = float(silhouette_score(coordinates, labels))
    stats["subsample_ari"] = float(quality["mean_subsample_ari_vs_reference"].iloc[0])
    return scores, coordinates, labels, quality, stats


def _bootstrap_statistics(adjusted: pd.DataFrame, target: pd.Series, features: list[str], included: pd.Series) -> pd.DataFrame:
    raw = adjusted.loc[included, features].reset_index(drop=True)
    y = _numeric(target.loc[included]).reset_index(drop=True)
    rng = np.random.default_rng(INFERENCE_RANDOM_STATE + 5000)
    rows: list[dict[str, object]] = []
    for bootstrap in range(1, N_BOOTSTRAPS + 1):
        sample = rng.integers(0, len(raw), size=len(raw))
        sample_raw = raw.iloc[sample].reset_index(drop=True)
        sample_y = y.iloc[sample].reset_index(drop=True)
        scaled, _, _ = _prepare_feature_matrix(sample_raw)
        pca = PCA(n_components=min(3, scaled.shape[0] - 1, scaled.shape[1]), random_state=INFERENCE_RANDOM_STATE + bootstrap)
        coordinates = pca.fit_transform(scaled)
        labels = KMeans(n_clusters=2, n_init=50, random_state=INFERENCE_RANDOM_STATE + bootstrap).fit_predict(coordinates)
        stat = _cluster_statistics(sample_y, coordinates, labels)
        rows.append(
            {
                "bootstrap": bootstrap,
                "standardized_difference": stat["standardized_difference_cluster_1_minus_0"],
                "absolute_standardized_difference": stat["absolute_standardized_difference"],
                "correlation_pc1": stat["correlation_pc1"],
                "correlation_pc2": stat["correlation_pc2"],
            }
        )
    return pd.DataFrame(rows)


def _permutation_statistics(adjusted: pd.DataFrame, dataset: pd.DataFrame, target: pd.Series, metadata: pd.DataFrame, inventory: pd.DataFrame, candidate_features: list[str], domain: str, observed_abs_d: float) -> pd.DataFrame:
    valid = target.notna()
    X = adjusted.loc[valid].reset_index(drop=True)
    y = _numeric(target.loc[valid]).reset_index(drop=True)
    rng = np.random.default_rng(INFERENCE_RANDOM_STATE + 7000 + list(DOMAINS).index(domain))
    rows: list[dict[str, object]] = []
    for permutation in range(1, N_PERMUTATIONS + 1):
        shuffled = pd.Series(rng.permutation(y.to_numpy()), dtype=float)
        coefficient_summary = _coefficient_summary(X, shuffled, domain, repeats=PERMUTATION_REPEATS)
        selected = _select_features(coefficient_summary, metadata, inventory, domain)
        features = selected["feature_name"].astype(str).tolist()
        raw = X[features]
        included = raw.notna().mean(axis=1).ge(PATIENT_FEATURE_COVERAGE_THRESHOLD)
        scaled, _, _ = _prepare_feature_matrix(raw.loc[included].reset_index(drop=True))
        pca = PCA(n_components=min(3, scaled.shape[0] - 1, scaled.shape[1]), random_state=INFERENCE_RANDOM_STATE + permutation)
        coordinates = pca.fit_transform(scaled)
        labels = KMeans(n_clusters=2, n_init=50, random_state=INFERENCE_RANDOM_STATE + permutation).fit_predict(coordinates)
        stat = _cluster_statistics(shuffled.loc[included].reset_index(drop=True), coordinates, labels)
        rows.append(
            {
                "domain": domain,
                "permutation": permutation,
                "absolute_standardized_difference": stat["absolute_standardized_difference"],
                "correlation_pc1_absolute": abs(stat["correlation_pc1"]) if np.isfinite(stat["correlation_pc1"]) else np.nan,
                "correlation_pc2_absolute": abs(stat["correlation_pc2"]) if np.isfinite(stat["correlation_pc2"]) else np.nan,
                "analyzed_patients": int(included.sum()),
                "selected_features": ";".join(features),
                "exceeded_observed_absolute_d": bool(stat["absolute_standardized_difference"] >= observed_abs_d),
            }
        )
        if permutation % 10 == 0:
            print(f"{domain}: completed permutation {permutation}/{N_PERMUTATIONS}")
    result = pd.DataFrame(rows)
    result["observed_absolute_standardized_difference"] = observed_abs_d
    return result


def _feature_comparison(scores: pd.DataFrame, adjusted: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    frame = scores[[ID_COLUMN, "cluster_label"]].copy()
    frame = frame.join(adjusted.loc[_normalize_id(adjusted[ID_COLUMN]).isin(set(frame[ID_COLUMN]))].set_index(ID_COLUMN)[selected["feature_name"].tolist()], on=ID_COLUMN)
    rows: list[dict[str, object]] = []
    for _, feature in selected.iterrows():
        name = str(feature["feature_name"])
        left = _numeric(frame.loc[frame["cluster_label"].eq(0), name]).dropna()
        right = _numeric(frame.loc[frame["cluster_label"].eq(1), name]).dropna()
        rows.append(
            {
                "feature_name": name,
                "feature_family": feature.get("feature_family", ""),
                "source_table": feature.get("source_table", ""),
                "cluster_0_median_iqr": _format_median_iqr(left),
                "cluster_1_median_iqr": _format_median_iqr(right),
                "standardized_difference_cluster_1_minus_0": ((right.mean() - left.mean()) / math.sqrt(((len(left) - 1) * left.var(ddof=1) + (len(right) - 1) * right.var(ddof=1)) / (len(left) + len(right) - 2))) if len(left) > 1 and len(right) > 1 and ((len(left) - 1) * left.var(ddof=1) + (len(right) - 1) * right.var(ddof=1)) > 0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _run_domain(domain: str, dataset: pd.DataFrame, adjusted: pd.DataFrame, technical: pd.DataFrame, metadata: pd.DataFrame, inventory: pd.DataFrame, candidate_features: list[str]) -> dict[str, object]:
    domain_dir = OUTPUT_DIR / _slug(domain)
    domain_dir.mkdir(parents=True, exist_ok=True)
    target = _numeric(dataset[DOMAINS[domain]])
    coefficient_summary = _coefficient_summary(adjusted[candidate_features], target, domain)
    selected = _select_features(coefficient_summary, metadata, inventory, domain)
    selected.to_csv(domain_dir / "adjusted_feature_selection.csv", index=False)
    coefficient_summary.to_csv(domain_dir / "adjusted_ridge_coefficient_summary.csv", index=False)
    if len(selected) != TOP_N:
        raise RuntimeError(f"{domain} has fewer than five eligible adjusted features.")
    features = selected["feature_name"].astype(str).tolist()
    scores, coordinates, labels, quality, observed = _fit_panel(adjusted, dataset, features, target)
    scores.to_csv(domain_dir / "adjusted_pca_patient_scores.csv", index=False)
    quality.to_csv(domain_dir / "adjusted_cluster_quality.csv", index=False)
    transformations = pd.DataFrame()
    _, transformations, _ = _prepare_feature_matrix(adjusted.loc[adjusted[features].notna().mean(axis=1).ge(PATIENT_FEATURE_COVERAGE_THRESHOLD), features].reset_index(drop=True))
    transformations.to_csv(domain_dir / "adjusted_feature_transformations.csv", index=False)
    feature_comparison = _feature_comparison(scores, adjusted.assign(**{ID_COLUMN: _normalize_id(dataset[ID_COLUMN])}), selected)
    feature_comparison.to_csv(domain_dir / "adjusted_cluster_feature_comparison.csv", index=False)

    technical_domain = technical.merge(scores[[ID_COLUMN, "cluster_label"]], on=ID_COLUMN, how="inner")
    technical_domain.to_csv(domain_dir / "adjusted_technical_patient_audit.csv", index=False)
    technical_summary = _technical_comparison(technical_domain)
    technical_summary.to_csv(domain_dir / "adjusted_technical_confounding_comparison.csv", index=False)
    cognitive_points, cognitive_summary = _cognitive_overlay(dataset, scores)
    cognitive_points.to_csv(domain_dir / "adjusted_cognitive_overlay_points.csv", index=False)
    cognitive_summary.to_csv(domain_dir / "adjusted_cognitive_overlay_summary.csv", index=False)

    included = adjusted[features].notna().mean(axis=1).ge(PATIENT_FEATURE_COVERAGE_THRESHOLD) & target.notna()
    bootstrap = _bootstrap_statistics(adjusted, target, features, included)
    bootstrap.to_csv(domain_dir / "bootstrap_statistics.csv", index=False)
    for column in ["standardized_difference", "absolute_standardized_difference", "correlation_pc1", "correlation_pc2"]:
        observed[f"bootstrap_{column}_median"] = float(bootstrap[column].median())
        observed[f"bootstrap_{column}_ci_2_5"] = float(bootstrap[column].quantile(0.025))
        observed[f"bootstrap_{column}_ci_97_5"] = float(bootstrap[column].quantile(0.975))
    permutations = _permutation_statistics(adjusted[candidate_features], dataset, target, metadata, inventory, candidate_features, domain, float(observed["absolute_standardized_difference"]))
    permutations.to_csv(domain_dir / "selection_aware_permutation_statistics.csv", index=False)
    permutation_p = (1 + int(permutations["exceeded_observed_absolute_d"].sum())) / (len(permutations) + 1)
    observed["selection_aware_permutation_p_value"] = permutation_p
    observed["selection_aware_permutation_exceedances"] = int(permutations["exceeded_observed_absolute_d"].sum())
    observed["domain"] = domain
    observed["target"] = DOMAINS[domain]
    observed["selected_features"] = ";".join(features)
    observed_frame = pd.DataFrame([observed])
    observed_frame.to_csv(domain_dir / "adjusted_observed_statistics.csv", index=False)
    return observed


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={ID_COLUMN: str, "Subject_ID_N": str})
    dataset[ID_COLUMN] = _normalize_id(dataset[ID_COLUMN])
    metadata = pd.read_csv(METADATA_PATH, dtype=str).drop_duplicates("feature_name")
    inventory = pd.read_csv(PANEL_INVENTORY_PATH)
    candidate_features = _all_available_features(metadata, dataset)
    technical = _technical_frame(dataset, candidate_features)
    technical[ID_COLUMN] = _normalize_id(technical[ID_COLUMN])
    adjusted, adjustment_summary = _adjust_features(dataset, technical, candidate_features)
    adjusted.insert(0, ID_COLUMN, dataset[ID_COLUMN].to_numpy())
    adjustment_summary.to_csv(OUTPUT_DIR / "feature_adjustment_summary.csv", index=False)
    technical.to_csv(OUTPUT_DIR / "technical_patient_audit.csv", index=False)

    observed_rows = []
    for domain in DOMAINS:
        print(f"Running adjusted observed analysis for {domain}")
        observed_rows.append(_run_domain(domain, dataset, adjusted, technical, metadata, inventory, candidate_features))
    observed_summary = pd.DataFrame(observed_rows)
    observed_summary.to_csv(OUTPUT_DIR / "adjusted_inference_summary.csv", index=False)
    run_record = {
        "analysis_name": "pre-specified coverage-adjusted Motor and Attention inference",
        "original_outputs_changed": False,
        "domains": list(DOMAINS),
        "candidate_features": "all observed T1-week and adjusted-window Phase 11 features",
        "final_panel_restriction": "real features in the fixed 41-feature USML panel; missingness indicators excluded",
        "adjustment": "volume-like features divided by observed timestamp-span days; transformed observed values residualized against fixed collection-intensity and coverage variables",
        "technical_variables": TECHNICAL_COLUMNS,
        "ridge_selection": f"repeated {N_SPLITS}-fold cross-validation repeated {N_REPEATS} times, fold-local median imputation with missingness indicators, standardization, and inner-CV alpha selection",
        "pca_and_clustering": "separate PCA for each selected five-feature panel; fixed k=2 K-means; patients require at least 50% of selected feature values",
        "permutation": f"{N_PERMUTATIONS} permutations per domain; each permutation reruns Ridge feature selection, five-feature PCA, and fixed k=2 clustering",
        "bootstrap": f"{N_BOOTSTRAPS} resamples per domain conditional on the observed adjusted five-feature panel",
        "permutation_p_definition": "(1 + number of permuted absolute standardized differences at least as large as observed) / (1 + number of permutations)",
        "exploratory_only": True,
    }
    (OUTPUT_DIR / "adjusted_inference_run_record.json").write_text(json.dumps(run_record, indent=2), encoding="utf-8")
    readme = """# Pre-specified coverage-adjusted Motor and Attention inference

This separate sensitivity analysis tests whether the strongest Motor and Attention findings remain after reducing collection-intensity effects.

## Pre-specified workflow

1. Use the all-available Phase 11 T1 candidate feature catalog.
2. Divide volume-like features by each patient's observed timestamp-span exposure.
3. Residualize transformed observed feature values against observed timestamp span, total source rows, recorded table count, baseline feature missingness, baseline table coverage, and candidate-feature coverage. These technical variables never enter PCA or clustering directly.
4. Rank features separately for Motor T1 and Attention T1 using the same repeated 5-fold x20 Ridge coefficient procedure used in the domain-specific USML analysis. Restrict the final five features to real features in the fixed 41-feature USML panel.
5. Fit a separate PCA and fixed k=2 K-means solution for each adjusted five-feature panel.
6. Permute each cognitive outcome 100 times. For every permutation, repeat Ridge feature selection, select a new five-feature panel, refit PCA, refit k=2 K-means, and calculate the absolute cluster standardized difference. The calibrated p-value compares the observed effect with this selection-aware null distribution.
7. Bootstrap the observed adjusted five-feature panel 1,000 times to report variability intervals for the cluster effect and PCA correlations.

## Interpretation boundary

The permutation p-value is more honest than the original post-selection p-value because it repeats the outcome-informed selection process under a null outcome. It is still exploratory, limited by the small cohort and 100-permutation Monte Carlo resolution, and does not establish clinical validity. Bootstrap intervals are sampling-variability summaries, not independent validation intervals.

The original USML, domain-specific USML, and all earlier outputs are unchanged.
"""
    (OUTPUT_DIR / "README_adjusted_inference.md").write_text(readme, encoding="utf-8")
    print(observed_summary[["domain", "selected_features", "standardized_difference_cluster_1_minus_0", "selection_aware_permutation_p_value", "bootstrap_standardized_difference_ci_2_5", "bootstrap_standardized_difference_ci_97_5"]].round(4).to_string(index=False))
    print(f"outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
