# Investor Progress Snapshot - NeuroTrax SensorDB Digital Phenotyping

## One-Line Summary

We have converted the project from raw SensorDB access into a structured exploratory digital biomarker pipeline: cognitive data are organized, Phase 1 phenotype profiles are built, and Phase 2 has already reviewed **10 SensorDB tables** with **29 manually selected features** and **27 currently calculable numeric feature values**.

## What This Project Is Building

The project links NeuroTrax cognitive assessments with passive smartphone SensorDB data to create exploratory digital phenotype features for dementia research.

The two planned research outputs are:

1. **T1 baseline digital phenotype:** describe smartphone-derived behavior/context around the T1 cognitive assessment.
2. **T1-to-T2 digital phenotype change:** later quantify digital change between T1 and T2 and test whether it helps predict cognitive outcomes.

This work is exploratory and protocol-development stage. It is not diagnostic and not confirmatory.

## Progress So Far

| Metric | Current value |
|---|---:|
| SensorDB tables tracked | 44 |
| Reviewed table files | 10 |
| Candidate feature definitions | 69 |
| Manually selected features | 29 |
| Currently calculated numeric feature values | 27 |
| Tables with calculated feature values | 8 |
| SensorDB inventory rows | 44 |

## Phase 1 Result

Phase 1 created clinically readable exploratory phenotype profiles for the proof-of-concept cohort:

- baseline digital phenotype profiles for 8 usable subjects
- limited T1-to-T2 change profiles for subjects `024` and `077`
- phenotype axes including phone engagement, nighttime phone activity, app-use breadth, active phone interaction, physical activity context, and data-quality support

## Phase 2 Result So Far

Phase 2 is systematically reviewing SensorDB tables before broad extraction. Each table is inspected safely with device/time-filtered SQL, candidate features are proposed, and only manually selected aggregate features are implemented.

### Reviewed / Feature-Tracked Tables

| table_name | candidate_features | selected_features | currently_calculated_values | status |
| --- | --- | --- | --- | --- |
| keyboard | 15 | 6 | 6 | calculated |
| calls | 6 | 5 | 5 | calculated |
| light | 7 | 4 | 4 | calculated |
| applications_foreground | 8 | 3 | 3 | calculated |
| gsm | 6 | 3 | 3 | calculated |
| locations | 7 | 2 | 2 | calculated |
| messages | 5 | 2 | 2 | calculated |
| bluetooth | 2 | 2 | 2 | calculated |
| battery | 6 | 2 | 0 | selected_not_calculated |
| linear_accelerometer | 7 | 0 | 0 | reviewed_or_candidate |

## What We Can Calculate Right Now

The current exploratory selected-feature table already contains numeric features from app use, Bluetooth, calls, GSM, keyboard, light, locations, and messages. Battery is selected but currently has no protocol-valid T1-week window, so it remains missing rather than being converted to zero.

| table_name | feature_name | feature_value | Subject_ID_D | global_T1 | T1_date_iso | window_rule | window_start_local | window_end_local | feature_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| applications_foreground | app_foreground_event_count | 698 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| applications_foreground | unique_foreground_apps | 22 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| applications_foreground | app_use_diversity | 3.593 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| bluetooth | unique_bluetooth_addresses | 302 | 085 | 100.0 | 2025-03-04 | exploratory_fallback_first_24h_span_within_T1_week | 2025-03-04 10:26:13+0200 | 2025-03-05 10:26:13+0200 | calculated |
| bluetooth | bluetooth_address_diversity_ratio | 0.172 | 085 | 100.0 | 2025-03-04 | exploratory_fallback_first_24h_span_within_T1_week | 2025-03-04 10:26:13+0200 | 2025-03-05 10:26:13+0200 | calculated |
| calls | call_event_count | 5 | 032 | 110.6 | 2025-01-23 | exploratory_primary_day_after_T1 | 2025-01-24 00:00:00+0200 | 2025-01-25 00:00:00+0200 | calculated |
| calls | incoming_call_count | 1 | 032 | 110.6 | 2025-01-23 | exploratory_primary_day_after_T1 | 2025-01-24 00:00:00+0200 | 2025-01-25 00:00:00+0200 | calculated |
| calls | outgoing_call_count | 4 | 032 | 110.6 | 2025-01-23 | exploratory_primary_day_after_T1 | 2025-01-24 00:00:00+0200 | 2025-01-25 00:00:00+0200 | calculated |
| calls | missed_rejected_blocked_call_count | 0 | 032 | 110.6 | 2025-01-23 | exploratory_primary_day_after_T1 | 2025-01-24 00:00:00+0200 | 2025-01-25 00:00:00+0200 | calculated |
| calls | total_call_duration_seconds | 210 | 032 | 110.6 | 2025-01-23 | exploratory_primary_day_after_T1 | 2025-01-24 00:00:00+0200 | 2025-01-25 00:00:00+0200 | calculated |
| gsm | unique_gsm_cell_count | 16 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| gsm | unique_gsm_lac_count | 2 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| gsm | gsm_cell_transition_count | 35 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| keyboard | keyboard_median_inter_event_interval_ms | 482.5 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| keyboard | keyboard_inter_event_interval_iqr_ms | 281.5 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| keyboard | keyboard_long_pause_count_2s | 72 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| keyboard | keyboard_typing_burst_count | 26 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| keyboard | keyboard_median_word_completion_time_ms | 2340 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| keyboard | keyboard_deletion_event_count | 109 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| light | median_light_lux | 0 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| light | percent_dark_samples | 64.99 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| light | night_mean_light_lux | 2.705e-06 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| light | light_lux_iqr | 18.1 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| locations | location_distinct_observation_count | 185 | 085 | 100.0 | 2025-03-04 | exploratory_fallback_first_24h_span_within_T1_week | 2025-03-04 10:26:12+0200 | 2025-03-05 10:26:12+0200 | calculated |
| locations | location_total_distance_km | 2.008 | 085 | 100.0 | 2025-03-04 | exploratory_fallback_first_24h_span_within_T1_week | 2025-03-04 10:26:12+0200 | 2025-03-05 10:26:12+0200 | calculated |
| messages | message_distinct_event_count | 9 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |
| messages | outgoing_message_count | 0 | 041 | 119.4 | 2025-01-08 | exploratory_primary_day_after_T1 | 2025-01-09 00:00:00+0200 | 2025-01-10 00:00:00+0200 | calculated |

## Scientific / Clinical Guardrails

- Missing data is never interpreted as zero activity.
- Raw message text, contacts, phone numbers, typed text, and raw coordinates are not used as model-facing features.
- Features are aggregate exploratory markers only.
- The current values are feature-development examples, not final full-cohort analysis.

## Files In This Snapshot

- `investor_phase2_progress_metrics.csv`
- `investor_phase2_feature_progress_by_table.csv`
- `investor_current_calculable_feature_values.csv`
- `investor_phase2_progress_snapshot.svg`
