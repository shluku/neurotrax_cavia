# Phase 1 Digital Phenotype Profiles v2

## Scope
- Uses only existing Phase 1 output files.
- Does not query SQL.
- Does not extract new features.
- Does not modify previous outputs.
- Exploratory clinical readability layer only; not diagnostic and not confirmatory.

## Phenotype axes
- phone_engagement: relative early-window phone/app event engagement. Features: screen_early_event_count, app_early_foreground_event_count.
- nighttime_phone_activity: relative early-window nighttime screen activity. Features: screen_early_night_event_count.
- app_use_breadth: relative early-window app breadth and diversity. Features: app_early_unique_foreground_apps, app_early_app_use_diversity.
- active_phone_interaction: relative early-window keyboard and touch interaction. Features: keyboard_early_event_count, touch_early_event_count.
- physical_activity_context: relative early-window activity-recognition context signal. Features: activity_early_event_count, activity_early_still_event_count, activity_early_walking_event_count, activity_early_in_vehicle_event_count.
- data_quality_support: relative logging support for data availability; not a behavior axis. Features: aware_log_early_rows, aware_log_early_active_days.

## Classification method
- low / medium / high labels are relative to the 8 baseline-usable subjects only.
- Axis scores use percentile ranks of the contributing features within baseline-usable subjects, then tertile labels on the axis score.
- If a required feature column is unavailable, the axis is marked insufficient_data.
- Missing values are not converted to zero activity.

## Why aware_log is separate
- aware_log is treated only as data-quality/logging support.
- aware_log does not contribute to behavioral phenotype labels.
- data_quality_support_level is reported separately from the behavioral axes.

## Current sample limitations
- Top-decline Phase 1 subset only.
- Baseline phenotype available for 8 subjects: 001, 024, 030, 062, 077, 087, 093, 095.
- Change phenotype available only for 024 and 077.
- Change profiles are limited summaries of existing early-vs-late feature columns.
- Labels are descriptive, relative, and exploratory.

## Axes with insufficient source columns
- none

## Generated files
- phase1_subject_phenotype_profiles_v2.csv
- phase1_subject_phenotype_cards_v2.md
- phase1_change_profiles_024_077_v2.csv
- README_phase1_digital_phenotype_profiles_v2.md