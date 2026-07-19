# Phase 3 sensor_linear_accelerometer Adjusted First-Available 7-Day Extraction

This table-run applies selected `sensor_linear_accelerometer` metadata/support features to all T1 patients except Subject_ID_D `001`.

This is not the standard T1-week Phase 3 acquisition rule.

Adjusted rule:

1. For each patient and mapped device, find the first `sensor_linear_accelerometer` timestamp at or after T1.
2. Require at least 1 row in the first 7 days from that timestamp.
3. Calculate only manually selected adjusted metadata/support features.

These are hardware/data-availability support features only, not movement features. Missing data remains missing and is not converted to zero movement.

Patients processed: 81
