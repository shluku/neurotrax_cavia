# Phase 4 10-Day Other Models

This is an isolated exploratory phase using all selected 10-day features and 81 patients. Every preprocessing step is fit within the training fold. Models are intentionally conservative: shallow trees, minimum leaf sizes, strong regularization, and repeated 5-fold validation. Held-out permutation importance is reported descriptively for the first repeated-CV pass only. No model replaces the primary Phase 4 result.

Mean-baseline RMSE: `8.5536`

mean_baseline RMSE: `8.5536`
elastic_net RMSE: `8.7006`
extra_trees RMSE: `8.8076`
spline_ridge RMSE: `8.8555`
random_forest RMSE: `8.9066`
xgboost RMSE: `8.9290`
hist_gradient_boosting RMSE: `9.1807`
pls RMSE: `9.5881`
