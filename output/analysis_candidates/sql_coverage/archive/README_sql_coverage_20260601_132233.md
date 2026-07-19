# SQL Coverage Scan (Top10 Decline)

This scan checks data availability only.

- It does **not** compute features.
- Missing rows are **not** interpreted as zero activity.
- Every query is filtered by both `device_id` and `timestamp` range.
- Results are used to decide which tables are usable for first digital phenotype extraction.

Scanned tables:
- aware_log, battery, screen, wifi, calls, messages, locations,
  applications_foreground, keyboard, touch, gsm, gsm_neighbor,
  telephony, plugin_google_activity_recognition

Scanned windows:
- early_window
- late_window
- full_T1_T2_window

Outputs:
- top10_sql_coverage_long.csv
- top10_sql_coverage_summary_by_subject.csv
- top10_sql_coverage_summary_by_table.csv
