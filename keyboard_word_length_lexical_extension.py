"""Privacy-safe Word-Length and Lexical Diversity extension.

The SensorDB keyboard table contains text-state snapshots, not key events. This
script keeps text and normalized tokens in memory only and stages aggregate JSON
for Artifact Tool export. It never writes raw text, words, vocabularies, hashes,
or excerpts. Existing keyboard outputs are untouched.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from main import connect_sensordata_db
from keyboard_deep_dive import T1_STATUS, T2_STATUS, fetch_keyboard_rows, load_windows, local_timestamp, parse_json, text_value, BURST_GAP_MS, LONG_PAUSE_MS

ROOT = Path(__file__).resolve().parent
STAGE = Path("/tmp/keyboard_extension_20261021")
TZ = "Asia/Jerusalem"
BOUNDARIES = {"morning": (6, 12), "afternoon": (12, 18), "evening": (18, 24), "night": (0, 6)}
DELIM_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)
DELIMITER_RE = re.compile(r"[\s\.,!?;:()\[\]{}\"'“”‘’/\\<>|+=_*~`@#$%^&-]")
SEED = 20261021


def clean(v: Any):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    return v


def sanitize(v: Any):
    """Convert pandas/numpy missing values to JSON null recursively."""
    if isinstance(v, dict):
        return {str(k): sanitize(val) for k, val in v.items()}
    if isinstance(v, list):
        return [sanitize(x) for x in v]
    if isinstance(v, (np.floating, float)) and not math.isfinite(float(v)):
        return None
    if v is pd.NA or v is pd.NaT:
        return None
    if isinstance(v, (np.integer, np.floating)):
        return v.item()
    return v


def norm_token(s: str) -> str:
    return unicodedata.normalize("NFKC", s).casefold()


def language_group(token: str) -> str:
    has_hebrew = any("HEBREW" in unicodedata.name(c, "") for c in token)
    has_latin = any("LATIN" in unicodedata.name(c, "") for c in token)
    if has_hebrew and has_latin:
        return "mixed"
    if has_hebrew:
        return "hebrew"
    if has_latin:
        return "latin"
    return "other"


def bucket(ts: int) -> str:
    h = local_timestamp(ts).hour
    return next(k for k, (lo, hi) in BOUNDARIES.items() if lo <= h < hi)


def parse_events(rows: list[dict[str, Any]]):
    events, seen = [], set(); parse_errors = 0; password_rows = 0
    for row in rows:
        obj = parse_json(row.get("data"))
        if obj is None:
            parse_errors += 1; continue
        ts = pd.to_numeric(row.get("timestamp"), errors="coerce")
        if pd.isna(ts): continue
        password = str(obj.get("is_password") or "").strip()
        if password.lower() in {"1", "true", "yes", "y"}:
            password_rows += 1; continue
        before = text_value(obj.get("before_text")); current = text_value(obj.get("current_text"))
        device = str(row.get("device_id") or ""); package = str(obj.get("package_name") or "").strip()
        key = (int(ts), device, before, current, package, password)
        if key in seen: continue
        seen.add(key)
        events.append({"timestamp": int(ts), "device": device, "package": package, "before": before, "current": current})
    events.sort(key=lambda e: (e["device"], e["package"], e["timestamp"]))
    return events, len(rows) - len(events) - parse_errors - password_rows, parse_errors, password_rows


def robust_stats(vals: list[float], prefix: str):
    if not vals:
        return {f"{prefix}_{k}": None for k in ("mean_ms", "median_ms", "sd_ms", "iqr_ms", "mad_ms", "cv")}
    a = np.asarray(vals, dtype=float); mean = float(a.mean()); q25, q75 = np.quantile(a, [.25, .75])
    return {f"{prefix}_mean_ms": float(a.mean()), f"{prefix}_median_ms": float(np.median(a)),
            f"{prefix}_sd_ms": float(a.std(ddof=1)) if len(a) > 1 else None, f"{prefix}_iqr_ms": float(q75-q25),
            f"{prefix}_mad_ms": float(np.median(np.abs(a-np.median(a)))), f"{prefix}_cv": float(a.std(ddof=1)/mean) if len(a)>1 and mean>0 else None}


def mattr(tokens: list[str], window: int) -> float | None:
    if len(tokens) < window: return None
    vals = [len(set(tokens[i:i+window]))/window for i in range(len(tokens)-window+1)]
    return float(np.mean(vals)) if vals else None


def mtld(tokens: list[str], threshold=.72) -> float | None:
    if len(tokens) < 100: return None
    factors = 0.0; start = 0; types = set()
    for i, tok in enumerate(tokens, 1):
        types.add(tok)
        if len(types)/i <= threshold:
            factors += 1; start = i; types = set()
    remainder = len(tokens)-start
    if remainder: factors += (1 - len(types)/remainder) / (1-threshold) if remainder else 0
    return float(len(tokens)/factors) if factors else None


def completed_word(current: str) -> str | None:
    words = DELIM_RE.findall(current)
    return norm_token(words[-1]) if words else None


def extract_window(events: list[dict[str, Any]], sid: str, window: str, start: int, end: int, raw_rows: int, duplicates: int, parse_errors: int, password_rows: int):
    groups = defaultdict(list)
    for e in events: groups[(e["device"], e["package"])].append(e)
    comps = []; tokens: list[str] = []; days = set(); obs_by_day = Counter(); packages = set(); devices = set()
    continuity_breaks = 0; multi_char_jumps = 0; repeated_states = 0; incomplete_starts = 0; correction_events = 0; paste_like = 0
    valid_intervals = 0; long_pauses = 0; bursts = 0; active_minutes = 0.0
    daily_tokens = Counter(); daily_words = defaultdict(list); time_tokens = defaultdict(list)
    for (device, package), group in groups.items():
        packages.add(package); devices.add(device); bursts += 1
        if not group: continue
        burst_start = group[0]["timestamp"]; previous = None; candidate = None
        for event in group:
            ts = event["timestamp"]; day = str(local_timestamp(ts).date()); days.add(day); obs_by_day[day] += 1
            if previous is not None:
                d = ts - previous["timestamp"]
                if d > BURST_GAP_MS:
                    active_minutes += max(0, previous["timestamp"]-burst_start)/60000.; burst_start=ts
                    if candidate is not None: incomplete_starts += 1
                    candidate = None
                elif d > 0:
                    valid_intervals += 1
                    if d > LONG_PAUSE_MS: long_pauses += 1
            before, current = event["before"], event["current"]
            if previous is not None:
                continuity = previous["current"] == before
                if not continuity:
                    continuity_breaks += 1
                    if candidate is not None: candidate["ambiguous"] = True
            else:
                continuity = False
            if previous is not None and previous["current"] == current and previous["before"] == before:
                repeated_states += 1
            is_append = current.startswith(before) and len(current) >= len(before)
            jump = len(current) - len(before) if is_append else 0
            if jump > 1: multi_char_jumps += 1
            if not is_append and current != before: correction_events += 1
            if jump >= 3 and is_append: paste_like += 1
            ends_delim = bool(current) and bool(DELIMITER_RE.search(current[-1]))
            before_ends_delim = bool(before) and bool(DELIMITER_RE.search(before[-1]))
            starts_word = bool(current.strip()) and not ends_delim and (before == "" or before_ends_delim)
            if starts_word and is_append:
                candidate = {"start_ts": ts, "boundary": True, "continuous": continuity or previous is None, "append_only": True, "interrupted": False, "text": current}
            elif candidate is not None:
                candidate["continuous"] &= continuity
                candidate["append_only"] &= is_append
                candidate["text"] = current
                if previous is not None and d > LONG_PAUSE_MS and d <= BURST_GAP_MS: candidate["interrupted"] = True
            if candidate is not None and ends_delim and not before_ends_delim:
                token = completed_word(current)
                if token:
                    duration = max(0, ts-candidate["start_ts"]); length = len(token); lang=language_group(token)
                    quality = "reliable_continuous" if candidate["boundary"] and candidate["continuous"] and candidate["append_only"] and not candidate["interrupted"] else "ambiguous"
                    comps.append({"duration_ms": float(duration), "length": length, "bucket": bucket(ts), "day": day, "token": token, "language": lang, "quality": quality, "multi_char": jump > 1})
                    if quality == "reliable_continuous":
                        tokens.append(token); daily_tokens[day]+=1; daily_words[day].append(token); time_tokens[bucket(ts)].append(token)
                candidate = None
            previous = event
        if previous is not None:
            active_minutes += max(0, previous["timestamp"]-burst_start)/60000.
            if candidate is not None: incomplete_starts += 1
    reliable = [c for c in comps if c["quality"] == "reliable_continuous"]
    durations = [c["duration_ms"] for c in reliable]; lengths = [c["length"] for c in reliable]
    row = {"Subject_ID_D": sid, "window_name": window, "window_start_ms": start, "window_end_ms": end,
           "raw_rows_in_window": raw_rows, "distinct_observations_in_window": len(events), "duplicate_rows_removed": duplicates,
           "json_parse_errors": parse_errors, "password_rows_excluded": password_rows, "active_days": len(days), "active_minutes": active_minutes,
           "valid_interval_count": valid_intervals, "long_pause_count_2s": long_pauses, "unique_package_count": len(packages), "unique_device_count": len(devices),
           "reconstructed_completion_count_all": len(comps), "reliable_completion_count": len(reliable), "ambiguous_completion_count": sum(c["quality"]=="ambiguous" for c in comps),
           "reliable_fraction": len(reliable)/len(comps) if comps else None, "continuity_break_count": continuity_breaks, "multi_character_jump_count": multi_char_jumps,
           "repeated_state_count": repeated_states, "incomplete_word_start_count": incomplete_starts, "correction_transition_count": correction_events, "paste_like_jump_count": paste_like,
           "word_token_count": len(tokens), "word_type_count": len(set(tokens)), "word_ttr": len(set(tokens))/len(tokens) if tokens else None,
           "word_repetition_rate": 1-len(set(tokens))/len(tokens) if tokens else None, "word_mean_length_chars": float(np.mean(lengths)) if lengths else None,
           "word_median_length_chars": float(np.median(lengths)) if lengths else None, "word_length_sd_chars": float(np.std(lengths,ddof=1)) if len(lengths)>1 else None,
           "word_mattr_50": mattr(tokens,50), "word_mattr_100": mattr(tokens,100), "word_mtld": mtld(tokens),
           "language_latin_token_count": sum(c["language"]=="latin" for c in reliable), "language_hebrew_token_count": sum(c["language"]=="hebrew" for c in reliable),
           "language_mixed_token_count": sum(c["language"]=="mixed" for c in reliable), "language_other_token_count": sum(c["language"]=="other" for c in reliable)}
    row.update(robust_stats(durations, "completion")); row["completion_per_character_median_ms"] = float(np.median([d/l for d,l in zip(durations,lengths) if l])) if durations else None
    for lo, hi, name in [(2,3,"len_2_3"),(4,5,"len_4_5"),(6,8,"len_6_8"),(9,10**9,"len_9_plus")]:
        vals=[c["duration_ms"] for c in reliable if lo<=c["length"]<=hi]
        row[f"{name}_count"]=len(vals); row.update(robust_stats(vals,name))
    groups_iqr=[row[f"{name}_iqr_ms"] for name in ("len_2_3","len_4_5","len_6_8","len_9_plus") if row[f"{name}_iqr_ms"] is not None]
    row["length_adjusted_iqr_equal_group_median_ms"] = float(np.median(groups_iqr)) if groups_iqr else None
    if len(reliable)>=20 and len(set(lengths))>=3:
        X=np.column_stack([np.ones(len(lengths)), np.asarray(lengths,float), np.asarray(lengths,float)**2]); y=np.asarray(durations,float); beta=np.linalg.lstsq(X,y,rcond=None)[0]; resid=y-X@beta; row["length_residual_sd_ms"]=float(np.std(resid,ddof=1)); row["length_residual_iqr_ms"]=float(np.quantile(resid,.75)-np.quantile(resid,.25))
    else: row["length_residual_sd_ms"]=None; row["length_residual_iqr_ms"]=None
    rng=np.random.default_rng(SEED+int(sid) if str(sid).isdigit() else SEED)
    if len(tokens)>=50:
        vals=[]
        for _ in range(20):
            ss=list(rng.choice(tokens,size=min(50,len(tokens)),replace=False)); vals.append(len(set(ss))/len(ss))
        row["ttr50_subsample_sd"]=float(np.std(vals,ddof=1))
    else: row["ttr50_subsample_sd"]=None
    daily=[]
    for day in sorted(obs_by_day):
        ts=daily_words[day]; daily.append({"Subject_ID_D":sid,"window_name":window,"local_date":day,"distinct_observations":obs_by_day[day],"reliable_word_token_count":len(ts),"word_type_count":len(set(ts)),"word_ttr":len(set(ts))/len(ts) if ts else None,"word_mattr_50":mattr(ts,50)})
    quality=[{"Subject_ID_D":sid,"window_name":window,"quality_class":q,"count":sum(c["quality"]==q for c in comps)} for q in ("reliable_continuous","ambiguous")]
    return row,daily,quality


def build_stage():
    STAGE.mkdir(parents=True,exist_ok=True); conn=connect_sensordata_db(); rows=[]; daily=[]; quality=[]
    try:
        specs=pd.concat([load_windows(T1_STATUS,"T1"),load_windows(T2_STATUS,"T2")],ignore_index=True)
        for _,s in specs.iterrows():
            sid=str(s.Subject_ID_D); start=int(float(s.window_start_ms)); end=int(float(s.window_end_ms)); devices=[x for x in str(s.get("device_ids_used") or "").split(";") if x and x.lower()!="nan"]
            raw=fetch_keyboard_rows(conn,devices,start,end); events,dup,err,pw=parse_events(raw); w,d,q=extract_window(events,sid,str(s.window_name),start,end,len(raw),dup,err,pw); rows.append(w); daily.extend(d); quality.extend(q)
            print(f"{sid} {s.window_name}: raw={len(raw)} obs={len(events)} reliable_words={w['reliable_completion_count']}",flush=True)
    finally: conn.close()
    wf=pd.DataFrame(rows); df=pd.DataFrame(daily); qf=pd.DataFrame(quality)
    # Patient-level T1/T2 deltas contain only numeric aggregate fields.
    metric=[c for c in wf.columns if c not in {"Subject_ID_D","window_name","window_start_ms","window_end_ms"} and pd.api.types.is_numeric_dtype(wf[c])]
    t1=wf[wf.window_name.eq("T1")][["Subject_ID_D",*metric]].rename(columns={c:f"{c}_T1" for c in metric}); t2=wf[wf.window_name.eq("T2")][["Subject_ID_D",*metric]].rename(columns={c:f"{c}_T2" for c in metric}); pt=t1.merge(t2,on="Subject_ID_D",how="outer")
    for c in metric: pt[f"{c}_delta"]=pd.to_numeric(pt[f"{c}_T2"],errors="coerce")-pd.to_numeric(pt[f"{c}_T1"],errors="coerce")
    cog=pd.read_csv(ROOT/"output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv",dtype={"Subject_ID_D":str}); pt=pt.merge(cog,on="Subject_ID_D",how="left")
    # Association is gated: only run if >=20 paired patients with >=100 reliable tokens in each window.
    paired=pt[(pt.reliable_completion_count_T1>=100)&(pt.reliable_completion_count_T2>=100)&pt.global_delta.notna()].copy(); gate={"paired_patients_min100_tokens_each_window":int(len(paired)),"gate_passed":bool(len(paired)>=20),"threshold":">=100 reliable continuous tokens in both T1 and T2"}
    assoc=[]
    if gate["gate_passed"]:
        for f in ["length_adjusted_iqr_equal_group_median_ms_delta","length_residual_iqr_ms_delta","completion_iqr_ms_delta","word_ttr_delta","word_mattr_50_delta","word_mtld_delta"]:
            z=paired[[f,"global_delta"]].replace([np.inf,-np.inf],np.nan).dropna()
            if len(z)>=12 and z[f].nunique()>2:
                rho,p=spearmanr(z[f],z.global_delta); assoc.append({"feature_name":f,"outcome":"global_delta","n":len(z),"spearman_rho":float(rho),"spearman_p":float(p)})
    # Literature is static and separately identified; no claims are made from search snippets.
    literature=[
      {"citation":"McCarthy & Jarvis (2010), Behavior Research Methods","doi":"10.3758/BRM.42.2.381","url":"https://pubmed.ncbi.nlm.nih.gov/20479170/","population_method":"Validation study of MTLD, vocd-D and HD-D on language samples","finding":"MTLD was evaluated as a length-robust lexical-diversity measure","limitation":"Not passive smartphone typing or cognitive decline."},
      {"citation":"Covington & McFall (2010), Journal of Quantitative Linguistics","doi":"10.1080/09296171003643098","url":"https://doi.org/10.1080/09296171003643098","population_method":"Introduced moving-average TTR (MATTR)","finding":"Moving windows reduce the length dependence of ordinary TTR","limitation":"Requires enough observed tokens and does not solve snapshot reconstruction bias."},
      {"citation":"Vizer et al. (2020), Frontiers in Digital Health","doi":"10.3389/fdgth.2020.567158","url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC8521910/","population_method":"MCI vs healthy controls using natural-language and touchscreen-typing features","finding":"Lexical richness/repetition and typing features contributed to classification","limitation":"Spontaneous text processing still requires reliable text tokens; not equivalent to this SensorDB snapshot schema."},
      {"citation":"Kampman et al. (2022), Multiple Sclerosis Journal: Experimental, Translational and Clinical","doi":"10.1177/20552173221139584","url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC9679948/","population_method":"Longitudinal passive smartphone keystroke dynamics in 102 people with MS","finding":"Timing features were associated with arm function and processing speed","limitation":"Used true keystroke metadata, so timing is not directly comparable to text-state snapshots."},
      {"citation":"Shen et al. (2025), Alzheimer's & Dementia, 21(S2):e107368","doi":"10.1002/alz70856_107368","url":"https://alz-journals.onlinelibrary.wiley.com/doi/10.1002/alz70856_107368","population_method":"21 older adults with one year of passive multimodal smartphone sensing","finding":"Preliminary typing variability differences separated cognitively normal from MCI/dementia participants","limitation":"Conference abstract, small cohort, and keystroke measures differ from this text-state database."},
      {"citation":"Petriglia et al. (2025), Research Methods in Medicine & Health Sciences, 4:100276","doi":"10.1016/j.rmal.2025.100276","url":"https://www.sciencedirect.com/science/article/pii/S2772766125000977","population_method":"Lexical-diversity measures in 251 adults aged 25–89","finding":"Age-related lexical-diversity decline varied by metric; MATTR/MTLD effects were smaller or inconsistent","limitation":"Language samples, not passive typing; supports metric caution rather than a clinical claim."}
    ]
    feature_dict=[
      {"feature_name":"length_adjusted_iqr_equal_group_median_ms","family":"word_length_adjusted","definition":"Median of within-length-group completion-time IQRs across 2–3, 4–5, 6–8, 9+ character groups with data","units":"ms","privacy":"aggregate only","status":"exploratory"},
      {"feature_name":"length_residual_iqr_ms","family":"word_length_adjusted","definition":"IQR of residuals from within-window duration ~ length + length², only with ≥20 reliable completions","units":"ms","privacy":"aggregate only","status":"exploratory"},
      {"feature_name":"word_ttr","family":"lexical","definition":"unique normalized observable completed tokens / reliable completed tokens","units":"ratio","privacy":"aggregate only","status":"feasibility"},
      {"feature_name":"word_mattr_50","family":"lexical","definition":"mean type-token ratio over fixed 50-token moving windows","units":"ratio","privacy":"aggregate only","status":"feasibility"},
      {"feature_name":"word_mattr_100","family":"lexical","definition":"mean type-token ratio over fixed 100-token moving windows","units":"ratio","privacy":"aggregate only","status":"feasibility"},
      {"feature_name":"word_mtld","family":"lexical","definition":"MTLD factor-based lexical-diversity estimate, only when ≥100 tokens","units":"tokens per factor","privacy":"aggregate only","status":"feasibility"},
      {"feature_name":"word_repetition_rate","family":"lexical","definition":"1 − unique normalized token count / token count","units":"ratio","privacy":"aggregate only","status":"feasibility"},
    ]
    privacy=[{"check":"raw_text_export","result":"pass","implementation":"text and tokens are local variables only; no raw text/words/hashes in staged payload"},{"check":"password_exclusion","result":"pass","implementation":"is_password truthy rows excluded before transition inspection"},{"check":"patient_vocab_export","result":"pass","implementation":"unique set discarded after aggregate window summaries"},{"check":"raw_logging","result":"pass","implementation":"progress logs include only patient/window IDs and numeric counts"},{"check":"snapshot_overlap","result":"measured","implementation":"exact previous.current versus next.before continuity count exported"}]
    comparison=[{"existing_feature":"word_completion_iqr_ms","new_feature":"length_adjusted_iqr_equal_group_median_ms","comparison":"same snapshot completion candidates; new feature equalizes length groups","limitation":"both remain observable snapshot timing"},{"existing_feature":"word_completion_iqr_ms","new_feature":"length_residual_iqr_ms","comparison":"same candidates after within-window length adjustment","limitation":"residual model is descriptive and requires ≥20 candidates"},{"existing_feature":"word_completion_count/high_confidence_fraction","new_feature":"word_ttr/MATTR/MTLD","comparison":"new lexical metrics use only reliable completed tokens and report quantity","limitation":"language/app mix and text quantity can dominate"}]
    payload={"word_length_windows":wf.to_dict("records"),"word_length_daily":df.to_dict("records"),"quality":qf.to_dict("records"),"patient_table":pt.to_dict("records"),"feature_dictionary":feature_dict,"supervisor_results":assoc,"privacy_report":privacy,"literature_review":literature,"comparison":comparison,"gate":gate,"manifest":{"version":"20261021_v1","raw_text_persisted":False,"existing_outputs_modified":False,"models_trained":False,"new_cognitive_screen_run":bool(assoc)}}
    (STAGE/"payload.json").write_text(json.dumps(sanitize(payload),ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"windows":len(wf),"daily":len(df),"quality":len(qf),"patients":len(pt),"gate":gate,"stage":str(STAGE/"payload.json")},indent=2))


if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--run",action="store_true")
    args=ap.parse_args()
    if not args.run: raise SystemExit("Use --run to perform authorized raw extraction; no files are overwritten.")
    build_stage()
