"""Cognitive-domain graphs/models for coverage-ranked Suggestions cohorts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RepeatedKFold

from phase4_model_t1_cognitive_domain_groups import DOMAIN_FEATURES, DOMAIN_TARGETS, build_pipeline
from other_models_phase4_10day import DATA_DIR, RANDOM_STATE


OUT_DIR = DATA_DIR / "suggestions"
DATASET_PATH = DATA_DIR / "phase4_10day_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_10day_t1_baseline_feature_metadata.csv"
METRICS_PATH = OUT_DIR / "suggestions_10day_cognitive_domain_metrics.csv"
PATIENT_PATH = OUT_DIR / "suggestions_10day_cognitive_domain_patient_predictions.csv"
PREDICTIONS_PATH = OUT_DIR / "suggestions_10day_cognitive_domain_predictions.csv"

N_SPLITS = 5
N_REPEATS = 10
COHORT_SIZES = [30, 20, 10]


def metric_row(actual: np.ndarray, predicted: np.ndarray, cohort_size: int, domain: str, model: str, repeat: int | str) -> dict[str, object]:
    return {
        "analysis_scope": "repeat" if repeat != "pooled" else "pooled",
        "repeat": repeat,
        "cohort_size": cohort_size,
        "domain": domain,
        "model": model,
        "n_predictions": len(actual),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
    }


def run_domain_cohort(dataset: pd.DataFrame, all_features: list[str], cohort_size: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    subset = dataset.head(cohort_size).copy().reset_index(drop=True)
    prediction_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    for domain, target_name in DOMAIN_TARGETS.items():
        target = pd.to_numeric(subset[target_name], errors="coerce")
        valid = target.notna()
        domain_dataset = subset.loc[valid].reset_index(drop=True)
        y = target.loc[valid].to_numpy(dtype=float)
        x_all = domain_dataset[all_features].apply(pd.to_numeric, errors="coerce")
        group_features = [feature for feature in DOMAIN_FEATURES[domain] if feature in domain_dataset.columns]
        x_group = domain_dataset[group_features].apply(pd.to_numeric, errors="coerce")
        buffers: dict[str, dict[int, dict[str, list[float]]]] = {
            "ridge": {},
            "domain_group_ridge": {},
        }
        outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
        for split_index, (train_idx, test_idx) in enumerate(outer.split(x_all)):
            repeat = split_index // N_SPLITS + 1
            fold = split_index % N_SPLITS + 1
            y_train, y_test = y[train_idx], y[test_idx]
            baseline = np.repeat(y_train.mean(), len(test_idx))
            all_model = build_pipeline()
            group_model = build_pipeline()
            all_model.fit(x_all.iloc[train_idx], y_train)
            group_model.fit(x_group.iloc[train_idx], y_train)
            all_prediction = all_model.predict(x_all.iloc[test_idx])
            group_prediction = group_model.predict(x_group.iloc[test_idx])
            for model_name, prediction in [("ridge", all_prediction), ("domain_group_ridge", group_prediction)]:
                buffers[model_name].setdefault(repeat, {"actual": [], "prediction": []})
                buffers[model_name][repeat]["actual"].extend(y_test.tolist())
                buffers[model_name][repeat]["prediction"].extend(prediction.tolist())
            for row_index, row_pos in enumerate(test_idx):
                prediction_rows.append(
                    {
                        "cohort_size": cohort_size,
                        "domain": domain,
                        "target": target_name,
                        "repeat": repeat,
                        "fold": fold,
                        "Subject_ID_D": domain_dataset.loc[row_pos, "Subject_ID_D"],
                        "Subject_ID_N": domain_dataset.loc[row_pos, "Subject_ID_N"],
                        "actual_T1": y_test[row_index],
                        "mean_baseline_prediction": baseline[row_index],
                        "ridge_prediction": all_prediction[row_index],
                        "group_ridge_prediction": group_prediction[row_index],
                    }
                )
        for model_name in ["ridge", "domain_group_ridge"]:
            for repeat, values in buffers[model_name].items():
                metric_rows.append(metric_row(
                    np.asarray(values["actual"]), np.asarray(values["prediction"]), cohort_size, domain, model_name, repeat
                ))
        domain_predictions = pd.DataFrame([row for row in prediction_rows if row["cohort_size"] == cohort_size and row["domain"] == domain])
        pooled_actual = np.tile(y, N_REPEATS)
        metric_rows.append(metric_row(
            pooled_actual, domain_predictions["mean_baseline_prediction"].to_numpy(), cohort_size, domain, "mean_baseline", "pooled"
        ))
        for model_name, column in [("ridge", "ridge_prediction"), ("domain_group_ridge", "group_ridge_prediction")]:
            metric_rows.append(metric_row(
                pooled_actual, domain_predictions[column].to_numpy(), cohort_size, domain, model_name, "pooled"
            ))

    predictions_df = pd.DataFrame(prediction_rows)
    patient_df = predictions_df.groupby(
        ["cohort_size", "domain", "target", "Subject_ID_D", "Subject_ID_N"], dropna=False
    ).agg(
        actual_T1=("actual_T1", "first"),
        mean_baseline_prediction=("mean_baseline_prediction", "mean"),
        ridge_prediction=("ridge_prediction", "mean"),
        group_ridge_prediction=("group_ridge_prediction", "mean"),
    ).reset_index()
    return predictions_df, patient_df, pd.DataFrame(metric_rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    all_features = metadata["feature_name"].dropna().tolist()
    dataset = dataset.sort_values(
        ["baseline_feature_missing_fraction", "baseline_table_coverage_fraction", "Subject_ID_D"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    prediction_frames: list[pd.DataFrame] = []
    patient_frames: list[pd.DataFrame] = []
    metric_frames: list[pd.DataFrame] = []
    for cohort_size in COHORT_SIZES:
        print(f"running cognitive domains top_{cohort_size}", flush=True)
        predictions, patients, metrics = run_domain_cohort(dataset, all_features, cohort_size)
        prediction_frames.append(predictions)
        patient_frames.append(patients)
        metric_frames.append(metrics)
    pd.concat(prediction_frames, ignore_index=True).to_csv(PREDICTIONS_PATH, index=False)
    pd.concat(patient_frames, ignore_index=True).to_csv(PATIENT_PATH, index=False)
    pd.concat(metric_frames, ignore_index=True).to_csv(METRICS_PATH, index=False)
    print(pd.concat(metric_frames, ignore_index=True).query("analysis_scope == 'pooled'").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
