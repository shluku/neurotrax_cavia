# Manuscript Outline

## Working title

From SensorDB to Patient-Level Digital Phenotyping: A Coverage-Aware Proof-of-Concept Study of Baseline Cognition in Dementia

## Abstract

- Background: passive sensing may provide repeated behavioral information, but patient-level phenotype construction is affected by sparse coverage, heterogeneous devices, and missing data.
- Objective: build and audit a reproducible patient-level digital phenotyping workflow and explore its relationship with baseline cognition.
- Methods: describe cohort, windows, feature families, coverage audit, domain outcomes, imputation, and cross-validated regularized models.
- Results: summarize cohort size, feature availability, missingness, exploratory feature findings, and performance relative to the mean baseline.
- Conclusion: the workflow is feasible and exposes important measurement constraints, but the current cohort does not support a clinically reliable prediction score.

## 1. Introduction

1. Dementia and the need for scalable cognitive monitoring.
2. Digital phenotyping and passive smartphone sensing.
3. Why patient-level prediction is harder than feature-level association.
4. The specific gaps addressed: time-window definition, coverage, missingness, interpretability, and transparent baselines.
5. Study objective and contribution.

## 2. Methods

### 2.1 Cohort and cognitive assessments

Describe participants, T1/T2 assessments, available domains, and the observational nature of the cohort.

### 2.2 SensorDB and observation windows

Describe raw tables, patient/device mapping, T1 anchoring, midpoint-span construction, fallback rule, and sensitivity windows.

### 2.3 Feature taxonomy

Describe behavioral, communication, keyboard, screen, telephony, activity, and supplemental modality families.

### 2.4 Coverage and missingness audit

Define table coverage, feature coverage, patient-level missingness, and the distinction between no observed data and a measured zero.

### 2.5 Outcomes and cognitive domains

Define global T1 and the domain outcomes, including the exploratory baseline-severity comparison.

### 2.6 Statistical analysis

Describe descriptive summaries, multiplicity correction, effect sizes, training-fold imputation, robust scaling, Ridge models, cross-validation, metrics, and the common mean baseline.

### 2.7 Interpretation safeguards

State that feature selection and model evaluation from the same cohort are exploratory, no external validation was performed, and no clinical threshold was derived.

## 3. Results

### 3.1 Cohort and data availability

Table 1: participant and cognitive assessment characteristics.

### 3.2 Feature coverage and missingness

Figure 1: pipeline from raw data to patient-level phenotype.

Figure 2: coverage and missingness overview.

### 3.3 Feature relationships with baseline cognition

Present the all-feature clinical-style table and clearly label nominal keyboard findings as exploratory and not FDR-confirmed.

### 3.4 Baseline digital phenotype models

Present observed-versus-estimated plots, mean baseline comparison, model metrics, and calibration or residual summaries.

### 3.5 Cognitive-domain analyses

Present domain-specific results only if the cohort and missingness support a clear interpretation; otherwise move detailed plots to the supplement.

## 4. Discussion

1. Main finding: the pipeline is feasible, but reliable patient-level prediction is not established.
2. Why feature-level trends did not translate directly into prediction.
3. Coverage and missingness as measurement properties of the phenotype.
4. Value of transparent baselines and interpretable models.
5. Relationship to prior feasibility and reproducibility work.

## 5. Limitations and future work

- Small single-cohort sample.
- No external validation.
- Heterogeneous observation and device coverage.
- Exploratory feature selection on the same cohort.
- Potential sensitivity to observation-window definition.
- Need for prospective collection, larger cohorts, prespecified features, and independent validation.

## 6. Conclusion

The study establishes an auditable foundation for patient-level digital phenotyping and identifies the data-quality and validation requirements that must be addressed before clinical use.

## Planned main artifacts

- Table 1: cohort and cognitive assessment summary.
- Table 2: coverage and missingness summary.
- Table 3: primary model comparison against the mean baseline.
- Figure 1: data-to-phenotype pipeline.
- Figure 2: feature coverage and missingness.
- Figure 3: observed versus estimated baseline cognition.
- Supplement: complete feature tables, domain plots, window comparisons, and exploratory models.
