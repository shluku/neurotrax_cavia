# Supplemental High-Frequency Modalities Subproject

## Purpose

This subproject analyzes the deferred direct sensor modalities and later tests whether they improve the existing phenotype models:

- `proximity` using `double_proximity`;
- `light` using `double_light_lux`;
- raw `accelerometer` motion data using validated metadata anchors.

All outputs are additive. Existing Phase 4, Phase 6, Phase 11, Phase 12, and Phase 111 outputs remain unchanged.

## Cohort spans

The same supplemental feature engine will support four explicit span families:

1. Phase 4 24-hour T1 baseline and the corresponding T2 24-hour span.
2. Phase 7 10-day availability-anchored T1 and T2 spans.
3. Phase 11/12 patient-specific midpoint spans, including the documented 123-day fallback for patients without T2.
4. Phase 111 full `[T1, T2)` interval, or `[T1, T1+123 days)` when T2 is unavailable.

Each modality/span combination has its own status, coverage, feature metadata, and wide patient-level output. A missing modality window remains missing; it is never converted to zero activity.

## Execution strategy

### Proximity and light

These are processed in bounded time chunks. The first features reuse the established definitions where available:

- valid row count and observed coverage;
- median and variability summaries;
- dark-light proportion and nighttime light summary;
- proximity value distribution, near/covered proportion, transitions, and temporal spread after per-device value inspection.

The direct sensor values are not treated as clinical states without documenting device-specific distributions and missingness.

### Accelerometer

The raw `accelerometer` table is approximately 1.56 TB and is not scanned broadly. The sequence is:

1. Use existing `sensor_accelerometer` metadata QC to identify candidate patient-device anchors.
2. Inspect short bounded raw windows around confirmed anchors to validate JSON fields, x/y/z availability, sampling density, duplicates, and gaps.
3. Extract by patient, device, and small time chunk; retain derived summaries rather than raw rows in cohort files.
4. Start with robust time-domain features such as valid sample count, coverage hours, sampling density, vector-magnitude summaries, variability, high-movement fraction, and movement-bout summaries.
5. Consider frequency-domain features only after signal regularity and field quality are demonstrated.

The existing accelerometer metadata QC is engineering context, not a movement biomarker. Missing raw rows are missing data, not no movement.

## Output contract

The subproject writes under:

`output/analysis_candidates/supplemental_modalities/`

Each modality/span output should include:

- resumable checkpoint JSONL;
- patient-table status CSV;
- device/window coverage CSV;
- derived feature long CSV;
- derived feature wide CSV;
- feature metadata and missingness summary;
- a README documenting the exact window, chunking, and QC rules.

## Model integration

After modality features are reviewed, build new augmented copies of each existing cohort:

- original active feature set;
- original plus proximity;
- original plus light;
- original plus accelerometer;
- original plus all supplemental modalities.

Rerun the same models with identical patient splits, target definitions, imputation rules, and mean baselines. The comparison must report performance deltas and coverage changes. No original model output is overwritten.

## Current starting point

The first implementation stage is the non-destructive inventory and anchor manifest. It does not query the raw accelerometer table. The existing metadata QC reports `sensor_accelerometer` anchors for 77 patients, which will guide the later bounded signal checks.
