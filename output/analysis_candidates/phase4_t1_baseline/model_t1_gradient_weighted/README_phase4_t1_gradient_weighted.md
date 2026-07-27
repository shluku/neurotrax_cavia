# Phase 4 Gradient-Weighted T1 Ridge

This is a separate exploratory comparison to the primary 37-feature ridge model. Within each outer training fold, each feature receives a multiplier of `1 + abs(Spearman rho)` based only on that fold's training patients. The range is 1.0 to 2.0; missingness indicators are not weighted. The weighted model is still trained and evaluated with repeated 5-fold cross-validation and fold-local imputation/scaling.

Pooled mean-baseline RMSE: `8.532`

Pooled gradient-weighted ridge RMSE: `8.759`
