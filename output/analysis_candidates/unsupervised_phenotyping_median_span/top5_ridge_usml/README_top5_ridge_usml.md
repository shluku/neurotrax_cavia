# Top-five Ridge feature USML analysis

This is a separate exploratory unsupervised analysis using the five strongest real features from the midpoint/all-available T1 Ridge coefficient summary. Missingness-indicator terms were excluded, and selected terms had to be present in the fixed 41-feature USML panel.

## Selected features

keyboard_median_word_completion_time_ms, app_use_diversity, telephony_mobile_data_enabled_fraction, touch_scroll_index_change_median, message_distinct_event_count

## Design

- Patient inclusion requires at least 50% of the five selected feature values to be observed.
- Features use the same log1p-if-skewed transformation, median imputation, and robust scaling as the original USML pipeline.
- PCA and K-means clustering are unsupervised; cognitive outcomes and technical variables are not used to define them.
- Candidate k=2, 3, and 4 solutions are audited using silhouette and repeated subsample ARI. The displayed solution is selected using the same minimum-cluster-size rule as the original USML run.
- Feature, technical, cognitive, and follow-up-informed post-hoc outputs are written separately from the original USML outputs.

## Interpretation boundary

Ridge coefficient ranking is outcome-informed, so this five-feature USML run is hypothesis-generating and not independent validation. A visually separated cluster or a strong coefficient does not establish a clinical phenotype. All post-hoc p-values are exploratory.
