# Cross-Modal Phase 2 — Timestamp Synchronization Pilot

## Decision
The synchronization pilot was stopped before feature calculation. The saved event-level files are small review samples, not complete patient episodes: keyboard, screen, touch, foreground-app and activity-recognition files each contain only the archived sample rows. They cannot support session reconstruction, censoring, patient-level overlap, or 1/5/10/15-minute stability estimates.

A bounded SensorDB connection was attempted and failed with: `DatabaseError 2005: Unknown MySQL server host applebaum-sensor-data-prod-db-1.ch6c2iwae148.us-west-2.rds.amazonaws.com`. Because timestamp-level synchronization could not be verified, no cross-table feature was calculated and no same-calendar-day availability was treated as simultaneous recording.

## What was verified
Archived records use millisecond epoch timestamps and preserve Asia/Jerusalem local timestamps. They contain device identifiers; the review samples are from one selected device. Duplicate handling is possible using timestamp + device ID, but the saved samples are too sparse and censored to infer complete sessions. Keyboard text and app labels were not exported into the Phase 2 outputs.

## Feature status
All seven requested feature rows are marked `not computed` in `pilot_feature_table.csv`. The requested 1-, 5-, 10- and 15-minute comparison is marked `not computed` in `short_window_coverage_stability.csv`. The example timeline is anonymized and descriptive only; it is not an episode reconstruction.

## ACC assessment
The archived accelerometer pilot contains approximately 3,202 rows in five minutes (~10.7 Hz), but no event-level keyboard/app episode join. Jerk was not calculated. Linear accelerometer remains blocked because no rows were found in checked T1-week windows. Any future jerk feature must first define raw versus gravity-compensated acceleration, deduplicate timestamps, quantify irregular sampling and resample only within valid continuous chunks.

## Next executable step
Restore SensorDB connectivity, then run a bounded same-device query for a coverage-diverse sample selected without cognition. Retrieve complete keyboard, screen, touch and foreground-app rows for one 24-hour T1 window, reconstruct only semantically supported screen-unlocked sessions, and calculate the seven features with explicit boundary censoring.
