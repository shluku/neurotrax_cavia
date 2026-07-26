# Phase 4: T1 Baseline Digital Phenotype

## Purpose

Phase 4 moves from table-level feature finding to a patient-level baseline digital phenotype dataset. It is the first analysis layer for Outcome 1:

> Build T1 baseline digital phenotype features using an exploratory first-valid 24-hour T1-week protocol, then apply the finalized features to patient-level baseline analyses.

This remains a proof of concept. The output is intended for transparent exploration, feature stability checks, and hypothesis generation. It is not a validated clinical biomarker or a confirmatory prediction model.

## Acquisition Rule

The preferred baseline window is a 24-hour period beginning on the local calendar day after NeuroTrax T1. If that window is unavailable, the extractor may use the first observed timestamp that supports a complete 24-hour period within the patient's first T1 week.

The following acquisition labels must remain visible:

- `exploratory_primary_day_after_T1`: strict preferred window.
- `exploratory_fallback_first_24h_span_within_T1_week`: first usable 24-hour period within the T1 week.
- `adjusted_first_available_7d_after_T1`: delayed first-available window used for selected tables that did not have a valid strict T1-week window.
- missing status: no protocol-valid window or insufficient signal.

"As soon as data gets available" is acceptable for this exploratory phase only when the selected timestamp, delay from T1, window boundaries, table, device IDs, row counts, and window rule are retained in the audit outputs.

## Patient-Level Dataset

The Phase 4 builder starts from the existing all-T1 extraction and creates:

- one patient row per mapped T1 patient;
- cognitive T1/T2 variables and demographics;
- selected aggregate SensorDB features;
- feature-level missingness indicators;
- patient-level table and feature coverage summaries;
- protocol and source metadata for auditability.

The raw extracted values are preserved. Phase 4 does not overwrite missing values with zero or a population statistic.

## Missingness and Coverage Policy

Missingness is part of the phenotype measurement process. It can reflect device availability, app logging, window timing, sensor coverage, or insufficient signal. It must not be interpreted as no activity.

Primary dataset rules:

1. Preserve feature values as observed or missing.
2. Add feature-level missing indicators for analysis.
3. Report table-level and patient-level coverage separately from behavior features.
4. Keep strict T1-week features separate from adjusted first-available features.
5. Do not use an all-patient complete-case filter as the default; it would discard too much information and can introduce selection bias.

## Modeling Imputation Policy

For descriptive tables and phenotype profiles, do not impute the primary values.

For a first exploratory regression model, median imputation is acceptable as a baseline preprocessing method, but only under these rules:

- fit the median using the training fold only;
- apply that training median to the validation fold;
- add a missingness indicator for every imputed feature;
- never calculate medians using the full dataset before cross-validation;
- compare against a simple mean-only model and a complete-case or high-coverage sensitivity analysis;
- report how many values were imputed and whether model performance changes materially.

This prevents validation leakage and lets the model distinguish an imputed value from a genuinely observed value.

## First Modeling Target

The primary exploratory target is continuous `global_T1`. The first model comparison should be:

1. mean-only baseline;
2. ridge regression with standardized features and fold-fitted median imputation plus missingness indicators;
3. elastic net as a secondary stability analysis.

Random forest and boosting models are deferred because the effective sample size is small relative to the number of correlated features and because acquisition artifacts may dominate unstable nonlinear models.

## Feature Inclusion Policy

The initial baseline model should use only features from strict or fallback T1-week 24-hour windows. Features from adjusted first-available 7-day windows are retained in the Phase 4 dataset but excluded from the primary model and used only in a labeled sensitivity analysis.

For the first POC model, a provisional coverage screen also applies: a T1-week feature must be observed in at least 50% of the 81-patient baseline cohort to enter the primary feature pool. Features below that threshold remain available as `coverage_sensitivity` variables. Features with no observed values are excluded from modeling but remain in the audit files.

Hardware metadata and table-availability fields are coverage/context variables. They should not be presented as direct behavior without a separate justification.

## Required Outputs

- `phase4_t1_baseline_patient_dataset.csv`: raw patient-level values plus protocol and coverage summaries.
- `phase4_t1_baseline_feature_metadata.csv`: feature source, family, window class, and inclusion recommendation.
- `phase4_t1_baseline_missingness_summary.csv`: observed/missing counts and percentages.
- `phase4_t1_baseline_table_coverage.csv`: patient-table status and window coverage summary.
- `README_phase4_t1_baseline_dataset.md`: generated run summary.

## Current Limitation

The current dataset is a cohort-level exploratory extraction, not yet a locked final biomarker panel. Feature definitions, coverage thresholds, and the model inclusion list must be reviewed before any performance estimate is treated as meaningful.
