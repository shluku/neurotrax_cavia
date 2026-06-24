from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


OUT_ROOT = Path("output/analysis_candidates/phase2_feature_review")
SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")
TZ = "Asia/Jerusalem"


def safe_ident(table_name: str, whitelist: set[str]) -> str:
    if table_name not in whitelist or not SAFE_TABLE_RE.match(table_name):
        raise ValueError(f"unsafe_or_unknown_table_name:{table_name}")
    return f"`{table_name}`"


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


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


SENSITIVE_KEY_PARTS = [
    "text",
    "message",
    "body",
    "phone",
    "number",
    "line_number",
    "subscriber",
    "imei",
    "sim_serial",
    "contact",
    "email",
    "address",
    "name",
    "ssid",
    "bssid",
]


def is_sensitive_key(key: str) -> bool:
    key_lower = key.lower()
    if key_lower == "application_name":
        return False
    return any(part in key_lower for part in SENSITIVE_KEY_PARTS)


def sanitize_json_value(key: str, value: Any) -> Any:
    return value


def to_local_datetime(timestamp_ms: Any) -> str:
    ts = pd.to_numeric(timestamp_ms, errors="coerce")
    if pd.isna(ts):
        return ""
    return pd.to_datetime(int(ts), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z")


def get_tables(conn) -> set[str]:
    cur = conn.cursor()
    try:
        cur.execute("SHOW TABLES")
        return {str(r[0]) for r in cur.fetchall()}
    finally:
        cur.close()


def get_columns(conn, table_name: str, whitelist: set[str]) -> list[str]:
    cur = conn.cursor()
    try:
        cur.execute(f"SHOW COLUMNS FROM {safe_ident(table_name, whitelist)}")
        return [str(r[0]) for r in cur.fetchall()]
    finally:
        cur.close()


def find_sample_device(conn, table_name: str, whitelist: set[str], min_rows: int) -> dict[str, Any] | None:
    quoted = safe_ident(table_name, whitelist)
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"""
            SELECT
              device_id,
              COUNT(*) AS n_rows,
              MIN(timestamp) AS first_ts,
              MAX(timestamp) AS last_ts
            FROM {quoted}
            GROUP BY device_id
            HAVING n_rows >= %s
            ORDER BY n_rows DESC
            LIMIT 1
            """,
            (int(min_rows),),
        )
        return cur.fetchone()
    finally:
        cur.close()


def sample_rows(conn, table_name: str, whitelist: set[str], device_id: str, sample_limit: int) -> list[dict[str, Any]]:
    quoted = safe_ident(table_name, whitelist)
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"""
            SELECT *
            FROM {quoted}
            WHERE device_id = %s
            ORDER BY timestamp ASC
            LIMIT %s
            """,
            (device_id, int(sample_limit)),
        )
        return cur.fetchall()
    finally:
        cur.close()


def write_outputs(
    table_name: str,
    columns: list[str],
    sample_device: dict[str, Any],
    rows: list[dict[str, Any]],
    min_rows: int,
    sample_limit: int,
) -> list[Path]:
    out_dir = OUT_ROOT / table_name
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"{table_name}_sample_rows.csv"
    expanded_csv_path = out_dir / f"{table_name}_sample_rows_expanded.csv"
    jsonl_path = out_dir / f"{table_name}_sample_rows.jsonl"
    key_summary_path = out_dir / f"{table_name}_json_key_summary.csv"
    readme_path = out_dir / f"README_{table_name}_feature_review.md"

    sample_rows_out = []
    expanded_rows_out = []
    json_key_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for i, row in enumerate(rows, start=1):
        out = dict(row)
        out["sample_index"] = i
        out["local_datetime"] = to_local_datetime(row.get("timestamp"))
        sample_rows_out.append(out)

        obj = parse_json(row.get("data"))
        expanded = {
            "sample_index": i,
            "_id": row.get("_id"),
            "timestamp": row.get("timestamp"),
            "local_datetime": out["local_datetime"],
            "device_id": row.get("device_id"),
            "sample_context": "general_raw_sanity_sample_not_clinically_anchored",
        }
        if obj:
            for key, value in obj.items():
                json_key_counts[str(key)][value_type(value)] += 1
                expanded[str(key)] = sanitize_json_value(str(key), value)
        expanded_rows_out.append(expanded)

    pd.DataFrame(sample_rows_out).to_csv(csv_path, index=False)
    pd.DataFrame(expanded_rows_out).to_csv(expanded_csv_path, index=False)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in sample_rows_out:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    key_rows = []
    for key, counts in sorted(json_key_counts.items()):
        key_rows.append(
            {
                "json_key": key,
                "n_rows_with_key": sum(counts.values()),
                "value_type_counts": "; ".join(f"{k}:{v}" for k, v in sorted(counts.items())),
            }
        )
    pd.DataFrame(key_rows).to_csv(key_summary_path, index=False)

    readme_path.write_text(
        f"""# {table_name} Stage A Feature Review Sample

This folder contains a Stage A manual-review sample for `{table_name}`.

Stage A goal:

- Understand raw rows and JSON structure.
- Do not extract patient-level features.
- Do not make clinical conclusions.

Sample-device discovery query:

```sql
SELECT device_id, COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
FROM `{table_name}`
GROUP BY device_id
HAVING n_rows >= %s
ORDER BY n_rows DESC
LIMIT 1;
```

Sample query:

```sql
SELECT *
FROM `{table_name}`
WHERE device_id = %s
ORDER BY timestamp ASC
LIMIT %s;
```

Selected sample device:

- device_id: `{sample_device.get("device_id")}`
- rows available for device: `{sample_device.get("n_rows")}`
- first timestamp: `{sample_device.get("first_ts")}` / {to_local_datetime(sample_device.get("first_ts"))}
- last timestamp: `{sample_device.get("last_ts")}` / {to_local_datetime(sample_device.get("last_ts"))}

Requested minimum rows: {min_rows}
Rows sampled: {len(rows)}
Sample limit: {sample_limit}

Columns in table:

```text
{chr(10).join(columns)}
```

This is for manual feature review only. Missing data in later clinical windows must remain missing and must not be converted to zero.

The raw JSON is preserved in `{table_name}_sample_rows.csv`.
The expanded per-key inspection view is saved in `{table_name}_sample_rows_expanded.csv`.
""",
        encoding="utf-8",
    )

    return [csv_path, expanded_csv_path, jsonl_path, key_summary_path, readme_path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample rows from any one eligible device for Phase 2 table review.")
    parser.add_argument("--table", required=True)
    parser.add_argument("--min-rows", type=int, default=20)
    parser.add_argument("--sample-limit", type=int, default=20)
    args = parser.parse_args()

    conn = connect_sensordata_db()
    try:
        tables = get_tables(conn)
        table_name = args.table
        if table_name not in tables:
            raise SystemExit(f"Table not found: {table_name}")

        columns = get_columns(conn, table_name, tables)
        required = {"device_id", "timestamp"}
        missing = sorted(required - set(columns))
        if missing:
            raise SystemExit(f"Table {table_name} missing required columns for Stage A sample: {missing}")

        sample_device = find_sample_device(conn, table_name, tables, args.min_rows)
        if not sample_device:
            raise SystemExit(f"No device found with at least {args.min_rows} rows for {table_name}.")

        rows = sample_rows(conn, table_name, tables, str(sample_device["device_id"]), args.sample_limit)
        outputs = write_outputs(table_name, columns, sample_device, rows, args.min_rows, args.sample_limit)
    finally:
        conn.close()

    print(f"table: {args.table}")
    print(f"sample_device: {sample_device.get('device_id')}")
    print(f"rows_available_for_device: {sample_device.get('n_rows')}")
    print(f"rows_sampled: {len(rows)}")
    print("generated files:")
    for path in outputs:
        print(f"- {path}")


if __name__ == "__main__":
    main()
