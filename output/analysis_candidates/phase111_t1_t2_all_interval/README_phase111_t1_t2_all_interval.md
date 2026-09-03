# Phase 111 Full T1-to-T2 Interval Baseline Ridge

Phase 111 uses all active-feature data in `[T1, T2)` when T2 exists. Patients without valid T2 use `[T1, T1+123 days)`. The target is the mean of observed T1 and T2 scores, or T1 alone when T2 is unavailable; a domain without a valid T1 score is excluded from that domain model. The standard median of two observations is identical to this mean.

This first run uses only cross-validated Ridge versus the fold-local mean baseline. Light, barometer, Bluetooth-proximity, and sensor-linear-accelerometer features remain deferred.
