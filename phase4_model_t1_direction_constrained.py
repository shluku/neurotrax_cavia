from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.preprocessing import StandardScaler

from phase4_model_t1_slope_selected import slope_rank_features


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "output/analysis_candidates/phase4_t1_baseline"
DATASET_PATH = DATA_DIR / "phase4_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_t1_baseline_feature_metadata.csv"
OUT_DIR = DATA_DIR / "model_t1_direction_constrained"
PREDICTIONS_PATH = OUT_DIR / "phase4_t1_direction_constrained_predictions.csv"
PATIENT_PATH = OUT_DIR / "phase4_t1_direction_constrained_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "phase4_t1_direction_constrained_metrics.csv"
SELECTION_PATH = OUT_DIR / "phase4_t1_direction_constrained_features_by_fold.csv"
COEFFICIENT_PATH = OUT_DIR / "phase4_t1_direction_constrained_coefficients.csv"
README_PATH = OUT_DIR / "README_phase4_t1_direction_constrained.md"

TARGET = "global_T1"
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260726
ALPHAS = np.logspace(-3, 4, 30)


def fit_bounded_ridge(X: np.ndarray, y: np.ndarray, alpha: float, signs: list[int]) -> np.ndarray:
    y_mean = float(y.mean())
    y_centered = y - y_mean
    augmented_X = np.vstack([X, np.sqrt(alpha) * np.eye(X.shape[1])])
    augmented_y = np.concatenate([y_centered, np.zeros(X.shape[1])])
    lower = np.asarray([0.0 if sign > 0 else -np.inf for sign in signs], dtype=float)
    upper = np.asarray([0.0 if sign < 0 else np.inf for sign in signs], dtype=float)
    result = lsq_linear(
        augmented_X,
        augmented_y,
        bounds=(lower, upper),
        method="trf",
        lsmr_tol="auto",
        max_iter=2000,
    )
    if not result.success:
        raise RuntimeError(f"Bounded ridge optimization failed: {result.message}")
    return np.asarray(result.x, dtype=float)


def choose_alpha(X: np.ndarray, y: np.ndarray, signs: list[int]) -> float:
    inner = KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE)
    scores: list[float] = []
    for alpha in ALPHAS:
        fold_errors: list[float] = []
        for train_idx, test_idx in inner.split(X):
            beta = fit_bounded_ridge(X[train_idx], y[train_idx], float(alpha), signs)
            prediction = y[train_idx].mean() + X[test_idx] @ beta
            fold_errors.append(float(np.mean((y[test_idx] - prediction) ** 2)))
        scores.append(float(np.mean(fold_errors)))
    return float(ALPHAS[int(np.argmin(scores))])


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
    selection_rows: list[dict[str, object]] = []
    coefficient_rows: list[dict[str, object]] = []
    repeat_buffers: dict[int, dict[str, list[float]]] = {}

    for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
        repeat = split_index // N_SPLITS + 1
        fold = split_index % N_SPLITS + 1
        X_train_raw = X.iloc[train_idx]
        X_test_raw = X.iloc[test_idx]
        y_train = y[train_idx]
        y_test = y[test_idx]
        selected, ranked = slope_rank_features(X_train_raw, y_train, features)
        slope_lookup = ranked.set_index("feature")["slope"].to_dict()
        signs = [1 if slope_lookup[feature] > 0 else -1 for feature in selected]
        for _, row in ranked.iterrows():
            selection_rows.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "feature": row["feature"],
                    "slope": row["slope"],
                    "selected": row["feature"] in selected,
                    "coefficient_constraint": ">= 0" if row["feature"] in selected and row["slope"] > 0 else "<= 0" if row["feature"] in selected else "not selected",
                }
            )

        imputer = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
        X_train_imputed = imputer.fit_transform(X_train_raw[selected])
        X_test_imputed = imputer.transform(X_test_raw[selected])
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_imputed)
        X_test_scaled = scaler.transform(X_test_imputed)
        signs_with_indicators = signs + [0] * (X_train_scaled.shape[1] - len(selected))
        alpha = choose_alpha(X_train_scaled, y_train, signs_with_indicators)
        beta = fit_bounded_ridge(X_train_scaled, y_train, alpha, signs_with_indicators)
        prediction = y_train.mean() + X_test_scaled @ beta
        baseline = np.repeat(y_train.mean(), len(test_idx))
        repeat_buffers.setdefault(repeat, {"actual": [], "baseline": [], "constrained": []})
        repeat_buffers[repeat]["actual"].extend(y_test.tolist())
        repeat_buffers[repeat]["baseline"].extend(baseline.tolist())
        repeat_buffers[repeat]["constrained"].extend(prediction.tolist())
        coefficient_names = selected + [f"missing__{feature}" for feature in selected]
        for term_name, coefficient, sign in zip(coefficient_names, beta, signs_with_indicators):
            coefficient_rows.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "term_name": term_name,
                    "coefficient": float(coefficient),
                    "constraint": ">= 0" if sign > 0 else "<= 0" if sign < 0 else "unconstrained",
                    "alpha": alpha,
                }
            )
        selected_text = "|".join(selected)
        for row_index, row_pos in enumerate(test_idx):
            predictions.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "Subject_ID_D": dataset.loc[row_pos, "Subject_ID_D"],
                    "Subject_ID_N": dataset.loc[row_pos, "Subject_ID_N"],
                    "actual_global_T1": y_test[row_index],
                    "mean_baseline_prediction": baseline[row_index],
                    "direction_constrained_prediction": prediction[row_index],
                    "selected_features": selected_text,
                    "ridge_alpha": alpha,
                }
            )

    predictions_df = pd.DataFrame(predictions)
    patient_df = (
        predictions_df.groupby(["Subject_ID_D", "Subject_ID_N"], dropna=False)
        .agg(
            actual_global_T1=("actual_global_T1", "first"),
            mean_baseline_prediction=("mean_baseline_prediction", "mean"),
            direction_constrained_prediction=("direction_constrained_prediction", "mean"),
        )
        .reset_index()
    )
    metrics: list[dict[str, object]] = []
    for repeat, values in repeat_buffers.items():
        actual = np.asarray(values["actual"])
        metrics.append(metric_row(actual, np.asarray(values["baseline"]), "mean_baseline", repeat))
        metrics.append(metric_row(actual, np.asarray(values["constrained"]), "direction_constrained_ridge", repeat))
    pooled_actual = np.tile(y, N_REPEATS)
    metrics.append(metric_row(pooled_actual, predictions_df["mean_baseline_prediction"].to_numpy(), "mean_baseline", "pooled"))
    metrics.append(metric_row(pooled_actual, predictions_df["direction_constrained_prediction"].to_numpy(), "direction_constrained_ridge", "pooled"))

    predictions_df.to_csv(PREDICTIONS_PATH, index=False)
    patient_df.to_csv(PATIENT_PATH, index=False)
    pd.DataFrame(metrics).to_csv(METRICS_PATH, index=False)
    pd.DataFrame(selection_rows).to_csv(SELECTION_PATH, index=False)
    pd.DataFrame(coefficient_rows).to_csv(COEFFICIENT_PATH, index=False)
    pooled = pd.DataFrame(metrics).query("analysis_scope == 'pooled'").set_index("model")
    README_PATH.write_text(
        "# Phase 4 Direction-Constrained T1 Ridge\n\n"
        "This is a separate exploratory model using the same fold-local eight-feature slope selection as the "
        "slope-selected model. Positive-slope features have coefficients constrained to be nonnegative; "
        "negative-slope features have coefficients constrained to be nonpositive. Missingness indicators are unconstrained. "
        "The ridge penalty is selected by inner cross-validation.\n\n"
        f"Pooled mean-baseline RMSE: `{pooled.loc['mean_baseline', 'rmse']:.3f}`\n\n"
        f"Pooled direction-constrained ridge RMSE: `{pooled.loc['direction_constrained_ridge', 'rmse']:.3f}`\n",
        encoding="utf-8",
    )
    print(f"patients: {len(dataset)}")
    print(pd.DataFrame(metrics).query("analysis_scope == 'pooled'").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
