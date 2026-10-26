"""Audit saved covariate availability for top-15 coverage adjustment."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/research_summary_20261025/top15_article_statistics_v1"
TOP = pd.read_csv(ROOT / "output/research_summary_20261025/top15_feature_cognition_associations_20261025.csv")
PATS = []
for name in ["top15_exact_patient_level_table.csv", "top15_threshold_patient_level_table_v1.csv", "top15_all_reconstructed_patient_level_table_v1.csv"]:
    q = pd.read_csv(OUT / name, dtype={"Subject_ID_D": str}); q["Subject_ID_D"] = q.Subject_ID_D.astype(str).str.zfill(3); PATS.append(q)
PAT = pd.concat(PATS, ignore_index=True).drop_duplicates(subset=["top15_row", "Subject_ID_D"])
C1 = pd.read_csv(ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv", dtype={"Subject_ID_D": str})
C1["Subject_ID_D"] = C1.Subject_ID_D.astype(str).str.zfill(3)
WIN = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/keyboard_deep_dive_window_features.csv", dtype={"Subject_ID_D": str})
WIN["Subject_ID_D"] = WIN.Subject_ID_D.astype(str).str.zfill(3)
dem = C1.set_index("Subject_ID_D")
cov = WIN.pivot(index="Subject_ID_D", columns="window_name", values=["active_local_days", "distinct_observations_in_window", "keyboard_valid_interval_count"])
cov.columns = [f"{a}_{b}" for a, b in cov.columns]
cov = cov.reset_index().set_index("Subject_ID_D")
rows = []
for i, r in TOP.iterrows():
    sub = PAT[PAT.top15_row.eq(i + 1)].copy()
    if r.outcome_timepoint == "T1":
        sub = sub[sub.feature_early.notna() & sub.cognitive_t1.notna()]
    else:
        sub = sub[sub.feature_delta.notna() & sub.cognitive_delta.notna()]
    ids = set(sub["Subject_ID_D"])
    if not ids:
        rows.append({"top15_row": i + 1, "label": r.label, "cohort_n": 0})
        continue
    idx = pd.Index(sorted(ids)); dd = dem.reindex(idx); cc = cov.reindex(idx)
    rows.append({
        "top15_row": i + 1, "label": r.label, "feature": r.feature, "outcome": r.outcome, "timepoint": r.outcome_timepoint,
        "cohort_n": len(idx), "age_n": int(dd.age.notna().sum()) if "age" in dd else 0, "sex_n": int(dd["Gender (1=M, 2=F)"].notna().sum()) if "Gender (1=M, 2=F)" in dd else 0, "education_n": int(dd["Education (years)"].notna().sum()) if "Education (years)" in dd else 0,
        "t1_active_days_n": int(cc.active_local_days_T1.notna().sum()) if "active_local_days_T1" in cc else 0, "t2_active_days_n": int(cc.active_local_days_T2.notna().sum()) if "active_local_days_T2" in cc else 0,
        "t1_snapshots_n": int(cc.distinct_observations_in_window_T1.notna().sum()) if "distinct_observations_in_window_T1" in cc else 0, "t2_snapshots_n": int(cc.distinct_observations_in_window_T2.notna().sum()) if "distinct_observations_in_window_T2" in cc else 0,
        "t1_valid_intervals_n": int(cc.keyboard_valid_interval_count_T1.notna().sum()) if "keyboard_valid_interval_count_T1" in cc else 0, "t2_valid_intervals_n": int(cc.keyboard_valid_interval_count_T2.notna().sum()) if "keyboard_valid_interval_count_T2" in cc else 0,
        "t1_device_count_n": 0, "t2_device_count_n": 0,
        "join_status": "coverage_and_demographics_joinable" if dd.age.notna().sum() == len(idx) and cc.active_local_days_T1.notna().sum() == len(idx) else "partial_join_or_missing_covariate",
    })
out = pd.DataFrame(rows)
out.to_csv(OUT / "top15_covariate_join_audit_v1.csv", index=False)
print(out.to_string(index=False))
