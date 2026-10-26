# Keyboard Deep Dive v1 Protocol

**Status:** approved extraction and feature-QC phase; model integration is deferred.  
**Authorized:** 2026-10-20  
**Primary objective:** expand the keyboard component of the patient-level digital Feature Bank so it can be evaluated in the overall cognitive models.

## Scope

This phase implements the first five planning sections:

1. Freeze a versioned keyboard feature contract.
2. Audit the available keyboard schema and field prevalence.
3. Build a privacy-safe canonical event representation in memory.
4. Calculate daily keyboard summaries.
5. Aggregate those summaries into the existing Phase 11 T1 and Phase 12 T2 windows.

No existing keyboard pipeline, feature matrix, model, or output is overwritten. New files are written only under `output/analysis_candidates/keyboard_deep_dive_v1/`.

## Source schema

The sampled SensorDB `keyboard` table has SQL fields `_id`, `timestamp`, `device_id`, and `data`. The sampled JSON keys are `before_text`, `current_text`, `package_name`, `is_password`, `device_id`, and `timestamp`.

The table contains timestamped text-state snapshots rather than explicit key press/release records. Exact hold time, flight time, press-to-press latency, release-to-release latency, and delete-key hold time are therefore unavailable unless a separate press/release source is found during the schema audit. The implemented features are named text-state timing proxies.

## Privacy and canonicalization

Raw `before_text` and `current_text` values are used transiently to derive lengths and transition categories. They are never written to the output. Raw package identifiers are also excluded from model-facing output; only aggregate package counts are retained.

Rows are deduplicated using timestamp, device, before-text, current-text, package, and password-field status. Events are ordered by device, package, and timestamp. A typing burst is separated by a gap greater than 30 seconds. Inter-event pauses above 2 seconds are retained as pauses but are not allowed to define normal typing speed.

## Feature contract

The v1 extraction produces daily and window-level values for:

- distinct observation count and observations per active minute;
- median, SD, IQR, MAD, P05–P95 spread, and coefficient of variation of valid inter-event intervals;
- long-pause count and rate;
- burst count, burst duration, and session fragmentation;
- deletion count and deletion rate;
- pre-correction pause, post-correction pause, correction recovery time, and deletion burst count;
- text-growth transitions and approximate word-completion time;
- six-hour activity, speed, and variability summaries;
- daily speed/rhythm variability and robust trends where enough daily observations exist.

The existing six keyboard features remain unchanged. New features are additive and carry their denominators and quality fields.

## Window definitions

The extraction reads the saved clinical windows from:

- `output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_patient_table_status.csv`
- `output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_patient_table_status.csv`

T1 and T2 are extracted independently. Local time is `Asia/Jerusalem`; intervals are half-open `[window_start_ms, window_end_ms)`. The existing global-decline rule is not applied during extraction; it remains a later analysis eligibility rule.

## Missingness and quality

No keyboard rows means missing keyboard data, not zero typing. Every daily/window output includes raw-row count, distinct-observation count, valid-interval count, active minutes, active days, parse errors, duplicate rows removed, and a feature status. Features requiring insufficient observations are left missing.

## Planned downstream use

After review of the schema audit, coverage, duplicate burden, feature distributions, and privacy checks, the new Feature Bank may be evaluated in the overall Global T1 and T2–T1 models, followed by cognitive-domain models. Keyboard-only modeling remains secondary. Any feature selection must occur inside participant-level validation folds.

## Reproduction

```bash
.venv/bin/python3 -u keyboard_deep_dive.py --schema-only
.venv/bin/python3 -u keyboard_deep_dive.py
```

The script writes a run manifest, schema audit, daily features, T1/T2 window features, coverage summaries, and a machine-readable feature dictionary. It does not modify prior outputs.
