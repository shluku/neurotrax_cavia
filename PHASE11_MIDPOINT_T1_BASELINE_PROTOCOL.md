# Phase 11 T1 Baseline Midpoint Cohort

## Purpose

This exploratory phase applies the Phase 4 T1 baseline feature algorithms to more of the available sensor data while keeping the patient-level analysis auditable.

## Window rule

- For patients with valid T1 and T2 dates, use the half-open interval `[T1, midpoint)`, where `midpoint = T1 + (T2 - T1) / 2`.
- For patients with T1 but no valid T2 date, use the documented fallback midpoint `T1 + 123 days`.
- The exact midpoint/fallback source and actual interval duration are recorded in the status and long feature CSVs.
- All valid mapped devices are pooled for each patient and table, except patient `001`, which remains excluded from the active cohort.

## Active feature scope

The selected non-light Phase 2 features are used. Light, proximity, and accelerometer work remain outside this phase and will be addressed later.

## Interpretation boundary

This is not a strict 24-hour baseline. The first-half interval may contain behavior after the T1 assessment and is therefore an exploratory midpoint-based T1 phenotype cohort. The Phase 4 model families, cross-validation, imputation, and graph presentation are reused for comparability only.
