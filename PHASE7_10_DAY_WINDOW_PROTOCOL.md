# Phase 7: 10-Day Availability-Anchored Window

## Purpose

Repeat the selected-feature extraction with more observations per patient while preserving the Phase 2 feature definitions and excluding the unreliable `light` table.

## Window Rules

The window is selected separately for every patient, table, and mapped device:

- **T1:** search after the T1 assessment, find the first available timestamp, and include the entire following 10 days.
- **T2:** search the available pre-T2 period, find the latest available timestamp before T2, and include the preceding 10 days.

The T2 anchor search extends back up to 30 days when necessary. The 10-day interval is anchored to actual sensor availability rather than to a fixed calendar interval. The selected device, anchor timestamp, window boundaries, row count, and status are recorded for every patient-table attempt.

All existing table-specific fetchers and feature calculators are reused. The `light` table remains outside the active run because its high-volume query previously caused repeated database disconnects.

## Outputs

T1 and T2 outputs are isolated under:

`output/analysis_candidates/phase7_10day_window/t1/`

`output/analysis_candidates/phase7_10day_window/t2/`

Rows are appended after each patient completes. Checkpoints allow the job to resume without overwriting completed patient results.

## Next Analysis

After both endpoints finish, rebuild feature-level coverage audits and rerun the independent T1/T2 models:

`estimated T1` from 10-day T1 features

`estimated T2` from 10-day T2 features

`digital change = estimated T2 - estimated T1`

This phase is exploratory. Wider windows can improve coverage and reduce noise, but they can also increase exposure to time drift, behavior changes, and computational load. These effects will be reported alongside the model results.
