# NeuroTrax-SensorDB Dementia Digital Phenotyping Project Summary

## Main Goal

This project links NeuroTrax cognitive assessments with SensorDB passive smartphone sensing data to build exploratory digital phenotype profiles for dementia research.

The current proof of concept focuses on the 10 subjects with the largest decline in NeuroTrax global cognitive score. The goal is to describe each subject's early/baseline digital phenotype and, where data coverage allows, explore early-vs-late digital change around T1 and T2 cognitive assessment windows.

This work is exploratory only. It is not diagnostic, not confirmatory, and does not make causal claims.

## Two Main Project Outcomes

### Outcome 1: T1 Baseline Digital Phenotype

Describe the patient's digital phenotype at the T1 time point using the Phase B 24-hour acquisition window after T1. This outcome will compare baseline digital patterns across NeuroTrax overall/global score rank, including high-ranked T1 overall/global performance and lower-ranked T2 overall/global performance patterns. The later modeling goal is to test whether T1 digital phenotype can help predict the patient's NeuroTrax overall/global T1 score.

### Outcome 2: T1-to-T2 Digital Phenotype Delta

Describe the digital phenotype change between T1 and T2. The later modeling goal is to test whether T1 baseline digital phenotype plus digital change can help predict the patient's NeuroTrax overall/global T2 score.

## Core Protocol Principles

- Missing data is not zero activity.
- `no_data` windows remain missing/NaN.
- SQL queries must always be filtered by `device_id` and timestamp.
- Full T1-to-T2 SensorDB windows are avoided because they are too large and unsafe for this stage.
- Current SQL work uses only the existing top-10 subject/device/window mapping.
- Early and late 7-day local calendar windows are preferred.
- Time windows use Asia/Jerusalem local calendar dates.
- Unix timestamps are milliseconds.
- Multiple `device_id` values can belong to the same subject and are treated as device episodes.
- High-frequency motion tables are postponed unless handled by a dedicated safe extraction protocol.
- `aware_log` is data-quality/system-logging support only, not a behavioral phenotype feature.
- Privacy-sensitive fields are flagged and should not be used as phenotype features.

## Cognitive Data Prepared

The cognitive master table was built from the NeuroTrax workbook and includes 83 subjects.

Key outputs:

- `output/cognitive_master/master_cognitive_wide.csv`
- `output/cognitive_master/cognitive_code_flags_long.csv`
- `output/cognitive_master/cognitive_data_dictionary.csv`
- `output/cognitive_master/delta_consistency_report.csv`
- `output/cognitive_master/README_cognitive_master.md`

Current cognitive status:

- 83 subject rows.
- 62 subjects have non-missing global delta and valid T1/T2 dates.
- Top-10 global decline subjects were selected for the current proof of concept.
- The top-10 subject/device mapping contains 22 device episodes.

## Phase 1 SensorDB Feature Extraction

Phase 1 extracted safe early/late window features from selected SensorDB tables.

Phase 1A included:

- `screen`
- `applications_foreground`
- `aware_log` as data-quality support only

Phase 1B included:

- `keyboard`
- `touch`
- `plugin_google_activity_recognition`

Important outputs:

- `output/analysis_candidates/phase1_features/extracted/phase1a_subject_window_features.csv`
- `output/analysis_candidates/phase1_features/extracted/phase1b_subject_window_features.csv`
- `output/analysis_candidates/phase1_features/extracted/phase1_subject_usability_summary.csv`
- `output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide.csv`

Phase 1 readiness:

- Baseline phenotype is available for 8 of 10 top-decline subjects.
- Early-vs-late change analysis is available only for subjects `024` and `077`.
- Subjects `044` and `074` currently have insufficient Phase 1 baseline data.

## Rich Phase 1 Wide Table

A richer wide table was rebuilt from existing extracted subject-window outputs. No SQL was queried and no new features were extracted from the database.

Output:

- `output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide_rich.csv`

Result:

- Old wide table: 10 rows x 56 columns.
- Rich wide table: 10 rows x 79 columns.
- 34 columns added compared with the old wide table.

The rich table fixed a structural issue where already-extracted Phase 1A fields were missing from the merged wide table, including:

- `screen_early_night_event_count`
- `screen_early_active_days`
- `app_early_unique_foreground_apps`
- `app_early_app_use_diversity`
- `app_early_active_days`

## Phase 1 Digital Phenotype Profiles v2

Clinically readable exploratory phenotype profiles were created from the rich wide table.

Output folder:

- `output/analysis_candidates/phase1_features/phenotype_profiles/`

Main outputs:

- `phase1_subject_phenotype_profiles_v2.csv`
- `phase1_subject_phenotype_cards_v2.md`
- `phase1_change_profiles_024_077_v2.csv`
- `README_phase1_digital_phenotype_profiles_v2.md`

Phenotype axes:

- `phone_engagement`
- `nighttime_phone_activity`
- `app_use_breadth`
- `active_phone_interaction`
- `physical_activity_context`
- `data_quality_support`

All axis labels are relative to the 8 baseline-usable subjects and use low/medium/high categories. These labels are descriptive only.

Baseline subjects profiled:

- `001`
- `024`
- `030`
- `062`
- `077`
- `087`
- `093`
- `095`

Change subjects profiled:

- `024`
- `077`

Updated axis distributions:

- `phone_engagement`: medium 3, high 3, low 2, insufficient_data 2
- `nighttime_phone_activity`: medium 5, high 3, insufficient_data 2
- `app_use_breadth`: medium 3, high 3, low 2, insufficient_data 2
- `active_phone_interaction`: high 3, medium 3, low 2, insufficient_data 2
- `physical_activity_context`: high 3, medium 3, low 2, insufficient_data 2
- `data_quality_support`: medium 3, high 3, low 2, insufficient_data 2

The previous all-`insufficient_data` problem for `nighttime_phone_activity` and `app_use_breadth` was resolved by using the rich wide table.

## Subject-Level Phenotype Examples

Subject `024`:

- Cognitive decline: `global_delta=-6.5`
- Phone engagement: medium
- Nighttime phone activity: high
- App-use breadth: medium
- Active phone interaction: low
- Physical activity context: low
- Change profile available: yes

Subject `077`:

- Cognitive decline: `global_delta=-5.1`
- Phone engagement: low
- Nighttime phone activity: medium
- App-use breadth: low
- Active phone interaction: medium
- Physical activity context: high
- Change profile available: yes

## Phase 2 SQL Fieldwork Status

Phase 2 is intended to systematically review additional SensorDB tables before implementing any new features.

A fieldwork inventory script was created:

- `phase2_sql_feature_fieldwork_inventory.py`

Planned outputs:

- `phase2_sql_table_inventory.csv`
- `phase2_sql_coverage_by_table_subject_window.csv`
- `phase2_sql_json_key_inventory.csv`
- `phase2_sql_table_decision_matrix.csv`
- `phase2_candidate_feature_dictionary.csv`
- `README_phase2_sql_feature_fieldwork.md`

A separate manual-review sampling script was also created:

- `sample_10_rows_per_sensordb_table.py`

This script is designed to sample up to 10 chronological rows per eligible SensorDB table, always filtered by `device_id` and early/late timestamp windows, with sensitive fields redacted.

Partial sample output folder:

- `output/analysis_candidates/phase2_sql_fieldwork_samples/`

The sampling run was interrupted by user request, so the sample outputs should be treated as partial unless rerun to completion.

## Privacy and Safety Notes

Privacy-sensitive fields must not be used directly as phenotype features.

Sensitive fields include, but are not limited to:

- keyboard text
- message body or message text
- phone numbers
- contact names
- email addresses
- subscriber IDs
- IMEI / IMSI / SIM serials
- Wi-Fi SSID/BSSID
- raw location identifiers

Communication, location, Wi-Fi, Bluetooth, GSM, telephony, and network tables require aggregate-only handling and additional review before use.

## Recommended Next Protocol Steps

1. Complete the Phase 2 SQL table fieldwork inventory with constrained early/late window scans.
2. Complete the 10-row-per-table manual review sample if needed.
3. Review privacy-sensitive fields before any new feature extraction.
4. Select a limited Phase 2 feature set, preferably context and phone-state features first.
5. Implement Phase 2 extraction in small, table-specific scripts.
6. Add QC checks that verify missing data remains missing and sensitive raw values are not saved.

## Current Interpretation Boundary

The current results support exploratory descriptive profiling for a small proof-of-concept cohort only.

They do not support:

- diagnostic classification
- confirmatory statistics
- causal interpretation
- generalization beyond the current sample
- treating missing SensorDB data as inactivity
