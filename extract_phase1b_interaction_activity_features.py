import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

import pandas as pd

from main import connect_sensordata_db

TZ = "Asia/Jerusalem"
TABLES = ["keyboard", "touch", "plugin_google_activity_recognition"]
WINDOWS = [
    ("early", "early_window_start_ms", "early_window_end_ms"),
    ("late", "late_window_start_ms", "late_window_end_ms"),
]
HIGH_CONF_THRESH = 50.0


def normalize_subject_id_d(v) -> str:
    s = str(v).strip()
    return s.zfill(3) if s.isdigit() else s


def to_local(ts_ms: int) -> pd.Timestamp:
    return pd.to_datetime(int(ts_ms), unit="ms", utc=True).tz_convert(TZ)


def shannon_entropy(counts) -> Optional[float]:
    total = sum(counts)
    if total <= 0:
        return None
    e = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = c / total
        e -= p * math.log(p, 2)
    return e


def safe_num(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def parse_row(ts, did, data_raw):
    if data_raw is None:
        return {"timestamp": int(ts), "device_id": did, "data_json": None, "parse_ok": True}
    try:
        if isinstance(data_raw, (bytes, bytearray)):
            data_raw = data_raw.decode("utf-8", errors="ignore")
        if isinstance(data_raw, str):
            data_json = json.loads(data_raw)
        elif isinstance(data_raw, dict):
            data_json = data_raw
        else:
            data_json = None
        return {"timestamp": int(ts), "device_id": did, "data_json": data_json, "parse_ok": True}
    except Exception:
        return {"timestamp": int(ts), "device_id": did, "data_json": "__ERR__", "parse_ok": False}


def query_rows(conn, table, device_id, start_ms, end_ms):
    sql = f"SELECT timestamp, device_id, data FROM `{table}` WHERE device_id = %s AND timestamp >= %s AND timestamp < %s"
    cur = conn.cursor()
    out = []
    try:
        cur.execute(sql, (device_id, int(start_ms), int(end_ms)))
        while True:
            b = cur.fetchmany(5000)
            if not b:
                break
            for ts, did, data in b:
                out.append(parse_row(ts, did, data))
        return out, None
    except Exception as e:
        return None, str(e)
    finally:
        try:
            cur.close()
        except Exception:
            pass


def extract_activity_label_and_conf(dj):
    label = None
    conf = None
    if not isinstance(dj, dict):
        return label, conf

    if dj.get("activity_name") is not None:
        label = str(dj.get("activity_name")).strip().lower()
    if dj.get("confidence") is not None:
        conf = safe_num(dj.get("confidence"))

    acts = dj.get("activities")
    if acts is not None and (label is None or conf is None):
        arr = None
        if isinstance(acts, list):
            arr = acts
        elif isinstance(acts, str):
            try:
                arr = json.loads(acts)
            except Exception:
                arr = None
        if isinstance(arr, list) and arr:
            best = None
            best_c = -1
            for item in arr:
                if not isinstance(item, dict):
                    continue
                c = safe_num(item.get("confidence"))
                if c is None:
                    c = -1
                if c > best_c:
                    best_c = c
                    best = item
            if best is not None:
                if label is None and best.get("activity") is not None:
                    label = str(best.get("activity")).strip().lower()
                if conf is None and best_c >= 0:
                    conf = float(best_c)

    return label, conf


def main():
    ap = argparse.ArgumentParser(description="Phase 1B extraction: keyboard + touch + activity only.")
    ap.add_argument("--episodes", default="output/analysis_candidates/top10_subject_device_episodes.csv")
    ap.add_argument("--subject-readiness", default="output/analysis_candidates/sql_coverage/top10_subject_readiness.csv")
    ap.add_argument("--coverage-matrix", default="output/analysis_candidates/sql_coverage/top10_subject_table_coverage_matrix.csv")
    ap.add_argument("--feature-plan", default="output/analysis_candidates/phase1_features/phase1_feature_plan.csv")
    ap.add_argument("--json-review", default="output/analysis_candidates/phase1_features/phase1_json_value_distribution_review.csv")
    ap.add_argument("--out-dir", default="output/analysis_candidates/phase1_features/extracted")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    episodes = pd.read_csv(args.episodes, dtype=str)
    _ = pd.read_csv(args.subject_readiness, dtype=str)
    _ = pd.read_csv(args.coverage_matrix, dtype=str)
    _ = pd.read_csv(args.feature_plan, dtype=str)
    _ = pd.read_csv(args.json_review, dtype=str)

    episodes = episodes[episodes["mapping_status"].astype(str) == "ok"].copy()
    episodes["Subject_ID_D"] = episodes["Subject_ID_D"].map(normalize_subject_id_d)

    conn = connect_sensordata_db()

    device_rows = []
    subj_agg = defaultdict(lambda: {
        "n_raw_rows": 0,
        "active_days": set(),
        "json_parse_errors": 0,
        "statuses": [],
        "activity_label_counter": Counter(),
        "activity_conf_vals": [],
        "high_conf_count": 0,
    })

    try:
        for _, ep in episodes.iterrows():
            sid_d = normalize_subject_id_d(ep["Subject_ID_D"])
            sid_n = str(ep["Subject_ID_N"])
            did = str(ep["device_id"])
            ep_idx = str(ep["device_episode_index"])
            n_dev = str(ep["n_devices_for_subject"])

            for table in TABLES:
                for wname, s_col, e_col in WINDOWS:
                    start_ms = ep.get(s_col)
                    end_ms = ep.get(e_col)
                    row = {
                        "Subject_ID_N": sid_n,
                        "Subject_ID_D": sid_d,
                        "device_id": did,
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
                        "json_parse_errors": 0,
                        "keyboard_event_count": None,
                        "active_keyboard_days": None,
                        "keyboard_events_per_active_day": None,
                        "touch_event_count": None,
                        "active_touch_days": None,
                        "touch_events_per_active_day": None,
                        "activity_event_count": None,
                        "active_activity_days": None,
                        "still_event_count": None,
                        "walking_event_count": None,
                        "in_vehicle_event_count": None,
                        "activity_diversity": None,
                        "high_confidence_activity_event_count": None,
                        "mean_activity_confidence": None,
                    }

                    if pd.isna(start_ms) or pd.isna(end_ms):
                        row["extraction_status"] = "missing_window"
                        device_rows.append(row)
                        subj_agg[(sid_d, wname, table)]["statuses"].append("missing_window")
                        continue

                    try:
                        s = int(float(start_ms)); e = int(float(end_ms))
                    except Exception:
                        row["extraction_status"] = "missing_window"
                        device_rows.append(row)
                        subj_agg[(sid_d, wname, table)]["statuses"].append("missing_window")
                        continue

                    rows, err = query_rows(conn, table, did, s, e)
                    if err is not None:
                        row["extraction_status"] = "sql_error"
                        row["error_message"] = err[:500]
                        device_rows.append(row)
                        subj_agg[(sid_d, wname, table)]["statuses"].append("sql_error")
                        continue

                    row["n_raw_rows"] = len(rows)
                    row["table_has_data"] = len(rows) > 0

                    if len(rows) == 0:
                        row["extraction_status"] = "ok_no_data"
                        device_rows.append(row)
                        subj_agg[(sid_d, wname, table)]["statuses"].append("ok_no_data")
                        continue

                    parse_bad = sum(1 for r in rows if not r["parse_ok"])
                    active_days = {to_local(r["timestamp"]).strftime("%Y-%m-%d") for r in rows}
                    n_days = len(active_days)

                    row["n_active_days"] = n_days
                    row["json_parse_errors"] = parse_bad

                    agg = subj_agg[(sid_d, wname, table)]
                    agg["n_raw_rows"] += len(rows)
                    agg["json_parse_errors"] += parse_bad
                    agg["active_days"].update(active_days)

                    if table == "keyboard":
                        row["keyboard_event_count"] = len(rows)
                        row["active_keyboard_days"] = n_days
                        row["keyboard_events_per_active_day"] = (len(rows) / n_days) if n_days > 0 else None

                    elif table == "touch":
                        row["touch_event_count"] = len(rows)
                        row["active_touch_days"] = n_days
                        row["touch_events_per_active_day"] = (len(rows) / n_days) if n_days > 0 else None

                    elif table == "plugin_google_activity_recognition":
                        labels = []
                        confs = []
                        for rr in rows:
                            dj = rr["data_json"] if rr["data_json"] != "__ERR__" else None
                            label, conf = extract_activity_label_and_conf(dj)
                            if label:
                                labels.append(label)
                            if conf is not None:
                                confs.append(conf)

                        c = Counter(labels)
                        still = int(c.get("still", 0))
                        walking = int(c.get("walking", 0))
                        in_vehicle = int(c.get("in_vehicle", 0))
                        diversity = shannon_entropy(c.values()) if c else None
                        high_conf = int(sum(1 for x in confs if x >= HIGH_CONF_THRESH)) if confs else None
                        mean_conf = float(sum(confs) / len(confs)) if confs else None

                        row["activity_event_count"] = len(rows)
                        row["active_activity_days"] = n_days
                        row["still_event_count"] = still if labels else None
                        row["walking_event_count"] = walking if labels else None
                        row["in_vehicle_event_count"] = in_vehicle if labels else None
                        row["activity_diversity"] = diversity
                        row["high_confidence_activity_event_count"] = high_conf
                        row["mean_activity_confidence"] = mean_conf

                        agg["activity_label_counter"].update(c)
                        agg["activity_conf_vals"].extend(confs)
                        if confs:
                            agg["high_conf_count"] += int(sum(1 for x in confs if x >= HIGH_CONF_THRESH))

                    row["extraction_status"] = "json_parse_error" if parse_bad > 0 else "ok_has_data"
                    agg["statuses"].append(row["extraction_status"])
                    device_rows.append(row)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    device_df = pd.DataFrame(device_rows)
    device_path = out_dir / "phase1b_device_window_features.csv"
    device_df.to_csv(device_path, index=False)

    subj_info = episodes[["Subject_ID_D", "Subject_ID_N", "n_devices_for_subject"]].drop_duplicates().set_index("Subject_ID_D")
    subj_rows = []

    for (sid_d, wname, table), agg in subj_agg.items():
        sid_n = subj_info.loc[sid_d, "Subject_ID_N"] if sid_d in subj_info.index else ""
        n_dev = subj_info.loc[sid_d, "n_devices_for_subject"] if sid_d in subj_info.index else ""
        n_rows = agg["n_raw_rows"]
        n_days = len(agg["active_days"])

        st = agg["statuses"]
        if any(x == "sql_error" for x in st):
            status = "sql_error"
        elif any(x == "missing_window" for x in st):
            status = "missing_window"
        elif any(x == "json_parse_error" for x in st):
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
            "keyboard_event_count": None,
            "active_keyboard_days": None,
            "keyboard_events_per_active_day": None,
            "touch_event_count": None,
            "active_touch_days": None,
            "touch_events_per_active_day": None,
            "activity_event_count": None,
            "active_activity_days": None,
            "still_event_count": None,
            "walking_event_count": None,
            "in_vehicle_event_count": None,
            "activity_diversity": None,
            "high_confidence_activity_event_count": None,
            "mean_activity_confidence": None,
        }

        # Primary metrics remain missing unless window is valid data (ok_has_data).
        if table == "keyboard" and status == "ok_has_data":
            row["keyboard_event_count"] = n_rows
            row["active_keyboard_days"] = n_days
            row["keyboard_events_per_active_day"] = (n_rows / n_days) if n_days > 0 else None
        elif table == "touch" and status == "ok_has_data":
            row["touch_event_count"] = n_rows
            row["active_touch_days"] = n_days
            row["touch_events_per_active_day"] = (n_rows / n_days) if n_days > 0 else None
        elif table == "plugin_google_activity_recognition" and status == "ok_has_data":
            c = agg["activity_label_counter"]
            confs = agg["activity_conf_vals"]
            row["activity_event_count"] = n_rows
            row["active_activity_days"] = n_days
            row["still_event_count"] = int(c.get("still", 0)) if c else None
            row["walking_event_count"] = int(c.get("walking", 0)) if c else None
            row["in_vehicle_event_count"] = int(c.get("in_vehicle", 0)) if c else None
            row["activity_diversity"] = shannon_entropy(c.values()) if c else None
            row["high_confidence_activity_event_count"] = int(agg["high_conf_count"]) if confs else None
            row["mean_activity_confidence"] = (sum(confs) / len(confs)) if confs else None

        subj_rows.append(row)

    subj_df = pd.DataFrame(subj_rows)
    subj_path = out_dir / "phase1b_subject_window_features.csv"
    subj_df.to_csv(subj_path, index=False)

    # wide
    wide_rows = []
    for sid in sorted(normalize_subject_id_d(x) for x in episodes["Subject_ID_D"].astype(str).unique()):
        sid_n = subj_info.loc[sid, "Subject_ID_N"] if sid in subj_info.index else ""
        out = {"Subject_ID_N": sid_n, "Subject_ID_D": sid}

        def get(table, w):
            q = subj_df[(subj_df["Subject_ID_D"] == sid) & (subj_df["table_name"] == table) & (subj_df["window_name"] == f"{w}_window")]
            return None if q.empty else q.iloc[0]

        def get_primary_or_nan(row, col):
            if row is None:
                return None
            return row[col] if str(row.get("extraction_status")) == "ok_has_data" else None

        # keyboard
        ke, kl = get("keyboard", "early"), get("keyboard", "late")
        out["keyboard_early_event_count"] = get_primary_or_nan(ke, "keyboard_event_count")
        out["keyboard_late_event_count"] = get_primary_or_nan(kl, "keyboard_event_count")
        if pd.notna(out["keyboard_early_event_count"]) and pd.notna(out["keyboard_late_event_count"]):
            e, l = float(ke["keyboard_event_count"]), float(kl["keyboard_event_count"])
            out["keyboard_delta_event_count"] = l - e
            out["keyboard_pct_change_event_count"] = (l - e) / e if e > 0 else None
            out["keyboard_delta_status"] = "ok_both_windows"
        else:
            out["keyboard_delta_event_count"] = None
            out["keyboard_pct_change_event_count"] = None
            out["keyboard_delta_status"] = "missing_early_or_late"

        # touch
        te, tl = get("touch", "early"), get("touch", "late")
        out["touch_early_event_count"] = get_primary_or_nan(te, "touch_event_count")
        out["touch_late_event_count"] = get_primary_or_nan(tl, "touch_event_count")
        if pd.notna(out["touch_early_event_count"]) and pd.notna(out["touch_late_event_count"]):
            e, l = float(te["touch_event_count"]), float(tl["touch_event_count"])
            out["touch_delta_event_count"] = l - e
            out["touch_pct_change_event_count"] = (l - e) / e if e > 0 else None
            out["touch_delta_status"] = "ok_both_windows"
        else:
            out["touch_delta_event_count"] = None
            out["touch_pct_change_event_count"] = None
            out["touch_delta_status"] = "missing_early_or_late"

        # activity
        ae, al = get("plugin_google_activity_recognition", "early"), get("plugin_google_activity_recognition", "late")
        out["activity_early_event_count"] = get_primary_or_nan(ae, "activity_event_count")
        out["activity_late_event_count"] = get_primary_or_nan(al, "activity_event_count")
        out["activity_early_still_event_count"] = get_primary_or_nan(ae, "still_event_count")
        out["activity_late_still_event_count"] = get_primary_or_nan(al, "still_event_count")
        out["activity_early_walking_event_count"] = get_primary_or_nan(ae, "walking_event_count")
        out["activity_late_walking_event_count"] = get_primary_or_nan(al, "walking_event_count")
        out["activity_early_in_vehicle_event_count"] = get_primary_or_nan(ae, "in_vehicle_event_count")
        out["activity_late_in_vehicle_event_count"] = get_primary_or_nan(al, "in_vehicle_event_count")
        out["activity_early_mean_confidence"] = get_primary_or_nan(ae, "mean_activity_confidence")
        out["activity_late_mean_confidence"] = get_primary_or_nan(al, "mean_activity_confidence")

        if pd.notna(out["activity_early_event_count"]) and pd.notna(out["activity_late_event_count"]):
            e, l = float(ae["activity_event_count"]), float(al["activity_event_count"])
            out["activity_delta_event_count"] = l - e
            out["activity_pct_change_event_count"] = (l - e) / e if e > 0 else None
            out["activity_delta_status"] = "ok_both_windows"
        else:
            out["activity_delta_event_count"] = None
            out["activity_pct_change_event_count"] = None
            out["activity_delta_status"] = "missing_early_or_late"

        wide_rows.append(out)

    wide_df = pd.DataFrame(wide_rows)
    wide_path = out_dir / "phase1b_subject_features_wide.csv"
    wide_df.to_csv(wide_path, index=False)

    readme = out_dir / "README_phase1b_extraction.md"
    readme.write_text(
        """# Phase 1B Extraction

First-pass Phase 1B extraction.

Included:
- keyboard (counts/timing only; no raw text fields)
- touch
- plugin_google_activity_recognition

Excluded in this phase:
- gsm/gsm_neighbor/telephony/messages
- screen_state-specific features
- any high-frequency motion tables

Rules:
- early and late windows only
- missing data is not zero activity
- delta/pct_change computed only when both windows are available
"""
    )

    n_subjects = wide_df["Subject_ID_D"].nunique()

    def coverage(prefix):
        e = pd.to_numeric(wide_df[f"{prefix}_early_event_count"], errors="coerce")
        l = pd.to_numeric(wide_df[f"{prefix}_late_event_count"], errors="coerce")
        return int(e.notna().sum()), int(l.notna().sum()), int((e.notna() & l.notna()).sum())

    k_e, k_l, k_b = coverage("keyboard")
    t_e, t_l, t_b = coverage("touch")
    a_e, a_l, a_b = coverage("activity")

    print(f"number_of_subjects_extracted={n_subjects}")
    print(f"keyboard_early_subjects_with_data={k_e}")
    print(f"keyboard_late_subjects_with_data={k_l}")
    print(f"keyboard_subjects_with_both_early_late={k_b}")
    print(f"touch_early_subjects_with_data={t_e}")
    print(f"touch_late_subjects_with_data={t_l}")
    print(f"touch_subjects_with_both_early_late={t_b}")
    print(f"activity_early_subjects_with_data={a_e}")
    print(f"activity_late_subjects_with_data={a_l}")
    print(f"activity_subjects_with_both_early_late={a_b}")

    print("top_10_rows_wide_features:")
    print(wide_df.head(10).to_string(index=False))

    print("generated_files:")
    print(f"- {device_path}")
    print(f"- {subj_path}")
    print(f"- {wide_path}")
    print(f"- {readme}")


if __name__ == "__main__":
    main()
