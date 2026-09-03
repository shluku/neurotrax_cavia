"""Extract proximity/light features over the actual Phase 11/12 midpoint spans.

Phase 11 uses ``[T1, midpoint)`` and Phase 12 uses ``[midpoint, T2)``.  The
midpoint and fallback rules come from ``phase11_12_extract_midpoint_interval``
so these supplemental values have the same patient-specific span as the
existing Phase 11/12 feature tables.

The direct streams are queried in bounded multi-device chunks.  Only
patient-level aggregates, coverage rows, and a resumable checkpoint are
written; raw sensor rows are never persisted by this extractor.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

import phase11_12_extract_midpoint_interval as midpoint
import phase5_extract_selected_features_all_t2_patients as phase5
from phase2_extract_exploratory_t1_week_24h_selected_features import (
    fetch_light_lux_values,
    normalize_subject_id_d,
)
from phase2_extract_selected_features_all_t1_patients import load_device_map_strict

from .extract_phase4_24h_t1 import (
    LIGHT_FEATURES,
    PROXIMITY_FEATURES,
    LightAccumulator,
    ProximityAccumulator,
)
from .config import OUTPUT_ROOT


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT_DIRECT = OUTPUT_ROOT / "phase11_12_midpoint_direct"
CHUNK_HOURS = 6
BATCH_ROWS = 10_000
MODALITIES = ("proximity", "light")
FEATURES = {"proximity": PROXIMITY_FEATURES, "light": LIGHT_FEATURES}


def output_dir(endpoint: str) -> Path:
    path = OUTPUT_ROOT_DIRECT / endpoint
    path.mkdir(parents=True, exist_ok=True)
    return path


def paths(endpoint: str) -> dict[str, Path]:
    prefix = f"phase{11 if endpoint == 't1' else 12}_{'t1_midpoint' if endpoint == 't1' else 'midpoint_t2'}_direct"
    out = output_dir(endpoint)
    return {
        "wide": out / f"{prefix}_features_wide.csv",
        "long": out / f"{prefix}_features_long.csv",
        "status": out / f"{prefix}_patient_modality_status.csv",
        "coverage": out / f"{prefix}_coverage.csv",
        "checkpoint": out / f"{prefix}_checkpoint.jsonl",
        "readme": out / f"README_{prefix}.md",
    }


def normalize_id(value: Any) -> str:
    return normalize_subject_id_d(value)


def valid_devices(device_map: dict[str, list[str]], subject_id: str) -> list[str]:
    devices = device_map.get(subject_id, [])
    return sorted({str(device).strip() for device in devices if str(device).strip()})


def placeholders(values: Iterable[str]) -> str:
    return ", ".join(["%s"] * len(list(values)))


def fetch_direct_chunk(
    conn: Any,
    table_name: str,
    device_ids: list[str],
    start_ms: int,
    end_ms: int,
) -> list[dict[str, Any]]:
    """Fetch one bounded chunk for all patient devices."""
    if not device_ids:
        return []
    cursor = conn.cursor(dictionary=True)
    try:
        device_placeholders = ", ".join(["%s"] * len(device_ids))
        if table_name == "light":
            query = f"""
                SELECT timestamp, device_id,
                       CAST(JSON_UNQUOTE(JSON_EXTRACT(data, '$.double_light_lux')) AS DECIMAL(18,6)) AS lux
                FROM `light`
                WHERE device_id IN ({device_placeholders})
                  AND timestamp >= %s AND timestamp < %s
                  AND JSON_EXTRACT(data, '$.double_light_lux') IS NOT NULL
                ORDER BY timestamp ASC, device_id ASC
            """
        elif table_name == "proximity":
            query = f"""
                SELECT timestamp, device_id, data
                FROM `proximity`
                WHERE device_id IN ({device_placeholders})
                  AND timestamp >= %s AND timestamp < %s
                ORDER BY timestamp ASC, device_id ASC
            """
        else:
            raise ValueError(f"Unsupported direct modality table: {table_name}")
        cursor.execute(query, [*device_ids, int(start_ms), int(end_ms)])
        rows: list[dict[str, Any]] = []
        while True:
            batch = cursor.fetchmany(BATCH_ROWS)
            if not batch:
                break
            rows.extend(batch)
        return rows
    finally:
        cursor.close()


def count_direct_rows(
    conn: Any,
    table_name: str,
    device_ids: list[str],
    start_ms: int,
    end_ms: int,
) -> dict[str, dict[str, int | None]]:
    """Count all raw rows once per device for coverage and light provenance."""
    if not device_ids:
        return {}
    cursor = conn.cursor(dictionary=True)
    try:
        device_placeholders = ", ".join(["%s"] * len(device_ids))
        cursor.execute(
            f"""
            SELECT device_id, COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM `{table_name}`
            WHERE device_id IN ({device_placeholders})
              AND timestamp >= %s AND timestamp < %s
            GROUP BY device_id
            """,
            [*device_ids, int(start_ms), int(end_ms)],
        )
        result: dict[str, dict[str, int | None]] = {}
        for row in cursor.fetchall() or []:
            device_id = str(row.get("device_id", ""))
            result[device_id] = {
                "n_rows": int(row.get("n_rows") or 0),
                "first_ts": int(row["first_ts"]) if row.get("first_ts") is not None else None,
                "last_ts": int(row["last_ts"]) if row.get("last_ts") is not None else None,
            }
        return result
    finally:
        cursor.close()


def split_by_device(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("device_id", "")), []).append(row)
    return grouped


def empty_feature_values(modality: str) -> dict[str, Any]:
    return {feature: pd.NA for feature in FEATURES[modality]}


def extract_modality(
    conn: Any,
    patient: pd.Series,
    modality: str,
    device_ids: list[str],
    window: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], str, str]:
    subject_id = str(patient["Subject_ID_D"])
    feature_values = empty_feature_values(modality)
    table_name = modality
    raw_count_by_device: dict[str, dict[str, int | None]] = {}
    status = "missing_invalid_patient_interval"
    error_message = ""

    if window is None:
        status = "missing_invalid_patient_interval"
    elif not device_ids:
        status = "missing_no_mapped_device"
    else:
        raw_count_by_device = count_direct_rows(
            conn, table_name, device_ids, int(window["start_ms"]), int(window["end_ms"])
        )
        if modality == "proximity":
            accumulator = ProximityAccumulator()
            for chunk_start in range_chunks(int(window["start_ms"]), int(window["end_ms"])):
                chunk_end = min(chunk_start + CHUNK_HOURS * 3_600_000, int(window["end_ms"]))
                accumulator.add(fetch_direct_chunk(conn, table_name, device_ids, chunk_start, chunk_end))
            if accumulator.valid_rows:
                feature_values = accumulator.finish(len({device for device in accumulator.previous_by_device}))
                status = "calculated"
            elif sum(int(row["n_rows"] or 0) for row in raw_count_by_device.values()) > 0:
                status = "missing_no_valid_numeric_rows"
            else:
                status = "missing_no_rows_in_interval"
        else:
            accumulator = LightAccumulator()
            for chunk_start in range_chunks(int(window["start_ms"]), int(window["end_ms"])):
                chunk_end = min(chunk_start + CHUNK_HOURS * 3_600_000, int(window["end_ms"]))
                rows = fetch_direct_chunk(conn, table_name, device_ids, chunk_start, chunk_end)
                for device_id, device_rows in split_by_device(rows).items():
                    accumulator.add(device_rows, device_id)
            raw_rows = sum(int(row["n_rows"] or 0) for row in raw_count_by_device.values())
            if accumulator.valid_rows:
                feature_values = accumulator.finish(raw_rows, len({device for device in accumulator.previous_by_device}))
                status = "calculated"
            elif raw_rows:
                status = "missing_no_valid_numeric_rows"
            else:
                status = "missing_no_rows_in_interval"

    base = {
        "Subject_ID_D": subject_id,
        "Subject_ID_N": patient.get("Subject_ID_N", ""),
        "global_T1": patient.get("global_T1", ""),
        "T1_date_iso": patient.get("T1_date_iso", ""),
        "T2_date_iso": patient.get("T2_date_iso", ""),
        "modality": modality,
        "table_name": table_name,
        **feature_values,
        "status": status,
        "feature_status": status,
        "error_message": error_message,
        "window_rule": window.get("window_rule", "") if window else "",
        "midpoint_source": window.get("midpoint_source", "") if window else "",
        "fallback_midpoint_days": window.get("fallback_midpoint_days", pd.NA) if window else pd.NA,
        "t1_timestamp": window.get("t1_timestamp", pd.NA) if window else pd.NA,
        "t2_timestamp": window.get("t2_timestamp", pd.NA) if window else pd.NA,
        "midpoint_timestamp": window.get("midpoint_timestamp", pd.NA) if window else pd.NA,
        "interval_days_from_t1_to_t2": window.get("interval_days_from_t1_to_t2", pd.NA) if window else pd.NA,
        "interval_days_in_endpoint": window.get("interval_days_in_endpoint", pd.NA) if window else pd.NA,
        "window_start_ms": window.get("start_ms", pd.NA) if window else pd.NA,
        "window_end_ms": window.get("end_ms", pd.NA) if window else pd.NA,
        "device_ids_available": ";".join(device_ids),
        "device_ids_used": ";".join(
            device_id for device_id, row in raw_count_by_device.items() if int(row["n_rows"] or 0) > 0
        ),
        "n_devices_available": len(device_ids),
        "n_devices_used": sum(int(row["n_rows"] or 0) > 0 for row in raw_count_by_device.values()),
    }
    coverage_rows = []
    for device_id in device_ids:
        counts = raw_count_by_device.get(device_id, {"n_rows": 0, "first_ts": None, "last_ts": None})
        coverage_rows.append(
            {
                "Subject_ID_D": subject_id,
                "modality": modality,
                "table_name": table_name,
                "device_id": device_id,
                "rows_in_window": counts["n_rows"],
                "first_data_timestamp": counts["first_ts"],
                "last_data_timestamp": counts["last_ts"],
                "window_rule": base["window_rule"],
                "midpoint_source": base["midpoint_source"],
                "window_start_ms": base["window_start_ms"],
                "window_end_ms": base["window_end_ms"],
            }
        )
    return base, coverage_rows, status, error_message


def range_chunks(start_ms: int, end_ms: int) -> Iterable[int]:
    chunk_ms = CHUNK_HOURS * 3_600_000
    current = int(start_ms)
    while current < int(end_ms):
        yield current
        current += chunk_ms


def append_records(path: Path, records: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    if not records:
        return
    frame = pd.DataFrame(records)
    if columns:
        frame = frame.reindex(columns=columns)
    frame.to_csv(path, mode="a", header=not path.exists() or path.stat().st_size == 0, index=False)


def read_checkpoint(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    completed: set[tuple[str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("status") == "completed":
            completed.add((str(row.get("Subject_ID_D", "")), str(row.get("modality", ""))))
    return completed


def write_checkpoint(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def clear_outputs(file_paths: dict[str, Path]) -> None:
    for path in file_paths.values():
        if path.exists() and path.suffix in {".csv", ".jsonl"}:
            path.unlink()


def run_endpoint(
    endpoint: str,
    modality_arg: str,
    max_patients: int,
    resume: bool,
    subject_id: str | None,
) -> None:
    file_paths = paths(endpoint)
    patients = midpoint.load_patients(endpoint)
    fallback_days = midpoint.cohort_fallback_midpoint_days(pd.read_csv(midpoint.DATASET_PATH, dtype=str))
    device_map = load_device_map_strict()
    modalities = list(MODALITIES if modality_arg == "all" else [modality_arg])

    if not resume:
        clear_outputs(file_paths)
        completed: set[tuple[str, str]] = set()
    else:
        completed = read_checkpoint(file_paths["checkpoint"])

    patients = patients.copy()
    if subject_id:
        patients = patients[patients["Subject_ID_D"].eq(normalize_id(subject_id))].copy()
    if max_patients > 0:
        patients = patients.head(max_patients).copy()

    wide_records: list[dict[str, Any]] = []
    long_records: list[dict[str, Any]] = []
    status_records: list[dict[str, Any]] = []
    coverage_records: list[dict[str, Any]] = []

    for index, (_, patient) in enumerate(patients.iterrows(), start=1):
        current_subject = str(patient["Subject_ID_D"])
        window = midpoint.patient_interval(endpoint, patient, fallback_days)
        device_ids = valid_devices(device_map, current_subject)
        print(
            f"{endpoint} patient {index}/{len(patients)} Subject_ID_D={current_subject} "
            f"interval_days={window.get('interval_days_in_endpoint', 'NA') if window else 'NA'} "
            f"devices={len(device_ids)} modalities={','.join(modalities)}",
            flush=True,
        )
        for modality in modalities:
            if (current_subject, modality) in completed:
                print(f"  skip completed modality={modality}", flush=True)
                continue
            status = "error"
            error_message = ""
            feature_row: dict[str, Any]
            coverage_rows: list[dict[str, Any]]
            conn = None
            try:
                if window is None or not device_ids:
                    feature_row, coverage_rows, status, error_message = extract_modality(
                        None, patient, modality, device_ids, window
                    )
                else:
                    conn = phase5.connect_sensordata_db()
                    conn.ping(reconnect=True, attempts=3, delay=1)
                    feature_row, coverage_rows, status, error_message = extract_modality(
                        conn, patient, modality, device_ids, window
                    )
            except Exception as exc:  # noqa: BLE001
                error_message = str(exc)
                feature_row = {
                    "Subject_ID_D": current_subject,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "T2_date_iso": patient.get("T2_date_iso", ""),
                    "modality": modality,
                    "table_name": modality,
                    **empty_feature_values(modality),
                    "status": "needs_retry",
                    "feature_status": "needs_retry",
                    "error_message": error_message,
                    "window_rule": window.get("window_rule", "") if window else "",
                    "midpoint_source": window.get("midpoint_source", "") if window else "",
                }
                coverage_rows = []
                status = "needs_retry"
            finally:
                if conn is not None:
                    conn.close()

            wide_records.append(feature_row)
            status_records.append(
                {
                    **{key: feature_row.get(key, "") for key in [
                        "Subject_ID_D", "Subject_ID_N", "global_T1", "T1_date_iso", "T2_date_iso",
                        "modality", "table_name", "status", "feature_status", "error_message",
                        "window_rule", "midpoint_source", "fallback_midpoint_days", "t1_timestamp",
                        "t2_timestamp", "midpoint_timestamp", "interval_days_from_t1_to_t2",
                        "interval_days_in_endpoint", "window_start_ms", "window_end_ms",
                        "device_ids_available", "device_ids_used", "n_devices_available", "n_devices_used",
                    ]},
                }
            )
            coverage_records.extend(coverage_rows)
            for feature_name in FEATURES[modality]:
                value = pd.to_numeric(feature_row.get(feature_name), errors="coerce")
                long_records.append(
                    {
                        "Subject_ID_D": current_subject,
                        "modality": modality,
                        "feature_name": feature_name,
                        "feature_value": value if not pd.isna(value) else pd.NA,
                        "feature_status": feature_row.get("feature_status", status),
                        "window_rule": feature_row.get("window_rule", ""),
                        "midpoint_source": feature_row.get("midpoint_source", ""),
                        "interval_days_in_endpoint": feature_row.get("interval_days_in_endpoint", pd.NA),
                        "error_message": error_message,
                    }
                )

            append_records(file_paths["wide"], [feature_row])
            append_records(file_paths["status"], [status_records[-1]])
            append_records(file_paths["coverage"], coverage_rows)
            append_records(file_paths["long"], long_records[-len(FEATURES[modality]):])
            write_checkpoint(
                file_paths["checkpoint"],
                {
                    "Subject_ID_D": current_subject,
                    "modality": modality,
                    "status": "completed" if status != "needs_retry" else "needs_retry",
                    "feature_status": status,
                    "error_message": error_message,
                },
            )
            print(f"  modality done={modality} status={status}", flush=True)

    # Rebuild a deterministic wide file from the append-only rows so resume
    # runs cannot leave duplicate patient/modality rows in the final artifact.
    if file_paths["wide"].exists():
        wide = pd.read_csv(file_paths["wide"], dtype=str)
        wide["Subject_ID_D"] = wide["Subject_ID_D"].map(normalize_id)
        wide = wide.drop_duplicates(["Subject_ID_D", "modality"], keep="last")
        wide.to_csv(file_paths["wide"], index=False)
    if file_paths["status"].exists():
        status_frame = pd.read_csv(file_paths["status"], dtype=str)
        status_frame["Subject_ID_D"] = status_frame["Subject_ID_D"].map(normalize_id)
        status_frame = status_frame.drop_duplicates(["Subject_ID_D", "modality"], keep="last")
        status_frame.to_csv(file_paths["status"], index=False)
    if file_paths["coverage"].exists():
        coverage = pd.read_csv(file_paths["coverage"], dtype=str)
        coverage["Subject_ID_D"] = coverage["Subject_ID_D"].map(normalize_id)
        coverage = coverage.drop_duplicates(["Subject_ID_D", "modality", "device_id"], keep="last")
        coverage.to_csv(file_paths["coverage"], index=False)
    if file_paths["long"].exists():
        long_frame = pd.read_csv(file_paths["long"], dtype=str)
        long_frame["Subject_ID_D"] = long_frame["Subject_ID_D"].map(normalize_id)
        long_frame = long_frame.drop_duplicates(["Subject_ID_D", "modality", "feature_name"], keep="last")
        long_frame.to_csv(file_paths["long"], index=False)

    file_paths["readme"].write_text(
        f"# Phase {11 if endpoint == 't1' else 12} direct supplemental extraction\n\n"
        f"This output uses the actual midpoint interval for endpoint `{endpoint}`. "
        f"The interval is half-open `[start, end)` and is patient-specific when T2 is available. "
        f"Phase 11 is `T1 -> midpoint`; Phase 12 is `midpoint -> T2`.\n\n"
        f"For Phase 11 patients without a valid T2, midpoint fallback is T1 plus the cohort median half-interval "
        f"({fallback_days:.3f} days). All valid mapped devices are pooled, excluding the project-wide excluded patient 001.\n\n"
        f"Proximity and light are queried in {CHUNK_HOURS}-hour multi-device chunks. Raw rows are not written to outputs. "
        "The feature table is an exploratory supplemental extraction and is not a model result.\n",
        encoding="utf-8",
    )
    print(f"completed endpoint={endpoint} output={output_dir(endpoint)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract proximity/light over Phase 11/12 midpoint intervals.")
    parser.add_argument("--endpoint", choices=["t1", "t2", "both"], default="both")
    parser.add_argument("--modality", choices=["proximity", "light", "all"], default="all")
    parser.add_argument("--max-patients", type=int, default=0)
    parser.add_argument("--subject-id")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    endpoints = ["t1", "t2"] if args.endpoint == "both" else [args.endpoint]
    for endpoint in endpoints:
        run_endpoint(endpoint, args.modality, args.max_patients, args.resume, args.subject_id)


if __name__ == "__main__":
    main()
