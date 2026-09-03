# Raw Accelerometer SQL Median-Day Minute Reconnaissance

This is a read-only structural and sampling reconnaissance of the SQL source. It is not patient-level feature extraction.

## Protocol

- Source: MySQL `sensordata` database; raw tables `accelerometer` and `linear_accelerometer`.
- Timestamp interpretation: Unix milliseconds, displayed in `Asia/Jerusalem`.
- Experiment span used: `2025-01-05 18:45:38.214000+02:00` through `2026-07-15 00:19:05.851000+03:00` across the two raw tables.
- Median day: `2025-10-10`; this is the lower midpoint day between the earliest and latest local calendar dates.
- Inspection window: `2025-10-10 09:00:00` to `09:01:00` local time, with an end-exclusive SQL boundary.
- Row ordering: timestamp ascending, then device ID ascending, then row ID ascending.
- The sensor tables are hardware and collection-context references only. Their metadata must not be interpreted as movement behavior.

## Raw window results

| raw table | rows | distinct devices | first local row | last local row |
|---|---:|---:|---|---|
| `accelerometer` | 0 | 0 | none | none |
| `linear_accelerometer` | 306 | 1 | 2025-10-10 09:00:00.127000+03:00 | 2025-10-10 09:00:59.863000+03:00 |

## Sensor metadata interpretation

The paired `sensor_*` tables can contain `double_sensor_minimum_delay`, resolution, maximum range, power, vendor, and sensor identity. Minimum delay can describe a hardware/request capability and does not prove that the raw stream was sampled continuously at that rate.

Outputs:

- `median_day_minute_summary.csv`: global span and exact one-minute raw-table counts.
- `median_day_minute_raw_samples.csv`: representative raw JSON rows from each target table.
- `median_day_minute_sensor_summary.csv`: paired sensor-table availability and matching-device counts.
- `median_day_minute_sensor_samples.csv`: representative sensor metadata JSON rows.
- `median_day_minute_sensor_key_summary.csv`: observed metadata keys and numeric summaries.

The analysis does not alter the SQL database or the Parquet backups.
