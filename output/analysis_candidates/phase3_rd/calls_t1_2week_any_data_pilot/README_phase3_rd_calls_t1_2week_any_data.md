# Phase 3 R&D: Calls T1 Two-Week Any-Data Pilot

This is a research-and-development pilot, separate from the strict Phase 3 implementation output.

## Question

Does `calls` coverage improve if we use the first 14 days after T1 and calculate selected call features whenever any call rows exist?

## Rule Tested

- Table: `calls`
- Window: T1 local midnight through 14 days after T1
- Requirement: at least one row in that two-week window
- No full T1-to-T2 query
- Always filtered by `device_id` and timestamp
- Missing remains missing; no rows are not converted to zero calls

## Interpretation

This is not yet the final clinical protocol. It is an R&D comparison to evaluate whether sparse event tables need a longer acquisition window.
