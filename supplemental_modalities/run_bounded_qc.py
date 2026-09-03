"""Run bounded QC probes for the deferred direct sensor modalities.

The runner deliberately does not extract full-span raw data. Proximity and
light are checked in the Phase 4-style T1 window. Raw accelerometer is checked
only in a short window anchored by the existing sensor-accelerometer metadata
QC. Outputs are appended one patient at a time and can be resumed from the
checkpoint file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db
from phase2_extract_selected_features_all_t1_patients import load_device_map_strict
from phase2_extract_exploratory_t1_week_24h_selected_features import (
    COGNITIVE_CANDIDATES_PATH,
    TZ,
    local_to_ms,
    ms_to_local,
    normalize_subject_id_d,
)

from .config import ACCELEROMETER_PATIENT_QC, MODALITIES, OUTPUT_ROOT


EXCLUDED_SUBJECTS = {"001"}
DIRECT_MODALITIES = {"proximity", "light"}
ACCELEROMETER_PROBE_MINUTES = 10
DEFAULT_SAMPLE_LIMIT = 50
RETRYABLE_DB_TERMS = (
    "lost connection",
    "server has gone away",
    "mysql connection not available",
    "connection reset",
)


def output_dir() -> Path:
    # Keep the first interrupted probe immutable; this clean pass has a new
    # output namespace after the connector-buffering fix.
    path = OUTPUT_ROOT / "bounded_qc_v2"
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_json(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:  # noqa: BLE001
        return None
    return value if isinstance(value, dict) else None


def numeric(value: Any) -> float | None:
    converted = pd.to_numeric(value, errors="coerce")
    return None if pd.isna(converted) else float(converted)


def local_timestamp(value: Any) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    if parsed.tzinfo is None:
        return parsed.tz_localize(TZ)
    return parsed.tz_convert(TZ)


def to_ms(value: Any) -> int | None:
    parsed = local_timestamp(value)
    return None if parsed is None else local_to_ms(parsed)


def load_patients() -> pd.DataFrame:
    patients = pd.read_csv(COGNITIVE_CANDIDATES_PATH, dtype=str)
    patients["Subject_ID_D"] = patients["Subject_ID_D"].map(normalize_subject_id_d)
    patients["Subject_ID_D"] = patients["Subject_ID_D"].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    patients = patients.dropna(subset=["Subject_ID_D", "T1_date_iso"]).copy()
    patients = patients[~patients["Subject_ID_D"].isin(EXCLUDED_SUBJECTS)].copy()
    return patients.sort_values("Subject_ID_D").drop_duplicates("Subject_ID_D").reset_index(drop=True)


def load_accelerometer_anchors() -> pd.DataFrame:
    anchors = pd.read_csv(ACCELEROMETER_PATIENT_QC, dtype=str)
    anchors["Subject_ID_D"] = anchors["Subject_ID_D"].map(normalize_subject_id_d)
    anchors = anchors[~anchors["Subject_ID_D"].isin(EXCLUDED_SUBJECTS)].copy()
    anchors["has_anchor"] = anchors["has_sensor_accelerometer_metadata_after_T1"].astype(str).str.lower().isin(
        {"true", "1", "yes"}
    )
    anchors = anchors[anchors["has_anchor"]].copy()
    anchors["selected_device_id"] = anchors["selected_device_id"].fillna("").astype(str).str.strip()
    anchors = anchors[anchors["selected_device_id"].ne("")].copy()
    return anchors.sort_values("Subject_ID_D").drop_duplicates("Subject_ID_D")


def table_name(modality: str) -> str:
    return str(MODALITIES[modality]["table_name"])


def json_key(modality: str) -> str | list[str]:
    if modality == "accelerometer":
        return ["double_values_0", "double_values_1", "double_values_2"]
    return str(MODALITIES[modality]["json_key"])


def is_retryable_db_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(term in message for term in RETRYABLE_DB_TERMS)


def query_count(conn: Any, table: str, device_id: str, start_ms: int, end_ms: int) -> dict[str, Any]:
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute(
            f"""
            SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM `{table}`
            WHERE device_id = %s AND timestamp >= %s AND timestamp < %s
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        row = cursor.fetchone() or {}
        return {
            "n_rows": int(row.get("n_rows") or 0),
            "first_ts": int(row["first_ts"]) if row.get("first_ts") is not None else None,
            "last_ts": int(row["last_ts"]) if row.get("last_ts") is not None else None,
        }
    finally:
        cursor.close()


def query_first_timestamp(conn: Any, table: str, device_id: str, start_ms: int, end_ms: int) -> int | None:
    cursor = conn.cursor(buffered=True)
    try:
        cursor.execute(
            f"""
            SELECT timestamp FROM `{table}`
            WHERE device_id = %s AND timestamp >= %s AND timestamp < %s
            ORDER BY timestamp ASC LIMIT 1
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        cursor.close()


def query_samples(
    conn: Any,
    table: str,
    device_id: str,
    start_ms: int,
    end_ms: int,
    limit: int,
) -> list[dict[str, Any]]:
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute(
            f"""
            SELECT timestamp, device_id, data
            FROM `{table}`
            WHERE device_id = %s AND timestamp >= %s AND timestamp < %s
            ORDER BY timestamp ASC LIMIT %s
            """,
            (device_id, int(start_ms), int(end_ms), int(limit)),
        )
        return list(cursor.fetchall() or [])
    finally:
        cursor.close()


def t1_probe_window(patient: pd.Series) -> dict[str, Any]:
    t1 = local_timestamp(patient.get("T1_date_iso"))
    if t1 is None:
        return {}
    primary_start = t1.normalize() + pd.Timedelta(days=1)
    primary_end = primary_start + pd.Timedelta(days=1)
    return {
        "window_rule": "phase4_primary_day_after_T1",
        "start_ms": local_to_ms(primary_start),
        "end_ms": local_to_ms(primary_end),
        "start_local": primary_start.strftime("%Y-%m-%d %H:%M:%S%z"),
        "end_local": primary_end.strftime("%Y-%m-%d %H:%M:%S%z"),
    }


def select_direct_window(
    conn: Any,
    modality: str,
    patient: pd.Series,
    device_ids: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    table = table_name(modality)
    primary = t1_probe_window(patient)
    if not primary:
        return {}, []

    device_rows: list[dict[str, Any]] = []
    for device_id in device_ids:
        counts = query_count(conn, table, device_id, primary["start_ms"], primary["end_ms"])
        device_rows.append(
            {
                "device_id": device_id,
                "primary_n_rows": counts["n_rows"],
                "primary_first_ts": counts["first_ts"],
                "primary_last_ts": counts["last_ts"],
            }
        )
    if sum(int(row["primary_n_rows"]) for row in device_rows) > 0:
        return primary, device_rows

    t1 = local_timestamp(patient.get("T1_date_iso"))
    assert t1 is not None
    fallback_search_start = local_to_ms(t1)
    fallback_search_end = local_to_ms(t1 + pd.Timedelta(days=7) - pd.Timedelta(days=1))
    candidates: list[tuple[int, str]] = []
    for row in device_rows:
        first_ts = query_first_timestamp(conn, table, row["device_id"], fallback_search_start, fallback_search_end)
        row["fallback_first_ts"] = first_ts
        if first_ts is not None:
            candidates.append((first_ts, row["device_id"]))
    if not candidates:
        return {
            **primary,
            "window_rule": "phase4_no_primary_or_fallback_data_in_T1_week",
        }, device_rows

    first_ts, _ = min(candidates)
    fallback_start = pd.to_datetime(first_ts, unit="ms", utc=True).tz_convert(TZ)
    fallback_end = fallback_start + pd.Timedelta(days=1)
    window = {
        "window_rule": "phase4_fallback_first_available_24h_in_T1_week",
        "start_ms": first_ts,
        "end_ms": local_to_ms(fallback_end),
        "start_local": fallback_start.strftime("%Y-%m-%d %H:%M:%S%z"),
        "end_local": fallback_end.strftime("%Y-%m-%d %H:%M:%S%z"),
    }
    for row in device_rows:
        counts = query_count(conn, table, row["device_id"], window["start_ms"], window["end_ms"])
        row["selected_n_rows"] = counts["n_rows"]
        row["selected_first_ts"] = counts["first_ts"]
        row["selected_last_ts"] = counts["last_ts"]
    return window, device_rows


def summarize_samples(modality: str, samples: list[dict[str, Any]], sample_limit: int) -> dict[str, Any]:
    key = json_key(modality)
    timestamps: list[int] = []
    values: list[float] = []
    component_values: dict[str, list[float]] = {item: [] for item in key} if isinstance(key, list) else {}
    parse_errors = 0
    key_present = 0
    for row in samples:
        timestamp = numeric(row.get("timestamp"))
        if timestamp is not None:
            timestamps.append(int(timestamp))
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        if isinstance(key, list):
            component_present = False
            row_components: list[float] = []
            for component in key:
                value = numeric(obj.get(component))
                if value is not None:
                    component_values[component].append(value)
                    row_components.append(value)
                    component_present = True
            if component_present:
                key_present += 1
            if len(row_components) == len(key):
                values.append(sum(value**2 for value in row_components) ** 0.5)
        else:
            raw_value = obj.get(key)
            if raw_value is not None:
                key_present += 1
            value = numeric(raw_value)
            if value is not None:
                values.append(value)

    timestamps.sort()
    intervals = [right - left for left, right in zip(timestamps, timestamps[1:]) if right >= left]
    summary: dict[str, Any] = {
        "sample_rows_requested": sample_limit,
        "sample_rows_returned": len(samples),
        "sample_json_parse_errors": parse_errors,
        "sample_key_present_rows": key_present,
        "sample_numeric_valid_rows": len(values),
        "sample_numeric_min": min(values) if values else pd.NA,
        "sample_numeric_median": float(pd.Series(values).median()) if values else pd.NA,
        "sample_numeric_max": max(values) if values else pd.NA,
        "sample_median_interval_ms": float(pd.Series(intervals).median()) if intervals else pd.NA,
        "sample_duplicate_timestamp_rows": len(timestamps) - len(set(timestamps)),
    }
    for component, component_values_list in component_values.items():
        summary[f"sample_{component}_valid_rows"] = len(component_values_list)
    return summary


def collect_direct_patient(
    conn: Any,
    modality: str,
    patient: pd.Series,
    device_ids: list[str],
    sample_limit: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    base = {
        "Subject_ID_D": patient["Subject_ID_D"],
        "Subject_ID_N": patient.get("Subject_ID_N", ""),
        "global_T1": patient.get("global_T1", ""),
        "T1_date_iso": patient.get("T1_date_iso", ""),
        "modality": modality,
        "table_name": table_name(modality),
        "device_ids_available": ";".join(device_ids),
        "n_devices_available": len(device_ids),
        "protocol_variant": "bounded_phase4_style_t1_probe",
    }
    if not device_ids:
        return {**base, "status": "missing_no_mapped_device"}, [], {}

    window, device_rows = select_direct_window(conn, modality, patient, device_ids)
    selected_start = window.get("start_ms")
    selected_end = window.get("end_ms")
    device_ids_used = [row["device_id"] for row in device_rows if int(row.get("selected_n_rows", row.get("primary_n_rows", 0)) or 0) > 0]
    samples: list[dict[str, Any]] = []
    for device_id in device_ids_used:
        samples.extend(query_samples(conn, table_name(modality), device_id, selected_start, selected_end, sample_limit))
    sample_summary = summarize_samples(modality, samples, sample_limit)
    n_rows = sum(int(row.get("selected_n_rows", row.get("primary_n_rows", 0)) or 0) for row in device_rows)
    status = "calculated" if n_rows > 0 else str(window.get("window_rule", "missing_no_data"))
    row = {
        **base,
        "status": status,
        "window_rule": window.get("window_rule", ""),
        "window_start_ms": selected_start,
        "window_end_ms": selected_end,
        "window_start_local": window.get("start_local", ""),
        "window_end_local": window.get("end_local", ""),
        "device_ids_used": ";".join(device_ids_used),
        "n_devices_with_rows": len(device_ids_used),
        "rows_in_selected_window": n_rows,
        **sample_summary,
    }
    device_frame = []
    for device_row in device_rows:
        device_frame.append(
            {
                **base,
                "device_id": device_row["device_id"],
                "window_rule": window.get("window_rule", ""),
                "window_start_ms": selected_start,
                "window_end_ms": selected_end,
                "primary_n_rows": device_row.get("primary_n_rows", 0),
                "fallback_first_ts": device_row.get("fallback_first_ts"),
                "selected_n_rows": device_row.get("selected_n_rows", device_row.get("primary_n_rows", 0)),
                "selected_first_ts": device_row.get("selected_first_ts", device_row.get("primary_first_ts")),
                "selected_last_ts": device_row.get("selected_last_ts", device_row.get("primary_last_ts")),
            }
        )
    return row, device_frame, {"sample_rows": len(samples)}


def collect_accelerometer_patient(
    conn: Any,
    patient: pd.Series,
    anchors: pd.DataFrame,
    sample_limit: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    subject_id = str(patient["Subject_ID_D"])
    base = {
        "Subject_ID_D": subject_id,
        "Subject_ID_N": patient.get("Subject_ID_N", ""),
        "global_T1": patient.get("global_T1", ""),
        "T1_date_iso": patient.get("T1_date_iso", ""),
        "modality": "accelerometer",
        "table_name": "accelerometer",
        "protocol_variant": "bounded_existing_metadata_anchor_10_minute_probe",
    }
    matching = anchors[anchors["Subject_ID_D"].astype(str) == subject_id]
    if matching.empty:
        return {**base, "status": "missing_no_sensor_accelerometer_metadata_anchor"}, [], {}
    anchor = matching.iloc[0]
    start_ms = to_ms(anchor.get("window_start_local"))
    device_id = str(anchor.get("selected_device_id", "")).strip()
    if start_ms is None or not device_id:
        return {**base, "status": "missing_incomplete_accelerometer_anchor"}, [], {}
    end_ms = start_ms + ACCELEROMETER_PROBE_MINUTES * 60 * 1000
    counts = query_count(conn, "accelerometer", device_id, start_ms, end_ms)
    samples = query_samples(conn, "accelerometer", device_id, start_ms, end_ms, sample_limit)
    sample_summary = summarize_samples("accelerometer", samples, sample_limit)
    status = "calculated" if counts["n_rows"] > 0 else "missing_no_raw_rows_in_anchor_probe"
    row = {
        **base,
        "status": status,
        "anchor_source": "sensor_accelerometer.window_start_local",
        "device_id": device_id,
        "window_rule": "sensor_accelerometer_anchor_plus_10_minutes",
        "window_start_ms": start_ms,
        "window_end_ms": end_ms,
        "window_start_local": ms_to_local(start_ms),
        "window_end_local": ms_to_local(end_ms),
        "rows_in_selected_window": counts["n_rows"],
        "first_ts": counts["first_ts"],
        "last_ts": counts["last_ts"],
        **sample_summary,
    }
    device_row = {
        **base,
        "device_id": device_id,
        "window_rule": row["window_rule"],
        "window_start_ms": start_ms,
        "window_end_ms": end_ms,
        "selected_n_rows": counts["n_rows"],
        "selected_first_ts": counts["first_ts"],
        "selected_last_ts": counts["last_ts"],
    }
    return row, [device_row], {"sample_rows": len(samples)}


def append_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    pd.DataFrame(rows).to_csv(path, mode="a", header=not path.exists() or path.stat().st_size == 0, index=False)


def checkpoint_states(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    states: set[tuple[str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("status") in {"calculated", "missing", "error"}:
            states.add((str(record.get("modality", "")), normalize_subject_id_d(record.get("Subject_ID_D"))))
    return states


def write_checkpoint(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def write_readme(path: Path) -> None:
    path.write_text(
        "# Supplemental modality bounded QC\n\n"
        "This run is an availability and payload-quality audit, not the final feature extraction. "
        "It does not save raw sensor payloads.\n\n"
        "- Proximity and light: all mapped devices except patient 001, Phase 4-style day-after-T1 24-hour probe; "
        "if empty, first available 24-hour span inside the T1 week is checked.\n"
        "- Accelerometer: existing `sensor_accelerometer` metadata-selected device and a 10-minute raw probe from its anchor.\n"
        "- Counts use bounded device-and-timestamp SQL filters. Samples are parsed in memory and only QC summaries are saved.\n"
        "- Missing rows are not interpreted as zero activity.\n"
        "- Patient 001 remains excluded because its raw accelerometer volume is atypical and was explicitly excluded from the prior pilot.\n\n"
        "The result is a gate for later chunked feature extraction across the four cohort spans.\n",
        encoding="utf-8",
    )


def run(modalities: list[str], limit_patients: int, resume: bool, sample_limit: int) -> None:
    patients = load_patients()
    if limit_patients > 0:
        patients = patients.head(limit_patients).copy()
    device_map = load_device_map_strict()
    anchors = load_accelerometer_anchors()
    out = output_dir()
    patient_path = out / "supplemental_bounded_patient_qc.csv"
    device_path = out / "supplemental_bounded_device_qc.csv"
    checkpoint_path = out / "supplemental_bounded_qc_checkpoint.jsonl"
    readme_path = out / "README_supplemental_bounded_qc.md"
    write_readme(readme_path)
    completed = checkpoint_states(checkpoint_path) if resume else set()

    conn = connect_sensordata_db()
    try:
        for modality in modalities:
            for index, (_, patient) in enumerate(patients.iterrows(), start=1):
                subject_id = str(patient["Subject_ID_D"])
                if (modality, subject_id) in completed:
                    print(f"skip modality={modality} patient={subject_id} checkpointed", flush=True)
                    continue
                print(f"probe modality={modality} patient={index}/{len(patients)} Subject_ID_D={subject_id}", flush=True)
                try:
                    if modality in DIRECT_MODALITIES:
                        patient_row, device_rows, extra = collect_direct_patient(
                            conn, modality, patient, device_map.get(subject_id, []), sample_limit
                        )
                    else:
                        patient_row, device_rows, extra = collect_accelerometer_patient(
                            conn, patient, anchors, sample_limit
                        )
                    append_rows(patient_path, [patient_row])
                    append_rows(device_path, device_rows)
                    checkpoint_status = "calculated" if patient_row.get("status") == "calculated" else "missing"
                    write_checkpoint(
                        checkpoint_path,
                        {
                            "modality": modality,
                            "Subject_ID_D": subject_id,
                            "status": checkpoint_status,
                            "patient_status": patient_row.get("status", ""),
                            "rows_in_selected_window": patient_row.get("rows_in_selected_window", 0),
                            "sample_rows": extra.get("sample_rows", 0),
                        },
                    )
                    print(
                        f"  status={patient_row.get('status', '')} rows={patient_row.get('rows_in_selected_window', 0)} "
                        f"sample_rows={extra.get('sample_rows', 0)}",
                        flush=True,
                    )
                except Exception as exc:  # noqa: BLE001
                    if is_retryable_db_error(exc):
                        try:
                            conn.close()
                        except Exception:  # noqa: BLE001
                            pass
                        conn = connect_sensordata_db()
                        try:
                            if modality in DIRECT_MODALITIES:
                                patient_row, device_rows, extra = collect_direct_patient(
                                    conn, modality, patient, device_map.get(subject_id, []), sample_limit
                                )
                            else:
                                patient_row, device_rows, extra = collect_accelerometer_patient(
                                    conn, patient, anchors, sample_limit
                                )
                            append_rows(patient_path, [patient_row])
                            append_rows(device_path, device_rows)
                            write_checkpoint(
                                checkpoint_path,
                                {
                                    "modality": modality,
                                    "Subject_ID_D": subject_id,
                                    "status": "calculated" if patient_row.get("status") == "calculated" else "missing",
                                    "patient_status": patient_row.get("status", ""),
                                    "rows_in_selected_window": patient_row.get("rows_in_selected_window", 0),
                                    "sample_rows": extra.get("sample_rows", 0),
                                    "retried_after_db_error": True,
                                },
                            )
                            print(
                                f"  retry_status={patient_row.get('status', '')} rows={patient_row.get('rows_in_selected_window', 0)}",
                                flush=True,
                            )
                            continue
                        except Exception as retry_exc:  # noqa: BLE001
                            exc = retry_exc
                    error_row = {
                        "Subject_ID_D": subject_id,
                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                        "global_T1": patient.get("global_T1", ""),
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                        "modality": modality,
                        "table_name": table_name(modality),
                        "status": "error",
                        "error_message": str(exc),
                        "protocol_variant": "bounded_qc",
                    }
                    append_rows(patient_path, [error_row])
                    write_checkpoint(
                        checkpoint_path,
                        {"modality": modality, "Subject_ID_D": subject_id, "status": "error", "error_message": str(exc)},
                    )
                    print(f"  status=error error={exc}", flush=True)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded QC for supplemental sensor modalities.")
    parser.add_argument(
        "--modality",
        choices=["all", *MODALITIES.keys()],
        default="all",
        help="Modality to probe; all runs proximity, light, then accelerometer.",
    )
    parser.add_argument("--limit-patients", type=int, default=0)
    parser.add_argument("--sample-limit", type=int, default=DEFAULT_SAMPLE_LIMIT)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    modalities = list(MODALITIES.keys()) if args.modality == "all" else [args.modality]
    run(modalities, args.limit_patients, args.resume, max(1, args.sample_limit))


if __name__ == "__main__":
    main()
