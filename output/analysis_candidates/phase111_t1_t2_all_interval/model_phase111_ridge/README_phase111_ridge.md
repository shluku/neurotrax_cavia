# Phase 111 Full-Interval Ridge

Features are calculated from all available active-feature data in `[T1, T2)`, or `[T1, T1+123 days)` when T2 is unavailable.

For each outcome, the target is the mean of observed T1 and T2 scores when both exist, or observed T1 alone without T2. A domain without a valid T1 score is excluded from that domain model. With two observations, the standard median is identical to this mean.

Ridge uses fold-local median imputation, missingness indicators, standardization, inner-CV alpha selection, and repeated 5-fold cross-validation. Every Ridge result is compared against the same fold-local mean baseline.

## Pooled results

- Global / mean_baseline: RMSE `8.294`, MAE `6.585`, R2 `-0.025`.
- Global / ridge: RMSE `8.442`, MAE `6.667`, R2 `-0.062`.
- Memory / mean_baseline: RMSE `12.546`, MAE `10.146`, R2 `-0.024`.
- Memory / ridge: RMSE `12.827`, MAE `10.351`, R2 `-0.070`.
- Executive function / mean_baseline: RMSE `10.876`, MAE `8.557`, R2 `-0.030`.
- Executive function / ridge: RMSE `11.027`, MAE `8.774`, R2 `-0.059`.
- Processing speed / mean_baseline: RMSE `13.589`, MAE `10.804`, R2 `-0.031`.
- Processing speed / ridge: RMSE `13.721`, MAE `11.014`, R2 `-0.051`.
- Attention / mean_baseline: RMSE `11.394`, MAE `8.800`, R2 `-0.031`.
- Attention / ridge: RMSE `11.870`, MAE `9.088`, R2 `-0.119`.
- Motor / mean_baseline: RMSE `9.874`, MAE `8.206`, R2 `-0.029`.
- Motor / ridge: RMSE `10.045`, MAE `8.215`, R2 `-0.065`.
