import argparse
import csv
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import mysql.connector
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfilt, sosfiltfilt

from main import connect_sensordata_db


MS_PER_DAY = 86_400_000


def parse_label_map_rows(label_map_csv: Path, row_start: int, row_end: int) -> List[Tuple[str, List[str]]]:
    if row_start < 1 or row_end < row_start:
        raise ValueError("Invalid row range.")
    out: List[Tuple[str, List[str]]] = []
    with label_map_csv.open(newline="") as f:
        r = csv.DictReader(f)
        for idx, row in enumerate(r, start=1):
            if idx < row_start or idx > row_end:
                continue
            patient_label = (row.get("label") or "").strip()
            raw = (row.get("device_ids") or "").strip()
            device_ids = sorted({x.strip() for x in raw.split(";") if x.strip()})
            out.append((patient_label, device_ids))
    return out


def parse_ranges_csv(ranges_csv: Path) -> Dict[Tuple[str, str], Tuple[Optional[int], Optional[int], str]]:
    out: Dict[Tuple[str, str], Tuple[Optional[int], Optional[int], str]] = {}
    with ranges_csv.open(newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            patient_label = (row.get("patient_label") or "").strip()
            device_id = (row.get("device_id") or "").strip()
            first_ts = (row.get("first_ts") or "").strip()
            last_ts = (row.get("last_ts") or "").strip()
            status = (row.get("status") or "").strip()
            out[(patient_label, device_id)] = (
                int(first_ts) if first_ts else None,
                int(last_ts) if last_ts else None,
                status,
            )
    return out


def reconnect(day_timeout_ms: int = 180000):
    conn = connect_sensordata_db()
    cur = conn.cursor()
    try:
        # Bound each SELECT so stuck days can be skipped.
        cur.execute(f"SET SESSION MAX_EXECUTION_TIME={int(day_timeout_ms)}")
    except Exception:
        pass
    return conn, cur


def run_with_retry(
    fn: Callable[[object], object],
    conn,
    cur,
    retries: int,
    retry_sleep: float,
    day_timeout_ms: int,
):
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            return fn(cur), conn, cur
        except mysql.connector.Error as e:
            last_err = e
            print(f"mysql_error attempt={attempt + 1}/{retries + 1}: {e}")
            if attempt >= retries:
                break
            try:
                cur.close()
                conn.close()
            except Exception:
                pass
            time.sleep(retry_sleep)
            conn, cur = reconnect(day_timeout_ms=day_timeout_ms)
    raise last_err if last_err is not None else RuntimeError("Unknown DB error")


def get_significant_day_buckets(
    device_id: str,
    first_ts: int,
    last_ts: int,
    max_days: Optional[int],
    conn,
    cur,
    retries: int,
    retry_sleep: float,
    day_timeout_ms: int,
):
    def q(c):
        sql = """
            SELECT DISTINCT FLOOR(timestamp / 86400000) AS day_bucket
            FROM significant
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp <= %s
            ORDER BY day_bucket
        """
        params: List[object] = [device_id, first_ts, last_ts]
        if max_days is not None and max_days > 0:
            sql += "\nLIMIT %s"
            params.append(max_days)
        c.execute(sql, tuple(params))
        return c.fetchall()

    rows, conn, cur = run_with_retry(q, conn, cur, retries, retry_sleep, day_timeout_ms)
    buckets = [int(r[0]) for r in rows if r and r[0] is not None]
    return buckets, conn, cur


def get_range_day_buckets(
    first_ts: int,
    last_ts: int,
    tz: str,
    max_days: Optional[int],
) -> List[int]:
    first_local = pd.to_datetime(first_ts, unit="ms", utc=True).tz_convert(tz).floor("D")
    last_local = pd.to_datetime(last_ts, unit="ms", utc=True).tz_convert(tz).floor("D")
    out: List[int] = []
    day = first_local
    while day <= last_local:
        start_ms = int(day.tz_convert("UTC").value // 1_000_000)
        out.append(start_ms // MS_PER_DAY)
        if max_days is not None and max_days > 0 and len(out) >= max_days:
            break
        day = day + pd.Timedelta(days=1)
    return out


def linear_day_exists(
    device_id: str,
    day_start_ms: int,
    day_end_ms: int,
    conn,
    cur,
    retries: int,
    retry_sleep: float,
    day_timeout_ms: int,
):
    def q(c):
        c.execute(
            """
            SELECT 1
            FROM linear_accelerometer
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            LIMIT 1
            """,
            (device_id, day_start_ms, day_end_ms),
        )
        return c.fetchone()

    row, conn, cur = run_with_retry(q, conn, cur, retries, retry_sleep, day_timeout_ms)
    return row is not None, conn, cur


def create_temp_day(
    device_id: str,
    day_start_ms: int,
    day_end_ms: int,
    conn,
    cur,
    retries: int,
    retry_sleep: float,
    day_timeout_ms: int,
):
    def q(c):
        c.execute("DROP TEMPORARY TABLE IF EXISTS temp_accel_day")
        c.execute(
            """
            CREATE TEMPORARY TABLE temp_accel_day AS
            SELECT
                timestamp,
                CAST(data->>'$.double_values_0' AS DOUBLE) AS x_axis,
                CAST(data->>'$.double_values_1' AS DOUBLE) AS y_axis,
                CAST(data->>'$.double_values_2' AS DOUBLE) AS z_axis
            FROM linear_accelerometer
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            """,
            (device_id, day_start_ms, day_end_ms),
        )
        c.execute("CREATE INDEX idx_temp_ts ON temp_accel_day(timestamp)")
        return None

    _, conn, cur = run_with_retry(q, conn, cur, retries, retry_sleep, day_timeout_ms)
    return conn, cur


def calc_day_power(conn, cur, retries: int, retry_sleep: float, day_timeout_ms: int):
    def q(c):
        c.execute(
            """
            SELECT
              COUNT(*) AS n_samples,
              AVG((x_axis * x_axis) + (y_axis * y_axis) + (z_axis * z_axis)) AS signal_power
            FROM temp_accel_day
            """
        )
        return c.fetchone()

    row, conn, cur = run_with_retry(q, conn, cur, retries, retry_sleep, day_timeout_ms)
    n_samples = int(row[0] or 0)
    signal_power = float(row[1]) if row[1] is not None else None
    return n_samples, signal_power, conn, cur


def calc_day_power_direct(
    device_id: str,
    day_start_ms: int,
    day_end_ms: int,
    conn,
    cur,
    retries: int,
    retry_sleep: float,
    day_timeout_ms: int,
    heavy_split_threshold: int,
    heavy_chunk_minutes: int,
    band_low_hz: float,
    band_high_hz: float,
):
    def q_count(c):
        c.execute(
            """
            SELECT COUNT(*)
            FROM linear_accelerometer
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            """,
            (device_id, day_start_ms, day_end_ms),
        )
        return c.fetchone()

    n_samples: Optional[int] = None
    use_chunked = False
    try:
        row, conn, cur = run_with_retry(q_count, conn, cur, retries, retry_sleep, day_timeout_ms)
        n_samples = int(row[0] or 0)
        if n_samples <= 0:
            return 0, None, conn, cur
        use_chunked = n_samples > max(0, heavy_split_threshold)
    except Exception:
        # If count itself is too heavy/unstable, switch to chunked scan directly.
        use_chunked = True

    def q_stream_window(c, w_start: int, w_end: int):
        c.execute(
            """
            SELECT
              timestamp,
              CAST(data->>'$.double_values_0' AS DOUBLE) AS x_axis,
              CAST(data->>'$.double_values_1' AS DOUBLE) AS y_axis,
              CAST(data->>'$.double_values_2' AS DOUBLE) AS z_axis
            FROM linear_accelerometer
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp
            """,
            (device_id, w_start, w_end),
        )
        ts_vals: List[int] = []
        x_vals: List[float] = []
        y_vals: List[float] = []
        z_vals: List[float] = []
        while True:
            rows = c.fetchmany(10000)
            if not rows:
                break
            for ts, x_axis, y_axis, z_axis in rows:
                if ts is None or x_axis is None or y_axis is None or z_axis is None:
                    continue
                ts_vals.append(int(ts))
                x_vals.append(float(x_axis))
                y_vals.append(float(y_axis))
                z_vals.append(float(z_axis))

        n = len(ts_vals)
        if n < 16:
            return n, None

        ts_arr = np.asarray(ts_vals, dtype=np.float64)
        dt = np.diff(ts_arr) / 1000.0
        dt = dt[dt > 0]
        if dt.size == 0:
            return 0, None
        fs = 1.0 / float(np.median(dt))
        # If nominal band is above Nyquist, adapt high cutoff to available fs.
        high_hz = min(float(band_high_hz), 0.45 * fs)
        low_hz = float(band_low_hz)
        if high_hz <= low_hz:
            return n, None

        x_arr = np.asarray(x_vals, dtype=np.float64)
        y_arr = np.asarray(y_vals, dtype=np.float64)
        z_arr = np.asarray(z_vals, dtype=np.float64)
        a = np.sqrt(x_arr * x_arr + y_arr * y_arr + z_arr * z_arr)
        a = a - float(np.mean(a))

        sos = butter(4, [low_hz, high_hz], btype="bandpass", fs=fs, output="sos")
        try:
            a_band = sosfiltfilt(sos, a)
        except ValueError:
            # Fallback to causal filtering if filtfilt cannot run on this chunk.
            try:
                a_band = sosfilt(sos, a)
            except ValueError:
                return n, None
        power = float(np.mean(a_band * a_band))
        return n, power

    if not use_chunked:
        def q_stream_full(c):
            return q_stream_window(c, day_start_ms, day_end_ms)

        result, conn, cur = run_with_retry(q_stream_full, conn, cur, retries, retry_sleep, day_timeout_ms)
        streamed_n, signal_power = result
        return int(streamed_n), signal_power, conn, cur

    chunk_ms = max(1, int(heavy_chunk_minutes)) * 60_000
    total_n = 0
    total_sum = 0.0
    w_start = day_start_ms
    while w_start < day_end_ms:
        w_end = min(w_start + chunk_ms, day_end_ms)

        def q_chunk(c):
            return q_stream_window(c, w_start, w_end)

        result, conn, cur = run_with_retry(q_chunk, conn, cur, retries, retry_sleep, day_timeout_ms)
        n_k, mean_k = result
        if n_k > 0 and mean_k is not None:
            total_n += int(n_k)
            total_sum += float(mean_k) * int(n_k)
        w_start = w_end

    signal_power = (total_sum / total_n) if total_n > 0 else None
    return int(total_n), signal_power, conn, cur


def open_writer(out_path: Path, append: bool, fields: Sequence[str]):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    exists = out_path.exists() and out_path.stat().st_size > 0
    f = out_path.open(mode, newline="")
    w = csv.DictWriter(f, fieldnames=fields)
    if not append or not exists:
        w.writeheader()
        f.flush()
    return f, w


def _fmt_hz(v: float) -> str:
    return str(v).replace(".", "p")


def main():
    p = argparse.ArgumentParser(description="Scalable phase 2: linear_accelerometer day power by day (default uses full range).")
    p.add_argument("--label-map-csv", type=Path, default=Path("output/label_device_map.csv"))
    p.add_argument("--ranges-csv", type=Path, default=Path("output/device_time_ranges_significant.csv"))
    p.add_argument("--patient-row-start", type=int, default=1)
    p.add_argument("--patient-row-end", type=int, default=90)
    p.add_argument("--patient-label", default="")
    p.add_argument("--device-id", default="", help="Optional: process only this device_id.")
    p.add_argument("--days-per-device", type=int, default=0, help="Use first N significant days per device. <=0 means all.")
    p.add_argument("--start-day-index", type=int, default=1, help="1-based day index to start from within selected day source.")
    p.add_argument("--day-source", choices=["significant", "range"], default="significant",
                   help="significant=only days seen in significant, range=all local calendar days between first_ts and last_ts")
    p.add_argument("--ask", action="store_true", help="Prompt in terminal for label/day span inputs.")
    p.add_argument("--use-temp-table", action="store_true", help="Use MySQL TEMPORARY TABLE per day (default: direct aggregate query).")
    p.add_argument("--tz", default="Asia/Jerusalem")
    p.add_argument("--min-samples", type=int, default=1)
    p.add_argument("--sleep-seconds", type=float, default=0.0)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--retry-sleep", type=float, default=8.0)
    p.add_argument("--day-timeout-seconds", type=int, default=180)
    p.add_argument("--heavy-split-threshold", type=int, default=90000,
                   help="If day row count exceeds this, process the day in chunks.")
    p.add_argument("--heavy-chunk-minutes", type=int, default=60,
                   help="Chunk size (minutes) when splitting heavy days.")
    p.add_argument("--band-low-hz", type=float, default=0.5)
    p.add_argument("--band-high-hz", type=float, default=5.0)
    p.add_argument("--append", action="store_true")
    p.add_argument("--out", type=Path, default=Path("output/daily_signal_power_from_significant_days.csv"))
    args = p.parse_args()

    if args.ask:
        label_in = input("Patient label to run (e.g. 002): ").strip()
        if label_in:
            args.patient_label = label_in
        start_in = input("Start day index (1-based, default 1): ").strip()
        if start_in:
            args.start_day_index = max(1, int(start_in))
        days_in = input("How many days to run (0 = all from start): ").strip()
        if days_in:
            args.days_per_device = int(days_in)

    all_rows = parse_label_map_rows(args.label_map_csv, args.patient_row_start, args.patient_row_end)
    if args.patient_label:
        rows = [x for x in all_rows if x[0] == args.patient_label]
    else:
        rows = all_rows
    if args.device_id:
        filtered_rows: List[Tuple[str, List[str]]] = []
        for label, devs in rows:
            only = [d for d in devs if d == args.device_id]
            if only:
                filtered_rows.append((label, only))
        rows = filtered_rows
    if not rows:
        raise ValueError("No matching patients/devices.")

    ranges_map = parse_ranges_csv(args.ranges_csv)
    power_col = f"band_power_{_fmt_hz(args.band_low_hz)}_{_fmt_hz(args.band_high_hz)}hz"
    fields = [
        "index",
        "patient_label",
        "device_id",
        "day_local",
        "day_start_ms_utc",
        "day_end_ms_utc",
        "n_samples",
        power_col,
        "status",
    ]
    out_f, out_w = open_writer(args.out, args.append, fields)
    next_index = 1
    if args.append and args.out.exists() and args.out.stat().st_size > 0:
        with args.out.open() as f:
            # header + existing rows
            next_index = max(1, sum(1 for _ in f))

    def write_row(payload: Dict[str, object]) -> None:
        nonlocal next_index
        row = {"index": next_index}
        row.update(payload)
        out_w.writerow(row)
        out_f.flush()
        next_index += 1

    day_timeout_ms = max(1, int(args.day_timeout_seconds)) * 1000
    conn, cur = reconnect(day_timeout_ms=day_timeout_ms)
    try:
        for p_idx, (patient_label, device_ids) in enumerate(rows, start=1):
            print(f"patient={patient_label} ({p_idx}/{len(rows)}), devices={len(device_ids)}")
            for device_id in device_ids:
                first_ts, last_ts, status = ranges_map.get((patient_label, device_id), (None, None, "no_data"))
                if first_ts is None or last_ts is None or status != "ok":
                    write_row(
                        {
                            "patient_label": patient_label,
                            "device_id": device_id,
                            "day_local": "",
                            "day_start_ms_utc": "",
                            "day_end_ms_utc": "",
                            "n_samples": "",
                            power_col: "",
                            "status": "no_data",
                        }
                    )
                    continue

                try:
                    max_days = args.days_per_device if args.days_per_device > 0 else None
                    max_days_query = max_days if int(args.start_day_index) <= 1 else None
                    if args.day_source == "significant":
                        day_buckets, conn, cur = get_significant_day_buckets(
                            device_id=device_id,
                            first_ts=first_ts,
                            last_ts=last_ts,
                            max_days=max_days_query,
                            conn=conn,
                            cur=cur,
                            retries=args.retries,
                            retry_sleep=args.retry_sleep,
                            day_timeout_ms=day_timeout_ms,
                        )
                    else:
                        day_buckets = get_range_day_buckets(
                            first_ts=first_ts,
                            last_ts=last_ts,
                            tz=args.tz,
                            max_days=max_days_query,
                        )
                except Exception as e:
                    write_row(
                        {
                            "patient_label": patient_label,
                            "device_id": device_id,
                            "day_local": "",
                            "day_start_ms_utc": "",
                            "day_end_ms_utc": "",
                            "n_samples": "",
                            power_col: "",
                            "status": f"error:{e}",
                        }
                    )
                    continue

                # Apply day span selection: start-day-index + days-per-device.
                start_idx = max(0, int(args.start_day_index) - 1)
                if start_idx >= len(day_buckets):
                    write_row(
                        {
                            "patient_label": patient_label,
                            "device_id": device_id,
                            "day_local": "",
                            "day_start_ms_utc": "",
                            "day_end_ms_utc": "",
                            "n_samples": "",
                            power_col: "",
                            "status": "start_day_out_of_range",
                        }
                    )
                    continue
                if args.days_per_device > 0:
                    day_buckets = day_buckets[start_idx:start_idx + args.days_per_device]
                else:
                    day_buckets = day_buckets[start_idx:]

                if not day_buckets:
                    write_row(
                        {
                            "patient_label": patient_label,
                            "device_id": device_id,
                            "day_local": "",
                            "day_start_ms_utc": "",
                            "day_end_ms_utc": "",
                            "n_samples": "",
                            power_col: "",
                            "status": "no_significant_days",
                        }
                    )
                    continue

                for idx, day_bucket in enumerate(day_buckets, start=1):
                    day_start_ms = day_bucket * MS_PER_DAY
                    day_end_ms = (day_bucket + 1) * MS_PER_DAY
                    day_local = pd.to_datetime(day_start_ms, unit="ms", utc=True).tz_convert(args.tz).date()
                    try:
                        exists, conn, cur = linear_day_exists(
                            device_id=device_id,
                            day_start_ms=day_start_ms,
                            day_end_ms=day_end_ms,
                            conn=conn,
                            cur=cur,
                            retries=args.retries,
                            retry_sleep=args.retry_sleep,
                            day_timeout_ms=day_timeout_ms,
                        )
                    except Exception as e:
                        write_row(
                            {
                                "patient_label": patient_label,
                                "device_id": device_id,
                                "day_local": str(day_local),
                                "day_start_ms_utc": day_start_ms,
                                "day_end_ms_utc": day_end_ms,
                                "n_samples": "",
                                power_col: "",
                                "status": f"error:{e}",
                            }
                        )
                        continue

                    if not exists:
                        print(
                            f"device={device_id} day={idx}/{len(day_buckets)} "
                            f"local={day_local} skipped=no_linear_data"
                        )
                        continue
                    try:
                        used_direct = not args.use_temp_table
                        if args.use_temp_table:
                            try:
                                conn, cur = create_temp_day(
                                    device_id=device_id,
                                    day_start_ms=day_start_ms,
                                    day_end_ms=day_end_ms,
                                conn=conn,
                                cur=cur,
                                retries=args.retries,
                                retry_sleep=args.retry_sleep,
                                day_timeout_ms=day_timeout_ms,
                            )
                                n_samples, signal_power, conn, cur = calc_day_power(
                                    conn=conn,
                                    cur=cur,
                                    retries=args.retries,
                                    retry_sleep=args.retry_sleep,
                                    day_timeout_ms=day_timeout_ms,
                                )
                            except Exception:
                                used_direct = True
                                n_samples, signal_power, conn, cur = calc_day_power_direct(
                                    device_id=device_id,
                                    day_start_ms=day_start_ms,
                                    day_end_ms=day_end_ms,
                                    conn=conn,
                                    cur=cur,
                                    retries=args.retries,
                                    retry_sleep=args.retry_sleep,
                                    day_timeout_ms=day_timeout_ms,
                                    heavy_split_threshold=args.heavy_split_threshold,
                                    heavy_chunk_minutes=args.heavy_chunk_minutes,
                                    band_low_hz=args.band_low_hz,
                                    band_high_hz=args.band_high_hz,
                                )
                        else:
                            n_samples, signal_power, conn, cur = calc_day_power_direct(
                                device_id=device_id,
                                day_start_ms=day_start_ms,
                                day_end_ms=day_end_ms,
                                conn=conn,
                                cur=cur,
                                retries=args.retries,
                                retry_sleep=args.retry_sleep,
                                day_timeout_ms=day_timeout_ms,
                                heavy_split_threshold=args.heavy_split_threshold,
                                heavy_chunk_minutes=args.heavy_chunk_minutes,
                                band_low_hz=args.band_low_hz,
                                band_high_hz=args.band_high_hz,
                            )
                        if n_samples < args.min_samples:
                            row_status = "low_samples"
                        elif signal_power is None:
                            row_status = "power_unavailable"
                        else:
                            row_status = "ok"
                        write_row(
                            {
                                "patient_label": patient_label,
                                "device_id": device_id,
                                "day_local": str(day_local),
                                "day_start_ms_utc": day_start_ms,
                                "day_end_ms_utc": day_end_ms,
                                "n_samples": n_samples,
                                power_col: signal_power if signal_power is not None else "",
                                "status": row_status,
                            }
                        )
                        print(
                            f"device={device_id} day={idx}/{len(day_buckets)} "
                            f"local={day_local} n={n_samples} status={row_status}"
                            f"{' mode=direct' if used_direct else ''}"
                        )
                    except Exception as e:
                        write_row(
                            {
                                "patient_label": patient_label,
                                "device_id": device_id,
                                "day_local": str(day_local),
                                "day_start_ms_utc": day_start_ms,
                                "day_end_ms_utc": day_end_ms,
                                "n_samples": "",
                                power_col: "",
                                "status": f"error:{e}",
                            }
                        )
                    if args.sleep_seconds > 0:
                        time.sleep(args.sleep_seconds)
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass
        out_f.close()

    print(args.out)


if __name__ == "__main__":
    main()
