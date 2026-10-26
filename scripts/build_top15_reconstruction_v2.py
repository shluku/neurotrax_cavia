"""Consolidate all recoverable top-15 patient cohorts from saved outputs."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/research_summary_20261025/top15_article_statistics_v1"
TOP = pd.read_csv(ROOT / "output/research_summary_20261025/top15_feature_cognition_associations_20261025.csv")
OLD = pd.read_csv(OUT / "top15_reconstruction_audit.csv")
TH = pd.read_csv(OUT / "top15_threshold_reconstruction_audit_v1.csv")

def norm(s):
    return s.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(3)

w = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/keyboard_deep_dive_window_features.csv", dtype={"Subject_ID_D": str}); w.Subject_ID_D = norm(w.Subject_ID_D)
wide = w.pivot(index="Subject_ID_D", columns="window_name", values=["keyboard_06_12_median_inter_event_interval_ms", "keyboard_median_correction_recovery_time_ms"])
wide.columns = [f"{a}_{b}" for a, b in wide.columns]; wide = wide.reset_index()
c1 = pd.read_csv(ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv", dtype={"Subject_ID_D": str}); c1.Subject_ID_D = norm(c1.Subject_ID_D)
c2 = pd.read_csv(ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv", dtype={"Subject_ID_D": str}); c2.Subject_ID_D = norm(c2.Subject_ID_D)
third = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity/third_patient_data_min7.csv", dtype={"Subject_ID_D": str}); third.Subject_ID_D = norm(third.Subject_ID_D)

specs = {
    1: ("keyboard_06_12_median_inter_event_interval_ms", "attention_delta", "midpoint"),
    6: ("keyboard_median_correction_recovery_time_ms", "attention_delta", "midpoint"),
}
rows = []
audits = []
for rownum, (feature, outcome, _) in specs.items():
    r = TOP.iloc[rownum - 1]
    q = third[["Subject_ID_D", feature + "_delta"]].merge(wide[["Subject_ID_D", feature + "_T1", feature + "_T2"]], on="Subject_ID_D", how="inner")
    q = q.merge(c2[["Subject_ID_D", outcome]], on="Subject_ID_D", how="inner")
    q["feature_delta_reconstructed"] = q[feature + "_T2"] - q[feature + "_T1"]
    # The thirds cohort is the fixed min-7 active-day cohort; the historical
    # midpoint comparison then drops rows missing the feature or outcome.
    q = q[q[feature + "_delta"].notna() & q["feature_delta_reconstructed"].notna() & q[outcome].notna()].copy()
    rho, p = spearmanr(q["feature_delta_reconstructed"], q[outcome])
    exact = len(q) == int(r.n) and np.isclose(rho, float(r.estimate), atol=1e-6)
    audits.append({"top15_row": rownum, "label": r.label, "historical_n": r.n, "reconstructed_n": len(q), "historical_rho": r.estimate, "reconstructed_rho": rho, "historical_p": r.p, "reconstructed_p": p, "cohort_rule": "first/last thirds eligible cohort: >=7 active days in each third; midpoint comparison on same patients", "cohort_match_status": "exact_reproduction" if exact else "reconstruction_mismatch"})
    q = q.rename(columns={feature + "_T1": "feature_early", feature + "_T2": "feature_late", "feature_delta_reconstructed": "feature_delta", outcome: "cognitive_delta"})
    q["cognitive_t1"] = q.Subject_ID_D.map(c1.set_index("Subject_ID_D")["attention_T1"])
    q["cognitive_t2"] = q.Subject_ID_D.map(c2.set_index("Subject_ID_D")["attention_T2"])
    cov = w[w.window_name.isin(["T1", "T2"])].pivot(index="Subject_ID_D", columns="window_name", values=["active_local_days", "distinct_observations_in_window", "keyboard_valid_interval_count"])
    cov.columns = [f"{a}_{b}" for a, b in cov.columns]; cov = cov.reset_index()
    q = q.merge(cov, on="Subject_ID_D", how="left")
    q = q.rename(columns={"active_local_days_T1": "coverage_active_days_early", "active_local_days_T2": "coverage_active_days_late", "distinct_observations_in_window_T1": "coverage_snapshots_early", "distinct_observations_in_window_T2": "coverage_snapshots_late", "keyboard_valid_interval_count_T1": "coverage_valid_intervals_early", "keyboard_valid_interval_count_T2": "coverage_valid_intervals_late"})
    q.insert(0, "top15_row", rownum); q.insert(1, "label", r.label); q.insert(2, "cohort_rule", "thirds_min7_same_patients_midpoint_comparison")
    rows.append(q[["top15_row", "label", "cohort_rule", "Subject_ID_D", "feature_early", "feature_late", "feature_delta", "cognitive_t1", "cognitive_t2", "cognitive_delta", "coverage_active_days_early", "coverage_active_days_late", "coverage_snapshots_early", "coverage_snapshots_late", "coverage_valid_intervals_early", "coverage_valid_intervals_late"]])

new_audit = pd.DataFrame(audits)
audit = OLD.copy()
for _, nr in pd.concat([TH.rename(columns={"historical_n": "source_n", "reconstructed_n": "reconstructed_n", "historical_rho": "source_rho", "reconstructed_rho": "reconstructed_rho", "historical_p": "source_p", "reconstructed_p": "reconstructed_p", "threshold_match_status": "cohort_match_status"}), new_audit], ignore_index=True).iterrows():
    idx = audit.index[audit.top15_row.eq(nr.top15_row)]
    if len(idx):
        audit.loc[idx[0], "reconstructed_n"] = nr.get("reconstructed_n", np.nan)
        audit.loc[idx[0], "reconstructed_rho"] = nr.get("reconstructed_rho", np.nan)
        audit.loc[idx[0], "cohort_match_status"] = nr.get("cohort_match_status", "")
        audit.loc[idx[0], "rho_difference"] = nr.get("reconstructed_rho", np.nan) - float(audit.loc[idx[0], "source_n"] * 0 + TOP.iloc[int(nr.top15_row)-1].estimate) if pd.notna(nr.get("reconstructed_rho", np.nan)) else np.nan
audit.to_csv(OUT / "top15_reconstruction_audit_v2.csv", index=False)
pd.concat(rows, ignore_index=True).to_csv(OUT / "top15_restricted_window_patient_table_v1.csv", index=False)
pd.DataFrame(audits).to_csv(OUT / "top15_restricted_window_reconstruction_v1.csv", index=False)
print(new_audit.to_string(index=False))
print("exact reconstructed rows in v2:", int(audit.cohort_match_status.eq("exact_reproduction").sum()), "/", len(audit))
