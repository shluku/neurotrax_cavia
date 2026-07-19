import csv
import os
from pathlib import Path
from typing import Optional

import mysql.connector


def load_local_env(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE pairs from a local .env file if present."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def connect_sensordata_db(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
):
    """Return a MySQL connection to the sensordata database."""
    load_local_env()
    resolved_host = host or os.getenv("DB_HOST")
    resolved_database = database or os.getenv("DB_NAME", "sensordata")
    resolved_user = user or os.getenv("DB_USER")
    resolved_password = password or os.getenv("DB_PASSWORD")
    if not resolved_host or not resolved_user or not resolved_password:
        raise RuntimeError(
            "Missing SensorDB connection settings. Set DB_HOST, DB_USER, and DB_PASSWORD "
            "in your environment before connecting."
        )
    return mysql.connector.connect(
        host=resolved_host,
        port=port or int(os.getenv("DB_PORT", "3306")),
        database=resolved_database,
        user=resolved_user,
        password=resolved_password,
        connection_timeout=10,
        read_timeout=120,
    )


def export_accelerometer(
    device_id: str,
    start_ts_ms: int,
    days: int = 2,
    chunk_ms: int = 600_000,
    out_dir: Optional[Path] = None,
):
    """Export accelerometer rows in small time chunks to avoid large scans."""
    out_dir = out_dir or Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"accelerometer_{device_id}_{days}days.csv"

    end_ts_ms = start_ts_ms + days * 86_400_000
    query = (
        "SELECT timestamp, device_id, "
        "data->>'$.double_values_0' AS x, "
        "data->>'$.double_values_1' AS y, "
        "data->>'$.double_values_2' AS z "
        "FROM accelerometer "
        "WHERE timestamp >= %s AND timestamp < %s AND device_id = %s "
        "ORDER BY timestamp"
    )

    conn = connect_sensordata_db()
    try:
        cur = conn.cursor()
        with out_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "device_id", "x", "y", "z"])
            t = start_ts_ms
            while t < end_ts_ms:
                t_next = min(t + chunk_ms, end_ts_ms)
                cur.execute(query, (t, t_next, device_id))
                while True:
                    rows = cur.fetchmany(10_000)
                    if not rows:
                        break
                    writer.writerows(rows)
                print(f"Wrote chunk {t} -> {t_next}")
                t = t_next
    finally:
        cur.close()
        conn.close()

    print(out_path)


def main():
    # Device + time window (ms timestamps)
    device_id = "fdce7e53-e549-45b0-a477-8c300329c656"
    start_ts_ms = 1752132145714
    export_accelerometer(device_id, start_ts_ms, days=2, chunk_ms=600_000)


if __name__ == "__main__":
    main()
