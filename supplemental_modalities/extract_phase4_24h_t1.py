"""Extract supplemental modality features for the Phase 4-style T1 window.

This is the first production feature stage for the supplemental subproject.
Proximity and light are streamed in bounded time chunks. Accelerometer uses
the existing metadata anchor and the validated 5-minute signal analyzer. Raw
rows are never written to cohort outputs.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from main import connect_sensordata_db
from phase2_extract_exploratory_t1_week_24h_selected_features import (
    COGNITIVE_CANDIDATES_PATH,
    TZ,
    fetch_light_lux_values,
    local_to_ms,
    ms_to_local,
    normalize_subject_id_d,
)
from phase2_extract_selected_features_all_t1_patients import COGNITIVE_COLUMNS, load_device_map_strict
from phase3_extract_accelerometer_24h_all_t1_streaming import fetch_chunk_rows
from phase3_extract_accelerometer_24h_pilot import FEATURE_NAMES as ACCELEROMETER_FEATURES, local_string_to_ms
from analyze_accelerometer_24h_local_pilot import CHUNK_MINUTES, analyze_chunk, summarize_features

from .config import ACCELEROMETER_PATIENT_QC, MODALITIES, OUTPUT_ROOT
from .run_bounded_qc import (
    EXCLUDED_SUBJECTS,
    is_retryable_db_error,
    load_accelerometer_anchors,
    select_direct_window,
    table_name,
    t1_probe_window,
)


OUTPUT_DIR = OUTPUT_ROOT / "phase4_24h_t1"
DIRECT_MODALITIES = {"proximity", "light"}
DIRECT_CHUNK_MINUTES = 15
ACCELEROMETER_WINDOW_HOURS = 24
DEFAULT_BATCH_ROWS = 10000
RESERVOIR_LIMIT = 100000
INTERVAL_RESERVOIR_LIMIT = 50000
NEAR_THRESHOLD = 0.5

PROXIMITY_FEATURES = [
    "proximity_raw_rows_in_window",
    "proximity_valid_numeric_rows",
    "proximity_json_parse_errors",
    "proximity_duplicate_adjacent_rows",
    "proximity_observed_span_hours",
    "proximity_active_hour_count",
    "proximity_median_value",
    "proximity_iqr_value",
    "proximity_near_sample_fraction",
    "proximity_near_transition_count",
    "proximity_near_bout_count",
    "proximity_median_interval_ms",
    "proximity_p95_interval_ms",
    "proximity_device_count",
]

LIGHT_FEATURES = [
    "light_raw_rows_in_window",
    "light_valid_lux_rows",
    "light_observed_span_hours",
    "light_active_hour_count",
    "median_light_lux",
    "percent_dark_samples",
    "night_mean_light_lux",
    "light_lux_iqr",
    "light_median_interval_ms",
    "light_p95_interval_ms",
    "light_device_count",
]

FEATURES = {
    "proximity": PROXIMITY_FEATURES,
    "light": LIGHT_FEATURES,
    "accelerometer": list(ACCELEROMETER_FEATURES),
}


def append_frame(path: Path, frame: pd.DataFrame, columns: list[str]) -> None:
    if frame.empty:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = frame.reindex(columns=columns)
    frame.to_csv(path, mode="a", header=not path.exists() or path.stat().st_size == 0, index=False)


def write_checkpoint(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def checkpoint_states(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    done: set[tuple[str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("status") in {"calculated", "missing"}:
            done.add((str(row.get("modality", "")), normalize_subject_id_d(row.get("Subject_ID_D"))))
    return done


def load_patients() -> pd.DataFrame:
    patients = pd.read_csv(COGNITIVE_CANDIDATES_PATH, dtype=str)
    patients["Subject_ID_D"] = patients["Subject_ID_D"].map(normalize_subject_id_d)
    patients["Subject_ID_D"] = patients["Subject_ID_D"].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    patients = patients.dropna(subset=["Subject_ID_D", "T1_date_iso"]).copy()
    patients = patients[~patients["Subject_ID_D"].isin(EXCLUDED_SUBJECTS)].copy()
    return patients.sort_values("Subject_ID_D").drop_duplicates("Subject_ID_D").reset_index(drop=True)


def numeric(value: Any) -> float | None:
    converted = pd.to_numeric(value, errors="coerce")
    return None if pd.isna(converted) else float(converted)


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


def reservoir_add(values: list[float], seen: int, value: float, limit: int, rng: random.Random) -> int:
    seen += 1
    if len(values) < limit:
        values.append(value)
    else:
        replacement = rng.randrange(seen)
        if replacement < limit:
            values[replacement] = value
    return seen


def quantile_summary(values: list[float]) -> tuple[float | pd._libs.missing.NAType, float | pd._libs.missing.NAType, float | pd._libs.missing.NAType]:
    if not values:
        return pd.NA, pd.NA, pd.NA
    series = pd.Series(values, dtype="float64")
    return float(series.median()), float(series.quantile(0.75) - series.quantile(0.25)), float(series.quantile(0.95))


def fetch_proximity_chunk(
    conn: Any,
    device_id: str,
    start_ms: int,
    end_ms: int,
    batch_rows: int,
) -> list[dict[str, Any]]:
    cursor = conn.cursor(dictionary=True)
    rows: list[dict[str, Any]] = []
    try:
        cursor.execute(
            """
            SELECT timestamp, device_id, data
            FROM `proximity`
            WHERE device_id = %s AND timestamp >= %s AND timestamp < %s
            ORDER BY timestamp ASC
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        while True:
            batch = cursor.fetchmany(batch_rows)
            if not batch:
                break
            rows.extend(batch)
    finally:
        cursor.close()
    return rows


class ProximityAccumulator:
    def __init__(self) -> None:
        self.raw_rows = 0
        self.valid_rows = 0
        self.parse_errors = 0
        self.duplicate_adjacent_rows = 0
        self.near_rows = 0
        self.near_transitions = 0
        self.near_bouts = 0
        self.active_hours: set[str] = set()
        self.values: list[float] = []
        self.intervals: list[float] = []
        self.seen_values = 0
        self.seen_intervals = 0
        self.rng = random.Random(20260804)
        self.interval_rng = random.Random(20260805)
        self.first_ts: int | None = None
        self.last_ts: int | None = None
        self.previous_by_device: dict[str, tuple[int, float, bool]] = {}

    def add(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self.raw_rows += 1
            device_id = str(row.get("device_id", ""))
            timestamp = numeric(row.get("timestamp"))
            obj = parse_json(row.get("data"))
            if obj is None:
                self.parse_errors += 1
                continue
            value = numeric(obj.get("double_proximity"))
            if timestamp is None or value is None:
                continue
            timestamp = int(timestamp)
            state_near = value <= NEAR_THRESHOLD
            previous = self.previous_by_device.get(device_id)
            if previous is not None:
                previous_ts, previous_value, previous_near = previous
                if timestamp == previous_ts and value == previous_value:
                    self.duplicate_adjacent_rows += 1
                if timestamp > previous_ts:
                    self.seen_intervals = reservoir_add(
                        self.intervals,
                        self.seen_intervals,
                        float(timestamp - previous_ts),
                        INTERVAL_RESERVOIR_LIMIT,
                        self.interval_rng,
                    )
                if state_near != previous_near:
                    self.near_transitions += 1
                if state_near and not previous_near:
                    self.near_bouts += 1
            self.previous_by_device[device_id] = (timestamp, value, state_near)
            self.valid_rows += 1
            self.near_rows += int(state_near)
            self.seen_values = reservoir_add(self.values, self.seen_values, value, RESERVOIR_LIMIT, self.rng)
            local = pd.to_datetime(timestamp, unit="ms", utc=True).tz_convert(TZ)
            self.active_hours.add(local.strftime("%Y-%m-%d %H"))
            self.first_ts = timestamp if self.first_ts is None else min(self.first_ts, timestamp)
            self.last_ts = timestamp if self.last_ts is None else max(self.last_ts, timestamp)

    def finish(self, device_count: int) -> dict[str, Any]:
        median, iqr, _ = quantile_summary(self.values)
        _, _, p95 = quantile_summary(self.intervals)
        return {
            "proximity_raw_rows_in_window": self.raw_rows,
            "proximity_valid_numeric_rows": self.valid_rows,
            "proximity_json_parse_errors": self.parse_errors,
            "proximity_duplicate_adjacent_rows": self.duplicate_adjacent_rows,
            "proximity_observed_span_hours": (
                (self.last_ts - self.first_ts) / 3_600_000 if self.first_ts is not None and self.last_ts is not None else pd.NA
            ),
            "proximity_active_hour_count": len(self.active_hours) if self.valid_rows else pd.NA,
            "proximity_median_value": median,
            "proximity_iqr_value": iqr,
            "proximity_near_sample_fraction": self.near_rows / self.valid_rows if self.valid_rows else pd.NA,
            "proximity_near_transition_count": self.near_transitions if self.valid_rows else pd.NA,
            "proximity_near_bout_count": self.near_bouts if self.valid_rows else pd.NA,
            "proximity_median_interval_ms": float(pd.Series(self.intervals).median()) if self.intervals else pd.NA,
            "proximity_p95_interval_ms": p95,
            "proximity_device_count": device_count if self.valid_rows else pd.NA,
        }


class LightAccumulator:
    def __init__(self) -> None:
        self.valid_rows = 0
        self.dark_rows = 0
        self.night_rows = 0
        self.night_sum = 0.0
        self.active_hours: set[str] = set()
        self.values: list[float] = []
        self.intervals: list[float] = []
        self.seen_values = 0
        self.seen_intervals = 0
        self.rng = random.Random(20260806)
        self.interval_rng = random.Random(20260807)
        self.first_ts: int | None = None
        self.last_ts: int | None = None
        self.previous_by_device: dict[str, int] = {}

    def add(self, rows: list[dict[str, Any]], device_id: str) -> None:
        for row in rows:
            timestamp = numeric(row.get("timestamp"))
            value = numeric(row.get("lux"))
            if timestamp is None or value is None:
                continue
            timestamp = int(timestamp)
            previous_ts = self.previous_by_device.get(device_id)
            if previous_ts is not None and timestamp > previous_ts:
                self.seen_intervals = reservoir_add(
                    self.intervals,
                    self.seen_intervals,
                    float(timestamp - previous_ts),
                    INTERVAL_RESERVOIR_LIMIT,
                    self.interval_rng,
                )
            self.previous_by_device[device_id] = timestamp
            self.valid_rows += 1
            self.dark_rows += int(value < 10)
            local = pd.to_datetime(timestamp, unit="ms", utc=True).tz_convert(TZ)
            if local.hour >= 22 or local.hour < 6:
                self.night_rows += 1
                self.night_sum += value
            self.active_hours.add(local.strftime("%Y-%m-%d %H"))
            self.seen_values = reservoir_add(self.values, self.seen_values, value, RESERVOIR_LIMIT, self.rng)
            self.first_ts = timestamp if self.first_ts is None else min(self.first_ts, timestamp)
            self.last_ts = timestamp if self.last_ts is None else max(self.last_ts, timestamp)

    def finish(self, raw_rows: int, device_count: int) -> dict[str, Any]:
        median, iqr, p95 = quantile_summary(self.values)
        _, _, interval_p95 = quantile_summary(self.intervals)
        return {
            "light_raw_rows_in_window": raw_rows,
            "light_valid_lux_rows": self.valid_rows,
            "light_observed_span_hours": (
                (self.last_ts - self.first_ts) / 3_600_000 if self.first_ts is not None and self.last_ts is not None else pd.NA
            ),
            "light_active_hour_count": len(self.active_hours) if self.valid_rows else pd.NA,
            "median_light_lux": median,
            "percent_dark_samples": 100 * self.dark_rows / self.valid_rows if self.valid_rows else pd.NA,
            "night_mean_light_lux": self.night_sum / self.night_rows if self.night_rows else pd.NA,
            "light_lux_iqr": iqr,
            "light_median_interval_ms": float(pd.Series(self.intervals).median()) if self.intervals else pd.NA,
            "light_p95_interval_ms": interval_p95 if self.intervals else pd.NA,
            "light_device_count": device_count if self.valid_rows else pd.NA,
            "light_quantile_method": "deterministic_reservoir_sample_max_100000",
        }


def direct_device_rows(device_rows: list[dict[str, Any]], fallback: bool = False) -> list[str]:
    key = "selected_n_rows" if fallback else "primary_n_rows"
    return [row["device_id"] for row in device_rows if int(row.get(key, 0) or 0) > 0]


def base_row(patient: pd.Series, modality: str) -> dict[str, Any]:
    return {
        "Subject_ID_D": patient.get("Subject_ID_D", ""),
        "Subject_ID_N": patient.get("Subject_ID_N", ""),
        "global_T1": patient.get("global_T1", ""),
        "T1_date_iso": patient.get("T1_date_iso", ""),
        "modality": modality,
        "table_name": table_name(modality),
    }


def direct_feature_row(
    conn: Any,
    patient: pd.Series,
    modality: str,
    device_ids: list[str],
    batch_rows: int,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    window, device_rows = select_direct_window(conn, modality, patient, device_ids)
    primary_available = window.get("window_rule") == "phase4_primary_day_after_T1"
    fallback_available = window.get("window_rule") == "phase4_fallback_first_available_24h_in_T1_week"
    used_devices = direct_device_rows(device_rows, fallback=fallback_available)
    status = "calculated" if used_devices else str(window.get("window_rule", "missing_no_data"))
    feature_values = {name: pd.NA for name in FEATURES[modality]}
    total_raw_rows = 0
    if used_devices:
        for row in device_rows:
            if fallback_available:
                total_raw_rows += int(row.get("selected_n_rows", 0) or 0)
            elif primary_available:
                total_raw_rows += int(row.get("primary_n_rows", 0) or 0)
        if modality == "proximity":
            accumulator = ProximityAccumulator()
            chunk_ms = DIRECT_CHUNK_MINUTES * 60 * 1000
            for device_id in used_devices:
                t = int(window["start_ms"])
                while t < int(window["end_ms"]):
                    t_next = min(t + chunk_ms, int(window["end_ms"]))
                    accumulator.add(fetch_proximity_chunk(conn, device_id, t, t_next, batch_rows))
                    t = t_next
            feature_values = accumulator.finish(len(used_devices))
        else:
            accumulator = LightAccumulator()
            chunk_ms = DIRECT_CHUNK_MINUTES * 60 * 1000
            for device_id in used_devices:
                t = int(window["start_ms"])
                while t < int(window["end_ms"]):
                    t_next = min(t + chunk_ms, int(window["end_ms"]))
                    rows = fetch_light_lux_values(conn, device_id, t, t_next)
                    accumulator.add(rows, device_id)
                    t = t_next
            feature_values = accumulator.finish(total_raw_rows, len(used_devices))
    feature_values["feature_status"] = status
    row = {
        **base_row(patient, modality),
        **feature_values,
        "status": status,
        "window_rule": window.get("window_rule", ""),
        "window_start_ms": window.get("start_ms", pd.NA),
        "window_end_ms": window.get("end_ms", pd.NA),
        "window_start_local": window.get("start_local", ""),
        "window_end_local": window.get("end_local", ""),
        "device_ids_available": ";".join(device_ids),
        "device_ids_used": ";".join(used_devices),
        "n_devices_available": len(device_ids),
        "n_devices_used": len(used_devices),
    }
    coverage_rows = []
    for device_row in device_rows:
        coverage_rows.append(
            {
                **base_row(patient, modality),
                "device_id": device_row["device_id"],
                "window_rule": window.get("window_rule", ""),
                "window_start_ms": window.get("start_ms", pd.NA),
                "window_end_ms": window.get("end_ms", pd.NA),
                "primary_n_rows": device_row.get("primary_n_rows", 0),
                "fallback_first_ts": device_row.get("fallback_first_ts", pd.NA),
                "selected_n_rows": device_row.get("selected_n_rows", device_row.get("primary_n_rows", 0)),
                "selected_first_ts": device_row.get("selected_first_ts", device_row.get("primary_first_ts", pd.NA)),
                "selected_last_ts": device_row.get("selected_last_ts", device_row.get("primary_last_ts", pd.NA)),
            }
        )
    return row, {"status": status, "rows_in_window": total_raw_rows}, coverage_rows


def accelerometer_feature_row(
    conn: Any,
    patient: pd.Series,
    anchor: pd.Series | None,
    batch_rows: int,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    row_base = base_row(patient, "accelerometer")
    feature_values = {name: pd.NA for name in ACCELEROMETER_FEATURES}
    if anchor is None:
        row = {
            **row_base,
            **feature_values,
            "status": "missing_no_sensor_accelerometer_metadata_anchor",
            "feature_status": "missing_no_sensor_accelerometer_metadata_anchor",
            "window_rule": "sensor_accelerometer_anchor_plus_24_hours",
        }
        return row, {"status": row["status"], "rows_in_window": 0}, []

    device_id = str(anchor.get("selected_device_id", "")).strip()
    start_ms = local_string_to_ms(anchor.get("window_start_local"))
    if not device_id or start_ms is None:
        status = "missing_incomplete_sensor_accelerometer_anchor"
        return {
            **row_base,
            **feature_values,
            "status": status,
            "feature_status": status,
            "window_rule": "sensor_accelerometer_anchor_plus_24_hours",
        }, {"status": status, "rows_in_window": 0}, []

    end_ms = start_ms + ACCELEROMETER_WINDOW_HOURS * 60 * 60 * 1000
    chunk_rows: list[dict[str, Any]] = []
    raw_rows = 0
    clean_rows = 0
    duplicate_rows = 0
    chunk_ms = CHUNK_MINUTES * 60 * 1000
    chunk_index = 0
    t = start_ms
    while t < end_ms:
        t_next = min(t + chunk_ms, end_ms)
        chunk_df, chunk_raw_rows = fetch_chunk_rows(conn, device_id, t, t_next, batch_rows)
        raw_rows += chunk_raw_rows
        before = len(chunk_df)
        if not chunk_df.empty:
            chunk_df = chunk_df.drop_duplicates(subset=["timestamp", "x", "y", "z"], keep="first").copy()
        duplicate_rows += before - len(chunk_df)
        clean_rows += len(chunk_df)
        analysis_row = analyze_chunk(chunk_index, t, t_next, chunk_df)
        analysis_row.update({"Subject_ID_D": patient["Subject_ID_D"], "device_id": device_id, "raw_rows_downloaded": chunk_raw_rows})
        chunk_rows.append(analysis_row)
        print(
            f"patient={patient['Subject_ID_D']} modality=accelerometer chunk={chunk_index:03d} "
            f"rows={chunk_raw_rows:,} status={analysis_row.get('status', '')}",
            flush=True,
        )
        t = t_next
        chunk_index += 1

    if raw_rows > 0:
        chunk_frame = pd.DataFrame(chunk_rows)
        manifest = {
            "Subject_ID_D": patient.get("Subject_ID_D", ""),
            "Subject_ID_N": patient.get("Subject_ID_N", ""),
            "global_T1": patient.get("global_T1", ""),
            "T1_date_iso": patient.get("T1_date_iso", ""),
            "device_id": device_id,
            "candidate_window_start_local": ms_to_local(start_ms),
            "candidate_window_end_local": ms_to_local(end_ms),
        }
        summary = summarize_features(chunk_frame, manifest, clean_rows, duplicate_rows)
        if not summary.empty:
            feature_values = summary.iloc[0].to_dict()
        status = "calculated"
    else:
        status = "missing_no_raw_rows_in_accelerometer_24h_anchor"

    row = {
        **row_base,
        **{name: feature_values.get(name, pd.NA) for name in ACCELEROMETER_FEATURES},
        "status": status,
        "feature_status": status,
        "window_rule": "sensor_accelerometer_anchor_plus_24_hours",
        "window_start_ms": start_ms,
        "window_end_ms": end_ms,
        "window_start_local": ms_to_local(start_ms),
        "window_end_local": ms_to_local(end_ms),
        "device_id": device_id,
        "raw_rows_downloaded": raw_rows,
        "clean_signal_rows": clean_rows,
        "duplicates_removed": duplicate_rows,
    }
    coverage = [{
        **row_base,
        "device_id": device_id,
        "window_rule": row["window_rule"],
        "window_start_ms": start_ms,
        "window_end_ms": end_ms,
        "selected_n_rows": raw_rows,
        "selected_first_ts": pd.NA,
        "selected_last_ts": pd.NA,
    }]
    return row, {"status": status, "rows_in_window": raw_rows}, coverage


def write_readme() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "README_phase4_24h_t1_supplemental_modalities.md").write_text(
        "# Supplemental Phase 4 24-hour T1 feature extraction\n\n"
        "This is the first derived-feature stage for the supplemental modalities.\n\n"
        "- Proximity and light use the Phase 4 primary day-after-T1 window, with the first available 24-hour span inside the T1 week as fallback.\n"
        "- Accelerometer uses the existing `sensor_accelerometer` metadata-selected device and a 24-hour window from that anchor.\n"
        "- Proximity/light are fetched in 15-minute chunks. Accelerometer is fetched in validated 5-minute signal-analysis chunks.\n"
        "- Raw payloads are parsed in memory and discarded. Only patient-level features and coverage/status outputs are written.\n"
        "- Proximity near-state is a provisional engineering threshold (`double_proximity <= 0.5`) based on the observed 0/maximum-range pattern; it is not a clinical label.\n"
        "- Light median and IQR use a deterministic bounded reservoir (maximum 100,000 valid values per patient); counts, dark fraction, and nighttime mean use all valid SQL-projected lux rows.\n"
        "- Missingness remains missing; it is never filled with zero.\n\n"
        "This output is additive and is not yet merged into Phase 4 models.\n",
        encoding="utf-8",
    )


def run(modalities: list[str], limit_patients: int, resume: bool, batch_rows: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_readme()
    patients = load_patients()
    if limit_patients > 0:
        patients = patients.head(limit_patients).copy()
    device_map = load_device_map_strict()
    anchors = load_accelerometer_anchors()
    completed = checkpoint_states(OUTPUT_DIR / "phase4_24h_t1_supplemental_checkpoint.jsonl") if resume else set()

    for modality in modalities:
        status_path = OUTPUT_DIR / f"{modality}_patient_status.csv"
        features_long_path = OUTPUT_DIR / f"{modality}_features_long.csv"
        features_wide_path = OUTPUT_DIR / f"{modality}_features_wide.csv"
        coverage_path = OUTPUT_DIR / f"{modality}_coverage.csv"
        checkpoint_path = OUTPUT_DIR / "phase4_24h_t1_supplemental_checkpoint.jsonl"
        status_columns = [
            "Subject_ID_D", "Subject_ID_N", "global_T1", "T1_date_iso", "modality", "table_name", "status",
            "window_rule", "window_start_ms", "window_end_ms", "window_start_local", "window_end_local",
            "device_ids_available", "device_ids_used", "n_devices_available", "n_devices_used", "rows_in_window",
            "error_message",
        ]
        long_columns = [
            "Subject_ID_D", "Subject_ID_N", "global_T1", "T1_date_iso", "modality", "feature_name",
            "feature_value", "feature_status", "window_rule", "window_start_local", "window_end_local",
        ]
        wide_base_columns = [column for column in COGNITIVE_COLUMNS if column in patients.columns]
        wide_columns = wide_base_columns + FEATURES[modality] + ["feature_status", "status", "window_rule", "window_start_local", "window_end_local"]
        coverage_columns = [
            "Subject_ID_D", "Subject_ID_N", "global_T1", "T1_date_iso", "modality", "table_name", "device_id",
            "window_rule", "window_start_ms", "window_end_ms", "primary_n_rows", "fallback_first_ts",
            "selected_n_rows", "selected_first_ts", "selected_last_ts",
        ]

        for index, (_, patient) in enumerate(patients.iterrows(), start=1):
            subject_id = str(patient["Subject_ID_D"])
            if (modality, subject_id) in completed:
                print(f"skip modality={modality} patient={subject_id} checkpointed", flush=True)
                continue
            print(f"extract modality={modality} patient={index}/{len(patients)} Subject_ID_D={subject_id}", flush=True)
            conn = connect_sensordata_db()
            try:
                try:
                    if modality in DIRECT_MODALITIES:
                        feature_row, result, coverage_rows = direct_feature_row(
                            conn, patient, modality, device_map.get(subject_id, []), batch_rows
                        )
                    else:
                        anchor_match = anchors[anchors["Subject_ID_D"].astype(str).eq(subject_id)]
                        anchor = anchor_match.iloc[0] if not anchor_match.empty else None
                        feature_row, result, coverage_rows = accelerometer_feature_row(conn, patient, anchor, batch_rows)
                    status = str(result["status"])
                    long_rows = [
                        {
                            "Subject_ID_D": subject_id,
                            "Subject_ID_N": patient.get("Subject_ID_N", ""),
                            "global_T1": patient.get("global_T1", ""),
                            "T1_date_iso": patient.get("T1_date_iso", ""),
                            "modality": modality,
                            "feature_name": name,
                            "feature_value": feature_row.get(name, pd.NA),
                            "feature_status": feature_row.get("feature_status", status),
                            "window_rule": feature_row.get("window_rule", ""),
                            "window_start_local": feature_row.get("window_start_local", ""),
                            "window_end_local": feature_row.get("window_end_local", ""),
                        }
                        for name in FEATURES[modality]
                    ]
                    append_frame(pd.DataFrame([feature_row]), features_wide_path, wide_columns)
                    append_frame(pd.DataFrame(long_rows), features_long_path, long_columns)
                    append_frame(pd.DataFrame(coverage_rows), coverage_path, coverage_columns)
                    status_row = {
                        **base_row(patient, modality),
                        "status": status,
                        "window_rule": feature_row.get("window_rule", ""),
                        "window_start_ms": feature_row.get("window_start_ms", pd.NA),
                        "window_end_ms": feature_row.get("window_end_ms", pd.NA),
                        "window_start_local": feature_row.get("window_start_local", ""),
                        "window_end_local": feature_row.get("window_end_local", ""),
                        "device_ids_available": feature_row.get("device_ids_available", ""),
                        "device_ids_used": feature_row.get("device_ids_used", feature_row.get("device_id", "")),
                        "n_devices_available": feature_row.get("n_devices_available", pd.NA),
                        "n_devices_used": feature_row.get("n_devices_used", pd.NA),
                        "rows_in_window": result.get("rows_in_window", 0),
                        "error_message": "",
                    }
                    append_frame(pd.DataFrame([status_row]), status_path, status_columns)
                    write_checkpoint(
                        checkpoint_path,
                        {
                            "modality": modality,
                            "Subject_ID_D": subject_id,
                            "status": "calculated" if status == "calculated" else "missing",
                            "patient_status": status,
                            "rows_in_window": result.get("rows_in_window", 0),
                        },
                    )
                    print(f"  status={status} rows={result.get('rows_in_window', 0)}", flush=True)
                except Exception as exc:  # noqa: BLE001
                    if is_retryable_db_error(exc):
                        raise
                    status_row = {
                        **base_row(patient, modality),
                        "status": "error",
                        "window_rule": "",
                        "window_start_ms": pd.NA,
                        "window_end_ms": pd.NA,
                        "window_start_local": "",
                        "window_end_local": "",
                        "device_ids_available": ";".join(device_map.get(subject_id, [])),
                        "device_ids_used": "",
                        "n_devices_available": len(device_map.get(subject_id, [])),
                        "n_devices_used": 0,
                        "rows_in_window": 0,
                        "error_message": str(exc),
                    }
                    append_frame(pd.DataFrame([status_row]), status_path, status_columns)
                    write_checkpoint(
                        checkpoint_path,
                        {"modality": modality, "Subject_ID_D": subject_id, "status": "error", "error_message": str(exc)},
                    )
                    print(f"  status=error error={exc}", flush=True)
            except Exception as exc:  # noqa: BLE001
                # Reopen once for the connector failures common to large JSON
                # tables. The patient is retried on the next --resume pass if
                # the retry also fails.
                if is_retryable_db_error(exc):
                    print(f"  reconnect_required error={exc}", flush=True)
                    try:
                        conn.close()
                    except Exception:  # noqa: BLE001
                        pass
                    continue
                raise
            finally:
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract supplemental Phase 4 24-hour T1 features.")
    parser.add_argument("--modality", choices=["all", *MODALITIES.keys()], default="all")
    parser.add_argument("--limit-patients", type=int, default=0)
    parser.add_argument("--batch-rows", type=int, default=DEFAULT_BATCH_ROWS)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    modalities = list(MODALITIES.keys()) if args.modality == "all" else [args.modality]
    run(modalities, args.limit_patients, args.resume, max(100, args.batch_rows))


if __name__ == "__main__":
    main()
