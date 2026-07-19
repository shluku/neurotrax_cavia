# bluetooth Highest-T1 Phase B 24h Selected Features

Selected features:

- `unique_bluetooth_addresses`
- `bluetooth_address_diversity_ratio`

Deduplication key:

```text
timestamp + device_id + bt_address + bt_rssi
```

Result:

- Subject_ID_D: `041`
- global_T1: `119.4`
- window_rule: `no_bluetooth_data_with_24h_span_in_T1_week`
- T1 week: `2025-01-08 00:00:00+0200` to `2025-01-15 00:00:00+0200`
- raw rows in selected window: `0`
- distinct observations: `0`
- feature_status: `insufficient_data_no_distinct_bluetooth_observations`

Missing data is not zero activity.
