# Other Models: exploratory Phase 4 10-day T1

This is an isolated exploratory phase. It uses the Phase 4 10-day patient-level T1 dataset and does not overwrite the primary Phase 4, Phase 4 10-day, or Phase 6 outputs.

## Objective

Search for nonlinear, interaction, latent-domain, and regularized patterns that a simple linear Ridge model may miss. The objective is both predictive comparison and hypothesis discovery; this phase is not a validated clinical model.

## Models

- Elastic Net
- PLS regression
- Spline Ridge for smooth nonlinear effects
- Shallow Random Forest
- Shallow Extra Trees
- Conservative HistGradientBoosting
- Conservative XGBoost

All seven models use the same 81 patients, all selected 10-day features, fold-local median imputation with missingness indicators, and repeated 5-fold cross-validation. Tree models use shallow depth, minimum leaf sizes, subsampling, and regularization to limit overfitting.

## Interpretation rules

The mean baseline is recalculated within every training fold and is the reference for every comparison. Lower RMSE and MAE are better. A model that fits the training data but does not beat the mean baseline in repeated validation is not considered predictive.

Held-out permutation importance is descriptive only. It is calculated on the five folds of the first repeated validation pass and is not used for feature selection or refitting.

## Current status

The first run produced no improvement over the mean baseline. Elastic Net was closest; the tree models and PLS were worse. This is a negative predictive result, but the phase remains useful for documenting whether nonlinear or interaction-based searches reveal stable candidate patterns.
