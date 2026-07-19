# significant R&D T1-to-30-Day Review

This is an R&D manual-review scan for `significant`.

It is not the standard Phase 2A protocol. The standard Phase 2A T1-week scan found no rows. This scan tests whether a broader bounded window, T1 to T1+30 days, can provide a manual inspection sample.

Safety rules used:

- SQL filtered by mapped `device_id`
- SQL filtered by timestamp from T1 to T1+30 days
- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- no feature extraction
- no aggregation beyond bounded row counts
- sample limited to first 20 chronological rows

Selected R&D review window:

No mapped ranked patient had at least 20 rows between T1 and T1+30 days.

Files:

- `significant_rd_t1_30day_sample_rows.csv`
- `significant_rd_t1_30day_sample_rows_expanded.csv`
- `significant_rd_t1_30day_sample_rows.jsonl`
- `significant_rd_t1_30day_json_key_summary.csv`
- `significant_rd_t1_30day_coverage_scan.csv`

This is for manual feature review only. Missing data is not zero activity.
