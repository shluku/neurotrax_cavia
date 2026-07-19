# barometer Adjusted First-Available 7-Day Review

This is a table-specific adjusted Phase 2A review for `barometer`.

The standard T1-week scan found no rows. This adjusted review finds the first available `barometer` timestamp at or after T1 for each ranked mapped patient/device and samples the first 7 days from that point.

This is not a T1 baseline acquisition window. It is delayed first-available table analysis for manual feature fieldwork.

Selected adjusted review window:

- Subject_ID_D: `045`
- Subject_ID_N: `51`
- global_T1: `93.4`
- T1_date_iso: `2025-01-21`
- device_id: `fdce7e53-e549-45b0-a477-8c300329c656`
- window_rule: `adjusted_first_available_7d_after_T1`
- window_start_local: `2025-07-10 10:36:07+0300`
- window_end_local: `2025-07-17 10:36:07+0300`
- n_rows_in_window: `2750`
- days_first_available_after_T1: `169`

Files:

- `barometer_adjusted_first_available_7d_sample_rows.csv`
- `barometer_adjusted_first_available_7d_sample_rows_expanded.csv`
- `barometer_adjusted_first_available_7d_sample_rows.jsonl`
- `barometer_adjusted_first_available_7d_json_key_summary.csv`
- `barometer_adjusted_first_available_7d_coverage_scan.csv`

Missing data is not zero activity. This review is exploratory and not diagnostic.
