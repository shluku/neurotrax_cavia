# calls Feature Review

## Table Meaning

`calls` records phone call-log events observed on the device.

For the current protocol, one `calls` event means one raw row in the `calls` table within the selected 24-hour T1-week window.

This table is potentially clinically useful as communication-context information, but it is also sensitive and must be interpreted cautiously. A call row is not the same as a meaningful social interaction. It may reflect incoming calls, outgoing calls, missed calls, very short calls, service calls, repeated attempts, or device/call-log behavior.

## Fields Seen in `data`

The Phase 2A expanded sample shows these fields in `calls.data`:

- `device_id`
- `timestamp`
- `trace`
- `call_type`
- `call_duration`

Current observations:

- `trace` appears to be a hashed or encoded call/contact trace identifier. It should be used only for aggregate counting, such as distinct traces, and not as a direct phenotype label.
- `call_type` is string-coded numeric and should be interpreted using this mapping:

| call_type code | meaning |
|---:|---|
| `1` | incoming |
| `2` | outgoing |
| `3` | missed |
| `4` | voicemail |
| `5` | rejected |
| `6` | blocked |
| `7` | answered externally |

- `call_duration` is string-coded numeric and appears to be duration in seconds. Zero-duration rows are present and may represent missed, rejected, unanswered, or otherwise non-conversation calls depending on `call_type`.

## Selected Features

Five `calls` features are selected:

| Feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `call_event_count` | Count all observed `calls` rows in the selected 24-hour window. | Overall call-log activity volume. | Row count is not social interaction count. Missing rows are missing data, not zero calls. |
| `incoming_call_count` | Count rows with `call_type == 1`. | Incoming call exposure/activity context. | Incoming calls may be social, service, spam, or other contacts. |
| `outgoing_call_count` | Count rows with `call_type == 2`. | Outgoing call attempt/activity context. | Outgoing calls are communication attempts, not necessarily completed conversations. |
| `missed_rejected_blocked_call_count` | Count rows with `call_type` in `{3, 5, 6}`. | Unanswered or interrupted call context. | Missed, rejected, and blocked calls have different meanings but are grouped as a simple major feature. |
| `total_call_duration_seconds` | Sum numeric `call_duration` over observed rows. | Total observed call duration in the window. | Strongly affected by one long call; duration does not prove meaningful conversation. |

## Candidate Features Not Yet Selected

| Feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `unique_call_trace_count` | Count distinct `trace` values in the selected window. | Breadth of distinct call traces observed. | `trace` is not a person label; it may represent hashed contacts or other identifiers. |

## Privacy Notes

- Call-log data is privacy-sensitive even if direct phone numbers are not shown.
- `trace` should be treated as an internal identifier and used only for aggregate features.
- Final phenotype summaries should describe aggregate communication context only.
- Do not expose raw trace values in clinical summaries.

## Current Feature-Finding Result

Phase 2A found a sparse but protocol-valid `calls` review window using the current T1-ranked feature-finding protocol.

Selected review window:

- Subject_ID_D: `032`
- Subject_ID_N: `62`
- global_T1: `110.6`
- T1 date: `2025-01-23`
- device_id: `c7fce041-6004-4299-b7d5-8947b4cb54cb`
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-24 00:00:00+0200`
- window_end_local: `2025-01-25 00:00:00+0200`
- rows in selected window: `5`

Output files:

- `output/analysis_candidates/phase2_feature_review/calls/calls_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/calls/calls_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/calls/calls_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/calls/calls_phase2a_t1_ranked_coverage_scan.csv`

Important interpretation rules:

- The standard 20-row review threshold was not met for `calls`.
- A sparse-table review was therefore performed with `--min-rows 1`.
- The 5 observed rows are sufficient to inspect structure, but not enough to validate stable clinical behavior.
- Missing calls data is not zero communication.

## Possible Future Derived Features

If `calls` features are selected later, use only aggregate values and document the exact handling of zero-duration calls and `call_type` codes.
