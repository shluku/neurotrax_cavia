# keyboard Feature Review

## Table Meaning

`keyboard` records keyboard text-state events observed on the device.

For the current protocol, one raw `keyboard` row means one keyboard observation row within the selected 24-hour T1-week window. The Phase 2A sample suggests rows can appear as duplicated pairs, so raw row counts may overstate the number of distinct keyboard observations unless duplication is handled explicitly.

This table can be useful for active phone-interaction context, but it is highly sensitive because it contains text-state fields. Future model-facing features should use aggregate counts only, not raw typed content.

## Fields Seen in `data`

The Phase 2A expanded sample shows these fields in `keyboard.data`:

- `before_text`
- `current_text`
- `is_password`
- `package_name`
- `device_id`
- `timestamp`

Current observations:

- `before_text` and `current_text` contain text-state values and should not be used directly as phenotype features.
- `current_text` appears masked/bracketed in the sample, but it still reflects typed-content state and should be treated as sensitive.
- `is_password` was `0` in the first 20 sampled rows.
- `package_name` was `com.whatsapp` in the first 20 sampled rows.
- The first 20 raw rows collapse to 10 distinct observations using `timestamp`, `device_id`, `before_text`, `current_text`, `package_name`, and `is_password`.

## Candidate Features

Six `keyboard` features are selected for Phase 2B:

| Selected feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `keyboard_median_inter_event_interval_ms` | Median milliseconds between consecutive deduplicated keyboard observations inside active typing intervals. | Typical keyboard text-state rhythm. | Not true key hold/flight time; duplicates and long idle gaps are handled before calculation. |
| `keyboard_inter_event_interval_iqr_ms` | IQR of milliseconds between consecutive deduplicated keyboard observations. | Variability of keyboard text-state rhythm. | High variability can reflect pauses, interruptions, app behavior, or logging artifacts. |
| `keyboard_long_pause_count_2s` | Count intervals greater than 2 seconds and no more than the active-burst threshold. | Within-typing pause structure. | Pauses are nonspecific and not diagnostic. |
| `keyboard_typing_burst_count` | Count typing bursts separated by gaps greater than 30 seconds. | Number of distinct typing episodes. | Threshold-dependent exploratory feature. |
| `keyboard_median_word_completion_time_ms` | Infer word boundaries from text-state transitions ending in a space and compute median completion time. | Approximate word production timing. | Raw text-state is parsed transiently only; no words are saved. Language, emoji, and editing complicate interpretation. |
| `keyboard_deletion_event_count` | Count transitions where text length decreases. | Deletion/backspace-like correction behavior. | Deletion is not direct error rate. |

Basic candidate features not selected yet:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `keyboard_event_count` | Count observed `keyboard` rows in the selected 24-hour window, with duplicate handling documented. | Active typing/text-entry event volume. | Raw row count may include duplicated rows; missing rows are missing data, not no typing. |
| `keyboard_distinct_observation_count` | Count distinct observations after deduplicating by `timestamp`, `device_id`, `before_text`, `current_text`, `package_name`, and `is_password`. | Cleaner estimate of keyboard observation volume. | Still depends on logging behavior and text-state changes, not exact keystrokes. |
| `keyboard_unique_package_count` | Count distinct `package_name` values observed in keyboard rows. | Breadth of apps where keyboard activity occurred. | Package names may be sensitive; final outputs should stay aggregate. |
| `keyboard_password_field_event_count` | Count rows where `is_password` indicates password-field typing. | Context for sensitive/password-field keyboard logging. | Better treated as data/privacy context, not behavioral phenotype. |

## Advanced Keyboard-Dynamics Candidate Features

Literature on keystroke dynamics and smartphone digital phenotyping commonly uses timing metadata rather than raw typed content: inter-key or inter-event intervals, pause structure, session/burst structure, backspace/correction behavior, and word/space timing. The DeepMood/BiAffect line of work is especially relevant because it used mobile keyboard metadata while avoiding collection of ordinary character content, keeping only timing and limited key metadata such as backspace and space. General keystroke-dynamics work also emphasizes typing rhythm, variability, and error/correction patterns.

Our `keyboard` table is not true keydown/keyup data. It contains timestamped text-state snapshots (`before_text`, `current_text`) rather than explicit key press and release events, so we should call these features **keyboard text-state dynamics**, not exact keystroke dynamics.

More creative candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `keyboard_median_inter_event_interval_ms` | After deduplication and timestamp sorting, median milliseconds between consecutive keyboard observations in the same app/session. | Typical typing rhythm or event tempo. | Not true key hold/flight time; duplicates and long idle gaps must be excluded. |
| `keyboard_inter_event_interval_iqr_ms` | IQR of consecutive inter-event intervals after filtering implausible duplicates and long gaps. | Variability of typing rhythm. | High variability can reflect pauses, app behavior, interruptions, or logging artifacts. |
| `keyboard_long_pause_count_2s` | Count gaps greater than 2 seconds between consecutive keyboard observations inside active typing bursts. | Pausing during typing. | Pauses may reflect thinking, interruption, reading, or app behavior; not diagnostic. |
| `keyboard_typing_burst_count` | Count typing bursts separated by gaps greater than a fixed threshold, for example 30 seconds. | Number of distinct typing episodes. | Threshold must be documented and sensitivity-tested. |
| `keyboard_median_burst_duration_ms` | Median duration from first to last observation in each typing burst. | Typical length of active typing episodes. | Depends on logging density and burst threshold. |
| `keyboard_median_word_completion_time_ms` | Infer word boundaries from transitions ending in a space; estimate time from first character after a boundary to the next boundary. | Approximate time to complete a word. | Requires raw text-state parsing during calculation; output must be aggregate only and not save words. Hebrew/English/mixed text and emojis complicate parsing. |
| `keyboard_median_between_word_pause_ms` | Time from a word boundary/space to the first subsequent non-space text-state change. | Approximate pause between words. | Sensitive to editing, punctuation, language, and app-specific keyboard behavior. |
| `keyboard_deletion_event_count` | Count transitions where text length decreases. | Backspace/deletion activity. | Can reflect editing, typo correction, or field reset; not necessarily error rate. |
| `keyboard_correction_event_ratio` | Deletion/edit events divided by distinct keyboard observations. | Relative correction burden. | Requires exact transition rules; high values may reflect editing style or app behavior. |
| `keyboard_text_growth_event_count` | Count transitions where text length increases. | Text-entry progress observations. | Not exact character count because one event can add multiple characters or an emoji. |
| `keyboard_space_boundary_event_count` | Count transitions where current text newly ends with a space. | Approximate word-boundary count. | Space is only a proxy for words and may not work equally across languages/apps. |

Recommended short list to consider first:

1. `keyboard_distinct_observation_count`
2. `keyboard_median_inter_event_interval_ms`
3. `keyboard_long_pause_count_2s`
4. `keyboard_typing_burst_count`
5. `keyboard_median_word_completion_time_ms`
6. `keyboard_deletion_event_count`
7. `keyboard_correction_event_ratio`

These are more clinically interesting than raw row count because they describe tempo, pausing, episode structure, and correction behavior.

## Privacy Notes

- Raw `before_text` and `current_text` should not be used as model-facing phenotype features.
- Raw text-state values may be visible only for authorized manual inspection.
- Final phenotype outputs should use aggregate keyboard activity counts and app-context breadth only.

## Current Feature-Finding Result

Phase 2A found a protocol-valid `keyboard` review window using the current T1-ranked feature-finding protocol.

Selected review window:

- Subject_ID_D: `041`
- Subject_ID_N: `15`
- global_T1: `119.4`
- T1 date: `2025-01-08`
- device_id: `d74f7acf-f82f-491d-90b9-d7321e6d4bcf`
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-09 00:00:00+0200`
- window_end_local: `2025-01-10 00:00:00+0200`
- rows in selected window: `1832`
- sampled raw rows: `20`
- distinct sampled observations: `10`

Output files:

- `output/analysis_candidates/phase2_feature_review/keyboard/keyboard_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/keyboard/keyboard_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/keyboard/keyboard_sample_rows_distinct_observations.csv`
- `output/analysis_candidates/phase2_feature_review/keyboard/keyboard_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/keyboard/keyboard_phase2a_t1_ranked_coverage_scan.csv`

Important interpretation rules:

- Keyboard rows are not exact keystrokes.
- Duplicate rows must be considered before interpreting row counts.
- Advanced timing features should be calculated only after deduplication.
- Raw text should be used only transiently for deriving aggregate timing/correction features and should not be saved in model-facing outputs.
- Missing keyboard data is not zero typing.
- This is exploratory feature review only and not diagnostic.

## Literature Notes

- Keystroke dynamics studies generally model typing rhythm using timing features such as inter-key timing, variability, and error/correction behavior.
- DeepMood modeled mobile phone typing dynamics for mood prediction using keyboard metadata and avoided collecting ordinary character content, except special keys such as backspace and space.
- Smartphone digital phenotyping literature supports using passive phone interaction metadata, but keyboard-derived features require extra privacy care and cautious interpretation.

Sources reviewed:

- DeepMood: Modeling Mobile Phone Typing Dynamics for Mood Detection: https://arxiv.org/abs/1803.08986
- A Survey of Biometric Keystroke Dynamics: Approaches, Security and Challenges: https://arxiv.org/abs/0910.0817
- Digital phenotyping overview: https://en.wikipedia.org/wiki/Digital_phenotyping
