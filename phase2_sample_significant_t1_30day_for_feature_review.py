from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db
from phase2_sample_table_exploratory_t1_week_for_feature_review import (
    TZ,
    get_tables,
    load_device_map,
    load_ranked_patients,
    ms_to_local,
    parse_json,
    safe_ident,
    sanitize_row,
    sanitize_value,
    value_type,
)


ROOT = Path(__file__).parent
TABLE_NAME = "significant"
OUT_DIR = ROOT / "output/analysis_candidates/phase2_feature_review/significant"
SAMPLE_LIMIT = 20
MIN_ROWS = 20


def local_to_ms(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def count_rows(conn, quoted_table: str, device_id: str, start_ms: int, end_ms: int) -> dict[str, Any]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"""
            SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM {quoted_table}
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        return cur.fetchone() or {"n_rows": 0, "first_ts": None, "last_ts": None}
    finally:
        cur.close()


def sample_rows(conn, quoted_table: str, device_id: str, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"""
            SELECT *
            FROM {quoted_table}
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT %s
            """,
            (device_id, int(start_ms), int(end_ms), SAMPLE_LIMIT),
        )
        return cur.fetchall()
    finally:
        cur.close()


def t1_30day_window(patient: pd.Series) -> dict[str, Any]:
    start = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize(TZ)
    end = start + pd.Timedelta(days=30)
    return {
        "window_start": start,
        "window_end": end,
        "window_start_ms": local_to_ms(start),
        "window_end_ms": local_to_ms(end),
        "window_start_local": start.strftime("%Y-%m-%d %H:%M:%S%z"),
        "window_end_local": end.strftime("%Y-%m-%d %H:%M:%S%z"),
    }


def find_window(conn, quoted_table: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    ranked = load_ranked_patients()
    ranked = ranked[ranked["Subject_ID_D"].astype(str) != "001"].copy()
    device_map = load_device_map()
    coverage_rows: list[dict[str, Any]] = []

    for _, patient in ranked.iterrows():
        subject_id = str(patient["Subject_ID_D"])
        device_ids = device_map.get(subject_id, [])
        if not device_ids:
            continue
        window = t1_30day_window(patient)
        print(f"patient={subject_id} global_T1={patient.get('global_T1', '')} devices={len(device_ids)}", flush=True)
        device_counts = []
        for device_id in device_ids:
            row = count_rows(conn, quoted_table, device_id, window["window_start_ms"], window["window_end_ms"])
            n_rows = int(row.get("n_rows") or 0)
            coverage_rows.append(
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": device_id,
                    "window_rule": "rd_t1_to_t1_plus_30_days",
                    "window_start_ms": window["window_start_ms"],
                    "window_end_ms": window["window_end_ms"],
                    "window_start_local": window["window_start_local"],
                    "window_end_local": window["window_end_local"],
                    "n_rows": n_rows,
                    "first_ts": row.get("first_ts"),
                    "last_ts": row.get("last_ts"),
                    "first_local": ms_to_local(row.get("first_ts")),
                    "last_local": ms_to_local(row.get("last_ts")),
                }
            )
            device_counts.append((n_rows, device_id, row))
        device_counts = sorted(device_counts, reverse=True, key=lambda item: item[0])
        if device_counts and device_counts[0][0] >= MIN_ROWS:
            n_rows, device_id, row = device_counts[0]
            selected = {
                "Subject_ID_D": subject_id,
                "Subject_ID_N": patient.get("Subject_ID_N", ""),
                "global_T1": patient.get("global_T1", ""),
                "T1_date_iso": patient.get("T1_date_iso", ""),
                "device_id": device_id,
                "window_rule": "rd_t1_to_t1_plus_30_days",
                "window_start_ms": window["window_start_ms"],
                "window_end_ms": window["window_end_ms"],
                "window_start_local": window["window_start_local"],
                "window_end_local": window["window_end_local"],
                "n_rows_in_window": n_rows,
                "first_ts": row.get("first_ts"),
                "last_ts": row.get("last_ts"),
                "first_local": ms_to_local(row.get("first_ts")),
                "last_local": ms_to_local(row.get("last_ts")),
            }
            return selected, coverage_rows
    return None, coverage_rows


def write_outputs(window: dict[str, Any] | None, coverage_rows: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample_path = OUT_DIR / "significant_rd_t1_30day_sample_rows.csv"
    expanded_path = OUT_DIR / "significant_rd_t1_30day_sample_rows_expanded.csv"
    jsonl_path = OUT_DIR / "significant_rd_t1_30day_sample_rows.jsonl"
    keys_path = OUT_DIR / "significant_rd_t1_30day_json_key_summary.csv"
    coverage_path = OUT_DIR / "significant_rd_t1_30day_coverage_scan.csv"
    readme_path = OUT_DIR / "README_significant_rd_t1_30day_review.md"

    sample_out = []
    expanded_out = []
    key_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for index, row in enumerate(rows, start=1):
        out = sanitize_row(dict(row))
        out["sample_index"] = index
        out["local_datetime"] = ms_to_local(row.get("timestamp"))
        sample_out.append(out)

        obj = parse_json(row.get("data"))
        expanded = {
            "sample_index": index,
            "_id": row.get("_id"),
            "timestamp": row.get("timestamp"),
            "local_datetime": out["local_datetime"],
            "device_id": row.get("device_id"),
            "sample_context": "rd_t1_30day_manual_review_sample_not_phase2a_protocol",
        }
        if obj:
            for key, value in obj.items():
                key_counts[str(key)][value_type(value)] += 1
                expanded[str(key)] = sanitize_value(key, value)
        expanded_out.append(expanded)

    pd.DataFrame(sample_out).to_csv(sample_path, index=False)
    pd.DataFrame(expanded_out).to_csv(expanded_path, index=False)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in sample_out:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    pd.DataFrame(
        [
            {
                "json_key": key,
                "n_rows_with_key": sum(counts.values()),
                "value_type_counts": "; ".join(f"{k}:{v}" for k, v in sorted(counts.items())),
            }
            for key, counts in sorted(key_counts.items())
        ]
    ).to_csv(keys_path, index=False)
    pd.DataFrame(coverage_rows).to_csv(coverage_path, index=False)

    if window:
        window_text = f"""
- Subject_ID_D: `{window['Subject_ID_D']}`
- Subject_ID_N: `{window['Subject_ID_N']}`
- global_T1: `{window['global_T1']}`
- T1_date_iso: `{window['T1_date_iso']}`
- device_id: `{window['device_id']}`
- window_rule: `{window['window_rule']}`
- window_start_local: `{window['window_start_local']}`
- window_end_local: `{window['window_end_local']}`
- n_rows_in_window: `{window['n_rows_in_window']}`
- first_local: `{window['first_local']}`
- last_local: `{window['last_local']}`
"""
    else:
        window_text = "\nNo mapped ranked patient had at least 20 rows between T1 and T1+30 days.\n"

    readme_path.write_text(
        f"""# significant R&D T1-to-30-Day Review

This is an R&D manual-review scan for `significant`.

It is not the standard Phase 2A protocol. The standard Phase 2A T1-week scan found no rows. This scan tests whether a broader bounded window, T1 to T1+30 days, can provide a manual inspection sample.

Safety rules used:

- SQL filtered by mapped `device_id`
- SQL filtered by timestamp from T1 to T1+30 days
- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- no feature extraction
- no aggregation beyond bounded row counts
- sample limited to first 20 chronological rows

Selected R&D review window:
{window_text}
Files:

- `{sample_path.name}`
- `{expanded_path.name}`
- `{jsonl_path.name}`
- `{keys_path.name}`
- `{coverage_path.name}`

This is for manual feature review only. Missing data is not zero activity.
""",
        encoding="utf-8",
    )
    return [sample_path, expanded_path, jsonl_path, keys_path, coverage_path, readme_path]


def main() -> None:
    conn = connect_sensordata_db()
    try:
        whitelist = get_tables(conn)
        quoted_table = safe_ident(TABLE_NAME, whitelist)
        window, coverage_rows = find_window(conn, quoted_table)
        rows = (
            sample_rows(conn, quoted_table, window["device_id"], window["window_start_ms"], window["window_end_ms"])
            if window
            else []
        )
    finally:
        conn.close()

    paths = write_outputs(window, coverage_rows, rows)
    print(f"table_name: {TABLE_NAME}")
    print("scan_rule: rd_t1_to_t1_plus_30_days")
    print(f"sampled_rows: {len(rows)}")
    if window:
        print(pd.DataFrame([window]).to_string(index=False))
    else:
        print("no_t1_30day_review_window_found")
    print("generated files:")
    for path in paths:
        print(f"- {path}")


if __name__ == "__main__":
    main()
