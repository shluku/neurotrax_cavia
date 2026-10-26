# Candidate Evidence Completeness — 2026-10-21 v1

This versioned audit covers the six original Keyboard Signal Discovery candidates (K1–K6), the legacy word-completion/Attention T1 association (W1), and Word Completion v1 IQR change/Global cognitive change (W2). It reuses saved patient/window outputs and saved inferential tables. It does not run a broad feature search, train a model, or replace an historical result.

## Files

- `candidate_evidence_completeness_table_20261021_v1.csv` — one row per candidate, with historical discovery/validation statistics, coverage summaries, missing evidence, and the minimum prespecified validation plan.
- `candidate_evidence_descriptive_distributions_20261021_v1.csv` — candidate-specific aggregate distributions for Early/T1, Late/T2, change, cognition, active days, canonical snapshots, valid intervals, package counts, and (for W2) high-confidence fraction. No patient identifiers or raw text are exported.
- `candidate_evidence_source_index_20261021_v1.csv` — source files and testing context; repeated same-cohort sensitivity results are explicitly not independent replication.
- `candidate_evidence_manifest_20261021_v1.json` — version and provenance metadata.

## Methods and interpretation

For K1–K6 and W1, Early/T1 and Late/T2 are the saved midpoint keyboard windows; change is Late minus Early. Paired summaries are complete-case, candidate-specific summaries and therefore do not reproduce every historical discovery cohort. Canonical distinct observations, valid intervals, active days, and package counts are carried forward from the saved window tables. Snapshot inter-event intervals are elapsed time between recorded text-state snapshots (milliseconds), not keypress timing. The correction-recovery feature is the median elapsed time from a detected deletion/correction snapshot to the first later within-burst text-growth snapshot. The word-completion measures are snapshot-observable proxies.

The new descriptive effect is an exploratory OLS outcome difference per observed feature IQR, with a 2,000-resample patient bootstrap. It is a scale aid, not a new confirmatory model and not a causal or clinically validated effect.

W2 uses the saved Word Completion v1 patient table. Its algorithm has unresolved continuity and classification problems: no true keypresses, incomplete snapshots, ambiguous paste/predictive/autocorrect/correction transitions, a literal-space boundary, and quality classes that cannot prove a word was continuously observed. The adjusted W2 file has no saved FDR q-value or confidence interval. W1 has historical n=60 after removal of two extreme feature values, but no saved q-value, CI, LOO, permutation, or recording-adjusted result.

## Evidence status

- K1 (afternoon IEI → Executive Function change): discovery ρ=.593, n=28, p=.000885, q=.0903; full technical adjustment attenuates to ρ=.356, p=.113. Treat as coverage-sensitive exploratory evidence.
- K2 (correction recovery → Executive Function change): discovery ρ=−.589, n=32, p=.000394, q=.0803; LOO, outlier and permutation checks are stable, but full recording adjustment attenuates. Requires prespecified recording/device validation.
- K3 (IEI CV → Executive Function change): discovery ρ=−.513, n=33, p=.00227, q=.154; age/sex/education adjustment remains, full recording adjustment attenuates.
- K4 (evening IEI → Executive Function change): discovery ρ=.524, n=29, p=.00355, q=.181; age/sex/education adjustment remains, recording-adjusted uncertainty crosses zero.
- K5 (morning IEI → Executive Function change): discovery ρ=.485, n=31, p=.00572, q=.195; age/sex/education adjustment remains, recording adjustment attenuates.
- K6 (afternoon IEI → Attention change): discovery ρ=.513, n=28, p=.00528, q=.195; it is the same feature/cohort family as K1, not independent replication.
- W1 (legacy word proxy → Attention T1): historical ρ=−.354, n=60, p=.00545; q/CI and technical sensitivity are missing.
- W2 (Word Completion v1 IQR change → Global change): unadjusted ρ=.409, n=31, p=.0225, q=.858, bootstrap CI [.051, .673]; saved recording-adjusted partial ρ=.525, p=.00413, n=31, without q/CI. Resolve algorithm continuity before interpretation.

The smallest useful next validation set is: (1) predeclare comparable coverage and device/app rules; (2) reconstruct each candidate from canonical distinct observations; (3) use parsimonious adjustment for baseline cognition, active days, snapshot/valid-interval rates, and device change; and (4) report reliability, leave-one-patient-out, permutation, and bootstrap uncertainty. Do not select thresholds or candidates using cognitive outcomes.
