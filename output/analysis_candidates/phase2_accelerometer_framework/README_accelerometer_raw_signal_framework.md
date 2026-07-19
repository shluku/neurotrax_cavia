# General Accelerometer Raw Signal Framework

This is the first bounded raw-signal step after the `sensor_accelerometer` metadata QC.

Why general accelerometer now:

- `sensor_accelerometer` metadata was found for 77 of 81 mapped T1 patients.
- `sensor_linear_accelerometer` metadata was found for 31 of 81 mapped T1 patients.
- Therefore general `accelerometer` is currently the better first raw motion stream to investigate.

What this script did:

- Used mapped T1 patients only.
- Excluded Subject_ID_D `001` through the shared ranked-patient loader.
- Scanned patients by descending T1 global score among patients with `sensor_accelerometer` metadata.
- Queried only bounded device/time windows anchored to known `sensor_accelerometer` metadata.
- Used a targeted 10-minute raw `accelerometer` window rather than scanning full 24-hour raw windows.
- Fetched only the first 20 chronological raw rows.
- Ran only a small 5-minute density count from the first raw row.
- Did not extract full raw data and did not compute model-facing features.

Selected raw sample window:


- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1_date_iso: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `targeted_around_sensor_accelerometer_metadata_10min`
- window_start_local: `2025-01-08 09:07:27+0200`
- window_end_local: `2025-01-08 09:17:27+0200`
- first_raw_row_local: `2025-01-08 09:07:27+0200`
- sampled rows: `20`
- 5-minute density rows: `3202`


Interpretation:

- This is manual fieldwork for row structure and sampling feasibility.
- The raw `accelerometer` table is approximately 1.56 TB, so future work must be chunked.
- General accelerometer includes gravity plus phone motion.
- Phone motion is not direct body movement.
- Missing raw accelerometer rows are missing data, not no movement.

Generated files:

- `accelerometer_raw_phase2a_sample_rows.csv`
- `accelerometer_raw_phase2a_sample_rows_expanded.csv`
- `accelerometer_raw_phase2a_sample_rows.jsonl`
- `accelerometer_raw_phase2a_json_key_summary.csv`
- `accelerometer_raw_phase2a_candidate_window_summary.csv`

Next signal-analysis candidates:

- raw signal QC: valid minutes, sampling interval, gap burden
- dynamic phone-motion intensity: gravity-corrected magnitude mean and SD
- burst behavior: high-motion burst count and stillness fraction
- abruptness: jerk from filtered dynamic magnitude
- frequency domain: low-frequency power and dominant motion frequency

These are candidates only. They require a small Phase 2B pilot with documented filtering, chunking, gap handling, and threshold sensitivity before selection.
