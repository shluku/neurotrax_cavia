# barometer Feature Review

## Table Meaning

`barometer` is a raw/high-frequency environmental pressure sensor stream. It may contain atmospheric pressure observations if the phone hardware and AWARE configuration support barometer logging.

This table should be treated cautiously because environmental pressure can reflect context and device hardware, but it is not directly a cognitive or behavioral phenotype.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp
- no aggregation was used for the manual sample

Result: no protocol-valid review window with at least 20 rows was found.

The coverage scan checked `318` bounded device/window candidates. All checked T1-week candidates had `0` rows.

## Review Sample

No manual 20-row sample is available under the current protocol.

Output files:

- `output/analysis_candidates/phase2_feature_review/barometer/barometer_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/barometer/barometer_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/barometer/barometer_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/barometer/barometer_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/barometer/barometer_phase2a_t1_ranked_coverage_scan.csv`

## Adjusted Phase 2A Result

Because the standard T1-week scan had no rows, a table-specific adjusted Phase 2A review was run.

Adjusted rule:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- for each mapped device, find the first `barometer` timestamp at or after T1
- sample the first 7 days from that first available timestamp
- require at least 20 rows for manual review
- this is delayed first-available table analysis, not T1 baseline acquisition

Selected adjusted review window:

- Subject_ID_D: `045`
- Subject_ID_N: `51`
- global_T1: `93.4`
- T1_date_iso: `2025-01-21`
- device_id: `fdce7e53-e549-45b0-a477-8c300329c656`
- window_start_local: `2025-07-10 10:36:07+0300`
- window_end_local: `2025-07-17 10:36:07+0300`
- days_first_available_after_T1: `169`
- rows in adjusted 7-day window: `2,750`
- sampled rows: `20`

Observed JSON/data fields in the adjusted sample:

| field | type / observed pattern |
|---|---|
| `timestamp` | integer millisecond timestamp |
| `device_id` | string |
| `label` | empty string in sampled rows |
| `accuracy` | string, sampled value `3` |
| `double_values_0` | numeric pressure-like value around `972.5` |

The sampled rows are rapid sequential readings from `2025-07-10 10:36:07+0300` to `2025-07-10 10:36:10+0300`.

Adjusted output files:

- `output/analysis_candidates/phase2_feature_review/barometer/barometer_adjusted_first_available_7d_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/barometer/barometer_adjusted_first_available_7d_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/barometer/barometer_adjusted_first_available_7d_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/barometer/barometer_adjusted_first_available_7d_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/barometer/barometer_adjusted_first_available_7d_coverage_scan.csv`
- `output/analysis_candidates/phase2_feature_review/barometer/README_barometer_adjusted_first_available_7d_review.md`

## Candidate Features

No candidate features are proposed from the standard Phase 2A result.

The adjusted sample confirms that `barometer` can produce numeric pressure-like readings, but only in delayed first-available data for this review.

Possible later candidate features, if we decide to use this table:

| Candidate feature | Calculation idea | Meaning | Limitation |
|---|---|---|---|
| `barometer_event_count` | Count rows in a bounded window. | Sensor availability / sampling density. | High row count reflects logging frequency, not behavior by itself. |
| `barometer_active_hour_count` | Number of hours with at least one row. | Coverage continuity. | Data-quality/context support only. |
| `barometer_mean_pressure` | Mean `double_values_0` in a bounded window. | Ambient pressure context. | Strongly affected by altitude/weather/device context. |
| `barometer_pressure_variability` | Standard deviation or robust range of `double_values_0`. | Environmental pressure fluctuation. | Requires careful handling of high-frequency sampling and short bursts. |

## Adjusted Phase 2B Signal Feature Extraction

The selected barometer signal features were calculated for the adjusted first-available 7-day window.

Signal-processing thresholds:

| Parameter | Value |
|---|---:|
| pressure source | `data.double_values_0` |
| accepted pressure range | `300` to `1100` hPa |
| resampling grid | `1 second` |
| short-gap interpolation limit | `5 seconds` |
| rolling median smoothing | `10 seconds`, centered |
| Butterworth low-pass order | `2` |
| Butterworth cutoff | `0.05 Hz` |
| pressure-to-elevation approximation | `-8.3 * pressure_delta_hPa` |
| large vertical shift threshold | `3 meters` |
| minimum transition duration | `10 seconds` |
| transition refractory window | `30 seconds` |

Calculated values:

| Feature | Value |
|---|---:|
| `barometer_pressure_range` | `2.695557` |
| `barometer_pressure_sd` | `1.140157` |
| `barometer_large_vertical_shift_count` | `1` |
| `barometer_estimated_elevation_change_m` | `21.351376` |
| `barometer_upward_transition_count` | `1` |
| `barometer_downward_transition_count` | `0` |

Signal QC:

- raw rows: `2,750`
- parsed pressure rows: `2,750`
- pressure outlier rows removed: `0`
- observed signal span: `2025-07-10 10:36:07+0300` to `2025-07-10 17:07:06+0300`
- observed duration: about `6.5` hours inside the adjusted 7-day window
- resampled 1-second points: `23,460`
- smoothed valid points: `510`
- smoothing method: `Butterworth`
- detected transition: one upward transition from `2025-07-10 10:36:07+0300` to `2025-07-10 17:01:02+0300`, estimated `21.351376` meters

Important interpretation note: this detected upward transition occurs over several hours, so it may reflect vertical movement, environmental/weather pressure drift, or a mixture of both. It should be treated as an exploratory vertical-context support feature, not a direct mobility or posture marker.

Phase 2B output files:

- `output/analysis_candidates/phase2_feature_extraction/adjusted_first_available_7d/phase2_adjusted_first_available_7d_selected_features_barometer.csv`
- `output/analysis_candidates/phase2_feature_extraction/adjusted_first_available_7d/phase2_adjusted_first_available_7d_coverage_scan_barometer.csv`
- `output/analysis_candidates/phase2_feature_extraction/adjusted_first_available_7d/phase2_adjusted_first_available_7d_barometer_signal_qc.csv`
- `output/analysis_candidates/phase2_feature_extraction/adjusted_first_available_7d/phase2_adjusted_first_available_7d_barometer_detected_transitions.csv`
- `output/analysis_candidates/phase2_feature_extraction/adjusted_first_available_7d/phase2_adjusted_first_available_7d_barometer_signal_timeseries.csv`
- `output/analysis_candidates/phase2_feature_extraction/adjusted_first_available_7d/README_phase2_adjusted_first_available_7d_barometer_signal_features.md`

## Feature Decision

Six adjusted `barometer` signal features are selected and calculated for the current Phase 2B exploratory review.

Current recommendation: keep these as adjusted/delayed exploratory vertical-context support features. They should not be treated as T1 baseline features unless we later decide on a separate delayed-sensor feature family.

## Scale Metadata

The metadata-only large-sensor scan found:

- approximate rows: `25,763,375`
- approximate total table size: `7.525 GB`
- columns include `device_id`, `timestamp`, and `data`

This table is smaller than the multi-TB motion streams, but the current T1-week protocol still found no usable review sample.

## Interpretation Rules

- Missing T1-week barometer data is missing data, not absence of environmental exposure or activity.
- Do not convert missing windows to zero.
- Do not infer behavior without a confirmed sampled window and feature definition.
- This is exploratory feature fieldwork only, not diagnostic and not confirmatory.
