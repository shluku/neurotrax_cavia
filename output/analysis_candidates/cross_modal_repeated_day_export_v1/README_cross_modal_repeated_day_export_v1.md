# Cross-Modal Phase 8 — Targeted Repeated-Day Export

## Objective and selection

This phase expanded the technical event export without using NeuroTrax outcomes or motion-effect values for selection. The saved Phase 3 coverage matrix identified five devices with two technically observed days each. Three devices had both days with all four event tables in the saved matrix: `dev_72e21d`, `dev_c9cc92`, and `dev_ed3860`. The targeted run also retained `dev_1b799d` and `dev_cc373e` as coverage controls because their second days lacked one or more event tables.

Ten device-days were queried in bounded, read-only batches. At most two closed screen-active episodes per day were exported, limited to ten minutes and requiring observed touch events. No broad joins or unrestricted scans were used.

## Extraction coverage

The checkpoint manifest records all ten completed batches. The export contains 17 selected sessions with ACC or event data; ACC was present in eight sessions:

- `dev_72e21d`: two ACC days, four sessions, 30,847 ACC rows, 179 touch rows, 19 keyboard snapshots.
- `dev_c9cc92`: two ACC days, four sessions, 6,337 ACC rows, 86 touch rows, no keyboard snapshots.
- `dev_cc373e`: one ACC day, two sessions, 16,337 ACC rows, 215 touch rows, 24 keyboard snapshots.
- `dev_1b799d` and `dev_ed3860`: event rows were present, but no ACC rows were retrieved in the selected episodes, so they cannot support motion-conditioned contrasts.

The candidate yield audit is in `candidate_yield_from_saved_coverage.csv`. Device metadata is in `candidate_sensor_metadata.csv`. Batch status, row totals, and cadence are in `checkpoint_manifest.csv` and `patient_device_day_qc.csv`.

## Motion-state analysis

The Phase 7 motion definition was reapplied without changing thresholds: session-specific median-vector subtraction, one-second bins, residual-motion thresholds 0.05, 0.15, and 0.30, and separate high/mid/low cadence strata. A bottom-30% versus top-30% quantile sensitivity was also preserved from Phase 7. Missing ACC was never classified as stationary.

`motion_conditioned_session_feasibility.csv` and `motion_conditioned_contrast_feasibility.csv` contain the state counts and touch/keyboard interval summaries. The keyboard feature remains a text-state snapshot interval, not physical keypress timing.

## Eligibility and repeated-day feasibility

Using the prespecified minimum of three intervals in both motion states:

- Touch contrasts were eligible in only **one session** at each fixed threshold.
- Keyboard contrasts were eligible in **zero sessions**.
- Only `dev_72e21d` and `dev_c9cc92` had ACC on both targeted days. Their repeated-day ACC coverage is technically real, but adequate moving/stationary interaction-event coverage was not repeated across days.
- `dev_cc373e` supplied one ACC day with keyboard rows, but it cannot establish repeated-day reliability.
- No ICC or patient-day reliability estimate is justified because there are not enough eligible paired motion-state sessions per device-day.

The quantile sensitivity did not solve the problem: moving-state touch coverage was sparse and keyboard moving-state coverage remained absent.

## Decision

**Repeated-day measurement is not yet feasible for the requested motion-conditioned features.**

The larger export improves technical coverage and confirms that repeated ACC days can be obtained for two devices, but the interaction features still fail the prespecified within-session and repeated-day eligibility requirements. The limiting factor is not the absence of event tables; it is insufficient overlap of ACC states with enough touch or keyboard events, compounded by cadence differences and missing ACC on some candidate devices.

The next extraction should target repeated sessions on `dev_72e21d` and `dev_c9cc92` only after adding a pre-query ACC availability screen and a minimum-event forecast. It should not broaden to more patients until at least two device-days per device contain adequate events in both motion states. No cognition testing or predictive modeling was run.

## Privacy and reproducibility

Parquet partitions are under `parquet/` and retain pseudonymous IDs, timestamps, ACC vectors, touch/app metadata, and keyboard timestamps/event labels. Raw text, passwords, raw package names, and production device IDs are excluded. The checkpointed extractor and motion-analysis scripts are copied into this directory.
