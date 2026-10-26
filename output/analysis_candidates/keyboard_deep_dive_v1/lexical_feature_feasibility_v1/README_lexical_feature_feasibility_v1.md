# Privacy-Preserving Lexical Feature Feasibility — v1

This additive run tests whether timestamped text-state snapshots can support aggregate lexical-diversity features without storing words. Text and normalized tokens were held in volatile memory only; per-window type sets were discarded after numeric summaries.

## Reconstruction and privacy

Password-state rows were excluded before transition inspection. Snapshots were deduplicated and grouped by device and application. A token was counted only after a delimiter boundary and a reliable continuous append-only sequence in which each previous `current_text` matched the next `before_text`, with no >2-second interruption. Duplicate snapshots, continuity breaks, multi-character jumps, corrections and incomplete starts were quantified. Unicode NFKC normalization and case folding were used in memory. Language groups were reported only as aggregate counts (Latin, Hebrew, mixed, other). No words, vocabularies, hashes, text excerpts or embeddings were persisted or logged.

## Candidate measures

The output contains total reliable tokens, unique types, TTR, repetition rate, mean/median word length, length variability, MATTR-50, MATTR-100, MTLD (only with at least 100 tokens), language-group counts, daily summaries, and fixed 50-token subsampling variability. These measures quantify observed text production, not vocabulary knowledge. TTR and type counts remain strongly dependent on token quantity, language, application and recording coverage.

## Feasibility gate

Across 81 T1 and 60 T2 windows, 30,800 reliable tokens were reconstructed at T1 and 4,264 at T2. The weighted reliable fractions were 55.8% and 6.7%, respectively. Only 3 paired patients met the prespecified minimum of 100 reliable tokens in both windows. The feasibility gate failed, so no baseline-language or longitudinal cognitive screen was run. This is not a negative cognitive result; the data do not presently support a defensible paired lexical analysis.

The strong T1/T2 imbalance, continuity breaks and multi-character jumps make patient comparisons vulnerable to recording density, device/application composition and incomplete observation. Fixed-token subsampling and within-patient reliability cannot be meaningfully assessed for most paired windows until reconstruction coverage improves.

## Literature review

The accompanying table distinguishes language-sample evidence from passive smartphone typing. McCarthy and Jarvis validated MTLD as a length-robust lexical-diversity measure; Covington and McFall introduced MATTR to reduce ordinary TTR's length dependence. Vizer et al. combined touchscreen typing with lexical/NLP features for MCI classification, but their text-processing assumptions are stronger than this snapshot schema. Longitudinal smartphone keystroke studies in MS and recent passive-sensing abstracts support typing metadata as a possible cognitive marker, but they use true keystroke or app-derived timing rather than reconstructed text-state words. These sources motivate measurement choices, not claims about this cohort.

No cognitive association was run. The smallest next step is to validate the continuity algorithm on consented synthetic/state-transition cases and establish language/application comparability before considering an exploratory cognitive family.
