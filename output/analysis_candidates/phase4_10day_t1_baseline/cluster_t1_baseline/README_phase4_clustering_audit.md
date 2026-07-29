# Phase 4 Clustering Audit

This audit covers the first five clustering checks for Outcome 1.

## Full Cohort

- PCA scatter coordinates: `phase4_cluster_pca_scatter.csv`; the Streamlit page renders the scatter plot.
- Cluster quality: k=2 through k=5, with 20 seeds per k.
- Selected full-cohort k: `2`.

## Cluster Audit

`phase4_cluster_patient_audit.csv` and `phase4_cluster_audit_summary.csv` compare clusters on age, global T1, missingness, table coverage, and mapped device-episode count. `phase4_cluster_feature_differences.csv` ranks standardized feature differences between clusters.

## High-Coverage Re-clustering

The predefined high-coverage subset includes patients with:

- `baseline_feature_missing_fraction <= 0.50`
- `baseline_table_coverage_fraction >= 0.50`

Subset size: `54` patients. The best subset solution is k=`2` with mean silhouette `0.447` and mean pairwise ARI `1.000`.

The subset analysis is a sensitivity check. It does not prove that the full-cohort clusters are clinical or behavioral phenotypes.
