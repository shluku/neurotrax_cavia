from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "output/analysis_candidates/phase4_t1_baseline"
DATASET_PATH = DATA_DIR / "phase4_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_t1_baseline_feature_metadata.csv"
OUT_DIR = DATA_DIR / "model_t1_ridge"

PREDICTIONS_PATH = OUT_DIR / "phase4_t1_ridge_predictions.csv"
METRICS_PATH = OUT_DIR / "phase4_t1_ridge_metrics.csv"
FEATURE_SET_PATH = OUT_DIR / "phase4_t1_ridge_feature_set.csv"
README_PATH = OUT_DIR / "README_phase4_t1_ridge.md"

TARGET = "global_T1"
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260726
ALPHAS = np.logspace(-3, 4, 30)


def metric_rows(y_true: np.ndarray, prediction: np.ndarray, model: str, repeat: int | str) -> dict[str, object]:
    return {
        "analysis_scope": "repeat" if repeat != "pooled" else "pooled",
        "repeat": repeat,
        "model": model,
        "n_predictions": len(y_true),
        "rmse": float(np.sqrt(mean_squared_error(y_true, prediction))),
        "mae": float(mean_absolute_error(y_true, prediction)),
        "r2": float(r2_score(y_true, prediction)),
        "actual_mean": float(np.mean(y_true)),
        "prediction_mean": float(np.mean(prediction)),
    }


def build_pipeline() -> Pipeline:
    inner_cv = KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE)
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
            ("ridge", RidgeCV(alphas=ALPHAS, cv=inner_cv, scoring="neg_root_mean_squared_error")),
        ]
    )


def build_readme(feature_set: pd.DataFrame, metrics: pd.DataFrame, predictions: pd.DataFrame) -> str:
    primary = int(feature_set["model_inclusion"].eq("primary").sum())
    non_primary = int(feature_set["model_inclusion"].ne("primary").sum())
    pooled = metrics[metrics["analysis_scope"] == "pooled"].set_index("model")
    lines = [
        "# Phase 4 T1 Ridge Model",
        "",
        "This is the first exploratory patient-level model for Outcome 1. It compares a training-set mean predictor with ridge regression for continuous `global_T1`.",
        "",
        "## Design",
        "",
        f"- Patients with non-missing `global_T1`: `{predictions['Subject_ID_D'].nunique()}`.",
        f"- Primary features: `{primary}`.",
        f"- Non-primary features retained for sensitivity analysis: `{non_primary}`.",
        f"- Outer validation: repeated `{N_SPLITS}`-fold cross-validation, `{N_REPEATS}` repeats.",
        "- Ridge alpha: selected inside each outer training fold using 4-fold inner cross-validation.",
        "- Preprocessing: training-fold median imputation, missingness indicators, then standardization.",
        "- The reference mean predictor uses only the training-fold target mean.",
        "",
        "## Pooled Cross-Validated Results",
        "",
    ]
    for model in ["mean_baseline", "ridge"]:
        if model in pooled.index:
            row = pooled.loc[model]
            lines.append(f"- `{model}`: RMSE `{row['rmse']:.3f}`, MAE `{row['mae']:.3f}`, R2 `{row['r2']:.3f}`.")
    if {"mean_baseline", "ridge"}.issubset(pooled.index):
        lines.append(f"- Ridge pooled RMSE minus mean-baseline pooled RMSE: `{pooled.loc['ridge', 'rmse'] - pooled.loc['mean_baseline', 'rmse']:.3f}`.")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "These are exploratory cross-validated associations in a small proof-of-concept cohort. They are not an externally validated prediction estimate. Repeated cross-validation gives a stability view, not an independent test-set result.",
            "",
            "The non-primary features are not discarded. Adjusted-window features, low-coverage T1-week features, and zero-coverage features are retained in the feature-set audit and should be tested in separately labeled sensitivity analyses.",
            "",
            "## Files",
            "",
            "- `phase4_t1_ridge_predictions.csv`: fold-level predictions for both models.",
            "- `phase4_t1_ridge_metrics.csv`: per-repeat and pooled metrics.",
            "- `phase4_t1_ridge_feature_set.csv`: primary versus sensitivity feature decisions.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    feature_set = metadata[["source_table", "feature_name", "feature_family", "window_class", "missing_percent", "primary_model_recommendation"]].copy()
    feature_set["model_inclusion"] = np.where(
        feature_set["primary_model_recommendation"].eq("include_primary"), "primary", "sensitivity_only"
    )

    target = pd.to_numeric(dataset[TARGET], errors="coerce")
    valid = target.notna()
    dataset = dataset.loc[valid].reset_index(drop=True)
    y = target.loc[valid].to_numpy(dtype=float)
    features = feature_set.loc[feature_set["model_inclusion"].eq("primary"), "feature_name"].tolist()
    X = dataset[features].apply(pd.to_numeric, errors="coerce")

    feature_set["n_model_patients"] = len(dataset)
    feature_set["used_in_primary_model"] = feature_set["model_inclusion"].eq("primary")
    feature_set.to_csv(FEATURE_SET_PATH, index=False)

    predictions: list[dict[str, object]] = []
    metric_rows_out: list[dict[str, object]] = []
    outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
    repeat_buffers: dict[int, dict[str, list[float]]] = {}

    for split_index, (train_idx, test_idx) in enumerate(outer.split(X), start=0):
        repeat = split_index // N_SPLITS + 1
        fold = split_index % N_SPLITS + 1
        y_train = y[train_idx]
        y_test = y[test_idx]
        mean_prediction = np.repeat(y_train.mean(), len(test_idx))

        model = build_pipeline()
        model.fit(X.iloc[train_idx], y_train)
        ridge_prediction = model.predict(X.iloc[test_idx])
        ridge_alpha = float(model.named_steps["ridge"].alpha_)

        repeat_buffers.setdefault(repeat, {"actual": [], "mean": [], "ridge": []})
        repeat_buffers[repeat]["actual"].extend(y_test.tolist())
        repeat_buffers[repeat]["mean"].extend(mean_prediction.tolist())
        repeat_buffers[repeat]["ridge"].extend(ridge_prediction.tolist())

        for row_index, row_pos in enumerate(test_idx):
            predictions.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "Subject_ID_D": dataset.loc[row_pos, "Subject_ID_D"],
                    "Subject_ID_N": dataset.loc[row_pos, "Subject_ID_N"],
                    "actual_global_T1": y_test[row_index],
                    "mean_baseline_prediction": mean_prediction[row_index],
                    "ridge_prediction": ridge_prediction[row_index],
                    "ridge_alpha": ridge_alpha,
                    "n_train": len(train_idx),
                    "n_test": len(test_idx),
                }
            )

    predictions_df = pd.DataFrame(predictions)
    for repeat, values in repeat_buffers.items():
        actual = np.asarray(values["actual"])
        metric_rows_out.append(metric_rows(actual, np.asarray(values["mean"]), "mean_baseline", repeat))
        metric_rows_out.append(metric_rows(actual, np.asarray(values["ridge"]), "ridge", repeat))

    pooled_actual = np.tile(y, N_REPEATS)
    pooled_mean = predictions_df["mean_baseline_prediction"].to_numpy(dtype=float)
    pooled_ridge = predictions_df["ridge_prediction"].to_numpy(dtype=float)
    metric_rows_out.append(metric_rows(pooled_actual, pooled_mean, "mean_baseline", "pooled"))
    metric_rows_out.append(metric_rows(pooled_actual, pooled_ridge, "ridge", "pooled"))
    metrics_df = pd.DataFrame(metric_rows_out)

    predictions_df.to_csv(PREDICTIONS_PATH, index=False)
    metrics_df.to_csv(METRICS_PATH, index=False)
    README_PATH.write_text(build_readme(feature_set, metrics_df, predictions_df), encoding="utf-8")

    pooled = metrics_df[metrics_df["analysis_scope"] == "pooled"].set_index("model")
    print(f"patients: {len(dataset)}")
    print(f"primary_features: {len(features)}")
    print(f"predictions: {len(predictions_df)}")
    print(f"mean_baseline_rmse: {pooled.loc['mean_baseline', 'rmse']:.4f}")
    print(f"ridge_rmse: {pooled.loc['ridge', 'rmse']:.4f}")
    print(f"ridge_rmse_minus_mean: {pooled.loc['ridge', 'rmse'] - pooled.loc['mean_baseline', 'rmse']:.4f}")
    print(f"outputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
