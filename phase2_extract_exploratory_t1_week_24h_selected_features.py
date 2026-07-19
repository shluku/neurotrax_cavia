from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


TZ = "Asia/Jerusalem"
ROOT = Path(__file__).parent
OUT_DIR = ROOT / "output/analysis_candidates/phase2_feature_extraction/exploratory_t1_week_24h"
FEATURES_PATH = OUT_DIR / "phase2_exploratory_t1_week_24h_selected_features.csv"
COVERAGE_PATH = OUT_DIR / "phase2_exploratory_t1_week_24h_coverage_scan.csv"
SELECTED_FEATURES_PATH = ROOT / "phase2_selected_features.csv"
COGNITIVE_CANDIDATES_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
LABEL_DEVICE_MAP_PATH = ROOT / "output/label_device_map.csv"

SAFE_TABLES = {
    "applications_foreground",
    "battery",
    "bluetooth",
    "calls",
    "gsm",
    "gsm_neighbor",
    "keyboard",
    "light",
    "locations",
    "messages",
    "plugin_google_activity_recognition",
    "screen",
    "telephony",
    "touch",
}
EXCLUDED_EXPLORATORY_SUBJECTS = {"001"}


def normalize_subject_id_d(value: Any) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    return s.zfill(3) if s.isdigit() else s


def parse_json(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def local_to_ms(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def ms_to_local(ms: int | float | None) -> str:
    if ms is None or pd.isna(ms):
        return ""
    return pd.to_datetime(int(ms), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z")


def shannon_entropy(counts) -> float | None:
    total = sum(counts)
    if total <= 0:
        return None
    entropy = 0.0
    for count in counts:
        if count <= 0:
            continue
        p = count / total
        entropy -= p * math.log(p, 2)
    return entropy


def numeric(value: Any) -> float | None:
    out = pd.to_numeric(value, errors="coerce")
    if pd.isna(out):
        return None
    return float(out)


def load_ranked_patients() -> pd.DataFrame:
    df = pd.read_csv(COGNITIVE_CANDIDATES_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id_d)
    df["global_T1_num"] = pd.to_numeric(df["global_T1"], errors="coerce")
    df = df.dropna(subset=["Subject_ID_D", "global_T1_num", "T1_date_iso"]).copy()
    return df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True])


def load_device_map() -> dict[str, list[str]]:
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    out: dict[str, list[str]] = {}
    for _, row in label_map.iterrows():
        subject_id = normalize_subject_id_d(row.get("label"))
        raw = str(row.get("device_ids", ""))
        out[subject_id] = [x.strip() for x in raw.split(";") if x.strip() and x.strip().lower() != "nan"]
    return out


def count_rows(conn, table_name: str, device_id: str, start_ms: int, end_ms: int) -> tuple[int, int | None, int | None]:
    if table_name not in SAFE_TABLES:
        raise ValueError(f"Unsafe table name: {table_name}")
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM `{table_name}`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        n_rows, first_ts, last_ts = cur.fetchone()
        return int(n_rows or 0), int(first_ts) if first_ts is not None else None, int(last_ts) if last_ts is not None else None
    finally:
        cur.close()


def first_existing_between(conn, table_name: str, device_id: str, start_ms: int, latest_start_ms: int) -> int | None:
    if table_name not in SAFE_TABLES:
        raise ValueError(f"Unsafe table name: {table_name}")
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT timestamp
            FROM `{table_name}`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp <= %s
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (device_id, int(start_ms), int(latest_start_ms)),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        cur.close()


def fetch_rows(conn, table_name: str, device_id: str, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    if table_name not in SAFE_TABLES:
        raise ValueError(f"Unsafe table name: {table_name}")
    cur = conn.cursor(dictionary=True)
    out: list[dict[str, Any]] = []
    try:
        cur.execute(
            f"""
            SELECT _id, timestamp, device_id, data
            FROM `{table_name}`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        while True:
            batch = cur.fetchmany(5000)
            if not batch:
                break
            out.extend(batch)
    finally:
        cur.close()
    return out


def fetch_light_lux_values(conn, device_id: str, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    cur = conn.cursor(dictionary=True)
    out: list[dict[str, Any]] = []
    try:
        cur.execute(
            """
            SELECT
                timestamp,
                CAST(JSON_UNQUOTE(JSON_EXTRACT(data, '$.double_light_lux')) AS DECIMAL(18,6)) AS lux
            FROM `light`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
              AND JSON_EXTRACT(data, '$.double_light_lux') IS NOT NULL
            ORDER BY timestamp ASC
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        while True:
            batch = cur.fetchmany(20000)
            if not batch:
                break
            out.extend(batch)
    finally:
        cur.close()
    return out


def compute_applications_foreground(rows: list[dict[str, Any]]) -> dict[str, Any]:
    apps = []
    parse_errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        app_id = obj.get("package_name") or obj.get("application_name")
        if app_id is not None and str(app_id).strip():
            apps.append(str(app_id).strip())
    counts = Counter(apps)
    return {
        "app_foreground_event_count": len(rows),
        "unique_foreground_apps": len(counts) if apps else pd.NA,
        "app_use_diversity": shannon_entropy(counts.values()) if apps else pd.NA,
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if rows else "insufficient_data_no_rows",
    }


def battery_percent(obj: dict[str, Any]) -> float | None:
    level = numeric(obj.get("battery_level"))
    scale = numeric(obj.get("battery_scale"))
    if level is None:
        return None
    if scale is not None and scale > 0:
        return 100.0 * level / scale
    return level


def is_charging_or_plugged(obj: dict[str, Any]) -> bool | None:
    adaptor = numeric(obj.get("battery_adaptor"))
    status = numeric(obj.get("battery_status"))
    if adaptor is None and status is None:
        return None
    return (adaptor is not None and adaptor != 0) or (status is not None and int(status) in {2, 5})


def compute_battery(rows: list[dict[str, Any]]) -> dict[str, Any]:
    parse_errors = 0
    low_battery_event_count = 0
    charging_or_plugged_event_count = 0
    usable_battery_level_rows = 0
    usable_charging_status_rows = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            obj = {}
        percent = battery_percent(obj)
        charging = is_charging_or_plugged(obj)
        if percent is not None:
            usable_battery_level_rows += 1
            if percent <= 20:
                low_battery_event_count += 1
        if charging is not None:
            usable_charging_status_rows += 1
            if charging:
                charging_or_plugged_event_count += 1
    return {
        "low_battery_event_count": low_battery_event_count if rows else pd.NA,
        "charging_or_plugged_event_count": charging_or_plugged_event_count if rows else pd.NA,
        "battery_rows_in_window": len(rows),
        "usable_battery_level_rows": usable_battery_level_rows,
        "usable_charging_status_rows": usable_charging_status_rows,
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if rows else "insufficient_data_no_rows",
    }


def distinct_bluetooth_observations(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen = set()
    out = []
    parse_errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        key = (
            str(row.get("timestamp")),
            str(row.get("device_id")),
            str(obj.get("bt_address")),
            str(obj.get("bt_rssi")),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append({"bt_address": obj.get("bt_address")})
    return out, parse_errors


def compute_bluetooth(rows: list[dict[str, Any]]) -> dict[str, Any]:
    distinct_rows, parse_errors = distinct_bluetooth_observations(rows)
    addresses = [str(row.get("bt_address")).strip() for row in distinct_rows if str(row.get("bt_address", "")).strip()]
    unique_addresses = len(set(addresses))
    return {
        "unique_bluetooth_addresses": unique_addresses if addresses else pd.NA,
        "bluetooth_address_diversity_ratio": unique_addresses / len(addresses) if addresses else pd.NA,
        "bluetooth_raw_rows_in_window": len(rows),
        "bluetooth_distinct_observations": len(distinct_rows),
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if addresses else "insufficient_data_no_distinct_bluetooth_observations",
    }


def compute_calls(rows: list[dict[str, Any]]) -> dict[str, Any]:
    call_event_count = len(rows)
    incoming_call_count = 0
    outgoing_call_count = 0
    missed_rejected_blocked_call_count = 0
    total_call_duration_seconds = 0.0
    valid_duration_rows = 0
    json_parse_errors = 0

    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            json_parse_errors += 1
            obj = {}

        call_type = numeric(obj.get("call_type"))
        if call_type is not None:
            call_type_int = int(call_type)
            if call_type_int == 1:
                incoming_call_count += 1
            elif call_type_int == 2:
                outgoing_call_count += 1
            elif call_type_int in {3, 5, 6}:
                missed_rejected_blocked_call_count += 1

        duration = numeric(obj.get("call_duration"))
        if duration is not None:
            valid_duration_rows += 1
            total_call_duration_seconds += duration

    return {
        "call_event_count": call_event_count if rows else pd.NA,
        "incoming_call_count": incoming_call_count if rows else pd.NA,
        "outgoing_call_count": outgoing_call_count if rows else pd.NA,
        "missed_rejected_blocked_call_count": missed_rejected_blocked_call_count if rows else pd.NA,
        "total_call_duration_seconds": total_call_duration_seconds if rows else pd.NA,
        "valid_call_duration_rows": valid_duration_rows,
        "json_parse_errors": json_parse_errors,
        "feature_status": "calculated" if rows else "insufficient_data_no_rows",
    }


def compute_gsm(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cids: list[str] = []
    lacs: list[str] = []
    parse_errors = 0

    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            obj = {}
        cid = obj.get("cid")
        lac = obj.get("lac")
        if cid is not None and str(cid).strip():
            cids.append(str(cid).strip())
        if lac is not None and str(lac).strip():
            lacs.append(str(lac).strip())

    transitions = 0
    previous = None
    for cid in cids:
        if previous is not None and cid != previous:
            transitions += 1
        previous = cid

    return {
        "unique_gsm_cell_count": len(set(cids)) if cids else pd.NA,
        "unique_gsm_lac_count": len(set(lacs)) if lacs else pd.NA,
        "gsm_cell_transition_count": transitions if cids else pd.NA,
        "gsm_rows_in_window": len(rows),
        "gsm_rows_with_cid": len(cids),
        "gsm_rows_with_lac": len(lacs),
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if cids else "insufficient_data_no_valid_gsm_cell_ids",
    }


def valid_cell_value(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"} or text == "-1":
        return ""
    return text


def distinct_gsm_neighbor_observations(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen = set()
    observations = []
    parse_errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if pd.isna(timestamp):
            continue
        cid = str(obj.get("cid") or "").strip()
        lac = str(obj.get("lac") or "").strip()
        psc = str(obj.get("psc") or "").strip()
        signal_strength = str(obj.get("signal_strength") or "").strip()
        key = (int(timestamp), cid, lac, psc, signal_strength)
        if key in seen:
            continue
        seen.add(key)
        observations.append(
            {
                "timestamp": int(timestamp),
                "cid": cid,
                "lac": lac,
                "psc": psc,
                "signal_strength": signal_strength,
            }
        )
    return sorted(observations, key=lambda item: (item["timestamp"], item["cid"], item["lac"], item["psc"])), parse_errors


def compute_gsm_neighbor(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observations, parse_errors = distinct_gsm_neighbor_observations(rows)
    valid_cids = [valid_cell_value(obs["cid"]) for obs in observations]
    valid_cids = [cid for cid in valid_cids if cid]
    valid_lacs = [valid_cell_value(obs["lac"]) for obs in observations]
    valid_lacs = [lac for lac in valid_lacs if lac]

    transitions = 0
    previous_cid = None
    for obs in observations:
        cid = valid_cell_value(obs["cid"])
        if not cid:
            continue
        if previous_cid is not None and cid != previous_cid:
            transitions += 1
        previous_cid = cid

    return {
        "unique_gsm_neighbor_cell_count": len(set(valid_cids)) if valid_cids else pd.NA,
        "unique_gsm_neighbor_lac_count": len(set(valid_lacs)) if valid_lacs else pd.NA,
        "gsm_neighbor_cell_transition_count": transitions if valid_cids else pd.NA,
        "gsm_neighbor_raw_rows_in_window": len(rows),
        "gsm_neighbor_distinct_observation_count": len(observations),
        "gsm_neighbor_valid_cid_observations": len(valid_cids),
        "gsm_neighbor_valid_lac_observations": len(valid_lacs),
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if valid_cids else "insufficient_data_no_valid_neighbor_cell_ids",
    }


def normalize_keyboard_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value)
    if len(text) >= 2 and text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return text


def distinct_keyboard_events(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen = set()
    events = []
    parse_errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if pd.isna(timestamp):
            continue
        before_text = normalize_keyboard_text(obj.get("before_text"))
        current_text = normalize_keyboard_text(obj.get("current_text"))
        package_name = str(obj.get("package_name") or "").strip()
        is_password = str(obj.get("is_password") or "").strip()
        key = (
            int(timestamp),
            str(row.get("device_id")),
            before_text,
            current_text,
            package_name,
            is_password,
        )
        if key in seen:
            continue
        seen.add(key)
        events.append(
            {
                "timestamp": int(timestamp),
                "device_id": str(row.get("device_id")),
                "before_text": before_text,
                "current_text": current_text,
                "package_name": package_name,
                "is_password": is_password,
            }
        )
    return sorted(events, key=lambda x: (x["device_id"], x["package_name"], x["timestamp"])), parse_errors


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    return float(pd.Series(values, dtype="float64").quantile(q))


def compute_keyboard(rows: list[dict[str, Any]]) -> dict[str, Any]:
    events, parse_errors = distinct_keyboard_events(rows)
    active_interval_max_ms = 30_000
    long_pause_threshold_ms = 2_000

    intervals: list[int] = []
    typing_burst_count = 0
    deletion_event_count = 0
    word_completion_times: list[int] = []

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for event in events:
        grouped.setdefault((event["device_id"], event["package_name"]), []).append(event)

    for group_events in grouped.values():
        if not group_events:
            continue
        typing_burst_count += 1
        word_start_ts: int | None = None
        previous_ts: int | None = None
        previous_current = ""

        for event in group_events:
            timestamp = event["timestamp"]
            before_text = event["before_text"]
            current_text = event["current_text"]

            if previous_ts is not None:
                delta = timestamp - previous_ts
                if delta > active_interval_max_ms:
                    typing_burst_count += 1
                    word_start_ts = None
                elif delta > 0:
                    intervals.append(delta)

            if len(current_text) < len(before_text) or len(current_text) < len(previous_current):
                deletion_event_count += 1

            before_ends_space = before_text.endswith(" ")
            current_ends_space = current_text.endswith(" ")
            current_has_nonspace = bool(current_text.strip())
            if word_start_ts is None and current_has_nonspace and not current_ends_space:
                word_start_ts = timestamp
            if before_ends_space and current_has_nonspace and not current_ends_space:
                word_start_ts = timestamp
            if word_start_ts is not None and current_ends_space and not before_ends_space and timestamp >= word_start_ts:
                word_completion_times.append(timestamp - word_start_ts)
                word_start_ts = None

            previous_ts = timestamp
            previous_current = current_text

    median_interval = percentile([float(x) for x in intervals], 0.5)
    interval_q1 = percentile([float(x) for x in intervals], 0.25)
    interval_q3 = percentile([float(x) for x in intervals], 0.75)
    interval_iqr = (interval_q3 - interval_q1) if interval_q1 is not None and interval_q3 is not None else None
    long_pause_count = sum(1 for value in intervals if value > long_pause_threshold_ms)
    median_word_completion = percentile([float(x) for x in word_completion_times], 0.5)

    return {
        "keyboard_median_inter_event_interval_ms": median_interval if median_interval is not None else pd.NA,
        "keyboard_inter_event_interval_iqr_ms": interval_iqr if interval_iqr is not None else pd.NA,
        "keyboard_long_pause_count_2s": long_pause_count if intervals else pd.NA,
        "keyboard_typing_burst_count": typing_burst_count if events else pd.NA,
        "keyboard_median_word_completion_time_ms": median_word_completion if median_word_completion is not None else pd.NA,
        "keyboard_deletion_event_count": deletion_event_count if events else pd.NA,
        "keyboard_raw_rows_in_window": len(rows),
        "keyboard_distinct_observations": len(events),
        "keyboard_interval_count": len(intervals),
        "keyboard_word_completion_count": len(word_completion_times),
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if events else "insufficient_data_no_distinct_keyboard_observations",
    }


def compute_light_from_values(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = []
    night_values = []
    for row in rows:
        lux = numeric(row.get("lux"))
        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if lux is None or pd.isna(timestamp):
            continue
        values.append(lux)
        local_hour = pd.to_datetime(int(timestamp), unit="ms", utc=True).tz_convert(TZ).hour
        if local_hour >= 22 or local_hour < 6:
            night_values.append(lux)

    if not values:
        return {
            "median_light_lux": pd.NA,
            "percent_dark_samples": pd.NA,
            "night_mean_light_lux": pd.NA,
            "light_lux_iqr": pd.NA,
            "light_valid_lux_rows": 0,
            "light_night_lux_rows": 0,
            "feature_status": "insufficient_data_no_valid_lux",
        }

    series = pd.Series(values, dtype="float64")
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    dark_n = int((series < 10).sum())
    return {
        "median_light_lux": float(series.median()),
        "percent_dark_samples": 100.0 * dark_n / len(series),
        "night_mean_light_lux": float(pd.Series(night_values, dtype="float64").mean()) if night_values else pd.NA,
        "light_lux_iqr": q3 - q1,
        "light_valid_lux_rows": len(values),
        "light_night_lux_rows": len(night_values),
        "light_dark_threshold_lux": 10,
        "feature_status": "calculated",
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def distinct_location_observations(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen = set()
    out = []
    parse_errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        lat = numeric(obj.get("double_latitude"))
        lon = numeric(obj.get("double_longitude"))
        if pd.isna(timestamp):
            continue
        key = (
            int(timestamp),
            str(obj.get("double_latitude")),
            str(obj.get("double_longitude")),
            str(obj.get("provider")),
            str(obj.get("accuracy")),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "timestamp": int(timestamp),
                "latitude": lat,
                "longitude": lon,
                "provider": obj.get("provider"),
                "accuracy": numeric(obj.get("accuracy")),
            }
        )
    return sorted(out, key=lambda x: x["timestamp"]), parse_errors


def compute_locations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observations, parse_errors = distinct_location_observations(rows)
    valid_points = [
        obs
        for obs in observations
        if obs["latitude"] is not None
        and obs["longitude"] is not None
        and -90 <= obs["latitude"] <= 90
        and -180 <= obs["longitude"] <= 180
    ]

    total_distance_km = 0.0
    for previous, current in zip(valid_points, valid_points[1:]):
        total_distance_km += haversine_km(
            previous["latitude"],
            previous["longitude"],
            current["latitude"],
            current["longitude"],
        )

    return {
        "location_distinct_observation_count": len(observations) if rows else pd.NA,
        "location_total_distance_km": total_distance_km if len(valid_points) >= 2 else pd.NA,
        "location_raw_rows_in_window": len(rows),
        "location_valid_coordinate_observations": len(valid_points),
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if observations else "insufficient_data_no_distinct_location_observations",
    }


def distinct_message_observations(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen = set()
    out = []
    parse_errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if pd.isna(timestamp):
            continue
        message_type = str(obj.get("message_type") or "").strip()
        trace = str(obj.get("trace") or "").strip()
        key = (int(timestamp), trace, message_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "timestamp": int(timestamp),
                "trace": trace,
                "message_type": message_type,
            }
        )
    return sorted(out, key=lambda x: x["timestamp"]), parse_errors


def compute_messages(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observations, parse_errors = distinct_message_observations(rows)
    outgoing_count = sum(1 for obs in observations if obs["message_type"] == "2")
    return {
        "message_distinct_event_count": len(observations) if rows else pd.NA,
        "outgoing_message_count": outgoing_count if observations else pd.NA,
        "message_raw_rows_in_window": len(rows),
        "message_distinct_observations": len(observations),
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if observations else "insufficient_data_no_distinct_message_observations",
    }


def normalize_activity_name(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def compute_plugin_google_activity_recognition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels: list[str] = []
    active_hours: set[str] = set()
    parse_errors = 0

    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue

        label = normalize_activity_name(obj.get("activity_name"))
        if not label:
            continue
        labels.append(label)

        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if pd.notna(timestamp):
            local_hour = pd.to_datetime(int(timestamp), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H")
            active_hours.add(local_hour)

    label_counts = Counter(labels)
    transitions = 0
    previous_label = None
    for label in labels:
        if previous_label is not None and label != previous_label:
            transitions += 1
        previous_label = label

    total_labels = len(labels)
    return {
        "activity_still_fraction": (
            label_counts.get("still", 0) / total_labels if total_labels else pd.NA
        ),
        "activity_unknown_fraction": (
            label_counts.get("unknown", 0) / total_labels if total_labels else pd.NA
        ),
        "activity_state_diversity": shannon_entropy(label_counts.values()) if total_labels else pd.NA,
        "activity_transition_count": transitions if total_labels else pd.NA,
        "activity_active_hour_count": len(active_hours) if total_labels else pd.NA,
        "activity_recognition_raw_rows_in_window": len(rows),
        "activity_recognition_valid_label_rows": total_labels,
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if total_labels else "insufficient_data_no_valid_activity_labels",
    }


def screen_status_value(obj: dict[str, Any]) -> int | None:
    value = numeric(obj.get("screen_status"))
    if value is None:
        return None
    return int(value)


def compute_screen(rows: list[dict[str, Any]]) -> dict[str, Any]:
    events: list[dict[str, int]] = []
    active_hours: set[str] = set()
    parse_errors = 0

    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        status = screen_status_value(obj)
        if pd.isna(timestamp) or status is None:
            continue
        ts = int(timestamp)
        events.append({"timestamp": ts, "screen_status": status})
        local_dt = pd.to_datetime(ts, unit="ms", utc=True).tz_convert(TZ)
        active_hours.add(local_dt.strftime("%Y-%m-%d %H"))

    events = sorted(events, key=lambda event: event["timestamp"])
    status_counts = Counter(event["screen_status"] for event in events)

    night_count = 0
    for event in events:
        hour = pd.to_datetime(event["timestamp"], unit="ms", utc=True).tz_convert(TZ).hour
        if hour >= 22 or hour < 6:
            night_count += 1

    transitions = 0
    previous_status = None
    for event in events:
        status = event["screen_status"]
        if previous_status is not None and status != previous_status:
            transitions += 1
        previous_status = status

    unlocked_durations_sec: list[float] = []
    unlock_start: int | None = None
    for event in events:
        status = event["screen_status"]
        if status == 3:
            unlock_start = event["timestamp"]
        elif status in {0, 2} and unlock_start is not None and event["timestamp"] >= unlock_start:
            unlocked_durations_sec.append((event["timestamp"] - unlock_start) / 1000.0)
            unlock_start = None

    median_unlocked = percentile(unlocked_durations_sec, 0.5)
    return {
        "screen_event_count": len(events) if events else pd.NA,
        "screen_unlock_event_count": status_counts.get(3, 0) if events else pd.NA,
        "screen_on_event_count": status_counts.get(1, 0) if events else pd.NA,
        "screen_off_event_count": status_counts.get(0, 0) if events else pd.NA,
        "screen_active_hour_count": len(active_hours) if events else pd.NA,
        "night_screen_event_count": night_count if events else pd.NA,
        "screen_transition_count": transitions if events else pd.NA,
        "median_unlocked_session_duration_seconds": median_unlocked if median_unlocked is not None else pd.NA,
        "screen_raw_rows_in_window": len(rows),
        "screen_valid_status_rows": len(events),
        "screen_unlocked_session_count": len(unlocked_durations_sec),
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if events else "insufficient_data_no_valid_screen_status",
    }


def telephony_data_enabled_value(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().lower()
    if text in {"", "nan", "none", "null"}:
        return None
    if text in {"true", "enabled", "on", "connected", "yes"}:
        return True
    if text in {"false", "disabled", "off", "disconnected", "no"}:
        return False
    number = numeric(value)
    if number is None:
        return None
    return int(number) in {1, 2}


def compute_telephony(rows: list[dict[str, Any]]) -> dict[str, Any]:
    parse_errors = 0
    data_enabled_values: list[bool] = []
    network_types: list[str] = []

    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue

        enabled = telephony_data_enabled_value(obj.get("data_enabled"))
        if enabled is not None:
            data_enabled_values.append(enabled)

        network_type = obj.get("network_type")
        if network_type is not None and str(network_type).strip():
            network_types.append(str(network_type).strip())

    network_counts = Counter(network_types)
    return {
        "telephony_event_count": len(rows) if rows else pd.NA,
        "telephony_mobile_data_enabled_fraction": (
            sum(data_enabled_values) / len(data_enabled_values) if data_enabled_values else pd.NA
        ),
        "telephony_network_type_diversity": shannon_entropy(network_counts.values()) if network_types else pd.NA,
        "telephony_raw_rows_in_window": len(rows),
        "telephony_valid_data_enabled_rows": len(data_enabled_values),
        "telephony_valid_network_type_rows": len(network_types),
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if rows else "insufficient_data_no_rows",
    }


def distinct_touch_observations(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen = set()
    observations = []
    parse_errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if pd.isna(timestamp):
            continue
        touch_app = str(obj.get("touch_app") or "").strip()
        touch_action = str(obj.get("touch_action") or "").strip()
        scroll_items = str(obj.get("scroll_items") or "").strip()
        scroll_to_index = str(obj.get("scroll_to_index") or "").strip()
        scroll_from_index = str(obj.get("scroll_from_index") or "").strip()
        touch_action_text = str(obj.get("touch_action_text") or "").strip()
        key = (
            int(timestamp),
            str(row.get("device_id")),
            touch_app,
            touch_action,
            scroll_items,
            scroll_to_index,
            scroll_from_index,
            touch_action_text,
        )
        if key in seen:
            continue
        seen.add(key)
        observations.append(
            {
                "timestamp": int(timestamp),
                "device_id": str(row.get("device_id")),
                "touch_app": touch_app,
                "touch_action": touch_action,
                "scroll_items": scroll_items,
                "scroll_to_index": scroll_to_index,
                "scroll_from_index": scroll_from_index,
            }
        )
    return sorted(observations, key=lambda item: (item["timestamp"], item["device_id"], item["touch_app"])), parse_errors


def touch_scroll_direction(action: str) -> str:
    text = str(action).upper()
    if "SCROLLED_UP" in text:
        return "up"
    if "SCROLLED_DOWN" in text:
        return "down"
    return ""


def compute_touch(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observations, parse_errors = distinct_touch_observations(rows)
    actions = [obs["touch_action"] for obs in observations]
    apps = [obs["touch_app"] for obs in observations if obs["touch_app"]]
    app_counts = Counter(apps)

    click_count = sum(1 for action in actions if action == "ACTION_AWARE_TOUCH_CLICKED")
    scroll_events = [obs for obs in observations if "SCROLLED" in obs["touch_action"].upper()]
    scroll_count = len(scroll_events)

    direction_changes = 0
    previous_direction = ""
    for obs in scroll_events:
        direction = touch_scroll_direction(obs["touch_action"])
        if not direction:
            continue
        if previous_direction and direction != previous_direction:
            direction_changes += 1
        previous_direction = direction

    active_hours: set[str] = set()
    for obs in observations:
        local_hour = pd.to_datetime(obs["timestamp"], unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H")
        active_hours.add(local_hour)

    scroll_index_changes = []
    for obs in scroll_events:
        to_index = numeric(obs["scroll_to_index"])
        from_index = numeric(obs["scroll_from_index"])
        if to_index is None or from_index is None or to_index < 0 or from_index < 0:
            continue
        scroll_index_changes.append(abs(to_index - from_index))

    median_scroll_change = percentile([float(value) for value in scroll_index_changes], 0.5)
    return {
        "touch_distinct_event_count": len(observations) if observations else pd.NA,
        "touch_click_event_count": click_count if observations else pd.NA,
        "touch_scroll_event_count": scroll_count if observations else pd.NA,
        "touch_scroll_direction_change_count": direction_changes if scroll_events else pd.NA,
        "touch_unique_app_count": len(set(apps)) if apps else pd.NA,
        "touch_app_diversity": shannon_entropy(app_counts.values()) if apps else pd.NA,
        "touch_active_hour_count": len(active_hours) if observations else pd.NA,
        "touch_scroll_index_change_median": median_scroll_change if median_scroll_change is not None else pd.NA,
        "touch_raw_rows_in_window": len(rows),
        "touch_distinct_observations": len(observations),
        "touch_valid_app_rows": len(apps),
        "touch_scroll_rows_with_valid_index_change": len(scroll_index_changes),
        "json_parse_errors": parse_errors,
        "feature_status": "calculated" if observations else "insufficient_data_no_distinct_touch_observations",
    }


def compute_features(table_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if table_name == "applications_foreground":
        return compute_applications_foreground(rows)
    if table_name == "battery":
        return compute_battery(rows)
    if table_name == "bluetooth":
        return compute_bluetooth(rows)
    if table_name == "calls":
        return compute_calls(rows)
    if table_name == "gsm":
        return compute_gsm(rows)
    if table_name == "gsm_neighbor":
        return compute_gsm_neighbor(rows)
    if table_name == "keyboard":
        return compute_keyboard(rows)
    if table_name == "light":
        return compute_light_from_values(rows)
    if table_name == "locations":
        return compute_locations(rows)
    if table_name == "messages":
        return compute_messages(rows)
    if table_name == "plugin_google_activity_recognition":
        return compute_plugin_google_activity_recognition(rows)
    if table_name == "screen":
        return compute_screen(rows)
    if table_name == "telephony":
        return compute_telephony(rows)
    if table_name == "touch":
        return compute_touch(rows)
    raise ValueError(f"Unsupported table: {table_name}")


def selected_window_for_patient(conn, table_name: str, patient: pd.Series, device_ids: list[str], hours: int = 24):
    t1_date = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize(TZ)
    week_start = t1_date
    week_end = week_start + pd.Timedelta(days=7)
    latest_fallback_start = week_end - pd.Timedelta(hours=hours)
    primary_start = t1_date + pd.Timedelta(days=1)
    primary_end = primary_start + pd.Timedelta(hours=hours)

    primary_start_ms = local_to_ms(primary_start)
    primary_end_ms = local_to_ms(primary_end)
    week_start_ms = local_to_ms(week_start)
    week_end_ms = local_to_ms(week_end)
    latest_fallback_start_ms = local_to_ms(latest_fallback_start)

    coverage_rows = []
    total_primary_rows = 0
    for device_id in device_ids:
        n_rows, first_ts, last_ts = count_rows(conn, table_name, device_id, primary_start_ms, primary_end_ms)
        total_primary_rows += n_rows
        coverage_rows.append(
            {
                "table_name": table_name,
                "Subject_ID_D": patient["Subject_ID_D"],
                "Subject_ID_N": patient.get("Subject_ID_N", ""),
                "global_T1": patient.get("global_T1", ""),
                "T1_date_iso": patient.get("T1_date_iso", ""),
                "device_id": device_id,
                "window_candidate": "primary_day_after_T1",
                "window_start_ms": primary_start_ms,
                "window_end_ms": primary_end_ms,
                "window_start_local": primary_start.strftime("%Y-%m-%d %H:%M:%S%z"),
                "window_end_local": primary_end.strftime("%Y-%m-%d %H:%M:%S%z"),
                "n_rows": n_rows,
                "first_ts": first_ts,
                "last_ts": last_ts,
                "first_local": ms_to_local(first_ts),
                "last_local": ms_to_local(last_ts),
            }
        )
    if total_primary_rows > 0:
        return {
            "window_rule": "exploratory_primary_day_after_T1",
            "start_ms": primary_start_ms,
            "end_ms": primary_end_ms,
            "start_local": primary_start.strftime("%Y-%m-%d %H:%M:%S%z"),
            "end_local": primary_end.strftime("%Y-%m-%d %H:%M:%S%z"),
            "coverage_rows": coverage_rows,
        }

    first_candidates = []
    for device_id in device_ids:
        first_ts = first_existing_between(conn, table_name, device_id, week_start_ms, latest_fallback_start_ms)
        coverage_rows.append(
            {
                "table_name": table_name,
                "Subject_ID_D": patient["Subject_ID_D"],
                "Subject_ID_N": patient.get("Subject_ID_N", ""),
                "global_T1": patient.get("global_T1", ""),
                "T1_date_iso": patient.get("T1_date_iso", ""),
                "device_id": device_id,
                "window_candidate": "fallback_first_24h_span_within_T1_week_lookup",
                "window_start_ms": week_start_ms,
                "window_end_ms": week_end_ms,
                "window_start_local": week_start.strftime("%Y-%m-%d %H:%M:%S%z"),
                "window_end_local": week_end.strftime("%Y-%m-%d %H:%M:%S%z"),
                "latest_allowed_fallback_start_ms": latest_fallback_start_ms,
                "latest_allowed_fallback_start_local": latest_fallback_start.strftime("%Y-%m-%d %H:%M:%S%z"),
                "n_rows": 1 if first_ts is not None else 0,
                "first_ts": first_ts,
                "last_ts": first_ts,
                "first_local": ms_to_local(first_ts),
                "last_local": ms_to_local(first_ts),
            }
        )
        if first_ts is not None:
            first_candidates.append((first_ts, device_id))

    if not first_candidates:
        return {"coverage_rows": coverage_rows}

    first_ts, _ = min(first_candidates)
    selected_start = pd.to_datetime(first_ts, unit="ms", utc=True).tz_convert(TZ)
    selected_end = selected_start + pd.Timedelta(hours=hours)
    return {
        "window_rule": "exploratory_fallback_first_24h_span_within_T1_week",
        "start_ms": int(first_ts),
        "end_ms": local_to_ms(selected_end),
        "start_local": selected_start.strftime("%Y-%m-%d %H:%M:%S%z"),
        "end_local": selected_end.strftime("%Y-%m-%d %H:%M:%S%z"),
        "coverage_rows": coverage_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Find exploratory protocol-valid T1-week 24h selected-feature values.")
    parser.add_argument("--table", choices=sorted(SAFE_TABLES), help="Run only one reviewed table.")
    parser.add_argument("--max-patients", type=int, default=0, help="Optional cap for debugging; 0 means no cap.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    features_path = (
        OUT_DIR / f"phase2_exploratory_t1_week_24h_selected_features_{args.table}.csv"
        if args.table
        else FEATURES_PATH
    )
    coverage_path = (
        OUT_DIR / f"phase2_exploratory_t1_week_24h_coverage_scan_{args.table}.csv"
        if args.table
        else COVERAGE_PATH
    )
    selected = pd.read_csv(SELECTED_FEATURES_PATH, dtype=str)
    tables = [table for table in selected["source_table"].dropna().unique().tolist() if table in SAFE_TABLES]
    if args.table:
        tables = [args.table]
    ranked_patients = load_ranked_patients()
    ranked_patients = ranked_patients[~ranked_patients["Subject_ID_D"].isin(EXCLUDED_EXPLORATORY_SUBJECTS)].copy()
    if args.max_patients > 0:
        ranked_patients = ranked_patients.head(args.max_patients).copy()
    device_map = load_device_map()

    feature_rows = []
    all_coverage_rows = []
    conn = connect_sensordata_db()
    try:
        for table_name in tables:
            print(f"scanning_table={table_name}", flush=True)
            chosen = None
            selected_for_table = selected[selected["source_table"].astype(str) == table_name]
            selected_feature_names = selected_for_table["feature_name"].dropna().astype(str).tolist()
            for _, patient in ranked_patients.iterrows():
                device_ids = device_map.get(patient["Subject_ID_D"], [])
                if not device_ids:
                    continue
                print(
                    f"  patient={patient['Subject_ID_D']} global_T1={patient.get('global_T1', '')} devices={len(device_ids)}",
                    flush=True,
                )
                window = selected_window_for_patient(conn, table_name, patient, device_ids)
                all_coverage_rows.extend(window.get("coverage_rows", []))
                if "start_ms" not in window:
                    continue
                rows = []
                device_ids_with_rows = set()
                for device_id in device_ids:
                    if table_name == "light":
                        device_rows = fetch_light_lux_values(conn, device_id, window["start_ms"], window["end_ms"])
                    else:
                        device_rows = fetch_rows(conn, table_name, device_id, window["start_ms"], window["end_ms"])
                    if device_rows:
                        device_ids_with_rows.add(device_id)
                    rows.extend(device_rows)
                if not rows:
                    continue
                rows = sorted(rows, key=lambda r: (int(r["timestamp"]), str(r.get("device_id", ""))))
                features = compute_features(table_name, rows)
                has_selected_values = False
                for feature_name in selected_feature_names:
                    value = features.get(feature_name)
                    numeric_value = pd.to_numeric(value, errors="coerce")
                    if not pd.isna(numeric_value):
                        has_selected_values = True
                        break
                if not has_selected_values:
                    print(
                        f"  insufficient_selected_feature_signal patient={patient['Subject_ID_D']} rows={len(rows)} status={features.get('feature_status', '')}",
                        flush=True,
                    )
                    continue
                chosen = {
                    "table_name": table_name,
                    "Subject_ID_D": patient["Subject_ID_D"],
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_ids_used": ";".join(sorted(device_ids_with_rows)),
                    "window_rule": window["window_rule"],
                    "window_start_local": window["start_local"],
                    "window_end_local": window["end_local"],
                    **features,
                }
                print(
                    f"  selected_patient={chosen['Subject_ID_D']} window_rule={chosen['window_rule']} rows={len(rows)}",
                    flush=True,
                )
                break

            if chosen is None:
                print(f"  no_protocol_valid_patient_found_for={table_name}", flush=True)
                for _, selected_feature in selected_for_table.iterrows():
                    feature_rows.append(
                        {
                            "table_name": table_name,
                            "feature_name": str(selected_feature["feature_name"]),
                            "feature_value": pd.NA,
                            "calculation_context": "exploratory_t1_ranked_first_valid_24h_in_T1_week",
                            "Subject_ID_D": "",
                            "Subject_ID_N": "",
                            "device_id_used": "",
                            "global_T1": "",
                            "T1_date_iso": "",
                            "window_rule": "no_protocol_valid_24h_window_in_T1_week",
                            "window_start_local": "",
                            "window_end_local": "",
                            "feature_status": "no_protocol_valid_patient_found",
                            "source_file": str(features_path.relative_to(ROOT)),
                        }
                    )
                continue

            for _, selected_feature in selected_for_table.iterrows():
                feature_name = str(selected_feature["feature_name"])
                value = chosen.get(feature_name)
                if pd.isna(value):
                    continue
                numeric_value = pd.to_numeric(value, errors="coerce")
                if pd.isna(numeric_value):
                    continue
                feature_rows.append(
                    {
                        "table_name": table_name,
                        "feature_name": feature_name,
                        "feature_value": numeric_value,
                        "calculation_context": "exploratory_t1_ranked_first_valid_24h_in_T1_week",
                        "Subject_ID_D": chosen["Subject_ID_D"],
                        "Subject_ID_N": chosen["Subject_ID_N"],
                        "device_id_used": chosen["device_ids_used"],
                        "global_T1": chosen["global_T1"],
                        "T1_date_iso": chosen["T1_date_iso"],
                        "window_rule": chosen["window_rule"],
                        "window_start_local": chosen["window_start_local"],
                        "window_end_local": chosen["window_end_local"],
                        "feature_status": chosen.get("feature_status", "calculated"),
                        "source_file": str(features_path.relative_to(ROOT)),
                    }
                )
    finally:
        conn.close()

    pd.DataFrame(feature_rows).to_csv(features_path, index=False)
    pd.DataFrame(all_coverage_rows).to_csv(coverage_path, index=False)

    print(f"exploratory_feature_rows: {len(feature_rows)}")
    print(features_path)
    if feature_rows:
        print(pd.DataFrame(feature_rows).to_string(index=False))
    print("generated files:")
    print(f"- {features_path}")
    print(f"- {coverage_path}")


if __name__ == "__main__":
    main()
