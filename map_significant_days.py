import argparse
import csv
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import mysql.connector
import pandas as pd

from main import connect_sensordata_db


MS_PER_DAY = 86_400_000


def reconnect():
    conn = connect_sensordata_db()
    cur = conn.cursor()
    return conn, cur


def run_with_retry(
    fn: Callable[[object], object],
    conn,
    cur,
    retries: int,
    retry_sleep: float,
):
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            return fn(cur), conn, cur
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


def load_device_ranges(ranges_csv: Path, patient_label: str) -> List[Tuple[str, int, int]]:
    out: List[Tuple[str, int, int]] = []
    with ranges_csv.open(newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if (row.get("patient_label") or "").strip() != patient_label:
                continue
            if (row.get("status") or "").strip() != "ok":
                continue
            device_id = (row.get("device_id") or "").strip()
            first_ts = (row.get("first_ts") or "").strip()
            last_ts = (row.get("last_ts") or "").strip()
            if device_id and first_ts and last_ts:
                out.append((device_id, int(first_ts), int(last_ts)))
    return out


def get_significant_day_buckets(
    device_id: str,
    first_ts: int,
    last_ts: int,
    conn,
    cur,
    retries: int,
    retry_sleep: float,
):
    def q(c):
        c.execute(
            """
            SELECT DISTINCT FLOOR(timestamp / 86400000) AS day_bucket
            FROM significant
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp <= %s
            ORDER BY day_bucket
            """,
            (device_id, first_ts, last_ts),
        )
        return c.fetchall()

    rows, conn, cur = run_with_retry(q, conn, cur, retries, retry_sleep)
    buckets = [int(r[0]) for r in rows if r and r[0] is not None]
    return buckets, conn, cur


def main():
    p = argparse.ArgumentParser(description="Map local days that have data in significant table within known time ranges.")
    p.add_argument("--ranges-csv", type=Path, default=Path("output/device_time_ranges_significant.csv"))
    p.add_argument("--patient-label", required=True)
    p.add_argument("--tz", default="Asia/Jerusalem")
    p.add_argument("--out", type=Path, default=Path("output/significant_days_map.csv"))
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--retry-sleep", type=float, default=8.0)
    args = p.parse_args()

    devices = load_device_ranges(args.ranges_csv, args.patient_label)
    if not devices:
        raise ValueError(f"No 'ok' device ranges found for patient {args.patient_label}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "patient_label",
                "device_id",
                "day_local",
                "day_start_local",
                "day_end_local",
                "day_start_ms_utc",
                "day_end_ms_utc",
            ],
        )
        w.writeheader()
        f.flush()

        conn, cur = reconnect()
        try:
            for device_id, first_ts, last_ts in devices:
                day_buckets, conn, cur = get_significant_day_buckets(
                    device_id=device_id,
                    first_ts=first_ts,
                    last_ts=last_ts,
                    conn=conn,
                    cur=cur,
                    retries=args.retries,
                    retry_sleep=args.retry_sleep,
                )
                print(f"device={device_id} significant_days={len(day_buckets)}")
                for day_bucket in day_buckets:
                    day_start_ms = day_bucket * MS_PER_DAY
                    day_end_ms = (day_bucket + 1) * MS_PER_DAY
                    start_local = pd.to_datetime(day_start_ms, unit="ms", utc=True).tz_convert(args.tz)
                    end_local = pd.to_datetime(day_end_ms, unit="ms", utc=True).tz_convert(args.tz)
                    w.writerow(
                        {
                            "patient_label": args.patient_label,
                            "device_id": device_id,
                            "day_local": str(start_local.date()),
                            "day_start_local": str(start_local),
                            "day_end_local": str(end_local),
                            "day_start_ms_utc": day_start_ms,
                            "day_end_ms_utc": day_end_ms,
                        }
                    )
                    f.flush()
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass

    print(args.out)


if __name__ == "__main__":
    main()
