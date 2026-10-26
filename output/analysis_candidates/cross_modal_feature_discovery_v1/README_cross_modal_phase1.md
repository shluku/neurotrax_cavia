# Cross-Table Digital Phenotyping — Phase 1

## Scope
This phase audited saved SensorDB schema reviews and bounded T1 coverage outputs. It did not train models, run cognition screens, or join massive raw motion tables. The live SensorDB host was unavailable during this run (`Unknown MySQL server host`), so timestamp-level ±5/30/60-second overlap counts were not claimed from archived window-count tables.

## Literature
The literature register verifies Ning et al. (CHI 2023, PMID 38115842), Twose et al. (Alzheimer’s & Dementia, DOI 10.1002/alz.086452), the older-adult multimodal guide (Innovation in Aging, PMID 41853224 / DOI 10.1093/geroni/igag007), Butler et al. (Nature Medicine 2025, DOI 10.1038/s41591-024-03475-9), and DeepMood as a directly relevant supplementary source. Literature supports synchronizing keyboard dynamics with accelerometer context and using daily/session summaries, but the closest studies use true keypress events or proprietary sensor streams.

## Local data audit
Keyboard, applications_foreground, screen and touch have usable bounded T1 examples. Keyboard has 80 mapped patients and 3,150,391 mapped rows; applications_foreground has 86 patients and 2,020,313 rows. A selected patient/device 24-hour window contained 1,832 keyboard rows, 698 foreground-app rows, 304 screen rows, 1,820 touch rows and 423 activity-recognition rows. Archived accelerometer pilot data demonstrated dense raw signal (~3,202 rows in five minutes, approximately 10.7 Hz), but broad patient-level raw motion overlap was not available. Linear accelerometer had no rows in the checked T1-week protocol windows; gyroscope, gravity and rotation likewise had zero rows in the reviewed primary windows.

## Synchronization decision
The archived coverage scans include only the Phase 2A selected review windows and support same-patient/same-window co-coverage for that pilot record only. They do not contain enough event-level rows to calculate true simultaneous overlap or ±5/30/60-second coverage. Those deliverables are explicitly marked `not computed` in `short_window_feasibility.csv`, rather than treating calendar-window co-coverage as synchronization.

## Priority
The first pilot should use screen–touch burst variability or foreground-app switching during screen-unlocked sessions because both are event-based and technically accessible. A second pilot can add keyboard snapshot variability stratified by application. Accelerometer-coupled features should wait for a bounded same-device raw-motion query and sampling/duplicate QC. Jerk must be defined on resampled, gravity-compensated or explicitly raw acceleration; no feature should be called tremor, gait, or hand-motor impairment.

## Files
- `literature_to_feature_matrix.csv`
- `table_schema_and_timestamp_audit.csv`
- `patient_temporal_overlap_matrix.csv`
- `short_window_feasibility.csv`
- `cross_modal_feature_proposals.csv`

All historical keyboard, sensor and model outputs are preserved.
