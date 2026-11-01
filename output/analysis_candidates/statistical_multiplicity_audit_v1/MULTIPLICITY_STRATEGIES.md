# Statistically defensible multiplicity strategies

## 1. Original scope-level BH

The original analysis controls expected false discovery rate under standard BH assumptions across the full 204-test T1 scope and separately across the full 204-test longitudinal scope. Positive dependence among tests is often compatible with BH, but arbitrary dependence can require more conservative procedures. This is the correct historical result and must remain the primary exploratory reference.

It does not support confirmatory claims because the hypotheses and feature families were explored in the same cohort, and the six-signal set was selected after screening.

## 2. Hierarchical or grouped testing

A future hierarchy could define one primary outcome and a small number of scientifically justified feature families. A gatekeeping procedure could test a family-level Simes p-value first, then test prespecified members only after the gate passes. This can control FWER or a structured FDR, depending on the exact procedure.

Assumptions: the hierarchy, family membership, primary outcomes, and allocation of alpha are fixed before outcome review; family-level hypotheses are scientifically meaningful; within-family dependence is handled by the chosen procedure.

The current grouped q-values are descriptive sensitivity comparisons only. They are not confirmatory because the family structure was examined after discovery and the family-level gate was not prespecified.

## 3. Dependence-aware permutation / maxT

The audit includes a 1,000-replicate maximum-statistic permutation calibration over the 204 longitudinal tests. The same patient-level outcome permutation is used across feature tests within each outcome, preserving patient independence and major feature-dependence structure. It is unadjusted for nuisance covariates.

This controls an approximate strong FWER under exchangeability of the outcome labels within the eligible paired cohort and under the null. The headline maxT p-values remain large: approximately .341 for correction-recovery/Executive Function, .323 for afternoon IEI/Executive Function, and .694 for IEI-CV/Executive Function.

This is a useful robustness calibration, not a confirmatory rescue. A future confirmatory version should prespecify a covariate-adjusted Freedman–Lane or equivalent permutation scheme, preserve the exact matching and missingness rules, and use more replicates with a frozen primary family.

## 4. Outcome-independent composite

A composite of timing/irregularity features could improve precision if its direction, scaling, feature membership, missingness rule, and weights are fixed independently of cognitive outcomes. It could then be tested as one primary hypothesis, with FWER controlled across a small number of composites or outcomes.

The current data cannot support a confirmatory composite because feature directions and candidates were selected using cognitive outcomes. An outcome-informed composite would be post-selection and exploratory. Independent validation is required even if a composite appears stable in the current cohort.

## 5. Future 2–3 hypothesis family

The cleanest future design is one primary hypothesis—afternoon IEI change versus Executive Function change—or at most three fully prespecified hypotheses with Bonferroni/Holm FWER control. A new participant cohort or genuine temporal holdout is required. Reanalysis of the original cohort cannot supply independent confirmation.

The sample-size scenarios in `confirmatory_sample_size_scenarios.csv` suggest approximately 82–105 independent usable participants for 80–90% power at |rho|=.35 under a three-hypothesis Bonferroni family, before inflation for missingness, coverage failure, or model complexity. A practical target is approximately 100–120 usable participants.
