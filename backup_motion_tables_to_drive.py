"""Resumable full raw motion backups as independently verified SQL/Zstandard chunks.

Copies every device and preserves duplicate source rows and JSON fields. Frozen
primary-key bounds define each table's scope. Each chunk has its own transaction;
this is not a database-wide point-in-time snapshot if existing rows are edited.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from backup_accelerometer_by_day import MYSQLDUMP, ZSTD, make_mysql_defaults_file
from main import connect_sensordata_db

TABLES = ("accelerometer", "rotation", "gyroscope", "gravity")
DEFAULT_ROOT = Path("/Volumes/SENSORDATA_MAIN/sensordata_backup/full_raw_motion")


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, record):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, indent=2) + "\n")
    tmp.replace(path)


def metadata(table):
    conn = connect_sensordata_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SET SESSION MAX_EXECUTION_TIME=30000")
        cur.execute(f"SHOW INDEX FROM `{table}`")
        primary = [r for r in cur.fetchall() if r["Key_name"] == "PRIMARY"]
        if len(primary) != 1 or primary[0]["Column_name"] != "_id":
            raise ValueError(f"Expected a single-column _id primary key: {table}")
        cur.execute(f"SELECT MIN(_id) AS min_id, MAX(_id) AS max_id FROM `{table}`")
        bounds = cur.fetchone()
        cur.execute("SELECT TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s", (table,))
        result = {**bounds, **cur.fetchone(), "table": table, "captured_at": now()}
        cur.close()
        return result
    finally:
        conn.close()


def dump_chunk(table, lower, upper, destination, defaults, log):
    if destination.exists():
        raise FileExistsError(f"Untracked completed file requires review: {destination}")
    partial = destination.with_suffix(destination.suffix + ".partial")
    if partial.exists():
        # Preserve incomplete attempts for review rather than silently deleting them.
        partial.rename(partial.with_name(partial.name + f".interrupted-{time.time_ns()}"))
    args = [str(MYSQLDUMP), f"--defaults-extra-file={defaults}",
            "--single-transaction", "--quick", "--skip-lock-tables",
            "--set-gtid-purged=OFF", "--hex-blob", "--no-tablespaces",
            "--default-character-set=utf8mb4", "--skip-masking-policies",
            "--skip-add-drop-masking-policy", "--ignore-table=sensordata.column_masking_policy",
            f"--where=_id >= {lower} AND _id < {upper}", "sensordata", table]
    dump = compressor = None
    try:
        with log.open("ab") as errors, partial.open("xb") as target:
            dump = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=errors)
            compressor = subprocess.Popen([str(ZSTD), "-T2", "-3", "-q", "-c"],
                                          stdin=dump.stdout, stdout=target, stderr=errors)
            dump.stdout.close()
            dump_rc = dump.wait()
            zstd_rc = compressor.wait()
        if dump_rc or zstd_rc or not partial.stat().st_size:
            raise RuntimeError(f"Chunk failed: mysqldump={dump_rc}, zstd={zstd_rc}; see {log}")
        subprocess.run([str(ZSTD), "-q", "-t", str(partial)], check=True)
        result = {"compressed_bytes": partial.stat().st_size, "sha256": sha256(partial)}
        partial.replace(destination)
        return result
    finally:
        for process in (dump, compressor):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def run(args):
    root = args.output_root.resolve()
    if not Path("/Volumes/SENSORDATA_MAIN").is_mount():
        raise RuntimeError("SENSORDATA_MAIN must be mounted; refusing to write to an unmounted path")
    root.mkdir(parents=True, exist_ok=True)
    lock = (root / "backup.lock").open("a")
    if args.wait_for_lock:
        print("waiting_for_current_backup_lock", flush=True)
    fcntl.flock(lock, fcntl.LOCK_EX | (0 if args.wait_for_lock else fcntl.LOCK_NB))
    plan_path = root / "backup_plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        if plan["tables"] != args.tables or plan["chunk_id_span"] != args.chunk_id_span:
            raise ValueError("Resume requires the same table order and chunk span as backup_plan.json")
    else:
        plan = {"created_at": now(), "tables": args.tables, "chunk_id_span": args.chunk_id_span,
                "format": "sql.zst; schema included in each chunk; all source rows preserved",
                "scope": "all devices; fixed per-table ID high-water mark; per-chunk transactions",
                "metadata": {table: metadata(table) for table in args.tables}}
        write_json(plan_path, plan)
    manifest = root / "completed_chunks.jsonl"
    completed = {}
    if manifest.exists():
        for line in manifest.read_text().splitlines():
            record = json.loads(line)
            completed[record["relative_path"]] = record
    defaults = make_mysql_defaults_file()
    processed = 0
    try:
        for table in args.tables:
            info = plan["metadata"][table]
            folder = root / table
            folder.mkdir(exist_ok=True)
            if info["min_id"] is None:
                raise RuntimeError(f"Empty table {table}; schema-only handling requires review")
            for lower in range(int(info["min_id"]), int(info["max_id"]) + 1, args.chunk_id_span):
                upper = min(lower + args.chunk_id_span, int(info["max_id"]) + 1)
                path = folder / f"{table}_id_{lower}_to_{upper}_exclusive.sql.zst"
                relative = str(path.relative_to(root))
                if relative in completed:
                    record = completed[relative]
                    if not path.exists() or path.stat().st_size != record["compressed_bytes"]:
                        raise RuntimeError(f"Completed archive missing or size changed: {path}")
                    continue
                free = shutil.disk_usage(root).free
                if free < args.min_free_gb * 10**9:
                    raise RuntimeError(f"Free space below {args.min_free_gb} GB reserve; backup paused")
                started = now()
                print(f"chunk_start table={table} lower={lower} upper_exclusive={upper} at={started}", flush=True)
                write_json(root / "status.json", {"status": "running", "table": table,
                           "lower_id": lower, "upper_id_exclusive": upper, "started_at": started,
                           "completed_chunks": len(completed)})
                tick = time.monotonic()
                result = dump_chunk(table, lower, upper, path, defaults, folder / "mysqldump.log")
                record = {"table": table, "lower_id": lower, "upper_id_exclusive": upper,
                          "relative_path": relative, "started_at": started, "finished_at": now(),
                          "elapsed_seconds": time.monotonic() - tick, **result}
                with manifest.open("a") as stream:
                    stream.write(json.dumps(record) + "\n")
                    stream.flush()
                completed[relative] = record
                processed += 1
                print("chunk_complete " + json.dumps(record), flush=True)
                if args.max_chunks and processed >= args.max_chunks:
                    write_json(root / "status.json", {"status": "paused_after_requested_chunks", "updated_at": now(), "completed_chunks": len(completed)})
                    return
        write_json(root / "status.json", {"status": "complete", "updated_at": now(), "completed_chunks": len(completed)})
        print("all_tables_complete", flush=True)
    except BaseException as exc:
        write_json(root / "status.json", {"status": "interrupted_or_error", "updated_at": now(),
                   "error_type": type(exc).__name__, "completed_chunks": len(completed)})
        raise
    finally:
        defaults.unlink(missing_ok=True)
        lock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", nargs="+", choices=TABLES, default=list(TABLES))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--chunk-id-span", type=int, default=5_000_000)
    parser.add_argument("--max-chunks", type=int, default=0, help="Stop after this many new chunks; zero means all")
    parser.add_argument("--min-free-gb", type=float, default=100)
    parser.add_argument("--wait-for-lock", action="store_true", help="Queue behind an active pilot, then resume sequentially")
    args = parser.parse_args()
    if args.chunk_id_span < 1 or args.max_chunks < 0 or args.min_free_gb < 100:
        parser.error("Require a positive chunk span, nonnegative max-chunks, and at least 100 GB reserve")
    run(args)
