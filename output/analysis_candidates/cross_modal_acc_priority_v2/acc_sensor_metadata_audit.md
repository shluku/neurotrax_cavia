# ACC Sensor Metadata Audit (Phase 3B prerequisite)

**Date:** 2026-10-22  
**Scope:** bounded, read-only SensorDB metadata inspection and comparison with the two devices used in ACC Phase 3A. No raw tables were modified and no cognition/model analyses were run.

## Main conclusion

SensorDB does contain accelerometer-level hardware metadata, but it does **not** contain a recorded sampling-frequency field or a configuration history that explains the approximately 5 Hz versus 125 Hz observed difference. The two devices use the same raw table (`accelerometer`), the same JSON vector keys (`double_values_0/1/2`), and the same Android sensor type code (`1`), but they are different physical sensor implementations. Their metadata reports different minimum-delay capabilities (2,000 and 2,500 microseconds), neither of which predicts the observed cadence. Therefore, the observed rate difference is most consistent with collection configuration, duty cycling/gating, transport/storage behavior, or timestamp/event availability; it cannot be attributed to the nominal hardware fields alone.

The measurements are comparable at the **schema and modality** level (raw acceleration vectors from the general accelerometer stream), but not automatically equivalent at the **sampling-rate/resolution/hardware** level. ACC motion and jerk features should therefore be rate-aware and require minimum effective sampling and gap rules; comparisons across these devices should not pool unqualified raw jerk summaries.

## Tables and schemas confirmed

The `information_schema` search returned these relevant base tables:

- Raw streams: `accelerometer`, `linear_accelerometer`, `gyroscope`, `gravity`, `rotation`.
- Metadata streams: `sensor_accelerometer`, `sensor_linear_accelerometer`, `sensor_gyroscope`, `sensor_gravity`, `sensor_rotation` (plus other sensor metadata tables).

Each inspected table has only four physical columns: `_id`, `timestamp` (`double`), `device_id` (`varchar(128)`), and `data` (`json`). Thus sensor identity and capability fields are JSON attributes rather than relational columns. The raw `accelerometer` rows contain timestamp, device ID, and vector values in `data`; Phase 3A parsed `double_values_0`, `double_values_1`, and `double_values_2`.

A bounded JSON-key inspection of `sensor_accelerometer` confirmed these fields:

- `sensor_name`, `sensor_type`, `sensor_vendor`, `sensor_version`
- `double_sensor_power_ma`
- `double_sensor_resolution`
- `double_sensor_maximum_range`
- `double_sensor_minimum_delay`
- metadata `timestamp` and `device_id`

No `frequency`, `sampling_frequency`, `sampling_period`, requested-rate, software-version, units, or configuration-ID field was present in the inspected schema/JSON. The metadata table is not a raw movement stream; repeated rows at one timestamp are metadata records.

## Field interpretation

- `double_sensor_minimum_delay` is stored as a numeric delay in microseconds in the project’s existing hardware-timeline code. It is a nominal sensor capability/context field, not the timestamp-derived rate of the raw stream and not proof that the app requested that rate.
- Resolution, maximum range, and power are hardware-context values. Their units are not declared in the JSON. The range values are numerically consistent with Android-style acceleration ranges, but this audit does not add an undocumented unit conversion.
- `sensor_type=1` is the same code for both devices. The database does not separately label hardware versus software sensor implementation beyond the sensor name/vendor fields.
- No time-varying configuration was observed for either Phase 3A device: each had one distinct metadata configuration at one metadata timestamp (36 and 167 repeated metadata rows respectively). This does not prove that the device or app configuration never changed outside the observed metadata record.
- No `sensor_linear_accelerometer` metadata rows were found for either Phase 3A device in the bounded lookup. The Phase 3A signal is therefore the general accelerometer stream, which may include gravity; its segment magnitudes were near 9.9–10.0, consistent with that interpretation, but units are not explicitly declared.

## Device comparison

See [`device_level_comparison.csv`](device_level_comparison.csv). Values below come from the saved Phase 3A segment output plus the bounded metadata queries; the device labels are anonymized consistently with Phase 3A.

| Device | Phase 3A patient | Observed cadence | Metadata sensor | Vendor/version | Minimum delay | Resolution | Maximum range | Metadata configuration changes observed |
|---|---:|---:|---|---|---:|---:|---:|---|
| `dev_d74f7a` | 041 | median 200 ms (~5 Hz) | accelerometer-lsm6dsm | st / 1 | 2,000 µs (~500 Hz capability) | 0.0000095768 | 78.4532 | none; one configuration timestamp |
| `dev_72e21d` | 039 | median 8 ms (~125 Hz) | BMI120 Accelerometer | BOSCH / 2062701 | 2,500 µs (~400 Hz capability) | 0.00239563 | 156.9064 | none; one configuration timestamp |

The high-rate device still has occasional longer intervals (saved Phase 3A median p95 interval 63 ms), while the low-rate device’s median p95 interval was 204 ms. This reinforces that actual cadence must be computed from timestamps with duplicate handling and gap QC.

## What the metadata can and cannot explain

The hardware identities, resolution, and range differ substantially, so they are potential measurement modifiers. However, the minimum-delay values imply capabilities much faster than both observed streams and are not ordered in the same way as observed rates (the 2,000-µs device was the slower observed stream). Consequently, the metadata does **not** explain the 5-versus-125-Hz difference by itself. The remaining explanations include app/requested sampling configuration, sensor listener scheduling, collection duty cycling, database ingestion/retention, or timestamp/duplicate behavior. The current tables do not store enough information to discriminate these mechanisms.

The two raw streams are comparable for broad acceleration magnitude and low-frequency movement features only after explicit rate and gap standardization. Jerk is especially sensitive to the 8-ms versus 200-ms cadence and should be calculated only within contiguous segments at a prespecified minimum effective rate, with device/hardware configuration retained as a QC covariate or stratification variable.

## Bounded query and reproducibility record

1. Queried `information_schema.tables` and `information_schema.columns` for names containing sensor/accelerometer/acc/sampling/frequency/accuracy/device.
2. Inspected JSON keys and up to five metadata rows per Phase 3A device in `sensor_accelerometer`, `sensor_linear_accelerometer`, `sensor_gravity`, and `sensor_gyroscope`.
3. Grouped `sensor_accelerometer` metadata by sensor identity and capability fields for each device to check configuration changes.
4. Reused the saved Phase 3A timestamp-derived segment metrics; no broad raw-ACC scan was performed.

All queries were read-only and bounded. No credentials, raw text, or raw sensor payloads were written to the deliverables.

## Recommended Phase 3B gate

Before cohort-scale ACC/jerk analysis, retain `sensor_name`, vendor, version, resolution, maximum range, minimum delay, device ID, and observed cadence/gap metrics as QC fields. Define separate eligibility for low-rate and high-rate streams; do not treat nominal minimum delay as the sampling rate. First validate a small set of same-device contiguous segments across days, then compare motion features within rate-homogeneous strata or after a documented resampling/filtering procedure.
