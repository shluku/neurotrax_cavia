# Phase 4 Exploratory T1 Baseline Clustering

This is an exploratory unsupervised analysis of the patient-level T1 baseline phenotype.

## Design

- Patients: `81`.
- Features: `37` primary T1-week features only.
- Missing numeric feature values: cohort-median imputation for this descriptive clustering run.
- Scaling: standardized feature values.
- Dimension reduction: PCA to `10` components before clustering.
- Candidate cluster counts: `k=2` through `k=5`.
- Stability: 20 K-means seeds per candidate k, assessed with silhouette variation and pairwise adjusted Rand index.

## Selected Exploratory Solution

- Selected k by highest mean silhouette score: `2`.
- Mean silhouette at selected k: `0.497`.
- Mean pairwise adjusted Rand stability at selected k: `1.000`.

Cluster labels are arbitrary identifiers, not clinical classes. The clustering should be interpreted alongside missingness, table coverage, device episodes, and the original feature distributions. It must not be presented as a validated patient taxonomy.

## Important Limitation

Median imputation and PCA are used here to create an analyzable exploratory representation. Missingness indicators were not included in the clustering input because that would encourage clusters to represent data availability rather than digital phenotype. Coverage variables remain in the assignment output for post hoc audit.

## Files

- `phase4_t1_cluster_assignments.csv`: patient cluster labels, PCA scores, and coverage audit fields.
- `phase4_t1_cluster_quality.csv`: silhouette and stability results for each candidate k.
- `phase4_t1_cluster_feature_summary.csv`: feature summaries by cluster.
- `phase4_t1_cluster_pca_loadings.csv`: PCA feature loadings for interpretation.
