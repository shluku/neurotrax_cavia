"""Investigate lower T2 keyboard reliability without fitting predictive models.

All thresholds are measurement-based and declared in THRESHOLDS before any
cognitive outcome is used. Outputs are isolated from the original discovery
and validation directories.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, t


ROOT = Path(__file__).parent
DEEP = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1"
OUT = DEEP / "t2_reliability_investigation"
WINDOW = DEEP / "keyboard_deep_dive_window_features.csv"
DAILY = DEEP / "keyboard_deep_dive_daily_features.csv"
T1_PATH = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"
T2_PATH = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv"
SEED = 20261020
BOOTSTRAPS = 500

SIGNALS = [
    ("keyboard_median_correction_recovery_time_ms", "executive_function"),
    ("keyboard_12_18_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_inter_event_interval_cv", "executive_function"),
    ("keyboard_18_24_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_06_12_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_12_18_median_inter_event_interval_ms", "attention"),
]
PREFIX = {"global": "global", "memory": "memory", "executive_function": "ef", "processing_speed": "processing_speed", "attention": "attention", "motor": "motor"}
THRESHOLDS = {
    "all_available": {},
    "both_windows_min_active_days_7": {"active_days": 7},
    "both_windows_min_active_days_14": {"active_days": 14},
    "both_windows_min_active_days_28": {"active_days": 28},
    "both_windows_min_valid_intervals_500": {"valid_intervals": 500},
    "both_windows_min_valid_intervals_2000": {"valid_intervals": 2000},
    "both_windows_min_snapshots_500": {"snapshots": 500},
    "both_windows_min_snapshots_2000": {"snapshots": 2000},
}


def norm_id(v: object) -> str:
    s = str(v).strip()
    return s.zfill(3) if s.isdigit() else s


def bh(values: pd.Series) -> np.ndarray:
    p = values.to_numpy(float); q = np.full(len(p), np.nan); ok = np.isfinite(p)
    if not ok.any(): return q
    order = np.argsort(p[ok]); ranked = p[ok][order]
    adj = np.minimum.accumulate((ranked * len(ranked) / np.arange(1, len(ranked) + 1))[::-1])[::-1]
    restored = np.empty(len(ranked)); restored[order] = np.minimum(adj, 1.0); q[ok] = restored
    return q


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    windows = pd.read_csv(WINDOW, dtype={"Subject_ID_D": str}); windows["Subject_ID_D"] = windows["Subject_ID_D"].map(norm_id)
    daily = pd.read_csv(DAILY, dtype={"Subject_ID_D": str}); daily["Subject_ID_D"] = daily["Subject_ID_D"].map(norm_id)
    t1 = pd.read_csv(T1_PATH, dtype={"Subject_ID_D": str}); t2 = pd.read_csv(T2_PATH, dtype={"Subject_ID_D": str})
    t1["Subject_ID_D"] = t1["Subject_ID_D"].map(norm_id); t2["Subject_ID_D"] = t2["Subject_ID_D"].map(norm_id)
    # The Phase 11 wide file already carries the paired cognitive T2-minus-T1
    # outcomes; retain one canonical copy to avoid merge suffixes.
    cognitive = t1[["Subject_ID_D", *[f"{p}_delta" for p in PREFIX.values()]]].copy()
    return windows, daily, cognitive


def daily_periods(windows: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, w in windows.iterrows():
        d = daily[daily.Subject_ID_D.eq(w.Subject_ID_D) & daily.window_name.eq(w.window_name)].copy()
        d["local_date"] = pd.to_datetime(d.local_date)
        d = d.sort_values("local_date").reset_index(drop=True)
        row = {"Subject_ID_D": w.Subject_ID_D, "window_name": w.window_name, "active_days": len(d), "first_date": d.local_date.min(), "last_date": d.local_date.max(), "duration_days": (float(w.window_end_ms) - float(w.window_start_ms)) / 86_400_000, "window_status": w.window_status, "snapshots": w.distinct_observations_in_window, "valid_intervals": w.keyboard_valid_interval_count, "recording_intensity": w.distinct_observations_in_window / max((float(w.window_end_ms) - float(w.window_start_ms)) / 86_400_000, 1e-9), "valid_interval_intensity": pd.to_numeric(w.keyboard_valid_interval_count, errors="coerce") / max((float(w.window_end_ms) - float(w.window_start_ms)) / 86_400_000, 1e-9)}
        row["observation_span_days"] = (d.local_date.max() - d.local_date.min()).days if len(d) else np.nan
        row["first_last_14_gap_days"] = (d.local_date.iloc[-14] - d.local_date.iloc[13]).days if len(d) >= 28 else np.nan
        for f, _ in SIGNALS:
            row[f + "_window"] = pd.to_numeric(w[f], errors="coerce")
            row[f + "_first14"] = d.iloc[:14][f].median() if len(d) >= 14 else np.nan
            row[f + "_last14"] = d.iloc[-14:][f].median() if len(d) >= 14 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def make_pairs(periods: pd.DataFrame, cognitive: pd.DataFrame) -> pd.DataFrame:
    t1 = periods[periods.window_name.eq("T1")].copy(); t2 = periods[periods.window_name.eq("T2")].copy()
    p = t1.merge(t2, on="Subject_ID_D", suffixes=("_T1", "_T2"), how="inner").merge(cognitive, on="Subject_ID_D", how="left")
    for f, _ in SIGNALS:
        p[f + "_delta"] = pd.to_numeric(p[f + "_window_T2"], errors="coerce") - pd.to_numeric(p[f + "_window_T1"], errors="coerce")
        p[f + "_first14_delta"] = pd.to_numeric(p[f + "_first14_T2"], errors="coerce") - pd.to_numeric(p[f + "_first14_T1"], errors="coerce")
        p[f + "_last14_delta"] = pd.to_numeric(p[f + "_last14_T2"], errors="coerce") - pd.to_numeric(p[f + "_last14_T1"], errors="coerce")
    return p


def association(p: pd.DataFrame, feature_col: str, outcome: str, scenario: str) -> dict[str, object]:
    target = PREFIX[outcome] + "_delta"; d = p[[feature_col, target]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < 12 or d[feature_col].nunique() < 3 or d[target].nunique() < 3:
        return {"scenario": scenario, "feature_name": feature_col, "outcome": outcome, "n": len(d), "rho": np.nan, "p": np.nan, "ci_low": np.nan, "ci_high": np.nan}
    rho, pv = spearmanr(d[feature_col], d[target]); stable_offset = sum(ord(ch) for ch in f"{feature_col}|{outcome}|{scenario}") % 100000; rng = np.random.default_rng(SEED + stable_offset)
    vals = []
    for _ in range(BOOTSTRAPS):
        idx = rng.integers(0, len(d), len(d)); vals.append(spearmanr(d[feature_col].iloc[idx], d[target].iloc[idx]).statistic)
    return {"scenario": scenario, "feature_name": feature_col, "outcome": outcome, "n": len(d), "rho": rho, "p": pv, "ci_low": np.nanpercentile(vals, 2.5), "ci_high": np.nanpercentile(vals, 97.5)}


def sensitivity(pairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario, rules in THRESHOLDS.items():
        eligible = pairs.copy()
        for metric, threshold in rules.items():
            eligible = eligible[(pd.to_numeric(eligible[metric + "_T1"], errors="coerce") >= threshold) & (pd.to_numeric(eligible[metric + "_T2"], errors="coerce") >= threshold)]
        for feature, outcome in SIGNALS:
            rows.append(association(eligible, feature + "_delta", outcome, scenario))
    for scenario in sorted(set(r["scenario"] for r in rows)):
        idx = [i for i, r in enumerate(rows) if r["scenario"] == scenario]
        q = bh(pd.Series([rows[i]["p"] for i in idx]))
        for j, i in enumerate(idx): rows[i]["fdr_q"] = q[j]
    return pd.DataFrame(rows)


def comparable_periods(pairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario in ["first14_observed_days", "last14_observed_days"]:
        eligible = pairs[(pairs.active_days_T1 >= 14) & (pairs.active_days_T2 >= 14)].copy()
        for feature, outcome in SIGNALS:
            period_prefix = "first14" if scenario.startswith("first14") else "last14"
            rows.append(association(eligible, feature + "_" + period_prefix + "_delta", outcome, scenario))
    out = pd.DataFrame(rows)
    for scenario in out.scenario.unique(): out.loc[out.scenario.eq(scenario), "fdr_q"] = bh(out.loc[out.scenario.eq(scenario), "p"])
    return out


def reliability(periods: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for window in ["T1", "T2"]:
        for feature in sorted({feature for feature, _ in SIGNALS}):
            d = periods[periods.window_name.eq(window)][["active_days", feature + "_first14", feature + "_last14"]].dropna()
            for threshold_name, threshold in [("min_active_days_14", 14), ("min_active_days_28", 28), ("min_valid_intervals_500", None), ("min_snapshots_500", None)]:
                q = d.copy()
                if threshold_name == "min_active_days_14": q = q[q.active_days >= 14]
                if threshold_name == "min_active_days_28": q = q[q.active_days >= 28]
                # First/last 14-day reliability is only defined when at least 28 observed days exist.
                if threshold_name in {"min_valid_intervals_500", "min_snapshots_500"}: continue
                if len(q) < 4: continue
                a = q[feature + "_first14"].to_numpy(float); b = q[feature + "_last14"].to_numpy(float); rho, p = spearmanr(a, b)
                frame = np.column_stack([a, b]); n, k = frame.shape; ms = k * np.sum((frame.mean(1) - frame.mean()) ** 2) / (n - 1); mr = n * np.sum((frame.mean(0) - frame.mean()) ** 2) / (k - 1); err = frame - frame.mean(1)[:, None] - frame.mean(0)[None, :] + frame.mean(); me = np.sum(err ** 2) / ((n - 1) * (k - 1)); icc = (ms - me) / (ms + (k - 1) * me + k * (mr - me) / n)
                rows.append({"window_name": window, "feature_name": feature, "threshold": threshold_name, "n": n, "icc_2_1": icc, "spearman_rho": rho, "spearman_p": p})
    return pd.DataFrame(rows)


def coverage_summary(periods: pd.DataFrame) -> pd.DataFrame:
    metrics = ["duration_days", "active_days", "snapshots", "valid_intervals", "recording_intensity", "valid_interval_intensity", "observation_span_days", "first_last_14_gap_days"]
    rows = []
    for window in ["T1", "T2"]:
        d = periods[periods.window_name.eq(window)]
        for metric in metrics:
            x = pd.to_numeric(d[metric], errors="coerce")
            rows.append({"window_name": window, "metric": metric, "n": int(x.notna().sum()), "missing_n": int(x.isna().sum()), "median": x.median(), "iqr": x.quantile(.75) - x.quantile(.25), "min": x.min(), "max": x.max()})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    windows, daily, cognitive = load_inputs(); periods = daily_periods(windows, daily); pairs = make_pairs(periods, cognitive)
    periods.to_csv(OUT / "t2_reliability_period_metrics.csv", index=False); coverage_summary(periods).to_csv(OUT / "t2_reliability_coverage_summary.csv", index=False)
    sensitivity(pairs).to_csv(OUT / "t2_reliability_signal_sensitivity.csv", index=False); comparable_periods(pairs).to_csv(OUT / "t2_reliability_comparable_periods.csv", index=False); reliability(periods).to_csv(OUT / "t2_reliability_thresholds.csv", index=False)
    manifest = {"status": "complete", "paired_patients": int(len(pairs)), "signals": 6, "predeclared_thresholds": THRESHOLDS, "comparable_period_definition": "first or last 14 observed keyboard days in both T1 and T2; minimum 14 active days per window", "bootstrap_replicates": BOOTSTRAPS, "predictive_models_trained": False, "existing_outputs_modified": False}
    (OUT / "t2_reliability_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8"); print(json.dumps(manifest, indent=2))


if __name__ == "__main__": main()
