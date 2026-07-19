# light Feature Review

## Table Meaning

`light` records ambient light observations from the phone light sensor.

The locally available SQL catalog confirms:

- table has `device_id`
- table has `timestamp`
- table has JSON `data`
- confirmed JSON key: `double_light_lux`

`double_light_lux` is ambient light intensity in lux. This table may support environment and circadian-context features, but it is also extremely large in the SQL catalog, so all future queries must remain tightly bounded by `device_id` and timestamp.

## Current Phase 2A Status

Phase 2A found a protocol-valid `light` review window using the current T1-ranked feature-finding protocol.

Selected review window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1 date: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-09 00:00:00+0200`
- window_end_local: `2025-01-10 00:00:00+0200`
- rows in selected window: `228215`
- sampled raw rows: `20`

The first 20 chronological rows occur at local midnight and all have `double_light_lux = 0`. This confirms the table structure, but it does not describe the full 24-hour light distribution. For Phase 2B features, the full bounded 24-hour window should be summarized rather than relying on the first 20 sample rows.

Fields seen in the Phase 2A expanded sample:

- `label`
- `accuracy`
- `double_light_lux`
- `device_id`
- `timestamp`

Output files:

- `output/analysis_candidates/phase2_feature_review/light/light_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/light/light_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/light/light_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/light/light_phase2a_t1_ranked_coverage_scan.csv`

## Selected Features

Four `light` features are selected:

| Selected feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `median_light_lux` | Median numeric `double_light_lux` in the selected 24-hour window. | Typical ambient light level. | Phone may be pocketed, covered, or face-down; missing is not zero lux. |
| `percent_dark_samples` | Percent valid lux samples below `10 lux`. | Approximate low-light context. | Low lux can reflect pocket/bag/covered phone or nighttime; not sleep by itself. |
| `night_mean_light_lux` | Mean lux during local nighttime hours `22:00-06:00`. | Nighttime ambient light context. | Requires enough nighttime samples and timezone handling. |
| `light_lux_iqr` | IQR of valid `double_light_lux` values in the selected window. | Variability in observed ambient light context. | Variability may reflect phone placement or logging artifacts. |

## Candidate Features

Focused candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `light_event_count` | Count observed `light` rows in the selected 24-hour window. | Light-table data coverage and sampling density. | Mostly data-quality/support; missing rows are missing data, not darkness. |
| `mean_light_lux` | Mean numeric `double_light_lux` in the selected 24-hour window. | Average ambient light exposure/context. | Phone may be in pocket, bag, face-down, or covered; not direct room illumination. |
| `median_light_lux` | Median numeric `double_light_lux` in the selected window. | Typical ambient light level, less outlier-sensitive than mean. | Same phone-placement limitations as mean lux. |
| `percent_dark_samples` | Percent of valid lux samples below a fixed low-light threshold, for example `<10 lux`. | Approximate low-light/dark context. | Low lux can mean pocket/bag/covered phone, not necessarily dark environment or sleep. |
| `night_mean_light_lux` | Mean lux during local nighttime hours, for example 22:00-06:00. | Nighttime light exposure/context. | Requires enough nighttime samples and careful timezone handling. |
| `daytime_mean_light_lux` | Mean lux during local daytime hours, for example 06:00-22:00. | Daytime light exposure/context. | Depends on sensor exposure and phone placement. |
| `light_lux_iqr` | IQR of valid `double_light_lux` values in the selected window. | Variability in observed ambient light context. | Variability may reflect phone placement or sensor logging, not activity alone. |

## Recommended First Feature Set

For the first selected set, consider:

1. `mean_light_lux`
2. `median_light_lux`
3. `percent_dark_samples`
4. `night_mean_light_lux`
5. `light_lux_iqr`

These are more clinically interpretable than row count alone, while still staying aggregate and non-content-based.

## Privacy And Safety Notes

- Ambient light is not direct location, but it can still reveal routine context.
- Do not interpret low light as sleep or inactivity.
- Do not convert missing light data to zero lux.
- Because `light` is very large, never run unbounded table queries.

## Required Next Step

Run Phase 2A protocol sampling once local DB credentials are available:

```bash
.venv/bin/python3 phase2_sample_table_exploratory_t1_week_for_feature_review.py light
```

Then inspect the 20 chronological raw rows and update this review before selecting Phase 2B features.

## Global Coverage Summary

Global coverage summary failed for `light`.

- Error: `3024 (HY000): Query execution was interrupted, maximum statement execution time exceeded`

This does not change the Phase 2A feature decision.
