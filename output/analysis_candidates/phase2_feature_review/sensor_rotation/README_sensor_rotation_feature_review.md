# sensor_rotation Feature Review

## Table Meaning

`sensor_rotation` records hardware metadata for the device rotation-vector sensor.

This is different from the raw `rotation` table. The raw `rotation` table is a very large high-frequency sensor stream and was skipped in global preview because it is above the large-table threshold. `sensor_rotation` appears to describe whether the rotation-vector sensor exists and its hardware properties.

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

No raw rotation-vector values were observed in `sensor_rotation`.

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
- window_start_local: `2025-01-08 09:07:27+0200`
- window_end_local: `2025-01-09 09:07:27+0200`
- raw rows in window: `37`
- sampled rows: `20`

Observed sample summary:

| field | observed sample value |
|---|---|
| `sensor_name` | `rotation Vector` |
| `sensor_type` | `11` |
| `sensor_vendor` | `huawei` |
| `sensor_version` | `1` |
| `double_sensor_power_ma` | `6.099999904632568` |
| `double_sensor_resolution` | `5.960464477539063e-08` |
| `double_sensor_maximum_range` | `1` |
| `double_sensor_minimum_delay` | `10000` |

All first 20 sampled rows had the same timestamp and same metadata values. This supports treating `sensor_rotation` as a hardware metadata table, not as behavioral phone-orientation data.

## Candidate Features

Support-only candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `sensor_rotation_available` | Whether at least one rotation-vector metadata row exists in the selected window. | Confirms rotation-vector sensor metadata was logged. | Hardware/context only; not a behavior feature. |
| `sensor_rotation_resolution` | Median or first observed `double_sensor_resolution`. | Hardware resolution context. | Does not measure phone orientation or movement. |
| `sensor_rotation_maximum_range` | Median or first observed `double_sensor_maximum_range`. | Hardware maximum range context. | Hardware capability only. |
| `sensor_rotation_minimum_delay_us` | Median or first observed `double_sensor_minimum_delay`. | Hardware sampling capability context. | Does not prove actual rotation-vector sampling occurred. |

## Feature Decision

No `sensor_rotation` features are selected for model extraction now.

Reason:

- The table appears to contain repeated hardware metadata, not raw rotation-vector observations.
- The raw `rotation` table is the relevant source for future orientation/motion features, but it is very large and requires a separate bounded high-frequency-sensor strategy.
- `sensor_rotation` may remain useful later as hardware/data-quality support.

## Output Files

- `output/analysis_candidates/phase2_feature_review/sensor_rotation/sensor_rotation_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_rotation/sensor_rotation_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_rotation/sensor_rotation_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/sensor_rotation/sensor_rotation_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_rotation/sensor_rotation_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- Do not interpret `sensor_rotation` row counts as orientation changes.
- Do not use hardware metadata as a behavioral phenotype feature.
- Missing `sensor_rotation` rows are missing metadata, not absence of phone movement.
- Use a separate bounded high-frequency protocol before considering raw `rotation` features.

## Global Coverage Summary

This compact summary describes global `sensor_rotation` availability from the current Streamlit coverage preview.

- Approximate mapped rows in preview: `15,427`
- Mapped study/pseudo labels with rows in preview: many mapped patients show some rows
- Top mapped subjects by rows include Subject_ID_D `007`, `024`, `001`, `057`, and `015`
- The raw `rotation` table is large: preview marked it as above 200 GB.

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
