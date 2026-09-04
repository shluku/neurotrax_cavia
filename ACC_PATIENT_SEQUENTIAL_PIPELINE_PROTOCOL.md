# General Accelerometer Patient-Sequential Extraction Protocol

**Status:** validated two-patient run complete; full mapped-cohort extraction ready to resume

**Last documented:** 2026-09-04

## Purpose

This protocol defines the current general-accelerometer pipeline. It converts
raw three-axis phone accelerometer records into exploratory patient-level
movement features. The pipeline is deliberately patient-sequential: every
candidate day for one patient is attempted, the successful days are merged
into that patient's summary, and only then does processing continue to the
next patient.

This is an exploratory digital-phenotyping analysis. The features are signal
proxies and do not identify walking, tremor, or another specific clinical
activity.

## Cohort And Current Checkpoint

The candidate manifest is derived from the plugin activity movement dictionary.
Only patient-device-local days with a mapped patient and device are eligible.

| Item | Current value |
|---|---:|
| Mapped patients | 59 |
| Candidate device-days | 7,374 |
| Candidate patient-local days | 7,343 |
| Completed patients | 2 (003, 004) |
| Remaining patients | 57 |
| Remaining candidate device-days | 7,091 |
| Remaining candidate patient-local days | 7,060 |

Completed checkpoint:

| Patient | Candidate days | Feature days | No raw ACC days | Failed days |
|---|---:|---:|---:|---:|
| 003 | 106 | 24 | 82 | 0 |
| 004 | 177 | 85 | 92 | 0 |

The two completed patients and all subsequent patients are stored together in
the cumulative sequential output files. The original pilot outputs are not
overwritten.

## Acquisition Rule

1. Read the movement dictionary and select mapped patient, device, and local date rows.
2. For each candidate, query the complete local calendar day: 00:00 through the next local midnight in `Asia/Jerusalem`.
3. Query only the matched device IDs for that patient-day.
4. In the database, group by `device_id + timestamp`, retain the row with the smallest database `_id`, and count the original multiplicity.
5. Discard later rows at the same device timestamp, including rows with different axis values. The discarded count is retained as a QC variable.
6. Parse the retained JSON x/y/z values and retain only valid timestamps and valid numeric three-axis values.
7. Never convert unobserved time into zero movement. A day with no returned raw rows is recorded explicitly as `no_raw_rows`.

## Feature Calculation

For each completed patient-device-local day, calculate the current 24-feature
catalog:

- raw and valid row counts
- duplicate rows removed
- valid signal minutes and calendar coverage
- observed span, sampling intervals, and gap burden
- vector-magnitude level summaries
- dynamic magnitude relative to the day's median magnitude
- low- and high-motion fractions
- motion-bout count and longest observed quiet interval
- daytime and nighttime motion minutes
- day/night motion ratio and hourly motion entropy
- median and upper-tail magnitude change rate (jerk proxy)

The dynamic motion measure is an orientation-tolerant signal proxy, not a
validated activity classifier. Threshold-based features require adequate
observed time and must be interpreted together with coverage variables.

## Aggregation And Files

After each candidate day, the pipeline writes the current status, device-day
features, patient-day merge, patient-level merge, progress table, and run
summary. Multiple devices on one patient-local day are combined into a
patient-day row. The patient-level table contains the median and mean across
completed patient-local days; the documented primary aggregation is the
median.

Main output directory:

`output/analysis_candidates/accelerometer_patient_sequential_pipeline/`

Important files:

- `accelerometer_patient_sequential_candidates.csv`
- `accelerometer_patient_sequential_status.csv`
- `accelerometer_patient_sequential_device_day_features.csv`
- `accelerometer_patient_sequential_patient_day_features.csv`
- `accelerometer_patient_sequential_patient_level_features.csv`
- `accelerometer_patient_sequential_patient_progress.csv`
- `accelerometer_patient_sequential_run_summary.csv`
- `accelerometer_patient_sequential_checkpoint.json`

Compressed per-day timestamp-deduplicated archives are retained on the
external drive under:

`/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_accelerometer/plugin_event_day_sql_zst/`

No raw accelerometer rows are written into the local feature tables, and no
existing pilot output is deleted.

## Restart And Resume

After restarting the computer:

1. Mount the external drive at `/Volumes/SENSORDATA_MAIN`.
2. Open the project directory and use the project virtual environment.
3. Confirm that the source database is reachable.
4. Run the full remaining-cohort command:

```bash
.venv/bin/python3 -u extract_accelerometer_patient_sequential.py
```

The command reads the cumulative manifest and status files. Completed
patient-days are skipped automatically, so it resumes from the first pending
candidate without reprocessing patients 003 or 004. It processes patients in
patient ID order and does not start downstream modeling automatically.

To validate or retry one patient only:

```bash
.venv/bin/python3 -u extract_accelerometer_patient_sequential.py --patient-id 005
```

Use `--force --patient-id NNN` only when a patient must be deliberately
reprocessed. Use `--through-date YYYY-MM-DD` only for a bounded validation run;
it leaves later dates pending.

## Monitoring

The Streamlit page **ACC Patient-Sequential Pipeline** reads the output files
live. Refresh it to see completed feature-days, no-raw days, failures, pending
days, patient progress, and patient-level rows. The protocol is also shown in
that page's **Protocol** tab.

Before downstream modeling, review the final distribution of coverage,
observed minutes, duplicate burden, no-raw days, and feature missingness. The
current run is extraction only; it does not add ACC features to the existing
digital-phenotype models yet.

## Deliberately Deferred

Light, proximity, linear-accelerometer, barometer, and other supplemental
modalities are outside this current pipeline. They will be analyzed and
joined later under separately documented acquisition rules.
