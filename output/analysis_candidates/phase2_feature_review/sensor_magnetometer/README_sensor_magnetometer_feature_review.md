# sensor_magnetometer Phase 2A Feature Review Sample

This folder contains a Phase 2A manual-review sample for `sensor_magnetometer`.

Current Phase 2A review search:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: 24 hours starting local midnight day after T1
- fallback: first complete 24-hour span inside T1 week
- SQL always filtered by `device_id` and `timestamp`

No protocol-valid review window with enough rows was found.

Files:

- `sensor_magnetometer_sample_rows.csv`
- `sensor_magnetometer_sample_rows_expanded.csv`
- `sensor_magnetometer_sample_rows.jsonl`
- `sensor_magnetometer_json_key_summary.csv`
- `sensor_magnetometer_phase2a_t1_ranked_coverage_scan.csv`

This is manual feature review only. It is not diagnostic, not confirmatory, and missing data is not zero activity.
