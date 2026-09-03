# Supplemental modality bounded QC

This run is an availability and payload-quality audit, not the final feature extraction. It does not save raw sensor payloads.

- Proximity and light: all mapped devices except patient 001, Phase 4-style day-after-T1 24-hour probe; if empty, first available 24-hour span inside the T1 week is checked.
- Accelerometer: existing `sensor_accelerometer` metadata-selected device and a 10-minute raw probe from its anchor.
- Counts use bounded device-and-timestamp SQL filters. Samples are parsed in memory and only QC summaries are saved.
- Missing rows are not interpreted as zero activity.
- Patient 001 remains excluded because its raw accelerometer volume is atypical and was explicitly excluded from the prior pilot.

The result is a gate for later chunked feature extraction across the four cohort spans.

Repair note: this v3 directory contains one patient and one device CSV per modality. The original mixed-schema v2 files are retained as an audit artifact.

## Completed QC summary

- Cohort: 81 valid subjects; patient `001` excluded by protocol.
- Proximity: 25/81 patients with rows; 9,392 rows counted.
- Light: 31/81 patients with rows; 17,417,887 rows counted.
- Accelerometer: 30/81 patients with raw rows in the 10-minute anchor probe; 47 had an anchor but no raw rows in that probe and 4 had no metadata anchor; 4,432,362 rows counted.

These counts are not feature values and do not imply that the modalities are clinically useful. They determine which modality/span combinations are eligible for the next bounded feature-extraction stage.
