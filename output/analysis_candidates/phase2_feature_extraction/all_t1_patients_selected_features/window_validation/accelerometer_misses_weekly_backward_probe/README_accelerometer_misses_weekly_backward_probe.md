# Accelerometer Misses Weekly Backward Probe

Date: 2026-07-21

Purpose:

- Test whether previous accelerometer misses `007` and `013` have any raw `accelerometer` samples near their metadata windows.
- For each post-T1 `sensor_accelerometer` metadata window, probe backward from the window end in 7-day jumps.
- Each probe is bounded to a short window and returns at most 10 raw samples.

Output:

- Probe CSV: `/Users/ofirfizitsky/PycharmProjects/research_dbeaver/output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_misses_weekly_backward_probe/accelerometer_misses_weekly_backward_probe.csv`

Result:

- Probe rows: 3
- Subjects with any raw hit: none

Interpretation:

- This is still not a full raw-table absence proof.
- It is a low-cost diagnostic: if raw sampling exists near the end of the metadata week, this should usually catch it.
- No hit means no raw samples were found in the bounded weekly-backward probe locations.
