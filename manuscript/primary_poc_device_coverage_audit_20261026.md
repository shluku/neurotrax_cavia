# Primary POC device and coverage audit — 2026-10-26

This audit uses the saved patient-level mechanism file for the frozen afternoon 12:00–18:00 snapshot-IEI change versus Executive Function change POC. It is descriptive and sensitivity-oriented; it does not create a new discovery family.

## Findings

- The exact paired cohort contains 28 participants.
- Across all participants, feature change and Executive Function change have Spearman rho=0.593 (the saved discovery estimate).
- The feature is also associated with change in afternoon active days: rho=-.489, p=.0082 in the same cohort.
- The saved mechanism audit indicates that 22/28 participants (78.6%) changed device set between the two windows.
- The device-unchanged subgroup has n=6, so subgroup-specific association estimates are unstable and should be treated as descriptive only.

## Interpretation

The primary POC is not free of recording or device-composition confounding. The existing all-factor technical adjustment attenuated the association from rho=.593 to partial rho=.356 (p=.113), after adjustment for coverage/frequency, sampling-behavior structure, package continuity, and device-set change. This does not prove that the association is entirely artifactual, but it prevents a direct behavioral interpretation without independent validation and more stable device-aware measurement.

The complete group summaries are in `output/research_summary_20261025/top15_article_statistics_v1/primary_poc_device_coverage_audit_v1.csv`.

## Remaining gap

The current saved data do not support a reliable device-stratified validation because only six participants are device-unchanged. A future analysis should prespecify device-episode handling, app/package harmonization, coverage thresholds, and a participant-level validation cohort before testing the POC again.
