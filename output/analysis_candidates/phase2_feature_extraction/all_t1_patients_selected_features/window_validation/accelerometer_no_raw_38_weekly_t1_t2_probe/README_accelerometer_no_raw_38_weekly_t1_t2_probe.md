# Accelerometer 38 No-Raw Weekly T1-T2 Probe

Date: 2026-07-21

Purpose:

- Re-check patients that had `sensor_accelerometer` metadata but no raw rows in the selected metadata week.
- Probe raw `accelerometer` across each patient's broader T1-to-T2 study span.
- Use short bounded probes aligned to the metadata time-of-day, jumping backward weekly from near T2.
- If a patient has no T2 date, use the cohort's latest available T2 end timestamp as a fallback upper bound.

Outputs:

- Patient validation table: `/Users/ofirfizitsky/PycharmProjects/research_dbeaver/output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_no_raw_38_weekly_t1_t2_probe/accelerometer_no_raw_38_weekly_t1_t2_patient_windows.csv`
- Probe detail table: `/Users/ofirfizitsky/PycharmProjects/research_dbeaver/output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_no_raw_38_weekly_t1_t2_probe/accelerometer_no_raw_38_weekly_t1_t2_probes.csv`

Patient rows: 38
Probe rows: 1510

Raw validation status counts:

- `missing_no_raw_rows_in_weekly_t1_t2_probes`: 32
- `raw_window_found_from_weekly_t1_t2_probe`: 6

Interpretation:

- `raw_window_found_from_weekly_t1_t2_probe`: raw accelerometer rows were found in a weekly T1-to-T2 probe.
- `missing_no_raw_rows_in_weekly_t1_t2_probes`: no raw rows were found in the weekly T1-to-T2 probe series.
- This is still a bounded probe strategy, not a continuous full raw-table scan.
