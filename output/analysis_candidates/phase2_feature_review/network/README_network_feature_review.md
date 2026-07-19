# network Phase 2A Feature Review Sample

This folder contains the current Phase 2A manual-review sample for `network`.

## Important Context

The standard T1-ranked T1-week 24-hour Phase 2A scan found no `network` rows:

- Bounded patient/device/window checks: 318
- Windows with any rows: 0
- Maximum rows in any checked window: 0

Because the table is not empty globally, this manual-review file now contains the first 20 chronological `network` rows in the database.

## Current Manual Sample

- sample_context: `phase2a_network_global_earliest_20_manual_review`
- sampled rows: 20
- first row local time: `2025-05-23 12:50:44+0300`
- last row local time: `2025-05-23 14:32:18+0300`
- mapped subjects in sample: `NOT_MAPPED`
- devices in sample: `a182f886-53f6-4d1f-a535-ae20e5a2060e; afed394e-f4e2-4372-89b9-df56506976b3`

This sample is for manual row/JSON inspection only. It is not feature extraction, not diagnostic, and not a T1-window clinical phenotype result.

## Files

- `network_sample_rows.csv`
- `network_sample_rows_expanded.csv`
- `network_sample_rows.jsonl`
- `network_json_key_summary.csv`
- `network_phase2a_t1_ranked_coverage_scan.csv`
