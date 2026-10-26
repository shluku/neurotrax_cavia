# Cross-Modal Phase 4 — Novel Interaction Features

## Scope and status

This is a bounded feasibility pilot using the two verified same-device days from Phase 2 and the six synchronized ACC segments from Phase 3A. It does not use cognitive outcomes, does not train models, and does not replace prior outputs.

The novelty audit found that touch rate/interval summaries, app transition rates, and same-app keyboard snapshot IEI were already implemented in Phase 2/3. They are explicitly excluded from the new-feature shortlist. The three new families are event-centered Touch–Motion Coupling, Motion-Conditioned Touch Variability, and App-Switch Interruption Cost.

## Data and quality controls

The verified base contains two patients, two device-days, and 60 screen-unlocked sessions in the Phase 2 event tables. The saved ACC synchronization output contains six segments (three per device) with both keyboard-associated and screen-active/no-keyboard segments. ACC sensor identity and native timestamp cadence are retained: `dev_d74f7a` uses accelerometer-lsm6dsm/ST at approximately 5 Hz, and `dev_72e21d` uses BMI120/BOSCH at approximately 125 Hz. ACC magnitudes are treated as raw general-accelerometer magnitude proxies and may include gravity. Native rate, sample count, p95 interval, gap fraction, and metadata identity remain QC fields.

A bounded live retrieval attempt was made for interaction-bearing sessions. Some session-scoped ACC retrievals did not complete within the safe query budget, so event-level ACC/touch alignment was not claimed. No missing ACC was treated as stationary, and no event-level values were imputed.

## Feature definitions

1. **Touch–Motion Coupling (target definition).** For each touch timestamp, compute ACC magnitude in a prespecified ±500-ms window (sensitivity ±1,000 ms), then compare with matched no-touch windows inside the same verified screen session. Report within-session median difference, sample counts, native ACC rate, and gaps. This is temporal association, not causation.
2. **Motion-Conditioned Touch Variability (target definition).** Partition screen sessions into fixed 5-second bins. Classify a bin as moving when ACC magnitude SD exceeds a prespecified threshold (primary 0.15 in raw magnitude units; sensitivity 0.05 and 0.30). Compare touch inter-event IQR/CV only when both endpoints fall in bins with the same condition. Missing ACC bins remain missing.
3. **App-Switch Interruption Cost (target definition).** At a verified foreground-app package transition, calculate keyboard snapshot IEI in the preceding and following 10-second windows. The primary contrast is post minus pre, with an uninterrupted same-app window as control. This remains a text-state timing proxy, not physical keystroke latency.

## What is currently estimable

The saved summaries support two coarse session-level proxies: touch rate multiplied by ACC moving fraction and touch rate multiplied by the stationary fraction. These are descriptive interaction proxies, not substitutes for event-centered coupling. They are saved in `interaction_session_proxy_table.csv` and summarized in `pilot_feature_distributions.csv`.

Event-centered touch–motion contrasts, motion-conditioned touch interval variability, and app-switch interruption cost are **not estimable** from the saved aggregates because touch timestamps, ACC samples, app-transition timestamps, and keyboard rows were not persisted together in a privacy-safe event-level output. The attempted bounded retrieval was not stable enough to create those outputs without broadening the query budget.

## Feasibility decision

The relationship between phone movement and digital interaction cannot yet be quantified reliably at the requested event level. The coarse proxies are available for a small, two-device pilot but are strongly exposed to sampling-rate and session-composition confounding. The 5-Hz and 125-Hz streams must not be pooled for jerk or high-frequency comparisons.

Recommended next step: build a checkpointed, same-device event-level extract for a small fixed set of short sessions, retrieving only timestamps, touch/app/keyboard event metadata needed for alignment and ACC vectors in volatile memory. Require minimum ACC sample counts and gap limits before computing the three target features. Expand to repeated days only after event-level QC succeeds.

## Outputs

- `novelty_literature_provenance_matrix.csv`
- `patient_device_day_coverage.csv`
- `session_interaction_coverage.csv` (Phase 2 session table joined to saved ACC segments)
- `interaction_session_proxy_table.csv`
- `pilot_feature_distributions.csv`
- `touch_motion_coupling.csv`, `motion_conditioned_touch_variability.csv`, and `app_switch_interruption_cost.csv` are reserved for event-level extraction; no unverified values are written.

No cognitive association testing or predictive modeling was run.
