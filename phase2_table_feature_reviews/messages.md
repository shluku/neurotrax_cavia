# messages Feature Review

## Table Meaning

`messages` records SMS/message-log observations from the device.

This table is clinically interesting as communication-context information, but it is highly privacy-sensitive. Raw message content, phone numbers, contact identifiers, and address-like fields should not become phenotype features or model inputs.

The Phase 2A sample shows these JSON fields:

- `trace`
- `device_id`
- `timestamp`
- `message_type`

`message_type` appears to follow the common Android SMS type code structure:

| message_type | Working meaning |
|---:|---|
| `1` | inbox / received |
| `2` | sent |
| `3` | draft |
| `4` | outbox |
| `5` | failed |
| `6` | queued |

This mapping should be treated as a working interpretation unless confirmed from the local AWARE table documentation.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp
- review outputs redact message content and phone/contact/address-like fields

Selected review window:

- Subject_ID_D: `089`
- Subject_ID_N: `61`
- global_T1: `109.3`
- T1_date_iso: `2025-01-23`
- device_id: `e361ed72-5d8b-48b9-b2eb-c5eeb03da274`
- window_rule: `exploratory_fallback_first_24h_span_within_T1_week`
- window_start_local: `2025-01-23 12:51:16+0200`
- window_end_local: `2025-01-24 12:51:16+0200`
- raw rows in window: `64`
- distinct message observations in window: `1`

## Duplicate/Repeated Row Issue

The first 20 raw rows were repeated copies of the same message event. Therefore raw row count is not currently a good message-volume feature.

The raw redacted sample is preserved, but a distinct-observation inspection file was also created:

- `output/analysis_candidates/phase2_feature_review/messages/messages_sample_rows_distinct_observations.csv`

Current distinct-observation key:

- `timestamp`
- `trace`
- `message_type`

The distinct sample is the primary Phase A inspection view for feature decisions.

## Selected Features

The following `messages` features are selected for Phase 2B exploratory calculation:

| Selected feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `message_distinct_event_count` | Count distinct message observations after deduplication by `timestamp + trace + message_type`. | Overall SMS/message-log activity volume. | A message row is not a social interaction; missing rows are missing data, not zero messages. |
| `outgoing_message_count` | Count distinct observations where `message_type == 2`. | Sent-message volume. | Depends on Android/AWARE message type mapping; does not capture content, intent, or successful social exchange. |

## Candidate Features

Recommended major candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `incoming_message_count` | Count distinct observations where `message_type == 1`. | Received-message volume. | Depends on Android/AWARE message type mapping; does not measure message content or quality. |
| `failed_or_queued_message_count` | Count distinct observations where `message_type` is failed/queued/outbox-like. | Message delivery/context signal. | Sparse and platform-dependent; may reflect technical conditions. |
| `message_active_hour_count` | Count unique local hours with at least one distinct message observation. | Temporal spread of message activity. | Sparse windows can make this unstable. |

## Current Decision

Proceed with Phase 2B for the two selected aggregate features.

## Phase 2B Exploratory Result

Selected-feature extraction used the current exploratory T1-ranked first-valid 24-hour T1-week protocol.

Result:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1_date_iso: `2025-01-08`
- device_id_used: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-09 00:00:00+0200`
- window_end_local: `2025-01-10 00:00:00+0200`
- `message_distinct_event_count`: `9`
- `outgoing_message_count`: `0`

Note: Phase 2A manual inspection required at least 20 rows and therefore used Subject_ID_D `089`. Phase 2B selected-feature extraction can use the first ranked patient with usable selected-feature rows, so it used Subject_ID_D `041`.

## Interpretation Rules

- Missing message data is missing data, not zero communication.
- Use aggregate counts only.
- Do not save or model raw message text, phone numbers, contact names, or addresses.
- Message features describe phone message-log context, not social functioning by themselves.

## Global Coverage Summary

This compact summary describes global `messages` availability across the SensorDB table, mapped back to the current study device map.

- Devices with `messages` rows: `151`
- Mapped study patients with `messages` rows: `80`
- Mapped devices with rows: `121`
- Unmapped devices with rows: `30`
- Rows mapped to study patients: `39,295`
- Rows on unmapped devices: `1,274`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
