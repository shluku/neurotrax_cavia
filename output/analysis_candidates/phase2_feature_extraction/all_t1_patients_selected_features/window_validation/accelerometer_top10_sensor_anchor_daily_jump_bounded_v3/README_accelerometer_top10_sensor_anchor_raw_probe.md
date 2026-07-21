# Accelerometer Top-10 Sensor-Anchor Raw Probe Pilot

Date: 2026-07-21

Purpose:

- Validate candidate raw `accelerometer` 24-hour windows for the top 10 T1-score patients.
- Use lightweight `sensor_accelerometer` metadata as the candidate-window generator.
- Probe raw `accelerometer` only in short bounded windows around metadata timestamps.
- Avoid full raw-table discovery scans and avoid exact 24-hour row counts in this phase.

Output:

- Patient-level table: `output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_top10_sensor_anchor_daily_jump_bounded_v3/accelerometer_top10_sensor_anchor_raw_probe_patient_windows.csv`
- Metadata candidate probe table: `accelerometer_top10_sensor_anchor_raw_probe_candidates.csv`
- Hourly raw existence detail: `accelerometer_top10_sensor_anchor_raw_probe_hourly.csv`

Rows:

- Patient rows: 10
- Metadata candidates probed: 17
- Hourly probe rows: 0

Patient window status counts:

- `raw_window_found_from_sensor_anchor_probe`: 8
- `missing_no_raw_rows_near_checked_sensor_accelerometer_anchors`: 2

Window rule:

- Rank patients by descending `global_T1`.
- For each patient, read post-T1 `sensor_accelerometer` metadata candidates from `sensor_accelerometer_qc_by_device_window.csv`.
- Prefer the patient-level selected device first, then other patient devices by earliest metadata availability.
- For each metadata anchor, run a raw `accelerometer` probe from 5 minutes before to 15 minutes after the metadata timestamp.
- If raw rows are found, start the candidate 24-hour window at the first raw row in that short probe.
- If the short probe misses for every checked candidate, jump the same bounded probe forward in 24-hour steps; if a jump hits, use the first raw timestamp as the candidate 24-hour window start.
    - By default, record the candidate 24-hour start/end timestamps and defer deeper hourly coverage checks.
    - Optional hourly probes can be enabled later for selected candidate windows.

Important interpretation:

- `raw_probe_sampled_rows_20min` is a bounded sample count, not an exact count.
- `raw_probe_hit_sample_limit=True` means at least `raw_probe_sample_limit` rows exist in the 20-minute probe window.
- `daily_jump_fallback_used=True` means the short probe missed and the script tried bounded 24-hour-spaced probes within the metadata window.
- `active_hour_bins_in_24h_probe` is blank when hourly probes were deferred.
- `raw_rows_in_24h` is intentionally blank because exact 24-hour counts are deferred to the selected-window download/analysis phase.
- Missing raw rows near a metadata anchor means that metadata alone is not enough to prove raw accelerometer signal.
