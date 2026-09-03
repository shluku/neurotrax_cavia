"""Coverage-adjusted sensitivity audit for the fixed median-span PCA result.

The original unsupervised PCA and cluster assignments are never overwritten.
This run keeps the original 76-patient comparison cohort and evaluates whether
the digital structure survives adjustments for observed recording exposure and
technical data-quality variables. Cognitive outcomes are post-hoc only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import RobustScaler

from unsupervised_phenotyping_posthoc import _normalize_id, _technical_patient_table


ROOT = Path(__file__).parent
BASE_DIR = ROOT / "output/analysis_candidates/phase11_t1_baseline"
SPAN_DIR = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline"
UNSUPERVISED_DIR = ROOT / "output/analysis_candidates/unsupervised_phenotyping_median_span"
PANEL_DIR = UNSUPERVISED_DIR / "usable_catalog_50pct"
OUTPUT_DIR = UNSUPERVISED_DIR / "coverage_adjusted_posthoc"

DATASET_PATH = BASE_DIR / "phase11_t1_baseline_patient_dataset.csv"
METADATA_PATH = BASE_DIR / "phase11_t1_baseline_feature_metadata.csv"
STATUS_PATH = SPAN_DIR / "phase11_midpoint_t1_baseline_patient_table_status.csv"
COVERAGE_PATH = SPAN_DIR / "phase11_midpoint_t1_baseline_coverage.csv"
ORIGINAL_SCORES_PATH = PANEL_DIR / "pca_patient_scores.csv"
ORIGINAL_LOADINGS_PATH = PANEL_DIR / "pca_loadings.csv"
INVENTORY_PATH = PANEL_DIR / "feature_inventory.csv"

ID_COLUMN = "Subject_ID_D"
CLUSTER_COLUMN = "cluster_label"
RANDOM_STATE = 20260830
N_PCS = 10
N_SEEDS = 20
N_RESAMPLES = 100

TECHNICAL_VARIABLES = [
    "observed_timestamp_span_days",
    "total_rows_in_window",
    "mean_rows_per_calculated_table",
    "recorded_table_count",
    "tables_without_data",
    "table_status_error_or_retry_count",
    "patient_feature_coverage_percent",
    "baseline_feature_missing_percent",
    "baseline_table_coverage_percent",
    "n_devices_available",
    "n_devices_used",
]

COGNITIVE_OUTCOMES = [
    ("Global T1", "global_T1", "baseline"),
    ("Global T2", "global_T2", "follow-up"),
    ("Global T2-T1 delta", "global_delta", "change"),
    ("Memory T2-T1 delta", "memory_delta", "change"),
    ("Attention T2-T1 delta", "attention_delta", "change"),
    ("Executive function T2-T1 delta", "ef_delta", "change"),
    ("Processing speed T2-T1 delta", "processing_speed_delta", "change"),
    ("Motor T2-T1 delta", "motor_delta", "change"),
    ("Verbal T2-T1 delta", "verbal_delta", "change"),
    ("IQ T2-T1 delta", "iq_delta", "change"),
]

VARIANT_DEFINITIONS = {
    "raw_reference": {
        "label": "Original processing reference",
        "description": "Same feature cohort and preprocessing logic as the original usable-catalog PCA; no adjustment.",
    },
    "exposure_normalized": {
        "label": "Exposure-normalized features",
        "description": "Volume-like features are divided by observed recording-span days before the original transform and scaling steps.",
    },
    "technical_residualized": {
        "label": "Technical-residualized features",
        "description": "The transformed feature values are residualized against observed span, source rows, feature coverage, missingness, and table coverage.",
    },
    "quality_trimmed": {
        "label": "Quality-trimmed reference",
        "description": "The original processing is rerun after removing patients in the extreme 5% tails of available quality/intensity variables.",
    },
}


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _median_iqr(values: pd.Series) -> str:
    numeric = _numeric(values).dropna()
    if numeric.empty:
        return "NA"
    return f"{numeric.median():.2f} ({numeric.quantile(.25):.2f}-{numeric.quantile(.75):.2f})"


def _standardized_difference(left: pd.Series, right: pd.Series) -> float:
    left = _numeric(left).dropna()
    right = _numeric(right).dropna()
    if len(left) < 2 or len(right) < 2:
        return np.nan
    pooled_variance = (
        (len(left) - 1) * left.var(ddof=1) + (len(right) - 1) * right.var(ddof=1)
    ) / (len(left) + len(right) - 2)
    if not np.isfinite(pooled_variance) or pooled_variance <= 0:
        return np.nan
    return float((right.mean() - left.mean()) / math.sqrt(pooled_variance))


def _mw_p_value(left: pd.Series, right: pd.Series) -> float:
    left = _numeric(left).dropna()
    right = _numeric(right).dropna()
    if len(left) < 3 or len(right) < 3:
        return np.nan
    try:
        return float(mannwhitneyu(left, right, alternative="two-sided").pvalue)
    except ValueError:
        return np.nan


def _fdr_bh(values: pd.Series) -> pd.Series:
    numeric = _numeric(values)
    result = pd.Series(np.nan, index=values.index, dtype=float)
    valid = numeric.notna()
    if not valid.any():
        return result
    p = numeric.loc[valid].to_numpy(dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    restored = np.empty_like(adjusted)
    restored[order] = np.minimum(adjusted, 1.0)
    result.loc[valid] = restored
    return result


def _is_fraction_like(feature: str) -> bool:
    lowered = feature.lower()
    return any(token in lowered for token in ("fraction", "ratio", "diversity"))


def _is_volume_like(feature: str) -> bool:
    """Identify features whose accumulated value can reasonably be exposure-adjusted."""
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


def _transform_and_impute(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    transformed = pd.DataFrame(index=raw.index)
    rows: list[dict[str, object]] = []
    for feature in raw.columns:
        values = _numeric(raw[feature])
        valid = values.dropna()
        transformation = "none"
        if (
            not valid.empty
            and (valid >= 0).all()
            and not _is_fraction_like(feature)
            and valid.nunique() > 1
            and abs(float(valid.skew())) > 1.5
        ):
            transformed[feature] = np.log1p(values)
            transformation = "log1p_nonnegative_skewed"
        else:
            transformed[feature] = values
        rows.append(
            {
                "feature_name": feature,
                "transformation": transformation,
                "observed_before_imputation": int(valid.size),
                "missing_percent_before_imputation": float(values.isna().mean() * 100),
            }
        )
    medians = transformed.median(numeric_only=True)
    imputed = transformed.fillna(medians).fillna(0.0)
    records = pd.DataFrame(rows)
    records["imputation_value_after_transformation"] = records["feature_name"].map(medians).fillna(0.0)
    return imputed, records


def _robust_scale(values: pd.DataFrame) -> np.ndarray:
    return RobustScaler(quantile_range=(25.0, 75.0)).fit_transform(values.to_numpy(dtype=float))


def _prepare_variant(
    raw: pd.DataFrame,
    technical: pd.DataFrame,
    variant: str,
    feature_names: list[str],
) -> tuple[np.ndarray, pd.DataFrame, pd.DataFrame]:
    working = raw.copy()
    transformation_note = ""
    if variant == "exposure_normalized":
        exposure = _numeric(technical["observed_timestamp_span_days"])
        fallback = _numeric(technical["configured_endpoint_interval_days"])
        exposure = exposure.where(exposure.gt(0), fallback)
        exposure = exposure.where(exposure.gt(0), 1.0).fillna(1.0)
        for feature in feature_names:
            if _is_volume_like(feature):
                working[feature] = _numeric(working[feature]) / exposure.to_numpy()
        transformation_note = "volume-like features divided by observed recording-span days"

    transformed, records = _transform_and_impute(working)
    if variant == "technical_residualized":
        technical_columns = [
            "observed_timestamp_span_days",
            "total_rows_in_window",
            "patient_feature_coverage_percent",
            "baseline_feature_missing_percent",
            "baseline_table_coverage_percent",
        ]
        design_parts = [np.ones(len(technical))]
        for column in technical_columns:
            values = _numeric(technical[column]).replace([np.inf, -np.inf], np.nan)
            values = values.fillna(values.median()).fillna(0.0)
            if column in {"observed_timestamp_span_days", "total_rows_in_window"}:
                values = np.log1p(values.clip(lower=0))
            design_parts.append(values.to_numpy(dtype=float))
        design = np.column_stack(design_parts)
        residualized = pd.DataFrame(index=transformed.index)
        for feature in feature_names:
            values = transformed[feature].to_numpy(dtype=float)
            coefficients, *_ = np.linalg.lstsq(design, values, rcond=None)
            residualized[feature] = values - design @ coefficients
        transformed = residualized
        records["transformation"] = records["transformation"].astype(str) + "; technical_residualized"
        transformation_note = "transformed values residualized against five technical variables"
    elif variant == "exposure_normalized":
        records["transformation"] = records["transformation"].astype(str) + "; exposure_normalized"
    else:
        transformation_note = "original feature processing"

    records["variant"] = variant
    records["variant_note"] = transformation_note
    return _robust_scale(transformed), records, transformed


def _quality_trim_mask(technical: pd.DataFrame) -> pd.Series:
    variables = [
        "observed_timestamp_span_days",
        "total_rows_in_window",
        "patient_feature_coverage_percent",
        "baseline_table_coverage_percent",
    ]
    mask = pd.Series(True, index=technical.index)
    for variable in variables:
        values = _numeric(technical[variable])
        finite = values.replace([np.inf, -np.inf], np.nan).dropna()
        if len(finite) < 12:
            continue
        low, high = finite.quantile([0.05, 0.95])
        mask &= values.ge(low) & values.le(high)
    return mask.fillna(False)


def _cluster_quality(scores: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    if len(np.unique(labels)) < 2:
        return {"mean_silhouette": np.nan, "mean_subsample_ari": np.nan, "mean_seed_ari": np.nan}
    silhouettes: list[float] = []
    seed_labels: list[np.ndarray] = []
    for offset in range(N_SEEDS):
        candidate = KMeans(n_clusters=2, n_init=50, random_state=RANDOM_STATE + offset).fit_predict(scores)
        seed_labels.append(candidate)
        silhouettes.append(float(silhouette_score(scores, candidate)))
    seed_ari = [
        adjusted_rand_score(seed_labels[left], seed_labels[right])
        for left in range(len(seed_labels))
        for right in range(left + 1, len(seed_labels))
    ]
    rng = np.random.default_rng(RANDOM_STATE + 99)
    reference = seed_labels[0]
    sample_size = max(6, int(round(len(scores) * 0.80)))
    resample_ari: list[float] = []
    for _ in range(N_RESAMPLES):
        indices = rng.choice(len(scores), size=sample_size, replace=False)
        model = KMeans(n_clusters=2, n_init=25, random_state=int(rng.integers(0, 2**31 - 1))).fit(scores[indices])
        resample_ari.append(float(adjusted_rand_score(reference, model.predict(scores))))
    return {
        "mean_silhouette": float(np.mean(silhouettes)),
        "mean_subsample_ari": float(np.mean(resample_ari)),
        "mean_seed_ari": float(np.mean(seed_ari)),
    }


def _compare_clusters(frame: pd.DataFrame, variable: str) -> dict[str, object]:
    left = _numeric(frame.loc[frame[CLUSTER_COLUMN].eq(0), variable]).dropna()
    right = _numeric(frame.loc[frame[CLUSTER_COLUMN].eq(1), variable]).dropna()
    return {
        "n_cluster_0": int(len(left)),
        "n_cluster_1": int(len(right)),
        "cluster_0_mean": float(left.mean()) if not left.empty else np.nan,
        "cluster_1_mean": float(right.mean()) if not right.empty else np.nan,
        "cluster_0_median_iqr": _median_iqr(left),
        "cluster_1_median_iqr": _median_iqr(right),
        "cluster_difference_cluster_1_minus_0": float(right.mean() - left.mean()) if not left.empty and not right.empty else np.nan,
        "standardized_difference_cluster_1_minus_0": _standardized_difference(left, right),
        "exploratory_p_value": _mw_p_value(left, right),
    }


def _technical_comparison(frame: pd.DataFrame, variant: str, variant_label: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    descriptions = {
        "observed_timestamp_span_days": "Earliest-to-latest observed timestamp span; not continuous recording time.",
        "total_rows_in_window": "Total source rows across the midpoint span; a collection-intensity proxy.",
        "mean_rows_per_calculated_table": "Mean source rows per calculated table.",
        "recorded_table_count": "Number of tables with a calculated result.",
        "tables_without_data": "Number of source tables with no rows in the span.",
        "table_status_error_or_retry_count": "Number of tables without a calculated result.",
        "patient_feature_coverage_percent": "Observed fraction of the fixed 41-feature panel.",
        "baseline_feature_missing_percent": "Missingness across the extracted baseline catalog.",
        "baseline_table_coverage_percent": "Fraction of baseline tables with a calculated value.",
        "n_devices_available": "Number of distinct available devices; identifiers are not used.",
        "n_devices_used": "Number of distinct devices used by calculated tables.",
    }
    for variable in TECHNICAL_VARIABLES:
        if variable not in frame.columns:
            continue
        row = {
            "variant": variant,
            "variant_label": variant_label,
            "variable": variable,
            "description": descriptions.get(variable, variable),
        }
        row.update(_compare_clusters(frame, variable))
        rows.append(row)
    result = pd.DataFrame(rows)
    if not result.empty:
        result["absolute_standardized_difference"] = result["standardized_difference_cluster_1_minus_0"].abs()
        result["exploratory_q_value_fdr_bh"] = _fdr_bh(result["exploratory_p_value"])
        result = result.sort_values("absolute_standardized_difference", ascending=False)
    return result


def _cognitive_outputs(frame: pd.DataFrame, variant: str, variant_label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = frame.copy()
    pairs = {
        "global_delta": ("global_T1", "global_T2"),
        "memory_delta": ("memory_T1", "memory_T2"),
        "attention_delta": ("attention_T1", "attention_T2"),
        "ef_delta": ("ef_T1", "ef_T2"),
        "processing_speed_delta": ("processing_speed_T1", "processing_speed_T2"),
        "motor_delta": ("motor_T1", "motor_T2"),
        "verbal_delta": ("verbal_T1", "verbal_T2"),
        "iq_delta": ("iq_T1", "iq_T2"),
    }
    for delta, (t1, t2) in pairs.items():
        frame[delta] = _numeric(frame.get(t2, pd.Series(np.nan, index=frame.index))) - _numeric(frame.get(t1, pd.Series(np.nan, index=frame.index)))

    point_rows: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []
    for label, column, outcome_type in COGNITIVE_OUTCOMES:
        if column not in frame.columns:
            continue
        subset = frame[[ID_COLUMN, CLUSTER_COLUMN, "PC1", "PC2", column]].copy()
        subset = subset.rename(columns={column: "outcome_value"}).dropna()
        if subset.empty:
            continue
        subset["variant"] = variant
        subset["variant_label"] = variant_label
        subset["outcome"] = label
        subset["outcome_column"] = column
        subset["outcome_type"] = outcome_type
        point_rows.append(subset)
        comparison = _compare_clusters(subset, "outcome_value")
        summary_rows.append(
            {
                "variant": variant,
                "variant_label": variant_label,
                "outcome": label,
                "outcome_column": column,
                "outcome_type": outcome_type,
                "n": int(len(subset)),
                "correlation_pc1": float(subset["PC1"].corr(subset["outcome_value"])) if len(subset) >= 3 else np.nan,
                "correlation_pc2": float(subset["PC2"].corr(subset["outcome_value"])) if len(subset) >= 3 else np.nan,
                **comparison,
            }
        )
    points = pd.concat(point_rows, ignore_index=True) if point_rows else pd.DataFrame()
    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        summary["exploratory_q_value_fdr_bh"] = summary.groupby("variant")["exploratory_p_value"].transform(_fdr_bh)
        summary["interpretation_note"] = np.where(
            summary["outcome_type"].eq("change"),
            "Negative delta means lower T2 than T1; exploratory only.",
            "Post-hoc observed score; exploratory only.",
        )
    return points, summary


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={ID_COLUMN: str, "Subject_ID_N": str})
    dataset[ID_COLUMN] = _normalize_id(dataset[ID_COLUMN])
    inventory = pd.read_csv(INVENTORY_PATH)
    features = inventory[inventory["selected_for_panel"].astype(str).str.lower().eq("true")]["feature_name"].astype(str).tolist()
    if len(features) < 2:
        raise RuntimeError("The fixed usable-catalog feature inventory is unavailable.")

    original_scores = pd.read_csv(ORIGINAL_SCORES_PATH, dtype={ID_COLUMN: str})
    original_scores[ID_COLUMN] = _normalize_id(original_scores[ID_COLUMN])
    original_scores[CLUSTER_COLUMN] = pd.to_numeric(original_scores[CLUSTER_COLUMN], errors="coerce").astype("Int64")
    original_scores = original_scores.dropna(subset=[ID_COLUMN, CLUSTER_COLUMN]).copy()
    cohort = original_scores[[ID_COLUMN]].merge(dataset, on=ID_COLUMN, how="left", validate="one_to_one")
    cohort = cohort.dropna(subset=features, how="all").reset_index(drop=True)

    status = pd.read_csv(STATUS_PATH, dtype={ID_COLUMN: str})
    coverage = pd.read_csv(COVERAGE_PATH, dtype={ID_COLUMN: str})
    technical = _technical_patient_table(status, coverage)
    technical[ID_COLUMN] = _normalize_id(technical[ID_COLUMN])
    technical = technical.merge(cohort[[ID_COLUMN]], on=ID_COLUMN, how="right")
    technical = technical.merge(
        cohort[[ID_COLUMN, "baseline_feature_missing_fraction", "baseline_table_coverage_fraction"]],
        on=ID_COLUMN,
        how="left",
    )
    raw_panel = cohort[features].apply(pd.to_numeric, errors="coerce")
    technical["patient_feature_coverage_percent"] = raw_panel.notna().mean(axis=1).to_numpy() * 100
    technical["baseline_feature_missing_percent"] = _numeric(technical["baseline_feature_missing_fraction"]) * 100
    technical["baseline_table_coverage_percent"] = _numeric(technical["baseline_table_coverage_fraction"]) * 100
    technical.drop(columns=["baseline_feature_missing_fraction", "baseline_table_coverage_fraction"], inplace=True, errors="ignore")
    technical = technical.fillna({column: technical[column].median() for column in technical.columns if column != ID_COLUMN})

    original_aligned = original_scores.set_index(ID_COLUMN).reindex(cohort[ID_COLUMN]).reset_index()
    original_reference = original_aligned[[ID_COLUMN, CLUSTER_COLUMN, "PC1", "PC2"]].copy()
    original_loadings = pd.read_csv(ORIGINAL_LOADINGS_PATH)
    quality_trim_mask = _quality_trim_mask(technical)
    pd.DataFrame({ID_COLUMN: cohort[ID_COLUMN], "included_in_quality_trimmed_variant": quality_trim_mask}).to_csv(
        OUTPUT_DIR / "quality_trimmed_patient_audit.csv", index=False
    )

    all_variant_rows: list[dict[str, object]] = []
    all_technical: list[pd.DataFrame] = []
    all_cognitive_points: list[pd.DataFrame] = []
    all_cognitive_summary: list[pd.DataFrame] = []

    for variant, definition in VARIANT_DEFINITIONS.items():
        if variant == "quality_trimmed":
            variant_mask = quality_trim_mask.to_numpy(dtype=bool)
        else:
            variant_mask = np.ones(len(cohort), dtype=bool)
        if int(variant_mask.sum()) < 12:
            all_variant_rows.append(
                {
                    "variant": variant,
                    "variant_label": definition["label"],
                    "status": "not_run_fewer_than_12_patients",
                    "n_patients": int(variant_mask.sum()),
                }
            )
            continue

        variant_raw = raw_panel.loc[variant_mask].reset_index(drop=True)
        variant_technical = technical.loc[variant_mask].reset_index(drop=True)
        variant_cohort = cohort.loc[variant_mask].reset_index(drop=True)
        scaled, transformations, transformed = _prepare_variant(variant_raw, variant_technical, variant, features)
        n_pcs = min(N_PCS, scaled.shape[0] - 1, scaled.shape[1])
        pca = PCA(n_components=n_pcs, random_state=RANDOM_STATE)
        coordinates = pca.fit_transform(scaled)
        pc_columns = [f"PC{i}" for i in range(1, n_pcs + 1)]
        model = KMeans(n_clusters=2, n_init=100, random_state=RANDOM_STATE)
        labels = model.fit_predict(coordinates)
        quality = _cluster_quality(coordinates, labels)

        scores = variant_cohort[[ID_COLUMN, "global_T1", "memory_T1", "ef_T1", "processing_speed_T1", "attention_T1", "motor_T1"]].copy()
        scores[CLUSTER_COLUMN] = labels
        for index, column in enumerate(pc_columns):
            scores[column] = coordinates[:, index]
        scores["variant"] = variant
        scores["variant_label"] = definition["label"]
        scores["patient_feature_coverage_percent"] = variant_technical["patient_feature_coverage_percent"].to_numpy()
        scores["observed_timestamp_span_days"] = variant_technical["observed_timestamp_span_days"].to_numpy()
        scores.to_csv(OUTPUT_DIR / f"pca_patient_scores_{variant}.csv", index=False)

        loadings = pd.DataFrame(pca.components_.T, columns=pc_columns)
        loadings.insert(0, "feature_name", features)
        loadings["variant"] = variant
        loadings["variant_label"] = definition["label"]
        loadings["maximum_absolute_loading"] = loadings[pc_columns].abs().max(axis=1)
        loadings = loadings.sort_values("maximum_absolute_loading", ascending=False)
        loadings.to_csv(OUTPUT_DIR / f"pca_loadings_{variant}.csv", index=False)
        transformations.to_csv(OUTPUT_DIR / f"feature_transformations_{variant}.csv", index=False)

        aligned_original = original_reference.set_index(ID_COLUMN).reindex(variant_cohort[ID_COLUMN]).reset_index()
        ari_original = float(adjusted_rand_score(aligned_original[CLUSTER_COLUMN], labels))
        pc1_corr = abs(float(pd.Series(coordinates[:, 0]).corr(pd.to_numeric(aligned_original["PC1"], errors="coerce"))))
        pc2_corr = abs(float(pd.Series(coordinates[:, 1]).corr(pd.to_numeric(aligned_original["PC2"], errors="coerce"))))
        variance = pca.explained_variance_ratio_
        variant_summary = {
            "variant": variant,
            "variant_label": definition["label"],
            "description": definition["description"],
            "status": "completed",
            "n_patients": int(len(variant_cohort)),
            "n_features": int(len(features)),
            "pc1_pc2_explained_variance_percent": float(variance[:2].sum() * 100),
            "cluster_0_n": int((labels == 0).sum()),
            "cluster_1_n": int((labels == 1).sum()),
            "mean_silhouette": quality["mean_silhouette"],
            "mean_subsample_ari": quality["mean_subsample_ari"],
            "mean_seed_ari": quality["mean_seed_ari"],
            "ari_vs_original_clusters": ari_original,
            "absolute_pc1_correlation_with_original": pc1_corr,
            "absolute_pc2_correlation_with_original": pc2_corr,
        }
        all_variant_rows.append(variant_summary)

        technical_frame = variant_technical.copy()
        technical_frame[CLUSTER_COLUMN] = labels
        technical_frame["PC1"] = coordinates[:, 0]
        technical_frame["PC2"] = coordinates[:, 1]
        all_technical.append(_technical_comparison(technical_frame, variant, definition["label"]))

        cognitive_frame = variant_cohort.copy()
        cognitive_frame[CLUSTER_COLUMN] = labels
        cognitive_frame["PC1"] = coordinates[:, 0]
        cognitive_frame["PC2"] = coordinates[:, 1]
        points, cognitive_summary = _cognitive_outputs(cognitive_frame, variant, definition["label"])
        if not points.empty:
            all_cognitive_points.append(points)
        if not cognitive_summary.empty:
            all_cognitive_summary.append(cognitive_summary)

    variant_summary_frame = pd.DataFrame(all_variant_rows)
    variant_summary_frame.to_csv(OUTPUT_DIR / "variant_summary.csv", index=False)
    technical_frame = pd.concat(all_technical, ignore_index=True) if all_technical else pd.DataFrame()
    technical_frame.to_csv(OUTPUT_DIR / "technical_confounding_by_variant.csv", index=False)
    cognitive_points = pd.concat(all_cognitive_points, ignore_index=True) if all_cognitive_points else pd.DataFrame()
    cognitive_points.to_csv(OUTPUT_DIR / "cognitive_overlay_points_by_variant.csv", index=False)
    cognitive_summary = pd.concat(all_cognitive_summary, ignore_index=True) if all_cognitive_summary else pd.DataFrame()
    cognitive_summary.to_csv(OUTPUT_DIR / "cognitive_overlay_summary_by_variant.csv", index=False)

    run_record = {
        "original_pca_and_cluster_outputs_changed": False,
        "reference_scores": str(ORIGINAL_SCORES_PATH.relative_to(ROOT)),
        "feature_panel": "usable_catalog_50pct fixed selected features",
        "feature_count": int(len(features)),
        "reference_patient_count": int(len(cohort)),
        "quality_trimmed_patient_count": int(quality_trim_mask.sum()),
        "quality_trim_rule": "retain patients within the 5th to 95th percentile for observed span, total rows, panel coverage, and baseline table coverage",
        "exposure_denominator": "observed timestamp span days; configured endpoint interval used only as fallback",
        "volume_like_feature_rule": "count, unique, event-count, transition-count, distance, and duration features; fractions, ratios, diversity, and timing features are not divided",
        "technical_residualization_variables": [
            "observed_timestamp_span_days",
            "total_rows_in_window",
            "patient_feature_coverage_percent",
            "baseline_feature_missing_percent",
            "baseline_table_coverage_percent",
        ],
        "cognitive_variables_used_to_define_pca_or_clusters": False,
        "exploratory_p_values_only": True,
        "variants": list(VARIANT_DEFINITIONS),
    }
    (OUTPUT_DIR / "coverage_adjusted_run_record.json").write_text(json.dumps(run_record, indent=2), encoding="utf-8")

    readme = f"""# Coverage-adjusted PCA sensitivity audit

This is a separate post-hoc sensitivity analysis of the fixed median-timespan baseline cohort. The original PCA coordinates and cluster assignments in `usable_catalog_50pct` are unchanged.

## Question

Does the observed digital-behavior structure survive when differences in observed recording exposure and data quality are reduced, or is it mainly a measurement-intensity pattern?

## Fixed comparison design

- The same fixed usable-catalog feature panel is used in every variant ({len(features)} features).
- The original reference cohort is retained for direct comparison ({len(cohort)} patients).
- Cognitive scores are never used to recompute PCA or clustering.
- Each variant uses two clusters so the comparison remains aligned with the original two-cluster result.
- All p-values are exploratory and not confirmatory evidence.

## Variants

- **Original processing reference:** reproduces the existing feature transformation, median imputation, robust scaling, PCA, and two-cluster analysis.
- **Exposure-normalized features:** volume-like features are divided by observed timestamp-span days. This reduces the effect of longer observed windows but may also remove genuine duration-related behavior.
- **Technical-residualized features:** transformed features are residualized against observed span, source-row intensity, feature coverage, feature missingness, and table coverage. This is a stronger sensitivity analysis and can remove real behavior if behavior and recording intensity are correlated.
- **Quality-trimmed reference:** removes patients in the extreme 5% tails of the available quality/intensity variables before rerunning the original processing.

## Interpretation

Evidence for a more genuine behavioral structure would be persistence of PCA alignment, feature loadings, cluster stability, and cognitive overlays after adjustment. If the structure changes substantially, the original result should be described as potentially driven by coverage or collection intensity. This analysis cannot prove causality or clinical validity.

The technical and cognitive analyses are post-hoc. The cognitive delta is defined as T2 minus T1, so negative values indicate lower T2 than T1.
"""
    (OUTPUT_DIR / "README_coverage_adjusted_pca.md").write_text(readme, encoding="utf-8")
    print(variant_summary_frame.round(4).to_string(index=False))
    print(f"outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
