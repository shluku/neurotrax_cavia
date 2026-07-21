# Accelerometer All-Patient Data Window Frame

Date: 2026-07-21

Purpose:

- Provide one working row per mapped T1 patient for accelerometer data-window planning.
- Use `sensor_accelerometer` metadata as the all-patient candidate-window layer.
- Overlay raw `accelerometer` validation where the top-10 pilot already tested raw data.
- Mark `007` and `013` as likely no usable raw accelerometer data based on the weekly-backward miss probe.

Inputs:

- `/Users/ofirfizitsky/PycharmProjects/research_dbeaver/output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_patient.csv`
- `/Users/ofirfizitsky/PycharmProjects/research_dbeaver/output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_device_window.csv`
- `/Users/ofirfizitsky/PycharmProjects/research_dbeaver/output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_top10_sensor_anchor_daily_jump_bounded_v3/accelerometer_top10_sensor_anchor_raw_probe_patient_windows.csv`
- `/Users/ofirfizitsky/PycharmProjects/research_dbeaver/output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_misses_weekly_backward_probe/accelerometer_misses_weekly_backward_probe.csv`

Rows:

- Patient rows: 81
- Device-window metadata rows available for drill-down: 159

Patient status counts:

- `likely_no_usable_raw_accelerometer`: 2
- `no_sensor_accelerometer_metadata_after_T1`: 4
- `raw_24h_window_validated`: 8
- `sensor_metadata_window_candidate_pending_raw_validation`: 67

Interpretation:

- `raw_24h_window_validated`: raw accelerometer rows were found and a candidate 24h raw window is recorded.
- `likely_no_usable_raw_accelerometer`: metadata exists, but targeted raw probes found no raw samples.
- `sensor_metadata_window_candidate_pending_raw_validation`: metadata suggests a candidate window, but raw data has not yet been checked.
- `no_sensor_accelerometer_metadata_after_T1`: no post-T1 metadata candidate exists in the current framework.
