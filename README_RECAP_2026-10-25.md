# Research recap — 2026-10-22 to 2026-10-25

This recap records the latest work and is intended as the starting page for the next research week. All work remained exploratory and used saved outputs unless explicitly stated.

## What was completed

### Cross-modal decision gate

The latest synchronized Parquet export was audited before considering more ACC extraction. It contains 17 verified same-device screen sessions across 5 patients, 5 devices, and 9 patient-device-days. ACC was present in 10 sessions, 4 passed the existing sampling/gap quality-control rules, and only 1 contained both prespecified motion states. ACC–keyboard overlap was available in 2 sessions. The decision is to defer broad ACC expansion until a new, repeated-day, cadence-stratified sample can be obtained.

### New non-ACC cross-table candidates

Four event-linked candidates were evaluated without cognitive testing:

1. App-switch recovery latency to the next touch or keyboard event.
2. App-switch interaction disruption before versus after a transition.
3. Screen-resume latency to the first observed interaction.
4. Cross-modal interaction fragmentation linking touch inactivity, app transitions, and keyboard interruptions.

The export contained 137 app transitions. A later touch was observed after 110 transitions; a later keyboard snapshot after 22. Screen-resume latency was measurable in all 17 sessions. Keyboard recovery had no repeated-day patient coverage, and matched controls for disruption were not yet established. The recommended next implementations are screen-resume latency and app-switch recovery.

### Historical findings register and forest plot source

The complete Master Association Table remains the source of truth for saved digital-feature/cognition associations. The new forest-plot source is a transparent view of the 15 smallest saved p-values after excluding superseded rows and retaining one strongest saved row per feature–outcome key. Repeated sensitivity analyses are still labeled in the source columns and must not be treated as independent discoveries.

The strongest numerical association in this view is a restricted midpoint comparison between morning keyboard snapshot inter-event interval change and Attention change (Spearman ρ=.784, n=18, p=.000119). It is a small sensitivity cohort and is not confirmatory. The broader exploratory candidate remains afternoon snapshot inter-event-interval change versus Executive Function change, which has technical measurement limitations because snapshot intervals are not true keystroke timing.

## Current interpretation

The project has a large exploratory evidence register, but the most compelling correlations are concentrated in small keyboard cohorts and repeated window/sensitivity analyses. Cross-modal ACC work is currently constrained by missing or irregular motion coverage. Event-linked non-ACC measures have better immediate coverage and clearer timestamps, but they remain observational proxies and require repeated-day reliability work before cognitive testing.

## Next week’s working page

The Streamlit page **Research Summary and Findings** is now the review surface for:

- project status and recent decisions;
- the top-15 saved association forest plot;
- exact p-values, effect estimates, sample sizes, confidence intervals where saved, and source files;
- links to the historical association register and the latest cross-modal decision outputs.

On 2026-10-25, the top-15 table was audited for missing confidence intervals. Four rows had matching saved patient-level inputs, so 500-resample partial-Spearman bootstrap intervals were added for the T1 word-completion and morning interval-IQR associations. Restricted midpoint and legacy trimmed rows remain explicitly without CIs because their exact patient-level cohorts were not saved. See [CI audit](output/research_summary_20261025/CI_AUDIT_20261025.md).

The same audit now provides a large all-association view: 1,871 historical rows, 990 saved CIs, 372 additional CIs recomputed from exact saved patient-level inputs, and 509 rows still marked unavailable. This full table is available in the Streamlit summary section and in [all_associations_with_ci_20261025.csv](output/research_summary_20261025/all_associations_with_ci_20261025.csv).

The focused [Top-15 Article Statistics workstream](output/research_summary_20261025/top15_article_statistics_v1/README_top15_article_statistics_v1.md) now organizes the selected rows into eight article-preparation phases: definition, cohort/coverage, patient-level distributions, raw association reporting, adjusted robustness, reliability/sensitivity, figures/interpretation, and independent validation. The dedicated Streamlit page is the working review window for completing these phases.

Future updates should be added to this recap and the existing handoff README, preserving historical results and explicitly separating exploratory associations from validated predictive performance.
