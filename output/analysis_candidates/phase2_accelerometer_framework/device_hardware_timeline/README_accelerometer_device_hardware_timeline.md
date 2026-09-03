# Accelerometer Device Hardware Timeline

This is a hardware and data-collection context analysis. It is not a behavioral phenotype and it does not replace raw-signal QC.

## Main table

`accelerometer_device_hardware_timeline.csv` contains one row per device ID observed in the sensor metadata tables or in the raw linear-accelerometer Parquet copy.

Each device row includes sensor metadata first/last seen timestamps, active months, sensor identity, vendor, version, nominal minimum delay, resolution, range, power, and raw linear-accelerometer row counts where available.

## Interpretation

- `device_id` is an app/device identifier and is not automatically a unique physical phone or patient.
- Sensor metadata rows are snapshots and may repeat; metadata row count is not device prevalence.
- `double_sensor_minimum_delay` is nominal hardware/request capability context, not observed sampling frequency.
- The raw `linear_accelerometer` Parquet was scanned for complete per-device counts and time spans.
- The full raw `accelerometer` table is not available as local Parquet, so its full per-device row count is explicitly marked unavailable rather than inferred.
- Use the monthly prevalence and configuration tables to identify hardware turnover and possible cross-device comparability problems before building motion features.

## Outputs

- `accelerometer_device_hardware_timeline.csv`: one row per device ID.
- `sensor_device_summary_long.csv`: one row per device and sensor metadata table.
- `sensor_configuration_summary.csv`: configuration prevalence and time span.
- `device_hardware_monthly_prevalence.csv`: monthly metadata/raw-stream prevalence.
- `raw_linear_device_summary.csv`: full raw linear-accelerometer per-device scan.
- `device_hardware_timeline_summary.csv`: audit counts and scan status.

No SQL tables, Parquet files, or existing patient-level cohorts were modified.
