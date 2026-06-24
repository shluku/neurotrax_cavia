import csv
import os
import time
import mysql.connector

DEVICE_ID = "877c14a8-9ab8-48d4-8fe3-ad3df98c3750"
OUT_CSV = "last_5_minutes_accelerometer.csv"

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "sensordata"),
}

# We search for the latest row within a constrained time window
# so MySQL can use the (timestamp, device_id) index efficiently.
FIND_LAST_LOOKBACK_SECONDS = 6 * 60 * 60   # 6 hours (safe), still uses timestamp prefix well
LAST_WINDOW_SECONDS = 5 * 60               # 5 minutes
CHUNK_SIZE = 5000


def main():
    if not DB_CONFIG["host"] or not DB_CONFIG["user"] or not DB_CONFIG["password"]:
        raise RuntimeError("Set DB_HOST, DB_USER, and DB_PASSWORD before connecting to SensorDB.")
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True, buffered=False)

    try:
        now_ts = time.time()
        t_min = now_ts - FIND_LAST_LOOKBACK_SECONDS

        # 1) Find last timestamp for the device, but ONLY inside last X hours
        cur.execute(
            """
            SELECT timestamp
            FROM accelerometer
            WHERE timestamp >= %s
              AND device_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (t_min, DEVICE_ID),
        )
        row = cur.fetchone()
        if not row or row.get("timestamp") is None:
            print("No data found for this device in the last lookback window.")
            return

        last_ts = float(row["timestamp"])
        start_ts = last_ts - LAST_WINDOW_SECONDS
        end_ts = last_ts  # inclusive-ish; we use <= by using < end_ts+epsilon if needed

        print(f"Last ts: {last_ts}")
        print(f"Exporting last 5 minutes: [{start_ts}, {end_ts}] (unix seconds)")

        # 2) Export last 5 minutes (uses index prefix timestamp range + device_id)
        cur.execute(
            """
            SELECT timestamp, device_id, data
            FROM accelerometer
            WHERE timestamp >= %s
              AND timestamp <= %s
              AND device_id = %s
            ORDER BY timestamp ASC
            """,
            (start_ts, end_ts, DEVICE_ID),
        )

        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "device_id", "data"])
            writer.writeheader()

            total = 0
            while True:
                batch = cur.fetchmany(CHUNK_SIZE)
                if not batch:
                    break
                writer.writerows(batch)
                total += len(batch)

        print(f"Done. Wrote {total} rows to {OUT_CSV}")

    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
