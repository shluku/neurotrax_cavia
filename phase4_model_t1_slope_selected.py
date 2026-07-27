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
OUT_DIR = DATA_DIR / "model_t1_slope_selected"
PREDICTIONS_PATH = OUT_DIR / "phase4_t1_slope_selected_predictions.csv"
PATIENT_PATH = OUT_DIR / "phase4_t1_slope_selected_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "phase4_t1_slope_selected_metrics.csv"
SELECTION_PATH = OUT_DIR / "phase4_t1_slope_selected_features_by_fold.csv"
README_PATH = OUT_DIR / "README_phase4_t1_slope_selected.md"

TARGET = "global_T1"
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260726
ALPHAS = np.logspace(-3, 4, 30)


def slope_rank_features(X_train: pd.DataFrame, y_train: np.ndarray, features: list[str]) -> tuple[list[str], pd.DataFrame]:
    rows: list[dict[str, object]] = []
    for feature in features:
        values = pd.to_numeric(X_train[feature], errors="coerce")
        trend = pd.DataFrame({"feature_value": values, "t1": y_train}).dropna()
        if len(trend) < 8 or trend["feature_value"].nunique() < 4:
            continue
        trend["feature_group"] = pd.qcut(trend["feature_value"], q=4, labels=False, duplicates="drop")
        medians = trend.groupby("feature_group", observed=False)["t1"].median().dropna()
        if len(medians) < 3:
            continue
        slope = float(np.polyfit(medians.index.to_numpy(dtype=float) + 1, medians.to_numpy(dtype=float), 1)[0])
        rows.append({"feature": feature, "slope": slope, "n_observed": len(trend)})
    ranked = pd.DataFrame(rows)
    if ranked.empty:
        return [], ranked
    positive = ranked[ranked["slope"] >= 0].nlargest(5, "slope")["feature"].tolist()
    negative = ranked[ranked["slope"] < 0].nsmallest(3, "slope")["feature"].tolist()
    return positive + negative, ranked


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
    repeat_buffers: dict[int, dict[str, list[float]]] = {}

    for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
        repeat = split_index // N_SPLITS + 1
        fold = split_index % N_SPLITS + 1
        X_train_raw = X.iloc[train_idx]
        X_test_raw = X.iloc[test_idx]
        y_train = y[train_idx]
        y_test = y[test_idx]
        selected, ranked = slope_rank_features(X_train_raw, y_train, features)
        if len(selected) < 3:
            raise RuntimeError(f"Fold {repeat}/{fold} did not yield enough slope-selected features")
        for _, row in ranked.iterrows():
            selection_rows.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "feature": row["feature"],
                    "slope": row["slope"],
                    "selected": row["feature"] in selected,
                }
            )

        imputer = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
        X_train_imputed = imputer.fit_transform(X_train_raw[selected])
        X_test_imputed = imputer.transform(X_test_raw[selected])
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_imputed)
        X_test_scaled = scaler.transform(X_test_imputed)
        inner_cv = KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE)
        model = RidgeCV(alphas=ALPHAS, cv=inner_cv, scoring="neg_root_mean_squared_error")
        model.fit(X_train_scaled, y_train)
        prediction = model.predict(X_test_scaled)
        baseline = np.repeat(y_train.mean(), len(test_idx))
        repeat_buffers.setdefault(repeat, {"actual": [], "baseline": [], "slope": []})
        repeat_buffers[repeat]["actual"].extend(y_test.tolist())
        repeat_buffers[repeat]["baseline"].extend(baseline.tolist())
        repeat_buffers[repeat]["slope"].extend(prediction.tolist())
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
                    "slope_selected_prediction": prediction[row_index],
                    "selected_features": selected_text,
                    "n_features": len(selected),
                    "ridge_alpha": float(model.alpha_),
                }
            )

    predictions_df = pd.DataFrame(predictions)
    patient_df = (
        predictions_df.groupby(["Subject_ID_D", "Subject_ID_N"], dropna=False)
        .agg(
            actual_global_T1=("actual_global_T1", "first"),
            mean_baseline_prediction=("mean_baseline_prediction", "mean"),
            slope_selected_prediction=("slope_selected_prediction", "mean"),
        )
        .reset_index()
    )
    metrics: list[dict[str, object]] = []
    for repeat, values in repeat_buffers.items():
        actual = np.asarray(values["actual"])
        metrics.append(metric_row(actual, np.asarray(values["baseline"]), "mean_baseline", repeat))
        metrics.append(metric_row(actual, np.asarray(values["slope"]), "slope_selected_ridge", repeat))
    pooled_actual = np.tile(y, N_REPEATS)
    metrics.append(metric_row(pooled_actual, predictions_df["mean_baseline_prediction"].to_numpy(), "mean_baseline", "pooled"))
    metrics.append(metric_row(pooled_actual, predictions_df["slope_selected_prediction"].to_numpy(), "slope_selected_ridge", "pooled"))

    predictions_df.to_csv(PREDICTIONS_PATH, index=False)
    patient_df.to_csv(PATIENT_PATH, index=False)
    pd.DataFrame(metrics).to_csv(METRICS_PATH, index=False)
    pd.DataFrame(selection_rows).to_csv(SELECTION_PATH, index=False)
    pooled = pd.DataFrame(metrics).query("analysis_scope == 'pooled'").set_index("model")
    README_PATH.write_text(
        "# Phase 4 Slope-Selected T1 Ridge\n\n"
        "This is a separate exploratory model using only eight features selected inside each outer training fold: "
        "the five highest positive linear slopes and three lowest negative linear slopes. "
        "Slope is fitted to the four feature-quantile median T1 values. The model uses fold-local median imputation, "
        "missingness indicators, standardization, and inner-CV ridge alpha selection.\n\n"
        f"Pooled mean-baseline RMSE: `{pooled.loc['mean_baseline', 'rmse']:.3f}`\n\n"
        f"Pooled slope-selected ridge RMSE: `{pooled.loc['slope_selected_ridge', 'rmse']:.3f}`\n",
        encoding="utf-8",
    )
    print(f"patients: {len(dataset)}")
    print(pd.DataFrame(metrics).query("analysis_scope == 'pooled'").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
