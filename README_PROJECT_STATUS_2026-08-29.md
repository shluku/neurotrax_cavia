# NeuroTrax and Passive Smartphone Sensing Project Status

Last updated: 2026-08-29

## Project Purpose

This proof-of-concept study links repeated NeuroTrax cognitive testing with passive smartphone sensing. The project has two scientific aims:

1. Build and audit patient-level baseline digital phenotypes around NeuroTrax T1.
2. Describe digital change between T1 and T2 and explore whether digital information can help characterize or predict cognitive decline.

The project is exploratory. It is intended to establish a defensible data-analysis pipeline, identify promising behavioral signals, expose technical limitations, and define what a better-powered validation study would require.

## Core Data Principles

- Missing data is not zero activity.
- Data availability, feature coverage, and recording intensity are part of the result and must be reported.
- SQL queries must be bounded by both `device_id` and timestamp.
- Dates are aligned using local calendar time in Asia/Jerusalem; SQL timestamps are Unix milliseconds.
- Multiple device identifiers can belong to one patient because of repeated app installations.
- High-frequency sensor tables require separate processing and are not silently mixed with low-frequency features.
- Cognitive outcomes must not be used to create an unsupervised representation when the analysis is described as unsupervised.

## Cognitive Data

The processed NeuroTrax workbook is converted into a patient-level cognitive master table containing global cognition and domain scores, including memory, executive function, attention, processing speed, verbal, motor, and IQ-related fields where available.

Current cognitive master status:

- 83 cognitive records.
- 83 unique `Subject_ID_N` values.
- 62 patients with a valid global T1-to-T2 delta in the earlier candidate table.
- Special NeuroTrax flags such as FP and DI are retained for review rather than being automatically discarded.

Main outputs are under `output/cognitive_master/` and `output/analysis_candidates/`.

## Patient-Level Feature Cohorts

Several acquisition protocols were created as separate, non-destructive cohorts:

- **24-hour T1 baseline:** the exploratory first-valid 24-hour window after T1.
- **10-day T1 baseline:** all available data in the first 10 available days after T1.
- **T1-to-T2 decline:** digital change between independently calculated T1 and T2 feature values.
- **10-day T1-to-T2 decline:** the same longitudinal logic using the 10-day windows.
- **Midpoint baseline:** available data from T1 toward the midpoint of the T1-to-T2 interval; a median approximately 123-day midpoint is used when T2 is unavailable.
- **Midpoint T2 change:** the corresponding backward-looking T2 interval for longitudinal comparison.
- **Full-interval baseline sensitivity:** all available data between T1 and T2, with a patient-level cognitive target based on the mean of T1 and T2 when both exist and T1 alone when T2 is unavailable.

Each cohort has separate feature, coverage, missingness, table-status, and README outputs. Earlier cohorts remain available and are not overwritten by later experiments.

## Current Feature Catalog

The feature work began with selected low-frequency SensorDB tables and expanded through several review and sensitivity stages. Current catalog families include:

- Messaging and calls
- Keyboard timing and typing dynamics
- Applications and foreground activity
- Touch and screen interaction
- GSM and telephony context
- Locations and significant activity
- Battery and charging context
- Bluetooth context where available

Light, proximity, barometer, accelerometer, and other motion-derived features were treated separately because of coverage, interpretation, or table size. High-frequency raw motion streams require dedicated signal-processing decisions before they are added to the patient-level models.

### Raw accelerometer SQL one-minute reconnaissance (2026-09-02)

A read-only SQL reconnaissance was added for the raw `accelerometer` and `linear_accelerometer` tables. It defines the experiment span from the earliest and latest timestamp across both raw tables, selects the lower midpoint local calendar day, and inspects the exact 09:00-09:01 window in `Asia/Jerusalem` time. Rows are ordered by timestamp, device ID, and row ID. The paired `sensor_accelerometer` and `sensor_linear_accelerometer` tables are inspected for hardware and sampling-context metadata.

Current result:

- Raw experiment span: 2025-01-05 through 2026-07-15.
- Midpoint inspection day: 2025-10-10.
- `accelerometer`: 0 rows and 0 devices in the selected minute.
- `linear_accelerometer`: 306 rows from 1 device in the selected minute, spanning 59.736 seconds, approximately 5.1 rows/second.
- The raw linear-acceleration JSON contains three signal values (`double_values_0`, `double_values_1`, and `double_values_2`) plus accuracy and timestamp fields.
- Sensor metadata includes minimum delay, resolution, maximum range, power, sensor name, vendor, type, and version. These describe hardware or collection context and do not prove continuous raw sampling at the nominal rate.

An additional explicit-date probe was run for 2025-06-01 at 09:00-09:01 local time. It found 9,925 `accelerometer` rows from 6 devices and no `linear_accelerometer` rows. The paired `sensor_accelerometer` metadata table contained 735 rows for those six devices. This contrast confirms that the two raw streams must be analyzed as separate modalities rather than treated as interchangeable. The dated output is in `sql_median_day_minute/2025-06-01/`, and both dates can be selected in Streamlit.

A second time-window probe was run on the same date at 21:00-21:01 local time. It found 11,013 `accelerometer` rows from 5 devices and no `linear_accelerometer` rows. The paired `sensor_accelerometer` metadata table contained 684 rows for those five devices. The output is in `sql_median_day_minute/2025-06-01_21-00/`; the Streamlit selector distinguishes both times on 2025-06-01.

A third explicit-date probe was run for 2025-07-01 at 09:00-09:01 local time. It found 3,662 `accelerometer` rows from 2 devices and 2,972 `linear_accelerometer` rows from 1 device. The paired sensor metadata contained 298 rows for the two general-accelerometer devices and 27 rows for the linear-accelerometer device. The output is in `sql_median_day_minute/2025-07-01/`.

Outputs are in `output/analysis_candidates/phase2_accelerometer_framework/sql_median_day_minute/` and are displayed at the top of the **R&D** Streamlit page. This remains a structural reconnaissance step; no patient-level accelerometer features or models were changed.

### Plugin-anchored full-day general ACC pilot (2026-09-03)

A separate pilot was added to use the mapped plugin movement dictionary to select full local calendar days for raw general-accelerometer analysis. The first two mapped patients in numeric order are `002` and `003`. Each unique patient-device-local-date with at least one plugin movement event is queried from local midnight through the next local midnight; the plugin event minute is retained as context and does not restrict the ACC window.

The pilot defines 24 exploratory features covering raw and valid signal counts, day coverage, observed span and sampling gaps, vector-magnitude signal level, dynamic motion proxies, observed-minute motion bouts and quiet intervals, day/night activity, hourly distribution, and magnitude-change-rate summaries. General ACC includes gravity, so these are phone-signal proxies rather than validated clinical movement measures. Frequency-domain features remain deferred until sampling regularity and signal sufficiency are reviewed.

Current partial-run accounting:

- 2 patients and 108 candidate patient-device-days.
- 6 device-days with calculated features: 002 on 2025-06-07 and 2025-06-23; 003 on 2025-01-06, 2025-01-07, 2025-01-14, and 2025-01-25.
- 13 device-days with confirmed zero raw ACC rows.
- 16 explicit error/retry rows, including database transport failures and interrupted earlier calculation attempts.
- 73 candidate device-days remain pending; they are not classified as missing.
- The calculated feature rows cover 24,868,316 raw rows in their recorded preflight context, with high duplicate/fragmentation burden visible in the QC fields.

Outputs are under `output/analysis_candidates/accelerometer_plugin_event_day_pilot/` and are shown in the new **ACC Movement Feature Pilot** Streamlit sidebar page. The extraction is resumable with `.venv/bin/python3 -u extract_accelerometer_plugin_event_day_pilot.py`; `--finalize-only` rebuilds derived tables without a SQL connection. No prior patient-level cohort or ACC output is overwritten.

### ACC feature audit and patient-level handoff (2026-09-03)

The saved pilot features now have a separate SQL-free audit and aggregation layer. It adds per-observed-hour versions for selected count/minute motion measures, summarizes distributions and patient/day coverage, compares features with raw row count, valid signal minutes, calendar coverage, and observed span, and records a recommended model role for each feature.

The 24 features are currently organized as 12 primary behavioral candidates, 3 signal-level sensitivity features, and 9 quality-control-only variables. The QC variables describe collection intensity or sampling and are excluded from the primary behavioral panel. Patient-level rows use the median across completed patient-local days, while mean values remain available for sensitivity review. No final feature selection or model fitting is permitted from the two-patient pilot.

The audit outputs are under `output/analysis_candidates/accelerometer_feature_audit/` and are shown in the **ACC Feature Audit** Streamlit sidebar page. After the larger patient cohort is extracted, the planned handoff is to compare the mean baseline, existing digital phenotype, ACC-only, existing-plus-ACC, and coverage-normalized Ridge models on identical patients and validation folds, with all imputation, scaling, feature selection, and alpha selection fit inside training folds.

### Accelerometer device hardware timeline (2026-09-02)

A device-level hardware and collection-context table was built from the local Parquet copies of `sensor_accelerometer`, `sensor_linear_accelerometer`, and raw `linear_accelerometer`. The main table has one row per device ID and records metadata first/last seen timestamps, active months, sensor identity, vendor, type/version, nominal hardware fields, and raw linear-accelerometer counts and time span where available. A separate configuration table summarizes how often each sensor configuration appears, and a monthly table shows device prevalence over the experiment.

Current audit counts:

- 564 device IDs in the combined timeline (562 from sensor metadata, plus 2 raw linear-only IDs).
- 559 devices in `sensor_accelerometer` metadata.
- 386 devices in `sensor_linear_accelerometer` metadata.
- 178 devices with raw linear-accelerometer observations in the local Parquet file.
- 65 distinct sensor configurations: 52 general accelerometer configurations and 13 linear-accelerometer configurations.
- 16,696 general-accelerometer metadata rows and 3,051 linear-accelerometer metadata rows.
- All parsed sensor metadata JSON rows were valid.
- Full raw `accelerometer` per-device counts are explicitly marked unavailable because a local raw ACC Parquet copy has not been created yet.

The results are exploratory hardware and data-collection context, not behavioral features. `device_id` is an app/device identifier and is not automatically a unique physical phone or patient. Nominal sensor minimum delay is not treated as observed sampling frequency. Outputs are in `output/analysis_candidates/phase2_accelerometer_framework/device_hardware_timeline/` and are displayed under **R&D → Accelerometer device hardware timeline** in Streamlit. No SQL tables, existing Parquet files, or patient-level cohorts were modified.

### Patient-device crosswalk (2026-09-02)

The existing `output/label_device_map.csv` was linked to the hardware timeline using the project’s strict mapping rule: exact three-digit patient labels take precedence over legacy labels. The active cohort is the 82 current cognitive candidates with Subject `001` excluded, giving 81 patients.

Current crosswalk audit:

- 162 device IDs are assigned to 84 numeric patient labels in the mapping source.
- 148 mapped device IDs are present in the local hardware timeline.
- 14 mapped device IDs are not observed in the local sensor metadata or raw linear-accelerometer Parquet currently available.
- 416 device IDs are present in the local hardware timeline without a numeric patient mapping and remain explicitly unmatched.
- Among the 84 numeric labels, 27 have one mapped device, 40 have two, and 17 have three or more. This is why device IDs cannot be interpreted as patient counts.

The patient-level outputs are `patient_device_crosswalk.csv`, `patient_device_summary.csv`, `patient_device_configuration_crosswalk.csv`, and `unmatched_device_ids.csv` in `output/analysis_candidates/phase2_accelerometer_framework/device_hardware_timeline/`. They are shown in the Streamlit hardware section. The 65 hardware configurations remain a separate sensor-metadata concept: 52 general-accelerometer and 13 linear-accelerometer combinations of sensor identity, vendor, type/version, and nominal hardware fields. They are not 65 patients or 65 physical phones.

### Patient accelerometer data coverage and unmatched-device audit (2026-09-02)

A local evidence audit was added for the active 81-person cohort. It retains one row for every patient and separates hardware metadata from actual raw-signal evidence:

- 77 of 81 patients have `sensor_accelerometer` metadata, 31 have `sensor_linear_accelerometer` metadata, and 25 have raw linear-accelerometer rows in the local Parquet inventory.
- Of the 25 patients with raw linear-accelerometer rows, 24 span more than one local calendar day. Eleven patients have confirmed raw general-accelerometer observations in the existing bounded SQL probes and completed 24-hour downloads; six of those span more than one local calendar day. This is confirmation of selected devices, not a full raw-ACC coverage estimate.
- The active cohort has 159 mapped device IDs; 146 have completed local evidence on or before 2025-12-30, representing 77 of 81 patients.
- 416 observed device IDs remain without a current numeric patient mapping. Of these, 153 have raw linear-accelerometer rows and should be treated as high-priority linkage candidates rather than discarded.

The report is in `output/analysis_candidates/phase2_accelerometer_framework/device_hardware_timeline/data_coverage/` and is displayed under **R&D → Patient ACC coverage and unmapped-device investigation**. The multi-billion-row SQL `accelerometer` table was not fully scanned because the current remote query path is too slow and unstable for a complete per-device audit. Therefore, no raw-ACC probe absence is interpreted as proof of no raw ACC. A local raw-ACC export/Parquet conversion remains the definitive next step.

### Raw general-ACC daily export pilot (2026-09-02)

The first local-calendar day of raw general ACC was exported to the mounted `SENSORDATA_MAIN` drive as `motion_accelerometer/sql_zst/accelerometer_2025-01-05_to_2025-01-06.sql.zst`. The half-open local window is 2025-01-05 00:00 through 2025-01-06 00:00 Asia/Jerusalem. It contains 301,682 rows from one device, observed from 18:45:38 through 23:59:59 local time. The device is currently unmatched to a patient, so the export intentionally includes all devices rather than only the active 81-person mapping. The 3.8 MB `.sql.zst` file passed zstd integrity testing; its expected counts and path are recorded in the external-drive `daily_export_manifest.jsonl` and displayed at the top of **R&D** in Streamlit.

Future days should use the same timestamp-chunk method, preserve each `.sql.zst` file, and use `--data-only` after the first schema-bearing day so importing multiple chunks cannot replace earlier data. No source SQL tables were modified and no Parquet conversion has been started for this ACC export.

The next seven-day export was started for the half-open local window 2025-01-06 00:00 through 2025-01-13 00:00. It uses only device IDs mapped to the active 81-person cohort and is split into one-day, data-only files named `accelerometer_YYYY-MM-DD_to_YYYY-MM-DD_mapped81.sql.zst`. The seven-day aggregate preflight was too slow for the remote multi-billion-row table, so the daily checkpoints are intentional. Jan 6 completed as a 74,710,412-byte dump containing 6,355,243 rows from 6 mapped devices and passed zstd integrity validation. The run was stopped during Jan 7 at the user's request; its 5.8 MB `.partial` file is preserved for audit and is not treated as a completed export. Jan 8–13 were not started.

### Plugin activity movement timestamp dictionary (2026-09-03)

A mapped timestamp-level dictionary was built from `plugin_google_activity_recognition` before starting another raw ACC extraction. The extraction uses the active 81-patient cohort, excludes subject `001` under the existing project rule, queries only the 159 mapped device IDs, and bounds each query to local midnight at T1 through local midnight at T2 (T2 exclusive). Patients without a valid ordered T2 remain documented but are not assigned an artificial endpoint.

The completed run queried 123 valid patient-device intervals with no database query failures and retained 2,013,532 plugin events. Each event keeps its timestamp, patient/device mapping, primary activity label, activity type, confidence, nested candidate labels, and a canonical movement-context class (`active_land`, `vehicle`, `still`, `orientation_change`, `unknown`, or `other`). The full source JSON payload is not copied into the dictionary. UTC minute bins and device-day/patient-day summaries were also generated, allowing later ACC windows to be selected using explicit phone-derived movement context and observed data density.

The dictionary is exploratory phone-derived context, not direct body movement and not a clinical outcome. A mapped device with zero plugin rows is distinguished from a failed query, and an empty minute means no observed plugin event rather than confirmed stillness. The outputs are in `output/analysis_candidates/plugin_activity_movement_dictionary/`, with the protocol and interpretation in `README_plugin_activity_movement_dictionary.md`. Streamlit shows the dictionary at the top of **R&D**, including patient-level and patient-day coverage, activity-label totals, device status, and responsive samples of the minute/event dictionaries. No existing cohort, feature, or model output was changed.

### T1-only plugin activity extension for patients without T2 (2026-09-03)

The 20 active patients without T2 were additionally queried using their mapped devices from local midnight at T1 through the latest usable timestamp in the plugin table, `2026-07-15 14:59:38` local time. This produced 36 successful device intervals, 569,261 additional events, and 352,350 occupied UTC minutes; 19 of the 20 patients had at least one event. The extension is stored separately under `output/analysis_candidates/plugin_activity_movement_dictionary/t1_only_extension/` and is shown in its own Streamlit subsection.

This endpoint is a data-availability boundary, not a clinical T2 visit. The T1-only events can be used to characterize available movement-context evidence and guide ACC extraction, but should not be pooled directly with the T1-to-T2 dictionary for decline modeling because follow-up duration is not comparable.

## Supervised Modeling So Far

The project tested cross-validated patient-level models against the same mean baseline, including:

- Mean baseline.
- Ridge regression.
- Domain-specific Ridge models.
- Direction-constrained and gradient-weighted exploratory models.
- Slope-selected feature models.
- T1-to-T2 change models.
- Full-interval Ridge sensitivity analysis.

The general result is that the current small and heterogeneous cohorts do not yet produce a clinically reliable predictive fit. The mean baseline is often competitive. This is not a failure of the data pipeline; it is evidence that feature coverage, sample size, exposure differences, and the relationship between passive behavior and cognitive scores need more work before clinical prediction can be claimed.

## Unsupervised Phenotyping

The largest current patient-level baseline analysis uses the median-timespan T1 cohort.

### Fixed PCA and clustering result

- Source patients: 81.
- Patients entering the fixed unsupervised representation: 76.
- Features used to create the default PCA/clustering input: 41.
- Active catalog features available for descriptive post-hoc comparison: 54.
- PCA PC1 plus PC2 explains approximately 59% of transformed feature variation.
- Reference solution: two clusters, Cluster 0 with 11 patients and Cluster 1 with 65 patients.
- Mean silhouette: approximately 0.458.
- 80%-subsample ARI: approximately 0.997.

The cluster structure is stable and is mainly an interaction-intensity pattern. Cluster 0 generally has more messaging, keyboard, screen, touch, and GSM activity. It should not be called a disease subtype or clinical class.

### Technical confounding audit

The same cluster is also associated with collection-intensity variables:

- Higher total source-row volume.
- Slightly better table coverage.
- Fewer missing feature values.
- More calculated tables.

Device counts and observed timestamp spans are relatively similar. The current interpretation is therefore mixed: the structure may contain genuine digital interaction behavior, but it may also contain differences in recording or sampling intensity.

### Cognitive overlays

Observed cognitive outcomes were added only after PCA and clustering. Global T1 has almost no relationship with the PCA axes, and global T2-T1 change also has a weak relationship. Domain-specific cognitive deltas do not currently show a convincing association with the fixed digital-behavior structure.

### Follow-up-informed baseline sensitivity

A separate exploratory sensitivity was added for every available cognitive domain:

- If T2 is higher than T1, use `(T1 + T2) / 2`.
- If T2 is lower than or equal to T1, retain T1.
- If T2 is unavailable, retain T1.

This changes the descriptive cognitive reference but does not create a strong PCA gradient. Because it uses future T2 information, it is not a valid prospective baseline target or prediction model.

Unsupervised analysis files:

- `unsupervised_phenotyping.py`
- `unsupervised_phenotyping_posthoc.py`
- `UNSUPERVISED_PHENOTYPING_PROTOCOL.md`
- `UNSUPERVISED_POSTHOC_PROTOCOL.md`
- `output/analysis_candidates/unsupervised_phenotyping_median_span/`

## Current Scientific Interpretation

The strongest current finding is not a cognitive prediction result. It is a stable, interpretable digital-interaction structure that spans several smartphone modalities. The main unresolved question is whether it represents patient behavior, collection intensity, or both.

The next defensible unsupervised sensitivity analysis is exposure adjustment:

- Convert count features into rates per observed day or valid recording day.
- Keep fractions, ratios, medians, and diversity measures on their appropriate scales.
- Re-run the same PCA and clustering audit without using cognitive outcomes.
- Compare cluster membership, stability, feature drivers, technical confounding, and cognitive overlays with the raw-count solution.

This should be performed alongside the current raw-count result, not as a replacement.

### Coverage-adjusted PCA post-hoc audit (2026-08-30)

A separate corrected sensitivity run was completed without changing the original PCA or cluster outputs. It uses the same 41-feature panel and compares:

- Original processing reference: 76 patients, PC1+PC2 variance 59.1%, silhouette 0.458.
- Exposure-normalized features: volume-like features divided by observed timestamp-span days; PC1+PC2 variance 83.1%, silhouette 0.728, ARI versus original clusters 0.616.
- Technical-residualized features: transformed features residualized against observed span, source rows, panel coverage, feature missingness, and table coverage; silhouette 0.201, ARI versus original clusters 0.010.
- Quality-trimmed reference: extreme 5% quality/intensity tails removed, 57 patients; silhouette 0.196, ARI versus original clusters 0.061.

The raw reference exactly reproduced the original result. The adjusted runs changed the patient grouping substantially, so the original high-interaction structure cannot yet be treated as independent of collection intensity or coverage. The new outputs and protocol are in `output/analysis_candidates/unsupervised_phenotyping_median_span/coverage_adjusted_posthoc/`, and Streamlit exposes them under the **Coverage-adjusted audit** tab within **Exploratory Unsupervised Phenotyping**.

### Top-five Ridge feature USML (2026-08-30)

A separate USML run was performed using the five strongest real features from the midpoint/all-available T1 Ridge coefficient ranking. Missingness-indicator terms were excluded, and the features were restricted to the original 41-feature USML panel:

- `keyboard_median_word_completion_time_ms`
- `app_use_diversity`
- `telephony_mobile_data_enabled_fraction`
- `touch_scroll_index_change_median`
- `message_distinct_event_count`

The run analyzed 71 patients and selected a two-cluster reference solution of 24 versus 47 patients. PC1+PC2 explained 63.0% of feature variation, but the silhouette was only 0.234 and the repeated 80%-subsample ARI was 0.229. Global T1 had a modest descriptive relationship with PC1/PC2, but the cluster comparison was not convincing. The technical audit showed substantial differences in panel coverage and source-row intensity between the clusters, so this Ridge-informed five-feature structure should be treated as hypothesis-generating and coverage-sensitive. Outputs are in `output/analysis_candidates/unsupervised_phenotyping_median_span/top5_ridge_usml/`, with a **Top-5 Ridge USML** tab in Streamlit.

### Domain-specific Ridge-informed USML (2026-08-30)

A separate exploratory extension now ranks the five strongest real features independently for Global, Memory, Executive function, Processing speed, Attention, and Motor T1. The ranking uses the all-available Phase 11 T1 catalog with repeated 5-fold cross-validation repeated 20 times, then restricts the selected features to the fixed 41-feature USML panel. Missingness-indicator terms are excluded, and a feature can appear in more than one domain panel.

Each domain has its own PCA, K-means audit, patient map, 3D map with the relevant observed T1 score, cluster profiles, technical confounding audit, and post-hoc T1/T2/delta overlays. The results show meaningful panel differences: Memory selected screen-event features and analyzed 76 patients with subsample ARI 0.860; Processing speed selected telephony, touch, screen, and keyboard features and selected k=3 with subsample ARI 0.837; Attention selected a mixed screen/telephony/keyboard/app panel and had subsample ARI 0.432. Global and Executive function selected the same five-feature panel as the existing global top-five run, with subsample ARI 0.229. Motor selected keyboard, screen, touch, app, and GSM-neighbor features, with subsample ARI 0.231.

These results are useful for hypothesis generation, but the outcome-informed feature ranking means the maps are not independent validation. Technical variables remain post-hoc only. Outputs are in `output/analysis_candidates/unsupervised_phenotyping_median_span/domain_specific_ridge_usml/`, with a **Domain-specific Ridge USML** tab inside **Exploratory Unsupervised Phenotyping**.

### Pre-specified coverage-adjusted Motor/Attention inference (2026-08-30)

The Motor and Attention candidates were tested in a separate stricter analysis. Volume-like features were normalized by observed timestamp span, transformed values were residualized against collection-intensity and coverage variables, and each outcome received a new domain-specific top-five panel. The analysis fixed k=2 and used 100 selection-aware permutations; each permutation repeated Ridge feature selection, five-feature PCA, and clustering. A 1,000-resample bootstrap quantified variability conditional on the adjusted panel.

The original exploratory effects did not persist: adjusted Motor standardized cluster difference was `0.387` with selection-aware permutation `p=0.535` and bootstrap 95% interval `-2.470 to 2.053`; adjusted Attention standardized difference was `-0.224` with permutation `p=0.762` and bootstrap 95% interval `-1.045 to 0.970`. This suggests the earlier Motor/Attention p-values were likely influenced by outcome-informed selection and/or collection-intensity effects. It does not prove that no behavioral signal exists. It defines the current POC result more honestly: the unadjusted findings are candidates, not robust evidence yet. Outputs are in `output/analysis_candidates/unsupervised_phenotyping_median_span/domain_specific_adjusted_inference/`, with an **Adjusted Motor/Attention** tab in Streamlit.

### All-mapped ACC event-day extraction from local archives (2026-09-03)

The ACC extraction was expanded from the original two-patient pilot to every patient currently represented in the mapped plugin movement dictionary. The current source mapping contains 59 of the 81 NeuroTrax patients and 7,374 mapped patient-device-local-day candidates. Patients without T2 are included in this baseline ACC extraction whenever they have a mapped device; they will be excluded only from later T1-to-T2 delta analyses. The remaining 22 patients require a separate device-crosswalk investigation and are not silently treated as having no ACC data.

The remote raw ACC table could not reliably sustain device-specific Python queries or aggregate preflights. A new resumable workflow therefore exports one local calendar day at a time with `mysqldump`, restricted to that day's candidate mapped devices, and preserves each compressed `.sql.zst` archive on the first external drive under `motion_accelerometer/plugin_event_day_sql_zst/`. The 24 ACC features are calculated locally from each completed archive; no raw signal archive is deleted or overwritten.

The first validation day, 2025-01-06, reused the existing mapped archive and produced six additional patient-device-day feature rows. The current project checkpoint contains 7 completed feature-days, 50 retryable prior extraction errors, and 7,317 pending device-days. This is an active, partial extraction rather than a completed cohort result. The run script is `extract_accelerometer_plugin_event_day_from_archives.py`; the live checkpoint and tables are in `output/analysis_candidates/accelerometer_all_mapped_event_day_features/`, and the corresponding patient-level audit is in `output/analysis_candidates/accelerometer_all_mapped_feature_audit/`. Streamlit exposes the live counters under **ACC All-Mapped Feature Audit**.

## Manuscript Work

A manuscript workspace has been created under `manuscript/`. The current framing is a methods and proof-of-concept paper describing:

- Patient-level passive digital phenotyping in a small heterogeneous cohort.
- Hundreds of feature and window-processing decisions.
- Coverage and missingness auditing.
- Hand-selected and sensitivity feature panels.
- Baseline and longitudinal exploratory modeling.
- Transparent reporting of weak or non-confirmatory findings.

The manuscript should use reader-facing terms rather than internal labels such as “Phase 11” or “SensorDB” without explanation.

## External Drive and Parquet Status

The first external drive is mounted at:

`/Volumes/SENSORDATA_MAIN/sensordata_backup`

It currently contains:

- Compressed SQL logical backups for the low-frequency tables.
- Parquet conversions for those completed tables.
- A dedicated `motion_linear_accelerometer/` folder.
- Checkpoints and logs for resumable operations.

The source `.sql.zst` files are intentionally preserved when Parquet files are created.

Important current motion status:

- `sensor_linear_accelerometer` backup and Parquet conversion are complete.
- The large raw `linear_accelerometer` table is estimated at approximately 534 million rows and 222 GB of database storage.
- Previous raw `linear_accelerometer` backup attempts failed because `mysqldump` was denied access to the `column_masking_policy` metadata.
- This is a database-client/permissions issue, not evidence that the drive lacks space.
- The corrected raw `linear_accelerometer` backup completed on 2026-08-30.
- The validated archive is `motion_linear_accelerometer/sql_zst/linear_accelerometer.sql.zst` and is 21,251,552,372 bytes (about 21.25 GB decimal).
- The raw archive was validated with `zstd -t`; the completion checkpoint records `mysqldump_returncode=0` and `zstd_returncode=0`.
- A separate Parquet conversion completed on 2026-09-02 at `motion_linear_accelerometer/parquet/linear_accelerometer.parquet`.
- The Parquet file contains 561,602,194 rows, 4 columns, and is 21,036,813,713 bytes (about 21.04 GB decimal).
- The Parquet metadata was inspected successfully; the raw `.sql.zst` archive remains preserved and unchanged.
- The SQL database remains the source of truth and is unchanged.

The next motion-data step is to review the Parquet schema and analysis requirements before beginning feature extraction from the raw motion table. The `.zst` source must remain preserved.

## Immediate Next Step

1. Keep the completed raw `linear_accelerometer.sql.zst` archive as the archival copy.
2. Use the validated `linear_accelerometer.parquet` copy for future local inspection, preserving the `.zst` source.
3. Continue interpreting the coverage-adjusted PCA sensitivity results before making stronger claims about a digital-behavior phenotype.
4. Do not begin feature extraction from the raw motion table until its schema, timestamps, device filtering, sampling behavior, and manageable analysis windows are reviewed.

## Important Boundaries

- No clinical phenotype or diagnosis has been validated.
- Exploratory p-values are not confirmatory evidence.
- The small Cluster 0 limits precision.
- Features selected after inspecting the same outcome or cluster should not be presented as independent validation.
- Follow-up-informed cognitive values must not be used for prospective prediction claims.
- High-frequency motion data should be processed with a separate signal-quality and windowing protocol.
