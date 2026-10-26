# Top-15 Article Statistics Workstream v1

This workstream isolates the 15 strongest saved feature–cognition rows for focused article preparation. It does not replace the complete 1,871-row association register and does not treat repeated sensitivity rows as independent discoveries.

## Planned phases

1. Confirm exact feature definition, units, and window.
2. Freeze the patient cohort and coverage denominators.
3. Produce patient-level distributions and missingness summaries.
4. Report estimate, n, p, CI, q, and testing context.
5. Attach coverage-adjusted and demographic-adjusted results where they were actually performed.
6. Attach reliability, leave-one-patient-out, outlier, permutation, and alternate-window results where available.
7. Produce article-ready figures and cautious interpretation.
8. Mark independent validation as future work.

`top15_article_evidence_register.csv` is the working evidence table. `top15_analysis_phase_gap_register.csv` identifies what is complete, partial, or missing for each phase. Existing source statistics are preserved exactly; missing statistics are not inferred from unrelated cohorts.

Current scope includes 15 rows selected from the saved Master Association Table by smallest p-value after excluding superseded rows and retaining one saved row per feature–outcome key. The selection is exploratory and should not be described as a new hypothesis test.

## First evidence-audit result — 2026-10-26

The first patient-level reconstruction pass found exact reproduction from saved inputs for 7 of 15 rows. Four additional rows have broad saved T1/T2 inputs but their threshold-defined T2 reliability cohorts are not saved, so they are not treated as exact reproductions. Two restricted midpoint rows have no matching patient-level values saved, and two legacy word-completion rows have broad patient inputs but not the exact trimmed cohorts used by their source associations. The audit and privacy-safe numeric patient table are `top15_reconstruction_audit.csv` and `top15_patient_level_pairs_reconstructable.csv`; descriptive summaries are in `top15_reconstructable_distributions.csv`.

For the seven exact-reproduction rows, `top15_exact_patient_level_table.csv` contains numeric patient-level feature, cognitive, and coverage values, while `top15_exact_distribution_summary.csv` reports medians, IQRs, ranges, change direction counts, and coverage summaries. T1-only rows have no Early/Late change; their Late and change fields are intentionally empty. These tables are descriptive evidence for article preparation and do not constitute independent validation.
