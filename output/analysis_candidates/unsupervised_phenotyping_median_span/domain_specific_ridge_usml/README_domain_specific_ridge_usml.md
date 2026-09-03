# Domain-specific Ridge-informed USML

This separate exploratory analysis asks whether each baseline cognitive domain has a different digital-feature structure.

## Workflow

1. Fit a separate Ridge model for Global, Memory, Executive function, Processing speed, Attention, and Motor T1 scores.
2. Use repeated 5-fold cross-validation repeated 20 times, with fold-local median imputation, missingness indicators, standardization, and inner-CV alpha selection.
3. Rank real features by the absolute mean coefficient across the 100 outer folds for each domain. Missingness-indicator terms are excluded from the final panels, and a feature must belong to the fixed 41-feature USML panel.
4. Select the strongest five features independently for each domain. The same feature can appear in more than one domain panel.
5. Run a new PCA and exploratory K-means audit for each five-feature panel. Patient inclusion requires at least 50% of the five values to be observed.
6. Compare cluster feature profiles, technical collection variables, baseline cognitive scores, follow-up scores, and T2-minus-T1 changes only after the domain-specific PCA and clustering are complete.

## Interpretation boundary

The feature-ranking step uses the cognitive outcome, so the resulting PCA/clustering maps are outcome-informed and hypothesis-generating. They are not independent validation of a clinical phenotype. Cognitive and technical variables do not enter the PCA or K-means calculations. All p-values and cognitive overlays are exploratory, and cluster stability should be interpreted together with coverage and technical audits.

Each domain directory contains its own feature selection, PCA coordinates/loadings, cluster quality/profile tables, technical audit, and cognitive overlay outputs. The original USML, coverage-adjusted USML, and global top-five outputs are unchanged.
