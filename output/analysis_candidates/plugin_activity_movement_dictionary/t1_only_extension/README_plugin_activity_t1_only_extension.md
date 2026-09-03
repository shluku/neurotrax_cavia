# T1-only Plugin Activity Extension

This companion dictionary maps plugin activity-recognition events for the active patients who do not have a recorded T2. It does not modify the original T1-to-T2 dictionary.

## Protocol

- Patients: active mapped cohort members with a valid T1 and no T2 date.
- Devices: only device IDs from `output/label_device_map.csv`.
- Window: local midnight at T1, inclusive, through the latest usable timestamp in `plugin_google_activity_recognition`, inclusive by timestamp value.
- Latest plugin timestamp in this run: `2026-07-15 14:59:38+0300` local time.
- The endpoint is a data-availability boundary, not a clinical T2 visit and not an imputed T2 date.
- Missing plugin rows remain missing; they are not converted to stillness.
- Event labels and minute bins use the same canonical movement classes as the original dictionary.

This extension is intended to characterize available longitudinal movement-context evidence for T1-only patients. It must not be pooled directly with the T1-to-T2 dictionary for a T2-change analysis because its follow-up duration is data-bounded and differs between patients.

## Current extraction state

- T1-only patients: 20
- Mapped devices: 36
- Completed device intervals: 36
- Patients with plugin events: 19
- Raw event rows: 569261

## Outputs

- `plugin_activity_t1_only_events.csv`: timestamp-level event dictionary.
- `plugin_activity_t1_only_minutes.csv`: UTC-minute movement-context dictionary.
- `plugin_activity_t1_only_device_day_summary.csv`: device-day coverage and label counts.
- `plugin_activity_t1_only_patient_day_summary.csv`: patient-day aggregation.
- `plugin_activity_t1_only_patient_summary.csv`: one row per T1-only patient.
- `plugin_activity_t1_only_status.csv`: query and parse status per mapped device.
- `plugin_activity_t1_only_summary.csv`: cohort accounting.
- `plugin_activity_t1_only_checkpoint.json`: resumable device-level checkpoint.

The data are exploratory phone-derived activity context, not direct body movement and not a clinical outcome.
