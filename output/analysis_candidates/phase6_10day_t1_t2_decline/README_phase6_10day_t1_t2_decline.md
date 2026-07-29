# Phase 6 Independent T1/T2 Digital Phenotyping

T1 and T2 digital phenotype scores are estimated independently from their corresponding timepoint features. The T2 estimate is not calculated as T1 plus predicted change.

Digital change is calculated only after both independent estimates exist: estimated T2 minus estimated T1. Observed change is observed T2 minus observed T1.

The T2 models use fold-local median imputation, missingness indicators, standardization, and Ridge regularization with repeated 5-fold cross-validation.

## Pooled results

- Global / mean_baseline_T2: RMSE `8.164`, MAE `6.389`, R2 `-0.033`.
- Global / t1_primary_10pct_independent_t2_ridge: RMSE `8.195`, MAE `6.411`, R2 `-0.041`.
- Global / working_10pct_independent_t2_ridge: RMSE `8.204`, MAE `6.415`, R2 `-0.043`.
- Memory / mean_baseline_T2: RMSE `12.301`, MAE `10.175`, R2 `-0.029`.
- Memory / Memory_domain_independent_t2_ridge: RMSE `12.323`, MAE `10.196`, R2 `-0.033`.
- Executive function / mean_baseline_T2: RMSE `10.600`, MAE `8.247`, R2 `-0.034`.
- Executive function / Executive function_domain_independent_t2_ridge: RMSE `10.750`, MAE `8.398`, R2 `-0.064`.
- Processing speed / mean_baseline_T2: RMSE `15.714`, MAE `12.373`, R2 `-0.028`.
- Processing speed / Processing speed_domain_independent_t2_ridge: RMSE `15.919`, MAE `12.482`, R2 `-0.055`.
- Attention / mean_baseline_T2: RMSE `10.275`, MAE `7.908`, R2 `-0.022`.
- Attention / Attention_domain_independent_t2_ridge: RMSE `10.564`, MAE `8.075`, R2 `-0.080`.
- Motor / mean_baseline_T2: RMSE `8.724`, MAE `6.632`, R2 `-0.055`.
- Motor / Motor_domain_independent_t2_ridge: RMSE `9.189`, MAE `6.878`, R2 `-0.171`.
- Global / mean_change_baseline: RMSE `5.738`, MAE `4.269`, R2 `0.000`.
- Global / independent_digital_decline: RMSE `6.227`, MAE `4.668`, R2 `-0.178`.
- Memory / mean_change_baseline: RMSE `10.692`, MAE `7.894`, R2 `0.000`.
- Memory / independent_digital_decline: RMSE `10.968`, MAE `8.182`, R2 `-0.052`.
- Executive function / mean_change_baseline: RMSE `9.662`, MAE `7.545`, R2 `0.000`.
- Executive function / independent_digital_decline: RMSE `10.619`, MAE `8.467`, R2 `-0.208`.
- Processing speed / mean_change_baseline: RMSE `12.006`, MAE `8.106`, R2 `0.000`.
- Processing speed / independent_digital_decline: RMSE `13.707`, MAE `9.223`, R2 `-0.303`.
- Attention / mean_change_baseline: RMSE `7.794`, MAE `5.822`, R2 `0.000`.
- Attention / independent_digital_decline: RMSE `8.602`, MAE `6.589`, R2 `-0.218`.
- Motor / mean_change_baseline: RMSE `7.884`, MAE `5.757`, R2 `0.000`.
- Motor / independent_digital_decline: RMSE `8.275`, MAE `6.304`, R2 `-0.102`.
