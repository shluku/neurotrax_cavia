# Exploratory Unsupervised Phenotyping Protocol

## Purpose

This analysis explores whether patient-level passive-sensing features form reproducible patterns without using the observed cognitive scores to define those patterns. It is a hypothesis-generating extension of the baseline digital-phenotyping work, not a validated clinical taxonomy.

## Cohort

The first analysis uses the median-timespan T1 baseline cohort. This is currently the largest patient-level baseline extraction and contains 81 source patients. The source cohort is retained in the audit files even when an individual patient does not have enough observed feature values for the selected representation.

## Data Unit

The analysis uses one row per patient and one column per extracted feature. The raw SQL event tables are not clustered directly. Raw tables have repeated observations and unequal recording density; using them directly would risk discovering data volume, device availability, or sampling behavior instead of patient-level digital phenotypes.

## Feature Panels

Three panels are generated separately:

1. **Usable feature catalog:** catalog features observed in at least 50% of the source patients. This is the primary exploratory representation.
2. **Primary 37 features:** the predefined primary baseline feature set.
3. **Expanded catalog:** catalog features observed in at least 10% of source patients. This is a sensitivity analysis and is more vulnerable to imputation-related structure.

The additional sparse sensor columns that are not yet in the active feature metadata catalog are not silently added to the primary representation. They remain available for later modality-specific analysis after their coverage and feature definitions are finalized.

## Patient Availability Rule

For each panel, a patient must have at least 50% of the selected feature columns observed. Patients below this threshold are excluded from PCA and clustering for that panel but remain in the patient-level audit. This prevents a patient with almost no observed data from becoming a median-imputation artifact.

## Preprocessing

1. Numeric feature values are parsed from the extracted patient dataset.
2. Highly right-skewed nonnegative features that are not fractions, ratios, or diversity measures are transformed with `log1p` when their observed skewness exceeds 1.5.
3. Remaining missing values are imputed using the median of the transformed analyzable cohort.
4. Features are robust-scaled using the interquartile range before PCA.
5. Coverage and missingness are excluded from the clustering input and retained for post-hoc audit.

The imputation and transformation records are written to each panel directory. They are descriptive preprocessing choices for this exploratory analysis, not a final clinical modeling standard.

## PCA

PCA is applied to the transformed and robust-scaled patient-by-feature matrix. It is used to describe the dominant axes of feature variation and to create an interpretable patient map. PCA coordinates are not themselves clinical scores.

The primary visual is PC1 versus PC2. The page can color the same patient map by cluster, observed global T1, feature coverage, or missingness. Cognitive scores are overlaid only after the unsupervised representation has been created.

## Clustering

K-means solutions with `k=2`, `k=3`, and `k=4` are evaluated on the first 10 PCA components, or fewer if the matrix has fewer available dimensions. The displayed solution is selected using the mean silhouette score, with subsample stability used as a secondary criterion and a minimum reference cluster size of five patients where possible.

Stability is assessed through:

- 20 repeated K-means seeds on the full PCA representation.
- 100 refits on 80% subsamples, followed by comparison of full-cohort assignments using adjusted Rand index.

Cluster labels are arbitrary identifiers. They must not be called disease subtypes or clinical classes without independent validation.

## Required Interpretation Checks

Every apparent cluster pattern must be checked against:

- Patient-level feature coverage and missingness.
- The selected feature panel and coverage threshold.
- The transformation and imputation records.
- Primary-feature and expanded-catalog sensitivity panels.
- Whether the same pattern is visible when colored by observed T1 or cognitive domain scores.

## Planned Longitudinal Extension

After the baseline representation is understood, the same feature catalog can be applied independently at T1 and T2. The change matrix will be calculated as `T2 feature - T1 feature`, followed by PCA on feature changes. With only two assessments, this should be described as a longitudinal displacement or change vector rather than a full trajectory. The T1-to-T2 analysis will be a separate step and is not included in this baseline run.

## Output Files

Each panel produces:

- `pca_patient_scores.csv`: patient coordinates, cluster labels, cognitive scores, and audit fields.
- `pca_variance.csv`: explained variance by component.
- `pca_loadings.csv`: feature contributions to each principal component.
- `cluster_quality.csv`: silhouette and stability statistics for candidate cluster counts.
- `cluster_profiles.csv`: cluster sizes, observed T1 summaries, coverage, and missingness.
- `cluster_feature_profiles.csv`: feature patterns within each cluster.
- `patient_cohort_audit.csv`: all source patients and panel-specific inclusion status.
- `feature_inventory.csv` and `feature_transformations.csv`: feature coverage and preprocessing records.
