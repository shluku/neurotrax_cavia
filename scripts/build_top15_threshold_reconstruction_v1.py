"""Reconstruct top-15 T2-reliability cohorts from saved period metrics.

Descriptive audit only. Applies documented measurement thresholds and writes
versioned outputs without changing historical association files.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/research_summary_20261025/top15_article_statistics_v1"
TOP = pd.read_csv(ROOT / "output/research_summary_20261025/top15_feature_cognition_associations_20261025.csv")
SENS = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/t2_reliability_investigation/t2_reliability_signal_sensitivity.csv")
PER = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/t2_reliability_investigation/t2_reliability_period_metrics.csv", dtype={"Subject_ID_D": str})
PER["Subject_ID_D"] = PER["Subject_ID_D"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(3)
C1 = pd.read_csv(ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv", dtype={"Subject_ID_D": str})
C1["Subject_ID_D"] = C1["Subject_ID_D"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(3)

T1 = PER[PER.window_name.eq("T1")].copy()
T2 = PER[PER.window_name.eq("T2")].copy()
P = T1.merge(T2, on="Subject_ID_D", suffixes=("_T1", "_T2"))
P = P.merge(C1[["Subject_ID_D", "ef_delta", "attention_delta"]], on="Subject_ID_D", how="left")

def candidates(row):
    d = SENS[(SENS.feature_name.eq(row.feature + "_delta")) & (SENS.outcome.eq(row.outcome))].copy()
    d["rho_diff"] = (d.rho - float(row.estimate)).abs()
    d["p_diff"] = (d.p - float(row.p)).abs()
    return d.sort_values(["rho_diff", "p_diff", "n"]).head(1)

def apply_rule(frame, scenario):
    for metric, suffix in [("active_days", "active_days"), ("snapshots", "snapshots"), ("valid_intervals", "valid_intervals")]:
        for threshold in [7, 14, 28, 500, 2000]:
            if scenario.endswith(f"min_{metric}_{threshold}"):
                return frame[(frame[f"{metric}_T1"] >= threshold) & (frame[f"{metric}_T2"] >= threshold)]
    return frame

def num(frame, col):
    return pd.to_numeric(frame[col], errors="coerce") if col in frame else pd.Series(np.nan, index=frame.index)

rows, summaries, audits = [], [], []
for i, row in TOP.iterrows():
    if "t2_reliability" not in str(row.source_file):
        continue
    match = candidates(row)
    if match.empty:
        continue
    scenario = match.iloc[0].scenario
    q = apply_rule(P, scenario).copy()
    feat = row.feature
    outcome_col = "ef_delta" if row.outcome == "executive_function" else "attention_delta"
    q["feature_early"] = num(q, feat + "_window_T1")
    q["feature_late"] = num(q, feat + "_window_T2")
    q["feature_delta"] = q.feature_late - q.feature_early
    q["cognitive_delta"] = num(q, outcome_col)
    q["coverage_active_days_early"] = num(q, "active_days_T1")
    q["coverage_active_days_late"] = num(q, "active_days_T2")
    q["coverage_snapshots_early"] = num(q, "snapshots_T1")
    q["coverage_snapshots_late"] = num(q, "snapshots_T2")
    q["coverage_valid_intervals_early"] = num(q, "valid_intervals_T1")
    q["coverage_valid_intervals_late"] = num(q, "valid_intervals_T2")
    keep = ["Subject_ID_D", "feature_early", "feature_late", "feature_delta", "cognitive_delta", "coverage_active_days_early", "coverage_active_days_late", "coverage_snapshots_early", "coverage_snapshots_late", "coverage_valid_intervals_early", "coverage_valid_intervals_late"]
    d = q[keep].replace([np.inf, -np.inf], np.nan).dropna(subset=["feature_delta", "cognitive_delta"])
    rho, p = spearmanr(d.feature_delta, d.cognitive_delta)
    exact = len(d) == int(row.n) and np.isclose(rho, float(row.estimate), atol=1e-6)
    audits.append({"top15_row": i + 1, "label": row.label, "historical_n": row.n, "reconstructed_n": len(d), "historical_rho": row.estimate, "reconstructed_rho": rho, "historical_p": row.p, "reconstructed_p": p, "matched_threshold_scenario": scenario, "threshold_match_status": "exact_reproduction" if exact else "threshold_reconstruction_mismatch"})
    d.insert(0, "top15_row", i + 1); d.insert(1, "label", row.label); d.insert(2, "threshold_scenario", scenario); rows.append(d)
    sm = {"top15_row": i + 1, "label": row.label, "threshold_scenario": scenario, "n": len(d)}
    for name in ["feature_early", "feature_late", "feature_delta", "cognitive_delta"]:
        x = pd.to_numeric(d[name], errors="coerce").dropna()
        sm.update({name + "_median": x.median(), name + "_iqr": x.quantile(.75) - x.quantile(.25), name + "_min": x.min(), name + "_max": x.max(), name + "_n": len(x)})
    change = pd.to_numeric(d.feature_delta, errors="coerce").dropna()
    sm.update({"positive_feature_changes": int((change > 0).sum()), "negative_feature_changes": int((change < 0).sum()), "zero_feature_changes": int((change == 0).sum())})
    summaries.append(sm)

pd.DataFrame(audits).to_csv(OUT / "top15_threshold_reconstruction_audit_v1.csv", index=False)
pd.concat(rows, ignore_index=True).to_csv(OUT / "top15_threshold_patient_level_table_v1.csv", index=False)
pd.DataFrame(summaries).to_csv(OUT / "top15_threshold_distribution_summary_v1.csv", index=False)
print(pd.DataFrame(audits).to_string(index=False))
