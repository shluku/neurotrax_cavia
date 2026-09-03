"""Create a resumable compressed logical backup of the non-motion SensorDB tables.

The table manifest is generated from the live database before this runner is
started. Each table is dumped independently so an interrupted transfer can be
resumed without replacing completed files.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from main import load_local_env


BACKUP_ROOT = Path("/Volumes/SENSORDATA_MAIN/sensordata_backup")
MANIFEST_PATH = BACKUP_ROOT / "manifests" / "live_table_inventory.csv"
CHECKPOINT_PATH = BACKUP_ROOT / "manifests" / "low_frequency_backup_checkpoint.jsonl"
TABLE_OUTPUT_DIR = BACKUP_ROOT / "low_frequency_tables"
LOG_DIR = BACKUP_ROOT / "manifests" / "logs"
MYSQLDUMP = Path("/opt/homebrew/opt/mysql-client/bin/mysqldump")
ZSTD = Path("/opt/homebrew/bin/zstd")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_manifest() -> list[dict[str, str]]:
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows = [row for row in rows if row.get("included_on_main_drive") == "yes"]
    return sorted(rows, key=lambda row: int(row.get("total_bytes", "0")))


def completed_tables() -> set[str]:
    completed: set[str] = set()
    if not CHECKPOINT_PATH.exists():
        return completed
    with CHECKPOINT_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("status") == "completed":
                completed.add(str(record.get("table_name")))
    return completed


def append_checkpoint(record: dict[str, object]) -> None:
    with CHECKPOINT_PATH.open("a", encoding="utf-8") as handle:
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


def dump_table(table: str, defaults_file: Path) -> tuple[int, int, int]:
    final_path = TABLE_OUTPUT_DIR / f"{table}.sql.zst"
    partial_path = TABLE_OUTPUT_DIR / f".{table}.sql.zst.partial"
    dump_log = LOG_DIR / f"{table}.mysqldump.log"
    zstd_log = LOG_DIR / f"{table}.zstd.log"

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
        "sensordata",
        table,
    ]

    partial_path.unlink(missing_ok=True)
    with dump_log.open("ab") as dump_stderr, zstd_log.open("ab") as zstd_stderr:
        with partial_path.open("wb") as output:
            dump = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=dump_stderr)
            assert dump.stdout is not None
            compressor = subprocess.Popen(
                [str(ZSTD), "-T0", "-3", "-q", "-c"],
                stdin=dump.stdout,
                stdout=output,
                stderr=zstd_stderr,
            )
            dump.stdout.close()
            compressor_rc = compressor.wait()
            dump_rc = dump.wait()

    if dump_rc != 0 or compressor_rc != 0 or partial_path.stat().st_size == 0:
        partial_path.unlink(missing_ok=True)
        return dump_rc, compressor_rc, 0

    test = subprocess.run([str(ZSTD), "-q", "-t", str(partial_path)], check=False)
    if test.returncode != 0:
        partial_path.unlink(missing_ok=True)
        return dump_rc, compressor_rc, 0

    partial_path.replace(final_path)
    return dump_rc, compressor_rc, final_path.stat().st_size


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(MANIFEST_PATH)
    if not MYSQLDUMP.exists() or not ZSTD.exists():
        raise FileNotFoundError("Required mysqldump or zstd binary is missing")

    TABLE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_manifest()
    done = completed_tables()
    defaults_file = make_mysql_defaults_file()
    try:
        print(f"tables_total={len(rows)} tables_already_completed={len(done)}", flush=True)
        for index, row in enumerate(rows, start=1):
            table = row["table_name"]
            final_path = TABLE_OUTPUT_DIR / f"{table}.sql.zst"
            if table in done and final_path.exists() and final_path.stat().st_size > 0:
                print(f"skip_completed={table} ({index}/{len(rows)})", flush=True)
                continue

            expected_gb = float(row.get("total_gb_decimal", "0") or 0)
            print(f"starting={table} ({index}/{len(rows)}) expected_db_size_gb={expected_gb}", flush=True)
            started = now_iso()
            dump_rc, compressor_rc, output_bytes = dump_table(table, defaults_file)
            status = "completed" if output_bytes else "error"
            append_checkpoint(
                {
                    "table_name": table,
                    "status": status,
                    "started_at": started,
                    "finished_at": now_iso(),
                    "mysqldump_returncode": dump_rc,
                    "zstd_returncode": compressor_rc,
                    "compressed_bytes": output_bytes,
                }
            )
            print(
                f"finished={table} status={status} compressed_bytes={output_bytes}",
                flush=True,
            )
            if status != "completed":
                raise RuntimeError(f"Backup failed for table {table}; see {LOG_DIR}")
    finally:
        defaults_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
