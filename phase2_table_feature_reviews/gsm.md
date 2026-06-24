# gsm Feature Review

## Table Meaning

`gsm` records cellular network observations for the device.

For the current protocol, one `gsm` event means one raw row in the `gsm` table within the selected 24-hour T1-week window.

This table is best understood as mobility/environment/context support rather than direct behavior. Changes in observed cellular tower identifiers may reflect movement between network areas, but they can also reflect cellular handoff, reception conditions, carrier behavior, or device logging behavior.

## Fields Seen in `data`

The Phase 2A expanded sample shows these fields in `gsm.data`:

- `device_id`
- `timestamp`
- `cid`
- `lac`
- `psc`
- `bit_error_rate`
- `signal_strength`

Current observations:

- `cid` appears to identify a cell tower/cell identifier.
- `lac` appears to identify a location area code.
- `psc` appears to be a network/cell signal identifier.
- `signal_strength` and `bit_error_rate` were `2147483647` in all sampled rows, which likely represents an invalid, unknown, or sentinel value rather than a true physiologic or behavioral signal.

## Selected Features

Three `gsm` features are selected:

| Feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `unique_gsm_cell_count` | Count distinct `cid` values in the selected window. | Breadth of observed cell identifiers. | Cell changes can reflect movement, handoff, reception, or logging behavior. Not direct distance traveled. |
| `unique_gsm_lac_count` | Count distinct `lac` values in the selected window. | Breadth of observed location-area identifiers. | Usually coarse; may be zero/low even when the person moves locally. |
| `gsm_cell_transition_count` | Count changes in consecutive `cid` values ordered by timestamp. | Cellular context transitions over time. | Sensitive to repeated rows, tower handoff, and signal conditions. |

## Candidate Features Not Yet Selected

| Feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `gsm_event_count` | Count all observed `gsm` rows in the selected 24-hour window. | GSM logging/activity coverage in the selected window. | Mostly data coverage/context; missing rows are missing data, not no mobility. |
| `valid_gsm_signal_strength_count` | Count rows where `signal_strength` is present and not the sentinel `2147483647`. | Amount of usable signal-strength evidence. | Data-quality support; current sample suggests signal strength may be unusable. |
| `mean_valid_gsm_signal_strength` | Mean `signal_strength` after excluding sentinel `2147483647`. | Average cellular signal strength when valid. | Use only if enough valid signal rows exist; not a behavioral feature by itself. |

## Privacy Notes

- GSM cell identifiers can indirectly reveal location context.
- Final phenotype outputs should use aggregate features only.
- Raw `cid`, `lac`, and `psc` values should not appear in clinical summaries.

## Current Feature-Finding Result

Phase 2A found a protocol-valid `gsm` review window using the current T1-ranked feature-finding protocol.

Selected review window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1 date: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-09 00:00:00+0200`
- window_end_local: `2025-01-10 00:00:00+0200`
- rows in selected window: `93`
- sampled rows: `20`

Output files:

- `output/analysis_candidates/phase2_feature_review/gsm/gsm_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/gsm/gsm_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/gsm/gsm_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/gsm/gsm_phase2a_t1_ranked_coverage_scan.csv`

Important interpretation rules:

- `gsm` is a context/mobility-support table, not a direct clinical behavior table.
- Missing GSM rows are missing data, not no mobility.
- The sentinel value `2147483647` must be excluded before using signal-strength or bit-error-rate features.

## Possible Future Derived Features

If `gsm` features are selected later, prioritize simple aggregate cell-context features first. Signal-quality features should be used only after confirming enough non-sentinel signal values exist.
