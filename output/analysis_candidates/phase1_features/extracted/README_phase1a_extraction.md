# Phase 1A Extraction

This is first-pass Phase 1A extraction.

Included tables:
- screen
- applications_foreground
- aware_log (data-quality only)

Not included yet:
- keyboard, touch, activity recognition, gsm/gsm_neighbor, telephony, messages
- any high-frequency motion tables

Notes:
- Missing data is not interpreted as zero activity.
- Only early_window and late_window were extracted.
- Early-vs-late deltas are computed only when both windows have data.
- aware_log features are data-quality denominators, not direct phenotype measures.
