from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


EPISODES_PATH = Path("output/analysis_candidates/top10_subject_device_episodes.csv")
OUT_DIR = Path("output/analysis_candidates/phase2_sql_fieldwork_samples")
SAMPLE_OUT = OUT_DIR / "sensordb_10_rows_per_table_sample.csv"
SUMMARY_OUT = OUT_DIR / "sensordb_10_rows_per_table_summary.csv"
README_OUT = OUT_DIR / "README_sensordb_10_rows_per_table_sample.md"

SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")
TZ = "Asia/Jerusalem"

HIGH_FREQUENCY_TABLES = {
    "accelerometer",
    "linear_accelerometer",
    "gyroscope",
    "rotation",
    "gravity",
    "magnetometer",
}

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


def normalize_subject_id_d(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    return s.zfill(3) if s.isdigit() else s


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
    if pd.isna(value) if not isinstance(value, (dict, list, tuple)) else False:
        return None
    return value


def sanitize_row(row_dict: dict[str, Any]) -> dict[str, Any]:
    return {str(k): sanitize_value(str(k), v) for k, v in row_dict.items()}


def to_local_datetime(timestamp_ms: Any) -> str:
    ts = pd.to_numeric(timestamp_ms, errors="coerce")
    if pd.isna(ts):
        return ""
    return pd.to_datetime(int(ts), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z")


def append_csv(path: Path, row: dict[str, Any], fieldnames: list[str]) -> None:
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fieldnames})


def load_episodes() -> pd.DataFrame:
    episodes = pd.read_csv(EPISODES_PATH, dtype=str)
    episodes = episodes[episodes["mapping_status"].astype(str).eq("ok")].copy()
    episodes["Subject_ID_D"] = episodes["Subject_ID_D"].map(normalize_subject_id_d)
    for col in ["early_window_start_ms", "early_window_end_ms", "late_window_start_ms", "late_window_end_ms"]:
        episodes[col] = pd.to_numeric(episodes[col], errors="coerce")
    return episodes.dropna(
        subset=["device_id", "early_window_start_ms", "early_window_end_ms", "late_window_start_ms", "late_window_end_ms"]
    )


def fetch_table_columns(conn, table_name: str, whitelist: set[str]) -> list[str]:
    cur = conn.cursor()
    try:
        cur.execute(f"SHOW COLUMNS FROM {safe_ident(table_name, whitelist)}")
        return [str(r[0]) for r in cur.fetchall()]
    finally:
        cur.close()


def sample_table_window(
    conn,
    table_name: str,
    whitelist: set[str],
    episodes: pd.DataFrame,
    window_name: str,
    remaining: int,
) -> tuple[list[dict[str, Any]], str]:
    start_col = f"{window_name}_window_start_ms"
    end_col = f"{window_name}_window_end_ms"
    out = []
    quoted = safe_ident(table_name, whitelist)

    for _, ep in episodes.iterrows():
        if len(out) >= remaining:
            break
        cur = conn.cursor()
        try:
            cur.execute(
                f"""
                SELECT /*+ MAX_EXECUTION_TIME(15000) */ *
                FROM {quoted}
                WHERE device_id = %s
                  AND timestamp >= %s
                  AND timestamp < %s
                ORDER BY timestamp ASC
                LIMIT 10
                """,
                (str(ep["device_id"]), int(ep[start_col]), int(ep[end_col])),
            )
            col_names = [d[0] for d in cur.description]
            rows = cur.fetchall()
            for raw_row in rows:
                if len(out) >= remaining:
                    break
                row_dict = dict(zip(col_names, raw_row))
                out.append(
                    {
                        "Subject_ID_D": ep["Subject_ID_D"],
                        "Subject_ID_N": ep["Subject_ID_N"],
                        "device_id": ep["device_id"],
                        "device_episode_index": ep["device_episode_index"],
                        "window_name": window_name,
                        "row": row_dict,
                    }
                )
        finally:
            cur.close()

    return out, ""


def write_readme(total_tables: int, eligible_tables: int) -> None:
    README_OUT.write_text(
        f"""# SensorDB 10 Rows Per Table Sample

This file contains up to 10 chronological sampled rows per eligible SensorDB table.

Eligibility:
- Tables must contain both `device_id` and `timestamp` columns.
- Tables were discovered using `SHOW TABLES`.
- Column eligibility was checked using `SHOW COLUMNS FROM table`.

Query safety:
- Queries were filtered by `device_id` and timestamp.
- Samples were taken only from the current top-10 subject/device early and late windows.
- The script preferred `early_window` and fell back to `late_window` only if no early rows were found for that table.
- Slow queries use a MySQL execution-time hint and failed/slow tables are recorded in the summary.
- No full-table `COUNT(*)` was run.
- No full T1-to-T2 windows were queried.
- At most 10 rows per table were saved.

Privacy:
- Obvious sensitive fields were redacted before writing the sample CSV.
- Redacted fields include text/message/body/phone/number/subscriber/IMEI/SIM/contact/email/address/name/SSID/BSSID fields.
- `application_name` is explicitly allowed.

Use:
- This output is for manual review only.
- It is not feature extraction.
- Missing data is not interpreted as zero activity.

Run summary:
- total tables found: {total_tables}
- eligible tables with device_id and timestamp: {eligible_tables}

Generated files:
- sensordb_10_rows_per_table_sample.csv
- sensordb_10_rows_per_table_summary.csv
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in [SAMPLE_OUT, SUMMARY_OUT]:
        if path.exists():
            path.unlink()

    sample_fields = [
        "database_name",
        "table_name",
        "timestamp_ms",
        "device_id",
        "json_data_sanitized",
        "error_message",
    ]
    summary_fields = [
        "table_name",
        "has_device_id",
        "has_timestamp",
        "sampled_rows",
        "sampled_from_window",
        "sampled_subjects",
        "status",
        "error_message",
    ]

    episodes = load_episodes()
    total_tables = 0
    eligible_tables = 0
    sampled_successfully = 0
    skipped = 0
    errors = 0
    total_rows_saved = 0

    conn = connect_sensordata_db()
    try:
        cur = conn.cursor()
        try:
            cur.execute("SELECT DATABASE()")
            database_name = str(cur.fetchone()[0])
            cur.execute("SHOW TABLES")
            table_names = sorted(str(r[0]) for r in cur.fetchall())
        finally:
            cur.close()
    finally:
        conn.close()

    table_names = sorted(table_names, key=lambda t: (t in HIGH_FREQUENCY_TABLES, t))
    whitelist = set(table_names)
    total_tables = len(table_names)

    for table_name in table_names:
        table_conn = None
        try:
            table_conn = connect_sensordata_db()
            columns = []
            error_message = ""
            sampled_rows: list[dict[str, Any]] = []
            sampled_from_window = ""
            status = "skipped"

            try:
                columns = fetch_table_columns(table_conn, table_name, whitelist)
                has_device_id = "device_id" in columns
                has_timestamp = "timestamp" in columns

                if not (has_device_id and has_timestamp):
                    skipped += 1
                    error_message = "missing device_id and/or timestamp"
                    append_csv(
                        SUMMARY_OUT,
                        {
                            "table_name": table_name,
                            "has_device_id": has_device_id,
                            "has_timestamp": has_timestamp,
                            "sampled_rows": 0,
                            "sampled_from_window": "",
                            "sampled_subjects": "",
                            "status": "skipped_missing_required_columns",
                            "error_message": error_message,
                        },
                        summary_fields,
                    )
                    continue

                eligible_tables += 1
                if table_name in HIGH_FREQUENCY_TABLES:
                    append_csv(
                        SUMMARY_OUT,
                        {
                            "table_name": table_name,
                            "has_device_id": has_device_id,
                            "has_timestamp": has_timestamp,
                            "sampled_rows": 0,
                            "sampled_from_window": "",
                            "sampled_subjects": "",
                            "status": "skipped_high_frequency_heavy_table",
                            "error_message": "known high-frequency/heavy raw sensor table; skipped for safe manual sampling",
                        },
                        summary_fields,
                    )
                    continue

                sampled_rows, _ = sample_table_window(table_conn, table_name, whitelist, episodes, "early", 10)
                if sampled_rows:
                    sampled_from_window = "early"
                else:
                    sampled_rows, _ = sample_table_window(table_conn, table_name, whitelist, episodes, "late", 10)
                    sampled_from_window = "late" if sampled_rows else ""

                if sampled_rows:
                    status = "sampled"
                    sampled_successfully += 1
                    for idx, sample in enumerate(sampled_rows, start=1):
                        row_dict = sample["row"]
                        sanitized = sanitize_row(row_dict)
                        timestamp_ms = row_dict.get("timestamp")
                        json_data = sanitized.get("data", sanitized)
                        append_csv(
                            SAMPLE_OUT,
                            {
                                "database_name": database_name,
                                "table_name": table_name,
                                "timestamp_ms": timestamp_ms,
                                "device_id": row_dict.get("device_id", sample["device_id"]),
                                "json_data_sanitized": json.dumps(json_data, ensure_ascii=False, default=str),
                                "error_message": "",
                            },
                            sample_fields,
                        )
                    total_rows_saved += len(sampled_rows)
                else:
                    status = "no_rows_in_top10_early_or_late_windows"

                append_csv(
                    SUMMARY_OUT,
                    {
                        "table_name": table_name,
                        "has_device_id": has_device_id,
                        "has_timestamp": has_timestamp,
                        "sampled_rows": len(sampled_rows),
                        "sampled_from_window": sampled_from_window,
                        "sampled_subjects": ";".join(sorted({s["Subject_ID_D"] for s in sampled_rows})),
                        "status": status,
                        "error_message": "",
                    },
                    summary_fields,
                )
            except Exception as exc:
                errors += 1
                error_message = str(exc)[:1000]
                append_csv(
                    SUMMARY_OUT,
                    {
                        "table_name": table_name,
                        "has_device_id": "device_id" in columns,
                        "has_timestamp": "timestamp" in columns,
                        "sampled_rows": len(sampled_rows),
                        "sampled_from_window": sampled_from_window,
                        "sampled_subjects": ";".join(sorted({s["Subject_ID_D"] for s in sampled_rows})),
                        "status": "error",
                        "error_message": error_message,
                    },
                    summary_fields,
                )
        finally:
            if table_conn is not None:
                try:
                    table_conn.close()
                except Exception:
                    pass

    if not SAMPLE_OUT.exists():
        with SAMPLE_OUT.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=sample_fields).writeheader()

    write_readme(total_tables, eligible_tables)

    print(f"total_tables_found={total_tables}")
    print(f"eligible_tables_with_device_id_and_timestamp={eligible_tables}")
    print(f"tables_sampled_successfully={sampled_successfully}")
    print(f"tables_skipped={skipped}")
    print(f"tables_with_errors={errors}")
    print(f"total_sampled_rows_saved={total_rows_saved}")
    print("output_file_paths:")
    print(f"- {SAMPLE_OUT}")
    print(f"- {SUMMARY_OUT}")
    print(f"- {README_OUT}")


if __name__ == "__main__":
    main()
