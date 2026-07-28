# Phase 6: T1-to-T2 Decline Digital Phenotyping

## Outcome

Predict cognitive change for each paired patient as:

`T2 cognitive score - T1 cognitive score`

This is an exploratory POC outcome. It is not a clinical decline classifier or validated prediction tool.

## Digital Predictors

For each eligible feature, calculate the paired change:

`T2 feature - T1 feature`

The active T2 set excludes the unreliable `light` table and uses the Phase 5 10% patient-coverage rule. Fold-local median imputation, missingness indicators, standardization, and Ridge regularization are used inside cross-validation.

## Models

All models are compared against the same fold-local mean outcome baseline:

1. T1-primary features meeting 10% T2 coverage.
2. All working features meeting 10% T2 coverage.
3. Cognitive-domain feature-group models using the union of relevant Phase 4 group features that survive the T2 coverage rule.

## Graph Order

The Streamlit Phase 6 page follows the Phase 4 presentation order:

1. Global decline: working-feature digital estimate.
2. Global decline: T1-primary-feature digital estimate.
3. Model-fit comparison against the mean baseline.
4. Memory decline feature-group model.
5. Executive-function decline feature-group model.
6. Processing-speed decline feature-group model.
7. Attention decline feature-group model.
8. Motor decline feature-group model.

Patients are ordered from the lowest to highest observed change. Patient IDs are shown in the hover details. Each graph is based on out-of-fold predictions.

## Interpretation Boundary

The paired cohort is small and feature missingness is high. A model that does not beat the mean baseline is still a valid negative POC result. No imputation method can restore information that was never observed.
