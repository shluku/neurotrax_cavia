"""Build the manuscript-facing table for the six prespecified keyboard signals."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/research_summary_20261025/top15_article_statistics_v1"
K = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1"
signals = [
    ("keyboard_median_correction_recovery_time_ms", "executive_function"),
    ("keyboard_12_18_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_inter_event_interval_cv", "executive_function"),
    ("keyboard_18_24_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_06_12_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_12_18_median_inter_event_interval_ms", "attention"),
]
disc = pd.read_csv(K / "signal_discovery/signal_feature_associations.csv")
adj = pd.read_csv(K / "signal_validation/validation_adjusted_associations.csv")
rob = pd.read_csv(K / "signal_validation/validation_robustness.csv")
rel = pd.read_csv(K / "signal_validation/validation_reliability.csv")
third = pd.read_csv(K / "thirds_sensitivity_corrected_v2/corrected_coverage_adjusted_associations.csv")
rows = []
for feature, outcome in signals:
    d = disc[(disc.feature_name.eq(feature)) & (disc.outcome.eq(outcome)) & disc.scope.eq("T2_minus_T1")].iloc[0]
    a = adj[(adj.feature_name.eq(feature)) & (adj.outcome.eq(outcome)) & adj.adjustment.eq("core_baseline_recording")].iloc[0]
    r = rob[(rob.feature_name.eq(feature)) & (rob.outcome.eq(outcome))].iloc[0]
    t = third[(third.feature_name.eq(feature + "_delta")) & (third.outcome.eq(outcome))].iloc[0]
    t1 = rel[(rel.feature_name.eq(feature)) & rel.window_name.eq("T1") & rel.method.eq("first_last_14_observed_days")]
    t2 = rel[(rel.feature_name.eq(feature)) & rel.window_name.eq("T2") & rel.method.eq("first_last_14_observed_days")]
    rows.append({
        "feature_name": feature, "outcome": outcome,
        "discovery_n": d.n, "discovery_rho": d.spearman_rho, "discovery_p": d.spearman_p, "discovery_q": d.fdr_q, "discovery_ci_low": d.bootstrap_ci_low, "discovery_ci_high": d.bootstrap_ci_high,
        "recording_adjusted_n": a.n, "recording_adjusted_partial_rho": a.partial_rho, "recording_adjusted_p": a.partial_p, "recording_adjusted_q": a.fdr_q_within_adjustment, "recording_adjusted_ci_low": a.bootstrap_ci_low, "recording_adjusted_ci_high": a.bootstrap_ci_high,
        "loo_min_rho": r.loo_min_rho, "loo_max_rho": r.loo_max_rho, "loo_sign_consistency": r.loo_sign_consistency, "outlier_filtered_n": r.outlier_filtered_n, "outlier_filtered_rho": r.outlier_filtered_rho, "permutation_p": r.permutation_p, "permutation_q": r.permutation_fdr_q,
        "t1_reliability_n": int(t1.n_patients.iloc[0]) if not t1.empty else pd.NA, "t1_icc": t1.icc_2_1_absolute_agreement.iloc[0] if not t1.empty else pd.NA, "t1_spearman": t1.split_half_spearman_rho.iloc[0] if not t1.empty else pd.NA,
        "t2_reliability_n": int(t2.n_patients.iloc[0]) if not t2.empty else pd.NA, "t2_icc": t2.icc_2_1_absolute_agreement.iloc[0] if not t2.empty else pd.NA, "t2_spearman": t2.split_half_spearman_rho.iloc[0] if not t2.empty else pd.NA,
        "corrected_thirds_n": t.n_corrected, "corrected_thirds_partial_rho": t.partial_spearman_rho_corrected, "corrected_thirds_p": t.partial_spearman_p_corrected, "corrected_thirds_q": t.fdr_q_corrected, "corrected_thirds_ci_low": t.bootstrap_ci_low_corrected, "corrected_thirds_ci_high": t.bootstrap_ci_high_corrected,
    })
out = pd.DataFrame(rows)
out.to_csv(OUT / "six_signal_article_ready_table_v1.csv", index=False)
print(out.to_string(index=False))
