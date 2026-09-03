"""Post-hoc characterization of the fixed median-span unsupervised solution.

This script deliberately does not recompute PCA or clustering. It consumes the
existing usable_catalog_50pct patient coordinates and cluster labels, then
describes digital features, technical coverage variables, and cognitive
outcomes. Cognitive outcomes are post-hoc and are never used as clustering
inputs.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu


ROOT = Path(__file__).parent
BASE_DIR = ROOT / "output/analysis_candidates/phase11_t1_baseline"
SPAN_DIR = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline"
UNSUPERVISED_DIR = ROOT / "output/analysis_candidates/unsupervised_phenotyping_median_span"
PANEL_DIR = UNSUPERVISED_DIR / "usable_catalog_50pct"
OUTPUT_DIR = UNSUPERVISED_DIR / "posthoc"

DATASET_PATH = BASE_DIR / "phase11_t1_baseline_patient_dataset.csv"
METADATA_PATH = BASE_DIR / "phase11_t1_baseline_feature_metadata.csv"
STATUS_PATH = SPAN_DIR / "phase11_midpoint_t1_baseline_patient_table_status.csv"
COVERAGE_PATH = SPAN_DIR / "phase11_midpoint_t1_baseline_coverage.csv"
SCORES_PATH = PANEL_DIR / "pca_patient_scores.csv"
LOADINGS_PATH = PANEL_DIR / "pca_loadings.csv"
INVENTORY_PATH = PANEL_DIR / "feature_inventory.csv"

ID_COLUMN = "Subject_ID_D"
CLUSTER_COLUMN = "cluster_label"

CATEGORICAL_FEATURE_GROUPS = {
    "Circadian": ("night_", "active_hour", "session_duration"),
    "Messaging": ("message",),
    "Keyboard": ("keyboard",),
    "App activity": ("app_", "foreground_app", "unique_foreground"),
    "Touch": ("touch",),
    "Screen": ("screen", "unlocked_session", "night_screen"),
    "Mobility/activity": (
        "activity_",
        "significant_",
        "location_",
        "gsm_",
        "unique_gsm",
        "telephony_",
    ),
}

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


def _normalize_id(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    normalized = values.astype(str).str.strip()
    numeric_mask = numeric.notna()
    normalized.loc[numeric_mask] = numeric.loc[numeric_mask].round().astype(int).astype(str)
    return normalized.str.zfill(3)


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _median_iqr(values: pd.Series) -> str:
    values = _numeric(values).dropna()
    if values.empty:
        return "NA"
    return f"{values.median():.2f} ({values.quantile(.25):.2f}-{values.quantile(.75):.2f})"


def _standardized_difference(cluster_0: pd.Series, cluster_1: pd.Series) -> float:
    left = _numeric(cluster_0).dropna()
    right = _numeric(cluster_1).dropna()
    if len(left) < 2 or len(right) < 2:
        return float("nan")
    pooled_variance = (
        (len(left) - 1) * left.var(ddof=1) + (len(right) - 1) * right.var(ddof=1)
    ) / (len(left) + len(right) - 2)
    if not np.isfinite(pooled_variance) or pooled_variance <= 0:
        return float("nan")
    return float((right.mean() - left.mean()) / math.sqrt(pooled_variance))


def _mw_p_value(cluster_0: pd.Series, cluster_1: pd.Series) -> float:
    left = _numeric(cluster_0).dropna()
    right = _numeric(cluster_1).dropna()
    if len(left) < 3 or len(right) < 3 or left.nunique() == 1 and right.nunique() == 1:
        return float("nan")
    try:
        return float(mannwhitneyu(left, right, alternative="two-sided").pvalue)
    except ValueError:
        return float("nan")


def _fdr_bh(values: pd.Series) -> pd.Series:
    """Benjamini-Hochberg q-values while retaining missing p-values."""
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
    adjusted = np.minimum(adjusted, 1.0)
    restored = np.empty_like(adjusted)
    restored[order] = adjusted
    result.loc[valid] = restored
    return result


def _feature_group(feature_name: str, source_table: str = "") -> str:
    lowered = f"{feature_name} {source_table}".lower()
    for group, tokens in CATEGORICAL_FEATURE_GROUPS.items():
        if any(token in lowered for token in tokens):
            return group
    return "Other digital activity"


def _cluster_comparison(frame: pd.DataFrame, variable: str) -> dict[str, object]:
    left = frame.loc[frame[CLUSTER_COLUMN].eq(0), variable]
    right = frame.loc[frame[CLUSTER_COLUMN].eq(1), variable]
    left_num = _numeric(left).dropna()
    right_num = _numeric(right).dropna()
    return {
        "n_cluster_0": int(len(left_num)),
        "n_cluster_1": int(len(right_num)),
        "cluster_0_mean": float(left_num.mean()) if not left_num.empty else np.nan,
        "cluster_1_mean": float(right_num.mean()) if not right_num.empty else np.nan,
        "cluster_0_median": float(left_num.median()) if not left_num.empty else np.nan,
        "cluster_1_median": float(right_num.median()) if not right_num.empty else np.nan,
        "cluster_0_median_iqr": _median_iqr(left_num),
        "cluster_1_median_iqr": _median_iqr(right_num),
        "cluster_0_sd": float(left_num.std(ddof=1)) if len(left_num) > 1 else np.nan,
        "cluster_1_sd": float(right_num.std(ddof=1)) if len(right_num) > 1 else np.nan,
        "cluster_difference_cluster_1_minus_0": (
            float(right_num.mean() - left_num.mean()) if not left_num.empty and not right_num.empty else np.nan
        ),
        "standardized_difference_cluster_1_minus_0": _standardized_difference(left_num, right_num),
        "exploratory_p_value": _mw_p_value(left_num, right_num),
    }


def _parse_device_ids(value: object) -> set[str]:
    if pd.isna(value):
        return set()
    return {item.strip() for item in str(value).split(";") if item.strip()}


def _technical_patient_table(status: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    """Aggregate collection-quality variables without using device IDs as features."""
    status = status.copy()
    status[ID_COLUMN] = _normalize_id(status[ID_COLUMN])
    status["rows_numeric"] = _numeric(status.get("rows_in_window", pd.Series(index=status.index))) .fillna(0)
    status["is_calculated"] = status.get("table_status", "").astype(str).eq("calculated")
    status["has_rows"] = status["rows_numeric"].gt(0)

    rows: list[dict[str, object]] = []
    for patient_id, group in status.groupby(ID_COLUMN, sort=True):
        available_devices: set[str] = set()
        used_devices: set[str] = set()
        for column, target in [("device_ids_available", available_devices), ("device_ids_used", used_devices)]:
            if column in group:
                for value in group[column]:
                    target.update(_parse_device_ids(value))
        endpoint_days = _numeric(group.get("interval_days_in_endpoint", pd.Series(index=group.index))).dropna()
        rows.append(
            {
                ID_COLUMN: patient_id,
                "recorded_table_count": int(group["is_calculated"].sum()),
                "tables_with_any_rows": int(group["has_rows"].sum()),
                "tables_without_data": int((~group["has_rows"]).sum()),
                "total_rows_in_window": float(group["rows_numeric"].sum()),
                "mean_rows_per_calculated_table": float(group.loc[group["is_calculated"], "rows_numeric"].mean())
                if group["is_calculated"].any()
                else np.nan,
                "n_devices_available": len(available_devices),
                "n_devices_used": len(used_devices),
                "configured_endpoint_interval_days": float(endpoint_days.median()) if not endpoint_days.empty else np.nan,
                "table_status_error_or_retry_count": int((~group["is_calculated"]).sum()),
            }
        )

    patient_table = pd.DataFrame(rows)
    if coverage.empty:
        patient_table["observed_timestamp_span_days"] = np.nan
        patient_table["coverage_rows_across_devices"] = np.nan
        return patient_table

    coverage = coverage.copy()
    coverage[ID_COLUMN] = _normalize_id(coverage[ID_COLUMN])
    coverage["first_numeric"] = _numeric(coverage.get("first_data_timestamp", pd.Series(index=coverage.index)))
    coverage["last_numeric"] = _numeric(coverage.get("last_data_timestamp", pd.Series(index=coverage.index)))
    coverage["coverage_rows_numeric"] = _numeric(coverage.get("rows_in_window", pd.Series(index=coverage.index))).fillna(0)
    coverage_summary = coverage.groupby(ID_COLUMN).agg(
        first_data_timestamp=("first_numeric", "min"),
        last_data_timestamp=("last_numeric", "max"),
        coverage_rows_across_devices=("coverage_rows_numeric", "sum"),
    ).reset_index()
    coverage_summary["observed_timestamp_span_days"] = (
        coverage_summary["last_data_timestamp"] - coverage_summary["first_data_timestamp"]
    ) / 86_400_000
    return patient_table.merge(
        coverage_summary[[ID_COLUMN, "observed_timestamp_span_days", "coverage_rows_across_devices"]],
        on=ID_COLUMN,
        how="outer",
    )


def _write_comparison(frame: pd.DataFrame, features: pd.DataFrame, loadings: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    loading_lookup = loadings.set_index("feature_name", drop=False) if not loadings.empty else pd.DataFrame()
    for _, feature in features.iterrows():
        name = str(feature["feature_name"])
        stats = _cluster_comparison(frame, name)
        loading = loading_lookup.loc[name] if name in loading_lookup.index else pd.Series(dtype=object)
        rows.append(
            {
                "feature_name": name,
                "source_table": str(feature.get("source_table", "")),
                "feature_family": str(feature.get("feature_family", "")),
                "short_description": str(feature.get("short_description", "")),
                "feature_group": _feature_group(name, str(feature.get("source_table", ""))),
                "used_in_fixed_pca_clustering": bool(feature.get("selected_for_panel", False)),
                "feature_coverage_percent": float(_numeric(pd.Series([feature.get("source_patient_coverage_percent")])).iloc[0]),
                **stats,
                "pca_loading_pc1": float(loading.get("PC1", np.nan)),
                "pca_loading_pc2": float(loading.get("PC2", np.nan)),
                "pca_max_abs_loading": float(loading.get("maximum_absolute_loading", np.nan)),
            }
        )
    result = pd.DataFrame(rows)
    result["exploratory_q_value_fdr_bh"] = _fdr_bh(result["exploratory_p_value"])
    result["absolute_standardized_difference"] = result["standardized_difference_cluster_1_minus_0"].abs()
    result["separation_rank"] = result["absolute_standardized_difference"].rank(method="min", ascending=False).astype("Int64")
    result["pca_loading_rank"] = result["pca_max_abs_loading"].rank(method="min", ascending=False).astype("Int64")
    return result.sort_values(["absolute_standardized_difference", "feature_name"], ascending=[False, True])


def _write_technical(frame: pd.DataFrame, technical: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    audit_columns = [
        ("patient_feature_coverage_percent", "patient_feature_coverage_fraction", "Fixed PCA panel audit", "Observed fraction of the 41 primary-panel features used in this PCA representation."),
        ("baseline_feature_missing_percent", "baseline_feature_missing_fraction", "Baseline dataset audit", "Missingness across the full extracted baseline feature catalog."),
        ("baseline_feature_missing_count", "baseline_feature_missing_count", "Baseline dataset audit", "Count of missing extracted baseline feature values."),
        ("baseline_table_coverage_percent", "baseline_table_coverage_fraction", "Baseline dataset audit", "Fraction of baseline tables with a calculated feature value."),
    ]
    rows: list[dict[str, object]] = []
    for display_name, source_column, source, description in audit_columns:
        values = frame[source_column] if source_column in frame.columns else pd.Series(np.nan, index=frame.index)
        if display_name.endswith("percent"):
            values = _numeric(values) * 100
        comparison = _cluster_comparison(pd.DataFrame({CLUSTER_COLUMN: frame[CLUSTER_COLUMN], display_name: values}), display_name)
        rows.append({"variable": display_name, "source": source, "description": description, "available": values.notna().any(), **comparison})
    technical_only_columns = {
        "recorded_table_count",
        "tables_without_data",
        "total_rows_in_window",
        "mean_rows_per_calculated_table",
        "n_devices_available",
        "n_devices_used",
        "configured_endpoint_interval_days",
        "observed_timestamp_span_days",
    }
    for variable in [column for column in technical.columns if column in technical_only_columns]:
        description = {
            "recorded_table_count": "Number of tables with a calculated result in the patient midpoint span.",
            "tables_with_any_rows": "Number of source tables with at least one row in the patient midpoint span.",
            "tables_without_data": "Number of source tables with no rows in the patient midpoint span.",
            "total_rows_in_window": "Total source rows reported across the calculated table spans; a collection-intensity proxy, not a clinical feature.",
            "mean_rows_per_calculated_table": "Mean source rows per calculated table.",
            "n_devices_available": "Number of distinct device identifiers available across the table statuses; identifiers themselves are not exported.",
            "n_devices_used": "Number of distinct device identifiers used by at least one calculated table.",
            "configured_endpoint_interval_days": "Configured T1-to-midpoint endpoint interval, not the number of recorded days.",
            "table_status_error_or_retry_count": "Number of tables without a calculated result.",
            "observed_timestamp_span_days": "Span between earliest and latest observed timestamps across coverage records; not continuous recording time.",
            "coverage_rows_across_devices": "Rows reported in the coverage audit across devices.",
        }.get(variable, variable)
        comparison = _cluster_comparison(technical, variable)
        rows.append({"variable": variable, "source": "Phase 11 midpoint status/coverage audit", "description": description, "available": technical[variable].notna().any(), **comparison})

    result = pd.DataFrame(rows)
    result["exploratory_q_value_fdr_bh"] = _fdr_bh(result["exploratory_p_value"])
    result["absolute_standardized_difference"] = result["standardized_difference_cluster_1_minus_0"].abs()
    result = result.sort_values("absolute_standardized_difference", ascending=False)

    inventory = pd.DataFrame(
        [
            {"variable": "Exact recorded days", "available": False, "source": "Not present in current Phase 11 patient-level exports", "note": "The available audit contains rows and first/last timestamps, but not a deduplicated daily recording calendar."},
            {"variable": "Operating system/version", "available": False, "source": "Not present in current Phase 11 patient-level exports", "note": "Do not infer this from device identifiers."},
            {"variable": "Device type", "available": False, "source": "Not present in current Phase 11 patient-level exports", "note": "Device counts are available; device type is not."},
            {"variable": "Device count", "available": True, "source": "Phase 11 midpoint patient-table status", "note": "Only counts are used in the technical audit; raw identifiers are excluded from comparison outputs."},
            {"variable": "Source rows/events", "available": True, "source": "Phase 11 midpoint patient-table status", "note": "Reported rows are treated as a technical intensity proxy."},
            {"variable": "Observed timestamp span", "available": True, "source": "Phase 11 midpoint coverage audit", "note": "Earliest-to-latest span; not continuous recording duration."},
        ]
    )
    return result, inventory


def _cognitive_frame(dataset: pd.DataFrame, scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    dataset = dataset.copy()
    dataset[ID_COLUMN] = _normalize_id(dataset[ID_COLUMN])
    scores = scores.copy()
    scores[ID_COLUMN] = _normalize_id(scores[ID_COLUMN])
    scores[CLUSTER_COLUMN] = pd.to_numeric(scores[CLUSTER_COLUMN], errors="coerce").astype("Int64")
    score_columns = [ID_COLUMN, CLUSTER_COLUMN, "PC1", "PC2"]
    merged = scores[score_columns].merge(dataset, on=ID_COLUMN, how="left", suffixes=("", "_dataset"))

    # Recompute every delta as T2 - T1 so the definition is explicit and consistent.
    delta_pairs = {
        "global_delta": ("global_T1", "global_T2"),
        "memory_delta": ("memory_T1", "memory_T2"),
        "attention_delta": ("attention_T1", "attention_T2"),
        "ef_delta": ("ef_T1", "ef_T2"),
        "processing_speed_delta": ("processing_speed_T1", "processing_speed_T2"),
        "motor_delta": ("motor_T1", "motor_T2"),
        "verbal_delta": ("verbal_T1", "verbal_T2"),
        "iq_delta": ("iq_T1", "iq_T2"),
    }
    for delta, (t1, t2) in delta_pairs.items():
        merged[delta] = _numeric(merged.get(t2, pd.Series(np.nan, index=merged.index))) - _numeric(merged.get(t1, pd.Series(np.nan, index=merged.index)))

    point_rows: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []
    for label, column, outcome_type in COGNITIVE_OUTCOMES:
        if column not in merged.columns:
            continue
        subset = merged[[ID_COLUMN, CLUSTER_COLUMN, "PC1", "PC2", column]].copy()
        subset = subset.rename(columns={column: "outcome_value"}).dropna(subset=["outcome_value", "PC1", "PC2", CLUSTER_COLUMN])
        subset["outcome"] = label
        subset["outcome_column"] = column
        subset["outcome_type"] = outcome_type
        point_rows.append(subset[[ID_COLUMN, CLUSTER_COLUMN, "PC1", "PC2", "outcome", "outcome_column", "outcome_type", "outcome_value"]])
        comparison = _cluster_comparison(subset, "outcome_value") if not subset.empty else {}
        pc1_corr = float(subset["PC1"].corr(subset["outcome_value"])) if len(subset) >= 3 else np.nan
        pc2_corr = float(subset["PC2"].corr(subset["outcome_value"])) if len(subset) >= 3 else np.nan
        summary_rows.append({"outcome": label, "outcome_column": column, "outcome_type": outcome_type, "n": int(len(subset)), "correlation_pc1": pc1_corr, "correlation_pc2": pc2_corr, **comparison})

    points = pd.concat(point_rows, ignore_index=True) if point_rows else pd.DataFrame()
    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        summary["exploratory_q_value_fdr_bh"] = _fdr_bh(summary["exploratory_p_value"])
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
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    scores = pd.read_csv(SCORES_PATH, dtype={ID_COLUMN: str})
    scores[ID_COLUMN] = _normalize_id(scores[ID_COLUMN])
    loadings = pd.read_csv(LOADINGS_PATH)
    inventory = pd.read_csv(INVENTORY_PATH)
    selected_features = inventory[inventory["selected_for_panel"].astype(str).str.lower().eq("true")].copy()
    if selected_features.empty:
        selected_features = inventory.copy()
    catalog_features = inventory.copy()
    catalog_features["selected_for_panel"] = catalog_features["feature_name"].isin(selected_features["feature_name"])
    coverage = dataset[catalog_features["feature_name"].tolist()].notna().mean().mul(100)
    catalog_features["source_patient_coverage_percent"] = catalog_features["feature_name"].map(coverage)
    fixed = scores[[ID_COLUMN, CLUSTER_COLUMN, "PC1", "PC2", "patient_feature_coverage_fraction"]].copy()
    fixed[CLUSTER_COLUMN] = pd.to_numeric(fixed[CLUSTER_COLUMN], errors="coerce").astype("Int64")
    frame = fixed.merge(dataset, on=ID_COLUMN, how="left", suffixes=("", "_dataset"))

    feature_comparison = _write_comparison(frame, catalog_features, loadings)
    feature_comparison.to_csv(OUTPUT_DIR / "cluster_feature_comparison.csv", index=False)

    status = pd.read_csv(STATUS_PATH, dtype={ID_COLUMN: str})
    coverage = pd.read_csv(COVERAGE_PATH, dtype={ID_COLUMN: str})
    technical = _technical_patient_table(status, coverage)
    technical = technical.merge(frame[[ID_COLUMN, CLUSTER_COLUMN]], on=ID_COLUMN, how="inner")
    technical = technical.merge(
        frame[[ID_COLUMN, "patient_feature_coverage_fraction", "baseline_feature_missing_fraction", "baseline_feature_missing_count", "baseline_table_coverage_fraction"]],
        on=ID_COLUMN,
        how="left",
    )
    technical["patient_feature_coverage_percent"] = _numeric(technical["patient_feature_coverage_fraction"]) * 100
    technical["baseline_feature_missing_percent"] = _numeric(technical["baseline_feature_missing_fraction"]) * 100
    technical["baseline_table_coverage_percent"] = _numeric(technical["baseline_table_coverage_fraction"]) * 100
    technical.drop(columns=["patient_feature_coverage_fraction", "baseline_feature_missing_fraction", "baseline_table_coverage_fraction"], inplace=True)
    technical.to_csv(OUTPUT_DIR / "technical_patient_audit.csv", index=False)
    technical_comparison, technical_inventory = _write_technical(frame, technical)
    technical_comparison.to_csv(OUTPUT_DIR / "technical_confounding_comparison.csv", index=False)
    technical_inventory.to_csv(OUTPUT_DIR / "technical_variable_inventory.csv", index=False)

    cognitive_points, cognitive_summary = _cognitive_frame(dataset, scores)
    cognitive_points.to_csv(OUTPUT_DIR / "cognitive_overlay_points.csv", index=False)
    cognitive_summary.to_csv(OUTPUT_DIR / "cognitive_overlay_summary.csv", index=False)

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
        "fixed_panel": "usable_catalog_50pct",
        "fixed_pca_scores": str(SCORES_PATH.relative_to(ROOT)),
        "fixed_cluster_assignments_recomputed": False,
        "fixed_pca_coordinates_recomputed": False,
        "feature_count": int(len(selected_features)),
        "descriptive_catalog_feature_count": int(len(catalog_features)),
        "analyzed_patients": int(len(frame)),
        "cluster_sizes": {str(key): int(value) for key, value in frame[CLUSTER_COLUMN].value_counts().sort_index().items()},
        "cognitive_outcomes": cognitive_summary["outcome"].tolist() if not cognitive_summary.empty else [],
        "technical_variables_used_to_define_clusters": False,
        "cognitive_variables_used_to_define_clusters": False,
        "exploratory_p_values_only": True,
    }
    (OUTPUT_DIR / "posthoc_run_record.json").write_text(json.dumps(run_record, indent=2), encoding="utf-8")
    print(json.dumps(run_record, indent=2))
    print(f"outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
