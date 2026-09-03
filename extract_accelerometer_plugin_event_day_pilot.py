"""Extract full local calendar-day general-ACC features for the first pilot patients.

The plugin activity dictionary supplies the eligibility context.  A plugin event
selects the patient/device/local date, but it does not restrict the ACC query to
the event minute: the complete local calendar day is queried.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from main import connect_sensordata_db


ROOT = Path(__file__).parent
TZ_NAME = "Asia/Jerusalem"
TABLE_NAME = "accelerometer"
MOVEMENT_DEVICE_DAYS_PATH = (
    ROOT
    / "output/analysis_candidates/plugin_activity_movement_dictionary/plugin_activity_device_day_summary.csv"
)
OUT_DIR = ROOT / "output/analysis_candidates/accelerometer_plugin_event_day_pilot"
FEATURE_WIDE_PATH = OUT_DIR / "accelerometer_plugin_event_day_features_wide.csv"
FEATURE_LONG_PATH = OUT_DIR / "accelerometer_plugin_event_day_features_long.csv"
PATIENT_DAY_PATH = OUT_DIR / "accelerometer_plugin_event_day_patient_day_features.csv"
CHUNK_PATH = OUT_DIR / "accelerometer_plugin_event_day_5min_summary.csv"
PREFLIGHT_PATH = OUT_DIR / "accelerometer_plugin_event_day_raw_preflight.csv"
STATUS_PATH = OUT_DIR / "accelerometer_plugin_event_day_status.csv"
CANDIDATE_PATH = OUT_DIR / "accelerometer_plugin_event_day_candidates.csv"
SUMMARY_PATH = OUT_DIR / "accelerometer_plugin_event_day_run_summary.csv"
CATALOG_PATH = OUT_DIR / "accelerometer_plugin_event_day_feature_catalog.csv"
CHECKPOINT_PATH = OUT_DIR / "accelerometer_plugin_event_day_checkpoint.json"
README_PATH = OUT_DIR / "README_accelerometer_plugin_event_day_pilot.md"

CHUNK_MINUTES = 5
SECONDS_PER_DAY = 24 * 60 * 60
LARGE_GAP_SECONDS = 1.0
MAX_JERK_INTERVAL_SECONDS = 5.0
LOW_MOTION_THRESHOLD = 0.10
MOTION_THRESHOLD = 0.20
HIGH_MOTION_THRESHOLD = 0.75


def configure_output_dir(output_dir: Path) -> None:
    """Redirect all generated files for an isolated cohort run."""
    global OUT_DIR, FEATURE_WIDE_PATH, FEATURE_LONG_PATH, PATIENT_DAY_PATH
    global CHUNK_PATH, PREFLIGHT_PATH, STATUS_PATH, CANDIDATE_PATH
    global SUMMARY_PATH, CATALOG_PATH, CHECKPOINT_PATH, README_PATH
    OUT_DIR = output_dir
    FEATURE_WIDE_PATH = OUT_DIR / "accelerometer_plugin_event_day_features_wide.csv"
    FEATURE_LONG_PATH = OUT_DIR / "accelerometer_plugin_event_day_features_long.csv"
    PATIENT_DAY_PATH = OUT_DIR / "accelerometer_plugin_event_day_patient_day_features.csv"
    CHUNK_PATH = OUT_DIR / "accelerometer_plugin_event_day_5min_summary.csv"
    PREFLIGHT_PATH = OUT_DIR / "accelerometer_plugin_event_day_raw_preflight.csv"
    STATUS_PATH = OUT_DIR / "accelerometer_plugin_event_day_status.csv"
    CANDIDATE_PATH = OUT_DIR / "accelerometer_plugin_event_day_candidates.csv"
    SUMMARY_PATH = OUT_DIR / "accelerometer_plugin_event_day_run_summary.csv"
    CATALOG_PATH = OUT_DIR / "accelerometer_plugin_event_day_feature_catalog.csv"
    CHECKPOINT_PATH = OUT_DIR / "accelerometer_plugin_event_day_checkpoint.json"
    README_PATH = OUT_DIR / "README_accelerometer_plugin_event_day_pilot.md"


FEATURE_CATALOG = [
    {
        "feature_name": "accelerometer_raw_row_count",
        "feature_group": "quality",
        "definition": "Number of raw general-accelerometer rows returned for the mapped device and local day.",
        "interpretation": "Collection volume; not a movement measure.",
    },
    {
        "feature_name": "accelerometer_valid_numeric_row_count",
        "feature_group": "quality",
        "definition": "Rows containing valid numeric x, y, and z values after JSON parsing.",
        "interpretation": "Usable signal count.",
    },
    {
        "feature_name": "accelerometer_exact_duplicate_rows_removed",
        "feature_group": "quality",
        "definition": "Duplicate rows with the same timestamp and all three signal values removed before feature calculation.",
        "interpretation": "Data-integrity audit measure.",
    },
    {
        "feature_name": "accelerometer_valid_signal_minutes",
        "feature_group": "quality",
        "definition": "Number of local clock minutes containing at least one valid three-axis signal.",
        "interpretation": "Observed time coverage; not equivalent to continuous recording.",
    },
    {
        "feature_name": "accelerometer_calendar_coverage_fraction",
        "feature_group": "quality",
        "definition": "Valid signal minutes divided by the number of minutes in the local calendar day.",
        "interpretation": "Coarse day-level coverage indicator.",
    },
    {
        "feature_name": "accelerometer_observed_span_hours",
        "feature_group": "quality",
        "definition": "Elapsed time from the first to the last valid signal in the day.",
        "interpretation": "Extent of the observed interval; gaps inside the interval remain possible.",
    },
    {
        "feature_name": "accelerometer_median_sampling_interval_ms",
        "feature_group": "quality",
        "definition": "Median positive interval between consecutive valid timestamps.",
        "interpretation": "Observed timing regularity and approximate sampling interval.",
    },
    {
        "feature_name": "accelerometer_p95_sampling_interval_ms",
        "feature_group": "quality",
        "definition": "95th percentile of positive intervals between consecutive valid timestamps.",
        "interpretation": "Tail of sampling gaps.",
    },
    {
        "feature_name": "accelerometer_gap_burden_fraction",
        "feature_group": "quality",
        "definition": "Seconds in gaps longer than one second divided by the 24-hour calendar day.",
        "interpretation": "Conservative fragmentation indicator; it is not missingness imputed as zero movement.",
    },
    {
        "feature_name": "accelerometer_magnitude_median",
        "feature_group": "signal_level",
        "definition": "Median vector magnitude sqrt(x^2 + y^2 + z^2).",
        "interpretation": "Includes gravity and phone orientation; not a direct body-acceleration measure.",
    },
    {
        "feature_name": "accelerometer_magnitude_sd",
        "feature_group": "signal_level",
        "definition": "Standard deviation of vector magnitude over valid samples.",
        "interpretation": "Overall signal variability, affected by orientation and collection context.",
    },
    {
        "feature_name": "accelerometer_magnitude_p95",
        "feature_group": "signal_level",
        "definition": "95th percentile of vector magnitude.",
        "interpretation": "Upper signal level, including gravity and phone-state effects.",
    },
    {
        "feature_name": "accelerometer_dynamic_magnitude_rms",
        "feature_group": "dynamic_motion",
        "definition": "Root-mean-square absolute deviation of magnitude from the day median magnitude.",
        "interpretation": "Orientation-tolerant motion proxy; not a validated activity classifier.",
    },
    {
        "feature_name": "accelerometer_dynamic_magnitude_p95",
        "feature_group": "dynamic_motion",
        "definition": "95th percentile absolute deviation of magnitude from the day median magnitude.",
        "interpretation": "Upper dynamic-motion proxy.",
    },
    {
        "feature_name": "accelerometer_low_motion_fraction",
        "feature_group": "dynamic_motion",
        "definition": "Fraction of valid samples with dynamic magnitude at or below 0.10.",
        "interpretation": "Low-variation phone-signal fraction; can reflect phone placement or no use.",
    },
    {
        "feature_name": "accelerometer_high_motion_fraction",
        "feature_group": "dynamic_motion",
        "definition": "Fraction of valid samples with dynamic magnitude at or above 0.75.",
        "interpretation": "High-variation phone-signal fraction; exploratory only.",
    },
    {
        "feature_name": "accelerometer_motion_bout_count",
        "feature_group": "temporal_pattern",
        "definition": "Runs of consecutive observed minutes whose median dynamic magnitude is at least 0.20.",
        "interpretation": "Number of separated active-looking periods; requires adequate minute coverage.",
    },
    {
        "feature_name": "accelerometer_longest_observed_quiet_interval_minutes",
        "feature_group": "temporal_pattern",
        "definition": "Longest run of consecutive observed minutes below the 0.20 motion threshold.",
        "interpretation": "Quiet interval among observed minutes; unobserved time is not labeled quiet.",
    },
    {
        "feature_name": "accelerometer_daytime_motion_minutes",
        "feature_group": "circadian",
        "definition": "Observed minutes with median dynamic magnitude at least 0.20 from 06:00 through 21:59 local time.",
        "interpretation": "Daytime motion proxy.",
    },
    {
        "feature_name": "accelerometer_nighttime_motion_minutes",
        "feature_group": "circadian",
        "definition": "Observed minutes with median dynamic magnitude at least 0.20 from 22:00 through 05:59 local time.",
        "interpretation": "Nighttime motion proxy.",
    },
    {
        "feature_name": "accelerometer_day_night_motion_ratio",
        "feature_group": "circadian",
        "definition": "Daytime motion minutes divided by nighttime motion minutes.",
        "interpretation": "Undefined when no nighttime motion minutes are observed.",
    },
    {
        "feature_name": "accelerometer_hourly_motion_entropy",
        "feature_group": "circadian",
        "definition": "Shannon entropy of active-looking observed minutes across local clock hours.",
        "interpretation": "Distribution of motion across the day; not a sleep measure.",
    },
    {
        "feature_name": "accelerometer_magnitude_jerk_median",
        "feature_group": "rapid_change",
        "definition": "Median absolute magnitude change per second for positive intervals no longer than five seconds.",
        "interpretation": "Signal-change-rate proxy; not clinical tremor or motor speed.",
    },
    {
        "feature_name": "accelerometer_magnitude_jerk_p95",
        "feature_group": "rapid_change",
        "definition": "95th percentile absolute magnitude change per second for positive intervals no longer than five seconds.",
        "interpretation": "Upper signal-change-rate proxy.",
    },
]
FEATURE_NAMES = [item["feature_name"] for item in FEATURE_CATALOG]
FEATURE_GROUPS = {item["feature_name"]: item["feature_group"] for item in FEATURE_CATALOG}


def numeric(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def parse_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if not isinstance(raw, str):
        return {}
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def local_day_bounds(local_date: str) -> tuple[int, int, str, str]:
    start = pd.Timestamp(local_date).tz_localize(TZ_NAME)
    end = (start + pd.Timedelta(days=1)).tz_convert(TZ_NAME)
    start_ms = int(start.tz_convert("UTC").timestamp() * 1000)
    end_ms = int(end.tz_convert("UTC").timestamp() * 1000)
    return start_ms, end_ms, start.isoformat(), end.isoformat()


def local_text(timestamp_ms: int | float | None) -> str:
    if timestamp_ms is None or pd.isna(timestamp_ms):
        return ""
    return pd.to_datetime(int(timestamp_ms), unit="ms", utc=True).tz_convert(TZ_NAME).strftime(
        "%Y-%m-%d %H:%M:%S%z"
    )


def normalize_patient_id(value: Any) -> str:
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def load_candidates(limit_patients: int) -> pd.DataFrame:
    if not MOVEMENT_DEVICE_DAYS_PATH.exists():
        raise FileNotFoundError(f"Missing movement dictionary: {MOVEMENT_DEVICE_DAYS_PATH}")
    device_days = pd.read_csv(MOVEMENT_DEVICE_DAYS_PATH, dtype=str)
    device_days["patient_id"] = device_days["patient_id"].map(normalize_patient_id)
    device_days["local_date"] = pd.to_datetime(device_days["local_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    device_days = device_days.dropna(subset=["patient_id", "device_id", "local_date"]).copy()
    patient_ids = sorted(device_days["patient_id"].unique(), key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value))
    selected_patients = patient_ids[:limit_patients] if limit_patients > 0 else patient_ids
    candidates = device_days[device_days["patient_id"].isin(selected_patients)].copy()
    candidates = candidates.drop_duplicates(["patient_id", "device_id", "local_date"])
    candidates["candidate_id"] = candidates.apply(
        lambda row: f"{row['patient_id']}__{row['device_id']}__{row['local_date']}", axis=1
    )
    starts: list[int] = []
    ends: list[int] = []
    start_local: list[str] = []
    end_local: list[str] = []
    for local_date in candidates["local_date"]:
        start_ms, end_ms, start_text, end_text = local_day_bounds(local_date)
        starts.append(start_ms)
        ends.append(end_ms)
        start_local.append(start_text)
        end_local.append(end_text)
    candidates["window_start_ms"] = starts
    candidates["window_end_ms_exclusive"] = ends
    candidates["window_start_local"] = start_local
    candidates["window_end_local_exclusive"] = end_local
    return candidates.sort_values(["patient_id", "local_date", "device_id"]).reset_index(drop=True)


def raw_preflight(conn: Any, candidate: pd.Series) -> dict[str, Any]:
    # Use a bounded existence probe; exact counts are collected during extraction.
    cur = conn.cursor(dictionary=True, buffered=True)
    try:
        cur.execute(
            """
            SELECT timestamp AS first_timestamp_ms
            FROM `accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (
                str(candidate["device_id"]),
                int(candidate["window_start_ms"]),
                int(candidate["window_end_ms_exclusive"]),
            ),
        )
        result = cur.fetchone() or {}
    finally:
        cur.close()
    first_ts = result.get("first_timestamp_ms")
    has_rows = first_ts is not None and not pd.isna(first_ts)
    return {
        "candidate_id": candidate["candidate_id"],
        "patient_id": candidate["patient_id"],
        "device_id": candidate["device_id"],
        "local_date": candidate["local_date"],
        "window_start_local": candidate["window_start_local"],
        "window_end_local_exclusive": candidate["window_end_local_exclusive"],
        "plugin_event_count": candidate.get("plugin_event_count", ""),
        "plugin_dominant_movement_evidence_class": candidate.get("dominant_movement_evidence_class", ""),
        "raw_row_count": "",
        "first_raw_time_local": local_text(first_ts),
        "last_raw_time_local": "",
        "raw_data_available": int(has_rows),
        "preflight_status": "has_raw_rows" if has_rows else "no_raw_rows",
    }


def batch_raw_preflight(conn: Any, candidates: list[pd.Series]) -> dict[str, dict[str, Any]]:
    """Check many candidate windows with bounded existence probes.

    This intentionally does not run COUNT/MIN/MAX over the raw signal table.
    Exact row counts and last timestamps are collected only for windows that
    pass this probe and are subsequently streamed for feature calculation.
    """
    if not candidates:
        return {}
    fragments: list[str] = []
    parameters: list[Any] = []
    for candidate in candidates:
        fragments.append(
            """
            SELECT %s AS candidate_id,
                   MIN(probe.timestamp) AS first_timestamp_ms
            FROM (
                SELECT timestamp
                FROM `accelerometer`
                WHERE device_id = %s
                  AND timestamp >= %s
                  AND timestamp < %s
                ORDER BY timestamp ASC
                LIMIT 1
            ) AS probe
            """
        )
        parameters.extend(
            [
                str(candidate["candidate_id"]),
                str(candidate["device_id"]),
                int(candidate["window_start_ms"]),
                int(candidate["window_end_ms_exclusive"]),
            ]
        )
    cur = conn.cursor(dictionary=True, buffered=True)
    try:
        cur.execute(" UNION ALL ".join(fragments), tuple(parameters))
        rows = cur.fetchall()
    finally:
        cur.close()
    return {str(row["candidate_id"]): row for row in rows}


def fetch_raw_records(conn: Any, candidate: pd.Series, batch_rows: int) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Stream one day and retain only compact timestamp/magnitude arrays."""
    timestamp_parts: list[np.ndarray] = []
    magnitude_parts: list[np.ndarray] = []
    counters = Counter()
    previous_key: tuple[int, float, float, float] | None = None
    cur = conn.cursor(dictionary=True, buffered=False)
    try:
        cur.execute(
            """
            SELECT timestamp, device_id,
                   data->>'$.double_values_0' AS x,
                   data->>'$.double_values_1' AS y,
                   data->>'$.double_values_2' AS z
            FROM `accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            """,
            (
                str(candidate["device_id"]),
                int(candidate["window_start_ms"]),
                int(candidate["window_end_ms_exclusive"]),
            ),
        )
        while True:
            batch = cur.fetchmany(batch_rows)
            if not batch:
                break
            counters["raw_rows"] += len(batch)
            frame = pd.DataFrame(batch)
            frame["timestamp"] = pd.to_numeric(frame["timestamp"], errors="coerce")
            for column in ["x", "y", "z"]:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
            invalid_timestamp = frame["timestamp"].isna()
            invalid_signal = frame[["x", "y", "z"]].isna().any(axis=1)
            counters["invalid_timestamp_rows"] += int(invalid_timestamp.sum())
            counters["invalid_signal_rows"] += int((~invalid_timestamp & invalid_signal).sum())
            frame = frame[~invalid_timestamp & ~invalid_signal][["timestamp", "x", "y", "z"]].copy()
            if frame.empty:
                continue
            frame["timestamp"] = frame["timestamp"].astype("int64")
            frame = frame.drop_duplicates(["timestamp", "x", "y", "z"], keep="first")
            if frame.empty:
                continue
            if previous_key is not None:
                first = frame.iloc[0]
                first_key = (int(first["timestamp"]), float(first["x"]), float(first["y"]), float(first["z"]))
                if first_key == previous_key:
                    frame = frame.iloc[1:].copy()
            if frame.empty:
                continue
            counters["duplicate_rows"] += (
                len(batch)
                - int(invalid_timestamp.sum())
                - int((~invalid_timestamp & invalid_signal).sum())
                - len(frame)
            )
            last = frame.iloc[-1]
            previous_key = (int(last["timestamp"]), float(last["x"]), float(last["y"]), float(last["z"]))
            timestamp_parts.append(frame["timestamp"].to_numpy(dtype=np.int64))
            magnitude_parts.append(
                np.sqrt(
                    frame["x"].to_numpy(dtype=float) ** 2
                    + frame["y"].to_numpy(dtype=float) ** 2
                    + frame["z"].to_numpy(dtype=float) ** 2
                )
            )
    finally:
        cur.close()
    if not timestamp_parts:
        return np.array([], dtype=np.int64), np.array([], dtype=float), dict(counters)
    return np.concatenate(timestamp_parts), np.concatenate(magnitude_parts), dict(counters)


def fetch_raw_records_for_group(
    conn: Any, candidates: list[pd.Series], batch_rows: int
):
    """Yield compact day results from one bounded query covering several dates."""
    if not candidates:
        return
    ordered = sorted(candidates, key=lambda row: (str(row["local_date"]), str(row["candidate_id"])))
    device_id = str(ordered[0]["device_id"])
    conditions = " OR ".join("(timestamp >= %s AND timestamp < %s)" for _ in ordered)
    parameters: list[Any] = [device_id]
    for candidate in ordered:
        parameters.extend([int(candidate["window_start_ms"]), int(candidate["window_end_ms_exclusive"])])
    cur = conn.cursor(dictionary=True, buffered=False)
    pointer = 0
    timestamp_parts: list[np.ndarray] = []
    magnitude_parts: list[np.ndarray] = []
    counters: Counter[str] = Counter()
    previous_key: tuple[int, float, float, float] | None = None

    def reset_day() -> None:
        nonlocal timestamp_parts, magnitude_parts, counters, previous_key
        timestamp_parts = []
        magnitude_parts = []
        counters = Counter()
        previous_key = None

    def finish_day(candidate: pd.Series):
        nonlocal timestamp_parts, magnitude_parts, counters
        if timestamp_parts:
            timestamps = np.concatenate(timestamp_parts)
            magnitudes = np.concatenate(magnitude_parts)
        else:
            timestamps = np.array([], dtype=np.int64)
            magnitudes = np.array([], dtype=float)
        result_counters = dict(counters)
        result_counters["raw_rows"] = int(result_counters.get("raw_rows", 0))
        yield candidate, timestamps, magnitudes, result_counters
        reset_day()

    try:
        cur.execute(
            f"""
            SELECT timestamp, device_id,
                   data->>'$.double_values_0' AS x,
                   data->>'$.double_values_1' AS y,
                   data->>'$.double_values_2' AS z
            FROM `accelerometer`
            WHERE device_id = %s
              AND ({conditions})
            ORDER BY timestamp ASC
            """,
            tuple(parameters),
        )
        while True:
            batch = cur.fetchmany(batch_rows)
            if not batch:
                break
            raw_frame = pd.DataFrame(batch)
            raw_frame["timestamp"] = pd.to_numeric(raw_frame["timestamp"], errors="coerce")
            for column in ["x", "y", "z"]:
                raw_frame[column] = pd.to_numeric(raw_frame[column], errors="coerce")
            timestamp_frame = raw_frame[raw_frame["timestamp"].notna()].copy()
            if timestamp_frame.empty:
                counters["unassigned_invalid_timestamp_rows"] += len(raw_frame)
                continue
            timestamp_frame["timestamp"] = timestamp_frame["timestamp"].astype("int64")
            batch_min = int(timestamp_frame["timestamp"].min())
            batch_max = int(timestamp_frame["timestamp"].max())

            while pointer < len(ordered):
                candidate = ordered[pointer]
                start_ms = int(candidate["window_start_ms"])
                end_ms = int(candidate["window_end_ms_exclusive"])
                if batch_max < start_ms:
                    break
                if batch_min >= end_ms:
                    yield from finish_day(candidate)
                    pointer += 1
                    continue

                subset = timestamp_frame[
                    (timestamp_frame["timestamp"] >= start_ms) & (timestamp_frame["timestamp"] < end_ms)
                ]
                if not subset.empty:
                    counters["raw_rows"] += len(subset)
                    first_raw = int(subset["timestamp"].min())
                    last_raw = int(subset["timestamp"].max())
                    counters["first_raw_timestamp_ms"] = min(
                        int(counters.get("first_raw_timestamp_ms", first_raw)), first_raw
                    )
                    counters["last_raw_timestamp_ms"] = max(
                        int(counters.get("last_raw_timestamp_ms", last_raw)), last_raw
                    )
                    invalid_signal = subset[["x", "y", "z"]].isna().any(axis=1)
                    counters["invalid_signal_rows"] += int(invalid_signal.sum())
                    valid = subset[~invalid_signal][["timestamp", "x", "y", "z"]].copy()
                    if not valid.empty:
                        valid = valid.drop_duplicates(["timestamp", "x", "y", "z"], keep="first")
                        if previous_key is not None and not valid.empty:
                            first = valid.iloc[0]
                            first_key = (int(first["timestamp"]), float(first["x"]), float(first["y"]), float(first["z"]))
                            if first_key == previous_key:
                                valid = valid.iloc[1:].copy()
                        counters["duplicate_rows"] += len(subset) - int(invalid_signal.sum()) - len(valid)
                        if not valid.empty:
                            last = valid.iloc[-1]
                            previous_key = (int(last["timestamp"]), float(last["x"]), float(last["y"]), float(last["z"]))
                            timestamp_parts.append(valid["timestamp"].to_numpy(dtype=np.int64))
                            magnitude_parts.append(
                                np.sqrt(
                                    valid["x"].to_numpy(dtype=float) ** 2
                                    + valid["y"].to_numpy(dtype=float) ** 2
                                    + valid["z"].to_numpy(dtype=float) ** 2
                                )
                            )
                if batch_max >= end_ms:
                    yield from finish_day(candidate)
                    pointer += 1
                    continue
                break
    finally:
        cur.close()
    while pointer < len(ordered):
        yield from finish_day(ordered[pointer])
        pointer += 1


def longest_quiet_run(active: np.ndarray, minute_keys: np.ndarray) -> int:
    if len(active) == 0:
        return 0
    best = current = 0
    one_minute_ms = 60_000
    for index, value in enumerate(active):
        if index and minute_keys[index] - minute_keys[index - 1] != one_minute_ms:
            current = 0
        current = current + 1 if not value else 0
        best = max(best, current)
    return best


def count_bouts(active: np.ndarray, minute_keys: np.ndarray) -> int:
    if len(active) == 0:
        return 0
    one_minute_ms = 60_000
    starts = active.copy()
    starts[1:] &= minute_keys[1:] - minute_keys[:-1] != one_minute_ms
    return int(starts.sum())


def entropy_from_hours(hours: np.ndarray) -> float:
    if len(hours) == 0:
        return float("nan")
    _, counts = np.unique(hours, return_counts=True)
    probabilities = counts / counts.sum()
    return float(-(probabilities * np.log2(probabilities)).sum())


def analyze_day_arrays(
    candidate: pd.Series,
    timestamps: np.ndarray,
    magnitude: np.ndarray,
    counters: dict[str, int],
) -> tuple[dict[str, Any], pd.DataFrame]:
    base = {
        "candidate_id": candidate["candidate_id"],
        "patient_id": candidate["patient_id"],
        "device_id": candidate["device_id"],
        "local_date": candidate["local_date"],
        "window_start_local": candidate["window_start_local"],
        "window_end_local_exclusive": candidate["window_end_local_exclusive"],
        "plugin_event_count": candidate.get("plugin_event_count", ""),
        "plugin_dominant_movement_evidence_class": candidate.get("dominant_movement_evidence_class", ""),
        "plugin_observed_minutes": candidate.get("n_observed_minutes", ""),
    }
    empty_values = {name: float("nan") for name in FEATURE_NAMES}
    empty_values.update(
        {
            "accelerometer_raw_row_count": counters.get("raw_rows", 0),
            "accelerometer_valid_numeric_row_count": 0,
            "accelerometer_exact_duplicate_rows_removed": 0,
            "accelerometer_valid_signal_minutes": 0,
            "accelerometer_calendar_coverage_fraction": 0.0,
        }
    )
    if len(timestamps) == 0:
        return {**base, **empty_values}, pd.DataFrame()
    order = np.argsort(timestamps, kind="stable")
    timestamps = timestamps[order]
    magnitude = magnitude[order]
    intervals_ms = np.diff(timestamps)
    positive_intervals_ms = intervals_ms[intervals_ms > 0]
    gap_seconds = positive_intervals_ms / 1000.0
    first_ts = int(timestamps[0])
    last_ts = int(timestamps[-1])
    observed_span_hours = max((last_ts - first_ts) / 3_600_000.0, 0.0)
    magnitude = magnitude.astype(float, copy=False)
    baseline = float(np.median(magnitude))
    dynamic = np.abs(magnitude - baseline)
    dt_local = pd.to_datetime(timestamps, unit="ms", utc=True).tz_convert(TZ_NAME)
    local_minutes = dt_local.floor("min")
    local_minute_keys = local_minutes.asi8
    local_hours = np.asarray(dt_local.hour, dtype=int)
    valid_minutes = int(len(np.unique(local_minute_keys)))
    _, end_ms, _, _ = local_day_bounds(str(candidate["local_date"]))
    day_start_ms = int(candidate["window_start_ms"])
    calendar_minutes = max(int(round((end_ms - day_start_ms) / 60_000)), 1)

    minute_keys, minute_starts, minute_counts = np.unique(
        local_minute_keys, return_index=True, return_counts=True
    )
    minute_dynamic_median = np.asarray(
        [np.median(dynamic[start : start + count]) for start, count in zip(minute_starts, minute_counts)]
    )
    minute_hours = local_hours[minute_starts]
    minute_active = minute_dynamic_median >= MOTION_THRESHOLD
    day_motion_minutes = int((minute_active & np.isin(minute_hours, np.arange(6, 22))).sum())
    night_motion_minutes = int((minute_active & ((minute_hours < 6) | (minute_hours >= 22))).sum())
    active_hours = minute_hours[minute_active]

    positive_interval_mask = intervals_ms > 0
    interval_seconds = intervals_ms[positive_interval_mask] / 1000.0
    valid_jerk_intervals = interval_seconds <= MAX_JERK_INTERVAL_SECONDS
    magnitude_deltas = np.abs(np.diff(magnitude))[positive_interval_mask]
    jerk = magnitude_deltas[valid_jerk_intervals] / interval_seconds[valid_jerk_intervals]

    gap_seconds_total = float(gap_seconds[gap_seconds > LARGE_GAP_SECONDS].sum()) if len(gap_seconds) else 0.0
    feature_values = {
        "accelerometer_raw_row_count": int(counters.get("raw_rows", 0)),
        "accelerometer_valid_numeric_row_count": int(len(timestamps)),
        "accelerometer_exact_duplicate_rows_removed": int(counters.get("duplicate_rows", 0)),
        "accelerometer_valid_signal_minutes": valid_minutes,
        "accelerometer_calendar_coverage_fraction": valid_minutes / calendar_minutes,
        "accelerometer_observed_span_hours": observed_span_hours,
        "accelerometer_median_sampling_interval_ms": float(np.median(positive_intervals_ms)) if len(positive_intervals_ms) else float("nan"),
        "accelerometer_p95_sampling_interval_ms": float(np.percentile(positive_intervals_ms, 95)) if len(positive_intervals_ms) else float("nan"),
        "accelerometer_gap_burden_fraction": min(gap_seconds_total / SECONDS_PER_DAY, 1.0),
        "accelerometer_magnitude_median": baseline,
        "accelerometer_magnitude_sd": float(np.std(magnitude)),
        "accelerometer_magnitude_p95": float(np.percentile(magnitude, 95)),
        "accelerometer_dynamic_magnitude_rms": float(np.sqrt(np.mean(dynamic ** 2))),
        "accelerometer_dynamic_magnitude_p95": float(np.percentile(dynamic, 95)),
        "accelerometer_low_motion_fraction": float(np.mean(dynamic <= LOW_MOTION_THRESHOLD)),
        "accelerometer_high_motion_fraction": float(np.mean(dynamic >= HIGH_MOTION_THRESHOLD)),
        "accelerometer_motion_bout_count": count_bouts(minute_active, minute_keys),
        "accelerometer_longest_observed_quiet_interval_minutes": longest_quiet_run(~minute_active, minute_keys),
        "accelerometer_daytime_motion_minutes": day_motion_minutes,
        "accelerometer_nighttime_motion_minutes": night_motion_minutes,
        "accelerometer_day_night_motion_ratio": day_motion_minutes / night_motion_minutes if night_motion_minutes else float("nan"),
        "accelerometer_hourly_motion_entropy": entropy_from_hours(active_hours),
        "accelerometer_magnitude_jerk_median": float(np.median(jerk)) if len(jerk) else float("nan"),
        "accelerometer_magnitude_jerk_p95": float(np.percentile(jerk, 95)) if len(jerk) else float("nan"),
    }
    chunk_keys, chunk_starts, chunk_counts = np.unique(
        local_minute_keys // (CHUNK_MINUTES * 60_000),
        return_index=True,
        return_counts=True,
    )
    chunk_rows: list[dict[str, Any]] = []
    for start, count in zip(chunk_starts, chunk_counts):
        chunk_dynamic = dynamic[start : start + count]
        chunk_magnitude = magnitude[start : start + count]
        chunk_rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "patient_id": candidate["patient_id"],
                "device_id": candidate["device_id"],
                "local_date": candidate["local_date"],
                "chunk_start_local": str(local_minutes[start]),
                "valid_sample_count": int(count),
                "median_magnitude": float(np.median(chunk_magnitude)),
                "median_dynamic_magnitude": float(np.median(chunk_dynamic)),
                "mean_dynamic_magnitude": float(np.mean(chunk_dynamic)),
            }
        )
    chunk = pd.DataFrame(chunk_rows)
    if not chunk.empty:
        chunk["chunk_state"] = np.select(
            [
                chunk["median_dynamic_magnitude"] <= LOW_MOTION_THRESHOLD,
                chunk["median_dynamic_magnitude"] >= HIGH_MOTION_THRESHOLD,
                chunk["median_dynamic_magnitude"] >= MOTION_THRESHOLD,
            ],
            ["low_motion", "high_motion", "motion"],
            default="intermediate_motion",
        )
    return {**base, **feature_values}, chunk


def analyze_day(candidate: pd.Series, records: list[dict[str, Any]], counters: dict[str, int]) -> tuple[dict[str, Any], pd.DataFrame]:
    """Small in-memory wrapper used by local unit tests and examples."""
    if not records:
        return analyze_day_arrays(candidate, np.array([], dtype=np.int64), np.array([], dtype=float), counters)
    frame = pd.DataFrame(records)
    frame = frame.drop_duplicates(["timestamp_ms", "x", "y", "z"], keep="first")
    counters = dict(counters)
    counters["duplicate_rows"] = counters.get("duplicate_rows", 0) + len(records) - len(frame)
    timestamps = frame["timestamp_ms"].to_numpy(dtype=np.int64)
    magnitude = np.sqrt(
        frame["x"].to_numpy(dtype=float) ** 2
        + frame["y"].to_numpy(dtype=float) ** 2
        + frame["z"].to_numpy(dtype=float) ** 2
    )
    return analyze_day_arrays(candidate, timestamps, magnitude, counters)


def append_frame(path: Path, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    if frame.empty:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns:
        frame = frame.reindex(columns=columns)
    frame.to_csv(path, mode="a", header=not path.exists() or path.stat().st_size == 0, index=False)


def build_long(features: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "candidate_id": features["candidate_id"],
                "patient_id": features["patient_id"],
                "device_id": features["device_id"],
                "local_date": features["local_date"],
                "feature_name": name,
                "feature_group": FEATURE_GROUPS[name],
                "value": features.get(name, float("nan")),
            }
            for name in FEATURE_NAMES
        ]
    )


def build_patient_day_features(wide: pd.DataFrame) -> pd.DataFrame:
    if wide.empty:
        return pd.DataFrame()
    numeric_columns = [column for column in FEATURE_NAMES if column in wide.columns]
    rows: list[dict[str, Any]] = []
    for (patient_id, local_date), group in wide.groupby(["patient_id", "local_date"], dropna=False):
        row: dict[str, Any] = {
            "patient_id": patient_id,
            "local_date": local_date,
            "device_count": int(group["device_id"].nunique()),
            "source_device_day_count": int(len(group)),
            "plugin_event_count": pd.to_numeric(group.get("plugin_event_count"), errors="coerce").sum(),
        }
        for name in numeric_columns:
            values = pd.to_numeric(group[name], errors="coerce")
            if name.endswith("_count") or name.endswith("_minutes") or name.endswith("_row_count"):
                row[name] = float(values.sum(min_count=1)) if values.notna().any() else float("nan")
            else:
                row[name] = float(values.mean()) if values.notna().any() else float("nan")
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["patient_id", "local_date"]).reset_index(drop=True)


def write_catalog() -> None:
    pd.DataFrame(FEATURE_CATALOG).to_csv(CATALOG_PATH, index=False)


def write_summary(candidates: pd.DataFrame, preflight: pd.DataFrame, status: pd.DataFrame, wide: pd.DataFrame) -> None:
    status_text = status.get("status", pd.Series(dtype=str)).astype(str) if not status.empty else pd.Series(dtype=str)
    raw_counts = pd.to_numeric(preflight.get("raw_row_count", pd.Series(dtype=float)), errors="coerce") if not preflight.empty else pd.Series(dtype=float)
    preflight_text = preflight.get("preflight_status", pd.Series(dtype=str)).astype(str) if not preflight.empty else pd.Series(dtype=str)
    summary = pd.DataFrame(
        [
            {"metric": "selected_patient_count", "value": candidates["patient_id"].nunique() if not candidates.empty else 0},
            {"metric": "selected_patients", "value": ", ".join(sorted(candidates["patient_id"].unique())) if not candidates.empty else ""},
            {"metric": "candidate_device_day_count", "value": len(candidates)},
            {"metric": "preflight_days_with_raw_rows", "value": int(preflight_text.eq("has_raw_rows").sum())},
            {"metric": "completed_device_day_features", "value": int(status_text.eq("features_calculated").sum())},
            {"metric": "days_without_raw_rows", "value": int(preflight_text.eq("no_raw_rows").sum())},
            {"metric": "failed_device_day_extractions", "value": int(preflight_text.eq("error").sum())},
            {"metric": "pending_device_days", "value": int(preflight_text.eq("pending").sum())},
            {"metric": "total_raw_rows_preflight", "value": int(raw_counts.sum()) if not raw_counts.empty else 0},
            {"metric": "feature_rows_written", "value": len(wide)},
            {"metric": "feature_count", "value": len(FEATURE_NAMES)},
        ]
    )
    summary.to_csv(SUMMARY_PATH, index=False)


def write_readme(candidates: pd.DataFrame, preflight: pd.DataFrame, status: pd.DataFrame) -> None:
    status_counts = status["status"].value_counts().to_dict() if not status.empty and "status" in status else {}
    raw_count = int(pd.to_numeric(preflight.get("raw_row_count", pd.Series(dtype=float)), errors="coerce").sum()) if not preflight.empty else 0
    pending_count = int(preflight.get("preflight_status", pd.Series(dtype=str)).astype(str).eq("pending").sum()) if not preflight.empty else len(candidates) - len(status)
    patient_list = ", ".join(sorted(candidates["patient_id"].unique())) if not candidates.empty else "none"
    text = f"""# General Accelerometer Full-Day Pilot Anchored by Plugin Movement Events

This is a separate exploratory pilot. It does not modify the existing Phase 3 or patient-level ACC outputs.

## Protocol

- Source context: the mapped `plugin_google_activity_recognition` movement dictionary.
- Patients represented in this run: `{patient_list}`.
- Unit of extraction: one unique patient-device-local-calendar-day with at least one plugin movement event.
- A plugin event selects the day; the ACC query covers the complete local day from local midnight inclusive to the next local midnight exclusive in `{TZ_NAME}`.
- Only mapped device IDs are queried. The plugin event minute is retained as context and is not used to limit the ACC signal.
- Raw SQL is bounded by both `device_id` and timestamp. Raw ACC rows are streamed from SQL and are not copied into this pilot output.
- General ACC contains gravity. Vector magnitude and deviation from the day median are used as signal summaries; these are phone-signal proxies, not validated clinical movement measures.
- Exact duplicate rows with identical timestamp and x/y/z are removed before feature calculation. Invalid JSON or incomplete axes remain in QC counts and are not converted to zero.
- Missing raw ACC produces a status row and missing features; no movement is imputed.

## Feature bundle

The pilot calculates {len(FEATURE_NAMES)} features across quality/coverage, signal level, dynamic motion, temporal pattern, circadian pattern, and rapid signal-change groups. The complete definitions are in `{CATALOG_PATH.name}`.

The 5-minute table is descriptive QC. Frequency-domain features are intentionally deferred until sampling regularity and adequate signal duration are reviewed; no frequency band is called walking, tremor, or another clinical behavior in this pilot.

## Current run accounting

- Candidate device-days: {len(candidates)}
- Device-days with a recorded status: {len(status)}
- Device-days still pending: {pending_count}
- Known raw rows counted during extraction: {raw_count:,}
- Status counts: {status_counts}

## Outputs

- `{CANDIDATE_PATH.name}`: candidate event-day manifest and plugin context.
- `{PREFLIGHT_PATH.name}`: bounded raw-ACC availability and first raw timestamp; exact counts and final timestamps are filled during extraction.
- `{FEATURE_WIDE_PATH.name}`: one row per patient-device-day with calculated features.
- `{PATIENT_DAY_PATH.name}`: one row per patient-local-day, aggregating devices.
- `{FEATURE_LONG_PATH.name}`: tidy feature/value representation.
- `{CHUNK_PATH.name}`: observed 5-minute signal summaries and coarse state labels.
- `{STATUS_PATH.name}`: extraction status, raw and valid row counts, and errors.
- `{CATALOG_PATH.name}`: feature definitions and interpretation cautions.

This is a method-development extraction. It is not a patient-level model, a clinical validation, or evidence of a digital biomarker.

This saved snapshot is partial when `Device-days still pending` is greater than zero. Error rows record database transport or prior interrupted calculation attempts and must be retried before the pilot is treated as a complete event-day audit.
"""
    README_PATH.write_text(text, encoding="utf-8")


def fetch_raw_records_for_local_day(
    conn: Any, candidates: list[pd.Series], batch_rows: int
):
    """Stream one local day for all mapped devices that have a candidate.

    The raw table is indexed by timestamp first and device ID second. Querying
    one device at a time therefore rescans the same day repeatedly. This
    day-oriented query scans the timestamp range once, keeps only candidate
    devices, and then assigns rows to their patient-device-day buffers.
    """
    if not candidates:
        return
    ordered = sorted(candidates, key=lambda row: (str(row["device_id"]), str(row["candidate_id"])))
    device_to_candidates: dict[str, list[str]] = {}
    candidate_by_id: dict[str, pd.Series] = {}
    for candidate in ordered:
        device_to_candidates.setdefault(str(candidate["device_id"]), []).append(str(candidate["candidate_id"]))
        candidate_by_id[str(candidate["candidate_id"])] = candidate
    device_ids = list(device_to_candidates)
    placeholders = ", ".join("%s" for _ in device_ids)
    day_start_ms = min(int(candidate["window_start_ms"]) for candidate in ordered)
    day_end_ms = max(int(candidate["window_end_ms_exclusive"]) for candidate in ordered)

    timestamp_parts: dict[str, list[np.ndarray]] = {candidate_id: [] for candidate_id in candidate_by_id}
    magnitude_parts: dict[str, list[np.ndarray]] = {candidate_id: [] for candidate_id in candidate_by_id}
    counters: dict[str, Counter[str]] = {candidate_id: Counter() for candidate_id in candidate_by_id}
    previous_keys: dict[str, tuple[int, float, float, float] | None] = {
        candidate_id: None for candidate_id in candidate_by_id
    }
    cur = conn.cursor(dictionary=True, buffered=False)
    try:
        cur.execute(
            f"""
            SELECT timestamp, device_id,
                   data->>'$.double_values_0' AS x,
                   data->>'$.double_values_1' AS y,
                   data->>'$.double_values_2' AS z
            FROM `accelerometer`
            WHERE timestamp >= %s
              AND timestamp < %s
              AND device_id IN ({placeholders})
            ORDER BY timestamp ASC
            """,
            tuple([day_start_ms, day_end_ms, *device_ids]),
        )
        while True:
            batch = cur.fetchmany(batch_rows)
            if not batch:
                break
            raw_frame = pd.DataFrame(batch)
            raw_frame["device_id"] = raw_frame["device_id"].astype(str)
            raw_frame["timestamp"] = pd.to_numeric(raw_frame["timestamp"], errors="coerce")
            for column in ["x", "y", "z"]:
                raw_frame[column] = pd.to_numeric(raw_frame[column], errors="coerce")
            for device_id, device_frame in raw_frame.groupby("device_id", sort=False):
                candidate_ids = device_to_candidates.get(str(device_id), [])
                if not candidate_ids:
                    continue
                for candidate_id in candidate_ids:
                    candidate_counters = counters[candidate_id]
                    candidate_counters["raw_rows"] += len(device_frame)
                    invalid_timestamp = device_frame["timestamp"].isna()
                    invalid_signal = device_frame[["x", "y", "z"]].isna().any(axis=1)
                    candidate_counters["invalid_timestamp_rows"] += int(invalid_timestamp.sum())
                    candidate_counters["invalid_signal_rows"] += int((~invalid_timestamp & invalid_signal).sum())
                    frame = device_frame[~invalid_timestamp & ~invalid_signal][["timestamp", "x", "y", "z"]].copy()
                    if frame.empty:
                        continue
                    frame["timestamp"] = frame["timestamp"].astype("int64")
                    frame = frame.drop_duplicates(["timestamp", "x", "y", "z"], keep="first")
                    if frame.empty:
                        continue
                    previous_key = previous_keys[candidate_id]
                    if previous_key is not None:
                        first = frame.iloc[0]
                        first_key = (int(first["timestamp"]), float(first["x"]), float(first["y"]), float(first["z"]))
                        if first_key == previous_key:
                            frame = frame.iloc[1:].copy()
                    candidate_counters["duplicate_rows"] += len(device_frame) - int(invalid_timestamp.sum()) - int(
                        (~invalid_timestamp & invalid_signal).sum()
                    ) - len(frame)
                    if frame.empty:
                        continue
                    first_timestamp = int(frame["timestamp"].min())
                    last_timestamp = int(frame["timestamp"].max())
                    existing_first = candidate_counters.get("first_raw_timestamp_ms")
                    existing_last = candidate_counters.get("last_raw_timestamp_ms")
                    candidate_counters["first_raw_timestamp_ms"] = (
                        first_timestamp if existing_first is None else min(int(existing_first), first_timestamp)
                    )
                    candidate_counters["last_raw_timestamp_ms"] = (
                        last_timestamp if existing_last is None else max(int(existing_last), last_timestamp)
                    )
                    last = frame.iloc[-1]
                    previous_keys[candidate_id] = (
                        int(last["timestamp"]), float(last["x"]), float(last["y"]), float(last["z"])
                    )
                    timestamp_parts[candidate_id].append(frame["timestamp"].to_numpy(dtype=np.int64))
                    magnitude_parts[candidate_id].append(
                        np.sqrt(
                            frame["x"].to_numpy(dtype=float) ** 2
                            + frame["y"].to_numpy(dtype=float) ** 2
                            + frame["z"].to_numpy(dtype=float) ** 2
                        )
                    )
    finally:
        cur.close()

    for candidate in ordered:
        candidate_id = str(candidate["candidate_id"])
        if timestamp_parts[candidate_id]:
            timestamps = np.concatenate(timestamp_parts[candidate_id])
            magnitudes = np.concatenate(magnitude_parts[candidate_id])
        else:
            timestamps = np.array([], dtype=np.int64)
            magnitudes = np.array([], dtype=float)
        yield candidate, timestamps, magnitudes, dict(counters[candidate_id])


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract full local ACC days for first patients with plugin movement events.")
    parser.add_argument("--limit-patients", type=int, default=2)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUT_DIR,
        help="Directory for this cohort run; use a new directory to preserve an earlier pilot.",
    )
    parser.add_argument("--batch-rows", type=int, default=100000)
    parser.add_argument(
        "--days-per-query",
        type=int,
        default=1,
        help="Use one day per query by default; grouped ranges are experimental for this remote database.",
    )
    parser.add_argument(
        "--preflight-batch-days",
        type=int,
        default=25,
        help="Initial number of candidate days checked together for raw-row availability before signal streaming; failed batches split automatically.",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip raw-table COUNT/probe preflight and discover empty windows during extraction.",
    )
    parser.add_argument(
        "--query-by-local-day",
        action="store_true",
        help="Scan each local calendar day once for all candidate devices; useful with the timestamp-first ACC index.",
    )
    parser.add_argument(
        "--finalize-only",
        action="store_true",
        help="Rebuild derived pilot outputs from recorded files without connecting to SQL.",
    )
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    configure_output_dir(args.output_dir)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates(args.limit_patients)
    candidates.to_csv(CANDIDATE_PATH, index=False)
    write_catalog()

    if args.finalize_only:
        status_df = pd.read_csv(STATUS_PATH, dtype=str) if STATUS_PATH.exists() else pd.DataFrame()
        wide_df = pd.read_csv(FEATURE_WIDE_PATH, dtype=str) if FEATURE_WIDE_PATH.exists() else pd.DataFrame()
        preflight_df = pd.read_csv(PREFLIGHT_PATH, dtype=str) if PREFLIGHT_PATH.exists() else pd.DataFrame()
        if not preflight_df.empty and not wide_df.empty and "candidate_id" in wide_df.columns:
            feature_by_id = wide_df.set_index("candidate_id")
            for candidate_id, row in preflight_df.iterrows():
                key = row.get("candidate_id", "")
                if row.get("preflight_status") == "pending" and key in feature_by_id.index:
                    raw_count = feature_by_id.loc[key].get("accelerometer_raw_row_count", "")
                    preflight_df.at[candidate_id, "raw_row_count"] = raw_count
                    preflight_df.at[candidate_id, "raw_data_available"] = "1"
                    preflight_df.at[candidate_id, "preflight_status"] = "has_raw_rows"
                    preflight_df.at[candidate_id, "error_message"] = ""
        if not preflight_df.empty:
            # Preserve every non-pending preflight outcome in the status table,
            # including outcomes from interrupted runs that had no status row.
            status_df = status_df.drop_duplicates("candidate_id", keep="last") if not status_df.empty else pd.DataFrame()
            known_status_ids = set(status_df.get("candidate_id", pd.Series(dtype=str)))
            wide_by_id = wide_df.set_index("candidate_id") if not wide_df.empty else pd.DataFrame()
            supplemental_status: list[dict[str, Any]] = []
            for row in preflight_df.to_dict("records"):
                candidate_id = row.get("candidate_id", "")
                preflight_status = str(row.get("preflight_status", "") or "")
                if not candidate_id or preflight_status == "pending" or candidate_id in known_status_ids:
                    continue
                feature_row = wide_by_id.loc[candidate_id] if candidate_id in wide_by_id.index else {}
                raw_rows = row.get("raw_row_count", 0)
                supplemental_status.append(
                    {
                        "candidate_id": candidate_id,
                        "patient_id": row.get("patient_id", ""),
                        "device_id": row.get("device_id", ""),
                        "local_date": row.get("local_date", ""),
                        "window_start_local": row.get("window_start_local", ""),
                        "window_end_local_exclusive": row.get("window_end_local_exclusive", ""),
                        "plugin_event_count": row.get("plugin_event_count", ""),
                        "plugin_dominant_movement_evidence_class": row.get("plugin_dominant_movement_evidence_class", ""),
                        "preflight_raw_row_count": raw_rows,
                        "status": "features_calculated" if candidate_id in wide_by_id.index else (
                            "no_raw_rows" if preflight_status == "no_raw_rows" else "error"
                        ),
                        "raw_rows": raw_rows,
                        "valid_numeric_rows": feature_row.get("accelerometer_valid_numeric_row_count", 0) if isinstance(feature_row, pd.Series) else 0,
                        "invalid_timestamp_rows": feature_row.get("accelerometer_invalid_timestamp_rows", 0) if isinstance(feature_row, pd.Series) else 0,
                        "invalid_signal_rows": feature_row.get("accelerometer_invalid_signal_rows", 0) if isinstance(feature_row, pd.Series) else 0,
                        "duplicates_removed": feature_row.get("accelerometer_exact_duplicate_rows_removed", 0) if isinstance(feature_row, pd.Series) else 0,
                        "valid_signal_minutes": feature_row.get("accelerometer_valid_signal_minutes", 0) if isinstance(feature_row, pd.Series) else 0,
                        "error_message": row.get("error_message", ""),
                    }
                )
            if supplemental_status:
                status_df = pd.concat([status_df, pd.DataFrame(supplemental_status)], ignore_index=True)
            pending_ids = set(preflight_df.loc[preflight_df["preflight_status"].eq("pending"), "candidate_id"])
            if not status_df.empty and "candidate_id" in status_df.columns:
                status_df = status_df[~status_df["candidate_id"].isin(pending_ids)].drop_duplicates("candidate_id", keep="last")
            status_df.to_csv(STATUS_PATH, index=False)
        preflight_df.to_csv(PREFLIGHT_PATH, index=False)
        if not wide_df.empty:
            build_patient_day_features(wide_df).to_csv(PATIENT_DAY_PATH, index=False)
            long_df = pd.DataFrame(
                [
                    {
                        "candidate_id": row["candidate_id"],
                        "patient_id": row["patient_id"],
                        "device_id": row["device_id"],
                        "local_date": row["local_date"],
                        "feature_name": name,
                        "feature_group": FEATURE_GROUPS[name],
                        "value": row.get(name, float("nan")),
                    }
                    for _, row in wide_df.iterrows()
                    for name in FEATURE_NAMES
                ]
            )
            long_df.to_csv(FEATURE_LONG_PATH, index=False)
        write_summary(candidates, preflight_df, status_df, wide_df)
        write_readme(candidates, preflight_df, status_df)
        print("accelerometer_plugin_event_day_pilot_finalized", flush=True)
        print(f"feature_days: {len(wide_df)}", flush=True)
        print(f"status_rows: {len(status_df)}", flush=True)
        print(
            "pending_days: "
            f"{int(preflight_df.get('preflight_status', pd.Series(dtype=str)).astype(str).eq('pending').sum()) if not preflight_df.empty else len(candidates)}",
            flush=True,
        )
        return

    existing_status = pd.read_csv(STATUS_PATH, dtype=str) if STATUS_PATH.exists() else pd.DataFrame()
    completed_ids = set()
    if not existing_status.empty and "candidate_id" in existing_status.columns:
        completed_ids = set(existing_status.loc[existing_status["status"].eq("features_calculated"), "candidate_id"])
        if not args.retry_failed:
            completed_ids |= set(existing_status.loc[existing_status["status"].eq("no_raw_rows"), "candidate_id"])
        retry_ids = set(candidates["candidate_id"]) - completed_ids
        existing_status = existing_status[~existing_status["candidate_id"].isin(retry_ids)].copy()

    status_rows: list[dict[str, Any]] = existing_status.to_dict("records") if not existing_status.empty else []
    feature_rows: list[dict[str, Any]] = []
    if FEATURE_WIDE_PATH.exists():
        existing_wide = pd.read_csv(FEATURE_WIDE_PATH, dtype=str)
        if not existing_wide.empty:
            feature_rows.extend(existing_wide.to_dict("records"))
            if "candidate_id" in existing_wide.columns:
                completed_ids |= set(existing_wide["candidate_id"].astype(str))

    preflight_rows: dict[str, dict[str, Any]] = {
        row["candidate_id"]: {
            "candidate_id": row["candidate_id"],
            "patient_id": row["patient_id"],
            "device_id": row["device_id"],
            "local_date": row["local_date"],
            "window_start_local": row["window_start_local"],
            "window_end_local_exclusive": row["window_end_local_exclusive"],
            "plugin_event_count": row.get("plugin_event_count", ""),
            "plugin_dominant_movement_evidence_class": row.get("dominant_movement_evidence_class", ""),
            "raw_row_count": "",
            "first_raw_time_local": "",
            "last_raw_time_local": "",
            "raw_data_available": "",
            "preflight_status": "pending",
            "error_message": "",
        }
        for _, row in candidates.iterrows()
    }
    existing_preflight = pd.read_csv(PREFLIGHT_PATH, dtype=str) if PREFLIGHT_PATH.exists() else pd.DataFrame()
    if not existing_preflight.empty and "candidate_id" in existing_preflight.columns:
        for row in existing_preflight.to_dict("records"):
            candidate_id = row.get("candidate_id", "")
            if candidate_id in preflight_rows:
                preflight_rows[candidate_id].update(row)

    def persist_progress() -> None:
        preflight_frame = pd.DataFrame(list(preflight_rows.values()))
        status_frame = pd.DataFrame(status_rows).drop_duplicates("candidate_id", keep="last")
        preflight_frame.to_csv(PREFLIGHT_PATH, index=False)
        status_frame.to_csv(STATUS_PATH, index=False)
        feature_frame = pd.DataFrame(feature_rows)
        if not feature_frame.empty:
            feature_frame = feature_frame.drop_duplicates("candidate_id", keep="last")
        feature_frame.to_csv(FEATURE_WIDE_PATH, index=False)
        build_patient_day_features(feature_frame).to_csv(PATIENT_DAY_PATH, index=False)
        write_summary(candidates, preflight_frame, status_frame, feature_frame)
        write_readme(candidates, preflight_frame, status_frame)

    if args.skip_preflight:
        print("raw preflight skipped; empty windows will be classified during local-day extraction", flush=True)
        preflight_targets = candidates.iloc[0:0].copy()
    else:
        preflight_targets = candidates[
            candidates["candidate_id"].map(
                lambda candidate_id: preflight_rows.get(candidate_id, {}).get("preflight_status") in {"pending", "error", ""}
            )
        ].copy()
    if not preflight_targets.empty:
        print(f"batched preflight candidates={len(preflight_targets)}", flush=True)
    def run_preflight_batch(query_candidates: list[pd.Series]) -> None:
        """Run a batch, recursively splitting it when the database cannot finish it."""
        if not query_candidates:
            return
        device_id = str(query_candidates[0]["device_id"])
        conn = None
        try:
            conn = connect_sensordata_db()
            results = batch_raw_preflight(conn, query_candidates)
            for candidate in query_candidates:
                result = results.get(str(candidate["candidate_id"]), {})
                first_ts = result.get("first_timestamp_ms")
                has_rows = first_ts is not None and not pd.isna(first_ts)
                preflight_rows[candidate["candidate_id"]].update(
                    {
                        "raw_row_count": "",
                        "first_raw_time_local": local_text(first_ts),
                        "last_raw_time_local": "",
                        "raw_data_available": int(has_rows),
                        "preflight_status": "has_raw_rows" if has_rows else "no_raw_rows",
                        "error_message": "",
                    }
                )
            print(
                f"preflight device={device_id} dates={query_candidates[0]['local_date']}..{query_candidates[-1]['local_date']} count={len(query_candidates)}",
                flush=True,
            )
            persist_progress()
            return
        except Exception as exc:  # noqa: BLE001
            error_text = str(exc)
            print(
                f"preflight split device={device_id} dates={query_candidates[0]['local_date']}..{query_candidates[-1]['local_date']} count={len(query_candidates)}: {error_text}",
                flush=True,
            )
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
        if len(query_candidates) > 1:
            midpoint = len(query_candidates) // 2
            run_preflight_batch(query_candidates[:midpoint])
            run_preflight_batch(query_candidates[midpoint:])
            return
        candidate = query_candidates[0]
        preflight_rows[candidate["candidate_id"]].update(
            {
                "preflight_status": "error",
                "error_message": error_text,
            }
        )
        persist_progress()

    for _, device_group in preflight_targets.groupby("device_id", sort=False):
        device_candidates = [row for _, row in device_group.sort_values("local_date").iterrows()]
        batch_size = max(args.preflight_batch_days, 1)
        for group_start in range(0, len(device_candidates), batch_size):
            run_preflight_batch(device_candidates[group_start : group_start + batch_size])

    candidate_positions = {row["candidate_id"]: index for index, (_, row) in enumerate(candidates.iterrows(), start=1)}

    def record_day_result(
        candidate: pd.Series,
        timestamps: np.ndarray,
        magnitudes: np.ndarray,
        counters: dict[str, int],
        error_message: str = "",
    ) -> None:
        candidate_id = candidate["candidate_id"]
        status_row: dict[str, Any] = {
            "candidate_id": candidate_id,
            "patient_id": candidate["patient_id"],
            "device_id": candidate["device_id"],
            "local_date": candidate["local_date"],
            "window_start_local": candidate["window_start_local"],
            "window_end_local_exclusive": candidate["window_end_local_exclusive"],
            "plugin_event_count": candidate.get("plugin_event_count", ""),
            "plugin_dominant_movement_evidence_class": candidate.get("dominant_movement_evidence_class", ""),
            "preflight_raw_row_count": counters.get("raw_rows", 0),
            "status": "error" if error_message else "pending",
            "raw_rows": counters.get("raw_rows", 0),
            "valid_numeric_rows": len(timestamps),
            "invalid_timestamp_rows": counters.get("invalid_timestamp_rows", 0),
            "invalid_signal_rows": counters.get("invalid_signal_rows", 0),
            "duplicates_removed": 0,
            "valid_signal_minutes": 0,
            "error_message": error_message,
        }
        raw_count = int(counters.get("raw_rows", 0))
        first_raw = counters.get("first_raw_timestamp_ms")
        last_raw = counters.get("last_raw_timestamp_ms")
        preflight_rows[candidate_id].update(
            {
                "raw_row_count": raw_count,
                "first_raw_time_local": local_text(first_raw),
                "last_raw_time_local": local_text(last_raw),
                "raw_data_available": int(raw_count > 0),
                "preflight_status": "error" if error_message else ("has_raw_rows" if raw_count > 0 else "no_raw_rows"),
                "error_message": error_message,
            }
        )
        if not error_message:
            features, chunk = analyze_day_arrays(candidate, timestamps, magnitudes, counters)
            feature_status = "features_calculated" if len(timestamps) else (
                "no_valid_numeric_signal" if raw_count else "no_raw_rows"
            )
            status_row.update(
                {
                    "status": feature_status,
                    "duplicates_removed": features.get("accelerometer_exact_duplicate_rows_removed", 0),
                    "valid_signal_minutes": features.get("accelerometer_valid_signal_minutes", 0),
                }
            )
            if feature_status == "features_calculated":
                feature_rows.append(features)
                append_frame(CHUNK_PATH, chunk)
            print(
                f"complete {candidate_positions[candidate_id]}/{len(candidates)} patient={candidate['patient_id']} date={candidate['local_date']} raw={raw_count:,} valid_minutes={features.get('accelerometer_valid_signal_minutes', 0)}",
                flush=True,
            )
        else:
            print(
                f"error {candidate_positions[candidate_id]}/{len(candidates)} patient={candidate['patient_id']} date={candidate['local_date']}: {error_message}",
                flush=True,
            )
        status_rows.append(status_row)
        persist_progress()
        checkpoint = {
            "last_candidate_id": candidate_id,
            "completed_feature_days": int(sum(row.get("status") == "features_calculated" for row in status_rows)),
            "candidate_count": len(candidates),
        }
        CHECKPOINT_PATH.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")

    preflight_no_raw = set(
        candidates.loc[
            candidates["candidate_id"].map(lambda candidate_id: preflight_rows.get(candidate_id, {}).get("preflight_status") == "no_raw_rows"),
            "candidate_id",
        ]
    )
    for candidate in candidates[candidates["candidate_id"].isin(preflight_no_raw)].itertuples(index=False):
        if candidate.candidate_id in completed_ids:
            continue
        record_day_result(pd.Series(candidate._asdict()), np.array([], dtype=np.int64), np.array([], dtype=float), {})
        completed_ids.add(candidate.candidate_id)

    unresolved = candidates[~candidates["candidate_id"].isin(completed_ids)].copy()
    if args.query_by_local_day:
        query_groups = unresolved.groupby("local_date", sort=True)
        for local_date, day_group in query_groups:
            query_candidates = [row for _, row in day_group.sort_values(["device_id", "candidate_id"]).iterrows()]
            yielded_ids: set[str] = set()
            print(
                f"query local_date={local_date} candidate_devices={day_group['device_id'].nunique()} candidates={len(query_candidates)}",
                flush=True,
            )
            conn = None
            try:
                conn = connect_sensordata_db()
                for candidate, timestamps, magnitudes, counters in fetch_raw_records_for_local_day(
                    conn, query_candidates, args.batch_rows
                ):
                    yielded_ids.add(candidate["candidate_id"])
                    record_day_result(candidate, timestamps, magnitudes, counters)
            except Exception as exc:  # noqa: BLE001
                for candidate in query_candidates:
                    if candidate["candidate_id"] not in yielded_ids:
                        record_day_result(candidate, np.array([], dtype=np.int64), np.array([], dtype=float), {}, str(exc))
            finally:
                if conn is not None:
                    conn.close()
    else:
        for device_id, device_group in unresolved.groupby("device_id", sort=False):
            device_candidates = [row for _, row in device_group.sort_values("local_date").iterrows()]
            for group_start in range(0, len(device_candidates), max(args.days_per_query, 1)):
                query_candidates = device_candidates[group_start : group_start + max(args.days_per_query, 1)]
                yielded_ids: set[str] = set()
                print(
                    f"query device={device_id} dates={query_candidates[0]['local_date']}..{query_candidates[-1]['local_date']} count={len(query_candidates)}",
                    flush=True,
                )
                conn = None
                try:
                    conn = connect_sensordata_db()
                    for candidate, timestamps, magnitudes, counters in fetch_raw_records_for_group(
                        conn, query_candidates, args.batch_rows
                    ):
                        yielded_ids.add(candidate["candidate_id"])
                        record_day_result(candidate, timestamps, magnitudes, counters)
                except Exception as exc:  # noqa: BLE001
                    for candidate in query_candidates:
                        if candidate["candidate_id"] not in yielded_ids:
                            record_day_result(candidate, np.array([], dtype=np.int64), np.array([], dtype=float), {}, str(exc))
                finally:
                    if conn is not None:
                        conn.close()

    status_df = pd.DataFrame(status_rows).drop_duplicates("candidate_id", keep="last") if status_rows else pd.DataFrame()
    wide_df = pd.DataFrame(feature_rows).drop_duplicates("candidate_id", keep="last") if feature_rows else pd.DataFrame()
    preflight = pd.DataFrame(list(preflight_rows.values()))
    preflight.to_csv(PREFLIGHT_PATH, index=False)
    if not wide_df.empty:
        wide_df.to_csv(FEATURE_WIDE_PATH, index=False)
        build_patient_day_features(wide_df).to_csv(PATIENT_DAY_PATH, index=False)
    status_df.to_csv(STATUS_PATH, index=False)
    if not wide_df.empty:
        build_long_rows = pd.DataFrame(
            [
                {
                    "candidate_id": row["candidate_id"],
                    "patient_id": row["patient_id"],
                    "device_id": row["device_id"],
                    "local_date": row["local_date"],
                    "feature_name": name,
                    "feature_group": FEATURE_GROUPS[name],
                    "value": row.get(name, float("nan")),
                }
                for _, row in wide_df.iterrows()
                for name in FEATURE_NAMES
            ]
        )
        build_long_rows.to_csv(FEATURE_LONG_PATH, index=False)
    write_summary(candidates, preflight, status_df, wide_df)
    write_readme(candidates, preflight, status_df)
    print("accelerometer_plugin_event_day_pilot_complete", flush=True)
    print(f"patients: {candidates['patient_id'].nunique() if not candidates.empty else 0}", flush=True)
    print(f"candidate_device_days: {len(candidates)}", flush=True)
    print(f"features_calculated: {int(status_df['status'].eq('features_calculated').sum()) if not status_df.empty else 0}", flush=True)
    print(f"output_directory: {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
