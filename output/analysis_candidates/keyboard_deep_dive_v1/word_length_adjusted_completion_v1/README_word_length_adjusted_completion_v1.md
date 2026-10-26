# Word-Length-Adjusted Completion Variability — v1

This additive run audits the existing observable word-completion proxy using exact snapshot continuity and derives length-adjusted timing summaries. It does not alter prior Word Completion v1 files or train models.

## Extraction

Rows were read from the saved T1/T2 clinical windows. Password-state rows were excluded before text inspection. Rows were deduplicated using timestamp, device, before text, current text, package, and password status, then processed within device/package streams. A candidate began after an empty or delimiter-terminated state and ended when a later current state reached a delimiter. A candidate was `reliable_continuous` only when previous `current_text` equaled next `before_text` throughout, the state transitions were append-only, no gap exceeded 2 seconds, and a boundary-start was observed. Multi-character jumps were retained but counted separately; they are observable text increments, not individual keypresses. Gaps over 30 seconds reset a candidate and are excluded from interval continuity.

The extracted word length is the Unicode-normalized character count of the completed observable token. It is not a count of keystrokes and does not prove that every character was observed. Punctuation, paste, predictive text, autocorrect and unobserved intermediate states remain possible.

Features include raw duration, duration per character (descriptive only), fixed length groups (2–3, 4–5, 6–8, 9+), within-group median/IQR/MAD/CV, an equal-group median of IQRs, and within-window quadratic duration-on-length residual variability when at least 20 reliable completions are available. All outputs are aggregate numeric values.

## Feasibility result

The run processed 141 windows: 81 T1 and 60 T2. It identified 55,228 candidate completions in T1 and 63,812 in T2. Reliable continuous completions were 30,800 in T1 (55.8% of candidates) and 4,264 in T2 (6.7%). Median reliable completions per window were 49 at T1 and 0 at T2. Only 3 paired patients had at least 100 reliable completions in both windows, the prespecified gate for a focused longitudinal cognitive screen. The gate therefore failed, and no Global-change association was run. This is a feasibility failure, not evidence of no cognitive relationship.

The low T2 yield and very high continuity-break/multi-character-jump counts indicate that this strict reconstruction is strongly affected by snapshot sequencing and recording structure. Results should not be presented as true word-typing speed. The full window, daily, quality and patient-level tables retain coverage denominators and missingness.

## Files

- `word_length_window_features_20261021_v1.csv`
- `word_length_daily_features_20261021_v1.csv`
- `word_length_quality_summary_20261021_v1.csv`
- `word_length_patient_table_20261021_v1.csv`
- `feature_dictionary_20261021_v1.csv`
- `feature_dictionary_word_length_extension_20261021_v1.csv` (complete timing-family definitions)
- `supervisor_results_20261021_v1.csv` (gate status; no cognitive screen)
- `comparison_existing_word_features_20261021_v1.csv`

No raw text, completed words, word lists, hashes, excerpts or embeddings were written. The next defensible step is labeled state-transition validation or a less strict, explicitly proxy-level reconstruction; do not interpret the current T2−T1 lexical/timing changes as validated behavioral measures.
