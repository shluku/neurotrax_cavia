"""Privacy-safe word-completion timing audit and exploratory feature extraction.

Keyboard rows contain text-state snapshots rather than key events.  This script
therefore reports *observable* completion time: the elapsed time from the first
snapshot after an empty/space boundary to a later snapshot ending in a space.
Raw text is held in memory only and is never written to disk.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, t

from main import connect_sensordata_db
from keyboard_deep_dive import (BURST_GAP_MS, LONG_PAUSE_MS, TZ, T1_STATUS,
                                T2_STATUS, fetch_keyboard_rows, load_windows,
                                local_timestamp, parse_json, text_value)

ROOT = Path(__file__).parent
OUT = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/word_completion_timing_v1"
T1_WIDE = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"
SEED = 20261021
BOUNDARIES = {"morning": (6, 12), "afternoon": (12, 18), "evening": (18, 24), "night": (0, 6)}


def normalize_id(v: Any) -> str:
    s = str(v).strip()
    return s.zfill(3) if s.isdigit() else s


def robust_mad(a: np.ndarray) -> float:
    m = np.median(a)
    return float(np.median(np.abs(a - m)))


def stats(values: list[float], prefix: str) -> dict[str, Any]:
    if not values:
        return {f"{prefix}_{k}": pd.NA for k in ("mean_ms", "median_ms", "sd_ms", "iqr_ms", "mad_ms", "p10_ms", "p90_ms", "cv")}
    a = np.asarray(values, dtype=float)
    mean = float(a.mean())
    return {
        f"{prefix}_mean_ms": mean,
        f"{prefix}_median_ms": float(np.median(a)),
        f"{prefix}_sd_ms": float(a.std(ddof=1)) if len(a) > 1 else pd.NA,
        f"{prefix}_iqr_ms": float(np.quantile(a, .75) - np.quantile(a, .25)),
        f"{prefix}_mad_ms": robust_mad(a),
        f"{prefix}_p10_ms": float(np.quantile(a, .10)),
        f"{prefix}_p90_ms": float(np.quantile(a, .90)),
        f"{prefix}_cv": float(a.std(ddof=1) / mean) if len(a) > 1 and mean > 0 else pd.NA,
    }


def parse_events(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    """Parse and deduplicate rows; text values do not leave this function."""
    out, seen = [], set(); errors = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            errors += 1; continue
        ts = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if pd.isna(ts):
            continue
        before = text_value(obj.get("before_text")); current = text_value(obj.get("current_text"))
        device = str(row.get("device_id") or ""); package = str(obj.get("package_name") or "").strip()
        password = str(obj.get("is_password") or "").strip()
        if password.lower() in {"1", "true", "yes", "y"}:
            # Password-state snapshots are excluded before any text transition is inspected.
            continue
        key = (int(ts), device, before, current, package, password)
        if key in seen: continue
        seen.add(key)
        out.append({"timestamp": int(ts), "device": device, "package": package,
                    "before": before, "current": current, "is_password": password})
    out.sort(key=lambda e: (e["device"], e["package"], e["timestamp"]))
    return out, len(rows) - len(out) - errors, errors


def bucket(ts: int) -> str:
    h = local_timestamp(ts).hour
    return next(k for k, (lo, hi) in BOUNDARIES.items() if lo <= h < hi)


def extract(events: list[dict[str, Any]], sid: str, window: str, start: int, end: int,
            raw_rows: int, duplicates: int, parse_errors: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return window, daily, and quality summaries.  No text is emitted."""
    groups = defaultdict(list)
    for e in events: groups[(e["device"], e["package"])].append(e)
    completions: list[dict[str, Any]] = []
    valid_intervals = 0; long_pauses = 0; active_minutes = 0.; days = set(); packages = set()
    obs_by_day = defaultdict(int)
    for (device, package), group in groups.items():
        packages.add(package)
        if not group: continue
        burst_start = group[0]["timestamp"]; previous = group[0]; word_start = None
        word_start_kind = None; append_only = True; interrupted = False; edits = False
        for event in group:
            ts = event["timestamp"]; days.add(local_timestamp(ts).date()); obs_by_day[str(local_timestamp(ts).date())] += 1
            if event is not group[0]:
                d = ts - previous["timestamp"]
                if d > BURST_GAP_MS:
                    active_minutes += max(0, previous["timestamp"] - burst_start) / 60000.; burst_start = ts
                    word_start = None; word_start_kind = None; append_only = True; interrupted = True
                elif d > 0:
                    valid_intervals += 1
                    if d > LONG_PAUSE_MS: long_pauses += 1; interrupted = True
            before, current = event["before"], event["current"]
            is_append = current.startswith(before) and len(current) >= len(before)
            if not is_append: edits = True; append_only = False
            # Existing proxy starts at first observable non-space state and closes at space.
            if word_start is None and current.strip() and not current.endswith(" "):
                word_start = ts
                word_start_kind = "boundary" if (before == "" or before.endswith(" ")) else "partial_start"
                append_only = is_append
                interrupted = False
            if before.endswith(" ") and current.strip() and not current.endswith(" "):
                word_start = ts; word_start_kind = "boundary"; append_only = is_append; interrupted = False
            if word_start is not None and current.endswith(" ") and not before.endswith(" "):
                duration = ts - word_start
                if duration >= 0:
                    quality = "high_confidence_observable" if word_start_kind == "boundary" and append_only and not edits and not interrupted else "ambiguous_edit_or_gap"
                    if word_start_kind == "partial_start": quality = "partial_start"
                    completions.append({"timestamp": ts, "duration_ms": float(duration), "quality": quality,
                                        "word_len_proxy": max(0, len(current.rstrip()) - len(before.rstrip())),
                                        "bucket": bucket(ts), "day": str(local_timestamp(ts).date()),
                                        "device": device, "package": package})
                word_start = None; word_start_kind = None; append_only = True; interrupted = False; edits = False
            previous = event
        active_minutes += max(0, previous["timestamp"] - burst_start) / 60000.
    high = [c for c in completions if c["quality"] == "high_confidence_observable"]
    vals = [c["duration_ms"] for c in high]
    row = {"Subject_ID_D": sid, "window_name": window, "window_start_ms": start, "window_end_ms": end,
           "raw_rows_in_window": raw_rows, "distinct_observations_in_window": len(events),
           "duplicate_rows_removed": duplicates, "json_parse_errors": parse_errors,
           "active_days": len(days), "active_minutes": active_minutes, "valid_interval_count": valid_intervals,
           "long_pause_count_2s": long_pauses, "snapshot_rate_per_active_minute": len(events)/active_minutes if active_minutes else pd.NA,
           "unique_package_count": len(packages), "word_completion_count_all": len(completions),
           "word_completion_count_high_confidence": len(high),
           "word_completion_count_partial": sum(c["quality"] == "partial_start" for c in completions),
           "word_completion_count_ambiguous": sum(c["quality"] == "ambiguous_edit_or_gap" for c in completions),
           "high_confidence_fraction": len(high)/len(completions) if completions else pd.NA,
           "word_completion_days": len({c["day"] for c in high}),
           "word_completion_rate_per_active_minute": len(high)/active_minutes if active_minutes else pd.NA}
    row.update(stats(vals, "word_completion"))
    for b in BOUNDARIES:
        row.update(stats([c["duration_ms"] for c in high if c["bucket"] == b], f"word_completion_{b}"))
    # Per-day rows are aggregates only; no words or text are saved.
    daily = []
    for day in sorted(obs_by_day):
        dc = [c for c in high if c["day"] == day]
        drow = {"Subject_ID_D": sid, "window_name": window, "local_date": day,
                "distinct_observations": obs_by_day[day], "word_completion_count_high_confidence": len(dc)}
        drow.update(stats([c["duration_ms"] for c in dc], "word_completion")); daily.append(drow)
    quality = [{"Subject_ID_D": sid, "window_name": window, "quality_class": q,
                "count": sum(c["quality"] == q for c in completions)}
               for q in ("high_confidence_observable", "partial_start", "ambiguous_edit_or_gap")]
    return row, daily, quality


def bh(p: pd.Series) -> np.ndarray:
    a = p.to_numpy(float); q = np.full(len(a), np.nan); ok = np.isfinite(a)
    if ok.any():
        idx = np.where(ok)[0]; order = idx[np.argsort(a[idx])]; adj = a[order] * len(order) / np.arange(1, len(order)+1)
        adj = np.minimum.accumulate(adj[::-1])[::-1]; q[order] = np.minimum(adj, 1.)
    return q


def association(data: pd.DataFrame, features: list[str], outcomes: dict[str, str], scope: str) -> pd.DataFrame:
    rows = []; rng = np.random.default_rng(SEED + (1 if scope == "delta" else 0))
    for outname, ycol in outcomes.items():
        for f in features:
            x = pd.to_numeric(data[f], errors="coerce"); y = pd.to_numeric(data[ycol], errors="coerce")
            z = pd.concat([x.rename("x"), y.rename("y")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
            if len(z) < 12 or z.x.nunique() < 3 or z.y.nunique() < 3: continue
            rho, p = spearmanr(z.x, z.y); boots=[]
            for _ in range(500):
                ix = rng.integers(0, len(z), len(z)); boots.append(spearmanr(z.x.iloc[ix], z.y.iloc[ix]).statistic)
            rows.append({"scope": scope, "outcome": outname, "feature_name": f, "n": len(z),
                         "spearman_rho": float(rho), "spearman_p": float(p),
                         "bootstrap_ci_low": float(np.nanpercentile(boots, 2.5)), "bootstrap_ci_high": float(np.nanpercentile(boots, 97.5))})
    out = pd.DataFrame(rows)
    if not out.empty: out["fdr_q"] = bh(out["spearman_p"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--out-dir", default=str(OUT)); ap.add_argument("--no-db", action="store_true")
    args = ap.parse_args(); out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    if args.no_db: raise SystemExit("--no-db is reserved for inspection; raw extraction is required")
    conn = connect_sensordata_db(); windows=[]; daily=[]; quality=[]
    try:
        specs = pd.concat([load_windows(T1_STATUS, "T1"), load_windows(T2_STATUS, "T2")], ignore_index=True)
        for _, s in specs.iterrows():
            sid = normalize_id(s.Subject_ID_D); start=int(float(s.window_start_ms)); end=int(float(s.window_end_ms))
            devices=[x for x in str(s.get("device_ids_used") or "").split(";") if x and x.lower() != "nan"]
            raw=fetch_keyboard_rows(conn, devices, start, end); events, dup, err=parse_events(raw)
            w,d,q=extract(events,sid,str(s.window_name),start,end,len(raw),dup,err); windows.append(w); daily.extend(d); quality.extend(q)
            print(f"{sid} {s.window_name}: raw={len(raw)} observations={len(events)} words={w['word_completion_count_high_confidence']}", flush=True)
    finally: conn.close()
    wf=pd.DataFrame(windows); df=pd.DataFrame(daily); qf=pd.DataFrame(quality)
    # Daily and weekly stability/trend summaries are calculated from aggregates.
    if not df.empty:
        df["local_date_dt"] = pd.to_datetime(df["local_date"])
        trend_rows=[]
        for (sid, win), g in df.groupby(["Subject_ID_D", "window_name"]):
            g=g.sort_values("local_date_dt"); med=pd.to_numeric(g["word_completion_median_ms"],errors="coerce").dropna()
            x=(g.loc[med.index,"local_date_dt"]-g.loc[med.index,"local_date_dt"].min()).dt.days.to_numpy(float)
            y=med.to_numpy(float)
            slope=float(np.polyfit(x,y,1)[0]) if len(y)>=3 and np.ptp(x)>0 else pd.NA
            iso=g.assign(week=g.local_date_dt.dt.isocalendar().week.astype(int)).groupby("week")["word_completion_count_high_confidence"].sum()
            trend_rows.append({"Subject_ID_D":sid,"window_name":win,
                               "word_completion_daily_median_sd_ms":float(np.std(y,ddof=1)) if len(y)>1 else pd.NA,
                               "word_completion_daily_median_slope_ms_per_day":slope,
                               "word_completion_weekly_count_sd":float(iso.std(ddof=1)) if len(iso)>1 else pd.NA,
                               "word_completion_week_count":int(len(iso))})
        wf=wf.merge(pd.DataFrame(trend_rows),on=["Subject_ID_D","window_name"],how="left")
    else:
        for c in ("word_completion_daily_median_sd_ms","word_completion_daily_median_slope_ms_per_day","word_completion_weekly_count_sd","word_completion_week_count"): wf[c]=pd.NA
    if "local_date_dt" in df: df=df.drop(columns=["local_date_dt"])
    wf.to_csv(out/"word_completion_window_features.csv", index=False); df.to_csv(out/"word_completion_daily_features.csv", index=False); qf.to_csv(out/"word_completion_quality_summary.csv", index=False)
    # Patient-level T1/T2 deltas and saved cognitive outcomes.
    cog=pd.read_csv(T1_WIDE, dtype={"Subject_ID_D": str}); cog["Subject_ID_D"]=cog["Subject_ID_D"].map(normalize_id)
    t1=wf[wf.window_name.eq("T1")].copy(); t2=wf[wf.window_name.eq("T2")].copy()
    metric_cols=[c for c in wf.columns if c.startswith("word_completion_") and (c.endswith("_ms") or c.endswith("_cv") or c.endswith("_minute"))] + ["high_confidence_fraction","snapshot_rate_per_active_minute","active_days","valid_interval_count","distinct_observations_in_window"]
    p=t1[["Subject_ID_D",*metric_cols]].rename(columns={c:f"{c}_T1" for c in metric_cols}).merge(t2[["Subject_ID_D",*metric_cols]].rename(columns={c:f"{c}_T2" for c in metric_cols}),on="Subject_ID_D",how="outer")
    for c in metric_cols: p[f"{c}_delta"]=pd.to_numeric(p[f"{c}_T2"],errors="coerce")-pd.to_numeric(p[f"{c}_T1"],errors="coerce")
    p=p.merge(cog,on="Subject_ID_D",how="left"); p.to_csv(out/"word_completion_patient_table.csv",index=False)
    feats=[c+"_T1" for c in metric_cols if c.startswith("word_completion_")] + [c+"_delta" for c in metric_cols if c.startswith("word_completion_")]
    outcomes={"Global_T1":"global_T1","Memory_T1":"memory_T1","Executive_Function_T1":"ef_T1","Attention_T1":"attention_T1","Global_delta":"global_delta","Executive_Function_delta":"ef_delta","Attention_delta":"attention_delta"}
    assoc=pd.concat([association(p, [f for f in feats if f.endswith("_T1")], {k:v for k,v in outcomes.items() if k.endswith("_T1")}, "T1"), association(p,[f for f in feats if f.endswith("_delta")],{k:v for k,v in outcomes.items() if k.endswith("delta")},"delta")],ignore_index=True)
    assoc.to_csv(out/"word_completion_cognitive_associations.csv",index=False)
    manifest={"status":"complete","windows":len(wf),"daily_rows":len(df),"patients_with_T1":int(t1.Subject_ID_D.nunique()),"patients_with_T2":int(t2.Subject_ID_D.nunique()),"privacy":"raw text retained only in memory; no words exported","timing_interpretation":"observable snapshot timing, not keystroke timing","historical_outputs_modified":False,"model_integration":False}
    (out/"word_completion_manifest.json").write_text(json.dumps(manifest,indent=2)); print(json.dumps(manifest,indent=2))


if __name__ == "__main__": main()
