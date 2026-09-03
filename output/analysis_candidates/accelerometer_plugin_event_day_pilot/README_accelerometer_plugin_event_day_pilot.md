# General Accelerometer Full-Day Pilot Anchored by Plugin Movement Events

This is a separate exploratory pilot. It does not modify the existing Phase 3 or patient-level ACC outputs.

## Protocol

- Source context: the mapped `plugin_google_activity_recognition` movement dictionary.
- Patients: the first two mapped patient IDs in numeric order (`002, 003`).
- Unit of extraction: one unique patient-device-local-calendar-day with at least one plugin movement event.
- A plugin event selects the day; the ACC query covers the complete local day from local midnight inclusive to the next local midnight exclusive in `Asia/Jerusalem`.
- Only mapped device IDs are queried. The plugin event minute is retained as context and is not used to limit the ACC signal.
- Raw SQL is bounded by both `device_id` and timestamp. Raw ACC rows are streamed from SQL and are not copied into this pilot output.
- General ACC contains gravity. Vector magnitude and deviation from the day median are used as signal summaries; these are phone-signal proxies, not validated clinical movement measures.
- Exact duplicate rows with identical timestamp and x/y/z are removed before feature calculation. Invalid JSON or incomplete axes remain in QC counts and are not converted to zero.
- Missing raw ACC produces a status row and missing features; no movement is imputed.

## Feature bundle

The pilot calculates 24 features across quality/coverage, signal level, dynamic motion, temporal pattern, circadian pattern, and rapid signal-change groups. The complete definitions are in `accelerometer_plugin_event_day_feature_catalog.csv`.

The 5-minute table is descriptive QC. Frequency-domain features are intentionally deferred until sampling regularity and adequate signal duration are reviewed; no frequency band is called walking, tremor, or another clinical behavior in this pilot.

## Current run accounting

- Candidate device-days: 108
- Device-days with a recorded status: 35
- Device-days still pending: 73
- Preflight raw rows across candidate days: 24,868,316
- Status counts: {'error': 16, 'no_raw_rows': 13, 'features_calculated': 6}

## Outputs

- `accelerometer_plugin_event_day_candidates.csv`: candidate event-day manifest and plugin context.
- `accelerometer_plugin_event_day_raw_preflight.csv`: bounded raw-ACC availability and first/last raw timestamps.
- `accelerometer_plugin_event_day_features_wide.csv`: one row per patient-device-day with calculated features.
- `accelerometer_plugin_event_day_patient_day_features.csv`: one row per patient-local-day, aggregating devices.
- `accelerometer_plugin_event_day_features_long.csv`: tidy feature/value representation.
- `accelerometer_plugin_event_day_5min_summary.csv`: observed 5-minute signal summaries and coarse state labels.
- `accelerometer_plugin_event_day_status.csv`: extraction status, raw and valid row counts, and errors.
- `accelerometer_plugin_event_day_feature_catalog.csv`: feature definitions and interpretation cautions.

This is a method-development pilot with two patients. It is not a patient-level model, a clinical validation, or evidence of a digital biomarker.

This saved snapshot is partial when `Device-days still pending` is greater than zero. Error rows record database transport or prior interrupted calculation attempts and must be retried before the pilot is treated as a complete event-day audit.
