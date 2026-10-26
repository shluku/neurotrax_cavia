# Exploratory Keyboard T1–T2 Change and T1 PCA

## Purpose

This isolated phase follows the two preselected keyboard features from the
median-timespan T1 analysis into the paired midpoint T1/T2 windows:

- `keyboard_median_word_completion_time_ms`
- `keyboard_inter_event_interval_iqr_ms`

It also tests whether the two T1 keyboard measurements form a compact
two-dimensional typing-pattern axis using PCA.

No SQL extraction is performed. Existing T1 and T2 feature files are read only;
existing models and the running ACC pipeline are not changed.

## Analyses

### T1–T2 feature change

- Pair patients by `Subject_ID_D`.
- Use the Phase 11 midpoint T1 file and Phase 12 midpoint T2 file.
- Define each digital feature delta as `T2 feature - T1 feature`.
- Show paired T1/T2 values and the distribution of feature deltas.
- Test whether the paired feature delta differs from zero with a two-sided
  Wilcoxon signed-rank test.
- Report the median and mean delta and the number of paired observations.
- As a post-hoc exploratory analysis, correlate feature delta with cognitive
  Global T2–T1 delta using Spearman correlation.

### T1 PCA

- Use only patients with both keyboard features observed at T1.
- Standardize the two features before PCA so milliseconds in the two measures
  do not determine the result solely by scale.
- Report explained variance, loadings, and patient PC scores.
- Cognitive scores are not used to construct the PCA. They may be shown only as
  post-hoc overlays.

## Interpretation boundary

This is a focused exploratory analysis of features selected from the same
project. A nonzero keyboard delta does not establish cognitive decline, and a
PCA component is not a clinical phenotype. The two-feature PCA is useful for
visualizing whether typing speed and typing-rhythm variability move together or
separately; it is not evidence of a validated latent construct.

## Reproduction

```bash
.venv/bin/python3 phase_keyboard_t1_t2_delta_pca.py
```

Outputs are written to:

`output/analysis_candidates/keyboard_t1_t2_delta_pca/`

