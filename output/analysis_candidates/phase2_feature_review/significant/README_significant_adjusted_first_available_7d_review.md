# significant Adjusted First-Available 7-Day Review

This is a table-specific adjusted Phase 2A review for `significant`.

The standard T1-week and T1+30-day scans found no rows. This adjusted review finds the first available `significant` timestamp for each ranked mapped patient/device and samples the first 7 days from that point.

This is not a T1 baseline acquisition window. It is delayed first-available table analysis, useful for understanding and potentially extracting `significant` features separately from baseline T1 digital phenotyping.

Safety rules used:

- SQL filtered by mapped `device_id`
- SQL filtered by timestamp for a bounded 7-day window
- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- no feature extraction
- sample limited to first 20 chronological rows

Selected adjusted review window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1_date_iso: `2025-01-08`
- device_id: `bce3e6dc-a61a-4fc5-8d6f-41ff16761f5b`
- window_rule: `adjusted_first_available_7d`
- window_start_local: `2025-07-08 10:55:14+0300`
- window_end_local: `2025-07-15 10:55:14+0300`
- n_rows_in_window: `776`
- days_first_available_after_T1: `180`

## Observed Row Structure

The adjusted sample contains a very small JSON structure:

- `device_id`
- `timestamp`
- `is_moving`

In the first 20 sampled rows, `is_moving` was `1` for all rows. This suggests the table may mostly record significant-motion detections rather than continuous movement/non-movement state. This needs to be checked in Phase 2B before interpreting fraction or transition features.

## Candidate Features

Recommended adjusted-window candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `significant_event_count` | Count rows in the adjusted first-available 7-day window. | Volume of significant-motion detections once this delayed stream becomes available. | Delayed window only; not T1 baseline. |
| `significant_moving_event_count` | Count rows where `is_moving` indicates moving. | Moving-labeled significant events. | May be identical to row count if the table logs only moving detections. |
| `significant_moving_fraction` | Moving-labeled rows divided by valid `is_moving` rows. | Proportion of moving-labeled observations. | May be uninformative if all rows are moving by design. |
| `significant_active_hour_count` | Count unique local hours with at least one row. | Temporal spread of significant-motion detections. | Data availability/timing support; missing is not no movement. |
| `significant_motion_transition_count` | Count changes between consecutive valid `is_moving` states. | Variability if both moving and non-moving states appear. | May be zero if the table only records significant moving events. |

## Feature Decision

No adjusted `significant` features are selected yet.

If selected, Phase 2B should be labeled as adjusted first-available 7-day analysis, not T1 baseline digital phenotyping.

Files:

- `significant_adjusted_first_available_7d_sample_rows.csv`
- `significant_adjusted_first_available_7d_sample_rows_expanded.csv`
- `significant_adjusted_first_available_7d_sample_rows.jsonl`
- `significant_adjusted_first_available_7d_json_key_summary.csv`
- `significant_adjusted_first_available_7d_coverage_scan.csv`

Missing data is not zero activity. This review is exploratory and not diagnostic.
