# Phase 6 T1-to-T2 Cognitive Decline Digital Phenotyping

Outcome: cognitive change defined as T2 score minus T1 score. Predictors are paired digital-feature changes, T2 feature minus T1 feature.

The active T2 feature set excludes light and uses features meeting the exploratory 10% T2 patient-coverage threshold. Missing predictors are handled inside each training fold with median imputation, missingness indicators, standardization, and Ridge alpha selection.

All model comparisons use the same fold-local mean baseline and repeated 5-fold cross-validation. Results are exploratory because feature eligibility was defined from the current T2 coverage audit and the paired cohort is small.

## Pooled results

- Attention / mean_baseline: RMSE `7.971`, MAE `5.984`, R2 `-0.046`.
- Attention / domain_group_10pct_delta_ridge: RMSE `7.977`, MAE `5.989`, R2 `-0.047`.
- Attention / t1_primary_10pct_delta_ridge: RMSE `7.984`, MAE `5.996`, R2 `-0.049`.
- Attention / working_10pct_delta_ridge: RMSE `8.596`, MAE `6.252`, R2 `-0.216`.
- Executive function / mean_baseline: RMSE `9.797`, MAE `7.651`, R2 `-0.028`.
- Executive function / domain_group_10pct_delta_ridge: RMSE `13.201`, MAE `8.706`, R2 `-0.867`.
- Executive function / t1_primary_10pct_delta_ridge: RMSE `11.789`, MAE `8.444`, R2 `-0.489`.
- Executive function / working_10pct_delta_ridge: RMSE `11.832`, MAE `8.369`, R2 `-0.500`.
- Global / mean_baseline: RMSE `5.843`, MAE `4.347`, R2 `-0.037`.
- Global / t1_primary_10pct_delta_ridge: RMSE `5.948`, MAE `4.443`, R2 `-0.075`.
- Global / working_10pct_delta_ridge: RMSE `5.913`, MAE `4.435`, R2 `-0.062`.
- Memory / mean_baseline: RMSE `10.860`, MAE `8.026`, R2 `-0.032`.
- Memory / domain_group_10pct_delta_ridge: RMSE `10.943`, MAE `8.103`, R2 `-0.047`.
- Memory / t1_primary_10pct_delta_ridge: RMSE `10.981`, MAE `8.128`, R2 `-0.055`.
- Memory / working_10pct_delta_ridge: RMSE `10.918`, MAE `8.076`, R2 `-0.043`.
- Motor / mean_baseline: RMSE `8.047`, MAE `5.891`, R2 `-0.042`.
- Motor / domain_group_10pct_delta_ridge: RMSE `8.302`, MAE `6.009`, R2 `-0.109`.
- Motor / t1_primary_10pct_delta_ridge: RMSE `8.126`, MAE `5.935`, R2 `-0.062`.
- Motor / working_10pct_delta_ridge: RMSE `8.697`, MAE `6.233`, R2 `-0.217`.
- Processing speed / mean_baseline: RMSE `12.226`, MAE `8.269`, R2 `-0.037`.
- Processing speed / domain_group_10pct_delta_ridge: RMSE `12.444`, MAE `8.588`, R2 `-0.074`.
- Processing speed / t1_primary_10pct_delta_ridge: RMSE `12.322`, MAE `8.338`, R2 `-0.053`.
- Processing speed / working_10pct_delta_ridge: RMSE `12.351`, MAE `8.364`, R2 `-0.058`.
