# battery Feature Review

## Table Meaning

`battery` records device battery state observations over time.

For the current protocol, one `battery` event means one raw row in the `battery` table within the selected device/time window.

The table is best understood as device-state and charging-context information. It is useful as a supportive context feature family, not as a direct dementia phenotype by itself.

## Fields Seen in `data`

The 20-row expanded sanity sample shows these fields in `battery.data`:

- `device_id`
- `timestamp`
- `battery_level`
- `battery_scale`
- `battery_health`
- `battery_status`
- `battery_adaptor`
- `battery_voltage`
- `battery_technology`
- `battery_temperature`

Most values are stored as string-coded numeric values inside JSON.

## Selected Features

| Feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `low_battery_event_count` | Count rows where normalized battery percent is `<= 20`. Use `100 * battery_level / battery_scale` when `battery_scale` is available and numeric; otherwise treat numeric `battery_level` as percent. | Device availability and charging-context marker. Higher values suggest more observed low-battery states within a window. | Row frequency can bias counts. This is context/supportive information, not a direct dementia phenotype. Missing rows are missing data, not zero low-battery events. |
| `charging_or_plugged_event_count` | Count rows where `battery_adaptor != 0`, or where validated `battery_status` indicates charging/full. Expected Android status codes are `2` = charging and `5` = full. | Charging-context and routine marker. May help contextualize device availability and phone routine. | Requires value-code validation for AWARE/Android battery fields. This is not a direct behavioral phenotype alone. Missing rows are missing data, not zero charging. |

## Candidate Features Not Yet Selected

- `battery_event_count`
- `mean_battery_level`
- `min_battery_level`
- `active_battery_days` as data-quality support

## Privacy Notes

- Battery level and charging state are low privacy risk compared with communication, location, or text fields.
- Battery data should still be reported only as aggregate features.
- `device_id` should remain an internal linkage field and should not appear in clinical summaries.

## Current Feature-Finding Result

The current feature-finding protocol scans patients from highest T1 score downward and uses the first patient with a valid 24-hour window inside the T1 week.

Because highest-T1 Phase A was unavailable, a general raw sanity sample was created from one device with enough `battery` rows for table-structure inspection only.

General sanity sample:

- Sample device: `fdce7e53-e549-45b0-a477-8c300329c656`
- Rows available for that device: `22809`
- Rows sampled: `100`
- First sampled local time: `2025-07-10 10:22:44+0300`
- Last sampled local time: `2025-07-11 00:42:59+0300`
- Expanded sample file: `output/analysis_candidates/phase2_feature_review/battery/battery_sample_rows_expanded.csv`
- Raw sample file: `output/analysis_candidates/phase2_feature_review/battery/battery_sample_rows.csv`

Exploratory T1-ranked protocol result:

- Purpose: when no specific patient is requested, find the first T1-ranked patient with a valid battery 24-hour span inside the T1 week.
- Explicit exploratory exclusion: Subject_ID_D `001` is skipped because its device mapping is not suitable for table-level exploration.
- Result: no protocol-valid patient/window found for `battery`.
- Selected feature rows are kept in the overview with missing values and `feature_status=no_protocol_valid_patient_found`.
- Output file: `output/analysis_candidates/phase2_feature_extraction/exploratory_t1_week_24h/phase2_exploratory_t1_week_24h_selected_features_battery.csv`

Important interpretation rules:

- The saved 100 rows are useful for understanding raw `battery` structure and JSON fields.
- The saved 100 rows are not clinically anchored and are not feature values.
- This does not mean patients had no battery activity.
- It means no reviewed patient had a protocol-valid 24-hour battery window inside the T1 week under the current mapping and exclusion rules.
- Missing battery rows must remain missing and must not be converted to zero activity.
- The two selected features remain selected, but their current feature-finding values are missing because no protocol-valid window was found.

## Possible Future Derived Features

If later coverage supports reliable extraction, add parallel context or data-quality features such as:

- battery logging coverage
- mean observed battery level
- minimum observed battery level
- active battery days
- low-battery fraction rather than count, if row frequency varies strongly

These would be new features, not replacements for the two selected battery features.
