from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).parent
MODEL_DIR = ROOT / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge"
PREDICTIONS_PATH = MODEL_DIR / "phase4_t1_ridge_predictions.csv"
COEFFICIENTS_PATH = MODEL_DIR / "phase4_t1_ridge_coefficients.csv"

CALIBRATION_PATH = MODEL_DIR / "phase4_t1_score_calibration_by_patient.csv"
CALIBRATION_BINS_PATH = MODEL_DIR / "phase4_t1_score_calibration_bins.csv"
CALIBRATION_METRICS_PATH = MODEL_DIR / "phase4_t1_score_calibration_metrics.csv"
COEFFICIENT_SUMMARY_PATH = MODEL_DIR / "phase4_t1_ridge_coefficient_summary.csv"
README_PATH = MODEL_DIR / "README_phase4_t1_score_calibration.md"


def calibration_line(actual: np.ndarray, predicted: np.ndarray) -> tuple[float, float, float]:
    slope, intercept = np.polyfit(predicted, actual, 1)
    correlation = np.corrcoef(actual, predicted)[0, 1] if len(actual) > 1 else np.nan
    return float(slope), float(intercept), float(correlation)


def main() -> None:
    predictions = pd.read_csv(PREDICTIONS_PATH, dtype={"Subject_ID_D": str})
    coefficients = pd.read_csv(COEFFICIENTS_PATH, dtype=str)
    patient_rows: list[pd.DataFrame] = []
    bin_rows: list[pd.DataFrame] = []
    metric_rows: list[dict[str, object]] = []

    for scope, group in predictions.groupby("feature_scope"):
        patient = (
            group.groupby(["Subject_ID_D", "Subject_ID_N"], dropna=False)
            .agg(
                actual_global_T1=("actual_global_T1", "first"),
                mean_baseline_prediction=("mean_baseline_prediction", "mean"),
                ridge_prediction=("ridge_prediction", "mean"),
            )
            .reset_index()
        )
        patient["feature_scope"] = scope
        patient["ridge_error"] = patient["ridge_prediction"] - patient["actual_global_T1"]
        patient["mean_baseline_error"] = patient["mean_baseline_prediction"] - patient["actual_global_T1"]
        patient_rows.append(patient)

        for model_name, prediction_column in [("mean_baseline", "mean_baseline_prediction"), ("ridge", "ridge_prediction")]:
            actual = patient["actual_global_T1"].to_numpy(dtype=float)
            predicted = patient[prediction_column].to_numpy(dtype=float)
            slope, intercept, correlation = calibration_line(actual, predicted)
            metric_rows.append(
                {
                    "feature_scope": scope,
                    "model": model_name,
                    "n_patients": len(patient),
                    "rmse": float(np.sqrt(np.mean((actual - predicted) ** 2))),
                    "mae": float(np.mean(np.abs(actual - predicted))),
                    "calibration_slope_actual_on_predicted": slope,
                    "calibration_intercept": intercept,
                    "actual_predicted_correlation": correlation,
                    "actual_mean": actual.mean(),
                    "predicted_mean": predicted.mean(),
                }
            )
            binned = patient.copy()
            binned["prediction_bin"] = pd.qcut(predicted, q=4, duplicates="drop")
            binned = (
                binned.groupby("prediction_bin", observed=False)
                .agg(
                    feature_scope=("feature_scope", "first"),
                    n_patients=("actual_global_T1", "size"),
                    mean_actual_global_T1=("actual_global_T1", "mean"),
                    mean_predicted_global_T1=(prediction_column, "mean"),
                )
                .reset_index()
            )
            binned["model"] = model_name
            bin_rows.append(binned)

    calibration = pd.concat(patient_rows, ignore_index=True)
    calibration_bins = pd.concat(bin_rows, ignore_index=True)
    metrics = pd.DataFrame(metric_rows)

    coefficients["coefficient"] = pd.to_numeric(coefficients["coefficient"], errors="coerce")
    coefficient_summary = (
        coefficients.groupby(["feature_scope", "term_name"], dropna=False)
        .agg(
            coefficient_mean=("coefficient", "mean"),
            coefficient_sd=("coefficient", "std"),
            coefficient_median=("coefficient", "median"),
            coefficient_positive_fraction=("coefficient", lambda x: float((x > 0).mean())),
            n_outer_folds=("coefficient", "size"),
        )
        .reset_index()
    )
    coefficient_summary["absolute_mean_coefficient"] = coefficient_summary["coefficient_mean"].abs()
    coefficient_summary = coefficient_summary.sort_values(["feature_scope", "absolute_mean_coefficient"], ascending=[True, False])

    calibration.to_csv(CALIBRATION_PATH, index=False)
    calibration_bins.to_csv(CALIBRATION_BINS_PATH, index=False)
    metrics.to_csv(CALIBRATION_METRICS_PATH, index=False)
    coefficient_summary.to_csv(COEFFICIENT_SUMMARY_PATH, index=False)

    primary = metrics[(metrics["feature_scope"] == "primary_37") & (metrics["model"] == "ridge")].iloc[0]
    README_PATH.write_text(
        f"""# Phase 4 T1 Score Calibration and Interpretation

This report summarizes patient-level repeated cross-validated ridge predictions for continuous `global_T1`.

## Calibration

Calibration checks whether predicted scores track actual scores on the correct scale. For the primary ridge model: RMSE `{primary['rmse']:.3f}`, MAE `{primary['mae']:.3f}`, calibration slope `{primary['calibration_slope_actual_on_predicted']:.3f}`, intercept `{primary['calibration_intercept']:.3f}`, and actual-predicted correlation `{primary['actual_predicted_correlation']:.3f}`.

The Streamlit page displays actual-versus-predicted points and prediction bins. The diagonal reference means perfect agreement.

## Interpretation

`phase4_t1_ridge_coefficient_summary.csv` summarizes coefficient direction and stability across outer folds. Coefficients are exploratory associations, not causal or clinical effects. Terms with unstable signs should not be treated as reliable findings.

Missingness indicators are included in the coefficient output and must be distinguished from behavior features.

## Boundary

The digital window is generally after T1. This is a T1-anchored digital estimate of an already observed T1 score, not prospective prediction of a future assessment. It is exploratory and not for clinical use.
""",
        encoding="utf-8",
    )
    print(f"patient_rows: {len(calibration)}")
    print(f"metric_rows: {len(metrics)}")
    print(f"coefficient_summary_rows: {len(coefficient_summary)}")


if __name__ == "__main__":
    main()
