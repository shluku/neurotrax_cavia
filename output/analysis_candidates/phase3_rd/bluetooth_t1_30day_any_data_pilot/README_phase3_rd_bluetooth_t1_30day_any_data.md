# Phase 3 R&D: Bluetooth T1 30-Day Any-Data Pilot

This is a research-and-development pilot, separate from the strict Phase 3 implementation output.

## Question

Does `bluetooth` coverage improve if we use the first 30 days after T1 and calculate selected Bluetooth features whenever any Bluetooth rows exist?

## Rule Tested

- Table: `bluetooth`
- Window: T1 local midnight through 30 days after T1
- Requirement: at least one row in that 30-day window
- No full T1-to-T2 query
- Always filtered by `device_id` and timestamp
- Missing remains missing; no rows are not converted to zero Bluetooth activity

## Features

- `unique_bluetooth_addresses`
- `bluetooth_address_diversity_ratio`

## Interpretation

This is not yet the final clinical protocol. It is an R&D comparison to evaluate whether sparse/context tables need a longer acquisition window.
