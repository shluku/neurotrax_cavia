# screen Feature Review

## Table Meaning

`screen` records screen state transition events from the device.

This table is clinically interesting as phone-engagement and temporal-use context. It should not be interpreted as cognition by itself. Missing screen data is missing data, not zero phone use.

The Phase 2A sample shows these JSON fields:

- `screen_status`
- `device_id`
- `timestamp`

Working `screen_status` interpretation, based on common AWARE screen-event coding:

| screen_status | Working meaning |
|---:|---|
| `0` | screen off |
| `1` | screen on |
| `2` | screen locked |
| `3` | screen unlocked |

This mapping should be treated as a working interpretation unless confirmed from the local AWARE table documentation.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp
- no aggregation was used for the manual sample

Selected review window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1_date_iso: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-09 00:00:00+0200`
- window_end_local: `2025-01-10 00:00:00+0200`
- raw rows in window: `304`
- sampled rows: `20`
- first sampled/local row: `2025-01-09 06:00:02+0200`
- last sampled/local row: `2025-01-09 07:00:34+0200`

Sample status counts in the first 20 rows:

| screen_status | count |
|---:|---:|
| `0` | 4 |
| `1` | 5 |
| `2` | 9 |
| `3` | 2 |

## Candidate Features

Recommended major candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `screen_event_count` | Count all screen rows in the selected window. | Basic screen-state event volume. | Event count is not screen time; repeated transitions can inflate count. |
| `screen_unlock_event_count` | Count rows where `screen_status == 3`. | Approximate count of unlock events. | Unlocks are phone interaction opportunities, not direct task engagement. |
| `screen_on_event_count` | Count rows where `screen_status == 1`. | Approximate screen-on activations. | Screen-on events can occur without meaningful interaction. |
| `screen_off_event_count` | Count rows where `screen_status == 0`. | Approximate screen-off transitions. | Mostly useful together with on/unlock transitions. |
| `screen_active_hour_count` | Count unique local hours with at least one screen event. | Temporal spread of screen activity. | Sparse logging makes this unstable. |
| `night_screen_event_count` | Count screen events during local nighttime, for example 22:00-06:00. | Nighttime phone-activity context. | Night screen activity is not sleep disturbance by itself. |
| `screen_transition_count` | Count changes between consecutive `screen_status` values ordered by timestamp. | Screen-state switching intensity. | Can reflect OS logging behavior as well as use behavior. |
| `estimated_unlocked_duration_minutes` | Sum time from unlocked events to next lock/off event when observable. | Approximate unlocked-session duration. | Requires careful pairing logic and censoring at window boundaries. |
| `median_unlocked_session_duration_seconds` | Median paired unlocked-session duration. | Typical unlocked-session length. | Sensitive to missing lock/off events and repeated status rows. |

## Feature Decision

Selected features:

- `screen_event_count`
- `screen_unlock_event_count`
- `screen_on_event_count`
- `screen_off_event_count`
- `screen_active_hour_count`
- `night_screen_event_count`
- `screen_transition_count`
- `median_unlocked_session_duration_seconds`

Selection note: user selected feature numbers `87`, `84`, `83`, `79`, `82`, `81`, `85`, and `80`. Because `79` exists only in the zero-based working candidate table, these selections are interpreted as zero-based candidate numbers. This selects all current `screen` candidates except `estimated_unlocked_duration_minutes`.

## Output Files

- `output/analysis_candidates/phase2_feature_review/screen/screen_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/screen/screen_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/screen/screen_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/screen/screen_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/screen/screen_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- Missing screen rows are missing data, not zero phone use.
- Use aggregate window-bounded features only.
- Screen features describe device screen-state context, not cognition or diagnosis.
- Duration features require explicit pairing rules and should be treated cautiously.

## Global Coverage Summary

This compact summary describes global `screen` availability from the current Streamlit coverage preview.

- Approximate mapped rows in preview: `1,149,927`
- Mapped study/pseudo labels with rows in preview: `84`
- Top mapped subject by rows: Subject_ID_D `001`, `122,544` rows
- Highest non-001 examples include Subject_ID_D `018`, `061`, `012`, and `004`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
