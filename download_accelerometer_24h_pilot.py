from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


ROOT = Path(__file__).parent
TZ = "Asia/Jerusalem"
TABLE_NAME = "accelerometer"
QC_PATH = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_patient.csv"
OUT_DIR = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot"
EXCLUDED_SUBJECTS = {"001"}
KNOWN_START_MS = 1736320047852


def ms_to_local(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.to_datetime(int(value), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z")


def local_to_ms(value: pd.Timestamp) -> int:
    if value.tzinfo is None:
        value = value.tz_localize(TZ)
    return int(value.tz_convert("UTC").timestamp() * 1000)


def known_verified_pilot() -> dict[str, Any]:
    end_ms = KNOWN_START_MS + 24 * 60 * 60 * 1000
    return {
        "Subject_ID_D": "041",
        "Subject_ID_N": "15",
        "global_T1": "119.4",
        "T1_date_iso": "2025-01-08",
        "device_id": "d74f7acf-f82f-491d-90b9-d7321e6d4bcf",
        "candidate_window_start_ms": KNOWN_START_MS,
        "candidate_window_end_ms": end_ms,
        "candidate_window_start_local": ms_to_local(KNOWN_START_MS),
        "candidate_window_end_local": ms_to_local(end_ms),
        "first_raw_ts": KNOWN_START_MS,
        "first_raw_local": ms_to_local(KNOWN_START_MS),
        "status": "known_verified_from_10min_phase2a_raw_sample",
    }


def numeric(value: Any) -> float | None:
    out = pd.to_numeric(value, errors="coerce")
    if pd.isna(out):
        return None
    return float(out)


def parse_data(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def signal_fields(data: dict[str, Any]) -> dict[str, Any]:
    x = numeric(data.get("double_values_0"))
    y = numeric(data.get("double_values_1"))
    z = numeric(data.get("double_values_2"))
    magnitude = ""
    if x is not None and y is not None and z is not None:
        magnitude = (x**2 + y**2 + z**2) ** 0.5
    return {
        "x": x if x is not None else "",
        "y": y if y is not None else "",
        "z": z if z is not None else "",
        "accuracy": data.get("accuracy", ""),
        "label": data.get("label", ""),
        "magnitude": magnitude,
    }


def load_ranked_qc() -> pd.DataFrame:
    df = pd.read_csv(QC_PATH, dtype=str)
    df["global_T1_num"] = pd.to_numeric(df.get("global_T1"), errors="coerce")
    df = df.dropna(subset=["Subject_ID_D", "global_T1_num", "T1_date_iso", "selected_device_id"]).copy()
    df["Subject_ID_D"] = df["Subject_ID_D"].astype(str).str.zfill(3)
    df = df[~df["Subject_ID_D"].isin(EXCLUDED_SUBJECTS)].copy()
    if "has_sensor_accelerometer_metadata_after_T1" in df.columns:
        df = df[df["has_sensor_accelerometer_metadata_after_T1"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    df = df[df["selected_device_id"].astype(str).str.strip().ne("")]
    return df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True])


def first_existing_raw_row(conn, device_id: str, start_ms: int, end_ms: int) -> int | None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT timestamp
            FROM `accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        cur.close()


def count_raw_rows(conn, device_id: str, start_ms: int, end_ms: int) -> dict[str, Any]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM `accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        return cur.fetchone() or {"n_rows": 0, "first_ts": None, "last_ts": None}
    finally:
        cur.close()


def find_24h_candidate(conn, min_rows: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    checked: list[dict[str, Any]] = []
    for _, patient in load_ranked_qc().iterrows():
        subject_id = str(patient["Subject_ID_D"])
        device_id = str(patient["selected_device_id"]).strip()
        t1 = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize(TZ)
        week_start = t1
        week_end = t1 + pd.Timedelta(days=7)
        first_ts = first_existing_raw_row(conn, device_id, local_to_ms(week_start), local_to_ms(week_end))
        row: dict[str, Any] = {
            "Subject_ID_D": subject_id,
            "Subject_ID_N": patient.get("Subject_ID_N", ""),
            "global_T1": patient.get("global_T1", ""),
            "T1_date_iso": patient.get("T1_date_iso", ""),
            "device_id": device_id,
            "search_start_local": week_start.strftime("%Y-%m-%d %H:%M:%S%z"),
            "search_end_local": week_end.strftime("%Y-%m-%d %H:%M:%S%z"),
            "first_raw_ts": first_ts,
            "first_raw_local": ms_to_local(first_ts),
        }
        if first_ts is None:
            row.update({"candidate_24h_rows": 0, "status": "no_raw_rows_in_T1_week"})
            checked.append(row)
            print(f"checked subject={subject_id} no raw accelerometer in T1 week", flush=True)
            continue
        start_ms = int(first_ts)
        end_ms = start_ms + 24 * 60 * 60 * 1000
        coverage = count_raw_rows(conn, device_id, start_ms, end_ms)
        n_rows = int(coverage.get("n_rows") or 0)
        row.update(
            {
                "candidate_window_start_ms": start_ms,
                "candidate_window_end_ms": end_ms,
                "candidate_window_start_local": ms_to_local(start_ms),
                "candidate_window_end_local": ms_to_local(end_ms),
                "candidate_24h_rows": n_rows,
                "candidate_first_local": ms_to_local(coverage.get("first_ts")),
                "candidate_last_local": ms_to_local(coverage.get("last_ts")),
                "status": "candidate_has_min_rows" if n_rows >= min_rows else "candidate_below_min_rows",
            }
        )
        checked.append(row)
        print(f"checked subject={subject_id} raw_24h_rows={n_rows:,}", flush=True)
        if n_rows >= min_rows:
            return row, checked
    return None, checked


def fetch_chunk(conn, device_id: str, start_ms: int, end_ms: int, batch_rows: int):
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT _id, timestamp, device_id, data
            FROM `accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        while True:
            rows = cur.fetchmany(batch_rows)
            if not rows:
                break
            yield rows
    finally:
        cur.close()


def write_readme(candidate: dict[str, Any] | None, total_rows: int, chunk_minutes: int, raw_path: Path, signal_path: Path) -> str:
    if candidate:
        selected_text = f"""
- Subject_ID_D: `{candidate["Subject_ID_D"]}`
- Subject_ID_N: `{candidate["Subject_ID_N"]}`
- global_T1: `{candidate["global_T1"]}`
- T1_date_iso: `{candidate["T1_date_iso"]}`
- device_id: `{candidate["device_id"]}`
- window_start_local: `{candidate["candidate_window_start_local"]}`
- window_end_local: `{candidate["candidate_window_end_local"]}`
- downloaded_rows: `{total_rows}`
"""
    else:
        selected_text = "No 24h raw accelerometer candidate was downloaded."
    return f"""# Accelerometer 24h Raw Pilot

This folder contains a bounded local raw-data pilot for the `accelerometer` table.

Purpose:

- Download one patient/device 24-hour raw accelerometer window for local signal analysis.
- Avoid repeated SQL calls while developing filtering, frequency, and activity-state logic.
- Keep this separate from Phase 3 model-facing feature outputs.

Safety and scope:

- No full-table query was run.
- SQL was filtered by one `device_id` and bounded timestamps.
- Rows were fetched chronologically and written in chunks.
- Missing raw rows remain missing and are not interpreted as no movement.
- General accelerometer includes gravity plus phone motion, so this is phone-state signal analysis, not direct body-movement diagnosis.

Candidate-selection rule:

- Rank patients by T1 global score, excluding Subject_ID_D `001`.
- For each selected `sensor_accelerometer` device, search only the first week from T1.
- Use the first available raw `accelerometer` timestamp in that week as the 24-hour window start.
- Select the first ranked patient/device whose 24-hour raw window has the minimum row threshold.

Selected window:

{selected_text}

Files:

- `{raw_path.name}`: raw `_id`, `timestamp`, `local_datetime`, `device_id`, and original JSON data.
- `{signal_path.name}`: expanded signal columns for faster local analysis: x, y, z, accuracy, label, magnitude.
- `accelerometer_24h_pilot_manifest.csv`: selected window, row counts, file paths, and chunk settings.
- `accelerometer_24h_pilot_candidate_scan.csv`: ranked patient/device search trail.
- `accelerometer_24h_pilot_chunk_log.csv`: per-chunk rows written and error status.

Chunk size: `{chunk_minutes}` minutes.
"""


def download_candidate(candidate: dict[str, Any], chunk_minutes: int, batch_rows: int) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    subject_id = candidate["Subject_ID_D"]
    device_id = candidate["device_id"]
    start_ms = int(candidate["candidate_window_start_ms"])
    end_ms = int(candidate["candidate_window_end_ms"])
    base = f"accelerometer_24h_subject_{subject_id}_device_{device_id[:8]}_{start_ms}_{end_ms}"
    raw_path = OUT_DIR / f"{base}_raw.csv.gz"
    signal_path = OUT_DIR / f"{base}_signal.csv.gz"
    chunk_log_path = OUT_DIR / "accelerometer_24h_pilot_chunk_log.csv"

    raw_fields = ["_id", "timestamp", "local_datetime", "device_id", "data_json"]
    signal_fields_out = ["_id", "timestamp", "local_datetime", "device_id", "x", "y", "z", "accuracy", "label", "magnitude"]
    chunk_rows: list[dict[str, Any]] = []
    total_rows = 0

    conn = connect_sensordata_db()
    try:
        with gzip.open(raw_path, "wt", newline="", encoding="utf-8") as raw_handle, gzip.open(
            signal_path, "wt", newline="", encoding="utf-8"
        ) as signal_handle:
            raw_writer = csv.DictWriter(raw_handle, fieldnames=raw_fields)
            signal_writer = csv.DictWriter(signal_handle, fieldnames=signal_fields_out)
            raw_writer.writeheader()
            signal_writer.writeheader()

            chunk_ms = chunk_minutes * 60 * 1000
            t = start_ms
            while t < end_ms:
                t_next = min(t + chunk_ms, end_ms)
                chunk_count = 0
                status = "ok"
                error_message = ""
                try:
                    for batch in fetch_chunk(conn, device_id, t, t_next, batch_rows):
                        for row in batch:
                            data = parse_data(row.get("data"))
                            local_datetime = ms_to_local(row.get("timestamp"))
                            raw_writer.writerow(
                                {
                                    "_id": row.get("_id", ""),
                                    "timestamp": row.get("timestamp", ""),
                                    "local_datetime": local_datetime,
                                    "device_id": row.get("device_id", ""),
                                    "data_json": json.dumps(data, ensure_ascii=False, default=str),
                                }
                            )
                            signal_writer.writerow(
                                {
                                    "_id": row.get("_id", ""),
                                    "timestamp": row.get("timestamp", ""),
                                    "local_datetime": local_datetime,
                                    "device_id": row.get("device_id", ""),
                                    **signal_fields(data),
                                }
                            )
                            chunk_count += 1
                    total_rows += chunk_count
                except Exception as exc:  # noqa: BLE001
                    status = "error"
                    error_message = str(exc)
                chunk_rows.append(
                    {
                        "chunk_start_ms": t,
                        "chunk_end_ms": t_next,
                        "chunk_start_local": ms_to_local(t),
                        "chunk_end_local": ms_to_local(t_next),
                        "rows_written": chunk_count,
                        "cumulative_rows_written": total_rows,
                        "status": status,
                        "error_message": error_message,
                    }
                )
                pd.DataFrame(chunk_rows).to_csv(chunk_log_path, index=False)
                print(
                    f"chunk {ms_to_local(t)} -> {ms_to_local(t_next)} rows={chunk_count:,} total={total_rows:,} status={status}",
                    flush=True,
                )
                if status == "error":
                    break
                t = t_next
    finally:
        conn.close()

    return {
        "raw_path": raw_path,
        "signal_path": signal_path,
        "chunk_log_path": chunk_log_path,
        "total_rows": total_rows,
        "raw_size_mb": raw_path.stat().st_size / (1024 * 1024) if raw_path.exists() else pd.NA,
        "signal_size_mb": signal_path.stat().st_size / (1024 * 1024) if signal_path.exists() else pd.NA,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Download one bounded 24h raw accelerometer pilot window.")
    parser.add_argument("--min-rows", type=int, default=1000)
    parser.add_argument("--chunk-minutes", type=int, default=5)
    parser.add_argument("--batch-rows", type=int, default=10000)
    parser.add_argument(
        "--candidate-scan",
        action="store_true",
        help="Search ranked QC patients for a 24h candidate before downloading. Default uses the previously verified subject 041 raw window.",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scan_path = OUT_DIR / "accelerometer_24h_pilot_candidate_scan.csv"
    manifest_path = OUT_DIR / "accelerometer_24h_pilot_manifest.csv"
    readme_path = OUT_DIR / "README_accelerometer_24h_pilot.md"

    if args.candidate_scan:
        conn = connect_sensordata_db()
        try:
            candidate, checked = find_24h_candidate(conn, args.min_rows)
        finally:
            conn.close()
    else:
        candidate = known_verified_pilot()
        checked = [
            {
                **candidate,
                "search_mode": "known_verified_window_no_24h_count",
                "note": "Avoids slow raw accelerometer 24h COUNT; row count is produced during chunked download.",
            }
        ]

    pd.DataFrame(checked).to_csv(scan_path, index=False)
    if candidate is None:
        pd.DataFrame(
            [
                {
                    "status": "no_candidate_found",
                    "min_rows": args.min_rows,
                    "candidate_scan_path": str(scan_path),
                }
            ]
        ).to_csv(manifest_path, index=False)
        readme_path.write_text(write_readme(None, 0, args.chunk_minutes, Path(""), Path("")), encoding="utf-8")
        print("No 24h candidate found.")
        print(f"candidate_scan: {scan_path}")
        print(f"manifest: {manifest_path}")
        return

    result = download_candidate(candidate, args.chunk_minutes, args.batch_rows)
    manifest = {
        **candidate,
        "status": "download_complete",
        "min_rows": args.min_rows,
        "chunk_minutes": args.chunk_minutes,
        "batch_rows": args.batch_rows,
        "downloaded_rows": result["total_rows"],
        "raw_path": str(result["raw_path"]),
        "signal_path": str(result["signal_path"]),
        "chunk_log_path": str(result["chunk_log_path"]),
        "raw_size_mb": result["raw_size_mb"],
        "signal_size_mb": result["signal_size_mb"],
    }
    pd.DataFrame([manifest]).to_csv(manifest_path, index=False)
    readme_path.write_text(
        write_readme(candidate, result["total_rows"], args.chunk_minutes, result["raw_path"], result["signal_path"]),
        encoding="utf-8",
    )

    print("download_complete")
    print(f"subject: {candidate['Subject_ID_D']}")
    print(f"device: {candidate['device_id']}")
    print(f"window_start: {candidate['candidate_window_start_local']}")
    print(f"window_end: {candidate['candidate_window_end_local']}")
    print(f"downloaded_rows: {result['total_rows']:,}")
    print(f"raw_file: {result['raw_path']}")
    print(f"signal_file: {result['signal_path']}")
    print(f"manifest: {manifest_path}")
    print(f"scan: {scan_path}")
    print(f"chunk_log: {result['chunk_log_path']}")


if __name__ == "__main__":
    main()
