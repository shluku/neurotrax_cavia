# Non-keyboard CI computation audit — 2026-10-29

The dated table `all_associations_with_ci_20261029.csv` preserves the 2025 source table and fills confidence intervals only when the exact saved patient-level matrix and estimand were recoverable.

- Missing CIs before: 509 of 1871 rows.
- Missing CIs after: 421 of 1871 rows.
- Non-keyboard missing CIs before: 99.
- Non-keyboard CIs recomputed: 88 ({'Phase 11 dataset; metadata pending': 2, 'applications_foreground': 3, 'behavioral': 18, 'calls': 5, 'coverage': 18, 'gsm': 3, 'gsm_neighbor': 3, 'locations': 2, 'messages': 2, 'plugin_google_activity_recognition': 5, 'screen': 8, 'telephony': 3, 'temporal': 8, 'touch': 8}).
- Non-keyboard CIs still unavailable: 11.

Phase 4 supplemental rows use paired patient-level bootstrap resampling for the saved Pearson or Spearman estimand. Phase 11 baseline-severity rows use stratified patient bootstrap resampling of Cliff's delta, preserving the observed Global-T1 median split. Rows with no exact saved feature matrix remain unavailable; no substitute cohort or new database extraction was used.

The Streamlit research-summary forest view now prefers the 2026-10-29 table when present and falls back to the 2025 table otherwise.
