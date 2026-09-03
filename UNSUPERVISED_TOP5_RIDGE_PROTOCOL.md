# Top-Five Ridge Feature USML Protocol

## Purpose

Examine whether the strongest real digital features from the midpoint/all-available T1 Ridge model form an interpretable unsupervised patient structure.

## Feature selection

Rank the Ridge coefficient summary by absolute mean coefficient. Exclude terms beginning with `missingindicator_` because they describe missingness rather than digital behavior. Restrict the ranking to features present in the fixed 41-feature USML panel. Select the top five and record the coefficients, sign stability, and coverage.

## Unsupervised analysis

Use the same feature preprocessing as the original USML analysis: log1p for highly skewed non-negative non-fraction features, feature-median imputation after transformation, robust scaling, PCA, and K-means evaluation for k=2, 3, and 4. Cognitive scores are never used to create PCA or clusters.

## Post-hoc audit

Characterize the clusters using the five features, technical collection variables, global and domain-specific cognitive outcomes, and T2-minus-T1 deltas. The PCA map and interactive 3D patient view are descriptive. All p-values are exploratory.

## Interpretation boundary

Because the feature ranking used T1 outcome information, this analysis is hypothesis-generating and cannot be presented as independent validation. It asks whether a small Ridge-informed feature panel reveals a coherent digital-behavior structure worth testing in a future held-out cohort.
