"""Parsimonious coverage-adjusted audit for the nine non-selected-six rows."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, t

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/research_summary_20261025/top15_article_statistics_v1"
SEED, BOOT = 20261026, 500
TARGET_ROWS = [1, 6, 8, 9, 10, 12, 13, 14, 15]

def norm(s): return s.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(3)
def partial(d, x, y, covars):
    z = d[[x, y, *covars]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    n = len(z)
    if n < max(12, len(covars) + 4): return np.nan, np.nan, n
    ranks = z.rank(method="average")
    design = np.column_stack([np.ones(n), ranks[covars].to_numpy(float)])
    rx = ranks[x].to_numpy(float) - design @ np.linalg.lstsq(design, ranks[x].to_numpy(float), rcond=None)[0]
    ry = ranks[y].to_numpy(float) - design @ np.linalg.lstsq(design, ranks[y].to_numpy(float), rcond=None)[0]
    if np.std(rx) == 0 or np.std(ry) == 0: return np.nan, np.nan, n
    rho = float(np.corrcoef(rx, ry)[0, 1]); df = max(n - design.shape[1] - 1, 1)
    stat = rho * np.sqrt(df / max(1 - rho * rho, 1e-12))
    return rho, float(2 * t.sf(abs(stat), df)), n
def boot(d, x, y, covars, seed):
    z = d[[x, y, *covars]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    ranks = z.rank(method="average").to_numpy(float); rng = np.random.default_rng(seed); vals = []
    for _ in range(BOOT):
        idx = rng.integers(0, len(ranks), len(ranks)); rr = ranks[idx]
        design = np.column_stack([np.ones(len(rr)), rr[:, 2:]])
        rx = rr[:, 0] - design @ np.linalg.lstsq(design, rr[:, 0], rcond=None)[0]
        ry = rr[:, 1] - design @ np.linalg.lstsq(design, rr[:, 1], rcond=None)[0]
        if np.std(rx) and np.std(ry): vals.append(float(np.corrcoef(rx, ry)[0, 1]))
    return (float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))) if vals else (np.nan, np.nan)

tables = {}
for name in ["top15_exact_patient_level_table.csv", "top15_all_reconstructed_patient_level_table_v1.csv"]:
    q = pd.read_csv(OUT / name, dtype={"Subject_ID_D": str}); q.Subject_ID_D = norm(q.Subject_ID_D); tables[name] = q
exact, allq = tables["top15_exact_patient_level_table.csv"], tables["top15_all_reconstructed_patient_level_table_v1.csv"]
C1 = pd.read_csv(ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv", dtype={"Subject_ID_D": str}); C1.Subject_ID_D = norm(C1.Subject_ID_D)
WIN = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/keyboard_deep_dive_window_features.csv", dtype={"Subject_ID_D": str}); WIN.Subject_ID_D = norm(WIN.Subject_ID_D)
cov = WIN.pivot(index="Subject_ID_D", columns="window_name", values=["active_local_days", "distinct_observations_in_window", "keyboard_valid_interval_count"])
cov.columns = [f"{a}_{b}" for a, b in cov.columns]; cov = cov.reset_index()
base = cov.merge(C1[["Subject_ID_D", "age", "Gender (1=M, 2=F)", "Education (years)", "attention_T1", "ef_T1"]], on="Subject_ID_D", how="left")
for w in ["T1", "T2"]:
    base[f"snapshot_rate_{w}"] = base[f"distinct_observations_in_window_{w}"] / base[f"active_local_days_{w}"].replace(0, np.nan)
    base[f"valid_rate_{w}"] = base[f"keyboard_valid_interval_count_{w}"] / base[f"active_local_days_{w}"].replace(0, np.nan)
base["snapshot_rate_delta"] = base.snapshot_rate_T2 - base.snapshot_rate_T1
base["valid_rate_delta"] = base.valid_rate_T2 - base.valid_rate_T1
meta = pd.read_csv(ROOT / "output/research_summary_20261025/top15_feature_cognition_associations_20261025.csv")
rows = []
for rownum in TARGET_ROWS:
    r = meta.iloc[rownum - 1]; longitudinal = r.outcome_timepoint == "T2_minus_T1"
    src = allq[allq.top15_row.eq(rownum)].copy() if rownum in [1, 6, 12, 14] else exact[exact.top15_row.eq(rownum)].copy()
    if longitudinal:
        src = src[src.feature_delta.notna() & src.cognitive_delta.notna()].copy(); x, y = "feature_delta", "cognitive_delta"
        src = src.merge(base, on="Subject_ID_D", how="left")
        baseline = "attention_T1" if r.outcome == "attention" else "ef_T1"; src["baseline_cognitive"] = src[baseline]
        sets = {"core_age_sex_education": ["age", "Gender (1=M, 2=F)", "Education (years)"], "core_plus_baseline": ["age", "Gender (1=M, 2=F)", "Education (years)", "baseline_cognitive"], "core_recording": ["age", "Gender (1=M, 2=F)", "Education (years)", "baseline_cognitive", "snapshot_rate_delta", "valid_rate_delta"]}
    else:
        src = src[src.feature_early.notna() & src.cognitive_t1.notna()].copy(); x, y = "feature_early", "cognitive_t1"; src = src.merge(base, on="Subject_ID_D", how="left")
        sets = {"core_age_sex_education": ["age", "Gender (1=M, 2=F)", "Education (years)"], "core_recording": ["age", "Gender (1=M, 2=F)", "Education (years)", "snapshot_rate_T1", "valid_rate_T1"]}
    for adj_name, covars in sets.items():
        rho, p, n = partial(src, x, y, covars); lo, hi = boot(src, x, y, covars, SEED + rownum * 100 + len(covars)) if np.isfinite(rho) else (np.nan, np.nan)
        rows.append({"top15_row": rownum, "label": r.label, "feature": r.feature, "outcome": r.outcome, "timepoint": r.outcome_timepoint, "adjustment": adj_name, "covariates": ";".join(covars), "n": n, "partial_rho": rho, "partial_p": p, "bootstrap_ci_low": lo, "bootstrap_ci_high": hi, "source_cohort": "reconstructed_saved_patient_level_inputs", "device_change_included": False})
out = pd.DataFrame(rows)
for adj_name in out.adjustment.unique():
    m = out.adjustment.eq(adj_name); pvals = out.loc[m, "partial_p"].to_numpy(float); q = np.full(len(pvals), np.nan); ok = np.isfinite(pvals)
    if ok.any():
        idx = np.where(ok)[0]; order = idx[np.argsort(pvals[idx])]; ranked = pvals[order]; adj = np.minimum.accumulate((ranked * len(ranked) / np.arange(1, len(ranked) + 1))[::-1])[::-1]; q[order] = np.minimum(adj, 1.0)
    out.loc[m, "fdr_q_within_adjustment"] = q
out.to_csv(OUT / "top15_remaining_coverage_adjusted_v1.csv", index=False)
print(out.to_string(index=False))
