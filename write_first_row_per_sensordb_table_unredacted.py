from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


OUT_DIR = Path("output/analysis_candidates/phase2_sql_fieldwork_samples")
OUT_CSV = OUT_DIR / "sensordb_first_row_per_table_unredacted.csv"
OUT_MD = OUT_DIR / "sensordb_first_row_per_table_unredacted.md"

SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")
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


def json_ready(value: Any) -> Any:
    value = maybe_parse_json(value)
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_ready(v) for v in value]
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if not isinstance(value, (dict, list, tuple)) and pd.isna(value):
        return None
    return value


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
                        "row_json": "",
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
                                "row_json": "",
                                "error_message": "",
                            }
                        )
                        continue
                    col_names = [d[0] for d in cur.description]
                    row = dict(zip(col_names, fetched))
                    row_json = {str(k): json_ready(v) for k, v in row.items()}
                    rows_out.append(
                        {
                            "database_name": database_name,
                            "table_name": table_name,
                            "status": "ok",
                            "timestamp_ms": row.get("timestamp", ""),
                            "device_id": row.get("device_id", ""),
                            "row_json": json.dumps(row_json, ensure_ascii=False, default=str),
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
                        "row_json": "",
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
        "row_json",
        "error_message",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    lines = ["# SensorDB First Row Per Table - Unredacted", ""]
    lines.append("This file contains one first available row per non-heavy table with no field-level redaction.")
    lines.append("Known high-frequency raw tables are skipped for query safety only.")
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
        if row["row_json"]:
            lines.append("```json")
            lines.append(row["row_json"])
            lines.append("```")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"database_name={database_name}")
    print(f"total_tables={len(rows_out)}")
    print(f"ok_tables={sum(1 for r in rows_out if r['status'] == 'ok')}")
    print(f"skipped_high_frequency_heavy_table={sum(1 for r in rows_out if r['status'] == 'skipped_high_frequency_heavy_table')}")
    print(f"error_tables={sum(1 for r in rows_out if r['status'] == 'error')}")
    print(f"output_csv={OUT_CSV}")
    print(f"output_md={OUT_MD}")


if __name__ == "__main__":
    main()
