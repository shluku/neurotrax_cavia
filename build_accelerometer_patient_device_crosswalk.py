"""Build a patient-device crosswalk for accelerometer hardware auditing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).parent
MAP_PATH = ROOT / "output/label_device_map.csv"
COHORT_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
HARDWARE_DIR = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/device_hardware_timeline"
TIMELINE_PATH = HARDWARE_DIR / "accelerometer_device_hardware_timeline.csv"
SENSOR_DEVICE_PATH = HARDWARE_DIR / "sensor_device_summary_long.csv"
CONFIG_PATH = HARDWARE_DIR / "sensor_configuration_summary.csv"
OUT_DIR = HARDWARE_DIR
EXCLUDED_ACTIVE_COHORT_IDS = {"001"}
TIMEZONE = "Asia/Jerusalem"


def normalize_subject_id(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def clean(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "<na>"} else text


def strict_numeric_patient_mapping() -> pd.DataFrame:
    """Use exact three-digit labels before legacy or non-patient labels."""
    source = pd.read_csv(MAP_PATH, dtype=str).fillna("")
    rows: list[dict[str, str]] = []
    exact_labels_seen: set[str] = set()
    for _, record in source.iterrows():
        raw_label = clean(record.get("label"))
        subject_id = normalize_subject_id(raw_label)
        if not subject_id or subject_id.lower() in {"nan", "none"}:
            continue
        exact_three_digit = raw_label.isdigit() and len(raw_label) == 3
        if subject_id in exact_labels_seen and not exact_three_digit:
            continue
        device_ids = sorted({clean(value) for value in clean(record.get("device_ids")).split(";") if clean(value)})
        if exact_three_digit:
            exact_labels_seen.add(subject_id)
        if not raw_label.isdigit() or len(raw_label) > 3:
            continue
        for device_id in device_ids:
            rows.append(
                {
                    "patient_id": subject_id,
                    "device_id": device_id,
                    "mapping_source_label": raw_label,
                    "mapping_rule": "exact_three_digit_patient_label",
                }
            )
    mapping = pd.DataFrame(rows).drop_duplicates(["patient_id", "device_id"])
    if mapping["device_id"].duplicated().any():
        duplicated = mapping.loc[mapping["device_id"].duplicated(False), "device_id"].tolist()
        raise ValueError(f"device_ids_assigned_to_multiple_patients: {duplicated[:10]}")
    return mapping


def current_cohort_ids() -> set[str]:
    cohort = pd.read_csv(COHORT_PATH, dtype=str)
    return {
        normalize_subject_id(value)
        for value in cohort["Subject_ID_D"].dropna().tolist()
        if normalize_subject_id(value)
    } - EXCLUDED_ACTIVE_COHORT_IDS


def parse_timestamp(value: Any) -> pd.Timestamp | None:
    text = clean(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce", utc=True)
    return None if pd.isna(parsed) else parsed


def local_timestamp_text(value: pd.Timestamp | None) -> str:
    if value is None:
        return ""
    return value.tz_convert(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S%z")


def local_date_text(value: pd.Timestamp | None) -> str:
    if value is None:
        return ""
    return value.tz_convert(TIMEZONE).strftime("%Y-%m-%d")


def first_or_last(row: pd.Series, columns: list[str], mode: str) -> pd.Timestamp | None:
    values = [parse_timestamp(row.get(column)) for column in columns]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return min(values) if mode == "first" else max(values)


def configuration_text(row: pd.Series, source_table: str) -> str:
    suffix = source_table
    parts = [
        f"sensor={clean(row.get(f'sensor_names_{suffix}'))}",
        f"vendor={clean(row.get(f'sensor_vendors_{suffix}'))}",
        f"type={clean(row.get(f'sensor_types_{suffix}'))}",
        f"version={clean(row.get(f'sensor_versions_{suffix}'))}",
        f"nominal_delay_us={clean(row.get(f'sensor_minimum_delay_median_{suffix}'))}",
        f"resolution={clean(row.get(f'sensor_resolution_median_{suffix}'))}",
        f"range={clean(row.get(f'sensor_maximum_range_median_{suffix}'))}",
        f"power_ma={clean(row.get(f'sensor_power_ma_median_{suffix}'))}",
    ]
    if not any(part.split("=", 1)[1] for part in parts):
        return ""
    label = "general_accelerometer" if source_table == "sensor_accelerometer" else "linear_accelerometer"
    return f"{label} | " + " | ".join(part for part in parts if part.split("=", 1)[1])


def build_crosswalk() -> None:
    mapping = strict_numeric_patient_mapping()
    active_cohort = current_cohort_ids()
    timeline = pd.read_csv(TIMELINE_PATH, dtype=str).fillna("")
    timeline["device_id"] = timeline["device_id"].map(clean)
    timeline = timeline[timeline["device_id"].ne("")].drop_duplicates("device_id")

    sensor_devices = pd.read_csv(SENSOR_DEVICE_PATH, dtype=str).fillna("")
    sensor_devices["device_id"] = sensor_devices["device_id"].map(clean)
    sensor_devices = sensor_devices[sensor_devices["device_id"].ne("")].copy()
    sensor_devices["sensor_configuration"] = sensor_devices.apply(
        lambda row: (
            f"{('general_accelerometer' if row['source_table'] == 'sensor_accelerometer' else 'linear_accelerometer')} "
            f"| sensor={clean(row.get('sensor_names'))}"
            f" | vendor={clean(row.get('sensor_vendors'))}"
            f" | type={clean(row.get('sensor_types'))}"
            f" | version={clean(row.get('sensor_versions'))}"
            f" | nominal_delay_us={clean(row.get('sensor_minimum_delay_median'))}"
            f" | resolution={clean(row.get('sensor_resolution_median'))}"
            f" | range={clean(row.get('sensor_maximum_range_median'))}"
            f" | power_ma={clean(row.get('sensor_power_ma_median'))}"
        ),
        axis=1,
    )

    timeline_indexed = timeline.set_index("device_id")
    timeline_first_columns = [
        "metadata_first_seen_local_sensor_accelerometer",
        "metadata_first_seen_local_sensor_linear_accelerometer",
        "raw_linear_first_seen_local",
    ]
    timeline_last_columns = [
        "metadata_last_seen_local_sensor_accelerometer",
        "metadata_last_seen_local_sensor_linear_accelerometer",
        "raw_linear_last_seen_local",
    ]

    rows: list[dict[str, Any]] = []
    for _, mapped in mapping.iterrows():
        device_id = mapped["device_id"]
        observed = device_id in timeline_indexed.index
        timeline_row = timeline_indexed.loc[device_id] if observed else pd.Series(dtype=object)
        first = first_or_last(timeline_row, timeline_first_columns, "first") if observed else None
        last = first_or_last(timeline_row, timeline_last_columns, "last") if observed else None
        in_active = mapped["patient_id"] in active_cohort
        rows.append(
            {
                "patient_id": mapped["patient_id"],
                "device_id": device_id,
                "mapping_source_label": mapped["mapping_source_label"],
                "belongs_to_81_person_cohort": "yes" if in_active else "no",
                "cohort_membership": "active_81_person_cohort" if in_active else ("excluded_subject_001" if mapped["patient_id"] == "001" else "known_numeric_label_outside_81_cohort"),
                "device_link_status": "mapped_patient_device",
                "hardware_observation_status": "observed_in_local_hardware_timeline" if observed else "mapped_device_not_observed_in_local_hardware_timeline",
                "first_observed_local": local_timestamp_text(first),
                "last_observed_local": local_timestamp_text(last),
                "first_observed_date": local_date_text(first),
                "last_observed_date": local_date_text(last),
                "observation_sources": ";".join(
                    source
                    for source, available in [
                        ("sensor_accelerometer", bool(clean(timeline_row.get("metadata_first_seen_local_sensor_accelerometer")))),
                        ("sensor_linear_accelerometer", bool(clean(timeline_row.get("metadata_first_seen_local_sensor_linear_accelerometer")))),
                        ("raw_linear_accelerometer", bool(clean(timeline_row.get("raw_linear_first_seen_local")))),
                    ]
                    if available
                ),
                "general_accelerometer_configuration": configuration_text(timeline_row, "sensor_accelerometer") if observed else "",
                "linear_accelerometer_configuration": configuration_text(timeline_row, "sensor_linear_accelerometer") if observed else "",
                "raw_linear_accelerometer_rows": clean(timeline_row.get("raw_linear_accelerometer_rows")) if observed else "",
            }
        )

    mapped_device_ids = set(mapping["device_id"])
    for device_id in sorted(set(timeline["device_id"]) - mapped_device_ids):
        timeline_row = timeline_indexed.loc[device_id]
        first = first_or_last(timeline_row, timeline_first_columns, "first")
        last = first_or_last(timeline_row, timeline_last_columns, "last")
        rows.append(
            {
                "patient_id": "",
                "device_id": device_id,
                "mapping_source_label": "",
                "belongs_to_81_person_cohort": "no",
                "cohort_membership": "unmatched_device_id",
                "device_link_status": "unmatched_device_id_no_patient_mapping",
                "hardware_observation_status": "observed_in_local_hardware_timeline",
                "first_observed_local": local_timestamp_text(first),
                "last_observed_local": local_timestamp_text(last),
                "first_observed_date": local_date_text(first),
                "last_observed_date": local_date_text(last),
                "observation_sources": ";".join(
                    source
                    for source, available in [
                        ("sensor_accelerometer", bool(clean(timeline_row.get("metadata_first_seen_local_sensor_accelerometer")))),
                        ("sensor_linear_accelerometer", bool(clean(timeline_row.get("metadata_first_seen_local_sensor_linear_accelerometer")))),
                        ("raw_linear_accelerometer", bool(clean(timeline_row.get("raw_linear_first_seen_local")))),
                    ]
                    if available
                ),
                "general_accelerometer_configuration": configuration_text(timeline_row, "sensor_accelerometer"),
                "linear_accelerometer_configuration": configuration_text(timeline_row, "sensor_linear_accelerometer"),
                "raw_linear_accelerometer_rows": clean(timeline_row.get("raw_linear_accelerometer_rows")),
            }
        )

    crosswalk = pd.DataFrame(rows)
    device_counts = mapping.groupby("patient_id")["device_id"].nunique().to_dict()
    crosswalk["number_of_devices_for_patient"] = crosswalk["patient_id"].map(device_counts).fillna(0).astype(int)
    crosswalk = crosswalk.sort_values(["belongs_to_81_person_cohort", "patient_id", "device_id"], ascending=[False, True, True])
    crosswalk.to_csv(OUT_DIR / "patient_device_crosswalk.csv", index=False)

    patient_summary = pd.DataFrame({"patient_id": sorted(set(mapping["patient_id"]) | active_cohort)})
    patient_summary["belongs_to_81_person_cohort"] = patient_summary["patient_id"].isin(active_cohort).map({True: "yes", False: "no"})
    patient_summary["number_of_devices_for_patient"] = patient_summary["patient_id"].map(device_counts).fillna(0).astype(int)
    linked = crosswalk[crosswalk["patient_id"].ne("")].copy()
    patient_summary["observed_device_count_in_local_timeline"] = patient_summary["patient_id"].map(
        linked[linked["hardware_observation_status"].eq("observed_in_local_hardware_timeline")].groupby("patient_id")["device_id"].nunique()
    ).fillna(0).astype(int)
    patient_summary["mapped_device_not_observed_count"] = patient_summary["number_of_devices_for_patient"] - patient_summary["observed_device_count_in_local_timeline"]
    patient_summary["patient_device_link_status"] = patient_summary["number_of_devices_for_patient"].map(
        lambda count: "mapped_device_ids_available" if count else "no_mapped_device_id"
    )
    patient_summary.to_csv(OUT_DIR / "patient_device_summary.csv", index=False)

    configuration_crosswalk = sensor_devices.merge(mapping, on="device_id", how="left")
    configuration_crosswalk["belongs_to_81_person_cohort"] = configuration_crosswalk["patient_id"].isin(active_cohort).map({True: "yes", False: "no"})
    configuration_crosswalk["configuration_observation_status"] = configuration_crosswalk["patient_id"].notna().map({True: "mapped_to_patient", False: "unmatched_device_id"})
    configuration_crosswalk = configuration_crosswalk[
        [
            "patient_id",
            "device_id",
            "belongs_to_81_person_cohort",
            "configuration_observation_status",
            "source_table",
            "metadata_rows",
            "metadata_first_seen_local",
            "metadata_last_seen_local",
            "sensor_configuration",
        ]
    ].sort_values(["belongs_to_81_person_cohort", "patient_id", "device_id", "source_table"], ascending=[False, True, True, True])
    configuration_crosswalk.to_csv(OUT_DIR / "patient_device_configuration_crosswalk.csv", index=False)

    mapped_absent = set(mapping["device_id"]) - set(timeline["device_id"])
    timeline_unmatched = set(timeline["device_id"]) - mapped_device_ids
    unmatched = pd.DataFrame(
        sorted(
            [
                {
                    "device_id": device_id,
                    "unmatched_reason": "mapped_to_numeric_patient_but_absent_from_local_hardware_timeline",
                    "patient_id_from_label_map": mapping.loc[mapping["device_id"].eq(device_id), "patient_id"].iloc[0],
                }
                for device_id in mapped_absent
            ]
            + [
                {
                    "device_id": device_id,
                    "unmatched_reason": "present_in_local_hardware_timeline_without_numeric_patient_mapping",
                    "patient_id_from_label_map": "",
                }
                for device_id in timeline_unmatched
            ],
            key=lambda row: row["device_id"],
        )
    )
    unmatched.to_csv(OUT_DIR / "unmatched_device_ids.csv", index=False)

    configurations = pd.read_csv(CONFIG_PATH, dtype=str).fillna("")
    summary = pd.DataFrame(
        [
            {"metric": "active_81_person_cohort_patients", "value": len(active_cohort)},
            {"metric": "numeric_patient_labels_in_mapping", "value": mapping["patient_id"].nunique()},
            {"metric": "mapped_device_ids_in_numeric_patient_mapping", "value": mapping["device_id"].nunique()},
            {"metric": "mapped_device_ids_observed_in_local_hardware_timeline", "value": len(mapped_device_ids & set(timeline["device_id"]))},
            {"metric": "mapped_device_ids_absent_from_local_hardware_timeline", "value": len(mapped_absent)},
            {"metric": "unmatched_device_ids_in_local_hardware_timeline", "value": len(timeline_unmatched)},
            {"metric": "general_accelerometer_configurations", "value": int((configurations["source_table"] == "sensor_accelerometer").sum())},
            {"metric": "linear_accelerometer_configurations", "value": int((configurations["source_table"] == "sensor_linear_accelerometer").sum())},
            {"metric": "total_hardware_configurations", "value": len(configurations)},
            {"metric": "patients_with_one_device", "value": int((patient_summary["number_of_devices_for_patient"] == 1).sum())},
            {"metric": "patients_with_two_devices", "value": int((patient_summary["number_of_devices_for_patient"] == 2).sum())},
            {"metric": "patients_with_three_or_more_devices", "value": int((patient_summary["number_of_devices_for_patient"] >= 3).sum())},
        ]
    )
    summary.to_csv(OUT_DIR / "patient_device_crosswalk_summary.csv", index=False)

    readme = f"""# Patient-Device Crosswalk

This table links the existing study patient labels to accelerometer device IDs for hardware and data-collection auditing. It does not create a new behavioral feature or change any patient-level model.

## Mapping rule

- Source mapping: `output/label_device_map.csv`.
- Exact three-digit patient labels are preferred over legacy labels such as `1`, `2`, or `p001`.
- The active analysis cohort is the current cognitive candidate set with Subject `001` excluded: {len(active_cohort)} patients.
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
"""
    (OUT_DIR / "README_patient_device_crosswalk.md").write_text(readme, encoding="utf-8")
    print(f"active_cohort_patients={len(active_cohort)}")
    print(f"crosswalk_rows={len(crosswalk)}")
    print(f"patient_summary_rows={len(patient_summary)}")
    print(f"mapped_device_ids={mapping['device_id'].nunique()}")
    print(f"mapped_observed_device_ids={len(mapped_device_ids & set(timeline['device_id']))}")
    print(f"mapped_absent_device_ids={len(mapped_absent)}")
    print(f"unmatched_observed_device_ids={len(timeline_unmatched)}")
    print(f"configuration_rows={len(configurations)}")


if __name__ == "__main__":
    build_crosswalk()
