"""Build device-level accelerometer hardware timelines from local Parquet copies."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import pandas as pd
import duckdb
import pyarrow.parquet as pq


ROOT = Path(__file__).parent
PARQUET_ROOT = Path("/Volumes/SENSORDATA_MAIN/sensordata_backup/parquet")
DEFAULT_OUT_DIR = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/device_hardware_timeline"
TIMEZONE = "Asia/Jerusalem"
SENSOR_TABLES = {
    "sensor_accelerometer": PARQUET_ROOT / "sensor_accelerometer.parquet",
    "sensor_linear_accelerometer": PARQUET_ROOT / "sensor_linear_accelerometer.parquet",
}
RAW_LINEAR_PATH = Path(
    "/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_linear_accelerometer/parquet/linear_accelerometer.parquet"
)
SENSOR_FIELDS = [
    "sensor_name",
    "sensor_vendor",
    "sensor_type",
    "sensor_version",
    "double_sensor_minimum_delay",
    "double_sensor_resolution",
    "double_sensor_maximum_range",
    "double_sensor_power_ma",
]
NUMERIC_SENSOR_FIELDS = [
    "double_sensor_minimum_delay",
    "double_sensor_resolution",
    "double_sensor_maximum_range",
    "double_sensor_power_ma",
]


def json_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value or "")


def parse_payload(value: Any) -> Dict[str, Any]:
    try:
        payload = json.loads(json_text(value))
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def format_values(values: Iterable[Any]) -> str:
    cleaned = []
    for value in values:
        if pd.isna(value) or value == "":
            continue
        if isinstance(value, float):
            if not math.isfinite(value):
                continue
            cleaned.append(f"{value:.8g}")
        else:
            cleaned.append(str(value))
    return ";".join(sorted(set(cleaned)))


def numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna()


def summarize_series(series: pd.Series) -> Tuple[Any, Any, Any, str]:
    numeric = numeric_series(series)
    if numeric.empty:
        return "", "", "", ""
    return (
        float(numeric.min()),
        float(numeric.median()),
        float(numeric.max()),
        format_values(numeric.tolist()),
    )


def read_sensor_table(path: Path, table_name: str) -> Tuple[pd.DataFrame, int]:
    table = pq.read_table(path, columns=["_id", "timestamp", "device_id", "data"])
    frame = table.to_pandas()
    raw_data = frame["data"].tolist()
    payloads = [parse_payload(value) for value in raw_data]
    payload_frame = pd.json_normalize(payloads)
    payload_frame = payload_frame.drop(columns=[column for column in payload_frame.columns if column in frame.columns], errors="ignore")
    frame = pd.concat([frame.drop(columns=["data"]).reset_index(drop=True), payload_frame], axis=1)
    frame["table_name"] = table_name
    frame["timestamp_local"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True).dt.tz_convert(TIMEZONE)
    frame["month"] = frame["timestamp_local"].dt.strftime("%Y-%m")
    for field in NUMERIC_SENSOR_FIELDS:
        if field in frame:
            frame[field] = pd.to_numeric(frame[field], errors="coerce")
    for field in SENSOR_FIELDS:
        if field not in frame:
            frame[field] = pd.NA
    parse_errors = sum(1 for raw, payload in zip(raw_data, payloads) if not payload)
    return frame, parse_errors


def unique_join(series: pd.Series) -> str:
    return format_values(series.dropna().astype(str).tolist())


def sensor_device_summary(frame: pd.DataFrame, table_name: str) -> pd.DataFrame:
    rows = []
    for device_id, group in frame.groupby("device_id", dropna=False):
        if pd.isna(device_id):
            continue
        summary: Dict[str, Any] = {
            "device_id": str(device_id),
            "source_table": table_name,
            "metadata_rows": len(group),
            "metadata_first_seen_local": str(group["timestamp_local"].min()),
            "metadata_last_seen_local": str(group["timestamp_local"].max()),
            "metadata_active_months": ";".join(sorted(group["month"].dropna().unique().tolist())),
            "sensor_names": unique_join(group["sensor_name"]),
            "sensor_vendors": unique_join(group["sensor_vendor"]),
            "sensor_types": unique_join(group["sensor_type"]),
            "sensor_versions": unique_join(group["sensor_version"]),
        }
        for field in NUMERIC_SENSOR_FIELDS:
            minimum, median, maximum, values = summarize_series(group[field])
            prefix = field.removeprefix("double_")
            summary[f"{prefix}_min"] = minimum
            summary[f"{prefix}_median"] = median
            summary[f"{prefix}_max"] = maximum
            summary[f"{prefix}_values"] = values
        rows.append(summary)
    return pd.DataFrame(rows)


def sensor_configuration_summary(frame: pd.DataFrame, table_name: str) -> pd.DataFrame:
    work = frame.copy()
    work["sensor_name_normalized"] = work["sensor_name"].astype(str).str.strip().str.lower()
    work["sensor_vendor_normalized"] = work["sensor_vendor"].astype(str).str.strip().str.lower()
    config_fields = [
        "sensor_name_normalized",
        "sensor_vendor_normalized",
        "sensor_type",
        "sensor_version",
        *NUMERIC_SENSOR_FIELDS,
    ]
    rows = []
    for config, group in work.groupby(config_fields, dropna=False):
        values = dict(zip(config_fields, config))
        rows.append(
            {
                "source_table": table_name,
                "sensor_name": format_values(group["sensor_name"]),
                "sensor_vendor": format_values(group["sensor_vendor"]),
                "sensor_type": values["sensor_type"],
                "sensor_version": values["sensor_version"],
                "minimum_delay_us": values["double_sensor_minimum_delay"],
                "resolution": values["double_sensor_resolution"],
                "maximum_range": values["double_sensor_maximum_range"],
                "power_ma": values["double_sensor_power_ma"],
                "metadata_rows": len(group),
                "device_count": group["device_id"].nunique(),
                "first_seen_local": str(group["timestamp_local"].min()),
                "last_seen_local": str(group["timestamp_local"].max()),
                "active_months": ";".join(sorted(group["month"].dropna().unique().tolist())),
            }
        )
    return pd.DataFrame(rows).sort_values(["source_table", "device_count", "metadata_rows"], ascending=[True, False, False])


def sensor_monthly_summary(frame: pd.DataFrame, table_name: str) -> pd.DataFrame:
    rows = (
        frame.groupby("month", dropna=False)
        .agg(
            metadata_rows=("_id", "size"),
            unique_device_count=("device_id", "nunique"),
            unique_sensor_name_count=("sensor_name", "nunique"),
            unique_vendor_count=("sensor_vendor", "nunique"),
        )
        .reset_index()
    )
    rows.insert(0, "source_table", table_name)
    return rows


def scan_raw_linear(path: Path, threads: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate raw linear-ACC by device and local month in one columnar scan."""
    print("raw_linear_scan_start", flush=True)
    con = duckdb.connect()
    try:
        con.execute(f"PRAGMA threads={int(threads)}")
        con.execute("SET preserve_insertion_order=false")
        monthly_device = con.execute(
            """
            WITH source AS (
                SELECT
                    CAST(device_id AS VARCHAR) AS device_id,
                    CAST(timestamp AS DOUBLE) AS timestamp,
                    strftime(
                        timezone('Asia/Jerusalem', to_timestamp(CAST(timestamp AS DOUBLE) / 1000.0)),
                        '%Y-%m'
                    ) AS month
                FROM read_parquet(?)
                WHERE device_id IS NOT NULL AND timestamp IS NOT NULL
            )
            SELECT
                device_id,
                month,
                COUNT(*)::BIGINT AS raw_rows,
                MIN(timestamp)::DOUBLE AS first_timestamp_ms,
                MAX(timestamp)::DOUBLE AS last_timestamp_ms
            FROM source
            GROUP BY device_id, month
            ORDER BY device_id, month
            """,
            [str(path)],
        ).fetchdf()
    finally:
        con.close()

    if monthly_device.empty:
        return pd.DataFrame(), pd.DataFrame()

    monthly_device["device_id"] = monthly_device["device_id"].astype(str)
    monthly_device["raw_rows"] = pd.to_numeric(monthly_device["raw_rows"], errors="coerce").fillna(0).astype("int64")
    monthly_device["first_timestamp_ms"] = pd.to_numeric(monthly_device["first_timestamp_ms"], errors="coerce")
    monthly_device["last_timestamp_ms"] = pd.to_numeric(monthly_device["last_timestamp_ms"], errors="coerce")
    device_rows = (
        monthly_device.groupby("device_id", as_index=False)
        .agg(
            raw_linear_accelerometer_rows=("raw_rows", "sum"),
            raw_linear_first_timestamp_ms=("first_timestamp_ms", "min"),
            raw_linear_last_timestamp_ms=("last_timestamp_ms", "max"),
        )
    )
    device_rows["raw_linear_accelerometer_rows"] = device_rows["raw_linear_accelerometer_rows"].astype("int64")
    device_rows["raw_linear_first_seen_local"] = pd.to_datetime(
        device_rows["raw_linear_first_timestamp_ms"], unit="ms", utc=True
    ).dt.tz_convert(TIMEZONE).astype(str)
    device_rows["raw_linear_last_seen_local"] = pd.to_datetime(
        device_rows["raw_linear_last_timestamp_ms"], unit="ms", utc=True
    ).dt.tz_convert(TIMEZONE).astype(str)
    first = pd.to_datetime(device_rows["raw_linear_first_timestamp_ms"], unit="ms", utc=True)
    last = pd.to_datetime(device_rows["raw_linear_last_timestamp_ms"], unit="ms", utc=True)
    device_rows["raw_linear_active_span_days"] = (last - first).dt.total_seconds() / 86400

    monthly_rows = (
        monthly_device.groupby("month", as_index=False)
        .agg(raw_rows=("raw_rows", "sum"), unique_device_count=("device_id", "nunique"))
        .sort_values("month")
    )
    monthly_rows.insert(0, "source_table", "linear_accelerometer")
    print(
        f"raw_linear_scan_complete rows={int(device_rows['raw_linear_accelerometer_rows'].sum()):,} "
        f"devices={len(device_rows)} months={len(monthly_rows)}",
        flush=True,
    )
    return device_rows, monthly_rows


def add_raw_linear_timestamps(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["raw_linear_accelerometer_rows"] = frame["raw_linear_accelerometer_rows"].fillna(0).astype("int64")
    frame["raw_linear_accelerometer_available"] = frame["raw_linear_accelerometer_rows"] > 0
    return frame


def build_outputs(args: argparse.Namespace) -> None:
    if not all(path.exists() for path in SENSOR_TABLES.values()):
        missing = [str(path) for path in SENSOR_TABLES.values() if not path.exists()]
        raise FileNotFoundError(f"Missing sensor Parquet files: {missing}")
    if not RAW_LINEAR_PATH.exists():
        raise FileNotFoundError(f"Missing raw linear accelerometer Parquet: {RAW_LINEAR_PATH}")

    sensor_frames = {}
    sensor_device_frames = []
    sensor_configuration_frames = []
    sensor_monthly_frames = []
    parse_errors = {}
    for table_name, path in SENSOR_TABLES.items():
        frame, errors = read_sensor_table(path, table_name)
        sensor_frames[table_name] = frame
        parse_errors[table_name] = errors
        sensor_device_frames.append(sensor_device_summary(frame, table_name))
        sensor_configuration_frames.append(sensor_configuration_summary(frame, table_name))
        sensor_monthly_frames.append(sensor_monthly_summary(frame, table_name))

    sensor_devices = pd.concat(sensor_device_frames, ignore_index=True)
    sensor_devices["device_id"] = sensor_devices["device_id"].astype(str)
    sensor_devices.to_csv(args.out_dir / "sensor_device_summary_long.csv", index=False)
    configurations = pd.concat(sensor_configuration_frames, ignore_index=True)
    configurations.to_csv(args.out_dir / "sensor_configuration_summary.csv", index=False)
    sensor_monthly = pd.concat(sensor_monthly_frames, ignore_index=True)

    raw_linear_devices, raw_linear_monthly = scan_raw_linear(RAW_LINEAR_PATH, args.threads)
    raw_linear_devices = add_raw_linear_timestamps(raw_linear_devices)
    raw_linear_devices.to_csv(args.out_dir / "raw_linear_device_summary.csv", index=False)

    combined = sensor_devices.pivot(index="device_id", columns="source_table")
    combined.columns = [f"{column}_{source}" for column, source in combined.columns]
    combined = combined.reset_index()
    combined = combined.merge(raw_linear_devices, on="device_id", how="outer")
    combined["device_id"] = combined["device_id"].astype(str)
    for column in combined.columns:
        if column.endswith("_metadata_rows") or column.endswith("_raw_linear_accelerometer_rows"):
            combined[column] = pd.to_numeric(combined[column], errors="coerce").fillna(0).astype("int64")
    combined["raw_accelerometer_rows"] = pd.NA
    combined["raw_accelerometer_count_status"] = "not_available_locally_raw_accelerometer_parquet_not_created"
    combined["raw_linear_accelerometer_source"] = str(RAW_LINEAR_PATH)
    combined.to_csv(args.out_dir / "accelerometer_device_hardware_timeline.csv", index=False)

    sensor_monthly["raw_rows"] = pd.NA
    sensor_monthly["source_kind"] = "sensor_metadata"
    raw_linear_monthly["metadata_rows"] = pd.NA
    raw_linear_monthly["unique_sensor_name_count"] = pd.NA
    raw_linear_monthly["unique_vendor_count"] = pd.NA
    raw_linear_monthly["source_kind"] = "raw_stream"
    monthly = pd.concat([sensor_monthly, raw_linear_monthly], ignore_index=True, sort=False)
    monthly.to_csv(args.out_dir / "device_hardware_monthly_prevalence.csv", index=False)

    summary = pd.DataFrame(
        [
            {"metric": "unique_device_ids_any_sensor_metadata", "value": int(sensor_devices["device_id"].nunique())},
            {"metric": "sensor_accelerometer_device_ids", "value": int(sensor_devices.loc[sensor_devices.source_table.eq("sensor_accelerometer"), "device_id"].nunique())},
            {"metric": "sensor_linear_accelerometer_device_ids", "value": int(sensor_devices.loc[sensor_devices.source_table.eq("sensor_linear_accelerometer"), "device_id"].nunique())},
            {"metric": "raw_linear_accelerometer_device_ids", "value": int(raw_linear_devices["device_id"].nunique())},
            {"metric": "sensor_accelerometer_metadata_rows", "value": int(len(sensor_frames["sensor_accelerometer"]))},
            {"metric": "sensor_linear_accelerometer_metadata_rows", "value": int(len(sensor_frames["sensor_linear_accelerometer"]))},
            {"metric": "raw_linear_accelerometer_rows_scanned", "value": int(raw_linear_devices["raw_linear_accelerometer_rows"].sum())},
            {"metric": "sensor_accelerometer_json_parse_errors", "value": parse_errors["sensor_accelerometer"]},
            {"metric": "sensor_linear_accelerometer_json_parse_errors", "value": parse_errors["sensor_linear_accelerometer"]},
            {"metric": "raw_accelerometer_rows_status", "value": "not_scanned_full_table"},
        ]
    )
    summary.to_csv(args.out_dir / "device_hardware_timeline_summary.csv", index=False)

    lines = [
        "# Accelerometer Device Hardware Timeline",
        "",
        "This is a hardware and data-collection context analysis. It is not a behavioral phenotype and it does not replace raw-signal QC.",
        "",
        "## Main table",
        "",
        "`accelerometer_device_hardware_timeline.csv` contains one row per device ID observed in the sensor metadata tables or in the raw linear-accelerometer Parquet copy.",
        "",
        "Each device row includes sensor metadata first/last seen timestamps, active months, sensor identity, vendor, version, nominal minimum delay, resolution, range, power, and raw linear-accelerometer row counts where available.",
        "",
        "## Interpretation",
        "",
        "- `device_id` is an app/device identifier and is not automatically a unique physical phone or patient.",
        "- Sensor metadata rows are snapshots and may repeat; metadata row count is not device prevalence.",
        "- `double_sensor_minimum_delay` is nominal hardware/request capability context, not observed sampling frequency.",
        "- The raw `linear_accelerometer` Parquet was scanned for complete per-device counts and time spans.",
        "- The full raw `accelerometer` table is not available as local Parquet, so its full per-device row count is explicitly marked unavailable rather than inferred.",
        "- Use the monthly prevalence and configuration tables to identify hardware turnover and possible cross-device comparability problems before building motion features.",
        "",
        "## Outputs",
        "",
        "- `accelerometer_device_hardware_timeline.csv`: one row per device ID.",
        "- `sensor_device_summary_long.csv`: one row per device and sensor metadata table.",
        "- `sensor_configuration_summary.csv`: configuration prevalence and time span.",
        "- `device_hardware_monthly_prevalence.csv`: monthly metadata/raw-stream prevalence.",
        "- `raw_linear_device_summary.csv`: full raw linear-accelerometer per-device scan.",
        "- `device_hardware_timeline_summary.csv`: audit counts and scan status.",
        "",
        "No SQL tables, Parquet files, or existing patient-level cohorts were modified.",
    ]
    (args.out_dir / "README_accelerometer_device_hardware_timeline.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"output_dir={args.out_dir}")
    print(f"device_rows={len(combined)}")
    print(f"configuration_rows={len(configurations)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if args.threads < 1:
        raise ValueError("--threads must be positive")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    build_outputs(args)


if __name__ == "__main__":
    main()
