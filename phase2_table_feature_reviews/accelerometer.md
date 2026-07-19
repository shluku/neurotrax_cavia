# accelerometer Raw Signal Framework

## Table Meaning

`accelerometer` is the raw high-frequency general accelerometer stream.

It records phone acceleration on x/y/z axes and includes gravity. This is different from `linear_accelerometer`, which attempts to remove gravity.

Observed raw keys:

- `double_values_0`
- `double_values_1`
- `double_values_2`
- `accuracy`
- `timestamp`
- `device_id`
- `label`

Working interpretation:

- `double_values_0`, `double_values_1`, and `double_values_2` are x/y/z acceleration axes.
- Vector magnitude is approximately `sqrt(x^2 + y^2 + z^2)`.
- Because gravity is included, a still phone can show magnitude near `9.8`.

## Why General Accelerometer First

The accelerometer metadata QC showed:

- `sensor_accelerometer` metadata after T1: `77` of `81` patients
- `sensor_linear_accelerometer` metadata after T1: `31` of `81` patients

Therefore general `accelerometer` is the better first raw motion stream to investigate.

## Raw Phase 2A Targeted Sample

The first naive raw table scan against a 24-hour window was too slow. That was important information: the table is too large for broad raw-window probing.

The framework was adjusted to a metadata-anchored raw sample:

- start from patients with `sensor_accelerometer` metadata
- rank by highest T1 global score
- use the selected metadata device/time
- query only a 10-minute raw `accelerometer` window
- fetch only first 20 chronological rows
- run a 5-minute density count from the first raw row

Selected sample:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1 date: `2025-01-08`
- device: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window: `2025-01-08 09:07:27+0200` to `2025-01-08 09:17:27+0200`
- sampled raw rows: `20`
- rows in first 5 minutes: `3202`

This confirms raw `accelerometer` is dense and must be chunked.

## Candidate Feature Direction

No model-facing accelerometer features are selected yet.

The next step should be signal-QC feature design, not direct behavioral extraction.

Likely future feature families:

| Feature family | Example calculation | Meaning | Caution |
|---|---|---|---|
| raw coverage | row count, active minutes, gap counts in bounded chunks | raw signal availability | coverage is not movement |
| sampling quality | median interval, p95 interval, gap distribution | feasibility for signal processing | device-dependent |
| magnitude context | `sqrt(x^2+y^2+z^2)` mean/SD | phone acceleration including gravity | not body movement |
| dynamic motion | `abs(magnitude - local_baseline_gravity)` | phone movement beyond static gravity | needs baseline/window method |
| high-motion bursts | count segments above threshold | bursts of phone movement | threshold must be validated |
| frequency domain | band power from chunked/resampled magnitude | rhythmic phone motion | only after sampling QC |

## Interpretation Boundary

- This is not physical activity recognition.
- This is phone motion, not direct body movement.
- Missing data remains missing, not no movement.
- Raw `accelerometer` is very large, approximately `1.56 TB`.
- Future analysis must use small chunks, metadata-anchored windows, and audited sampling QC.

## Output Files

```text
output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_sample_rows.csv
output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_sample_rows_expanded.csv
output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_sample_rows.jsonl
output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_json_key_summary.csv
output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_candidate_window_summary.csv
output/analysis_candidates/phase2_accelerometer_framework/README_accelerometer_raw_signal_framework.md
```
