# SQL Coverage Scan (Top10 Decline)

This scan checks data availability only.

- It does **not** compute features.
- Missing rows are **not** interpreted as zero activity.
- Every query is filtered by both `device_id` and `timestamp` range.
- `full_T1_T2_window` uses a lighter query (`COUNT, MIN, MAX` only), without `COUNT DISTINCT day`.
- Results are used to decide which tables are usable for first digital phenotype extraction.
