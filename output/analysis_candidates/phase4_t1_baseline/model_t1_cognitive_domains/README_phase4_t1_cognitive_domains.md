# Phase 4 T1 Cognitive Domain Models

Each domain is modeled separately using the same 37 primary features, repeated 5-fold cross-validation repeated 20 times, and fold-local median imputation, missingness indicators, standardization, and inner-CV Ridge alpha selection.

## Pooled results

- Memory / mean_baseline: RMSE `13.768`, MAE `10.992`, R2 `0.000`.
- Memory / ridge: RMSE `13.869`, MAE `11.065`, R2 `-0.014`.
- Executive function / mean_baseline: RMSE `11.420`, MAE `9.230`, R2 `-0.002`.
- Executive function / ridge: RMSE `11.585`, MAE `9.370`, R2 `-0.031`.
- Processing speed / mean_baseline: RMSE `13.536`, MAE `11.106`, R2 `-0.001`.
- Processing speed / ridge: RMSE `14.519`, MAE `11.798`, R2 `-0.151`.
- Attention / mean_baseline: RMSE `12.026`, MAE `9.575`, R2 `-0.001`.
- Attention / ridge: RMSE `12.154`, MAE `9.703`, R2 `-0.022`.
- Motor / mean_baseline: RMSE `10.505`, MAE `8.771`, R2 `-0.004`.
- Motor / ridge: RMSE `11.405`, MAE `9.427`, R2 `-0.183`.
