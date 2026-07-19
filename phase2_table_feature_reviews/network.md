# network

## Phase 2A Manual Review Status

The standard Phase 2A T1-ranked T1-week 24-hour protocol found no `network` rows.

To support manual feature discovery, the current review sample uses the first 20 chronological rows from the `network` table.

## Current Manual Sample

- sample_context: `phase2a_network_global_earliest_20_manual_review`
- sampled rows: 20
- first row local time: `2025-05-23 12:50:44+0300`
- last row local time: `2025-05-23 14:32:18+0300`
- mapped subjects in sample: `NOT_MAPPED`
- devices in sample: `a182f886-53f6-4d1f-a535-ae20e5a2060e; afed394e-f4e2-4372-89b9-df56506976b3`

## Standard Protocol Coverage Result

- Bounded patient/device/window checks: 318
- Windows with any rows: 0
- Maximum rows in any checked window: 0

## Feature Decision

No `network` features are selected yet. The first 20 rows are available for manual inspection before candidate features are chosen.

## Output Files

- `output/analysis_candidates/phase2_feature_review/network/network_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/network/network_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/network/network_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/network/network_phase2a_t1_ranked_coverage_scan.csv`

## Caution

This global earliest-row sample is not a T1-window phenotype result. Missing `network` rows near T1 are not interpreted as no network activity.

## Global Coverage Summary

This compact summary describes global `network` availability across the SensorDB table, mapped back to the current study device map.

- Devices with `network` rows: `13`
- Mapped study patients with `network` rows: `5`
- Mapped devices with rows: `5`
- Unmapped devices with rows: `8`
- Rows mapped to study patients: `160,426`
- Rows on unmapped devices: `79`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
