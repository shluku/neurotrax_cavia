from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


COGNITIVE_PATH = Path("output/analysis_candidates/cognitive_candidates_all.csv")
LABEL_DEVICE_MAP_PATH = Path("output/label_device_map.csv")
OUT_ROOT = Path("output/analysis_candidates/phase2_feature_review")
SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")
TZ = "Asia/Jerusalem"
WINDOW_HOURS = 36


def normalize_subject_id_d(value: Any) -> str:
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


def load_highest_t1_patient() -> dict[str, Any]:
    cognitive = pd.read_csv(COGNITIVE_PATH, dtype=str)
    cognitive["Subject_ID_D"] = cognitive["Subject_ID_D"].map(normalize_subject_id_d)
    cognitive["global_T1_numeric"] = pd.to_numeric(cognitive["global_T1"], errors="coerce")
    cognitive = cognitive.dropna(subset=["global_T1_numeric", "T1_date_iso", "Subject_ID_D"]).copy()
    cognitive = cognitive.sort_values(["global_T1_numeric", "Subject_ID_D"], ascending=[False, True])
    if cognitive.empty:
        raise ValueError("No usable highest-T1 patient found.")

    patient = cognitive.iloc[0].to_dict()
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    label_map["Subject_ID_D"] = label_map["label"].map(normalize_subject_id_d)
    match = label_map[label_map["Subject_ID_D"] == patient["Subject_ID_D"]]
    if match.empty:
        raise ValueError(f"No device mapping found for Subject_ID_D={patient['Subject_ID_D']}.")

    raw_device_ids = str(match.iloc[0].get("device_ids", "") or "")
    device_ids = [x.strip() for x in raw_device_ids.split(";") if x.strip() and x.strip().lower() != "nan"]
    if not device_ids:
        raise ValueError(f"No device IDs found for Subject_ID_D={patient['Subject_ID_D']}.")

    patient["device_ids"] = device_ids
    return patient


def primary_window_ms(t1_date_iso: str) -> tuple[int, int, str, str]:
    t1 = pd.Timestamp(t1_date_iso).tz_localize(TZ)
    start = (t1 + pd.Timedelta(days=1)).normalize()
    end = start + pd.Timedelta(hours=WINDOW_HOURS)
    return (
        int(start.tz_convert("UTC").timestamp() * 1000),
        int(end.tz_convert("UTC").timestamp() * 1000),
        start.strftime("%Y-%m-%d %H:%M:%S%z"),
        end.strftime("%Y-%m-%d %H:%M:%S%z"),
    )


def coverage(conn, quoted_table: str, device_id: str, start_ms: int, end_ms: int) -> dict[str, Any]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"""
            SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM {quoted_table}
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        return cur.fetchone() or {"n_rows": 0, "first_ts": None, "last_ts": None}
    finally:
        cur.close()


def first_observed_for_device(conn, quoted_table: str, device_id: str) -> Any:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"""
            SELECT MIN(timestamp) AS first_ts
            FROM {quoted_table}
            WHERE device_id = %s
            """,
            (device_id,),
        )
        row = cur.fetchone() or {}
        return row.get("first_ts")
    finally:
        cur.close()


def select_review_window(conn, quoted_table: str, device_ids: list[str], start_ms: int, end_ms: int) -> dict[str, Any] | None:
    primary_rows = []
    for device_id in device_ids:
        row = coverage(conn, quoted_table, device_id, start_ms, end_ms)
        row["device_id"] = device_id
        primary_rows.append(row)
    primary_rows = sorted(primary_rows, key=lambda x: int(x.get("n_rows") or 0), reverse=True)
    if primary_rows and int(primary_rows[0].get("n_rows") or 0) > 0:
        return {
            "window_status": "primary_day_after_t1",
            "device_id": primary_rows[0]["device_id"],
            "window_start_ms": start_ms,
            "window_end_ms": end_ms,
            "n_rows_in_window": int(primary_rows[0].get("n_rows") or 0),
            "first_ts": primary_rows[0].get("first_ts"),
            "last_ts": primary_rows[0].get("last_ts"),
        }

    fallback_candidates = []
    for device_id in device_ids:
        first_ts = first_observed_for_device(conn, quoted_table, device_id)
        if first_ts is not None:
            fallback_candidates.append({"device_id": device_id, "first_ts": int(first_ts)})
    if not fallback_candidates:
        return None

    chosen = sorted(fallback_candidates, key=lambda x: x["first_ts"])[0]
    fallback_start = chosen["first_ts"]
    fallback_end = fallback_start + WINDOW_HOURS * 60 * 60 * 1000
    row = coverage(conn, quoted_table, chosen["device_id"], fallback_start, fallback_end)
    return {
        "window_status": "fallback_first_observed_patient_table_data",
        "device_id": chosen["device_id"],
        "window_start_ms": fallback_start,
        "window_end_ms": fallback_end,
        "n_rows_in_window": int(row.get("n_rows") or 0),
        "first_ts": row.get("first_ts"),
        "last_ts": row.get("last_ts"),
    }


def sample_rows(conn, quoted_table: str, window: dict[str, Any], sample_limit: int) -> list[dict[str, Any]]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"""
            SELECT *
            FROM {quoted_table}
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT %s
            """,
            (
                window["device_id"],
                int(window["window_start_ms"]),
                int(window["window_end_ms"]),
                int(sample_limit),
            ),
        )
        return cur.fetchall()
    finally:
        cur.close()


def write_outputs(
    table_name: str,
    columns: list[str],
    patient: dict[str, Any],
    window: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    primary_start_local: str,
    primary_end_local: str,
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
        out["phase_a_subject_id_d"] = patient.get("Subject_ID_D")
        out["phase_a_subject_id_n"] = patient.get("Subject_ID_N")
        out["window_status"] = window.get("window_status") if window else "unavailable"
        sample_rows_out.append(out)

        obj = parse_json(row.get("data"))
        expanded = {
            "sample_index": i,
            "_id": row.get("_id"),
            "timestamp": row.get("timestamp"),
            "local_datetime": out["local_datetime"],
            "device_id": row.get("device_id"),
            "phase_a_subject_id_d": patient.get("Subject_ID_D"),
            "phase_a_subject_id_n": patient.get("Subject_ID_N"),
            "window_status": window.get("window_status") if window else "unavailable",
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
        f"""# {table_name} Highest-T1 Phase A Feature Review Sample

This folder contains the Phase A manual-review sample for `{table_name}`.

Phase A patient:

- Subject_ID_D: `{patient.get("Subject_ID_D")}`
- Subject_ID_N: `{patient.get("Subject_ID_N")}`
- global_T1: `{patient.get("global_T1")}`
- T1_date_iso: `{patient.get("T1_date_iso")}`
- mapped device IDs: `{';'.join(patient.get("device_ids", []))}`

Primary window:

- local start: {primary_start_local}
- local end: {primary_end_local}
- rule: day after T1, 36 continuous hours

Selected sample window:

- status: `{window.get("window_status") if window else "unavailable"}`
- device_id: `{window.get("device_id") if window else ""}`
- window_start_ms: `{window.get("window_start_ms") if window else ""}` / {to_local_datetime(window.get("window_start_ms") if window else None)}
- window_end_ms: `{window.get("window_end_ms") if window else ""}` / {to_local_datetime(window.get("window_end_ms") if window else None)}
- rows in selected window: `{window.get("n_rows_in_window") if window else 0}`
- rows sampled: {len(rows)}
- sample limit: {sample_limit}

Columns in table:

```text
{chr(10).join(columns)}
```

This is for manual table understanding only. It is not feature extraction and not a clinical conclusion.

If the selected window status is fallback, the sample is not true day-after-T1 behavior; it is the first observed 36-hour window for that table across the patient's mapped devices.
""",
        encoding="utf-8",
    )

    return [csv_path, expanded_csv_path, jsonl_path, key_summary_path, readme_path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase A highest-T1 table sample for feature review.")
    parser.add_argument("--table", required=True)
    parser.add_argument("--sample-limit", type=int, default=20)
    args = parser.parse_args()

    patient = load_highest_t1_patient()
    start_ms, end_ms, start_local, end_local = primary_window_ms(str(patient["T1_date_iso"]))

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
            raise SystemExit(f"Table {table_name} missing required columns for Phase A sample: {missing}")

        quoted = safe_ident(table_name, tables)
        window = select_review_window(conn, quoted, patient["device_ids"], start_ms, end_ms)
        rows = sample_rows(conn, quoted, window, args.sample_limit) if window else []
        outputs = write_outputs(table_name, columns, patient, window, rows, start_local, end_local, args.sample_limit)
    finally:
        conn.close()

    print(f"table: {args.table}")
    print(f"phase_a_subject_id_d: {patient.get('Subject_ID_D')}")
    print(f"phase_a_global_T1: {patient.get('global_T1')}")
    print(f"window_status: {window.get('window_status') if window else 'unavailable'}")
    print(f"sample_device: {window.get('device_id') if window else ''}")
    print(f"rows_in_selected_window: {window.get('n_rows_in_window') if window else 0}")
    print(f"rows_sampled: {len(rows)}")
    print("generated files:")
    for path in outputs:
        print(f"- {path}")


if __name__ == "__main__":
    main()
