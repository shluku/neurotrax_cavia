# Measurement, confounding, and robustness audit

## Strongest longitudinal signals

| Signal | Discovery rho | Original q | Recording-adjusted partial rho | Adjusted p | Adjusted 95% CI |
|---|---:|---:|---:|---:|---:|
| Correction-recovery change → Executive Function change | −.589 | .080 | −.303 | .150 | [−.666, .079] |
| Afternoon 12–18 IEI change → Executive Function change | +.593 | .090 | +.508 | .022 | [.103, .786] |
| IEI-CV change → Executive Function change | −.513 | .154 | −.211 | .311 | [−.620, .184] |

The broader afternoon mechanism audit adds text-change size, long-pause rate, package continuity, device change, active-day change, interval-count change, and events per active day. The afternoon IEI/Executive Function estimate attenuates from .593 to .356 (p=.113) after all seven technical factors. This is the most important robustness result.

## Recording and device composition

In the exact afternoon primary cohort (n=28):

- 22/28 participants changed device set between windows.
- Median package-set Jaccard similarity was .233.
- IEI change correlated with active-day change (rho=−.489, p=.0082), interval-count change (rho=−.515, p=.0051), and events per active day (rho=−.545, p=.0027).
- The technical factors also relate to Executive Function change.

This pattern makes a clean behavioral interpretation inappropriate. The signal is compatible with a mixture of behavior, measurement opportunity, app/device composition, and snapshot cadence.

## Text-change sensitivity

The saved audit includes median absolute text-length change, signed text-length change, long-pause rate, and related event-density summaries. These are sensitivity covariates, not keystroke measures. They do not verify that a snapshot interval corresponds to a user typing continuously.

Single-character transitions cannot be reconstructed from the saved aggregate mechanism file because raw before/current text transitions were not retained in the audit output. A cleaner sensitivity analysis would require a new authorized extraction of row-level snapshots with a prespecified rule such as: same device and package, adjacent valid snapshots, absolute text-length change exactly one, no password field, no duplicate timestamp/value, and a maximum gap threshold. Even then, the measure would be a snapshot-transition proxy, not a direct keypress interval.

## Influential-patient and reliability evidence

The saved leave-one-patient-out checks preserve the sign for the three headline signals. Maximum absolute LOO changes were approximately .048, .059, and .051 for correction-recovery, afternoon IEI, and IEI-CV respectively. This indicates no single patient reverses the unadjusted direction, but it does not resolve recording/device confounding.

The corrected-thirds sensitivity is weaker, especially after coverage adjustment. T2 test–retest reliability is uneven; the afternoon IEI signal has T2 ICC≈.416, while morning IEI has poor T2 reliability. These results support technical feasibility and hypothesis prioritization, not validation.

All analyses in this document are exploratory or sensitivity analyses. They must not be used to relabel the original discovery as confirmatory.
