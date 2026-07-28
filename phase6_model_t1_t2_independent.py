"""Phase 6 independent T1/T2 digital phenotype models."""

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
T1_PATH = ROOT / "output/analysis_candidates/phase4_t1_baseline/phase4_t1_baseline_patient_dataset.csv"
T2_PATH = ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_selected_features_wide.csv"
FEATURE_SUMMARY_PATH = ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_feature_coverage_summary.csv"
T1_CALIBRATION_PATH = ROOT / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/phase4_t1_score_calibration_by_patient.csv"
T1_DOMAIN_PATH = ROOT / "output/analysis_candidates/phase4_t1_baseline/model_t1_cognitive_domain_groups/phase4_t1_cognitive_domain_group_patient_predictions.csv"
TAXONOMY_PATH = ROOT / "output/analysis_candidates/phase4_t1_baseline/model_t1_cognitive_domain_groups/phase4_cognitive_domain_feature_taxonomy.csv"
OUT_DIR = ROOT / "output/analysis_candidates/phase6_t1_t2_decline"
PREDICTIONS_PATH = OUT_DIR / "phase6_t1_t2_decline_predictions.csv"
PATIENT_PATH = OUT_DIR / "phase6_t1_t2_decline_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "phase6_t1_t2_decline_metrics.csv"
FEATURE_SET_PATH = OUT_DIR / "phase6_t1_t2_decline_feature_sets.csv"
DOMAIN_TAXONOMY_PATH = OUT_DIR / "phase6_t1_t2_decline_domain_taxonomy.csv"
README_PATH = OUT_DIR / "README_phase6_t1_t2_decline.md"

DOMAIN_TARGETS = {
    "Global": "global",
    "Memory": "memory",
    "Executive function": "ef",
    "Processing speed": "processing_speed",
    "Attention": "attention",
    "Motor": "motor",
}
N_SPLITS = 5
N_REPEATS = 5
RANDOM_STATE = 20260728
ALPHAS = np.logspace(-3, 4, 15)


def clean_id(value: object) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(3)


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


def metric(actual: np.ndarray, predicted: np.ndarray, outcome: str, model: str, scope: str, repeat: int | str) -> dict[str, object]:
    return {
        "analysis_scope": scope,
        "repeat": repeat,
        "outcome": outcome,
        "model": model,
        "n_predictions": len(actual),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
    }


def fit_t2_model(
    dataset: pd.DataFrame,
    outcome: str,
    target_column: str,
    feature_columns: list[str],
    model_name: str,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    valid = pd.to_numeric(dataset[target_column], errors="coerce").notna()
    data = dataset.loc[valid].reset_index(drop=True)
    y = pd.to_numeric(data[target_column], errors="coerce").to_numpy(dtype=float)
    X = data[feature_columns].apply(pd.to_numeric, errors="coerce")
    n_splits = min(N_SPLITS, len(data))
    predictions: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    buffers: dict[int, dict[str, list[float]]] = {}
    outer = RepeatedKFold(n_splits=n_splits, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
    for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
        repeat = split_index // n_splits + 1
        fold = split_index % n_splits + 1
        baseline = np.repeat(y[train_idx].mean(), len(test_idx))
        model = build_pipeline()
        model.fit(X.iloc[train_idx], y[train_idx])
        estimate = model.predict(X.iloc[test_idx])
        buffers.setdefault(repeat, {"actual": [], "baseline": [], "estimate": []})
        buffers[repeat]["actual"].extend(y[test_idx].tolist())
        buffers[repeat]["baseline"].extend(baseline.tolist())
        buffers[repeat]["estimate"].extend(estimate.tolist())
        for row_index, row_pos in enumerate(test_idx):
            predictions.append(
                {
                    "outcome": outcome,
                    "target": f"{target_column}_independent_T2",
                    "model": model_name,
                    "repeat": repeat,
                    "fold": fold,
                    "Subject_ID_D": data.loc[row_pos, "Subject_ID_D"],
                    "actual_T2": y[row_pos],
                    "mean_baseline_T2": baseline[row_index],
                    "estimated_T2": estimate[row_index],
                    "n_features": len(feature_columns),
                    "ridge_alpha": float(model.named_steps["ridge"].alpha_),
                }
            )
    for repeat, values in buffers.items():
        actual = np.asarray(values["actual"])
        metrics.append(metric(actual, np.asarray(values["baseline"]), outcome, "mean_baseline_T2", "repeat", repeat))
        metrics.append(metric(actual, np.asarray(values["estimate"]), outcome, model_name, "repeat", repeat))
    prediction_df = pd.DataFrame(predictions)
    actual = prediction_df["actual_T2"].to_numpy(dtype=float)
    metrics.append(metric(actual, prediction_df["mean_baseline_T2"].to_numpy(dtype=float), outcome, "mean_baseline_T2", "pooled", "pooled"))
    metrics.append(metric(actual, prediction_df["estimated_T2"].to_numpy(dtype=float), outcome, model_name, "pooled", "pooled"))
    return prediction_df, metrics


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t1 = pd.read_csv(T1_PATH, dtype=str)
    t2 = pd.read_csv(T2_PATH, dtype=str)
    t1["Subject_ID_D"] = t1["Subject_ID_D"].map(clean_id)
    t2["Subject_ID_D"] = t2["Subject_ID_D"].map(clean_id)
    summary = pd.read_csv(FEATURE_SUMMARY_PATH, dtype=str)
    summary["t2_coverage_percent"] = pd.to_numeric(summary["t2_coverage_percent"], errors="coerce")
    working_features = summary.loc[summary["t2_coverage_percent"].ge(10), "feature_name"].tolist()
    primary_features = summary.loc[summary["t2_analysis_role"].eq("primary_eligible_10pct"), "feature_name"].tolist()
    paired = t1.merge(t2, on="Subject_ID_D", how="inner", suffixes=("_T1dataset", "_T2dataset"))

    taxonomy = pd.read_csv(TAXONOMY_PATH, dtype=str)
    taxonomy = taxonomy[taxonomy["feature"].isin(working_features)].copy()
    taxonomy.to_csv(DOMAIN_TAXONOMY_PATH, index=False)

    feature_rows = []
    for feature in working_features:
        feature_rows.append(
            {
                "feature_name": feature,
                "t1_feature_column": feature,
                "t2_feature_column": f"{feature}_T2dataset",
                "t2_coverage_percent": summary.loc[summary["feature_name"].eq(feature), "t2_coverage_percent"].iloc[0],
                "t2_analysis_role": summary.loc[summary["feature_name"].eq(feature), "t2_analysis_role"].iloc[0],
                "input_scale": "independent_T2_feature_level",
                "model_set": "t1_primary_10pct" if feature in primary_features else "working_10pct_support",
            }
        )
    pd.DataFrame(feature_rows).to_csv(FEATURE_SET_PATH, index=False)

    all_predictions: list[pd.DataFrame] = []
    all_metrics: list[dict[str, object]] = []
    model_specs: dict[str, list[str]] = {
        "t1_primary_10pct_independent_t2_ridge": [f"{feature}_T2dataset" for feature in primary_features],
        "working_10pct_independent_t2_ridge": [f"{feature}_T2dataset" for feature in working_features],
    }
    selected_model_by_outcome = {"Global": "working_10pct_independent_t2_ridge"}
    for outcome, prefix in DOMAIN_TARGETS.items():
        target_column = f"{prefix}_T2_T2dataset"
        if target_column not in paired.columns:
            continue
        if outcome != "Global":
            domain_features = taxonomy.loc[taxonomy["domain"].eq(outcome), "feature"].tolist()
            model_specs[f"{outcome}_domain_independent_t2_ridge"] = [f"{feature}_T2dataset" for feature in domain_features]
            selected_model_by_outcome[outcome] = f"{outcome}_domain_independent_t2_ridge"
        for model_name, features in list(model_specs.items()):
            if outcome == "Global" and not model_name.startswith(("t1_primary", "working")):
                continue
            if outcome != "Global" and model_name != selected_model_by_outcome[outcome]:
                continue
            if features:
                prediction_df, metric_rows = fit_t2_model(paired, outcome, target_column, features, model_name)
                all_predictions.append(prediction_df)
                all_metrics.extend(metric_rows)

    t2_predictions = pd.concat(all_predictions, ignore_index=True)
    metrics = pd.DataFrame(all_metrics).drop_duplicates(["analysis_scope", "repeat", "outcome", "model"], keep="first")

    t1_calibration = pd.read_csv(T1_CALIBRATION_PATH, dtype=str)
    t1_calibration["Subject_ID_D"] = t1_calibration["Subject_ID_D"].map(clean_id)
    t1_primary = t1_calibration[t1_calibration["feature_scope"].eq("primary_37")][["Subject_ID_D", "ridge_prediction"]].copy()
    t1_primary["estimated_T1"] = pd.to_numeric(t1_primary["ridge_prediction"], errors="coerce")
    t1_primary = t1_primary[["Subject_ID_D", "estimated_T1"]]
    domain_t1 = pd.read_csv(T1_DOMAIN_PATH, dtype=str)
    domain_t1["Subject_ID_D"] = domain_t1["Subject_ID_D"].map(clean_id)

    patient_rows: list[pd.DataFrame] = []
    decline_metrics: list[dict[str, object]] = []
    for outcome, prefix in DOMAIN_TARGETS.items():
        model_name = selected_model_by_outcome.get(outcome)
        if not model_name:
            continue
        pred = t2_predictions[(t2_predictions["outcome"].eq(outcome)) & (t2_predictions["model"].eq(model_name))]
        pred = pred.groupby("Subject_ID_D", as_index=False)["estimated_T2"].mean()
        observed = paired[["Subject_ID_D", f"{prefix}_T1_T1dataset", f"{prefix}_T2_T2dataset"]].copy()
        observed["observed_T1"] = pd.to_numeric(observed[f"{prefix}_T1_T1dataset"], errors="coerce")
        observed["observed_T2"] = pd.to_numeric(observed[f"{prefix}_T2_T2dataset"], errors="coerce")
        if outcome == "Global":
            estimates = t1_primary.copy()
        else:
            estimates = domain_t1[domain_t1["domain"].eq(outcome)][["Subject_ID_D", "group_ridge_prediction"]].copy()
            estimates["estimated_T1"] = pd.to_numeric(estimates["group_ridge_prediction"], errors="coerce")
            estimates = estimates[["Subject_ID_D", "estimated_T1"]]
        frame = observed[["Subject_ID_D", "observed_T1", "observed_T2"]].merge(estimates, on="Subject_ID_D", how="left").merge(pred, on="Subject_ID_D", how="left")
        frame = frame.rename(columns={"estimated_T2": "estimated_T2"})
        frame["actual_change"] = frame["observed_T2"] - frame["observed_T1"]
        frame["estimated_change"] = frame["estimated_T2"] - frame["estimated_T1"]
        frame["model_prediction"] = frame["estimated_change"]
        frame["outcome"] = outcome
        frame["target"] = f"{prefix}_T2_minus_T1"
        frame["model"] = model_name
        patient_rows.append(frame)
        valid = frame["actual_change"].notna() & frame["estimated_change"].notna()
        actual = frame.loc[valid, "actual_change"].to_numpy(dtype=float)
        estimated = frame.loc[valid, "estimated_change"].to_numpy(dtype=float)
        baseline = np.repeat(actual.mean(), len(actual))
        decline_metrics.extend(
            [
                metric(actual, baseline, outcome, "mean_change_baseline", "pooled", "pooled"),
                metric(actual, estimated, outcome, "independent_digital_decline", "pooled", "pooled"),
            ]
        )

    patient_predictions = pd.concat(patient_rows, ignore_index=True)
    metrics = pd.concat([metrics, pd.DataFrame(decline_metrics)], ignore_index=True).drop_duplicates(["analysis_scope", "repeat", "outcome", "model"], keep="first")
    t2_predictions.to_csv(PREDICTIONS_PATH, index=False)
    patient_predictions.to_csv(PATIENT_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    lines = [
        "# Phase 6 Independent T1/T2 Digital Phenotyping",
        "",
        "T1 and T2 digital phenotype scores are estimated independently from their corresponding timepoint features. The T2 estimate is not calculated as T1 plus predicted change.",
        "",
        "Digital change is calculated only after both independent estimates exist: estimated T2 minus estimated T1. Observed change is observed T2 minus observed T1.",
        "",
        "The T2 models use fold-local median imputation, missingness indicators, standardization, and Ridge regularization with repeated 5-fold cross-validation.",
        "",
        "## Pooled results",
        "",
    ]
    for row in metrics[metrics["analysis_scope"].eq("pooled")].itertuples():
        lines.append(f"- {row.outcome} / {row.model}: RMSE `{row.rmse:.3f}`, MAE `{row.mae:.3f}`, R2 `{row.r2:.3f}`.")
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"paired_patients: {len(paired)}")
    print(f"t2_prediction_rows: {len(t2_predictions)}")
    print(metrics[metrics["analysis_scope"].eq("pooled")][["outcome", "model", "n_predictions", "rmse", "mae", "r2"]].to_string(index=False))


if __name__ == "__main__":
    main()
