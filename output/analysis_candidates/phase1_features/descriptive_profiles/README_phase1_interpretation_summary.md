# Phase 1 Interpretation Summary

## Executive summary
- Top-decline subjects analyzed: 10
- Baseline-usable subjects: 8 (001, 024, 030, 062, 077, 087, 093, 095)
- Change-usable subjects: 2 (024, 077)
- Phase 1 supports descriptive baseline profiling for most subjects, and limited early-vs-late change review for 024 and 077.

## What Phase 1 currently supports
- Descriptive baseline digital phenotype across core feature families.
- Relative ranking (low/medium/high) within baseline-usable subjects.
- Exploratory change summaries for subjects with both windows.

## What Phase 1 does not support yet
- Confirmatory inference, hypothesis testing, or causal claims.
- Robust change modeling beyond the 2 subjects with both windows.
- Context/social augmentation from optional tables (Phase 1C not yet integrated).

## Main descriptive findings
- Highest variability features (descriptive): aware_log_early_rows, touch_early_event_count, app_early_foreground_event_count, keyboard_early_event_count, screen_early_event_count.
- Baseline interaction patterns are heterogeneous across subjects.
- Late-window missingness substantially limits change interpretation for most subjects.

## Baseline phenotype summary (8 subjects)
- Subjects: 001, 024, 030, 062, 077, 087, 093, 095
- Core families used: screen, applications_foreground, keyboard, touch, activity_recognition.
- aware_log included only as data-quality support.

## Change summary (024 and 077)
- Change interpretation is possible only for available deltas with both windows.
- Missing deltas indicate non-interpretable feature change, not true zero change.

## Data quality and missingness interpretation
- Missing data is not zero activity.
- no_data windows remain NaN by design.
- aware_log rows help assess logging availability but are not behavior endpoints.

## Why no confirmatory statistics
- Sample size is small (n=10; baseline n=8; change n=2).
- Coverage heterogeneity and missingness preclude stable inferential conclusions.
- This phase is exploratory profiling only.

## Recommended next step
### Option A
Continue interpretation of the current Phase 1 core phenotype outputs and validate utility with domain stakeholders.

### Option B
Proceed to Phase 1C optional/context extraction: gsm, gsm_neighbor, telephony, messages.

### Recommendation
Option A is recommended now: continue interpreting current Phase 1 core phenotype outputs first. Option B (Phase 1C: gsm/gsm_neighbor/telephony/messages) should proceed only after confirming current summaries are useful and interpretable.