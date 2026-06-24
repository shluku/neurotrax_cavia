# bluetooth Feature Review

## Table Meaning

`bluetooth` records nearby Bluetooth scan observations for a device over time.

`bt_address` is the Bluetooth identifier seen during a scan. One `bt_address` should not be interpreted as one person. Nearby phones, watches, headphones, cars, computers, beacons, and other devices can all appear in Bluetooth scans. Some modern devices may also rotate or randomize Bluetooth addresses, so a high number of observed addresses can reflect environmental Bluetooth density and scan behavior rather than true social contact.

For the current Bluetooth review, one meaningful Bluetooth observation means one distinct row after deduplication by:

```text
timestamp + device_id + bt_address + bt_rssi
```

The raw table contains duplicate database rows, so raw row count is not currently considered the main Bluetooth signal.

The table is best understood as a social/environmental proximity context table. It may indicate nearby Bluetooth-enabled devices, but it should not be interpreted directly as social interaction without validation.

## Fields Seen in `data`

The 20-row expanded sanity sample shows these fields in `bluetooth.data`:

- `device_id`
- `timestamp`
- `label`
- `bt_name`
- `bt_rssi`
- `bt_address`

The expanded inspection file shows raw Bluetooth fields for authorized Helsinki-approved manual review:

- `bt_name`
- `bt_address`

Current relevant signal:

- `bt_rssi`

At this stage, `bt_rssi` is the only Bluetooth value considered directly useful for candidate feature design.

## Selected Features

Two `bluetooth` features are selected:

| Feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `unique_bluetooth_addresses` | Count distinct `bt_address` values after deduplicating observations by `timestamp + device_id + bt_address + bt_rssi`. | Breadth of nearby Bluetooth addresses observed in the selected Bluetooth stream. | Counts nearby Bluetooth identifiers, not people. Missing Bluetooth rows are missing data, not zero nearby devices. |
| `bluetooth_address_diversity_ratio` | Count distinct `bt_address` values after deduplication, then divide by the total number of deduplicated Bluetooth address observations. | Diversity of the observed Bluetooth address stream. A value closer to 1 means most observations are different addresses; a lower value means more repeated addresses. | Depends on scan behavior, address randomization, and deduplication rule. It is not a direct social-interaction measure. |

## Candidate Features Not Yet Selected

- `mean_bluetooth_rssi`
- `median_bluetooth_rssi`
- `max_bluetooth_rssi`
- `strong_signal_bluetooth_event_count`
- `bluetooth_rssi_observation_count`
- `bluetooth_rssi_variability`

Candidate feature meanings:

| Feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `mean_bluetooth_rssi` | Mean numeric `bt_rssi` across distinct Bluetooth observations. | Average observed Bluetooth signal strength. Less negative values suggest stronger/nearer signals. | RSSI depends on device hardware, environment, body/pocket position, and scan behavior. Not a direct social-contact measure. |
| `median_bluetooth_rssi` | Median numeric `bt_rssi` across distinct Bluetooth observations. | Robust central tendency of nearby Bluetooth signal strength. | Same RSSI limitations; may be preferable to mean if outliers exist. |
| `max_bluetooth_rssi` | Maximum numeric `bt_rssi` across distinct observations. | Strongest observed Bluetooth signal in the inspection window. | A single strong signal can reflect a nearby device, accessory, or environmental device. |
| `strong_signal_bluetooth_event_count` | Count distinct observations with `bt_rssi` above a predefined threshold, such as `>= -70 dBm`. | Count of relatively strong nearby Bluetooth observations. | Threshold must be fixed before extraction. Strong signal does not necessarily mean social interaction. |
| `bluetooth_rssi_observation_count` | Count distinct observations with valid numeric `bt_rssi`. | Amount of usable RSSI evidence after deduplication. | Mostly coverage/support. Missing data is not zero Bluetooth exposure. |
| `bluetooth_rssi_variability` | Standard deviation or IQR of numeric `bt_rssi` across distinct observations. | Variability in observed Bluetooth signal strength. | Can reflect movement, environment, scan instability, or changing nearby devices. |

## Manual Review Notes

- Raw Bluetooth fields are visible in this project workspace for authorized manual review.
- `bt_name` and `bt_address` are currently used for inspection and deduplication.
- Current proposed model-facing Bluetooth features focus on aggregate RSSI signals, not raw Bluetooth names or addresses.

## Current Extraction Prototype

The Phase A highest-T1 raw inspection was attempted for `bluetooth`.

Highest-T1 Phase A:

- Highest-T1 patient: Subject_ID_D `041`
- global_T1: `119.4`
- Primary start rule: local midnight on the day after `T1_date_iso`
- Timezone: Asia/Jerusalem
- Primary end: primary start + 36 continuous hours
- Result: no `bluetooth` rows found for the highest-T1 patient's mapped devices

Because highest-T1 Phase A was unavailable, a general raw sanity sample was created from one device with enough `bluetooth` rows.

General sanity sample:

- Sample patient: Subject_ID_D `085`
- Subject_ID_N: `81`
- Sample device: `b89546ef-9f57-4fd0-ad48-638a4a783d19`
- Rows available for that device: `309360`
- Rows sampled: `20`
- First sampled local time: `2025-03-04 10:26:13+0200`
- Expanded sample file: `output/analysis_candidates/phase2_feature_review/bluetooth/bluetooth_sample_rows_expanded.csv`
- Raw sample file: `output/analysis_candidates/phase2_feature_review/bluetooth/bluetooth_sample_rows.csv`

Duplicate-heavy table finding:

- The first 20 raw rows were exact duplicate copies of one underlying Bluetooth observation.
- Each row had a different database `_id`, but the same `timestamp`, `device_id`, `bt_address`, and `bt_rssi`.
- A distinct-observation inspection file was therefore created.

Distinct-observation inspection:

- Raw rows scanned: `5000`
- Distinct observations saved: `20`
- Deduplication key: `timestamp + device_id + bt_address + bt_rssi`
- Output file: `output/analysis_candidates/phase2_feature_review/bluetooth/bluetooth_sample_rows_distinct_observations.csv`
- This distinct-observation file is the primary Phase A view for Bluetooth feature decisions.

Selected-feature check on the distinct 20-observation sample:

- `unique_bluetooth_addresses`: `11`
- `bluetooth_address_diversity_ratio`: `0.55`
- Output file: `output/analysis_candidates/phase2_feature_review/bluetooth/bluetooth_selected_feature_check.csv`

Exploratory T1-ranked protocol result:

- Purpose: when no specific patient is requested, find the first T1-ranked patient with a valid Bluetooth 24-hour span inside the T1 week.
- Explicit exploratory exclusion: Subject_ID_D `001` is skipped because its device mapping is not suitable for table-level exploration.
- Selected patient: Subject_ID_D `085`
- Subject_ID_N: `81`
- global_T1: `100.0`
- T1 date: `2025-03-04`
- Device IDs used: `b89546ef-9f57-4fd0-ad48-638a4a783d19;ba371144-2edb-4839-9fd5-1d0466e41510`
- window_rule: `exploratory_fallback_first_24h_span_within_T1_week`
- window_start_local: `2025-03-04 10:26:13+0200`
- window_end_local: `2025-03-05 10:26:13+0200`
- raw rows in selected window: `42144`
- `unique_bluetooth_addresses`: `302`
- `bluetooth_address_diversity_ratio`: `0.171982`
- Output file: `output/analysis_candidates/phase2_feature_extraction/exploratory_t1_week_24h/phase2_exploratory_t1_week_24h_selected_features_bluetooth.csv`

This exploratory result is protocol-valid for table development, but it does not replace missing values for a specifically requested patient.

Important interpretation rules:

- The raw first 20 rows are useful for understanding the duplicate issue.
- The distinct 20 observations are useful for Bluetooth feature selection.
- The distinct 20 observations are not clinically anchored to the highest-T1 patient.
- Missing Bluetooth rows must remain missing and must not be converted to zero activity.
- The selected Bluetooth features are calculated only as aggregate values; raw Bluetooth addresses are not model-facing phenotype features.

## Possible Future Derived Features

If Bluetooth features are selected later, possible aggregate features include:

- RSSI central tendency
- RSSI strongest observed signal
- RSSI strong-signal counts
- RSSI observation coverage
- RSSI variability

These would be new features and require explicit manual selection before extraction.
