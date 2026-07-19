# sensor_linear_accelerometer Feature Review

## Table Meaning

`sensor_linear_accelerometer` is treated as a sensor metadata and QC table for the accelerometer workstream.

It is different from `linear_accelerometer`:

- `sensor_linear_accelerometer` describes the Android linear-acceleration sensor and its metadata.
- `linear_accelerometer` contains the high-frequency phone-motion signal that may later support x/y/z movement features.

This table is therefore a planning and quality-control layer, not a behavioral phenotype table.

## Current Accelerometer Framework

The accelerometer workflow is:

1. Analyze `sensor_linear_accelerometer` first.
2. Use it to understand device capability, sampling context, and metadata availability.
3. Only later analyze `linear_accelerometer` for bounded phone-motion biomarkers.

## QC Rule Used

Adjusted first-available rule:

- mapped T1 patients only
- Subject_ID_D `001` excluded
- for each mapped device, find first `sensor_linear_accelerometer` row at or after T1
- build a bounded 7-day window from that timestamp
- query only that device/time window
- summarize metadata and timestamp-readiness fields

This is not the standard T1-week behavior protocol. It is a sensor-readiness protocol.

## QC Fields

The QC framework summarizes:

- metadata row count
- active days and active hours
- first and last metadata timestamps
- observed span
- median and p95 timestamp interval
- maximum gap
- sensor name, vendor, type, and version
- sensor resolution
- maximum sensor range
- sensor power
- minimum delay
- implied maximum sampling rate from minimum delay

## Current Results

Current run:

- patients checked: `81`
- patients with any post-T1 `sensor_linear_accelerometer` metadata: `31`
- patients with metadata available for device context: `11`
- sparse metadata patients: `10`
- very sparse metadata patients: `10`
- no metadata after T1: `50`

These values are metadata availability counts. They are not movement counts.

## Output Files

```text
output/analysis_candidates/phase2_accelerometer_framework/sensor_linear_accelerometer_qc_by_patient.csv
output/analysis_candidates/phase2_accelerometer_framework/sensor_linear_accelerometer_qc_by_device_window.csv
output/analysis_candidates/phase2_accelerometer_framework/README_accelerometer_framework.md
```

## Interpretation Boundary

- This table should not be used as a behavioral feature table.
- Missing metadata is missing metadata, not no movement.
- Linear acceleration features should only be defined after raw `linear_accelerometer` signal continuity, x/y/z fields, and sampling behavior are confirmed.
