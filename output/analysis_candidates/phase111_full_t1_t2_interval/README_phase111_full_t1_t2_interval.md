# Phase 111 Full T1-to-T2 Interval Ridge Cohort

This exploratory cohort uses all available active-feature data in the half-open interval `[T1, T2)`. Patients without a valid T2 use `[T1, T1+123 days)` as the documented fallback window. Light, barometer, Bluetooth-proximity, and sensor-linear-accelerometer features are deferred.

The target is the mean of the observed T1 and T2 score when both exist, or the observed T1 score alone when T2 is unavailable. For two observations, the standard median is identical to this mean.
