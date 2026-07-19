# significant Feature Review

## Phase 2A Result

`significant` was reviewed with the standard Phase 2A T1-ranked 24-hour T1-week protocol.

Current Phase 2A review search:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: 24 hours starting local midnight day after T1
- fallback: first complete 24-hour span inside T1 week
- SQL always filtered by `device_id` and `timestamp`

Result:

- Protocol-valid review sample found: `no`
- Sampled rows: `0`
- Coverage scan rows checked: `318`
- Nonzero protocol-window coverage rows: `0`

This means no ranked patient/device had enough `significant` rows inside the allowed T1-week 24-hour protocol window. Missing data remains missing and is not interpreted as zero significant events.

## Important Context

The global Streamlit coverage preview indicates that `significant` does have rows later in the study:

- Approximate mapped rows in preview: `120,208`
- Mapped study/pseudo labels with rows in preview: `54`
- Top mapped subjects by rows include Subject_ID_D `061`, `024`, `007`, `020`, and `032`

However, these rows are not available in the current Phase 2A T1-week feature-review window. Therefore, this table should not proceed to Phase 2B under the current protocol unless the acquisition rule is explicitly changed.

## Feature Decision

Standard T1-week features:

No standard-protocol `significant` features are selected.

Reason:

- No protocol-valid T1-week 24-hour review sample was found.
- The table cannot yet be interpreted for T1 digital phenotype extraction under the current Phase 2 protocol.

## Adjusted Significant-Only Review

Because `significant` starts much later than T1 for mapped subjects, this table now has a separate adjusted review path:

- adjusted Phase 2A: first available `significant` timestamp, then first 7 days of data
- adjusted Phase 2B: calculate selected `significant` features only in that first-available 7-day window
- this is outside the normal T1-week Phase 2A/2B protocol
- it should not be described as T1 baseline digital phenotyping

Adjusted Phase 2A selected review window:

- Subject_ID_D: `041`
- device_id: `bce3e6dc-a61a-4fc5-8d6f-41ff16761f5b`
- first available significant data: `2025-07-08 10:55:14+0300`
- days after T1: `180`
- adjusted window: `2025-07-08 10:55:14+0300` to `2025-07-15 10:55:14+0300`
- rows in adjusted window: `776`

Adjusted selected features:

- `significant_moving_event_count`
- `significant_moving_fraction`
- `significant_active_hour_count`
- `significant_motion_transition_count`

See also:

- `README_significant_adjusted_first_available_7d_review.md`

## Output Files

- `output/analysis_candidates/phase2_feature_review/significant/significant_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/significant/significant_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/significant/significant_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/significant/significant_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/significant/significant_phase2a_t1_ranked_coverage_scan.csv`

## Interpretation Rules

- Do not treat missing T1-week `significant` rows as zero events.
- Do not select features from this table until a valid manual inspection sample is available.
- Later use may require a separate R&D acquisition rule because current coverage appears later than T1 for many subjects.
- This is exploratory table fieldwork only, not diagnostic and not confirmatory.
