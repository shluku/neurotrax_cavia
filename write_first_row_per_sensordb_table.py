from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


OUT_DIR = Path("output/analysis_candidates/phase2_sql_fieldwork_samples")
OUT_CSV = OUT_DIR / "sensordb_first_row_per_table.csv"
OUT_MD = OUT_DIR / "sensordb_first_row_per_table.md"

SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")
SENSITIVE_FIELD_PARTS = [
    "text",
    "current_text",
    "before_text",
    "message",
    "body",
    "phone",
    "number",
    "line_number",
    "subscriber",
    "imei",
    "imei_meid_esn",
    "sim_serial",
    "contact",
    "email",
    "address",
    "ssid",
    "bssid",
]

HIGH_FREQUENCY_TABLES = {
    "accelerometer",
    "linear_accelerometer",
    "gyroscope",
    "rotation",
    "gravity",
    "magnetometer",
}


def safe_ident(table_name: str, whitelist: set[str]) -> str:
    if table_name not in whitelist or not SAFE_TABLE_RE.match(table_name):
        raise ValueError(f"unsafe_or_unknown_table_name:{table_name}")
    return f"`{table_name}`"


def is_sensitive_field(field_name: str) -> bool:
    f = str(field_name).lower()
    if f == "application_name":
        return False
    if f == "name" or f.endswith("_name") or f.startswith("name_"):
        return True
    return any(part in f for part in SENSITIVE_FIELD_PARTS)


def maybe_parse_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")
    if not isinstance(value, str):
        return value
    s = value.strip()
    if not ((s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]"))):
        return value
    try:
        return json.loads(s)
    except Exception:
        return value


def sanitize_value(field_name: str, value: Any) -> Any:
    if is_sensitive_field(field_name):
        return "[REDACTED_SENSITIVE_FIELD]"
    value = maybe_parse_json(value)
    if isinstance(value, dict):
        return {str(k): sanitize_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_value(field_name, v) for v in value]
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if not isinstance(value, (dict, list, tuple)) and pd.isna(value):
        return None
    return value


def sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(k): sanitize_value(str(k), v) for k, v in row.items()}


def fetch_columns(conn, table_name: str, whitelist: set[str]) -> list[str]:
    cur = conn.cursor()
    try:
        cur.execute(f"SHOW COLUMNS FROM {safe_ident(table_name, whitelist)}")
        return [str(r[0]) for r in cur.fetchall()]
    finally:
        cur.close()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows_out = []

    conn = connect_sensordata_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DATABASE()")
        database_name = str(cur.fetchone()[0])
        cur.execute("SHOW TABLES")
        table_names = sorted(str(r[0]) for r in cur.fetchall())
        cur.close()

        whitelist = set(table_names)
        for table_name in table_names:
            if table_name in HIGH_FREQUENCY_TABLES:
                rows_out.append(
                    {
                        "database_name": database_name,
                        "table_name": table_name,
                        "status": "skipped_high_frequency_heavy_table",
                        "timestamp_ms": "",
                        "device_id": "",
                        "row_json_sanitized": "",
                        "error_message": "known high-frequency/heavy raw sensor table; skipped to avoid unsafe slow query",
                    }
                )
                continue
            table_conn = connect_sensordata_db()
            try:
                columns = fetch_columns(table_conn, table_name, whitelist)
                has_timestamp = "timestamp" in columns
                order_clause = "ORDER BY timestamp ASC" if has_timestamp else ""
                cur = table_conn.cursor()
                try:
                    cur.execute(
                        f"""
                        SELECT /*+ MAX_EXECUTION_TIME(15000) */ *
                        FROM {safe_ident(table_name, whitelist)}
                        {order_clause}
                        LIMIT 1
                        """
                    )
                    fetched = cur.fetchone()
                    if fetched is None:
                        rows_out.append(
                            {
                                "database_name": database_name,
                                "table_name": table_name,
                                "status": "empty_or_no_row_returned",
                                "timestamp_ms": "",
                                "device_id": "",
                                "row_json_sanitized": "",
                                "error_message": "",
                            }
                        )
                        continue
                    col_names = [d[0] for d in cur.description]
                    row = dict(zip(col_names, fetched))
                    sanitized = sanitize_row(row)
                    rows_out.append(
                        {
                            "database_name": database_name,
                            "table_name": table_name,
                            "status": "ok",
                            "timestamp_ms": row.get("timestamp", ""),
                            "device_id": row.get("device_id", ""),
                            "row_json_sanitized": json.dumps(sanitized, ensure_ascii=False, default=str),
                            "error_message": "",
                        }
                    )
                finally:
                    cur.close()
            except Exception as exc:
                rows_out.append(
                    {
                        "database_name": database_name,
                        "table_name": table_name,
                        "status": "error",
                        "timestamp_ms": "",
                        "device_id": "",
                        "row_json_sanitized": "",
                        "error_message": str(exc)[:1000],
                    }
                )
            finally:
                table_conn.close()
    finally:
        conn.close()

    fieldnames = [
        "database_name",
        "table_name",
        "status",
        "timestamp_ms",
        "device_id",
        "row_json_sanitized",
        "error_message",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    lines = ["# SensorDB First Row Per Table", ""]
    lines.append("Sensitive fields are redacted. Tables that failed or timed out are recorded with the error message.")
    lines.append("")
    for row in rows_out:
        lines.append(f"## {row['table_name']}")
        lines.append(f"- status: {row['status']}")
        if row["timestamp_ms"] != "":
            lines.append(f"- timestamp_ms: {row['timestamp_ms']}")
        if row["device_id"] != "":
            lines.append(f"- device_id: {row['device_id']}")
        if row["error_message"]:
            lines.append(f"- error_message: {row['error_message']}")
        if row["row_json_sanitized"]:
            lines.append("```json")
            lines.append(row["row_json_sanitized"])
            lines.append("```")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"database_name={database_name}")
    print(f"total_tables={len(rows_out)}")
    print(f"ok_tables={sum(1 for r in rows_out if r['status'] == 'ok')}")
    print(f"error_tables={sum(1 for r in rows_out if r['status'] == 'error')}")
    print(f"output_csv={OUT_CSV}")
    print(f"output_md={OUT_MD}")


if __name__ == "__main__":
    main()
