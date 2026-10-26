# Keyboard Deep Dive: First/Last-Third Sensitivity Analysis

This is an exploratory sensitivity analysis of the keyboard Deep Dive midpoint design. It does not replace or overwrite the 50/50 midpoint results and does not train predictive models.

## Protocol

For each patient with ordered NeuroTrax T1 and T2 dates, the actual local-calendar interval `[T1, T2)` is divided into three equal-duration calendar periods. Only the first third and last third are queried from the timestamped `keyboard` table. The middle third is excluded. The two period summaries use the same 34 keyboard features as the original Deep Dive. Feature change is defined as `last_third - first_third`. Missing observations remain missing; they are never converted to zero activity.

The raw query is restricted to mapped keyboard devices and the exact third boundaries. The extractor is [`keyboard_thirds_sensitivity.py`](../../../../keyboard_thirds_sensitivity.py). The extraction path reuses the established privacy-safe event parser and feature definitions from [`keyboard_deep_dive.py`](../../../../keyboard_deep_dive.py), while preserving this analysis in its own directory.

## Coverage and eligibility

`third_coverage.csv` reports active days, raw snapshots, valid intervals, and recording intensity for each third. `third_eligibility_summary.csv` reports the number of patients meeting prespecified active-day thresholds in both thirds (0, 7, 14, and 28 days). No threshold is selected from cognitive outcomes.

## Cognitive associations

The analysis tests Spearman associations between each first/last-third feature change and T2−T1 cognitive change for Global and available NeuroTrax domains. It reports 500 bootstrap 95% confidence intervals and Benjamini–Hochberg FDR q-values. A parsimonious rank-based sensitivity adjustment includes age, sex, education, mean active days, and mean snapshots across the two thirds.

The six previously discovered keyboard candidates are included explicitly. Because this is a window-design sensitivity analysis, results are interpreted as exploratory and are not independent validation.

## Comparison with the 50/50 design

`third_vs_midpoint_comparison_same_patients.csv` compares the first/last-third and original midpoint changes on the same eligible patients. This separates window-definition effects from cohort-composition effects. `third_coverage_comparison.png`, `third_vs_midpoint_associations.png`, and `third_selected_feature_correlations.png` are the reproducible figures.

## Limitations

Keyboard timestamps are text-state snapshots rather than true key-down/key-up events. Inter-event and correction measures are therefore behavioral proxies. Equal calendar thirds do not guarantee equal active-day coverage. Sparse or highly tied features may yield non-estimable correlations. The middle third is intentionally excluded, so this sensitivity analysis is not a model-training dataset.
