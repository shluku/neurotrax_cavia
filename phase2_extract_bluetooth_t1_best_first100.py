from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


TZ = "Asia/Jerusalem"
COGNITIVE_CANDIDATES = Path("output/analysis_candidates/cognitive_candidates_all.csv")
LABEL_DEVICE_MAP = Path("output/label_device_map.csv")
OUT_DIR = Path("output/analysis_candidates/phase2_feature_review/bluetooth")


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


def ms_to_local(ms: int | float | None) -> str:
    if ms is None or pd.isna(ms):
        return ""
    return pd.to_datetime(int(ms), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z")


def load_ranked_patients() -> pd.DataFrame:
    df = pd.read_csv(COGNITIVE_CANDIDATES, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id_d)
    df["global_T1_num"] = pd.to_numeric(df["global_T1"], errors="coerce")
    df = df.dropna(subset=["Subject_ID_D", "global_T1_num"]).copy()
    return df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True])


def load_device_map() -> dict[str, list[str]]:
    label_map = pd.read_csv(LABEL_DEVICE_MAP, dtype=str)
    out: dict[str, list[str]] = {}
    for _, row in label_map.iterrows():
        subject_id = normalize_subject_id_d(row.get("label"))
        raw = str(row.get("device_ids", ""))
        out[subject_id] = [x.strip() for x in raw.split(";") if x.strip() and x.strip().lower() != "nan"]
    return out


def device_bluetooth_coverage(conn, device_id: str) -> tuple[int, int | None, int | None]:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM `bluetooth`
            WHERE device_id = %s
            """,
            (device_id,),
        )
        n_rows, first_ts, last_ts = cur.fetchone()
        return int(n_rows or 0), int(first_ts) if first_ts is not None else None, int(last_ts) if last_ts is not None else None
    finally:
        cur.close()


def fetch_first_rows(conn, device_id: str, limit: int = 100) -> list[dict[str, Any]]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT _id, timestamp, device_id, data
            FROM `bluetooth`
            WHERE device_id = %s
            ORDER BY timestamp ASC
            LIMIT %s
            """,
            (device_id, int(limit)),
        )
        return cur.fetchall()
    finally:
        cur.close()


def expand_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    expanded = []
    distinct = []
    seen = set()
    parse_errors = 0
    for i, row in enumerate(rows, start=1):
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1
            obj = {}
        rec = {
            "sample_index": i,
            "_id": row.get("_id"),
            "timestamp": int(float(row.get("timestamp"))),
            "local_datetime": ms_to_local(row.get("timestamp")),
            "device_id": row.get("device_id"),
            "label": obj.get("label"),
            "bt_name": obj.get("bt_name"),
            "bt_rssi": obj.get("bt_rssi"),
            "bt_address": obj.get("bt_address"),
        }
        expanded.append(rec)
        key = (
            str(row.get("timestamp")),
            str(row.get("device_id")),
            str(obj.get("bt_address")),
            str(obj.get("bt_rssi")),
        )
        if key in seen:
            continue
        seen.add(key)
        distinct_rec = dict(rec)
        distinct_rec["distinct_observation_index"] = len(distinct) + 1
        distinct_rec["dedup_key"] = "timestamp+device_id+bt_address+bt_rssi"
        distinct.append(distinct_rec)
    return expanded, distinct, parse_errors


def compute_features(distinct_rows: list[dict[str, Any]]) -> dict[str, Any]:
    addresses = [str(row.get("bt_address")).strip() for row in distinct_rows if str(row.get("bt_address", "")).strip()]
    if not addresses:
        return {
            "unique_bluetooth_addresses": pd.NA,
            "bluetooth_address_diversity_ratio": pd.NA,
        }
    unique_addresses = len(set(addresses))
    return {
        "unique_bluetooth_addresses": unique_addresses,
        "bluetooth_address_diversity_ratio": unique_addresses / len(addresses),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ranked = load_ranked_patients()
    device_map = load_device_map()

    conn = connect_sensordata_db()
    coverage_rows = []
    chosen = None
    try:
        for _, patient in ranked.iterrows():
            subject_id = patient["Subject_ID_D"]
            for device_id in device_map.get(subject_id, []):
                n_rows, first_ts, last_ts = device_bluetooth_coverage(conn, device_id)
                coverage_rows.append(
                    {
                        "Subject_ID_D": subject_id,
                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                        "global_T1": patient.get("global_T1", ""),
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                        "device_id": device_id,
                        "bluetooth_rows": n_rows,
                        "first_ts": first_ts,
                        "last_ts": last_ts,
                        "first_local": ms_to_local(first_ts),
                        "last_local": ms_to_local(last_ts),
                    }
                )
                if n_rows >= 100 and chosen is None:
                    chosen = {
                        "Subject_ID_D": subject_id,
                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                        "global_T1": patient.get("global_T1", ""),
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                        "device_id": device_id,
                        "bluetooth_rows": n_rows,
                        "first_ts": first_ts,
                        "last_ts": last_ts,
                    }
                    break
            if chosen is not None:
                break

        if chosen is None:
            rows = []
        else:
            rows = fetch_first_rows(conn, chosen["device_id"], 100)
    finally:
        conn.close()

    expanded, distinct, parse_errors = expand_rows(rows)
    features = compute_features(distinct)

    pd.DataFrame(coverage_rows).to_csv(OUT_DIR / "bluetooth_t1_ranked_device_coverage.csv", index=False)
    pd.DataFrame(expanded).to_csv(OUT_DIR / "bluetooth_t1_best_first100_rows_expanded.csv", index=False)
    pd.DataFrame(distinct).to_csv(OUT_DIR / "bluetooth_t1_best_first100_distinct_observations.csv", index=False)

    result = {
        "table_name": "bluetooth",
        "sample_context": "t1_best_patient_with_at_least_100_bluetooth_rows_first100",
        "Subject_ID_D": chosen.get("Subject_ID_D", "") if chosen else "",
        "Subject_ID_N": chosen.get("Subject_ID_N", "") if chosen else "",
        "global_T1": chosen.get("global_T1", "") if chosen else "",
        "T1_date_iso": chosen.get("T1_date_iso", "") if chosen else "",
        "device_id": chosen.get("device_id", "") if chosen else "",
        "rows_sampled": len(rows),
        "distinct_observation_count": len(distinct),
        "dedup_key": "timestamp+device_id+bt_address+bt_rssi",
        "first_local_datetime": expanded[0]["local_datetime"] if expanded else "",
        "last_local_datetime": expanded[-1]["local_datetime"] if expanded else "",
        "json_parse_errors": parse_errors,
        **features,
    }
    pd.DataFrame([result]).to_csv(OUT_DIR / "bluetooth_t1_best_first100_selected_feature_check.csv", index=False)

    print(pd.DataFrame([result]).to_string(index=False))
    print("generated files:")
    for path in [
        OUT_DIR / "bluetooth_t1_ranked_device_coverage.csv",
        OUT_DIR / "bluetooth_t1_best_first100_rows_expanded.csv",
        OUT_DIR / "bluetooth_t1_best_first100_distinct_observations.csv",
        OUT_DIR / "bluetooth_t1_best_first100_selected_feature_check.csv",
    ]:
        print(f"- {path}")


if __name__ == "__main__":
    main()
