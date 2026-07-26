# Phase 4 T1 Ridge Model

This is the first exploratory patient-level model for Outcome 1. It compares a training-set mean predictor with ridge regression for continuous `global_T1`.

## Design

- Patients with non-missing `global_T1`: `81`.
- Primary features: `37`.
- Non-primary features retained for sensitivity analysis: `34`.
- Outer validation: repeated `5`-fold cross-validation, `20` repeats.
- Ridge alpha: selected inside each outer training fold using 4-fold inner cross-validation.
- Preprocessing: training-fold median imputation, missingness indicators, then standardization.
- The reference mean predictor uses only the training-fold target mean.

## Pooled Cross-Validated Results

- `mean_baseline`: RMSE `8.532`, MAE `6.797`, R2 `-0.000`.
- `ridge`: RMSE `8.725`, MAE `6.916`, R2 `-0.046`.
- Ridge pooled RMSE minus mean-baseline pooled RMSE: `0.193`.

## Interpretation Boundary

These are exploratory cross-validated associations in a small proof-of-concept cohort. They are not an externally validated prediction estimate. Repeated cross-validation gives a stability view, not an independent test-set result.

The non-primary features are not discarded. Adjusted-window features, low-coverage T1-week features, and zero-coverage features are retained in the feature-set audit and should be tested in separately labeled sensitivity analyses.

## Files

- `phase4_t1_ridge_predictions.csv`: fold-level predictions for both models.
- `phase4_t1_ridge_metrics.csv`: per-repeat and pooled metrics.
- `phase4_t1_ridge_feature_set.csv`: primary versus sensitivity feature decisions.
