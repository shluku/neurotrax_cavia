# Phase 6 — ACC × Touch Temporal Coupling Validation

## Cohort and data

This validation reused the Phase 5 Parquet export and did not query SensorDB or expand the cohort. It contains **2 independent patients, 2 devices, 4 device-days, and 7 sessions with usable touch and ACC data**, totaling **251 touch events**. Individual ACC samples were used to form event profiles, but inference was summarized at the session level.

The devices were retained separately by observed cadence. Sessions included high-rate (median interval ≤20 ms), mid-rate (20–100 ms), and low-rate (>100 ms) strata. ACC gaps, duplicate timestamps, sample counts, and profile coverage are reported in `session_validation_summary.csv`. No raw jerk was calculated.

## Original pilot results

The saved direct-window pilot contained seven usable sessions. The within-session median event-minus-control differences were:

- ±500 ms: median **+0.0003**, mean **−0.0448**, range **−0.3718 to +0.0524**.
- ±1,000 ms: median **+0.0010**, mean **−0.0095**, range **−0.0822 to +0.0700**.

The sign and magnitude changed across sessions, especially in the low-rate device/session. Widening the window reduced the largest negative outlier but did not create a consistent positive effect.

## Event-triggered profiles

`event_triggered_profiles.csv` contains 100-ms bins from −2,000 to +2,000 ms around each touch event, aggregated within sessions. Each profile is baseline-subtracted using the −1,500 to −500 ms pre-touch region, then contrasted with matched non-touch windows from the same session. The profile plot is `event_triggered_motion_profile.png`.

The observed session-level central contrast (−500 to +500 ms) had median **+0.0080** and mean **−0.0282**. A session bootstrap 95% interval was **−0.1266 to +0.0461**. This interval is wide and includes zero.

## Matched controls and temporal negative controls

Control windows were selected within the same verified session, away from true touch neighborhoods and with available ACC coverage. The negative-control analysis shifted touch timestamps within session boundaries, excluded true touch neighborhoods, and repeated the procedure 50 times per session. It produced **340 shifted-control contrasts**. Their median was **+0.0008**, and the 95th percentile of absolute contrasts was **0.1738**. The observed median is therefore close to the negative-control distribution and is not clearly separated from ordinary within-session timing variation.

## Cadence sensitivity

| ACC stratum | Sessions | Patients | Median event-profile contrast |
|---|---:|---:|---:|
| ≤20 ms | 2 | 1 | +0.0683 |
| 20–100 ms | 3 | 2 | −0.0004 |
| >100 ms | 2 | 1 | −0.0293 |

The high-rate stratum shows a positive descriptive contrast, but it is based on two sessions from one device/patient. The direction is not reproduced in the mid- or low-rate strata. ACC gaps and profile coverage also differ by device, so this pattern cannot be interpreted as a stable touch-linked motion response.

## Decision

**Technically measurable but unstable — improve extraction or processing.**

Touch-centered ACC values can be computed from the synchronized export, but this pilot does not demonstrate a reproducible motion signal beyond matched arbitrary timestamps. The observed contrast is small relative to its session uncertainty and overlaps the temporal negative-control distribution. The main unresolved issue is heterogeneous sampling cadence and gaps, not lack of computability.

The next technical step should be a prespecified rate-homogeneous validation, preferably repeated sessions from the same device and cadence stratum, with a fixed minimum coverage rule and a robust filtering/resampling method. Do not expand cohort extraction or test cognition until that rule is fixed.

## Privacy and reproducibility

No text, words, passwords, raw package names, production device IDs, cognitive variables, or model outputs were used. The validation script is copied into this directory. Existing Phase 5 files and all historical outputs are unchanged.
