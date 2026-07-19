# sensor_magnetometer Feature Review

## Table Meaning

`sensor_magnetometer` appears to record magnetometer sensor metadata/capability information from the device.

This is not the raw high-frequency magnetic-field stream. It is best treated as sensor/hardware context unless later inspection shows usable raw axis values.

The separate `magnetometer` table is a large high-frequency stream and has previously been treated as later raw-signal work because bounded checks can be expensive.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp
- no aggregation was used for the manual sample

Result: no protocol-valid review window with at least 20 rows was found.

The coverage scan checked `318` bounded device/window candidates. All checked T1-week candidates had `0` rows.

## Review Sample

No manual 20-row sample is available under the current protocol.

Output files were still written for traceability:

- `output/analysis_candidates/phase2_feature_review/sensor_magnetometer/sensor_magnetometer_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_magnetometer/sensor_magnetometer_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_magnetometer/sensor_magnetometer_sample_rows.jsonl`
- `output/analysis_candidates/phase2_feature_review/sensor_magnetometer/sensor_magnetometer_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/sensor_magnetometer/sensor_magnetometer_phase2a_t1_ranked_coverage_scan.csv`

## Candidate Features

No candidate phenotype features are proposed from this Phase 2A result.

If this table is revisited later, possible support-only features could include metadata availability or sensor capability fields, but only after an adjusted review sample confirms the row contents.

## Feature Decision

No `sensor_magnetometer` features are selected.

Current recommendation: save this table for later sensor/hardware-context review. Do not use it as a behavioral phenotype source now.

## Global Coverage Summary

The current Streamlit global coverage preview shows later `sensor_magnetometer` rows exist outside the standard Phase 2A T1-week review windows.

- Mapped/pseudo labels with rows in preview: `35`
- Approximate rows in preview: `2,601`
- Top rows by label include Subject_ID_D `007`, `001`, `015`, `035`, and `044`

This means the table is not globally empty, but it is not usable under the current T1-week Phase 2A protocol.

## Interpretation Rules

- Missing T1-week data is missing data, not absence of magnetometer activity.
- Do not infer mobility, orientation, tremor, or behavior from this metadata table.
- Keep this table separate from the large raw `magnetometer` stream.
- This is manual feature review only, not diagnostic and not confirmatory.
