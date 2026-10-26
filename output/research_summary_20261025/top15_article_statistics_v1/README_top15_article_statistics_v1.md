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

## Corrected T2-reliability cohort audit — 2026-10-26

The first audit classified four T2-reliability rows as threshold-cohort mismatches because it used broad T1/T2 inputs without applying the documented eligibility gates. The underlying `t2_reliability_period_metrics.csv` retains the needed active-day, snapshot, and valid-interval denominators. Matching each historical row to its saved sensitivity scenario and applying the prespecified rule reproduces all four rows exactly: two use at least 500 snapshots in both windows (n=23 each), and two use at least 7 active days in both windows (n=20 each). The corrected audit is `top15_threshold_reconstruction_audit_v1.csv`; patient-level values and descriptive summaries are `top15_threshold_patient_level_table_v1.csv` and `top15_threshold_distribution_summary_v1.csv`. This closes the cohort reconstruction gap for 11 of 15 rows. Rows 1 and 6 still lack exact patient-level inputs, while rows 12 and 14 lack the historical legacy trimming rule.

## Final restricted-window recovery audit — 2026-10-26

The saved `third_patient_data_min7.csv` contains the 19 patients eligible for the first/last-third sensitivity analysis. Rejoining those IDs to the saved 50/50 midpoint features and T2 cognitive changes, then applying the historical complete-case rule, reproduces both restricted same-patient rows exactly at n=18: morning IEI → Attention (rho=.783686, p=.000119) and correction-recovery time → Attention (rho=-.720702, p=.000740). The patient-level table is `top15_restricted_window_patient_table_v1.csv`; the direct reproduction check is `top15_restricted_window_reconstruction_v1.csv`.

The legacy patient table also preserves feature-specific flags identifying the one lowest and one highest observed value removed for each feature. Applying those documented flags reproduces both legacy n=60 associations exactly: word-completion proxy → Attention (rho=-.354479, p=.005455) and Global (rho=-.342235, p=.007439). The audit is `top15_legacy_trimmed_reconstruction_v1.csv`. The consolidated `top15_reconstruction_audit_v2.csv` and `top15_all_reconstructed_patient_level_table_v1.csv` now show **15/15** top findings exactly reconstructable from saved data and documented cohort rules.
