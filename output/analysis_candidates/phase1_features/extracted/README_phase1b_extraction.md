# Phase 1B Extraction

First-pass Phase 1B extraction.

Included:
- keyboard (counts/timing only; no raw text fields)
- touch
- plugin_google_activity_recognition

Excluded in this phase:
- gsm/gsm_neighbor/telephony/messages
- screen_state-specific features
- any high-frequency motion tables

Rules:
- early and late windows only
- missing data is not zero activity
- delta/pct_change computed only when both windows are available
