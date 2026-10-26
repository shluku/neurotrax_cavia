# Exploratory Two-Feature Keyboard Analysis: Median-Timespan T1

## Purpose

This isolated exploratory phase examines the two keyboard features that had the
lowest nominal p-values in the earlier median-split comparison of global T1:

- `keyboard_median_word_completion_time_ms`
- `keyboard_inter_event_interval_iqr_ms`

The source is the existing Phase 11 midpoint/median-timespan T1 dataset. No
new SQL extraction is performed and no existing cohort, model, or ACC output is
changed.

## Primary question

How do these two preselected keyboard features vary across observed Global T1
cognitive scores when using all available median-timespan T1 data?

## Analysis definition

- One row represents one patient-level T1 record.
- The digital features are taken exactly as already calculated in the source
  dataset; they are not recalculated here.
- Global T1 is the observed NeuroTrax global score.
- Each feature is plotted separately against Global T1.
- Spearman correlation is reported because the relationship need not be linear
  and the feature distributions are skewed.
- Complete cases are used separately for each feature; the two feature sample
  sizes may differ.
- Cognitive outcomes are used only for this post-selection descriptive
  association analysis. They are not used to create an unsupervised
  representation or cluster.

## Interpretation

The earlier nominal group directions were negative: the higher-T1 group had
lower values for both features. In this phase, a negative Spearman rho means
that the feature tends to decrease as Global T1 increases.

For the word-completion feature, lower values represent shorter typical
inferred word-completion times. For the inter-event IQR feature, lower values
represent a tighter spread of pauses between consecutive keyboard events, not
necessarily faster typing.

These are exploratory associations from a feature panel selected after looking
at the same cohort. They are hypothesis-generating and not independent
validation, causal evidence, or a clinical outcome.

## Reproduction

```bash
.venv/bin/python3 phase_keyboard_two_feature_median_timespan.py
```

Outputs are written to:

`output/analysis_candidates/keyboard_two_feature_median_timespan/`

## Outputs

- `keyboard_two_feature_patient_data.csv` — patient-level plotting data.
- `keyboard_two_feature_associations.csv` — Spearman statistics, p-values,
  coverage, and descriptive group medians.
- `README_keyboard_two_feature_median_timespan.md` — generated output note.

