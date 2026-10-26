# NeuroTrax–Passive Smartphone Sensing Project

> **Review update, 2026-10-20:** [Complete historical review](#complete-historical-research-review--2026-10-20), including corrected interpretation of historical pooled metrics and all research branches. Earlier status paragraphs are retained as historical context.

**Project handoff and current status**
**Last updated:** 2026-10-15 (Asia/Jerusalem)
**Repository:** `research_dbeaver`

This repository contains an exploratory observational study that links repeated NeuroTrax cognitive assessments with passive smartphone, interaction, activity, and sensor data. The project is a measurement, quality-control, and feasibility study. It is not a diagnostic system and no current model is clinically validated.

## Current status

The main analysis pipeline, patient-level digital phenotype, longitudinal analyses, unsupervised sensitivity analyses, ACC extraction, full raw-motion archive, and Streamlit review dashboard are implemented. The latest major analysis is the domain-specific Full Model PCA.

| Workstream | Status | Source of truth |
|---|---|---|
| Cognitive master table and QC | Complete | `output/cognitive_master/` |
| Digital feature discovery and extraction | Complete exploratory pipeline | `output/analysis_candidates/phase1_features/` and phase-specific folders |
| Baseline and longitudinal digital models | Complete exploratory analyses | `output/analysis_candidates/phase11_t1_baseline/`, `phase12_t1_t2_decline/`, `phase111_full_t1_t2_interval/` |
| Unsupervised phenotyping | Complete exploratory and coverage-adjusted sensitivity analyses | `output/analysis_candidates/unsupervised_phenotyping_median_span/` |
| Patient-sequential general ACC extraction | Complete; audit recorded | `output/analysis_candidates/accelerometer_patient_sequential_pipeline/` |
| Full raw ACC/rotation/gyroscope/gravity archive | Complete as compressed SQL chunks | external drive `full_raw_motion/` |
| Full Model PCA | Complete; latest run includes domain panels | `output/analysis_candidates/full_model_pca/current.json` |
| Streamlit review dashboard | Running on demand | `streamlit_app.py` |
| Keyboard feature expansion | Next research session | existing keyboard outputs and protocols |
| Keyboard Deep Dive v1 extraction and QC | Extraction complete; model integration deferred | `output/analysis_candidates/keyboard_deep_dive_v1/` |
| Parquet conversion of the full raw-motion archive | Planned later | not yet started for the four-table archive |

## Scientific interpretation

The strongest result is methodological: passive smartphone data can be transformed into patient-level summaries, but apparent behavioral structure is strongly affected by data availability, recording intensity, device changes, missingness, and window definition. Current results do not support a reliable clinical cognitive score, disease subtype, or decline predictor.

All analyses must preserve these rules:

- Missing data is not zero activity.
- Coverage, observation time, missingness, and source-row volume are reported separately from behavioral features.
- Queries are bounded by both device and timestamp.
- Database timestamps are converted to local calendar time in `Asia/Jerusalem`.
- Device IDs are not automatically patients or physical phones; reinstall and device changes are possible.
- High-frequency raw motion streams remain separate from low-frequency event features.
- Outcome-informed feature selection and displayed cognitive overlays are exploratory, not independent validation.
- ACC measures are phone-signal proxies, not validated measures of walking, tremor, gait, or activity.

## Cognitive data and cohort

The processed cognitive master table contains global cognition and domain scores, including Memory, Executive function, Attention, Processing speed, Verbal, Motor, and IQ-related fields where available.

Key files:

- `output/cognitive_master/master_cognitive_wide.csv`
- `output/cognitive_master/cognitive_data_dictionary.csv`
- `output/cognitive_master/qc_missingness_report.csv`
- `output/cognitive_master/qc_special_code_summary.csv`
- `output/cognitive_master/delta_consistency_report.csv`
- `output/label_device_map.csv`

The source inventory contains 83 cognitive records and 83 unique subject identifiers. Earlier longitudinal candidate tables contain 62 patients with a valid global T1-to-T2 delta. Special NeuroTrax codes such as `FP` and `DI` remain available for review rather than being silently converted to numeric values.

## Digital phenotype and modeling history

The project developed from raw SensorDB discovery into bounded feature extraction, coverage auditing, and patient-level modeling.

### Phase 1: discovery and initial phenotype

Raw tables and JSON fields were inventoried, privacy-sensitive fields were reviewed, and the first patient-level digital phenotype was created. Outputs are under `output/analysis_candidates/phase1_features/`.

### Phase 2–3: feature review, extraction, and sensor pilots

Table meanings, feature availability, privacy boundaries, device mappings, and bounded SQL extraction were reviewed. Feature families include keyboard timing, screen and touch behavior, applications, calls, messages, telephony/GSM, locations, battery, Bluetooth, activity, and sensor modalities. Raw message content, phone numbers, contact identifiers, SIM identifiers, and similar sensitive values are not phenotype features.

The principal outputs are under `output/analysis_candidates/phase2_feature_review/`, `phase2_feature_extraction/`, `phase2_accelerometer_framework/`, and `phase3_rd/`.

### Baseline and longitudinal models

The repository contains 24-hour, 10-day, midpoint-anchored, availability-anchored, and full-interval sensitivity analyses. Models include mean baselines, Ridge, domain-specific Ridge, direction-constrained Ridge, gradient-weighted Ridge, slope-selected features, T1-to-T2 change models, and full-interval models.

The mean baseline is often competitive or better. A representative documented result is the Phase 4 10-day direction-constrained model: pooled RMSE `8.8995` versus `8.5320` for the mean baseline. These results are exploratory and should not be presented as validated prediction.

Important protocols and outputs:

- `PHASE4_T1_BASELINE_DIGITAL_PHENOTYPE_PROTOCOL.md`
- `PHASE5_T2_FEATURE_EXTRACTION_PROTOCOL.md`
- `PHASE6_T1_T2_DECLINE_DIGITAL_PHENOTYPING_PROTOCOL.md`
- `PHASE7_10_DAY_WINDOW_PROTOCOL.md`
- `PHASE11_MIDPOINT_T1_BASELINE_PROTOCOL.md`
- `PHASE111_ALL_INTERVAL_RIDGE_PROTOCOL.md`
- `output/analysis_candidates/phase11_t1_baseline/`
- `output/analysis_candidates/phase12_t1_t2_decline/`
- `output/analysis_candidates/phase111_full_t1_t2_interval/`

## Unsupervised phenotyping

The original fixed baseline representation used 76 patients and 41 features. Its reference two-cluster solution had Cluster 0 with 11 patients and Cluster 1 with 65, PC1+PC2 explaining approximately 59.1%, silhouette approximately 0.458, and 80%-subsample ARI approximately 0.997.

The dominant structure was interaction intensity: messaging, keyboard, screen, touch, and GSM activity. It was also associated with source-row volume, table coverage, missingness, and the number of calculated tables. Coverage-adjusted analyses materially changed the structure, showing that collection intensity is entangled with the raw-count clusters. Earlier nominal Motor and Attention findings did not persist in stricter adjusted analyses.

Protocols and scripts:

- `UNSUPERVISED_PHENOTYPING_PROTOCOL.md`
- `UNSUPERVISED_POSTHOC_PROTOCOL.md`
- `UNSUPERVISED_COVERAGE_ADJUSTED_POSTHOC_PROTOCOL.md`
- `unsupervised_phenotyping.py`
- `unsupervised_phenotyping_posthoc.py`
- `unsupervised_phenotyping_coverage_adjusted.py`
- `output/analysis_candidates/unsupervised_phenotyping_median_span/`

## Accelerometer and raw-motion workstream

General accelerometer data is treated as a separate exploratory modality. It includes phone orientation and gravity effects. The separate `linear_accelerometer` stream must not be treated as interchangeable with general ACC.

### Patient-sequential ACC extraction

Protocol: `ACC_PATIENT_SEQUENTIAL_PIPELINE_PROTOCOL.md`
Main script: `extract_accelerometer_patient_sequential.py`

The final checkpoint completed 7,374 candidate device-days, including 773 device-days with usable features and 769 patient-local days with features. There were 6,601 no-raw-ACC device-days, zero failed extractions, and no pending device-days. The completion audit passed 76 consistency checks.

The audit identified four multi-device patient-days whose current aggregation does not reconstruct a pooled signal. Patient-day and patient-level ACC results therefore remain usable for descriptive review, but multi-device aggregation must be corrected or sensitivity-tested before definitive modeling.

Main outputs:

- `output/analysis_candidates/accelerometer_patient_sequential_pipeline/accelerometer_patient_sequential_checkpoint.json`
- `accelerometer_patient_sequential_device_day_features.csv`
- `accelerometer_patient_sequential_patient_day_features.csv`
- `accelerometer_patient_sequential_patient_level_features.csv`
- `accelerometer_patient_sequential_patient_progress.csv`
- `accelerometer_patient_sequential_run_summary.csv`
- `output/analysis_candidates/accelerometer_patient_sequential_pipeline/completion_audit/README_ACC_COMPLETION_AUDIT.md`

### Full raw-motion archive

The independent backup job completed on 2026-09-30. It archived the four full raw tables as compressed `.sql.zst` chunks on the external drive:

| Table | Chunks |
|---|---:|
| `accelerometer` | 859 |
| `rotation` | 794 |
| `gyroscope` | 859 |
| `gravity` | 784 |
| **Total** | **3,296** |

The archive occupied approximately 413 GB at the last verification. The backup supervisor completed with retries and resumable chunk receipts. The external-drive path is:

`/Volumes/SENSORDATA_MAIN/sensordata_backup/full_raw_motion/`

The drive must be mounted before inspecting this path. The full archive has not yet been converted to Parquet; that is a later storage step.

The separate linear-accelerometer archive and Parquet copy already exist when the drive is mounted:

- `/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_linear_accelerometer/sql_zst/linear_accelerometer.sql.zst`
- `/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_linear_accelerometer/parquet/linear_accelerometer.parquet`

## Keyboard Deep Dive v1

Protocol: `KEYBOARD_DEEP_DIVE_PROTOCOL.md`
Extractor: `keyboard_deep_dive.py`
Dashboard page: **Keyboard Deep Dive**
Output: `output/analysis_candidates/keyboard_deep_dive_v1/`

The first extraction phase is complete. It audited the live keyboard schema, built a privacy-safe in-memory event representation, calculated daily keyboard summaries, and aggregated them into the saved Phase 11 T1 and Phase 12 T2 windows. It produced 141 window rows and 2,657 daily rows. Keyboard data was present in 66 T1 windows and 43 T2 windows; missing windows remain missing rather than being treated as zero typing.

The live schema contains `_id`, `timestamp`, `device_id`, and JSON `data` with `before_text`, `current_text`, `package_name`, `is_password`, `device_id`, and `timestamp`. It does not contain press/release timestamps, so exact hold and flight time remain unavailable. The new features are text-state timing proxies and additive outputs; no existing feature matrix or model was changed.

The next gate is feature QC: inspect duplicate burden, active-day and interval denominators, distributions, circadian coverage, correction-transition validity, and T1/T2 availability before any Feature Bank or model integration.

Keyboard-only supervised and unsupervised analyses are now implemented in `keyboard_deep_dive_models.py` and stored under `output/analysis_candidates/keyboard_deep_dive_v1/models/`. They cover six T1 outcomes, six T2-minus-T1 outcomes, mean/Ridge/Elastic Net/random-forest models, and keyboard-only PCA/K-means. The current unsupervised quality-controlled representation uses 32 features in 66 patients; its selected k=2 solution has cluster sizes 6/60, silhouette 0.457, and PC1+PC2 explaining 65.31%. Supervised results remain exploratory: the keyboard-only models do not currently outperform the mean baseline consistently, and no result has been added to the main Feature Bank.

The follow-up candidate-generation screen is implemented in `keyboard_signal_discovery.py` and stored under `output/analysis_candidates/keyboard_deep_dive_v1/signal_discovery/`. It tests 34 keyboard features against six T1 outcomes and six T2-minus-T1 outcomes using Spearman associations, 500 bootstrap replicates, FDR adjustment, covariate-adjusted rank correlations, and repeated cross-validated feature-family comparisons. Six exploratory candidates passed the prespecified review rule, all in T2-minus-T1 Executive Function or Attention analyses; they are candidates for validation, not confirmed biomarkers. The Streamlit **Signal discovery** tab exposes the rankings and plots.

Phase 2 validation is implemented in `keyboard_signal_validation.py` and stored under `output/analysis_candidates/keyboard_deep_dive_v1/signal_validation/`. It covers snapshot-based test-retest reliability, coverage and recording adjustments, baseline-score adjustment, device-set comparison, leave-one-patient-out sensitivity, IQR outlier checks, permutation tests, and correlations among the six selected feature changes. No predictive models were trained and no existing outputs were overwritten. The Streamlit **Signal Validation** tab exposes the results.

The T2 reliability investigation is implemented in `keyboard_t2_reliability_investigation.py` and stored under `output/analysis_candidates/keyboard_deep_dive_v1/t2_reliability_investigation/`. It compares T1/T2 active days, snapshots, valid intervals, recording intensity, observed-span gaps, and missingness; applies predeclared coverage thresholds; and recalculates the six associations in threshold-defined and comparable first/last observed-day cohorts. The calendar midpoint split was not estimable for most windows because keyboard observations were concentrated on one side of the clinical interval. The Streamlit **Reliability Investigation** tab exposes the tables and figures. No predictive models were trained.

The first/last-third sensitivity analysis is implemented in `keyboard_thirds_sensitivity.py` and stored separately under `output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity/`. For each valid T1–T2 interval it queries the original timestamped keyboard rows in the first and last equal calendar thirds, excludes the middle third, recalculates the same 34 features, and defines change as Last Third minus First Third. It reports coverage, prespecified active-day eligibility thresholds, Spearman associations with Global and domain T2−T1 change, bootstrap confidence intervals, FDR q-values, parsimonious coverage-adjusted associations, and same-patient comparisons with the 50/50 midpoint design. This is an exploratory window sensitivity analysis; it does not modify the Feature Bank or train models. The Streamlit **Thirds Sensitivity** tab exposes the outputs and plots.

A technical audit of keyboard denominators is implemented in `keyboard_count_audit.py` and stored under `output/analysis_candidates/keyboard_deep_dive_v1/count_audit/`. It found zero patient/window cases in which valid intervals exceeded canonical snapshots. The apparent contradiction in earlier coverage summaries came from comparing independently calculated medians across different nonmissing rows, rather than paired patient/window counts. The audit also found that the original first/last-third coverage table labeled raw database rows as snapshots; the corrected script now uses canonical distinct observations and retains raw rows separately. The shared extractor enforces the interval≤snapshot invariant, with regression tests in `test_keyboard_deep_dive.py`. Existing keyboard feature values, signal results, reliability results, and models were preserved; the third-run coverage-adjusted results require reanalysis before being used with snapshot denominators, and no reanalysis was run for this audit.

## Full Model PCA

Protocol: `FULL_MODEL_PCA_PROTOCOL.md`
Run script: `full_model_pca.py`
Dashboard page: **Full Model PCA**
Current run pointer: `output/analysis_candidates/full_model_pca/current.json`

The analysis combines the original 41 digital features with 15 non-quality ACC movement features. Patient `002` is excluded at the user’s request after the original fit produced a singleton cluster driven by only 29 ACC minutes. The original run remains preserved for comparison.

The current run is `20260920T100206991834Z`: 41 eligible patients in the all-feature reference, 56 varying candidate features, 50.26% PC1+PC2 explained variance, 9 paired global decliners, and frozen T1 preprocessing/PCA parameters for T2 and new-subject projection.

The domain-specific extension repeats the earlier 100-fold Ridge ranking separately for each cognitive domain. Each domain has its own top-five feature panel, preprocessing, PCA, clustering, frozen projection, T2 view, decline view, and cognitive-score overlay.

| Domain | T1 patients | Selected features | PC1+PC2 | Cluster sizes | Paired global decliners |
|---|---:|---:|---:|---|---:|
| Global | 39 | 5 | 63.13% | 6 / 12 / 21 | 7 |
| Memory | 41 | 5 | 95.99% | 25 / 16 | 9 |
| Executive function | 39 | 5 | 70.53% | 29 / 10 | 8 |
| Processing speed | 36 | 5 | 68.49% | 11 / 25 | 8 |
| Attention | 41 | 5 | 57.96% | 30 / 11 | 9 |
| Motor | 40 | 5 | 78.52% | 4 / 36 | 9 |

Motor’s four-patient cluster fails the existing minimum-size criterion and is displayed as a reference solution. No additional patient was removed.

The dashboard displays 3D PC1/PC2/observed-score maps, overall and cluster geometric trend lines, Pearson and Spearman associations, in-sample score-on-PC1/PC2 R², T2 projections, decline-only views, feature rankings, audits, and new-subject projection. The lines show the dominant standardized 3D direction of the point cloud; they are descriptive geometry, not a regression line or clinical prediction model.

The full-model implementation and tests are in:

- `full_model_pca.py`
- `full_model_pca_domains.py`
- `pca_cognitive_trends.py`
- `full_model_pca_dashboard.py`
- `full_model_pca_config.json`
- `test_full_model_pca.py`
- `output/analysis_candidates/full_model_pca/runs/20260920T100206991834Z/`

## Streamlit dashboard

Start the dashboard from the repository root:

```bash
.venv/bin/streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8510
```

Open locally at `http://localhost:8510`. From a phone, use the Mac’s current Wi-Fi address rather than a permanently stored IP. The last verified address was:

`http://192.168.1.2:8510/?page=Full%20Model%20PCA`

The address can change after reconnecting to Wi-Fi. The dashboard is read-only with respect to analysis outputs and does not execute SQL. It includes the phase pages, coverage audits, raw-motion backup status, knowledge graph, model results, and Full Model PCA.

Related documentation:

- `README_STREAMLIT_APP.md`
- `RAW_MOTION_BACKUP_SERVICE.md`
- `project_knowledge_graph.py`

## Manuscript workspace

The manuscript workspace is under `manuscript/`.

Key files:

- `manuscript/README.md`
- `manuscript/study_protocol.md`
- `manuscript/manuscript_outline.md`
- `manuscript/draft_v01.md`
- `manuscript/analysis_decisions.md`
- `manuscript/evidence_register.csv`
- `manuscript/section_status.csv`
- `manuscript/references.md`
- `manuscript/figures/`
- `manuscript/tables/`

The recommended article is a methods/feasibility and exploratory observational paper. Its primary contribution should be the auditable patient-level measurement and quality-control framework, with coverage and recording intensity reported alongside behavioral features. Current prediction, cluster, and ACC results should remain clearly exploratory.

## Reproducibility and safe startup

Required local resources:

- Python environment: `.venv/`
- Dependencies: `requirements.txt`
- External drive mount: `/Volumes/SENSORDATA_MAIN/sensordata_backup`
- Database credentials: local environment only; never commit secrets.

Before running a pipeline:

1. Mount the external drive and confirm the expected archive or Parquet path.
2. Check the relevant protocol and current checkpoint.
3. Confirm database connectivity before a new extraction.
4. Do not replace cumulative outputs with an older backup.
5. Keep source archives and checkpoints unchanged.

Useful commands:

```bash
# Run the full-model PCA and update its versioned current pointer
.venv/bin/python3 -u full_model_pca.py

# Run the ACC completion audit
.venv/bin/python3 audit_accelerometer_patient_sequential.py

# Run the Full Model PCA tests
.venv/bin/python3 -m unittest test_full_model_pca -v

# Start the review dashboard
.venv/bin/streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8510
```

## Next research queue

1. Complete Keyboard Deep Dive v1 feature QC and decide which features enter the Feature Bank.
2. Correct or sensitivity-test the four multi-device ACC patient-days.
3. Convert the four-table raw-motion archive to Parquet with manifests and checksums, while preserving the compressed source.
4. Freeze one primary manuscript cohort, outcome, feature library, window, and validation protocol.
5. Update the manuscript evidence register before promoting any new exploratory result.
6. Produce publication tables and figures only after denominators, missingness rules, and exclusions are frozen.

## Source-of-truth hierarchy

When documents disagree, use this order:

1. Live checkpoints, manifests, and cumulative outputs.
2. The latest dedicated protocol for the pipeline.
3. The latest versioned run record under `output/analysis_candidates/`.
4. This project handoff README and the dashboard.
5. Historical README files and Git history for provenance only.

Never use an older README or old commit to overwrite newer cumulative outputs.

### Keyboard Deep Dive final correction and model integration (2026-10-20)

A versioned correction reran only the First/Last Third coverage-adjusted associations using canonical `distinct_observations_in_window`; the historical thirds outputs were preserved. The unchanged eligibility rule produced 19 paired participants. Across the 34-feature × 8-outcome screen, no corrected association passed FDR (minimum q = .836). The inter-event-interval CV / executive-function association remained similar (partial ρ = −.576, p = .031, q = .836, 95% bootstrap CI −.933 to .024), while correction-recovery time / executive function disappeared after correction (ρ = .014, p = .962, q = .974). See `output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity_corrected_v2/`.

The expanded 34-feature keyboard bank was then evaluated in a separate leakage-safe Ridge integration. Existing versus expanded Feature Bank variants used identical cohorts and repeated folds within each T1 or T2-minus-T1 task, with imputation, scaling, feature selection, and alpha tuning fit inside training folds. Coverage covariates were included in both variants. The expanded bank improved only T1 memory among the main domains (RMSE 14.80 vs 16.54) and was worse for T1 Global (11.03 vs 10.47) and longitudinal Global (8.19 vs 6.40); it did not consistently beat the mean baseline and all R² estimates were negative. Outcome-specific cohorts were T1 n=71–81 and longitudinal n=51–61. These predictive results are distinct from exploratory correlations and do not justify promotion to the primary model yet. Outputs are under `output/analysis_candidates/keyboard_deep_dive_v1/general_model_integration_v1/` and are shown in the Keyboard Deep Dive → General Model Integration tab.


## Complete historical research review — 2026-10-20

This dated review uses saved results and code inspection only. No extraction, correlation, bootstrap, permutation, model, or PCA was rerun; historical outputs were not edited. Arithmetic summaries below average already-saved per-repeat metrics. This section supersedes conflicting interpretive statements earlier in this README while retaining their historical record.

**Main assessment:** no validated cognitive biomarker or general predictive improvement is established. The strongest direct saved feature–cognition coefficient is keyboard morning-interval change versus attention change (Spearman ρ=.783686, n=18), in a restricted midpoint comparator. The most promising longitudinal candidate after considering adjustment, sample size and reliability is afternoon snapshot-interval change versus executive-function change; it remains exploratory. Saved aligned per-repeat metrics also reveal modest positive processing-speed and Motor Ridge results that were obscured by erroneous historical pooled summaries.

### Review scope and evidence rules

The review searched repository CSV headers and inspected all 136 files with correlation/prediction statistic fields, relevant analysis scripts, protocols, run records, and historical READMEs. The attached catalog has 1,810 saved direct feature–cognition estimates (including sensitivities/adjustments), 235 per-repeat model summaries, and a document/script index. It is a repository review, not a fresh audit of external databases, archives or every patient-level value. Script presence alone does not establish that every optional mode ran.

- Direct observed-feature correlations are kept separate from PC–score overlays, PCA loadings, cluster differences, technical correlations, fitted coefficients and actual/predicted correlations.
- Rank by absolute coefficient to answer the magnitude question, then assess robustness separately. The main top ten contain distinct feature–outcome pairs; repeated thresholds/windows for the same pair are not counted as new discoveries. A separate top-ten-estimates table includes repeated pairs.
- Unadjusted and partial Spearman coefficients are explicitly distinguished. Historical superseded estimates are retained and labeled, never recommended as current evidence.
- `NR` means not reported for that exact estimate. A CI or q-value from another cohort, adjustment or test is not substituted. FDR families differ and none adjusts for all research decisions across the project.
- Chronology below follows the documented analysis dependencies; it does not invent run dates for phases lacking a dated run record. Global/domain scale errors and change-scale errors are not directly comparable by RMSE.

Review tables within the existing manuscript structure:

- [Full chronological inventory with methods and scripts](manuscript/tables/research_review_chronology_20261020.csv)
- [Top ten distinct feature–outcome pairs, full precision and provenance](manuscript/tables/research_review_top10_correlations_20261020.csv)
- [Ten largest saved estimates, allowing repeated pairs](manuscript/tables/research_review_top10_estimates_including_repeat_pairs_20261020.csv)
- [All 1,810 saved direct estimates](manuscript/tables/research_review_all_saved_direct_correlations_20261020.csv)
- [All saved per-repeat model summaries](manuscript/tables/research_review_saved_repeat_model_summary_20261020.csv)
- [136 statistical source files, roles and SHA-256 hashes](manuscript/tables/research_review_saved_result_inventory_20261020.csv)
- [Repository documentation/script index](manuscript/tables/research_review_document_script_index_20261020.csv)

### Chronological analysis inventory

Each row names the purpose/design, cohort, measured features/outcomes, observed findings, limits and source. Operational cohorts are not statistical sample sizes.

| Phase/workstream | Cohort | Methods, features and outcomes | Saved findings and limits | Source |
|---|---|---|---|---|
| 01. Cognitive master, device mapping and initial SQL discovery | 83 cognitive records; early longitudinal candidate count 62 | NeuroTrax Global, memory, executive function, processing speed, attention, motor, verbal and IQ; special-code and delta QC; device/time inventories | Created cognitive master, mapping and bounded extraction eligibility; mapped/active subsets differ from the source cohort. No cognitive association inferred from availability. | [Original record](output/cognitive_master/README_cognitive_master.md) |
| 02. Early daily movement and frequency/power pilots | 2 rows in daily_movement_summary; 971 in daily_signal_power_from_significant_days; these are not patient counts | Daily squared-magnitude aggregation; first significant-day signal powers, Butterworth/Welch exploratory spectral summaries | Saved engineering outputs exist; no saved cognitive effect, p/q/CI or validated activity label. Script existence does not prove every optional activity_analysis.py mode was executed. | [Original record](output/daily_signal_power_from_significant_days.csv) |
| 03. Phase 1 top-decline proof of concept | 10 selected; baseline usable 8; early/late change 2 | Early/late seven-day availability; screen/app logs, keyboard/touch and activity; descriptive phenotype axes | Rich table 10×79 and six descriptive engagement/nighttime/app/interaction/activity/quality axes. Early–late evidence extremely limited and cohort selected on decline. | [Original record](output/analysis_candidates/phase1_features/phenotype_profiles/README_phase1_digital_phenotype_profiles_v2.md) |
| 04. Phase 2 feature review, SQL fieldwork and high-T1 pilots | Initial review snapshot 29 selected features/27 calculable values; later active extraction 81 | Schema/JSON and privacy review across keyboard, apps, battery, calls, messages, GSM, locations, touch, screen, sensors; highest-T1 36h and bounded sample pilots | Engineering feasibility, not a prediction study. The initial feature counts are historical snapshots, not the final bank. Raw identifiers/content not model variables. | [Original record](output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/README_phase2_all_t1_selected_features.md) |
| 05. Phase 2/3 24h and adjusted seven-day extraction | 81 active T1 patients; coverage varies by feature | Day after T1, then first valid 24h in T1 week; first-available seven-day barometer/significant-motion/linear-sensor sensitivities | 71 selected columns feed Phase 4; 37 primary, 15 adjusted, 17 low-coverage, 2 entirely missing in documented Phase 4 construction. Availability anchors differ across modalities. | [Original record](output/analysis_candidates/phase4_t1_baseline/README_phase4_t1_baseline_dataset.md) |
| 06. Phase 3 calls and Bluetooth extended-window R&D | 82 status rows per pilot | Calls whole 7/14/30-day post-T1 windows; Bluetooth 7/30 days; any-data coverage sensitivities | Calculated calls: 6/82, 11/82, 12/82; Bluetooth: 1/82 in both windows. Longer windows did not solve absent streams. No predictive inference. | [Original record](output/analysis_candidates/phase3_rd) |
| 07. ACC metadata, hardware, raw 24h and minute probes | Metadata: general ACC 77/81, linear sensor 31/81; local raw pilot one window | Hardware timelines, raw/metadata alignment, 24h chunked signal QC, PSD/band feasibility and thresholds; calendar-minute SQL probes | Local pilot 1,072,778 raw rows; 288 five-minute chunks (287 signal-valid). Phone-state labels and frequency bands are provisional; metadata availability is not raw-signal availability. | [Original record](output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_state_summary.csv) |
| 08. Phase 4 24h Global prediction and score calibration | 81; primary 37 plus sensitivity scopes | Repeated 5-fold ×20 Ridge/mean; gradient weighting, slope-selected and direction-constrained Ridge; elastic net, PLS/spline alternatives; calibration | Global performance generally near/worse than mean. Historical pooled tables have outcome/prediction-order defects; review uses saved per-repeat rows. Calibration correlations are prediction diagnostics, not feature associations. | [Original record](output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/phase4_t1_ridge_metrics.csv) |
| 09. Phase 4 24h cognitive domains and domain feature groups | 71–81 outcome-specific; Motor n=79 | Separate domain Ridge using primary features; expert domain-group panels | Motor per-repeat Ridge RMSE 10.186 vs mean 10.678; mean R² .0559. Small exploratory advantage, no external validation; other domains often negative. | [Original record](output/analysis_candidates/phase4_t1_baseline/model_t1_cognitive_domains/phase4_t1_cognitive_domain_metrics.csv) |
| 10. Phase 4 clustering, profiles and coverage audits | 81×37; high-coverage subset 53 | Median imputation, standardized PCA, K-means k=2–5, 20 seeds; profiles, high-coverage and strict-feature sensitivities | 24h k=2 silhouette .497 and seed ARI 1.00; high-coverage k=3 silhouette .404. Seed stability does not establish clinical groups; coverage-sensitive. | [Original record](output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/README_phase4_clustering_audit.md) |
| 11. Phase 5 pre-T2 extraction | 61 represented; 17 tables; 71 selected features | First valid pre-T2 24h in prior week, latest fallback to 30 days; adjusted seven-day sensor windows | Sparse follow-up coverage documented separately; absence remains missing. No model in extraction step. | [Original record](output/analysis_candidates/phase5_t2_feature_extraction/README_phase5_t2_selected_features.md) |
| 12. Phase 6 independent T1/T2 scores and derived change | Up to 61 paired; domain-specific missingness | Independent endpoint Ridge/mean, then estimated T2−T1; 5-fold ×5 for T2 | Global T2 RMSE 8.534 working Ridge vs 8.164 mean; derived Global change 6.198 vs descriptive mean-change 5.738. Not a baseline-only prospective forecast; mean-change benchmark uses whole paired outcome mean. | [Original record](output/analysis_candidates/phase6_t1_t2_decline/README_phase6_t1_t2_decline.md) |
| 13. Phase 7 10-day window extraction and coverage comparison | T1 81; T2 61 | Availability-anchored ten-day windows vs 24h; same-feature coverage audit | T1 missingness 38.5%→33.5% (50 common features); T2 76.2%→76.0% (61 common). More rows do not imply more covered patients. | [Original record](output/analysis_candidates/phase7_10day_window/comparison/README_phase7_comparison_24h_vs_10d.md) |
| 14. 10-day Phase 4 models, domains, constraints and clustering | 81 source; 67 metadata features; 71–81 outcomes | Same baseline model families, all-direction constraint and k=2–5 clustering | Processing-speed Ridge per-repeat RMSE 12.950 vs 13.718 mean; R² .0799, n=71. Cluster silhouette .528 (k=2). Pooled metrics require correction before use. | [Original record](output/analysis_candidates/phase4_10day_t1_baseline/model_t1_cognitive_domains/phase4_t1_cognitive_domain_metrics.csv) |
| 15. 10-day additional models and coverage-ranked suggestions | Full 81; prespecified coverage-ranked 30/20/10 subsets | Elastic net, PLS, spline Ridge, RF, ExtraTrees, hist-gradient and XGBoost; domain suggestions | Best saved per-repeat result: top-10 Global elastic net RMSE 7.978 vs 10.454, R² .266; n=10 descriptive only. Top-20/30 do not reproduce that gain. Pooled .053 R² is affected by ordering defect. | [Original record](output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_coverage_metrics.csv) |
| 16. 10-day Phase 6 independent endpoint/change sensitivity | Up to 61 paired | Reuse independent T2 and derived difference workflow on ten-day data | Global T2 Ridge 8.195 vs mean 8.164; derived change 6.227 vs 5.738 descriptive mean. No clear improvement from longer acquisition. | [Original record](output/analysis_candidates/phase6_10day_t1_t2_decline/README_phase6_10day_t1_t2_decline.md) |
| 17. Phase 11 first-half midpoint phenotype, models and clinical tables | 81; active feature metadata 54; target-specific n | [T1,midpoint), fallback T1+123d; model family reruns, clustering and median-severity comparison | Global primary Ridge saved per-repeat RMSE 8.775 vs 8.647 mean. Two nominal keyboard median-split findings (p=.032/.036) fail FDR. Post-T1 data cannot serve as a genuinely pre-T1 predictor. | [Original record](output/analysis_candidates/phase11_t1_baseline/README_phase11_t1_baseline.md) |
| 18. Phase 12 second-half midpoint endpoint/change analysis | 61 cognitive pairs, variable sensor coverage | [midpoint,T2); independent endpoint estimation; subtraction after modeling | Global T2 working Ridge 8.267 vs 8.164 mean; derived change 6.159 vs 5.738 descriptive mean. Not prospective early-only forecasting. | [Original record](output/analysis_candidates/phase12_t1_t2_decline/README_phase12_t1_t2_decline.md) |
| 19. Phase 111 full-interval representation and mean cognition | 81 source; domain-specific n | [T1,T2), otherwise 123d; target average of observed T1/T2 or T1 alone; repeated Ridge | Global RMSE 8.442 vs mean 8.294, R² −.062. Different target from baseline or cognitive change; not directly comparable RMSE. | [Original record](output/analysis_candidates/phase111_t1_t2_all_interval/model_phase111_ridge/README_phase111_ridge.md) |
| 20. Supplemental proximity/light/ACC QC, bounded v1–v3 and 11b/12b | 81 T1 and 61 change table rows; light n≤31, proximity n≤25 correlations | Bounded modality QC; direct 24h extraction, nine recommended additions; separate midpoint T1 extraction | Largest direct non-keyboard saved coefficient: proximity raw-row count vs Global r=.503, n=25 (technical intensity; no p/q/CI). Night light rho=−.483, n=9. 11b/12b builder itself trains no models; T1 24h additions are not midpoint changes. | [Original record](output/analysis_candidates/supplemental_modalities/phase4_24h_t1/phase4_supplemental_feature_review.csv) |
| 21. Empirical two-keyboard-feature Global model | 81; both observed 62 | Preselected word-completion/IQR directions; equal-weight and positive Ridge, 5-fold ×20 | Positive Ridge RMSE 8.561 vs 8.664 mean; R² −.007. Same-cohort outcome-informed feature/direction selection limits claimed CV validity. | [Original record](output/analysis_candidates/phase_exploratory_empirical_findings/README_exploratory_empirical_findings.md) |
| 22. Empirical extremes (1;4) sensitivity | Lowest 20 + highest 20 Global T1 =40 | Extreme-score comparison with fixed two keyboard features and same models | Word-completion p=.059, IQR p=.064, both q=.967; Ridge RMSE 11.966 vs mean 11.898. Outcome-selected spectrum, no generalization evidence. | [Original record](output/analysis_candidates/phase_exploratory_empirical_findings_1_4/README_exploratory_empirical_findings_1_4.md) |
| 23. Legacy two-feature keyboard correlations, delta and PCA | Trimmed T1 pairs 58–64; delta n=31/33; PCA n=47 | Midpoint word-completion/IQR; min/max trim; Spearman, paired Wilcoxon, standardized two-feature PCA | Word-completion vs Attention rho=−.354 (n=60,p=.00546); Global −.342 (p=.00744). Global-change rho .256/.160 (p=.165/.372); PCA PC1 71.47%, not cognition explained. | [Original record](output/analysis_candidates/keyboard_t1_t2_delta_pca/keyboard_t1_t2_delta_summary.csv) |
| 24. USML median-span phenotyping and fixed post-hoc overlays | 81 source; default n=76, 41 features; alternate primary/expanded panels | Skew log1p, median/IQR scaling, PCA/K-means k2–4; seeds/subsampling; T1/T2/change overlays and follow-up-informed score sensitivity | Default clusters 11/65, PC1+2 59.09%, silhouette .458; interaction volume dominates. Follow-up-informed baseline is outcome-derived; overlays do not validate prediction. | [Original record](output/analysis_candidates/unsupervised_phenotyping_median_span/README_unsupervised_phenotyping.md) |
| 25. USML exposure/technical residualization and quality trimming | Same reference n=76,41 features; trimmed n=57 | Exposure-normalized, technical-residualized and quality-tail-trimmed fixed k2 comparisons | ARI versus original .616 exposure; .00985 residualized; .0610 trimmed. Strong evidence structure depends on measurement; no causal conclusion. | [Original record](output/analysis_candidates/unsupervised_phenotyping_median_span/coverage_adjusted_posthoc/variant_summary.csv) |
| 26. Global top-5 and domain-specific Ridge-selected USML | Outcome/panel-specific; Motor cognitive n=69, Attention n=76 in adjusted follow-up | Repeated Ridge coefficient ranking; top-five PCA/clusters; cognitive overlays; downstream Motor/Attention adjusted inference | Selection uses cognition, so large PC/cluster effects are circular exploratory displays. Selection-aware adjusted permutation p=.535 Motor, .762 Attention (100 permutations); bootstrap intervals broad. | [Original record](output/analysis_candidates/unsupervised_phenotyping_median_span/domain_specific_adjusted_inference/adjusted_inference_summary.csv) |
| 27. Plugin movement dictionary and T1-only extension | 81 active; 159 mapped devices; T1-only20 (19 with events) | Mapped T1–T2 minute/event/day context, confidence≥70 flag; separate data-bounded extension | 2,013,532 paired-interval events; 569,261 extension events. Phone activity context, not validated movement; extension cannot be pooled as T2 change. | [Original record](output/analysis_candidates/plugin_activity_movement_dictionary/README_plugin_activity_movement_dictionary.md) |
| 28. Plugin-anchored ACC pilots and feature audits | Initial 2 patients/6 feature-days; attempted all-mapped branch 59 selected, 7 feature device-days | 24 signal/QC features; median aggregation; technical-correlation audit; initial streaming/archive extraction | Pilots are incomplete historical snapshots; 12 behavioral/3 sensitivity/9 quality candidates. Technical correlations and median/mean agreement are not cognition correlations. | [Original record](output/analysis_candidates/accelerometer_feature_audit/README_accelerometer_feature_audit.md) |
| 29. Completed patient-sequential ACC and completion audit (Sep 11–14) | 59 processed;51 with signal;773 device-days/769 patient-days | 24 features, duplicate/sample/gap QC, median/mean patient aggregation, technical relationships | All 7,374 candidate device-days handled;6,601 no raw signal;77.40% timestamp duplicates. Four multi-device days need special handling; candidate days conditional on plugin observations. | [Original record](output/analysis_candidates/accelerometer_patient_sequential_pipeline/completion_audit/README_ACC_COMPLETION_AUDIT.md) |
| 30. Full Model PCA combined digital/ACC (three Sep 20 runs) | Latest n=41,56 features (41 digital+15 ACC);9 paired decliners | Original, post-hoc subject002 exclusion, domain extension; identical-patient digital/ACC/mean/device panels; frozen projection | Combined PC1+2 50.26%, clusters6/35; ACC-only clusters4/37 reference-only. Decline-only n=9; no validated predictive ACC gain. Source run history retained. | [Original record](output/analysis_candidates/full_model_pca/runs/20260920T100206991834Z/panel_comparison.csv) |
| 31. Full Model PCA domain panels and 3D trend lines | Baseline n=36–41;decline n=7–9 | Five outcome-ranked features per domain; separate PCA/projections; geometric 3D lines and in-sample score-plane fits | PC–cognitive rho reaches .857 in n=7–8 decline-selected samples; not a direct feature correlation or held-out prediction. Subject exclusion and selection are outcome/post-hoc informed. | [Original record](output/analysis_candidates/full_model_pca/runs/20260920T100206991834Z/domains) |
| 32. Keyboard Deep Dive extraction and dictionary | 141 endpoint windows (81 T1/60 T2);2,657 daily rows;34 features | Canonical text-state snapshots; 30s burst boundary; timing/volume/correction/variability/circadian/day trend and fragmentation | True key hold/flight times unavailable; features are proxies. Window names mean first/second clinical-interval halves, not pre-T1/post-T2. | [Original record](KEYBOARD_DEEP_DIVE_PROTOCOL.md) |
| 33. Keyboard-only supervised, PCA and clustering | 12 target tasks; outcome n=51–81; PCA n=66/32 varying features | Repeated 5-fold×5 mean/Ridge/elastic net/RF; PCA/k2–4 | PCA PC1+2 65.31%; model fit does not establish cognition relationship. Family screen shows small T1 Motor typing-volume gain (10.400 vs 10.526 RMSE) but no general longitudinal gain. | [Original record](output/analysis_candidates/keyboard_deep_dive_v1/models/models_manifest.json) |
| 34. Keyboard Signal Discovery | 408 tests:204 T1 +204 change; six candidates n=28–33 | Spearman,500 bootstrap,age/sex/education partial ranks; BH per scope; candidate q≤.20 | Six longitudinal candidates, five with executive function and one attention; none meets discovery q<.05. Largest discovery raw rho .593 afternoon/EF; recovery −.589 EF. Not independent evidence. | [Original record](output/analysis_candidates/keyboard_deep_dive_v1/signal_discovery/signal_feature_associations.csv) |
| 35. Keyboard Signal Validation | Six selected associations n=28–33; reliability T1 n=15–16/T2 n=18 | Baseline/recording/device adjusted ranks; LOO, outlier check,2,000 permutations; daily first/last14-day ICC | All six LOO signs stable; selected-six permutation q≤.0085. Recording adjustment attenuates; best afternoon/EF partial rho=.508,p=.0222,q=.133. T2 ICC lower; post-selection tests are not independent validation. | [Original record](output/analysis_candidates/keyboard_deep_dive_v1/signal_validation/validation_adjusted_associations.csv) |
| 36. T2 reliability and coverage sensitivity | 60 paired keyboard-window patients;seven-day threshold associations n=20 | Predefined7/14/28 active-day and500/2000 snapshot/interval gates; comparable observed-day periods | Timing changes stronger in ≥7-day subset (evening/EF rho .702,n=20), but limited coverage and poor T2 reliability remain. Old separate medians have different denominators. | [Original record](output/analysis_candidates/keyboard_deep_dive_v1/t2_reliability_investigation/t2_reliability_signal_sensitivity.csv) |
| 37. First/last-third raw re-extraction and midpoint sensitivity | 61 paired source;both thirds≥7d n=19;≥14d n=7;≥28d n=2 | 34 features from first/last calendar thirds;middle excluded;Spearman/bootstrap/FDR and same-patient midpoint comparison | Strongest saved direct association rho .784 morning/attention in midpoint comparator n=18; corresponding thirds rho .573. Strict threshold association tables empty due insufficient n. | [Original record](output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity/third_vs_midpoint_comparison_same_patients.csv) |
| 38. Keyboard count audit and canonical snapshot correction | 141 midpoint/122 thirds windows;109/86 paired-count rows;v2 cohort19 | Shared count invariant;duplicate/multistream tests;separate adjusted-correlation rerun with canonical observation counts | Zero per-window count violations. Misleading independent medians and raw-row labeling identified. Corrected 272 planned/270 estimable tests: no FDR finding,min q=.836; originals preserved. | [Original record](output/analysis_candidates/keyboard_deep_dive_v1/count_audit/count_audit_summary.csv) |
| 39. Expanded keyboard general-model integration (Oct 20) | T1 n=71–81;change n=51–61;61 existing/89 expanded candidate features +4 technical covariates | Raw Phase11/12 wide bank;replace six keyboard features with 34;identical-fold nested Ridge,3×5 outer/3 inner CV;all8 outcomes | Global RMSE worsens10.47→11.03 T1 and6.40→8.19 change;T1 memory improves16.54→14.80 but mean13.80. All fold-mean R² negative. This bank omits newer raw-ACC block and is not the exact historical primary 37 model. | [Original record](output/analysis_candidates/keyboard_deep_dive_v1/general_model_integration_v1/model_summary.csv) |
| 40. Backup/conversion, dashboards, graph and manuscript infrastructure | Operational manifests; no inferential cohort | Resumable motion archive, selected-table Parquet conversion,Streamlit knowledge graph and provenance | Operational achievements are separate from findings. Four-table raw-motion Parquet conversion is not established by model outputs; external archive integrity not rechecked in this review. | [Original record](RAW_MOTION_BACKUP_SERVICE.md) |

### Top ten strongest distinct observed feature–cognition pairs

All ten are longitudinal changes: later minus earlier keyboard measurement versus cognitive T2−T1. Positive cognitive change means higher T2 score. “IEI” below means **text-state inter-event interval**, not true keystroke latency. The maxima were found across all available branches, not only Keyboard Deep Dive; non-keyboard findings appear below for context. This is a retrospective magnitude ranking, not a confirmatory selection rule.

Windows: **M18** = 50/50 midpoint comparator restricted to the same participants eligible for both designs; **M7** = midpoint-change sensitivity with ≥7 active days in both halves; **T3c** = first/last thirds with ≥7 active days each and canonical coverage adjustment; **T3old** = superseded raw-row-adjusted thirds. M18 q-values cover 40 tests per design; M7 q-values cover the six selected signals within that scenario; T3c q-values cover 270 finite adjusted tests among 272 planned pairs. T3old files do not provide matching adjusted CIs or q-values.

| Rank | Feature change → cognitive change | Window / statistic | n | Coefficient | p | q | 95% bootstrap CI | Robustness / limitation | Source |
|---:|---|---|---:|---:|---:|---:|---|---|---|
| 1 | Morning (06–12) median IEI → Attention | M18 / ρ | 18 | +0.783686 | 0.000119137 | 0.00476549 | NR | Small restricted subset; same-patient thirds rho=.573; corrected thirds rho=.577, q=.836; morning T2 ICC=-.016. | [CSV](output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity/third_vs_midpoint_comparison_same_patients.csv) (line 75) |
| 2 | IEI CV → Executive function | M18 / ρ | 18 | -0.721362 | 0.00072796 | 0.00986873 | NR | Restricted subset; recording-adjusted full discovery rho=-.211, q=.311; corrected thirds rho=-.576, q=.836. | [CSV](output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity/third_vs_midpoint_comparison_same_patients.csv) (line 39) |
| 3 | Correction recovery → Attention | M18 / ρ | 18 | -0.720702 | 0.000740155 | 0.00986873 | NR | Restricted subset and not one of original six discovery associations; corrected thirds rho=-.016, q=.974. | [CSV](output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity/third_vs_midpoint_comparison_same_patients.csv) (line 11) |
| 4 | Evening (18–24) median IEI → Executive function | M7 / ρ | 20 | +0.702256 | 0.000556435 | 0.00168057 | [0.352, 0.873] | Minimum-seven-day sensitivity; recording-adjusted discovery rho=.380, q=.179; T2 ICC=.263. | [CSV](output/analysis_candidates/keyboard_deep_dive_v1/t2_reliability_investigation/t2_reliability_signal_sensitivity.csv) (line 11) |
| 5 | Morning median IEI → Executive function | M7 / ρ | 20 | +0.691729 | 0.000728485 | 0.00168057 | [0.332, 0.885] | Minimum-seven-day sensitivity; recording-adjusted discovery rho=.301, q=.196; T2 ICC=-.016. | [CSV](output/analysis_candidates/keyboard_deep_dive_v1/t2_reliability_investigation/t2_reliability_signal_sensitivity.csv) (line 12) |
| 6 | Afternoon (12–18) median IEI → Executive function | M7 / ρ | 20 | +0.685972 | 0.000840285 | 0.00168057 | [0.255, 0.912] | Minimum-seven-day sensitivity; recording-adjusted discovery rho=.508, p=.0222, q=.133; T2 ICC=.416; promising but uncertain. | [CSV](output/analysis_candidates/keyboard_deep_dive_v1/t2_reliability_investigation/t2_reliability_signal_sensitivity.csv) (line 9) |
| 7 | Post-correction pause → Processing speed | T3c / partial ρ | 17 | +0.654604 | 0.0208954 | 0.835982 | [-0.352, 0.971] | Already coverage-adjusted; small n; CI crosses zero and q=.836; no independent validation. | [CSV](output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity_corrected_v2/corrected_coverage_adjusted_associations.csv) (line 117) |
| 8 | IEI CV → Motor | T3c / partial ρ | 18 | -0.640125 | 0.0184427 | 0.835982 | [-0.938, 0.035] | Already coverage-adjusted; small n; CI crosses zero and q=.836; no independent validation. | [CSV](output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity_corrected_v2/corrected_coverage_adjusted_associations.csv) (line 197) |
| 9 | Morning IEI IQR → Verbal | T3old / partial ρ | 19 | +0.623974 | 0.0170868 | NR | NR | Historical denominator superseded: corrected rho=.597410, p=.024070, q=.835982, CI [-.091945,.885516]. | [CSV](output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity/third_associations.csv) (line 233) |
| 10 | Pre-correction pause → Processing speed | T3old / partial ρ | 17 | +0.623956 | 0.030132 | NR | NR | Historical denominator superseded: corrected rho=.499197, p=.098481, q=.886332, CI [-.657527,.945702]. | [CSV](output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity/third_associations.csv) (line 116) |

Rows 9–10 are included solely because the request covers the strongest *ever observed* saved coefficients. Their current corrected estimates are .597410 (Verbal; q=.835982) and .499197 (Processing speed; q=.886332), respectively. Excluding superseded estimates would bring morning IEI IQR/Global (partial ρ=.619870, n=19, p=.018050, q=.835982, CI [−.268041,.909347]) and correction recovery/Executive function (discovery ρ=−.588710, n=32, p=.000394, q=.080284, CI [−.761834,−.312292]) into the distinct-pair top ten. These sensitivity variants are not independent replications.

Other saved direct evidence, important for avoiding keyboard-only selection bias:

- **Proximity raw rows and valid numeric rows / Global T1:** Pearson r=.503091, n=25, no saved p/q/CI; these are recording-volume features. Near-bout/transition counts reach r=.459405/.459235, n=25. [Supplemental review](output/analysis_candidates/supplemental_modalities/phase4_24h_t1/phase4_supplemental_feature_review.csv).
- **Nighttime mean light / Global T1:** Spearman ρ=−.483333, n=9, p/q/CI not saved; too small for a strong substantive claim. Same source.
- **Legacy word-completion proxy / Attention T1:** ρ=−.354479, n=60, p=.005455; /Global T1 ρ=−.342235, n=60, p=.007439. Two preselected features, min/max trimming; no saved multiplicity correction or CI. [Original associations](output/analysis_candidates/keyboard_two_feature_median_timespan/keyboard_two_feature_associations.csv).
- **Full Model PCA:** PC–cognition ρ reaches .857143 in decline-only n=7–8. These are composite-axis overlays in outcome-selected, sometimes outcome-ranked panels; they are not individual feature correlations. [Global decline overlay](output/analysis_candidates/full_model_pca/runs/20260920T100206991834Z/domains/global/decline_change/correlations.csv).
- **ACC extraction audit:** strong median/mean and technical-volume correlations are not ACC–cognition findings. The available combined ACC PCA does not substitute for an independently evaluated ACC predictive gain.

### Most promising scientific candidate

**Afternoon (12:00–18:00) median snapshot-interval change versus executive-function change** is the most defensible candidate for further investigation among the longitudinal discovery signals, rather than the numerically largest n=18 result:

1. Discovery: ρ=.592856, n=28, p=.000885, scope-wide q=.090318, bootstrap CI [.217589,.832254]. [Discovery CSV](output/analysis_candidates/keyboard_deep_dive_v1/signal_discovery/signal_feature_associations.csv).
2. Age/sex/education/baseline/recording/device adjustment: partial ρ=.507994, n=28, p=.022209, q=.133256 across the six selected tests, bootstrap CI [.102805,.785821]. It does **not** pass q<.05. [Adjusted CSV](output/analysis_candidates/keyboard_deep_dive_v1/signal_validation/validation_adjusted_associations.csv).
3. Leave-one-patient-out range [.546481,.652114], all signs positive; outlier-filtered ρ=.474322, n=25. Permutation p=.003498, q=.006997 is conditional on six previously selected associations; it does not repeat the original 408-test discovery procedure. [Robustness CSV](output/analysis_candidates/keyboard_deep_dive_v1/signal_validation/validation_robustness.csv).
4. T1 daily-summary ICC=.885 (n=16); T2 ICC=.416 (n=18), lower but the largest T2 ICC among these five unique selected features. These are observed-day stability estimates in a subset, not reliability of every patient's window-level delta. [Reliability CSV](output/analysis_candidates/keyboard_deep_dive_v1/signal_validation/validation_reliability.csv).
5. Same-patient n=18 midpoint ρ=.647393 versus thirds .634675; corrected coverage-adjusted thirds ρ=.496090, n=19, p=.071200, q=.835982, CI [−.502230,.904992]. Persistence of direction is encouraging; uncertainty and window sensitivity prevent validation. [Corrected thirds](output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity_corrected_v2/corrected_coverage_adjusted_associations.csv).

Classification: **exploratory and uncertain, with plausible recording bias; not a validated biomarker**. The positive sign means a larger snapshot interval accompanies a higher cognitive change score. It cannot be interpreted as “slower typing improves cognition.” Sampling cadence, text edits, app mix and recording gaps can change the interval without a change in true typing speed. At the overall project level, the most robust methodological result is the dependence of apparent phenotype structure on recording coverage/intensity, illustrated by cluster ARI falling to .00985 after technical residualization.

### Predictive performance, kept separate from correlations

**Material audit finding:** `phase4_model_t1_ridge.py:220`, `phase4_model_t1_cognitive_domains.py:121`, `suggestions_10day_coverage_models.py:111` and related baseline-family scripts construct pooled outcomes with `np.tile(y, N_REPEATS)` while predictions are appended in test-fold order. Saved top-10 prediction ID/outcome order differs from the source cohort order. Thus those historical pooled values are not correctly paired and cannot be used to select the best model. The per-repeat rows in the named Ridge/domain/coverage scripts use actual and predicted values appended together; those saved rows can be summarized without refitting or recalculating any prediction metric. No defect was fixed or metric replaced in this review.

The table reports arithmetic means of already-saved per-repeat metrics. RMSE ranges are descriptive across CV repeats, **not confidence intervals**; repeat folds reuse participants. n is people, not pooled prediction rows. Results on different outcomes/cohorts should not be ranked by raw RMSE.

| Candidate | People / repeats | RMSE model / mean baseline | MAE model / baseline | Mean R² model / baseline | Model RMSE repeat range | Assessment |
|---|---|---|---|---|---|---|
| Coverage top-10 Global, 10-day elastic net | 10 / 10 | 7.978 / 10.454 | 6.514 / 7.873 | .2657 / −.2350 | 6.753–10.156 | Highest aligned saved mean R², but n=10 and selected best of many models/cohorts; descriptive only |
| Processing speed T1, 10-day Ridge | 71 / 20 | 12.950 / 13.718 | 10.380 / 11.259 | .0799 / −.0278 | 11.582–15.202 | Strongest positive larger-cohort result by mean R²; modest exploratory candidate |
| Motor T1, 24h Ridge | 79 / 20 | 10.186 / 10.678 | 8.571 / 8.925 | .0559 / −.0371 | 9.759–10.820 | Smaller positive larger-cohort result; requires clean prospective validation |
| Global T1, Phase11 primary Ridge | 81 / 20 | 8.775 / 8.647 | 6.940 / 6.885 | −.0585 / −.0277 | 8.552–9.177 | No average gain over mean |

Sources: [coverage suggestions](output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_coverage_metrics.csv), [10-day domains](output/analysis_candidates/phase4_10day_t1_baseline/model_t1_cognitive_domains/phase4_t1_cognitive_domain_metrics.csv), [24h domains](output/analysis_candidates/phase4_t1_baseline/model_t1_cognitive_domains/phase4_t1_cognitive_domain_metrics.csv), [Phase11 Ridge](output/analysis_candidates/phase11_t1_baseline/model_t1_ridge/phase4_t1_ridge_metrics.csv). Full source-specific summaries: [model review table](manuscript/tables/research_review_saved_repeat_model_summary_20261020.csv).

For the tiny top-10 subset, the reported historical pooled elastic-net RMSE9.1575/R².0534 should not be used; the aligned saved per-repeat summaries above answer the comparison without recalculation. The per-repeat top20 elastic-net RMSE9.184 exceeds mean7.879; top30 8.203 exceeds7.633. The apparent gain does not persist in these broader subsets. Older pipelines fit imputation/scaling on each outer training split before RidgeCV/ElasticNetCV's inner splits, so they protect outer test data but are **not fully nested preprocessing for inner tuning**.

The latest keyboard integration uses a proper GridSearchCV pipeline for inner preprocessing, but it is a different comparison: 61 columns selected from raw Phase11 wide data versus 89 expanded candidates, plus four technical covariates in both. This is not a rerun of the historical active 54-feature catalog or primary 37 panel and does not include the newer raw-ACC feature block. Its saved fold-mean RMSEs are:

| Outcome/task | n | Mean baseline | Existing candidate bank | Expanded keyboard bank |
|---|---:|---:|---:|---:|
| Global T1 |81|8.522|10.470|11.030|
| Memory T1 |81|13.798|16.537|14.803|
| Global change |61|5.725|6.397|8.194|
| Verbal change |58|13.650|16.609|16.417|

[Latest metrics](output/analysis_candidates/keyboard_deep_dive_v1/general_model_integration_v1/model_summary.csv). Expansion improves T1 memory and slightly longitudinal verbal relative to the reconstructed existing bank, but neither beats the mean baseline. Other tasks worsen; all fold-mean R² values are negative. The columns named `rmse_ci_low/high` are 2.5th/97.5th percentiles of 15 fold RMSEs, **not 95% confidence intervals for generalization error**. The saved PNG groups by outcome without task and retains the first value; use the task-labeled CSV to distinguish T1 from change. Exact uncertainty for paired model improvement is not saved.

### Methodological limitations, documentation corrections and unresolved items

1. **Temporal design:** baseline-labeled features often occur after T1. Midpoint intervals are `[T1, midpoint)` and `[midpoint,T2)`, with a 123-day fallback when T2 is absent. Full-interval targets average T1/T2. These answer different questions; a prospective decline model cannot use later-half features as baseline inputs. Clinical intervals and recording spans vary by participant.
2. **Multiple searches and cohort selection:** many windows, outcomes, thresholds, feature panels and exclusions were explored on the same small cohort. Within-table FDR does not correct the entire research history. Discovery candidates used q≤.20; selected-six permutation/adjustment tests are not independent validation. Full-model decline samples are selected on the outcome, and subject002 was excluded after inspecting a singleton cluster.
3. **Measurement and missingness:** text snapshots are not keydown/up events. True hold/flight time is unavailable. No-data is not no activity. Sparse/cadence-dependent timing, multi-device episodes and coverage-dependent attrition can drive associations. Eight covariates with n=28–33 in recording-adjusted keyboard models are not especially parsimonious and can produce unstable estimates.
4. **Reliability:** T2 first/last14 observed-day ICCs range −.016 to .416; periods are not necessarily adjacent calendar weeks. Coverage thresholds leave as few as seven/two people in thirds sensitivities. No covariance/noise correction or independent external reliability study is available in this repository.
5. **Corrected thirds interpretation:** 272 planned comparisons but only270 finite p-values entered BH. The comparison file's historical q and CI fields came from *unadjusted* tests; they must not be compared as if they were old adjusted q/CI. Recovery/EF changed only .047132→.014196 (p .872884→.961585) after denominator correction; it was already near zero in the old adjusted thirds analysis. Earlier wording that correction alone “removed” the discovery association is inaccurate.
6. **Counts and manifests:** source 83, older R&D 82, active 81, cognitive paired 61 and keyboard-window paired 60 are different populations. The keyboard-only models manifest says `paired_patients:81`; it reflects a merged table size, not81 usable change pairs. Use outcome-specific saved counts. Independent coverage medians over different nonmissing sets do not imply valid intervals exceed observations in a patient/window.
7. **Prediction reporting:** affected historical pooled rows need patient-order reconciliation. Outer-CV repeats are not independent new patients; pooled row counts1620/100 are not n=1620/n=100. Averaged fold R² is not pooled out-of-fold R². Older inner tuning preprocesses before inner folds. No independent external test set or valid paired uncertainty for the selected best model is saved.
8. **ACC and sensors:** plugin-selected days, timestamp deduplication, irregular sampling and phone placement constrain interpretation. Four multi-device patient-days have aggregation issues; the Full Model PCA mitigates them with exclusion/best-device sensitivity. ACC technical correlations, PCA loadings and 3D geometry do not demonstrate cognitive prediction. Gyroscope/gravity/rotation archive completion is not a saved clinical feature-analysis result.
9. **Missing/not comparable outputs:** thirds min14/min28 association CSVs are empty (n=7/n=2); direct supplemental midpoint T2 output directory is absent; barometer retry is documented deferred. Early `activity_analysis.py` optional modes lack a complete named run manifest; do not infer execution from the script. Raw external data and archive integrity were not reverified. Subscale-specific inferential results beyond the saved named domains/Verbal/IQ were not found. Historical backup directories and three PCA runs are versions, not independent studies.
10. **Source integrity limits:** the review stores hashes for 136 statistical source files. Legacy outputs usually lack immutable source/commit hashes, so full provenance across overwritten historical input snapshots cannot be guaranteed. This review makes no new clinical/causal claim and does not repair analyses without a separate correction stage.

### Recommended next research direction

First reconcile historical pooled outcome/prediction order **from saved predictions**, as a separately versioned reporting correction, before any manuscript model comparison or new feature search. Freeze a coherent model catalog and outcome/window/cohort definition; the latest 61-column bank, active 54-feature catalog, primary 37 panel and ACC-extended 56-feature PCA are different objects.

Then prioritize a small prespecified hypothesis: afternoon snapshot-interval dynamics and executive-function change, with sufficient comparable recording periods, explicit intensity/coverage modeling, baseline cognition adjustment, and validation in new participants or genuinely held-out data. Keep the n=18 maximum as a sensitivity observation, not a target to optimize. For prediction, the larger-cohort processing-speed Ridge and Motor Ridge results justify confirmation under fully nested preprocessing with matched folds and paired uncertainty; the n=10 elastic-net result does not justify deployment. If future data collection can include consented key press/release events and sampling/device metadata, it would directly address the current measurement ambiguity.

The strongest manuscript now is an auditable feasibility/measurement study with clearly labeled exploratory cognitive signals and negative general-model results. No further extraction, model training or hypothesis testing was performed for this review.

### Model-results audit and research freeze — 2026-10-20

A separate saved-prediction audit now corrects the outcome-order reporting defect described above. It reads only historical prediction rows, verifies every saved actual score against the relevant patient table, and writes new files under [model_results_audit_20261020](output/analysis_candidates/model_results_audit_20261020/README_model_results_audit.md). No original analysis output was changed and no model was trained.

| Candidate | n / repeats | Corrected mean RMSE, model / mean | Corrected mean MAE, model / mean | Corrected mean R², model / mean | Freeze decision |
|---|---:|---:|---:|---:|---|
| Processing speed T1, 10-day Ridge | 71 / 20 | 12.950 / 13.718 | 10.380 / 11.259 | .0799 / −.0278 | Primary historical candidate for external confirmation only. |
| Motor T1, 24-hour Ridge | 79 / 20 | 10.186 / 10.678 | 8.571 / 8.925 | .0559 / −.0371 | Secondary exploratory candidate. |
| Global T1, coverage top-10 elastic net | 10 / 10 | 7.978 / 10.454 | 6.514 / 7.873 | .2657 / −.2350 | Descriptive only; do not promote. |

The historical pooled rows (for example, Processing-speed Ridge RMSE 16.149/R² −.424) remain invalid because they paired tiled source-order outcomes with fold-order predictions. Correctly paired row-level pooled values and repeat/fold summaries are in [historical-versus-corrected metrics](output/analysis_candidates/model_results_audit_20261020/historical_pooled_vs_corrected_metrics.csv), [summary](output/analysis_candidates/model_results_audit_20261020/corrected_model_summary.csv), and [matched baseline comparisons](output/analysis_candidates/model_results_audit_20261020/corrected_model_vs_mean_baseline.csv). Conditional patient-cluster bootstrap RMSE-improvement intervals are 0.75 [−1.13,2.37] for Processing Speed, 0.48 [−0.31,1.20] for Motor, and 2.12 [−1.93,5.57] for top-10 Global; all include zero and do not establish superiority. Details are in [bootstrap comparisons](output/analysis_candidates/model_results_audit_20261020/model_vs_mean_cluster_bootstrap.csv). All three saved prediction sets have one observation per patient per repeat, five folds per repeat, zero duplicate patient/repeat rows, and complete agreement of saved actuals with their source patient tables.

**Research freeze:** the sole candidate for a future confirmatory analysis is T1 Processing Speed using the first-available 10-day post-T1 window and the fixed 37-feature primary panel. This n=71 model has the most credible historical balance of sample size, improvement and feature-set discipline, but it is still exploratory. The post-T1 window makes it a concurrent correlate of T1 score, not a prospective predictor. Confirmation must use a new held-out cohort, pre-specified eligibility/features, fully nested preprocessing and tuning, matched mean-baseline folds, and patient-level paired uncertainty. Candidate-specific coefficients were not saved, so feature contribution cannot be reconstructed from predictions. The historical inner tuning also was not fully nested because imputation/scaling occurred before inner CV splits.

### Potential POC Findings for Manuscript — 2026-10-20

The [Master Association Table](manuscript/tables/master_association_table_20261020.csv) catalogs every saved **direct individual digital-feature–cognition** estimate: 1,871 rows from 10 source outputs. It combines the prior 1,810 correlation estimates with 61 Phase 11 Global-T1 median-group feature contrasts. It retains all non-significant and 270 superseded historical-thirds rows. Its separate [p<.05](manuscript/tables/master_associations_p_lt_0_05_20261020.csv), [q<.05](manuscript/tables/master_associations_fdr_q_lt_0_05_20261020.csv), and [q≤.20](manuscript/tables/master_associations_fdr_q_le_0_20_20261020.csv) extracts are filters of the same table, not new analyses.

- **Counts are estimates, not discoveries:** 154 rows have p<.05; 40 have q<.05 and 62 have q≤.20. These q-values belong to different testing families and cannot be compared as one project-wide FDR. Repeated windows, adjustments, and coverage thresholds are linked through a feature–outcome key and must not be counted as replications.
- **Most defensible manuscript POC:** afternoon (12:00–18:00) snapshot inter-event-interval change versus executive-function change: discovery Spearman ρ=.592856, n=28, p=.000885, q=.090318, bootstrap CI [.217589,.832254]. After age, sex, education, baseline EF, recording intensity, coverage and device adjustment it remains partial ρ=.507994, p=.022209, q=.133256, CI [.102805,.785821]. The canonical first/last-thirds sensitivity is weaker (partial ρ=.496090, n=19, p=.071200, q=.835982, CI [−.502230,.904992]). This is promising but unconfirmed and uses text-state timing proxies, not true keystrokes.
- **Related executive-function candidates are less robust:** correction-recovery change begins at ρ=−.588710, n=32, p=.000394, q=.080284, CI [−.761834,−.312292], but becomes partial ρ=−.303181, p=.149828, q=.196180 after recording adjustment and is null in corrected thirds (ρ=.014196, p=.961585, q=.973978). IEI CV and evening interval change have discovery q≤.20 but similarly attenuate after recording adjustment; retain them only as supplementary hypotheses.
- **Largest numerical result is not the primary POC:** morning interval change versus attention in the restricted same-patient midpoint comparison has ρ=.783686, n=18, p=.000119, q=.004765 within 40 tests. It is a small post-hoc window sensitivity, has poor morning T2 reliability, and its corrected-thirds version has q=.835982. It is not confirmatory evidence.
- **Baseline keyboard signals:** the legacy word-completion proxy versus Attention T1 has ρ=−.354479, n=60, p=.005455, but no matching q/CI; the broader 204-test discovery screen does not retain baseline keyboard associations after FDR. The Phase 11 Global-T1 group table has two raw keyboard p<.05 results—word completion p=.032359 and IEI IQR p=.036239—but both q=.659148 across 61 features.
- **Other modalities:** the Phase 11 group table includes applications, screen, touch, activity/motion, calls, GSM and messages, but no feature survives its 61-feature FDR. The 24-hour supplemental review contributes 44 direct proximity/light/etc. estimates with n=9–25 but no saved p, q or CI; the largest raw values are recording-volume or coverage measures and are not manuscript efficacy candidates. No saved direct individual touch, screen, apps or motion correlation screen comparable to the keyboard 204-test screen was found.

PCA/cluster score overlays, fitted-model coefficients, technical feature–feature correlations and reliability/coverage outputs are deliberately excluded from the master because they are not individual feature–cognition associations; see the [excluded-output inventory](manuscript/tables/master_association_excluded_output_classes_20261020.csv). For the manuscript, report the master table as supplementary evidence, use the afternoon interval/EF finding as a clearly labeled exploratory POC, and foreground the negative coverage-adjusted and multi-modality results. Do not claim a validated biomarker, a modality-wide discovery, or independent replication.

### Afternoon Keyboard Interval — Mechanism Audit (2026-10-20)

The original 28-person afternoon snapshot-interval/Executive-Function discovery association was traced from raw keyboard rows through canonical deduplication, device/package-local pairing, the local 12:00–18:00 bin, and the saved Late−Early feature delta. The [mechanism audit](output/analysis_candidates/keyboard_deep_dive_v1/afternoon_interval_mechanism_audit_20261020/README_afternoon_interval_mechanism_audit.md) recomputed the saved Early and Late medians exactly for all 28 participants without storing raw text, app package names, or device IDs.

The source association is ρ=.592856, n=28, p=.000885. IEI delta covaries with changed device set (ρ=−.592714, p=.000889), interval-count change (ρ=−.514849, p=.005057), event rate per active day (ρ=−.544683, p=.002727), active-day change (ρ=−.489461, p=.008205), and long-pause-rate change (ρ=.497879, p=.007016). These technical variables also correlate with Executive-Function change. The association remains .461 (p=.0205) after coverage/frequency adjustment, falls to .395 (p=.0562) with sampling-structure variables, and falls to .356 (p=.1132) with all seven audited factors. All are exploratory sensitivities without multiplicity correction.

**Interpretation:** increasing snapshot IEI cannot currently be called meaningful typing slowing or a behavioral improvement marker. It is a text-state snapshot proxy, and this audit shows material entanglement with recording cadence, device changes, long pauses, and app composition. Retain it as an exploratory POC only.

### Word Completion Timing & Variability — 2026-10-21

The new [word-completion audit](output/analysis_candidates/keyboard_deep_dive_v1/word_completion_timing_v1/README_word_completion_timing.md) and `keyboard_word_completion_deep_dive.py` evaluate whether timestamped `before_text`/`current_text` snapshots can support a more interpretable completion-time family. The database has no keypress or key-release events, so the resulting measure is explicitly **observable snapshot completion time**, not true word-typing time.

The existing `keyboard_median_word_completion_time_ms` implementation follows the same basic boundary rule: it starts when a non-space state is observed and closes when a later state ends with a literal space. It does not require that the first character or every intermediate character was observed, does not identify punctuation/newline delimiters, and does not distinguish paste, predictive text, autocorrect, or correction transitions. The new extractor retains raw text only in memory, groups sequences within device and application, resets at the established 30-second burst boundary, and exports only aggregate timing and quality classes.

The run covers 81 T1 and 60 T2 windows, 2,657 patient-days, and 1,467,287 distinct snapshots. It identifies 105,402 candidate completions: 64,667 high-confidence observable, 2,255 partial-start, and 38,480 ambiguous edit/gap candidates. High-confidence means a boundary-start, append-only observable sequence without a >2-second interruption; it is a quality label, not confirmation that every keystroke was captured. The output reports mean/median/SD/IQR/MAD/P10/P90/CV, counts, high-confidence fraction, completions per active recording minute, time-of-day summaries, daily/weekly variability and trends, coverage, and T2−T1 deltas. No raw text, words, package names, or device identifiers are saved.

The exploratory cognitive screen has 256 estimable rows. The largest baseline absolute correlation is .362 (evening timing with Attention, n=52, q=.352); the largest longitudinal result is ρ=.409 for Global change versus word-completion IQR change (n=31, p=.0225, bootstrap CI [.051,.673], q=.858). Nothing passes q<.05 or q≤.20. Therefore the family is feasible as a privacy-safe aggregate proxy, but the present evidence does not show that it is more reliable or more interpretable than snapshot IEI. It must remain separate from the Feature Bank and general predictive models until independent coverage-controlled validation is available. This phase did not train models or overwrite historical outputs.

A separate 263-row recording-adjusted screen (active days, snapshot rate, valid intervals) and a matched comparison with the 28-patient afternoon-IEI audit are saved in the same directory. In the matched cohort, word-completion median delta versus Executive-Function delta is ρ=−.145 (n=27, p=.471) and IQR delta is ρ=−.007 (n=27, p=.971), versus the saved snapshot-IEI association ρ=.593 (n=28, p=.000885). This is a descriptive comparison with different missingness and no multiplicity claim; it does not support replacing the snapshot-IEI proxy with word-completion timing.

## Complete Feature Dictionary, Cognitive Findings & POC Validation Roadmap

**Saved-results register, version 20261021_v1.** This section updates the research-status interpretation while preserving every earlier section and all historical outputs. No source-data extraction, correlation calculation, FDR recalculation, bootstrap, model training, or predictive integration was performed. The register includes all 1,871 prior Master Association rows, additional saved statistical outputs, Word Completion Timing v1, and non-estimable recorded comparisons.

Start with the [14-row supervisor findings table](manuscript/tables/supervisor_feature_findings_20261021_v1.csv). The complete deliverables are:

| File | Contents and reading guidance |
|---|---|
| [Detailed feature dictionary](manuscript/tables/complete_feature_dictionary_20261021_v1.csv) | 1,246 source/version definition records covering 496 exact feature or derived-output names. Includes original definitions verbatim, calculation expressions and source lines, units, windows, practical meaning, hypothetical behavioral meaning, and measurement limitations. These counts include QC fields, endpoint transforms, planned/code-only features and repeated historical catalogs; they are not counts of validated biomarkers or eligible model predictors. |
| [Complete feature–cognition associations](manuscript/tables/complete_feature_cognitive_associations_20261021_v1.csv) | 2,560 saved estimate records from 20 source files. Exact source p-values appear first, with q-values, n, effect type, CI bounds, direction, plain-English interpretation, linked definitions, adjustments, reliability, sensitivity and provenance. All 1,871 historical master rows remain individually linked. |
| [All p < 0.05 records](manuscript/tables/complete_feature_cognitive_p_lt_0_05_20261021_v1.csv) | 216 rows, including exploratory, repeated and superseded results. A filter of the complete register, not an independent set of discoveries. |
| [Candidate validation roadmap](manuscript/tables/poc_validation_roadmap_20261021_v1.csv) | 919 feature-version/outcome/timepoint groups, each linked to representative and repeated evidence and a concrete next validation step. Groups are navigation aids, not pooled estimates or independent hypotheses. |
| [Statistical-source inventory](manuscript/tables/feature_findings_source_inventory_20261021_v1.csv) | 119 saved CSVs with statistical fields, with inclusion/exclusion reasons and hashes. PCA/cluster overlays, feature-to-feature correlations, model coefficients and copied summaries are distinguished from direct individual feature–cognition evidence. |
| [Provenance manifest](manuscript/tables/complete_feature_findings_manifest_20261021_v1.json) | Counts and SHA-256 hashes of 185 source/code files. Source-statistic checks and hash comparisons verify that historical inputs were preserved. |

**How to read the dictionary.** A definition record belongs to its source catalog/version and window. The same name in Phase 1, the shared legacy extractor, Deep Dive, supplemental sensors, or a PCA sensitivity is not assumed to have the same denominator or aggregation. `original_definition_verbatim` and `original_catalog_metadata_json` retain the historical wording; code expressions and clarification fields show what could actually be verified. Forty definition records have no resolved code expression and remain explicitly uncertain/catalog-only. Do not infer extraction success from a feature's presence in code or a plan. A feature with no saved cognitive test is marked untested, not negative.

Direct measurements must remain distinct from hypotheses. Higher keyboard IEI is a larger accepted interval between text-state snapshots; higher IEI IQR/MAD/SD is greater dispersion of those intervals. Neither demonstrates slower keystrokes. The legacy word proxy is elapsed time between heuristic start/space states; length-decrease events are deletion-like state changes, not confirmed typing errors. Touch events are accessibility records, screen counts are state-event counts rather than screen time, and app entropy is diversity of logged event categories rather than task efficiency. Activity labels and raw ACC describe the phone and recording context; `sensor_linear_accelerometer_*` capability fields describe hardware, not movement. Light/proximity, cellular, Bluetooth, battery and communications measures have source-specific environmental, device and exposure limitations documented in the dictionary. Possible clinical meanings are hypotheses only.

**Temporal and statistical conventions.** The Deep Dive's T1-labeled keyboard features generally summarize `[T1, midpoint)`, after the T1 assessment. T2-labeled features summarize `[midpoint,T2)`. They are not pre-T1 baseline measurements. Change features are Late−Early; first/last-third sensitivities use their separately labeled windows. NeuroTrax cognitive change is T2−T1: a positive association with a feature change means larger feature change accompanies more positive cognitive change (greater improvement or less decline), not necessarily that everybody improved. Clinical-group comparisons use Cliff's delta and Mann–Whitney p-values; they are not correlations. Legacy fitted slopes are separately labeled and are not cross-validated prediction.

Every statistical value is copied from its saved source as a decimal string. Missing statistics stay blank with a reason; they are not reconstructed. The register contains 140 rows without p-values, 1,113 without matching q-values and 74 non-estimable/missing effect sizes. Historical thirds adjusted estimates do **not** inherit the unadjusted q-values or bootstrap CIs sitting beside them in their source file. Selected-six validation q-values belong to a six-test family, not the original 204-test discovery scope. There are 52 q<0.05 and 74 q≤0.20 estimate rows; all 52 q<0.05 rows come from selected-signal or restricted-cohort follow-ups. These are not 52 independent discoveries, and their q-values do not control project-wide FDR.

### Supervisor interpretation and POC priorities

The table below uses original discovery/screen estimates as representatives, rather than choosing the strongest adjusted or restricted-subset result. Exact p-values are displayed; coefficients and q-values are rounded here only. All saved precision, CIs, missing-statistic flags and repeated versions are in the CSVs.

| Feature / cognitive outcome | Exact p-value | Effect; n; q | Practical relationship and current status |
|---|---|---|---|
| Afternoon snapshot IEI change / Executive Function change | 0.0008854663078159199 | ρ=.593; n=28; q=.0903 | Larger afternoon snapshot-gap change accompanied more positive EF change. Preferred historical exploratory mechanism hypothesis; measurement confounding remains substantial. |
| Correction-recovery proxy change / Executive Function change | 0.0003935497903806719 | ρ=−.589; n=32; q=.0803 | Shorter proxy recovery change accompanied more positive EF change. Attenuates after recording adjustment; corrected thirds are near null. |
| Snapshot IEI CV change / Executive Function change | 0.0022651665195853234 | ρ=−.513; n=33; q=.1540 | Lower relative dispersion change accompanied more positive EF change. Coverage sensitivity and weak T2 reliability limit interpretation. |
| Evening snapshot IEI change / Executive Function change | 0.0035540361732903807 | ρ=.524; n=29; q=.1813 | Larger evening gap change accompanied more positive EF change. Exploratory, recording-dependent and weakly reliable at T2. |
| Morning snapshot IEI change / Executive Function change | 0.005723212336766826 | ρ=.485; n=31; q=.1946 | Positive EF-change association, but morning T2 ICC is −.016 in the saved reliability subset. |
| Afternoon snapshot IEI change / Attention change | 0.0052798532586369904 | ρ=.513; n=28; q=.1946 | Positive Attention-change association; same snapshot and small-cohort limitations. |
| Legacy word-completion proxy / Attention T1 | 0.005454608917258615 | ρ=−.354; n=60; q unavailable | Longer observed heuristic completion time accompanied lower Attention. Nominal exploratory result; extreme feature values were removed in the source. |
| Word Completion v1 evening median / Attention T1 | 0.008434441024630313 | ρ=−.362; n=52; q=.3523 | Longer algorithm-selected evening completion intervals accompanied lower Attention. No FDR support; technical clarification required. |
| Word Completion v1 IQR change / Global change | 0.022513814202466575 | ρ=.409; n=31; q=.8584 | Increasing dispersion of selected completion intervals accompanied more positive Global change. No FDR support; technical clarification required. |

The afternoon/EF discovery CI is [.217589,.832254]. In the saved mechanism audit, adjustment for coverage/frequency gives partial ρ=.460520, **p=0.02052453002823002**; the seven-factor technical adjustment gives ρ=.356059, **p=0.11315185142672757**, n=28, with no saved q or CI. Its first/last-14-observed-day reliability is ICC=.885 at T1 (n=16) versus .416 at T2 (n=18). These are different reliability subsets and are not independent validation. The full register retains the intermediate selected-six recording adjustment and corrected-thirds evidence too; the mechanism audit prevents a claim of robust behavioral slowing or a validated biomarker.

The large restricted morning-IEI/Attention correlation (ρ=.783686, n=18, p=.0001191373351379, q=.0047654934055162) remains in the register as a post-hoc same-patient sensitivity. Its broader discovery result is ρ=.338139, n=31, p=.06280910479020077, q=.6185020334458017. Reporting only the n=18 result would omit important contrary evidence.

Negative findings are retained. None of the 61 Phase 11 digital-feature/Global-T1 median-group contrasts has q<.05 (minimum q=.659148). The supervisor CSV includes touch-app diversity (p=.14671447727181147), screen transitions (p=.28913749130637534), foreground-app diversity (p=.24499716803909544) and activity active hours (p=.4387902481778112) as examples; their effects are Cliff's delta, not rho. The extreme-score 61-feature comparison, omitted from the previous master, is now included. Supplemental correlations without saved p/q/CI remain feasibility observations. Raw ACC dictionary/PCA features do not establish a direct individual feature–cognition association; no comparable saved direct raw-ACC screen was located.

### Word Completion Timing v1: corrections and unresolved technical questions

This read-only code/output review qualifies the earlier completion report; source outputs are preserved as-is:

1. The final saved unadjusted CSV has **270** rows, not 256: 168 T1 tests (four outcomes) and 102 change tests (three outcomes). BH is separate within those scopes. Motor, Processing Speed and the other available domains were not included in that word screen. The separate adjusted file has 263 rows and no saved q-values or CIs.
2. The adjusted word-completion IQR-change/Global-change result is partial ρ=.5249247963140329, n=31, **p=.0041305973834450385** after active-day, snapshot-rate and valid-interval-count adjustment. Its missing q/CI cannot be filled using the unadjusted q=.8583919827510633 or unadjusted CI [.0514696,.6733136]. It remains a technically unresolved exploratory observation. The adjusted evening-median/Attention result is ρ=−.3473354793387599, n=52, p=.014475415446127751, also without q/CI.
3. `current.startswith(before)` checks each row internally; it does not verify continuity between the previous snapshot's `current_text` and the next snapshot's `before_text`. Multi-character increments may pass, so the label `high_confidence_observable` does not establish fully observed character-by-character word formation, or exclude paste/predictive text. The `edits` state can persist through abandoned candidates or burst resets. The completion parser accepts literal ASCII spaces only and permits nonnegative rather than strictly positive completion duration.
4. The 64,667/105,402 accepted-candidate fraction describes the algorithm's classifications. It is not a measured proportion of all actual words correctly reconstructed. No saved missing-snapshot simulation, true word-length adjustment, application-composition adjustment, or word-feature test–retest analysis was found. Daily variability/slope is not reliability evidence. Weekly variability is **SD of completion counts**, grouped by ISO week number without a year key; it is not week-to-week completion-time variability.
5. The source file now contains a password-state exclusion added after the saved extraction in the session history. The saved manifest has no code hash verifying that exclusion for these results. It must not be claimed retrospectively. Current code also folds skipped rows into its generic discarded-row accounting. No raw text appears in the delivered register.
6. The file called `word_completion_vs_snapshot_iei_matched.csv` has n=27 for word features and n=28 for IEI. It shares a source cohort but does not compare identical complete cases. It cannot establish comparative reliability or superiority. Its estimates remain cataloged with this qualification.

### Validation roadmap and manuscript use

The roadmap's group-membership labels can overlap: an original promising candidate can also weaken after adjustment. The six original discovery candidates retain the **promising exploratory** flag; all have limitations, and none is independently validated. Primary categories currently put ten candidate groups under recording/coverage weakening, 56 under nominal or restricted findings, 325 under technical clarification, and 528 under negative/unsupported evidence. This grouping includes alternate feature versions and estimators and is not a discovery count.

1. **Promising exploratory POC candidates:** keep afternoon snapshot-cadence change/EF as a narrowly stated mechanism hypothesis. Freeze the feature/window/cohort definition, establish recording comparability, and validate in new participants with prespecified baseline cognition and technical covariates. Do not optimize coverage thresholds on cognition.
2. **Nominal results without FDR support:** retain the baseline word proxies and similar observations in supplementary tables. Require independent, prespecified replication with multiplicity control; do not treat a selected small-subset q-value as discovery-wide evidence.
3. **Signals weakened by recording/coverage adjustment:** investigate sampling cadence, app/device continuity and comparable exposure before any behavioral or clinical claim. Report the original, adjusted and window-sensitivity estimates together.
4. **Technical clarification:** audit/freeze Word Completion v1 sequence continuity, quality flags, zero-duration handling and saved-code provenance before reanalysis. Validate against labeled, consented sequences or explicit event telemetry; then assess density, length, application composition and test–retest behavior. Clarify units/calibration for catalog-only and supplemental sensor features. No repairs or reanalyses were undertaken for this register.
5. **Negative/unsupported associations:** retain all null and missing tests. Features with no saved direct association are untested, not ineffective. Do not promote touch, screen, app or raw motion features on the basis of PCA loadings, clustering or fitted importance alone.

For the manuscript, use a measurement-feasibility and exploratory-association framing, include negative findings and source-specific testing families, and keep predictive performance in the separate historical model audit. The research freeze and no-integration decision remain in place. The register gives every unique candidate a specific next step; it does not authorize new analysis.

Reproduce the catalog only (saved files and source-code text, no database or model calls):

```bash
.venv/bin/python3 build_complete_feature_findings_register.py
node export_complete_feature_findings_register.mjs
.venv/bin/python3 verify_complete_feature_findings_register.py
```

The exporter uses the installed Artifact Tool runtime and refuses to replace a differing existing register version. Verification checks all 1,871 historical master IDs, all definition links, the p-filter, supervisor statistics, 10,240 exact p/q/CI string comparisons, and all 185 source hashes. Original statistics are never recalculated to repair missing values.

## Research Status — Preliminary Results and Validation Plan

**Candidate evidence completeness audit, version 20261021_v1.** This candidate-specific audit covers K1–K6 (the six original Keyboard Signal Discovery candidates), the legacy word-completion → Attention T1 association (W1), and Word Completion v1 IQR change → Global cognitive change (W2). It reuses saved patient/window outputs and saved inferential tables. New calculations are limited to aggregate Early/Late/change distributions and an exploratory OLS effect per observed feature IQR with a 2,000-resample patient bootstrap; no broad feature search, model training, or historical-output overwrite was performed.

The [versioned evidence table](output/analysis_candidates/keyboard_deep_dive_v1/candidate_evidence_completeness_20261021/candidate_evidence_completeness_table_20261021_v1.csv) reports exact discovery and saved validation statistics, complete-case counts, coverage summaries, adjusted/sensitivity results, missing statistics, and the smallest prespecified validation set. The [descriptive distribution table](output/analysis_candidates/keyboard_deep_dive_v1/candidate_evidence_completeness_20261021/candidate_evidence_descriptive_distributions_20261021_v1.csv) contains Early/T1, Late/T2, change, cognitive, active-day, canonical-snapshot, valid-interval, package-count, and Word v1 quality summaries. The [source index](output/analysis_candidates/keyboard_deep_dive_v1/candidate_evidence_completeness_20261021/candidate_evidence_source_index_20261021_v1.csv) records testing context and marks repeated same-cohort sensitivity analyses as non-independent. Methods and interpretation are in the [versioned audit README](output/analysis_candidates/keyboard_deep_dive_v1/candidate_evidence_completeness_20261021/README_candidate_evidence_completeness.md).

The strongest saved evidence remains exploratory. K1 afternoon IEI → Executive Function change is ρ=.593, n=28, p=.000885, q=.0903, but the saved full technical adjustment attenuates it to ρ=.356, p=.113. K2 correction-recovery → Executive Function change is ρ=−.589, n=32, p=.000394, q=.0803 and is stable to the saved LOO/outlier/permutation checks, yet attenuates after full recording adjustment. K3–K5 retain nominal or age/sex/education-adjusted associations but remain coverage-sensitive; K6 is the same afternoon IEI feature/cohort family as K1 and is not independent replication. W1 is a nominal historical association (ρ=−.354, n=60, p=.00545) with no saved q/CI/LOO/recording adjustment. W2 is ρ=.409, n=31, p=.0225, q=.858, CI [.051,.673] unadjusted and ρ=.525, p=.00413 after saved recording adjustment, but the adjusted file lacks q/CI and the algorithm has unresolved continuity/classification limitations.

Before manuscript claims, predeclare comparable coverage and device/app rules, reconstruct candidates from canonical distinct observations, adjust parsimoniously for baseline cognition and recording intensity, and report reliability, LOO, permutation, and bootstrap uncertainty. Word Completion v1 requires continuity tests and quality-class validation first. No candidate is promoted to the general model by this audit.

## Keyboard Research Extension — Word-Length Timing and Lexical Feasibility

Version `20261021_v1` adds two separate feasibility outputs while preserving all prior keyboard features and results: [Word-Length-Adjusted Completion](output/analysis_candidates/keyboard_deep_dive_v1/word_length_adjusted_completion_v1/README_word_length_adjusted_completion_v1.md) and [Lexical Feature Feasibility](output/analysis_candidates/keyboard_deep_dive_v1/lexical_feature_feasibility_v1/README_lexical_feature_feasibility_v1.md).

The extractor requires exact `previous.current_text == next.before_text` continuity, append-only transitions, a boundary-start, and no interruption longer than two seconds for a reliable candidate. It excludes password-state rows before inspection, works within device/application streams, counts multi-character jumps and corrections, and writes only aggregate numeric outputs. Word length is the normalized observable token length; it is not a keystroke count. TTR, MATTR, MTLD and repetition metrics are observed-text measures, not direct vocabulary knowledge.

The run covered 81 T1 and 60 T2 windows. It reconstructed 30,800 reliable continuous completions at T1 and 4,264 at T2. Weighted reliable fractions were 55.8% and 6.7%, and only 3 paired patients had at least 100 reliable tokens in both windows. The prespecified feasibility gate therefore failed. No new cognitive screen was run, and no predictive model was trained. This is a recording/reconstruction limitation rather than a negative cognitive finding. The large T1/T2 imbalance and high continuity-break and multi-character-jump counts make current lexical and length-adjusted longitudinal comparisons unreliable.

The associated [literature review](output/analysis_candidates/keyboard_deep_dive_v1/lexical_feature_feasibility_v1/literature_review_20261021_v1.csv) separates language-sample evidence from true smartphone keystroke studies. MATTR and MTLD are methodologically relevant, while MCI typing studies and longitudinal keystroke work use richer text or key-event data than this SensorDB schema. The next step is labeled synthetic/state-transition validation and language/application comparability; these features should not enter the general model yet.

## T1-only Lexical and Word-Timing Cognitive Analysis — 2026-10-21

The [T1-only cross-sectional analysis](output/analysis_candidates/keyboard_deep_dive_v1/lexical_t1_cross_sectional_v1/README_lexical_t1_cross_sectional_v1.md) reuses the strict continuity aggregates from the two preceding feasibility runs. It includes all 81 patients with valid Global T1 scores and saved T1 keyboard windows; T2 data are not required. The T1 window starts a median of 0.083 days before the assessment (about two hours), with offsets from −0.125 to −0.083 days.

Fixed thresholds were set before testing: 20 reliable tokens for simple lexical, word-length and timing measures; 50 for MATTR-50; and 100 for MATTR-100/MTLD. The analysis produced 49 estimates across three prespecified testing families. Four were nominally p<.05, but none had family-level q<.05. The leading nominal results were completion MAD versus Attention (ρ=−.319, n=50, p=.0240, q=.336), completion IQR versus Attention (ρ=−.308, n=50, p=.0295, q=.336), length-residual SD versus Executive Function (ρ=−.288, n=50, p=.0422, q=.336), and 4–5-character-group IQR versus Executive Function (ρ=−.284, n=50, p=.0458, q=.336). Coverage adjustment weakened the timing results. An adjusted MATTR-100/Verbal association (ρ=.607, p=.00274, q=.0274, n=22) is based on only 22 high-token patients and remains unstable exploratory evidence.

This is not independent validation of the historical legacy word-completion/Attention finding (n=60, p=.00545): the cohort overlaps, continuity rules are stricter, and feature definitions and missingness differ. No raw text or words were accessed or exported, and no predictive models were changed. Use the versioned [results directory](output/analysis_candidates/keyboard_deep_dive_v1/lexical_t1_cross_sectional_v1/) for the coverage table, full statistics, p<.05 table, feature dictionary, privacy checks and scatter plots.

The [other-domain follow-up](output/analysis_candidates/keyboard_deep_dive_v1/lexical_t1_cross_sectional_v2_other_domains/README_lexical_t1_other_domains_v2.md) tests Memory, Motor and IQ with the same fixed definitions and thresholds. It produced 57 estimates and three nominal p<.05 results: MATTR-100/Motor (ρ=.544, n=21, p=.0108, q=.1615), completion MAD/Motor (ρ=−.297, n=48, p=.0407, q=.576), and 2–3-character completion IQR/IQ (ρ=−.287, n=48, p=.0481, q=.576). None passes family-level FDR. MATTR-100/Motor is based on only 21 high-token patients and remains unstable exploratory evidence. This follow-up is same-cohort evidence, not independent validation.

## MATTR-100 Focused Validation Audit — 2026-10-21

The new [MATTR-100 audit](output/analysis_candidates/keyboard_deep_dive_v1/mattr100_validation_audit_20261021/README_mattr100_validation_audit_20261021.md) preserves all historical estimates and adds a fixed-threshold cohort, coverage, language/application, leave-one-out, and domain-overlap review. The threshold was 100 reliable T1 word tokens: 22 patients met it and 59 did not. The high-coverage subgroup had much more recording (median 386 vs 15 reliable tokens; 32.5 vs 5 active days) and modestly higher median Global/Verbal scores.

The saved unadjusted estimates were Verbal rho=.326,p=.139,n=22 and Motor rho=.544,p=.0108,n=21. Historical coverage-only partial estimates remain Verbal rho=.607,p=.00274,q=.0274 and Motor rho=.562,p=.00797,q=.1195. A new parsimonious demographic-plus-coverage sensitivity attenuated Verbal to rho=.180,p=.422 and left Motor at rho=.539,p=.0117. Leave-one-out direction was positive for every omission; Verbal p ranged .067–.324 and Motor p ranged .0027–.0311. Verbal and Motor were not correlated in the shared cohort (rho=-.060,p=.797). Aggregate other-language token count was associated with MATTR (rho=.466,p=.0286), leaving a language/application concern.

The current interpretation is that MATTR-100 is not a robust Verbal signal after fuller adjustment. Motor is more stable but remains exploratory evidence from a small, selected high-coverage subgroup. No predictive model was trained and no historical output was overwritten.

## Cross-Table Digital Phenotyping — Phase 1 (2026-10-22)

A new feasibility workstream is documented under [cross_modal_feature_discovery_v1](output/analysis_candidates/cross_modal_feature_discovery_v1/README_cross_modal_phase1.md). It verifies the literature on synchronized keyboard–accelerometer sensing, passive cognition monitoring, older-adult multimodal sensing, and smartphone/smartwatch brain-health research, then audits the saved SensorDB schema reviews and bounded T1 coverage outputs.

The local audit confirms usable event-based bounded examples for keyboard, foreground applications, screen, touch and activity-recognition streams. The selected 24-hour patient/device review window contained 1,832 keyboard rows, 698 foreground-app rows, 304 screen rows, 1,820 touch rows and 423 activity-recognition rows. The archived accelerometer pilot showed dense raw sampling (3,202 rows in five minutes, approximately 10.7 Hz), but broad patient-level synchronized motion overlap was not available. Linear accelerometer had zero rows in checked T1-week windows; reviewed gyroscope, gravity and rotation windows also had zero rows.

Because the live SensorDB host was unavailable during this audit, timestamp-level ±5/30/60-second overlap counts were not inferred from calendar-window counts. The short-window table marks those quantities as not computed. The recommended first pilot is screen–touch burst variability or foreground-app switching during screen-unlocked sessions, followed by application-stratified keyboard snapshot variability. Accelerometer-coupled features require a bounded same-device raw query and sampling/duplicate QC before implementation. No cognition screen or predictive model was run.

## Cross-Modal Phase 2 — Timestamp Synchronization Pilot (2026-10-22)

The [Phase 2 README](output/analysis_candidates/cross_modal_feature_discovery_v2/README_cross_modal_phase2.md) records a controlled stop before feature extraction. Saved keyboard, screen, touch, foreground-app and activity-recognition files were small review samples, not complete patient episodes. A bounded SensorDB connection was attempted but failed with MySQL error 2005 (`Unknown MySQL server host`). Therefore no timestamp-level overlap, screen-session reconstruction, short-window stability estimate, or cross-table feature was claimed.

The requested touch, screen, foreground-app and keyboard-context measures are specified in `episode_definitions.md` and listed as not computed in `pilot_feature_table.csv`. The accelerometer assessment confirms that the archived pilot signal was dense but unsynchronized; jerk was not calculated. Future work requires restored SensorDB access and a complete same-device bounded episode query.

## Cross-Modal Phase 2 — Connection fix and synchronization pilot (2026-10-22 update)

Python and DBeaver were using the same SensorDB endpoint, port, database and native MySQL authentication. The earlier Python error 2005 was caused by restricted sandbox DNS/network isolation, not a hostname mismatch or SSH tunnel. Running the authorized read-only query outside that restriction made Python connectivity work; `SELECT 1` returned `1`.

The bounded pilot retrieved complete same-device event rows for two coverage-selected patient/device days. Both had keyboard, screen, touch and foreground-app data. After deduplication and verified unlock-to-lock/off session reconstruction, 2 patients and 60 sessions had genuinely synchronized event data. Touch and app transition rates and keyboard snapshot timing were calculated in anonymized aggregate outputs. Foreground-app duration was deferred because isolated package observations did not provide defensible episode durations. ACC jerk was not calculated because synchronized motion samples were not demonstrated.

See [Phase 2 outputs](output/analysis_candidates/cross_modal_feature_discovery_v2/) and the updated [Phase 2 README](output/analysis_candidates/cross_modal_feature_discovery_v2/README_cross_modal_phase2.md). Historical files remain unchanged.

## Cross-Modal Phase 3A and Phase 3 — 2026-10-22

The [accelerometer priority pilot](output/analysis_candidates/cross_modal_acc_priority_v1/README_cross_modal_acc_priority_v1.md) retrieved synchronized raw accelerometer segments during verified screen sessions for two coverage-selected devices. Six 60-second segments had at least 50 ACC samples, zero gaps over one second, and calculable raw vector jerk. Median acceleration magnitudes were gravity-like, but sampling differed sharply by device, so raw jerk is not yet comparable across devices. Jerk remains a newly proposed, exploratory phone-motion measure and was not interpreted as tremor or motor impairment.

The [cohort-scale Phase 3 workstream](output/analysis_candidates/cross_modal_feature_discovery_v3/README_cross_modal_phase3.md) reuses the validated two-patient, 60-session event pilot. Screen×Touch, Screen×Foreground App, and Keyboard×Foreground App features were computed with 1/5/10/15-minute within-session sensitivity tables. An expansion attempt across five additional coverage-selected devices exceeded the safe bounded-query budget, so no broader coverage or longitudinal reliability was claimed. ICC and early/late estimates remain not estimable until repeated days are retrieved per patient.

## Cross-Modal Phase 4 — Novel Interaction Features (2026-10-22)

The [Phase 4 interaction-feature audit](output/analysis_candidates/cross_modal_interaction_features_v1/README_cross_modal_interaction_features_v1.md) reviewed the existing feature bank and excluded the Phase 2/3 Screen×Touch, Screen×App, and Keyboard×App summaries from the novelty shortlist. Three new families were specified: event-centered Touch–Motion Coupling, Motion-Conditioned Touch Variability, and App-Switch Interruption Cost. The saved Phase 3 ACC segments support only coarse session-level touch-rate × moving-fraction proxies for two patients and six synchronized segments. Event-level ACC/touch alignment and transition-level keyboard contrasts were not claimed because bounded retrieval was unstable and the required timestamp-level rows were not retained together. Sensor identity and native cadence remain mandatory QC fields; the approximately 5-Hz and 125-Hz devices must not be pooled for jerk. No cognition or predictive analysis was run.

## Cross-Modal Phase 5 — Checkpointed Event-Level Export (2026-10-22)

The [Phase 5 event-export README](output/analysis_candidates/cross_modal_event_export_v1/README_cross_modal_event_export_v1.md) documents a bounded, resumable event-level dataset for four technically selected device-days and eight verified short screen sessions. Parquet partitions preserve pseudonymous patient/device/date/modality, timestamps, session membership, ACC vectors, touch/app metadata, and keyboard event metadata without exporting text, passwords, raw package names, or production device IDs. The export retains native ACC cadence, including approximately 7–160 ms observed intervals across the pilot. The focused ACC×Touch pilot reports within-session event-centered magnitude contrasts at ±500 and ±1,000 ms with matched same-session controls. These are technical measurement results only; no cognition or predictive analysis was run. Broad extraction remains deferred pending predeclared cadence and gap eligibility rules.

## Cross-Modal Phase 6 — ACC × Touch Temporal Coupling Validation (2026-10-22)

The [Phase 6 validation](output/analysis_candidates/cross_modal_acc_touch_validation_v1/README_cross_modal_acc_touch_validation_v1.md) reused the Phase 5 Parquet export without new database queries. It evaluated event-triggered acceleration profiles, same-session matched controls, shifted temporal negative controls, and cadence strata across 2 patients, 4 device-days, 7 usable sessions, and 251 touch events. The observed central profile contrast was small (session median +0.0080; bootstrap 95% interval −0.1266 to +0.0461) and overlapped the negative-control distribution. The decision is technically measurable but unstable; rate-homogeneous repeated-session validation is required before cohort expansion or cognitive testing.

## Cross-Modal Phase 7 — Motion-Conditioned Interaction Feasibility (2026-10-22)

The [Phase 7 feasibility report](output/analysis_candidates/cross_modal_motion_conditioned_v1/README_cross_modal_motion_conditioned_v1.md) reused the Phase 5 Parquet export and preserved the Phase 6 negative ACC×Touch result. A gravity-referenced residual ACC proxy was evaluated separately by cadence stratum. Touch variability in both motion states was estimable in only one session, and keyboard snapshots were absent or insufficient in both states for nearly all sessions. No reliable motion-conditioned interaction feature can be supported from the current export; a small repeated-day, rate-stratified export is required before further analysis.

## Cross-Modal Phase 8 — Targeted Repeated-Day Export (2026-10-22)

The [Phase 8 repeated-day export](output/analysis_candidates/cross_modal_repeated_day_export_v1/README_cross_modal_repeated_day_export_v1.md) used technical coverage only to select ten device-days and exported bounded, checkpointed same-device episodes. Repeated ACC days were obtained for two devices, but the prespecified moving/stationary event minimum was met in only one touch session and no keyboard session. Missing ACC on several event-covered candidate days and heterogeneous cadence remain the limiting factors. No repeated-day reliability, cognition testing, or predictive modeling was claimed.

## Cross-Modal Phase 9 — Coverage Bottleneck Analysis (2026-10-22)

The [Phase 9 bottleneck report](output/analysis_candidates/cross_modal_coverage_bottleneck_v1/README_cross_modal_coverage_bottleneck_v1.md) shows that the loss occurs at multiple technical stages: 7 of 17 verified sessions lack ACC, 6 of 10 ACC sessions fail the existing gap rule, and only 1 session has both motion states at the fixed threshold. No touch or keyboard session meets the minimum interval requirement in both states. The recommended strategy is to redesign toward continuous ACC context during touch or interaction-density windows rather than expand dual-state motion-conditioned extraction.

## Cross-Modal Phase 10 — Continuous ACC × Touch Features (2026-10-22)

The [Phase 10 continuous interaction analysis](output/analysis_candidates/cross_modal_continuous_interaction_v1/README_cross_modal_continuous_interaction_v1.md) replaced dual-state eligibility with non-overlapping 30/60-second ACC-plus-touch windows. Three sessions supported descriptive motion-density coupling at 30 seconds and two supported variability coupling at 60 seconds, but directions changed across sessions and no comparable repeated-day set supported reliability. The feature family is technically promising for a rate-matched repeated-day pilot; no cognition or predictive analysis was run.

## Cross-Modal Decision Gate and Non-ACC Interactions (2026-10-22)

The [decision-gate workstream](output/analysis_candidates/cross_modal_decision_and_nonacc_v1/README_cross_modal_decision_and_nonacc_v1.md) used the saved repeated-day Parquet export and did not rerun ACC×Touch analyses. Of 17 verified same-device screen sessions, ACC was present in 10, only 4 passed the existing sampling/gap QC, and only 1 contained both prespecified motion states. ACC×keyboard overlap was available in 2 sessions. The decision is to **defer broad ACC expansion** until a new coverage source or targeted export can provide a repeated-day, cadence-stratified sample; this is a technical coverage limitation, not a null behavioral result.

The same phase audited existing feature duplication and evaluated four event-linked non-ACC candidates. The export contained 137 app transitions across 17 sessions. A subsequent touch was observed after 110 transitions (5 patients, 5 devices, 9 patient-device-days); a subsequent keyboard snapshot after 22 transitions (4 patients, 4 sessions, 4 days), with no repeated keyboard-recovery patient across exported days. Screen-resume latency was measurable in all 17 sessions, but it remains an observed interaction proxy with explicit censoring, not a human response-time measure. App-switch disruption lacked an established matched uninterrupted-control set, and fragmentation is descriptive because it mixes behavior with event-capture density. The recommended next two implementations are Screen-Resume Interaction Latency and App-Switch Interaction Recovery. Prior Screen×Touch, Screen×App, and Keyboard×App summaries remain historical duplicates and are not counted as new features.

## Top-15 Article Evidence and Six-Signal Manuscript Table — 2026-10-26

The top-15 article evidence audit now reconstructs all 15 selected associations from saved patient-level files and documented cohort rules. Every row has a confidence interval and an FDR field; derived intervals and q-values are labeled separately from historical source statistics. The consolidated inferential table is `output/research_summary_20261025/top15_article_statistics_v1/top15_article_inferential_audit_v1.csv`.

The manuscript-facing six-signal table combines discovery, recording-adjusted partial Spearman results, leave-one-patient-out and permutation sensitivity, T1/T2 test–retest reliability, and corrected first/last-thirds sensitivity: `output/research_summary_20261025/top15_article_statistics_v1/six_signal_article_ready_table_v1.csv`. The preferred exploratory POC remains afternoon snapshot inter-event-interval change versus Executive Function change: discovery rho=.592856 (n=28, p=.000885, q=.090318, CI [.217589,.832254]); recording-adjusted partial rho=.507994 (p=.022209, q=.133256, CI [.102805,.785821]); T2 ICC=.415503 (n=18); corrected-thirds partial rho=.496090 (n=19, p=.071200, q=.835982, CI [-.502230,.904992]). This remains exploratory because the timing measure is a text-state snapshot proxy, T2 reliability is limited, corrected-window support is weak, and no independent validation exists.

The restricted morning IEI/Attention result has the largest coefficient (rho=.783686, n=18, p=.000119, q=.004765) but is a small window-selected sensitivity result with poor T2 reliability and weak corrected-thirds evidence. It should remain supplementary. Correlations and cross-validated predictive model performance must be reported in separate sections.
