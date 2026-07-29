"""Exploratory alternative models for the isolated Phase 4 10-day T1 cohort."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.cross_decomposition import PLSRegression
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNetCV, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.preprocessing import SplineTransformer, StandardScaler

if Path("/opt/homebrew/opt/libomp/lib").exists():
    os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/opt/libomp/lib")

from xgboost import XGBRegressor


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "output/analysis_candidates/phase4_10day_t1_baseline"
DATASET_PATH = DATA_DIR / "phase4_10day_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_10day_t1_baseline_feature_metadata.csv"
OUT_DIR = DATA_DIR / "other_models"
PREDICTIONS_PATH = OUT_DIR / "phase4_10day_other_models_predictions.csv"
PATIENT_PATH = OUT_DIR / "phase4_10day_other_models_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "phase4_10day_other_models_metrics.csv"
IMPORTANCE_PATH = OUT_DIR / "phase4_10day_other_models_permutation_importance.csv"
README_PATH = OUT_DIR / "README_phase4_10day_other_models.md"

TARGET = "global_T1"
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260729
ALPHAS = np.logspace(-2, 5, 30)
ELASTIC_ALPHAS = np.logspace(-1, 4, 14)


def metric_row(actual: np.ndarray, predicted: np.ndarray, model: str, repeat: int | str) -> dict[str, object]:
    return {
        "analysis_scope": "repeat" if repeat != "pooled" else "pooled",
        "repeat": repeat,
        "model": model,
        "n_predictions": len(actual),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
    }


def preprocess(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    imputer = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    train_imputed = imputer.fit_transform(X_train)
    test_imputed = imputer.transform(X_test)
    names = list(X_train.columns)
    if getattr(imputer, "indicator_", None) is not None:
        names.extend(f"missing__{name}" for name in imputer.indicator_.features_)
    scaler = StandardScaler()
    return scaler.fit_transform(train_imputed), scaler.transform(test_imputed), names


def fit_elastic_net(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> np.ndarray:
    model = ElasticNetCV(
        l1_ratio=[0.05, 0.2, 0.5, 0.8, 0.95, 1.0],
        alphas=ELASTIC_ALPHAS,
        cv=KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE),
        max_iter=10000,
        tol=1e-3,
        selection="random",
        random_state=RANDOM_STATE,
    )
    model.fit(X_train, y_train)
    return model.predict(X_test)


def fit_pls(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> np.ndarray:
    max_components = min(8, X_train.shape[1], X_train.shape[0] - 2)
    inner = KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE)
    scores: list[tuple[int, float]] = []
    for n_components in range(1, max_components + 1):
        errors = []
        for train_idx, validation_idx in inner.split(X_train):
            model = PLSRegression(n_components=n_components, scale=False, max_iter=2000)
            model.fit(X_train[train_idx], y_train[train_idx])
            prediction = model.predict(X_train[validation_idx]).ravel()
            errors.append(float(np.mean((y_train[validation_idx] - prediction) ** 2)))
        scores.append((n_components, float(np.mean(errors))))
    best_components = min(scores, key=lambda item: item[1])[0]
    model = PLSRegression(n_components=best_components, scale=False, max_iter=2000)
    model.fit(X_train, y_train)
    return model.predict(X_test).ravel()


def fit_spline_ridge(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> np.ndarray:
    spline = SplineTransformer(n_knots=4, degree=2, knots="quantile", include_bias=False)
    train_spline = spline.fit_transform(X_train)
    test_spline = spline.transform(X_test)
    model = RidgeCV(
        alphas=ALPHAS,
        cv=KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE),
        scoring="neg_root_mean_squared_error",
    )
    model.fit(train_spline, y_train)
    return model.predict(test_spline)


def fit_tree_models(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> dict[str, np.ndarray]:
    models = {
        "random_forest": RandomForestRegressor(
            n_estimators=300,
            max_depth=2,
            min_samples_leaf=6,
            max_features=0.7,
            random_state=RANDOM_STATE,
            n_jobs=1,
        ),
        "extra_trees": ExtraTreesRegressor(
            n_estimators=300,
            max_depth=2,
            min_samples_leaf=6,
            max_features=0.7,
            random_state=RANDOM_STATE,
            n_jobs=1,
        ),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=100,
            learning_rate=0.03,
            max_leaf_nodes=5,
            min_samples_leaf=8,
            l2_regularization=10.0,
            random_state=RANDOM_STATE,
        ),
        "xgboost": XGBRegressor(
            n_estimators=100,
            max_depth=2,
            learning_rate=0.03,
            min_child_weight=8,
            subsample=0.8,
            colsample_bytree=0.7,
            reg_alpha=1.0,
            reg_lambda=10.0,
            objective="reg:squarederror",
            eval_metric="rmse",
            tree_method="hist",
            n_jobs=1,
            random_state=RANDOM_STATE,
            verbosity=0,
        ),
    }
    predictions = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        predictions[name] = model.predict(X_test)
    return predictions


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    features = metadata["feature_name"].dropna().tolist()
    target = pd.to_numeric(dataset[TARGET], errors="coerce")
    valid = target.notna()
    dataset = dataset.loc[valid].reset_index(drop=True)
    y = target.loc[valid].to_numpy(dtype=float)
    X = dataset[features].apply(pd.to_numeric, errors="coerce")

    model_names = [
        "elastic_net",
        "pls",
        "spline_ridge",
        "random_forest",
        "extra_trees",
        "hist_gradient_boosting",
        "xgboost",
    ]
    outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
    predictions: list[dict[str, object]] = []
    repeat_buffers: dict[tuple[int, str], dict[str, list[float]]] = {}
    importance_rows: list[dict[str, object]] = []

    for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
        repeat = split_index // N_SPLITS + 1
        fold = split_index % N_SPLITS + 1
        X_train, X_test, feature_names = preprocess(X.iloc[train_idx], X.iloc[test_idx])
        y_train, y_test = y[train_idx], y[test_idx]
        baseline = np.repeat(y_train.mean(), len(test_idx))
        predictions_by_model = {
            "elastic_net": fit_elastic_net(X_train, y_train, X_test),
            "pls": fit_pls(X_train, y_train, X_test),
            "spline_ridge": fit_spline_ridge(X_train, y_train, X_test),
            **fit_tree_models(X_train, y_train, X_test),
        }
        for model_name, model_prediction in predictions_by_model.items():
            repeat_buffers.setdefault((repeat, model_name), {"actual": [], "prediction": []})
            repeat_buffers[(repeat, model_name)]["actual"].extend(y_test.tolist())
            repeat_buffers[(repeat, model_name)]["prediction"].extend(model_prediction.tolist())
        # Held-out permutation importance is recorded only for tree models on the first
        # repeated-CV pass. It is descriptive, not another feature-selection step, and is
        # never used to refit the remaining folds.
        if repeat == 1:
            for model_name in ["random_forest", "extra_trees", "hist_gradient_boosting", "xgboost"]:
                fitted_model = {
                "random_forest": RandomForestRegressor(
                    n_estimators=300, max_depth=2, min_samples_leaf=6, max_features=0.7,
                    random_state=RANDOM_STATE, n_jobs=1,
                ),
                "extra_trees": ExtraTreesRegressor(
                    n_estimators=300, max_depth=2, min_samples_leaf=6, max_features=0.7,
                    random_state=RANDOM_STATE, n_jobs=1,
                ),
                "hist_gradient_boosting": HistGradientBoostingRegressor(
                    max_iter=100, learning_rate=0.03, max_leaf_nodes=5, min_samples_leaf=8,
                    l2_regularization=10.0, random_state=RANDOM_STATE,
                ),
                "xgboost": XGBRegressor(
                    n_estimators=100, max_depth=2, learning_rate=0.03, min_child_weight=8,
                    subsample=0.8, colsample_bytree=0.7, reg_alpha=1.0, reg_lambda=10.0,
                    objective="reg:squarederror", eval_metric="rmse", tree_method="hist",
                    n_jobs=1, random_state=RANDOM_STATE, verbosity=0,
                ),
                }[model_name]
                fitted_model.fit(X_train, y_train)
                importance = permutation_importance(
                    fitted_model, X_test, y_test, scoring="neg_root_mean_squared_error", n_repeats=3,
                    random_state=RANDOM_STATE,
                )
                for name, mean, std in zip(feature_names, importance.importances_mean, importance.importances_std):
                    importance_rows.append({
                        "repeat": repeat, "fold": fold, "model": model_name,
                        "feature": name, "importance_mean": float(mean), "importance_std": float(std),
                    })
        for row_index, row_pos in enumerate(test_idx):
            row = {
                "repeat": repeat,
                "fold": fold,
                "Subject_ID_D": dataset.loc[row_pos, "Subject_ID_D"],
                "Subject_ID_N": dataset.loc[row_pos, "Subject_ID_N"],
                "actual_global_T1": y_test[row_index],
                "mean_baseline_prediction": baseline[row_index],
            }
            for model_name, model_prediction in predictions_by_model.items():
                row[f"{model_name}_prediction"] = model_prediction[row_index]
            predictions.append(row)

    predictions_df = pd.DataFrame(predictions)
    patient_df = predictions_df.groupby(["Subject_ID_D", "Subject_ID_N"], dropna=False).agg(
        actual_global_T1=("actual_global_T1", "first"),
        mean_baseline_prediction=("mean_baseline_prediction", "mean"),
        **{f"{name}_prediction": (f"{name}_prediction", "mean") for name in model_names},
    ).reset_index()
    metrics: list[dict[str, object]] = []
    for (repeat, model_name), values in repeat_buffers.items():
        metrics.append(metric_row(np.asarray(values["actual"]), np.asarray(values["prediction"]), model_name, repeat))
    for repeat, repeat_frame in predictions_df.groupby("repeat"):
        metrics.append(metric_row(
            repeat_frame["actual_global_T1"].to_numpy(),
            repeat_frame["mean_baseline_prediction"].to_numpy(),
            "mean_baseline", int(repeat),
        ))
    pooled_actual = np.tile(y, N_REPEATS)
    metrics.append(metric_row(pooled_actual, predictions_df["mean_baseline_prediction"].to_numpy(), "mean_baseline", "pooled"))
    for model_name in model_names:
        metrics.append(metric_row(pooled_actual, predictions_df[f"{model_name}_prediction"].to_numpy(), model_name, "pooled"))

    predictions_df.to_csv(PREDICTIONS_PATH, index=False)
    patient_df.to_csv(PATIENT_PATH, index=False)
    pd.DataFrame(metrics).to_csv(METRICS_PATH, index=False)
    pd.DataFrame(importance_rows).to_csv(IMPORTANCE_PATH, index=False)
    metrics_df = pd.DataFrame(metrics)
    pooled = metrics_df.query("analysis_scope == 'pooled'").sort_values("rmse")
    baseline_rmse = float(pooled.loc[pooled["model"] == "mean_baseline", "rmse"].iloc[0])
    README_PATH.write_text(
        "# Phase 4 10-Day Other Models\n\n"
        "This is an isolated exploratory phase using all selected 10-day features and 81 patients. "
        "Every preprocessing step is fit within the training fold. Models are intentionally conservative: "
        "shallow trees, minimum leaf sizes, strong regularization, and repeated 5-fold validation. "
        "Held-out permutation importance is reported descriptively for the first repeated-CV pass only. "
        "No model replaces the primary Phase 4 result.\n\n"
        f"Mean-baseline RMSE: `{baseline_rmse:.4f}`\n\n"
        + "\n".join(f"{row.model} RMSE: `{row.rmse:.4f}`" for row in pooled.itertuples())
        + "\n",
        encoding="utf-8",
    )
    print(f"patients: {len(dataset)}")
    print(pooled[["model", "rmse", "mae", "r2"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
