from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


ROOT = Path(__file__).parent
OUT_DIR = ROOT / "output/analysis_candidates/phase2_large_sensor_metadata"
COGNITIVE_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
LABEL_DEVICE_MAP_PATH = ROOT / "output/label_device_map.csv"
TZ = "Asia/Jerusalem"
SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")

TABLES = [
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

SKIP_BOUNDED_AVAILABILITY_TABLES = {
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
}

WINDOW_SPECS = [
    ("t1_day_after", "T1_date_iso", 1, 2),
    ("t1_week_after", "T1_date_iso", 0, 7),
    ("t2_day_before", "T2_date_iso", -1, 0),
]


def normalize_subject_id(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def local_to_ms(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def ms_to_local_date(ms: Any) -> str:
    value = pd.to_numeric(ms, errors="coerce")
    if pd.isna(value):
        return ""
    return pd.to_datetime(int(value), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d")


def safe_ident(table_name: str, whitelist: set[str]) -> str:
    if table_name not in whitelist or not SAFE_TABLE_RE.match(table_name):
        raise ValueError(f"unsafe_or_unknown_table:{table_name}")
    return f"`{table_name}`"


def get_tables(conn) -> set[str]:
    cur = conn.cursor()
    try:
        cur.execute("SHOW TABLES")
        return {str(row[0]) for row in cur.fetchall()}
    finally:
        cur.close()


def show_columns(conn, table_name: str, whitelist: set[str]) -> pd.DataFrame:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"SHOW COLUMNS FROM {safe_ident(table_name, whitelist)}")
        return pd.DataFrame(cur.fetchall())
    finally:
        cur.close()


def show_indexes(conn, table_name: str, whitelist: set[str]) -> pd.DataFrame:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"SHOW INDEX FROM {safe_ident(table_name, whitelist)}")
        return pd.DataFrame(cur.fetchall())
    finally:
        cur.close()


def show_table_status(conn, table_name: str) -> dict[str, Any]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SHOW TABLE STATUS LIKE %s", (table_name,))
        return cur.fetchone() or {}
    finally:
        cur.close()


def load_patients() -> pd.DataFrame:
    df = pd.read_csv(COGNITIVE_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id)
    t1 = pd.to_datetime(df.get("T1_date_iso", pd.Series(dtype=str)), errors="coerce")
    df = df[t1.notna()].copy()
    df = df[df["Subject_ID_D"].ne("001")].copy()
    return df.sort_values("Subject_ID_D")


def load_device_map() -> dict[str, list[str]]:
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    out: dict[str, list[str]] = {}
    exact_seen: set[str] = set()
    for _, row in label_map.iterrows():
        raw_label = "" if pd.isna(row.get("label")) else str(row.get("label")).strip()
        subject_id = normalize_subject_id(raw_label)
        if not subject_id or subject_id.lower() in {"nan", "none"}:
            continue
        is_exact = raw_label.isdigit() and len(raw_label) == 3
        if subject_id in exact_seen and not is_exact:
            continue
        raw_devices = "" if pd.isna(row.get("device_ids")) else str(row.get("device_ids"))
        out[subject_id] = [
            item.strip()
            for item in raw_devices.split(";")
            if item.strip() and item.strip().lower() not in {"nan", "none"}
        ]
        if is_exact:
            exact_seen.add(subject_id)
    return out


def patient_window(patient: pd.Series, date_col: str, start_offset_days: int, end_offset_days: int) -> tuple[int, int, str, str] | None:
    raw = patient.get(date_col)
    if pd.isna(raw) or str(raw).strip() == "":
        return None
    base = pd.Timestamp(str(raw)).tz_localize(TZ)
    start = base + pd.Timedelta(days=start_offset_days)
    end = base + pd.Timedelta(days=end_offset_days)
    return local_to_ms(start), local_to_ms(end), start.strftime("%Y-%m-%d %H:%M:%S%z"), end.strftime("%Y-%m-%d %H:%M:%S%z")


def exists_in_window(conn, quoted_table: str, device_id: str, start_ms: int, end_ms: int) -> tuple[bool, Any, Any]:
    cur = conn.cursor(dictionary=True)
    try:
        try:
            cur.execute("SET SESSION MAX_EXECUTION_TIME=15000")
        except Exception:
            pass
        cur.execute(
            f"""
            SELECT timestamp
            FROM {quoted_table}
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        first = cur.fetchone()
        if not first:
            return False, None, None
        cur.execute(
            f"""
            SELECT timestamp
            FROM {quoted_table}
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        last = cur.fetchone()
        return True, first.get("timestamp"), (last or {}).get("timestamp")
    finally:
        cur.close()


def write_readme(paths: dict[str, Path]) -> None:
    paths["readme"].write_text(
        """# Phase 2 Large Sensor Table Metadata Scan

This folder contains metadata-only fieldwork for large or raw SensorDB sensor tables.

Tables scanned:

- accelerometer
- aware_log
- barometer
- gravity
- gyroscope
- light
- linear_accelerometer
- magnetometer
- proximity
- rotation

What was collected:

- `SHOW TABLE STATUS LIKE ...` metadata, including approximate row count and table size.
- `SHOW COLUMNS` schema metadata.
- `SHOW INDEX` index metadata.
- Availability status rows documenting that bounded patient/window checks were intentionally skipped for these large/raw streams.

What was intentionally not collected:

- No full-table grouped row counts.
- No full raw sensor extraction.
- No feature extraction.
- No unbounded T1-to-T2 scans.

Why bounded patient availability was skipped:

- These tables were the ones that previously made global coverage scans slow or unavailable.
- Even bounded `LIMIT 1` checks can be slow on multi-hundred-GB or multi-TB raw streams depending on index layout.
- The current purpose is metadata and planning, not extraction.

If a table is selected later for feature work, run a separate table-specific bounded sampler with explicit chunking and stop rules.

These outputs support Phase 2 planning for large tables. Missing data remains missing and must not be interpreted as zero activity.
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "table_metadata": OUT_DIR / "phase2_large_sensor_table_metadata.csv",
        "columns": OUT_DIR / "phase2_large_sensor_table_columns.csv",
        "indexes": OUT_DIR / "phase2_large_sensor_table_indexes.csv",
        "availability": OUT_DIR / "phase2_large_sensor_bounded_patient_availability.csv",
        "summary": OUT_DIR / "phase2_large_sensor_bounded_patient_summary.csv",
        "readme": OUT_DIR / "README_phase2_large_sensor_table_metadata_scan.md",
    }

    patients = load_patients()
    device_map = load_device_map()
    metadata_rows: list[dict[str, Any]] = []
    column_frames: list[pd.DataFrame] = []
    index_frames: list[pd.DataFrame] = []
    availability_rows: list[dict[str, Any]] = []

    conn = connect_sensordata_db()
    try:
        whitelist = get_tables(conn)
        for table_name in TABLES:
            print(f"table={table_name}", flush=True)
            table_row: dict[str, Any] = {"table_name": table_name}
            if table_name not in whitelist:
                table_row.update({"table_exists": False, "metadata_status": "missing_table"})
                metadata_rows.append(table_row)
                pd.DataFrame(metadata_rows).to_csv(paths["table_metadata"], index=False)
                continue

            table_row["table_exists"] = True
            try:
                cols = show_columns(conn, table_name, whitelist)
                idx = show_indexes(conn, table_name, whitelist)
                status = show_table_status(conn, table_name)
                columns = set(cols["Field"].astype(str)) if not cols.empty and "Field" in cols.columns else set()
                table_row.update(
                    {
                        "has_device_id": "device_id" in columns,
                        "has_timestamp": "timestamp" in columns,
                        "has_data": "data" in columns,
                        "n_columns": len(columns),
                        "metadata_estimated_rows": status.get("Rows"),
                        "data_length_bytes": status.get("Data_length"),
                        "index_length_bytes": status.get("Index_length"),
                        "total_size_bytes": (int(status.get("Data_length") or 0) + int(status.get("Index_length") or 0)),
                        "total_size_gb": round((int(status.get("Data_length") or 0) + int(status.get("Index_length") or 0)) / (1024**3), 3),
                        "create_time": status.get("Create_time"),
                        "update_time": status.get("Update_time"),
                        "metadata_status": "ok",
                        "error_message": "",
                    }
                )
                cols.insert(0, "table_name", table_name)
                idx.insert(0, "table_name", table_name)
                column_frames.append(cols)
                index_frames.append(idx)
                pd.concat(column_frames, ignore_index=True).to_csv(paths["columns"], index=False)
                pd.concat(index_frames, ignore_index=True).to_csv(paths["indexes"], index=False)

                if not {"device_id", "timestamp"}.issubset(columns):
                    metadata_rows.append(table_row)
                    pd.DataFrame(metadata_rows).to_csv(paths["table_metadata"], index=False)
                    continue

                if table_name in SKIP_BOUNDED_AVAILABILITY_TABLES:
                    for window_name, _, _, _ in WINDOW_SPECS:
                        availability_rows.append(
                            {
                                "table_name": table_name,
                                "Subject_ID_D": "",
                                "Subject_ID_N": "",
                                "window_name": window_name,
                                "window_start_local": "",
                                "window_end_local": "",
                                "n_devices_mapped": "",
                                "n_devices_checked_until_result": "",
                                "has_data": "",
                                "first_row_date": "",
                                "last_row_date": "",
                                "status": "skipped_metadata_only_large_raw_stream",
                                "error_message": "bounded patient availability intentionally skipped for large raw/quality-log stream",
                            }
                        )
                    pd.DataFrame(availability_rows).to_csv(paths["availability"], index=False)
                    metadata_rows.append(table_row)
                    pd.DataFrame(metadata_rows).to_csv(paths["table_metadata"], index=False)
                    continue

                quoted_table = safe_ident(table_name, whitelist)
                for _, patient in patients.iterrows():
                    subject_id = patient["Subject_ID_D"]
                    device_ids = device_map.get(subject_id, [])
                    for window_name, date_col, start_offset, end_offset in WINDOW_SPECS:
                        win = patient_window(patient, date_col, start_offset, end_offset)
                        if win is None:
                            continue
                        start_ms, end_ms, start_local, end_local = win
                        patient_has_data = False
                        first_ts = None
                        last_ts = None
                        error_message = ""
                        checked_devices = 0
                        for device_id in device_ids:
                            checked_devices += 1
                            try:
                                has_data, first, last = exists_in_window(conn, quoted_table, device_id, start_ms, end_ms)
                            except Exception as exc:
                                error_message = str(exc)
                                break
                            if has_data:
                                patient_has_data = True
                                first_ts = first
                                last_ts = last
                                break
                        availability_rows.append(
                            {
                                "table_name": table_name,
                                "Subject_ID_D": subject_id,
                                "Subject_ID_N": patient.get("Subject_ID_N", ""),
                                "window_name": window_name,
                                "window_start_local": start_local,
                                "window_end_local": end_local,
                                "n_devices_mapped": len(device_ids),
                                "n_devices_checked_until_result": checked_devices,
                                "has_data": patient_has_data,
                                "first_row_date": ms_to_local_date(first_ts),
                                "last_row_date": ms_to_local_date(last_ts),
                                "status": "error" if error_message else "ok",
                                "error_message": error_message,
                            }
                        )
                pd.DataFrame(availability_rows).to_csv(paths["availability"], index=False)
            except Exception as exc:
                table_row.update({"metadata_status": "error", "error_message": str(exc)})
            metadata_rows.append(table_row)
            pd.DataFrame(metadata_rows).to_csv(paths["table_metadata"], index=False)
    finally:
        conn.close()

    availability = pd.DataFrame(availability_rows)
    if not availability.empty:
        ok_summary = (
            availability[availability["status"].eq("ok")]
            .groupby(["table_name", "window_name"], as_index=False)
            .agg(
                patients_checked=("Subject_ID_D", "nunique"),
                patients_with_data=("has_data", "sum"),
            )
        )
        if not ok_summary.empty:
            ok_summary["patients_with_data"] = ok_summary["patients_with_data"].astype(int)
            ok_summary["percentage_with_data"] = (
                100 * ok_summary["patients_with_data"] / ok_summary["patients_checked"]
            ).round(1)
            ok_summary["status"] = "ok"
            ok_summary["note"] = ""
        skipped = availability[availability["status"].astype(str).str.startswith("skipped")].copy()
        skipped_summary = pd.DataFrame()
        if not skipped.empty:
            skipped_summary = skipped[["table_name", "window_name", "status", "error_message"]].drop_duplicates()
            skipped_summary = skipped_summary.rename(columns={"error_message": "note"})
            skipped_summary["patients_checked"] = 0
            skipped_summary["patients_with_data"] = pd.NA
            skipped_summary["percentage_with_data"] = pd.NA
            skipped_summary = skipped_summary[
                [
                    "table_name",
                    "window_name",
                    "patients_checked",
                    "patients_with_data",
                    "percentage_with_data",
                    "status",
                    "note",
                ]
            ]
        summary = pd.concat([ok_summary, skipped_summary], ignore_index=True)
        summary.to_csv(paths["summary"], index=False)
    else:
        pd.DataFrame(columns=["table_name", "window_name", "patients_checked", "patients_with_data", "percentage_with_data"]).to_csv(
            paths["summary"], index=False
        )

    write_readme(paths)
    print("generated files:")
    for path in paths.values():
        print(path)
    print(f"tables_requested: {len(TABLES)}")
    print(f"patients_checked: {patients['Subject_ID_D'].nunique()}")
    print(f"availability_rows: {len(availability_rows)}")


if __name__ == "__main__":
    main()
