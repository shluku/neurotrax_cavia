# Pre-specified coverage-adjusted Motor and Attention inference

This separate sensitivity analysis tests whether the strongest Motor and Attention findings remain after reducing collection-intensity effects.

## Pre-specified workflow

1. Use the all-available Phase 11 T1 candidate feature catalog.
2. Divide volume-like features by each patient's observed timestamp-span exposure.
3. Residualize transformed observed feature values against observed timestamp span, total source rows, recorded table count, baseline feature missingness, baseline table coverage, and candidate-feature coverage. These technical variables never enter PCA or clustering directly.
4. Rank features separately for Motor T1 and Attention T1 using the same repeated 5-fold x20 Ridge coefficient procedure used in the domain-specific USML analysis. Restrict the final five features to real features in the fixed 41-feature USML panel.
5. Fit a separate PCA and fixed k=2 K-means solution for each adjusted five-feature panel.
6. Permute each cognitive outcome 100 times. For every permutation, repeat Ridge feature selection, select a new five-feature panel, refit PCA, refit k=2 K-means, and calculate the absolute cluster standardized difference. The calibrated p-value compares the observed effect with this selection-aware null distribution.
7. Bootstrap the observed adjusted five-feature panel 1,000 times to report variability intervals for the cluster effect and PCA correlations.

## Interpretation boundary

The permutation p-value is more honest than the original post-selection p-value because it repeats the outcome-informed selection process under a null outcome. It is still exploratory, limited by the small cohort and 100-permutation Monte Carlo resolution, and does not establish clinical validity. Bootstrap intervals are sampling-variability summaries, not independent validation intervals.

The original USML, domain-specific USML, and all earlier outputs are unchanged.
