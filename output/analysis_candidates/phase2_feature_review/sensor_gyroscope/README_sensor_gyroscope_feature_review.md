# sensor_gyroscope Feature Review

## Table Meaning

`sensor_gyroscope` records hardware metadata for the device gyroscope sensor.

This is different from the raw `gyroscope` table. The raw `gyroscope` table is a very large high-frequency sensor stream and was skipped in global preview because it is above the large-table threshold. `sensor_gyroscope` appears to describe whether the gyroscope exists and its hardware properties.

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

No raw gyroscope angular-velocity values were observed in `sensor_gyroscope`.

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
- raw rows in window: `36`
- sampled rows: `20`

Observed sample summary:

| field | observed sample value |
|---|---|
| `sensor_name` | `gyroscope-lsm6dsm` |
| `sensor_type` | `4` |
| `sensor_vendor` | `st` |
| `sensor_version` | `1` |
| `double_sensor_power_ma` | `6.099999904632568` |
| `double_sensor_resolution` | `1.7453292457503267e-05` |
| `double_sensor_maximum_range` | `34.906585693359375` |
| `double_sensor_minimum_delay` | `2000` |

All first 20 sampled rows had the same timestamp and same metadata values. This supports treating `sensor_gyroscope` as a hardware metadata table, not as behavioral phone-rotation or movement data.

## Candidate Features

Support-only candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `sensor_gyroscope_available` | Whether at least one gyroscope metadata row exists in the selected window. | Confirms gyroscope metadata was logged. | Hardware/context only; not a behavior feature. |
| `sensor_gyroscope_resolution` | Median or first observed `double_sensor_resolution`. | Hardware resolution context. | Does not measure phone rotation or movement. |
| `sensor_gyroscope_maximum_range` | Median or first observed `double_sensor_maximum_range`. | Hardware maximum range context. | Hardware capability only. |
| `sensor_gyroscope_minimum_delay_us` | Median or first observed `double_sensor_minimum_delay`. | Hardware sampling capability context. | Does not prove actual gyroscope sampling occurred. |

## Feature Decision

No `sensor_gyroscope` features are selected for model extraction now.

Reason:

- The table appears to contain repeated hardware metadata, not raw gyroscope observations.
- The raw `gyroscope` table is the relevant source for future phone-rotation/motion features, but it is very large and requires a separate bounded high-frequency-sensor strategy.
- `sensor_gyroscope` may remain useful later as hardware/data-quality support.

## Output Files

- `output/analysis_candidates/phase2_feature_review/sensor_gyroscope/sensor_gyroscope_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_gyroscope/sensor_gyroscope_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_gyroscope/sensor_gyroscope_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/sensor_gyroscope/sensor_gyroscope_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_gyroscope/sensor_gyroscope_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- Do not interpret `sensor_gyroscope` row counts as phone rotation or movement.
- Do not use hardware metadata as a behavioral phenotype feature.
- Missing `sensor_gyroscope` rows are missing metadata, not absence of movement.
- Use a separate bounded high-frequency protocol before considering raw `gyroscope` features.

## Global Coverage Summary

This compact summary describes global `sensor_gyroscope` availability from the current Streamlit coverage preview.

- Approximate mapped rows in preview: `15,221`
- Mapped study/pseudo labels with rows in preview: many mapped patients show some rows
- Top mapped subjects by rows include Subject_ID_D `024`, `007`, `057`, `001`, and `026`
- The raw `gyroscope` table is large: preview marked it as above 200 GB.

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
