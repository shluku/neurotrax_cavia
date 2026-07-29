# Phase 4 T1 Cognitive Domain Models

Each domain is modeled separately using the same 37 primary features, repeated 5-fold cross-validation repeated 20 times, and fold-local median imputation, missingness indicators, standardization, and inner-CV Ridge alpha selection.

## Pooled results

- Memory / mean_baseline: RMSE `13.768`, MAE `10.992`, R2 `0.000`.
- Memory / ridge: RMSE `13.892`, MAE `11.065`, R2 `-0.018`.
- Executive function / mean_baseline: RMSE `11.420`, MAE `9.230`, R2 `-0.002`.
- Executive function / ridge: RMSE `11.598`, MAE `9.351`, R2 `-0.034`.
- Processing speed / mean_baseline: RMSE `13.536`, MAE `11.106`, R2 `-0.001`.
- Processing speed / ridge: RMSE `16.149`, MAE `12.977`, R2 `-0.424`.
- Attention / mean_baseline: RMSE `12.026`, MAE `9.575`, R2 `-0.001`.
- Attention / ridge: RMSE `12.352`, MAE `9.934`, R2 `-0.056`.
- Motor / mean_baseline: RMSE `10.505`, MAE `8.771`, R2 `-0.004`.
- Motor / ridge: RMSE `11.073`, MAE `9.122`, R2 `-0.115`.
