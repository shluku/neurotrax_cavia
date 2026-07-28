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

1. Global observed T1 score in the original 81-patient order.
2. Global observed T1, observed T2, and working-feature estimated T2 scores in that same order.
3. Global observed change versus working-feature estimated change.
4. Memory: T1 score, aligned T1/T2/estimated-T2 scores, then observed versus estimated change.
5. Executive function: T1 score, aligned T1/T2/estimated-T2 scores, then observed versus estimated change.
6. Processing speed: T1 score, aligned T1/T2/estimated-T2 scores, then observed versus estimated change.
7. Attention: T1 score, aligned T1/T2/estimated-T2 scores, then observed versus estimated change.
8. Motor: T1 score, aligned T1/T2/estimated-T2 scores, then observed versus estimated change.

Patients are ordered once from lowest to highest observed T1 score using the original 81-patient T1 baseline cohort. The same x-axis order is reused for T2 and predicted T2 values; patients without paired T2 data remain blank at their original positions. Patient IDs are shown in the hover details. Each estimate is based on out-of-fold predictions and is displayed on the score scale as `T1 score + predicted change`.

Graph colors follow Phase 4: black for observed T1, red for observed T2, blue for the general digital estimate, and the established domain color for the domain-group estimate.

## Interpretation Boundary

The paired cohort is small and feature missingness is high. A model that does not beat the mean baseline is still a valid negative POC result. No imputation method can restore information that was never observed.
