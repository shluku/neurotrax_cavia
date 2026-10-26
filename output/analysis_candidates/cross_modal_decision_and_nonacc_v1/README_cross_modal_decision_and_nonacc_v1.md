# Cross-Modal Decision and Non-ACC Interactions v1

## Scope
This phase used the existing privacy-safe, checkpointed Parquet export from `cross_modal_repeated_day_export_v1`. No production queries, cognition tests, model fitting, or ACC×Touch reanalysis were run.

## ACC coverage decision
The saved repeated-day export contains 17 verified same-device screen sessions from 5 patients and 5 devices across 9 device-days. ACC is present in 10/17 sessions; only 4/10 pass the existing ACC sampling/gap QC, and only 1 session contains both prespecified motion states. ACC×keyboard overlap is present in 2 sessions. Therefore the decision is **DEFER broad ACC expansion**: the current saved coverage does not support a reliable repeated-day validation sample. This is a coverage/QC bottleneck, not evidence of absent behavioral variation.

## Non-ACC event semantics and calculations
- **App-switch recovery:** consecutive foreground-app rows with a changed privacy-preserving `package_hash` define a transition. Latency is transition timestamp to the first later touch or keyboard timestamp in the same verified session. No later event is coded as a zero; it is right-censored (`event_observed=False`).
- **App-switch disruption:** counts of touch and keyboard observations in the 10 s before versus after each transition are descriptive. A matched uninterrupted same-app control requires a separate control selection; the exported sample does not provide enough independent controls for a confirmatory contrast.
- **Screen-resume latency:** verified screen session start (screen activation/unlock semantics from the existing episode definition) to first observed touch/keyboard event. Sessions without an event are censored. This is an observed-interaction proxy, not human response time.
- **Cross-modal fragmentation:** counts touch gaps >30 s, keyboard snapshot gaps >30 s, app transitions, and app transitions falling inside touch inactivity gaps, all within the same session. This measures observed recording/interaction fragmentation and is not a direct measure of cognition or intent.

## Feasibility
Results are in `nonacc_interaction_feasibility_matrix.csv`, `patient_day_coverage.csv`, `nonacc_session_features.csv`, `app_transition_recovery_and_disruption.csv`, and `cross_modal_fragmentation.csv`. The saved export contains 137 observed app transitions across 17 sessions, 5 patients, 5 devices, and 9 patient-device-days. A subsequent touch was observed after 110 transitions (5 patients, 17 sessions, 9 days); a subsequent keyboard snapshot after 22 transitions (4 patients, 4 sessions, 4 days), with no patient having keyboard recovery on two exported days. Screen-resume latency is measurable in all 17 sessions, while matched disruption controls were not established and must be added prospectively. Recovery and screen-resume are the most feasible candidates because they require one subsequent interaction event rather than dual motion-state coverage. Disruption is secondary because matched controls and sufficient pre/post events are limited. Fragmentation is feasible descriptively but mixes behavior with event-capture density.

## Recommended top two
1. **Screen-resume interaction latency** — implement first with explicit censoring and coverage QC.
2. **App-switch recovery latency** — implement separately for touch and keyboard, retaining event visibility and same-session rules.

Do not treat the prior Screen×Touch, Screen×App, or Keyboard×App rates/interval summaries as new; see `existing_feature_duplication_audit.csv`.
