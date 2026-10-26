# Afternoon keyboard interval mechanism audit — 2026-10-20

This separate, exploratory audit examines the original 28-person association between afternoon snapshot inter-event-interval (IEI) change and Executive Function change. It queried only those patients’ existing Early/Late windows and wrote no raw keyboard text, package name, or device identifier.

## Exact implementation

The tested feature is `keyboard_12_18_median_inter_event_interval_ms`.

- `keyboard_deep_dive.py:337-344` fetches keyboard rows for the saved window device IDs and half-open interval `[window_start_ms, window_end_ms)`.
- `keyboard_deep_dive.py:93-128` parses JSON, requires a numeric timestamp, and removes exact duplicates using `(timestamp, device_id, before_text, current_text, package_name, is_password)`. The retained event object contains lengths and flags; this audit never exports text.
- `keyboard_deep_dive.py:127,147-175` sorts by device/package/time and compares only adjacent records within the same device and package. An interval must be positive and at most 30,000 ms. Gaps above 30 seconds start a new burst and are excluded; zero/negative gaps are excluded.
- The timezone is `Asia/Jerusalem` (`keyboard_deep_dive.py:25,59-60`). Each interval is assigned to its later snapshot (`:171-173`). The 12:00–18:00 bin is local 12:00 inclusive through 18:00 exclusive (`:33,249-254`).
- The feature is the median of eligible intervals in milliseconds. Intervals above 2,000 ms remain in the median and are separately counted as long pauses, provided they are no longer than 30 seconds (`:174-175,205-206`).
- Early is the saved Phase 11 `[T1, midpoint)` window and Late is the saved Phase 12 `[midpoint, T2)` window. `keyboard_signal_discovery.py:66-82` joins the two window summaries and calculates `Late − Early` at line 81; the association is computed at lines 114-146.

The raw-query recomputation matched the saved Early and Late afternoon medians for all **28/28** participants.

## Findings

The saved discovery association is reproduced exactly: Spearman ρ=.592856, n=28, p=.000885. The labeled scatter is `afternoon_iei_vs_executive_function_scatter.png`; the patient-level table is `patient_level_mechanism_audit.csv`.

IEI change is strongly related to recording structure: changed device set ρ=−.593 (p=.000889), interval-count change ρ=−.515 (p=.0051), event rate per active day ρ=−.545 (p=.0027), active-day change ρ=−.489 (p=.0082), and long-pause-rate change ρ=.498 (p=.0070). Device sets differ between Early and Late in 22/28 participants. Median Early/Late package-set Jaccard similarity is .233; package names are not saved.

The same technical measures also relate to Executive Function change: interval-count change ρ=−.571 (p=.0015), active-day change ρ=−.465 (p=.0127), event-rate change ρ=−.417 (p=.0272), package-set similarity ρ=.502 (p=.0065), and device-set change ρ=−.453 (p=.0156). These correlations are exploratory and uncorrected for multiplicity.

| Adjustment | Partial Spearman ρ | p | n |
|---|---:|---:|---:|
| None | .593 | .000885 | 28 |
| Active days, log interval count, events per active day | .461 | .0205 | 28 |
| Text-length change, long-pause rate, package similarity, device change | .395 | .0562 | 28 |
| All seven audited technical factors | .356 | .1132 | 28 |

The attenuation, together with the strong relationship between recording structure and both variables, means the signal cannot currently be interpreted as clean typing slowing or a behavioral improvement marker. It is compatible with a mixture of behavior, device/app composition, and snapshot cadence. The combined adjustment has limited degrees of freedom and is a sensitivity analysis, not a causal model.

## Files and limits

`patient_level_mechanism_audit.csv` contains one row per participant with Early/Late IEI, EF T1/T2/change, coverage, and aggregate technical measures. `technical_factor_associations.csv` and `exploratory_adjusted_associations.csv` contain the new exploratory analyses. No historical output was overwritten. Validation with true keydown/keyup events and stable device/sampling metadata is still required.
