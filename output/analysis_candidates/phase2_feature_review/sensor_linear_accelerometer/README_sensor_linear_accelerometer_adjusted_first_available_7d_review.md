# sensor_linear_accelerometer Adjusted First-Available 7-Day Review

This is a table-specific adjusted review for `sensor_linear_accelerometer`.

The standard T1-week scan found no rows. This adjusted review finds the first available timestamp at or after T1 for each ranked mapped patient/device and samples the first 7 days from that point.

This is not a T1 baseline acquisition window. It is delayed first-available table analysis.

Selected adjusted review window:

- Subject_ID_D: `044`
- Subject_ID_N: `44`
- global_T1: `108.3`
- T1_date_iso: `2025-01-20`
- device_id: `6faf770c-e0bf-4100-9b63-c6167630c854`
- window_rule: `adjusted_first_available_7d_after_T1`
- window_start_local: `2025-07-10 11:22:50+0300`
- window_end_local: `2025-07-17 11:22:50+0300`
- n_rows_in_window: `25`
- days_first_available_after_T1: `170`

Files:

- `sensor_linear_accelerometer_adjusted_first_available_7d_sample_rows.csv`
- `sensor_linear_accelerometer_adjusted_first_available_7d_sample_rows_expanded.csv`
- `sensor_linear_accelerometer_adjusted_first_available_7d_sample_rows.jsonl`
- `sensor_linear_accelerometer_adjusted_first_available_7d_json_key_summary.csv`
- `sensor_linear_accelerometer_adjusted_first_available_7d_coverage_scan.csv`

Missing data is not zero movement. This review is exploratory and not diagnostic.
