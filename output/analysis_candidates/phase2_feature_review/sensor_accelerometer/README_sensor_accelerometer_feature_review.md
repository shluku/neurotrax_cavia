# sensor_accelerometer Phase 2A Feature Review Sample

This folder contains a Phase 2A manual-review sample for `sensor_accelerometer`.

Current Phase 2A review search:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: 24 hours starting local midnight day after T1
- fallback: first complete 24-hour span inside T1 week
- SQL always filtered by `device_id` and `timestamp`

Selected review window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1_date_iso: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `exploratory_fallback_first_24h_span_within_T1_week`
- window_start_local: `2025-01-08 09:07:27+0200`
- window_end_local: `2025-01-09 09:07:27+0200`
- n_rows_in_window: `36`

Files:

- `sensor_accelerometer_sample_rows.csv`
- `sensor_accelerometer_sample_rows_expanded.csv`
- `sensor_accelerometer_sample_rows.jsonl`
- `sensor_accelerometer_json_key_summary.csv`
- `sensor_accelerometer_phase2a_t1_ranked_coverage_scan.csv`

This is manual feature review only. It is not diagnostic, not confirmatory, and missing data is not zero activity.
