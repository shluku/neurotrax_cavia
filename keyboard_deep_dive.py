"""Keyboard Deep Dive v1 extraction.

This is an additive, privacy-safe extraction. It reads the saved Phase 11/12
windows, queries only the keyboard table, and writes a new output directory.
Existing feature matrices and model inputs are never modified.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from main import connect_sensordata_db


ROOT = Path(__file__).parent
OUT = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1"
TZ = "Asia/Jerusalem"
T1_STATUS = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_patient_table_status.csv"
T2_STATUS = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_patient_table_status.csv"
T1_WIDE = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"

BURST_GAP_MS = 30_000
LONG_PAUSE_MS = 2_000
MAX_NORMAL_INTERVAL_MS = BURST_GAP_MS
SIX_HOUR_BINS = ((0, 6), (6, 12), (12, 18), (18, 24))


def parse_json(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")
    if not isinstance(value, str):
        return None
    try:
        out = json.loads(value)
    except Exception:
        return None
    return out if isinstance(out, dict) else None


def text_value(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = str(value)
    if len(text) >= 2 and text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return text


def local_timestamp(ts_ms: int) -> pd.Timestamp:
    return pd.to_datetime(int(ts_ms), unit="ms", utc=True).tz_convert(TZ)


def robust_mad(values: list[float]) -> float | None:
    if not values:
        return None
    arr = np.asarray(values, dtype=float)
    med = float(np.median(arr))
    return float(np.median(np.abs(arr - med)))


def summarize(values: list[float], prefix: str) -> dict[str, Any]:
    if not values:
        return {
            f"{prefix}_median": pd.NA,
            f"{prefix}_sd": pd.NA,
            f"{prefix}_iqr": pd.NA,
            f"{prefix}_mad": pd.NA,
            f"{prefix}_p05_p95_spread": pd.NA,
            f"{prefix}_cv": pd.NA,
        }
    arr = np.asarray(values, dtype=float)
    mean = float(np.mean(arr))
    return {
        f"{prefix}_median": float(np.median(arr)),
        f"{prefix}_sd": float(np.std(arr, ddof=1)) if len(arr) > 1 else pd.NA,
        f"{prefix}_iqr": float(np.quantile(arr, 0.75) - np.quantile(arr, 0.25)),
        f"{prefix}_mad": robust_mad(values),
        f"{prefix}_p05_p95_spread": float(np.quantile(arr, 0.95) - np.quantile(arr, 0.05)),
        f"{prefix}_cv": float(np.std(arr, ddof=1) / mean) if len(arr) > 1 and mean > 0 else pd.NA,
    }


def canonical_events(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    events: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    parse_errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        ts = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if pd.isna(ts):
            continue
        device = str(row.get("device_id") or "")
        before = text_value(obj.get("before_text"))
        current = text_value(obj.get("current_text"))
        package = str(obj.get("package_name") or "").strip()
        password = str(obj.get("is_password") or "").strip()
        key = (int(ts), device, before, current, package, password)
        if key in seen:
            continue
        seen.add(key)
        events.append(
            {
                "timestamp": int(ts),
                "device_id": device,
                "package_name": package,
                "is_password": password,
                "before_len": len(before),
                "current_len": len(current),
                "current_has_text": bool(current.strip()),
                "current_ends_space": current.endswith(" "),
                "before_ends_space": before.endswith(" "),
            }
        )
    events.sort(key=lambda x: (x["device_id"], x["package_name"], x["timestamp"]))
    return events, len(rows) - len(events) - parse_errors, parse_errors


def group_features(events: list[dict[str, Any]]) -> dict[str, Any]:
    intervals: list[float] = []
    long_pauses = 0
    deletion_count = 0
    deletion_pauses_before: list[float] = []
    deletion_pauses_after: list[float] = []
    recovery_times: list[float] = []
    deletion_timestamps: list[int] = []
    growth_count = 0
    word_times: list[float] = []
    burst_durations: list[float] = []
    active_minutes = 0.0
    package_counts: Counter[str] = Counter()
    by_bucket: dict[int, list[float]] = {i: [] for i in range(4)}
    by_bucket_n: dict[int, int] = {i: 0 for i in range(4)}

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for event in events:
        grouped.setdefault((event["device_id"], event["package_name"]), []).append(event)
        package_counts[event["package_name"]] += 1

    for group in grouped.values():
        if not group:
            continue
        burst_start = group[0]["timestamp"]
        previous = group[0]
        word_start: int | None = None
        group_intervals: list[tuple[int, float]] = []
        for idx, event in enumerate(group):
            ts = event["timestamp"]
            if idx > 0:
                delta = ts - previous["timestamp"]
                if delta > BURST_GAP_MS:
                    burst_durations.append((previous["timestamp"] - burst_start) / 1000.0)
                    active_minutes += max(0.0, previous["timestamp"] - burst_start) / 60000.0
                    burst_start = ts
                    word_start = None
                elif delta > 0:
                    intervals.append(float(delta))
                    group_intervals.append((ts, float(delta)))
                    bucket = local_timestamp(ts).hour // 6
                    by_bucket[bucket].append(float(delta))
                    by_bucket_n[bucket] += 1
                    if delta > LONG_PAUSE_MS:
                        long_pauses += 1

            is_deletion = event["current_len"] < event["before_len"] or event["current_len"] < previous["current_len"]
            if is_deletion:
                deletion_count += 1
                deletion_timestamps.append(ts)
                if idx > 0:
                    deletion_pauses_before.append(float(ts - previous["timestamp"]))
                if idx + 1 < len(group):
                    deletion_pauses_after.append(float(group[idx + 1]["timestamp"] - ts))
                    for future in group[idx + 1 :]:
                        if future["current_len"] > event["current_len"]:
                            recovery_times.append(float(future["timestamp"] - ts))
                            break
            if event["current_len"] > event["before_len"]:
                growth_count += 1
            if word_start is None and event["current_has_text"] and not event["current_ends_space"]:
                word_start = ts
            if event["before_ends_space"] and event["current_has_text"] and not event["current_ends_space"]:
                word_start = ts
            if word_start is not None and event["current_ends_space"] and not event["before_ends_space"]:
                if ts >= word_start:
                    word_times.append(float(ts - word_start))
                word_start = None
            previous = event
        burst_durations.append((previous["timestamp"] - burst_start) / 1000.0)
        active_minutes += max(0.0, previous["timestamp"] - burst_start) / 60000.0

    valid_intervals = [v for v in intervals if 0 < v <= MAX_NORMAL_INTERVAL_MS]
    long_pause_rate = long_pauses / len(valid_intervals) if valid_intervals else None
    deletion_bursts = 0
    for prev, cur in zip(deletion_timestamps, deletion_timestamps[1:]):
        if cur - prev > LONG_PAUSE_MS:
            deletion_bursts += 1
    if deletion_timestamps:
        deletion_bursts += 1

    out: dict[str, Any] = {
        "keyboard_distinct_observation_count": len(events) if events else pd.NA,
        "keyboard_active_minutes": active_minutes if events else pd.NA,
        "keyboard_active_days": len({local_timestamp(e["timestamp"]).date() for e in events}) if events else pd.NA,
        "keyboard_observations_per_active_minute": (len(events) / active_minutes) if active_minutes > 0 else pd.NA,
        "keyboard_valid_interval_count": len(valid_intervals) if events else pd.NA,
        "keyboard_long_pause_count_2s": long_pauses if valid_intervals else pd.NA,
        "keyboard_long_pause_rate": long_pause_rate if valid_intervals else pd.NA,
        "keyboard_typing_burst_count": len(burst_durations) if events else pd.NA,
        "keyboard_median_burst_duration_ms": (float(np.median(burst_durations)) * 1000) if burst_durations else pd.NA,
        "keyboard_burst_duration_iqr_ms": (float(np.quantile(burst_durations, .75) - np.quantile(burst_durations, .25)) * 1000) if burst_durations else pd.NA,
        "keyboard_session_fragmentation_per_active_hour": (len(burst_durations) / (active_minutes / 60.0)) if active_minutes > 0 else pd.NA,
        "keyboard_deletion_event_count": deletion_count if events else pd.NA,
        "keyboard_deletion_rate": (deletion_count / len(events)) if events else pd.NA,
        "keyboard_median_pre_correction_pause_ms": float(np.median(deletion_pauses_before)) if deletion_pauses_before else pd.NA,
        "keyboard_median_post_correction_pause_ms": float(np.median(deletion_pauses_after)) if deletion_pauses_after else pd.NA,
        "keyboard_median_correction_recovery_time_ms": float(np.median(recovery_times)) if recovery_times else pd.NA,
        "keyboard_deletion_burst_count": deletion_bursts if deletion_timestamps else pd.NA,
        "keyboard_text_growth_event_count": growth_count if events else pd.NA,
        "keyboard_median_word_completion_time_ms": float(np.median(word_times)) if word_times else pd.NA,
        "keyboard_word_completion_count": len(word_times) if events else pd.NA,
        "keyboard_unique_package_count": len(package_counts) if events else pd.NA,
        "keyboard_raw_rows_in_window": pd.NA,
        "keyboard_duplicate_rows_removed": pd.NA,
        "keyboard_json_parse_errors": pd.NA,
    }
    out.update(summarize(valid_intervals, "keyboard_inter_event_interval"))
    for bucket, (start, end) in enumerate(SIX_HOUR_BINS):
        values = [v for v in by_bucket[bucket] if 0 < v <= MAX_NORMAL_INTERVAL_MS]
        label = f"keyboard_{start:02d}_{end:02d}"
        out[f"{label}_observation_count"] = by_bucket_n[bucket] if by_bucket_n[bucket] else pd.NA
        out[f"{label}_median_inter_event_interval_ms"] = float(np.median(values)) if values else pd.NA
        out[f"{label}_inter_event_interval_iqr_ms"] = (float(np.quantile(values, .75) - np.quantile(values, .25)) if values else pd.NA)
    return out


def compute_window(events: list[dict[str, Any]], raw_rows: int, duplicate_rows: int, parse_errors: int, sid: str, window_name: str, start_ms: int, end_ms: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    daily: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        day = str(local_timestamp(event["timestamp"]).date())
        daily.setdefault(day, []).append(event)
    day_rows: list[dict[str, Any]] = []
    for day, day_events in sorted(daily.items()):
        values = group_features(day_events)
        values.update({"Subject_ID_D": sid, "window_name": window_name, "local_date": day, "raw_rows_in_day": len(day_events), "distinct_observations_in_day": len(day_events)})
        day_rows.append(values)
    values = group_features(events)
    values.update({
        "Subject_ID_D": sid,
        "window_name": window_name,
        "window_start_ms": start_ms,
        "window_end_ms": end_ms,
        "window_start_local": str(local_timestamp(start_ms)),
        "window_end_local": str(local_timestamp(end_ms)),
        "raw_rows_in_window": raw_rows,
        "distinct_observations_in_window": len(events),
        "duplicate_rows_removed": duplicate_rows,
        "json_parse_errors": parse_errors,
        "active_local_days": len(day_rows),
        "window_status": "calculated" if events else "missing_no_keyboard_rows",
    })
    for key in list(values):
        if key.endswith("_raw_rows_in_window"):
            values[key] = raw_rows
        elif key.endswith("_duplicate_rows_removed"):
            values[key] = duplicate_rows
        elif key.endswith("_json_parse_errors"):
            values[key] = parse_errors
    return values, day_rows


def load_windows(path: Path, window_name: str) -> pd.DataFrame:
    status = pd.read_csv(path, dtype=str)
    status = status[status["table_name"].eq("keyboard")].copy()
    status = status.drop_duplicates(subset=["Subject_ID_D", "window_start_ms", "window_end_ms"])
    status["window_name"] = window_name
    status["device_ids_used"] = status["device_ids_used"].fillna(status["device_ids_available"])
    return status


def schema_audit(conn: Any) -> tuple[pd.DataFrame, pd.DataFrame]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SHOW COLUMNS FROM `keyboard`")
        columns = pd.DataFrame(cur.fetchall())
        cur.execute("SELECT data FROM `keyboard` ORDER BY timestamp ASC LIMIT 500")
        rows = cur.fetchall()
    finally:
        cur.close()
    counts: Counter[str] = Counter()
    n_parse = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            n_parse += 1
            continue
        counts.update(str(k) for k in obj)
    keys = pd.DataFrame([{"json_key": k, "n_rows_with_key": v, "sample_rows": len(rows), "percent_sample_rows": 100 * v / len(rows) if rows else 0} for k, v in sorted(counts.items())])
    keys = pd.concat([keys, pd.DataFrame([{"json_key": "__parse_errors__", "n_rows_with_key": n_parse, "sample_rows": len(rows), "percent_sample_rows": 100 * n_parse / len(rows) if rows else 0}])], ignore_index=True)
    return columns, keys


def fetch_keyboard_rows(conn: Any, device_ids: list[str], start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    if not device_ids:
        return []
    placeholders = ",".join(["%s"] * len(device_ids))
    sql = f"SELECT _id, timestamp, device_id, data FROM `keyboard` WHERE device_id IN ({placeholders}) AND timestamp >= %s AND timestamp < %s ORDER BY timestamp ASC"
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, (*device_ids, int(start_ms), int(end_ms)))
        rows: list[dict[str, Any]] = []
        while True:
            batch = cur.fetchmany(10000)
            if not batch:
                break
            rows.extend(batch)
        return rows
    finally:
        cur.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--out-dir", default=str(OUT))
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    conn = connect_sensordata_db()
    try:
        columns, keys = schema_audit(conn)
        columns.to_csv(out / "keyboard_schema_columns.csv", index=False)
        keys.to_csv(out / "keyboard_schema_json_key_audit.csv", index=False)
        if args.schema_only:
            (out / "run_manifest.json").write_text(json.dumps({"status": "schema_audit_complete", "protocol": "KEYBOARD_DEEP_DIVE_PROTOCOL.md"}, indent=2))
            print(f"Schema audit complete: {out}")
            return

        windows = pd.concat([load_windows(T1_STATUS, "T1"), load_windows(T2_STATUS, "T2")], ignore_index=True)
        window_rows: list[dict[str, Any]] = []
        daily_rows: list[dict[str, Any]] = []
        for _, spec in windows.iterrows():
            sid = str(spec["Subject_ID_D"])
            start = int(float(spec["window_start_ms"]))
            end = int(float(spec["window_end_ms"]))
            device_ids = [x for x in str(spec.get("device_ids_used") or "").split(";") if x and x.lower() != "nan"]
            raw = fetch_keyboard_rows(conn, device_ids, start, end)
            events, duplicate_rows, parse_errors = canonical_events(raw)
            window, daily = compute_window(events, len(raw), duplicate_rows, parse_errors, sid, str(spec["window_name"]), start, end)
            window_rows.append(window)
            daily_rows.extend(daily)
            print(f"{sid} {spec['window_name']}: raw={len(raw)} distinct={len(events)} days={len(daily)}")
    finally:
        conn.close()

    windows_df = pd.DataFrame(window_rows)
    daily_df = pd.DataFrame(daily_rows)
    windows_df.to_csv(out / "keyboard_deep_dive_window_features.csv", index=False)
    daily_df.to_csv(out / "keyboard_deep_dive_daily_features.csv", index=False)

    coverage = windows_df[["Subject_ID_D", "window_name", "window_status", "raw_rows_in_window", "distinct_observations_in_window", "duplicate_rows_removed", "json_parse_errors", "active_local_days"]].copy()
    coverage.to_csv(out / "keyboard_deep_dive_coverage.csv", index=False)
    feature_dictionary = pd.DataFrame([
        {"feature_name": c, "source": "keyboard", "level": "window" if c in windows_df.columns else "daily", "privacy_safe_output": "yes", "definition": "See KEYBOARD_DEEP_DIVE_PROTOCOL.md"}
        for c in sorted(set(windows_df.columns) | set(daily_df.columns))
        if c.startswith("keyboard_")
    ])
    feature_dictionary.to_csv(out / "keyboard_deep_dive_feature_dictionary.csv", index=False)
    manifest = {
        "status": "complete",
        "protocol": "KEYBOARD_DEEP_DIVE_PROTOCOL.md",
        "output_directory": str(out),
        "windows": int(len(windows_df)),
        "daily_rows": int(len(daily_df)),
        "existing_outputs_modified": False,
        "model_integration_performed": False,
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
