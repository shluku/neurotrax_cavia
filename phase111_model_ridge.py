"""First Phase 111 model: full-interval features versus a mean baseline."""

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
DATA_DIR = ROOT / "output/analysis_candidates/phase111_t1_t2_all_interval"
DATASET_PATH = DATA_DIR / "phase111_t1_t2_all_interval_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase111_t1_t2_all_interval_feature_metadata.csv"
OUT_DIR = DATA_DIR / "model_phase111_ridge"
PREDICTIONS_PATH = OUT_DIR / "phase111_ridge_predictions.csv"
PATIENT_PATH = OUT_DIR / "phase111_ridge_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "phase111_ridge_metrics.csv"
FEATURE_SET_PATH = OUT_DIR / "phase111_ridge_feature_set.csv"
COEFFICIENT_PATH = OUT_DIR / "phase111_ridge_coefficients.csv"
README_PATH = OUT_DIR / "README_phase111_ridge.md"

OUTCOMES = {
    "Global": "phase111_target_global",
    "Memory": "phase111_target_memory",
    "Executive function": "phase111_target_executive_function",
    "Processing speed": "phase111_target_processing_speed",
    "Attention": "phase111_target_attention",
    "Motor": "phase111_target_motor",
}
OBSERVED_T1 = {
    "Global": "global_T1",
    "Memory": "memory_T1",
    "Executive function": "ef_T1",
    "Processing speed": "processing_speed_T1",
    "Attention": "attention_T1",
    "Motor": "motor_T1",
}
OBSERVED_T2 = {outcome: column.replace("_T1", "_T2") for outcome, column in OBSERVED_T1.items()}
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260804
ALPHAS = np.logspace(-3, 4, 30)


def build_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scaler", StandardScaler()),
            (
                "ridge",
                RidgeCV(
                    alphas=ALPHAS,
                    cv=KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE),
                    scoring="neg_root_mean_squared_error",
                ),
            ),
        ]
    )


def metric_row(actual: np.ndarray, predicted: np.ndarray, outcome: str, model: str, repeat: int | str) -> dict[str, object]:
    return {
        "analysis_scope": "repeat" if repeat != "pooled" else "pooled",
        "repeat": repeat,
        "outcome": outcome,
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
    features = metadata["feature_name"].astype(str).tolist()
    dataset[features] = dataset[features].apply(pd.to_numeric, errors="coerce")
    pd.DataFrame(
        {
            "feature_name": features,
            "source_table": metadata.set_index("feature_name").reindex(features)["source_table"].to_numpy(),
            "model_scope": "all_active_54_features",
        }
    ).to_csv(FEATURE_SET_PATH, index=False)

    prediction_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    coefficient_rows: list[dict[str, object]] = []
    for outcome, target_column in OUTCOMES.items():
        target = pd.to_numeric(dataset[target_column], errors="coerce")
        valid = target.notna()
        data = dataset.loc[valid].reset_index(drop=True)
        y = target.loc[valid].to_numpy(dtype=float)
        X = data[features]
        n_splits = min(N_SPLITS, len(data))
        repeat_buffers: dict[int, dict[str, list[float]]] = {}
        outer = RepeatedKFold(n_splits=n_splits, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
        for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
            repeat = split_index // n_splits + 1
            fold = split_index % n_splits + 1
            baseline = np.repeat(y[train_idx].mean(), len(test_idx))
            model = build_pipeline()
            model.fit(X.iloc[train_idx], y[train_idx])
            estimate = model.predict(X.iloc[test_idx])
            repeat_buffers.setdefault(repeat, {"actual": [], "baseline": [], "ridge": []})
            repeat_buffers[repeat]["actual"].extend(y[test_idx].tolist())
            repeat_buffers[repeat]["baseline"].extend(baseline.tolist())
            repeat_buffers[repeat]["ridge"].extend(estimate.tolist())
            coefficients = model.named_steps["ridge"].coef_
            for feature, coefficient in zip(features, coefficients[: len(features)]):
                coefficient_rows.append(
                    {
                        "outcome": outcome,
                        "repeat": repeat,
                        "fold": fold,
                        "feature_name": feature,
                        "coefficient": float(coefficient),
                        "ridge_alpha": float(model.named_steps["ridge"].alpha_),
                    }
                )
            for row_index, row_pos in enumerate(test_idx):
                prediction_rows.append(
                    {
                        "outcome": outcome,
                        "target": target_column,
                        "repeat": repeat,
                        "fold": fold,
                        "Subject_ID_D": data.loc[row_pos, "Subject_ID_D"],
                        "Subject_ID_N": data.loc[row_pos, "Subject_ID_N"] if "Subject_ID_N" in data.columns else pd.NA,
                        "observed_T1": pd.to_numeric(data.loc[row_pos, OBSERVED_T1[outcome]], errors="coerce"),
                        "observed_T2": pd.to_numeric(data.loc[row_pos, OBSERVED_T2[outcome]], errors="coerce"),
                        "target_value": y[row_pos],
                        "target_source": data.loc[row_pos, f"{target_column}_source"],
                        "mean_baseline_prediction": baseline[row_index],
                        "ridge_prediction": estimate[row_index],
                        "ridge_alpha": float(model.named_steps["ridge"].alpha_),
                        "n_features": len(features),
                    }
                )
        for repeat, values in repeat_buffers.items():
            actual = np.asarray(values["actual"])
            metric_rows.append(metric_row(actual, np.asarray(values["baseline"]), outcome, "mean_baseline", repeat))
            metric_rows.append(metric_row(actual, np.asarray(values["ridge"]), outcome, "ridge", repeat))
        pooled = pd.DataFrame([row for row in prediction_rows if row["outcome"] == outcome])
        actual = pooled["target_value"].to_numpy(dtype=float)
        metric_rows.append(metric_row(actual, pooled["mean_baseline_prediction"].to_numpy(dtype=float), outcome, "mean_baseline", "pooled"))
        metric_rows.append(metric_row(actual, pooled["ridge_prediction"].to_numpy(dtype=float), outcome, "ridge", "pooled"))

    predictions = pd.DataFrame(prediction_rows)
    patient_predictions = (
        predictions.groupby(["outcome", "target", "Subject_ID_D", "Subject_ID_N"], dropna=False)
        .agg(
            observed_T1=("observed_T1", "first"),
            observed_T2=("observed_T2", "first"),
            target_value=("target_value", "first"),
            target_source=("target_source", "first"),
            mean_baseline_prediction=("mean_baseline_prediction", "mean"),
            ridge_prediction=("ridge_prediction", "mean"),
        )
        .reset_index()
    )
    metrics = pd.DataFrame(metric_rows)
    predictions.to_csv(PREDICTIONS_PATH, index=False)
    patient_predictions.to_csv(PATIENT_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    pd.DataFrame(coefficient_rows).to_csv(COEFFICIENT_PATH, index=False)

    pooled = metrics[metrics["analysis_scope"].eq("pooled")]
    lines = [
        "# Phase 111 Full-Interval Ridge",
        "",
        "Features are calculated from all available active-feature data in `[T1, T2)`, or `[T1, T1+123 days)` when T2 is unavailable.",
        "",
        "For each outcome, the target is the mean of observed T1 and T2 scores when both exist, or observed T1 alone without T2. With two observations, the standard median is identical to this mean.",
        "",
        "Ridge uses fold-local median imputation, missingness indicators, standardization, inner-CV alpha selection, and repeated 5-fold cross-validation. Every Ridge result is compared against the same fold-local mean baseline.",
        "",
        "## Pooled results",
        "",
    ]
    for row in pooled.itertuples():
        lines.append(f"- {row.outcome} / {row.model}: RMSE `{row.rmse:.3f}`, MAE `{row.mae:.3f}`, R2 `{row.r2:.3f}`.")
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"patients: {dataset['Subject_ID_D'].nunique()}")
    print(pooled[["outcome", "model", "n_predictions", "rmse", "mae", "r2"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
