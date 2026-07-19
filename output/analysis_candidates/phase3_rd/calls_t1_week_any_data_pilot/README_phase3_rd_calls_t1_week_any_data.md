# Phase 3 R&D: Calls T1-Week Any-Data Pilot

This is a research-and-development pilot, separate from the strict Phase 3 implementation output.

## Question

The strict implementation requires a protocol-valid 24-hour span inside the T1 week. This pilot asks whether `calls` has more usable signal if we use the entire first week after T1 and calculate features whenever any call rows exist in that week.

## Rule Tested

- Table: `calls`
- Window: T1 local midnight through seven days after T1
- Requirement: at least one row in the T1 week
- No full T1-to-T2 query
- Always filtered by `device_id` and timestamp
- Missing remains missing; no rows are not converted to zero calls

## Interpretation

This is not yet the final clinical protocol. It is an R&D comparison to evaluate whether the strict 24-hour rule is too restrictive for sparse event tables such as calls.
