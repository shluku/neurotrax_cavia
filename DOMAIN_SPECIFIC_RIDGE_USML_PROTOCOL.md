# Domain-specific Ridge-informed USML protocol

## Purpose

The original unsupervised analysis used one common digital-behavior panel for all cognitive outcomes. This exploratory extension asks whether different cognitive domains are associated with different candidate digital-feature panels.

## Feature selection

For Global, Memory, Executive function, Processing speed, Attention, and Motor baseline scores, a separate Ridge model is fit using the all-available Phase 11 T1 feature catalog. The model uses repeated 5-fold cross-validation repeated 20 times. Each training fold performs median imputation with missingness indicators, standardization, and inner cross-validation for Ridge alpha selection.

Within each domain, real features are ranked by the absolute mean coefficient across the 100 outer folds. Missingness-indicator terms are excluded. The final five features must also be present in the fixed 41-feature USML panel. A feature may appear in more than one domain panel.

## Domain-specific PCA and clustering

Each domain's five selected features are transformed with the existing USML rules: log1p for eligible highly skewed nonnegative features, median imputation, and robust scaling. Patients with at least 50% of that domain's five feature values observed enter that domain's PCA and clustering analysis. PCA is fit separately for every domain. Candidate K-means solutions with k=2, 3, and 4 are audited using silhouette and repeated subsample adjusted Rand index, with the same minimum cluster-size rule used in the original USML analysis.

## Post-hoc audits

Cognitive scores and technical variables are not used to create the domain-specific PCA coordinates or cluster assignments after feature selection. They are overlaid afterward to report baseline scores, follow-up scores, T2-minus-T1 deltas, cluster profiles, and technical collection differences.

## Interpretation boundary

The feature-ranking step uses each cognitive outcome, so these are outcome-informed, exploratory representations. They are useful for finding hypotheses and communicating domain-specific structure, but they are not independent validation and must not be described as validated clinical phenotypes. P-values are exploratory and do not provide confirmatory evidence in this small cohort.
