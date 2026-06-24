# Dementia / NeuroTrax + SensorDB Project Status

## 1. Project goal

The project has two main goals:

1. Characterize patients by their digital phenotypes, especially around the first usable digital day after NeuroTrax T1.
2. Detect digital phenotype changes over time and compare them with cognitive changes/deltas from NeuroTrax.

The current PoC focuses first on the 10 patients with the largest global cognitive decline.

## 2. Main analysis principles

- Data availability is part of the analysis and must be explicitly reported.
- SensorDB data must be aligned to real NeuroTrax T1/T2 dates.
- Date windows must use local calendar days in Asia/Jerusalem.
- Unix timestamps used for SQL are milliseconds.
- Many subjects may have multiple device_id values because each app installation may generate a new device_id.
- Multiple device IDs are treated as device episodes belonging to the same subject.
- Accelerometer / linear_accelerometer / gyroscope / rotation are postponed because they are high-frequency/heavy.
- sensor_* tables are operational tables and should be ignored for analysis.
- Missing data must not be interpreted as zero activity.

## 3. Input files

Main input files used so far:

- עותק של DATA_04.26_LIMOR.xlsx
- output/label_device_map.csv
- output/cognitive_master/*
- output/analysis_candidates/*
- output/sql_catalog/*

Primary cognitive input:

- עותק של DATA_04.26_LIMOR.xlsx

## 4. Cognitive master table stage

Script:

- build_master_cognitive_table.py

What it does:

- Reads the processed Limor NeuroTrax workbook.
- Uses subjects sheet as base table.
- Merges cognitive sheets:
  - Overall scores
  - Memory
  - EF
  - Attention
  - Processing speed
  - Verbal Fun
  - Motor
- Preserves Subject_ID_D as string with leading zeros.
- Converts numeric cognitive columns.
- Captures FP/DI/NA/N/A codes into long-format flags.
- Removes pure empty artifact rows.
- Keeps real subjects with missing Subject_ID_D if they have cognitive data.
- Drops fully empty artifact col_* columns.
- Generates reports.

Current final status:

- master_cognitive_wide.csv has 83 rows and 112 columns.
- Subject_ID_N is unique for all 83 subjects.
- One empty artifact row was removed.
- Subject_ID_N=6 is a real subject with missing Subject_ID_D and is preserved.
- subjects_missing_device_label_id.csv reports this subject.
- Special code flags include only actual codes:
  - DI = 106
  - FP = 75
- delta_consistency_report.csv has 0 mismatches.

Outputs:

- output/cognitive_master/master_cognitive_wide.csv
- output/cognitive_master/cognitive_code_flags_long.csv
- output/cognitive_master/cognitive_data_dictionary.csv
- output/cognitive_master/delta_consistency_report.csv
- output/cognitive_master/README_cognitive_master.md
- output/cognitive_master/subjects_missing_device_label_id.csv

## 5. Cognitive QC stage

Script:

- qc_cognitive_master.py

Checks:

- Subject_ID_N uniqueness.
- Subject_ID_D string preservation and leading zeros.
- Missingness by column.
- Subject-level completeness.
- Special code summaries.
- Suspicious subject rows.

Current QC status:

- 83 rows.
- 83 unique Subject_ID_N values.
- 21 subjects below 50% cognitive completeness.
- 20 suspicious/low-completeness rows remain, but these are not blockers for the current top10 PoC.
- Subject_ID_N=6 has missing Subject_ID_D and limited cognitive data.

Outputs:

- output/cognitive_master/qc_missingness_report.csv
- output/cognitive_master/qc_subject_completeness.csv
- output/cognitive_master/qc_special_code_summary.csv
- output/cognitive_master/qc_suspicious_subject_rows.csv

## 6. Cognitive candidates and top10 stage

Script:

- build_analysis_cognitive_candidates.py

Purpose:

Creates a clean analysis candidate table from the cognitive master.

Extracted outcomes:

- global_T1 / global_T2 / global_delta
- memory_T1 / memory_T2 / memory_delta
- ef_T1 / ef_T2 / ef_delta
- attention_T1 / attention_T2 / attention_delta
- processing_speed_T1 / processing_speed_T2 / processing_speed_delta
- verbal_T1 / verbal_T2 / verbal_delta
- motor_T1 / motor_T2 / motor_delta
- iq_T1 / iq_T2 / iq_delta

Also keeps:

- Initials
- Subject_ID_N
- Subject_ID_D
- age
- Gender
- Education
- T1 date
- T2 date
- Time lap

Derived ranking columns:

- global_decline_amount = -global_delta
- abs_global_delta = abs(global_delta)

Current status:

- number_of_candidate_subjects = 83
- number_with_non_missing_global_delta = 62
- number_with_valid_T1_and_T2_dates = 62
- top10_global_decline.csv created
- top10_global_abs_change.csv created
- top10 missing Subject_ID_D = False
- top10 includes some FP/DI flags, but those are not automatic exclusions.

Outputs:

- output/analysis_candidates/cognitive_candidates_all.csv
- output/analysis_candidates/top10_global_decline.csv
- output/analysis_candidates/top10_global_abs_change.csv

## 7. Time window QC stage

Scripts:

- build_analysis_cognitive_candidates.py
- qc_analysis_candidates_time_windows.py

Notes:

- Excel serial dates are converted to real dates.
- Timezone is Asia/Jerusalem.
- SQL timestamps are Unix milliseconds.
- Date windows are calculated using local calendar dates, not absolute 7*24h subtraction, to avoid DST bugs.

Windows:

- T1_start_ms / T1_end_ms
- T2_start_ms / T2_end_ms
- early_window_start_ms / early_window_end_ms
- late_window_start_ms / late_window_end_ms

Current QC status:

- invalid_ms_range_count = 0
- T2_before_T1_count = 0
- early_late_overlap_count = 0
- top10_subjects_with_valid_windows = 10

Important fixed bug:

- A DST issue caused late_window_start_iso for Subject_ID_N=13 to appear as 01:00.
- It was fixed to local midnight:
  - late_window_start_iso = 2025-10-22 00:00:00+0300
  - late_window_end_iso = 2025-10-29 00:00:00+0200

Outputs:

- output/analysis_candidates/qc_time_window_issues.csv
- output/analysis_candidates/top10_global_decline_time_windows_preview.csv

## 8. Top10 subject-device episode mapping

Script:

- build_top10_device_episode_map.py

Purpose:

- Links top10_global_decline.csv to output/label_device_map.csv.
- Matches Subject_ID_D to label.
- Splits semicolon-separated device_ids.
- Creates one row per subject-device episode.
- Multiple device IDs are expected and treated as multiple device episodes for the same subject.

Current status:

- number_of_top10_subjects = 10
- number_matched_to_label_device_map = 10
- number_without_label_match = 0
- number_with_no_device_ids = 0
- total_device_episodes = 22
- subjects_with_multiple_device_ids = 8

Outputs:

- output/analysis_candidates/top10_subject_device_episodes.csv
- output/analysis_candidates/top10_subject_device_summary.csv

## 9. SQL / SensorDB inventory and JSON discovery stage

Script:

- discover_sensordb_inventory_and_json_keys.py

Purpose:

A lightweight reconnaissance step before feature extraction.

Created:

- database inventory
- table inventory
- column inventory
- JSON key catalog
- sample values
- README

Current findings:

- Schemas found:
  - information_schema
  - performance_schema
  - sensordata

- sensordata contains 44 tables.

Largest tables by approximate total size include:

- rotation ~1,655,390 MB
- accelerometer ~1,597,214 MB
- gyroscope ~1,550,461 MB
- gravity ~1,549,822 MB
- light ~261,053 MB
- linear_accelerometer ~211,844 MB
- magnetometer ~134,914 MB
- proximity ~28,958 MB
- aware_log ~18,395 MB
- barometer ~7,706 MB
- touch ~1,991 MB
- keyboard ~1,819 MB
- wifi ~1,427 MB

High-frequency tables postponed:

- accelerometer
- gravity
- gyroscope
- linear_accelerometer
- magnetometer
- rotation

Operational sensor_* tables ignored.

Tables successfully sampled for JSON keys:

- applications_foreground
- aware_device
- aware_log
- battery
- calls
- gsm
- gsm_neighbor
- keyboard
- locations
- messages
- plugin_google_activity_recognition
- screen
- telephony
- touch
- wifi

Tables with no sampled rows in top10 T1-T2 windows:

- battery_charges
- battery_discharges
- bluetooth
- network
- network_traffic
- timezone

Tables that caused MySQL lost connection during discovery:

- light
- proximity
- barometer

Outputs:

- output/sql_catalog/database_inventory.csv
- output/sql_catalog/table_inventory.csv
- output/sql_catalog/column_inventory.csv
- output/sql_catalog/json_key_catalog.csv
- output/sql_catalog/json_sample_values.json
- output/sql_catalog/README_sql_catalog.md

## 10. Manual confirmation of heavy/error tables

One manual row was inspected for each heavy/error table.

light:

Example key:

- double_light_lux

Interpretation:

- ambient light in lux
- possible circadian/day-night exposure proxy
- but low light can mean phone in pocket/bag

Status:

- optional_later
- not used in first PoC extraction unless explicitly requested

proximity:

Example key:

- double_proximity

Interpretation:

- proximity sensor value, likely phone near/covered state
- device-dependent

Status:

- optional_later
- requires distribution check and safe day-level probing

barometer:

Example key:

- double_values_0

Interpretation:

- likely atmospheric pressure in hPa/mbar
- possible weak environment/altitude proxy

Status:

- later_low_priority

These were added to the SQL catalog and feature dictionary manually without querying SQL again.

## 11. SQL feature dictionary stage

Created files:

- output/sql_catalog/sql_table_interpretation.csv
- output/sql_catalog/sql_feature_dictionary.csv
- output/sql_catalog/README_sql_feature_dictionary.md

Notes:

This is a first-pass feature dictionary based on discovered JSON keys and manual confirmations.

Core PoC candidate tables:

- screen
- battery
- wifi
- locations
- applications_foreground
- calls
- messages
- keyboard
- touch
- plugin_google_activity_recognition
- gsm
- gsm_neighbor
- telephony
- aware_log

Optional/later tables:

- light
- proximity
- barometer

Postponed high-frequency tables:

- accelerometer
- linear_accelerometer
- gyroscope
- rotation
- gravity
- magnetometer

## 12. Recommended next step

Next script:

- scan_top10_sql_coverage.py

Purpose:

For each of the 22 top10 device episodes, check whether data exists in each relevant SQL table and each analysis window.

This should still be coverage only, not feature extraction.

Input:

- output/analysis_candidates/top10_subject_device_episodes.csv
- DB connection helper connect_sensordata_db from main.py

Suggested tables for coverage scan:

- aware_log
- battery
- screen
- wifi
- calls
- messages
- locations
- applications_foreground
- keyboard
- touch
- gsm
- gsm_neighbor
- telephony
- plugin_google_activity_recognition

Do not include in first coverage scan:

- accelerometer
- linear_accelerometer
- gyroscope
- rotation
- gravity
- magnetometer
- sensor_* tables
- light
- proximity
- barometer unless explicitly requested

Windows:

- early_window
- late_window
- full_T1_T2_window

For each subject/device/table/window compute:

- n_rows
- first_timestamp_ms
- last_timestamp_ms
- first_day_local
- last_day_local
- n_days_with_data
- coverage_status

Coverage status values:

- ok_has_data
- ok_no_data
- missing_device_id
- missing_time_window
- table_error

Outputs should be:

- output/analysis_candidates/sql_coverage/top10_sql_coverage_long.csv
- output/analysis_candidates/sql_coverage/top10_sql_coverage_summary_by_subject.csv
- output/analysis_candidates/sql_coverage/top10_sql_coverage_summary_by_table.csv
- output/analysis_candidates/sql_coverage/README_sql_coverage.md

## 13. Important warnings for tomorrow

- Do not interpret missing rows as zero activity.
- Always report data availability.
- Always filter SQL by both device_id and timestamp.
- Avoid querying huge tables without narrow time windows.
- Treat multiple device IDs as device episodes.
- Do not start feature extraction until coverage is known.
- Do not use correlations on n=10 as confirmatory statistics; this PoC is exploratory only.

Tomorrow checklist:

1. Confirm README_CURRENT_PROJECT_STATUS.md is updated.
2. Optionally patch table_inventory.csv with manual_confirmed_key for light/proximity/barometer if not already done.
3. Build scan_top10_sql_coverage.py.
4. Run coverage scan on core PoC tables only.
5. Review which tables have usable early/late/full-window data.
6. Only then decide which first digital phenotype features to extract.
