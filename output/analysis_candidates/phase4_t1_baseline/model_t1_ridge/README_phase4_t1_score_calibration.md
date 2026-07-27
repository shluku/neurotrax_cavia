# Phase 4 T1 Score Calibration and Interpretation

This report summarizes patient-level repeated cross-validated ridge predictions for continuous `global_T1`.

## Calibration

Calibration checks whether predicted scores track actual scores on the correct scale. For the primary ridge model: RMSE `8.796`, MAE `6.994`, calibration slope `-0.548`, intercept `151.683`, and actual-predicted correlation `-0.095`.

The Streamlit page displays actual-versus-predicted points and prediction bins. The diagonal reference means perfect agreement.

## Interpretation

`phase4_t1_ridge_coefficient_summary.csv` summarizes coefficient direction and stability across outer folds. Coefficients are exploratory associations, not causal or clinical effects. Terms with unstable signs should not be treated as reliable findings.

Missingness indicators are included in the coefficient output and must be distinguished from behavior features.

## Boundary

The digital window is generally after T1. This is a T1-anchored digital estimate of an already observed T1 score, not prospective prediction of a future assessment. It is exploratory and not for clinical use.
