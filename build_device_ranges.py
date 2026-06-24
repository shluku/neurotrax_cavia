import argparse
import csv
import datetime as dt
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import mysql.connector

from main import connect_sensordata_db


MS_PER_DAY = 86_400_000


def parse_label_map_rows(
    label_map_csv: Path,
    row_start: int,
    row_end: int,
) -> List[Tuple[str, List[str]]]:
    if row_start < 1 or row_end < row_start:
        raise ValueError("Invalid row range.")

    out: List[Tuple[str, List[str]]] = []
    with label_map_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            if idx < row_start or idx > row_end:
                continue
            label = (row.get("label") or "").strip()
            raw = (row.get("device_ids") or "").strip()
            device_ids = sorted({x.strip() for x in raw.split(";") if x.strip()})
            out.append((label, device_ids))
    return out


def utc_str_from_ms(ms: Optional[int]) -> str:
    if ms is None:
        return ""
    d = dt.datetime.fromtimestamp(ms / 1000.0, tz=dt.timezone.utc)
    return d.strftime("%Y-%m-%d %H:%M:%S.%f%z")


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


def fetch_device_ranges_batch(
    device_ids: Sequence[str],
    conn,
    cur,
    retries: int,
    retry_sleep: float,
) -> Tuple[Dict[str, Tuple[Optional[int], Optional[int]]], object, object]:
    placeholders = ",".join(["%s"] * len(device_ids))
    query = (
        "SELECT device_id, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts "
        "FROM significant "
        f"WHERE device_id IN ({placeholders}) "
        "GROUP BY device_id"
    )

    def q(c):
        c.execute(query, tuple(device_ids))
        return c.fetchall()

    rows, conn, cur = run_with_retry(q, conn, cur, retries, retry_sleep)
    out: Dict[str, Tuple[Optional[int], Optional[int]]] = {}
    for device_id, first_ts, last_ts in rows:
        out[str(device_id)] = (
            int(first_ts) if first_ts is not None else None,
            int(last_ts) if last_ts is not None else None,
        )
    return out, conn, cur


def fetch_device_range_single(
    device_id: str,
    conn,
    cur,
    retries: int,
    retry_sleep: float,
) -> Tuple[Tuple[Optional[int], Optional[int]], object, object]:
    def q(c):
        c.execute(
            """
            SELECT MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM significant
            WHERE device_id = %s
            """,
            (device_id,),
        )
        return c.fetchone()

    row, conn, cur = run_with_retry(q, conn, cur, retries, retry_sleep)
    if not row:
        return (None, None), conn, cur
    first_ts = int(row[0]) if row[0] is not None else None
    last_ts = int(row[1]) if row[1] is not None else None
    return (first_ts, last_ts), conn, cur


def main() -> None:
    parser = argparse.ArgumentParser(description="Build per-device timestamp ranges from significant table.")
    parser.add_argument("--label-map-csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("output/device_time_ranges_significant.csv"))
    parser.add_argument("--row-start", type=int, default=1)
    parser.add_argument("--row-end", type=int, default=90)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-sleep", type=float, default=8.0)
    args = parser.parse_args()

    patients = parse_label_map_rows(args.label_map_csv, args.row_start, args.row_end)
    if not patients:
        raise ValueError("No matching rows in label map.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as out_f:
        fieldnames = [
            "patient_label",
            "device_id",
            "first_ts",
            "last_ts",
            "span_days",
            "status",
            "first_utc",
            "last_utc",
        ]
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()
        out_f.flush()

        conn, cur = reconnect()
        try:
            for idx, (patient_label, device_ids) in enumerate(patients, start=1):
                if not device_ids:
                    print(f"patient={patient_label} ({idx}/{len(patients)}), devices=0")
                    continue

                print(f"patient={patient_label} ({idx}/{len(patients)}), devices={len(device_ids)}")
                try:
                    ranges_map, conn, cur = fetch_device_ranges_batch(
                        device_ids=device_ids,
                        conn=conn,
                        cur=cur,
                        retries=args.retries,
                        retry_sleep=args.retry_sleep,
                    )
                except Exception:
                    # Fallback to one-query-per-device so one bad query won't block all devices.
                    ranges_map = {}

                for device_id in device_ids:
                    try:
                        if device_id in ranges_map:
                            first_ts, last_ts = ranges_map[device_id]
                        else:
                            (first_ts, last_ts), conn, cur = fetch_device_range_single(
                                device_id=device_id,
                                conn=conn,
                                cur=cur,
                                retries=args.retries,
                                retry_sleep=args.retry_sleep,
                            )

                        if first_ts is None or last_ts is None:
                            status = "no_data"
                            span_days = ""
                        else:
                            status = "ok"
                            span_days = (last_ts - first_ts) / MS_PER_DAY

                        writer.writerow(
                            {
                                "patient_label": patient_label,
                                "device_id": device_id,
                                "first_ts": first_ts if first_ts is not None else "",
                                "last_ts": last_ts if last_ts is not None else "",
                                "span_days": span_days,
                                "status": status,
                                "first_utc": utc_str_from_ms(first_ts),
                                "last_utc": utc_str_from_ms(last_ts),
                            }
                        )
                        out_f.flush()
                    except Exception as e:
                        writer.writerow(
                            {
                                "patient_label": patient_label,
                                "device_id": device_id,
                                "first_ts": "",
                                "last_ts": "",
                                "span_days": "",
                                "status": f"error:{e}",
                                "first_utc": "",
                                "last_utc": "",
                            }
                        )
                        out_f.flush()
        finally:
            try:
                cur.close()
                conn.close()
            except Exception:
                pass

    print(args.out)


if __name__ == "__main__":
    main()
