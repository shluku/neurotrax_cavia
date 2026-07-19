# plugin_google_activity_recognition

## Phase 2A Manual Review Status

The standard Phase 2A T1-ranked T1-week 24-hour protocol found a valid review window for `plugin_google_activity_recognition`.

## Current Manual Sample

- sample_context: `phase2a_t1_ranked_24h_t1_week_review_sample`
- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1 date: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `exploratory_primary_day_after_T1`
- window: `2025-01-09 00:00:00+0200` to `2025-01-10 00:00:00+0200`
- rows in window: `423`
- sampled rows: `20`
- first sampled/local row: `2025-01-09 00:58:58+0200`
- last sampled/local row: `2025-01-09 19:51:57+0200`

## Field Meaning

This table stores Google/AWARE activity-recognition events. The records are categorical phone-derived context labels, not direct clinical measurement and not direct body movement measurement.

Observed review fields:

- `activity_name`: top inferred activity label, such as `still`, `unknown`, `on_foot`, `walking`, or `tilting`.
- `activity_type`: numeric activity code.
- `confidence`: confidence score for the top inferred activity.
- `activities`: list-like JSON string containing candidate activity labels and confidence values.
- `timestamp`, `device_id`: event time and device linkage fields.

## Activity Label Inventory

The SQL table stores these labels inside the JSON `data` column, not as ordinary SQL columns. The top-label inventory comes from `JSON_EXTRACT(data, '$.activity_name')`.

Top `activity_name` values found globally:

| activity_name | activity_type | rows |
|---|---:|---:|
| still | 3 | 1,390,326 |
| unknown | 4 | 561,229 |
| tilting | 5 | 398,862 |
| in_vehicle | 0 | 222,553 |
| on_foot | 2 | 137,788 |
| on_bicycle | 1 | 9,970 |
| tilting | 3 | 1 |

Candidate labels found inside the nested `activities` list:

| candidate activity | mentions |
|---|---:|
| still | 2,160,049 |
| unknown | 1,678,551 |
| in_vehicle | 1,236,387 |
| walking | 1,052,130 |
| on_foot | 1,052,036 |
| on_bicycle | 883,543 |
| running | 674,869 |
| tilting | 398,863 |

For feature extraction, `activity_name` should be treated as the primary top label. The nested `activities` list can support later confidence-distribution features, but it is more complex because it stores multiple candidate labels per row.

## Candidate Feature Plan

Candidate features for this table should stay aggregate and window-bounded:

- `activity_recognition_event_count`: number of activity-recognition events in the selected window.
- `activity_recognition_high_confidence_event_count`: number of events with confidence above a documented threshold.
- `activity_recognition_mean_confidence`: mean confidence across events.
- `activity_still_fraction`: fraction of top activity labels classified as still.
- `activity_walking_or_on_foot_event_count`: number of events classified as walking or on foot.
- `activity_in_vehicle_event_count`: number of events classified as in vehicle.
- `activity_unknown_fraction`: fraction of top activity labels classified as unknown.
- `activity_state_diversity`: diversity of observed top activity states.
- `activity_transition_count`: count of changes between consecutive top activity states.
- `activity_active_hour_count`: number of local hours with at least one event.

## Feature Decision

Selected features:

- `activity_transition_count`
- `activity_still_fraction`
- `activity_active_hour_count`
- `activity_unknown_fraction`
- `activity_state_diversity`

Selection note: user selected features `74`, `69`, `76`, `72`, and `73`. Because `76` was not in the earlier short numbered list, it is interpreted here as `activity_active_hour_count`, the next activity-recognition candidate in the working feature table.

## Output Files

- `output/analysis_candidates/phase2_feature_review/plugin_google_activity_recognition/plugin_google_activity_recognition_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/plugin_google_activity_recognition/plugin_google_activity_recognition_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/plugin_google_activity_recognition/plugin_google_activity_recognition_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/plugin_google_activity_recognition/plugin_google_activity_recognition_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/plugin_google_activity_recognition/plugin_google_activity_recognition_phase2a_t1_ranked_coverage_scan.csv`

## Caution

`still` does not mean sleep, inactivity, or being at home. `walking` or `on_foot` means the phone received a walking-like activity-recognition signal. Results can depend on phone carrying behavior, operating-system activity recognition, sampling behavior, and confidence thresholds.

## Global Coverage Summary

This compact summary describes global `plugin_google_activity_recognition` availability from the current Streamlit coverage preview.

- Approximate mapped rows: `2,497,482`
- Approximate patient coverage: `94%`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
