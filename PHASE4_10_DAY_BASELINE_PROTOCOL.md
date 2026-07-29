# Phase 4 10-Day T1 Baseline Digital Phenotype

This phase is an isolated equivalent of Phase 4 using the Phase 7 availability-anchored 10-day T1 feature table.

- T1 window: first available timestamp after T1, followed by 10 days of data.
- Tables: the same selected tables and feature functions as the original Phase 4, excluding `light`.
- Patients: the full T1 cohort represented in the Phase 7 T1 wide file.
- Models: the original Phase 4 Ridge, calibration, alternative, gradient-weighted, slope-selected, direction-constrained, cognitive-domain, domain-group, and clustering analyses.

The original 24-hour Phase 4 outputs are not overwritten. This remains an exploratory POC analysis; the wider window may improve feature coverage but may also incorporate more temporal behavior variation.
