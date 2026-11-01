"""Robustness audit for four restricted/legacy top-15 associations."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/research_summary_20261025/top15_article_statistics_v1"
SEED, PERM = 20261026, 2000

def run_robust(d, x, y, rownum, label, cohort):
    d = d[[x, y]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    rho, p = spearmanr(d[x], d[y])
    loo = []
    for i in range(len(d)):
        q = d.drop(index=i); loo.append(spearmanr(q[x], q[y]).statistic)
    q1x, q3x = d[x].quantile([.25, .75]); q1y, q3y = d[y].quantile([.25, .75])
    keep = d[x].between(q1x - 1.5*(q3x-q1x), q3x + 1.5*(q3x-q1x)) & d[y].between(q1y - 1.5*(q3y-q1y), q3y + 1.5*(q3y-q1y))
    out_rho = spearmanr(d.loc[keep, x], d.loc[keep, y]).statistic if keep.sum() >= 12 else np.nan
    rng = np.random.default_rng(SEED + rownum); xv, yv = d[x].to_numpy(float), d[y].to_numpy(float)
    null = np.array([spearmanr(xv, rng.permutation(yv)).statistic for _ in range(PERM)])
    perm_p = (1 + np.sum(np.abs(null) >= abs(rho))) / (PERM + 1)
    return {"top15_row": rownum, "label": label, "cohort": cohort, "n": len(d), "rho": rho, "p": p, "loo_min_rho": np.min(loo), "loo_max_rho": np.max(loo), "loo_sign_consistency": np.mean(np.sign(loo) == np.sign(rho)), "outlier_filtered_n": int(keep.sum()), "outlier_filtered_rho": out_rho, "permutation_replicates": PERM, "permutation_p": perm_p, "interpretation": "exploratory robustness only; not independent validation"}

restricted = pd.read_csv(OUT / "top15_restricted_window_patient_table_v1.csv", dtype={"Subject_ID_D": str})
legacy = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_two_feature_median_timespan/keyboard_two_feature_patient_data.csv", dtype={"Subject_ID_D": str})
rows = []
for rownum in [1, 6]:
    d = restricted[restricted.top15_row.eq(rownum)]; rows.append(run_robust(d, "feature_delta", "cognitive_delta", rownum, d.label.iloc[0], "restricted 50/50 midpoint same-patient cohort"))
for rownum, outcome in [(12, "attention_T1"), (14, "global_T1")]:
    feature = "keyboard_median_word_completion_time_ms"; flag = "excluded_extreme_" + feature
    d = legacy.loc[~legacy[flag].astype(bool), [feature, outcome]].dropna()
    rows.append(run_robust(d, feature, outcome, rownum, f"{feature} -> {outcome} (legacy min/max trimmed)", "legacy feature-specific min/max trimmed cohort"))
out = pd.DataFrame(rows)
out.to_csv(OUT / "top15_restricted_legacy_robustness_v1.csv", index=False)
print(out.to_string(index=False))
