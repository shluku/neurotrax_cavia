# battery Highest-T1 Phase B 24h Selected Features

This folder contains the Phase B prototype extraction for selected `battery` features.

Selected features:

- `low_battery_event_count`: count rows where normalized battery percent is `<= 20`.
- `charging_or_plugged_event_count`: count rows where `battery_adaptor != 0` or `battery_status` is in expected Android charging/full codes `2` or `5`.

Patient/window rule:

- Highest-T1 patient: Subject_ID_D `041`, global_T1 `119.4`.
- Primary start: local midnight on the day after `T1_date_iso`.
- Window length: 24 hours.
- Fallback: first observed `battery` timestamp that allows a complete 24-hour span inside the T1 week.
- T1 week: `2025-01-08 00:00:00+0200` to `2025-01-15 00:00:00+0200`.

Result:

- window_rule: `no_battery_data_with_24h_span_in_T1_week`
- rows in selected window: `0`
- feature_status: `insufficient_data_no_battery_rows`

Missing data is not zero activity. If no rows are available, selected feature values remain missing.
