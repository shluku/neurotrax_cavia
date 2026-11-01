# Confirmatory design and power planning

## Estimand

The confirmatory estimand should be a patient-level association between a frozen digital feature measured in a prespecified pre-assessment window and a prespecified cognitive outcome, or a predictive performance difference against a fixed mean baseline. The current post-T1 window is concurrent with the assessment and should not be called prospective prediction.

## Recommended design

1. Recruit or reserve independent participants not used in the current discovery.
2. Freeze one primary feature/outcome hypothesis, or at most three hypotheses with Holm/Bonferroni FWER control.
3. Freeze the window, coverage eligibility, device/app harmonization, feature calculation, nuisance covariates, missingness rule, and analysis code before outcome review.
4. Preserve patient-level independence and use a covariate-adjusted permutation or rank-residual model only if the exact procedure is prespecified.
5. Report the estimate, 95% CI, multiplicity-adjusted p-value, coverage, device changes, and an influential-patient analysis.

## Plausible effect sizes

The discovered absolute correlations (.51–.59) are likely optimistic because they were selected from 204 tests. The technical adjustment for the primary afternoon signal is .356, with a wide interval and p=.113. Planning around |rho|=.35 is therefore more defensible than planning around .59.

Approximate independent usable sample sizes:

- One primary hypothesis, |rho|=.35: n≈62 for 80% power; n≈82 for 90% power.
- Three primary hypotheses with Bonferroni FWER=.05, |rho|=.35: n≈82 for 80% power; n≈105 for 90% power.
- For a more conservative |rho|=.30 under three hypotheses: n≈113 for 80% power and n≈145 for 90% power.

These are correlation-test approximations, not substitutes for simulation. Inflate the recruitment target for unusable coverage, missing cognitive outcomes, device changes, and any prespecified covariate adjustment. A practical target is approximately 100–120 usable independent participants for a three-hypothesis design at an effect around .35.

## Reanalysis versus confirmation

Reanalysis of the current cohort can improve measurement characterization, uncertainty reporting, and robustness. It cannot establish independent confirmation because the cohort, outcomes, and search history are shared with the original discovery.
