# Patient-Device Crosswalk

This table links the existing study patient labels to accelerometer device IDs for hardware and data-collection auditing. It does not create a new behavioral feature or change any patient-level model.

## Mapping rule

- Source mapping: `output/label_device_map.csv`.
- Exact three-digit patient labels are preferred over legacy labels such as `1`, `2`, or `p001`.
- The active analysis cohort is the current cognitive candidate set with Subject `001` excluded: 81 patients.
- The hardware inventory is the previously generated local-Parquet timeline. Device IDs in that inventory without a numeric patient mapping are retained as unmatched.

## Outputs

- `patient_device_crosswalk.csv`: one row per mapped patient-device pair plus one row for every unmatched observed device ID.
- `patient_device_summary.csv`: one row per numeric patient label with device counts and local-observation status.
- `patient_device_configuration_crosswalk.csv`: sensor configuration rows linked to mapped or unmatched device IDs.
- `unmatched_device_ids.csv`: mapped device IDs absent from the local hardware inventory and observed device IDs without a numeric patient mapping.
- `patient_device_crosswalk_summary.csv`: audit counts.

## Interpretation

The 65 configurations are not 65 patients or 65 phones. They are distinct combinations reported by the sensor metadata, separated into 52 general-accelerometer configurations and 13 linear-accelerometer configurations. A configuration combines sensor identity, vendor, type/version, and nominal hardware fields such as minimum delay, resolution, range, and power. Multiple configurations are expected because Android devices expose different sensor chips, firmware/driver versions, and vendor implementations; repeated metadata snapshots do not necessarily represent new devices.

The nominal minimum delay is a hardware/request-context value, not the observed sampling rate. Device IDs are app/device identifiers and are not automatically unique physical phones.

No SQL tables, source Parquet files, or existing patient-level cohorts were modified.
