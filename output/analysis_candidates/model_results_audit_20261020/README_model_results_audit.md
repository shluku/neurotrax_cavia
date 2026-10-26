# Historical model-results audit — 2026-10-20

This is a reporting correction, not a model rerun. `audit_historical_model_results.py` reads the saved out-of-fold prediction rows for three historical candidates and recomputes RMSE, MAE, and R² only from the actual outcome and prediction stored on the same row. It does not read raw sensor data, fit a model, select a feature, or change a historical file.

## Why correction was necessary

The historical scripts formed their pooled outcome vector with `np.tile(y, n_repeats)`, while their predictions were appended in randomized outer-test-fold order. The two arrays therefore did not preserve patient/outcome alignment. Historical `analysis_scope=pooled` rows are retained as provenance but are invalid for performance reporting.

Every corrected candidate passed the saved-file integrity checks: each participant appears exactly once in each repeat, there are five folds per repeat, there are no duplicate participant/repeat rows or missing prediction rows, and the saved actual outcome matches the source patient table for every eligible participant.

## Corrected primary comparison

Values below are means across repeated out-of-fold runs; the row-aligned pooled values are in `corrected_model_summary.csv`. Repeat percentile ranges and fold values are descriptive of resampling variability, not independent 95% confidence intervals.

| Candidate | n / repeats | RMSE model vs mean | MAE model vs mean | R² model vs mean | Assessment |
|---|---:|---:|---:|---:|---|
| Processing Speed, 10-day Ridge | 71 / 20 | 12.950 vs 13.718 | 10.380 vs 11.259 | .0799 vs −.0278 | Most credible historical candidate; modest gain, exploratory. |
| Motor, 24-hour Ridge | 79 / 20 | 10.186 vs 10.678 | 8.571 vs 8.925 | .0559 vs −.0371 | Modest larger-cohort result; exploratory. |
| Global, coverage Top-10 elastic net | 10 / 10 | 7.978 vs 10.454 | 6.514 vs 7.873 | .2657 vs −.2350 | Descriptive only: n=10 and selected among many models/cohorts. |

Conditional participant-cluster bootstrap intervals for the RMSE improvement (mean baseline RMSE minus model RMSE) are **0.75 [−1.13, 2.37]** for Processing Speed, **0.48 [−0.31, 1.20]** for Motor, and **2.12 [−1.93, 5.57]** for Top-10 Global. They retain all repeated predictions for each sampled patient and do not refit models. All include zero, so none establishes reliable superiority over the mean baseline.

## Files

- `historical_pooled_vs_corrected_metrics.csv`: invalid historical pooled rows beside their row-aligned replacement.
- `corrected_model_summary.csv`: row-aligned pooled metrics and repeat-level means, SDs and percentile ranges.
- `corrected_model_vs_mean_baseline.csv`: fold-matched model–baseline improvements. Positive values mean improvement.
- `model_vs_mean_cluster_bootstrap.csv`: conditional patient-cluster bootstrap intervals for the fixed saved-prediction comparison.
- `corrected_metrics_by_repeat.csv` and `corrected_metrics_by_fold.csv`: reproducible component metrics.
- `cv_and_alignment_audit.csv`: participant alignment, outer-CV structure and code-audit findings.
- `candidate_feature_sets.csv`: exact feature names used by each historical candidate. Candidate-specific coefficients were not saved and cannot be recovered from predictions.

## Validation limits and research freeze

The outer test folds were protected: source code fit imputation/scaling and the prediction model on each outer training partition before scoring the outer test partition. However, preprocessing was fit before the inner `RidgeCV`/`ElasticNetCV` splits, so inner tuning was not fully nested. None of the candidates has an independent test cohort. The top-10 Elastic Net also used all 67 available metadata features and was retained after a wide model/cohort screen; it must not be treated as the main result.

Freeze the confirmatory target as **Processing Speed T1, the 10-day first-available-post-T1 window, and the fixed 37-feature primary panel**. It has a meaningful sample size (n=71), the larger mean RMSE/MAE improvement, a pre-defined feature panel, and less selection pressure than the top-10 result. It is temporally post-T1, so a future study should describe it as a concurrent digital correlate of T1 performance, not a prospective baseline predictor. A prospective claim requires data collected before the cognitive assessment.

The future confirmatory protocol should use a new held-out cohort, pre-specify eligibility and the 37 features, place imputation/scaling and Ridge alpha tuning inside a fully nested pipeline, retain the same patients/folds for the mean baseline, and report patient-level paired uncertainty. No new model was trained in this audit.
