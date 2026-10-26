# Full Model PCA


Authorized 2026-09-20: extend the original 41-feature PCA with ACC movement
features; fit on the existing cohort and freeze the transformation for new
subjects; use the existing Phase 11 / Phase 12 windows and retain only global
decliners in the longitudinal view (`global_T2 < global_T1`).

## Current explicit patient exclusion

After reviewing the first run, the user requested removal of patient **002**
(the singleton cluster, with 29 ACC minutes across two T1 days). The exclusion
is recorded in `full_model_pca_config.json` and applies before all model fits,
comparisons, T2 projections and change analyses. The patient remains in source
files and in the audit, with an explicit exclusion reason. No further outliers
are removed automatically.

Refit preprocessing, PCA and clustering on the remaining patients using the
same feature candidates, clinical windows, availability rules and seed. Freeze
the new parameters for future projection. Preserve the original run
`20260920T092803389833Z` and show its summary beside the rerun. This is an
exclusion chosen after inspecting the results, not a prespecified quality
threshold or independent validation.

## Inputs and clinical windows

Use the exact 41 feature names in the saved usable-catalog PCA loadings and the
Phase 11 patient dataset used by that analysis. ACC comes from the completed
September 11 patient-sequential **device-day** features. The 15 non-quality
features in its catalog are candidates; the nine quality features, identifiers,
cognitive outcomes, row counts, coverage and missingness do not enter PCA.

Use saved window start/end timestamps from the Phase 11 and Phase 12 status
tables. They define T1 to midpoint (including the existing fallback when no T2
exists), and midpoint to T2. Never invent a T2 window. ACC summaries describe
whole local calendar days: include only days fully contained in the half-open
window. Exclude days crossing its boundary because a daily summary cannot be
split exactly. Calendar boundaries use Asia/Jerusalem, including daylight saving.

The completion audit identified four multi-device patient-days with invalid
pooled coverage / quiet-interval conventions. The main analysis excludes these
days and computes patient medians from the remaining device-day records. A
sensitivity chooses one device per day by most observed minutes, then most
valid rows, then device ID. It never claims to reconstruct pooled signal. A
second sensitivity uses patient means across the main analysis's included days.
Original extraction and PCA files remain preserved.

## Availability and preprocessing

Retain all 81 source patients in the audit. To enter the combined representation,
a patient needs at least 50% observed values in **each** block (the original
digital panel and the ACC panel). This extends the original 50% availability
rule to both modalities so a fully imputed ACC block does not count as movement
evidence. No minimum-day threshold beyond having usable window-specific data is
imposed; numbers of observed days and coverage remain visible. Drop all-missing
or constant columns at fitting and report them.

Reuse the original USML transformation: log1p for nonnegative skewed features
(absolute skew >1.5, excluding fraction/ratio/diversity names), median imputation
and IQR RobustScaler, then up to 10 PCs. These choices and parameters are fit
only on the training cohort and saved in JSON. Apply the original K-means audit
(k=2..4, 20 seeds, 100 80%-subsamples; silhouette then stability with minimum
cluster size 5 where possible). Suppress clustering for fewer than 12 patients.
This is descriptive cohort PCA, not held-out predictive validation.

The primary T1 cohort includes eligible patients regardless of cognitive change.
Decline eligibility requires non-missing global scores with T2 < T1, ordered
clinical dates, both saved windows, and feature coverage at each endpoint. T2
values are projected using the frozen T1 transform/PCA, allowing arrows on the
same axes. A separate change PCA uses **observed** T2-minus-T1 feature pairs;
missing at either endpoint stays missing before the change PCA's own imputation.
Its axes are separate from the baseline axes. The decline-only sample is an
outcome-selected descriptive subset, not evidence of decline prediction.

## Comparisons, audits and new subjects

### Domain-specific feature panels and 3D score trends

The 2026-09-20 extension repeats the earlier domain-specific Ridge method for
Global, Memory, Executive function, Processing speed, Attention and Motor. The
candidate pool is the 41 digital plus 15 ACC features. Selection uses the current
eligible combined T1 cohort with patient 002 excluded, restricted to observed
scores for the domain. Repeated 5-fold splits (20 repeats) fit median imputation
with missingness indicators, StandardScaler and RidgeCV (the original 30 alpha
values and 4-fold inner search) on each outer training set. Rank real features
by absolute mean coefficient, then sign stability and feature name. Indicators
are never eligible for the top five. This reuses the earlier implementation;
it is a feature-ranking exercise, not a report of held-out prediction accuracy.

Each domain gets its own five selected features, preprocessing, PCA, cluster
audit and frozen projection parameters. Fit patients must be in the eligible
combined cohort, have an observed domain T1 score and at least 50% of that
five-feature panel observed. New-subject projection requires at least half of
the selected panel, including when it contains only one modality. No ACC feature
is forced into a panel if it does not rank among that domain's top five. Domain
relevance here means association in this cohort, not clinical specificity.

Show PC1, PC2 and the observed domain score as the 3D coordinates, colored by
cluster. As in the earlier keyboard plot, draw the dominant straight direction
of the standardized 3D point cloud, overall and within each cluster with at least
three complete observations. Use common overall coordinate scales for the
cluster lines. Suppress lines for constant scores or undefined directions.
These geometric lines are not regression lines predicting a score from two
PCs (that regression gives a plane). Separately report Pearson/Spearman
associations, cluster score summaries and in-sample R² for score ~ PC1 + PC2;
do not regress on arbitrary numerical cluster labels.

Domain score information enters feature selection, so the resulting associations
are outcome-informed and exploratory. Cross-validation used for selection does
not independently validate these displayed associations. Keep the existing
global-decline eligibility rule for T2 views. Project selected T2 features onto
the domain's frozen T1 axes; reuse its T1-selected panel for observed T2−T1
feature-change PCA without re-ranking against follow-up scores. Display the
domain-specific T2 score or cognitive change as height in those views. The
common 56-feature analysis remains accessible as a comparison.

Compare the original digital block, ACC alone, combined, mean aggregation and
single-device-choice sensitivity on identical eligible T1 patients. Show
explained variance, cluster quality and sizes, top loadings, technical
correlations and observed cognitive overlays. Outcomes and quality variables
are never PCA features. Reports include all inclusion/exclusion decisions,
window/day provenance, source SHA-256 hashes, software versions and fixed seed.

A new subject supplies one patient-level feature row using the same definitions
and window aggregation. Validate numeric finite values, block coverage and
nonnegative ACC values. Apply the saved feature order, log choices, medians,
scaler, PCA and cluster centers without refitting. Blank values stay missing;
zero is an observed value. The UI does not run SQL or fit models.

Run: `.venv/bin/python3 -u full_model_pca.py`. Successful runs are versioned under
`output/analysis_candidates/full_model_pca/runs/`; `current.json` is switched only
after completion and source-hash verification. Streamlit: **Full Model PCA**.

## This run

T1: 41 patients; 56 varying features. PC1+PC2: 50.26%. Paired decliners: 9; change PCA: 9 patients.
