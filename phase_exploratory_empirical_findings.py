"""Model the Phase 11 cohort using the exploratory empirical feature findings.

This phase is intentionally small and hypothesis-generating. It uses fixed
feature directions from the exploratory baseline-severity table, robust scaling,
and positive Ridge coefficients so the fitted estimate cannot reverse those
directions.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler


ROOT = Path(__file__).parent
SOURCE_DIR = ROOT / "output/analysis_candidates/phase11_t1_baseline"
DATASET_PATH = SOURCE_DIR / "phase11_t1_baseline_patient_dataset.csv"
SELECTION_PATH = SOURCE_DIR / "clinical_tables_baseline_severity/phase11_baseline_severity_all_features.csv"
OUT_DIR = ROOT / "output/analysis_candidates/phase_exploratory_empirical_findings"
FEATURE_CONFIG_PATH = OUT_DIR / "exploratory_empirical_feature_config.csv"
PREDICTIONS_PATH = OUT_DIR / "exploratory_empirical_predictions.csv"
PATIENT_PATH = OUT_DIR / "exploratory_empirical_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "exploratory_empirical_metrics.csv"
COEFFICIENT_PATH = OUT_DIR / "exploratory_empirical_coefficients.csv"
README_PATH = OUT_DIR / "README_exploratory_empirical_findings.md"

FEATURES = [
    "keyboard_median_word_completion_time_ms",
    "keyboard_inter_event_interval_iqr_ms",
    "missed_rejected_blocked_call_count",
    "call_event_count",
    "outgoing_call_count",
    "keyboard_typing_burst_count",
]
TARGET = "global_T1"
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260811
ALPHAS = np.logspace(-2, 4, 24)


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


def _load_selection() -> pd.DataFrame:
    if not SELECTION_PATH.exists():
        from phase11_build_clinical_tables import build_tables

        build_tables()
    selected = pd.read_csv(SELECTION_PATH)
    selected = selected.set_index("feature_name").reindex(FEATURES).reset_index()
    if selected["feature_name"].isna().any() or selected["p_value"].isna().all():
        raise ValueError("The empirical feature table does not contain the requested six findings.")
    return selected


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
    """Fit a transparent equal-weight robust score and positive calibration."""
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    scaler = RobustScaler(quantile_range=(25, 75))
    train_scaled = scaler.fit_transform(imputer.fit_transform(x_train))
    test_scaled = scaler.transform(imputer.transform(x_test))
    train_score = train_scaled.mean(axis=1)
    test_score = test_scaled.mean(axis=1)
    calibration = Ridge(alpha=1.0, positive=True)
    calibration.fit(train_score.reshape(-1, 1), y_train)
    return train_score, test_score, calibration.predict(test_score.reshape(-1, 1))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    selection = _load_selection()
    directions = np.sign(pd.to_numeric(selection["effect_size_cliffs_delta_higher_minus_lower"], errors="coerce"))
    directions = directions.replace(0, np.nan).fillna(1).astype(float).to_numpy()
    selection["direction_to_higher_T1"] = directions
    selection["model_input"] = "oriented feature = original feature * direction_to_higher_T1"
    selection["model_scope"] = "exploratory empirical six-feature set"
    selection.to_csv(FEATURE_CONFIG_PATH, index=False)

    x_raw = dataset[FEATURES].apply(pd.to_numeric, errors="coerce")
    x_oriented = x_raw.copy()
    for feature, direction in zip(FEATURES, directions):
        x_oriented[feature] = x_oriented[feature] * direction
    y_series = pd.to_numeric(dataset[TARGET], errors="coerce")
    valid = y_series.notna()
    dataset = dataset.loc[valid].reset_index(drop=True)
    x_oriented = x_oriented.loc[valid].reset_index(drop=True)
    x_raw = x_raw.loc[valid].reset_index(drop=True)
    y = y_series.loc[valid].to_numpy(dtype=float)

    n_splits = min(N_SPLITS, len(dataset))
    outer = RepeatedKFold(n_splits=n_splits, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
    prediction_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    coefficient_rows: list[dict[str, object]] = []
    repeat_buffers: dict[int, dict[str, list[float]]] = {}

    for split_index, (train_idx, test_idx) in enumerate(outer.split(x_oriented)):
        repeat = split_index // n_splits + 1
        fold = split_index % n_splits + 1
        x_train = x_oriented.iloc[train_idx]
        x_test = x_oriented.iloc[test_idx]
        y_train = y[train_idx]
        y_test = y[test_idx]
        baseline = np.repeat(y_train.mean(), len(test_idx))

        inner_splits = min(4, len(train_idx))
        ridge = GridSearchCV(
            _build_pipeline(),
            {"ridge__alpha": ALPHAS},
            cv=KFold(n_splits=inner_splits, shuffle=True, random_state=RANDOM_STATE + repeat + fold),
            scoring="neg_root_mean_squared_error",
            refit=True,
            n_jobs=1,
        )
        ridge.fit(x_train, y_train)
        ridge_prediction = ridge.predict(x_test)
        _, empirical_test_score, empirical_prediction = _fit_equal_weight_score(x_train, y_train, x_test)

        buffers = repeat_buffers.setdefault(
            repeat,
            {"actual": [], "baseline": [], "empirical": [], "ridge": []},
        )
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
                    "Subject_ID_D": dataset.loc[row_pos, "Subject_ID_D"],
                    "Subject_ID_N": dataset.loc[row_pos, "Subject_ID_N"] if "Subject_ID_N" in dataset else pd.NA,
                    "observed_global_T1": y[row_pos],
                    "mean_baseline_prediction": baseline[row_offset],
                    "equal_weight_empirical_prediction": empirical_prediction[row_offset],
                    "equal_weight_empirical_score": empirical_test_score[row_offset],
                    "direction_constrained_ridge_prediction": ridge_prediction[row_offset],
                    "n_empirical_features_observed": observed_count,
                    "all_six_features_observed": observed_count == len(FEATURES),
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
    pooled = predictions
    metric_rows.extend(
        [
            _metric_row(pooled["observed_global_T1"].to_numpy(), pooled["mean_baseline_prediction"].to_numpy(), "mean_baseline", "pooled"),
            _metric_row(pooled["observed_global_T1"].to_numpy(), pooled["equal_weight_empirical_prediction"].to_numpy(), "equal_weight_empirical_score", "pooled"),
            _metric_row(pooled["observed_global_T1"].to_numpy(), pooled["direction_constrained_ridge_prediction"].to_numpy(), "direction_constrained_ridge", "pooled"),
        ]
    )
    patient_predictions = (
        predictions.groupby(["Subject_ID_D", "Subject_ID_N"], dropna=False)
        .agg(
            observed_global_T1=("observed_global_T1", "first"),
            mean_baseline_prediction=("mean_baseline_prediction", "mean"),
            equal_weight_empirical_prediction=("equal_weight_empirical_prediction", "mean"),
            direction_constrained_ridge_prediction=("direction_constrained_ridge_prediction", "mean"),
            mean_empirical_score=("equal_weight_empirical_score", "mean"),
            n_empirical_features_observed=("n_empirical_features_observed", "first"),
            all_six_features_observed=("all_six_features_observed", "first"),
        )
        .reset_index()
    )
    metrics = pd.DataFrame(metric_rows)
    predictions.to_csv(PREDICTIONS_PATH, index=False)
    patient_predictions.to_csv(PATIENT_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    pd.DataFrame(coefficient_rows).to_csv(COEFFICIENT_PATH, index=False)

    pooled_metrics = metrics[metrics["analysis_scope"].eq("pooled")]
    lines = [
        "# Exploratory Empirical Findings",
        "",
        "This phase models observed `global_T1` using only six features selected from the exploratory Phase 11 baseline-severity comparison.",
        "",
        "## Selected findings",
        "",
        "The six features and their exploratory directions are fixed from the source comparison table. P-values are used for transparent reporting and feature selection; they are not used as predictive weights.",
        "",
        "## Model protocol",
        "",
        "- Missing values are imputed with the training-fold median. Missingness indicators are not added, so acquisition coverage is not intentionally treated as phenotype.",
        "- Each oriented feature is centered by its training-fold median and divided by its training-fold IQR. This is the minimum scaling needed to combine milliseconds and event counts without one unit dominating.",
        "- The equal-weight empirical score averages the six robust oriented features and uses a positive calibration to T1.",
        "- The primary direction-constrained Ridge uses only the six oriented features and positive coefficients. Therefore, a feature cannot reverse its observed direction in the fitted estimate.",
        "- All results are compared with the same fold-local mean baseline using repeated 5-fold cross-validation.",
        "",
        "## Pooled results",
        "",
    ]
    for row in pooled_metrics.itertuples():
        lines.append(f"- {row.model}: RMSE `{row.rmse:.3f}`, MAE `{row.mae:.3f}`, R2 `{row.r2:.3f}`.")
    lines.extend(
        [
            "",
            "## Important limitation",
            "",
            f"Only {int(x_raw.notna().all(axis=1).sum())} of {len(x_raw)} patients have all six features observed. Three call features have only 14 observed patients each. Feature-wise median imputation allows all patients to remain in the exploratory model, but the call-related contribution is supported by very sparse data.",
            "",
            "This is an exploratory empirical model, not a confirmatory clinical prediction model. The feature selection and directions were discovered in the same 81-patient cohort used for evaluation, so the cross-validated results can still be optimistic.",
        ]
    )
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"patients: {len(dataset)}")
    print(f"complete_six_features: {int(x_raw.notna().all(axis=1).sum())}")
    print(pooled_metrics[["model", "n_predictions", "rmse", "mae", "r2"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
