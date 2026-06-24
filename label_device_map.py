import csv
from collections import defaultdict
import os
from typing import Optional

import mysql.connector


def connect_sensordata_db(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
):
    """Return a MySQL connection to the sensordata database."""
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
        read_timeout=60,
    )


def main():
    conn = connect_sensordata_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT device_id, data->>'$.label' AS label
            FROM aware_device
            WHERE data->>'$.label' IS NOT NULL
              AND data->>'$.label' != '';
            """
        )
        label_to_devices = defaultdict(set)
        for device_id, label in cur.fetchall():
            if label is None:
                continue
            label_to_devices[label].add(device_id)
    finally:
        cur.close()
        conn.close()

    out_path = "output/label_device_map.csv"
    os.makedirs("output", exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "device_ids"])
        for label in sorted(label_to_devices.keys()):
            devices = sorted(label_to_devices[label])
            writer.writerow([label, ";".join(devices)])

    print(out_path)
    print(f"Labels found: {len(label_to_devices)}")


if __name__ == "__main__":
    main()
