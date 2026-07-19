from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


ROOT = Path(__file__).parent
LABEL_DEVICE_MAP_PATH = ROOT / "output/label_device_map.csv"
TRACKING_PATH = ROOT / "phase2_table_tracking.csv"
OUT_DIR = ROOT / "output/analysis_candidates/phase2_feature_review"
PREVIEW_PATH = OUT_DIR / "streamlit_global_patient_coverage_preview.csv"
STATUS_PATH = OUT_DIR / "streamlit_global_patient_coverage_status.csv"
SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")
MAX_DATA_BYTES = 200 * 1024**3


def normalize_subject_id(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def load_device_subject_lookup() -> dict[str, str]:
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    numeric_lookup: dict[str, str] = {}
    fallback_lookup: dict[str, str] = {}
    for _, row in label_map.iterrows():
        raw_label = "" if pd.isna(row.get("label")) else str(row.get("label")).strip()
        subject_id = normalize_subject_id(raw_label)
        if not subject_id or subject_id.lower() in {"nan", "none"}:
            continue
        raw_devices = "" if pd.isna(row.get("device_ids")) else str(row.get("device_ids"))
        for device_id in raw_devices.split(";"):
            device_id = device_id.strip()
            if device_id and device_id.lower() not in {"nan", "none"}:
                if raw_label.isdigit():
                    numeric_lookup.setdefault(device_id, subject_id)
                else:
                    fallback_lookup.setdefault(device_id, subject_id)
    return {**fallback_lookup, **numeric_lookup}


def ms_to_date(ms: Any) -> str:
    value = pd.to_numeric(ms, errors="coerce")
    if pd.isna(value):
        return ""
    return pd.to_datetime(int(value), unit="ms", utc=True).tz_convert("Asia/Jerusalem").date().isoformat()


def safe_ident(table_name: str, whitelist: set[str]) -> str:
    if table_name not in whitelist or not SAFE_TABLE_RE.match(table_name):
        raise ValueError(f"unsafe_or_unknown_table:{table_name}")
    return f"`{table_name}`"


def table_status(conn, table_name: str) -> dict[str, Any]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SHOW TABLE STATUS LIKE %s", (table_name,))
        return cur.fetchone() or {}
    finally:
        cur.close()


def table_columns(conn, table_name: str, whitelist: set[str]) -> set[str]:
    cur = conn.cursor()
    try:
        cur.execute(f"SHOW COLUMNS FROM {safe_ident(table_name, whitelist)}")
        return {str(row[0]) for row in cur.fetchall()}
    finally:
        cur.close()


def device_coverage(conn, table_name: str, whitelist: set[str]) -> pd.DataFrame:
    cur = conn.cursor(dictionary=True)
    try:
        try:
            cur.execute("SET SESSION MAX_EXECUTION_TIME=60000")
        except Exception:
            pass
        cur.execute(
            f"""
            SELECT device_id, COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM {safe_ident(table_name, whitelist)}
            GROUP BY device_id
            ORDER BY n_rows DESC
            """
        )
        return pd.DataFrame(cur.fetchall())
    finally:
        cur.close()


def load_requested_tables(conn) -> list[str]:
    cur = conn.cursor()
    try:
        cur.execute("SHOW TABLES")
        db_tables = sorted({str(row[0]) for row in cur.fetchall()})
    finally:
        cur.close()
    if TRACKING_PATH.exists():
        tracking = pd.read_csv(TRACKING_PATH, dtype=str)
        if "table_name" in tracking.columns:
            tracked = [str(x) for x in tracking["table_name"].dropna().tolist()]
            return [t for t in tracked if t in db_tables]
    return db_tables


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lookup = load_device_subject_lookup()
    preview_rows = []
    status_rows = []

    conn = connect_sensordata_db()
    try:
        cur = conn.cursor()
        try:
            cur.execute("SHOW TABLES")
            whitelist = {str(row[0]) for row in cur.fetchall()}
        finally:
            cur.close()

        for table_name in load_requested_tables(conn):
            print(f"table={table_name}", flush=True)
            status = table_status(conn, table_name)
            data_length = int(status.get("Data_length") or 0)
            estimated_rows = int(status.get("Rows") or 0)
            if data_length > MAX_DATA_BYTES:
                status_rows.append(
                    {
                        "table_name": table_name,
                        "status": "skipped_above_200gb",
                        "estimated_rows": estimated_rows,
                        "data_gb": round(data_length / 1024**3, 2),
                        "error_message": "",
                    }
                )
                continue
            cols = table_columns(conn, table_name, whitelist)
            if not {"device_id", "timestamp"}.issubset(cols):
                status_rows.append(
                    {
                        "table_name": table_name,
                        "status": "skipped_missing_device_id_or_timestamp",
                        "estimated_rows": estimated_rows,
                        "data_gb": round(data_length / 1024**3, 2),
                        "error_message": "",
                    }
                )
                continue
            try:
                device_df = device_coverage(conn, table_name, whitelist)
                if device_df.empty:
                    status_rows.append(
                        {
                            "table_name": table_name,
                            "status": "ok_no_rows",
                            "estimated_rows": estimated_rows,
                            "data_gb": round(data_length / 1024**3, 2),
                            "error_message": "",
                        }
                    )
                    continue
                device_df["Subject_ID_D"] = device_df["device_id"].astype(str).map(lookup).fillna("NOT_MAPPED")
                mapped = device_df[device_df["Subject_ID_D"].ne("NOT_MAPPED")].copy()
                if not mapped.empty:
                    mapped["n_rows"] = pd.to_numeric(mapped["n_rows"], errors="coerce").fillna(0).astype("int64")
                    subject_df = (
                        mapped.groupby("Subject_ID_D", as_index=False)
                        .agg(
                            rows=("n_rows", "sum"),
                            devices=("device_id", "nunique"),
                            first_ts=("first_ts", "min"),
                            last_ts=("last_ts", "max"),
                        )
                        .sort_values(["rows", "Subject_ID_D"], ascending=[False, True])
                    )
                    for _, row in subject_df.iterrows():
                        preview_rows.append(
                            {
                                "table_name": table_name,
                                "Subject_ID_D": row["Subject_ID_D"],
                                "rows": int(row["rows"]),
                                "devices": int(row["devices"]),
                                "first row": ms_to_date(row["first_ts"]),
                                "last row": ms_to_date(row["last_ts"]),
                            }
                        )
                status_rows.append(
                    {
                        "table_name": table_name,
                        "status": "ok",
                        "estimated_rows": estimated_rows,
                        "data_gb": round(data_length / 1024**3, 2),
                        "error_message": "",
                    }
                )
            except Exception as exc:
                status_rows.append(
                    {
                        "table_name": table_name,
                        "status": "error",
                        "estimated_rows": estimated_rows,
                        "data_gb": round(data_length / 1024**3, 2),
                        "error_message": str(exc),
                    }
                )
    finally:
        conn.close()

    preview = pd.DataFrame(preview_rows)
    status = pd.DataFrame(status_rows)
    preview.to_csv(PREVIEW_PATH, index=False)
    status.to_csv(STATUS_PATH, index=False)
    print("generated files:")
    print(PREVIEW_PATH)
    print(STATUS_PATH)
    print(f"preview_rows: {len(preview)}")
    print(status["status"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
