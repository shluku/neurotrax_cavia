# Phase 11 baseline cognitive severity tables

These tables compare the Phase 11 midpoint-span T1 cohort using an exploratory
median split of observed `global_T1`.

- Lower observed T1: global T1 <= 99.40 (n=41)
- Higher observed T1: global T1 > 99.40 (n=40)
- Participants with observed global T1: 81
- Digital features included: 61

This is a data-driven comparison, not a validated clinical severity or
impairment diagnosis. If a validated clinical cutoff becomes available, this
table should be regenerated with that prespecified threshold.

The detailed feature table includes every measured digital feature available in
the Phase 11 patient dataset, including features outside the primary model.
Missing values are not converted to zero or median-imputed for this descriptive
comparison. Each feature is summarized from its available observations, and
`n_lower`/`n_higher` make the coverage visible.

Feature p-values are two-sided Mann-Whitney U tests. `q_value_fdr_bh` is the
Benjamini-Hochberg false-discovery-rate adjustment across the tested features;
these results are exploratory and require validation in a larger cohort.
`effect_size_cliffs_delta_higher_minus_lower` is positive when the higher-T1
group tends to have larger feature values.
