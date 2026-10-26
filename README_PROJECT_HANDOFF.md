# NeuroTrax–Passive Smartphone Sensing Project Handoff

**Purpose:** portable project summary for moving this project to another computer or handing it to another researcher.

**Document status:** living handoff document; update the live ACC checkpoint after the current extraction finishes.

**Last verified:** 2026-09-06, Asia/Jerusalem.

## 1. Executive summary

This project links repeated NeuroTrax computerized cognitive assessments with passive smartphone and sensor records. It is an exploratory observational proof-of-concept and methods/feasibility study, not a diagnostic or clinically validated prediction system.

The project has two connected aims:

1. Build an auditable, patient-level digital phenotype around the first cognitive assessment (T1).
2. Explore whether passive digital measurements describe or predict change between T1 and T2.

The work has progressed from raw-table discovery and feature review to patient-level feature extraction, coverage auditing, supervised modeling, unsupervised sensitivity analyses, and a dedicated general-accelerometer pipeline.

The central scientific conclusion so far is methodological: passive smartphone data can be converted into interpretable patient-level summaries, but coverage, missingness, recording intensity, device changes, small sample size, and window choice strongly affect the results. Current models do not support a clinically reliable cognitive estimate or decline predictor.

The current operational priority is the resumable, patient-sequential extraction of general accelerometer data. It is running independently and must be allowed to finish before ACC modeling or final manuscript claims are made.

## 2. Current operational state

### 2.1 Authoritative ACC status

The most current operational protocol is [`ACC_PATIENT_SEQUENTIAL_PIPELINE_PROTOCOL.md`](ACC_PATIENT_SEQUENTIAL_PIPELINE_PROTOCOL.md), last documented 2026-09-04. The live source of truth is the checkpoint and cumulative output directory:

`output/analysis_candidates/accelerometer_patient_sequential_pipeline/`

As of the last live check on 2026-09-06:

| Quantity | Current value |
|---|---:|
| Mapped patients in manifest | 59 |
| Candidate device-days | 7,374 |
| Candidate patient-local days | 7,343 |
| Completed candidate device-days | 2,440 |
| Completed feature-days | 410 |
| No-raw-ACC days | 2,030 |
| Failed device-day extractions | 0 |
| Pending device-days | 4,934 |
| Patient-level rows currently written | 59 |
| Current patient reported by checkpoint | 029 |

The process was launched with:

```bash
.venv/bin/python3 -u extract_accelerometer_patient_sequential.py
```

It resumed from the cumulative checkpoint rather than reprocessing patients `003` and `004`. It processes patients in patient-ID order, beginning with the remaining patient `002`, and then continues through the remaining mapped cohort. The process does not launch downstream modeling automatically.

Do not delete, reset, overwrite, or manually edit the checkpoint or cumulative ACC tables while the extraction is running. Chatting with the assistant does not interrupt it; only stopping the active process, closing/losing the execution session, or a fatal environment/database failure can stop it.

### 2.2 ACC checkpoint files

- [`accelerometer_patient_sequential_checkpoint.json`](output/analysis_candidates/accelerometer_patient_sequential_pipeline/accelerometer_patient_sequential_checkpoint.json) — resumable progress state.
- [`accelerometer_patient_sequential_progress.csv`](output/analysis_candidates/accelerometer_patient_sequential_pipeline/accelerometer_patient_sequential_patient_progress.csv) — one row per mapped patient with candidate, completed, no-raw, failed, and pending counts.
- [`accelerometer_patient_sequential_run_summary.csv`](output/analysis_candidates/accelerometer_patient_sequential_pipeline/accelerometer_patient_sequential_run_summary.csv) — aggregate run counters and 24-feature count.
- [`full_cohort_extraction.log`](output/analysis_candidates/accelerometer_patient_sequential_pipeline/full_cohort_extraction.log) — activity log only; not the authoritative completion record.

### 2.3 What happens after ACC extraction

After all patients are complete:

1. Validate final ACC coverage, observed minutes, observed span, duplicate burden, no-raw days, and feature missingness.
2. Review the patient-day and patient-level distributions.
3. Compare median aggregation with mean aggregation as a sensitivity analysis.
4. Compare an ACC-only panel and an existing-digital-phenotype-plus-ACC panel against the mean baseline using identical patients and leakage-safe folds.
5. Keep ACC findings exploratory and separate from the already completed low-frequency phenotype results until this audit is complete.

## 3. Scientific interpretation and boundaries

The project must preserve these rules:

- Missing data is not zero activity.
- Data availability, coverage, and recording intensity are part of the result.
- SQL queries must be bounded by both `device_id` and timestamp.
- All dates are aligned to local calendar time in `Asia/Jerusalem`; database timestamps are Unix milliseconds.
- Multiple device IDs can belong to one patient because of app reinstalls or device changes.
- Device IDs are not automatically physical phones or patients.
- High-frequency raw motion streams are separate modalities and must not be silently mixed with low-frequency event features.
- Cognitive outcomes must not be used to create an unsupervised representation when the analysis is described as unsupervised.
- Features selected after inspecting the same outcome are exploratory and not independent validation.
- Follow-up-informed cognitive targets cannot support prospective baseline prediction claims.
- ACC features are phone-signal proxies. They do not identify walking, tremor, gait, stillness, or a specific clinical activity without validation.
- No analysis in this repository validates a diagnosis or provides a clinically deployable score.

## 4. Data and cohort definition

### Cognitive data

The processed NeuroTrax workbook is converted into a patient-level cognitive master table containing global cognition and domain scores, including memory, executive function, attention, processing speed, verbal, motor, and IQ-related fields where available.

Current documented cognitive inventory:

- 83 cognitive records.
- 83 unique `Subject_ID_N` values.
- 62 patients with a valid global T1-to-T2 delta in the earlier candidate table.
- Special NeuroTrax codes such as FP and DI are retained for review rather than automatically discarded.
- The active mapped ACC cohort excludes subject `001` under the existing project rule.

Key files:

- [`output/cognitive_master/master_cognitive_wide.csv`](output/cognitive_master/master_cognitive_wide.csv)
- [`output/cognitive_master/README_cognitive_master.md`](output/cognitive_master/README_cognitive_master.md)
- [`output/cognitive_master/cognitive_data_dictionary.csv`](output/cognitive_master/cognitive_data_dictionary.csv)
- [`output/cognitive_master/qc_missingness_report.csv`](output/cognitive_master/qc_missingness_report.csv)
- [`output/cognitive_master/qc_special_code_summary.csv`](output/cognitive_master/qc_special_code_summary.csv)
- [`output/cognitive_master/delta_consistency_report.csv`](output/cognitive_master/delta_consistency_report.csv)

### Device mapping and plugin movement dictionary

The existing device mapping is in [`output/label_device_map.csv`](output/label_device_map.csv). The plugin movement dictionary was built before the broad ACC extraction and supplies mapped patient, device, local-date, timestamp, activity label, confidence, and canonical movement-context information.

Important plugin outputs:

- [`README_plugin_activity_movement_dictionary.md`](output/analysis_candidates/plugin_activity_movement_dictionary/README_plugin_activity_movement_dictionary.md)
- `plugin_activity_movement_events.csv`
- `plugin_activity_movement_minutes.csv`
- `plugin_activity_device_day_summary.csv`
- `plugin_activity_patient_day_summary.csv`
- `plugin_activity_patient_summary.csv`
- `plugin_activity_extraction_status.csv`
- `plugin_activity_dictionary_cohort_summary.csv`

The dictionary contains 2,013,532 events from 123 valid patient-device intervals. A separate T1-only extension covers 20 patients without T2; it must not be pooled directly into T1-to-T2 decline analyses because its endpoint is data availability, not a clinical follow-up assessment.

## 5. Project history and analysis phases

The phase names are historical implementation labels. For a paper, use descriptive reader-facing terms and explain the actual windows and data transformations.

### Phase 1 — raw discovery and initial phenotype

Purpose: inspect SensorDB tables and JSON structures, review privacy-sensitive fields, identify candidate features, and create an initial digital phenotype for the original proof-of-concept cohort.

Main scripts:

- `discover_sensordb_inventory_and_json_keys.py`
- `inspect_phase1_json_value_distributions.py`
- `review_phase1_json_keys_and_feature_plan.py`
- `extract_phase1a_screen_app_log_features.py`
- `extract_phase1b_interaction_activity_features.py`
- `merge_phase1a_phase1b_features.py`
- `describe_phase1_digital_phenotype_profiles.py`
- `create_phase1_digital_phenotype_profiles_v2.py`
- `create_phase1_boss_review_pack.py`

Main outputs:

- `output/analysis_candidates/phase1_features/`
- `output/analysis_candidates/phase1_features/extracted/`
- `output/analysis_candidates/phase1_features/descriptive_profiles/`
- `output/analysis_candidates/phase1_features/phenotype_profiles/`
- `output/analysis_candidates/phase1_features/reviewer_pack/`

### Phase 2 — table review, privacy review, feature selection, and extraction framework

Purpose: inspect table meaning and JSON fields, separate usable aggregate features from privacy-sensitive raw values, test availability, and create bounded extraction workflows.

Main scripts:

- `phase2_sql_feature_fieldwork_inventory.py`
- `sample_10_rows_per_sensordb_table.py`
- `write_first_row_per_sensordb_table_unredacted.py`
- `build_phase2_highest_t1_calculated_feature_values.py`
- `phase2_extract_selected_features_all_t1_patients.py`
- `phase2_build_reviewed_table_global_coverage_summary.py`
- `phase2_build_reviewed_table_mapped_patient_coverage.py`
- `build_device_ranges.py`
- `build_top10_device_episode_map.py`

Table-specific interpretation files are under `phase2_table_feature_reviews/` and `output/analysis_candidates/phase2_feature_review/`.

Selected feature families include messages, calls, keyboard timing, applications/foreground activity, screen and touch behavior, GSM/telephony context, locations/significant activity, battery/charging, and Bluetooth context where available. Raw message content, phone numbers, contact identifiers, device identifiers, SIM identifiers, and similar sensitive fields are not phenotype features.

### Phase 3 — selected-feature extraction and sensor pilots

Purpose: scale bounded extraction to the active patient cohort and test high-frequency or sparse modalities separately.

Main scripts:

- `phase3_extract_accelerometer_24h_pilot.py`
- `phase3_extract_accelerometer_24h_all_t1_streaming.py`
- `phase3_extract_significant_adjusted_first_available_7d_all_t1_patients.py`
- `phase3_extract_barometer_adjusted_first_available_7d_all_t1_patients.py`
- `phase3_rd_bluetooth_t1_week_any_data_pilot.py`
- `phase3_rd_bluetooth_t1_30day_any_data_pilot.py`
- `phase3_rd_calls_t1_week_any_data_pilot.py`
- `phase3_rd_calls_t1_2week_any_data_pilot.py`
- `phase3_rd_calls_t1_30day_any_data_pilot.py`

Outputs are primarily under `output/analysis_candidates/phase2_feature_extraction/` and `output/analysis_candidates/phase3_rd/`.

### Phase 4 — 24-hour T1 baseline digital phenotype

Protocol: [`PHASE4_T1_BASELINE_DIGITAL_PHENOTYPE_PROTOCOL.md`](PHASE4_T1_BASELINE_DIGITAL_PHENOTYPE_PROTOCOL.md).

The exploratory feature-finding rule uses a first valid 24-hour window within the T1-week search period. The resulting patient-level dataset keeps selected features, table coverage, feature missingness, and status information separate.

Key script and outputs:

- `build_phase4_t1_baseline_dataset.py`
- `output/analysis_candidates/phase11_t1_baseline/`
- `output/analysis_candidates/phase11_t1_baseline/model_t1_ridge/`
- `output/analysis_candidates/phase11_t1_baseline/clinical_tables_baseline_severity/`

The Phase 4 workflow uses fold-fitted median imputation, missingness indicators where specified, standardization, and Ridge as the principal regularized model. A common mean-baseline comparator is required for interpretation.

### Phase 4 10-day baseline sensitivity

Protocol: [`PHASE4_10_DAY_BASELINE_PROTOCOL.md`](PHASE4_10_DAY_BASELINE_PROTOCOL.md).

This is a broader 10-day T1 baseline sensitivity cohort. The documented all-feature direction-constrained experiment used 81 patients and produced pooled RMSE `8.8995`, compared with `8.5320` for the mean baseline. It did not improve prediction in the current cohort.

Key script and outputs:

- `build_phase4_t1_baseline_dataset.py`
- `phase4_10day_all_direction_constrained.py`
- `output/analysis_candidates/phase4_10day_t1_baseline/`

### Phase 5/6 — T2 extraction and longitudinal decline

Protocols:

- [`PHASE5_T2_FEATURE_EXTRACTION_PROTOCOL.md`](PHASE5_T2_FEATURE_EXTRACTION_PROTOCOL.md)
- [`PHASE6_T1_T2_DECLINE_DIGITAL_PHENOTYPING_PROTOCOL.md`](PHASE6_T1_T2_DECLINE_DIGITAL_PHENOTYPING_PROTOCOL.md)
- [`PHASE6_10_DAY_DECLINE_PROTOCOL.md`](PHASE6_10_DAY_DECLINE_PROTOCOL.md)

These analyses calculate independent T1 and T2 digital feature values and define digital change as T2 minus T1. The 10-day longitudinal outputs are under `output/analysis_candidates/phase6_10day_t1_t2_decline/`. The earlier T2 and decline outputs are under `output/analysis_candidates/phase5_t2_feature_extraction/`, `output/analysis_candidates/phase12_t1_t2_decline/`, and `output/analysis_candidates/phase12_midpoint_t2_decline/`.

The current longitudinal models generally do not beat the mean change or mean T2 baselines. For example, the documented Phase 12 pooled results show independent digital-decline RMSE above the mean-change baseline for Global, Attention, and Motor. These are exploratory, small-cohort results.

### Phase 7 — availability-anchored 10-day windows

Protocol: [`PHASE7_10_DAY_WINDOW_PROTOCOL.md`](PHASE7_10_DAY_WINDOW_PROTOCOL.md).

This phase repeats selected-feature extraction with:

- T1: first available timestamp after T1, followed by a 10-day window.
- T2: latest available timestamp before T2, preceded by a 10-day window.
- The unreliable `light` table excluded.
- Existing table-specific fetchers and feature calculators reused.

Outputs:

- `output/analysis_candidates/phase7_10day_window/t1/`
- `output/analysis_candidates/phase7_10day_window/t2/`
- `output/analysis_candidates/phase7_10day_window/comparison/`

The completed comparison reports mean feature missingness of 24-hour versus 10-day windows as 38.5% versus 33.5% for T1, and 76.2% versus 76.0% for T2. A wider window can improve feature calculation without increasing the number of patients with any data in a table; table coverage and feature coverage must remain separate.

Phase 7 is a sensitivity analysis and does not supersede the ACC patient-sequential pipeline.

### Phase 11 — midpoint-anchored baseline

Protocol: [`PHASE11_MIDPOINT_T1_BASELINE_PROTOCOL.md`](PHASE11_MIDPOINT_T1_BASELINE_PROTOCOL.md).

For patients with valid T1 and T2 dates, the baseline interval is `[T1, midpoint)`. Patients without valid T2 use the documented fallback of T1 plus 123 days. The active catalog excludes deferred light, barometer, Bluetooth-proximity, and sensor-linear-accelerometer features from the main Phase 11 model set.

Key script and outputs:

- `phase11_12_extract_midpoint_interval.py`
- `phase11_run.py`
- `phase11_model_ridge.py`
- `output/analysis_candidates/phase11_midpoint_t1_baseline/`
- `output/analysis_candidates/phase11_t1_baseline/`

### Phase 111 — full-interval sensitivity

Protocol: [`PHASE111_ALL_INTERVAL_RIDGE_PROTOCOL.md`](PHASE111_ALL_INTERVAL_RIDGE_PROTOCOL.md).

This sensitivity analysis uses all available data between T1 and T2 and is not the primary prospective baseline definition. Outputs are under `output/analysis_candidates/phase111_full_t1_t2_interval/`.

## 6. Main supervised-model findings so far

Models tested include:

- Mean baseline.
- Ridge regression.
- Domain-specific Ridge.
- Direction-constrained Ridge.
- Gradient-weighted Ridge.
- Slope-selected features.
- Alternative exploratory models.
- T1-to-T2 change models.
- Full-interval Ridge sensitivity.

The mean baseline is often competitive or better. The small and heterogeneous cohort does not currently support a reliable patient-level cognitive prediction model. A numerical improvement in a particular exploratory split is not sufficient evidence of clinical usefulness.

Representative documented result: the Phase 4 10-day all-feature direction-constrained model had pooled RMSE `8.8995`, worse than the mean baseline RMSE `8.5320`.

Key output locations:

- `output/analysis_candidates/phase11_t1_baseline/model_t1_ridge/`
- `output/analysis_candidates/phase11_t1_baseline/model_t1_cognitive_domains/`
- `output/analysis_candidates/phase4_10day_t1_baseline/model_t1_ridge/`
- `output/analysis_candidates/phase4_10day_t1_baseline/model_t1_all_direction_constrained/`
- `output/analysis_candidates/phase12_t1_t2_decline/`
- `output/analysis_candidates/phase111_full_t1_t2_interval/`
- `output/analysis_candidates/phase_exploratory_empirical_findings/`

## 7. Unsupervised phenotyping findings

Protocols:

- [`UNSUPERVISED_PHENOTYPING_PROTOCOL.md`](UNSUPERVISED_PHENOTYPING_PROTOCOL.md)
- [`UNSUPERVISED_POSTHOC_PROTOCOL.md`](UNSUPERVISED_POSTHOC_PROTOCOL.md)
- [`UNSUPERVISED_COVERAGE_ADJUSTED_POSTHOC_PROTOCOL.md`](UNSUPERVISED_COVERAGE_ADJUSTED_POSTHOC_PROTOCOL.md)
- [`UNSUPERVISED_TOP5_RIDGE_PROTOCOL.md`](UNSUPERVISED_TOP5_RIDGE_PROTOCOL.md)
- [`DOMAIN_SPECIFIC_RIDGE_USML_PROTOCOL.md`](DOMAIN_SPECIFIC_RIDGE_USML_PROTOCOL.md)
- [`DOMAIN_SPECIFIC_ADJUSTED_INFERENCE_PROTOCOL.md`](DOMAIN_SPECIFIC_ADJUSTED_INFERENCE_PROTOCOL.md)

The fixed baseline representation used 76 patients and 41 features. The reference two-cluster solution had Cluster 0 with 11 patients and Cluster 1 with 65, PC1 plus PC2 explaining approximately 59.1% of variation, silhouette approximately 0.458, and 80%-subsample ARI approximately 0.997.

The dominant structure was interaction intensity: messaging, keyboard, screen, touch, and GSM activity. It was also associated with total source-row volume, table coverage, missingness, and number of calculated tables. Therefore it cannot yet be called a disease subtype or clinical class.

Coverage-adjusted post-hoc results materially changed the structure:

- Exposure-normalized features: PC1 plus PC2 approximately 83.1%, silhouette 0.728, ARI versus raw clusters 0.616.
- Technical residualization: silhouette 0.201, ARI 0.010.
- Quality-trimmed reference: 57 patients, silhouette 0.196, ARI 0.061.

The adjusted results show that collection intensity and coverage are entangled with the raw-count structure. Earlier nominal Motor and Attention findings did not persist in the stricter adjusted analysis: Motor permutation `p=0.535`; Attention permutation `p=0.762`; bootstrap intervals were wide and included zero.

Main outputs:

- `unsupervised_phenotyping.py`
- `unsupervised_phenotyping_coverage_adjusted.py`
- `unsupervised_phenotyping_posthoc.py`
- `output/analysis_candidates/unsupervised_phenotyping_median_span/`

## 8. Accelerometer workstream

### 8.1 Why general ACC is separate

The raw `accelerometer` table includes gravity and other phone-orientation effects. Its derived measures are exploratory phone-signal proxies, not validated physical-activity measures. The `linear_accelerometer` stream is a separate modality and must not be treated as interchangeable with general ACC.

### 8.2 Hardware and data-coverage audits

Scripts:

- `build_accelerometer_device_hardware_timeline.py`
- `build_accelerometer_patient_device_crosswalk.py`
- `build_accelerometer_patient_data_coverage_report.py`
- `build_sensor_linear_accelerometer_qc_framework.py`

Key documented audit results:

- 564 device IDs in the combined hardware timeline.
- 559 devices with `sensor_accelerometer` metadata.
- 386 with `sensor_linear_accelerometer` metadata.
- 178 with raw linear-accelerometer observations in the local Parquet file.
- 65 sensor configurations: 52 general ACC and 13 linear ACC configurations.
- The active crosswalk contains 159 mapped device IDs across 81 active patients.
- 416 observed device IDs lack a current numeric patient mapping; 153 have raw linear-accelerometer rows and are high-priority linkage candidates.

Outputs are under `output/analysis_candidates/phase2_accelerometer_framework/device_hardware_timeline/`, including:

- `accelerometer_device_hardware_timeline.csv`
- `sensor_configuration_summary.csv`
- `device_hardware_monthly_prevalence.csv`
- `patient_device_crosswalk.csv`
- `patient_device_summary.csv`
- `patient_device_configuration_crosswalk.csv`
- `unmatched_device_ids.csv`
- `data_coverage/patient_accelerometer_data_summary.csv`
- `data_coverage/patient_device_accelerometer_evidence.csv`
- `data_coverage/unmatched_device_data_investigation.csv`

### 8.3 Raw linear ACC archive and Parquet

The source archive is preserved on the external drive:

`/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_linear_accelerometer/sql_zst/linear_accelerometer.sql.zst`

The validated local/use copy is:

`/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_linear_accelerometer/parquet/linear_accelerometer.parquet`

Documented size and content:

- Raw compressed archive: approximately 21.25 GB.
- Parquet: 561,602,194 rows and 4 columns, approximately 21.04 GB.
- The archive passed `zstd -t` and remains unchanged.

Do not delete the `.zst` source when inspecting or processing the Parquet file.

### 8.4 Patient-sequential general ACC pipeline

Authoritative protocol: [`ACC_PATIENT_SEQUENTIAL_PIPELINE_PROTOCOL.md`](ACC_PATIENT_SEQUENTIAL_PIPELINE_PROTOCOL.md).

Main script:

- `extract_accelerometer_patient_sequential.py`

Main cumulative outputs:

- `accelerometer_patient_sequential_candidates.csv`
- `accelerometer_patient_sequential_status.csv`
- `accelerometer_patient_sequential_device_day_features.csv`
- `accelerometer_patient_sequential_patient_day_features.csv`
- `accelerometer_patient_sequential_patient_level_features.csv`
- `accelerometer_patient_sequential_patient_progress.csv`
- `accelerometer_patient_sequential_run_summary.csv`
- `accelerometer_patient_sequential_checkpoint.json`
- `accelerometer_plugin_event_day_feature_catalog.csv`

Acquisition and feature rules:

1. Select mapped patient/device/local-date candidates from the plugin movement dictionary.
2. Query each complete local calendar day from local midnight through the next midnight.
3. Restrict each query to the matched device IDs for that patient-day.
4. Group by `device_id + timestamp` and retain the smallest database `_id`.
5. Retain the duplicate count as QC and discard later same-timestamp rows.
6. Parse valid timestamps and numeric x/y/z values.
7. Keep unobserved time missing; never turn it into zero movement.

The 24-feature catalog includes raw/valid row counts, duplicate removal, valid minutes, calendar coverage, observed span, sampling intervals and gaps, vector-magnitude summaries, dynamic motion proxies, low/high-motion fractions, motion bouts, quiet intervals, day/night measures, hourly entropy, and magnitude-change-rate summaries.

The primary patient-level aggregation is the median across completed patient-local days. Mean values are retained for sensitivity analysis.

Compressed per-day timestamp-deduplicated archives are preserved externally at:

`/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_accelerometer/plugin_event_day_sql_zst/`

## 9. Streamlit and review tools

Main dashboard:

- `streamlit_app.py`
- Launch: `.venv/bin/streamlit run streamlit_app.py --server.port 8510`
- Current local URL used: `http://localhost:8510`

The dashboard is read-only with respect to analysis outputs and does not execute SQL. It exposes the major phase pages, model results, coverage audits, plugin movement dictionary, raw ACC reconnaissance, ACC feature pilots, and the **ACC Patient-Sequential Pipeline** live counters/protocol.

Other review tools:

- `result_explorer.py` — interactive feature/model/result exploration.
- `http_review_server.py` — local review server utilities.
- `README_STREAMLIT_APP.md` — dashboard usage notes.
- `README_HTTP_REVIEW_SERVER.md` — HTTP review-server notes.

## 10. Manuscript workspace and article proposal

The manuscript workspace is under `manuscript/`.

Key files:

- [`manuscript/README.md`](manuscript/README.md)
- [`manuscript/study_protocol.md`](manuscript/study_protocol.md)
- [`manuscript/manuscript_outline.md`](manuscript/manuscript_outline.md)
- [`manuscript/draft_v01.md`](manuscript/draft_v01.md)
- [`manuscript/analysis_decisions.md`](manuscript/analysis_decisions.md)
- [`manuscript/evidence_register.csv`](manuscript/evidence_register.csv)
- [`manuscript/section_status.csv`](manuscript/section_status.csv)
- [`manuscript/references.md`](manuscript/references.md)
- `manuscript/figures/`
- `manuscript/tables/`

### Suggested article

**Working title:** *Building and Auditing a Coverage-Aware Patient-Level Digital Phenotype of Cognition from Passive Smartphone Sensing: An Exploratory Proof-of-Concept Study*

**Article type:** methods/feasibility and exploratory observational study.

**Core research question:** Can heterogeneous passive smartphone records be transformed into interpretable, patient-level digital measurements linked to standardized cognition, and what data-quality conditions are required before prediction can be evaluated credibly?

**Recommended structure:**

1. Introduction: passive sensing, cognitive assessment, and the need for auditable patient-level measurement.
2. Methods: cohort, T1/T2 assessments, device mapping, local-time windows, feature taxonomy, privacy filtering, coverage definitions, missingness handling, and leakage-safe validation.
3. Results: cohort and device availability; feature coverage and missingness; baseline digital structure; model performance against the mean baseline; longitudinal sensitivity; ACC acquisition and signal-quality audit.
4. Discussion: reproducibility and feasibility value, interaction-intensity structure, collection-intensity confounding, weak predictive performance, and what a better-powered validation study requires.
5. Limitations: small heterogeneous cohort, incomplete T2, device changes, missingness, retrospective exploratory choices, outcome-informed analyses, raw-motion proxy interpretation, and lack of independent validation.
6. Conclusion: the project establishes an auditable pipeline and quantifies its current limits; it does not establish a clinical phenotype or validated prediction score.

**Recommended primary message:** The contribution is the auditable measurement and quality-control framework, not a positive clinical prediction claim. The strongest result is that coverage and recording intensity materially influence apparent digital structure and must be reported alongside behavioral features.

**Recommended main-paper analyses:** freeze one primary baseline cohort and one primary cognitive outcome with supervisor approval; report the mean baseline comparator; include feature/table coverage and missingness; include one transparent model result; keep unsupervised and ACC analyses as clearly labeled exploratory or supplementary analyses unless their protocols and cohorts are frozen before submission.

## 11. Reproducibility and transfer to another computer

### Required environment

- Python virtual environment: `.venv/`
- Dependencies: [`requirements.txt`](requirements.txt)
- Project root: this repository.
- External drive mount: `/Volumes/SENSORDATA_MAIN/sensordata_backup`
- Database credentials/configuration: local environment only; never copy secrets into Git or this README.

### Safe startup checklist

1. Clone or copy the repository.
2. Install the documented Python dependencies into the project virtual environment.
3. Mount the external drive using the same path or update scripts/configuration consistently.
4. Confirm that required Parquet files and preserved `.sql.zst` archives exist.
5. Confirm database connectivity before any new extraction.
6. Inspect the relevant protocol before running a script.
7. For resumable jobs, inspect the checkpoint first and never replace cumulative outputs with an older backup.
8. Start Streamlit for read-only review.

### ACC resume checklist

```bash
test -d /Volumes/SENSORDATA_MAIN/sensordata_backup
test -f extract_accelerometer_patient_sequential.py
.venv/bin/python3 -u extract_accelerometer_patient_sequential.py
```

One-patient validation:

```bash
.venv/bin/python3 -u extract_accelerometer_patient_sequential.py --patient-id 005
```

Use `--force --patient-id NNN` only for deliberate reprocessing. Use `--through-date YYYY-MM-DD` only for bounded validation; it leaves later dates pending.

## 12. What is usable later

The following artifacts are suitable as inputs to later analysis after their denominators and definitions are reviewed:

- `master_cognitive_wide.csv` and its QC reports.
- Device/patient crosswalk outputs, with unmatched devices retained explicitly.
- Plugin event, minute, device-day, and patient-day summaries.
- Existing low-frequency patient-level feature matrices and metadata.
- Feature-level and table-level coverage/missingness summaries.
- Mean-baseline and Ridge model predictions/metrics.
- Unsupervised raw-count and coverage-adjusted outputs as exploratory sensitivity results.
- Preserved raw-motion archives and validated Parquet copies.
- ACC device-day, patient-day, patient-level, progress, status, and QC outputs after the current extraction is complete.
- Streamlit as a read-only review and handoff interface.

The following are not yet suitable for definitive clinical claims:

- Any current prediction score.
- Any outcome-informed feature ranking as independent validation.
- Any unsupervised cluster as a disease subtype.
- ACC thresholds as validated activity labels.
- Absence of a raw ACC row as proof of no movement.
- T1-only plugin extension data as a T1-to-T2 longitudinal cohort.

## 13. Immediate next actions

1. Let the patient-sequential ACC extraction finish without interruption.
2. Record the final checkpoint and archive the completed external-drive SQL chunks.
3. Run the final ACC QC and patient-level audit.
4. Decide whether ACC is a supplementary article analysis or a later paper, based on coverage and signal quality.
5. Freeze the primary manuscript cohort, outcome, feature library, and model protocol with supervisor input.
6. Update `manuscript/evidence_register.csv` before promoting any new result into the manuscript.
7. Produce publication-ready aggregate tables and figures only after denominators and missingness rules are frozen.

## 14. Source-of-truth hierarchy

When documents disagree because they were written at different times, use this order:

1. The live checkpoint and cumulative output files for the current running pipeline.
2. The latest dedicated protocol for that pipeline, especially [`ACC_PATIENT_SEQUENTIAL_PIPELINE_PROTOCOL.md`](ACC_PATIENT_SEQUENTIAL_PIPELINE_PROTOCOL.md).
3. The dated project status summaries, including [`README_PROJECT_STATUS_2026-08-29.md`](README_PROJECT_STATUS_2026-08-29.md).
4. Individual output READMEs and historical phase protocols.
5. Git history for provenance; do not use old commits to overwrite newer cumulative outputs.

The 2026-08-29 status README is valuable historical context, but its ACC section describes an earlier all-mapped event-day checkpoint. The September 2026 patient-sequential protocol and live checkpoint describe the current ACC operation.
