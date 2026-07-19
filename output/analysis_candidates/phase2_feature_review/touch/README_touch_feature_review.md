# touch Feature Review

## Table Meaning

`touch` records touchscreen accessibility-style interaction events. The Phase 2A sample suggests that one row can represent a touch/click event or a scroll event in a foreground app or system UI context.

The table is useful for active phone interaction features, but raw rows should not be treated as exact finger taps. The same underlying observation can appear more than once in the database, so deduplication is required before feature calculation.

The Phase 2A sample shows these JSON fields:

- `touch_app`
- `touch_action`
- `touch_action_text`
- `scroll_items`
- `scroll_to_index`
- `scroll_from_index`
- `device_id`
- `timestamp`

Observed action labels in the first 20 raw sample rows:

- `ACTION_AWARE_TOUCH_CLICKED`
- `ACTION_AWARE_TOUCH_SCROLLED_DOWN`
- `ACTION_AWARE_TOUCH_SCROLLED_UP`

`touch_action_text` is redacted in review files because it can contain screen text. It should not become a model-facing raw feature.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp

Selected review window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1_date_iso: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-09 00:00:00+0200`
- window_end_local: `2025-01-10 00:00:00+0200`
- raw rows in window: `1820`
- sampled rows: `20`
- distinct sampled observations after deduplication: `10`

Observed sample structure:

| field | examples |
|---|---|
| `touch_app` | `com.android.systemui`, `com.huawei.android.launcher`, `com.whatsapp` |
| `touch_action` | `ACTION_AWARE_TOUCH_CLICKED`, `ACTION_AWARE_TOUCH_SCROLLED_DOWN`, `ACTION_AWARE_TOUCH_SCROLLED_UP` |
| `scroll_items` | `-1`, `36`, `283` |
| `scroll_to_index` | `-1`, `35`, `7`, `8` |
| `scroll_from_index` | `-1`, `34`, `33`, `1`, `2` |

The first 20 sampled raw rows contain paired duplicate database copies. Phase 2B extraction should deduplicate before calculating features. Current Phase 2A deduplication key:

`timestamp + device_id + touch_app + touch_action + scroll_items + scroll_to_index + scroll_from_index + touch_action_text`

## Candidate Features

Recommended major candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `touch_distinct_event_count` | Count distinct touch observations after deduplication. | Touchscreen interaction volume beyond screen on/off state. | Not exact finger taps; OS and accessibility logging can inflate rows. |
| `touch_click_event_count` | Count distinct observations where `touch_action` is `ACTION_AWARE_TOUCH_CLICKED`. | Tap/click-like interaction signal. | Click label is not guaranteed to equal one physical tap. |
| `touch_scroll_event_count` | Count distinct observations where `touch_action` contains `SCROLLED`. | Scroll-like interaction signal. | Depends on app UI and logging behavior. |
| `touch_scroll_direction_change_count` | Count changes between consecutive scroll directions after deduplication. | Approximate scroll interaction variability. | Sensitive to duplicate handling and app layout. |
| `touch_unique_app_count` | Count distinct `touch_app` values with touch observations. | Breadth of apps with active touch interaction. | Package names should stay aggregate in model-facing outputs. |
| `touch_app_diversity` | Diversity of distinct touch events across `touch_app`. | Concentration versus breadth of touch interaction by app. | Depends on system UI and package reporting. |
| `touch_active_hour_count` | Count local hours with at least one distinct touch observation. | Temporal spread of active interaction. | Data coverage/use timing support; missing is not no use. |
| `touch_scroll_index_change_median` | Median absolute difference between `scroll_to_index` and `scroll_from_index` for valid scroll rows. | Approximate scroll movement size when indexes are meaningful. | Index values are app dependent and not physical distance. |

## Feature Decision

Selected features:

- `touch_distinct_event_count`
- `touch_click_event_count`
- `touch_scroll_event_count`
- `touch_scroll_direction_change_count`
- `touch_unique_app_count`
- `touch_app_diversity`
- `touch_active_hour_count`
- `touch_scroll_index_change_median`

Selection note: user selected feature numbers `124`, `125`, `126`, `127`, `128`, `129`, `130`, and `131` from the current Streamlit candidate table.

Phase 2B calculation rules:

- Deduplicate observations using `timestamp + device_id + touch_app + touch_action + scroll_items + scroll_to_index + scroll_from_index + touch_action_text`.
- `touch_distinct_event_count`: count deduplicated observations.
- `touch_click_event_count`: count deduplicated observations where `touch_action` equals `ACTION_AWARE_TOUCH_CLICKED`.
- `touch_scroll_event_count`: count deduplicated observations where `touch_action` contains `SCROLLED`.
- `touch_scroll_direction_change_count`: count changes between consecutive scroll directions after deduplication.
- `touch_unique_app_count`: count distinct non-empty `touch_app` values.
- `touch_app_diversity`: Shannon diversity across deduplicated `touch_app` values.
- `touch_active_hour_count`: count unique local hours with at least one deduplicated touch observation.
- `touch_scroll_index_change_median`: median absolute difference between valid non-negative `scroll_to_index` and `scroll_from_index` values among scroll events.

Raw `touch_action_text` is used only as part of the deduplication key and is not saved as a model-facing feature.

## Output Files

- `output/analysis_candidates/phase2_feature_review/touch/touch_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/touch/touch_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/touch/touch_sample_rows_distinct_observations.csv`
- `output/analysis_candidates/phase2_feature_review/touch/touch_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/touch/touch_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/touch/touch_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- Deduplicate repeated observations before feature calculation.
- Do not interpret row count as exact number of physical taps.
- Do not use raw `touch_action_text` as a phenotype feature.
- Package names should be used only through aggregate features.
- Missing `touch` rows are missing data, not no touch activity.
- These features are exploratory digital interaction signals and are not diagnostic.

## Global Coverage Summary

This compact summary describes global `touch` availability from the current Streamlit coverage preview.

- Approximate mapped rows in preview: `4,598,236`
- Mapped study/pseudo labels with rows in preview: `72`
- Top mapped subjects by rows include Subject_ID_D `005`, `083`, `039`, `026`, and `023`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
