from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


TZ = "Asia/Jerusalem"
ROOT = Path(__file__).parent
OUT_ROOT = ROOT / "output/analysis_candidates/phase2_feature_review"
COGNITIVE_CANDIDATES_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
LABEL_DEVICE_MAP_PATH = ROOT / "output/label_device_map.csv"
SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")
EXCLUDED_EXPLORATORY_SUBJECTS = {"001"}


def normalize_subject_id_d(value: Any) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    return s.zfill(3) if s.isdigit() else s


def safe_ident(table_name: str, whitelist: set[str]) -> str:
    if table_name not in whitelist or not SAFE_TABLE_RE.match(table_name):
        raise ValueError(f"unsafe_or_unknown_table_name:{table_name}")
    return f"`{table_name}`"


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


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def ms_to_local(ms: Any) -> str:
    ts = pd.to_numeric(ms, errors="coerce")
    if pd.isna(ts):
        return ""
    return pd.to_datetime(int(ts), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d %H:%M:%S%z")


def local_to_ms(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def get_tables(conn) -> set[str]:
    cur = conn.cursor()
    try:
        cur.execute("SHOW TABLES")
        return {str(row[0]) for row in cur.fetchall()}
    finally:
        cur.close()


def get_columns(conn, table_name: str, whitelist: set[str]) -> list[str]:
    cur = conn.cursor()
    try:
        cur.execute(f"SHOW COLUMNS FROM {safe_ident(table_name, whitelist)}")
        return [str(row[0]) for row in cur.fetchall()]
    finally:
        cur.close()


def load_ranked_patients() -> pd.DataFrame:
    df = pd.read_csv(COGNITIVE_CANDIDATES_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id_d)
    df["global_T1_num"] = pd.to_numeric(df["global_T1"], errors="coerce")
    df = df.dropna(subset=["Subject_ID_D", "global_T1_num", "T1_date_iso"]).copy()
    df = df[~df["Subject_ID_D"].isin(EXCLUDED_EXPLORATORY_SUBJECTS)].copy()
    return df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True])


def load_device_map() -> dict[str, list[str]]:
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    out: dict[str, list[str]] = {}
    for _, row in label_map.iterrows():
        subject_id = normalize_subject_id_d(row.get("label"))
        raw = str(row.get("device_ids", ""))
        out[subject_id] = [x.strip() for x in raw.split(";") if x.strip() and x.strip().lower() != "nan"]
    return out


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


def first_existing_between(conn, quoted_table: str, device_id: str, start_ms: int, latest_start_ms: int) -> int | None:
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT timestamp
            FROM {quoted_table}
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


def candidate_windows_for_patient(patient: pd.Series, hours: int) -> dict[str, Any]:
    t1_date = pd.Timestamp(str(patient["T1_date_iso"])).tz_localize(TZ)
    week_start = t1_date
    week_end = week_start + pd.Timedelta(days=7)
    primary_start = t1_date + pd.Timedelta(days=1)
    primary_end = primary_start + pd.Timedelta(hours=hours)
    latest_fallback_start = week_end - pd.Timedelta(hours=hours)
    return {
        "week_start": week_start,
        "week_end": week_end,
        "primary_start": primary_start,
        "primary_end": primary_end,
        "latest_fallback_start": latest_fallback_start,
        "week_start_ms": local_to_ms(week_start),
        "week_end_ms": local_to_ms(week_end),
        "primary_start_ms": local_to_ms(primary_start),
        "primary_end_ms": local_to_ms(primary_end),
        "latest_fallback_start_ms": local_to_ms(latest_fallback_start),
    }


def find_review_window(conn, quoted_table: str, ranked: pd.DataFrame, device_map: dict[str, list[str]], hours: int, min_rows: int):
    coverage_rows = []
    for _, patient in ranked.iterrows():
        subject_id = patient["Subject_ID_D"]
        device_ids = device_map.get(subject_id, [])
        if not device_ids:
            continue
        print(f"patient={subject_id} global_T1={patient.get('global_T1', '')} devices={len(device_ids)}", flush=True)
        windows = candidate_windows_for_patient(patient, hours)

        primary_counts = []
        for device_id in device_ids:
            row = count_rows(conn, quoted_table, device_id, windows["primary_start_ms"], windows["primary_end_ms"])
            n_rows = int(row.get("n_rows") or 0)
            coverage_rows.append(
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": device_id,
                    "window_candidate": "primary_day_after_T1",
                    "window_start_ms": windows["primary_start_ms"],
                    "window_end_ms": windows["primary_end_ms"],
                    "window_start_local": windows["primary_start"].strftime("%Y-%m-%d %H:%M:%S%z"),
                    "window_end_local": windows["primary_end"].strftime("%Y-%m-%d %H:%M:%S%z"),
                    "n_rows": n_rows,
                    "first_ts": row.get("first_ts"),
                    "last_ts": row.get("last_ts"),
                    "first_local": ms_to_local(row.get("first_ts")),
                    "last_local": ms_to_local(row.get("last_ts")),
                }
            )
            primary_counts.append((n_rows, device_id, row))

        primary_counts = sorted(primary_counts, key=lambda x: x[0], reverse=True)
        if primary_counts and primary_counts[0][0] >= min_rows:
            n_rows, device_id, row = primary_counts[0]
            return (
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": device_id,
                    "window_rule": "exploratory_primary_day_after_T1",
                    "window_start_ms": windows["primary_start_ms"],
                    "window_end_ms": windows["primary_end_ms"],
                    "window_start_local": windows["primary_start"].strftime("%Y-%m-%d %H:%M:%S%z"),
                    "window_end_local": windows["primary_end"].strftime("%Y-%m-%d %H:%M:%S%z"),
                    "n_rows_in_window": n_rows,
                    "first_ts": row.get("first_ts"),
                    "last_ts": row.get("last_ts"),
                },
                coverage_rows,
            )

        fallback_candidates = []
        for device_id in device_ids:
            first_ts = first_existing_between(
                conn,
                quoted_table,
                device_id,
                windows["week_start_ms"],
                windows["latest_fallback_start_ms"],
            )
            coverage_rows.append(
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": device_id,
                    "window_candidate": "fallback_first_24h_span_within_T1_week_lookup",
                    "window_start_ms": windows["week_start_ms"],
                    "window_end_ms": windows["week_end_ms"],
                    "window_start_local": windows["week_start"].strftime("%Y-%m-%d %H:%M:%S%z"),
                    "window_end_local": windows["week_end"].strftime("%Y-%m-%d %H:%M:%S%z"),
                    "latest_allowed_fallback_start_ms": windows["latest_fallback_start_ms"],
                    "latest_allowed_fallback_start_local": windows["latest_fallback_start"].strftime("%Y-%m-%d %H:%M:%S%z"),
                    "n_rows": 1 if first_ts is not None else 0,
                    "first_ts": first_ts,
                    "last_ts": first_ts,
                    "first_local": ms_to_local(first_ts),
                    "last_local": ms_to_local(first_ts),
                }
            )
            if first_ts is not None:
                fallback_candidates.append((first_ts, device_id))

        if fallback_candidates:
            first_ts, device_id = sorted(fallback_candidates, key=lambda x: x[0])[0]
            start = pd.to_datetime(first_ts, unit="ms", utc=True).tz_convert(TZ)
            end = start + pd.Timedelta(hours=hours)
            start_ms = int(first_ts)
            end_ms = local_to_ms(end)
            row = count_rows(conn, quoted_table, device_id, start_ms, end_ms)
            n_rows = int(row.get("n_rows") or 0)
            if n_rows >= min_rows:
                return (
                    {
                        "Subject_ID_D": subject_id,
                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                        "global_T1": patient.get("global_T1", ""),
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                        "device_id": device_id,
                        "window_rule": "exploratory_fallback_first_24h_span_within_T1_week",
                        "window_start_ms": start_ms,
                        "window_end_ms": end_ms,
                        "window_start_local": start.strftime("%Y-%m-%d %H:%M:%S%z"),
                        "window_end_local": end.strftime("%Y-%m-%d %H:%M:%S%z"),
                        "n_rows_in_window": n_rows,
                        "first_ts": row.get("first_ts"),
                        "last_ts": row.get("last_ts"),
                    },
                    coverage_rows,
                )
    return None, coverage_rows


def sample_rows(conn, quoted_table: str, window: dict[str, Any], sample_limit: int) -> list[dict[str, Any]]:
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
            (
                str(window["device_id"]),
                int(window["window_start_ms"]),
                int(window["window_end_ms"]),
                int(sample_limit),
            ),
        )
        return cur.fetchall()
    finally:
        cur.close()


def write_outputs(table_name: str, columns: list[str], window: dict[str, Any] | None, coverage_rows, rows: list[dict[str, Any]]) -> list[Path]:
    out_dir = OUT_ROOT / table_name
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_path = out_dir / f"{table_name}_sample_rows.csv"
    expanded_path = out_dir / f"{table_name}_sample_rows_expanded.csv"
    jsonl_path = out_dir / f"{table_name}_sample_rows.jsonl"
    keys_path = out_dir / f"{table_name}_json_key_summary.csv"
    coverage_path = out_dir / f"{table_name}_phase2a_t1_ranked_coverage_scan.csv"
    readme_path = out_dir / f"README_{table_name}_feature_review.md"

    sample_out = []
    expanded_out = []
    key_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for index, row in enumerate(rows, start=1):
        out = dict(row)
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
            "sample_context": "phase2a_t1_ranked_24h_t1_week_review_sample",
        }
        if obj:
            for key, value in obj.items():
                key_counts[str(key)][value_type(value)] += 1
                expanded[str(key)] = value
        expanded_out.append(expanded)

    pd.DataFrame(sample_out).to_csv(sample_path, index=False)
    pd.DataFrame(expanded_out).to_csv(expanded_path, index=False)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in sample_out:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    key_rows = [
        {
            "json_key": key,
            "n_rows_with_key": sum(counts.values()),
            "value_type_counts": "; ".join(f"{k}:{v}" for k, v in sorted(counts.items())),
        }
        for key, counts in sorted(key_counts.items())
    ]
    pd.DataFrame(key_rows).to_csv(keys_path, index=False)
    pd.DataFrame(coverage_rows).to_csv(coverage_path, index=False)

    if window:
        window_text = f"""Selected review window:

- Subject_ID_D: `{window['Subject_ID_D']}`
- Subject_ID_N: `{window['Subject_ID_N']}`
- global_T1: `{window['global_T1']}`
- T1_date_iso: `{window['T1_date_iso']}`
- device_id: `{window['device_id']}`
- window_rule: `{window['window_rule']}`
- window_start_local: `{window['window_start_local']}`
- window_end_local: `{window['window_end_local']}`
- n_rows_in_window: `{window['n_rows_in_window']}`
"""
    else:
        window_text = "No protocol-valid review window with enough rows was found.\n"

    readme_path.write_text(
        f"""# {table_name} Phase 2A Feature Review Sample

This folder contains a Phase 2A manual-review sample for `{table_name}`.

Current Phase 2A review search:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: 24 hours starting local midnight day after T1
- fallback: first complete 24-hour span inside T1 week
- SQL always filtered by `device_id` and `timestamp`

{window_text}
Files:

- `{sample_path.name}`
- `{expanded_path.name}`
- `{jsonl_path.name}`
- `{keys_path.name}`
- `{coverage_path.name}`

This is manual feature review only. It is not diagnostic, not confirmatory, and missing data is not zero activity.
""",
        encoding="utf-8",
    )
    return [sample_path, expanded_path, jsonl_path, keys_path, coverage_path, readme_path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2A T1-ranked T1-week bounded table sampler.")
    parser.add_argument("table_name")
    parser.add_argument("--sample-limit", type=int, default=20)
    parser.add_argument("--min-rows", type=int, default=20)
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()

    conn = connect_sensordata_db()
    try:
        whitelist = get_tables(conn)
        quoted_table = safe_ident(args.table_name, whitelist)
        columns = get_columns(conn, args.table_name, whitelist)
        missing_cols = {"device_id", "timestamp"} - set(columns)
        if missing_cols:
            raise SystemExit(f"{args.table_name} missing required columns: {sorted(missing_cols)}")
        ranked = load_ranked_patients()
        device_map = load_device_map()
        window, coverage_rows = find_review_window(conn, quoted_table, ranked, device_map, args.hours, args.min_rows)
        rows = sample_rows(conn, quoted_table, window, args.sample_limit) if window else []
    finally:
        conn.close()

    paths = write_outputs(args.table_name, columns, window, coverage_rows, rows)
    print(f"table_name: {args.table_name}")
    print(f"sampled_rows: {len(rows)}")
    if window:
        print(pd.DataFrame([window]).to_string(index=False))
    else:
        print("no_protocol_valid_review_window_found")
    print("generated files:")
    for path in paths:
        print(f"- {path}")


if __name__ == "__main__":
    main()
