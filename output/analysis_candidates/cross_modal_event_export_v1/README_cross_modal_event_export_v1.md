# Cross-Modal Phase 5 — Checkpointed Event-Level Export

## Status

A small, repeated-day technical pilot completed successfully for four device-days and eight verified screen-active sessions:

- `dev_72e21d`: 2025-01-13 and 2025-07-08.
- `dev_c9cc92`: 2025-01-13 and 2025-07-10.

Selection came from the existing Phase 3 technical coverage matrix, not cognitive scores. At most two closed sessions per device-day were selected, limited to sessions of 10 minutes or less with observed touch events. Longer sessions and sessions without touch were excluded before ACC retrieval. This is a reusable pilot dataset, not a cohort-scale extract.

## Extraction and checkpointing

The extractor is `extract_cross_modal_event_export_v1.py`. It uses read-only timestamp/device-bounded queries, retrieves screen events first, reconstructs status-3 to status-0/2 closed sessions, then retrieves touch, foreground-app, keyboard, and ACC rows only inside selected sessions. Each device-day has a `.checkpoint_*.json` marker and is resumable. The flattened checkpoint record is `checkpoint_manifest.csv`.

Database indexes were inspected before extraction. All five source tables have a `(timestamp, device_id)` index. The bounded query plan used that index with index condition pushdown. No full-table scan or broad cohort query was run.

## Dataset contents

Parquet partitions are under `parquet/patient=<pseudonym>/device=<pseudonym>/date=<local date>/modality=<table>/`. Eight sessions were exported. Each row retains millisecond timestamp, local timestamp, source modality, session bounds, and same-device verification. ACC rows retain x/y/z, raw accuracy where available, and native timestamps. Touch rows retain action and a hashed app-context field. Foreground-app rows retain only a truncated SHA-256 package hash and system-app flag. Keyboard rows retain only a text-state event label and hashed package context; password rows and all `before_text`/`current_text` values were excluded.

The selected session totals are:

| Device-day | Sessions | ACC rows | Touch rows | App rows | Keyboard rows | Median ACC interval(s) |
|---|---:|---:|---:|---:|---:|---|
| dev_72e21d, 2025-01-13 | 2 | 11,880 | 34 | 26 | 0 | 7 ms |
| dev_72e21d, 2025-07-08 | 2 | 18,967 | 145 | 28 | 19 | 40 ms |
| dev_c9cc92, 2025-01-13 | 2 | 3,673 | 55 | 16 | 0 | 21–160 ms |
| dev_c9cc92, 2025-07-10 | 2 | 2,664 | 31 | 21 | 0 | 66.5–156 ms |

Keyboard rows are sparse in this technical sample and are not used in the ACC × Touch pilot.

## Synchronization QC

`synchronization_report.csv` records event counts, duplicate timestamps, median and 95th-percentile ACC intervals, >1-second gaps, duration, sensor identity, and matching counts. No duplicate ACC timestamps remained after modality-local deduplication. ACC coverage is not uniform: observed cadence ranges from approximately 7 ms to 160 ms across the selected sessions. This native-rate difference is retained as a QC stratum and is not normalized away.

The BMI120/BOSCH metadata for `dev_72e21d` is carried forward from the completed ACC metadata audit. `dev_c9cc92` sensor identity is intentionally marked not queried in this Phase 5 bounded run; it is not inferred from observed cadence.

## Focused ACC × Touch pilot

`run_acc_touch_pilot_v1.py` compares median acceleration magnitude in ±500-ms and ±1,000-ms windows around touch events with deterministic matched no-touch windows approximately two seconds away in the same session. It reports within-session paired differences, event/control counts, native cadence, and gap counts in `acc_touch_pilot_results.csv`.

All eight sessions had at least three matched pairs and therefore produced descriptive estimates. Differences varied by session and tolerance. They are measurement pilots only; they are not cognitive associations, causal effects, or evidence that touch caused motion. Jerk was not calculated because several sessions were low-rate or had long gaps, and the export intentionally preserves native cadence rather than imposing a resampling rule.

## Privacy audit

`privacy_audit.json` confirms that no raw text, words, password-state rows, raw package names, persistent word hashes, or production device IDs were exported. Package hashes are context identifiers only and cannot be used as a vocabulary or text representation.

## Decision

The success criterion is met for a small reproducible synchronized event dataset. The next step is a predeclared rate-aware ACC × Touch analysis on repeated sessions after adding sensor metadata for all selected devices and defining minimum cadence/gap eligibility. Broad cohort extraction remains deferred until those QC rules are fixed.
