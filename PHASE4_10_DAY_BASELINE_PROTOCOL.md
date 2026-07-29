# Phase 4 10-Day T1 Baseline Digital Phenotype

This phase is an isolated equivalent of Phase 4 using the Phase 7 availability-anchored 10-day T1 feature table.

- T1 window: first available timestamp after T1, followed by 10 days of data.
- Tables: the same selected tables and feature functions as the original Phase 4, excluding `light`.
- Patients: the full T1 cohort represented in the Phase 7 T1 wide file.
- Models: the original Phase 4 Ridge, calibration, alternative, gradient-weighted, slope-selected, direction-constrained, cognitive-domain, domain-group, and clustering analyses.

The original 24-hour Phase 4 outputs are not overwritten. This remains an exploratory POC analysis; the wider window may improve feature coverage but may also incorporate more temporal behavior variation.

## All-feature direction-constrained experiment

An exploratory model was added after the standard Phase 4 10-day comparisons. It uses every selected feature with usable fold-local variation. The sign of each feature coefficient is constrained by that feature's fold-local linear slope against observed T1: positive slopes receive nonnegative coefficients and negative slopes receive nonpositive coefficients. The signs and preprocessing are learned inside each repeated cross-validation training fold.

Using 81 patients and the same repeated 5-fold validation design as the other models, the pooled RMSE was `8.8995`, compared with `8.5320` for the mean baseline. This did not improve prediction in the current 10-day cohort and should remain labeled exploratory.
