import argparse
import csv
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import mysql.connector
import pandas as pd

from main import connect_sensordata_db


@dataclass
class DayWindow:
    day_local: str
    start_ms: int
    end_ms: int
    start_local: str
    end_local: str


def build_day_windows(start_ms: int, end_ms: int, tz_name: str) -> List[DayWindow]:
    start_utc = pd.to_datetime(start_ms, unit="ms", utc=True)
    end_utc = pd.to_datetime(end_ms, unit="ms", utc=True)
    start_local = start_utc.tz_convert(tz_name).floor("D")
    end_local = end_utc.tz_convert(tz_name).ceil("D")

    out: List[DayWindow] = []
    cur = start_local
    while cur < end_local:
        nxt = cur + pd.Timedelta(days=1)
        out.append(
            DayWindow(
                day_local=str(cur.date()),
                start_ms=int(cur.tz_convert("UTC").value // 1_000_000),
                end_ms=int(nxt.tz_convert("UTC").value // 1_000_000),
                start_local=str(cur),
                end_local=str(nxt),
            )
        )
        cur = nxt
    return out


def parse_label_map_rows(
    label_map_csv: Path,
    patient_row_start: int,
    patient_row_end: int,
) -> List[Tuple[str, List[str]]]:
    if patient_row_start < 1 or patient_row_end < patient_row_start:
        raise ValueError("Invalid patient row range.")

    patients: List[Tuple[str, List[str]]] = []
    with label_map_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        for row_idx, row in enumerate(reader, start=1):
            if row_idx < patient_row_start or row_idx > patient_row_end:
                continue
            label = (row.get("label") or "").strip()
            raw = (row.get("device_ids") or "").strip()
            device_ids = sorted(set([x.strip() for x in raw.split(";") if x.strip()]))
            if not device_ids:
                continue
            patients.append((label, device_ids))
    return patients


def _open_csv_writer(path: Path, fieldnames: List[str], append: bool):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    mode = "a" if append else "w"
    f = path.open(mode, newline="")
    w = csv.DictWriter(f, fieldnames=fieldnames)
    if not append or not exists:
        w.writeheader()
        f.flush()
    return f, w


def run_daily_aggregate(
    cur,
    device_id: str,
    start_ms: int,
    end_ms: int,
    downsample_ms: Optional[int],
):
    downsample_clause = ""
    params: List[object] = [device_id, start_ms, end_ms]
    if downsample_ms is not None:
        downsample_clause = " AND (timestamp % %s) = 0 "
        params.append(int(downsample_ms))

    query = f"""
        SELECT
          COUNT(*) AS n_samples,
          MIN(timestamp) AS min_ts,
          MAX(timestamp) AS max_ts,
          AVG(s2) AS mean_s2,
          VAR_POP(s2) AS var_s2
        FROM (
          SELECT
            timestamp,
            (
              POW(CAST(data->>'$.double_values_0' AS DOUBLE), 2) +
              POW(CAST(data->>'$.double_values_1' AS DOUBLE), 2) +
              POW(CAST(data->>'$.double_values_2' AS DOUBLE), 2)
            ) AS s2
          FROM accelerometer
          WHERE device_id = %s
            AND timestamp >= %s
            AND timestamp < %s
            {downsample_clause}
        ) t
    """
    cur.execute(query, tuple(params))
    return cur.fetchone()


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily movement summary via MySQL aggregation only.")
    parser.add_argument("--label-map-csv", type=Path, required=True, help="Path to label_device_map.csv")
    parser.add_argument("--patient-row-start", type=int, default=1, help="1-based data row start")
    parser.add_argument("--patient-row-end", type=int, default=90, help="1-based data row end")

    parser.add_argument("--start-ms", type=int)
    parser.add_argument("--end-ms", type=int)
    parser.add_argument("--start-date", type=str)
    parser.add_argument("--end-date", type=str)
    parser.add_argument("--days-back", type=int)
    parser.add_argument("--tz", default="Asia/Jerusalem")

    parser.add_argument("--min-samples", type=int, default=500)
    parser.add_argument("--out-dir", type=Path, default=Path("output"))
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--downsample-ms", type=int)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--day-retries", type=int, default=3)
    parser.add_argument("--retry-sleep-seconds", type=float, default=8.0)
    args = parser.parse_args()

    if (args.start_ms is None) != (args.end_ms is None):
        raise ValueError("Provide both --start-ms and --end-ms together.")
    if (args.start_date is None) != (args.end_date is None):
        raise ValueError("Provide both --start-date and --end-date together.")

    range_flags = int(args.start_ms is not None) + int(args.start_date is not None) + int(args.days_back is not None)
    if range_flags != 1:
        raise ValueError("Use exactly one of --start-ms/--end-ms, --start-date/--end-date, or --days-back.")

    if args.min_samples < 1:
        raise ValueError("--min-samples must be >= 1")
    if args.downsample_ms is not None and args.downsample_ms < 1:
        raise ValueError("--downsample-ms must be >= 1")

    now_ms = int(pd.Timestamp.now(tz="UTC").value // 1_000_000)
    if args.start_ms is not None:
        start_ms = args.start_ms
        end_ms = args.end_ms
    elif args.start_date is not None:
        start_local = pd.Timestamp(args.start_date).tz_localize(args.tz)
        end_local = (pd.Timestamp(args.end_date) + pd.Timedelta(days=1)).tz_localize(args.tz)
        start_ms = int(start_local.tz_convert("UTC").value // 1_000_000)
        end_ms = int(end_local.tz_convert("UTC").value // 1_000_000)
    else:
        end_ms = now_ms
        start_ms = end_ms - int(args.days_back) * 86_400_000

    day_windows = build_day_windows(start_ms, end_ms, args.tz)
    if not day_windows:
        print("No day windows in selected range.")
        return

    patients = parse_label_map_rows(args.label_map_csv, args.patient_row_start, args.patient_row_end)
    if not patients:
        raise ValueError("No patient rows with device_ids found in selected range.")

    out_path = args.out_dir / "daily_movement_summary.csv"
    fieldnames = [
        "patient_label",
        "device_id",
        "day_local",
        "start_local",
        "end_local",
        "n_samples",
        "fs_est_hz",
        "mean_s2",
        "var_s2",
        "movement_index",
        "intensity_index",
        "noise_score",
        "status",
    ]
    out_file, out_writer = _open_csv_writer(out_path, fieldnames, append=args.append)

    conn = connect_sensordata_db()
    cur = conn.cursor()
    try:
        for p_idx, (patient_label, device_ids) in enumerate(patients, start=1):
            print(f"patient={patient_label} ({p_idx}/{len(patients)}), devices={len(device_ids)}")
            for device_id in device_ids:
                for day_i, w in enumerate(day_windows, start=1):
                    row_written = False
                    for attempt in range(args.day_retries + 1):
                        try:
                            stats = run_daily_aggregate(
                                cur=cur,
                                device_id=device_id,
                                start_ms=w.start_ms,
                                end_ms=w.end_ms,
                                downsample_ms=args.downsample_ms,
                            )
                            n_samples, min_ts, max_ts, mean_s2, var_s2 = stats
                            n_samples = int(n_samples or 0)

                            duration_s = 0.0
                            fs_est_hz: Optional[float] = None
                            if min_ts is not None and max_ts is not None:
                                duration_s = (float(max_ts) - float(min_ts)) / 1000.0
                                if duration_s > 0 and n_samples > 1:
                                    fs_est_hz = (n_samples - 1) / duration_s

                            mean_s2_f = float(mean_s2) if mean_s2 is not None else 0.0
                            var_s2_f = float(var_s2) if var_s2 is not None else 0.0
                            movement_index = var_s2_f
                            intensity_index = mean_s2_f
                            noise_score = math.log1p(movement_index) if movement_index > -1 else 0.0

                            if n_samples == 0:
                                status = "skipped_no_data"
                            elif n_samples < args.min_samples:
                                status = "skipped_low_samples"
                            else:
                                status = "ok"

                            out_writer.writerow(
                                {
                                    "patient_label": patient_label,
                                    "device_id": device_id,
                                    "day_local": w.day_local,
                                    "start_local": w.start_local,
                                    "end_local": w.end_local,
                                    "n_samples": n_samples,
                                    "fs_est_hz": round(fs_est_hz, 6) if fs_est_hz is not None else "",
                                    "mean_s2": round(mean_s2_f, 6),
                                    "var_s2": round(var_s2_f, 6),
                                    "movement_index": round(movement_index, 6),
                                    "intensity_index": round(intensity_index, 6),
                                    "noise_score": round(noise_score, 6),
                                    "status": status,
                                }
                            )
                            out_file.flush()
                            row_written = True
                            break

                        except mysql.connector.Error as e:
                            if attempt >= args.day_retries:
                                out_writer.writerow(
                                    {
                                        "patient_label": patient_label,
                                        "device_id": device_id,
                                        "day_local": w.day_local,
                                        "start_local": w.start_local,
                                        "end_local": w.end_local,
                                        "n_samples": 0,
                                        "fs_est_hz": "",
                                        "mean_s2": 0.0,
                                        "var_s2": 0.0,
                                        "movement_index": 0.0,
                                        "intensity_index": 0.0,
                                        "noise_score": 0.0,
                                        "status": f"error:{e}",
                                    }
                                )
                                out_file.flush()
                                row_written = True
                                break

                            try:
                                cur.close()
                                conn.close()
                            except Exception:
                                pass
                            time.sleep(args.retry_sleep_seconds)
                            conn = connect_sensordata_db()
                            cur = conn.cursor()

                    if not row_written:
                        out_writer.writerow(
                            {
                                "patient_label": patient_label,
                                "device_id": device_id,
                                "day_local": w.day_local,
                                "start_local": w.start_local,
                                "end_local": w.end_local,
                                "n_samples": 0,
                                "fs_est_hz": "",
                                "mean_s2": 0.0,
                                "var_s2": 0.0,
                                "movement_index": 0.0,
                                "intensity_index": 0.0,
                                "noise_score": 0.0,
                                "status": "error:day_not_processed",
                            }
                        )
                        out_file.flush()

                    if args.sleep_seconds > 0:
                        time.sleep(args.sleep_seconds)

    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass
        out_file.close()

    print(out_path)


if __name__ == "__main__":
    main()
