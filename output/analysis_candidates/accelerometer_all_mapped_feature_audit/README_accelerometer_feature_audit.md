# Accelerometer Feature Audit and Patient-Level Aggregation

This is a SQL-free audit of the saved plugin-anchored general-accelerometer pilot. It does not overwrite the raw ACC pilot outputs or any existing patient-level cohort.

## Current scope

- Pilot patients: `59`.
- Candidate device-days: `7374`.
- Completed patient-local days: `7`.
- Completed device-day feature rows: `7`.
- Feature definitions audited: `24`.
- Patient-level aggregation: median across completed patient-local days.

The patient-level table is a model-ready shape, but it is not yet suitable for model fitting because the current pilot contains only two patients and incomplete extraction coverage.

## Feature roles

- `12` primary behavioral candidates: dynamic motion, temporal pattern, circadian pattern, and rapid signal-change features.
- `3` sensitivity-only signal-level features: vector magnitude summaries can be affected by gravity, phone orientation, and placement.
- `9` QC-only features: raw/valid counts, coverage, duration, sampling intervals, gap burden, and duplicate counts. These describe collection quality and are excluded from the primary behavioral panel.

Count and minute features also receive per-observed-hour versions. These are intended to reduce recording-intensity effects, but their usefulness must be checked on the larger cohort.

## Technical-confounding audit

Each feature is compared with raw row count, valid signal minutes, calendar coverage, and observed span. Correlations are descriptive only. A large absolute Spearman correlation is marked `review`; it does not prove confounding. No p-values are reported from this two-patient pilot.

## Model handoff protocol

After extraction is available for the intended patient cohort, repeat the audit and then compare the following on exactly the same patients and validation folds:

1. Fold-local mean baseline.
2. Existing digital phenotype model.
3. ACC behavioral candidates alone.
4. Existing features plus ACC behavioral candidates.
5. Coverage-normalized sensitivity model.

Median imputation, missingness indicators, scaling, feature selection, and Ridge alpha selection must be fit inside each training fold. The two-patient pilot must not be used to choose final features or to claim predictive evidence.
