# Phase 4 Slope-Selected T1 Ridge

This is a separate exploratory model using only eight features selected inside each outer training fold: the five highest positive linear slopes and three lowest negative linear slopes. Slope is fitted to the four feature-quantile median T1 values. The model uses fold-local median imputation, missingness indicators, standardization, and inner-CV ridge alpha selection.

Pooled mean-baseline RMSE: `8.532`

Pooled slope-selected ridge RMSE: `8.995`
