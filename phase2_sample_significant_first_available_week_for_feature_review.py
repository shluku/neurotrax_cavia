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
WINDOW_DAYS = 7


def first_available_ts(conn, quoted_table: str, device_id: str) -> int | None:
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT timestamp
            FROM {quoted_table}
            WHERE device_id = %s
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (device_id,),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        cur.close()


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
        print(f"patient={subject_id} global_T1={patient.get('global_T1', '')} devices={len(device_ids)}", flush=True)
        candidates = []
        for device_id in device_ids:
            first_ts = first_available_ts(conn, quoted_table, device_id)
            if first_ts is None:
                coverage_rows.append(
                    {
                        "Subject_ID_D": subject_id,
                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                        "global_T1": patient.get("global_T1", ""),
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                        "device_id": device_id,
                        "window_rule": "adjusted_first_available_7d_lookup",
                        "first_available_ts": None,
                        "first_available_local": "",
                        "n_rows": 0,
                    }
                )
                continue
            start_ms = first_ts
            end_ms = int((pd.to_datetime(first_ts, unit="ms", utc=True) + pd.Timedelta(days=WINDOW_DAYS)).timestamp() * 1000)
            row = count_rows(conn, quoted_table, device_id, start_ms, end_ms)
            n_rows = int(row.get("n_rows") or 0)
            first_available_local = ms_to_local(first_ts)
            t1_date = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize(TZ)
            days_after_t1 = (
                pd.to_datetime(first_ts, unit="ms", utc=True).tz_convert(TZ).normalize() - t1_date.normalize()
            ).days
            coverage_rows.append(
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": device_id,
                    "window_rule": "adjusted_first_available_7d",
                    "first_available_ts": first_ts,
                    "first_available_local": first_available_local,
                    "days_first_available_after_T1": days_after_t1,
                    "window_start_ms": start_ms,
                    "window_end_ms": end_ms,
                    "window_start_local": first_available_local,
                    "window_end_local": ms_to_local(end_ms),
                    "n_rows": n_rows,
                    "first_ts": row.get("first_ts"),
                    "last_ts": row.get("last_ts"),
                    "first_local": ms_to_local(row.get("first_ts")),
                    "last_local": ms_to_local(row.get("last_ts")),
                }
            )
            candidates.append((first_ts, n_rows, device_id, row, days_after_t1, start_ms, end_ms))
        valid = [candidate for candidate in candidates if candidate[1] >= MIN_ROWS]
        if valid:
            first_ts, n_rows, device_id, row, days_after_t1, start_ms, end_ms = sorted(valid, key=lambda item: item[0])[0]
            return (
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": device_id,
                    "window_rule": "adjusted_first_available_7d",
                    "window_start_ms": start_ms,
                    "window_end_ms": end_ms,
                    "window_start_local": ms_to_local(start_ms),
                    "window_end_local": ms_to_local(end_ms),
                    "n_rows_in_window": n_rows,
                    "first_ts": row.get("first_ts"),
                    "last_ts": row.get("last_ts"),
                    "first_local": ms_to_local(row.get("first_ts")),
                    "last_local": ms_to_local(row.get("last_ts")),
                    "days_first_available_after_T1": days_after_t1,
                },
                coverage_rows,
            )
    return None, coverage_rows


def write_outputs(window: dict[str, Any] | None, coverage_rows: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample_path = OUT_DIR / "significant_adjusted_first_available_7d_sample_rows.csv"
    expanded_path = OUT_DIR / "significant_adjusted_first_available_7d_sample_rows_expanded.csv"
    jsonl_path = OUT_DIR / "significant_adjusted_first_available_7d_sample_rows.jsonl"
    keys_path = OUT_DIR / "significant_adjusted_first_available_7d_json_key_summary.csv"
    coverage_path = OUT_DIR / "significant_adjusted_first_available_7d_coverage_scan.csv"
    readme_path = OUT_DIR / "README_significant_adjusted_first_available_7d_review.md"

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
            "sample_context": "adjusted_first_available_7d_manual_review_sample_not_T1_baseline",
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
- days_first_available_after_T1: `{window['days_first_available_after_T1']}`
"""
    else:
        window_text = "\nNo mapped ranked patient had at least 20 rows in the first 7 days after their first available `significant` timestamp.\n"

    readme_path.write_text(
        f"""# significant Adjusted First-Available 7-Day Review

This is a table-specific adjusted Phase 2A review for `significant`.

The standard T1-week and T1+30-day scans found no rows. This adjusted review finds the first available `significant` timestamp for each ranked mapped patient/device and samples the first 7 days from that point.

This is not a T1 baseline acquisition window. It is delayed first-available table analysis, useful for understanding and potentially extracting `significant` features separately from baseline T1 digital phenotyping.

Safety rules used:

- SQL filtered by mapped `device_id`
- SQL filtered by timestamp for a bounded 7-day window
- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- no feature extraction
- sample limited to first 20 chronological rows

Selected adjusted review window:
{window_text}
Files:

- `{sample_path.name}`
- `{expanded_path.name}`
- `{jsonl_path.name}`
- `{keys_path.name}`
- `{coverage_path.name}`

Missing data is not zero activity. This review is exploratory and not diagnostic.
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
    print("scan_rule: adjusted_first_available_7d")
    print(f"sampled_rows: {len(rows)}")
    if window:
        print(pd.DataFrame([window]).to_string(index=False))
    else:
        print("no_adjusted_first_available_7d_review_window_found")
    print("generated files:")
    for path in paths:
        print(f"- {path}")


if __name__ == "__main__":
    main()
