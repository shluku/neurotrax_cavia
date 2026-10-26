"""Complete missing top-15 CI/FDR fields from saved patient-level outputs.

Derived values are written separately and labeled; historical source values are
preserved unchanged.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/research_summary_20261025/top15_article_statistics_v1"
TOP = pd.read_csv(ROOT / "output/research_summary_20261025/top15_feature_cognition_associations_20261025.csv")
SIG = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/signal_discovery/signal_feature_associations.csv")
LEG = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_two_feature_median_timespan/keyboard_two_feature_associations.csv")
RESTRICTED = pd.read_csv(OUT / "top15_restricted_window_patient_table_v1.csv", dtype={"Subject_ID_D": str})
LEG_PAT = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_two_feature_median_timespan/keyboard_two_feature_patient_data.csv", dtype={"Subject_ID_D": str})

SEED = 20261026
BOOT = 5000

def bh(x):
    x = np.asarray(x, dtype=float); q = np.full(len(x), np.nan); ok = np.isfinite(x)
    if not ok.any(): return q
    idx = np.where(ok)[0]; order = idx[np.argsort(x[idx])]; ranked = x[order]
    adj = np.minimum.accumulate((ranked * len(ranked) / np.arange(1, len(ranked) + 1))[::-1])[::-1]
    q[order] = np.minimum(adj, 1.0); return q

def bootstrap_ci(x, y, seed):
    d = pd.DataFrame({"x": x, "y": y}).apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    rho = spearmanr(d.x, d.y).statistic
    rng = np.random.default_rng(seed); vals = []
    for _ in range(BOOT):
        idx = rng.integers(0, len(d), len(d)); vals.append(spearmanr(d.x.iloc[idx], d.y.iloc[idx]).statistic)
    return rho, float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5)), len(d)

# Partial-rank q-values are derived within the same T1/change screen only when
# the historical table contains the matching partial p-value. They are not the
# source file's unadjusted Spearman q-values.
SIG["partial_q_derived"] = np.nan
for scope in SIG.scope.dropna().unique():
    m = SIG.scope.eq(scope); SIG.loc[m, "partial_q_derived"] = bh(SIG.loc[m, "partial_spearman_p"])
legacy_q = bh(LEG.spearman_p_value)
LEG = LEG.assign(legacy_q_derived=legacy_q)

validation_keys = {
    ("keyboard_median_correction_recovery_time_ms", "executive_function"),
    ("keyboard_12_18_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_inter_event_interval_cv", "executive_function"),
    ("keyboard_18_24_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_06_12_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_12_18_median_inter_event_interval_ms", "attention"),
}
rows = []
for i, r in TOP.iterrows():
    row = r.to_dict(); feature = r.feature; outcome = r.outcome; tp = r.outcome_timepoint
    ci_low, ci_high, ci_source, ci_method = r.ci_low, r.ci_high, "historical_or_saved_recomputation", r.ci_method
    q_value, q_source, q_method = r.q, "historical_source", "saved source q-value"
    if not np.isfinite(q_value):
        if "signal_discovery" in str(r.source_file):
            ss = SIG[(SIG.feature_name.eq(feature)) & (SIG.outcome.eq(outcome)) & (SIG.scope.eq("T1" if tp == "T1" else "T2_minus_T1"))]
            if not ss.empty and np.isfinite(ss.iloc[0].partial_q_derived):
                q_value, q_source, q_method = ss.iloc[0].partial_q_derived, "derived_from_saved_partial_p", "BH across partial Spearman p-values within signal-discovery scope"
        elif "keyboard_two_feature" in str(r.source_file):
            ll = LEG[(LEG.feature_name.eq(feature)) & (LEG.outcome_column.eq(outcome))]
            if not ll.empty:
                q_value, q_source, q_method = ll.iloc[0].legacy_q_derived, "derived_from_saved_legacy_p", "BH across the 16 preselected legacy feature-outcome tests"
    if not (np.isfinite(ci_low) and np.isfinite(ci_high)):
        if i + 1 in (1, 6):
            d = RESTRICTED[RESTRICTED.top15_row.eq(i + 1)]
            x, y = d.feature_delta, d.cognitive_delta
            _, ci_low, ci_high, n_ci = bootstrap_ci(x, y, SEED + i)
            ci_source, ci_method = "recomputed_from_saved_patient_level_inputs", f"{BOOT}-resample percentile bootstrap of unadjusted Spearman; n={n_ci}"
        elif i + 1 in (12, 14):
            feat = feature; ycol = "attention_T1" if i + 1 == 12 else "global_T1"
            flag = "excluded_extreme_" + feat
            d = LEG_PAT.loc[~LEG_PAT[flag].astype(bool), [feat, ycol]].dropna()
            _, ci_low, ci_high, n_ci = bootstrap_ci(d[feat], d[ycol], SEED + i)
            ci_source, ci_method = "recomputed_from_saved_patient_level_inputs", f"{BOOT}-resample percentile bootstrap after documented legacy min/max trim; n={n_ci}"
    rows.append({
        "top15_row": i + 1, "label": r.label, "feature": feature, "outcome": outcome, "timepoint": tp,
        "estimate": r.estimate, "estimate_type": r.estimate_type, "n": r.n, "p": r.p,
        "q_final": q_value, "q_source": q_source, "q_method": q_method,
        "ci_low_final": ci_low, "ci_high_final": ci_high, "ci_source": ci_source, "ci_method": ci_method,
        "coverage_adjusted_evidence": "available_for_selected_six_validation" if (feature, outcome) in validation_keys else "not_saved_for_this_row",
        "reliability_robustness_evidence": "saved_selected_six_validation_outputs" if (feature, outcome) in validation_keys else "not_saved_for_this_row",
        "independent_validation": "not_performed",
        "article_status": "complete_saved_or_recomputed_descriptives" if np.isfinite(ci_low) and np.isfinite(ci_high) else "missing_CI",
    })
out = pd.DataFrame(rows)
out.to_csv(OUT / "top15_article_inferential_audit_v1.csv", index=False)
summary = pd.DataFrame([
    {"gap": "confidence_intervals", "resolved_rows": int(out.ci_low_final.notna().sum()), "total_rows": len(out), "remaining": int(out.ci_low_final.isna().sum()), "method": "saved CI where available; otherwise 5,000-resample bootstrap on exact saved cohort"},
    {"gap": "FDR_q_values", "resolved_rows": int(out.q_final.notna().sum()), "total_rows": len(out), "remaining": int(out.q_final.isna().sum()), "method": "saved q where available; otherwise explicitly derived within the documented signal or legacy testing family"},
    {"gap": "coverage_adjustment", "resolved_rows": int(out.coverage_adjusted_evidence.eq("available_for_selected_six_validation").sum()), "total_rows": len(out), "remaining": int(out.coverage_adjusted_evidence.ne("available_for_selected_six_validation").sum()), "method": "existing saved selected-six validation only"},
    {"gap": "independent_validation", "resolved_rows": 0, "total_rows": len(out), "remaining": len(out), "method": "no independent cohort or temporal validation saved"},
])
summary.to_csv(OUT / "top15_article_gap_summary_v1.csv", index=False)
print(out[["top15_row", "n", "p", "q_final", "q_source", "ci_low_final", "ci_high_final", "ci_source"]].to_string(index=False))
print(summary.to_string(index=False))
