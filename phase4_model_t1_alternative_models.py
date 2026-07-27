from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNetCV, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.cross_decomposition import PLSRegression
from sklearn.preprocessing import SplineTransformer, StandardScaler


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "output/analysis_candidates/phase4_t1_baseline"
DATASET_PATH = DATA_DIR / "phase4_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_t1_baseline_feature_metadata.csv"
OUT_DIR = DATA_DIR / "model_t1_alternatives"
PREDICTIONS_PATH = OUT_DIR / "phase4_t1_alternative_predictions.csv"
PATIENT_PATH = OUT_DIR / "phase4_t1_alternative_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "phase4_t1_alternative_metrics.csv"
README_PATH = OUT_DIR / "README_phase4_t1_alternative_models.md"

TARGET = "global_T1"
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260726
ALPHAS = np.logspace(-3, 4, 30)
ELASTIC_ALPHAS = np.logspace(-1, 4, 12)


def preprocess(X_train: pd.DataFrame, X_test: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    imputer = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    train_imputed = imputer.fit_transform(X_train)
    test_imputed = imputer.transform(X_test)
    scaler = StandardScaler()
    return scaler.fit_transform(train_imputed), scaler.transform(test_imputed)


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
    max_components = min(10, X_train.shape[1], X_train.shape[0] - 2)
    inner = KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE)
    component_scores: list[tuple[int, float]] = []
    for n_components in range(1, max_components + 1):
        errors: list[float] = []
        for train_idx, validation_idx in inner.split(X_train):
            model = PLSRegression(n_components=n_components, scale=False, max_iter=2000)
            model.fit(X_train[train_idx], y_train[train_idx])
            errors.append(float(np.mean((y_train[validation_idx] - model.predict(X_train[validation_idx]).ravel()) ** 2)))
        component_scores.append((n_components, float(np.mean(errors))))
    best_components = min(component_scores, key=lambda item: item[1])[0]
    model = PLSRegression(n_components=best_components, scale=False, max_iter=2000)
    model.fit(X_train, y_train)
    return model.predict(X_test).ravel()


def fit_spline_ridge(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> np.ndarray:
    spline = SplineTransformer(n_knots=4, degree=2, knots="quantile", include_bias=False)
    train_spline = spline.fit_transform(X_train)
    test_spline = spline.transform(X_test)
    model = RidgeCV(alphas=ALPHAS, cv=KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE), scoring="neg_root_mean_squared_error")
    model.fit(train_spline, y_train)
    return model.predict(test_spline)


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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    features = metadata.loc[
        metadata["primary_model_recommendation"] == "include_primary", "feature_name"
    ].tolist()
    target = pd.to_numeric(dataset[TARGET], errors="coerce")
    valid = target.notna()
    dataset = dataset.loc[valid].reset_index(drop=True)
    y = target.loc[valid].to_numpy(dtype=float)
    X = dataset[features].apply(pd.to_numeric, errors="coerce")

    outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
    predictions: list[dict[str, object]] = []
    repeat_buffers: dict[tuple[int, str], dict[str, list[float]]] = {}
    model_names = ["elastic_net", "pls", "spline_ridge"]

    for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
        repeat = split_index // N_SPLITS + 1
        fold = split_index % N_SPLITS + 1
        X_train, X_test = preprocess(X.iloc[train_idx], X.iloc[test_idx])
        y_train = y[train_idx]
        y_test = y[test_idx]
        baseline = np.repeat(y_train.mean(), len(test_idx))
        predictions_by_model = {
            "elastic_net": fit_elastic_net(X_train, y_train, X_test),
            "pls": fit_pls(X_train, y_train, X_test),
            "spline_ridge": fit_spline_ridge(X_train, y_train, X_test),
        }
        for model_name, model_prediction in predictions_by_model.items():
            repeat_buffers.setdefault((repeat, model_name), {"actual": [], "prediction": []})
            repeat_buffers[(repeat, model_name)]["actual"].extend(y_test.tolist())
            repeat_buffers[(repeat, model_name)]["prediction"].extend(model_prediction.tolist())
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
    patient_df = (
        predictions_df.groupby(["Subject_ID_D", "Subject_ID_N"], dropna=False)
        .agg(
            actual_global_T1=("actual_global_T1", "first"),
            mean_baseline_prediction=("mean_baseline_prediction", "mean"),
            elastic_net_prediction=("elastic_net_prediction", "mean"),
            pls_prediction=("pls_prediction", "mean"),
            spline_ridge_prediction=("spline_ridge_prediction", "mean"),
        )
        .reset_index()
    )
    metrics: list[dict[str, object]] = []
    for (repeat, model_name), values in repeat_buffers.items():
        metrics.append(metric_row(np.asarray(values["actual"]), np.asarray(values["prediction"]), model_name, repeat))
    for repeat, repeat_frame in predictions_df.groupby("repeat"):
        metrics.append(
            metric_row(
                repeat_frame["actual_global_T1"].to_numpy(),
                repeat_frame["mean_baseline_prediction"].to_numpy(),
                "mean_baseline",
                int(repeat),
            )
        )
    pooled_actual = np.tile(y, N_REPEATS)
    metrics.append(metric_row(pooled_actual, predictions_df["mean_baseline_prediction"].to_numpy(), "mean_baseline", "pooled"))
    for model_name in model_names:
        metrics.append(metric_row(pooled_actual, predictions_df[f"{model_name}_prediction"].to_numpy(), model_name, "pooled"))
    metrics_df = pd.DataFrame(metrics)
    predictions_df.to_csv(PREDICTIONS_PATH, index=False)
    patient_df.to_csv(PATIENT_PATH, index=False)
    metrics_df.to_csv(METRICS_PATH, index=False)
    pooled = metrics_df.query("analysis_scope == 'pooled'")
    baseline_row = metrics_df.query("analysis_scope == 'pooled' and model == 'mean_baseline'").iloc[0].to_dict()
    README_PATH.write_text(
        "# Phase 4 Alternative T1 Models\n\n"
        "Elastic Net, PLS, and spline Ridge are exploratory alternatives using the same primary 37 features, "
        "fold-local median imputation/missingness indicators, standardization, and repeated outer cross-validation. "
        "Spline Ridge allows smooth nonlinear feature effects.\n\n"
        f"Mean-baseline RMSE: `{baseline_row['rmse']:.3f}`\n\n"
        + "\n".join(
            f"{row.model} RMSE: `{row.rmse:.3f}`"
            for row in pooled.itertuples()
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"patients: {len(dataset)}")
    print("mean_baseline", round(baseline_row["rmse"], 4))
    print(pooled[["model", "rmse", "mae", "r2"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
