# Phase 1 Descriptive Profiles

## Executive summary
- Descriptive profiling only from validated merged Phase 1 table.
- No SQL queried; no new feature extraction.
- Baseline-usable subjects: 8
- Change-usable subjects: 2
- Change interpretation is limited to subjects 024 and 077 and remains exploratory.

## Data used
- phase1_digital_phenotype_wide.csv
- phase1_subject_usability_summary.csv
- top10_global_decline.csv
- README_phase1_digital_phenotype.md

## Feature families included
- screen
- applications_foreground
- keyboard
- touch
- plugin_google_activity_recognition
- aware_log (data quality only)

## Main descriptive patterns
- Baseline profile available for 8/10 subjects.
- Early-vs-late change interpretable only for a small subset (024, 077).
- Several features have missing late windows; those deltas remain missing by design.

## Subject-level summary
- baseline subjects: ['001', '024', '030', '062', '077', '087', '093', '095']
- change subjects: ['024', '077']
- insufficient phase1 data: ['044', '074']

## Early-vs-late summary for 024 and 077
- Included in phase1_change_profile_summary_024_077.csv with per-feature interpretability notes.

## Suggested columns missing from current merged table
- screen_early_night_event_count
- app_early_unique_foreground_apps
- app_early_app_use_diversity

## Limitations
- n=10 only
- baseline usable n=8
- change usable n=2
- exploratory only
- missing data is not zero activity
- no confirmatory statistics
- aware_log is data quality only
- phase 1 does not include GPS/high-frequency motion/context-social tables yet