# Phase 2 Large Sensor Table Metadata Scan

This folder contains metadata-only fieldwork for large or raw SensorDB sensor tables.

Tables scanned:

- accelerometer
- aware_log
- barometer
- gravity
- gyroscope
- light
- linear_accelerometer
- magnetometer
- proximity
- rotation

What was collected:

- `SHOW TABLE STATUS LIKE ...` metadata, including approximate row count and table size.
- `SHOW COLUMNS` schema metadata.
- `SHOW INDEX` index metadata.
- Availability status rows documenting that bounded patient/window checks were intentionally skipped for these large/raw streams.

What was intentionally not collected:

- No full-table grouped row counts.
- No full raw sensor extraction.
- No feature extraction.
- No unbounded T1-to-T2 scans.

Why bounded patient availability was skipped:

- These tables were the ones that previously made global coverage scans slow or unavailable.
- Even bounded `LIMIT 1` checks can be slow on multi-hundred-GB or multi-TB raw streams depending on index layout.
- The current purpose is metadata and planning, not extraction.

If a table is selected later for feature work, run a separate table-specific bounded sampler with explicit chunking and stop rules.

These outputs support Phase 2 planning for large tables. Missing data remains missing and must not be interpreted as zero activity.
