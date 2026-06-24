import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

from main import connect_sensordata_db

TZ = "Asia/Jerusalem"
TABLES = ["screen", "applications_foreground", "aware_log"]
WINDOWS = [
    ("early", "early_window_start_ms", "early_window_end_ms"),
    ("late", "late_window_start_ms", "late_window_end_ms"),
]


def to_local(ts_ms: int) -> pd.Timestamp:
    return pd.to_datetime(int(ts_ms), unit="ms", utc=True).tz_convert(TZ)


def shannon_entropy(counts) -> Optional[float]:
    total = sum(counts)
    if total <= 0:
        return None
    ent = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = c / total
        ent -= p * math.log(p, 2)
    return ent


def safe_float(v) -> Optional[float]:
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        return float(v)
    except Exception:
        return None


def compute_screen_features(rows):
    # rows: list of dicts {timestamp, data_json}
    days = set()
    event_count = 0
    night_count = 0
    parse_errors = 0
    has_state_key = False

    for r in rows:
        ts = r["timestamp"]
        dt = to_local(ts)
        days.add(dt.strftime("%Y-%m-%d"))
        event_count += 1
        hour = dt.hour
        if hour >= 22 or hour < 6:
            night_count += 1
        dj = r.get("data_json")
        if isinstance(dj, dict):
            if "screen_status" in dj or "screen_state" in dj:
                has_state_key = True
        elif dj is None:
            pass
        else:
            parse_errors += 1

    active_days = len(days)
    per_day = (event_count / active_days) if active_days > 0 else None

    return {
        "screen_event_count": event_count,
        "active_screen_days": active_days,
        "night_screen_event_count": night_count,
        "screen_events_per_active_day": per_day,
        "screen_state_key_present": has_state_key,
        "json_parse_errors": parse_errors,
    }


def compute_app_features(rows):
    days = set()
    event_count = 0
    parse_errors = 0
    apps = []

    for r in rows:
        ts = r["timestamp"]
        dt = to_local(ts)
        days.add(dt.strftime("%Y-%m-%d"))
        event_count += 1
        dj = r.get("data_json")
        if isinstance(dj, dict):
            app_id = dj.get("package_name") or dj.get("application_name")
            if app_id is not None and str(app_id).strip() != "":
                apps.append(str(app_id).strip())
        elif dj is None:
            pass
        else:
            parse_errors += 1

    active_days = len(days)
    per_day = (event_count / active_days) if active_days > 0 else None

    unique_apps = len(set(apps)) if apps else None
    entropy = shannon_entropy(Counter(apps).values()) if apps else None

    return {
        "app_foreground_event_count": event_count,
        "active_app_days": active_days,
        "unique_foreground_apps": unique_apps,
        "app_use_diversity": entropy,
        "app_events_per_active_day": per_day,
        "json_parse_errors": parse_errors,
    }


def compute_aware_log_features(rows):
    days = set()
    event_count = 0
    parse_errors = 0

    for r in rows:
        ts = r["timestamp"]
        dt = to_local(ts)
        days.add(dt.strftime("%Y-%m-%d"))
        event_count += 1
        dj = r.get("data_json")
        if dj is not None and not isinstance(dj, dict):
            parse_errors += 1

    active_days = len(days)
    density = (event_count / active_days) if active_days > 0 else None

    return {
        "aware_log_rows": event_count,
        "aware_log_active_days": active_days,
        "data_logging_coverage_days": active_days,
        "system_log_density": density,
        "json_parse_errors": parse_errors,
    }


def parse_row(ts, device_id, data_raw):
    data_json = None
    if data_raw is None:
        return {"timestamp": int(ts), "device_id": device_id, "data_json": None, "parse_ok": True}
    try:
        if isinstance(data_raw, (bytes, bytearray)):
            data_raw = data_raw.decode("utf-8", errors="ignore")
        if isinstance(data_raw, str):
            data_json = json.loads(data_raw)
        elif isinstance(data_raw, dict):
            data_json = data_raw
        else:
            data_json = None
        return {"timestamp": int(ts), "device_id": device_id, "data_json": data_json, "parse_ok": True}
    except Exception:
        return {"timestamp": int(ts), "device_id": device_id, "data_json": "__JSON_PARSE_ERROR__", "parse_ok": False}


def query_rows(conn, table: str, device_id: str, start_ms: int, end_ms: int):
    sql = (
        f"SELECT timestamp, device_id, data FROM `{table}` "
        "WHERE device_id = %s AND timestamp >= %s AND timestamp < %s"
    )
    cur = conn.cursor()
    out = []
    try:
        cur.execute(sql, (device_id, int(start_ms), int(end_ms)))
        while True:
            batch = cur.fetchmany(5000)
            if not batch:
                break
            for ts, did, data in batch:
                pr = parse_row(ts, did, data)
                out.append(pr)
        return out, None
    except Exception as e:
        return None, str(e)
    finally:
        try:
            cur.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="Phase 1A extraction: screen + app_foreground + aware_log only.")
    ap.add_argument("--episodes", default="output/analysis_candidates/top10_subject_device_episodes.csv")
    ap.add_argument("--subject-readiness", default="output/analysis_candidates/sql_coverage/top10_subject_readiness.csv")
    ap.add_argument("--coverage-matrix", default="output/analysis_candidates/sql_coverage/top10_subject_table_coverage_matrix.csv")
    ap.add_argument("--feature-plan", default="output/analysis_candidates/phase1_features/phase1_feature_plan.csv")
    ap.add_argument("--table-review", default="output/analysis_candidates/phase1_features/phase1_table_json_key_review.csv")
    ap.add_argument("--out-dir", default="output/analysis_candidates/phase1_features/extracted")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # load required inputs (for reproducibility/checks)
    episodes = pd.read_csv(args.episodes, dtype=str)
    _ = pd.read_csv(args.subject_readiness, dtype=str)
    _ = pd.read_csv(args.coverage_matrix, dtype=str)
    _ = pd.read_csv(args.feature_plan, dtype=str)
    _ = pd.read_csv(args.table_review, dtype=str)

    episodes = episodes[episodes["mapping_status"].astype(str) == "ok"].copy()

    conn = connect_sensordata_db()

    device_rows = []
    subject_agg = defaultdict(lambda: {
        "n_raw_rows": 0,
        "active_days": set(),
        "night_count": 0,
        "app_counter": Counter(),
        "json_parse_errors": 0,
        "statuses": [],
    })

    try:
        for _, ep in episodes.iterrows():
            sid_d = str(ep["Subject_ID_D"])
            sid_n = str(ep["Subject_ID_N"])
            dev = str(ep["device_id"])
            ep_idx = str(ep["device_episode_index"])
            n_dev = str(ep["n_devices_for_subject"])

            for table in TABLES:
                for wname, s_col, e_col in WINDOWS:
                    start_ms = ep.get(s_col)
                    end_ms = ep.get(e_col)

                    base = {
                        "Subject_ID_N": sid_n,
                        "Subject_ID_D": sid_d,
                        "device_id": dev,
                        "device_episode_index": ep_idx,
                        "n_devices_for_subject": n_dev,
                        "table_name": table,
                        "window_name": f"{wname}_window",
                        "window_start_ms": start_ms,
                        "window_end_ms": end_ms,
                        "table_has_data": False,
                        "n_raw_rows": 0,
                        "n_active_days": None,
                        "extraction_status": "ok_no_data",
                        "error_message": "",
                        # features
                        "screen_event_count": None,
                        "active_screen_days": None,
                        "night_screen_event_count": None,
                        "screen_events_per_active_day": None,
                        "app_foreground_event_count": None,
                        "active_app_days": None,
                        "unique_foreground_apps": None,
                        "app_use_diversity": None,
                        "app_events_per_active_day": None,
                        "aware_log_rows": None,
                        "aware_log_active_days": None,
                        "data_logging_coverage_days": None,
                        "system_log_density": None,
                        "json_parse_errors": 0,
                    }

                    if pd.isna(start_ms) or pd.isna(end_ms):
                        base["extraction_status"] = "missing_window"
                        device_rows.append(base)
                        subject_agg[(sid_d, wname, table)]["statuses"].append("missing_window")
                        continue

                    try:
                        s = int(float(start_ms))
                        e = int(float(end_ms))
                    except Exception:
                        base["extraction_status"] = "missing_window"
                        device_rows.append(base)
                        subject_agg[(sid_d, wname, table)]["statuses"].append("missing_window")
                        continue

                    rows, err = query_rows(conn, table, dev, s, e)
                    if err is not None:
                        base["extraction_status"] = "sql_error"
                        base["error_message"] = err[:500]
                        device_rows.append(base)
                        subject_agg[(sid_d, wname, table)]["statuses"].append("sql_error")
                        continue

                    base["n_raw_rows"] = len(rows)
                    base["table_has_data"] = len(rows) > 0

                    if len(rows) == 0:
                        base["extraction_status"] = "ok_no_data"
                        device_rows.append(base)
                        subject_agg[(sid_d, wname, table)]["statuses"].append("ok_no_data")
                        continue

                    parse_bad = sum(1 for r in rows if not r["parse_ok"])

                    # transform parse marker to None for compute functions
                    cleaned = []
                    for r in rows:
                        rr = dict(r)
                        if rr["data_json"] == "__JSON_PARSE_ERROR__":
                            rr["data_json"] = "__ERR__"
                        cleaned.append(rr)

                    if table == "screen":
                        feats = compute_screen_features(cleaned)
                        base.update({
                            "screen_event_count": feats["screen_event_count"],
                            "active_screen_days": feats["active_screen_days"],
                            "night_screen_event_count": feats["night_screen_event_count"],
                            "screen_events_per_active_day": feats["screen_events_per_active_day"],
                        })
                    elif table == "applications_foreground":
                        feats = compute_app_features(cleaned)
                        base.update({
                            "app_foreground_event_count": feats["app_foreground_event_count"],
                            "active_app_days": feats["active_app_days"],
                            "unique_foreground_apps": feats["unique_foreground_apps"],
                            "app_use_diversity": feats["app_use_diversity"],
                            "app_events_per_active_day": feats["app_events_per_active_day"],
                        })
                    elif table == "aware_log":
                        feats = compute_aware_log_features(cleaned)
                        base.update({
                            "aware_log_rows": feats["aware_log_rows"],
                            "aware_log_active_days": feats["aware_log_active_days"],
                            "data_logging_coverage_days": feats["data_logging_coverage_days"],
                            "system_log_density": feats["system_log_density"],
                        })

                    base["n_active_days"] = len({to_local(r['timestamp']).strftime('%Y-%m-%d') for r in cleaned})
                    base["json_parse_errors"] = parse_bad
                    base["extraction_status"] = "json_parse_error" if parse_bad > 0 else "ok_has_data"

                    # accumulate subject-window-table across devices
                    agg = subject_agg[(sid_d, wname, table)]
                    agg["n_raw_rows"] += len(cleaned)
                    agg["json_parse_errors"] += parse_bad
                    for r in cleaned:
                        d = to_local(r["timestamp"]).strftime("%Y-%m-%d")
                        agg["active_days"].add(d)
                        if table == "screen":
                            h = to_local(r["timestamp"]).hour
                            if h >= 22 or h < 6:
                                agg["night_count"] += 1
                        if table == "applications_foreground":
                            dj = r.get("data_json")
                            if isinstance(dj, dict):
                                app_id = dj.get("package_name") or dj.get("application_name")
                                if app_id is not None and str(app_id).strip() != "":
                                    agg["app_counter"][str(app_id).strip()] += 1

                    agg["statuses"].append(base["extraction_status"])
                    device_rows.append(base)

    finally:
        try:
            conn.close()
        except Exception:
            pass

    # device-level CSV
    device_df = pd.DataFrame(device_rows)
    device_path = out_dir / "phase1a_device_window_features.csv"
    device_df.to_csv(device_path, index=False)

    # subject-level final (subject x window x table)
    subj_rows = []
    subj_info = episodes[["Subject_ID_D", "Subject_ID_N", "n_devices_for_subject"]].drop_duplicates().set_index("Subject_ID_D")

    for (sid_d, wname, table), agg in subject_agg.items():
        sid_n = subj_info.loc[sid_d, "Subject_ID_N"] if sid_d in subj_info.index else ""
        n_dev = subj_info.loc[sid_d, "n_devices_for_subject"] if sid_d in subj_info.index else ""
        n_rows = agg["n_raw_rows"]
        n_days = len(agg["active_days"])

        statuses = agg["statuses"]
        if any(s == "sql_error" for s in statuses):
            status = "sql_error"
        elif any(s == "missing_window" for s in statuses):
            status = "missing_window"
        elif any(s == "json_parse_error" for s in statuses):
            status = "json_parse_error"
        elif n_rows > 0:
            status = "ok_has_data"
        else:
            status = "ok_no_data"

        row = {
            "Subject_ID_N": sid_n,
            "Subject_ID_D": sid_d,
            "n_devices_for_subject": n_dev,
            "table_name": table,
            "window_name": f"{wname}_window",
            "table_has_data": n_rows > 0,
            "n_raw_rows": n_rows,
            "n_active_days": n_days,
            "extraction_status": status,
            "error_message": "",
            "json_parse_errors": agg["json_parse_errors"],
            "screen_event_count": None,
            "active_screen_days": None,
            "night_screen_event_count": None,
            "screen_events_per_active_day": None,
            "app_foreground_event_count": None,
            "active_app_days": None,
            "unique_foreground_apps": None,
            "app_use_diversity": None,
            "app_events_per_active_day": None,
            "aware_log_rows": None,
            "aware_log_active_days": None,
            "data_logging_coverage_days": None,
            "system_log_density": None,
        }

        if table == "screen":
            row["screen_event_count"] = n_rows
            row["active_screen_days"] = n_days
            row["night_screen_event_count"] = agg["night_count"]
            row["screen_events_per_active_day"] = (n_rows / n_days) if n_days > 0 else None
        elif table == "applications_foreground":
            row["app_foreground_event_count"] = n_rows
            row["active_app_days"] = n_days
            row["unique_foreground_apps"] = len(agg["app_counter"]) if len(agg["app_counter"]) > 0 else None
            row["app_use_diversity"] = shannon_entropy(agg["app_counter"].values()) if len(agg["app_counter"]) > 0 else None
            row["app_events_per_active_day"] = (n_rows / n_days) if n_days > 0 else None
        elif table == "aware_log":
            row["aware_log_rows"] = n_rows
            row["aware_log_active_days"] = n_days
            row["data_logging_coverage_days"] = n_days
            row["system_log_density"] = (n_rows / n_days) if n_days > 0 else None

        subj_rows.append(row)

    subj_df = pd.DataFrame(subj_rows)
    subj_path = out_dir / "phase1a_subject_window_features.csv"
    subj_df.to_csv(subj_path, index=False)

    # wide subject table
    wide_rows = []
    subjects = sorted(set(episodes["Subject_ID_D"].astype(str)))

    for sid in subjects:
        sid_n = subj_info.loc[sid, "Subject_ID_N"] if sid in subj_info.index else ""
        out = {"Subject_ID_N": sid_n, "Subject_ID_D": sid}

        def get_row(table, w):
            q = subj_df[(subj_df["Subject_ID_D"] == sid) & (subj_df["table_name"] == table) & (subj_df["window_name"] == f"{w}_window")]
            if q.empty:
                return None
            return q.iloc[0]

        # screen
        se = get_row("screen", "early")
        sl = get_row("screen", "late")
        out["screen_early_event_count"] = se["screen_event_count"] if se is not None else None
        out["screen_late_event_count"] = sl["screen_event_count"] if sl is not None else None
        if se is not None and sl is not None and se["extraction_status"] == "ok_has_data" and sl["extraction_status"] == "ok_has_data":
            out["screen_delta_event_count"] = float(sl["screen_event_count"]) - float(se["screen_event_count"])
            out["screen_pct_change_event_count"] = (float(sl["screen_event_count"]) - float(se["screen_event_count"])) / float(se["screen_event_count"]) if float(se["screen_event_count"]) > 0 else None
            out["screen_delta_status"] = "ok"
        else:
            out["screen_delta_event_count"] = None
            out["screen_pct_change_event_count"] = None
            out["screen_delta_status"] = "missing_early_or_late"

        # app
        ae = get_row("applications_foreground", "early")
        al = get_row("applications_foreground", "late")
        out["app_early_foreground_event_count"] = ae["app_foreground_event_count"] if ae is not None else None
        out["app_late_foreground_event_count"] = al["app_foreground_event_count"] if al is not None else None
        if ae is not None and al is not None and ae["extraction_status"] == "ok_has_data" and al["extraction_status"] == "ok_has_data":
            out["app_delta_foreground_event_count"] = float(al["app_foreground_event_count"]) - float(ae["app_foreground_event_count"])
            out["app_pct_change_foreground_event_count"] = (float(al["app_foreground_event_count"]) - float(ae["app_foreground_event_count"])) / float(ae["app_foreground_event_count"]) if float(ae["app_foreground_event_count"]) > 0 else None
            out["app_delta_status"] = "ok"
        else:
            out["app_delta_foreground_event_count"] = None
            out["app_pct_change_foreground_event_count"] = None
            out["app_delta_status"] = "missing_early_or_late"

        # aware_log quality only
        le = get_row("aware_log", "early")
        ll = get_row("aware_log", "late")
        out["aware_log_early_rows"] = le["aware_log_rows"] if le is not None else None
        out["aware_log_late_rows"] = ll["aware_log_rows"] if ll is not None else None
        if le is not None and ll is not None and le["extraction_status"] == "ok_has_data" and ll["extraction_status"] == "ok_has_data":
            out["aware_log_delta_rows"] = float(ll["aware_log_rows"]) - float(le["aware_log_rows"])
            out["aware_log_delta_status"] = "ok"
        else:
            out["aware_log_delta_rows"] = None
            out["aware_log_delta_status"] = "missing_early_or_late"

        wide_rows.append(out)

    wide_df = pd.DataFrame(wide_rows)
    wide_path = out_dir / "phase1a_subject_features_wide.csv"
    wide_df.to_csv(wide_path, index=False)

    # README
    readme = out_dir / "README_phase1a_extraction.md"
    readme.write_text(
        """# Phase 1A Extraction

This is first-pass Phase 1A extraction.

Included tables:
- screen
- applications_foreground
- aware_log (data-quality only)

Not included yet:
- keyboard, touch, activity recognition, gsm/gsm_neighbor, telephony, messages
- any high-frequency motion tables

Notes:
- Missing data is not interpreted as zero activity.
- Only early_window and late_window were extracted.
- Early-vs-late deltas are computed only when both windows have data.
- aware_log features are data-quality denominators, not direct phenotype measures.
"""
    )

    # Print summary requested
    n_subjects = wide_df["Subject_ID_D"].nunique()

    def both_count(df, e_col, l_col):
        e = pd.to_numeric(df[e_col], errors="coerce")
        l = pd.to_numeric(df[l_col], errors="coerce")
        return int(((e > 0) & (l > 0)).sum())

    se = pd.to_numeric(wide_df["screen_early_event_count"], errors="coerce")
    sl = pd.to_numeric(wide_df["screen_late_event_count"], errors="coerce")
    ae = pd.to_numeric(wide_df["app_early_foreground_event_count"], errors="coerce")
    al = pd.to_numeric(wide_df["app_late_foreground_event_count"], errors="coerce")
    le = pd.to_numeric(wide_df["aware_log_early_rows"], errors="coerce")
    ll = pd.to_numeric(wide_df["aware_log_late_rows"], errors="coerce")

    print(f"number_of_subjects_extracted={n_subjects}")
    print(f"screen_early_subjects_with_data={(se > 0).sum()}")
    print(f"screen_late_subjects_with_data={(sl > 0).sum()}")
    print(f"screen_subjects_with_both_early_late={((se > 0) & (sl > 0)).sum()}")

    print(f"app_early_subjects_with_data={(ae > 0).sum()}")
    print(f"app_late_subjects_with_data={(al > 0).sum()}")
    print(f"app_subjects_with_both_early_late={((ae > 0) & (al > 0)).sum()}")

    print("aware_log_coverage_summary:")
    print(f"aware_log_early_subjects_with_data={(le > 0).sum()}")
    print(f"aware_log_late_subjects_with_data={(ll > 0).sum()}")
    print(f"aware_log_subjects_with_both_early_late={((le > 0) & (ll > 0)).sum()}")

    print("top_10_rows_subject_level_wide:")
    print(wide_df.head(10).to_string(index=False))

    print("generated_files:")
    print(f"- {device_path}")
    print(f"- {subj_path}")
    print(f"- {wide_path}")
    print(f"- {readme}")


if __name__ == "__main__":
    main()
