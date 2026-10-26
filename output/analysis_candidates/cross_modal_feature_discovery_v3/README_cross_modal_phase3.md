# Cross-Modal Phase 3 — Cohort-Scale Longitudinal Feasibility

## Status
The Phase 2 synchronization pilot was reused as the validated event-level base: 2 patients, 2 same-device days, and 60 verified unlocked sessions. Screen×Touch, Screen×Foreground App, and Keyboard×Foreground App aggregate features are available for these sessions.

An expansion attempt used read-only bounded queries on five additional coverage-selected devices and their first/last observed event days. The remote event-table retrieval did not complete within the safe query budget, so those patients were not added to the feature tables. No calendar overlap was treated as synchronization and no values were imputed.

## Pilot results

- Touch event rate, touch interval median/IQR/CV, and >30-second gap counts were computed within verified sessions.
- Foreground-app transitions per active minute, distinct observed applications, and transition fraction were computed.
- Keyboard snapshot interval median/IQR were computed within same-app segments, with password rows excluded and text retained only in memory.
- Foreground-app episode duration was not retained because isolated package observations did not establish a defensible duration.
- 1-, 5-, 10- and 15-minute within-session slices were generated. Both pilot patients contributed windows at every duration, but only the longer windows produced useful event counts consistently.

## Reliability and longitudinal limits

No ICC or early/late change estimate is reported. Each pilot patient contributed one observation day, so day-to-day and week-to-week repeatability cannot be estimated. The `reliability_summary.csv` and `longitudinal_early_late_summary.csv` files explicitly mark these quantities as not estimable.

The next cohort-scale run requires either a local/replicated event store or a larger bounded-query budget with checkpointing. It should retrieve one fixed early and one fixed late day per patient, then calculate the same session features and ICCs before any NeuroTrax analysis.

## Ranking for the next run

1. Screen×Touch event rate and interval variability: strongest current technical feasibility and direct event matching.
2. Screen×Foreground App transition rate and transition fraction: feasible, but app-event semantics and system packages remain confounders.
3. Keyboard×Foreground App snapshot intervals: feasible as a text-state timing proxy, but lower event density and app-specific logging make it more fragile.

No cognition tests or predictive models were run.
