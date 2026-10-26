"""First/last-third keyboard sensitivity analysis.

This is additive: it queries the timestamped keyboard table inside each valid
patient T1--T2 interval, splits that interval into three equal calendar-time
thirds, and writes a separate versioned output directory.  Existing midpoint
outputs and models are never modified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr, t

from main import connect_sensordata_db
from keyboard_deep_dive import canonical_events, compute_window, fetch_keyboard_rows, local_timestamp
from keyboard_signal_discovery import OUTCOMES, feature_columns, normalize_id

ROOT = Path(__file__).parent
OUT = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity"
WIDE = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"
T1_STATUS = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_patient_table_status.csv"
MIDPOINT = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/keyboard_deep_dive_window_features.csv"
T2_WIDE = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv"
TZ = "Asia/Jerusalem"
SEED = 20261020
BOOTSTRAPS = 500


def local_ms(ts: pd.Timestamp) -> int:
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def load_paired() -> pd.DataFrame:
    d = pd.read_csv(WIDE, dtype={"Subject_ID_D": str}).drop_duplicates("Subject_ID_D").copy()
    d["Subject_ID_D"] = d["Subject_ID_D"].map(normalize_id)
    d["T1_dt"] = pd.to_datetime(d["T1_date_iso"], errors="coerce").dt.tz_localize(TZ)
    d["T2_dt"] = pd.to_datetime(d["T2_date_iso"], errors="coerce").dt.tz_localize(TZ)
    return d[d.T1_dt.notna() & d.T2_dt.notna() & (d.T2_dt > d.T1_dt)].copy()


def load_device_map() -> dict[str, list[str]]:
    s = pd.read_csv(T1_STATUS, dtype=str)
    s = s[s.table_name.eq("keyboard")].copy()
    s["Subject_ID_D"] = s["Subject_ID_D"].map(normalize_id)
    result: dict[str, list[str]] = {}
    for sid, g in s.groupby("Subject_ID_D"):
        ids: set[str] = set()
        for value in g["device_ids_used"].fillna(g["device_ids_available"]):
            ids.update(x.strip() for x in str(value).split(";") if x.strip() and x.lower() != "nan")
        result[sid] = sorted(ids)
    return result


def third_windows(row: pd.Series) -> list[dict[str, object]]:
    start, end = row.T1_dt, row.T2_dt
    span = end - start
    a = start + span / 3
    b = start + span * 2 / 3
    return [
        {"window_name": "first_third", "start": start, "end": a},
        {"window_name": "last_third", "start": b, "end": end},
    ]


def extract(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    paired = load_paired()
    devices = load_device_map()
    conn = connect_sensordata_db()
    rows: list[dict[str, object]] = []
    daily: list[dict[str, object]] = []
    try:
        for i, (_, patient) in enumerate(paired.iterrows(), 1):
            sid = str(patient.Subject_ID_D)
            specs = third_windows(patient)
            full_start, full_end = local_ms(patient.T1_dt), local_ms(patient.T2_dt)
            raw = fetch_keyboard_rows(conn, devices.get(sid, []), full_start, full_end)
            events, _, _ = canonical_events(raw)
            for spec in specs:
                start_ms, end_ms = local_ms(spec["start"]), local_ms(spec["end"])
                part = [e for e in events if start_ms <= e["timestamp"] < end_ms]
                parsed = [e for e in raw if start_ms <= int(e.get("timestamp", -1)) < end_ms]
                subevents, duplicate, parse_errors = canonical_events(parsed)
                # Re-canonicalize from the split raw rows so duplicate burden is
                # measured within the third, exactly as in the original extractor.
                window, day_rows = compute_window(subevents, len(parsed), duplicate, parse_errors, sid, str(spec["window_name"]), start_ms, end_ms)
                window.update({"T1_date_iso": str(patient.T1_date_iso), "T2_date_iso": str(patient.T2_date_iso), "interval_days": (patient.T2_dt - patient.T1_dt).total_seconds() / 86400.0, "third_fraction": 1 / 3})
                rows.append(window)
                daily.extend(day_rows)
            print(f"{i}/{len(paired)} {sid}: full_raw={len(raw)}")
    finally:
        conn.close()
    pd.DataFrame(rows).to_csv(out / "third_window_features.csv", index=False)
    pd.DataFrame(daily).to_csv(out / "third_daily_features.csv", index=False)
    pd.DataFrame({"Subject_ID_D": paired.Subject_ID_D, "T1_date_iso": paired.T1_date_iso, "T2_date_iso": paired.T2_date_iso}).to_csv(out / "paired_cohort.csv", index=False)


def bh(p: pd.Series) -> np.ndarray:
    arr = p.to_numpy(float); q = np.full(len(arr), np.nan); ok = np.isfinite(arr)
    if not ok.any(): return q
    idx = np.where(ok)[0][np.argsort(arr[ok])]; ranked = arr[idx]
    adj = np.minimum.accumulate((ranked * len(ranked) / np.arange(1, len(ranked) + 1))[::-1])[::-1]
    q[idx] = np.minimum(adj, 1.0); return q


def partial_spearman(x: pd.Series, y: pd.Series, cov: pd.DataFrame) -> tuple[float, float, int]:
    z = pd.concat([x.rename("x"), y.rename("y"), cov], axis=1).apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    n = len(z)
    if n < 12: return np.nan, np.nan, n
    r = z.rank(method="average"); design = np.column_stack([np.ones(n), r.iloc[:, 2:].to_numpy()])
    rx = r.iloc[:, 0].to_numpy() - design @ np.linalg.lstsq(design, r.iloc[:, 0].to_numpy(), rcond=None)[0]
    ry = r.iloc[:, 1].to_numpy() - design @ np.linalg.lstsq(design, r.iloc[:, 1].to_numpy(), rcond=None)[0]
    rho = float(np.corrcoef(rx, ry)[0, 1]) if np.std(rx) and np.std(ry) else np.nan
    df = max(n - design.shape[1] - 1, 1); stat = rho * np.sqrt(df / max(1 - rho * rho, 1e-12)) if np.isfinite(rho) else np.nan
    return rho, float(2 * t.sf(abs(stat), df)) if np.isfinite(stat) else np.nan, n


def associations(data: pd.DataFrame, features: list[str], outcome_suffix: str, scope: str, covars: pd.DataFrame) -> pd.DataFrame:
    rows = []; rng = np.random.default_rng(SEED)
    for outcome, code in OUTCOMES.items():
        target = f"{code}_delta"
        if target not in data: continue
        for f in features:
            x, y = pd.to_numeric(data[f], errors="coerce"), pd.to_numeric(data[target], errors="coerce")
            valid = pd.concat([x.rename("x"), y.rename("y")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
            if len(valid) < 12 or valid.x.nunique() < 3 or valid.y.nunique() < 3: continue
            rho, p = spearmanr(valid.x, valid.y); boots = []
            for _ in range(BOOTSTRAPS):
                ix = rng.integers(0, len(valid), len(valid)); boots.append(spearmanr(valid.x.iloc[ix], valid.y.iloc[ix]).statistic)
            pr, pp, pn = partial_spearman(x, y, covars)
            rows.append({"scope": scope, "feature_name": f, "outcome": outcome, "n": len(valid), "spearman_rho": rho, "spearman_p": p, "bootstrap_ci_low": np.nanpercentile(boots, 2.5), "bootstrap_ci_high": np.nanpercentile(boots, 97.5), "partial_spearman_rho": pr, "partial_spearman_p": pp, "partial_n": pn})
    result = pd.DataFrame(rows)
    if not result.empty: result["fdr_q"] = bh(result.spearman_p)
    return result


def analyze(out: Path, min_active_days: int = 7) -> None:
    w = pd.read_csv(out / "third_window_features.csv", dtype={"Subject_ID_D": str}); w.Subject_ID_D = w.Subject_ID_D.map(normalize_id)
    features = feature_columns(w.columns.tolist())
    cov_cols = ["Subject_ID_D", "active_local_days", "raw_rows_in_window", "keyboard_valid_interval_count", "window_status"]
    coverage = w[cov_cols].copy().rename(columns={"active_local_days": "active_days", "raw_rows_in_window": "snapshots", "keyboard_valid_interval_count": "valid_intervals"})
    coverage["recording_intensity"] = coverage.snapshots / coverage.active_days.replace(0, np.nan)
    coverage.to_csv(out / "third_coverage.csv", index=False)
    p = w.pivot(index="Subject_ID_D", columns="window_name", values=features)
    p.columns = [f"{f}_{name}" for f, name in p.columns]
    p = p.reset_index()
    for f in features: p[f + "_delta"] = pd.to_numeric(p[f + "_last_third"], errors="coerce") - pd.to_numeric(p[f + "_first_third"], errors="coerce")
    cog = pd.read_csv(T2_WIDE, dtype={"Subject_ID_D": str}); cog.Subject_ID_D = cog.Subject_ID_D.map(normalize_id)
    keep = ["Subject_ID_D", "age", "Gender (1=M, 2=F)", "Education (years)", *[f"{v}_delta" for v in OUTCOMES.values()]]
    p = p.merge(cog[keep], on="Subject_ID_D", how="inner")
    active = w.pivot(index="Subject_ID_D", columns="window_name", values="active_local_days").add_suffix("_active_days").reset_index()
    snaps = w.pivot(index="Subject_ID_D", columns="window_name", values="raw_rows_in_window").add_suffix("_snapshots").reset_index()
    p = p.merge(active, on="Subject_ID_D", how="left").merge(snaps, on="Subject_ID_D", how="left")
    both = p[(p.first_third_active_days >= min_active_days) & (p.last_third_active_days >= min_active_days)].copy()
    both.to_csv(out / f"third_patient_data_min{min_active_days}.csv", index=False)
    cov = both[["age", "Gender (1=M, 2=F)", "Education (years)", "first_third_active_days", "last_third_active_days", "first_third_snapshots", "last_third_snapshots"]].copy()
    cov["mean_active_days"] = (cov.first_third_active_days + cov.last_third_active_days) / 2
    cov["mean_snapshots"] = (cov.first_third_snapshots + cov.last_third_snapshots) / 2
    assoc = associations(both, [f + "_delta" for f in features], "_delta", f"first_last_third_min_active_days_{min_active_days}", cov[["age", "Gender (1=M, 2=F)", "Education (years)", "mean_active_days", "mean_snapshots"]])
    assoc.to_csv(out / "third_associations.csv", index=False)
    counts = []
    for threshold in (0, 7, 14, 28):
        eligible = p[(p.first_third_active_days >= threshold) & (p.last_third_active_days >= threshold)]
        counts.append({"threshold_active_days_each_third": threshold, "eligible_patients": len(eligible), "median_first_active_days": eligible.first_third_active_days.median(), "median_last_active_days": eligible.last_third_active_days.median(), "median_first_snapshots": eligible.first_third_snapshots.median(), "median_last_snapshots": eligible.last_third_snapshots.median()})
    pd.DataFrame(counts).to_csv(out / "third_eligibility_summary.csv", index=False)
    # Pairwise feature dependence among the six previously discovered signals.
    six = ["keyboard_median_correction_recovery_time_ms", "keyboard_12_18_median_inter_event_interval_ms", "keyboard_inter_event_interval_cv", "keyboard_18_24_median_inter_event_interval_ms", "keyboard_06_12_median_inter_event_interval_ms"]
    six = [f + "_delta" for f in six]
    corr = both[six].corr(method="spearman"); corr.to_csv(out / "third_selected_feature_correlation_matrix.csv")
    # Direct 50/50 versus thirds comparison on the same eligible patients.
    midpoint = pd.read_csv(MIDPOINT, dtype={"Subject_ID_D": str}); midpoint.Subject_ID_D = midpoint.Subject_ID_D.map(normalize_id)
    m1 = midpoint[midpoint.window_name.eq("T1")].set_index("Subject_ID_D")
    m2 = midpoint[midpoint.window_name.eq("T2")].set_index("Subject_ID_D")
    same_ids = set(both.Subject_ID_D)
    comparison = []
    for f in [x.removesuffix("_delta") for x in six]:
        md = pd.to_numeric(m2[f], errors="coerce") - pd.to_numeric(m1[f], errors="coerce")
        td = pd.to_numeric(both[f + "_delta"], errors="coerce")
        for outcome, code in OUTCOMES.items():
            y = cog.set_index("Subject_ID_D").loc[list(same_ids), f"{code}_delta"]
            frame = pd.DataFrame({"third": td.reindex(y.index), "midpoint": md.reindex(y.index), "y": y}).dropna()
            if len(frame) >= 12 and frame.y.nunique() > 2:
                comparison.extend([
                    {"window_design": "first_last_third", "feature_name": f, "outcome": outcome, "n": len(frame), "rho": spearmanr(frame.third, frame.y).statistic, "p": spearmanr(frame.third, frame.y).pvalue},
                    {"window_design": "50_50_midpoint_same_patients", "feature_name": f, "outcome": outcome, "n": len(frame), "rho": spearmanr(frame.midpoint, frame.y).statistic, "p": spearmanr(frame.midpoint, frame.y).pvalue},
                ])
    comp = pd.DataFrame(comparison)
    if not comp.empty: comp["fdr_q_within_design"] = comp.groupby("window_design")["p"].transform(bh)
    comp.to_csv(out / "third_vs_midpoint_comparison_same_patients.csv", index=False)
    # Compact manuscript-ready figures.
    plot_cov = coverage[coverage.window_name.isin(["first_third", "last_third"])].copy()
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, metric in zip(axes, ["active_days", "snapshots", "valid_intervals"]):
        plot_cov.boxplot(column=metric, by="window_name", ax=ax, grid=False)
        ax.set_title(metric.replace("_", " ")); ax.set_xlabel("")
    fig.suptitle("First versus last third keyboard coverage"); fig.tight_layout(); fig.savefig(out / "third_coverage_comparison.png", dpi=180); plt.close(fig)
    if not comp.empty:
        pivot = comp.pivot_table(index="feature_name", columns="window_design", values="rho", aggfunc="first")
        ax = pivot.plot(kind="barh", figsize=(10, 6), color=["#2563eb", "#94a3b8"])
        ax.axvline(0, color="black", linewidth=.7); ax.set_xlabel("Spearman correlation"); ax.set_title("Thirds versus 50/50 on the same patients"); fig = ax.get_figure(); fig.tight_layout(); fig.savefig(out / "third_vs_midpoint_associations.png", dpi=180); plt.close(fig)
    if len(both) >= 3:
        fig, ax = plt.subplots(figsize=(8, 7)); im = ax.imshow(corr.to_numpy(), vmin=-1, vmax=1, cmap="RdBu_r"); ax.set_xticks(range(len(six)), [x.replace("keyboard_", "")[:18] for x in six], rotation=70, ha="right"); ax.set_yticks(range(len(six)), [x.replace("keyboard_", "")[:18] for x in six]); fig.colorbar(im, ax=ax, label="Spearman ρ"); fig.tight_layout(); fig.savefig(out / "third_selected_feature_correlations.png", dpi=180); plt.close(fig)
    manifest = {"status": "complete", "paired_cognitive_patients": int(len(p)), "third_feature_count": len(features), "eligible_min_active_days": min_active_days, "bootstrap_replicates": BOOTSTRAPS, "window_rule": "equal calendar thirds; first and last thirds only; change = last - first", "existing_outputs_modified": False, "models_trained": False}
    (out / "thirds_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--extract", action="store_true"); ap.add_argument("--analyze", action="store_true"); ap.add_argument("--out-dir", default=str(OUT)); ap.add_argument("--min-active-days", type=int, default=7); args = ap.parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    if args.extract: extract(out)
    if args.analyze: analyze(out, args.min_active_days)
    if not args.extract and not args.analyze: ap.error("choose --extract and/or --analyze")


if __name__ == "__main__": main()
