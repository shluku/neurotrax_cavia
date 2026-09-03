"""Export one local-calendar day of raw general accelerometer data.

The raw SQL table is exported by timestamp range because its useful index is
timestamp-first. Each day is a separate compressed SQL dump, preserving every
device, including currently unmatched device IDs. The source database is
read-only from this script.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db, load_local_env


BACKUP_ROOT = Path("/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_accelerometer")
SQL_DIR = BACKUP_ROOT / "sql_zst"
LOG_DIR = BACKUP_ROOT / "logs"
MANIFEST_PATH = BACKUP_ROOT / "manifests" / "daily_export_manifest.jsonl"
TABLE = "accelerometer"
TIMEZONE = "Asia/Jerusalem"
MYSQLDUMP = Path("/opt/homebrew/opt/mysql-client/bin/mysqldump")
ZSTD = Path("/opt/homebrew/bin/zstd")


def local_to_ms(value: str) -> int:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(TIMEZONE)
    return int(timestamp.tz_convert("UTC").timestamp() * 1000)


def ms_to_local(value: Any) -> str:
    if value is None:
        return ""
    return str(pd.to_datetime(int(float(value)), unit="ms", utc=True).tz_convert(TIMEZONE))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_manifest(record: dict[str, Any]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def make_mysql_defaults_file() -> Path:
    load_local_env()
    values = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT", "3306"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }
    missing = [key for key in ("host", "user", "password") if not values[key]]
    if missing:
        raise RuntimeError(f"Missing database settings: {', '.join(missing)}")

    fd, name = tempfile.mkstemp(prefix="sensordata-mysql-", suffix=".cnf")
    path = Path(name)
    os.chmod(path, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("[client]\n")
        for key, value in values.items():
            handle.write(f"{key}={value}\n")
    return path


def bounded_summary(start_ms: int, end_ms: int) -> dict[str, Any]:
    connection = connect_sensordata_db()
    cursor = connection.cursor()
    try:
        cursor.execute("SET SESSION MAX_EXECUTION_TIME=300000")
        cursor.execute(
            f"""
            SELECT COUNT(*) AS n_rows,
                   COUNT(DISTINCT device_id) AS n_devices,
                   MIN(timestamp) AS first_timestamp_ms,
                   MAX(timestamp) AS last_timestamp_ms
            FROM `{TABLE}`
            WHERE timestamp >= %s AND timestamp < %s
            """,
            (start_ms, end_ms),
        )
        row = cursor.fetchone() or (0, 0, None, None)
        return {
            "row_count": int(row[0] or 0),
            "device_count": int(row[1] or 0),
            "first_timestamp_ms": row[2],
            "last_timestamp_ms": row[3],
            "first_timestamp_local": ms_to_local(row[2]),
            "last_timestamp_local": ms_to_local(row[3]),
        }
    finally:
        cursor.close()
        connection.close()


def dump_day(
    defaults_file: Path,
    start_ms: int,
    end_ms: int,
    output_path: Path,
    log_path: Path,
    data_only: bool,
) -> tuple[int, int, int]:
    where_clause = f"timestamp >= {start_ms} AND timestamp < {end_ms}"
    args = [
        str(MYSQLDUMP),
        f"--defaults-extra-file={defaults_file}",
        "--single-transaction",
        "--quick",
        "--skip-lock-tables",
        "--set-gtid-purged=OFF",
        "--hex-blob",
        "--no-tablespaces",
        "--default-character-set=utf8mb4",
        "--skip-masking-policies",
        "--skip-add-drop-masking-policy",
        "--ignore-table=sensordata.column_masking_policy",
    ]
    if data_only:
        args.extend(["--no-create-info", "--skip-add-drop-table"])
    args.extend([f"--where={where_clause}", "sensordata", TABLE])

    partial_path = output_path.with_suffix(output_path.suffix + ".partial")
    with log_path.open("ab") as log_handle, partial_path.open("wb") as output_handle:
        dump = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=log_handle)
        assert dump.stdout is not None
        compressor = subprocess.Popen(
            [str(ZSTD), "-T0", "-3", "-q", "-c"],
            stdin=dump.stdout,
            stdout=output_handle,
            stderr=log_handle,
        )
        dump.stdout.close()
        compressor_rc = compressor.wait()
        dump_rc = dump.wait()

    output_bytes = partial_path.stat().st_size if partial_path.exists() else 0
    if dump_rc == 0 and compressor_rc == 0 and output_bytes > 0:
        integrity_rc = subprocess.run([str(ZSTD), "-q", "-t", str(partial_path)], check=False).returncode
    else:
        integrity_rc = 1
    if dump_rc != 0 or compressor_rc != 0 or integrity_rc != 0:
        return dump_rc, compressor_rc, output_bytes
    partial_path.replace(output_path)
    return dump_rc, compressor_rc, output_path.stat().st_size


def run(start_local: str, end_local: str, data_only: bool) -> None:
    if not MYSQLDUMP.exists() or not ZSTD.exists():
        raise FileNotFoundError("Required mysqldump or zstd binary is missing")
    start = pd.Timestamp(start_local)
    end = pd.Timestamp(end_local)
    if start.tzinfo is None:
        start = start.tz_localize(TIMEZONE)
    if end.tzinfo is None:
        end = end.tz_localize(TIMEZONE)
    if end <= start:
        raise ValueError("end-local must be after start-local")
    if (end - start) > pd.Timedelta(days=1):
        raise ValueError("This pilot exports at most one local calendar day")

    start_ms = local_to_ms(str(start))
    end_ms = local_to_ms(str(end))
    day_label = start.strftime("%Y-%m-%d")
    end_label = end.strftime("%Y-%m-%d")
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SQL_DIR / f"{TABLE}_{day_label}_to_{end_label}.sql.zst"
    partial_path = output_path.with_suffix(output_path.suffix + ".partial")
    log_path = LOG_DIR / f"{TABLE}_{day_label}.mysqldump.log"

    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"skip_existing={output_path}", flush=True)
        return
    if partial_path.exists():
        raise RuntimeError(f"A partial export already exists; inspect before retrying: {partial_path}")

    summary = bounded_summary(start_ms, end_ms)
    print(f"window_start_local={start}", flush=True)
    print(f"window_end_local={end}", flush=True)
    print(f"expected_rows={summary['row_count']}", flush=True)
    print(f"expected_devices={summary['device_count']}", flush=True)
    print(f"expected_first_local={summary['first_timestamp_local']}", flush=True)
    print(f"expected_last_local={summary['last_timestamp_local']}", flush=True)
    if summary["row_count"] == 0:
        print("no_rows_in_window=true; no export created", flush=True)
        return

    defaults_file = make_mysql_defaults_file()
    started_at = now_iso()
    try:
        print(f"starting_export={output_path}", flush=True)
        dump_rc, compressor_rc, output_bytes = dump_day(
            defaults_file,
            start_ms,
            end_ms,
            output_path,
            log_path,
            data_only,
        )
    finally:
        defaults_file.unlink(missing_ok=True)

    status = "completed" if output_path.exists() and output_bytes > 0 and dump_rc == 0 and compressor_rc == 0 else "error"
    append_manifest(
        {
            "table_name": TABLE,
            "status": status,
            "started_at": started_at,
            "finished_at": now_iso(),
            "window_start_local": str(start),
            "window_end_local": str(end),
            "window_start_ms": start_ms,
            "window_end_ms": end_ms,
            "data_only": data_only,
            "expected_row_count": summary["row_count"],
            "expected_device_count": summary["device_count"],
            "expected_first_timestamp_local": summary["first_timestamp_local"],
            "expected_last_timestamp_local": summary["last_timestamp_local"],
            "mysqldump_returncode": dump_rc,
            "zstd_returncode": compressor_rc,
            "compressed_bytes": output_bytes,
            "output_path": str(output_path),
            "log_path": str(log_path),
        }
    )
    print(f"finished_status={status}", flush=True)
    print(f"compressed_bytes={output_bytes}", flush=True)
    if status != "completed":
        raise RuntimeError(f"Export failed; inspect {log_path} and any partial file")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-local", default="2025-01-05 00:00:00")
    parser.add_argument("--end-local", default="2025-01-06 00:00:00")
    parser.add_argument("--data-only", action="store_true", help="Omit CREATE/DROP statements for later chunks.")
    args = parser.parse_args()
    run(args.start_local, args.end_local, args.data_only)


if __name__ == "__main__":
    main()
