# Accelerometer Work Summary for Next Session

This note summarizes the current accelerometer status and the next feature-development work.

## Current Decision

We will focus first on the raw general `accelerometer` table, not `linear_accelerometer`.

Reason:

- `sensor_accelerometer` metadata exists after T1 for `77` of `81` mapped T1 patients.
- `sensor_linear_accelerometer` metadata exists after T1 for `31` of `81` mapped T1 patients.
- General accelerometer therefore has much wider cohort potential.
- General accelerometer includes gravity; linear accelerometer attempts to remove gravity.

## Local 24h Pilot Now Available

A bounded 24-hour raw accelerometer window was downloaded locally for signal-analysis development.

Pilot patient/window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1 date: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window: `2025-01-08 09:07:27+0200` to `2025-01-09 09:07:27+0200`
- rows saved: `1,072,778`
- chunk size used for download: `5` minutes
- raw compressed file size: about `29.9 MB`
- expanded signal compressed file size: about `32.2 MB`

Local files:

- `raw_24h_pilot/*_raw.csv.gz`: original raw row JSON plus timestamp/device columns.
- `raw_24h_pilot/*_signal.csv.gz`: expanded x/y/z/accuracy/label/magnitude columns for local analysis.
- `raw_24h_pilot/accelerometer_24h_pilot_manifest.csv`
- `raw_24h_pilot/accelerometer_24h_pilot_chunk_log.csv`

The large raw/signal files are local working files and are intentionally not committed to Git.

## What The Signal Means

Observed raw JSON keys:

- `double_values_0`
- `double_values_1`
- `double_values_2`
- `accuracy`
- `timestamp`
- `device_id`
- `label`

Working interpretation:

- `double_values_0/1/2` are x/y/z acceleration axes.
- Raw magnitude is:

```text
magnitude = sqrt(x^2 + y^2 + z^2)
```

- Because this is general accelerometer, magnitude near `9.8` can simply mean a still phone under gravity.
- Phone movement is not the same as patient movement.

## Candidate Clinical/Digital Phenotype Directions

The goal is to create exploratory phone-motion biomarkers, not diagnostic labels.

Candidate feature families:

| Family | Possible features | Meaning |
|---|---|---|
| Coverage/QC | valid signal minutes, active chunks, gap burden | whether the raw signal is usable |
| Sampling quality | median sampling interval, p95 interval, max gap | whether frequency analysis is defensible |
| Phone stillness | still-phone minutes, stillness fraction | periods where the phone is not moving |
| Handling/motion | dynamic motion mean/SD, motion burst count | phone movement intensity and fragmentation |
| Walking-like rhythm | walking-like minutes, walking-like bout count | sustained rhythmic motion compatible with walking cadence |
| Shaking/tremor-like rhythm | tremor-band power, shaking-like minutes | high-frequency phone vibration/handling signal |
| Day/night pattern | day motion, night motion, night/day ratio | circadian phone-motion context |
| Hourly rhythm | hourly motion entropy, active-hour count | distribution of motion over the day |

## Frequency Bands To Evaluate

These are initial analysis bands, not final clinical cutoffs.

| Band | Approx range | Candidate interpretation |
|---|---:|---|
| Very low frequency | `<0.3 Hz` | drift, posture/orientation changes, slow phone movement |
| Handling/non-walking | `0.3-1 Hz` | irregular hand/phone handling |
| Walking-like | `1-3 Hz` | cadence-like rhythmic movement |
| Vigorous/running-like | `2.5-4 Hz` | stronger rhythmic movement, may overlap walking |
| Tremor/shaking-like | `3-8 Hz` | phone shaking, tremor-like or vibration-like signal |
| High frequency check | `8-12 Hz` | possible artifact or high-frequency vibration; use cautiously |

Interpretation caution:

- Walking-like frequency does not prove walking.
- Tremor-like frequency does not prove tremor.
- Phone may be on a table, in a pocket, in a bag, in a car, or held in hand.
- These labels should initially be named as phone-state candidates.

## Proposed Signal Pipeline

Tomorrow's first local algorithm should use the 24h signal file and avoid SQL.

Pipeline:

1. Load the local `*_signal.csv.gz`.
2. Parse timestamps and sort chronologically.
3. Remove exact duplicate timestamp/value rows.
4. Drop rows with missing or nonnumeric x/y/z.
5. Compute timestamp intervals and gap statistics.
6. Split into continuous chunks, initially 5-minute chunks.
7. Estimate sampling rate per chunk.
8. Compute raw magnitude.
9. Estimate gravity/static baseline with rolling median or low-pass filtering.
10. Compute dynamic magnitude:

```text
dynamic_magnitude = abs(magnitude - local_gravity_baseline)
```

11. Resample only continuous chunks with enough samples.
12. Apply frequency analysis per valid chunk.
13. Produce threshold-sensitivity tables before selecting final features.

## Initial Thresholds To Test

These values are for exploration only.

| Parameter | Initial value |
|---|---:|
| chunk length | `5 minutes` |
| large gap threshold | `1 second` |
| minimum samples per 5-minute chunk | `100` |
| stillness dynamic magnitude threshold | `0.05-0.10 m/s^2` |
| high-motion dynamic magnitude threshold | `0.5-1.0 m/s^2` |
| burst minimum duration | `0.5 seconds` |
| burst refractory period | `1 second` |
| walking-like band | `1-3 Hz` |
| shaking/tremor-like band | `3-8 Hz` |

## Candidate Features To Prototype Next

Suggested first local outputs:

- `accelerometer_valid_signal_minutes`
- `accelerometer_median_sampling_interval_ms`
- `accelerometer_gap_burden_fraction`
- `accelerometer_still_phone_minutes`
- `accelerometer_stillness_fraction`
- `accelerometer_phone_handling_minutes`
- `accelerometer_dynamic_magnitude_mean`
- `accelerometer_dynamic_magnitude_sd`
- `accelerometer_motion_burst_count`
- `accelerometer_high_motion_burst_count`
- `accelerometer_walking_like_minutes`
- `accelerometer_walking_like_bout_count`
- `accelerometer_tremor_band_power`
- `accelerometer_shaking_like_minutes`
- `accelerometer_day_motion_minutes`
- `accelerometer_night_motion_minutes`
- `accelerometer_day_night_motion_ratio`
- `accelerometer_hourly_motion_entropy`

## Tomorrow's Practical Plan

1. Build a local-only accelerometer signal analysis script.
2. Start with summary/QC outputs, not final features.
3. Plot or tabulate 5-minute chunk results across the 24h pilot.
4. Inspect day vs night differences.
5. Inspect frequency-band summaries.
6. Decide which accelerometer features should become selected Phase 2 features.
7. Only after pilot validation, generalize to all patients using chunked SQL extraction.

## Guardrails

- No SQL is needed for tomorrow's first analysis because the 24h pilot is local.
- Do not treat missing accelerometer rows as no activity.
- Do not overclaim body movement from phone movement.
- Keep accelerometer features exploratory and model-facing only after QC is documented.
- When generalized later, process patient/device/windows in chunks and append outputs rather than overwriting Phase 3 shared files.
