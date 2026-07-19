# telephony Phase 2A Feature Review Sample

This folder contains a Phase 2A manual-review sample for `telephony`.

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
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-09 00:00:00+0200`
- window_end_local: `2025-01-10 00:00:00+0200`
- n_rows_in_window: `93`

Files:

- `telephony_sample_rows.csv`
- `telephony_sample_rows_expanded.csv`
- `telephony_sample_rows.jsonl`
- `telephony_json_key_summary.csv`
- `telephony_phase2a_t1_ranked_coverage_scan.csv`

This is manual feature review only. It is not diagnostic, not confirmatory, and missing data is not zero activity.
