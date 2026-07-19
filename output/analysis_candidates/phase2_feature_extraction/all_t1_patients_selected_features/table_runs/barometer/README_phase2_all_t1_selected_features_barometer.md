# Phase 3 Barometer Adjusted First-Available 7-Day Signal Extraction

This table-run applies selected `barometer` signal features to all T1 patients except Subject_ID_D `001`.

This is not the standard T1-week Phase 3 acquisition rule.

Adjusted rule:

1. For each patient and mapped device, find the first `barometer` timestamp at or after T1.
2. Require at least 20 rows in the first 7 days from that timestamp.
3. Fetch only that bounded 7-day window.
4. Calculate selected pressure and vertical-context signal features using the documented Phase 2B thresholds.

Selected signal features:

- `barometer_pressure_range`
- `barometer_pressure_sd`
- `barometer_large_vertical_shift_count`
- `barometer_estimated_elevation_change_m`
- `barometer_upward_transition_count`
- `barometer_downward_transition_count`

Interpretation:

- This is delayed adjusted first-available data, not T1 baseline data.
- Barometer pressure can reflect altitude, weather, phone hardware, and sampling conditions.
- These are exploratory vertical-context support features, not posture markers and not diagnostic markers.
- Missing data remains missing and is not converted to zero activity.

Patients processed: 81
