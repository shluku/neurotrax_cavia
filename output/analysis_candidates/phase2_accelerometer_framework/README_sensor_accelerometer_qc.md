# Accelerometer Framework: sensor_accelerometer QC

This file documents the QC/readiness scan for `sensor_accelerometer`.

Order of work:

1. Use sensor metadata tables as QC/device-context layers.
2. Use QC results to decide whether and how to analyze `accelerometer`.
3. Only later define model-facing movement biomarkers from raw x/y/z acceleration.

What this script did:

- Used mapped T1 patients only.
- Excluded Subject_ID_D `001`.
- For each mapped device, searched for the first `sensor_accelerometer` timestamp at or after T1.
- Built a bounded 7-day window from that first available timestamp.
- Queried only that bounded device/time window.
- Did not query full patient windows or full raw sensor streams.
- Did not extract raw movement features from `accelerometer`.

Why this metadata table matters:

- It describes Android general accelerometer sensor metadata.
- It helps document sensor vendor, type, resolution, maximum range, power, and minimum delay.
- It supports sampling/readiness planning before high-frequency motion analysis.

Important interpretation:

- These are metadata and data-readiness summaries.
- They are not patient behavior features.
- Missing metadata is missing metadata, not no movement.
- `accelerometer` phone motion is not the same as body movement.

Current run:

- Patients checked: `81`
- Patients with any post-T1 `sensor_accelerometer` metadata: `77`

QC readiness distribution:

```text
qc_readiness_level
sparse_metadata         76
no_metadata_after_T1     4
very_sparse_metadata     1
```

Generated files:

- `sensor_accelerometer_qc_by_patient.csv`
- `sensor_accelerometer_qc_by_device_window.csv`
