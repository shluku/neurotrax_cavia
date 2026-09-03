# Phase 11/12 Deferred Modalities

The active midpoint phenotype models intentionally exclude these feature sources:

- `light`
- `barometer`
- `bluetooth` as the proximity-context source
- `sensor_linear_accelerometer`

They are deferred as a combined follow-up analysis. The reason is to keep the current Phase 11 T1 baseline and Phase 12 T1-to-T2 change results focused on the established behavioral and device-use features while preserving the other modalities for a controlled later comparison.

## Current barometer status

Barometer extraction was attempted during the midpoint cohort build. Patient `045` repeatedly encountered a database connection failure while querying the barometer interval. The retry was stopped intentionally. Patient `045` remains in the Phase 12 paired wide cohort with missing active feature values, while the unfinished barometer work is treated as deferred rather than as a true no-data finding.

No further barometer extraction is scheduled in the current phase. Barometer will be revisited together with light, accelerometer, and proximity in a later phase.

## Modeling rule

The raw midpoint extraction outputs may contain deferred modality columns for audit and future reuse. Phase 11 and Phase 12 model runners exclude the four deferred source tables from their active feature metadata, datasets, and model inputs.
