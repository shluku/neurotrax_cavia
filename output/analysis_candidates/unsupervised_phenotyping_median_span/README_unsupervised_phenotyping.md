# Exploratory Unsupervised Phenotyping: Median-Timespan T1 Cohort

This is a separate, exploratory unsupervised analysis of the largest currently available patient-level baseline cohort. The source cohort contains 81 patients from the median-timespan baseline extraction.

## Primary Representation

The default representation uses 41 catalog features observed in at least 50% of source patients. Patients must have at least 50% of the selected features observed to enter PCA and clustering; this produced 76 analyzable patients while retaining all 81 source patients in the audit.

- Counts and other highly right-skewed non-fraction features use log1p when skewness exceeds 1.5.
- Remaining missing feature values are imputed with the feature median after transformation.
- Features are robust-scaled using the 25th and 75th percentiles before PCA.
- Missingness and coverage are not clustering inputs; they are retained for post-hoc audit.
- The observed cognitive scores are not used to build PCA or clusters. They are overlaid afterward for interpretation.

## Dimension Reduction and Clustering

PCA is used to describe the main axes of variation. K-means clustering is evaluated for k=2, 3, and 4 on the first 10 PCA components, or fewer when the matrix requires it. Candidate solutions are compared using silhouette, repeated-seed adjusted Rand index, and 100 80%-subsample refits. Cluster labels are arbitrary and do not represent clinical diagnoses.

## Sensitivity Panels

- `primary_37`: predefined primary feature set.
- `usable_catalog_50pct`: default catalog panel with at least 50% source-patient coverage.
- `expanded_catalog_10pct`: exploratory sensitivity panel allowing features observed in at least 10% of source patients.

The panels are run separately because changing the acquisition window or coverage rule changes the feature matrix. They should not be pooled into one model.

## Interpretation Boundary

A visually separated PCA plot or a high silhouette does not establish a clinical subtype. Any apparent structure must be checked against coverage, missingness, device availability, feature transformations, and sensitivity panels before it is described as a digital phenotype.

## Outputs

Each panel directory contains patient PCA scores, loadings, cluster quality, cluster profiles, feature profiles, cohort audit, feature inventory, and transformation records.
