"""Build exploratory clinical comparison tables for the Phase 11 T1 cohort.

The severity grouping is intentionally an exploratory median split of observed
global T1. It is not a validated clinical impairment classification.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "output/analysis_candidates/phase11_t1_baseline"
DATASET_PATH = DATA_DIR / "phase11_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase11_t1_baseline_feature_metadata.csv"
OUTPUT_DIR = DATA_DIR / "clinical_tables_baseline_severity"

NON_FEATURE_COLUMNS = {
    "Subject_ID_N",
    "Subject_ID_D",
    "age",
    "Gender (1=M, 2=F)",
    "Education (years)",
    "T1_date_iso",
    "T2_date_iso",
    "global_T1",
    "global_T2",
    "global_delta",
    "memory_T1",
    "memory_T2",
    "memory_delta",
    "ef_T1",
    "ef_T2",
    "ef_delta",
    "attention_T1",
    "attention_T2",
    "attention_delta",
    "processing_speed_T1",
    "processing_speed_T2",
    "processing_speed_delta",
    "verbal_T1",
    "verbal_T2",
    "verbal_delta",
    "motor_T1",
    "motor_T2",
    "motor_delta",
    "iq_T1",
    "iq_T2",
    "iq_delta",
    "baseline_feature_missing_count",
    "baseline_feature_missing_fraction",
    "baseline_table_coverage_fraction",
}


def _format_number(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.{digits}f}"


def _format_median_iqr(values: pd.Series) -> str:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return "NA"
    median = numeric.median()
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    return f"{median:.2f} ({q1:.2f}-{q3:.2f})"


def _format_count_percent(count: int, denominator: int) -> str:
    if denominator == 0:
        return "NA"
    return f"{count} ({100 * count / denominator:.1f}%)"


def _cliffs_delta(lower: np.ndarray, higher: np.ndarray) -> float:
    if len(lower) == 0 or len(higher) == 0:
        return np.nan
    comparisons = higher[:, None] - lower[None, :]
    return float((np.sum(comparisons > 0) - np.sum(comparisons < 0)) / comparisons.size)


def _continuous_statistics(lower: pd.Series, higher: pd.Series) -> dict[str, object]:
    lower_numeric = pd.to_numeric(lower, errors="coerce").dropna().to_numpy(dtype=float)
    higher_numeric = pd.to_numeric(higher, errors="coerce").dropna().to_numpy(dtype=float)
    result: dict[str, object] = {
        "n_lower": int(len(lower_numeric)),
        "n_higher": int(len(higher_numeric)),
        "lower_summary": _format_median_iqr(pd.Series(lower_numeric)),
        "higher_summary": _format_median_iqr(pd.Series(higher_numeric)),
        "p_value": np.nan,
        "effect_size_cliffs_delta_higher_minus_lower": np.nan,
        "test": "not_tested",
    }
    if len(lower_numeric) >= 3 and len(higher_numeric) >= 3:
        try:
            result["p_value"] = float(
                mannwhitneyu(lower_numeric, higher_numeric, alternative="two-sided").pvalue
            )
            result["effect_size_cliffs_delta_higher_minus_lower"] = _cliffs_delta(
                lower_numeric, higher_numeric
            )
            result["test"] = "Mann-Whitney U"
        except ValueError:
            result["test"] = "not_tested_invalid_values"
    return result


def _fdr_bh(p_values: pd.Series) -> pd.Series:
    values = pd.to_numeric(p_values, errors="coerce")
    q_values = pd.Series(np.nan, index=values.index, dtype=float)
    valid = values.notna()
    if not valid.any():
        return q_values
    raw = values.loc[valid].to_numpy(dtype=float)
    order = np.argsort(raw)
    ranked = raw[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)
    restored = np.empty_like(adjusted)
    restored[order] = adjusted
    q_values.loc[valid] = restored
    return q_values


def _categorical_statistics(lower: pd.Series, higher: pd.Series, positive_value: int) -> dict[str, object]:
    lower_values = pd.to_numeric(lower, errors="coerce")
    higher_values = pd.to_numeric(higher, errors="coerce")
    lower_valid = lower_values.dropna()
    higher_valid = higher_values.dropna()
    lower_positive = int((lower_valid == positive_value).sum())
    higher_positive = int((higher_valid == positive_value).sum())
    result: dict[str, object] = {
        "n_lower": int(len(lower_valid)),
        "n_higher": int(len(higher_valid)),
        "lower_summary": _format_count_percent(lower_positive, len(lower_valid)),
        "higher_summary": _format_count_percent(higher_positive, len(higher_valid)),
        "p_value": np.nan,
        "effect_size_cliffs_delta_higher_minus_lower": np.nan,
        "test": "not_tested",
    }
    lower_negative = int(len(lower_valid) - lower_positive)
    higher_negative = int(len(higher_valid) - higher_positive)
    if len(lower_valid) >= 3 and len(higher_valid) >= 3:
        try:
            _, p_value = fisher_exact(
                [[lower_positive, lower_negative], [higher_positive, higher_negative]]
            )
            result["p_value"] = float(p_value)
            result["test"] = "Fisher exact"
        except ValueError:
            result["test"] = "not_tested_invalid_values"
    return result


def _feature_columns(dataset: pd.DataFrame, metadata: pd.DataFrame) -> list[str]:
    catalog_features = [
        name for name in metadata.get("feature_name", pd.Series(dtype=str)).dropna().astype(str)
        if name in dataset.columns
    ]
    catalog_set = set(catalog_features)
    extra_numeric = []
    for column in dataset.columns:
        if column in NON_FEATURE_COLUMNS or column in catalog_set:
            continue
        numeric = pd.to_numeric(dataset[column], errors="coerce")
        if numeric.notna().any():
            extra_numeric.append(column)
    return catalog_features + extra_numeric


def build_tables() -> dict[str, Path]:
    dataset = pd.read_csv(DATASET_PATH)
    metadata = pd.read_csv(METADATA_PATH)
    global_t1 = pd.to_numeric(dataset["global_T1"], errors="coerce")
    cutoff = float(global_t1.median())
    eligible = global_t1.notna()
    group = pd.Series(pd.NA, index=dataset.index, dtype="string")
    group.loc[eligible & (global_t1 <= cutoff)] = "Lower observed T1"
    group.loc[eligible & (global_t1 > cutoff)] = "Higher observed T1"
    dataset["baseline_severity_group"] = group

    lower_mask = group.eq("Lower observed T1")
    higher_mask = group.eq("Higher observed T1")
    n_lower = int(lower_mask.sum())
    n_higher = int(higher_mask.sum())
    feature_columns = _feature_columns(dataset, metadata)

    metadata_by_feature = metadata.set_index("feature_name", drop=False)
    feature_rows: list[dict[str, object]] = []
    for feature in feature_columns:
        values = pd.to_numeric(dataset[feature], errors="coerce")
        stats = _continuous_statistics(values.loc[lower_mask], values.loc[higher_mask])
        meta = metadata_by_feature.loc[feature] if feature in metadata_by_feature.index else pd.Series(dtype=object)
        lower_missing = float(values.loc[lower_mask].isna().mean() * 100) if n_lower else np.nan
        higher_missing = float(values.loc[higher_mask].isna().mean() * 100) if n_higher else np.nan
        feature_rows.append(
            {
                "feature_name": feature,
                "source_table": meta.get("source_table", "Phase 11 dataset; metadata pending"),
                "feature_family": meta.get("feature_family", "Dataset feature; metadata pending"),
                "short_description": meta.get("short_description", "Not yet documented in the feature metadata catalog"),
                "primary_model_recommendation": meta.get("primary_model_recommendation", "Not yet cataloged"),
                "n_overall": int(values.notna().sum()),
                "n_lower": stats["n_lower"],
                "n_higher": stats["n_higher"],
                "lower_median_iqr": stats["lower_summary"],
                "higher_median_iqr": stats["higher_summary"],
                "missing_overall_percent": float(values.isna().mean() * 100),
                "missing_lower_percent": lower_missing,
                "missing_higher_percent": higher_missing,
                "p_value": stats["p_value"],
                "effect_size_cliffs_delta_higher_minus_lower": stats[
                    "effect_size_cliffs_delta_higher_minus_lower"
                ],
                "test": stats["test"],
                "catalog_missing_percent": meta.get("missing_percent", np.nan),
            }
        )
    feature_table = pd.DataFrame(feature_rows)
    feature_table["q_value_fdr_bh"] = _fdr_bh(feature_table["p_value"])
    feature_table = feature_table.sort_values(
        ["q_value_fdr_bh", "p_value", "feature_name"], na_position="last"
    ).reset_index(drop=True)
    feature_table.insert(0, "exploratory_grouping", "Median split of observed global T1")
    feature_table.insert(1, "global_t1_median_cutoff", cutoff)

    clinical_rows: list[dict[str, object]] = []

    def add_continuous(label: str, column: str, unit: str = "") -> None:
        if column not in dataset:
            return
        values = pd.to_numeric(dataset[column], errors="coerce")
        stats = _continuous_statistics(values.loc[lower_mask], values.loc[higher_mask])
        clinical_rows.append(
            {
                "variable": label,
                "unit": unit,
                "overall": _format_median_iqr(values),
                "lower_observed_t1": stats["lower_summary"],
                "higher_observed_t1": stats["higher_summary"],
                "n_overall": int(values.notna().sum()),
                "n_lower": stats["n_lower"],
                "n_higher": stats["n_higher"],
                "p_value": stats["p_value"],
                "effect_size_cliffs_delta_higher_minus_lower": stats[
                    "effect_size_cliffs_delta_higher_minus_lower"
                ],
                "test": stats["test"],
            }
        )

    def add_binary(label: str, column: str, positive_value: int, unit: str = "") -> None:
        if column not in dataset:
            return
        values = pd.to_numeric(dataset[column], errors="coerce")
        stats = _categorical_statistics(values.loc[lower_mask], values.loc[higher_mask], positive_value)
        clinical_rows.append(
            {
                "variable": label,
                "unit": unit,
                "overall": _format_count_percent(int((values == positive_value).sum()), int(values.notna().sum())),
                "lower_observed_t1": stats["lower_summary"],
                "higher_observed_t1": stats["higher_summary"],
                "n_overall": int(values.notna().sum()),
                "n_lower": stats["n_lower"],
                "n_higher": stats["n_higher"],
                "p_value": stats["p_value"],
                "effect_size_cliffs_delta_higher_minus_lower": stats[
                    "effect_size_cliffs_delta_higher_minus_lower"
                ],
                "test": stats["test"],
            }
        )

    clinical_rows.append(
        {
            "variable": "Participants",
            "unit": "n",
            "overall": str(int(eligible.sum())),
            "lower_observed_t1": str(n_lower),
            "higher_observed_t1": str(n_higher),
            "n_overall": int(eligible.sum()),
            "n_lower": n_lower,
            "n_higher": n_higher,
            "p_value": np.nan,
            "effect_size_cliffs_delta_higher_minus_lower": np.nan,
            "test": "not_tested",
        }
    )
    add_continuous("Age", "age", "years")
    add_binary("Female sex", "Gender (1=M, 2=F)", 2, "n (%)")
    add_continuous("Education", "Education (years)", "years")
    add_continuous("Global cognitive T1", "global_T1", "score")
    for label, column in (
        ("Memory T1", "memory_T1"),
        ("Executive function T1", "ef_T1"),
        ("Processing speed T1", "processing_speed_T1"),
        ("Attention T1", "attention_T1"),
        ("Motor T1", "motor_T1"),
    ):
        add_continuous(label, column, "score")
    if "global_T2" in dataset:
        t2_available = dataset["global_T2"].notna().astype(int)
        dataset["t2_available"] = t2_available
        add_binary("T2 score available", "t2_available", 1, "n (%)")
    usable_count = pd.to_numeric(
        dataset[feature_columns].notna().sum(axis=1), errors="coerce"
    )
    dataset["usable_feature_count_all_available"] = usable_count
    add_continuous("Usable digital features", "usable_feature_count_all_available", "n")
    add_continuous("Patient-level feature missingness", "baseline_feature_missing_fraction", "fraction")
    add_continuous("Patient-level table coverage", "baseline_table_coverage_fraction", "fraction")

    clinical_table = pd.DataFrame(clinical_rows)
    clinical_table.insert(0, "exploratory_grouping", "Median split of observed global T1")
    clinical_table.insert(1, "global_t1_median_cutoff", cutoff)
    clinical_table["q_value_fdr_bh"] = _fdr_bh(clinical_table["p_value"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    group_assignments = dataset[
        [
            column
            for column in [
                "Subject_ID_N",
                "Subject_ID_D",
                "global_T1",
                "baseline_severity_group",
                "t2_available",
            ]
            if column in dataset
        ]
    ].copy()
    group_assignments.insert(0, "global_t1_median_cutoff", cutoff)
    group_assignments.to_csv(OUTPUT_DIR / "phase11_baseline_severity_group_assignments.csv", index=False)
    clinical_table.to_csv(OUTPUT_DIR / "phase11_baseline_severity_clinical_table1.csv", index=False)
    feature_table.to_csv(OUTPUT_DIR / "phase11_baseline_severity_all_features.csv", index=False)

    readme = f"""# Phase 11 baseline cognitive severity tables

These tables compare the Phase 11 midpoint-span T1 cohort using an exploratory
median split of observed `global_T1`.

- Lower observed T1: global T1 <= {cutoff:.2f} (n={n_lower})
- Higher observed T1: global T1 > {cutoff:.2f} (n={n_higher})
- Participants with observed global T1: {int(eligible.sum())}
- Digital features included: {len(feature_columns)}

This is a data-driven comparison, not a validated clinical severity or
impairment diagnosis. If a validated clinical cutoff becomes available, this
table should be regenerated with that prespecified threshold.

The detailed feature table includes every measured digital feature available in
the Phase 11 patient dataset, including features outside the primary model.
Missing values are not converted to zero or median-imputed for this descriptive
comparison. Each feature is summarized from its available observations, and
`n_lower`/`n_higher` make the coverage visible.

Feature p-values are two-sided Mann-Whitney U tests. `q_value_fdr_bh` is the
Benjamini-Hochberg false-discovery-rate adjustment across the tested features;
these results are exploratory and require validation in a larger cohort.
`effect_size_cliffs_delta_higher_minus_lower` is positive when the higher-T1
group tends to have larger feature values.
"""
    (OUTPUT_DIR / "README_phase11_baseline_severity_tables.md").write_text(readme, encoding="utf-8")
    return {
        "clinical_table": OUTPUT_DIR / "phase11_baseline_severity_clinical_table1.csv",
        "all_features": OUTPUT_DIR / "phase11_baseline_severity_all_features.csv",
        "group_assignments": OUTPUT_DIR / "phase11_baseline_severity_group_assignments.csv",
        "readme": OUTPUT_DIR / "README_phase11_baseline_severity_tables.md",
    }


if __name__ == "__main__":
    paths = build_tables()
    for label, path in paths.items():
        print(f"{label}: {path}")
