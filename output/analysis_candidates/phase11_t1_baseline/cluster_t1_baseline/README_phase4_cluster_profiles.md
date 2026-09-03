# Phase 4 Exploratory Cluster Profiles and Stability

This stage creates interpretable descriptive profiles for the full-cohort exploratory clusters and tests whether the two-cluster solution remains similar after reducing coverage-related effects.

## Profile Rule

Profiles use standardized feature means and ranked absolute cluster differences. They describe relative digital feature patterns only. They are not clinical subtypes.

## Stability Checks

- `full_primary_features`: all 81 patients and 37 primary features.
- `high_coverage_patients_primary_features`: patients with feature missingness <=50% and table coverage >=50%.
- `strict_feature_coverage_full_patients`: all patients, limited to primary features missing in <=25% of the cohort.

`ari_vs_full_primary_solution` compares each controlled solution with the original full-cohort labels. Low or moderate ARI means the original clusters are sensitive to coverage restrictions and should not be treated as stable phenotypes.

## Outputs

- `phase4_cluster_profiles.csv`: patient-level cluster profile summaries.
- `phase4_cluster_profile_features.csv`: ranked standardized feature patterns.
- `phase4_cluster_stability.csv`: coverage-control stability comparisons.
