# Completed ACC extraction audit

Verified 2026-09-14T13:32:40.038101+03:00. Final extraction checkpoint: 2026-09-11T01:25:27.370691+03:00.

The documented completed extraction command was:

```bash
.venv/bin/python3 -u extract_accelerometer_patient_sequential.py
```

The extraction log ends with patient 096 complete and the output-directory message. The checkpoint, status, progress, and feature files establish completion; the log alone does not establish counts.

## Completion and coverage

| Measure | Result |
|---|---:|
| Patients processed | 59 |
| Candidate device-days | 7,374 |
| Candidate patient-local days | 7,343 |
| Device-days with features | 773 (10.48%) |
| Device-days without raw ACC | 6,601 |
| Patient-days with features | 769 |
| Patients with signal | 51 |
| Patients with no signal | 8 |
| Source raw rows, including timestamp multiplicity | 2,746,735,444 |
| Valid retained rows | 620,662,351 |
| Rows removed by timestamp deduplication | 2,126,073,093 (77.40%) |

All progress rows are complete with zero failures and zero pending days. Missing raw days remain missing; they do not indicate inactivity. Candidate coverage is conditional on the plugin movement dictionary, not every calendar day in the clinical interval.

Across all patients, the median number of feature-days is 6; among patients with signal it is 7. Patients with at least 1/3/7/14/30 feature-days: [51, 39, 27, 18, 8]. These are descriptive counts, not chosen eligibility thresholds.

The median saved observed-minute count per feature patient-day is 592, and median saved coverage is 39.93%. Observed minutes contain at least one signal sample and do not establish continuous recording. Multi-device days have the qualification below.

## Validation and aggregation findings

- 76/76 consistency checks passed. Failed checks: none.
- All 24 saved patient medians and means reproduce from saved patient-day values; long-format values match device-day values.
- Device-day raw counts reconcile exactly to valid retained rows plus discarded timestamp duplicates.
- **Multi-device aggregation needs correction before modeling:** 4 patient-days average `exact_duplicate_rows_removed` instead of summing it, understating the patient-day duplicate total by 218,010 rows. Cohort duplicate totals above therefore use device-days.
- These days sum valid minutes but average calendar coverage; neither supplies a union of unique observed minutes across devices. The longest quiet interval is also summed, and other summaries are unweighted device averages. They are saved aggregation conventions, not raw-signal recomputation. Exact pooled medians and overlapping minute coverage cannot be recovered from daily summaries alone.
- Existing extraction files are preserved. The JSON evidence records source hashes and the four affected rows. Next, implement explicit feature-specific aggregation and compare against exclusion of multi-device days, preserving the completed extraction snapshot.
- Archive inventory: 7343 expected patient-day files; 0 missing and 0 empty; 9.60 GB present. This is a filename/size audit; compressed-stream integrity has not been retested.

## Feature missingness and aggregation sensitivity

| Feature | Patients observed / total | Missing among 51 with signal* | Median–mean Spearman |
|---|---:|---:|---:|
| raw_row_count | 51/59 | 0 | 0.905 |
| valid_numeric_row_count | 51/59 | 0 | 0.979 |
| exact_duplicate_rows_removed | 51/59 | 0 | 0.851 |
| valid_signal_minutes | 51/59 | 0 | 0.975 |
| calendar_coverage_fraction | 51/59 | 0 | 0.976 |
| observed_span_hours | 51/59 | 0 | 0.983 |
| median_sampling_interval_ms | 51/59 | 0 | 0.762 |
| p95_sampling_interval_ms | 51/59 | 0 | 0.939 |
| gap_burden_fraction | 51/59 | 0 | 0.686 |
| magnitude_median | 51/59 | 0 | 0.949 |
| magnitude_sd | 51/59 | 0 | 0.831 |
| magnitude_p95 | 51/59 | 0 | 0.805 |
| dynamic_magnitude_rms | 51/59 | 0 | 0.822 |
| dynamic_magnitude_p95 | 51/59 | 0 | 0.761 |
| low_motion_fraction | 51/59 | 0 | 0.956 |
| high_motion_fraction | 51/59 | 0 | 0.836 |
| motion_bout_count | 51/59 | 0 | 0.685 |
| longest_observed_quiet_interval_minutes | 51/59 | 0 | 0.890 |
| daytime_motion_minutes | 51/59 | 0 | 0.921 |
| nighttime_motion_minutes | 51/59 | 0 | 0.399 |
| day_night_motion_ratio | 35/59 | 16 | 0.861 |
| hourly_motion_entropy | 47/59 | 4 | 0.968 |
| magnitude_jerk_median | 51/59 | 0 | 0.660 |
| magnitude_jerk_p95 | 51/59 | 0 | 0.708 |

*Signal means at least one completed feature-day. Undefined feature values remain missing. Correlations compare the saved mean and median across patients; agreement is descriptive and is not model validation.

There are 2 non-quality feature/covariate pairs with absolute patient-level Spearman correlation at least 0.70 among the tested recording-day, observed-minute, and coverage measures. Full coefficients and pairwise counts are in `completion_audit.json`. No cognitive outcomes or p-values were used in this audit.

## Next analysis

Resolve multi-device aggregation, then review coverage and median-versus-mean sensitivity before freezing any model panel. Establish clinical-window alignment: full-interval ACC summaries cannot automatically be treated as prospective T1 predictors. Compare mean baseline, existing phenotype, ACC-only, and combined panels on identical patients and leakage-safe folds after these choices are documented.

Reproduce this audit with `.venv/bin/python3 audit_accelerometer_patient_sequential.py` from the project root. Sources are the sibling completed extraction CSVs and checkpoint; `completion_audit.json` contains detailed distributions, reconciliation results, archive inventory, and SHA-256 hashes.
