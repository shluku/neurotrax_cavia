# Pre-specified coverage-adjusted Motor and Attention inference

## Question

Do the apparent Motor and Attention relationships remain after reducing differences in recording exposure, source-row intensity, feature coverage, and baseline table coverage?

## Fixed analysis plan

- Outcomes: Motor T1 and Attention T1 only.
- Candidate features: all observed T1-week and adjusted-window features in the Phase 11 median-timespan cohort.
- Final feature restriction: five real features per outcome from the fixed 41-feature USML panel; missingness-indicator terms are excluded.
- Feature adjustment: volume-like features are divided by observed timestamp-span days. Transformed observed feature values are then residualized against observed timestamp span, total source rows, recorded table count, baseline feature missingness, baseline table coverage, and overall candidate-feature coverage.
- Ridge ranking: repeated 5-fold cross-validation repeated 20 times, with fold-local median imputation, missingness indicators, standardization, and inner-CV alpha selection. Features are ranked by absolute mean coefficient.
- PCA: a separate PCA is fit for Motor and Attention using their adjusted top-five panels. Patients require at least 50% of the five values to be observed.
- Clustering: fixed k=2 K-means with the existing stability audit. Cognitive scores are not PCA or clustering inputs after the Ridge-informed selection step.

## Selection-aware permutation test

Each outcome is permuted 100 times. For every permutation, the analysis repeats the Ridge feature ranking, selects a new top-five panel, refits PCA, refits fixed k=2 K-means, and calculates the absolute standardized difference in the permuted outcome between clusters. The calibrated p-value is:

`(1 + number of permuted effects at least as large as the observed effect) / (1 + number of permutations)`

This accounts for the fact that the original feature panel was selected using the cognitive outcome. The p-value is still exploratory and has limited resolution because only 100 permutations are used.

## Bootstrap assessment

The observed adjusted five-feature panel is resampled with replacement 1,000 times. PCA and fixed k=2 clustering are refit in each resample. The resulting 95% percentile intervals describe sampling variability conditional on the selected adjusted panel. They are not independent validation intervals and do not replace the permutation test.

## Interpretation boundary

The original Motor and Attention findings are considered more credible only if the adjusted effect remains non-trivial, the selection-aware permutation p-value remains small, the bootstrap interval is reasonably away from zero, and technical variables no longer strongly separate the clusters. Any remaining result is exploratory and requires confirmation in a larger, independently collected cohort.
