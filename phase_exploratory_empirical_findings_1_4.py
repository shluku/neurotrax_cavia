"""Repeat the exploratory empirical analysis in the two extreme T1 groups.

This is a separate analysis from ``phase_exploratory_empirical_findings.py``.
The model feature set remains the same two keyboard features so that the
cohort definition, rather than feature replacement, is the main change.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler


ROOT = Path(__file__).parent
SOURCE_DIR = ROOT / "output/analysis_candidates/phase11_t1_baseline"
DATASET_PATH = SOURCE_DIR / "phase11_t1_baseline_patient_dataset.csv"
METADATA_PATH = SOURCE_DIR / "phase11_t1_baseline_feature_metadata.csv"
MEDIAN_FEATURE_TABLE_PATH = SOURCE_DIR / "clinical_tables_baseline_severity/phase11_baseline_severity_all_features.csv"
OUT_DIR = ROOT / "output/analysis_candidates/phase_exploratory_empirical_findings_1_4"
FEATURE_COMPARISON_PATH = OUT_DIR / "exploratory_empirical_1_4_feature_comparison.csv"
FEATURE_CONFIG_PATH = OUT_DIR / "exploratory_empirical_1_4_feature_config.csv"
GROUP_ASSIGNMENTS_PATH = OUT_DIR / "exploratory_empirical_1_4_group_assignments.csv"
PREDICTIONS_PATH = OUT_DIR / "exploratory_empirical_1_4_predictions.csv"
PATIENT_PATH = OUT_DIR / "exploratory_empirical_1_4_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "exploratory_empirical_1_4_metrics.csv"
COEFFICIENT_PATH = OUT_DIR / "exploratory_empirical_1_4_coefficients.csv"
README_PATH = OUT_DIR / "README_exploratory_empirical_findings_1_4.md"

FEATURES = [
    "keyboard_median_word_completion_time_ms",
    "keyboard_inter_event_interval_iqr_ms",
]
TARGET = "global_T1"
EXTREME_N = 20
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260817
ALPHAS = np.logspace(-2, 4, 24)

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


def _format_median_iqr(values: pd.Series) -> str:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return "NA"
    return f"{numeric.median():.2f} ({numeric.quantile(0.25):.2f}-{numeric.quantile(0.75):.2f})"


def _cliffs_delta(low: np.ndarray, high: np.ndarray) -> float:
    if len(low) == 0 or len(high) == 0:
        return np.nan
    differences = high[:, None] - low[None, :]
    return float((np.sum(differences > 0) - np.sum(differences < 0)) / differences.size)


def _fdr_bh(p_values: pd.Series) -> pd.Series:
    values = pd.to_numeric(p_values, errors="coerce")
    result = pd.Series(np.nan, index=values.index, dtype=float)
    valid = values.notna()
    if not valid.any():
        return result
    raw = values.loc[valid].to_numpy(dtype=float)
    order = np.argsort(raw)
    ranked = raw[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    restored = np.empty_like(adjusted)
    restored[order] = np.clip(adjusted, 0, 1)
    result.loc[valid] = restored
    return result


def _feature_columns(dataset: pd.DataFrame, metadata: pd.DataFrame) -> list[str]:
    catalog = [
        name
        for name in metadata.get("feature_name", pd.Series(dtype=str)).dropna().astype(str)
        if name in dataset.columns
    ]
    catalog_set = set(catalog)
    extras = []
    for column in dataset.columns:
        if column in NON_FEATURE_COLUMNS or column in catalog_set:
            continue
        if pd.to_numeric(dataset[column], errors="coerce").notna().any():
            extras.append(column)
    return catalog + extras


def _build_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("robust_scaler", RobustScaler(quantile_range=(25, 75))),
            ("ridge", Ridge(positive=True)),
        ]
    )


def _fit_equal_weight_score(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    x_test: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    scaler = RobustScaler(quantile_range=(25, 75))
    train_scaled = scaler.fit_transform(imputer.fit_transform(x_train))
    test_scaled = scaler.transform(imputer.transform(x_test))
    train_score = train_scaled.mean(axis=1)
    test_score = test_scaled.mean(axis=1)
    calibration = Ridge(alpha=1.0, positive=True)
    calibration.fit(train_score.reshape(-1, 1), y_train)
    return train_score, test_score, calibration.predict(test_score.reshape(-1, 1))


def _metric_row(actual: np.ndarray, predicted: np.ndarray, model: str, repeat: int | str) -> dict[str, object]:
    return {
        "analysis_scope": "repeat" if repeat != "pooled" else "pooled",
        "repeat": repeat,
        "outcome": TARGET,
        "model": model,
        "n_predictions": len(actual),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
    }


def _build_extreme_groups(dataset: pd.DataFrame) -> tuple[pd.DataFrame, float, float]:
    valid = dataset[pd.to_numeric(dataset[TARGET], errors="coerce").notna()].copy()
    valid[TARGET] = pd.to_numeric(valid[TARGET], errors="coerce")
    valid = valid.sort_values([TARGET, "Subject_ID_D", "Subject_ID_N"], kind="mergesort")
    if len(valid) < 2 * EXTREME_N:
        raise ValueError(f"Need at least {2 * EXTREME_N} patients with observed {TARGET}.")
    low = valid.head(EXTREME_N).copy()
    high = valid.tail(EXTREME_N).copy()
    low["extreme_group"] = "Lowest 20 baseline scores"
    high["extreme_group"] = "Highest 20 baseline scores"
    selected = pd.concat([low, high], axis=0).sort_values(TARGET, kind="mergesort").reset_index(drop=True)
    return selected, float(low[TARGET].max()), float(high[TARGET].min())


def _compare_features(
    selected: pd.DataFrame,
    feature_columns: list[str],
    metadata: pd.DataFrame,
    median_table: pd.DataFrame,
    low_cutoff: float,
    high_cutoff: float,
) -> pd.DataFrame:
    metadata_by_feature = metadata.set_index("feature_name", drop=False)
    median_lookup = median_table.set_index("feature_name")
    low_mask = selected["extreme_group"].eq("Lowest 20 baseline scores")
    high_mask = selected["extreme_group"].eq("Highest 20 baseline scores")
    rows: list[dict[str, object]] = []
    for feature in feature_columns:
        values = pd.to_numeric(selected[feature], errors="coerce")
        low_values = values.loc[low_mask].dropna().to_numpy(dtype=float)
        high_values = values.loc[high_mask].dropna().to_numpy(dtype=float)
        p_value = np.nan
        effect = np.nan
        test = "not_tested"
        if len(low_values) >= 3 and len(high_values) >= 3:
            p_value = float(mannwhitneyu(low_values, high_values, alternative="two-sided").pvalue)
            effect = _cliffs_delta(low_values, high_values)
            test = "Mann-Whitney U"
        meta = metadata_by_feature.loc[feature] if feature in metadata_by_feature.index else pd.Series(dtype=object)
        prior = median_lookup.loc[feature] if feature in median_lookup.index else pd.Series(dtype=object)
        rows.append(
            {
                "feature_name": feature,
                "source_table": meta.get("source_table", "Dataset feature; metadata pending"),
                "feature_family": meta.get("feature_family", "Dataset feature; metadata pending"),
                "short_description": meta.get("short_description", "Not yet documented in the feature metadata catalog"),
                "n_lowest_20": int(len(low_values)),
                "n_highest_20": int(len(high_values)),
                "lowest_20_median_iqr": _format_median_iqr(pd.Series(low_values)),
                "highest_20_median_iqr": _format_median_iqr(pd.Series(high_values)),
                "extreme_p_value": p_value,
                "extreme_effect_cliffs_delta_highest_minus_lowest": effect,
                "extreme_test": test,
                "extreme_missing_percent": float(values.isna().mean() * 100),
                "median_split_p_value": prior.get("p_value", np.nan),
                "median_split_q_value": prior.get("q_value_fdr_bh", np.nan),
                "metadata_missing_percent": meta.get("missing_percent", np.nan),
            }
        )
    result = pd.DataFrame(rows)
    result["extreme_q_value"] = _fdr_bh(result["extreme_p_value"])
    result["extreme_rank_by_p_value"] = result["extreme_p_value"].rank(method="min", na_option="bottom").astype(int)
    result["grouping_rule"] = f"Lowest {EXTREME_N} versus highest {EXTREME_N} observed baseline global cognitive scores"
    result["lowest_20_max_score"] = low_cutoff
    result["highest_20_min_score"] = high_cutoff
    return result.sort_values(["extreme_q_value", "extreme_p_value", "feature_name"], na_position="last").reset_index(drop=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH)
    median_table = pd.read_csv(MEDIAN_FEATURE_TABLE_PATH)
    selected, low_cutoff, high_cutoff = _build_extreme_groups(dataset)
    feature_columns = _feature_columns(selected, metadata)
    comparison = _compare_features(selected, feature_columns, metadata, median_table, low_cutoff, high_cutoff)
    comparison.to_csv(FEATURE_COMPARISON_PATH, index=False)

    selected_features = comparison[comparison["feature_name"].isin(FEATURES)].copy()
    if len(selected_features) != len(FEATURES):
        raise ValueError("The fixed empirical keyboard feature set is incomplete in the extreme-group comparison.")
    directions = np.sign(pd.to_numeric(selected_features["extreme_effect_cliffs_delta_highest_minus_lowest"], errors="coerce"))
    directions = directions.replace(0, np.nan).fillna(1).astype(float).to_numpy()
    selected_features["direction_to_higher_T1"] = directions
    selected_features["model_input"] = "oriented feature = original feature * direction_to_higher_T1"
    selected_features["model_scope"] = "fixed two-feature set from the original empirical analysis"
    selected_features.to_csv(FEATURE_CONFIG_PATH, index=False)
    selected[["Subject_ID_D", "Subject_ID_N", TARGET, "extreme_group"]].to_csv(GROUP_ASSIGNMENTS_PATH, index=False)

    x_raw = selected[FEATURES].apply(pd.to_numeric, errors="coerce")
    x_oriented = x_raw.copy()
    for feature, direction in zip(FEATURES, directions):
        x_oriented[feature] = x_oriented[feature] * direction
    y = pd.to_numeric(selected[TARGET], errors="coerce").to_numpy(dtype=float)

    outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
    prediction_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    coefficient_rows: list[dict[str, object]] = []
    repeat_buffers: dict[int, dict[str, list[float]]] = {}

    for split_index, (train_idx, test_idx) in enumerate(outer.split(x_oriented)):
        repeat = split_index // N_SPLITS + 1
        fold = split_index % N_SPLITS + 1
        x_train = x_oriented.iloc[train_idx]
        x_test = x_oriented.iloc[test_idx]
        y_train = y[train_idx]
        y_test = y[test_idx]
        baseline = np.repeat(y_train.mean(), len(test_idx))
        ridge = GridSearchCV(
            _build_pipeline(),
            {"ridge__alpha": ALPHAS},
            cv=KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE + repeat + fold),
            scoring="neg_root_mean_squared_error",
            refit=True,
            n_jobs=1,
        )
        ridge.fit(x_train, y_train)
        ridge_prediction = ridge.predict(x_test)
        _, empirical_test_score, empirical_prediction = _fit_equal_weight_score(x_train, y_train, x_test)
        buffers = repeat_buffers.setdefault(repeat, {"actual": [], "baseline": [], "empirical": [], "ridge": []})
        buffers["actual"].extend(y_test.tolist())
        buffers["baseline"].extend(baseline.tolist())
        buffers["empirical"].extend(empirical_prediction.tolist())
        buffers["ridge"].extend(ridge_prediction.tolist())
        ridge_model = ridge.best_estimator_.named_steps["ridge"]
        for feature, direction, coefficient in zip(FEATURES, directions, ridge_model.coef_):
            coefficient_rows.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "feature_name": feature,
                    "direction_to_higher_T1": direction,
                    "oriented_coefficient": float(coefficient),
                    "original_direction_coefficient": float(coefficient * direction),
                    "ridge_alpha": float(ridge.best_params_["ridge__alpha"]),
                }
            )
        for row_offset, row_pos in enumerate(test_idx):
            observed_count = int(x_raw.iloc[row_pos].notna().sum())
            prediction_rows.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "Subject_ID_D": selected.iloc[row_pos]["Subject_ID_D"],
                    "Subject_ID_N": selected.iloc[row_pos]["Subject_ID_N"],
                    "observed_global_T1": y[row_pos],
                    "extreme_group": selected.iloc[row_pos]["extreme_group"],
                    "mean_baseline_prediction": baseline[row_offset],
                    "equal_weight_empirical_prediction": empirical_prediction[row_offset],
                    "equal_weight_empirical_score": empirical_test_score[row_offset],
                    "direction_constrained_ridge_prediction": ridge_prediction[row_offset],
                    "n_empirical_features_observed": observed_count,
                    "all_selected_features_observed": observed_count == len(FEATURES),
                    "ridge_alpha": float(ridge.best_params_["ridge__alpha"]),
                }
            )

    for repeat, values in repeat_buffers.items():
        actual = np.asarray(values["actual"])
        metric_rows.extend(
            [
                _metric_row(actual, np.asarray(values["baseline"]), "mean_baseline", repeat),
                _metric_row(actual, np.asarray(values["empirical"]), "equal_weight_empirical_score", repeat),
                _metric_row(actual, np.asarray(values["ridge"]), "direction_constrained_ridge", repeat),
            ]
        )

    predictions = pd.DataFrame(prediction_rows)
    metric_rows.extend(
        [
            _metric_row(predictions["observed_global_T1"].to_numpy(), predictions["mean_baseline_prediction"].to_numpy(), "mean_baseline", "pooled"),
            _metric_row(predictions["observed_global_T1"].to_numpy(), predictions["equal_weight_empirical_prediction"].to_numpy(), "equal_weight_empirical_score", "pooled"),
            _metric_row(predictions["observed_global_T1"].to_numpy(), predictions["direction_constrained_ridge_prediction"].to_numpy(), "direction_constrained_ridge", "pooled"),
        ]
    )
    patient_predictions = (
        predictions.groupby(["Subject_ID_D", "Subject_ID_N"], dropna=False)
        .agg(
            observed_global_T1=("observed_global_T1", "first"),
            extreme_group=("extreme_group", "first"),
            mean_baseline_prediction=("mean_baseline_prediction", "mean"),
            equal_weight_empirical_prediction=("equal_weight_empirical_prediction", "mean"),
            direction_constrained_ridge_prediction=("direction_constrained_ridge_prediction", "mean"),
            mean_empirical_score=("equal_weight_empirical_score", "mean"),
            n_empirical_features_observed=("n_empirical_features_observed", "first"),
            all_selected_features_observed=("all_selected_features_observed", "first"),
        )
        .reset_index()
        .sort_values("observed_global_T1")
    )
    metrics = pd.DataFrame(metric_rows)
    predictions.to_csv(PREDICTIONS_PATH, index=False)
    patient_predictions.to_csv(PATIENT_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    pd.DataFrame(coefficient_rows).to_csv(COEFFICIENT_PATH, index=False)

    pooled = metrics[metrics["analysis_scope"].eq("pooled")]
    top_five = comparison.head(5)
    comparison_lines = [
        f"- {row.feature_name}: extreme p `{row.extreme_p_value:.3f}`; median-split p `{row.median_split_p_value:.3f}`; extreme q `{row.extreme_q_value:.3f}`."
        for row in top_five.itertuples()
        if pd.notna(row.extreme_p_value)
    ]
    selected_lines = [
        f"- {row.feature_name}: extreme p `{row.extreme_p_value:.3f}` versus original median-split p `{row.median_split_p_value:.3f}`; direction `{row.direction_to_higher_T1:+.0f}`."
        for row in selected_features.itertuples()
    ]
    lines = [
        "# Exploratory Empirical Findings (1;4)",
        "",
        f"This separate exploratory analysis compares the {EXTREME_N} participants with the lowest observed baseline global cognitive scores against the {EXTREME_N} participants with the highest scores.",
        "",
        "## Cohort rule",
        "",
        f"- Lowest group: the 20 lowest observed baseline global cognitive scores.",
        f"- Highest group: the 20 highest observed baseline global cognitive scores.",
        f"- Lowest-group maximum score: `{low_cutoff:.2f}`.",
        f"- Highest-group minimum score: `{high_cutoff:.2f}`.",
        "- The two keyboard features from the original empirical model remain fixed so the p-value comparison changes the cohort definition rather than the model feature set.",
        "- This is an exploratory extreme-group comparison, not a validated clinical severity classification.",
        "",
        "## P-value comparison",
        "",
        "The full feature table stores the new extreme-group p-values beside the original median-split p-values. The five smallest extreme-group p-values are:",
        *comparison_lines,
        "",
        "For the fixed model features:",
        *selected_lines,
        "",
        "## Model protocol",
        "",
        "- The model uses the same two keyboard features as the original empirical analysis.",
        "- Missing values are imputed with training-fold medians; missingness indicators are not added.",
        "- Oriented features use training-fold robust scaling and a positive Ridge calibration.",
        "- Results use repeated 5-fold cross-validation with 20 repeats and the same fold-local mean baseline.",
        "",
        "## Pooled model results",
        "",
    ]
    for row in pooled.itertuples():
        lines.append(f"- {row.model}: RMSE `{row.rmse:.3f}`, MAE `{row.mae:.3f}`, R2 `{row.r2:.3f}`.")
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            f"The model cohort contains {len(selected)} participants, not the full 81-participant cohort. Feature-level p-values can become smaller when comparing extreme groups because the groups are farther apart by construction, but this does not establish generalizable prediction or a clinical threshold.",
            "",
            "The extreme-group selection and model evaluation use the same cohort. The results are therefore hypothesis-generating and require replication in a prespecified independent sample.",
        ]
    )
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"extreme_patients: {len(selected)}")
    print(f"lowest_20_max_score: {low_cutoff:.2f}")
    print(f"highest_20_min_score: {high_cutoff:.2f}")
    print("top_extreme_features:")
    print(comparison[["feature_name", "extreme_p_value", "extreme_q_value", "median_split_p_value"]].head(5).to_string(index=False))
    print("pooled_metrics:")
    print(pooled[["model", "n_predictions", "rmse", "mae", "r2"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
