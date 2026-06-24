from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


EPISODES_PATH = Path("output/analysis_candidates/top10_subject_device_episodes.csv")
OUT_ROOT = Path("output/analysis_candidates/phase2_feature_review")
SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")
TZ = "Asia/Jerusalem"


def normalize_subject_id_d(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    return s.zfill(3) if s.isdigit() else s


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


def to_local_datetime(timestamp_ms: Any) -> str:
    ts = pd.to_numeric(timestamp_ms, errors="coerce")
    if pd.isna(ts):
        return ""
    return pd.to_datetime(int(ts), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z")


def load_episodes() -> pd.DataFrame:
    episodes = pd.read_csv(EPISODES_PATH, dtype=str)
    episodes = episodes[episodes["mapping_status"].astype(str).eq("ok")].copy()
    episodes["Subject_ID_D"] = episodes["Subject_ID_D"].map(normalize_subject_id_d)
    for col in ["early_window_start_ms", "early_window_end_ms", "late_window_start_ms", "late_window_end_ms"]:
        episodes[col] = pd.to_numeric(episodes[col], errors="coerce")
    return episodes.dropna(
        subset=["device_id", "early_window_start_ms", "early_window_end_ms", "late_window_start_ms", "late_window_end_ms"]
    )


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


def find_review_window(conn, table_name: str, whitelist: set[str], episodes: pd.DataFrame, min_rows: int):
    quoted = safe_ident(table_name, whitelist)
    cur = conn.cursor(dictionary=True)
    try:
        for _, ep in episodes.iterrows():
            for window_name, start_col, end_col in [
                ("early", "early_window_start_ms", "early_window_end_ms"),
                ("late", "late_window_start_ms", "late_window_end_ms"),
            ]:
                cur.execute(
                    f"""
                    SELECT
                      COUNT(*) AS n_rows,
                      MIN(timestamp) AS first_ts,
                      MAX(timestamp) AS last_ts
                    FROM {quoted}
                    WHERE device_id = %s
                      AND timestamp >= %s
                      AND timestamp < %s
                    """,
                    (str(ep["device_id"]), int(ep[start_col]), int(ep[end_col])),
                )
                row = cur.fetchone() or {}
                n_rows = int(row.get("n_rows") or 0)
                if n_rows >= min_rows:
                    return {
                        "Subject_ID_N": ep["Subject_ID_N"],
                        "Subject_ID_D": ep["Subject_ID_D"],
                        "device_id": ep["device_id"],
                        "device_episode_index": ep["device_episode_index"],
                        "window_name": window_name,
                        "window_start_ms": int(ep[start_col]),
                        "window_end_ms": int(ep[end_col]),
                        "n_rows_in_window": n_rows,
                        "first_ts": row.get("first_ts"),
                        "last_ts": row.get("last_ts"),
                    }
    finally:
        cur.close()
    return None


def sample_rows(conn, table_name: str, whitelist: set[str], review_window: dict[str, Any], sample_limit: int):
    quoted = safe_ident(table_name, whitelist)
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"""
            SELECT *
            FROM {quoted}
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT %s
            """,
            (
                str(review_window["device_id"]),
                int(review_window["window_start_ms"]),
                int(review_window["window_end_ms"]),
                int(sample_limit),
            ),
        )
        return cur.fetchall()
    finally:
        cur.close()


def write_outputs(table_name: str, columns: list[str], review_window: dict[str, Any], rows: list[dict[str, Any]]) -> list[Path]:
    out_dir = OUT_ROOT / table_name
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"{table_name}_sample_rows.csv"
    jsonl_path = out_dir / f"{table_name}_sample_rows.jsonl"
    key_summary_path = out_dir / f"{table_name}_json_key_summary.csv"
    readme_path = out_dir / f"README_{table_name}_feature_review.md"

    sample_rows = []
    json_key_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for i, row in enumerate(rows, start=1):
        out = dict(row)
        out["sample_index"] = i
        out["local_datetime"] = to_local_datetime(row.get("timestamp"))
        sample_rows.append(out)

        obj = parse_json(row.get("data"))
        if obj:
            for key, value in obj.items():
                json_key_counts[str(key)][value_type(value)] += 1

    pd.DataFrame(sample_rows).to_csv(csv_path, index=False)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in sample_rows:
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
        f"""# {table_name} Feature Review Sample

This folder contains a bounded manual-review sample for `{table_name}`.

SQL method:

```sql
SELECT *
FROM `{table_name}`
WHERE device_id = %s
  AND timestamp >= %s
  AND timestamp < %s
ORDER BY timestamp ASC
LIMIT %s;
```

Selected review window:

- Subject_ID_D: {review_window['Subject_ID_D']}
- Subject_ID_N: {review_window['Subject_ID_N']}
- device_id: {review_window['device_id']}
- device_episode_index: {review_window['device_episode_index']}
- window_name: {review_window['window_name']}
- window_start_ms: {review_window['window_start_ms']}
- window_end_ms: {review_window['window_end_ms']}
- n_rows_in_window: {review_window['n_rows_in_window']}

Files:

- `{csv_path.name}`
- `{jsonl_path.name}`
- `{key_summary_path.name}`

This is manual fieldwork only. It is not feature extraction.
""",
        encoding="utf-8",
    )
    return [csv_path, jsonl_path, key_summary_path, readme_path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample one SensorDB table for Phase 2 feature-review fieldwork.")
    parser.add_argument("--table", default="applications_foreground")
    parser.add_argument("--min-rows", type=int, default=20)
    parser.add_argument("--sample-limit", type=int, default=20)
    args = parser.parse_args()

    episodes = load_episodes()
    conn = connect_sensordata_db()
    try:
        whitelist = get_tables(conn)
        table_name = args.table
        columns = get_columns(conn, table_name, whitelist)
        required = {"device_id", "timestamp"}
        missing = sorted(required - set(columns))
        if missing:
            raise SystemExit(f"Table {table_name} missing required columns: {missing}")

        review_window = find_review_window(conn, table_name, whitelist, episodes, args.min_rows)
        if not review_window:
            raise SystemExit(f"No top-10 early/late window found with at least {args.min_rows} rows for {table_name}.")

        rows = sample_rows(conn, table_name, whitelist, review_window, args.sample_limit)
        files = write_outputs(table_name, columns, review_window, rows)

        print(f"table={table_name}")
        print(f"selected_subject={review_window['Subject_ID_D']}")
        print(f"selected_device_id={review_window['device_id']}")
        print(f"selected_window={review_window['window_name']}")
        print(f"n_rows_in_window={review_window['n_rows_in_window']}")
        print(f"sampled_rows={len(rows)}")
        print("generated_files:")
        for path in files:
            print(f"- {path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
