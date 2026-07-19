# locations Phase 2A Feature Review Sample

This folder contains a Phase 2A manual-review sample for `locations`.

Current Phase 2A review search:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: 24 hours starting local midnight day after T1
- fallback: first complete 24-hour span inside T1 week
- SQL always filtered by `device_id` and `timestamp`

Selected review window:

- Subject_ID_D: `085`
- Subject_ID_N: `81`
- global_T1: `100.0`
- T1_date_iso: `2025-03-04`
- device_id: `b89546ef-9f57-4fd0-ad48-638a4a783d19`
- window_rule: `exploratory_fallback_first_24h_span_within_T1_week`
- window_start_local: `2025-03-04 10:26:12+0200`
- window_end_local: `2025-03-05 10:26:12+0200`
- n_rows_in_window: `4468`

Files:

- `locations_sample_rows.csv`
- `locations_sample_rows_expanded.csv`
- `locations_sample_rows.jsonl`
- `locations_json_key_summary.csv`
- `locations_phase2a_t1_ranked_coverage_scan.csv`

This is manual feature review only. It is not diagnostic, not confirmatory, and missing data is not zero activity.
