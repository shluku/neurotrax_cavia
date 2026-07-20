# Accelerometer 24h Local Signal Analysis Pilot

This analysis used only the local 24-hour pilot signal file. No SQL was queried.

Pilot window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1 date: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window: `2025-01-08 09:07:27+0200` to `2025-01-09 09:07:27+0200`
- loaded rows after numeric x/y/z filtering: `711769`
- valid signal minutes: `1435.0`

Processing:

- Loaded local `*_signal.csv.gz`.
- Sorted rows chronologically.
- Removed exact duplicate timestamp/x/y/z rows.
- Computed raw magnitude as `sqrt(x^2 + y^2 + z^2)`.
- Used each 5-minute chunk's median magnitude as a first-pass gravity/static baseline.
- Computed `dynamic_magnitude = abs(magnitude - chunk_median_magnitude)`.
- Computed sampling gaps and marked chunks with too few samples or heavy gaps.
- Resampled valid chunks to `10 Hz` for Welch frequency-band power.

Frequency bands tested:

- `<0.3 Hz`: very low frequency drift/orientation
- `0.3-1 Hz`: handling/non-walking motion
- `1-3 Hz`: walking-like rhythmic phone motion
- `2.5-4 Hz`: vigorous rhythmic phone motion
- `3-8 Hz`: shaking/tremor-like phone motion
- `8-12 Hz`: high-frequency check

Initial exploratory thresholds:

- chunk length: `5` minutes
- large gap: `1.0` second
- minimum samples per chunk: `100`
- still-phone dynamic threshold: `0.1` m/s^2
- handling dynamic threshold: `0.2` m/s^2
- high-motion dynamic threshold: `0.75` m/s^2
- walking-like power ratio threshold: `0.35`
- shaking-like power ratio threshold: `0.35`

Important interpretation:

- These are phone-state candidate labels, not clinical activity labels.
- `walking-like` does not prove walking.
- `shaking-like` does not prove tremor.
- A still phone does not prove a still patient.
- Missing accelerometer signal remains missing, not no activity.

Generated files:

- `accelerometer_24h_local_pilot_overall_features.csv`
- `accelerometer_24h_local_pilot_chunk_summary.csv`
- `accelerometer_24h_local_pilot_hourly_summary.csv`
- `accelerometer_24h_local_pilot_state_summary.csv`
- `accelerometer_24h_local_pilot_bandpower_summary.csv`
- `accelerometer_24h_local_pilot_threshold_sensitivity.csv`
