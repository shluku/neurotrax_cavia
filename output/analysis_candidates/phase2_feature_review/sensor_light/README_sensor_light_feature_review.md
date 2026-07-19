# sensor_light Feature Review

## Table Meaning

`sensor_light` records hardware metadata for the device light sensor.

This is different from the raw `light` table. The raw `light` table contains ambient-light lux readings and already has selected Phase 2 features. `sensor_light` appears to describe whether the light sensor exists and its hardware properties.

The Phase 2A sample shows these JSON fields:

- `sensor_name`
- `sensor_type`
- `sensor_vendor`
- `sensor_version`
- `double_sensor_power_ma`
- `double_sensor_resolution`
- `double_sensor_maximum_range`
- `double_sensor_minimum_delay`
- `device_id`
- `timestamp`

No raw ambient-light lux values were observed in `sensor_light`.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp

Selected review window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1_date_iso: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `exploratory_fallback_first_24h_span_within_T1_week`
- window_start_local: `2025-01-08 09:07:28+0200`
- window_end_local: `2025-01-09 09:07:28+0200`
- raw rows in window: `36`
- sampled rows: `20`

Observed sample summary:

| field | observed sample value |
|---|---|
| `sensor_name` | `als-tcs3701` |
| `sensor_type` | `5` |
| `sensor_vendor` | `ams` |
| `sensor_version` | `1` |
| `double_sensor_power_ma` | `0.75` |
| `double_sensor_resolution` | `1` |
| `double_sensor_maximum_range` | `10000` |
| `double_sensor_minimum_delay` | `0` |

All first 20 sampled rows had the same timestamp and same metadata values. This supports treating `sensor_light` as a hardware metadata table, not as behavioral ambient-light exposure data.

## Candidate Features

Support-only candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `sensor_light_available` | Whether at least one light-sensor metadata row exists in the selected window. | Confirms light sensor metadata was logged. | Hardware/context only; not a behavior feature. |
| `sensor_light_resolution` | Median or first observed `double_sensor_resolution`. | Hardware resolution context. | Does not measure ambient light exposure. |
| `sensor_light_maximum_range` | Median or first observed `double_sensor_maximum_range`. | Hardware maximum measurable light range. | Hardware capability only. |
| `sensor_light_minimum_delay_us` | Median or first observed `double_sensor_minimum_delay`. | Hardware sampling capability context. | Does not prove actual lux sampling occurred. |

## Feature Decision

No `sensor_light` features are selected for model extraction now.

Reason:

- The table appears to contain repeated hardware metadata, not observed ambient-light lux samples.
- The already-reviewed `light` table is the correct table for ambient-light phenotype features.
- `sensor_light` may remain useful later as hardware/data-quality support.

## Output Files

- `output/analysis_candidates/phase2_feature_review/sensor_light/sensor_light_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_light/sensor_light_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_light/sensor_light_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/sensor_light/sensor_light_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_light/sensor_light_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- Do not interpret `sensor_light` row counts as light exposure.
- Do not use hardware metadata as a behavioral phenotype feature.
- Missing `sensor_light` rows are missing metadata, not absence of ambient light.
- Use the raw `light` table for lux-based features.

## Global Coverage Summary

This compact summary describes global `sensor_light` availability from the current Streamlit coverage preview.

- Approximate mapped rows in preview: `13,120`
- Mapped study/pseudo labels with rows in preview: many mapped patients show some rows
- Top mapped subjects by rows include Subject_ID_D `007`, `057`, `001`, `026`, and `020`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
