# Phase 11 direct supplemental extraction

This output uses the actual midpoint interval for endpoint `t1`. The interval is half-open `[start, end)` and is patient-specific when T2 is available. Phase 11 is `T1 -> midpoint`; Phase 12 is `midpoint -> T2`.

For Phase 11 patients without a valid T2, midpoint fallback is T1 plus the cohort median half-interval (123.000 days). All valid mapped devices are pooled, excluding the project-wide excluded patient 001.

Proximity and light are queried in 6-hour multi-device chunks. Raw rows are not written to outputs. The feature table is an exploratory supplemental extraction and is not a model result.
