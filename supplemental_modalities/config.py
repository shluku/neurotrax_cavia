from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "output/analysis_candidates/supplemental_modalities"
TABLE_INVENTORY = ROOT / "output/sql_catalog/table_inventory.csv"
ACCELEROMETER_PATIENT_QC = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_patient.csv"
ACCELEROMETER_DEVICE_QC = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_device_window.csv"

MODALITIES = {
    "proximity": {
        "table_name": "proximity",
        "json_key": "double_proximity",
        "role": "direct_proximity_sensor",
        "raw_scale": "large_but_bounded_chunking_required",
    },
    "light": {
        "table_name": "light",
        "json_key": "double_light_lux",
        "role": "direct_ambient_light_sensor",
        "raw_scale": "large_but_bounded_chunking_required",
    },
    "accelerometer": {
        "table_name": "accelerometer",
        "json_key": "double_values_0..2",
        "role": "raw_high_frequency_motion_sensor",
        "raw_scale": "very_large_metadata_anchored_only",
    },
}

SPANS = {
    "phase4_24h": "Phase 4 24-hour T1/T2 acquisition span",
    "phase7_10day": "Phase 7 availability-anchored 10-day T1/T2 span",
    "phase11_12_midpoint": "Phase 11/12 patient-specific midpoint interval",
    "phase111_full_interval": "Phase 111 full T1-to-T2 interval or 123-day fallback",
}
