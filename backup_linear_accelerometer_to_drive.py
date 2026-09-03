"""Resumable raw linear_accelerometer backup to the external drive.

The SQL database remains the source of truth. This creates a compressed SQL
logical dump on the first external drive and preserves it for later Parquet
conversion. It intentionally handles the restricted MySQL masking-policy
metadata separately from the requested sensor table.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from backup_low_frequency_tables import load_local_env


BACKUP_ROOT = Path("/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_linear_accelerometer")
TABLE = "linear_accelerometer"
SQL_DIR = BACKUP_ROOT / "sql_zst"
CHECKPOINT_PATH = BACKUP_ROOT / "manifests" / "sql_backup_checkpoint.jsonl"
LOG_DIR = BACKUP_ROOT / "logs"
MYSQLDUMP = Path("/opt/homebrew/opt/mysql-client/bin/mysqldump")
ZSTD = Path("/opt/homebrew/bin/zstd")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_checkpoint(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def completed_successfully(path: Path) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("table_name") == TABLE and record.get("status") == "completed":
            return True
    return False


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


def dump_linear_accelerometer(defaults_file: Path) -> tuple[int, int]:
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    final_path = SQL_DIR / f"{TABLE}.sql.zst"
    partial_path = SQL_DIR / f".{TABLE}.sql.zst.partial"
    dump_log = LOG_DIR / f"{TABLE}.mysqldump.log"
    zstd_log = LOG_DIR / f"{TABLE}.zstd.log"
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
        "sensordata",
        TABLE,
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

    output_size = partial_path.stat().st_size if partial_path.exists() else 0
    integrity_rc = 1
    if dump_rc == 0 and compressor_rc == 0 and output_size > 0:
        integrity_rc = subprocess.run([str(ZSTD), "-q", "-t", str(partial_path)], check=False).returncode
    if dump_rc != 0 or compressor_rc != 0 or integrity_rc != 0:
        partial_path.unlink(missing_ok=True)
        return dump_rc, compressor_rc
    partial_path.replace(final_path)
    return dump_rc, compressor_rc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Retry even when a completed checkpoint exists.")
    args = parser.parse_args()
    if not MYSQLDUMP.exists() or not ZSTD.exists():
        raise FileNotFoundError("Required mysqldump or zstd binary is missing")
    final_path = SQL_DIR / f"{TABLE}.sql.zst"
    if not args.force and completed_successfully(CHECKPOINT_PATH) and final_path.exists() and final_path.stat().st_size > 0:
        print(f"skip_completed={TABLE} path={final_path}", flush=True)
        return

    defaults_file = make_mysql_defaults_file()
    started = now_iso()
    try:
        print(f"starting={TABLE} destination={final_path}", flush=True)
        dump_rc, compressor_rc = dump_linear_accelerometer(defaults_file)
        status = "completed" if dump_rc == 0 and compressor_rc == 0 and final_path.exists() else "error"
        append_checkpoint(
            CHECKPOINT_PATH,
            {
                "table_name": TABLE,
                "status": status,
                "started_at": started,
                "finished_at": now_iso(),
                "mysqldump_returncode": dump_rc,
                "zstd_returncode": compressor_rc,
                "compressed_bytes": final_path.stat().st_size if final_path.exists() else 0,
                "masking_policy_handling": "skip-masking-policies, skip-add-drop-masking-policy, ignore column_masking_policy",
            },
        )
        print(f"finished={TABLE} status={status} compressed_bytes={final_path.stat().st_size if final_path.exists() else 0}", flush=True)
        if status != "completed":
            raise RuntimeError(f"Backup failed for {TABLE}; see {LOG_DIR}")
    finally:
        defaults_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
