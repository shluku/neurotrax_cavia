"""Convert compressed MySQL logical-table backups to Parquet.

The source ``.sql.zst`` files are preserved. Conversion is table-by-table and
resumable; incomplete Parquet files remain hidden as ``.partial`` files until
the table has been written and reopened successfully.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pyarrow as pa
import pyarrow.parquet as pq


BACKUP_ROOT = Path("/Volumes/SENSORDATA_MAIN/sensordata_backup")
SOURCE_DIR = BACKUP_ROOT / "low_frequency_tables"
PARQUET_DIR = BACKUP_ROOT / "parquet"
MANIFEST_PATH = BACKUP_ROOT / "manifests" / "live_table_inventory.csv"
CHECKPOINT_PATH = BACKUP_ROOT / "manifests" / "parquet_conversion_checkpoint.jsonl"
ZSTD = Path("/opt/homebrew/bin/zstd")
BATCH_SIZE = 25_000

_COLUMN_RE = re.compile(r"^\s*`([^`]+)`\s+(.+?)(?:,)?\s*$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def included_tables() -> list[str]:
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("included_on_main_drive") == "yes"]
    return sorted(row["table_name"] for row in rows)


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


def mysql_type_to_arrow(definition: str) -> pa.DataType:
    kind = definition.strip().lower().split("(", 1)[0].split()[0]
    if kind in {"tinyint", "smallint", "mediumint", "int", "integer", "bigint", "year"}:
        return pa.int64()
    if kind in {"float", "double", "real", "decimal", "numeric"}:
        return pa.float64()
    if kind in {"binary", "varbinary", "blob", "tinyblob", "mediumblob", "longblob"}:
        return pa.binary()
    return pa.string()


def read_schema_and_data(stream) -> tuple[list[tuple[str, str]], Iterator[str]]:
    columns: list[tuple[str, str]] = []
    for line in stream:
        decoded = line.decode("utf-8") if isinstance(line, bytes) else line
        match = _COLUMN_RE.match(decoded.rstrip("\n"))
        if match and not decoded.lstrip().startswith(("PRIMARY ", "KEY ", "UNIQUE ", "CONSTRAINT ")):
            columns.append((match.group(1), match.group(2).rstrip(",")))
        if decoded.startswith("-- Dumping data for table"):
            break
    return columns, stream


def parse_sql_scalar(text: str):
    value = text.strip()
    if value.upper() == "NULL":
        return None
    if value.startswith("0x") or value.startswith("0X"):
        try:
            return bytes.fromhex(value[2:])
        except ValueError:
            return value
    return value


def parse_values(statement: str) -> Iterator[list[object]]:
    marker = statement.find(" VALUES ")
    if marker < 0:
        marker = statement.find(" VALUES")
    if marker < 0:
        return
    i = marker + statement[marker:].find("VALUES") + len("VALUES")
    n = len(statement)
    while i < n:
        while i < n and statement[i] in " \t\r\n,;":
            i += 1
        if i >= n or statement[i] != "(":
            return
        i += 1
        row: list[object] = []
        token: list[str] = []
        while i < n:
            char = statement[i]
            if char == "'":
                i += 1
                quoted: list[str] = []
                while i < n:
                    char = statement[i]
                    if char == "\\" and i + 1 < n:
                        escaped = statement[i + 1]
                        mapping = {"0": "\0", "b": "\b", "n": "\n", "r": "\r", "t": "\t", "Z": "\x1a"}
                        quoted.append(mapping.get(escaped, escaped))
                        i += 2
                        continue
                    if char == "'":
                        i += 1
                        break
                    quoted.append(char)
                    i += 1
                row.append("".join(quoted))
                token = []
                while i < n and statement[i] in " \t":
                    i += 1
                if i < n and statement[i] == ",":
                    i += 1
                    continue
                if i < n and statement[i] == ")":
                    i += 1
                    break
                continue

            if char == ",":
                row.append(parse_sql_scalar("".join(token)))
                token = []
                i += 1
                continue
            if char == ")":
                row.append(parse_sql_scalar("".join(token)))
                token = []
                i += 1
                break
            token.append(char)
            i += 1
        if row:
            yield row


def typed_value(value, arrow_type: pa.DataType):
    if value is None:
        return None
    if pa.types.is_integer(arrow_type):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    if pa.types.is_floating(arrow_type):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if pa.types.is_binary(arrow_type):
        return value if isinstance(value, bytes) else str(value).encode("utf-8")
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def rows_from_dump(source: Path, columns: list[tuple[str, str]]) -> Iterator[list[object]]:
    process = subprocess.Popen([str(ZSTD), "-dc", str(source)], stdout=subprocess.PIPE)
    assert process.stdout is not None
    try:
        _, data_stream = read_schema_and_data(process.stdout)
        for raw_line in data_stream:
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if "INSERT INTO" not in line or "VALUES" not in line:
                continue
            yield from parse_values(line)
    finally:
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"zstd failed for {source} with return code {return_code}")


def convert_table(table: str) -> tuple[int, int]:
    source = SOURCE_DIR / f"{table}.sql.zst"
    final_path = PARQUET_DIR / f"{table}.parquet"
    partial_path = PARQUET_DIR / f".{table}.parquet.partial"
    process = subprocess.Popen([str(ZSTD), "-dc", str(source)], stdout=subprocess.PIPE)
    assert process.stdout is not None
    try:
        columns, data_stream = read_schema_and_data(process.stdout)
        if not columns:
            raise RuntimeError(f"No CREATE TABLE columns found in {source}")
        names = [name for name, _ in columns]
        types = [mysql_type_to_arrow(definition) for _, definition in columns]
        schema = pa.schema(list(zip(names, types))).with_metadata(
            {
                b"source_backup": str(source).encode(),
                b"source_format": b"compressed_mysql_logical_dump",
                b"converted_at": now_iso().encode(),
            }
        )
        partial_path.unlink(missing_ok=True)
        writer = pq.ParquetWriter(partial_path, schema, compression="zstd")
        row_count = 0
        batch: list[list[object]] = []
        for raw_line in data_stream:
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if "INSERT INTO" not in line or "VALUES" not in line:
                continue
            for row in parse_values(line):
                if len(row) != len(columns):
                    raise RuntimeError(f"Column count mismatch in {table}: expected {len(columns)}, got {len(row)}")
                batch.append([typed_value(value, arrow_type) for value, arrow_type in zip(row, types)])
                if len(batch) >= BATCH_SIZE:
                    writer.write_table(pa.Table.from_pylist([dict(zip(names, r)) for r in batch], schema=schema))
                    row_count += len(batch)
                    batch.clear()
        if batch:
            writer.write_table(pa.Table.from_pylist([dict(zip(names, r)) for r in batch], schema=schema))
            row_count += len(batch)
        writer.close()
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"zstd failed for {source} with return code {return_code}")
        parquet_file = pq.ParquetFile(partial_path)
        if parquet_file.metadata.num_rows != row_count:
            raise RuntimeError(f"Parquet row-count check failed for {table}")
        partial_path.replace(final_path)
        return row_count, final_path.stat().st_size
    except Exception:
        process.kill()
        process.wait()
        partial_path.unlink(missing_ok=True)
        raise


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(MANIFEST_PATH)
    if not ZSTD.exists():
        raise FileNotFoundError(ZSTD)
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    tables = included_tables()
    completed = completed_tables()
    print(f"tables_total={len(tables)} tables_already_completed={len(completed)}", flush=True)
    for index, table in enumerate(tables, start=1):
        source = SOURCE_DIR / f"{table}.sql.zst"
        final_path = PARQUET_DIR / f"{table}.parquet"
        if table in completed and final_path.exists() and final_path.stat().st_size > 0:
            print(f"skip_completed={table} ({index}/{len(tables)})", flush=True)
            continue
        print(f"starting={table} ({index}/{len(tables)})", flush=True)
        started = now_iso()
        try:
            row_count, parquet_bytes = convert_table(table)
            append_checkpoint(
                {
                    "table_name": table,
                    "status": "completed",
                    "started_at": started,
                    "finished_at": now_iso(),
                    "row_count": row_count,
                    "parquet_bytes": parquet_bytes,
                }
            )
            print(f"finished={table} status=completed rows={row_count} parquet_bytes={parquet_bytes}", flush=True)
        except Exception as exc:
            append_checkpoint(
                {
                    "table_name": table,
                    "status": "error",
                    "started_at": started,
                    "finished_at": now_iso(),
                    "error": str(exc),
                }
            )
            raise


if __name__ == "__main__":
    main()
