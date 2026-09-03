# Patient Accelerometer Data Coverage and Mapping Audit

This local audit answers three questions:

1. Which of the active 81 patients have accelerometer evidence, and when was it observed?
2. Which observed device IDs are not mapped to a current patient, and do they contain data that should be investigated?
3. How many mapped devices/patients have local evidence from the first project date through **2025-12-30 inclusive**?

## Evidence layers

- **General ACC metadata**: `sensor_accelerometer` hardware metadata. It identifies a device and its sensor configuration, but it is not a count of raw movement rows.
- **Linear ACC metadata**: `sensor_linear_accelerometer` hardware metadata.
- **Raw linear ACC**: exact device-level row counts and first/last dates from the completed local Parquet inventory.
- **Confirmed raw ACC probes**: devices observed in the existing bounded SQL minute samples or the completed bounded 24-hour pilot. This is confirmation of raw ACC existence, not a full-table audit.

The 81-person cohort is the current cognitive candidate set with Subject `001` excluded. Patient rows are retained even when the completed local inventory has no evidence for a patient.

## Cutoff definition

The cutoff is a half-open local-time boundary at `2025-12-31 00:00:00` in `Asia/Jerusalem`. Therefore, "through 2025-12-30" includes all evidence before that boundary.

## Main outputs

- `patient_accelerometer_data_summary.csv`: exactly one row per active patient.
- `patient_device_accelerometer_evidence.csv`: one row per mapped or unmatched observed device, with source-specific evidence and dates.
- `unmatched_device_data_investigation.csv`: observed device IDs without a current numeric patient mapping.
- `mapped_device_data_through_2025_12_30.csv`: active-cohort device-level cutoff view.
- `accelerometer_data_coverage_summary.csv`: headline counts.
- `active_patient_accelerometer_metadata_summary.csv`: source-table metadata summarized by patient.
- `confirmed_raw_acc_probe_devices.csv`: raw ACC devices confirmed by existing bounded probes.

## Critical interpretation boundary

The SQL `accelerometer` table was not fully scanned in this audit because it is a multi-billion-row table with a timestamp-first index and per-device aggregation is too slow and unstable for an unbounded remote pass. Consequently, a patient or device marked `raw_acc_probe_available=no` is **not** evidence of no raw ACC data. It means no confirmation exists in the completed probes. The next definitive step is a local raw-ACC export/Parquet conversion, after which this same report can be rerun with exact raw ACC counts and dates.

No source SQL tables, source Parquet files, mappings, or patient-level modeling datasets were modified.
