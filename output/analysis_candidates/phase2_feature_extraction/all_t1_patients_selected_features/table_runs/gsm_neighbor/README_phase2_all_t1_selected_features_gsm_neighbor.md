# Phase 2 All-T1 Selected Feature Extraction

This folder contains the first bounded cohort-level extraction of the currently selected Phase 2 SensorDB features.

## Scope

- Patients: all NeuroTrax candidates with a T1 date in `output/analysis_candidates/cognitive_candidates_all.csv`.
- Tables: gsm_neighbor.
- Selected features: the manually selected features in `phase2_selected_features.csv`.
- Window rule: exploratory T1-week 24-hour protocol.

## Window Rule

For each patient, table, and mapped device:

1. Try the local 24-hour window starting on the day after T1.
2. If no rows exist there, search for the first timestamp that can support a complete 24-hour span inside the first week after T1.
3. If no complete span exists in that week, mark the table/features as missing for that patient.

Missing data remains missing. It is not converted to zero activity.

## Outputs

- `phase2_all_t1_selected_features_long.csv`: one row per patient-table-feature.
- `phase2_all_t1_selected_features_wide.csv`: one row per patient with selected features as columns.
- `phase2_all_t1_selected_features_coverage.csv`: bounded coverage checks used to choose windows.
- `phase2_all_t1_selected_features_patient_table_status.csv`: one row per patient-table with window and row-count status.

## Interpretation

These are exploratory digital biomarker candidates, not diagnostic features and not confirmatory findings. Raw privacy-sensitive content is not saved; keyboard/message/location calculations output aggregate values only.

## Run Summary Placeholder

This README was generated for 81 T1 patients. See the CSV outputs for actual coverage and feature availability.
