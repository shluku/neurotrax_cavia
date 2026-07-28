# Phase 5: T2 Digital Feature Extraction Protocol

## Purpose

Extract the manually selected Phase 2 digital features around the T2 assessment using the same feature definitions as T1, while changing only the assessment anchor and pre-assessment window rule.

This phase creates the T2 patient-level digital dataset. It does not yet calculate decline models.

## T2 Cohort

Include patients with:

- a valid `Subject_ID_D`;
- a valid `T2_date_iso`;
- a valid patient-to-device mapping.

Patients without a T2 date remain documented in the cohort audit but cannot receive T2 feature values.

The existing manually reviewed exclusion and device-mapping rules remain visible in the status outputs.

## Standard Pre-T2 Window

For ordinary selected features, search the interval:

`[T2 - 7 days, T2]`

Select the first valid 24-hour window whose end is no later than T2. The window selector must retain:

- T2 anchor;
- search start and end;
- selected window start and end;
- selection rule;
- first and last source timestamps;
- row counts by device;
- devices available and used.

No post-T2 rows are allowed.

## 30-Day Fallback

If no valid window exists in the preceding 7 days, extend the search backward to `T2 - 30 days` and select the latest valid 24-hour window available before T2.

The fallback must be labeled separately from the primary T2-week window. It must never be silently combined with the primary window.

The intended labels are:

- `t2_week_first_valid_24h`
- `t2_30day_latest_valid_24h_fallback`
- `missing_no_valid_pre_t2_window`

## Feature Algorithms

The T1-reviewed feature calculations will be reused without changing feature names, units, or definitions. The T2-specific change is the window anchor.

Feature families include:

- application foreground behavior;
- battery and charging context;
- Bluetooth and GSM diversity/transition behavior;
- calls, messages, and telephony;
- keyboard timing and pauses;
- light exposure;
- locations and movement through locations;
- activity-recognition states;
- screen behavior;
- touch behavior;
- selected barometer, significant-motion, and linear-accelerometer support features.

Table-specific adjusted algorithms remain separately labeled. Their longer calculation windows and minimum-row rules must be preserved and audited rather than silently converted into ordinary 24-hour features.

## Missingness and Coverage

For every patient, table, and feature, preserve:

- calculated value or missing value;
- feature status;
- table status;
- source row count;
- usable row count where available;
- device IDs available and used;
- window rule;
- window start/end in milliseconds and local time;
- first/last source timestamps;
- calculation or database error message.

Missing values are not converted to zero. Coverage is recorded separately from behavior.

## Forum: Coverage Decision After the First T2 Run

The first T2 run showed substantial coverage limitations. The current decision is:

- clean duplicate patient-table output rows before interpretation;
- temporarily exclude the `light` table from the active T2 feature set because repeated database failures make its current output unreliable;
- skip a separate light retry for this run and revisit light together with future accelerometer work;
- create feature-level, table-level, and patient-level coverage audits;
- define the working T2 feature set using a minimum patient coverage threshold of 10%;
- retain features below 10% coverage as sensitivity-only and do not use them in the primary exploratory model;
- defer the broader latest-available-before-T2 extraction until after the next T1 run.

The 10% threshold is a pragmatic POC screening rule, not a clinical validity threshold. The resulting feature set remains exploratory and must report coverage, missingness, and the number of patients contributing each feature.

## Execution Sequence

1. Load and freeze the T2 patient cohort and selected feature list.
2. Validate T2 dates, device mappings, and table names.
3. Run the database-wide T2 extraction with resumable table/status outputs.
4. Rebuild one wide patient-level T2 feature table from the long outputs.
5. Produce feature-level missingness and table-level coverage audits.
6. Compare T1 and T2 feature schemas, units, distributions, and window labels.
7. Only after extraction review, calculate T1-to-T2 feature changes and cognitive decline.

## Boundary

This remains a proof-of-concept extraction. It is not a prospective clinical prediction dataset until the timing, coverage, feature stability, and T2 outcome availability have been audited.
