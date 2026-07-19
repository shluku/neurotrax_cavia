# messages Phase 2A Feature Review Sample

This folder contains a Phase 2A manual-review sample for `messages`.

Current Phase 2A review search:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: 24 hours starting local midnight day after T1
- fallback: first complete 24-hour span inside T1 week
- SQL always filtered by `device_id` and `timestamp`

Selected review window:

- Subject_ID_D: `089`
- Subject_ID_N: `61`
- global_T1: `109.3`
- T1_date_iso: `2025-01-23`
- device_id: `e361ed72-5d8b-48b9-b2eb-c5eeb03da274`
- window_rule: `exploratory_fallback_first_24h_span_within_T1_week`
- window_start_local: `2025-01-23 12:51:16+0200`
- window_end_local: `2025-01-24 12:51:16+0200`
- n_rows_in_window: `64`

Files:

- `messages_sample_rows.csv`
- `messages_sample_rows_expanded.csv`
- `messages_sample_rows.jsonl`
- `messages_json_key_summary.csv`
- `messages_phase2a_t1_ranked_coverage_scan.csv`

This is manual feature review only. It is not diagnostic, not confirmatory, and missing data is not zero activity.
