# Pending Accelerometer Raw Window Validation

Date: 2026-07-21

Purpose:

- Validate the 67 pending `sensor_accelerometer` metadata windows against raw `accelerometer`.
- Use bounded 20-minute raw probes, repeated once per day across each metadata week.
- Record a candidate 24-hour raw window only when raw rows are found.

Outputs:

- Patient validation table: `output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_pending_raw_validation_smoke/accelerometer_pending_raw_validation_patient_windows.csv`
- Probe detail table: `output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_pending_raw_validation_smoke/accelerometer_pending_raw_validation_probes.csv`

Patient rows: 3
Probe rows: 14

Raw validation status counts:

- `raw_window_found_from_pending_metadata_probe`: 2
- `missing_no_raw_rows_in_bounded_daily_probes`: 1

Interpretation:

- `raw_window_found_from_pending_metadata_probe`: raw accelerometer rows were found; the row has a validated candidate 24h raw window.
- `missing_no_raw_rows_in_bounded_daily_probes`: no raw rows were found in daily bounded probes across the metadata window.
- Exact 24h raw row counts are deferred to extraction.
