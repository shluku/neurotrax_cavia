# Phase 6 T1-to-T2 Cognitive Decline Digital Phenotyping

Outcome: cognitive change defined as T2 score minus T1 score. Predictors are paired digital-feature changes, T2 feature minus T1 feature.

The active T2 feature set excludes light and uses features meeting the exploratory 10% T2 patient-coverage threshold. Missing predictors are handled inside each training fold with median imputation, missingness indicators, standardization, and Ridge alpha selection.

All model comparisons use the same fold-local mean baseline. Results are exploratory because feature eligibility was defined from the current T2 coverage audit and the paired cohort is small.

## Pooled results

