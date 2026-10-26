#!/usr/bin/env python3
"""Correct reporting metrics for selected historical saved prediction files.

This audit deliberately does *not* fit a model.  It recomputes performance only
from the row-aligned out-of-fold predictions already saved by the historical
scripts.  Outputs go to a new directory so the original model outputs remain
an immutable historical record.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


ROOT = Path(__file__).parent
OUT_DIR = ROOT / "output/analysis_candidates/model_results_audit_20261020"
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_RANDOM_STATE = 20261020

CANDIDATES = (
    {
        "candidate": "Processing Speed — 10-day Ridge",
        "short_name": "processing_speed_10day_ridge",
        "prediction_path": ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/model_t1_cognitive_domains/phase4_t1_cognitive_domain_predictions.csv",
        "historical_metrics_path": ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/model_t1_cognitive_domains/phase4_t1_cognitive_domain_metrics.csv",
        "dataset_path": ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/phase4_10day_t1_baseline_patient_dataset.csv",
        "metadata_path": ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/phase4_10day_t1_baseline_feature_metadata.csv",
        "filter_column": "domain",
        "filter_value": "Processing speed",
        "actual_column": "actual_T1",
        "target_column": "processing_speed_T1",
        "model_column": "ridge_prediction",
        "model": "ridge",
        "feature_scope": "37 fixed rows where primary_model_recommendation = include_primary",
        "expected_n": 71,
        "expected_repeats": 20,
        "source_script": "phase4_model_t1_cognitive_domains.py",
        "cohort_path": None,
        "historical_domain": "Processing speed",
        "historical_cohort_size": None,
    },
    {
        "candidate": "Motor — 24-hour Ridge",
        "short_name": "motor_24hour_ridge",
        "prediction_path": ROOT / "output/analysis_candidates/phase4_t1_baseline/model_t1_cognitive_domains/phase4_t1_cognitive_domain_predictions.csv",
        "historical_metrics_path": ROOT / "output/analysis_candidates/phase4_t1_baseline/model_t1_cognitive_domains/phase4_t1_cognitive_domain_metrics.csv",
        "dataset_path": ROOT / "output/analysis_candidates/phase4_t1_baseline/phase4_t1_baseline_patient_dataset.csv",
        "metadata_path": ROOT / "output/analysis_candidates/phase4_t1_baseline/phase4_t1_baseline_feature_metadata.csv",
        "filter_column": "domain",
        "filter_value": "Motor",
        "actual_column": "actual_T1",
        "target_column": "motor_T1",
        "model_column": "ridge_prediction",
        "model": "ridge",
        "feature_scope": "37 fixed rows where primary_model_recommendation = include_primary",
        "expected_n": 79,
        "expected_repeats": 20,
        "source_script": "phase4_model_t1_cognitive_domains.py",
        "cohort_path": None,
        "historical_domain": "Motor",
        "historical_cohort_size": None,
    },
    {
        "candidate": "Global — Coverage Top-10 Elastic Net",
        "short_name": "global_coverage_top10_elastic_net",
        "prediction_path": ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_coverage_predictions.csv",
        "historical_metrics_path": ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_coverage_metrics.csv",
        "dataset_path": ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/phase4_10day_t1_baseline_patient_dataset.csv",
        "metadata_path": ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/phase4_10day_t1_baseline_feature_metadata.csv",
        "filter_column": "cohort_size",
        "filter_value": 10,
        "actual_column": "actual_global_T1",
        "target_column": "global_T1",
        "model_column": "elastic_net_prediction",
        "model": "elastic_net",
        "feature_scope": "all 67 metadata feature rows; cohort ranked by feature missingness/table coverage before modelling",
        "expected_n": 10,
        "expected_repeats": 10,
        "source_script": "suggestions_10day_coverage_models.py + other_models_phase4_10day.py",
        "cohort_path": ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_coverage_cohorts.csv",
        "historical_domain": None,
        "historical_cohort_size": 10,
    },
)


def metrics(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    """Metrics computed only from paired rows in the saved prediction file."""
    return {
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
    }


def percentile_interval(values: pd.Series) -> tuple[float, float]:
    return tuple(float(x) for x in np.quantile(values, [0.025, 0.975]))


def source_alignment(frame: pd.DataFrame, spec: dict[str, object]) -> tuple[int, int, int]:
    """Verify saved actual values against the matching source patient table."""
    source = pd.read_csv(spec["dataset_path"], dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    source = source[["Subject_ID_D", "Subject_ID_N", spec["target_column"]]].copy()
    source[spec["target_column"]] = pd.to_numeric(source[spec["target_column"]], errors="coerce")
    source = source.drop_duplicates(["Subject_ID_D", "Subject_ID_N"])
    observed = frame[["Subject_ID_D", "Subject_ID_N", spec["actual_column"]]].drop_duplicates()
    checked = observed.merge(source, on=["Subject_ID_D", "Subject_ID_N"], how="left", validate="one_to_one")
    matched = np.isclose(
        checked[spec["actual_column"]].to_numpy(dtype=float),
        checked[spec["target_column"]].to_numpy(dtype=float),
        equal_nan=False,
    )
    return len(checked), int(matched.sum()), int(checked[spec["target_column"]].isna().sum())


def bootstrap_patient_cluster_intervals(frame: pd.DataFrame, actual_col: str, model_col: str, spec: dict[str, object]) -> dict[str, object]:
    """Conditional participant-cluster bootstrap of fixed saved OOF predictions.

    All repeated predictions belonging to a sampled participant stay together.
    This quantifies sampling uncertainty in the saved predictions; it is not an
    independent validation and does not refit the models.
    """
    rng = np.random.default_rng(BOOTSTRAP_RANDOM_STATE)
    patient_ids = frame["Subject_ID_D"].drop_duplicates().to_numpy()
    by_patient = {patient: group for patient, group in frame.groupby("Subject_ID_D", sort=False)}
    deltas: dict[str, list[float]] = {"rmse": [], "mae": [], "r2": []}
    for _ in range(BOOTSTRAP_REPLICATES):
        sampled = rng.choice(patient_ids, size=len(patient_ids), replace=True)
        sample = pd.concat([by_patient[patient] for patient in sampled], ignore_index=True)
        baseline = metrics(sample[actual_col], sample["mean_baseline_prediction"])
        model = metrics(sample[actual_col], sample[model_col])
        deltas["rmse"].append(baseline["rmse"] - model["rmse"])
        deltas["mae"].append(baseline["mae"] - model["mae"])
        deltas["r2"].append(model["r2"] - baseline["r2"])
    result: dict[str, object] = {
        "candidate": spec["candidate"], "short_name": spec["short_name"], "model": spec["model"],
        "n_unique_patients": len(patient_ids), "n_repeats_retained_per_patient": int(frame["repeat"].nunique()),
        "bootstrap_replicates": BOOTSTRAP_REPLICATES, "bootstrap_random_state": BOOTSTRAP_RANDOM_STATE,
        "interpretation": "Conditional participant-cluster bootstrap of saved repeated OOF predictions; not independent validation.",
    }
    for metric, values in deltas.items():
        low, high = percentile_interval(pd.Series(values))
        result[f"improvement_{metric}"] = float(np.mean(values))
        result[f"bootstrap95_low_improvement_{metric}"] = low
        result[f"bootstrap95_high_improvement_{metric}"] = high
    return result


def audit_candidate(spec: dict[str, object]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object], pd.DataFrame]:
    raw = pd.read_csv(spec["prediction_path"], dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    frame = raw.loc[raw[spec["filter_column"]].eq(spec["filter_value"])].copy()
    actual_col = spec["actual_column"]
    model_col = spec["model_column"]
    required = ["repeat", "fold", "Subject_ID_D", "Subject_ID_N", actual_col, "mean_baseline_prediction", model_col]
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(f"{spec['candidate']}: missing columns {missing}")
    for column in (actual_col, "mean_baseline_prediction", model_col):
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    repeat_rows: list[dict[str, object]] = []
    fold_rows: list[dict[str, object]] = []
    for repeat, repeat_frame in frame.groupby("repeat", sort=True):
        for model, prediction_col in (("mean_baseline", "mean_baseline_prediction"), (spec["model"], model_col)):
            repeat_rows.append({
                "candidate": spec["candidate"], "short_name": spec["short_name"], "repeat": int(repeat),
                "model": model, "n_patients": len(repeat_frame), **metrics(repeat_frame[actual_col], repeat_frame[prediction_col]),
            })
        for fold, fold_frame in repeat_frame.groupby("fold", sort=True):
            for model, prediction_col in (("mean_baseline", "mean_baseline_prediction"), (spec["model"], model_col)):
                fold_rows.append({
                    "candidate": spec["candidate"], "short_name": spec["short_name"], "repeat": int(repeat), "fold": int(fold),
                    "model": model, "n_patients": len(fold_frame), **metrics(fold_frame[actual_col], fold_frame[prediction_col]),
                })

    repeats = pd.DataFrame(repeat_rows)
    folds = pd.DataFrame(fold_rows)
    summary_rows: list[dict[str, object]] = []
    for model, prediction_col in (("mean_baseline", "mean_baseline_prediction"), (spec["model"], model_col)):
        pooled = metrics(frame[actual_col], frame[prediction_col])
        model_repeats = repeats.loc[repeats["model"].eq(model)]
        summary_rows.append({
            "candidate": spec["candidate"], "short_name": spec["short_name"], "model": model,
            "n_unique_patients": frame["Subject_ID_D"].nunique(), "n_repeats": frame["repeat"].nunique(),
            "n_row_aligned_oof_predictions": len(frame),
            **{f"pooled_{key}": value for key, value in pooled.items()},
            **{f"repeat_mean_{key}": float(model_repeats[key].mean()) for key in ("rmse", "mae", "r2")},
            **{f"repeat_sd_{key}": float(model_repeats[key].std(ddof=1)) for key in ("rmse", "mae", "r2")},
            **{f"repeat_p025_{key}": percentile_interval(model_repeats[key])[0] for key in ("rmse", "mae", "r2")},
            **{f"repeat_p975_{key}": percentile_interval(model_repeats[key])[1] for key in ("rmse", "mae", "r2")},
        })

    baseline = repeats.loc[repeats["model"].eq("mean_baseline")].set_index("repeat")
    model = repeats.loc[repeats["model"].eq(spec["model"])].set_index("repeat")
    comparison = {"candidate": spec["candidate"], "short_name": spec["short_name"], "model": spec["model"],
                  "n_unique_patients": frame["Subject_ID_D"].nunique(), "n_repeats": len(model)}
    for metric in ("rmse", "mae", "r2"):
        # Positive values consistently mean a benefit for the model over the baseline.
        delta = baseline[metric] - model[metric] if metric != "r2" else model[metric] - baseline[metric]
        low, high = percentile_interval(delta)
        comparison.update({
            f"mean_improvement_{metric}": float(delta.mean()),
            f"sd_improvement_{metric}": float(delta.std(ddof=1)),
            f"p025_improvement_{metric}": low,
            f"p975_improvement_{metric}": high,
            f"repeats_improved_{metric}": int((delta > 0).sum()),
        })

    checked, matched, missing_source = source_alignment(frame, spec)
    group_sizes = frame.groupby("repeat").agg(rows=("Subject_ID_D", "size"), patients=("Subject_ID_D", "nunique"), folds=("fold", "nunique"))
    metadata = pd.read_csv(spec["metadata_path"], dtype=str)
    if spec["short_name"] == "global_coverage_top10_elastic_net":
        features = metadata["feature_name"].dropna().tolist()
    else:
        features = metadata.loc[metadata["primary_model_recommendation"].eq("include_primary"), "feature_name"].dropna().tolist()
    feature_table = pd.DataFrame({"candidate": spec["candidate"], "feature_order": range(1, len(features) + 1), "feature_name": features})
    integrity = {
        "candidate": spec["candidate"], "short_name": spec["short_name"], "source_script": spec["source_script"],
        "n_rows": len(frame), "n_unique_patients": frame["Subject_ID_D"].nunique(), "n_repeats": frame["repeat"].nunique(),
        "n_folds_per_repeat_min": int(group_sizes["folds"].min()), "n_folds_per_repeat_max": int(group_sizes["folds"].max()),
        "duplicate_repeat_patient_rows": int(frame.duplicated(["repeat", "Subject_ID_D"]).sum()),
        "repeats_with_all_patients_once": bool((group_sizes["rows"] == spec["expected_n"]).all() and (group_sizes["patients"] == spec["expected_n"]).all()),
        "actual_constant_within_patient_across_repeats": bool((frame.groupby("Subject_ID_D")[actual_col].nunique() == 1).all()),
        "source_actual_patients_checked": checked, "source_actual_patients_matched": matched, "source_actual_patients_missing": missing_source,
        "prediction_or_actual_missing_rows": int(frame[[actual_col, "mean_baseline_prediction", model_col]].isna().any(axis=1).sum()),
        "feature_count": len(features), "feature_scope": spec["feature_scope"],
        "outer_test_leakage_assessment": "No evidence in source code: predictions are produced after outer-train-only preprocessing/model fitting.",
        "inner_cv_preprocessing_assessment": "Not fully nested: imputer/scaler are fit once on the outer training set before RidgeCV/ElasticNetCV inner splits.",
        "feature_contributions_saved": "No candidate-specific fold coefficients or feature-attribution output was saved; contributions cannot be reconstructed from predictions.",
    }
    bootstrap = bootstrap_patient_cluster_intervals(frame, actual_col, model_col, spec)
    return repeats, folds, {"summary": summary_rows, "comparison": comparison, "integrity": integrity, "bootstrap": bootstrap}, feature_table


def historical_vs_corrected(spec: dict[str, object], summary: pd.DataFrame) -> list[dict[str, object]]:
    """Keep invalid legacy pooled values visible beside their aligned replacement."""
    old = pd.read_csv(spec["historical_metrics_path"])
    old = old.loc[old["analysis_scope"].eq("pooled")].copy()
    if spec["historical_domain"] is not None:
        old = old.loc[old["domain"].eq(spec["historical_domain"])]
    if spec["historical_cohort_size"] is not None:
        old = old.loc[old["cohort_size"].eq(spec["historical_cohort_size"])]
    replacement = summary.loc[summary["short_name"].eq(spec["short_name"])]
    rows: list[dict[str, object]] = []
    for model in ("mean_baseline", spec["model"]):
        old_row = old.loc[old["model"].eq(model)].iloc[0]
        new_row = replacement.loc[replacement["model"].eq(model)].iloc[0]
        rows.append({
            "candidate": spec["candidate"], "model": model,
            "historical_pooled_rmse_INVALID": old_row["rmse"], "historical_pooled_mae_INVALID": old_row["mae"], "historical_pooled_r2_INVALID": old_row["r2"],
            "corrected_row_aligned_pooled_rmse": new_row["pooled_rmse"], "corrected_row_aligned_pooled_mae": new_row["pooled_mae"], "corrected_row_aligned_pooled_r2": new_row["pooled_r2"],
            "corrected_repeat_mean_rmse": new_row["repeat_mean_rmse"], "corrected_repeat_mean_mae": new_row["repeat_mean_mae"], "corrected_repeat_mean_r2": new_row["repeat_mean_r2"],
            "note": "Historical pooled values are invalid because tiled outcomes and randomized test-fold predictions were not patient-aligned.",
        })
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_repeats: list[pd.DataFrame] = []
    all_folds: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []
    comparisons: list[dict[str, object]] = []
    integrity_rows: list[dict[str, object]] = []
    features: list[pd.DataFrame] = []
    historical_comparisons: list[dict[str, object]] = []
    bootstrap_rows: list[dict[str, object]] = []
    for spec in CANDIDATES:
        repeats, folds, result, feature_table = audit_candidate(spec)
        all_repeats.append(repeats)
        all_folds.append(folds)
        summaries.extend(result["summary"])
        comparisons.append(result["comparison"])
        integrity_rows.append(result["integrity"])
        features.append(feature_table)
        historical_comparisons.extend(historical_vs_corrected(spec, pd.DataFrame(result["summary"])))
        bootstrap_rows.append(result["bootstrap"])

    pd.concat(all_repeats, ignore_index=True).to_csv(OUT_DIR / "corrected_metrics_by_repeat.csv", index=False)
    pd.concat(all_folds, ignore_index=True).to_csv(OUT_DIR / "corrected_metrics_by_fold.csv", index=False)
    pd.DataFrame(summaries).to_csv(OUT_DIR / "corrected_model_summary.csv", index=False)
    pd.DataFrame(comparisons).to_csv(OUT_DIR / "corrected_model_vs_mean_baseline.csv", index=False)
    pd.DataFrame(integrity_rows).to_csv(OUT_DIR / "cv_and_alignment_audit.csv", index=False)
    pd.DataFrame(historical_comparisons).to_csv(OUT_DIR / "historical_pooled_vs_corrected_metrics.csv", index=False)
    pd.DataFrame(bootstrap_rows).to_csv(OUT_DIR / "model_vs_mean_cluster_bootstrap.csv", index=False)
    pd.concat(features, ignore_index=True).to_csv(OUT_DIR / "candidate_feature_sets.csv", index=False)
    manifest = {
        "audit_date": "2026-10-20",
        "purpose": "Recalculate metrics only from row-aligned saved predictions; no model fit was run.",
        "historical_pooled_metric_problem": "Historical scripts used np.tile(y, n_repeats) while saved test predictions are ordered by randomized outer test folds. Those vectors are not patient-aligned.",
        "corrected_metric_method": "Use each prediction row's saved actual outcome and prediction from the same row. Aggregate as repeated-OOF pooled rows and separately as per-repeat summaries.",
        "candidates": [{key: str(value) for key, value in spec.items() if key not in {"prediction_path", "dataset_path", "metadata_path", "cohort_path"}} for spec in CANDIDATES],
    }
    (OUT_DIR / "audit_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote audit-only outputs to {OUT_DIR}")


if __name__ == "__main__":
    main()
