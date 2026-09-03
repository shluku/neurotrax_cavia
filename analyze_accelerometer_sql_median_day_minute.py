"""Inspect one SQL minute of the raw accelerometer streams and sensor metadata."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import mysql.connector
import pandas as pd

from main import connect_sensordata_db


ROOT = Path(__file__).parent
DEFAULT_OUT_DIR = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sql_median_day_minute"
TARGET_TZ = "Asia/Jerusalem"
RAW_SENSOR_PAIRS = (
    ("accelerometer", "sensor_accelerometer"),
    ("linear_accelerometer", "sensor_linear_accelerometer"),
)
FOCUS_SENSOR_KEYS = (
    "sensor_name",
    "sensor_type",
    "sensor_vendor",
    "sensor_version",
    "double_sensor_minimum_delay",
    "double_sensor_resolution",
    "double_sensor_maximum_range",
    "double_sensor_power_ma",
)


def ms_to_local(timestamp_ms: int, timezone: str) -> pd.Timestamp:
    return pd.to_datetime(int(timestamp_ms), unit="ms", utc=True).tz_convert(timezone)


def local_to_ms(value: pd.Timestamp) -> int:
    return int(value.tz_convert("UTC").value // 1_000_000)


def json_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value or "")


def parse_payload(value: Any) -> Tuple[Dict[str, Any], str]:
    raw = json_text(value)
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError) as exc:
        return {}, f"invalid_json:{exc}"
    if not isinstance(parsed, dict):
        return {}, f"json_type:{type(parsed).__name__}"
    return parsed, "ok"


def parse_calendar_date(value: str) -> date:
    text = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("Date must use YYYY-MM-DD, DD.MM.YY, or DD/MM/YYYY.")


def parse_clock_time(value: str) -> time:
    text = (value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    raise ValueError("Time must use HH:MM or HH:MM:SS.")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def first_last_timestamp(cur: Any, table_name: str) -> Tuple[int | None, int | None]:
    cur.execute(
        f"SELECT timestamp FROM `{table_name}` "
        "WHERE timestamp IS NOT NULL ORDER BY timestamp ASC LIMIT 1"
    )
    first = cur.fetchone()
    cur.execute(
        f"SELECT timestamp FROM `{table_name}` "
        "WHERE timestamp IS NOT NULL ORDER BY timestamp DESC LIMIT 1"
    )
    last = cur.fetchone()
    first_ms = int(float(first[0])) if first and first[0] is not None else None
    last_ms = int(float(last[0])) if last and last[0] is not None else None
    return first_ms, last_ms


def raw_window_stats(cur: Any, table_name: str, start_ms: int, end_ms: int) -> Dict[str, Any]:
    cur.execute(
        f"""
        SELECT COUNT(*), COUNT(DISTINCT device_id), MIN(timestamp), MAX(timestamp)
        FROM `{table_name}`
        WHERE timestamp >= %s AND timestamp < %s
        """,
        (start_ms, end_ms),
    )
    row = cur.fetchone() or (0, 0, None, None)
    return {
        "row_count": int(row[0] or 0),
        "distinct_device_count": int(row[1] or 0),
        "window_first_timestamp_ms": int(float(row[2])) if row[2] is not None else "",
        "window_last_timestamp_ms": int(float(row[3])) if row[3] is not None else "",
    }


def raw_window_samples(
    cur: Any,
    table_name: str,
    start_ms: int,
    end_ms: int,
    timezone: str,
    limit: int,
) -> List[Dict[str, Any]]:
    cur.execute(
        f"""
        SELECT _id, timestamp, device_id, data
        FROM `{table_name}`
        WHERE timestamp >= %s AND timestamp < %s
        ORDER BY timestamp ASC, device_id ASC, _id ASC
        LIMIT %s
        """,
        (start_ms, end_ms, limit),
    )
    rows: List[Dict[str, Any]] = []
    for index, row in enumerate(cur.fetchall(), start=1):
        timestamp_ms = int(float(row[1]))
        raw_data = json_text(row[3])
        payload, parse_status = parse_payload(raw_data)
        rows.append(
            {
                "table_name": table_name,
                "sample_order": index,
                "_id": row[0],
                "timestamp_ms": timestamp_ms,
                "timestamp_local": str(ms_to_local(timestamp_ms, timezone)),
                "device_id": row[2],
                "data_json": raw_data,
                "data_json_pretty": json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
                if payload
                else raw_data,
                "data_json_parse_status": parse_status,
                "data_json_keys": ";".join(sorted(payload)),
                "data_json_key_count": len(payload),
            }
        )
    return rows


def raw_window_device_ids(cur: Any, table_name: str, start_ms: int, end_ms: int) -> set[str]:
    cur.execute(
        f"""
        SELECT DISTINCT device_id
        FROM `{table_name}`
        WHERE timestamp >= %s AND timestamp < %s
          AND device_id IS NOT NULL
        ORDER BY device_id ASC
        """,
        (start_ms, end_ms),
    )
    return {str(row[0]) for row in cur.fetchall() if row and row[0] is not None}


def sensor_rows(cur: Any, table_name: str) -> List[Tuple[Any, Any, Any, Any]]:
    cur.execute(
        f"""
        SELECT _id, timestamp, device_id, data
        FROM `{table_name}`
        ORDER BY timestamp ASC, _id ASC
        """
    )
    return list(cur.fetchall())


def numeric_value(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def sensor_outputs(
    cur: Any,
    raw_table: str,
    sensor_table: str,
    window_device_ids: set[str],
    timezone: str,
    sample_limit: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows = sensor_rows(cur, sensor_table)
    parsed_rows = []
    parse_errors = 0
    key_values: Dict[str, List[Any]] = defaultdict(list)
    for row in rows:
        timestamp_ms = int(float(row[1])) if row[1] is not None else None
        payload, parse_status = parse_payload(row[3])
        if parse_status != "ok":
            parse_errors += 1
        for key, value in payload.items():
            if value not in (None, ""):
                key_values[key].append(value)
        parsed_rows.append(
            {
                "raw_table": raw_table,
                "sensor_table": sensor_table,
                "_id": row[0],
                "timestamp_ms": timestamp_ms if timestamp_ms is not None else "",
                "timestamp_local": str(ms_to_local(timestamp_ms, timezone)) if timestamp_ms is not None else "",
                "device_id": row[2],
                "data_json": json_text(row[3]),
                "data_json_pretty": json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
                if payload
                else json_text(row[3]),
                "data_json_parse_status": parse_status,
                "data_json_keys": ";".join(sorted(payload)),
            }
        )

    matching = [row for row in parsed_rows if str(row["device_id"]) in window_device_ids]
    chosen: List[Dict[str, Any]] = []
    seen_ids = set()
    for selection, candidates in (
        ("matching_window_device", matching),
        ("first_global_rows", parsed_rows),
    ):
        for row in candidates:
            key = (row["sensor_table"], row["_id"])
            if key in seen_ids or len(chosen) >= sample_limit * 2:
                continue
            copy = dict(row)
            copy["selection"] = selection
            chosen.append(copy)
            seen_ids.add(key)
            if selection == "matching_window_device" and len(
                [item for item in chosen if item["selection"] == selection]
            ) >= sample_limit:
                break
        if len(chosen) >= sample_limit * 2:
            break

    key_summary = []
    for key in sorted(key_values):
        values = key_values[key]
        numeric = [number for value in values if (number := numeric_value(value)) is not None]
        key_summary.append(
            {
                "raw_table": raw_table,
                "sensor_table": sensor_table,
                "key": key,
                "nonempty_rows": len(values),
                "example_values": " | ".join(str(value) for value in values[:5]),
                "numeric_min": min(numeric) if numeric else "",
                "numeric_median": float(pd.Series(numeric).median()) if numeric else "",
                "numeric_max": max(numeric) if numeric else "",
                "priority": "sampling_or_hardware_context" if key in FOCUS_SENSOR_KEYS else "other_metadata",
            }
        )

    summary = {
        "raw_table": raw_table,
        "sensor_table": sensor_table,
        "metadata_row_count": len(rows),
        "metadata_distinct_device_count": len({str(row["device_id"]) for row in parsed_rows}),
        "window_device_count": len(window_device_ids),
        "window_device_metadata_row_count": len(matching),
        "metadata_parse_error_count": parse_errors,
        "metadata_first_timestamp_ms": parsed_rows[0]["timestamp_ms"] if parsed_rows else "",
        "metadata_last_timestamp_ms": parsed_rows[-1]["timestamp_ms"] if parsed_rows else "",
        "sampling_or_hardware_keys_present": ";".join(
            key for key in FOCUS_SENSOR_KEYS if key in key_values
        ),
    }
    return summary, chosen, key_summary


def build_readme(
    out_dir: Path,
    timezone: str,
    experiment_start_ms: int,
    experiment_end_ms: int,
    median_day: date,
    inspection_day: date,
    inspection_time: time,
    table_summary: List[Dict[str, Any]],
    sensor_summary: List[Dict[str, Any]],
) -> None:
    start_local = ms_to_local(experiment_start_ms, timezone)
    end_local = ms_to_local(experiment_end_ms, timezone)
    lines = [
        "# Raw Accelerometer SQL Median-Day Minute Reconnaissance",
        "",
        "This is a read-only structural and sampling reconnaissance of the SQL source. It is not patient-level feature extraction.",
        "",
        "## Protocol",
        "",
        f"- Source: MySQL `sensordata` database; raw tables `{RAW_SENSOR_PAIRS[0][0]}` and `{RAW_SENSOR_PAIRS[1][0]}`.",
        f"- Timestamp interpretation: Unix milliseconds, displayed in `{timezone}`.",
        f"- Experiment span used: `{start_local}` through `{end_local}` across the two raw tables.",
        f"- Reference median day: `{median_day.isoformat()}`; this is the lower midpoint day between the earliest and latest local calendar dates.",
        f"- Inspection day: `{inspection_day.isoformat()}`; this is the reference median day unless a date was explicitly requested.",
        f"- Inspection window: `{inspection_day.isoformat()} {inspection_time.strftime('%H:%M:%S')}` to one minute later local time, with an end-exclusive SQL boundary.",
        "- Row ordering: timestamp ascending, then device ID ascending, then row ID ascending.",
        "- The sensor tables are hardware and collection-context references only. Their metadata must not be interpreted as movement behavior.",
        "",
        "## Raw window results",
        "",
        "| raw table | rows | distinct devices | first local row | last local row |",
        "|---|---:|---:|---|---|",
    ]
    for row in table_summary:
        first = (
            str(ms_to_local(int(row["window_first_timestamp_ms"]), timezone))
            if row["window_first_timestamp_ms"] != ""
            else "none"
        )
        last = (
            str(ms_to_local(int(row["window_last_timestamp_ms"]), timezone))
            if row["window_last_timestamp_ms"] != ""
            else "none"
        )
        lines.append(
            f"| `{row['table_name']}` | {row['row_count']:,} | {row['distinct_device_count']:,} | {first} | {last} |"
        )
    lines += [
        "",
        "## Sensor metadata interpretation",
        "",
        "The paired `sensor_*` tables can contain `double_sensor_minimum_delay`, resolution, maximum range, power, vendor, and sensor identity. Minimum delay can describe a hardware/request capability and does not prove that the raw stream was sampled continuously at that rate.",
        "",
        "Outputs:",
        "",
        "- `median_day_minute_summary.csv`: global span and exact one-minute raw-table counts.",
        "- `median_day_minute_raw_samples.csv`: representative raw JSON rows from each target table.",
        "- `median_day_minute_sensor_summary.csv`: paired sensor-table availability and matching-device counts.",
        "- `median_day_minute_sensor_samples.csv`: representative sensor metadata JSON rows.",
        "- `median_day_minute_sensor_key_summary.csv`: observed metadata keys and numeric summaries.",
        "",
        "The analysis does not alter the SQL database or the Parquet backups.",
    ]
    (out_dir / "README_raw_accelerometer_sql_median_day_minute.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = connect_sensordata_db()
    cur = conn.cursor()
    try:
        try:
            cur.execute("SET SESSION MAX_EXECUTION_TIME=300000")
        except mysql.connector.Error:
            pass

        bounds = {}
        for raw_table, _ in RAW_SENSOR_PAIRS:
            first_ms, last_ms = first_last_timestamp(cur, raw_table)
            if first_ms is None or last_ms is None:
                raise RuntimeError(f"No timestamped rows found in {raw_table}.")
            bounds[raw_table] = (first_ms, last_ms)

        experiment_start_ms = min(first for first, _ in bounds.values())
        experiment_end_ms = max(last for _, last in bounds.values())
        start_day = ms_to_local(experiment_start_ms, args.timezone).date()
        end_day = ms_to_local(experiment_end_ms, args.timezone).date()
        median_day = start_day + timedelta(days=(end_day - start_day).days // 2)
        inspection_day = args.requested_date or median_day
        inspection_time = args.requested_time or time(9, 0)
        window_start_local = pd.Timestamp(datetime.combine(inspection_day, inspection_time)).tz_localize(args.timezone)
        window_end_local = window_start_local + pd.Timedelta(minutes=1)
        window_start_ms = local_to_ms(window_start_local)
        window_end_ms = local_to_ms(window_end_local)

        table_summary = []
        raw_samples = []
        window_devices: Dict[str, set[str]] = {}
        for raw_table, _ in RAW_SENSOR_PAIRS:
            stats = raw_window_stats(cur, raw_table, window_start_ms, window_end_ms)
            samples = raw_window_samples(
                cur,
                raw_table,
                window_start_ms,
                window_end_ms,
                args.timezone,
                args.sample_limit,
            )
            window_devices[raw_table] = raw_window_device_ids(
                cur,
                raw_table,
                window_start_ms,
                window_end_ms,
            )
            stats.update(
                {
                    "table_name": raw_table,
                    "experiment_first_timestamp_ms": bounds[raw_table][0],
                    "experiment_last_timestamp_ms": bounds[raw_table][1],
                }
            )
            table_summary.append(stats)
            raw_samples.extend(samples)

        sensor_summary = []
        sensor_samples = []
        sensor_key_summary = []
        for raw_table, sensor_table in RAW_SENSOR_PAIRS:
            summary, samples, keys = sensor_outputs(
                cur,
                raw_table,
                sensor_table,
                window_devices[raw_table],
                args.timezone,
                args.sample_limit,
            )
            sensor_summary.append(summary)
            sensor_samples.extend(samples)
            sensor_key_summary.extend(keys)
    finally:
        cur.close()
        conn.close()

    common = {
        "experiment_start_local": str(ms_to_local(experiment_start_ms, args.timezone)),
        "experiment_end_local": str(ms_to_local(experiment_end_ms, args.timezone)),
        "median_day_local": median_day.isoformat(),
        "inspection_day_local": inspection_day.isoformat(),
        "inspection_time_local": inspection_time.strftime("%H:%M:%S"),
        "window_start_local": str(window_start_local),
        "window_end_local": str(window_end_local),
        "window_start_ms_utc": window_start_ms,
        "window_end_ms_utc": window_end_ms,
        "timezone": args.timezone,
        "source": "SQL database",
    }
    write_csv(
        out_dir / "median_day_minute_summary.csv",
        [{**common, **row} for row in table_summary],
        [*common.keys(), "table_name", "row_count", "distinct_device_count", "window_first_timestamp_ms", "window_last_timestamp_ms", "experiment_first_timestamp_ms", "experiment_last_timestamp_ms"],
    )
    write_csv(
        out_dir / "median_day_minute_raw_samples.csv",
        [{**common, **row} for row in raw_samples],
        [*common.keys(), "table_name", "sample_order", "_id", "timestamp_ms", "timestamp_local", "device_id", "data_json", "data_json_pretty", "data_json_parse_status", "data_json_keys", "data_json_key_count"],
    )
    write_csv(
        out_dir / "median_day_minute_sensor_summary.csv",
        [{**common, **row} for row in sensor_summary],
        [*common.keys(), "raw_table", "sensor_table", "metadata_row_count", "metadata_distinct_device_count", "window_device_count", "window_device_metadata_row_count", "metadata_parse_error_count", "metadata_first_timestamp_ms", "metadata_last_timestamp_ms", "sampling_or_hardware_keys_present"],
    )
    write_csv(
        out_dir / "median_day_minute_sensor_samples.csv",
        [{**common, **row} for row in sensor_samples],
        [*common.keys(), "raw_table", "sensor_table", "_id", "timestamp_ms", "timestamp_local", "device_id", "data_json", "data_json_pretty", "data_json_parse_status", "data_json_keys", "selection"],
    )
    write_csv(
        out_dir / "median_day_minute_sensor_key_summary.csv",
        [{**common, **row} for row in sensor_key_summary],
        [*common.keys(), "raw_table", "sensor_table", "key", "nonempty_rows", "example_values", "numeric_min", "numeric_median", "numeric_max", "priority"],
    )
    build_readme(
        out_dir,
        args.timezone,
        experiment_start_ms,
        experiment_end_ms,
        median_day,
        inspection_day,
        inspection_time,
        table_summary,
        sensor_summary,
    )
    print(f"output_dir={out_dir}")
    print(f"experiment_start_local={common['experiment_start_local']}")
    print(f"experiment_end_local={common['experiment_end_local']}")
    print(f"median_day_local={median_day.isoformat()}")
    print(f"inspection_day_local={inspection_day.isoformat()}")
    print(f"inspection_time_local={inspection_time.strftime('%H:%M:%S')}")
    print(f"window_local={window_start_local} to {window_end_local}")
    for row in table_summary:
        print(
            f"{row['table_name']}: rows={row['row_count']} "
            f"distinct_devices={row['distinct_device_count']} samples={len([x for x in raw_samples if x['table_name'] == row['table_name']])}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--date", help="Inspection date; YYYY-MM-DD, DD.MM.YY, or DD/MM/YYYY.")
    parser.add_argument("--time", dest="clock_time", help="Inspection local time; HH:MM or HH:MM:SS. Default: 09:00.")
    parser.add_argument("--timezone", default=TARGET_TZ)
    parser.add_argument("--sample-limit", type=int, default=20)
    args = parser.parse_args()
    if args.sample_limit < 1:
        raise ValueError("--sample-limit must be positive")
    args.requested_date = parse_calendar_date(args.date) if args.date else None
    args.requested_time = parse_clock_time(args.clock_time) if args.clock_time else None
    if args.out_dir is None:
        if args.requested_date:
            suffix = args.requested_date.isoformat()
            if args.requested_time and args.requested_time != time(9, 0):
                suffix += "_" + args.requested_time.strftime("%H-%M")
            args.out_dir = DEFAULT_OUT_DIR / suffix
        else:
            args.out_dir = DEFAULT_OUT_DIR
    run(args)


if __name__ == "__main__":
    main()
