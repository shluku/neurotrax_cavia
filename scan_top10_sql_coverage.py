import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

import mysql.connector
import pandas as pd

from main import connect_sensordata_db

TZ = "Asia/Jerusalem"
TABLES_TO_SCAN = [
    "aware_log",
    "battery",
    "screen",
    "wifi",
    "calls",
    "messages",
    "locations",
    "applications_foreground",
    "keyboard",
    "touch",
    "gsm",
    "gsm_neighbor",
    "telephony",
    "plugin_google_activity_recognition",
]
WINDOW_SPECS = [
    ("early_window", "early_window_start_ms", "early_window_end_ms", "early_window_start_iso", "early_window_end_iso"),
    ("late_window", "late_window_start_ms", "late_window_end_ms", "late_window_start_iso", "late_window_end_iso"),
    ("full_T1_T2_window", "T1_start_ms", "T2_end_ms", "T1_date_iso", "T2_date_iso"),
]


def safe_int(v) -> Optional[int]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def to_local_day(ts_ms: Optional[int], tz: str = TZ) -> str:
    if ts_ms is None or pd.isna(ts_ms):
        return ""
    dt = pd.to_datetime(int(ts_ms), unit="ms", utc=True).tz_convert(tz)
    return dt.strftime("%Y-%m-%d")


def to_iso_from_ms(ts_ms: Optional[int], tz: str = TZ) -> str:
    if ts_ms is None or pd.isna(ts_ms):
        return ""
    dt = pd.to_datetime(int(ts_ms), unit="ms", utc=True).tz_convert(tz)
    return dt.strftime("%Y-%m-%d %H:%M:%S%z")


def is_connection_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    if isinstance(exc, mysql.connector.Error):
        if getattr(exc, "errno", None) in {2006, 2013, 2014, 2055, 1205}:
            return True
    return any(t in msg for t in ["lost connection", "server has gone away", "timeout", "timed out", "closed"]) 


def make_conn():
    return connect_sensordata_db()


def ping_conn(conn) -> None:
    conn.ping(reconnect=True, attempts=2, delay=2)


def run_coverage_query(conn, table_name: str, device_id: str, start_ms: int, end_ms: int, window_name: str):
    if window_name == "full_T1_T2_window":
        sql = (
            f"SELECT /*+ MAX_EXECUTION_TIME(120000) */ COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts "
            f"FROM `{table_name}` "
            f"WHERE device_id = %s AND timestamp >= %s AND timestamp < %s"
        )
        query_stage = "full_light_count_min_max"
    else:
        sql = (
            f"SELECT /*+ MAX_EXECUTION_TIME(60000) */ COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts, "
            f"COUNT(DISTINCT DATE(FROM_UNIXTIME(timestamp/1000))) AS n_days "
            f"FROM `{table_name}` "
            f"WHERE device_id = %s AND timestamp >= %s AND timestamp < %s"
        )
        query_stage = "early_late_count_min_max_days"

    cur = conn.cursor()
    try:
        cur.execute(sql, (device_id, int(start_ms), int(end_ms)))
        row = cur.fetchone()
        if window_name == "full_T1_T2_window":
            n_rows, first_ts, last_ts = row
            n_days = None
        else:
            n_rows, first_ts, last_ts, n_days = row
        n_rows = int(n_rows or 0)
        return {
            "n_rows": n_rows,
            "first_ts": safe_int(first_ts),
            "last_ts": safe_int(last_ts),
            "n_days": int(n_days or 0) if n_days is not None else None,
            "coverage_status": "ok_has_data" if n_rows > 0 else "ok_no_data",
            "query_stage": query_stage,
            "coverage_note": "full window uses lighter query without COUNT DISTINCT days" if window_name == "full_T1_T2_window" else "",
        }
    finally:
        try:
            cur.close()
        except Exception:
            pass


def build_subject_summary(df_long: pd.DataFrame) -> pd.DataFrame:
    if df_long.empty:
        return pd.DataFrame(columns=[
            "Subject_ID_N", "Subject_ID_D", "total_device_episodes", "tables_with_any_data",
            "early_tables_with_data", "late_tables_with_data", "full_window_tables_with_data",
            "total_rows_all_scanned_tables", "coverage_note"
        ])

    d = df_long.copy()
    d["has_data"] = d["coverage_status"] == "ok_has_data"

    out_rows = []
    for (sid_n, sid_d), g in d.groupby(["Subject_ID_N", "Subject_ID_D"], dropna=False):
        total_device_episodes = int(g["device_id"].nunique())
        tables_with_any_data = int(g.loc[g["has_data"], "table_name"].nunique())
        early_tables = int(g.loc[(g["has_data"]) & (g["window_name"] == "early_window"), "table_name"].nunique())
        late_tables = int(g.loc[(g["has_data"]) & (g["window_name"] == "late_window"), "table_name"].nunique())
        full_tables = int(g.loc[(g["has_data"]) & (g["window_name"] == "full_T1_T2_window"), "table_name"].nunique())
        total_rows = int(pd.to_numeric(g["n_rows"], errors="coerce").fillna(0).sum())

        if total_rows == 0:
            note = "no_data_across_scanned_tables"
        elif early_tables > 0 and late_tables == 0:
            note = "early_only"
        elif late_tables > 0 and early_tables == 0:
            note = "late_only"
        else:
            note = "has_data"

        out_rows.append({
            "Subject_ID_N": sid_n,
            "Subject_ID_D": sid_d,
            "total_device_episodes": total_device_episodes,
            "tables_with_any_data": tables_with_any_data,
            "early_tables_with_data": early_tables,
            "late_tables_with_data": late_tables,
            "full_window_tables_with_data": full_tables,
            "total_rows_all_scanned_tables": total_rows,
            "coverage_note": note,
        })

    return pd.DataFrame(out_rows)


def build_table_summary(df_long: pd.DataFrame) -> pd.DataFrame:
    if df_long.empty:
        return pd.DataFrame(columns=[
            "table_name", "total_rows_across_top10", "n_subjects_with_any_data", "n_devices_with_any_data",
            "n_early_windows_with_data", "n_late_windows_with_data", "n_full_windows_with_data", "table_error_count"
        ])

    d = df_long.copy()
    d["has_data"] = d["coverage_status"] == "ok_has_data"
    d["is_real_error"] = d["coverage_status"] == "table_error"

    out = []
    for table, g in d.groupby("table_name", dropna=False):
        total_rows = int(pd.to_numeric(g["n_rows"], errors="coerce").fillna(0).sum())
        any_data = g[g["has_data"]]
        out.append({
            "table_name": table,
            "total_rows_across_top10": total_rows,
            "n_subjects_with_any_data": int(any_data["Subject_ID_D"].nunique()),
            "n_devices_with_any_data": int(any_data["device_id"].nunique()),
            "n_early_windows_with_data": int(g[(g["has_data"]) & (g["window_name"] == "early_window")].shape[0]),
            "n_late_windows_with_data": int(g[(g["has_data"]) & (g["window_name"] == "late_window")].shape[0]),
            "n_full_windows_with_data": int(g[(g["has_data"]) & (g["window_name"] == "full_T1_T2_window")].shape[0]),
            "table_error_count": int(g["is_real_error"].sum()),
        })

    return pd.DataFrame(out).sort_values("total_rows_across_top10", ascending=False)


def build_early_late_summary(df_long: pd.DataFrame) -> pd.DataFrame:
    d = df_long[df_long["window_name"].isin(["early_window", "late_window"])].copy()
    if d.empty:
        return pd.DataFrame(columns=[
            "Subject_ID_N", "Subject_ID_D", "n_devices_for_subject",
            "early_total_rows", "late_total_rows",
            "early_tables_with_data", "late_tables_with_data",
            "has_early_data", "has_late_data", "early_late_coverage_group"
        ])

    d["n_rows_num"] = pd.to_numeric(d["n_rows"], errors="coerce").fillna(0)
    d["has_data"] = d["coverage_status"] == "ok_has_data"

    out = []
    for (sid_n, sid_d), g in d.groupby(["Subject_ID_N", "Subject_ID_D"], dropna=False):
        n_dev = int(pd.to_numeric(g["n_devices_for_subject"], errors="coerce").max())
        early = g[g["window_name"] == "early_window"]
        late = g[g["window_name"] == "late_window"]
        early_total = int(early["n_rows_num"].sum())
        late_total = int(late["n_rows_num"].sum())
        early_tables = int(early.loc[early["has_data"], "table_name"].nunique())
        late_tables = int(late.loc[late["has_data"], "table_name"].nunique())
        has_early = early_total > 0
        has_late = late_total > 0

        if has_early and has_late:
            grp = "early_and_late_data"
        elif has_early and not has_late:
            grp = "early_only"
        elif has_late and not has_early:
            grp = "late_only"
        else:
            grp = "no_early_or_late_data"

        out.append({
            "Subject_ID_N": sid_n,
            "Subject_ID_D": sid_d,
            "n_devices_for_subject": n_dev,
            "early_total_rows": early_total,
            "late_total_rows": late_total,
            "early_tables_with_data": early_tables,
            "late_tables_with_data": late_tables,
            "has_early_data": has_early,
            "has_late_data": has_late,
            "early_late_coverage_group": grp,
        })

    return pd.DataFrame(out)


def write_readme(out_dir: Path) -> None:
    p = out_dir / "README_sql_coverage.md"
    p.write_text(
        """# SQL Coverage Scan (Top10 Decline)

This scan checks data availability only.

- It does **not** compute features.
- Missing rows are **not** interpreted as zero activity.
- Every query is filtered by both `device_id` and `timestamp` range.
- `early_window` and `late_window` were scanned directly and are the primary reliable outputs.
- `full_T1_T2_window` was intentionally skipped when span >45 days using safety guard.
- `skipped_long_full_window` is an intentional safety skip, not a DB error.
- Full-window coverage should be done later with a safer day-level strategy.
"""
    )


def archive_existing_outputs(out_dir: Path) -> None:
    archive_dir = out_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for name in [
        "top10_sql_coverage_long.csv",
        "top10_sql_coverage_summary_by_subject.csv",
        "top10_sql_coverage_summary_by_table.csv",
        "top10_sql_coverage_early_late_summary.csv",
        "README_sql_coverage.md",
    ]:
        src = out_dir / name
        if src.exists():
            src.replace(archive_dir / f"{src.stem}_{ts}{src.suffix}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan SQL coverage for top10 subject-device episodes.")
    parser.add_argument("--episodes-csv", default="output/analysis_candidates/top10_subject_device_episodes.csv")
    parser.add_argument("--out-dir", default="output/analysis_candidates/sql_coverage")
    args = parser.parse_args()

    episodes_path = Path(args.episodes_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    archive_existing_outputs(out_dir)

    long_csv = out_dir / "top10_sql_coverage_long.csv"
    subject_csv = out_dir / "top10_sql_coverage_summary_by_subject.csv"
    table_csv = out_dir / "top10_sql_coverage_summary_by_table.csv"
    early_late_csv = out_dir / "top10_sql_coverage_early_late_summary.csv"

    df = pd.read_csv(episodes_path, dtype=str)

    base_cols = [
        "Subject_ID_N", "Subject_ID_D", "device_id", "device_episode_index", "n_devices_for_subject",
        "table_name", "window_name", "window_start_ms", "window_end_ms", "window_start_iso", "window_end_iso",
        "n_rows", "first_timestamp_ms", "last_timestamp_ms", "first_day_local", "last_day_local", "n_days_with_data",
        "coverage_status", "error_type", "error_message", "query_stage", "coverage_note",
    ]

    total_queries = 0
    conn = make_conn()

    with long_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=base_cols)
        writer.writeheader()
        f.flush()

        for _, ep in df.iterrows():
            subj_n = ep.get("Subject_ID_N", "")
            subj_d = ep.get("Subject_ID_D", "")
            device_id = (ep.get("device_id", "") or "").strip()
            ep_idx = ep.get("device_episode_index", "")
            n_dev = ep.get("n_devices_for_subject", "")

            for table in TABLES_TO_SCAN:
                for (window_name, start_col, end_col, start_iso_col, end_iso_col) in WINDOW_SPECS:
                    total_queries += 1
                    retry_used = False
                    start_ms = safe_int(ep.get(start_col))
                    end_ms = safe_int(ep.get(end_col))

                    row_out = {
                        "Subject_ID_N": subj_n,
                        "Subject_ID_D": subj_d,
                        "device_id": device_id,
                        "device_episode_index": ep_idx,
                        "n_devices_for_subject": n_dev,
                        "table_name": table,
                        "window_name": window_name,
                        "window_start_ms": start_ms if start_ms is not None else "",
                        "window_end_ms": end_ms if end_ms is not None else "",
                        "window_start_iso": ep.get(start_iso_col, "") if start_iso_col in ep.index else to_iso_from_ms(start_ms),
                        "window_end_iso": ep.get(end_iso_col, "") if end_iso_col in ep.index else to_iso_from_ms(end_ms),
                        "n_rows": 0,
                        "first_timestamp_ms": "",
                        "last_timestamp_ms": "",
                        "first_day_local": "",
                        "last_day_local": "",
                        "n_days_with_data": "",
                        "coverage_status": "ok_no_data",
                        "error_type": "",
                        "error_message": "",
                        "query_stage": "",
                        "coverage_note": "",
                    }

                    if not device_id:
                        row_out["coverage_status"] = "missing_device_id"
                        row_out["query_stage"] = "precheck"
                    elif start_ms is None or end_ms is None or end_ms <= start_ms:
                        row_out["coverage_status"] = "missing_time_window"
                        row_out["query_stage"] = "precheck"
                    elif window_name == "full_T1_T2_window" and (end_ms - start_ms) > (45 * 86400000):
                        row_out["coverage_status"] = "skipped_long_full_window"
                        row_out["error_type"] = "full_window_guard"
                        row_out["error_message"] = "full window span >45 days skipped to avoid long-running query"
                        row_out["query_stage"] = "full_window_span_guard"
                        row_out["coverage_note"] = "intentional safety skip, not a DB error"
                    else:
                        attempts = 0
                        last_exc: Optional[Exception] = None
                        while attempts < 2:
                            attempts += 1
                            try:
                                ping_conn(conn)
                                res = run_coverage_query(conn, table, device_id, start_ms, end_ms, window_name)
                                row_out["n_rows"] = res["n_rows"]
                                row_out["first_timestamp_ms"] = res["first_ts"] if res["first_ts"] is not None else ""
                                row_out["last_timestamp_ms"] = res["last_ts"] if res["last_ts"] is not None else ""
                                row_out["first_day_local"] = to_local_day(res["first_ts"])
                                row_out["last_day_local"] = to_local_day(res["last_ts"])
                                row_out["n_days_with_data"] = "" if res["n_days"] is None else res["n_days"]
                                row_out["coverage_status"] = res["coverage_status"]
                                row_out["query_stage"] = res["query_stage"]
                                row_out["coverage_note"] = res["coverage_note"]
                                last_exc = None
                                break
                            except Exception as exc:
                                last_exc = exc
                                if attempts == 1 and is_connection_error(exc):
                                    retry_used = True
                                    try:
                                        conn.close()
                                    except Exception:
                                        pass
                                    conn = make_conn()
                                    continue
                                break

                        if last_exc is not None:
                            row_out["coverage_status"] = "table_error"
                            row_out["error_type"] = type(last_exc).__name__
                            row_out["error_message"] = str(last_exc).replace("\n", " ")[:700]
                            row_out["query_stage"] = row_out["query_stage"] or "query_failed"

                    writer.writerow(row_out)
                    f.flush()
                    print(
                        f"{subj_d} / ep={ep_idx} / {table} / {window_name} / "
                        f"{row_out['coverage_status']} / n_rows={row_out['n_rows']} / retry_used={retry_used}"
                    )

    try:
        conn.close()
    except Exception:
        pass

    df_long = pd.read_csv(long_csv, dtype=str)

    subject_summary = build_subject_summary(df_long)
    table_summary = build_table_summary(df_long)
    early_late_summary = build_early_late_summary(df_long)

    subject_summary.to_csv(subject_csv, index=False)
    table_summary.to_csv(table_csv, index=False)
    early_late_summary.to_csv(early_late_csv, index=False)
    write_readme(out_dir)

    total_device_episodes = int(df["device_id"].nunique()) if "device_id" in df.columns else 0
    is_real_err = df_long["coverage_status"] == "table_error"
    is_skip_long = df_long["coverage_status"] == "skipped_long_full_window"
    is_early_late = df_long["window_name"].isin(["early_window", "late_window"])

    total_real_table_errors = int(is_real_err.sum())
    total_skipped_long_full_window = int(is_skip_long.sum())
    early_late_queries_attempted = int(is_early_late.sum())
    early_late_real_table_errors = int((is_real_err & is_early_late).sum())

    print("\n=== COVERAGE SCAN SUMMARY ===")
    print(f"total_device_episodes_scanned={total_device_episodes}")
    print(f"total_queries_attempted={len(df_long)}")
    print(f"total_real_table_errors={total_real_table_errors}")
    print(f"total_skipped_long_full_window={total_skipped_long_full_window}")
    print(f"early_late_queries_attempted={early_late_queries_attempted}")
    print(f"early_late_real_table_errors={early_late_real_table_errors}")

    print("\nTop tables by n_rows:")
    if table_summary.empty:
        print("(none)")
    else:
        print(table_summary[["table_name", "total_rows_across_top10"]].head(10).to_string(index=False))

    print("\nGenerated files:")
    print(f"- {long_csv}")
    print(f"- {subject_csv}")
    print(f"- {table_csv}")
    print(f"- {early_late_csv}")
    print(f"- {out_dir / 'README_sql_coverage.md'}")


if __name__ == "__main__":
    main()
