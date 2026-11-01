# Original multiplicity and family audit

## Reconstructed original screen

The saved discovery manifest reports 34 keyboard features, six cognitive outcomes, and 408 association rows:

- 34 features × 6 outcomes = 204 T1 tests.
- 34 features × 6 outcomes = 204 T2−T1 change tests.
- Every original row has a finite Spearman p-value.
- There are no duplicate `(scope, outcome, feature)` hypotheses in the saved discovery table.

The original `fdr_q` values reproduce with maximum absolute difference `1.46 × 10^-14` when BH is recalculated across all 204 tests within each scope. Therefore, the original q-values are scope-level BH values, not family-level q-values.

The `family` column is a scientific grouping used for interpretation and candidate review:

- Circadian: 8 features
- Corrections: 6 features
- Sessions and fragmentation: 6 features
- Timing and variability: 9 features
- Typing volume and production: 5 features

These five families sum to 34 features for each outcome and scope. They were not the multiplicity families used for the original q-values.

## Important distinction

The candidate flag was a post-screen review rule requiring n≥20, q≤.20, bootstrap sign stability≥.80, and a bootstrap CI excluding zero. It did not redefine the original 204-test family. Any later six-signal validation, thirds sensitivity analysis, reliability analysis, or restricted-window comparison is post-selection and must not be described as a new confirmatory family.

## Dependence and redundancy

The longitudinal feature matrix contains 82 feature pairs with absolute Spearman correlation ≥.70 among the 34 originally tested features. Several pairs exceed .98, including broad activity/volume measures and closely related interval measures. This dependence does not justify deleting hypotheses after seeing results; it does justify using dependence-aware calibration and reducing redundancy prospectively in a future protocol.

The six cognitive change outcomes are also correlated, with absolute outcome correlations up to approximately .49. A single global permutation procedure should preserve this dependence if it is used for confirmatory inference.

Machine-readable outputs:

- `bh_reproduction_all_discovery_rows.csv`
- `original_testing_family_audit.csv`
- `duplicate_hypotheses.csv`
- `highly_correlated_longitudinal_feature_pairs.csv`
- `longitudinal_outcome_dependence.csv`
