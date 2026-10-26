# Word Completion Timing & Variability (v1)

## Purpose

This is an additive feasibility and exploratory analysis. It does not modify the existing keyboard Feature Bank, historical outputs, or predictive models.

## Data and identifiability

The source contains timestamped JSON text-state snapshots (`before_text`, `current_text`), a device identifier, and an application package. It does not contain key-down/key-up events. A completion time is therefore the interval between observable text states, not the time required to type a word. The first character may precede the first observed state; missing snapshots, paste, predictive text, autocorrect, corrections, and punctuation cannot be fully separated from ordinary text growth.

## Reproducible definition

Within each device/application sequence, a candidate starts at the first observed non-space state after an empty or space-terminated state and ends at a later current state ending in a literal ASCII space. Positive consecutive timestamps are retained. A gap above 30,000 ms starts a new burst and abandons an unfinished candidate. A high-confidence observable candidate has a boundary start, append-only transitions, and no >2,000-ms interruption or non-append edit transition. Partial starts and ambiguous edit/gap candidates are counted separately. Raw text is held in memory only and is never exported.

For high-confidence candidates, window features include mean, median, SD, IQR, MAD, P10, P90, CV, count, high-confidence fraction, and count per active recording minute. Morning/afternoon/evening/night summaries, active days, snapshots, valid intervals, long pauses, daily median variability/slope, weekly count variability, and T2−T1 deltas are also saved. The rate denominator is active recording minutes, so it is a production proxy rather than words per true typing minute.

## QC results

The run covers 81 T1 and 60 T2 windows, 2,657 patient-days, and 1,467,287 distinct observations. There are 105,402 candidate completions: 64,667 high-confidence observable (61.4%), 2,255 partial starts (2.1%), and 38,480 ambiguous edit/gap candidates (36.5%). The median window-level high-confidence fraction is 56.9%; 39 windows have no eligible completion. These figures support aggregate exploratory use, not individual word-speed reconstruction.

## Exploratory cognitive screen

The saved screen contains 256 estimable feature/outcome rows, 500 bootstrap resamples per row, and BH correction over that screen. The largest baseline absolute association is evening timing with Attention (ρ=−.362, n=52, p=.0084, bootstrap CI [−.593,−.112], q=.352). The largest longitudinal association is Global change versus word-completion IQR change (ρ=.409, n=31, p=.0225, bootstrap CI [.051,.673], q=.858). No association passes q<.05 or q≤.20. These tests are exploratory and do not constitute confirmation or model-selection evidence.

The separate `keyboard_word_completion_posthoc.py` output contains 263 recording-adjusted partial associations (active days, snapshot rate, valid intervals). In the 28-patient cohort shared with the afternoon IEI audit, median completion-time delta versus Executive-Function delta is ρ=−.145 (n=27, p=.471), IQR delta is ρ=−.007 (n=27, p=.971), and the existing snapshot-IEI delta is ρ=.593 (n=28, p=.000885). This matched comparison is descriptive and exploratory.

## Outputs

- `word_completion_window_features.csv`: privacy-safe T1/T2 window aggregates.
- `word_completion_daily_features.csv`: privacy-safe daily aggregates.
- `word_completion_quality_summary.csv`: counts by quality class.
- `word_completion_patient_table.csv`: paired aggregates and saved cognitive outcomes.
- `word_completion_cognitive_associations.csv`: baseline and T2−T1 exploratory associations.
- `word_completion_recording_adjusted_associations.csv`: exploratory partial rank associations with coverage covariates.
- `word_completion_vs_snapshot_iei_matched.csv`: matched descriptive comparison with the saved afternoon IEI audit.
- `word_completion_manifest.json`: cohort and privacy status.

Reproduce from the repository root with:

```bash
.venv/bin/python3 -u keyboard_word_completion_deep_dive.py
```

No general model integration was performed. The appropriate next step is independent, coverage-controlled validation, ideally with consented keypress/key-release telemetry or explicit sampling metadata.
