# Accelerometer 24h Raw Pilot

This folder contains a bounded local raw-data pilot for the `accelerometer` table.

Purpose:

- Download one patient/device 24-hour raw accelerometer window for local signal analysis.
- Avoid repeated SQL calls while developing filtering, frequency, and activity-state logic.
- Keep this separate from Phase 3 model-facing feature outputs.

Safety and scope:

- No full-table query was run.
- SQL was filtered by one `device_id` and bounded timestamps.
- Rows were fetched chronologically and written in chunks.
- Missing raw rows remain missing and are not interpreted as no movement.
- General accelerometer includes gravity plus phone motion, so this is phone-state signal analysis, not direct body-movement diagnosis.

Candidate-selection rule:

- Rank patients by T1 global score, excluding Subject_ID_D `001`.
- For each selected `sensor_accelerometer` device, search only the first week from T1.
- Use the first available raw `accelerometer` timestamp in that week as the 24-hour window start.
- Select the first ranked patient/device whose 24-hour raw window has the minimum row threshold.

Selected window:


- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1_date_iso: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_start_local: `2025-01-08 09:07:27+0200`
- window_end_local: `2025-01-09 09:07:27+0200`
- downloaded_rows: `1072778`


Files:

- `accelerometer_24h_subject_041_device_d74f7acf_1736320047852_1736406447852_raw.csv.gz`: raw `_id`, `timestamp`, `local_datetime`, `device_id`, and original JSON data.
- `accelerometer_24h_subject_041_device_d74f7acf_1736320047852_1736406447852_signal.csv.gz`: expanded signal columns for faster local analysis: x, y, z, accuracy, label, magnitude.
- `accelerometer_24h_pilot_manifest.csv`: selected window, row counts, file paths, and chunk settings.
- `accelerometer_24h_pilot_candidate_scan.csv`: ranked patient/device search trail.
- `accelerometer_24h_pilot_chunk_log.csv`: per-chunk rows written and error status.

Chunk size: `5` minutes.
