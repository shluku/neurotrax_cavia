# Phase 1 Reviewer Executive Summary

## Project purpose
Link NeuroTrax cognitive decline metrics with SensorDB digital phenotype signals in a constrained exploratory PoC.

## What was built
- Cognitive master and QC pipeline.
- Top10 decline subject selection and time-window alignment.
- Device-episode mapping (multiple device IDs per subject).
- SQL coverage and readiness mapping.
- Phase 1A extraction: screen + applications_foreground + aware_log.
- Phase 1B extraction: keyboard + touch + activity recognition.
- Merged Phase 1 digital phenotype table and descriptive interpretation outputs.

## What data was used
- Validated merged Phase 1 table and descriptive profile outputs only.
- No new SQL queries and no new extraction in this reviewer package step.

## What Phase 1 includes
- screen
- applications_foreground
- keyboard
- touch
- activity_recognition
- aware_log (data quality only)

## Main current results
- Baseline phenotype feasibility: 8/10 subjects.
- Change analysis feasibility: 2/10 subjects (024, 077).
- Merged Phase 1 table: 10 rows × 56 columns.

## Key methodological safeguards
- Missing data is not zero activity.
- no_data remains NaN.
- Privacy-sensitive keyboard text was not used.
- Subject_ID_D leading zeros preserved.
- No confirmatory statistics.

## Recommended next step
Continue interpreting current Phase 1 core phenotype before Phase 1C.