from __future__ import annotations

import argparse
import csv
import json
import math
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from main import connect_sensordata_db


ROOT = Path(__file__).parent
TZ_NAME = "Asia/Jerusalem"
LOCAL_TZ = ZoneInfo(TZ_NAME)
TABLE_NAME = "plugin_google_activity_recognition"
OUT_DIR = ROOT / "output/analysis_candidates/plugin_activity_movement_dictionary"
EVENTS_PATH = OUT_DIR / "plugin_activity_movement_events.csv"
MINUTES_PATH = OUT_DIR / "plugin_activity_movement_minutes.csv"
DEVICE_DAYS_PATH = OUT_DIR / "plugin_activity_device_day_summary.csv"
PATIENT_DAYS_PATH = OUT_DIR / "plugin_activity_patient_day_summary.csv"
STATUS_PATH = OUT_DIR / "plugin_activity_extraction_status.csv"
COHORT_SUMMARY_PATH = OUT_DIR / "plugin_activity_dictionary_cohort_summary.csv"
CHECKPOINT_PATH = OUT_DIR / "plugin_activity_dictionary_checkpoint.json"
README_PATH = OUT_DIR / "README_plugin_activity_movement_dictionary.md"
STAGING_DIR = OUT_DIR / "staging"

COGNITIVE_CANDIDATES_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
LABEL_DEVICE_MAP_PATH = ROOT / "output/label_device_map.csv"
EXCLUDED_SUBJECT_IDS = {"001"}

HIGH_CONFIDENCE_DEFAULT = 70
FETCH_BATCH_SIZE = 5_000
MAX_QUERY_ATTEMPTS = 3

EVENT_FIELDS = [
    "patient_id",
    "device_id",
    "event_id",
    "timestamp_ms",
    "event_time_utc",
    "event_time_local",
    "local_date",
    "minute_start_ms_utc",
    "minute_start_utc",
    "minute_start_local",
    "raw_activity_name",
    "activity_type",
    "confidence",
    "canonical_movement_class",
    "is_active_evidence",
    "is_still_evidence",
    "is_uncertain",
    "nested_activity_labels",
    "json_parse_status",
]

MINUTE_FIELDS = [
    "patient_id",
    "device_id",
    "minute_start_ms_utc",
    "minute_start_utc",
    "minute_start_local",
    "local_date",
    "plugin_event_count",
    "valid_label_event_count",
    "high_confidence_event_count",
    "active_land_event_count",
    "vehicle_event_count",
    "still_event_count",
    "orientation_change_event_count",
    "unknown_event_count",
    "other_event_count",
    "mean_confidence",
    "max_confidence",
    "n_distinct_activity_classes",
    "movement_evidence_class",
]

DEVICE_DAY_FIELDS = [
    "patient_id",
    "device_id",
    "local_date",
    "plugin_event_count",
    "valid_label_event_count",
    "high_confidence_event_count",
    "active_land_event_count",
    "vehicle_event_count",
    "still_event_count",
    "orientation_change_event_count",
    "unknown_event_count",
    "other_event_count",
    "mean_confidence",
    "max_confidence",
    "first_event_time_local",
    "last_event_time_local",
    "observed_hours",
    "n_observed_minutes",
    "dominant_movement_evidence_class",
]

STATUS_FIELDS = [
    "patient_id",
    "device_id",
    "t1_date",
    "t2_date",
    "window_start_local",
    "window_end_local",
    "window_start_ms",
    "window_end_ms_exclusive",
    "query_status",
    "raw_row_count",
    "valid_label_row_count",
    "json_parse_error_count",
    "invalid_timestamp_count",
    "first_event_time_local",
    "last_event_time_local",
    "nested_candidate_row_count",
    "error_message",
]


ACTIVE_LAND_LABELS = {"on_foot", "walking", "running", "on_bicycle", "cycling", "biking"}
VEHICLE_LABELS = {"in_vehicle", "in_vehicle_or_rail"}
STILL_LABELS = {"still"}
ORIENTATION_LABELS = {"tilting"}
UNKNOWN_LABELS = {"unknown"}


def normalize_subject_id(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def parse_payload(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None
    return None


def nested_activity_labels(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("activities")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
    if not isinstance(raw, list):
        return []
    labels: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = clean_text(item.get("activity")).lower()
        if label and label not in labels:
            labels.append(label)
    return labels


def normalize_activity_name(value: Any) -> str:
    return clean_text(value).lower()


def classify_activity(label: str) -> str:
    if label in ACTIVE_LAND_LABELS:
        return "active_land"
    if label in VEHICLE_LABELS:
        return "vehicle"
    if label in STILL_LABELS:
        return "still"
    if label in ORIENTATION_LABELS:
        return "orientation_change"
    if label in UNKNOWN_LABELS or not label:
        return "unknown"
    return "other"


def numeric(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def timestamp_ms(value: Any) -> int | None:
    result = numeric(value)
    if result is None:
        return None
    return int(result)


def datetime_strings(ts_ms: int) -> tuple[str, str, str]:
    value = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    local = value.astimezone(LOCAL_TZ)
    return (
        value.strftime("%Y-%m-%d %H:%M:%S%z"),
        local.strftime("%Y-%m-%d %H:%M:%S%z"),
        local.strftime("%Y-%m-%d"),
    )


def minute_strings(ts_ms: int) -> tuple[int, str, str]:
    minute_ms = (ts_ms // 60_000) * 60_000
    utc_text, local_text, _ = datetime_strings(minute_ms)
    return minute_ms, utc_text, local_text


def local_midnight_ms(date_value: Any) -> int | None:
    text = clean_text(date_value)
    if not text:
        return None
    try:
        local = datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=LOCAL_TZ)
    except ValueError:
        return None
    return int(local.astimezone(timezone.utc).timestamp() * 1000)


def load_patients() -> pd.DataFrame:
    patients = pd.read_csv(COGNITIVE_CANDIDATES_PATH, dtype=str)
    patients["patient_id"] = patients["Subject_ID_D"].map(normalize_subject_id)
    patients["t1_date"] = patients["T1_date_iso"].map(clean_text)
    patients["t2_date"] = patients["T2_date_iso"].map(clean_text)
    patients = patients[
        patients["patient_id"].ne("")
        & ~patients["patient_id"].isin(EXCLUDED_SUBJECT_IDS)
        & patients["t1_date"].ne("")
    ].copy()
    return patients.sort_values("patient_id").drop_duplicates("patient_id", keep="first")


def load_device_map() -> dict[str, list[str]]:
    mapping = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    out: dict[str, list[str]] = {}
    for _, row in mapping.iterrows():
        patient_id = normalize_subject_id(row.get("label"))
        if not patient_id:
            continue
        values = clean_text(row.get("device_ids"))
        devices = [value.strip() for value in values.split(";") if value.strip()]
        out[patient_id] = sorted(set(devices))
    return out


def append_rows(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def initialize_csv(path: Path, fields: list[str], resume: bool) -> None:
    if path.exists() and not resume and path.stat().st_size > 0:
        raise RuntimeError(f"Output already exists; use --resume to append safely: {path}")
    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=fields).writeheader()


def load_checkpoint() -> set[str]:
    if not CHECKPOINT_PATH.exists():
        return set()
    try:
        payload = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return set()
    return set(payload.get("completed_keys", []))


def save_checkpoint(completed_keys: set[str], patients_seen: int, devices_completed: int) -> None:
    payload = {
        "updated_at_local": datetime.now(tz=LOCAL_TZ).isoformat(),
        "completed_keys": sorted(completed_keys),
        "patients_seen": patients_seen,
        "devices_completed": devices_completed,
    }
    CHECKPOINT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def movement_evidence_class(counter: Counter[str]) -> str:
    present = {key for key, value in counter.items() if value > 0}
    if not present:
        return "no_valid_label"
    if len(present) == 1:
        return next(iter(present))
    if present == {"unknown"}:
        return "unknown"
    if "unknown" in present and len(present) == 2:
        return "known_plus_unknown"
    return "mixed"


def dominant_class(counter: Counter[str]) -> str:
    if not counter:
        return "no_valid_label"
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]


def new_aggregate() -> dict[str, Any]:
    return {
        "plugin_event_count": 0,
        "valid_label_event_count": 0,
        "high_confidence_event_count": 0,
        "class_counts": Counter(),
        "confidence_sum": 0.0,
        "confidence_count": 0,
        "max_confidence": None,
        "first_ts": None,
        "last_ts": None,
        "observed_minutes": set(),
    }


def update_aggregate(
    aggregate: dict[str, Any],
    ts_ms: int,
    movement_class: str,
    confidence: float | None,
    high_confidence_threshold: int,
    valid_label: bool,
) -> None:
    aggregate["plugin_event_count"] += 1
    if valid_label:
        aggregate["valid_label_event_count"] += 1
        aggregate["class_counts"][movement_class] += 1
    if confidence is not None:
        aggregate["confidence_sum"] += confidence
        aggregate["confidence_count"] += 1
        aggregate["max_confidence"] = max(confidence, aggregate["max_confidence"] or confidence)
        if confidence >= high_confidence_threshold:
            aggregate["high_confidence_event_count"] += 1
    aggregate["first_ts"] = ts_ms if aggregate["first_ts"] is None else min(aggregate["first_ts"], ts_ms)
    aggregate["last_ts"] = ts_ms if aggregate["last_ts"] is None else max(aggregate["last_ts"], ts_ms)
    aggregate["observed_minutes"].add((ts_ms // 60_000) * 60_000)


def class_counts_row(counter: Counter[str]) -> dict[str, int]:
    return {
        "active_land_event_count": counter.get("active_land", 0),
        "vehicle_event_count": counter.get("vehicle", 0),
        "still_event_count": counter.get("still", 0),
        "orientation_change_event_count": counter.get("orientation_change", 0),
        "unknown_event_count": counter.get("unknown", 0),
        "other_event_count": counter.get("other", 0),
    }


def summarize_aggregate(aggregate: dict[str, Any]) -> dict[str, Any]:
    confidence_count = aggregate["confidence_count"]
    return {
        **class_counts_row(aggregate["class_counts"]),
        "plugin_event_count": aggregate["plugin_event_count"],
        "valid_label_event_count": aggregate["valid_label_event_count"],
        "high_confidence_event_count": aggregate["high_confidence_event_count"],
        "mean_confidence": (
            aggregate["confidence_sum"] / confidence_count if confidence_count else ""
        ),
        "max_confidence": aggregate["max_confidence"] if aggregate["max_confidence"] is not None else "",
        "first_ts": aggregate["first_ts"],
        "last_ts": aggregate["last_ts"],
        "n_observed_minutes": len(aggregate["observed_minutes"]),
        "dominant_movement_evidence_class": dominant_class(aggregate["class_counts"]),
    }


def process_device(
    conn: Any,
    patient_id: str,
    device_id: str,
    t1_date: str,
    t2_date: str,
    start_ms: int,
    end_ms: int,
    high_confidence_threshold: int,
) -> tuple[dict[str, Any], Path | None, list[dict[str, Any]], list[dict[str, Any]]]:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    staging_path = STAGING_DIR / f"events_{patient_id}_{device_id}.csv.partial"
    staging_path.unlink(missing_ok=True)

    status: dict[str, Any] = {
        "patient_id": patient_id,
        "device_id": device_id,
        "t1_date": t1_date,
        "t2_date": t2_date,
        "window_start_local": f"{t1_date} 00:00:00 {TZ_NAME}",
        "window_end_local": f"{t2_date} 00:00:00 {TZ_NAME}",
        "window_start_ms": start_ms,
        "window_end_ms_exclusive": end_ms,
        "query_status": "failed",
        "raw_row_count": 0,
        "valid_label_row_count": 0,
        "json_parse_error_count": 0,
        "invalid_timestamp_count": 0,
        "first_event_time_local": "",
        "last_event_time_local": "",
        "nested_candidate_row_count": 0,
        "error_message": "",
    }
    minute_aggregates: dict[int, dict[str, Any]] = {}
    day_aggregates: dict[str, dict[str, Any]] = {}

    with staging_path.open("w", newline="", encoding="utf-8") as handle:
        event_writer = csv.DictWriter(handle, fieldnames=EVENT_FIELDS)
        event_writer.writeheader()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                f"""
                SELECT _id, timestamp, device_id, data
                FROM `{TABLE_NAME}`
                WHERE device_id = %s
                  AND timestamp >= %s
                  AND timestamp < %s
                ORDER BY timestamp ASC, _id ASC
                """,
                (device_id, int(start_ms), int(end_ms)),
            )
            while True:
                batch = cur.fetchmany(FETCH_BATCH_SIZE)
                if not batch:
                    break
                for row in batch:
                    status["raw_row_count"] += 1
                    ts_ms = timestamp_ms(row.get("timestamp"))
                    if ts_ms is None:
                        status["invalid_timestamp_count"] += 1
                        continue

                    utc_text, local_text, local_date = datetime_strings(ts_ms)
                    minute_ms, minute_utc, minute_local = minute_strings(ts_ms)
                    payload = parse_payload(row.get("data"))
                    nested_labels = nested_activity_labels(payload) if payload else []
                    status["nested_candidate_row_count"] += len(nested_labels)
                    if payload is None:
                        status["json_parse_error_count"] += 1
                        label = ""
                        activity_type = ""
                        confidence = None
                        parse_status = "invalid_json"
                    else:
                        label = normalize_activity_name(payload.get("activity_name"))
                        activity_type = clean_text(payload.get("activity_type"))
                        confidence = numeric(payload.get("confidence"))
                        parse_status = "valid_label" if label else "no_activity_label"

                    movement_class = classify_activity(label)
                    valid_label = bool(label)
                    if valid_label:
                        status["valid_label_row_count"] += 1
                    if status["first_event_time_local"] == "":
                        status["first_event_time_local"] = local_text
                    status["last_event_time_local"] = local_text

                    event_writer.writerow(
                        {
                            "patient_id": patient_id,
                            "device_id": device_id,
                            "event_id": clean_text(row.get("_id")),
                            "timestamp_ms": ts_ms,
                            "event_time_utc": utc_text,
                            "event_time_local": local_text,
                            "local_date": local_date,
                            "minute_start_ms_utc": minute_ms,
                            "minute_start_utc": minute_utc,
                            "minute_start_local": minute_local,
                            "raw_activity_name": label,
                            "activity_type": activity_type,
                            "confidence": confidence if confidence is not None else "",
                            "canonical_movement_class": movement_class,
                            "is_active_evidence": int(movement_class in {"active_land", "vehicle"}),
                            "is_still_evidence": int(movement_class == "still"),
                            "is_uncertain": int((not valid_label) or movement_class == "unknown" or (confidence is not None and confidence < high_confidence_threshold)),
                            "nested_activity_labels": ";".join(nested_labels),
                            "json_parse_status": parse_status,
                        }
                    )

                    minute_aggregate = minute_aggregates.setdefault(minute_ms, new_aggregate())
                    update_aggregate(
                        minute_aggregate,
                        ts_ms,
                        movement_class,
                        confidence,
                        high_confidence_threshold,
                        valid_label,
                    )
                    day_aggregate = day_aggregates.setdefault(local_date, new_aggregate())
                    update_aggregate(
                        day_aggregate,
                        ts_ms,
                        movement_class,
                        confidence,
                        high_confidence_threshold,
                        valid_label,
                    )
        finally:
            cur.close()

    minute_rows: list[dict[str, Any]] = []
    for minute_ms in sorted(minute_aggregates):
        aggregate = minute_aggregates[minute_ms]
        _, minute_utc, minute_local = minute_strings(minute_ms)
        summary = summarize_aggregate(aggregate)
        minute_rows.append(
            {
                "patient_id": patient_id,
                "device_id": device_id,
                "minute_start_ms_utc": minute_ms,
                "minute_start_utc": minute_utc,
                "minute_start_local": minute_local,
                "local_date": minute_local[:10],
                **{key: summary[key] for key in MINUTE_FIELDS if key in summary},
                "plugin_event_count": aggregate["plugin_event_count"],
                "valid_label_event_count": aggregate["valid_label_event_count"],
                "high_confidence_event_count": aggregate["high_confidence_event_count"],
                "mean_confidence": summary["mean_confidence"],
                "max_confidence": summary["max_confidence"],
                "n_distinct_activity_classes": len(aggregate["class_counts"]),
                "movement_evidence_class": movement_evidence_class(aggregate["class_counts"]),
            }
        )

    device_day_rows: list[dict[str, Any]] = []
    for local_date in sorted(day_aggregates):
        aggregate = day_aggregates[local_date]
        summary = summarize_aggregate(aggregate)
        first_local = datetime_strings(aggregate["first_ts"])[1] if aggregate["first_ts"] is not None else ""
        last_local = datetime_strings(aggregate["last_ts"])[1] if aggregate["last_ts"] is not None else ""
        observed_hours = (
            (aggregate["last_ts"] - aggregate["first_ts"]) / 3_600_000
            if aggregate["first_ts"] is not None and aggregate["last_ts"] is not None
            else ""
        )
        device_day_rows.append(
            {
                "patient_id": patient_id,
                "device_id": device_id,
                "local_date": local_date,
                **{key: summary[key] for key in DEVICE_DAY_FIELDS if key in summary},
                "plugin_event_count": aggregate["plugin_event_count"],
                "valid_label_event_count": aggregate["valid_label_event_count"],
                "high_confidence_event_count": aggregate["high_confidence_event_count"],
                "mean_confidence": summary["mean_confidence"],
                "max_confidence": summary["max_confidence"],
                "first_event_time_local": first_local,
                "last_event_time_local": last_local,
                "observed_hours": observed_hours,
                "n_observed_minutes": len(aggregate["observed_minutes"]),
                "dominant_movement_evidence_class": summary["dominant_movement_evidence_class"],
            }
        )

    status["query_status"] = "completed"
    return status, staging_path, minute_rows, device_day_rows


def append_staged_events(staging_path: Path) -> None:
    with staging_path.open("r", newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        with EVENTS_PATH.open("a", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=EVENT_FIELDS, extrasaction="ignore")
            for row in reader:
                writer.writerow(row)


def rebuild_patient_day_summary() -> None:
    if not DEVICE_DAYS_PATH.exists() or DEVICE_DAYS_PATH.stat().st_size == 0:
        return
    device_days = pd.read_csv(DEVICE_DAYS_PATH, dtype=str)
    if device_days.empty:
        return
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
        "n_observed_minutes",
    ]
    for column in numeric_columns:
        device_days[column] = pd.to_numeric(device_days[column], errors="coerce").fillna(0)
    device_days["mean_confidence_num"] = pd.to_numeric(device_days["mean_confidence"], errors="coerce")
    device_days["max_confidence_num"] = pd.to_numeric(device_days["max_confidence"], errors="coerce")
    grouped = device_days.groupby(["patient_id", "local_date"], dropna=False)
    rows: list[dict[str, Any]] = []
    for (patient_id, local_date), group in grouped:
        event_total = group["plugin_event_count"].sum()
        confidence_weight = group["mean_confidence_num"].notna() * group["plugin_event_count"]
        confidence_values = group["mean_confidence_num"].fillna(0) * group["plugin_event_count"]
        weighted_mean = confidence_values.sum() / confidence_weight.sum() if confidence_weight.sum() else ""
        classes = Counter()
        for _, row in group.iterrows():
            for key in ("active_land", "vehicle", "still", "orientation_change", "unknown", "other"):
                classes[key] += int(row[f"{key}_event_count"])
        rows.append(
            {
                "patient_id": patient_id,
                "local_date": local_date,
                "number_of_devices": group["device_id"].nunique(),
                "plugin_event_count": int(event_total),
                "valid_label_event_count": int(group["valid_label_event_count"].sum()),
                "high_confidence_event_count": int(group["high_confidence_event_count"].sum()),
                **class_counts_row(classes),
                "mean_confidence": weighted_mean,
                "max_confidence": group["max_confidence_num"].max() if group["max_confidence_num"].notna().any() else "",
                "first_event_time_local": group["first_event_time_local"].min(),
                "last_event_time_local": group["last_event_time_local"].max(),
                "n_observed_minutes_across_devices": int(group["n_observed_minutes"].sum()),
                "dominant_movement_evidence_class": dominant_class(classes),
            }
        )
    pd.DataFrame(rows).sort_values(["patient_id", "local_date"]).to_csv(PATIENT_DAYS_PATH, index=False)


def rebuild_summary(patients: pd.DataFrame, device_map: dict[str, list[str]], completed_keys: set[str]) -> None:
    status = pd.read_csv(STATUS_PATH, dtype=str) if STATUS_PATH.exists() else pd.DataFrame()
    valid_intervals = 0
    for _, patient in patients.iterrows():
        start_ms = local_midnight_ms(patient["t1_date"])
        end_ms = local_midnight_ms(patient["t2_date"])
        if start_ms is not None and end_ms is not None and end_ms > start_ms:
            valid_intervals += 1
    summary = {
        "active_patient_count": len(patients),
        "patients_with_valid_t1_t2_interval": valid_intervals,
        "patients_without_valid_t2_interval": len(patients) - valid_intervals,
        "mapped_device_count": sum(len(device_map.get(pid, [])) for pid in patients["patient_id"]),
        "completed_device_intervals": len([key for key in completed_keys if "|" in key and not key.endswith("|")]),
        "status_rows_written": len(status),
        "raw_event_rows_written": "",
        "minute_rows_written": "",
    }
    if EVENTS_PATH.exists():
        with EVENTS_PATH.open("r", encoding="utf-8") as handle:
            summary["raw_event_rows_written"] = max(sum(1 for _ in handle) - 1, 0)
    if MINUTES_PATH.exists():
        with MINUTES_PATH.open("r", encoding="utf-8") as handle:
            summary["minute_rows_written"] = max(sum(1 for _ in handle) - 1, 0)
    pd.DataFrame([summary]).to_csv(COHORT_SUMMARY_PATH, index=False)


def write_readme(patients: pd.DataFrame, device_map: dict[str, list[str]], confidence_threshold: int) -> None:
    status = pd.read_csv(STATUS_PATH, dtype=str) if STATUS_PATH.exists() else pd.DataFrame()
    completed = int((status.get("query_status", pd.Series(dtype=str)) == "completed").sum()) if not status.empty else 0
    failed = int((status.get("query_status", pd.Series(dtype=str)) == "failed").sum()) if not status.empty else 0
    rows = status[status["query_status"] == "completed"] if not status.empty else pd.DataFrame()
    raw_rows = int(pd.to_numeric(rows.get("raw_row_count", pd.Series(dtype=float)), errors="coerce").sum()) if not rows.empty else 0
    valid_rows = int(pd.to_numeric(rows.get("valid_label_row_count", pd.Series(dtype=float)), errors="coerce").sum()) if not rows.empty else 0
    return_text = f"""# Plugin Activity Movement Timestamp Dictionary

This is the first timestamp-level movement-context dictionary for the mapped active cohort. It is based on the SQL table `{TABLE_NAME}` and is intended to guide later raw accelerometer extraction.

## Protocol

- Cohort: patients with a T1 date in `cognitive_candidates_all.csv`, excluding subject `001` under the existing project rule.
- Mapping: only device IDs from `output/label_device_map.csv` are queried.
- Time interval: local midnight at T1, inclusive, through local midnight at T2, exclusive.
- Patients without a valid ordered T2 are retained in the cohort accounting but are not assigned an artificial movement interval.
- SQL is bounded by one mapped `device_id` and the patient-specific T1-to-T2 interval.
- Every valid SQL row is retained in the event dictionary. The full JSON payload is not copied; primary label, activity type, confidence, and nested candidate labels are retained.
- UTC minutes are used as the unambiguous time key; local timestamps are included for review.
- Confidence >= {confidence_threshold} is marked high confidence. Events are not removed because of low confidence.

## Movement classes

- `active_land`: `on_foot`, `walking`, `running`, or bicycle labels.
- `vehicle`: `in_vehicle` labels.
- `still`: `still`.
- `orientation_change`: `tilting`; this is not treated as walking or body movement.
- `unknown`: `unknown`, missing labels, or unparsable payloads.
- `other`: any other primary activity label.

This is phone-derived activity context, not a direct measure of patient movement. It may reflect phone carrying, placement, operating-system recognition, and collection intensity. Missing plugin rows mean no observed activity-recognition event, not confirmed stillness.

## Current extraction state

- Active patients in source cohort: {len(patients)}
- Mapped devices for active cohort: {sum(len(device_map.get(pid, [])) for pid in patients['patient_id'])}
- Completed device intervals recorded: {completed}
- Failed device intervals recorded: {failed}
- Raw event rows in completed intervals: {raw_rows}
- Valid primary-label rows: {valid_rows}

## Outputs

- `plugin_activity_movement_events.csv`: one row per plugin event, with raw primary label and derived movement class.
- `plugin_activity_movement_minutes.csv`: one row per patient-device UTC minute containing event counts and movement-context class.
- `plugin_activity_device_day_summary.csv`: device-day coverage and label totals.
- `plugin_activity_patient_day_summary.csv`: patient-day aggregation across mapped devices.
- `plugin_activity_extraction_status.csv`: interval-level row counts, parse quality, and errors.
- `plugin_activity_dictionary_cohort_summary.csv`: current cohort-level extraction accounting.
- `plugin_activity_dictionary_checkpoint.json`: completed device intervals for resumable execution.

## Planned investigation before accelerometer extraction

1. Check how many patients have plugin events, the number of observed days, and the distribution of event density.
2. Check whether activity classes and confidence are stable across devices and dates.
3. Use the minute dictionary to select short ACC windows with explicit movement-context labels.
4. Start raw general-ACC extraction only for mapped devices and selected windows, preserving sensor configuration metadata.

This dictionary is exploratory and should not be interpreted as a validated clinical digital biomarker.
"""
    README_PATH.write_text(return_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a mapped T1-to-T2 activity-recognition movement dictionary.")
    parser.add_argument("--resume", action="store_true", help="Resume completed device intervals without duplicating final rows.")
    parser.add_argument("--max-patients", type=int, default=0, help="Optional patient cap for a pilot; 0 means all.")
    parser.add_argument("--confidence-threshold", type=int, default=HIGH_CONFIDENCE_DEFAULT)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    for path, fields in (
        (EVENTS_PATH, EVENT_FIELDS),
        (MINUTES_PATH, MINUTE_FIELDS),
        (DEVICE_DAYS_PATH, DEVICE_DAY_FIELDS),
        (STATUS_PATH, STATUS_FIELDS),
    ):
        initialize_csv(path, fields, args.resume)

    patients = load_patients()
    if args.max_patients > 0:
        patients = patients.head(args.max_patients).copy()
    device_map = load_device_map()
    completed_keys = load_checkpoint() if args.resume else set()
    devices_completed = len(completed_keys)

    conn = None
    try:
        conn = connect_sensordata_db()
        for patient_index, (_, patient) in enumerate(patients.iterrows(), start=1):
            patient_id = patient["patient_id"]
            t1_date = patient["t1_date"]
            t2_date = patient["t2_date"]
            start_ms = local_midnight_ms(t1_date)
            end_ms = local_midnight_ms(t2_date)
            devices = device_map.get(patient_id, [])
            print(
                f"patient {patient_index}/{len(patients)} id={patient_id} devices={len(devices)} "
                f"t1={t1_date} t2={t2_date or 'missing'}",
                flush=True,
            )

            if start_ms is None or end_ms is None or end_ms <= start_ms:
                key = f"{patient_id}|"
                if key not in completed_keys:
                    append_rows(
                        STATUS_PATH,
                        STATUS_FIELDS,
                        [
                            {
                                "patient_id": patient_id,
                                "device_id": "",
                                "t1_date": t1_date,
                                "t2_date": t2_date,
                                "query_status": "no_valid_t2_interval",
                                "error_message": "T2 is missing or not later than T1; no artificial endpoint used.",
                            }
                        ],
                    )
                    completed_keys.add(key)
                    save_checkpoint(completed_keys, patient_index, devices_completed)
                continue

            if not devices:
                key = f"{patient_id}|"
                if key not in completed_keys:
                    append_rows(
                        STATUS_PATH,
                        STATUS_FIELDS,
                        [{"patient_id": patient_id, "t1_date": t1_date, "t2_date": t2_date, "query_status": "no_mapped_device"}],
                    )
                    completed_keys.add(key)
                    save_checkpoint(completed_keys, patient_index, devices_completed)
                continue

            for device_index, device_id in enumerate(devices, start=1):
                key = f"{patient_id}|{device_id}"
                if key in completed_keys:
                    print(f"  device {device_index}/{len(devices)} skipped completed {device_id}", flush=True)
                    continue

                last_error = ""
                result = None
                for attempt in range(1, MAX_QUERY_ATTEMPTS + 1):
                    try:
                        if conn is None or not conn.is_connected():
                            conn = connect_sensordata_db()
                        else:
                            conn.ping(reconnect=True, attempts=3, delay=1)
                        result = process_device(
                            conn,
                            patient_id,
                            device_id,
                            t1_date,
                            t2_date,
                            start_ms,
                            end_ms,
                            args.confidence_threshold,
                        )
                        break
                    except Exception as exc:
                        last_error = str(exc)
                        print(
                            f"  device={device_id} attempt={attempt}/{MAX_QUERY_ATTEMPTS} failed: {last_error}",
                            flush=True,
                        )
                        try:
                            if conn is not None:
                                conn.close()
                        except Exception:
                            pass
                        conn = None
                        if attempt < MAX_QUERY_ATTEMPTS:
                            time.sleep(1)

                if result is None:
                    append_rows(
                        STATUS_PATH,
                        STATUS_FIELDS,
                        [
                            {
                                "patient_id": patient_id,
                                "device_id": device_id,
                                "t1_date": t1_date,
                                "t2_date": t2_date,
                                "window_start_local": f"{t1_date} 00:00:00 {TZ_NAME}",
                                "window_end_local": f"{t2_date} 00:00:00 {TZ_NAME}",
                                "window_start_ms": start_ms,
                                "window_end_ms_exclusive": end_ms,
                                "query_status": "failed",
                                "error_message": last_error,
                            }
                        ],
                    )
                    continue

                status, staging_path, minute_rows, device_day_rows = result
                append_staged_events(staging_path)
                append_rows(MINUTES_PATH, MINUTE_FIELDS, minute_rows)
                append_rows(DEVICE_DAYS_PATH, DEVICE_DAY_FIELDS, device_day_rows)
                staging_path.unlink(missing_ok=True)
                append_rows(STATUS_PATH, STATUS_FIELDS, [status])
                completed_keys.add(key)
                devices_completed += 1
                save_checkpoint(completed_keys, patient_index, devices_completed)
                print(
                    f"  device {device_index}/{len(devices)} done {device_id} "
                    f"raw_rows={status['raw_row_count']} valid_labels={status['valid_label_row_count']}",
                    flush=True,
                )
    finally:
        if conn is not None:
            conn.close()

    rebuild_patient_day_summary()
    rebuild_summary(patients, device_map, completed_keys)
    write_readme(patients, device_map, args.confidence_threshold)
    print(f"dictionary_outputs={OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
