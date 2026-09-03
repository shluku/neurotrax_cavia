# Exploratory Empirical Findings (1;4)

This is a separate exploratory comparison of the two opposite ends of the observed baseline cognitive-score distribution.

## Cohort definition

- Lowest group: the 20 participants with the lowest observed baseline global cognitive scores.
- Highest group: the 20 participants with the highest observed baseline global cognitive scores.
- The two groups are selected by deterministic score ordering among participants with a non-missing baseline score.

## Purpose

The purpose is to see whether feature-level p-values and the resulting exploratory model differ when the comparison uses the two extremes rather than the full-cohort median split.

## Model control

The two keyboard features from the original exploratory empirical model remain fixed. This isolates the change in cohort definition. The analysis does not silently replace the features with a new selected set.

## Interpretation

Extreme-group comparisons can produce smaller p-values because the groups are farther apart by construction. They are useful for hypothesis generation, but they do not establish a clinical threshold, a general population association, or independent predictive validity. Model results use the same fold-local mean baseline and repeated cross-validation as the original empirical analysis, but the model cohort is only 40 participants.
