# Phase 4 T1 Ridge Sensitivity Models

This run compares four baseline feature scopes against the same training-fold mean predictor for continuous `global_T1`.

## Design

- Patients with non-missing `global_T1`: `81`.
- Outer validation: repeated `5`-fold cross-validation, `20` repeats.
- Every scope uses the same outer splits and the same mean-baseline predictions within each split.
- Ridge alpha is selected inside each outer training fold using 4-fold inner cross-validation.
- Preprocessing is fit inside each training fold: median imputation, missingness indicators, then standardization.

## Feature Scopes

- `primary_37`: the 37 T1-week features observed in at least 50% of patients.
- `t1_week_all_available`: primary plus lower-coverage T1-week features; adjusted-window features excluded.
- `primary_plus_adjusted`: primary plus adjusted first-available features; lower-coverage T1-week features excluded.
- `all_available`: all observed T1-week and adjusted-window features except zero-coverage features.

## Pooled Cross-Validated Results

- `primary_37`: mean RMSE `8.532`, ridge RMSE `8.725`, ridge minus mean `0.193`, ridge R2 `-0.046`.
- `t1_week_all_available`: mean RMSE `8.532`, ridge RMSE `9.506`, ridge minus mean `0.974`, ridge R2 `-0.242`.
- `primary_plus_adjusted`: mean RMSE `8.532`, ridge RMSE `8.625`, ridge minus mean `0.093`, ridge R2 `-0.022`.
- `all_available`: mean RMSE `8.532`, ridge RMSE `9.048`, ridge minus mean `0.516`, ridge R2 `-0.125`.

## Interpretation Boundary

These are exploratory POC comparisons, not independent validation estimates. Adding features with lower coverage or a different acquisition rule can improve apparent fit while reducing interpretability and increasing instability.

The mean baseline is deliberately identical in meaning across all four comparisons: it predicts the training-fold mean `global_T1`. The results should be read as whether each feature scope adds value beyond that reference under the same resampling design.

## Files

- `phase4_t1_ridge_predictions.csv`: repeated outer-fold predictions for every scope and model.
- `phase4_t1_ridge_metrics.csv`: per-repeat and pooled metrics.
- `phase4_t1_ridge_feature_set.csv`: feature membership by scope.
- `phase4_t1_ridge_coefficients.csv`: outer-fold coefficient stability for ridge terms.
