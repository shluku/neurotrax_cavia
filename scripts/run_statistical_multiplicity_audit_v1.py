#!/usr/bin/env python3
"""Statistical rescue audit for the original keyboard discovery screen.

This script reads only saved discovery, patient-level window, cognitive, and
validation outputs. It never overwrites historical results.
"""

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, norm


ROOT = Path(__file__).resolve().parents[1]
DISC = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/signal_discovery"
PATIENT = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1"
OUT = ROOT / "output/analysis_candidates/statistical_multiplicity_audit_v1"
OUT.mkdir(parents=True, exist_ok=True)

BOOTSTRAP_SEED = 20261031
PERMUTATIONS = 1000


def bh(p_values: pd.Series | np.ndarray) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    out = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    idx = np.flatnonzero(ok)
    order = idx[np.argsort(p[idx])]
    ranked = p[order] * len(order) / np.arange(1, len(order) + 1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1]
    out[order] = np.minimum(adjusted, 1.0)
    return out


def fisher_sample_size(r: float, alpha: float, power: float) -> int:
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    return int(math.ceil(3 + ((z_alpha + z_power) / np.arctanh(r)) ** 2))


def reconstruct_longitudinal() -> tuple[pd.DataFrame, list[str], list[str]]:
    w = pd.read_csv(PATIENT / "keyboard_deep_dive_window_features.csv", dtype={"Subject_ID_D": str})
    w["Subject_ID_D"] = w["Subject_ID_D"].str.zfill(3)
    pivot = w.pivot(index="Subject_ID_D", columns="window_name")
    c = pd.read_csv(ROOT / "output/cognitive_master/master_cognitive_wide.csv", dtype={"Subject_ID_D": str}).set_index("Subject_ID_D")
    feature_cols = [x for x in w.columns if x.startswith("keyboard_") and x not in {"keyboard_raw_rows_in_window", "keyboard_duplicate_rows_removed", "keyboard_json_parse_errors"}]
    outcomes = {
        "global": "overall_Global score Δ",
        "memory": "overall_Memory Δ",
        "executive_function": "overall_EF Δ",
        "attention": "overall_Attention Δ",
        "processing_speed": "overall_Processing speed Δ",
        "motor": "overall_Motor Δ",
    }
    rows = []
    for feature in feature_cols:
        if (feature, "T1") not in pivot or (feature, "T2") not in pivot:
            continue
        row = pd.DataFrame({"Subject_ID_D": pivot.index, "feature_name": feature, "feature_delta": pivot[(feature, "T2")] - pivot[(feature, "T1")]})
        for outcome, col in outcomes.items():
            row[outcome] = c[col].reindex(pivot.index).to_numpy()
        rows.append(row)
    long = pd.concat(rows, ignore_index=True)
    return long, feature_cols, list(outcomes)


def max_t_permutation(long: pd.DataFrame, discovery: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    tests = []
    observed = []
    for _, row in discovery[discovery.scope.eq("T2_minus_T1")].iterrows():
        d = long[(long.feature_name == row.feature_name)].dropna(subset=[row.outcome, "feature_delta"])
        x = d.feature_delta.to_numpy(float)
        y = d[row.outcome].to_numpy(float)
        tests.append((row.feature_name, row.outcome, d[["Subject_ID_D", "feature_delta"]].copy()))
        observed.append(abs(float(spearmanr(x, y).statistic)))
    outcome_base = long.drop_duplicates("Subject_ID_D").set_index("Subject_ID_D")
    outcome_ids = {outcome: outcome_base.index[outcome_base[outcome].notna()].to_numpy() for outcome in discovery[discovery.scope.eq("T2_minus_T1")].outcome.unique()}
    max_stats = np.zeros(PERMUTATIONS)
    for b in range(PERMUTATIONS):
        permuted_outcomes = {}
        for outcome, ids in outcome_ids.items():
            permuted_outcomes[outcome] = dict(zip(ids, rng.permutation(outcome_base.loc[ids, outcome].to_numpy(float))))
        max_value = 0.0
        for (_, outcome, frame), obs in zip(tests, observed):
            y_perm = frame.Subject_ID_D.map(permuted_outcomes[outcome]).to_numpy(float)
            stat = abs(float(spearmanr(frame.feature_delta.to_numpy(float), y_perm).statistic))
            if np.isfinite(stat):
                max_value = max(max_value, stat)
        max_stats[b] = max_value
    rows = []
    for (feature, outcome, _), obs in zip(tests, observed):
        rows.append({
            "feature_name": feature,
            "outcome": outcome,
            "observed_abs_rho": obs,
            "maxT_permutation_replicates": PERMUTATIONS,
            "maxT_FWER_p": float((1 + np.sum(max_stats >= obs)) / (PERMUTATIONS + 1)),
            "procedure": "common patient-level outcome permutation within outcome across all eligible feature tests; maximum absolute rho across all 204 longitudinal tests; no nuisance-covariate adjustment",
        })
    return pd.DataFrame(rows)


def main() -> None:
    discovery = pd.read_csv(DISC / "signal_feature_associations.csv")
    long, features, outcomes = reconstruct_longitudinal()
    longitudinal = discovery[discovery.scope.eq("T2_minus_T1")].copy()
    longitudinal["q_reproduced_scope_bh"] = bh(longitudinal.spearman_p)
    longitudinal["q_difference"] = longitudinal.q_reproduced_scope_bh - longitudinal.fdr_q
    discovery_out = discovery.merge(longitudinal[["feature_name", "outcome", "q_reproduced_scope_bh", "q_difference"]], on=["feature_name", "outcome"], how="left")
    discovery_out.to_csv(OUT / "bh_reproduction_all_discovery_rows.csv", index=False)

    family = discovery.groupby(["scope", "outcome", "family"], as_index=False).agg(
        n_tests=("feature_name", "size"), min_p=("spearman_p", "min"), min_q=("fdr_q", "min"),
    )
    family.to_csv(OUT / "original_testing_family_audit.csv", index=False)

    dup = discovery[discovery.duplicated(["scope", "outcome", "feature_name"], keep=False)].copy()
    dup.to_csv(OUT / "duplicate_hypotheses.csv", index=False)

    # Feature and outcome dependence among exact longitudinal paired data.
    discovery_features = sorted(discovery.feature_name.unique())
    wide = long[long.feature_name.isin(discovery_features)].pivot(index="Subject_ID_D", columns="feature_name", values="feature_delta")
    pairs = []
    cols = discovery_features
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            z = wide[[a, b]].dropna()
            if len(z) >= 10:
                rho = float(spearmanr(z[a], z[b]).statistic)
                if abs(rho) >= 0.7:
                    pairs.append({"feature_a": a, "feature_b": b, "n": len(z), "spearman_rho": rho, "absolute_rho": abs(rho)})
    pd.DataFrame(pairs).sort_values("absolute_rho", ascending=False).to_csv(OUT / "highly_correlated_longitudinal_feature_pairs.csv", index=False)
    outcome_wide = long.drop_duplicates(["Subject_ID_D"])[["Subject_ID_D", *outcomes]].set_index("Subject_ID_D")
    outcome_corr = outcome_wide.corr(method="spearman", min_periods=10).stack().reset_index()
    outcome_corr.columns = ["outcome_a", "outcome_b", "spearman_rho"]
    outcome_corr = outcome_corr[outcome_corr.outcome_a < outcome_corr.outcome_b]
    outcome_corr.to_csv(OUT / "longitudinal_outcome_dependence.csv", index=False)

    # Grouped BH comparisons are descriptive framework comparisons, not replacement claims.
    lead_keys = [
        ("keyboard_median_correction_recovery_time_ms", "executive_function"),
        ("keyboard_12_18_median_inter_event_interval_ms", "executive_function"),
        ("keyboard_inter_event_interval_cv", "executive_function"),
    ]
    comp = longitudinal[["feature_name", "outcome", "family", "spearman_p", "fdr_q"]].copy()
    comp["q_by_outcome"] = comp.groupby("outcome")["spearman_p"].transform(lambda s: bh(s.to_numpy()))
    comp["q_by_family_outcome"] = comp.groupby(["family", "outcome"])["spearman_p"].transform(lambda s: bh(s.to_numpy()))
    comp["is_lead_signal"] = comp.apply(lambda r: (r.feature_name, r.outcome) in lead_keys, axis=1)
    comp[comp.is_lead_signal].to_csv(OUT / "multiplicity_strategy_lead_signal_comparison.csv", index=False)

    max_t = max_t_permutation(long, discovery)
    max_t.to_csv(OUT / "dependence_aware_maxT_permutation_1000.csv", index=False)

    # Existing robustness and measurement outputs, copied into an audit-facing table.
    rob = pd.read_csv(PATIENT / "signal_validation/validation_robustness.csv")
    adj = pd.read_csv(PATIENT / "signal_validation/validation_adjusted_associations.csv")
    rel = pd.read_csv(PATIENT / "signal_validation/validation_reliability.csv")
    mechanism = pd.read_csv(PATIENT / "afternoon_interval_mechanism_audit_20261020/exploratory_adjusted_associations.csv")
    rob.to_csv(OUT / "leading_signal_robustness_existing.csv", index=False)
    adj.to_csv(OUT / "leading_signal_adjustment_existing.csv", index=False)
    rel.to_csv(OUT / "leading_signal_reliability_existing.csv", index=False)
    mechanism.to_csv(OUT / "primary_poc_technical_adjustment_existing.csv", index=False)

    scenarios = []
    for r in (0.25, 0.30, 0.35, 0.40, 0.45, 0.50):
        for alpha_label, alpha in [("FWER .05, one primary", .05), ("FWER .05, 3 primary hypotheses Bonferroni", .05 / 3)]:
            for power in (.80, .90):
                scenarios.append({"assumed_absolute_r": r, "alpha_rule": alpha_label, "power": power, "required_independent_n_approx": fisher_sample_size(r, alpha, power)})
    pd.DataFrame(scenarios).to_csv(OUT / "confirmatory_sample_size_scenarios.csv", index=False)

    manifest = {
        "status": "complete",
        "source_discovery_rows": int(len(discovery)),
        "original_longitudinal_tests": int(len(longitudinal)),
        "features_tested": int(discovery.feature_name.nunique()),
        "saved_window_feature_columns_reconstructed": int(len(features)),
        "outcomes": outcomes,
        "bh_reproduction_max_abs_difference": float(np.nanmax(np.abs(longitudinal.q_difference))),
        "duplicate_hypothesis_rows": int(len(dup)),
        "maxT_permutations": PERMUTATIONS,
        "historical_results_overwritten": False,
        "post_selection_analyses_labeled_separately": True,
    }
    (OUT / "audit_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
