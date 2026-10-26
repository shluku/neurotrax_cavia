# T1-only Lexical and Word-Timing Cognitive Analysis — v1

This is an additive cross-sectional exploratory analysis using the saved strict continuity aggregates from `word_length_adjusted_completion_v1` and `lexical_feature_feasibility_v1`. It does not require T2 data, does not modify historical results, and does not train or integrate models.

## Cohort and timing

The primary cohort includes all 81 patients with valid Global T1 scores and a saved T1 keyboard window row. Sixty-two patients have at least one reliable continuous reconstructed token. The documented T1 window begins 0.083 days before the T1 assessment at the median (approximately two hours), with observed start offsets from −0.125 to −0.083 days. This timing is inherited from the existing window definition and was not selected using cognition. No T2 data were used.

Prespecified coverage subsets were minimum 20, 50, and 100 reliable tokens. The full eligible cohort and each subset are reported in `t1_eligibility_coverage_20261021_v1.csv`. MATTR-50 requires 50 tokens, and MATTR-100/MTLD require 100 tokens. Simpler timing, length and TTR/repetition measures use 20 reliable tokens.

## Extraction validation

The saved extractor enforces exact previous-current continuity, password exclusion, device/application-local processing, duplicate handling, correction and multi-character-jump flags, and aggregate-only output. No raw text, words, vocabularies, hashes, excerpts or embeddings were accessed or exported in this T1 analysis. The saved v1 output does not contain time-of-day lexical fields or a word-length IQR; those measures are explicitly not imputed. Word-length SD is used as the available length-variability measure.

## Statistical design

Three testing families were fixed before evaluating outcomes: (1) lexical diversity/repetition versus Verbal and Global T1; (2) word length versus Verbal and Global T1; and (3) timing/variability versus Attention, Processing Speed and Executive Function T1. Spearman correlations use all eligible patients for each feature/outcome pair. Confidence intervals are 2,000 patient bootstrap percentile intervals. BH q-values are calculated within each family. Coverage-adjusted results use rank-residual partial Spearman correlations controlling for active days, canonical observations, valid intervals, package count, device count and reliable fraction. A fixed minimum-100-token sensitivity is also reported.

## Results

There are 49 valid feature/outcome estimates and 4 nominal p<.05 results. None passes unadjusted family-level FDR q<.05. The smallest nominal results are:

- Completion-time MAD vs Attention T1: ρ=−0.319, n=50, p=0.0240, bootstrap CI [−0.562, −0.023], q=0.336; coverage-adjusted ρ=−0.286, p=0.0439, q=0.468.
- Completion-time IQR vs Attention T1: ρ=−0.308, n=50, p=0.0295, CI [−0.552, −0.014], q=0.336; coverage-adjusted ρ=−0.268, p=0.0604, q=0.468.
- Length-residual SD vs Executive Function T1: ρ=−0.288, n=50, p=0.0422, CI [−0.566, 0.007], q=0.336; coverage-adjusted ρ=−0.196, p=0.172, q=0.472.
- 4–5-character-group completion IQR vs Executive Function T1: ρ=−0.284, n=50, p=0.0458, CI [−0.514, 0.006], q=0.336; coverage-adjusted ρ=−0.212, p=0.140, q=0.468.

The adjusted MATTR-100/Verbal result is ρ=0.607, p=0.00274, q=0.0274, n=22, but it is based on only 22 patients and 100-token eligibility; it is an unstable exploratory sensitivity and does not establish lexical validity. The fixed-100-token sensitivity generally weakens the nominal timing results.

The historical legacy word-completion/Attention finding was ρ=−0.354, n=60, p=0.00545 after source-specific extreme-value removal. It is not an independent replication: the present analysis reuses the same underlying cohort and has stricter continuity rules, different feature definitions, and different eligible samples.

## Interpretation and limitations

The nominal timing findings suggest that greater variability in observable completion intervals may accompany lower Attention or Executive Function scores, but they do not survive family-level FDR and weaken after coverage adjustment. The lexical results are dominated by token availability; MATTR-100 and MTLD are estimable in only 22 patients. Low or missing values must not be interpreted as low vocabulary diversity. Snapshot completion duration remains a recording proxy, not true word-typing time. Application composition, device changes, language mixture, incomplete sequences, predictive text, paste operations and text quantity remain potential confounders.

The complete outputs are: `statistical_results_20261021_v1.csv`, `significant_results_p_lt_0_05_20261021_v1.csv`, `t1_eligibility_coverage_20261021_v1.csv`, `assessment_to_recording_timing_20261021_v1.csv`, `feature_dictionary_20261021_v1.csv`, `supervisor_results_20261021_v1.csv`, `privacy_reproducibility_checks_20261021_v1.csv`, and the leading-association scatter PNGs. No result is suitable for confirmatory or predictive use without an independent cohort and validated text-state reconstruction.
