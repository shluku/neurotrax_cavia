# Phase 111 Full T1-to-T2 Interval Baseline Ridge

## Purpose

Phase 111 tests whether a single patient-level digital phenotype calculated from the full available interval between T1 and T2 can estimate a combined cognitive target better than a mean baseline.

## Cohort and interval

- Include patients with a valid T1 date, excluding patient `001` according to the project cohort rule.
- When T2 exists and is after T1, use the half-open interval `[T1, T2)`.
- When T2 is unavailable, use the fallback interval `[T1, T1+123 days)`.
- Pool all valid mapped devices for each active source table.
- The interval is deliberately broad and exploratory. It is not a strict baseline window and may include behavior measured throughout the T1-to-T2 period.

## Target definition

For Global cognitive and each domain (Memory, Executive function, Processing speed, Attention, and Motor):

- If both observed T1 and T2 scores exist, target = `(T1 + T2) / 2`.
- If T2 is unavailable, target = observed T1 score.
- The target source is recorded per patient.
- With exactly two observations, the standard median equals the arithmetic mean, so the first implementation uses the mean.

## First model

The first model is cross-validated Ridge using the current 54-feature active catalog. It is compared with the same fold-local mean baseline for every outcome. The workflow uses fold-local median imputation, missingness indicators, standardization, inner cross-validation for Ridge alpha selection, and repeated 5-fold outer cross-validation.

## Deferred sources

Light, barometer, Bluetooth-proximity, and sensor-linear-accelerometer features remain excluded. They are reserved for a later combined modality analysis.

## Interpretation boundary

This is a proof-of-concept exploratory phenotype. The target combines assessment-time scores rather than representing prospective T2 prediction or cognitive decline. Any improvement over the mean baseline must be evaluated for stability, coverage dependence, and external validation before clinical interpretation.
