import argparse
import csv
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import mysql.connector
import pandas as pd

from main import connect_sensordata_db


MS_PER_DAY = 86_400_000


def parse_label_map_rows(label_map_csv: Path, row_start: int, row_end: int) -> List[Tuple[str, List[str]]]:
    if row_start < 1 or row_end < row_start:
        raise ValueError("Invalid patient row range.")

    out: List[Tuple[str, List[str]]] = []
    with label_map_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            if idx < row_start or idx > row_end:
                continue
            label = (row.get("label") or "").strip()
            raw = (row.get("device_ids") or "").strip()
            device_ids = sorted({x.strip() for x in raw.split(";") if x.strip()})
            if device_ids:
                out.append((label, device_ids))
    return out


def open_csv_writer(path: Path, fieldnames: Sequence[str], append: bool):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    exists = path.exists() and path.stat().st_size > 0
    f = path.open(mode, newline="")
    w = csv.DictWriter(f, fieldnames=fieldnames)
    if (not append) or (not exists):
        w.writeheader()
        f.flush()
    return f, w


def reconnect() -> Tuple[object, object]:
    conn = connect_sensordata_db()
    cur = conn.cursor()
    return conn, cur


def run_with_retry(
    fn: Callable[[object], object],
    conn,
    cur,
    retries: int,
    retry_sleep: float,
) -> Tuple[object, object, object]:
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            result = fn(cur)
            return result, conn, cur
        except mysql.connector.Error as e:
            last_err = e
            if attempt >= retries:
                break
            try:
                cur.close()
                conn.close()
            except Exception:
                pass
            time.sleep(retry_sleep)
            conn, cur = reconnect()
    raise last_err if last_err is not None else RuntimeError("Unknown DB error")


def get_first_last_ts_ms(device_id: str, conn, cur, retries: int, retry_sleep: float):
    def q(c):
        c.execute(
            """
            SELECT MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM aware_log
            WHERE device_id = %s
            """,
            (device_id,),
        )
        return c.fetchone()

    row, conn, cur = run_with_retry(q, conn, cur, retries, retry_sleep)
    first_ms = int(row[0]) if row and row[0] is not None else None
    last_ms = int(row[1]) if row and row[1] is not None else None
    return first_ms, last_ms, conn, cur


def get_day_buckets(device_id: str, with_counts: bool, conn, cur, retries: int, retry_sleep: float):
    def q(c):
        if with_counts:
            c.execute(
                """
                SELECT FLOOR(timestamp / 86400000) AS day_bucket, COUNT(*) AS n_rows
                FROM aware_log
                WHERE device_id = %s
                GROUP BY day_bucket
                ORDER BY day_bucket
                """,
                (device_id,),
            )
        else:
            c.execute(
                """
                SELECT DISTINCT FLOOR(timestamp / 86400000) AS day_bucket
                FROM aware_log
                WHERE device_id = %s
                ORDER BY day_bucket
                """,
                (device_id,),
            )
        return c.fetchall()

    rows, conn, cur = run_with_retry(q, conn, cur, retries, retry_sleep)
    out: List[Tuple[int, Optional[int]]] = []
    for row in rows:
        if row[0] is None:
            continue
        if with_counts:
            out.append((int(row[0]), int(row[1] or 0)))
        else:
            out.append((int(row[0]), None))
    return out, conn, cur


def main() -> None:
    parser = argparse.ArgumentParser(description="Build device/day availability map from aware_log table.")
    parser.add_argument("--label-map-csv", type=Path, required=True)
    parser.add_argument("--patient-row-start", type=int, default=1)
    parser.add_argument("--patient-row-end", type=int, default=90)
    parser.add_argument("--tz", default="Asia/Jerusalem")
    parser.add_argument("--with-counts", action="store_true")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-sleep", type=float, default=8.0)
    parser.add_argument("--out-dir", type=Path, default=Path("output"))
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()

    patients = parse_label_map_rows(args.label_map_csv, args.patient_row_start, args.patient_row_end)
    if not patients:
        raise ValueError("No matching patients with device_ids in selected row range.")

    overview_path = args.out_dir / "aware_log_device_overview.csv"
    days_path = args.out_dir / "aware_log_device_days.csv"

    overview_fields = [
        "patient_label",
        "device_id",
        "first_ts_ms",
        "last_ts_ms",
        "first_local",
        "last_local",
        "approx_days_span",
        "status",
    ]
    day_fields = [
        "patient_label",
        "device_id",
        "day_local",
        "day_start_local",
        "day_end_local",
        "day_start_ms_utc",
        "day_end_ms_utc",
        "n_rows_day",
    ]

    overview_f, overview_w = open_csv_writer(overview_path, overview_fields, append=args.append)
    days_f, days_w = open_csv_writer(days_path, day_fields, append=args.append)

    conn, cur = reconnect()
    try:
        for p_idx, (patient_label, device_ids) in enumerate(patients, start=1):
            print(f"patient={patient_label} ({p_idx}/{len(patients)}), devices={len(device_ids)}")
            for device_id in device_ids:
                try:
                    first_ms, last_ms, conn, cur = get_first_last_ts_ms(
                        device_id=device_id,
                        conn=conn,
                        cur=cur,
                        retries=args.retries,
                        retry_sleep=args.retry_sleep,
                    )
                    if first_ms is None or last_ms is None:
                        overview_w.writerow(
                            {
                                "patient_label": patient_label,
                                "device_id": device_id,
                                "first_ts_ms": "",
                                "last_ts_ms": "",
                                "first_local": "",
                                "last_local": "",
                                "approx_days_span": "",
                                "status": "no_data",
                            }
                        )
                        overview_f.flush()
                        continue

                    first_local = pd.to_datetime(first_ms, unit="ms", utc=True).tz_convert(args.tz)
                    last_local = pd.to_datetime(last_ms, unit="ms", utc=True).tz_convert(args.tz)
                    first_day_local = first_local.floor("D")
                    last_day_local = last_local.floor("D")
                    span_days = int((last_day_local - first_day_local).days) + 1

                    overview_w.writerow(
                        {
                            "patient_label": patient_label,
                            "device_id": device_id,
                            "first_ts_ms": first_ms,
                            "last_ts_ms": last_ms,
                            "first_local": str(first_local),
                            "last_local": str(last_local),
                            "approx_days_span": span_days,
                            "status": "ok",
                        }
                    )
                    overview_f.flush()

                    buckets, conn, cur = get_day_buckets(
                        device_id=device_id,
                        with_counts=args.with_counts,
                        conn=conn,
                        cur=cur,
                        retries=args.retries,
                        retry_sleep=args.retry_sleep,
                    )
                    for idx, (bucket, n_rows) in enumerate(buckets, start=1):
                        day_start_ms = bucket * MS_PER_DAY
                        day_end_ms = (bucket + 1) * MS_PER_DAY
                        start_local = pd.to_datetime(day_start_ms, unit="ms", utc=True).tz_convert(args.tz)
                        end_local = pd.to_datetime(day_end_ms, unit="ms", utc=True).tz_convert(args.tz)
                        days_w.writerow(
                            {
                                "patient_label": patient_label,
                                "device_id": device_id,
                                "day_local": str(start_local.date()),
                                "day_start_local": str(start_local),
                                "day_end_local": str(end_local),
                                "day_start_ms_utc": day_start_ms,
                                "day_end_ms_utc": day_end_ms,
                                "n_rows_day": n_rows if args.with_counts else "",
                            }
                        )
                        days_f.flush()
                        print(f"device={device_id} day_bucket={idx}/{len(buckets)}")
                except Exception as e:
                    overview_w.writerow(
                        {
                            "patient_label": patient_label,
                            "device_id": device_id,
                            "first_ts_ms": "",
                            "last_ts_ms": "",
                            "first_local": "",
                            "last_local": "",
                            "approx_days_span": "",
                            "status": f"error:{e}",
                        }
                    )
                    overview_f.flush()
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass
        overview_f.close()
        days_f.close()

    print(overview_path)
    print(days_path)


if __name__ == "__main__":
    main()
