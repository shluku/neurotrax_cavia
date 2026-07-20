# Accelerometer Special Phase 3 24h Pilot

This folder contains a pilot implementation of the accelerometer-specific Phase 3 pipeline.

Scope:

- Table: `accelerometer`
- Candidate patients allowed: `10`
- Excluded patient: `001`
- Ranking: descending T1 global score among patients with `sensor_accelerometer` metadata
- SQL rule: one `device_id`, bounded timestamp window, 5-minute chunks
- Local rule: download temporary per-patient signal file, analyze locally, then delete temporary file unless `--keep-temp` is used
- Anchor source: `sensor-metadata`

Window rule:

1. Default pilot mode uses the known `sensor_accelerometer` metadata timestamp as the raw `accelerometer` anchor.
2. Optional `raw-first-in-T1-week` mode searches for the first raw `accelerometer` row in the first week from T1.
3. Start a 24-hour window at the selected anchor timestamp.
3. Download only that bounded 24-hour window in 5-minute chunks.
4. If the anchor produces only empty initial chunks, stop that patient early and continue down the ranked list.
5. Analyze locally with duplicate removal, sampling QC, magnitude/dynamic magnitude, state summaries, threshold sensitivity, and bandpass summaries.

Calculated patients in this pilot: `2`

Important:

- Missing raw data remains missing, not no movement.
- Frequency-band features include sampling feasibility checks.
- Shaking/tremor-like bands are only interpretable when the observed sampling rate can support those frequencies.
- Outputs are isolated table-run files and have not been merged into the shared Phase 3 matrix.

Generated files:

- `phase3_accelerometer_24h_pilot_features_wide.csv`
- `phase3_accelerometer_24h_pilot_features_long.csv`
- `phase3_accelerometer_24h_pilot_patient_status.csv`
- `phase3_accelerometer_24h_pilot_download_chunk_log.csv`
- `phase3_accelerometer_24h_pilot_chunk_summary.csv`
- `phase3_accelerometer_24h_pilot_threshold_sensitivity.csv`
- `phase3_accelerometer_24h_pilot_bandpass_summary.csv`
- `phase3_accelerometer_24h_pilot_bandpass_hourly_summary.csv`
