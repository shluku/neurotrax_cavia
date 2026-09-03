# Patient-Sequential General Accelerometer Pipeline

This workflow uses the plugin movement dictionary to select candidate
patient-device-local days. It processes patients sequentially: all candidate
days for one patient are extracted and merged into patient-level features before
the next patient begins.

For each candidate day, the complete local calendar day is exported, valid JSON
axes are parsed, vector and dynamic magnitude features are calculated, and
quality variables are retained. Missing time is not converted to zero movement.
The raw export keeps the first row by database `_id` for each `device_id +
timestamp` and records the number of rows collapsed at that timestamp. The
output contains no raw ACC rows; compressed timestamp-deduplicated archives are
retained on the external drive and feature files are written locally in this
directory.

The patient-level table uses the median across completed patient-local days and
also retains the mean. A patient can be marked `complete_with_errors` when every
candidate day was attempted but one or more days failed and require retry.
