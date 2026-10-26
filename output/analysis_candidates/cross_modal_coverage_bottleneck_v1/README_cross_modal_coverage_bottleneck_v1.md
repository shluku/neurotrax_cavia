# Phase 9 — Cross-Modal Coverage Bottleneck Analysis

## Main conclusion

The bottleneck is a combination of **missing synchronized ACC** and **insufficient motion-state variation**, with sampling gaps as an additional loss. It is not primarily caused by the interaction-event minimum alone.

The targeted export contains 17 verified screen sessions across 5 devices and 9 device-days. Only 10 sessions have ACC. Of those, 4 pass the existing ACC sample/gap rule, and only 1 has both stationary and moving one-second bins at the fixed 0.15 residual threshold. No session has the required three touch intervals in both states, and no session has the required keyboard intervals in both states.

## Sequential funnel

The exact funnel is in `sequential_eligibility_funnel.csv` and the session-level reasons are in `session_coverage_diagnostics.csv`.

| Stage | Sessions remaining | Devices | Device-days | Touch events | Keyboard snapshots |
|---|---:|---:|---:|---:|---:|
| Verified screen sessions | 17 | 5 | 9 | 573 | 61 |
| ACC present | 10 | 3 | 5 | 480 | 43 |
| ACC + touch synchronized | 10 | 3 | 5 | 480 | 43 |
| ACC sample/gap QC | 4 | 3 | 3 | 281 | 24 |
| Both motion states at 0.15 threshold | 1 | 1 | 1 | 14 | 0 |
| Touch minimum in both states | 0 | 0 | 0 | 0 | 0 |
| ACC + keyboard synchronized | 2 | 2 | 2 | 343 | 43 |
| Keyboard sample/gap QC | 1 | 1 | 1 | 212 | 24 |
| Keyboard minimum in both states | 0 | 0 | 0 | 0 | 0 |

The seven sessions lost at the ACC stage are missing recordings, not behavioral nulls. Among the ten ACC-bearing sessions, six fail the sampling/gap rule because at least one gap exceeds one second. Among the four sessions passing that rule, three have no stationary bins at the 0.15 threshold; this is insufficient motion-state variation under the existing definition. The remaining session has variation but too few touch intervals in both states. Keyboard coverage is independently sparse: only two ACC-bearing sessions contain keyboard snapshots, and only one passes ACC QC.

## Coverage distributions

`coverage_distributions.csv` shows that ACC duration has a median of 91.5 seconds, with a median longest contiguous segment of 30.2 seconds. The median observed ACC interval is 40 ms across ACC-bearing sessions, ranging from 7 to 160 ms. Touch counts range from 1 to 212 per selected session. Keyboard snapshots have a median of zero and a maximum of 24.

The fixed 0.15 motion-state bins are highly imbalanced in most sessions: stationary-bin counts are often zero, while moving bins cover nearly the full session. This indicates that the residual threshold is not calibrated to every sensor/cadence stratum, but it was retained unchanged as required. Quantile-based alternatives from Phase 7 remain sensitivity analyses and do not rescue repeated keyboard coverage.

## Counterfactual window feasibility

`counterfactual_window_feasibility.csv` uses fixed non-overlapping windows within the exported episodes:

| Window | Total windows | Sessions with ACC | Sessions with touch | Sessions with keyboard |
|---|---:|---:|---:|---:|
| 30 seconds | 69 | 10 | 10 | 2 |
| 1 minute | 32 | 9 | 9 | 2 |
| 5 minutes | 3 | 3 | 3 | 2 |
| 10 minutes | 0 | 0 | 0 | 0 |

Short windows preserve more usable episodes, but they do not solve the missing ACC or motion-state imbalance. Longer windows are uncommon because the selected verified sessions are short or interrupted.

## Alternative feature feasibility

The matrix is in `alternative_feature_feasibility_matrix.csv`.

- ACC magnitude during touch-active versus matched screen-active control periods is a genuinely new cross-table feature. It is feasible in the 10 ACC-touch sessions and remains technically plausible in the 4 sessions passing the current ACC QC because it does not require both motion states.
- Within-session association between ACC magnitude and interaction density is also new and could use fixed short bins in those 4 QC-passing sessions, subject to minimum bin counts.
- ACC variability conditional on foreground-app context is new and has 10 ACC-app sessions before QC, 4 after QC. App hashes are available, but repeated same-app episodes are sparse.
- Moving-minus-stationary touch and keyboard variability remain new but are blocked by dual-state eligibility.
- Touch-rate summaries, app transitions, and same-app keyboard IEI are existing Phase 2/3 summaries and are not counted as new features.

## Decision

**Redesign the cross-table feature definition because dual-state eligibility is the bottleneck.**

Targeted extraction should not expand blindly. The next pilot should use continuous ACC context during touch-active versus matched screen-active periods, or ACC magnitude versus interaction density, with cadence and gap strata retained. Motion-conditioned keyboard variability should be deferred until keyboard overlap is demonstrably repeated across days. No cognition associations or predictive models were run.

## Privacy and reproducibility

Only saved Parquet event exports were used. No raw text, passwords, raw package names, cognition outcomes, or predictive outputs were accessed. Historical analyses remain unchanged.
