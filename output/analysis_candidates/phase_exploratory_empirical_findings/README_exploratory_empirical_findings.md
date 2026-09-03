# Exploratory Empirical Findings

This phase models observed `global_T1` using only six features selected from the exploratory Phase 11 baseline-severity comparison.

## Selected findings

The six features and their exploratory directions are fixed from the source comparison table. P-values are used for transparent reporting and feature selection; they are not used as predictive weights.

## Model protocol

- Missing values are imputed with the training-fold median. Missingness indicators are not added, so acquisition coverage is not intentionally treated as phenotype.
- Each oriented feature is centered by its training-fold median and divided by its training-fold IQR. This is the minimum scaling needed to combine milliseconds and event counts without one unit dominating.
- The equal-weight empirical score averages the six robust oriented features and uses a positive calibration to T1.
- The primary direction-constrained Ridge uses only the six oriented features and positive coefficients. Therefore, a feature cannot reverse its observed direction in the fitted estimate.
- All results are compared with the same fold-local mean baseline using repeated 5-fold cross-validation.

## Pooled results

- mean_baseline: RMSE `8.664`, MAE `6.912`, R2 `-0.032`.
- equal_weight_empirical_score: RMSE `8.867`, MAE `7.077`, R2 `-0.080`.
- direction_constrained_ridge: RMSE `9.863`, MAE `7.363`, R2 `-0.337`.

## Important limitation

Only 13 of 81 patients have all six features observed. Three call features have only 14 observed patients each. Feature-wise median imputation allows all patients to remain in the exploratory model, but the call-related contribution is supported by very sparse data.

This is an exploratory empirical model, not a confirmatory clinical prediction model. The feature selection and directions were discovered in the same 81-patient cohort used for evaluation, so the cross-validated results can still be optimistic.
