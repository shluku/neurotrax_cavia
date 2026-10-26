# Phase 10 — Continuous ACC × Touch Interaction Features

## Scope

This phase reused the Phase 8 repeated-day Parquet export. No SensorDB queries, cohort expansion, cognition tests, or predictive models were run. Windows were non-overlapping and started at the verified screen-session boundary, so individual sensor samples were never treated as independent observations.

## Feature definitions

For each session, the median three-axis ACC vector was subtracted from every raw x/y/z vector. The residual vector norm is a gravity-referenced motion proxy. It is not calibrated linear acceleration and is not a tremor or typing measure. Within each 30- or 60-second window we calculated:

- ACC sample count, observed coverage, median and 95th-percentile timestamp interval, and >1-second gaps.
- Median, SD, and IQR of the residual motion proxy.
- Touch-event density per minute.
- Touch-interval IQR and CV when at least two touch intervals were available.

Primary window eligibility required at least 50 ACC samples, no >1-second ACC gap, and at least two touch events. Variability coupling required at least three touch events. Cadence strata were retained separately.

## Window feasibility

The complete window table is `window_level_qc_and_features.csv`; the eligibility summary is `window_eligibility_summary.csv`.

| Window | All windows | ACC-QC windows | Density-eligible | Variability-eligible | Sessions with estimable descriptive association |
|---|---:|---:|---:|---:|---:|
| 30 seconds | 69 | 52 | 30 | 28 | 3 |
| 60 seconds | 32 | 21 | 17 | 15 | 3 for density; 2 for variability |

The estimable sessions were concentrated in one day for `dev_72e21d` and one day for `dev_cc373e`. No feature has enough eligible repeated days across patients for reliability estimation.

## Within-session results

`within_session_descriptive_associations.csv` reports Spearman rho descriptively within each session, with no nominal p-values. This avoids treating windows or ACC samples as independent patients. At 30 seconds, density-coupling rho values were approximately −0.24, +0.32, and −0.01 in the three estimable sessions. Variability-coupling values were approximately −0.52, −1.00, and −0.42. At 60 seconds, density values were approximately −0.11 and −0.46 where estimable; variability values were +0.50 and +0.29 in two sessions. The direction changes across sessions and window durations, so these are feasibility observations rather than reproducible effects.

## Sampling and repeated-day limits

The ACC stream ranges from high-rate to low-rate devices. The analysis retains native cadence and gap QC; no raw jerk is pooled. Longer windows reduce the number of available windows, while shorter windows increase event sparsity. The same device can show different cadence across days, so repeated-day comparisons require cadence-matched eligibility.

The repeated-day feature table is `repeated_day_feature_feasibility.csv`. Although ACC exists on repeated days for two devices, eligible continuous interaction windows are not repeated across enough comparable days to estimate reliability.

## Decision

**Continuous ACC measurements are technically usable for a small descriptive pilot, but not yet sufficient for a reliable repeated-day interaction feature.**

The redesign improves feasibility relative to dual-state moving/stationary contrasts: three sessions support descriptive motion-density coupling at 30 seconds, and two sessions support variability coupling at 60 seconds. However, the evidence is concentrated in a few sessions and changes direction across sessions and durations. The next step should be a small rate-matched repeated-day export focused on continuous windows, with predeclared minimum windows per session and at least two comparable days per device before any inferential or cognitive analysis.

Touch and ACC features here are genuinely cross-table. Existing touch-rate, touch-interval, app-transition, and keyboard-IEI summaries remain separate historical features. No keyboard-conditioned continuous feature was evaluated because keyboard overlap remains too sparse.
