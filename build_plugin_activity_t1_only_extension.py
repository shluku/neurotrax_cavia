from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import build_plugin_activity_movement_dictionary as base


ROOT = Path(__file__).parent
OUT_DIR = ROOT / "output/analysis_candidates/plugin_activity_movement_dictionary/t1_only_extension"
EVENTS_PATH = OUT_DIR / "plugin_activity_t1_only_events.csv"
MINUTES_PATH = OUT_DIR / "plugin_activity_t1_only_minutes.csv"
DEVICE_DAYS_PATH = OUT_DIR / "plugin_activity_t1_only_device_day_summary.csv"
PATIENT_DAYS_PATH = OUT_DIR / "plugin_activity_t1_only_patient_day_summary.csv"
PATIENT_SUMMARY_PATH = OUT_DIR / "plugin_activity_t1_only_patient_summary.csv"
STATUS_PATH = OUT_DIR / "plugin_activity_t1_only_status.csv"
SUMMARY_PATH = OUT_DIR / "plugin_activity_t1_only_summary.csv"
CHECKPOINT_PATH = OUT_DIR / "plugin_activity_t1_only_checkpoint.json"
README_PATH = OUT_DIR / "README_plugin_activity_t1_only_extension.md"
STAGING_DIR = OUT_DIR / "staging"

STATUS_FIELDS = base.STATUS_FIELDS + ["window_rule"]


def configure_base_output_paths() -> None:
    """Reuse the tested event/minute processor with isolated extension outputs."""
    base.OUT_DIR = OUT_DIR
    base.EVENTS_PATH = EVENTS_PATH
    base.MINUTES_PATH = MINUTES_PATH
    base.DEVICE_DAYS_PATH = DEVICE_DAYS_PATH
    base.PATIENT_DAYS_PATH = PATIENT_DAYS_PATH
    base.PATIENT_SUMMARY_PATH = PATIENT_SUMMARY_PATH
    base.STATUS_PATH = STATUS_PATH
    base.COHORT_SUMMARY_PATH = SUMMARY_PATH
    base.CHECKPOINT_PATH = CHECKPOINT_PATH
    base.README_PATH = README_PATH
    base.STAGING_DIR = STAGING_DIR


def latest_plugin_timestamp(conn: Any) -> int:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT MAX(timestamp) FROM `plugin_google_activity_recognition`"
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
    value = base.timestamp_ms(row[0] if row else None)
    if value is None:
        raise RuntimeError("The plugin table has no usable timestamp")
    return value


def append_status(row: dict[str, Any]) -> None:
    base.append_rows(STATUS_PATH, STATUS_FIELDS, [row])


def rebuild_patient_summary(
    patients: pd.DataFrame,
    device_map: dict[str, list[str]],
    endpoint_local: str,
) -> None:
    status = pd.read_csv(STATUS_PATH, dtype=str) if STATUS_PATH.exists() else pd.DataFrame()
    patient_days = pd.read_csv(PATIENT_DAYS_PATH, dtype=str) if PATIENT_DAYS_PATH.exists() else pd.DataFrame()
    if status.empty:
        return
    status["raw_rows_num"] = pd.to_numeric(status.get("raw_row_count", 0), errors="coerce").fillna(0)
    status["valid_rows_num"] = pd.to_numeric(status.get("valid_label_row_count", 0), errors="coerce").fillna(0)
    if not patient_days.empty:
        numeric_columns = [
            "plugin_event_count",
            "valid_label_event_count",
            "high_confidence_event_count",
            "active_land_event_count",
            "vehicle_event_count",
            "still_event_count",
            "orientation_change_event_count",
            "unknown_event_count",
            "other_event_count",
            "n_observed_minutes_across_devices",
        ]
        for column in numeric_columns:
            patient_days[column] = pd.to_numeric(patient_days.get(column, 0), errors="coerce").fillna(0)
        patient_days["mean_confidence_num"] = pd.to_numeric(patient_days.get("mean_confidence", 0), errors="coerce")
        patient_days["max_confidence_num"] = pd.to_numeric(patient_days.get("max_confidence", 0), errors="coerce")

    rows: list[dict[str, Any]] = []
    for _, patient in patients.iterrows():
        patient_id = patient["patient_id"]
        patient_status = status[status["patient_id"].astype(str).eq(patient_id)]
        completed = patient_status[patient_status["query_status"].astype(str).eq("completed")]
        event_devices = completed[completed["raw_rows_num"] > 0]
        day_rows = patient_days[patient_days["patient_id"].astype(str).eq(patient_id)] if not patient_days.empty else pd.DataFrame()
        row: dict[str, Any] = {
            "patient_id": patient_id,
            "t1_date": patient["t1_date"],
            "endpoint": "latest plugin table timestamp",
            "endpoint_time_local": endpoint_local,
            "mapped_device_count": len(device_map.get(patient_id, [])),
            "completed_device_interval_count": len(completed),
            "devices_with_events": len(event_devices),
            "devices_with_zero_events": int((completed["raw_rows_num"] == 0).sum()),
            "raw_plugin_event_count": int(completed["raw_rows_num"].sum()),
            "valid_label_event_count": int(completed["valid_rows_num"].sum()),
            "observed_local_day_count": len(day_rows),
            "first_event_time_local": day_rows["first_event_time_local"].min() if not day_rows.empty else "",
            "last_event_time_local": day_rows["last_event_time_local"].max() if not day_rows.empty else "",
            "observed_minutes_across_devices": int(day_rows["n_observed_minutes_across_devices"].sum()) if not day_rows.empty else 0,
        }
        for key in ("active_land", "vehicle", "still", "orientation_change", "unknown", "other"):
            column = f"{key}_event_count"
            row[column] = int(day_rows[column].sum()) if not day_rows.empty else 0
        if not day_rows.empty:
            event_total = day_rows["plugin_event_count"].sum()
            row["mean_confidence"] = (
                (day_rows["mean_confidence_num"].fillna(0) * day_rows["plugin_event_count"]).sum() / event_total
                if event_total
                else ""
            )
            row["max_confidence"] = day_rows["max_confidence_num"].max()
        else:
            row["mean_confidence"] = ""
            row["max_confidence"] = ""
        rows.append(row)
    pd.DataFrame(rows).sort_values("patient_id").to_csv(PATIENT_SUMMARY_PATH, index=False)


def rebuild_summary(patients: pd.DataFrame, device_map: dict[str, list[str]], endpoint_local: str) -> None:
    status = pd.read_csv(STATUS_PATH, dtype=str) if STATUS_PATH.exists() else pd.DataFrame()
    if status.empty:
        return
    status["raw_rows_num"] = pd.to_numeric(status.get("raw_row_count", 0), errors="coerce").fillna(0)
    summary = {
        "t1_only_patient_count": len(patients),
        "mapped_device_count": sum(len(device_map.get(pid, [])) for pid in patients["patient_id"]),
        "latest_plugin_timestamp_local": endpoint_local,
        "status_rows_written": len(status),
        "completed_device_intervals": int(status["query_status"].eq("completed").sum()),
        "devices_with_events": int(((status["query_status"] == "completed") & (status["raw_rows_num"] > 0)).sum()),
        "raw_event_rows_written": int(status["raw_rows_num"].sum()),
        "minute_rows_written": 0,
    }
    if MINUTES_PATH.exists():
        with MINUTES_PATH.open("r", encoding="utf-8") as handle:
            summary["minute_rows_written"] = max(sum(1 for _ in handle) - 1, 0)
    pd.DataFrame([summary]).to_csv(SUMMARY_PATH, index=False)


def write_readme(patients: pd.DataFrame, device_map: dict[str, list[str]], endpoint_local: str) -> None:
    status = pd.read_csv(STATUS_PATH, dtype=str) if STATUS_PATH.exists() else pd.DataFrame()
    status["raw_rows_num"] = pd.to_numeric(status.get("raw_row_count", 0), errors="coerce").fillna(0) if not status.empty else pd.Series(dtype=float)
    completed = int(status["query_status"].eq("completed").sum()) if not status.empty else 0
    raw_rows = int(status["raw_rows_num"].sum()) if not status.empty else 0
    events_patients = int(status.loc[status["raw_rows_num"] > 0, "patient_id"].nunique()) if not status.empty else 0
    text = f"""# T1-only Plugin Activity Extension

This companion dictionary maps plugin activity-recognition events for the active patients who do not have a recorded T2. It does not modify the original T1-to-T2 dictionary.

## Protocol

- Patients: active mapped cohort members with a valid T1 and no T2 date.
- Devices: only device IDs from `output/label_device_map.csv`.
- Window: local midnight at T1, inclusive, through the latest usable timestamp in `{base.TABLE_NAME}`, inclusive by timestamp value.
- Latest plugin timestamp in this run: `{endpoint_local}` local time.
- The endpoint is a data-availability boundary, not a clinical T2 visit and not an imputed T2 date.
- Missing plugin rows remain missing; they are not converted to stillness.
- Event labels and minute bins use the same canonical movement classes as the original dictionary.

This extension is intended to characterize available longitudinal movement-context evidence for T1-only patients. It must not be pooled directly with the T1-to-T2 dictionary for a T2-change analysis because its follow-up duration is data-bounded and differs between patients.

## Current extraction state

- T1-only patients: {len(patients)}
- Mapped devices: {sum(len(device_map.get(pid, [])) for pid in patients['patient_id'])}
- Completed device intervals: {completed}
- Patients with plugin events: {events_patients}
- Raw event rows: {raw_rows}

## Outputs

- `plugin_activity_t1_only_events.csv`: timestamp-level event dictionary.
- `plugin_activity_t1_only_minutes.csv`: UTC-minute movement-context dictionary.
- `plugin_activity_t1_only_device_day_summary.csv`: device-day coverage and label counts.
- `plugin_activity_t1_only_patient_day_summary.csv`: patient-day aggregation.
- `plugin_activity_t1_only_patient_summary.csv`: one row per T1-only patient.
- `plugin_activity_t1_only_status.csv`: query and parse status per mapped device.
- `plugin_activity_t1_only_summary.csv`: cohort accounting.
- `plugin_activity_t1_only_checkpoint.json`: resumable device-level checkpoint.

The data are exploratory phone-derived activity context, not direct body movement and not a clinical outcome.
"""
    README_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract plugin activity for active T1-only patients.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-patients", type=int, default=0)
    parser.add_argument("--confidence-threshold", type=int, default=base.HIGH_CONFIDENCE_DEFAULT)
    args = parser.parse_args()

    configure_base_output_paths()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    for path, fields in (
        (EVENTS_PATH, base.EVENT_FIELDS),
        (MINUTES_PATH, base.MINUTE_FIELDS),
        (DEVICE_DAYS_PATH, base.DEVICE_DAY_FIELDS),
        (STATUS_PATH, STATUS_FIELDS),
    ):
        base.initialize_csv(path, fields, args.resume)

    patients = base.load_patients()
    patients = patients[patients["t2_date"].eq("")].copy()
    if args.max_patients > 0:
        patients = patients.head(args.max_patients).copy()
    device_map = base.load_device_map()
    completed_keys = base.load_checkpoint() if args.resume else set()

    conn = base.connect_sensordata_db()
    try:
        max_timestamp = latest_plugin_timestamp(conn)
        end_ms = max_timestamp + 1
        endpoint_local = base.datetime_strings(max_timestamp)[1]
        window_end_display = f"{endpoint_local} (latest plugin timestamp)"
        print(f"latest_plugin_timestamp_local={endpoint_local}", flush=True)
        for patient_index, (_, patient) in enumerate(patients.iterrows(), start=1):
            patient_id = patient["patient_id"]
            t1_date = patient["t1_date"]
            start_ms = base.local_midnight_ms(t1_date)
            devices = device_map.get(patient_id, [])
            print(f"patient {patient_index}/{len(patients)} id={patient_id} devices={len(devices)} t1={t1_date}", flush=True)
            if start_ms is None:
                append_status({"patient_id": patient_id, "t1_date": t1_date, "query_status": "invalid_t1_date", "window_rule": "t1_to_plugin_table_maximum"})
                continue
            if not devices:
                append_status({"patient_id": patient_id, "t1_date": t1_date, "query_status": "no_mapped_device", "window_rule": "t1_to_plugin_table_maximum"})
                continue
            for device_index, device_id in enumerate(devices, start=1):
                key = f"{patient_id}|{device_id}"
                if key in completed_keys:
                    print(f"  device {device_index}/{len(devices)} skipped completed {device_id}", flush=True)
                    continue
                try:
                    if not conn.is_connected():
                        conn = base.connect_sensordata_db()
                    else:
                        conn.ping(reconnect=True, attempts=3, delay=1)
                    status, staging_path, minute_rows, device_day_rows = base.process_device(
                        conn,
                        patient_id,
                        device_id,
                        t1_date,
                        "",
                        start_ms,
                        end_ms,
                        args.confidence_threshold,
                        window_end_display=window_end_display,
                    )
                    status["window_rule"] = "t1_local_midnight_to_latest_plugin_timestamp"
                    base.append_staged_events(staging_path)
                    base.append_rows(MINUTES_PATH, base.MINUTE_FIELDS, minute_rows)
                    base.append_rows(DEVICE_DAYS_PATH, base.DEVICE_DAY_FIELDS, device_day_rows)
                    staging_path.unlink(missing_ok=True)
                    append_status(status)
                    completed_keys.add(key)
                    base.save_checkpoint(completed_keys, patient_index, len(completed_keys))
                    print(
                        f"  device {device_index}/{len(devices)} done {device_id} "
                        f"raw_rows={status['raw_row_count']} valid_labels={status['valid_label_row_count']}",
                        flush=True,
                    )
                except Exception as exc:
                    append_status(
                        {
                            "patient_id": patient_id,
                            "device_id": device_id,
                            "t1_date": t1_date,
                            "window_start_local": f"{t1_date} 00:00:00 {base.TZ_NAME}",
                            "window_end_local": window_end_display,
                            "window_start_ms": start_ms,
                            "window_end_ms_exclusive": end_ms,
                            "query_status": "failed",
                            "error_message": str(exc),
                            "window_rule": "t1_local_midnight_to_latest_plugin_timestamp",
                        }
                    )
                    print(f"  device={device_id} failed: {exc}", flush=True)
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = base.connect_sensordata_db()
    finally:
        conn.close()

    base.rebuild_patient_day_summary()
    rebuild_patient_summary(patients, device_map, endpoint_local)
    rebuild_summary(patients, device_map, endpoint_local)
    write_readme(patients, device_map, endpoint_local)
    print(f"extension_outputs={OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
