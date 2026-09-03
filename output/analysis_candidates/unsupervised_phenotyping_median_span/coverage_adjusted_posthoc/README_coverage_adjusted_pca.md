# Coverage-adjusted PCA sensitivity audit

This is a separate post-hoc sensitivity analysis of the fixed median-timespan baseline cohort. The original PCA coordinates and cluster assignments in `usable_catalog_50pct` are unchanged.

## Question

Does the observed digital-behavior structure survive when differences in observed recording exposure and data quality are reduced, or is it mainly a measurement-intensity pattern?

## Fixed comparison design

- The same fixed usable-catalog feature panel is used in every variant (41 features).
- The original reference cohort is retained for direct comparison (76 patients).
- Cognitive scores are never used to recompute PCA or clustering.
- Each variant uses two clusters so the comparison remains aligned with the original two-cluster result.
- All p-values are exploratory and not confirmatory evidence.

## Variants

- **Original processing reference:** reproduces the existing feature transformation, median imputation, robust scaling, PCA, and two-cluster analysis.
- **Exposure-normalized features:** volume-like features are divided by observed timestamp-span days. This reduces the effect of longer observed windows but may also remove genuine duration-related behavior.
- **Technical-residualized features:** transformed features are residualized against observed span, source-row intensity, feature coverage, feature missingness, and table coverage. This is a stronger sensitivity analysis and can remove real behavior if behavior and recording intensity are correlated.
- **Quality-trimmed reference:** removes patients in the extreme 5% tails of the available quality/intensity variables before rerunning the original processing.

## Interpretation

Evidence for a more genuine behavioral structure would be persistence of PCA alignment, feature loadings, cluster stability, and cognitive overlays after adjustment. If the structure changes substantially, the original result should be described as potentially driven by coverage or collection intensity. This analysis cannot prove causality or clinical validity.

The technical and cognitive analyses are post-hoc. The cognitive delta is defined as T2 minus T1, so negative values indicate lower T2 than T1.
