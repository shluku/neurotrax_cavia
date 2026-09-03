# phase12_midpoint_t2_decline

This exploratory cohort uses the patient-level interval split at the midpoint between T1 and T2. The T2 interval is half-open: `[start, end)`. All valid mapped devices are pooled for each patient and table. The light, proximity, and accelerometer work remains outside this phase.

For Phase 11 patients without a valid T2, the midpoint fallback is T1 plus the current paired-cohort median half-interval (123.000 days, approximately 123 days). The status CSV records exact versus fallback midpoint provenance and interval duration.
