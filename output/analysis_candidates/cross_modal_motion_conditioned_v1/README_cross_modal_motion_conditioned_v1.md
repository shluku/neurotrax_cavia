# Phase 7 — Motion-Conditioned Interaction Feasibility

## Scope

This phase reused the existing Phase 5 synchronized Parquet export only. No SensorDB queries, cohort expansion, cognition tests, or predictive models were run. The methodological motivation is Ning et al. (2023), DOI: 10.1145/3544548.3580906, but the present measures are adapted to this database’s raw ACC and text-state snapshot limitations.

The export contains 2 independent patients, 2 devices, 4 device-days, and 7 ACC-bearing sessions. Touch data are available in all seven sessions. Keyboard data are available in only one selected session, with 19 snapshots. The other sessions have zero exported keyboard snapshots. This makes the keyboard-conditioned analysis infeasible in the current export.

## Motion-state definition

The raw ACC stream includes gravity and has no verified linear-accelerometer stream for these devices. For each session, the script calculates the median three-axis vector and subtracts it from each x/y/z vector. The residual vector norm is a gravity-referenced **motion proxy**, not calibrated linear acceleration. ACC samples are grouped into one-second bins and summarized by the median residual norm.

Fixed thresholds of 0.05, 0.15, and 0.30 in the raw residual units were tested. These thresholds were not imported from Ning et al.; the database does not document compatible units or calibration. High-rate (≤20 ms), mid-rate (20–100 ms), and low-rate (>100 ms) sessions were kept separate. A quantile sensitivity used the bottom 30% of bins as relatively stationary and the top 30% as relatively moving, excluding the middle 40%.

Missing ACC bins were left missing and never classified as stationary. No raw jerk was calculated.

## Proposed contrasts

- **Touch variability:** consecutive touch-event intervals were calculated only when both endpoints were assigned the same motion state. State-specific IQR and coefficient of variation were reported only with sufficient events.
- **Keyboard variability:** password-excluded text-state snapshot intervals were calculated within package-hash streams and assigned to motion states. These are snapshot intervals, not keypress timing or typing speed.
- Application context is available only as truncated package hashes in the export. The current sample is too sparse to support a stable application-stratified estimate or a time-of-day adjustment.

## Feasibility results

Using a minimum of three intervals in both states:

- Fixed-threshold touch contrasts were estimable in only **one session** at all tested thresholds.
- Fixed-threshold keyboard contrasts were estimable in **zero sessions**.
- Quantile-based states produced some stationary touch intervals, but moving-state coverage was usually absent or too small. Keyboard moving-state coverage remained absent.
- At the primary 0.15 threshold, the one eligible touch session had stationary touch IQR 2,231 ms and moving touch IQR 6,103 ms. This is a single-session descriptive result and is not a reproducible finding.

Full coverage is in `motion_conditioned_session_feasibility.csv`, `motion_state_event_coverage.csv`, and `quantile_motion_state_sensitivity.csv`. The output preserves cadence, ACC counts, state-bin counts, event counts, application-context count, and state-specific variability.

## Decision

**Insufficient data for a reliable motion-conditioned interaction feature in the current export.**

The touch contrast is technically calculable in one session but cannot be separated from cadence, gap, and session-composition effects. The keyboard contrast cannot be evaluated because nearly all selected sessions lack keyboard snapshots and no session has enough keyboard snapshots in both motion states. The existing export therefore does not meet the minimum-event requirement for a genuinely cross-table moving-versus-stationary keyboard feature.

A future small checkpointed export should target repeated days from one high-rate device and one low-rate device, require at least three sessions per device-day, and predefine minimum events in both motion states before extraction. It should retain app hashes and local hour for adjustment, but should not expand broadly until these technical requirements are met.

## Privacy

No text, words, raw package names, passwords, persistent word hashes, production device IDs, or timestamps were exported by this phase’s result tables. The privacy audit is `privacy_audit.json`.
