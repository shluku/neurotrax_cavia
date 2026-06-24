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

SAFE_TABLES = {"applications_foreground", "battery", "bluetooth", "calls", "gsm", "keyboard"}
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
    if table_name == "keyboard":
        return compute_keyboard(rows)
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
                for device_id in device_ids:
                    rows.extend(fetch_rows(conn, table_name, device_id, window["start_ms"], window["end_ms"]))
                if not rows:
                    continue
                rows = sorted(rows, key=lambda r: (int(r["timestamp"]), str(r["device_id"])))
                features = compute_features(table_name, rows)
                chosen = {
                    "table_name": table_name,
                    "Subject_ID_D": patient["Subject_ID_D"],
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_ids_used": ";".join(device_ids),
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
                selected_for_table = selected[selected["source_table"].astype(str) == table_name]
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

            selected_for_table = selected[selected["source_table"].astype(str) == table_name]
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
