# battery Stage A Feature Review Sample

This folder contains a Stage A manual-review sample for `battery`.

Stage A goal:

- Understand raw rows and JSON structure.
- Do not extract patient-level features.
- Do not make clinical conclusions.

Sample-device discovery query:

```sql
SELECT device_id, COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
FROM `battery`
GROUP BY device_id
HAVING n_rows >= %s
ORDER BY n_rows DESC
LIMIT 1;
```

Sample query:

```sql
SELECT *
FROM `battery`
WHERE device_id = %s
ORDER BY timestamp ASC
LIMIT %s;
```

Selected sample device:

- device_id: `fdce7e53-e549-45b0-a477-8c300329c656`
- rows available for device: `22809`
- first timestamp: `1752132164226.0` / 2025-07-10 10:22:44+0300
- last timestamp: `1761020966246.0` / 2025-10-21 07:29:26+0300

Requested minimum rows: 100
Rows sampled: 100
Sample limit: 100

Columns in table:

```text
_id
timestamp
device_id
data
```

This is for manual feature review only. Missing data in later clinical windows must remain missing and must not be converted to zero.

The raw JSON is preserved in `battery_sample_rows.csv`.
The expanded per-key inspection view is saved in `battery_sample_rows_expanded.csv`.


No selected battery feature values should be calculated from this manual inspection sample. Battery feature values must come from the Phase B 24-hour acquisition protocol or a documented exploratory T1-week 24-hour protocol window.
