# Full Model PCA


Authorized 2026-09-20: extend the original 41-feature PCA with ACC movement
features; fit on the existing cohort and freeze the transformation for new
subjects; use the existing Phase 11 / Phase 12 windows and retain only global
decliners in the longitudinal view (`global_T2 < global_T1`).

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

T1: 42 patients; 56 varying features. PC1+PC2: 80.63%. Paired decliners: 9; change PCA: 9 patients.
