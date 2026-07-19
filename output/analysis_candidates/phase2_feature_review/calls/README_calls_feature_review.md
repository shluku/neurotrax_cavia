# calls Phase 2A Feature Review Sample

This folder contains a Phase 2A manual-review sample for `calls`.

Current Phase 2A review search:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: 24 hours starting local midnight day after T1
- fallback: first complete 24-hour span inside T1 week
- SQL always filtered by `device_id` and `timestamp`

Selected review window:

- Subject_ID_D: `032`
- Subject_ID_N: `62`
- global_T1: `110.6`
- T1_date_iso: `2025-01-23`
- device_id: `c7fce041-6004-4299-b7d5-8947b4cb54cb`
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-24 00:00:00+0200`
- window_end_local: `2025-01-25 00:00:00+0200`
- n_rows_in_window: `5`

Files:

- `calls_sample_rows.csv`
- `calls_sample_rows_expanded.csv`
- `calls_sample_rows.jsonl`
- `calls_json_key_summary.csv`
- `calls_phase2a_t1_ranked_coverage_scan.csv`

This is manual feature review only. It is not diagnostic, not confirmatory, and missing data is not zero activity.
