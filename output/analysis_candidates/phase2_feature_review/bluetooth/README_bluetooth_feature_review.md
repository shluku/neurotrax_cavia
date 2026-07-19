# bluetooth Stage A Feature Review Sample

This folder contains a Stage A manual-review sample for `bluetooth`.

Stage A goal:

- Understand raw rows and JSON structure.
- Do not extract patient-level features.
- Do not make clinical conclusions.

Sample-device discovery query:

```sql
SELECT device_id, COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
FROM `bluetooth`
GROUP BY device_id
HAVING n_rows >= %s
ORDER BY n_rows DESC
LIMIT 1;
```

Sample query:

```sql
SELECT *
FROM `bluetooth`
WHERE device_id = %s
ORDER BY timestamp ASC
LIMIT %s;
```

Selected sample device:

- device_id: `b89546ef-9f57-4fd0-ad48-638a4a783d19`
- rows available for device: `309360`
- first timestamp: `1741076773084.0` / 2025-03-04 10:26:13+0200
- last timestamp: `1749711358092.0` / 2025-06-12 09:55:58+0300

Requested minimum rows: 20
Rows sampled: 20
Sample limit: 20

Columns in table:

```text
_id
timestamp
device_id
data
```

This is for manual feature review only. Missing data in later clinical windows must remain missing and must not be converted to zero.

The raw JSON is preserved in `bluetooth_sample_rows.csv`.
The expanded per-key inspection view is saved in `bluetooth_sample_rows_expanded.csv`.


## Distinct Observation Inspection

The first 20 raw Bluetooth rows were exact duplicate copies of one underlying observation.

A distinct-observation inspection file was therefore created for manual review.

Deduplication key:

```text
timestamp + device_id + bt_address + bt_rssi
```

Result:

- raw rows scanned: 5000
- distinct observations saved: 20
- source device_id: `b89546ef-9f57-4fd0-ad48-638a4a783d19`
- output file: `output/analysis_candidates/phase2_feature_review/bluetooth/bluetooth_sample_rows_distinct_observations.csv`

Raw Bluetooth values are visible in this file for authorized Helsinki-approved manual review.
This distinct file is for inspection only. It does not replace the raw sample and is not feature extraction.
