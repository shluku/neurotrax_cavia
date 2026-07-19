# sensor_proximity Feature Review

## Table Meaning

`sensor_proximity` records proximity sensor metadata/capability information from the device.

This is not the raw proximity-event stream. It does not contain near/far proximity measurements. It contains sensor identity and hardware capability fields such as sensor type, vendor, power use, resolution, range, and minimum delay.

The raw `proximity` table is separate, much larger, and was previously handled only with bounded checks. It should not be queried casually.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp
- no aggregation was used for the manual sample

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

The sampled rows are repeated metadata rows at the same timestamp.

Observed metadata:

| field | observed value |
|---|---|
| `sensor_name` | `proximity-tcs3701` |
| `sensor_type` | `8` |
| `sensor_vendor` | `ams` |
| `sensor_version` | `1` |
| `double_sensor_power_ma` | `0.75` |
| `double_sensor_resolution` | `5` |
| `double_sensor_maximum_range` | `5` |
| `double_sensor_minimum_delay` | `0` |

## Candidate Features

This table should be treated as data-quality / hardware-context support, not a behavioral digital phenotype table.

Candidate support features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `sensor_proximity_available` | Whether at least one metadata row exists in the selected window. | Confirms proximity metadata was logged for the device/window. | Availability of metadata is not proximity behavior. |
| `sensor_proximity_resolution` | Median or first observed `double_sensor_resolution`. | Hardware resolution/context. | Hardware context only; not behavior. |
| `sensor_proximity_maximum_range` | Median or first observed `double_sensor_maximum_range`. | Hardware range/context. | Hardware context only; not near/far events. |
| `sensor_proximity_minimum_delay_us` | Median or first observed `double_sensor_minimum_delay`. | Hardware sampling capability/context. | Does not prove actual proximity sampling occurred. |

## Feature Decision

No `sensor_proximity` features are selected yet.

Current recommendation: do not use this table as a behavioral phenotype feature source. If used later, keep it as hardware/data-quality support only.

## Output Files

- `output/analysis_candidates/phase2_feature_review/sensor_proximity/sensor_proximity_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_proximity/sensor_proximity_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_proximity/sensor_proximity_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/sensor_proximity/sensor_proximity_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_proximity/sensor_proximity_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- This table is not raw proximity-event data.
- Do not infer phone-to-face behavior, pocket state, calls, social proximity, or environmental proximity from this metadata table.
- Missing metadata is missing metadata, not absence of proximity events.
- Any future features from this table should be hardware/data-quality support only.

## Global Coverage Summary

This compact summary describes global `sensor_proximity` availability from the current Streamlit coverage preview.

- Approximate mapped rows in preview: `15,329`
- Mapped study/pseudo labels with rows in preview: `84`
- Top mapped subjects by rows include Subject_ID_D `024`, `007`, `057`, `001`, and `026`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
