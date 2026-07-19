# applications_foreground Highest T1 Phase B 24h Extraction

This is the first Phase 2 selected-feature extraction prototype.

Selected patient:

- Subject_ID_D: 041
- Subject_ID_N: 15
- global_T1: 119.4
- T1_date_iso: 2025-01-08

Window rule:

- Primary window starts at local midnight on the day after T1.
- Primary duration: 24 hours.
- If the primary window has no `applications_foreground` data across mapped devices, the fallback starts at the first observed `applications_foreground` timestamp that allows a complete 24-hour span inside the T1 week.
- T1 week: `2025-01-08 00:00:00+0200` to `2025-01-15 00:00:00+0200`.
- Missing data is not interpreted as zero activity.

Selected window:

- window_rule: primary_day_after_T1
- window_start_local: 2025-01-09 00:00:00+0200
- window_end_local: 2025-01-10 00:00:00+0200

Selected features:

- app_foreground_event_count
- unique_foreground_apps
- app_use_diversity

Generated files:

- `applications_foreground_highest_t1_36h_features.csv`
- `applications_foreground_highest_t1_36h_window_coverage.csv`
- `applications_foreground_highest_t1_36h_rows.csv`
