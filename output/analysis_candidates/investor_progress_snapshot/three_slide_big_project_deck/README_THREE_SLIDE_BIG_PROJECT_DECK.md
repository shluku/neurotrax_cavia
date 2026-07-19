# Three-Slide Big Project Deck

This folder contains a compact 3-slide SVG deck for presenting project scale and complexity.

Slides:

1. `slide_01_neurotrax_overview.svg` - packed NeuroTrax cohort/timeline/domain overview.
2. `slide_02_sensordb_sql_scale.svg` - SensorDB SQL scale, approximate 10 TB / 83 patients = 120.5 GB per patient, table families.
3. `slide_03_feature_algorithm_pipeline.svg` - how each SQL table requires custom feature algorithms, with keyboard as the detailed example.

Key framing:

- NeuroTrax subjects: 83
- Patients with T1: 83
- Patients with T1 + T2: 62
- Main NeuroTrax domains shown: 9
- Approximate raw storage scale: 10 TB
- Approximate storage per NeuroTrax patient: 120.5 GB
- Raw SQL tables tracked: 44
- Deduplicated table families: 33
- Relevant target analysis tables: 21
- Candidate feature definitions: 69
- Selected features: 29
- Current calculated numeric values: 27
