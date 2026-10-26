# Remaining Top-15 Coverage-Adjustment Report — 2026-10-26

This report covers the nine top-15 rows outside the six prespecified longitudinal validation signals. It uses reconstructed patient-level files and saved keyboard-window coverage fields. No new database query or broad feature search was used.

## Methods

Partial Spearman correlations were calculated by rank-residualizing the feature and cognitive outcome on prespecified covariates. Baseline rows used age, sex, education, and a recording-density sensitivity using T1 snapshots per active day and valid intervals per active day. Longitudinal rows used age, sex, education, baseline cognitive score, and changes in snapshot-rate and valid-interval-rate. Device change was unavailable in the reconstructed restricted and legacy tables and was not imputed. Confidence intervals use 500 patient bootstrap resamples. FDR values are BH values within this new nine-row adjustment family and are not comparable with the original discovery q-values.

## Findings

- The baseline word-completion associations remained similar after recording adjustment: Global rho changed from -.411 to -.410 (p=.00168), Attention from -.405 to -.381 (p=.00372), and Executive Function from -.385 to -.355 (p=.00728). The legacy trimmed Attention and Global rows remained negative after adjustment (rho=-.378 and -.397, respectively).
- The baseline morning IEI-IQR/Executive Function association was essentially unchanged (rho=-.343 to -.343; p=.00836).
- The restricted morning IEI/Attention association attenuated from the unadjusted restricted estimate to partial rho=.644 (p=.0238, n=18) after baseline and recording-rate adjustment. Its bootstrap interval crossed zero ([-.240, .971]).
- The restricted correction-recovery/Attention association remained negative after adjustment (partial rho=-.608, p=.0358, n=18), but its bootstrap interval also crossed zero ([-.957, .096]).
- Keyboard active-days change/Executive Function remained negative after adjustment (partial rho=-.402, p=.0305, n=35), but this feature is itself a recording-volume measure and should not be interpreted as a behavioral timing signal.

## Interpretation

Recording density does not explain away the baseline word-completion or morning IEI-IQR associations in these saved cohorts, but these analyses are still exploratory and do not establish clinical meaning. The restricted-window results are sensitive to small n and have wide bootstrap intervals. The new q-values describe only this focused nine-row adjustment family. These results do not provide independent validation and should be reported as sensitivity analyses alongside the original estimates.

The complete numeric output is `top15_remaining_coverage_adjusted_v1.csv`. The saved-data join audit is `top15_covariate_join_audit_v1.csv`.
