# Working Study Protocol

## 1. Research question

Can passive smartphone and sensor data be transformed into a transparent, patient-level digital phenotype that describes or estimates baseline cognitive performance in a small dementia cohort?

## 2. Study design

This is an exploratory observational proof-of-concept and methods/feasibility study. It is not a clinical validation study and does not claim that the current output is ready for clinical decision-making.

## 3. Objectives

### Primary objective

Develop and audit a reproducible pipeline that converts raw SensorDB tables into patient-level features aligned with cognitive assessment timepoints.

### Secondary objective

Describe feature coverage, missingness, observation-window effects, and the relationship between digital features and baseline cognitive scores.

### Exploratory objective

Compare transparent regularized models and feature-group models with a common mean baseline, while reporting weak or null performance as an informative result.

## 4. Current cohort and observation windows

The principal baseline analysis under consideration is the Phase 11 midpoint-span cohort. It uses available non-light data from T1 to a patient-specific midpoint between T1 and T2. Patients without a valid T2 use the documented 123-day fallback midpoint. The exact primary cohort and analysis cutoff must be frozen after supervisor review.

Other completed windows, including 24-hour, 10-day, Phase 12, and full-interval analyses, remain available as sensitivity or exploratory analyses. They should not all be presented as independent confirmatory tests.

Light, proximity, and accelerometer work is treated as an additional modality stream. Its role in the main manuscript must be decided after the feature review is complete.

## 5. Outcomes

- Primary candidate outcome: observed global cognitive T1 score.
- Secondary outcomes: available cognitive domains, including memory, executive function, processing speed, attention, and motor performance.
- Future outcome: T1-to-T2 cognitive change, if the longitudinal analysis is frozen and sufficiently complete.

## 6. Feature and data-quality rules

- Features are calculated at patient level from documented time windows.
- Missingness and coverage are retained as explicit audit outputs.
- Missing data are not silently interpreted as zero activity.
- Modeling imputation, when used, is performed within the training fold to avoid leakage.
- Feature selection based on the same cohort as model evaluation is labeled exploratory and potentially optimistic.

## 7. Modeling rules

- Every model is compared against the same fold-local mean baseline.
- Ridge or other regularized models are preferred because the cohort is small relative to the feature space.
- Performance is reported with RMSE, MAE, and R-squared, together with calibration or observed-versus-estimated plots where appropriate.
- A weak model is not described as a clinical digital phenotype score.
- No clinical threshold, diagnostic claim, or external validity claim is made without independent validation.

## 8. Reporting rules

The manuscript will report the complete analysis path, including coverage limitations, missingness, nominal findings that do not survive multiplicity correction, model results that do not outperform the baseline meaningfully, and analyses retained only for future work.

## 9. Decisions required before manuscript freeze

1. Confirm the primary cohort and observation window.
2. Confirm whether global T1 is the sole primary outcome.
3. Decide which domain analyses belong in the main paper and which belong in the supplement.
4. Decide whether supplemental modalities are included in the initial manuscript.
5. Freeze the primary feature catalog and model comparison.
6. Confirm the intended target journal and reporting checklist.
