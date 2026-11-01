# Project Handoff — 2026-11-01

This file is the restart point for the dementia digital-phenotyping project. It records the current dashboard, the latest statistical work, the scientific guardrails, and the next actions.

## Resume the project

Project directory:

`/Users/ofirfizitsky/PycharmProjects/research_dbeaver`

After reopening the terminal or Python environment:

```bash
cd /Users/ofirfizitsky/PycharmProjects/research_dbeaver
git pull
.venv/bin/streamlit run streamlit_app.py --server.headless true
```

Then open: `http://localhost:8501`

The new dashboard page is **Five Leading Keyboard Features**. The existing pages remain available, including **Research Summary and Findings** and **Top-15 Article Statistics**.

## Latest completed work

### Five-feature keyboard summary

The dashboard now summarizes the five leading longitudinal keyboard features from the saved discovery results:

1. Correction-recovery time — ρ=-0.589, n=32, original p=0.000394, exploratory q=0.0134.
2. Afternoon activity spacing — ρ=+0.593, n=28, original p=0.000885, exploratory q=0.0151.
3. Activity-spacing variability — ρ=-0.513, n=33, original p=0.00227, exploratory q=0.0257.
4. Evening activity spacing — ρ=+0.524, n=29, original p=0.00355, exploratory q=0.0302.
5. Morning activity spacing — ρ=+0.485, n=31, original p=0.00572, exploratory q=0.0389.

These are encouraging, interpretable signals around recovery, pace, regularity, and time-of-day behavior. They are not yet a validated biomarker. The strongest next step is independent reproduction under frozen feature definitions and quality rules.

The complete source outputs are in:

`output/analysis_candidates/keyboard_ef_only_fdr_v1/`

Important interpretation: the q-values above are from a **post-hoc, domain-specific exploratory FDR sensitivity analysis** of the complete 34-feature Executive Function-change slice. The original 204-test FDR remains the primary discovery analysis and must be preserved in any manuscript or presentation.

### Statistical multiplicity audit

The versioned audit is in:

`output/analysis_candidates/statistical_multiplicity_audit_v1/`

It reconstructs the original 204 longitudinal feature–outcome tests, reproduces the historical BH values, audits testing families and duplicates, compares defensible multiplicity strategies, and records a patient-level maxT permutation sensitivity analysis. The maxT review did not produce confirmatory evidence for the three headline signals in the existing cohort.

### Confidence-interval expansion

The saved research-summary table with expanded intervals is:

`output/research_summary_20261025/all_associations_with_ci_20261029.csv`

The supporting audit is:

`output/research_summary_20261025/NONKEYBOARD_CI_AUDIT_20261029.md`

Confidence intervals were recomputed only where the saved inputs supported a transparent reconstruction; unavailable rows remain labeled rather than being silently filled.

## Current scientific position

The project has a promising discovery pattern, but the evidence is still exploratory. The most important technical caution is that snapshot-derived inter-event intervals are not direct keypress times. Device/app composition, recording cadence, active-day coverage, and text-change definition can influence the observed associations.

The earlier technical adjustment work also showed that the primary afternoon timing association is sensitive to recording and device-set structure. That result should motivate better measurement and validation, not be described as settled evidence.

## Remaining gaps

- Independent new-participant validation has not yet been performed.
- The five-feature page is a communication summary, not a new analysis or a replacement for the original 204-test family.
- A confirmatory study still needs a prespecified 2–3-feature primary family, outcome definition, quality thresholds, and analysis plan.
- Measurement work should finalize text-change size, event density, active-day coverage, device/app changes, and the interpretation of single-character transitions.
- Effect-size planning should use uncertainty-aware ranges, not the largest discovered correlations.
- Manuscript integration and external validation remain open workstreams.

## Safe closing and reopening

No special Python state needs to be preserved. The important state is saved in the repository and in this handoff file. It is safe to close Python and the Streamlit process after confirming the latest changes are pushed.

On the next session, read this file first, run `git pull`, and start Streamlit with the command above. Continue from the **Five Leading Keyboard Features** page, then inspect the saved audit folders before beginning any new analysis.

## Reproducibility guardrails

- Do not overwrite historical outputs.
- Do not change the original p-values, sample sizes, feature definitions, or 204-test FDR values.
- Label the five-feature q-values as post-hoc domain-specific exploratory FDR.
- Do not claim confirmation without independent participants or a genuinely prespecified confirmatory analysis.
- Keep all post-selection sensitivity analyses separate from the original discovery results.

