# Phase 1 Digital Phenotype Wide Rich

This richer wide table was rebuilt from existing extracted Phase 1 subject-window outputs.

Scope:
- Input tables: phase1a_subject_window_features.csv and phase1b_subject_window_features.csv.
- No SQL was queried.
- No new feature extraction was performed.
- Previous outputs were not modified.
- Missing/no_data remains NaN in the rich wide table.
- aware_log is retained as data-quality support only, not a behavioral phenotype feature.

Why this table exists:
- The previous merged wide table omitted some already-extracted Phase 1A subject-window features.
- This rebuild includes safe existing fields such as screen nighttime counts, active-day counts, app breadth, and app-use diversity.

Shape:
- old wide table: 10 rows x 56 columns.
- rich wide table: 10 rows x 79 columns.
- columns added compared with old wide table: 34.

Delta rules:
- Primary count deltas are computed only when both early and late values are non-missing.
- If either window is missing, delta remains NaN and delta_status is missing_early_or_late.
- If both windows exist, delta is late minus early and delta_status is ok_both_windows.

Generated file:
- phase1_digital_phenotype_wide_rich.csv
