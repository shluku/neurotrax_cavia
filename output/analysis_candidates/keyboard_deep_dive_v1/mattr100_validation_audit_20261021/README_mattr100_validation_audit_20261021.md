# MATTR-100 Focused Validation Audit (2026-10-21)

## Scope and source

This audit evaluates the saved T1 MATTR-100 aggregate feature against NeuroTrax Verbal and Motor scores. It reuses the fixed `reliable_completion_count_T1 >= 100` eligibility rule and does not inspect or export raw text, words, vocabularies, hashes, or embeddings. The source was the saved patient-level aggregate table from `word_length_adjusted_completion_v1`; no broad feature search, model training, or historical-output replacement was performed.

The high-coverage subgroup contains 22 patients and the below-threshold group contains 59. MATTR-100 is defined only for the 22 patients with at least 100 reliable word completions.

## Cohort comparison

The high-coverage group had similar age (median 79.5 vs 80.0 years) and sex composition (median coded sex 2 in both groups). Education was slightly higher in the high-coverage group (median 16.5 vs 15 years; one education value missing below threshold). Median Global T1 was 99.9 vs 97.8, Verbal T1 was 108.85 vs 106.0, and Motor T1 was 97.8 vs 99.3 among patients with available scores. These descriptive differences do not establish selection bias, but they show that MATTR-100 is observed in a small, higher-coverage subgroup.

Coverage differences were large: high-coverage patients had median 386 reliable word tokens, 32.5 active days, 159.4 active minutes, and 6,815.5 distinct snapshots, compared with 15 tokens, 5 active days, 9.0 active minutes, and 366 snapshots below the threshold. The below-threshold group had 19 missing reliable-fraction values because no reliable completion was available.

## Associations and historical reconciliation

The new unadjusted estimates reproduce the saved cohort-level correlations: MATTR-100 vs Verbal T1, rho=0.326, p=0.139, n=22, bootstrap 95% CI [-0.146, 0.661]; MATTR-100 vs Motor T1, rho=0.544, p=0.0108, n=21, CI [0.137, 0.819].

The prior saved analyses reported coverage-only partial Spearman estimates of rho=0.607, p=0.00274, q=0.0274 for Verbal (n=22) and rho=0.562, p=0.00797, q=0.1195 for Motor (n=21). Those are retained as historical same-cohort sensitivity estimates and are not independent replication.

This audit added a prespecified parsimonious sensitivity adjustment for log token count, active days, age, coded sex, and education. The Verbal estimate attenuated to partial rho=0.180, p=0.422 (n=22). The Motor estimate remained similar at partial rho=0.539, p=0.0117 (n=21). Because the adjustment is estimated in only 21–22 patients, it is a sensitivity analysis rather than a definitive causal model.

## Coverage, language, and application checks

Within the 22 MATTR-100-eligible patients, MATTR-100 was not significantly associated with total token count (rho=0.164, p=0.465), active days (rho=0.336, p=0.126), active minutes (rho=0.269, p=0.225), snapshot count (rho=0.234, p=0.294), reliable fraction (rho=-0.330, p=0.133), or unique package count (rho=0.286, p=0.197). Unique device count was constant and therefore not estimable. The aggregate “other-language” token count was associated with MATTR-100 (rho=0.466, p=0.0286), whereas Latin token count was not (rho=0.145, p=0.519). Hebrew/mixed-language counts were zero in this saved table. The other-language result is based on a sparse aggregate measure and may reflect language or application composition; it is not a language-independent validation.

## Leave-one-patient-out sensitivity

All leave-one-out correlations retained a positive direction. For Verbal, rho ranged 0.226–0.407 and p ranged 0.0673–0.324; no single omission restored nominal significance across the full range. For Motor, rho ranged 0.483–0.633 and p ranged 0.00273–0.0311; the direction remained positive and the association stayed nominally significant after every single-patient omission. This supports direction stability for Motor, while the small cohort and high coverage requirement remain important limitations.

Verbal and Motor T1 scores were essentially unrelated in the shared MATTR-100 cohort (rho=-0.060, p=0.797, n=21, bootstrap CI [-0.464, 0.367]). Thus the two MATTR associations do not simply reflect a strong overlap between the two cognitive outcomes in this subgroup.

## Interpretation

MATTR-100 is not a robust Verbal signal after the fuller demographic-plus-coverage sensitivity adjustment. The historical Verbal p=0.00274 estimate is therefore coverage/model-specification sensitive and should remain exploratory. The Motor association is more stable in direction and leave-one-out testing, but it is still based on 21 high-coverage patients, has a sparse-language-composition concern, and does not establish that lexical diversity causes or measures Motor ability. The most defensible current conclusion is that MATTR-100 is a potentially interesting but unconfirmed high-coverage-subgroup signal, with stronger evidence for a Motor association than for Verbal.

## Files

- `mattr100_audit_summary_20261021_v1.csv`: new and historical association estimates plus LOO summary.
- `mattr100_cohort_comparison_20261021_v1.csv`: descriptive high/low coverage comparison.
- `mattr100_coverage_language_application_20261021_v1.csv`: aggregate recording, language, and application checks.
- `mattr100_leave_one_out_20261021_v1.csv`: patient-level LOO estimates without raw text.
- `mattr100_privacy_checks_20261021_v1.csv`: privacy validation flags.
- `scatter_mattr100_verbal_T1.png` and `scatter_mattr100_motor_T1.png`: labeled scatter plots with Spearman statistics.

All previous results remain in their original versioned directories.
