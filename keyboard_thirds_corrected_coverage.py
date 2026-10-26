"""Correct only the first/last-third coverage-adjusted correlations.

The historical thirds run used raw SQL row counts as its snapshot covariate.
This additive rerun uses canonical distinct observations and preserves the
historical results for direct comparison. No feature extraction or models are
rerun here.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, t

from keyboard_signal_discovery import OUTCOMES, feature_columns, normalize_id

ROOT = Path(__file__).parent
OLD = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity"
OUT = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity_corrected_v2"
COG = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv"
SEED = 20261020
BOOTSTRAPS = 500
THIRD_OUTCOMES = {**OUTCOMES, "verbal": "verbal", "iq": "iq"}


def partial_fit(x: np.ndarray, y: np.ndarray, cov: np.ndarray) -> float:
    ranks = pd.DataFrame(np.column_stack([x, y, cov])).rank(method="average").to_numpy(float)
    design = np.column_stack([np.ones(len(ranks)), ranks[:, 2:]])
    rx = ranks[:, 0] - design @ np.linalg.lstsq(design, ranks[:, 0], rcond=None)[0]
    ry = ranks[:, 1] - design @ np.linalg.lstsq(design, ranks[:, 1], rcond=None)[0]
    return float(np.corrcoef(rx, ry)[0, 1]) if np.std(rx) > 0 and np.std(ry) > 0 else np.nan


def partial_stats(x: pd.Series, y: pd.Series, cov: pd.DataFrame, rng: np.random.Generator) -> dict[str, float | int]:
    frame = pd.concat([x.rename("x"), y.rename("y"), cov], axis=1).apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    n = len(frame)
    if n < 12 or frame.x.nunique() < 3 or frame.y.nunique() < 3:
        return {"n": n, "rho": np.nan, "p": np.nan, "ci_low": np.nan, "ci_high": np.nan}
    rho = partial_fit(frame.x.to_numpy(float), frame.y.to_numpy(float), frame.iloc[:, 2:].to_numpy(float))
    df = max(n - frame.shape[1], 1)
    stat = rho * np.sqrt(df / max(1 - rho * rho, 1e-12)) if np.isfinite(rho) else np.nan
    p = float(2 * t.sf(abs(stat), df)) if np.isfinite(stat) else np.nan
    boots = []
    for _ in range(BOOTSTRAPS):
        idx = rng.integers(0, n, n)
        boots.append(partial_fit(frame.x.to_numpy(float)[idx], frame.y.to_numpy(float)[idx], frame.iloc[:, 2:].to_numpy(float)[idx]))
    return {"n": n, "rho": rho, "p": p, "ci_low": float(np.nanpercentile(boots, 2.5)), "ci_high": float(np.nanpercentile(boots, 97.5))}


def bh(p: pd.Series) -> np.ndarray:
    a = p.to_numpy(float); q = np.full(len(a), np.nan); ok = np.isfinite(a)
    if not ok.any(): return q
    idx = np.where(ok)[0][np.argsort(a[ok])]; ranked = a[idx]
    adj = np.minimum.accumulate((ranked * len(ranked) / np.arange(1, len(ranked) + 1))[::-1])[::-1]
    q[idx] = np.minimum(adj, 1.0); return q


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    w = pd.read_csv(OLD / "third_window_features.csv", dtype={"Subject_ID_D": str}); w.Subject_ID_D = w.Subject_ID_D.map(normalize_id)
    features = feature_columns(w.columns.tolist())
    p = w.pivot(index="Subject_ID_D", columns="window_name", values=features); p.columns = [f"{f}_{n}" for f, n in p.columns]; p = p.reset_index()
    for f in features: p[f + "_delta"] = pd.to_numeric(p[f + "_last_third"], errors="coerce") - pd.to_numeric(p[f + "_first_third"], errors="coerce")
    cov = w.pivot(index="Subject_ID_D", columns="window_name", values="distinct_observations_in_window").add_suffix("_snapshots").reset_index()
    active = w.pivot(index="Subject_ID_D", columns="window_name", values="active_local_days").add_suffix("_active_days").reset_index()
    p = p.merge(cov, on="Subject_ID_D").merge(active, on="Subject_ID_D")
    cog = pd.read_csv(COG, dtype={"Subject_ID_D": str}); cog.Subject_ID_D = cog.Subject_ID_D.map(normalize_id)
    keep = ["Subject_ID_D", "age", "Gender (1=M, 2=F)", "Education (years)", *[f"{v}_delta" for v in THIRD_OUTCOMES.values()]]
    p = p.merge(cog[keep], on="Subject_ID_D", how="inner")
    p = p[(p.first_third_active_days >= 7) & (p.last_third_active_days >= 7)].copy()
    p["mean_active_days"] = (p.first_third_active_days + p.last_third_active_days) / 2
    p["mean_snapshots"] = (p.first_third_snapshots + p.last_third_snapshots) / 2
    covars = ["age", "Gender (1=M, 2=F)", "Education (years)", "mean_active_days", "mean_snapshots"]
    rows = []; rng = np.random.default_rng(SEED)
    for outcome, code in THIRD_OUTCOMES.items():
        for f in features:
            stats = partial_stats(p[f + "_delta"], p[f"{code}_delta"], p[covars], rng)
            rows.append({"scope": "first_last_third_min_active_days_7_corrected", "feature_name": f + "_delta", "outcome": outcome, "partial_spearman_rho_corrected": stats["rho"], "partial_spearman_p_corrected": stats["p"], "bootstrap_ci_low_corrected": stats["ci_low"], "bootstrap_ci_high_corrected": stats["ci_high"], "n_corrected": stats["n"]})
    corrected = pd.DataFrame(rows); corrected["fdr_q_corrected"] = bh(corrected.partial_spearman_p_corrected); corrected.to_csv(OUT / "corrected_coverage_adjusted_associations.csv", index=False)
    old = pd.read_csv(OLD / "third_associations.csv")
    old = old[old.scope.eq("first_last_third_min_active_days_7")][["feature_name", "outcome", "partial_spearman_rho", "partial_spearman_p", "partial_n", "bootstrap_ci_low", "bootstrap_ci_high", "fdr_q"]].rename(columns={"partial_spearman_rho": "partial_spearman_rho_historical", "partial_spearman_p": "partial_spearman_p_historical", "partial_n": "n_historical", "bootstrap_ci_low": "bootstrap_ci_low_historical_unadjusted", "bootstrap_ci_high": "bootstrap_ci_high_historical_unadjusted", "fdr_q": "fdr_q_historical"})
    comparison = corrected.merge(old, on=["feature_name", "outcome"], how="left")
    comparison["rho_change"] = comparison.partial_spearman_rho_corrected - comparison.partial_spearman_rho_historical
    comparison["p_change"] = comparison.partial_spearman_p_corrected - comparison.partial_spearman_p_historical
    comparison.to_csv(OUT / "corrected_vs_historical_coverage_adjusted.csv", index=False)
    pd.DataFrame({"Subject_ID_D": p.Subject_ID_D, "mean_active_days": p.mean_active_days, "mean_snapshots_corrected": p.mean_snapshots}).to_csv(OUT / "corrected_coverage_cohort.csv", index=False)
    (OUT / "corrected_manifest.json").write_text(json.dumps({"status": "complete", "cohort_n": len(p), "features": len(features), "outcomes": len(THIRD_OUTCOMES), "bootstrap_replicates": BOOTSTRAPS, "snapshot_definition": "canonical distinct_observations_in_window", "historical_outputs_overwritten": False, "models_trained": False}, indent=2), encoding="utf-8")


if __name__ == "__main__": main()
