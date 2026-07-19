# Big Project Infographic Slide Pack

Created for explaining the scale and complexity of the NeuroTrax SensorDB CAVIA project.

Slides:

1. `big_project_slide_01_overview.svg` - overall project scale and outcomes
2. `big_project_slide_02_neurotrax.svg` - NeuroTrax cohort, domains, and timeline
3. `big_project_slide_03_sensordb_scale.svg` - SensorDB SQL table scale, GB by table, deduplicated table families
4. `big_project_slide_04_patient_coverage.svg` - patient/device data-day coverage and note about per-patient GB
5. `big_project_slide_05_keyboard_feature_depth.svg` - detailed keyboard feature engineering example
6. `big_project_slide_06_calculable_features.svg` - current calculated feature families and tables

Key numbers used:

- NeuroTrax subjects: 83
- Patients with T1: 83
- Patients with T1 + T2: 62
- NeuroTrax core domains shown: 8
- Raw SQL tables inventoried: 44
- Deduplicated table families: 33
- Estimated full SQL DB size: 6,862 GB
- Relevant target tables for Phase 2: 21
- Reviewed table files: 10
- Candidate feature definitions: 69
- Selected features: 29
- Current numeric calculated feature values: 27

Important note:

Approximate presentation estimate: 10 TB divided across 83 NeuroTrax patients is about 120 GB per patient. This is not an exact patient-level storage calculation; exact per-patient GB can be estimated later with a dedicated row-count/row-size script by device and table.
