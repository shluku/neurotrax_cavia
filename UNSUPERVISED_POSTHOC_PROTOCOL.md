# Post-hoc Characterization of the Exploratory Unsupervised Solution

## Scientific Question

Does the stable digital-behavior structure identified by the unsupervised model correspond to baseline cognition, future cognitive change, or neither?

## Fixed Unsupervised Representation

This analysis uses the existing median-timespan T1 baseline solution based on the usable catalog panel. It contains 41 features and 76 patients with sufficient feature availability. The existing PCA coordinates and K-means cluster assignments are read from the previously generated output. They are not recomputed by this post-hoc analysis.

The reference solution contains Cluster 0 (`n=11`) and Cluster 1 (`n=65`). Cluster labels are arbitrary identifiers, not clinical classes.

## 1. Cluster Characterization

For every feature in the active extracted catalog, the output reports. The 41 features used in the fixed PCA/clustering panel are marked explicitly; the remaining catalog features are descriptive post-hoc extensions and do not redefine the clusters:

- Patient count contributing a value in each cluster.
- Cluster-specific mean, median, standard deviation, and median/IQR.
- The raw mean difference, defined as Cluster 1 minus Cluster 0.
- A standardized mean difference using the pooled standard deviation.
- An exploratory two-sided Mann-Whitney U p-value and Benjamini-Hochberg q-value.
- The feature's PC1/PC2 loading and maximum absolute loading.
- Whether the feature was part of the fixed PCA/clustering input.

Features are grouped descriptively into messaging, keyboard, app activity, touch, screen, circadian, mobility/activity, and other digital activity. The grouping is only for interpretation and does not alter the clustering.

## 2. Technical and Coverage Confounding Audit

Technical variables are calculated after clustering and are not included in the PCA or K-means input. The audit compares clusters on:

- Fixed-panel feature coverage and baseline feature missingness.
- Number of calculated tables and tables with any rows.
- Total source rows in the patient midpoint span as a collection-intensity proxy.
- Mean rows per calculated table.
- Number of available and used devices, without exporting device identifiers.
- Configured endpoint interval length.
- Earliest-to-latest observed timestamp span, which is not assumed to be continuous recording time.
- Number of tables without a calculated result.

Exact deduplicated recorded-day counts, operating-system/version, and device type are not present in the current patient-level Phase 11 exports. They are listed as unavailable rather than inferred.

Technical variables are summarized with the same descriptive statistics, standardized difference, exploratory Mann-Whitney U p-value, and false-discovery-rate q-value. A strong technical difference means the behavioral interpretation requires caution because the cluster may partly reflect collection intensity or data availability.

## 3. Cognitive Change Overlays

Cognitive outcomes are completely post-hoc. They are not used to select features, calculate PCA, or assign clusters.

For each patient with the required scores, change is explicitly calculated as:

`T2 - T1`

The page provides the fixed PCA patient map colored by each available global or domain-specific outcome. The output reports correlation of the outcome with PC1 and PC2, cluster-specific mean and median/IQR, Cluster 1 minus Cluster 0 difference, standardized difference, sample size, exploratory p-value, and FDR q-value.

Negative cognitive delta means that the observed T2 score is lower than the observed T1 score. This is a descriptive convention, not a claim that every negative value represents clinically meaningful decline.

## 4. Summary Output

`unsupervised_posthoc_summary.csv` contains rows for global T1, global T2, global T2-T1 delta, and available domain deltas. Its statistics use only patients with a fixed PCA coordinate, a fixed cluster assignment, and the relevant cognitive outcome.

All p-values are exploratory. A value below 0.05 is not treated as confirmatory evidence. The small Cluster 0 and the incomplete T2/domain follow-up reduce precision, so effect sizes, sample sizes, technical differences, and replication in future cohorts are more important than isolated p-values.

## Output Files

- `cluster_feature_comparison.csv`: full feature-by-cluster comparison and separation rankings.
- `technical_confounding_comparison.csv`: technical/coverage variables compared between clusters.
- `technical_patient_audit.csv`: one row per fixed-cluster patient with collection-quality variables.
- `technical_variable_inventory.csv`: available and unavailable technical variables.
- `cognitive_overlay_points.csv`: fixed PC1/PC2 coordinates with post-hoc outcome values.
- `cognitive_overlay_summary.csv`: outcome-level correlations and cluster comparisons.
- `unsupervised_posthoc_summary.csv`: concise requested summary table.
- `posthoc_run_record.json`: reproducibility record confirming that PCA and clusters were not recomputed.
