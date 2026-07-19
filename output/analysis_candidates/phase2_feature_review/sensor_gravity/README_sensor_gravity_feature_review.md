# sensor_gravity Feature Review

## Table Meaning

`sensor_gravity` records hardware metadata for the device gravity sensor.

This is different from the raw `gravity` table. The raw `gravity` table is a very large high-frequency sensor stream and was skipped in global preview because it is above the large-table threshold. `sensor_gravity` appears to describe whether the gravity sensor exists and its hardware properties.

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

No raw gravity-vector values were observed in `sensor_gravity`.

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
| `sensor_name` | `gravity` |
| `sensor_type` | `9` |
| `sensor_vendor` | `huawei` |
| `sensor_version` | `1` |
| `double_sensor_power_ma` | `0.20000000298023224` |
| `double_sensor_resolution` | `0.15328125655651093` |
| `double_sensor_maximum_range` | `9.806650161743164` |
| `double_sensor_minimum_delay` | `10000` |

All first 20 sampled rows had the same timestamp and same metadata values. This supports treating `sensor_gravity` as a hardware metadata table, not as behavioral posture, orientation, or movement data.

## Candidate Features

Support-only candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `sensor_gravity_available` | Whether at least one gravity-sensor metadata row exists in the selected window. | Confirms gravity sensor metadata was logged. | Hardware/context only; not a behavior feature. |
| `sensor_gravity_resolution` | Median or first observed `double_sensor_resolution`. | Hardware resolution context. | Does not measure posture or movement. |
| `sensor_gravity_maximum_range` | Median or first observed `double_sensor_maximum_range`. | Hardware maximum range context. | Hardware capability only. |
| `sensor_gravity_minimum_delay_us` | Median or first observed `double_sensor_minimum_delay`. | Hardware sampling capability context. | Does not prove actual gravity-vector sampling occurred. |

## Feature Decision

No `sensor_gravity` features are selected for model extraction now.

Reason:

- The table appears to contain repeated hardware metadata, not raw gravity-vector observations.
- The raw `gravity` table is the relevant source for future posture/orientation features, but it is very large and requires a separate bounded high-frequency-sensor strategy.
- `sensor_gravity` may remain useful later as hardware/data-quality support.

## Output Files

- `output/analysis_candidates/phase2_feature_review/sensor_gravity/sensor_gravity_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_gravity/sensor_gravity_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_gravity/sensor_gravity_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/sensor_gravity/sensor_gravity_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_gravity/sensor_gravity_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- Do not interpret `sensor_gravity` row counts as movement, posture, or phone orientation.
- Do not use hardware metadata as a behavioral phenotype feature.
- Missing `sensor_gravity` rows are missing metadata, not absence of movement.
- Use a separate bounded high-frequency protocol before considering raw `gravity` features.

## Global Coverage Summary

This compact summary describes global `sensor_gravity` availability from the current Streamlit coverage preview.

- Approximate mapped rows in preview: `13,825`
- Mapped study/pseudo labels with rows in preview: many mapped patients show some rows
- Top mapped subjects by rows include Subject_ID_D `007`, `024`, `057`, `001`, and `026`
- The raw `gravity` table is large: preview marked it as above 200 GB.

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
