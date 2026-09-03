# Plugin Activity Movement Timestamp Dictionary

This is the first timestamp-level movement-context dictionary for the mapped active cohort. It is based on the SQL table `plugin_google_activity_recognition` and is intended to guide later raw accelerometer extraction.

## Protocol

- Cohort: patients with a T1 date in `cognitive_candidates_all.csv`, excluding subject `001` under the existing project rule.
- Mapping: only device IDs from `output/label_device_map.csv` are queried.
- Time interval: local midnight at T1, inclusive, through local midnight at T2, exclusive.
- Patients without a valid ordered T2 are retained in the cohort accounting but are not assigned an artificial movement interval.
- SQL is bounded by one mapped `device_id` and the patient-specific T1-to-T2 interval.
- Every valid SQL row is retained in the event dictionary. The full JSON payload is not copied; primary label, activity type, confidence, and nested candidate labels are retained.
- UTC minutes are used as the unambiguous time key; local timestamps are included for review.
- Confidence >= 70 is marked high confidence. Events are not removed because of low confidence.

## Movement classes

- `active_land`: `on_foot`, `walking`, `running`, or bicycle labels.
- `vehicle`: `in_vehicle` labels.
- `still`: `still`.
- `orientation_change`: `tilting`; this is not treated as walking or body movement.
- `unknown`: `unknown`, missing labels, or unparsable payloads.
- `other`: any other primary activity label.

This is phone-derived activity context, not a direct measure of patient movement. It may reflect phone carrying, placement, operating-system recognition, and collection intensity. Missing plugin rows mean no observed activity-recognition event, not confirmed stillness.

## Current extraction state

- Active patients in source cohort: 1
- Mapped devices for active cohort: 2
- Completed device intervals recorded: 2
- Failed device intervals recorded: 0
- Raw event rows in completed intervals: 13
- Valid primary-label rows: 13

## Outputs

- `plugin_activity_movement_events.csv`: one row per plugin event, with raw primary label and derived movement class.
- `plugin_activity_movement_minutes.csv`: one row per patient-device UTC minute containing event counts and movement-context class.
- `plugin_activity_device_day_summary.csv`: device-day coverage and label totals.
- `plugin_activity_patient_day_summary.csv`: patient-day aggregation across mapped devices.
- `plugin_activity_extraction_status.csv`: interval-level row counts, parse quality, and errors.
- `plugin_activity_dictionary_cohort_summary.csv`: current cohort-level extraction accounting.
- `plugin_activity_dictionary_checkpoint.json`: completed device intervals for resumable execution.

## Planned investigation before accelerometer extraction

1. Check how many patients have plugin events, the number of observed days, and the distribution of event density.
2. Check whether activity classes and confidence are stable across devices and dates.
3. Use the minute dictionary to select short ACC windows with explicit movement-context labels.
4. Start raw general-ACC extraction only for mapped devices and selected windows, preserving sensor configuration metadata.

This dictionary is exploratory and should not be interpreted as a validated clinical digital biomarker.
