from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


TZ = "Asia/Jerusalem"
OUT_DIR = Path("output/analysis_candidates/phase2_feature_extraction/bluetooth_highest_t1_36h")
COGNITIVE_CANDIDATES = Path("output/analysis_candidates/cognitive_candidates_all.csv")
LABEL_DEVICE_MAP = Path("output/label_device_map.csv")


def normalize_subject_id_d(value: Any) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    return s.zfill(3) if s.isdigit() else s


def parse_json(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def local_to_ms(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def ms_to_local(ms: int | float | None) -> str:
    if ms is None or pd.isna(ms):
        return ""
    return pd.to_datetime(int(ms), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z")


def get_highest_t1_patient() -> pd.Series:
    df = pd.read_csv(COGNITIVE_CANDIDATES, dtype={"Subject_ID_D": str})
    df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id_d)
    df["global_T1_num"] = pd.to_numeric(df["global_T1"], errors="coerce")
    df = df.dropna(subset=["Subject_ID_D", "global_T1_num", "T1_date_iso"]).copy()
    df = df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True])
    return df.iloc[0]


def get_device_ids(subject_id_d: str) -> list[str]:
    label_map = pd.read_csv(LABEL_DEVICE_MAP, dtype=str)
    label_map["label_norm"] = label_map["label"].map(normalize_subject_id_d)
    hit = label_map[label_map["label_norm"] == normalize_subject_id_d(subject_id_d)]
    if hit.empty:
        return []
    raw = str(hit.iloc[0].get("device_ids", ""))
    return [x.strip() for x in raw.split(";") if x.strip() and x.strip().lower() != "nan"]


def count_rows(conn, device_id: str, start_ms: int, end_ms: int) -> tuple[int, int | None, int | None]:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM `bluetooth`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        n_rows, first_ts, last_ts = cur.fetchone()
        return int(n_rows or 0), int(first_ts) if first_ts is not None else None, int(last_ts) if last_ts is not None else None
    finally:
        cur.close()


def first_existing_between(conn, device_id: str, start_ms: int, latest_start_ms: int) -> int | None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT timestamp
            FROM `bluetooth`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp <= %s
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (device_id, int(start_ms), int(latest_start_ms)),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        cur.close()


def fetch_rows(conn, device_id: str, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    cur = conn.cursor(dictionary=True)
    out: list[dict[str, Any]] = []
    try:
        cur.execute(
            """
            SELECT _id, timestamp, device_id, data
            FROM `bluetooth`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        while True:
            batch = cur.fetchmany(5000)
            if not batch:
                break
            out.extend(batch)
    finally:
        cur.close()
    return out


def distinct_observations(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen = set()
    out = []
    parse_errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            continue
        key = (
            str(row.get("timestamp")),
            str(row.get("device_id")),
            str(obj.get("bt_address")),
            str(obj.get("bt_rssi")),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "_id": row.get("_id"),
                "timestamp": row.get("timestamp"),
                "local_datetime": ms_to_local(row.get("timestamp")),
                "device_id": row.get("device_id"),
                "label": obj.get("label"),
                "bt_name": obj.get("bt_name"),
                "bt_rssi": obj.get("bt_rssi"),
                "bt_address": obj.get("bt_address"),
                "dedup_key": "timestamp+device_id+bt_address+bt_rssi",
            }
        )
    return out, parse_errors


def compute_features(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    distinct_rows, parse_errors = distinct_observations(rows)
    addresses = [str(row.get("bt_address")).strip() for row in distinct_rows if str(row.get("bt_address", "")).strip()]
    unique_addresses = len(set(addresses))

    if not distinct_rows:
        return (
            {
                "unique_bluetooth_addresses": pd.NA,
                "bluetooth_address_diversity_ratio": pd.NA,
                "bluetooth_raw_rows_in_window": len(rows),
                "bluetooth_distinct_observations": 0,
                "json_parse_errors": parse_errors,
                "feature_status": "insufficient_data_no_distinct_bluetooth_observations",
            },
            distinct_rows,
        )

    return (
        {
            "unique_bluetooth_addresses": unique_addresses,
            "bluetooth_address_diversity_ratio": unique_addresses / len(addresses) if addresses else pd.NA,
            "bluetooth_raw_rows_in_window": len(rows),
            "bluetooth_distinct_observations": len(distinct_rows),
            "json_parse_errors": parse_errors,
            "feature_status": "calculated",
        },
        distinct_rows,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract selected bluetooth features for highest global_T1 patient Phase B 24h window.")
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    patient = get_highest_t1_patient()
    subject_id_d = normalize_subject_id_d(patient["Subject_ID_D"])
    device_ids = get_device_ids(subject_id_d)
    if not device_ids:
        raise SystemExit(f"No mapped device_ids found for highest global_T1 subject {subject_id_d}")

    t1_date = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize(TZ)
    week_start = t1_date
    week_end = week_start + pd.Timedelta(days=7)
    latest_fallback_start = week_end - pd.Timedelta(hours=args.hours)
    primary_start = t1_date + pd.Timedelta(days=1)
    primary_end = primary_start + pd.Timedelta(hours=args.hours)
    week_start_ms = local_to_ms(week_start)
    week_end_ms = local_to_ms(week_end)
    latest_fallback_start_ms = local_to_ms(latest_fallback_start)
    primary_start_ms = local_to_ms(primary_start)
    primary_end_ms = local_to_ms(primary_end)

    conn = connect_sensordata_db()
    try:
        coverage_rows = []
        total_primary_rows = 0
        for device_id in device_ids:
            n_rows, first_ts, last_ts = count_rows(conn, device_id, primary_start_ms, primary_end_ms)
            total_primary_rows += n_rows
            coverage_rows.append(
                {
                    "Subject_ID_D": subject_id_d,
                    "Subject_ID_N": patient["Subject_ID_N"],
                    "device_id": device_id,
                    "window_candidate": "primary_day_after_T1",
                    "window_start_ms": primary_start_ms,
                    "window_end_ms": primary_end_ms,
                    "window_start_local": primary_start.strftime("%Y-%m-%d %H:%M:%S%z"),
                    "window_end_local": primary_end.strftime("%Y-%m-%d %H:%M:%S%z"),
                    "n_rows": n_rows,
                    "first_ts": first_ts,
                    "last_ts": last_ts,
                    "first_local": ms_to_local(first_ts),
                    "last_local": ms_to_local(last_ts),
                }
            )

        if total_primary_rows > 0:
            window_rule = "primary_day_after_T1"
            selected_start_ms = primary_start_ms
            selected_end_ms = primary_end_ms
            selected_start_local = primary_start.strftime("%Y-%m-%d %H:%M:%S%z")
            selected_end_local = primary_end.strftime("%Y-%m-%d %H:%M:%S%z")
        else:
            first_candidates = []
            for device_id in device_ids:
                first_ts = first_existing_between(conn, device_id, week_start_ms, latest_fallback_start_ms)
                coverage_rows.append(
                    {
                        "Subject_ID_D": subject_id_d,
                        "Subject_ID_N": patient["Subject_ID_N"],
                        "device_id": device_id,
                        "window_candidate": "fallback_first_24h_span_within_T1_week_lookup",
                        "window_start_ms": week_start_ms,
                        "window_end_ms": week_end_ms,
                        "window_start_local": week_start.strftime("%Y-%m-%d %H:%M:%S%z"),
                        "window_end_local": week_end.strftime("%Y-%m-%d %H:%M:%S%z"),
                        "latest_allowed_fallback_start_ms": latest_fallback_start_ms,
                        "latest_allowed_fallback_start_local": latest_fallback_start.strftime("%Y-%m-%d %H:%M:%S%z"),
                        "n_rows": 1 if first_ts is not None else 0,
                        "first_ts": first_ts,
                        "last_ts": first_ts,
                        "first_local": ms_to_local(first_ts),
                        "last_local": ms_to_local(first_ts),
                    }
                )
                if first_ts is not None:
                    first_candidates.append((first_ts, device_id))
            if not first_candidates:
                window_rule = "no_bluetooth_data_with_24h_span_in_T1_week"
                selected_start_ms = pd.NA
                selected_end_ms = pd.NA
                selected_start_local = ""
                selected_end_local = ""
            else:
                first_ts, selected_device = min(first_candidates)
                selected_start = pd.to_datetime(first_ts, unit="ms", utc=True).tz_convert(TZ)
                selected_end = selected_start + pd.Timedelta(hours=args.hours)
                selected_start_ms = int(first_ts)
                selected_end_ms = local_to_ms(selected_end)
                selected_start_local = selected_start.strftime("%Y-%m-%d %H:%M:%S%z")
                selected_end_local = selected_end.strftime("%Y-%m-%d %H:%M:%S%z")
                window_rule = "fallback_first_24h_span_within_T1_week"
                n_rows, coverage_first_ts, coverage_last_ts = count_rows(conn, selected_device, selected_start_ms, selected_end_ms)
                coverage_rows.append(
                    {
                        "Subject_ID_D": subject_id_d,
                        "Subject_ID_N": patient["Subject_ID_N"],
                        "device_id": selected_device,
                        "window_candidate": "fallback_first_24h_span_within_T1_week_selected",
                        "window_start_ms": selected_start_ms,
                        "window_end_ms": selected_end_ms,
                        "window_start_local": selected_start_local,
                        "window_end_local": selected_end_local,
                        "n_rows": n_rows,
                        "first_ts": coverage_first_ts,
                        "last_ts": coverage_last_ts,
                        "first_local": ms_to_local(coverage_first_ts),
                        "last_local": ms_to_local(coverage_last_ts),
                    }
                )

        rows = []
        if pd.notna(selected_start_ms) and pd.notna(selected_end_ms):
            for device_id in device_ids:
                rows.extend(fetch_rows(conn, device_id, int(selected_start_ms), int(selected_end_ms)))
        rows = sorted(rows, key=lambda r: (int(r["timestamp"]), str(r["device_id"])))
        features, distinct_rows = compute_features(rows)
    finally:
        conn.close()

    feature_row = {
        "Subject_ID_D": subject_id_d,
        "Subject_ID_N": patient["Subject_ID_N"],
        "global_T1": patient["global_T1"],
        "T1_date_iso": patient["T1_date_iso"],
        "n_device_ids_mapped": len(device_ids),
        "device_ids_used": ";".join(device_ids),
        "feature_table": "bluetooth",
        "window_rule": window_rule,
        "window_start_ms": selected_start_ms,
        "window_end_ms": selected_end_ms,
        "window_start_local": selected_start_local,
        "window_end_local": selected_end_local,
        **features,
    }

    features_path = OUT_DIR / "bluetooth_highest_t1_36h_features.csv"
    coverage_path = OUT_DIR / "bluetooth_highest_t1_36h_window_coverage.csv"
    rows_path = OUT_DIR / "bluetooth_highest_t1_36h_distinct_rows.csv"
    readme_path = OUT_DIR / "README_bluetooth_highest_t1_36h.md"

    pd.DataFrame([feature_row]).to_csv(features_path, index=False)
    pd.DataFrame(coverage_rows).to_csv(coverage_path, index=False)
    pd.DataFrame(distinct_rows).to_csv(rows_path, index=False)
    readme_path.write_text(
        f"""# bluetooth Highest-T1 Phase B 24h Selected Features

Selected features:

- `unique_bluetooth_addresses`
- `bluetooth_address_diversity_ratio`

Deduplication key:

```text
timestamp + device_id + bt_address + bt_rssi
```

Result:

- Subject_ID_D: `{subject_id_d}`
- global_T1: `{patient["global_T1"]}`
- window_rule: `{window_rule}`
- T1 week: `{week_start.strftime("%Y-%m-%d %H:%M:%S%z")}` to `{week_end.strftime("%Y-%m-%d %H:%M:%S%z")}`
- raw rows in selected window: `{features["bluetooth_raw_rows_in_window"]}`
- distinct observations: `{features["bluetooth_distinct_observations"]}`
- feature_status: `{features["feature_status"]}`

Missing data is not zero activity.
""",
        encoding="utf-8",
    )

    print(f"Subject_ID_D: {subject_id_d}")
    print(f"global_T1: {patient['global_T1']}")
    print(f"window_rule: {window_rule}")
    print(f"raw_rows: {features['bluetooth_raw_rows_in_window']}")
    print(f"distinct_observations: {features['bluetooth_distinct_observations']}")
    print(f"unique_bluetooth_addresses: {features['unique_bluetooth_addresses']}")
    print(f"bluetooth_address_diversity_ratio: {features['bluetooth_address_diversity_ratio']}")
    print("generated files:")
    for path in [features_path, coverage_path, rows_path, readme_path]:
        print(f"- {path}")


if __name__ == "__main__":
    main()
