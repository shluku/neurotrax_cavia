# Dementia / NeuroTrax + SensorDB Project Status — Phase 1

## 1. Project goal

This project links NeuroTrax cognitive data with SensorDB digital phenotyping data.

Main goals:

1. Characterize patients by their early/baseline digital phenotype.
2. Explore whether digital phenotype changes over time correspond to cognitive changes/deltas.

Current PoC:

- Focuses on the 10 subjects with the largest global cognitive decline.
- Baseline digital phenotype is currently feasible for 8/10 subjects.
- Early-vs-late digital change analysis is currently feasible for 2/10 subjects: 024 and 077.
- This is exploratory only, not confirmatory statistics.

## 2. Core principles

- Missing data is not zero activity.
- no_data windows must remain NaN/missing, not 0.0.
- Data availability is part of the analysis and must be reported.
- SQL must always be filtered by device_id and timestamp.
- Date windows use local calendar days in Asia/Jerusalem.
- SQL timestamps are Unix milliseconds.
- Many subjects have multiple device_ids due to repeated app installations.
- Multiple device_ids are treated as device episodes belonging to the same subject.
- High-frequency/heavy tables are postponed:
  - accelerometer
  - linear_accelerometer
  - gyroscope
  - rotation
  - gravity
  - magnetometer
- sensor_* tables are operational and ignored for analysis.
- aware_log is data-quality/system-logging only, not a behavioral phenotype endpoint.

## 3. Cognitive data preparation

Script:

- build_master_cognitive_table.py

Inputs:

- עותק של DATA_04.26_LIMOR.xlsx

What it did:

- Built master cognitive table from NeuroTrax workbook.
- Used subjects sheet as base.
- Merged:
  - Overall scores
  - Memory
  - EF
  - Attention
  - Processing speed
  - Verbal Fun
  - Motor
- Preserved Subject_ID_D as string with leading zeros.
- Captured FP/DI/NA/N/A flags.
- Removed one pure empty artifact row.
- Kept real subject with missing Subject_ID_D if cognitive data existed.

Final status:

- master_cognitive_wide.csv shape: 83 rows × 112 columns.
- Subject_ID_N unique for all 83 subjects.
- Subject_ID_N=6 preserved despite missing Subject_ID_D.
- DI flags: 106
- FP flags: 75
- delta_consistency_report.csv had 0 mismatches.

Outputs:

- output/cognitive_master/master_cognitive_wide.csv
- output/cognitive_master/cognitive_code_flags_long.csv
- output/cognitive_master/cognitive_data_dictionary.csv
- output/cognitive_master/delta_consistency_report.csv
- output/cognitive_master/README_cognitive_master.md
- output/cognitive_master/subjects_missing_device_label_id.csv

## 4. Cognitive QC

Script:

- qc_cognitive_master.py

Outputs:

- output/cognitive_master/qc_missingness_report.csv
- output/cognitive_master/qc_subject_completeness.csv
- output/cognitive_master/qc_special_code_summary.csv
- output/cognitive_master/qc_suspicious_subject_rows.csv

Current QC:

- 83 rows.
- 83 unique Subject_ID_N values.
- 21 subjects below 50% cognitive completeness.
- 20 suspicious/low-completeness rows remain but are not blockers for the current top10 PoC.

## 5. Cognitive candidates and top10

Script:

- build_analysis_cognitive_candidates.py

Created:

- output/analysis_candidates/cognitive_candidates_all.csv
- output/analysis_candidates/top10_global_decline.csv
- output/analysis_candidates/top10_global_abs_change.csv

Extracted cognitive columns:

- global_T1 / global_T2 / global_delta
- memory_T1 / memory_T2 / memory_delta
- ef_T1 / ef_T2 / ef_delta
- attention_T1 / attention_T2 / attention_delta
- processing_speed_T1 / processing_speed_T2 / processing_speed_delta
- verbal_T1 / verbal_T2 / verbal_delta
- motor_T1 / motor_T2 / motor_delta
- iq_T1 / iq_T2 / iq_delta

Current status:

- number_of_candidate_subjects = 83
- number_with_non_missing_global_delta = 62
- number_with_valid_T1_and_T2_dates = 62
- top10_global_decline.csv created.
- top10_global_abs_change.csv created.
- top10 missing Subject_ID_D = False.
- top10 includes some FP/DI flags, but these are not automatic exclusions.

## 6. Time windows

Scripts:

- build_analysis_cognitive_candidates.py
- qc_analysis_candidates_time_windows.py

Important:

- Excel serial dates converted to real dates.
- Timezone: Asia/Jerusalem.
- SQL timestamps: Unix milliseconds.
- Windows calculated by local calendar dates, not naive 7×24h subtraction, to avoid DST bugs.

Windows:

- early_window = T1 date to T1 + 7 calendar days
- late_window = T2 - 7 calendar days to T2 date
- full_T1_T2_window = T1 to T2, but not used for current feature extraction due query size

QC:

- invalid_ms_range_count = 0
- T2_before_T1_count = 0
- early_late_overlap_count = 0
- top10_subjects_with_valid_windows = 10

Important fixed bug:

- Subject_ID_N=13 had DST drift causing late_window_start_iso to appear as 01:00.
- Fixed to local midnight:
  - late_window_start_iso = 2025-10-22 00:00:00+0300
  - late_window_end_iso = 2025-10-29 00:00:00+0200

Outputs:

- output/analysis_candidates/qc_time_window_issues.csv
- output/analysis_candidates/top10_global_decline_time_windows_preview.csv

## 7. Top10 subject-device episodes

Script:

- build_top10_device_episode_map.py

What it does:

- Links top10_global_decline.csv to output/label_device_map.csv.
- Matches Subject_ID_D to label.
- Splits semicolon-separated device_ids.
- Creates one row per subject-device episode.
- Preserves all time-window columns.

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

Current top10_subject_device_episodes.csv shape:

- 22 rows × 29 columns

## 8. SensorDB inventory and JSON discovery

Script:

- discover_sensordb_inventory_and_json_keys.py

Purpose:

- Lightweight SQL reconnaissance before feature extraction.

Created:

- output/sql_catalog/database_inventory.csv
- output/sql_catalog/table_inventory.csv
- output/sql_catalog/column_inventory.csv
- output/sql_catalog/json_key_catalog.csv
- output/sql_catalog/json_sample_values.json
- output/sql_catalog/README_sql_catalog.md

Findings:

- sensordata contains 44 tables.

Largest tables approximately:

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

sensor_* tables:

- operational ingestion tables, ignored.

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

Manual confirmation for heavy/error tables:

- light:
  - key: double_light_lux
  - ambient light in lux
  - optional_later
- proximity:
  - key: double_proximity
  - proximity sensor value
  - optional_later
- barometer:
  - key: double_values_0
  - likely atmospheric pressure
  - later_low_priority

## 9. SQL feature dictionary and phase-1 shortlist

Created:

- output/sql_catalog/sql_table_interpretation.csv
- output/sql_catalog/sql_feature_dictionary.csv
- output/sql_catalog/README_sql_feature_dictionary.md

Shortlist files:

- output/analysis_candidates/sql_coverage/phase1_feature_table_shortlist.csv
- output/analysis_candidates/sql_coverage/README_phase1_feature_table_shortlist.md

Final Phase 1 shortlisted tables:

Core phenotype:

- screen
- applications_foreground
- keyboard
- touch
- plugin_google_activity_recognition

Optional/context:

- gsm
- gsm_neighbor
- telephony
- messages

Data quality only:

- aware_log

Excluded from Phase 1:

- battery: no meaningful early/late rows in current top10 coverage
- wifi: no meaningful early/late rows in current top10 coverage
- locations: very sparse in current top10 coverage
- calls: no meaningful early/late rows
- light/proximity/barometer: deferred for DB safety/manual later
- high-frequency motion tables: postponed
- sensor_*: operational, ignored

## 10. SQL coverage

Script:

- scan_top10_sql_coverage.py

Outputs:

- output/analysis_candidates/sql_coverage/top10_sql_coverage_long.csv
- output/analysis_candidates/sql_coverage/top10_sql_coverage_summary_by_subject.csv
- output/analysis_candidates/sql_coverage/top10_sql_coverage_summary_by_table.csv
- output/analysis_candidates/sql_coverage/top10_sql_coverage_early_late_summary.csv
- output/analysis_candidates/sql_coverage/README_sql_coverage.md

Important:

- early/late coverage scan completed successfully.
- No real DB errors.
- full_T1_T2_window intentionally skipped if span >45 days.

Final coverage metrics:

- total_device_episodes_scanned = 22
- total_queries_attempted = 924
- total_real_table_errors = 0
- total_skipped_long_full_window = 308
- early_late_queries_attempted = 616
- early_late_real_table_errors = 0

Top tables by early+late n_rows:

- aware_log 348082
- touch 47620
- applications_foreground 26873
- gsm_neighbor 15875
- keyboard 14704
- plugin_google_activity_recognition 12501
- screen 8560
- telephony 8302
- gsm 8223
- messages 319

Coverage groups:

- early_and_late_data: 2
- early_only: 6
- late_only: 1
- no_early_or_late_data: 1

## 11. Coverage readiness

Script:

- summarize_top10_coverage_readiness.py

Outputs:

- output/analysis_candidates/sql_coverage/top10_subject_readiness.csv
- output/analysis_candidates/sql_coverage/top10_table_readiness.csv
- output/analysis_candidates/sql_coverage/top10_subject_table_coverage_matrix.csv
- output/analysis_candidates/sql_coverage/README_top10_coverage_readiness.md

Key results:

- Baseline-ready subjects:
  - 001
  - 024
  - 030
  - 062
  - 077
  - 087
  - 093
  - 095

- Change-analysis-ready subjects:
  - 024
  - 077

## 12. Phase 1 JSON value distribution review

Script:

- inspect_phase1_json_value_distributions.py

Outputs:

- output/analysis_candidates/phase1_features/phase1_json_value_distribution_review.csv
- output/analysis_candidates/phase1_features/README_phase1_json_value_distribution_review.md

Safe/interpretable keys:

- screen:
  - screen_status
  - timestamp
- applications_foreground:
  - package_name
  - application_name
  - timestamp
  - is_system_app
- plugin_google_activity_recognition:
  - activity_name
  - activity_type
  - activities
  - confidence
  - timestamp
- messages:
  - message_type
  - timestamp, with code-mapping caution
- telephony:
  - network_type
  - sim_state
  - phone_type
  - data_enabled
  - timestamp
- gsm/gsm_neighbor:
  - cid
  - lac
  - psc
  - signal_strength
  - timestamp
- aware_log:
  - log_message
  - timestamp, data-quality use only

Manual review / caution:

- privacy identifiers:
  - telephony.subscriber_id
  - line_number
  - imei_meid_esn
  - sim_serial
  - many device_id keys
- keyboard raw text:
  - current_text
  - before_text
- messages.trace
- touch.scroll_* and touch_action_text need caution

Important:

- Do not use raw keyboard text fields.
- Do not use incoming/outgoing message splits until message_type mapping is validated.
- Do not use aware_log as direct phenotype.

## 13. Phase 1A extraction: screen/app/aware_log

Script:

- extract_phase1a_screen_app_log_features.py

Tables:

- screen
- applications_foreground
- aware_log

Windows:

- early_window
- late_window

Outputs:

- output/analysis_candidates/phase1_features/extracted/phase1a_device_window_features.csv
- output/analysis_candidates/phase1_features/extracted/phase1a_subject_window_features.csv
- output/analysis_candidates/phase1_features/extracted/phase1a_subject_features_wide.csv
- output/analysis_candidates/phase1_features/extracted/README_phase1a_extraction.md

Summary:

- number_of_subjects_extracted = 10

Screen:

- early subjects with data = 8
- late subjects with data = 2
- both early+late = 1

Applications foreground:

- early subjects with data = 8
- late subjects with data = 2
- both early+late = 1

Aware log:

- early subjects with data = 8
- late subjects with data = 2
- both early+late = 2

## 14. Phase 1A QC

Script:

- qc_phase1a_extracted_features.py

Outputs:

- output/analysis_candidates/phase1_features/extracted/qc_phase1a_feature_summary.csv
- output/analysis_candidates/phase1_features/extracted/qc_phase1a_subject_usability.csv
- output/analysis_candidates/phase1_features/extracted/qc_phase1a_issues.csv
- output/analysis_candidates/phase1_features/extracted/README_qc_phase1a.md

Final QC:

- number_of_qc_issues = 0

Baseline-usable subjects:

- 001
- 024
- 030
- 062
- 077
- 087
- 093
- 095

Change-usable subjects with aware_log support:

- 024

## 15. Phase 1B extraction: keyboard/touch/activity

Script:

- extract_phase1b_interaction_activity_features.py

Tables:

- keyboard
- touch
- plugin_google_activity_recognition

Windows:

- early_window
- late_window

Privacy:

- Keyboard raw text fields such as current_text and before_text were not saved or output.
- Privacy validation later passed.

Important patch:

- Initial Phase 1B wide outputs encoded no_data as 0.0, which was wrong.
- The script was patched so no_data/missing windows remain NaN.
- Subject_ID_D zero-padding preserved.
- Delta/pct_change computed only when both early and late are non-missing.

Outputs:

- output/analysis_candidates/phase1_features/extracted/phase1b_device_window_features.csv
- output/analysis_candidates/phase1_features/extracted/phase1b_subject_window_features.csv
- output/analysis_candidates/phase1_features/extracted/phase1b_subject_features_wide.csv
- output/analysis_candidates/phase1_features/extracted/README_phase1b_extraction.md

Final extraction summary:

- subjects extracted = 10

Keyboard:

- early = 8
- late = 2
- both = 1

Touch:

- early = 8
- late = 0
- both = 0

Activity recognition:

- early = 8
- late = 2
- both = 2

## 16. Phase 1B QC

Script:

- qc_phase1b_extracted_features.py

Outputs:

- output/analysis_candidates/phase1_features/extracted/qc_phase1b_feature_summary.csv
- output/analysis_candidates/phase1_features/extracted/qc_phase1b_subject_usability.csv
- output/analysis_candidates/phase1_features/extracted/qc_phase1b_issues.csv
- output/analysis_candidates/phase1_features/extracted/README_qc_phase1b.md

Final QC after patch/rerun:

- number_of_qc_issues = 0
- privacy validation = PASS
- no_data primary event counts are NaN, not 0.0
- delta_status_mismatch resolved
- Subject_ID_D zero-padding preserved

Baseline-usable subjects:

- 001
- 024
- 030
- 062
- 077
- 087
- 093
- 095

Change-usable subjects:

- 024
- 077

## 17. Merged Phase 1 digital phenotype table

Script:

- merge_phase1a_phase1b_features.py

Inputs:

- phase1a_subject_features_wide.csv
- phase1b_subject_features_wide.csv
- qc_phase1a_subject_usability.csv
- qc_phase1b_subject_usability.csv
- top10_global_decline.csv
- top10_subject_readiness.csv

Outputs:

- output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide.csv
- output/analysis_candidates/phase1_features/extracted/phase1_subject_usability_summary.csv
- output/analysis_candidates/phase1_features/extracted/README_phase1_digital_phenotype.md

Final merge results:

- final_merged_shape = (10, 56)
- number_of_feature_columns = 37

Baseline-usable subjects:

- 030
- 001
- 062
- 024
- 087
- 077
- 093
- 095

Change-usable subjects:

- 024
- 077

Main feature families included:

- screen
- applications_foreground
- aware_log, data-quality only
- keyboard
- touch
- activity_recognition

Important:

- No SQL was queried during merge.
- No new features were extracted during merge.
- Missing values were not force-filled.
- no_data remains NaN.

## 18. Current final outputs to use tomorrow

Main file for tomorrow:

- output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide.csv

Usability summary:

- output/analysis_candidates/phase1_features/extracted/phase1_subject_usability_summary.csv

Feature/QC references:

- output/analysis_candidates/phase1_features/extracted/README_phase1_digital_phenotype.md
- output/analysis_candidates/phase1_features/extracted/README_qc_phase1a.md
- output/analysis_candidates/phase1_features/extracted/README_qc_phase1b.md
- output/analysis_candidates/phase1_features/phase1_json_value_distribution_review.csv
- output/analysis_candidates/phase1_features/phase1_feature_plan.csv
- output/analysis_candidates/sql_coverage/README_top10_coverage_readiness.md

## 19. Recommended next steps for tomorrow

Do not start with new SQL.

Suggested next step:
Create a descriptive Phase 1 digital phenotype profiling report from:

- phase1_digital_phenotype_wide.csv
- phase1_subject_usability_summary.csv
- top10_global_decline.csv

Possible script:

- describe_phase1_digital_phenotype_profiles.py

Goals:

1. Summarize baseline digital phenotype for the 8 baseline-usable subjects.
2. Show cognitive decline alongside early digital features.
3. Identify descriptive patterns only.
4. Create subject-level profile cards/tables.
5. Explore early-vs-late changes only for 024 and 077.
6. Do not run confirmatory statistics.
7. Do not interpret missing as zero.
8. Keep aware_log as data-quality only.

Possible outputs:

- phase1_baseline_profile_summary.csv
- phase1_change_profile_summary_024_077.csv
- phase1_subject_profile_cards.md
- README_phase1_descriptive_profiles.md

After that:

- consider Phase 1C optional/context extraction:
  - gsm
  - gsm_neighbor
  - telephony
  - messages
- but only after reviewing the descriptive value of the current merged Phase 1 table.

## 20. Important warnings

- n=10 top decline subjects only.
- baseline usable n=8.
- change usable n=2.
- This is a PoC/exploratory pipeline.
- Do not use correlations or p-values as confirmatory evidence.
- Missing data is a result, not just a nuisance.
- Avoid adding too many features before interpreting the current ones.
- Do not use raw keyboard text or private identifiers.
- Do not query heavy/high-frequency tables unless a separate safe strategy is designed.
- Do not run full_T1_T2_window scans directly on large tables.
- Always preserve Subject_ID_D leading zeros.

## 21. Quick “start tomorrow” checklist

1. Open README_CURRENT_PROJECT_STATUS_PHASE1.md.
2. Confirm main file exists: output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide.csv
3. Inspect the first rows and columns of the merged phenotype table.
4. Create descriptive profile summary, not new extraction.
5. Focus on baseline phenotype for 8 subjects.
6. Handle change analysis only for 024 and 077.
7. Keep all conclusions exploratory.
8. Only after descriptive profiling, decide whether to extract Phase 1C context/social tables.
