# Phase 2 Feature Analysis Protocol

## Purpose

This protocol defines how we manually inspect one SensorDB table at a time before deciding which digital biomarker features to extract.

Table-specific reviews are stored separately in:

```text
phase2_table_feature_reviews/
```

The first reviewed table is:

- `applications_foreground`

## Main Rule

Before feature extraction, inspect a small number of raw rows from a safe device/time window and understand:

- What columns exist.
- What JSON keys exist.
- Which values are behavioral.
- Which values are data-quality only.
- Which values are identifiers or raw fields that should not become direct phenotype features.
- Which candidate features are scientifically meaningful.
- Which candidate features are technically reliable.

## SQL Safety Rules

- Do not query full tables.
- Do not query full T1-to-T2 windows.
- For manual table-understanding samples, first find a device with enough rows, then sample only that device with a small `LIMIT`.
- For clinical feature review/extraction, prefer existing top-10 subject/device early and late windows.
- Feature-review samples and extraction queries should filter by `device_id`.
- Clinical-window queries should always filter by both `device_id` and `timestamp`.
- Use parameterized values for `device_id`, `start_ms`, and `end_ms`.
- Use whitelisted table names from `SHOW TABLES`.
- Use `ORDER BY timestamp ASC`.
- Use a small `LIMIT`.

## Phase A / Phase B Table Review Method

The protocol has two phases. Phase A is only for manually inspecting 20 raw rows. Phase B is for deciding and later extracting project features after the table is understood.

### Phase A: Manual Inspection of 20 Raw Rows

Use this phase first for every new table.

Goal:

- Inspect exactly 20 chronological raw records when available.
- Understand the raw table structure and JSON keys.
- Understand what one table row means.
- Start thinking about which fields may be behavioral, technical, or data-quality only.
- Do not extract patient-level features yet.
- Do not aggregate.
- Do not calculate feature values.
- Do not make clinical conclusions.

Patient selection:

- Use `output/analysis_candidates/cognitive_candidates_all.csv`.
- Convert `global_T1` to numeric.
- Select the patient with the highest numeric `global_T1`.
- If ties occur, choose deterministically by lowest `Subject_ID_D`.
- Use mapped device IDs from `output/label_device_map.csv`.

Window rule:

- Primary start: local midnight on the day after `T1_date_iso`.
- Timezone: Asia/Jerusalem.
- Primary end: primary start + 24 continuous hours.
- Check the table across the highest-T1 patient's mapped device IDs.
- If there are at least 20 rows in the primary window, sample the first 20 chronological raw rows from that window.
- If the primary window does not have enough rows, scan downward by `global_T1` until a patient/device has a protocol-valid window.
- Fallback start: first observed table timestamp that allows a complete 24-hour span inside that patient's T1 week.
- Fallback end: fallback start + 24 continuous hours.
- The fallback window must be marked as `exploratory_fallback_first_24h_span_within_T1_week` and not described as true day-after-T1 behavior.

Primary coverage query:

```sql
SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
FROM `{table_name}`
WHERE device_id = %s
  AND timestamp >= %s
  AND timestamp < %s;
```

Fallback first-row query:

```sql
SELECT MIN(timestamp) AS first_ts
FROM `{table_name}`
WHERE device_id = %s;
```

Sample query:

```sql
SELECT *
FROM `{table_name}`
WHERE device_id = %s
  AND timestamp >= %s
  AND timestamp < %s
ORDER BY timestamp ASC
LIMIT %s;
```

For Phase A, the default sample is 20 rows. Larger samples should be used only if the first 20 rows are not enough to understand the raw table structure.

Outputs:

- `<table_name>_sample_rows.csv`
- `<table_name>_sample_rows.jsonl`
- `<table_name>_sample_rows_expanded.csv`
- `<table_name>_json_key_summary.csv`
- `README_<table_name>_feature_review.md`

Inspection format:

- Raw `data` JSON should be preserved unchanged in `<table_name>_sample_rows.csv`.
- A second expanded file should also be created when the table has JSON data:
  - `<table_name>_sample_rows_expanded.csv`
- The expanded file should keep core columns such as `_id`, `timestamp`, `local_datetime`, and `device_id`.
- Each top-level JSON key should be shown as its own column for manual inspection.
- This expanded file is for readability only. It is not feature extraction.
- Raw values may be shown in expanded inspection views for authorized Helsinki-approved project review.
- Raw identifiers should still not become direct phenotype features unless explicitly selected and justified; prefer aggregate feature calculations for model-facing outputs.

Duplicate-heavy table rule:

- If the first raw inspection rows contain repeated copies of the same underlying observation, keep the raw sample but also create a distinct-observation inspection file.
- The distinct-observation file is for manual inspection only and does not replace the raw sample.
- The deduplication key must be documented for that table.
- For `bluetooth`, the current Phase A inspection deduplication key is:
  - `timestamp`
  - `device_id`
  - `bt_address`
  - `bt_rssi`
- For `bluetooth`, the distinct-observation file should be treated as the primary Phase A inspection view because raw rows can contain many duplicate database copies.
- For `bluetooth`, `bt_rssi` is currently the main candidate signal. `bt_name` and `bt_address` may be visible in authorized manual inspection tables, but they are currently used only for inspection/deduplication and are not selected phenotype outputs.
- For `locations`, the first raw Phase A sample can contain repeated copies of the same timestamp/location. Preserve the raw sample, but also create a distinct-observation inspection file using:
  - `timestamp`
  - `data`
- For `locations`, the distinct-observation file should be treated as the primary Phase A inspection view for feature decisions.
- For `messages`, raw rows can contain repeated copies of the same message event. Preserve the redacted raw sample, but also create a distinct-observation inspection file using:
  - `timestamp`
  - `trace`
  - `message_type`
- For `messages`, message body, address, phone-number-like fields, and contact identifiers must be redacted in review files. `message_type` may remain visible because it is a non-content event code.
- For `messages`, the distinct-observation file should be treated as the primary Phase A inspection view for feature decisions.
- For `touch`, raw rows can contain repeated database copies of the same touch event. Preserve the raw sample, but also create a distinct-observation inspection file using:
  - `timestamp`
  - `device_id`
  - `touch_app`
  - `touch_action`
  - `scroll_items`
  - `scroll_to_index`
  - `scroll_from_index`
  - `touch_action_text`
- For `touch`, the distinct-observation file should be treated as the primary Phase A inspection view for feature decisions.
- Save the distinct-observation file as:
  - `<table_name>_sample_rows_distinct_observations.csv`

If no ranked patient has a protocol-valid 24-hour T1-week window with enough rows, mark Phase A as unavailable for that table. Optionally, a separate "general table sanity sample" may be used later only to understand JSON keys, but it must be labeled as not clinically anchored and not used for patient-level interpretation.

High-frequency sensor table rule:

- Tables such as `linear_accelerometer`, `accelerometer`, `gyroscope`, and related `sensor_*` motion tables can be extremely large.
- For these tables, do not broaden SQL searches across long date ranges just to find rows.
- First apply the same protocol-valid T1-week 24-hour search.
- If no ranked patient has data in the T1-week protocol window, mark the table as `phase2_later_high_frequency_no_protocol_coverage`.
- Any later review of these tables should use a dedicated bounded script with strict query timeouts, one patient/device/window at a time.
- Fourier or frequency-domain features require a confirmed sampling pattern and a bounded continuous window. They should not be computed until:
  - the x/y/z acceleration columns or JSON keys are confirmed,
  - timestamps are inspected for sampling regularity,
  - duplicate rows are handled,
  - the signal is transformed into vector magnitude,
  - the signal is resampled or segmented consistently.
- Missing high-frequency sensor data remains missing. It is not interpreted as no movement.

### Phase B: Feature Decision and Clinical-Window Extraction

Use this phase only after Phase A is understood.

Goal:

- Choose candidate and selected features.
- Define exact calculations and interpretation limits.
- Record the manually selected features in `phase2_selected_features.csv`.
- Mark selected rows in `phase2_candidate_feature_plan.csv` using `selected_for_extraction=yes`.
- Update the table-specific review file in `phase2_table_feature_reviews/<table_name>.md` with a Selected Features section.
- The Streamlit table overview should then show the selected-feature count for that table.
- After Phase B runs, rebuild `phase2_highest_t1_calculated_feature_values.csv`.
- From now on, the Streamlit current feature-values table must use only the exploratory feature-finding acquisition rule:
  - scan patients in descending `global_T1` order,
  - skip explicitly excluded subjects with known mapping problems,
  - choose the first patient/device set with a valid 24-hour span inside that patient's T1 week for the reviewed table,
  - calculate only manually selected features,
  - label the rows `exploratory_t1_ranked_first_valid_24h_in_T1_week`,
  - include the selected patient ID, device IDs, T1 score, T1 date, and window timestamps in the overview.
- If no patient has a valid 24-hour span inside the T1 week, keep the selected feature rows in the overview with missing values and `feature_status=no_protocol_valid_patient_found`.
- Review-sample-only values must not be added to the current feature-values table.
- These exploratory rows are for feature-finding and Streamlit tracking. Later full-cohort extraction may still produce missing values for some patients.
- Current exploratory exclusion: Subject_ID_D `001` is skipped because its device mapping is not suitable for table-level exploration.
- Every calculated feature row must include the patient identifier and device identifier used for the calculation:
  - `Subject_ID_D`
  - `Subject_ID_N` when available
  - `device_id_used`
- Later extract selected features for baseline T1 and T1-to-T2 delta analysis.
- The current feature-finding search is not a full-cohort extraction and is not diagnostic.

Current command for rebuilding the highlighted calculated-value table:

```bash
.venv/bin/python3 build_phase2_highest_t1_calculated_feature_values.py
```

For each top-10 device episode and each early/late window, run:

```sql
SELECT
  COUNT(*) AS n_rows,
  MIN(timestamp) AS first_ts,
  MAX(timestamp) AS last_ts
FROM `{table_name}`
WHERE device_id = %s
  AND timestamp >= %s
  AND timestamp < %s;
```

Use this only on bounded top-10 windows. Do not use this query on the full table.

Select the first window with at least the minimum number of rows needed for manual review, usually 20.

If a bounded top-10 clinical window is selected for further review, pull chronological sample rows:

After selecting a device/window:

```sql
SELECT *
FROM `{table_name}`
WHERE device_id = %s
  AND timestamp >= %s
  AND timestamp < %s
ORDER BY timestamp ASC
LIMIT %s;
```

### JSON Inspection

For tables with a `data` JSON column, inspect:

- top-level JSON keys
- value types
- missing/empty keys
- categorical values
- numeric values
- raw identifier/string values

Raw values may be saved in manual review outputs under the project's Helsinki-approved review context. Model-facing feature outputs should still document exactly which raw fields were used and should preferentially store aggregate numeric features.

## Table-Specific Review Files

Each reviewed SensorDB table should get its own markdown file:

```text
phase2_table_feature_reviews/<table_name>.md
```

Each file should document:

- table meaning
- fields or JSON keys seen
- selected features
- candidate features not yet selected
- privacy notes
- current extraction prototype or Phase A status
- possible future derived features

Use `phase2_table_feature_reviews/applications_foreground.md` as the template for every reviewed table. The section order should remain:

1. Table Meaning
2. Fields Seen in `data`
3. Selected Features
4. Candidate Features Not Yet Selected
5. Privacy Notes
6. Current Extraction Prototype
7. Possible Future Derived Features

The current `applications_foreground` review is available at:

```text
phase2_table_feature_reviews/applications_foreground.md
```

## Selected Feature Extraction Prototype

The first extraction prototype used the selected `applications_foreground` features for the patient with the highest NeuroTrax overall/global T1 score. The same structure should now be reused for each reviewed table, with table-specific exceptions documented explicitly.

For each table, the feature definitions and interpretation notes must be documented in:

```text
phase2_table_feature_reviews/<table_name>.md
```

Exploratory feature-finding patient selection rule:

- Use `output/analysis_candidates/cognitive_candidates_all.csv`.
- Convert `global_T1` to numeric.
- Search patients from highest numeric `global_T1` to lowest numeric `global_T1`.
- If ties occur, choose deterministically by lowest `Subject_ID_D`.
- Require a mapped `Subject_ID_D` in `output/label_device_map.csv`.
- Skip explicitly excluded subjects, currently Subject_ID_D `001`.
- Stop at the first patient with a valid 24-hour acquisition window inside that patient's T1 week.
- If no patient has a valid 24-hour acquisition window, record selected feature rows as missing with `feature_status=no_protocol_valid_patient_found`.

Exploratory feature-finding acquisition window rule:

- Primary start: local midnight on the day after `T1_date_iso`.
- Timezone: Asia/Jerusalem.
- Primary end: primary start + 24 continuous hours.
- If there are no rows for the reviewed table across the patient's mapped device IDs in the primary window, use fallback.
- Fallback search interval: local midnight on `T1_date_iso` through 7 days later.
- Fallback start: first observed timestamp for the reviewed table across mapped device IDs that allows a complete 24-hour span inside that T1 week.
- Fallback end: fallback start + 24 continuous hours.
- If no complete 24-hour span can be found inside the T1 week, selected feature values remain missing.
- The fallback window must be marked as `exploratory_fallback_first_24h_span_within_T1_week` and not described as true day-after-T1 behavior.

SQL rule:

```sql
SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
FROM `{table_name}`
WHERE device_id = %s
  AND timestamp >= %s
  AND timestamp < %s;
```

Then, only for the selected 24-hour window:

```sql
SELECT *
FROM `{table_name}`
WHERE device_id = %s
  AND timestamp >= %s
  AND timestamp < %s
ORDER BY timestamp ASC;
```

Important interpretation rule:

- A missing primary window is missing data, not zero activity.
- The extracted features are based only on observed rows in the selected 24-hour window.

## Output Files for Each Table Review

Recommended output folder:

```text
output/analysis_candidates/phase2_feature_review/<table_name>/
```

Recommended files:

- `<table_name>_sample_rows.csv`
- `<table_name>_sample_rows.jsonl`
- `<table_name>_sample_rows_expanded.csv`
- `<table_name>_sample_rows_distinct_observations.csv` when a duplicate-heavy rule is needed
- `<table_name>_json_key_summary.csv`
- `<table_name>_global_device_coverage_summary.csv`
- `README_<table_name>_feature_review.md`

## Global Coverage Summary

For every reviewed table, Phase 2A should include a compact global coverage summary. This is a planning and data-availability support artifact, not feature extraction.

The summary should report:

- Devices with `<table_name>` rows
- Mapped study patients with `<table_name>` rows
- Mapped devices with rows
- Unmapped devices with rows
- Rows mapped to study patients
- Rows on unmapped devices

The summary should be written into:

```text
output/analysis_candidates/phase2_feature_review/<table_name>/<table_name>_global_device_coverage_summary.csv
```

and appended to:

```text
phase2_table_feature_reviews/<table_name>.md
```

SQL may use a global `GROUP BY device_id` for moderate tables. For very large high-frequency tables, if the query exceeds a safe execution limit, record the coverage status as an error/pending rather than running an unsafe long query. Missing coverage summary values must not be interpreted as zero activity.

## Accelerometer Framework

Accelerometer-family analysis should be staged rather than treating all motion tables as immediately model-facing.

Order:

1. Analyze `sensor_linear_accelerometer` first as a QC and device-context table.
2. Use that QC to decide whether `linear_accelerometer` can support phone-motion signal features.
3. Only after QC, define raw linear acceleration features from x/y/z values.

`sensor_linear_accelerometer` is not a behavior table. It provides Android sensor metadata such as sensor name, vendor, type, resolution, maximum range, power, and minimum delay. These values help document the hardware and sampling context before high-frequency signal analysis.

Current bounded QC rule:

- Use mapped T1 patients only.
- Exclude Subject_ID_D `001`.
- For each mapped device, find the first `sensor_linear_accelerometer` timestamp at or after T1.
- Build a bounded 7-day window from that first available timestamp.
- Query only that device/time window.
- Summarize metadata availability, active days/hours, timestamp intervals, gaps, sensor vendor/type, resolution, maximum range, power, minimum delay, and implied maximum sampling rate.

Outputs:

```text
output/analysis_candidates/phase2_accelerometer_framework/
```

Important interpretation:

- These QC summaries are not movement biomarkers.
- Missing metadata is missing metadata, not no movement.
- `linear_accelerometer` measures phone motion with gravity removed; it is not direct body movement.
- Future Fourier or frequency-domain features require confirmed x/y/z columns, enough continuous signal, timestamp regularity, duplicate handling, vector magnitude, and consistent resampling.

## Interpretation Boundary

Manual row review is not feature extraction. It is fieldwork for deciding which features are safe, interpretable, and worth implementing later.
