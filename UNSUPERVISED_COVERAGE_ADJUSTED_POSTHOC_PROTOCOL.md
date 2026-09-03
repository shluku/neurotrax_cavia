# Coverage-Adjusted PCA Post-hoc Protocol

## Purpose

The original median-timespan PCA showed a stable two-group digital-behavior structure. The main concern is whether the structure reflects genuine differences in patient behavior or simply differences in recording duration, source-row intensity, coverage, and missingness.

This protocol is a post-hoc sensitivity analysis. It does not replace the original PCA and does not use cognitive outcomes to define features, PCA coordinates, or clusters.

## Fixed design

- Use the same fixed usable-catalog feature panel as the original analysis.
- Preserve the original analyzable patient cohort for direct comparisons whenever possible.
- Refit PCA and two-cluster K-means separately for each sensitivity variant.
- Compare each variant with the original using cluster ARI and absolute correlations of PC1/PC2.
- Report explained variance, silhouette, and repeated subsample ARI.

## Sensitivity variants

1. **Original processing reference:** unchanged feature transformation, median imputation, robust scaling, PCA, and two-cluster K-means.
2. **Exposure-normalized features:** divide volume-like features by observed recording-span days. Fractions, ratios, diversity measures, and timing features are not divided.
3. **Technical-residualized features:** after transformation and imputation, remove linear contributions of observed span, total source rows, fixed-panel coverage, baseline feature missingness, and baseline table coverage.
4. **Quality-trimmed reference:** remove patients in the extreme 5% tails of observed span, source rows, panel coverage, and baseline table coverage, then rerun the reference processing.

## Technical audit

For every variant, compare clusters on observed span, source rows, calculated-table count, missingness, panel coverage, table coverage, and device counts. These variables are not used to define the original clusters and are reported only as technical confounders.

## Cognitive post-hoc audit

Overlay global T1, global T2, and available domain-specific T2-minus-T1 deltas on each variant's PCA map. Report sample size, correlation with PC1/PC2, cluster summaries, standardized cluster difference, and exploratory Mann-Whitney p-values. Negative delta means lower T2 than T1.

## Interpretation boundary

Persistence after adjustment strengthens the case that the structure is not solely a coverage artifact. Disappearance after adjustment suggests that the original structure may primarily reflect measurement intensity. Neither result establishes a clinical phenotype or predictive validity.
