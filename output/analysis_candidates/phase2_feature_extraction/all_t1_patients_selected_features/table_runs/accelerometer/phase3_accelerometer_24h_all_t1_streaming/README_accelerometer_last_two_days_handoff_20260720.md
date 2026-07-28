# Accelerometer Last-Two-Days Handoff

Date written: 2026-07-20

This note summarizes the accelerometer work completed over the last two days and the stopped all-T1 streaming run state. It is intended as the restart point for the next pilot.

## What Was Built

We moved from accelerometer metadata/QC into raw accelerometer feature extraction.

Main files:

- `build_sensor_linear_accelerometer_qc_framework.py`
  - Built the accelerometer-family QC framework.
  - Established that `sensor_accelerometer` is the better first raw-motion stream than `sensor_linear_accelerometer` for this cohort.
- `phase2_accelerometer_raw_signal_framework.py`
  - Confirmed the raw `accelerometer` table is very large, about 1.56 TB.
  - Established that future extraction must use bounded, chunked SQL windows.
  - Used `sensor_accelerometer.window_start_local` metadata as the anchor for raw accelerometer lookup.
- `analyze_accelerometer_24h_local_pilot.py`
  - Defined the 24-hour local accelerometer feature logic.
  - Includes chunk summaries, duplicate handling, sampling/gap QC, stillness/handling/motion summaries, threshold sensitivity, and bandpass summaries.
- `phase3_extract_accelerometer_24h_all_t1_streaming.py`
  - Production-style streaming extractor for all eligible T1 patients.
  - Streams in 5-minute SQL chunks filtered by `device_id` and timestamp.
  - Does not save full raw 24-hour files.
  - Appends chunk download logs immediately.
  - Appends patient-level feature/status outputs only after a patient finishes.

## Current Run Folder

All current stopped-run outputs are here:

`output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_all_t1_streaming/`

Important outputs:

- `phase3_accelerometer_24h_all_t1_streaming_patient_status.csv`
- `phase3_accelerometer_24h_all_t1_streaming_download_chunk_log.csv`
- `phase3_accelerometer_24h_all_t1_streaming_features_wide.csv`
- `phase3_accelerometer_24h_all_t1_streaming_features_long.csv`
- `phase3_accelerometer_24h_all_t1_streaming_chunk_summary.csv`
- `phase3_accelerometer_24h_all_t1_streaming_threshold_sensitivity.csv`
- `phase3_accelerometer_24h_all_t1_streaming_bandpass_summary.csv`
- `phase3_accelerometer_24h_all_t1_streaming_bandpass_hourly_summary.csv`
- `phase3_accelerometer_24h_all_t1_streaming_checkpoint.jsonl`

## Stopped Run State

The all-T1 streaming run was manually stopped on 2026-07-20 at about 22:26 local time.

The process was stopped intentionally. No output files were deleted.

Final file counts at stop:

- `patient_status.csv`: 20 lines = 19 processed patient rows plus header
- `download_chunk_log.csv`: 1736 lines = 1735 chunk log rows plus header
- `features_wide.csv`: 5 lines = 4 calculated patient rows plus header

Processed patient status:

- 19 patients reached a patient-level status row.
- 4 patients calculated successfully.
- 14 patients had no raw rows at the accelerometer anchor.
- 1 patient errored: `055`, message `Encountered all NA values`.

Calculated patients:

| Subject_ID_D | Raw rows downloaded | Rows after numeric/duplicate QC | Duplicates removed | Valid signal minutes |
| --- | ---: | ---: | ---: | ---: |
| 041 | 1,072,768 | 711,764 | 361,004 | 1435.0 |
| 003 | 10,325,314 | 1,231,738 | 9,093,576 | 1440.0 |
| 078 | 34,328,500 | 493,500 | 33,835,000 | 330.0 |
| 053 | 106,716 | 17,786 | 88,930 | 15.0 |

Patients marked missing at anchor:

`074`, `032`, `013`, `089`, `044`, `007`, `076`, `022`, `072`, `002`, `050`, `026`, `014`, `062`

Errored patient:

- `055`: `Encountered all NA values`

## Exact Stop Point

The run stopped during subject `030`; this subject does not have a patient-level status row because it did not finish the 24-hour window.

Last written chunk:

```text
Subject_ID_D: 030
device_id: be1e1b3b-4ddf-4851-84d3-990843d5cb58
chunk_index: 126
chunk_start_local: 2025-01-08 19:38:36+0200
chunk_end_local: 2025-01-08 19:43:36+0200
raw_rows_downloaded in chunk: 187,274
cumulative_raw_rows_downloaded for subject 030: 71,302,568
status: ok
```

Important interpretation: subject `030` is partial only. It should not be treated as a completed calculated patient in the current output set.

## Key Lessons

- Raw `accelerometer` is feasible only with strict chunking.
- Some patients have metadata anchors but no raw accelerometer rows near that anchor.
- Some completed patients contain extreme duplication.
  - Example: `078` downloaded 34,328,500 raw rows but only 493,500 remained after numeric/duplicate QC.
  - Example: `003` downloaded 10,325,314 raw rows with 9,093,576 duplicates removed.
- Feature outputs are patient-boundary outputs. If a run is stopped mid-patient, only `download_chunk_log.csv` reflects the partial progress.
- Resume behavior currently skips patients present in `patient_status.csv`; it does not know how to resume subject `030` from chunk 127.

## Recommended Tomorrow Pilot

Do not continue the stopped all-T1 run blindly.

Recommended next pilot:

1. Use a fresh output directory for the new pilot.
2. Start with a small `--limit-patients` run.
3. Include at least one high-volume subject and one missing-at-anchor case.
4. Add a per-patient row for partial/interrupted patients if we need resumability inside a patient.
5. Consider a guardrail for excessive raw rows per patient or per chunk before running all 77 eligible patients.
6. Re-check subject `055` separately because the error row is shorter than the normal status schema and indicates an all-NA feature path.

Possible smoke-test command pattern:

```bash
PYTHONUNBUFFERED=1 .venv/bin/python3 phase3_extract_accelerometer_24h_all_t1_streaming.py \
  --limit-patients 3 \
  --out-dir output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/<new_pilot_dir>
```

Possible resume command for a completed-patient-only rerun:

```bash
PYTHONUNBUFFERED=1 .venv/bin/python3 phase3_extract_accelerometer_24h_all_t1_streaming.py \
  --resume \
  --out-dir output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/<new_or_existing_dir>
```

Use caution with `--resume` on the current stopped directory: it will skip the 19 patients in `patient_status.csv`, but subject `030` has only partial chunk logs and no patient status row. A plain resume into this same directory would likely start `030` again from the beginning and append duplicate chunk log rows.

## Suggested Code Improvements Before Next Full Run

- Add an explicit `partial_interrupted` or `in_progress` status row before starting each patient.
- Add chunk-level resume support keyed by `Subject_ID_D`, `device_id`, and `chunk_index`.
- Add a `--start-after-subject` or `--subject-list` option for controlled pilot selection.
- Add a row-count cap option for pilot runs, for example `--max-raw-rows-per-patient`.
- Normalize exception status rows so every row in `patient_status.csv` has the same columns.
- Write process logs to file from inside Python, not only through terminal/screen redirection.

## Bottom Line

The last two days produced a working streaming accelerometer extraction path and real patient-level outputs, but the stopped all-T1 run should be treated as exploratory production-pilot output, not a final cohort table. Tomorrow should continue with a smaller controlled pilot, ideally after adding partial-patient status and chunk-resume guardrails.
