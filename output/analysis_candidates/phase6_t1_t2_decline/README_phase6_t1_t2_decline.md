# Phase 6 Independent T1/T2 Digital Phenotyping

T1 and T2 digital phenotype scores are estimated independently from their corresponding timepoint features. The T2 estimate is not calculated as T1 plus predicted change.

Digital change is calculated only after both independent estimates exist: estimated T2 minus estimated T1. Observed change is observed T2 minus observed T1.

The T2 models use fold-local median imputation, missingness indicators, standardization, and Ridge regularization with repeated 5-fold cross-validation.

## Pooled results

- Global / mean_baseline_T2: RMSE `8.164`, MAE `6.389`, R2 `-0.033`.
- Global / t1_primary_10pct_independent_t2_ridge: RMSE `8.780`, MAE `6.647`, R2 `-0.195`.
- Global / working_10pct_independent_t2_ridge: RMSE `8.534`, MAE `6.574`, R2 `-0.129`.
- Memory / mean_baseline_T2: RMSE `12.301`, MAE `10.175`, R2 `-0.029`.
- Memory / Memory_domain_independent_t2_ridge: RMSE `12.365`, MAE `10.227`, R2 `-0.040`.
- Executive function / mean_baseline_T2: RMSE `10.600`, MAE `8.247`, R2 `-0.034`.
- Executive function / Executive function_domain_independent_t2_ridge: RMSE `10.797`, MAE `8.392`, R2 `-0.073`.
- Processing speed / mean_baseline_T2: RMSE `15.714`, MAE `12.373`, R2 `-0.028`.
- Processing speed / Processing speed_domain_independent_t2_ridge: RMSE `16.201`, MAE `12.880`, R2 `-0.093`.
- Attention / mean_baseline_T2: RMSE `10.275`, MAE `7.908`, R2 `-0.022`.
- Attention / Attention_domain_independent_t2_ridge: RMSE `10.542`, MAE `8.077`, R2 `-0.075`.
- Motor / mean_baseline_T2: RMSE `8.724`, MAE `6.632`, R2 `-0.055`.
- Motor / Motor_domain_independent_t2_ridge: RMSE `9.076`, MAE `6.853`, R2 `-0.142`.
- Global / mean_change_baseline: RMSE `5.738`, MAE `4.269`, R2 `0.000`.
- Global / independent_digital_decline: RMSE `6.198`, MAE `4.506`, R2 `-0.167`.
- Memory / mean_change_baseline: RMSE `10.692`, MAE `7.894`, R2 `0.000`.
- Memory / independent_digital_decline: RMSE `11.156`, MAE `8.350`, R2 `-0.089`.
- Executive function / mean_change_baseline: RMSE `9.662`, MAE `7.545`, R2 `0.000`.
- Executive function / independent_digital_decline: RMSE `10.541`, MAE `8.122`, R2 `-0.190`.
- Processing speed / mean_change_baseline: RMSE `12.006`, MAE `8.106`, R2 `0.000`.
- Processing speed / independent_digital_decline: RMSE `12.980`, MAE `9.006`, R2 `-0.169`.
- Attention / mean_change_baseline: RMSE `7.794`, MAE `5.822`, R2 `0.000`.
- Attention / independent_digital_decline: RMSE `8.808`, MAE `6.727`, R2 `-0.277`.
- Motor / mean_change_baseline: RMSE `7.884`, MAE `5.757`, R2 `0.000`.
- Motor / independent_digital_decline: RMSE `8.188`, MAE `6.273`, R2 `-0.079`.
