# Accelerometer Framework: Sensor Linear Accelerometer QC

This folder starts the accelerometer workstream.

Order of work:

1. Use `sensor_linear_accelerometer` as the metadata/QC layer.
2. Use the QC results to decide whether and how to analyze `linear_accelerometer`.
3. Only later define model-facing movement biomarkers from raw x/y/z linear acceleration.

What this script did:

- Used mapped T1 patients only.
- Excluded Subject_ID_D `001`.
- For each mapped device, searched for the first `sensor_linear_accelerometer` timestamp at or after T1.
- Built a bounded 7-day window from that first available timestamp.
- Queried only that bounded device/time window.
- Did not query full patient windows.
- Did not extract raw movement features from `linear_accelerometer`.

Why `sensor_linear_accelerometer` comes first:

- It describes the Android sensor metadata for linear acceleration.
- It helps document sensor vendor, type, resolution, maximum range, power, and minimum delay.
- It supports sampling/readiness planning before high-frequency motion analysis.

Important interpretation:

- These are metadata and data-readiness summaries.
- They are not patient behavior features.
- Missing metadata is missing metadata, not no movement.
- `linear_accelerometer` phone motion is not the same as body movement.

Current run:

- Patients checked: `81`
- Patients with any post-T1 `sensor_linear_accelerometer` metadata: `31`

Generated files:

- `sensor_linear_accelerometer_qc_by_patient.csv`
- `sensor_linear_accelerometer_qc_by_device_window.csv`
