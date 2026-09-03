# Exploratory Empirical Findings (1;4)

This separate exploratory analysis compares the 20 participants with the lowest observed baseline global cognitive scores against the 20 participants with the highest scores.

## Cohort rule

- Lowest group: the 20 lowest observed baseline global cognitive scores.
- Highest group: the 20 highest observed baseline global cognitive scores.
- Lowest-group maximum score: `92.80`.
- Highest-group minimum score: `104.10`.
- The two keyboard features from the original empirical model remain fixed so the p-value comparison changes the cohort definition rather than the model feature set.
- This is an exploratory extreme-group comparison, not a validated clinical severity classification.

## P-value comparison

The full feature table stores the new extreme-group p-values beside the original median-split p-values. The five smallest extreme-group p-values are:
- keyboard_median_word_completion_time_ms: extreme p `0.059`; median-split p `0.032`; extreme q `0.967`.
- keyboard_inter_event_interval_iqr_ms: extreme p `0.064`; median-split p `0.036`; extreme q `0.967`.
- telephony_mobile_data_enabled_fraction: extreme p `0.136`; median-split p `0.436`; extreme q `0.967`.
- telephony_network_type_diversity: extreme p `0.154`; median-split p `0.339`; extreme q `0.967`.
- activity_still_fraction: extreme p `0.194`; median-split p `0.909`; extreme q `0.967`.

For the fixed model features:
- keyboard_median_word_completion_time_ms: extreme p `0.059` versus original median-split p `0.032`; direction `-1`.
- keyboard_inter_event_interval_iqr_ms: extreme p `0.064` versus original median-split p `0.036`; direction `-1`.

## Model protocol

- The model uses the same two keyboard features as the original empirical analysis.
- Missing values are imputed with training-fold medians; missingness indicators are not added.
- Oriented features use training-fold robust scaling and a positive Ridge calibration.
- Results use repeated 5-fold cross-validation with 20 repeats and the same fold-local mean baseline.

## Pooled model results

- mean_baseline: RMSE `11.898`, MAE `10.959`, R2 `-0.048`.
- equal_weight_empirical_score: RMSE `11.864`, MAE `10.687`, R2 `-0.042`.
- direction_constrained_ridge: RMSE `11.966`, MAE `10.884`, R2 `-0.060`.

## Interpretation boundary

The model cohort contains 40 participants, not the full 81-participant cohort. Feature-level p-values can become smaller when comparing extreme groups because the groups are farther apart by construction, but this does not establish generalizable prediction or a clinical threshold.

The extreme-group selection and model evaluation use the same cohort. The results are therefore hypothesis-generating and require replication in a prespecified independent sample.
