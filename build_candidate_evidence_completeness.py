"""Build candidate-specific evidence completeness staging JSON.

This is deliberately descriptive and reuses saved patient/window outputs. It does
not search new feature/outcome pairs or rerun the discovery/validation screens.
Final CSV authoring is handled by export_candidate_evidence_20261021_v1.mjs.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
BASE = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1"
STAGE = Path("/tmp/candidate_evidence_completeness_20261021")
STAGE.mkdir(parents=True, exist_ok=True)


def clean(v):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    return v


def stat(v, digits=6):
    return None if pd.isna(v) else round(float(v), digits)


def summarize(series: pd.Series) -> dict:
    x = pd.to_numeric(series, errors="coerce").dropna().to_numpy(float)
    if len(x) == 0:
        return {"n": 0, "missing": int(series.isna().sum()), "median": None, "iqr": None,
                "min": None, "max": None, "positive": 0, "negative": 0, "zero": 0}
    q25, q75 = np.quantile(x, [0.25, 0.75])
    return {"n": int(len(x)), "missing": int(series.isna().sum()), "median": stat(np.median(x)),
            "iqr": stat(q75 - q25), "min": stat(np.min(x)), "max": stat(np.max(x)),
            "positive": int((x > 0).sum()), "negative": int((x < 0).sum()), "zero": int((x == 0).sum())}


def bootstrap_iqr_effect(x, y, seed=20261021, reps=2000):
    """OLS change in outcome per observed feature IQR, descriptive only."""
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[ok], np.asarray(y)[ok]
    if len(x) < 5:
        return {"n": int(len(x)), "effect": None, "ci_low": None, "ci_high": None,
                "feature_iqr": None, "definition": "OLS outcome change per observed feature IQR"}
    iqr = float(np.quantile(x, .75) - np.quantile(x, .25))
    if iqr == 0:
        return {"n": int(len(x)), "effect": None, "ci_low": None, "ci_high": None,
                "feature_iqr": 0.0, "definition": "OLS outcome change per observed feature IQR"}
    def fit(xx, yy):
        slope = np.polyfit(xx, yy, 1)[0]
        return float(slope * iqr)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(reps, len(x)))
    vals = np.array([fit(x[ii], y[ii]) for ii in idx])
    return {"n": int(len(x)), "effect": stat(fit(x, y)),
            "ci_low": stat(np.quantile(vals, .025)), "ci_high": stat(np.quantile(vals, .975)),
            "feature_iqr": stat(iqr), "definition": "OLS outcome change per observed feature IQR"}


def row_for(d, feature, outcome, scope="T2_minus_T1"):
    z = d[(d.feature_name == feature) & (d.outcome == outcome) & (d.scope == scope)]
    return z.iloc[0].to_dict() if len(z) else {}


def distribution_rows(candidate_id, label, data, feature_col, outcome_prefix, coverage_cols, window_design):
    rows = []
    metrics = [
        ("feature_early", feature_col + "_T1"),
        ("feature_late", feature_col + "_T2"),
        ("feature_change", feature_col + "_delta"),
        ("cognitive_T1", outcome_prefix + "_T1"),
        ("cognitive_T2", outcome_prefix + "_T2"),
        ("cognitive_change", outcome_prefix + "_delta"),
    ]
    for metric, col in metrics:
        s = summarize(data[col])
        rows.append({"candidate_id": candidate_id, "candidate": label, "window_design": window_design,
                     "measure": metric, "source_column": col, **s})
    for metric, col in coverage_cols:
        s = summarize(data[col])
        rows.append({"candidate_id": candidate_id, "candidate": label, "window_design": window_design,
                     "measure": metric, "source_column": col, **s})
    return rows


def main():
    win = pd.read_csv(BASE / "keyboard_deep_dive_window_features.csv")
    cog = pd.read_csv(ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv")
    win["Subject_ID_D"] = win["Subject_ID_D"].astype(str)
    cog["Subject_ID_D"] = cog["Subject_ID_D"].astype(str)
    wide = win.pivot(index="Subject_ID_D", columns="window_name")
    wide.columns = [f"{c[0]}_{c[1]}" for c in wide.columns]
    wide = wide.reset_index()
    # The wide midpoint file is the saved Early/T1 and Late/T2 source for the
    # original six and for the legacy proxy. Delta is calculated T2 minus T1.
    for f in [
        "keyboard_12_18_median_inter_event_interval_ms",
        "keyboard_median_correction_recovery_time_ms",
        "keyboard_inter_event_interval_cv",
        "keyboard_18_24_median_inter_event_interval_ms",
        "keyboard_06_12_median_inter_event_interval_ms",
        "keyboard_median_word_completion_time_ms",
    ]:
        for suffix in ("T1", "T2"):
            if f"{f}_{suffix}" not in wide:
                wide[f"{f}_{suffix}"] = np.nan
        wide[f"{f}_delta"] = wide[f"{f}_T2"] - wide[f"{f}_T1"]
    for f in ["keyboard_active_days", "distinct_observations_in_window", "keyboard_valid_interval_count", "keyboard_unique_package_count"]:
        for suffix in ("T1", "T2"):
            if f"{f}_{suffix}" not in wide:
                wide[f"{f}_{suffix}"] = np.nan
    data = wide.merge(cog, on="Subject_ID_D", how="left", suffixes=("", "_cog"))

    discovery = pd.read_csv(BASE / "signal_discovery/signal_feature_associations.csv")
    adj = pd.read_csv(BASE / "signal_validation/validation_adjusted_associations.csv")
    val = pd.read_csv(BASE / "signal_validation/validation_summary.csv")
    legacy = pd.read_csv(ROOT / "output/analysis_candidates/keyboard_two_feature_median_timespan/keyboard_two_feature_associations.csv")
    word = pd.read_csv(BASE / "word_completion_timing_v1/word_completion_cognitive_associations.csv")
    word_adj = pd.read_csv(BASE / "word_completion_timing_v1/word_completion_recording_adjusted_associations.csv")
    word_pt = pd.read_csv(BASE / "word_completion_timing_v1/word_completion_patient_table.csv")
    word_pt["Subject_ID_D"] = word_pt["Subject_ID_D"].astype(str)

    specs = [
        ("K1", "Afternoon median snapshot IEI change → Executive Function change", "keyboard_12_18_median_inter_event_interval_ms", "executive_function", "ef", "T2−T1 midpoint windows", "median valid inter-snapshot interval, 12:00–18:00 local, milliseconds; not keystroke time", "ms", "credibility reduced after full technical adjustment; reliability is strong at T1 and lower at T2"),
        ("K2", "Median correction-recovery time change → Executive Function change", "keyboard_median_correction_recovery_time_ms", "executive_function", "ef", "T2−T1 midpoint windows", "median milliseconds from a detected deletion/correction snapshot to the first later within-burst text-growth snapshot", "ms", "robust to LOO/outlier/permutation and parsimonious adjustment; full recording adjustment attenuates"),
        ("K3", "Inter-event interval CV change → Executive Function change", "keyboard_inter_event_interval_cv", "executive_function", "ef", "T2−T1 midpoint windows", "SD divided by mean of valid inter-snapshot intervals (0<interval≤30 s), unitless", "unitless", "age/sex/education adjusted signal remains; full recording adjustment attenuates"),
        ("K4", "Evening median snapshot IEI change → Executive Function change", "keyboard_18_24_median_inter_event_interval_ms", "executive_function", "ef", "T2−T1 midpoint windows", "median valid inter-snapshot interval, 18:00–24:00 local, milliseconds; not keystroke time", "ms", "age/sex/education adjusted signal remains; recording adjustment crosses uncertainty"),
        ("K5", "Morning median snapshot IEI change → Executive Function change", "keyboard_06_12_median_inter_event_interval_ms", "executive_function", "ef", "T2−T1 midpoint windows", "median valid inter-snapshot interval, 06:00–12:00 local, milliseconds; not keystroke time", "ms", "age/sex/education adjusted signal remains; recording adjustment attenuates"),
        ("K6", "Afternoon median snapshot IEI change → Attention change", "keyboard_12_18_median_inter_event_interval_ms", "attention", "attention", "T2−T1 midpoint windows", "median valid inter-snapshot interval, 12:00–18:00 local, milliseconds; not keystroke time", "ms", "same feature as K1; same-cohort sensitivity, not independent replication"),
    ]
    evidence, distributions, sources = [], [], []
    for cid, label, feat, outcome, op, design, definition, units, status in specs:
        sub = data.copy()
        # Candidate-specific complete cases reproduce the saved discovery n.
        complete = sub[[f"{feat}_T1", f"{feat}_T2", f"{op}_T1", f"{op}_T2", f"{op}_delta"]].notna().all(axis=1)
        sub = sub.loc[complete].copy()
        dr = row_for(discovery, feat, outcome)
        vr = val[(val.feature_name == feat) & (val.outcome == outcome)]
        ar = adj[(adj.feature_name == feat) & (adj.outcome == outcome)]
        ar_txt = "; ".join(f"{r.adjustment}: rho={r.partial_rho:.3f}, p={r.partial_p:.4g}, q={r.fdr_q_within_adjustment:.4g}, n={int(r.n)}" for _, r in ar.iterrows())
        ci = bootstrap_iqr_effect(sub[f"{feat}_delta"].to_numpy(float), sub[f"{op}_delta"].to_numpy(float))
        cov = [("active_days_early", "keyboard_active_days_T1"), ("active_days_late", "keyboard_active_days_T2"),
               ("snapshots_early", "distinct_observations_in_window_T1"), ("snapshots_late", "distinct_observations_in_window_T2"),
               ("valid_intervals_early", "keyboard_valid_interval_count_T1"), ("valid_intervals_late", "keyboard_valid_interval_count_T2"),
               ("packages_early", "keyboard_unique_package_count_T1"), ("packages_late", "keyboard_unique_package_count_T2")]
        distributions += distribution_rows(cid, label, sub, feat, op, cov, design)
        evidence.append({
            "candidate_id": cid, "candidate": label, "feature_name": feat, "outcome": outcome,
            "window_design": design, "measurement_definition": definition, "units": units,
            "paired_complete_n": int(len(sub)), "feature_early_n": int(sub[f"{feat}_T1"].notna().sum()),
            "feature_late_n": int(sub[f"{feat}_T2"].notna().sum()), "outcome_change_n": int(sub[f"{op}_delta"].notna().sum()),
            "discovery_rho": clean(dr.get("spearman_rho")), "discovery_p": clean(dr.get("spearman_p")),
            "discovery_fdr_q": clean(dr.get("fdr_q")), "discovery_ci_low": clean(dr.get("bootstrap_ci_low")),
            "discovery_ci_high": clean(dr.get("bootstrap_ci_high")), "discovery_n": clean(dr.get("n")),
            "validated_rho": clean(vr.iloc[0].get("rho")) if len(vr) else None,
            "validated_p": clean(vr.iloc[0].get("p")) if len(vr) else None,
            "validated_fdr_q": clean(vr.iloc[0].get("fdr_q")) if len(vr) else None,
            "validated_ci_low": clean(vr.iloc[0].get("ci_low")) if len(vr) else None,
            "validated_ci_high": clean(vr.iloc[0].get("ci_high")) if len(vr) else None,
            "validated_n": clean(vr.iloc[0].get("n")) if len(vr) else None,
            "loo_range": f"[{vr.iloc[0].loo_min_rho:.3f}, {vr.iloc[0].loo_max_rho:.3f}]" if len(vr) else "not available",
            "outlier_filtered": f"n={int(vr.iloc[0].outlier_filtered_n)}, rho={vr.iloc[0].outlier_filtered_rho:.3f}" if len(vr) else "not available",
            "permutation": f"p={vr.iloc[0].permutation_p:.4g}, q={vr.iloc[0].permutation_fdr_q:.4g}, reps={int(vr.iloc[0].permutation_replicates)}" if len(vr) else "not available",
            "adjusted_results": ar_txt or "no saved adjusted result",
            "exploratory_effect_per_feature_iqr": ci["effect"], "exploratory_effect_ci_low": ci["ci_low"],
            "exploratory_effect_ci_high": ci["ci_high"], "feature_observed_iqr": ci["feature_iqr"],
            "effect_definition": ci["definition"],
            "coverage_summary": f"active days median T1/T2={stat(sub.keyboard_active_days_T1.median())}/{stat(sub.keyboard_active_days_T2.median())}; canonical snapshots median T1/T2={stat(sub.distinct_observations_in_window_T1.median())}/{stat(sub.distinct_observations_in_window_T2.median())}; valid intervals median T1/T2={stat(sub.keyboard_valid_interval_count_T1.median())}/{stat(sub.keyboard_valid_interval_count_T2.median())}",
            "device_app_comparability": "Saved window aggregates expose package counts but not package identity/device-set overlap for this candidate; the afternoon mechanism audit provides this only for K1/K6.",
            "missingness_and_limitations": "Complete-case n varies by feature/outcome; snapshot intervals are recording proxies and can reflect collection intensity, app/device composition, and gaps.",
            "evidence_status": status,
            "minimum_validation": "Predeclare comparable coverage/device/app rules; repeat paired extraction with canonical observations; adjust parsimoniously for baseline score, active days, snapshot/valid-interval rates, and device change; report LOO/permutation and reliability without outcome-driven thresholds.",
        })
        sources += [{"candidate_id": cid, "source_role": "discovery", "source_file": "output/analysis_candidates/keyboard_deep_dive_v1/signal_discovery/signal_feature_associations.csv", "stat_context": "34 features × 12 outcomes; BH q within discovery screen", "independent_replication": "no"},
                    {"candidate_id": cid, "source_role": "validation", "source_file": "output/analysis_candidates/keyboard_deep_dive_v1/signal_validation/validation_summary.csv", "stat_context": "same six candidates; LOO, outlier, permutation", "independent_replication": "no"},
                    {"candidate_id": cid, "source_role": "adjustment", "source_file": "output/analysis_candidates/keyboard_deep_dive_v1/signal_validation/validation_adjusted_associations.csv", "stat_context": "same-cohort partial Spearman sensitivity", "independent_replication": "no"}]

    # Legacy word proxy: current paired midpoint summaries, historical association preserved.
    cid, label, feat, outcome, op = "W1", "Legacy word-completion proxy → Attention T1", "keyboard_median_word_completion_time_ms", "attention", "attention"
    sub = data[["Subject_ID_D", f"{feat}_T1", f"{feat}_T2", "keyboard_active_days_T1", "keyboard_active_days_T2", "distinct_observations_in_window_T1", "distinct_observations_in_window_T2", "keyboard_valid_interval_count_T1", "keyboard_valid_interval_count_T2", "keyboard_unique_package_count_T1", "keyboard_unique_package_count_T2"]].merge(cog[["Subject_ID_D", "attention_T1", "attention_T2", "attention_delta"]], on="Subject_ID_D")
    complete = sub[[f"{feat}_T1", f"{feat}_T2", "attention_T1"]].notna().all(axis=1)
    sub = sub.loc[complete].copy(); sub[f"{feat}_delta"] = sub[f"{feat}_T2"] - sub[f"{feat}_T1"]
    lr = legacy[(legacy.feature_name == feat) & (legacy.outcome_column == "attention_T1")].iloc[0]
    ci = bootstrap_iqr_effect(sub[f"{feat}_T1"].to_numpy(float), sub["attention_T1"].to_numpy(float))
    distributions += distribution_rows(cid, label, sub, feat, op, [("active_days_early", "keyboard_active_days_T1"), ("active_days_late", "keyboard_active_days_T2"), ("snapshots_early", "distinct_observations_in_window_T1"), ("snapshots_late", "distinct_observations_in_window_T2"), ("valid_intervals_early", "keyboard_valid_interval_count_T1"), ("valid_intervals_late", "keyboard_valid_interval_count_T2"), ("packages_early", "keyboard_unique_package_count_T1"), ("packages_late", "keyboard_unique_package_count_T2")], "T2−T1 midpoint windows; legacy T1 association")
    evidence.append({"candidate_id": cid, "candidate": label, "feature_name": feat, "outcome": outcome, "window_design": "T2−T1 midpoint windows; legacy T1 association", "measurement_definition": "median inferred word-completion proxy: observed non-space start to later literal-space snapshot within device/package burst; snapshot proxy, not true keypress word time", "units": "ms", "paired_complete_n": int(len(sub)), "feature_early_n": int(sub[f"{feat}_T1"].notna().sum()), "feature_late_n": int(sub[f"{feat}_T2"].notna().sum()), "outcome_change_n": int(sub.attention_delta.notna().sum()), "discovery_rho": clean(lr.spearman_rho), "discovery_p": clean(lr.spearman_p_value), "discovery_fdr_q": None, "discovery_ci_low": None, "discovery_ci_high": None, "discovery_n": clean(lr.n_observed), "validated_rho": None, "validated_p": None, "validated_fdr_q": None, "validated_ci_low": None, "validated_ci_high": None, "validated_n": None, "loo_range": "not available", "outlier_filtered": "historical source removed 2 extreme feature values; no saved LOO", "permutation": "not available", "adjusted_results": "no saved adjusted result for this legacy T1 association", "exploratory_effect_per_feature_iqr": ci["effect"], "exploratory_effect_ci_low": ci["ci_low"], "exploratory_effect_ci_high": ci["ci_high"], "feature_observed_iqr": ci["feature_iqr"], "effect_definition": ci["definition"] + "; T1 Attention", "coverage_summary": f"active days median T1/T2={stat(sub.keyboard_active_days_T1.median())}/{stat(sub.keyboard_active_days_T2.median())}; canonical snapshots median T1/T2={stat(sub.distinct_observations_in_window_T1.median())}/{stat(sub.distinct_observations_in_window_T2.median())}", "device_app_comparability": "Saved aggregates expose package counts, not identity overlap/device-set comparability.", "missingness_and_limitations": "Historical association n=60 and 23.4568% feature missingness; two extreme feature values were removed; no saved q/CI/coverage adjustment.", "evidence_status": "nominal exploratory; incomplete evidence" , "minimum_validation": "Reconstruct legacy cohort from preserved source, predeclare outlier and coverage rules, add device/app comparability, and report bootstrap/LOO/permutation before interpretation."})
    sources.append({"candidate_id": cid, "source_role": "historical association", "source_file": "output/analysis_candidates/keyboard_two_feature_median_timespan/keyboard_two_feature_associations.csv", "stat_context": "legacy T1 screen; 2 extreme values removed; no q/CI", "independent_replication": "no"})

    # Word Completion v1 IQR delta -> Global delta, using its saved patient table.
    cid, label = "W2", "Word Completion v1 IQR change → Global cognitive change"
    wp = word_pt.copy()
    f = "word_completion_iqr_ms"; op = "global"
    wp["Subject_ID_D"] = wp["Subject_ID_D"].astype(str)
    wp = wp[wp[[f"{f}_T1", f"{f}_T2", "global_T1", "global_T2", "global_delta"]].notna().all(axis=1)].copy()
    wp["word_completion_iqr_ms_delta"] = wp["word_completion_iqr_ms_T2"] - wp["word_completion_iqr_ms_T1"]
    wr = word[(word.feature_name == "word_completion_iqr_ms_delta") & (word.outcome == "Global_delta")].iloc[0]
    wa = word_adj[(word_adj.feature_name == "word_completion_iqr_ms_delta") & (word_adj.outcome == "global_delta")].iloc[0]
    ci = bootstrap_iqr_effect(wp["word_completion_iqr_ms_delta"].to_numpy(float), wp["global_delta"].to_numpy(float))
    cov = [("active_days_early", "active_days_T1"), ("active_days_late", "active_days_T2"), ("snapshots_early", "distinct_observations_in_window_T1"), ("snapshots_late", "distinct_observations_in_window_T2"), ("valid_intervals_early", "valid_interval_count_T1"), ("valid_intervals_late", "valid_interval_count_T2"), ("high_conf_fraction_early", "high_confidence_fraction_T1"), ("high_conf_fraction_late", "high_confidence_fraction_T2")]
    distributions += distribution_rows(cid, label, wp, f, op, cov, "Word Completion v1 T1/T2 windows")
    evidence.append({"candidate_id": cid, "candidate": label, "feature_name": "word_completion_iqr_ms_delta", "outcome": "global", "window_design": "Word Completion v1 T2−T1 windows", "measurement_definition": "T2 minus T1 IQR of snapshot-observable word-completion intervals; candidate classes include high-confidence, partial, and ambiguous transitions", "units": "ms", "paired_complete_n": int(len(wp)), "feature_early_n": int(wp[f"{f}_T1"].notna().sum()), "feature_late_n": int(wp[f"{f}_T2"].notna().sum()), "outcome_change_n": int(wp.global_delta.notna().sum()), "discovery_rho": clean(wr.spearman_rho), "discovery_p": clean(wr.spearman_p), "discovery_fdr_q": clean(wr.fdr_q), "discovery_ci_low": clean(wr.bootstrap_ci_low), "discovery_ci_high": clean(wr.bootstrap_ci_high), "discovery_n": clean(wr.n), "validated_rho": clean(wa.partial_spearman_rho), "validated_p": clean(wa.partial_spearman_p), "validated_fdr_q": None, "validated_ci_low": None, "validated_ci_high": None, "validated_n": clean(wa.n), "loo_range": "not available", "outlier_filtered": "not available", "permutation": "not available", "adjusted_results": f"recording-adjusted covariates={wa.covariates}: partial rho={wa.partial_spearman_rho:.3f}, p={wa.partial_spearman_p:.4g}, n={int(wa.n)}; q/CI not saved", "exploratory_effect_per_feature_iqr": ci["effect"], "exploratory_effect_ci_low": ci["ci_low"], "exploratory_effect_ci_high": ci["ci_high"], "feature_observed_iqr": ci["feature_iqr"], "effect_definition": ci["definition"] + " using Word Completion v1 delta", "coverage_summary": f"active days median T1/T2={stat(wp.active_days_T1.median())}/{stat(wp.active_days_T2.median())}; snapshots median T1/T2={stat(wp.distinct_observations_in_window_T1.median())}/{stat(wp.distinct_observations_in_window_T2.median())}; high-confidence fraction median T1/T2={stat(wp.high_confidence_fraction_T1.median())}/{stat(wp.high_confidence_fraction_T2.median())}", "device_app_comparability": "Saved v1 aggregates provide unique package counts but not identity overlap; within-device/package extraction does not eliminate app composition effects.", "missingness_and_limitations": "Algorithm continuity/classification limitations: no true keypresses, incomplete snapshots, paste/predictive/autocorrect ambiguity, literal-space boundary, and saved adjusted screen lacks q/CI. Validate algorithm continuity before interpreting cognitive association.", "evidence_status": "uncertain; technical validation first", "minimum_validation": "Audit continuity against synthetic/state-transition cases; predeclare high-confidence-only and coverage/device/app rules; repeat paired reliability and permutation/LOO before any model integration."})
    sources += [{"candidate_id": cid, "source_role": "word discovery", "source_file": "output/analysis_candidates/keyboard_deep_dive_v1/word_completion_timing_v1/word_completion_cognitive_associations.csv", "stat_context": "Word Completion v1 exploratory screen; BH q within screen", "independent_replication": "no"}, {"candidate_id": cid, "source_role": "word adjustment", "source_file": "output/analysis_candidates/keyboard_deep_dive_v1/word_completion_timing_v1/word_completion_recording_adjusted_associations.csv", "stat_context": "recording-adjusted same-cohort screen; q/CI absent", "independent_replication": "no"}]

    payload = {"evidence": [{k: clean(v) for k, v in r.items()} for r in evidence], "distributions": [{k: clean(v) for k, v in r.items()} for r in distributions], "sources": sources, "metadata": {"version": "20261021_v1", "new_analyses": "candidate-specific descriptive distributions and exploratory OLS-per-feature-IQR summaries only", "historical_outputs_overwritten": False}}
    (STAGE / "tables.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"evidence_rows": len(evidence), "distribution_rows": len(distributions), "source_rows": len(sources), "stage": str(STAGE / 'tables.json')}, indent=2))


if __name__ == "__main__":
    main()
