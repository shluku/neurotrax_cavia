"""Coverage-ranked exploratory model cohorts for the Phase 4 10-day T1 data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RepeatedKFold

from other_models_phase4_10day import (
    DATA_DIR,
    RANDOM_STATE,
    fit_elastic_net,
    fit_pls,
    fit_spline_ridge,
    fit_tree_models,
    metric_row,
    preprocess,
)


ROOT = Path(__file__).parent
DATASET_PATH = DATA_DIR / "phase4_10day_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_10day_t1_baseline_feature_metadata.csv"
OUT_DIR = DATA_DIR / "suggestions"
METRICS_PATH = OUT_DIR / "suggestions_10day_coverage_metrics.csv"
PATIENT_PATH = OUT_DIR / "suggestions_10day_coverage_patient_predictions.csv"
PREDICTIONS_PATH = OUT_DIR / "suggestions_10day_coverage_predictions.csv"
COHORT_PATH = OUT_DIR / "suggestions_10day_coverage_cohorts.csv"
README_PATH = OUT_DIR / "README_suggestions_10day_coverage_models.md"

TARGET = "global_T1"
COHORT_SIZES = [30, 20, 10]
N_SPLITS = 5
N_REPEATS = 10


MODEL_NAMES = [
    "elastic_net",
    "pls",
    "spline_ridge",
    "random_forest",
    "extra_trees",
    "hist_gradient_boosting",
    "xgboost",
]


def run_cohort(dataset: pd.DataFrame, features: list[str], cohort_size: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    subset = dataset.head(cohort_size).copy().reset_index(drop=True)
    y = pd.to_numeric(subset[TARGET], errors="coerce").to_numpy(dtype=float)
    X = subset[features].apply(pd.to_numeric, errors="coerce")
    outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
    predictions: list[dict[str, object]] = []
    repeat_buffers: dict[tuple[int, str], dict[str, list[float]]] = {}

    for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
        repeat = split_index // N_SPLITS + 1
        fold = split_index % N_SPLITS + 1
        X_train, X_test, _ = preprocess(X.iloc[train_idx], X.iloc[test_idx])
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
        for row_index, row_pos in enumerate(test_idx):
            row = {
                "cohort_size": cohort_size,
                "repeat": repeat,
                "fold": fold,
                "Subject_ID_D": subset.loc[row_pos, "Subject_ID_D"],
                "Subject_ID_N": subset.loc[row_pos, "Subject_ID_N"],
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
        **{f"{name}_prediction": (f"{name}_prediction", "mean") for name in MODEL_NAMES},
    ).reset_index()
    patient_df.insert(0, "cohort_size", cohort_size)

    metrics: list[dict[str, object]] = []
    for (repeat, model_name), values in repeat_buffers.items():
        row = metric_row(np.asarray(values["actual"]), np.asarray(values["prediction"]), model_name, repeat)
        row["cohort_size"] = cohort_size
        metrics.append(row)
    for repeat, repeat_frame in predictions_df.groupby("repeat"):
        row = metric_row(
            repeat_frame["actual_global_T1"].to_numpy(),
            repeat_frame["mean_baseline_prediction"].to_numpy(),
            "mean_baseline",
            int(repeat),
        )
        row["cohort_size"] = cohort_size
        metrics.append(row)
    pooled_actual = np.tile(y, N_REPEATS)
    row = metric_row(
        pooled_actual,
        predictions_df["mean_baseline_prediction"].to_numpy(),
        "mean_baseline",
        "pooled",
    )
    row["cohort_size"] = cohort_size
    metrics.append(row)
    for model_name in MODEL_NAMES:
        row = metric_row(
            pooled_actual,
            predictions_df[f"{model_name}_prediction"].to_numpy(),
            model_name,
            "pooled",
        )
        row["cohort_size"] = cohort_size
        metrics.append(row)
    return predictions_df, patient_df, pd.DataFrame(metrics)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    features = metadata["feature_name"].dropna().tolist()
    target = pd.to_numeric(dataset[TARGET], errors="coerce")
    dataset = dataset.loc[target.notna()].copy()
    ranked = dataset.sort_values(
        ["baseline_feature_missing_fraction", "baseline_table_coverage_fraction", "Subject_ID_D"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    ranked["coverage_rank"] = range(1, len(ranked) + 1)
    ranked["coverage_cohort"] = ranked["coverage_rank"].map(
        lambda rank: "top_10" if rank <= 10 else "top_20" if rank <= 20 else "top_30" if rank <= 30 else "full_81"
    )
    cohort_columns = [
        "coverage_rank", "coverage_cohort", "Subject_ID_D", "Subject_ID_N", TARGET,
        "baseline_feature_missing_count", "baseline_feature_missing_fraction", "baseline_table_coverage_fraction",
    ]
    ranked[cohort_columns].to_csv(COHORT_PATH, index=False)

    all_predictions: list[pd.DataFrame] = []
    all_patients: list[pd.DataFrame] = []
    all_metrics: list[pd.DataFrame] = []
    for cohort_size in COHORT_SIZES:
        print(f"running top_{cohort_size}", flush=True)
        predictions, patients, metrics = run_cohort(ranked, features, cohort_size)
        all_predictions.append(predictions)
        all_patients.append(patients)
        all_metrics.append(metrics)

    predictions_df = pd.concat(all_predictions, ignore_index=True)
    patient_df = pd.concat(all_patients, ignore_index=True)
    metrics_df = pd.concat(all_metrics, ignore_index=True)
    predictions_df.to_csv(PREDICTIONS_PATH, index=False)
    patient_df.to_csv(PATIENT_PATH, index=False)
    metrics_df.to_csv(METRICS_PATH, index=False)

    pooled = metrics_df[metrics_df["analysis_scope"].eq("pooled")].sort_values(["cohort_size", "rmse"])
    README_PATH.write_text(
        "# Suggestions: coverage-ranked 10-day T1 baseline models\n\n"
        "This isolated exploratory phase ranks patients only by feature coverage, then runs the same seven "
        "alternative model families on the top 30, top 20, and top 10 patients. The top 30 cohort is the main "
        "exploratory result; top 20 is sensitivity analysis; top 10 is descriptive only because validation variance "
        "is very high at that sample size. Every cohort has its own mean baseline.\n\n"
        "Coverage ranking uses lower baseline feature missingness, higher table coverage as a tie-breaker, and patient ID as a final deterministic tie-breaker. T1 scores are never used for cohort selection.\n\n"
        + "\n".join(
            f"Top {int(row.cohort_size)} {row.model} RMSE: `{row.rmse:.4f}`"
            for row in pooled.itertuples()
        )
        + "\n",
        encoding="utf-8",
    )
    print(pooled[["cohort_size", "model", "rmse", "mae", "r2"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
