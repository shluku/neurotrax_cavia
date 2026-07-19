# SQL Coverage Scan (Top10 Decline)

This scan checks data availability only.

- It does **not** compute features.
- Missing rows are **not** interpreted as zero activity.
- Every query is filtered by both `device_id` and `timestamp` range.
- `early_window` and `late_window` were scanned directly and are the primary reliable outputs.
- `full_T1_T2_window` was intentionally skipped when span >45 days using safety guard.
- `skipped_long_full_window` is an intentional safety skip, not a DB error.
- Full-window coverage should be done later with a safer day-level strategy.
