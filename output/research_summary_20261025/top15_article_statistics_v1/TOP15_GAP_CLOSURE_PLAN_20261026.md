# Top-15 Article Gap-Closure Plan — 2026-10-26

## Active order of work

1. Build a coverage-adjustment data-availability matrix for the nine top-15 rows without saved recording-adjusted results.
2. Reconstruct the exact cohort for each row from saved patient-level files and document available covariates.
3. Run parsimonious partial Spearman analyses only where the cohort and covariates are adequate; keep baseline and longitudinal estimands separate.
4. Add leave-one-patient-out, outlier, permutation, and bootstrap sensitivity for the restricted-window and legacy rows where sample size permits.
5. Update the manuscript-facing table with adjusted estimates, uncertainty, and explicit missingness.
6. Keep independent validation as a future prespecified cohort or temporal holdout; it cannot be completed with the current data.

## Covariate policy

Use age, sex, and education where available. Add baseline cognitive score for longitudinal outcomes. Add active days and snapshot/valid-interval recording intensity when available. Add device change only when the saved source defines it. Limit covariates for small cohorts and do not select covariates using cognitive results.

## Interpretation policy

Snapshot inter-event intervals remain recording proxies, not true keystroke timing. Correlations and cross-validated prediction remain separate evidence types. Reconstructed FDR values are labeled as derived within-family values and do not control the project-wide search history.

## Current endpoint

The six prespecified longitudinal signals already have coverage-adjusted and robustness outputs. The next work targets the remaining nine top-15 rows: restricted-window rows, baseline partial word-completion rows, and legacy trimmed T1 rows.

The first saved-data join audit is `top15_covariate_join_audit_v1.csv`. It confirms that the exact cohorts can be joined to demographics and T1/T2 keyboard coverage fields from the saved files; it does not yet contain new adjusted associations.
