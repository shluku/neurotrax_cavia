# Supplemental modality bounded QC

This run is an availability and payload-quality audit, not the final feature extraction. It does not save raw sensor payloads.

- Proximity and light: all mapped devices except patient 001, Phase 4-style day-after-T1 24-hour probe; if empty, first available 24-hour span inside the T1 week is checked.
- Accelerometer: existing `sensor_accelerometer` metadata-selected device and a 10-minute raw probe from its anchor.
- Counts use bounded device-and-timestamp SQL filters. Samples are parsed in memory and only QC summaries are saved.
- Missing rows are not interpreted as zero activity.
- Patient 001 remains excluded because its raw accelerometer volume is atypical and was explicitly excluded from the prior pilot.

The result is a gate for later chunked feature extraction across the four cohort spans.
