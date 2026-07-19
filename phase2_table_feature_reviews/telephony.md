# telephony Feature Review

## Table Meaning

`telephony` records phone/SIM/network telephony state observations from the device.

This table is mostly device connectivity and cellular state context. It contains several privacy-sensitive identifiers that must not be used as phenotype features or model-facing values.

The Phase 2A sample shows these JSON fields:

- `sim_state`
- `phone_type`
- `sim_serial`
- `line_number`
- `data_enabled`
- `network_type`
- `imei_meid_esn`
- `subscriber_id`
- `software_version`
- `sim_operator_code`
- `sim_operator_name`
- `network_operator_code`
- `network_operator_name`
- `network_country_iso_mcc`
- `device_id`
- `timestamp`

Privacy-sensitive fields:

- `sim_serial`
- `line_number`
- `imei_meid_esn`
- `subscriber_id`
- operator names/codes if they could identify carrier or location context in small samples

These fields should not become phenotype features.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp
- privacy-sensitive values were redacted in the review sample

Selected review window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1_date_iso: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-09 00:00:00+0200`
- window_end_local: `2025-01-10 00:00:00+0200`
- raw rows in window: `93`
- sampled rows: `20`
- first sampled/local row: `2025-01-09 00:58:52+0200`
- last sampled/local row: `2025-01-09 08:13:24+0200`

Observed safe sample summaries:

| field | sample values |
|---|---|
| `sim_state` | `5` in all sampled rows |
| `network_type` | `13` in all sampled rows |
| `data_enabled` | `0` in 16 rows, `2` in 4 rows |
| `network_country_iso_mcc` | `il` in all sampled rows |
| `software_version` | `60` in all sampled rows |

Working interpretation notes:

- Android `network_type == 13` commonly maps to LTE.
- Android `sim_state == 5` commonly maps to SIM ready.
- These mappings should be treated as working interpretations unless confirmed from local AWARE/Android documentation.

## Candidate Features

Recommended major candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `telephony_event_count` | Count all telephony rows in the selected window. | Telephony-state logging volume. | Data volume/context feature; not phone use by itself. |
| `telephony_mobile_data_enabled_fraction` | Fraction of rows with `data_enabled` indicating enabled/on state. | Mobile-data availability/connectivity context. | Coding of `data_enabled` must be confirmed; not actual internet use. |
| `telephony_network_type_diversity` | Diversity across observed `network_type` values. | Variation in cellular network mode, such as LTE/other. | Depends on Android code mapping and device reporting. |
| `telephony_network_type_transition_count` | Count changes between consecutive `network_type` values ordered by timestamp. | Cellular network-mode switching context. | May reflect coverage, modem behavior, or logging frequency. |
| `telephony_sim_ready_fraction` | Fraction of rows where `sim_state` indicates ready. | SIM availability/context. | Mostly data-quality/connectivity support; not behavior. |
| `telephony_active_hour_count` | Count unique local hours with at least one telephony row. | Temporal spread of telephony-state logging. | Data coverage support; missing is not no connectivity. |

## Feature Decision

Selected features:

- `telephony_event_count`
- `telephony_mobile_data_enabled_fraction`
- `telephony_network_type_diversity`

Selection note: user selected feature numbers `97`, `98`, and `99`, corresponding to the first three `telephony` candidates in the current candidate feature plan.

Phase 2B calculation rules:

- `telephony_event_count`: count all telephony rows in the selected protocol window.
- `telephony_mobile_data_enabled_fraction`: fraction of parsed rows where `data_enabled` indicates enabled/on/connected. Numeric values `1` and `2` are treated as enabled-like pending final local-code confirmation.
- `telephony_network_type_diversity`: Shannon entropy across observed `network_type` values in the selected protocol window.

These features are connectivity-context features. They are not direct behavioral, communication, or diagnostic features.

## Output Files

- `output/analysis_candidates/phase2_feature_review/telephony/telephony_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/telephony/telephony_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/telephony/telephony_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/telephony/telephony_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/telephony/telephony_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- Do not use raw SIM serial, line number, IMEI/MEID/ESN, subscriber ID, or operator identifiers as phenotype features.
- Telephony features describe connectivity/device context, not social communication.
- Missing telephony rows are missing data, not no connectivity.
- Coding of `data_enabled`, `sim_state`, and `network_type` should be documented before Phase 2B.

## Global Coverage Summary

This compact summary describes global `telephony` availability from the current Streamlit coverage preview.

- Approximate mapped rows in preview: `1,008,366`
- Mapped study/pseudo labels with rows in preview: `83`
- Top mapped subjects by rows include Subject_ID_D `032`, `044`, `045`, `018`, and `035`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
