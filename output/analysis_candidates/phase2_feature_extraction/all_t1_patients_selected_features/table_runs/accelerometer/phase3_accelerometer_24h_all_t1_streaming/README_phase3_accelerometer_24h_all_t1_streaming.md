# Accelerometer Special Phase 3 All-T1 Streaming Run

This is the production-style accelerometer Phase 3 implementation.

Key design:

- Does not save full raw 24-hour files.
- Streams each patient in 5-minute SQL chunks.
- SQL is always filtered by `device_id` and timestamp bounds.
- Each chunk is parsed, duplicate-cleaned, analyzed, and discarded from memory.
- Outputs are appended after each patient/chunk so the run is resumable.
- Patient `001` is excluded.

Anchor rule:

- Uses the `sensor_accelerometer` metadata anchor timestamp from the QC table.
- Runs a 24-hour window from that anchor.
- If the first 12 chunks are empty, the patient is marked missing at that anchor and skipped.

Interpretation:

- These are phone-state exploratory features, not diagnostic markers.
- Missing data remains missing.
- Frequency features include sampling feasibility checks.
