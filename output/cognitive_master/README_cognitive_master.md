# Cognitive Master Output

## Final Status

- `master_cognitive_wide.csv` has **83 rows** and **112 columns**.
- `Subject_ID_N` is unique for all **83** subjects.
- One empty artifact row was removed during build.
- One real subject has missing `Subject_ID_D` and is reported in `subjects_missing_device_label_id.csv`.
- Special code flags include only actual NeuroTrax codes: **DI=106** and **FP=75**.
- `delta_consistency_report.csv` has **0** mismatches.

## Current QC Files

- `qc_missingness_report.csv`
- `qc_subject_completeness.csv`
- `qc_special_code_summary.csv`
- `qc_suspicious_subject_rows.csv`
- `subjects_missing_device_label_id.csv`

## Core Files

- `master_cognitive_wide.csv`
- `cognitive_code_flags_long.csv`
- `cognitive_data_dictionary.csv`
- `delta_consistency_report.csv`
