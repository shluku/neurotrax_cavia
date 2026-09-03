# Phase 12 T1-to-T2 Change Midpoint Cohort

## Purpose

This exploratory phase applies the Phase 6 independent T1/T2 digital phenotyping workflow to the second half of the patient-level T1-to-T2 interval.

## Window rule

- Require valid T1 and T2 dates.
- Use the half-open interval `[midpoint, T2)`, where `midpoint = T1 + (T2 - T1) / 2`.
- The paired Phase 11 T1 first-half features and Phase 12 T2 second-half features are analyzed independently.
- All valid mapped devices are pooled for each patient and table, except patient `001`, which remains excluded from the active cohort.

## Active feature scope

The selected non-light Phase 2 features are used. Light, proximity, and accelerometer work remain outside this phase and will be addressed later.

## Interpretation boundary

The T1 and T2 estimates are independent feature-level estimates. Estimated digital change is calculated only after both estimates exist as `estimated T2 - estimated T1`; it is not a direct prediction from T1 to T2. This cohort is exploratory and is intended to compare coverage and model behavior against the earlier 10-day protocol.
