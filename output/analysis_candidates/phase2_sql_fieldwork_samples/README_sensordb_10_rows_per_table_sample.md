# SensorDB 10 Rows Per Table Sample

This file contains up to 10 chronological sampled rows per eligible SensorDB table.

Eligibility:
- Tables must contain both `device_id` and `timestamp` columns.
- Tables were discovered using `SHOW TABLES`.
- Column eligibility was checked using `SHOW COLUMNS FROM table`.

Query safety:
- Queries were filtered by `device_id` and timestamp.
- Samples were taken only from the current top-10 subject/device early and late windows.
- The script preferred `early_window` and fell back to `late_window` only if no early rows were found for that table.
- Slow queries use a MySQL execution-time hint and failed/slow tables are recorded in the summary.
- No full-table `COUNT(*)` was run.
- No full T1-to-T2 windows were queried.
- At most 10 rows per table were saved.

Privacy:
- Obvious sensitive fields were redacted before writing the sample CSV.
- Redacted fields include text/message/body/phone/number/subscriber/IMEI/SIM/contact/email/address/name/SSID/BSSID fields.
- `application_name` is explicitly allowed.

Use:
- This output is for manual review only.
- It is not feature extraction.
- Missing data is not interpreted as zero activity.

Run summary:
- total tables found: 44
- eligible tables with device_id and timestamp: 44

Generated files:
- sensordb_10_rows_per_table_sample.csv
- sensordb_10_rows_per_table_summary.csv
