"""Build the initial non-destructive supplemental modality QC manifest."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from supplemental_modalities.config import (
    ACCELEROMETER_DEVICE_QC,
    ACCELEROMETER_PATIENT_QC,
    MODALITIES,
    OUTPUT_ROOT,
    SPANS,
    TABLE_INVENTORY,
)


def build_inventory() -> pd.DataFrame:
    inventory = pd.read_csv(TABLE_INVENTORY, dtype=str)
    selected = inventory[inventory["table_name"].isin([item["table_name"] for item in MODALITIES.values()])].copy()
    selected["supplemental_modality"] = selected["table_name"].map(
        {item["table_name"]: modality for modality, item in MODALITIES.items()}
    )
    selected["json_key_expected"] = selected["supplemental_modality"].map(
        {modality: item["json_key"] for modality, item in MODALITIES.items()}
    )
    selected["analysis_role"] = selected["supplemental_modality"].map(
        {modality: item["role"] for modality, item in MODALITIES.items()}
    )
    selected["extraction_policy"] = selected["supplemental_modality"].map(
        {modality: item["raw_scale"] for modality, item in MODALITIES.items()}
    )
    return selected


def build_accelerometer_snapshot() -> tuple[pd.DataFrame, pd.DataFrame]:
    patient_qc = pd.read_csv(ACCELEROMETER_PATIENT_QC, dtype=str)
    device_qc = pd.read_csv(ACCELEROMETER_DEVICE_QC, dtype=str)
    return patient_qc, device_qc


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    inventory = build_inventory()
    patient_qc, device_qc = build_accelerometer_snapshot()
    inventory.to_csv(OUTPUT_ROOT / "supplemental_modality_inventory.csv", index=False)
    patient_qc.to_csv(OUTPUT_ROOT / "accelerometer_anchor_patient_qc_snapshot.csv", index=False)
    device_qc.to_csv(OUTPUT_ROOT / "accelerometer_anchor_device_qc_snapshot.csv", index=False)
    pd.DataFrame(
        [
            {"span_key": key, "span_description": description}
            for key, description in SPANS.items()
        ]
    ).to_csv(OUTPUT_ROOT / "supplemental_span_manifest.csv", index=False)
    (OUTPUT_ROOT / "README_supplemental_qc_manifest.md").write_text(
        "# Supplemental Modality QC Manifest\n\n"
        "This is the initial planning and QC snapshot for direct proximity, light, and raw accelerometer work. "
        "It does not query or copy raw high-frequency accelerometer rows. The accelerometer anchor files are inherited "
        "from the existing metadata QC framework and are retained here as a read-only snapshot for later bounded extraction.\n\n"
        f"Inventory rows: {len(inventory)}. Accelerometer patient QC rows: {len(patient_qc)}. "
        f"Patients with a metadata anchor: {int(patient_qc.get('has_sensor_accelerometer_metadata_after_T1', pd.Series(dtype=str)).astype(str).str.lower().isin({'true', '1', 'yes'}).sum())}.\n",
        encoding="utf-8",
    )
    print(f"inventory_rows: {len(inventory)}")
    print(f"accelerometer_patient_qc_rows: {len(patient_qc)}")
    print(f"accelerometer_device_qc_rows: {len(device_qc)}")


if __name__ == "__main__":
    main()
