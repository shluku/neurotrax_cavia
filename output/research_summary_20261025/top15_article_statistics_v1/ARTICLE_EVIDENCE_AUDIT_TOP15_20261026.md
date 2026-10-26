# Article Evidence Audit — Top 15 Findings

## Scope

This audit evaluates whether the 15 selected exploratory feature–cognition findings have the statistical fields and methodological context needed for manuscript drafting. It uses saved association outputs and saved patient-level files only. No SensorDB query, model training, or broad feature search was performed.

## Completed evidence

- All 15 historical associations are reproducible from saved patient-level inputs and documented cohort rules.
- All 15 rows now have a 95% confidence interval. Historical or previously saved intervals are retained; missing intervals were calculated with a 5,000-resample patient-level Spearman bootstrap on the exact reconstructed cohort.
- All 15 rows now have an FDR value. Saved q-values are retained. Missing q-values were derived only within a stated testing family: partial-p-value BH within the signal-discovery scope, or BH across the 16 preselected legacy tests. These derived q-values must be labeled as post hoc reconstruction and must not be presented as original source q-values.
- Exact cohort rules, n, effect direction, p, CI, q provenance, and reconstruction status are in `top15_article_inferential_audit_v1.csv` and `top15_reconstruction_audit_v2.csv`.

## Evidence still missing or limited

### Coverage adjustment

Saved coverage-adjusted or technical-adjusted results are available for the six prespecified Keyboard Discovery signals only. Nine top-15 rows have no saved coverage-adjusted estimate. The restricted-window findings and legacy T1 rows should therefore remain unadjusted exploratory evidence. The baseline partial-correlation rows have age/sex/education adjustment in the source, but their q-values are derived separately here and are not equivalent to an adjusted validation analysis.

### Robustness

Leave-one-patient-out, outlier, permutation, and reliability outputs are available mainly for the six selected longitudinal keyboard signals. They are not available for the restricted-window, legacy T1, or baseline word-completion rows. These rows should not be described as robust or validated solely because their bootstrap intervals exclude zero.

### Independent validation

No finding has an independent cohort, temporal holdout, or external replication. All top-15 rows are exploratory and share the project’s search history.

### Measurement interpretation

Keyboard IEI and correction features are intervals between text-state snapshots, not keypress timing. The word-completion feature is an observable snapshot proxy with continuity and boundary limitations. Article wording must preserve this distinction.

### Multiplicity

The 15-row display is a selected evidence set, not a new testing family. Its q-values retain their original testing context or are explicitly labeled as reconstructed within-family values. They must not be interpreted as project-wide FDR control.

## Manuscript readiness assessment

The dataset is ready for a transparent descriptive results table and cautious exploratory interpretation. It is not ready for a claim of a validated digital biomarker. The strongest candidate remains afternoon snapshot IEI change versus Executive Function change because it has saved coverage-adjusted and reliability evidence, although its corrected thirds sensitivity is weaker and T2 reliability is limited. The restricted morning/Attention association has the largest effect but is a small post hoc sensitivity result with poor T2 reliability. The legacy word-completion results are nominal baseline associations with reconstructed CIs and post hoc q-values, but no technical adjustment or independent validation.

## Next required work before submission

1. Freeze the primary POC and classify the remaining findings as supplementary exploratory results.
2. Attach the existing coverage-adjusted, reliability, leave-one-out, outlier, and permutation results to the six selected longitudinal signals.
3. Write a candidate-specific limitations paragraph covering coverage, device/app composition, window selection, snapshot semantics, and multiplicity.
4. Separate correlation results from cross-validated prediction results and report the audited model baseline comparison independently.
5. Prespecify an independent or temporal validation protocol before any confirmatory analysis.

