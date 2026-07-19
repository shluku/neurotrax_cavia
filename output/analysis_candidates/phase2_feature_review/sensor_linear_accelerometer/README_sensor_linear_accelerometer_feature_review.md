# sensor_linear_accelerometer Feature Review

## Phase 2A Result

`sensor_linear_accelerometer` was reviewed with the standard Phase 2A T1-ranked 24-hour T1-week protocol.

Current Phase 2A review search:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: 24 hours starting local midnight day after T1
- fallback: first complete 24-hour span inside T1 week
- SQL always filtered by `device_id` and `timestamp`

Result:

- Protocol-valid review sample found: `no`
- Sampled rows: `0`
- Coverage scan rows checked: `318`
- Nonzero protocol-window coverage rows: `0`
- Max rows in any protocol-window check: `0`

This means no ranked patient/device had any `sensor_linear_accelerometer` rows inside the allowed T1-week 24-hour protocol window.

## Global Coverage Context

The global Streamlit coverage preview indicates that `sensor_linear_accelerometer` does have later rows:

- Approximate mapped rows in preview: `2,548`
- Mapped study/pseudo labels with rows in preview: `35`
- Top mapped subjects by rows include Subject_ID_D `007`, `001`, `015`, `035`, and `044`
- Earliest mapped rows in preview are around June-July 2025, while many T1 dates are January 2025

This table is therefore not suitable for standard T1 baseline Phase 2B under the current protocol. It may be considered later under an explicitly adjusted or delayed-window rule, similar to the `significant` table, but it should be labeled separately from T1 baseline analysis.

## Feature Decision

No `sensor_linear_accelerometer` features are selected.

Reason:

- No protocol-valid T1-week 24-hour review sample was found.
- The current output files contain empty sample placeholders only.
- High-frequency or motion-derived features would require a separate bounded strategy and careful signal-processing validation.

## Adjusted First-Available Review

Following the `significant` table strategy, a separate adjusted first-available 7-day review was run for `sensor_linear_accelerometer`.

This adjusted review is outside the normal T1-week Phase 2A/2B protocol.

Adjusted Phase 2A selected review window:

- Subject_ID_D: `044`
- Subject_ID_N: `44`
- global_T1: `108.3`
- T1_date_iso: `2025-01-20`
- device_id: `6faf770c-e0bf-4100-9b63-c6167630c854`
- window_rule: `adjusted_first_available_7d_after_T1`
- window_start_local: `2025-07-10 11:22:50+0300`
- window_end_local: `2025-07-17 11:22:50+0300`
- days_first_available_after_T1: `170`
- rows in adjusted window: `25`

Observed fields:

- `sensor_name`
- `sensor_type`
- `sensor_vendor`
- `sensor_version`
- `double_sensor_power_ma`
- `double_sensor_resolution`
- `double_sensor_maximum_range`
- `double_sensor_minimum_delay`

Important finding:

This table appears to contain sensor metadata/capability rows, not raw x/y/z linear acceleration samples. Therefore, it should not be used for motion-intensity, gait, Fourier, or acceleration-magnitude features.

Adjusted candidate features are support/context only:

| Candidate feature | Meaning | Limitation |
|---|---|---|
| `sensor_linear_accelerometer_event_count` | Count metadata rows in adjusted first-available 7-day window. | Metadata coverage only; not movement. |
| `sensor_linear_accelerometer_active_hour_count` | Count local hours with metadata rows. | Data availability support only. |
| `sensor_linear_accelerometer_minimum_delay_us` | Hardware minimum delay/capability. | Does not prove actual raw sampling occurred. |
| `sensor_linear_accelerometer_resolution` | Hardware resolution. | Hardware metadata only. |
| `sensor_linear_accelerometer_maximum_range` | Hardware measurement range. | Hardware metadata only. |
| `sensor_linear_accelerometer_power_ma` | Hardware power/capability context. | Hardware metadata only. |

Adjusted selected features:

- `sensor_linear_accelerometer_event_count`
- `sensor_linear_accelerometer_active_hour_count`
- `sensor_linear_accelerometer_resolution`
- `sensor_linear_accelerometer_maximum_range`
- `sensor_linear_accelerometer_power_ma`

Feature `sensor_linear_accelerometer_minimum_delay_us` is not selected.

Adjusted Phase 2B was calculated using the same adjusted first-available 7-day window as adjusted Phase 2A. These are metadata/support values only, not movement features.

See also:

- `README_sensor_linear_accelerometer_adjusted_first_available_7d_review.md`

## Output Files

- `output/analysis_candidates/phase2_feature_review/sensor_linear_accelerometer/sensor_linear_accelerometer_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_linear_accelerometer/sensor_linear_accelerometer_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_linear_accelerometer/sensor_linear_accelerometer_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/sensor_linear_accelerometer/sensor_linear_accelerometer_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_linear_accelerometer/sensor_linear_accelerometer_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- Do not treat missing T1-week rows as no movement.
- Do not select motion features from this table until a valid inspection sample exists.
- Do not run broad high-frequency extraction without a bounded table-specific plan.
- This is exploratory table fieldwork only, not diagnostic and not confirmatory.
