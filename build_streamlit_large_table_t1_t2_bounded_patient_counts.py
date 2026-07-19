from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


ROOT = Path(__file__).parent
COGNITIVE_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
LABEL_DEVICE_MAP_PATH = ROOT / "output/label_device_map.csv"
TIMEOUT_STATUS_PATH = ROOT / "output/analysis_candidates/phase2_feature_review/streamlit_timeout_table_patient_counts.csv"
OUT_DIR = ROOT / "output/analysis_candidates/phase2_feature_review"
SUMMARY_PATH = OUT_DIR / "streamlit_large_table_t1_t2_bounded_patient_counts.csv"
DETAIL_PATH = OUT_DIR / "streamlit_large_table_t1_t2_bounded_patient_counts_detail.csv"
SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")
TZ = "Asia/Jerusalem"


def normalize_subject_id(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def load_patients() -> pd.DataFrame:
    df = pd.read_csv(COGNITIVE_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id)
    df = df.dropna(subset=["Subject_ID_D", "T1_date_iso"]).copy()
    return df[df["Subject_ID_D"].astype(str).str.len() > 0].copy()


def load_device_map() -> dict[str, list[str]]:
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    exact: dict[str, list[str]] = {}
    fallback: dict[str, list[str]] = {}
    for _, row in label_map.iterrows():
        raw_label = "" if pd.isna(row.get("label")) else str(row.get("label")).strip()
        subject_id = normalize_subject_id(raw_label)
        if not subject_id or subject_id.lower() in {"nan", "none"}:
            continue
        raw_devices = "" if pd.isna(row.get("device_ids")) else str(row.get("device_ids"))
        devices = [
            device.strip()
            for device in raw_devices.split(";")
            if device.strip() and device.strip().lower() not in {"nan", "none"}
        ]
        if raw_label.isdigit() and len(raw_label) == 3:
            exact[subject_id] = sorted(set(devices))
        elif raw_label.isdigit():
            fallback.setdefault(subject_id, sorted(set(devices)))
    out = dict(fallback)
    out.update(exact)
    return out


def local_to_ms(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def date_window_ms(date_iso: str, *, offset_days: int) -> tuple[int, int, str, str]:
    start = pd.Timestamp(str(date_iso)).tz_localize(TZ) + pd.Timedelta(days=offset_days)
    end = start + pd.Timedelta(days=1)
    return local_to_ms(start), local_to_ms(end), start.date().isoformat(), end.date().isoformat()


def t2_before_window_ms(date_iso: str) -> tuple[int, int, str, str]:
    end = pd.Timestamp(str(date_iso)).tz_localize(TZ)
    start = end - pd.Timedelta(days=1)
    return local_to_ms(start), local_to_ms(end), start.date().isoformat(), end.date().isoformat()


def target_tables() -> list[str]:
    if TIMEOUT_STATUS_PATH.exists():
        status = pd.read_csv(TIMEOUT_STATUS_PATH, dtype=str)
        return status["table_name"].dropna().astype(str).tolist()
    return [
        "accelerometer",
        "aware_log",
        "barometer",
        "gravity",
        "gyroscope",
        "light",
        "linear_accelerometer",
        "magnetometer",
        "proximity",
        "rotation",
    ]


def safe_ident(table_name: str, whitelist: set[str]) -> str:
    if table_name not in whitelist or not SAFE_TABLE_RE.match(table_name):
        raise ValueError(f"unsafe_or_unknown_table:{table_name}")
    return f"`{table_name}`"


def distinct_devices_in_window(conn, quoted_table: str, devices: list[str], start_ms: int, end_ms: int) -> set[str]:
    if not devices:
        return set()
    placeholders = ", ".join(["%s"] * len(devices))
    params = [int(start_ms), int(end_ms), *devices]
    cur = conn.cursor()
    try:
        try:
            cur.execute("SET SESSION MAX_EXECUTION_TIME=10000")
        except Exception:
            pass
        cur.execute(
            f"""
            SELECT DISTINCT device_id
            FROM {quoted_table}
            WHERE timestamp >= %s
              AND timestamp < %s
              AND device_id IN ({placeholders})
            """,
            params,
        )
        return {str(row[0]) for row in cur.fetchall()}
    finally:
        cur.close()


def build_window_maps(patients: pd.DataFrame, device_map: dict[str, list[str]]):
    t1_windows: dict[tuple[int, int, str, str], list[tuple[str, set[str]]]] = {}
    t2_windows: dict[tuple[int, int, str, str], list[tuple[str, set[str]]]] = {}
    for _, patient in patients.iterrows():
        subject_id = str(patient["Subject_ID_D"])
        devices = set(device_map.get(subject_id, []))
        if not devices:
            continue
        t1_key = date_window_ms(str(patient["T1_date_iso"]), offset_days=1)
        t1_windows.setdefault(t1_key, []).append((subject_id, devices))
        t2_date = patient.get("T2_date_iso")
        if pd.notna(t2_date) and str(t2_date).strip():
            t2_key = t2_before_window_ms(str(t2_date))
            t2_windows.setdefault(t2_key, []).append((subject_id, devices))
    return t1_windows, t2_windows


def check_windows(conn, quoted_table: str, windows: dict, all_devices: list[str]):
    subjects_with_data = set()
    detail = []
    errors = []
    for (start_ms, end_ms, start_date, end_date), subject_device_pairs in windows.items():
        try:
            devices_with_rows = distinct_devices_in_window(conn, quoted_table, all_devices, start_ms, end_ms)
        except Exception as exc:
            errors.append(str(exc))
            if len(errors) >= 5:
                break
            continue
        for subject_id, devices in subject_device_pairs:
            has_data = bool(devices & devices_with_rows)
            if has_data:
                subjects_with_data.add(subject_id)
            detail.append(
                {
                    "Subject_ID_D": subject_id,
                    "window_start_date": start_date,
                    "window_end_date": end_date,
                    "has_data": has_data,
                }
            )
    return subjects_with_data, detail, errors


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    patients = load_patients()
    device_map = load_device_map()
    all_devices = sorted({device for devices in device_map.values() for device in devices})
    t1_windows, t2_windows = build_window_maps(patients, device_map)
    t1_eligible = len({subject for pairs in t1_windows.values() for subject, _ in pairs})
    t2_eligible = len({subject for pairs in t2_windows.values() for subject, _ in pairs})

    summary_rows = []
    detail_rows = []
    conn = connect_sensordata_db()
    try:
        cur = conn.cursor()
        try:
            cur.execute("SHOW TABLES")
            whitelist = {str(row[0]) for row in cur.fetchall()}
        finally:
            cur.close()

        for table_name in target_tables():
            print(f"table={table_name}", flush=True)
            quoted = safe_ident(table_name, whitelist)
            t1_subjects, t1_detail, t1_errors = check_windows(conn, quoted, t1_windows, all_devices)
            t2_subjects, t2_detail, t2_errors = check_windows(conn, quoted, t2_windows, all_devices)
            for row in t1_detail:
                detail_rows.append({"table_name": table_name, "window_name": "t1_day_after", **row})
            for row in t2_detail:
                detail_rows.append({"table_name": table_name, "window_name": "t2_day_before", **row})
            errors = t1_errors + t2_errors
            summary_rows.append(
                {
                    "table_name": table_name,
                    "t1_day_after_patients_with_data": len(t1_subjects),
                    "t1_eligible_patients": t1_eligible,
                    "t1_day_after_percentage": round(100 * len(t1_subjects) / t1_eligible, 1) if t1_eligible else pd.NA,
                    "t2_day_before_patients_with_data": len(t2_subjects),
                    "t2_eligible_patients": t2_eligible,
                    "t2_day_before_percentage": round(100 * len(t2_subjects) / t2_eligible, 1) if t2_eligible else pd.NA,
                    "query_rule": "timestamp_window_and_device_id_in_bounded_exists",
                    "error_count": len(errors),
                    "first_error": errors[0] if errors else "",
                }
            )
    finally:
        conn.close()

    summary = pd.DataFrame(summary_rows)
    detail = pd.DataFrame(detail_rows)
    summary.to_csv(SUMMARY_PATH, index=False)
    detail.to_csv(DETAIL_PATH, index=False)
    print("generated files:")
    print(SUMMARY_PATH)
    print(DETAIL_PATH)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
