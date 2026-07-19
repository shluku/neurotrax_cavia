# gsm_neighbor Feature Review

## Table Meaning

`gsm_neighbor` records neighboring cellular tower/context observations from the device.

This table is related to the already-reviewed `gsm` table, but it describes nearby/neighboring cells rather than only the serving cell context. It can support coarse cellular-context and mobility-context features, but raw cellular identifiers can imply location context and should not be exposed as model-facing raw values.

The Phase 2A sample shows these JSON fields:

- `cid`
- `lac`
- `psc`
- `signal_strength`
- `device_id`
- `timestamp`

Observed invalid/sentinel-like values:

- `cid = -1`
- `lac = -1`
- `psc = -1`
- `signal_strength = 0`

These should be handled carefully during feature extraction.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp

Selected review window:

- Subject_ID_D: `076`
- Subject_ID_N: `71`
- global_T1: `107.5`
- T1_date_iso: `2025-01-28`
- device_id: `d7e2b2ca-098b-4c70-ae74-ef074e95af83`
- window_rule: `exploratory_fallback_first_24h_span_within_T1_week`
- window_start_local: `2025-01-28 12:27:04+0200`
- window_end_local: `2025-01-29 12:27:04+0200`
- raw rows in window: `252`
- sampled rows: `20`

Observed sample structure:

| field | examples |
|---|---|
| `cid` | `3835955`, `1034295`, `-1` |
| `lac` | `7101`, `10153`, `-1` |
| `psc` | `184`, `245`, `-1` |
| `signal_strength` | `96`, `0` |

The first 20 sampled rows include repeated records with the same timestamp and cell values. Phase 2B extraction should deduplicate before calculating features. A reasonable initial deduplication key is:

`timestamp + cid + lac + psc + signal_strength`

## Candidate Features

Recommended major candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `gsm_neighbor_distinct_observation_count` | Count distinct neighboring-cell observations after deduplicating repeated timestamp/cell rows. | Usable neighboring-cell observation volume. | Coverage/context feature; missing is not no mobility. |
| `unique_gsm_neighbor_cell_count` | Count distinct valid `cid` values, excluding invalid values such as `-1`. | Breadth of observed neighboring cellular identifiers. | Raw cell IDs can imply location context; aggregate only. |
| `unique_gsm_neighbor_lac_count` | Count distinct valid `lac` values, excluding invalid values such as `-1`. | Breadth of observed neighboring location-area identifiers. | Coarse cellular context; not direct GPS mobility. |
| `gsm_neighbor_cell_transition_count` | Count changes between consecutive valid neighbor `cid` values ordered by timestamp. | Cellular-context transition signal. | Sensitive to logging duplicates, handoff, and reception conditions. |
| `valid_gsm_neighbor_signal_strength_fraction` | Fraction of distinct observations with signal strength present and not invalid/sentinel-like. | Signal-quality support. | Data-quality/context support, not behavior by itself. |
| `mean_valid_gsm_neighbor_signal_strength` | Mean signal strength among distinct valid observations. | Average neighboring-cell signal context. | Signal scale is device/network dependent and needs validation. |

## Feature Decision

Selected features:

- `unique_gsm_neighbor_cell_count`
- `unique_gsm_neighbor_lac_count`
- `gsm_neighbor_cell_transition_count`

Selection note: user selected feature numbers `121`, `119`, and `120` from the current Streamlit candidate table. Interpreted as zero-based candidate rows, this selects the three cellular-context features above.

Phase 2B calculation rules:

- Deduplicate observations using `timestamp + cid + lac + psc + signal_strength`.
- Exclude invalid `cid` and `lac` values such as `-1` from unique-count and transition features.
- `unique_gsm_neighbor_cell_count`: count distinct valid neighboring `cid` values.
- `unique_gsm_neighbor_lac_count`: count distinct valid neighboring `lac` values.
- `gsm_neighbor_cell_transition_count`: count changes between consecutive valid neighboring `cid` values after deduplication and timestamp ordering.

Signal-strength features are not selected now because the value scale and invalid codes need additional validation.

## Output Files

- `output/analysis_candidates/phase2_feature_review/gsm_neighbor/gsm_neighbor_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/gsm_neighbor/gsm_neighbor_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/gsm_neighbor/gsm_neighbor_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/gsm_neighbor/gsm_neighbor_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/gsm_neighbor/gsm_neighbor_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- Do not expose raw `cid`, `lac`, or `psc` values as model-facing features.
- Use aggregate counts/diversity/transition features only.
- Deduplicate repeated timestamp/cell rows before calculating features.
- Exclude invalid values such as `-1` from unique-count and transition features.
- Missing `gsm_neighbor` rows are missing data, not no mobility.
- These are coarse cellular-context features, not GPS location and not diagnostic.

## Global Coverage Summary

This compact summary describes global `gsm_neighbor` availability from the current Streamlit coverage preview.

- Approximate mapped rows in preview: `3,578,683`
- Mapped study/pseudo labels with rows in preview: many mapped patients show rows
- Top mapped subjects by rows include Subject_ID_D `045`, `093`, `035`, `014`, and `028`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
