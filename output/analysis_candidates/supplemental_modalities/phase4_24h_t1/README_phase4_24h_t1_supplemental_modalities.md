# Supplemental Phase 4 24-hour T1 feature extraction

This is the first derived-feature stage for the supplemental modalities.

- Proximity and light use the Phase 4 primary day-after-T1 window, with the first available 24-hour span inside the T1 week as fallback.
- Accelerometer uses the existing `sensor_accelerometer` metadata-selected device and a 24-hour window from that anchor.
- Proximity/light are fetched in 15-minute chunks. Accelerometer is fetched in validated 5-minute signal-analysis chunks.
- Raw payloads are parsed in memory and discarded. Only patient-level features and coverage/status outputs are written.
- Proximity near-state is a provisional engineering threshold (`double_proximity <= 0.5`) based on the observed 0/maximum-range pattern; it is not a clinical label.
- Light median and IQR use a deterministic bounded reservoir (maximum 100,000 valid values per patient); counts, dark fraction, and nighttime mean use all valid SQL-projected lux rows.
- Missingness remains missing; it is never filled with zero.

This output is additive and is not yet merged into Phase 4 models.
