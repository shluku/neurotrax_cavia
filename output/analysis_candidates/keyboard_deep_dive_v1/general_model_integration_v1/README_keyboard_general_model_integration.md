# General Cognitive Model Integration v1

`keyboard_general_model_integration.py` compares the existing digital Feature Bank with an expanded bank containing 34 deep-dive keyboard features. Existing keyboard columns are replaced by the expanded set; recording coverage covariates are included in both variants.

T1 and T2-minus-T1 are separate tasks. For every outcome, the two variants use identical patient cohorts and repeated outer folds. The mean baseline is computed from each training fold. The model pipeline fits median imputation with indicators, robust scaling, `SelectKBest(f_regression)`, and Ridge alpha tuning strictly within the training fold. No full-dataset cognitive correlation selection is used.

Outputs include `fold_metrics.csv`, `model_summary.csv`, `model_comparison.csv`, `predictions.csv`, `fold_assignments.csv`, `expanded_feature_bank_inventory.csv`, `model_comparison.png`, and `integration_manifest.json`.

Three repeats of participant-level five-fold cross-validation were run. Outcome cohorts ranged from n=71–81 for T1 and n=51–61 for T2-minus-T1. The expanded bank improved T1 memory RMSE (14.80 vs 16.54) and was close to the existing bank for longitudinal verbal (16.42 vs 16.61). It was worse for the remaining outcomes, including Global (T1 11.03 vs 10.47; T2-minus-T1 8.19 vs 6.40). Neither model consistently beat the mean baseline; all R² estimates were negative. These are exploratory predictive results and do not promote the expanded bank into the primary Feature Bank.
