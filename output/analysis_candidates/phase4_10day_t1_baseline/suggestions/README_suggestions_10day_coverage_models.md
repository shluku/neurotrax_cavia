# Suggestions: coverage-ranked 10-day T1 baseline models

This isolated exploratory phase ranks patients only by feature coverage, then runs the same seven alternative model families on the top 30, top 20, and top 10 patients. The top 30 cohort is the main exploratory result; top 20 is sensitivity analysis; top 10 is descriptive only because validation variance is very high at that sample size. Every cohort has its own mean baseline.

Coverage ranking uses lower baseline feature missingness, higher table coverage as a tie-breaker, and patient ID as a final deterministic tie-breaker. T1 scores are never used for cohort selection.

Top 10 elastic_net RMSE: `9.1575`
Top 10 extra_trees RMSE: `9.5869`
Top 10 mean_baseline RMSE: `9.5869`
Top 10 hist_gradient_boosting RMSE: `9.5869`
Top 10 xgboost RMSE: `9.5869`
Top 10 random_forest RMSE: `9.5870`
Top 10 spline_ridge RMSE: `10.0853`
Top 10 pls RMSE: `12.4032`
Top 20 mean_baseline RMSE: `7.5307`
Top 20 xgboost RMSE: `7.5319`
Top 20 random_forest RMSE: `7.5429`
Top 20 extra_trees RMSE: `7.6035`
Top 20 hist_gradient_boosting RMSE: `7.6784`
Top 20 spline_ridge RMSE: `7.8096`
Top 20 elastic_net RMSE: `8.9234`
Top 20 pls RMSE: `10.3321`
Top 30 mean_baseline RMSE: `7.4418`
Top 30 extra_trees RMSE: `7.7248`
Top 30 xgboost RMSE: `7.8256`
Top 30 random_forest RMSE: `7.8940`
Top 30 elastic_net RMSE: `7.9247`
Top 30 spline_ridge RMSE: `7.9297`
Top 30 hist_gradient_boosting RMSE: `8.0390`
Top 30 pls RMSE: `9.7080`
