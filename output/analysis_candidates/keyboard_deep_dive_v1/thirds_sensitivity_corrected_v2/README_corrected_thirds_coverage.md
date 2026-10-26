# Corrected First/Last Third Coverage Analysis v2

This version reruns only the coverage-adjusted correlations from the historical First/Last Third analysis. The snapshot denominator is canonical `distinct_observations_in_window`, rather than raw SQL row count. The historical directory is unchanged.

- Cohort: 19 participants, at least 7 active days in each third.
- Features: 34 longitudinal keyboard features.
- Outcomes: Global, memory, executive function, processing speed, attention, motor, verbal, IQ.
- Adjustment: age, sex, education, mean active days, mean canonical snapshots.
- Statistics: partial Spearman, 500 bootstrap confidence intervals, BH FDR across 272 feature-outcome rows.

No corrected result passed FDR; the smallest q-value was 0.836. The inter-event-interval CV / executive-function association was ρ=-0.576 (p=.031, q=.836, 95% CI -0.933 to 0.024). Correction-recovery time / executive function was ρ=.014 (p=.962, q=.974, 95% CI -0.699 to 0.748).

The result is exploratory and remains limited by the small cohort and text-state snapshot proxy timing.
