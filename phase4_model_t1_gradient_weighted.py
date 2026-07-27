from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "output/analysis_candidates/phase4_t1_baseline"
DATASET_PATH = DATA_DIR / "phase4_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_t1_baseline_feature_metadata.csv"
OUT_DIR = DATA_DIR / "model_t1_gradient_weighted"
PREDICTIONS_PATH = OUT_DIR / "phase4_t1_gradient_weighted_predictions.csv"
PATIENT_PATH = OUT_DIR / "phase4_t1_gradient_weighted_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "phase4_t1_gradient_weighted_metrics.csv"
WEIGHTS_PATH = OUT_DIR / "phase4_t1_gradient_weights.csv"
README_PATH = OUT_DIR / "README_phase4_t1_gradient_weighted.md"

TARGET = "global_T1"
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260726
ALPHAS = np.logspace(-3, 4, 30)


def fold_gradient_weights(X_train: pd.DataFrame, y_train: np.ndarray, features: list[str]) -> np.ndarray:
    """Give stronger monotonic T1 features a modest, training-fold-only multiplier."""
    correlations = []
    for feature in features:
        values = pd.to_numeric(X_train[feature], errors="coerce")
        paired = pd.DataFrame({"feature": values, "target": y_train}).dropna()
        if len(paired) < 5 or paired["feature"].nunique() < 2:
            correlations.append(0.0)
        else:
            correlations.append(abs(float(paired["feature"].corr(paired["target"], method="spearman"))))
    # Weight range is 1.0 to 2.0. Missingness indicators remain unweighted.
    return 1.0 + np.asarray(correlations, dtype=float)


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
    weight_rows: list[dict[str, object]] = []
    repeat_buffers: dict[int, dict[str, list[float]]] = {}

    for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
        repeat = split_index // N_SPLITS + 1
        fold = split_index % N_SPLITS + 1
        X_train_raw = X.iloc[train_idx]
        X_test_raw = X.iloc[test_idx]
        y_train = y[train_idx]
        y_test = y[test_idx]

        imputer = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
        X_train_imputed = imputer.fit_transform(X_train_raw)
        X_test_imputed = imputer.transform(X_test_raw)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_imputed)
        X_test_scaled = scaler.transform(X_test_imputed)
        feature_weights = fold_gradient_weights(X_train_raw, y_train, features)
        all_weights = np.concatenate([feature_weights, np.ones(X_train_scaled.shape[1] - len(features))])
        X_train_weighted = X_train_scaled * all_weights
        X_test_weighted = X_test_scaled * all_weights

        inner_cv = KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE)
        model = RidgeCV(alphas=ALPHAS, cv=inner_cv, scoring="neg_root_mean_squared_error")
        model.fit(X_train_weighted, y_train)
        ridge_prediction = model.predict(X_test_weighted)
        mean_prediction = np.repeat(y_train.mean(), len(test_idx))
        repeat_buffers.setdefault(repeat, {"actual": [], "mean": [], "weighted": []})
        repeat_buffers[repeat]["actual"].extend(y_test.tolist())
        repeat_buffers[repeat]["mean"].extend(mean_prediction.tolist())
        repeat_buffers[repeat]["weighted"].extend(ridge_prediction.tolist())

        for feature, weight in zip(features, feature_weights):
            weight_rows.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "feature": feature,
                    "gradient_weight": float(weight),
                    "extra_weight": float(weight - 1.0),
                }
            )
        for row_index, row_pos in enumerate(test_idx):
            predictions.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "Subject_ID_D": dataset.loc[row_pos, "Subject_ID_D"],
                    "Subject_ID_N": dataset.loc[row_pos, "Subject_ID_N"],
                    "actual_global_T1": y_test[row_index],
                    "mean_baseline_prediction": mean_prediction[row_index],
                    "gradient_weighted_prediction": ridge_prediction[row_index],
                    "ridge_alpha": float(model.alpha_),
                    "n_features": len(features),
                    "n_train": len(train_idx),
                    "n_test": len(test_idx),
                }
            )

    predictions_df = pd.DataFrame(predictions)
    patient_df = (
        predictions_df.groupby(["Subject_ID_D", "Subject_ID_N"], dropna=False)
        .agg(
            actual_global_T1=("actual_global_T1", "first"),
            mean_baseline_prediction=("mean_baseline_prediction", "mean"),
            gradient_weighted_prediction=("gradient_weighted_prediction", "mean"),
        )
        .reset_index()
    )
    metrics: list[dict[str, object]] = []
    for repeat, values in repeat_buffers.items():
        actual = np.asarray(values["actual"])
        metrics.append(metric_row(actual, np.asarray(values["mean"]), "mean_baseline", repeat))
        metrics.append(metric_row(actual, np.asarray(values["weighted"]), "gradient_weighted_ridge", repeat))
    pooled_actual = np.tile(y, N_REPEATS)
    metrics.append(metric_row(pooled_actual, predictions_df["mean_baseline_prediction"].to_numpy(), "mean_baseline", "pooled"))
    metrics.append(metric_row(pooled_actual, predictions_df["gradient_weighted_prediction"].to_numpy(), "gradient_weighted_ridge", "pooled"))

    predictions_df.to_csv(PREDICTIONS_PATH, index=False)
    patient_df.to_csv(PATIENT_PATH, index=False)
    pd.DataFrame(metrics).to_csv(METRICS_PATH, index=False)
    pd.DataFrame(weight_rows).to_csv(WEIGHTS_PATH, index=False)
    pooled = pd.DataFrame(metrics).query("analysis_scope == 'pooled'").set_index("model")
    README_PATH.write_text(
        "# Phase 4 Gradient-Weighted T1 Ridge\n\n"
        "This is a separate exploratory comparison to the primary 37-feature ridge model. "
        "Within each outer training fold, each feature receives a multiplier of `1 + abs(Spearman rho)` "
        "based only on that fold's training patients. The range is 1.0 to 2.0; missingness indicators are not weighted. "
        "The weighted model is still trained and evaluated with repeated 5-fold cross-validation and fold-local imputation/scaling.\n\n"
        f"Pooled mean-baseline RMSE: `{pooled.loc['mean_baseline', 'rmse']:.3f}`\n\n"
        f"Pooled gradient-weighted ridge RMSE: `{pooled.loc['gradient_weighted_ridge', 'rmse']:.3f}`\n",
        encoding="utf-8",
    )
    print(f"patients: {len(dataset)}")
    print(pd.DataFrame(metrics).query("analysis_scope == 'pooled'").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
