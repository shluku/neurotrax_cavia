"""Phase 6 exploratory models for T1-to-T2 cognitive change."""

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
    t1 = pd.read_csv(T1_PATH, dtype=str)
    t2 = pd.read_csv(T2_PATH, dtype=str)
    summary = pd.read_csv(FEATURE_SUMMARY_PATH, dtype=str)
    summary["t2_coverage_percent"] = pd.to_numeric(summary["t2_coverage_percent"], errors="coerce")
    working_features = summary.loc[summary["t2_coverage_percent"].ge(10), "feature_name"].tolist()
    primary_features = summary.loc[
        summary["t2_analysis_role"].eq("primary_eligible_10pct"), "feature_name"
    ].tolist()

    paired = t1.merge(t2, on="Subject_ID_D", how="inner", suffixes=("_T1dataset", "_T2dataset"))
    delta_columns: dict[str, str] = {}
    for feature in working_features:
        if feature not in t1.columns or feature not in t2.columns:
            continue
        delta_name = f"delta__{feature}"
        paired[delta_name] = pd.to_numeric(paired[f"{feature}_T2dataset"], errors="coerce") - pd.to_numeric(
            paired[f"{feature}_T1dataset"], errors="coerce"
        )
        delta_columns[feature] = delta_name

    domain_taxonomy = pd.read_csv(TAXONOMY_PATH, dtype=str)
    domain_taxonomy = domain_taxonomy[domain_taxonomy["feature"].isin(delta_columns)].copy()
    domain_taxonomy.to_csv(DOMAIN_TAXONOMY_PATH, index=False)

    feature_set_rows = []
    for feature in working_features:
        feature_set_rows.append(
            {
                "feature_name": feature,
                "delta_column": delta_columns.get(feature, ""),
                "t2_coverage_percent": summary.loc[summary["feature_name"].eq(feature), "t2_coverage_percent"].iloc[0],
                "t2_analysis_role": summary.loc[summary["feature_name"].eq(feature), "t2_analysis_role"].iloc[0],
                "model_set": "t1_primary_10pct" if feature in primary_features else "working_10pct_support",
            }
        )
    pd.DataFrame(feature_set_rows).to_csv(FEATURE_SET_PATH, index=False)

    prediction_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    model_specs: dict[str, list[str]] = {
        "t1_primary_10pct_delta_ridge": [delta_columns[f] for f in primary_features if f in delta_columns],
        "working_10pct_delta_ridge": [delta_columns[f] for f in working_features if f in delta_columns],
    }

    for outcome, prefix in DOMAIN_TARGETS.items():
        target_name = f"{prefix}_T2_T2dataset"
        baseline_name = f"{prefix}_T1_T1dataset"
        if target_name not in paired.columns or baseline_name not in paired.columns:
            continue
        paired[f"observed_change__{outcome}"] = pd.to_numeric(paired[target_name], errors="coerce") - pd.to_numeric(
            paired[baseline_name], errors="coerce"
        )
        valid = paired[f"observed_change__{outcome}"].notna()
        outcome_data = paired.loc[valid].reset_index(drop=True)
        y = outcome_data[f"observed_change__{outcome}"].to_numpy(dtype=float)
        outcome_specs = dict(model_specs)
        if outcome != "Global":
            domain_features = domain_taxonomy.loc[domain_taxonomy["domain"].eq(outcome), "feature"].tolist()
            outcome_specs["domain_group_10pct_delta_ridge"] = [delta_columns[f] for f in domain_features if f in delta_columns]

        for model_name, feature_columns in outcome_specs.items():
            if not feature_columns:
                continue
            X = outcome_data[feature_columns].apply(pd.to_numeric, errors="coerce")
            outer = RepeatedKFold(n_splits=min(N_SPLITS, len(outcome_data)), n_repeats=N_REPEATS, random_state=RANDOM_STATE)
            buffers: dict[int, dict[str, list[float]]] = {}
            for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
                repeat = split_index // min(N_SPLITS, len(outcome_data)) + 1
                fold = split_index % min(N_SPLITS, len(outcome_data)) + 1
                baseline = np.repeat(y[train_idx].mean(), len(test_idx))
                model = build_pipeline()
                model.fit(X.iloc[train_idx], y[train_idx])
                prediction = model.predict(X.iloc[test_idx])
                buffers.setdefault(repeat, {"actual": [], "baseline": [], "model": []})
                buffers[repeat]["actual"].extend(y[test_idx].tolist())
                buffers[repeat]["baseline"].extend(baseline.tolist())
                buffers[repeat]["model"].extend(prediction.tolist())
                for row_index, row_pos in enumerate(test_idx):
                    prediction_rows.append(
                        {
                            "outcome": outcome,
                            "target": f"{prefix}_T2_minus_T1",
                            "model": model_name,
                            "repeat": repeat,
                            "fold": fold,
                            "Subject_ID_D": outcome_data.loc[row_pos, "Subject_ID_D"],
                            "actual_change": y[row_pos],
                            "mean_baseline_prediction": baseline[row_index],
                            "model_prediction": prediction[row_index],
                            "n_features": len(feature_columns),
                            "ridge_alpha": float(model.named_steps["ridge"].alpha_),
                        }
                    )
            for repeat, values in buffers.items():
                actual = np.asarray(values["actual"])
                metric_rows.append(metric_row(actual, np.asarray(values["baseline"]), outcome, "mean_baseline", repeat))
                metric_rows.append(metric_row(actual, np.asarray(values["model"]), outcome, model_name, repeat))

    predictions = pd.DataFrame(prediction_rows)
    if not predictions.empty:
        for (outcome, model), frame in predictions.groupby(["outcome", "model"], dropna=False):
            actual = frame["actual_change"].to_numpy(dtype=float)
            metric_rows.append(metric_row(actual, frame["mean_baseline_prediction"].to_numpy(dtype=float), outcome, "mean_baseline", "pooled"))
            metric_rows.append(metric_row(actual, frame["model_prediction"].to_numpy(dtype=float), outcome, model, "pooled"))
    patient_predictions = (
        predictions.groupby(["outcome", "target", "model", "Subject_ID_D"], dropna=False)
        .agg(actual_change=("actual_change", "first"), mean_baseline_prediction=("mean_baseline_prediction", "mean"), model_prediction=("model_prediction", "mean"))
        .reset_index()
    )
    metrics = pd.DataFrame(metric_rows)
    metrics = metrics.drop_duplicates(["analysis_scope", "repeat", "outcome", "model"], keep="first")
    predictions.to_csv(PREDICTIONS_PATH, index=False)
    patient_predictions.to_csv(PATIENT_PATH, index=False)
    metrics.to_csv(METRICS_PATH, index=False)
    lines = [
        "# Phase 6 T1-to-T2 Cognitive Decline Digital Phenotyping",
        "",
        "Outcome: cognitive change defined as T2 score minus T1 score. Predictors are paired digital-feature changes, T2 feature minus T1 feature.",
        "",
        "The active T2 feature set excludes light and uses features meeting the exploratory 10% T2 patient-coverage threshold. Missing predictors are handled inside each training fold with median imputation, missingness indicators, standardization, and Ridge alpha selection.",
        "",
        "All model comparisons use the same fold-local mean baseline and repeated 5-fold cross-validation. Results are exploratory because feature eligibility was defined from the current T2 coverage audit and the paired cohort is small.",
        "",
        "## Pooled results",
        "",
    ]
    if not metrics.empty:
        for row in metrics[metrics["analysis_scope"].eq("pooled")].itertuples():
            lines.append(f"- {row.outcome} / {row.model}: RMSE `{row.rmse:.3f}`, MAE `{row.mae:.3f}`, R2 `{row.r2:.3f}`.")
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"paired_patients: {len(paired)}")
    print(f"prediction_rows: {len(predictions)}")
    if not metrics.empty:
        print(metrics[metrics["analysis_scope"].eq("pooled")][["outcome", "model", "n_predictions", "rmse", "mae", "r2"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
