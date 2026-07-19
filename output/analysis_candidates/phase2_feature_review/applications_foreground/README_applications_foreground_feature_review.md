# applications_foreground Feature Review Sample

This folder contains a bounded manual-review sample for `applications_foreground`.

SQL method:

```sql
SELECT *
FROM `applications_foreground`
WHERE device_id = %s
  AND timestamp >= %s
  AND timestamp < %s
ORDER BY timestamp ASC
LIMIT %s;
```

Selected review window:

- Subject_ID_D: 044
- Subject_ID_N: 44
- device_id: 6faf770c-e0bf-4100-9b63-c6167630c854
- device_episode_index: 1
- window_name: late
- window_start_ms: 1756674000000
- window_end_ms: 1757278800000
- n_rows_in_window: 762

Files:

- `applications_foreground_sample_rows.csv`
- `applications_foreground_sample_rows.jsonl`
- `applications_foreground_json_key_summary.csv`

This is manual fieldwork only. It is not feature extraction.
