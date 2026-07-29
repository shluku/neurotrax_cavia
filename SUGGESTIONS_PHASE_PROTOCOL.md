# Suggestions: coverage-ranked 10-day T1 baseline exploration

This phase tests whether better-observed patients produce a more informative T1 digital phenotype. It uses only the Phase 4 10-day T1 dataset and does not overwrite any existing Phase 4, Phase 4 10-day, Phase 6, or Other Models outputs.

## Cohorts

- **Top 30:** primary exploratory cohort.
- **Top 20:** sensitivity cohort.
- **Top 10:** descriptive only; too small for stable predictive conclusions.

Patients are ranked without using T1 scores: lower feature missingness is preferred, higher table coverage breaks ties, and patient ID provides a deterministic final tie-breaker.

## Models

Each cohort is evaluated with Elastic Net, PLS, Spline Ridge, shallow Random Forest, Extra Trees, HistGradientBoosting, and conservative XGBoost. Preprocessing is fit within each validation fold. Each cohort is compared against its own mean baseline using repeated 5-fold cross-validation.

## Interpretation

Improvement in a high-coverage subgroup does not establish performance for the full cohort. It may indicate that better acquisition quality is necessary for phenotype prediction, or it may reflect selection and small-sample instability. The top-10 results are therefore descriptive and should not be used as evidence of a clinical model.
