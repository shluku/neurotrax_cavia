# Phase 3 Significant Adjusted First-Available 7-Day Extraction

This table-run applies selected `significant` features to all T1 patients except Subject_ID_D `001`.

## Important

This is not the standard T1-week Phase 3 acquisition rule.

`significant` starts much later than T1 for mapped subjects, so this table uses a table-specific adjusted rule:

1. For each patient and mapped device, find the first `significant` timestamp at or after T1.
2. Take the first 7 days from that timestamp.
3. Calculate only the manually selected adjusted `significant` features.

Missing data remains missing. It is not converted to zero movement.

This adjusted run is exploratory and not diagnostic.

Patients processed: 81
