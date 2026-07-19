# linear_accelerometer Feature Review

## Table Meaning

`linear_accelerometer` is a high-frequency motion-sensor table intended to record acceleration with gravity removed.

In principle, this table could support motion-intensity and phone-movement features. In the current project protocol, however, it is not usable yet because no reviewed T1-week window has data.

The example row structure provided during review was:

```json
{"label": "", "accuracy": "3", "device_id": "...", "timestamp": 1745923858377, "double_values_0": -0.35706043243408203, "double_values_1": -0.14849185943603516, "double_values_2": -0.03757977485656738}
```

Working interpretation for later review:

- `double_values_0`, `double_values_1`, and `double_values_2` are likely x/y/z linear acceleration axes.
- Linear acceleration usually means acceleration after gravity has been removed.
- This can describe phone movement, not direct body movement.
- Sampling can be very fast, so this table should be treated as a high-frequency table.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp

Result:

- sampled rows: `0`
- protocol-valid review window found: `no`
- coverage scan rows: `318`
- maximum rows in any checked patient/device/window: `0`
- nonzero checked windows: `0`

Output files:

- `output/analysis_candidates/phase2_feature_review/linear_accelerometer/linear_accelerometer_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/linear_accelerometer/linear_accelerometer_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/linear_accelerometer/linear_accelerometer_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/linear_accelerometer/linear_accelerometer_phase2a_t1_ranked_coverage_scan.csv`

## Current Decision

No `linear_accelerometer` features are selected.

Reason:

- The table has no rows in any checked T1-week protocol window.
- Missing data must remain missing and must not be converted to zero movement.
- High-frequency sensor tables can be heavy, so they should not be queried outside bounded protocol windows.
- A later attempt to search after T1 for Subject_ID_D `041` was stopped because bounded day/device queries became slow and timed out. This supports using a dedicated high-frequency strategy instead of broad probing.

## Candidate Features For Later

If future windows contain enough data, possible candidate features would be:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `linear_accel_event_count` | Count rows in a bounded window. | Data coverage and sensor activity. | Data-quality support; not movement by itself. |
| `linear_accel_mean_magnitude` | Mean vector magnitude from x/y/z acceleration values. | Average phone acceleration intensity. | Requires confirmed JSON keys and careful handling of units/sampling. |
| `linear_accel_high_movement_fraction` | Fraction of samples above a pre-defined magnitude threshold. | Proportion of high phone-movement samples. | Phone movement is not body movement; threshold must be validated. |
| `linear_accel_magnitude_iqr` | IQR of vector magnitude in a bounded window. | Variability of phone acceleration. | Sensitive to phone placement and sampling frequency. |
| `linear_accel_spectral_energy` | Frequency-domain energy from resampled acceleration magnitude. | Possible rhythmic movement or tremor-like phone-motion signal. | Requires regular sampling or resampling; not currently ready. |
| `linear_accel_dominant_frequency` | Dominant frequency from FFT on bounded segments. | Main repeated motion frequency in phone movement. | Needs validated sampling frequency and artifact handling. |
| `linear_accel_jerk_mean` | Mean absolute change in acceleration magnitude over time. | Abruptness of phone movement. | Highly sensitive to sampling rate and phone placement. |

## High-Frequency Analysis Requirements

Before selecting any linear accelerometer feature:

1. Find a protocol-valid bounded patient/device/window.
2. Confirm whether rows are stored as table numeric columns or JSON keys.
3. Confirm timestamp spacing and approximate sampling frequency.
4. Compute acceleration magnitude as `sqrt(x^2 + y^2 + z^2)`.
5. Decide whether duplicate or near-duplicate rows exist.
6. For Fourier-style features, resample or segment the signal consistently before applying FFT.

Until those checks are complete, this table remains `phase2_later`.

## Interpretation Rules

- No data in the protocol window is missing data, not no movement.
- Do not use this table for Phase 2B until a protocol-valid sample window exists.
- Prefer already-usable physical activity tables, such as activity recognition, before returning to this high-frequency sensor table.

## Global Coverage Summary

Global coverage summary failed for `linear_accelerometer`.

- Error: `3024 (HY000): Query execution was interrupted, maximum statement execution time exceeded`

This does not change the Phase 2A feature decision.
