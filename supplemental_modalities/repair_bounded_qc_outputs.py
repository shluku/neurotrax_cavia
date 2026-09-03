"""Repair the first mixed-schema bounded QC output into modality files.

The first runner version appended modality-specific columns to one CSV. This
repair is local-only: it reads those completed rows, separates them by the
modality field, and writes stable per-modality files for downstream use.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from .config import OUTPUT_ROOT


SOURCE = OUTPUT_ROOT / "bounded_qc_v2"
TARGET = OUTPUT_ROOT / "bounded_qc_v3"

DIRECT_PATIENT_COLUMNS = [
    "Subject_ID_D", "Subject_ID_N", "global_T1", "T1_date_iso", "modality", "table_name",
    "device_ids_available", "n_devices_available", "protocol_variant", "status", "window_rule",
    "window_start_ms", "window_end_ms", "window_start_local", "window_end_local", "device_ids_used",
    "n_devices_with_rows", "rows_in_selected_window", "sample_rows_requested", "sample_rows_returned",
    "sample_json_parse_errors", "sample_key_present_rows", "sample_numeric_valid_rows", "sample_numeric_min",
    "sample_numeric_median", "sample_numeric_max", "sample_median_interval_ms", "sample_duplicate_timestamp_rows",
]
ACCELEROMETER_PATIENT_COLUMNS = [
    "Subject_ID_D", "Subject_ID_N", "global_T1", "T1_date_iso", "modality", "table_name",
    "protocol_variant", "status", "anchor_source", "device_id", "window_rule", "window_start_ms",
    "window_end_ms", "window_start_local", "window_end_local", "rows_in_selected_window", "first_ts", "last_ts",
    "sample_rows_requested", "sample_rows_returned", "sample_json_parse_errors", "sample_key_present_rows",
    "sample_numeric_valid_rows", "sample_numeric_min", "sample_numeric_median", "sample_numeric_max",
    "sample_median_interval_ms", "sample_duplicate_timestamp_rows", "sample_double_values_0_valid_rows",
    "sample_double_values_1_valid_rows", "sample_double_values_2_valid_rows",
]

DIRECT_DEVICE_COLUMNS = [
    "Subject_ID_D", "Subject_ID_N", "global_T1", "T1_date_iso", "modality", "table_name",
    "device_ids_available", "n_devices_available", "protocol_variant", "device_id", "window_rule",
    "window_start_ms", "window_end_ms", "primary_n_rows", "fallback_first_ts", "selected_n_rows",
    "selected_first_ts", "selected_last_ts",
]
ACCELEROMETER_DEVICE_COLUMNS = [
    "Subject_ID_D", "Subject_ID_N", "global_T1", "T1_date_iso", "modality", "table_name",
    "protocol_variant", "device_id", "window_rule", "window_start_ms", "window_end_ms", "selected_n_rows",
    "selected_first_ts", "selected_last_ts",
]


def read_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def write_modality(rows: list[dict[str, str]], modality: str, suffix: str, columns: list[str]) -> None:
    if not rows:
        return
    frame = pd.DataFrame(rows).reindex(columns=columns)
    frame.to_csv(TARGET / f"{modality}_{suffix}.csv", index=False)


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    patient_rows = read_rows(SOURCE / "supplemental_bounded_patient_qc.csv")
    device_rows = read_rows(SOURCE / "supplemental_bounded_device_qc.csv")
    patient_by_modality: dict[str, list[dict[str, str]]] = {"proximity": [], "light": [], "accelerometer": []}
    device_by_modality: dict[str, list[dict[str, str]]] = {"proximity": [], "light": [], "accelerometer": []}

    for row in patient_rows[1:]:
        if len(row) < 5 or row[4] not in patient_by_modality:
            continue
        modality = row[4]
        columns = ACCELEROMETER_PATIENT_COLUMNS if modality == "accelerometer" else DIRECT_PATIENT_COLUMNS
        if modality == "accelerometer" and len(row) == 8:
            # No-anchor rows were emitted by the first runner before the
            # optional anchor fields were populated.
            row = row + [""] * (len(columns) - len(row))
        if len(row) != len(columns):
            raise ValueError(f"Unexpected patient row width for {modality}: {len(row)} != {len(columns)}")
        patient_by_modality[modality].append(dict(zip(columns, row)))

    for row in device_rows[1:]:
        if len(row) < 5 or row[4] not in device_by_modality:
            continue
        modality = row[4]
        columns = ACCELEROMETER_DEVICE_COLUMNS if modality == "accelerometer" else DIRECT_DEVICE_COLUMNS
        if len(row) != len(columns):
            raise ValueError(f"Unexpected device row width for {modality}: {len(row)} != {len(columns)}")
        device_by_modality[modality].append(dict(zip(columns, row)))

    summary_rows: list[dict[str, object]] = []
    for modality in patient_by_modality:
        patient_frame = pd.DataFrame(patient_by_modality[modality])
        write_modality(patient_by_modality[modality], modality, "patient_qc", list(patient_frame.columns))
        device_frame = pd.DataFrame(device_by_modality[modality])
        write_modality(device_by_modality[modality], modality, "device_qc", list(device_frame.columns))
        status_counts = patient_frame["status"].value_counts().to_dict() if not patient_frame.empty else {}
        summary_rows.append(
            {
                "modality": modality,
                "patient_rows": len(patient_frame),
                "device_rows": len(device_frame),
                "calculated_patients": int(patient_frame["status"].eq("calculated").sum()) if not patient_frame.empty else 0,
                "total_rows_in_selected_windows": pd.to_numeric(
                    patient_frame.get("rows_in_selected_window", pd.Series(dtype=float)), errors="coerce"
                ).sum(),
                "status_counts_json": json.dumps(status_counts, sort_keys=True),
            }
        )

    pd.DataFrame(summary_rows).to_csv(TARGET / "supplemental_bounded_modality_summary.csv", index=False)
    source_checkpoint = SOURCE / "supplemental_bounded_qc_checkpoint.jsonl"
    target_checkpoint = TARGET / "supplemental_bounded_qc_checkpoint.jsonl"
    target_checkpoint.write_text(source_checkpoint.read_text(encoding="utf-8"), encoding="utf-8")
    (TARGET / "README_supplemental_bounded_qc.md").write_text(
        (SOURCE / "README_supplemental_bounded_qc.md").read_text(encoding="utf-8")
        + "\nRepair note: this v3 directory contains one patient and one device CSV per modality. "
        "The original mixed-schema v2 files are retained as an audit artifact.\n",
        encoding="utf-8",
    )
    print(pd.DataFrame(summary_rows).to_string(index=False))


if __name__ == "__main__":
    main()
