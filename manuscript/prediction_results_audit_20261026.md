# Prediction results section — audited reporting draft

Prediction analyses are reported separately from the feature–cognition correlation analyses because they answer a different question. The models estimate individual cognitive scores from multiple digital features and are evaluated against a fold-matched mean baseline; they are not evidence that any single feature is a validated association.

The most credible saved historical candidate was the fixed 37-feature Ridge model for Processing Speed using the first available 10-day post-T1 window (n=71, 20 repeated five-fold runs). Corrected row-aligned performance was RMSE 12.950 versus 13.718 for the mean baseline, MAE 10.380 versus 11.259, and R² .0799 versus −.0278. The mean RMSE improvement was 0.75 points, but the conditional participant-cluster bootstrap interval was −1.13 to 2.37, which includes no improvement. Because the feature window is post-T1 and overlaps the assessment period, this result is a concurrent digital correlate, not prospective prediction.

The 24-hour Motor Ridge model was a secondary exploratory candidate (n=79). It had RMSE 10.186 versus 10.678 for the mean baseline, MAE 8.571 versus 8.925, and R² .0559 versus −.0371. Its bootstrap RMSE improvement was 0.48 points with a 95% interval of −0.31 to 1.20. The result is compatible with a modest numerical gain but does not establish reliable superiority.

The coverage Top-10 Global Elastic Net result was descriptive only (n=10, 10 repeats). Although its corrected RMSE was 7.978 versus 10.454 for the mean baseline, the candidate was selected after a broad model/cohort screen and its bootstrap interval for improvement was −1.93 to 5.57. It should not be used as the main prediction result.

All metrics were recomputed from correctly aligned saved out-of-fold predictions. Historical pooled metrics based on misaligned outcome ordering are retained for provenance but are not reported as valid performance. The saved outer test folds were protected, but preprocessing and tuning were not fully nested within inner folds. No candidate has an independent test cohort. Therefore, the prediction results demonstrate an auditable modeling workflow and modest historical signals, not clinical prediction validity.

## Required future confirmation

A confirmatory study should freeze the participant eligibility rule, 37-feature panel, window, outcome, preprocessing, tuning procedure, mean-baseline comparator, and uncertainty metric before outcome review. Imputation, scaling, and hyperparameter selection must be fully nested. The model must then be tested in new participants or a genuinely held-out temporal cohort collected before the cognitive assessment.

Source: `output/analysis_candidates/model_results_audit_20261020/`.
