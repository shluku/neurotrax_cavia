# Accelerometer Framework

This folder contains accelerometer-family metadata/QC outputs.

The current rule is identical across sensor metadata tables:

- mapped T1 patients only
- exclude Subject_ID_D `001`
- find the first table timestamp at or after T1 for each mapped device
- build a bounded 7-day window from that timestamp
- summarize metadata availability, active days/hours, timestamp gaps, sensor vendor/type, resolution, maximum range, power, minimum delay, and implied maximum sampling rate

These outputs are not behavior features. They are a readiness layer before raw high-frequency acceleration tables are used.

Current tables:

- `sensor_linear_accelerometer`: metadata/QC for later `linear_accelerometer` phone-motion analysis
- `sensor_accelerometer`: metadata/QC for later `accelerometer` phone-motion analysis
