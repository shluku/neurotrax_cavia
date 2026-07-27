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
OUT_DIR = DATA_DIR / "model_t1_cognitive_domains"
PREDICTIONS_PATH = OUT_DIR / "phase4_t1_cognitive_domain_predictions.csv"
PATIENT_PATH = OUT_DIR / "phase4_t1_cognitive_domain_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "phase4_t1_cognitive_domain_metrics.csv"
README_PATH = OUT_DIR / "README_phase4_t1_cognitive_domains.md"

DOMAIN_TARGETS = {
    "Memory": "memory_T1",
    "Executive function": "ef_T1",
    "Processing speed": "processing_speed_T1",
    "Attention": "attention_T1",
    "Motor": "motor_T1",
}
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260726
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


def metric_row(actual: np.ndarray, predicted: np.ndarray, domain: str, model: str, repeat: int | str) -> dict[str, object]:
    return {
        "analysis_scope": "repeat" if repeat != "pooled" else "pooled",
        "repeat": repeat,
        "domain": domain,
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
    X_all = dataset[features].apply(pd.to_numeric, errors="coerce")
    prediction_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []

    for domain, target_name in DOMAIN_TARGETS.items():
        target = pd.to_numeric(dataset[target_name], errors="coerce")
        valid = target.notna()
        X = X_all.loc[valid].reset_index(drop=True)
        domain_dataset = dataset.loc[valid].reset_index(drop=True)
        y = target.loc[valid].to_numpy(dtype=float)
        repeat_buffers: dict[int, dict[str, list[float]]] = {}
        outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)

        for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
            repeat = split_index // N_SPLITS + 1
            fold = split_index % N_SPLITS + 1
            y_train = y[train_idx]
            y_test = y[test_idx]
            baseline = np.repeat(y_train.mean(), len(test_idx))
            model = build_pipeline()
            model.fit(X.iloc[train_idx], y_train)
            prediction = model.predict(X.iloc[test_idx])
            repeat_buffers.setdefault(repeat, {"actual": [], "baseline": [], "ridge": []})
            repeat_buffers[repeat]["actual"].extend(y_test.tolist())
            repeat_buffers[repeat]["baseline"].extend(baseline.tolist())
            repeat_buffers[repeat]["ridge"].extend(prediction.tolist())
            for row_index, row_pos in enumerate(test_idx):
                prediction_rows.append(
                    {
                        "domain": domain,
                        "target": target_name,
                        "repeat": repeat,
                        "fold": fold,
                        "Subject_ID_D": domain_dataset.loc[row_pos, "Subject_ID_D"],
                        "Subject_ID_N": domain_dataset.loc[row_pos, "Subject_ID_N"],
                        "actual_T1": y_test[row_index],
                        "mean_baseline_prediction": baseline[row_index],
                        "ridge_prediction": prediction[row_index],
                        "ridge_alpha": float(model.named_steps["ridge"].alpha_),
                    }
                )

        for repeat, values in repeat_buffers.items():
            actual = np.asarray(values["actual"])
            metric_rows.append(metric_row(actual, np.asarray(values["baseline"]), domain, "mean_baseline", repeat))
            metric_rows.append(metric_row(actual, np.asarray(values["ridge"]), domain, "ridge", repeat))
        pooled_actual = np.tile(y, N_REPEATS)
        domain_predictions = pd.DataFrame([row for row in prediction_rows if row["domain"] == domain])
        metric_rows.append(metric_row(pooled_actual, domain_predictions["mean_baseline_prediction"].to_numpy(), domain, "mean_baseline", "pooled"))
        metric_rows.append(metric_row(pooled_actual, domain_predictions["ridge_prediction"].to_numpy(), domain, "ridge", "pooled"))

    predictions = pd.DataFrame(prediction_rows)
    patient_predictions = (
        predictions.groupby(["domain", "target", "Subject_ID_D", "Subject_ID_N"], dropna=False)
        .agg(
            actual_T1=("actual_T1", "first"),
            mean_baseline_prediction=("mean_baseline_prediction", "mean"),
            ridge_prediction=("ridge_prediction", "mean"),
        )
        .reset_index()
    )
    metrics = pd.DataFrame(metric_rows)
    predictions.to_csv(PREDICTIONS_PATH, index=False)
    patient_predictions.to_csv(PATIENT_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    pooled = metrics[metrics["analysis_scope"].eq("pooled")]
    lines = [
        "# Phase 4 T1 Cognitive Domain Models",
        "",
        "Each domain is modeled separately using the same 37 primary features, repeated 5-fold cross-validation repeated 20 times, and fold-local median imputation, missingness indicators, standardization, and inner-CV Ridge alpha selection.",
        "",
        "## Pooled results",
        "",
    ]
    for row in pooled.itertuples():
        lines.append(f"- {row.domain} / {row.model}: RMSE `{row.rmse:.3f}`, MAE `{row.mae:.3f}`, R2 `{row.r2:.3f}`.")
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"prediction rows: {len(predictions)}")
    print(pooled[["domain", "model", "rmse", "mae", "r2"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
