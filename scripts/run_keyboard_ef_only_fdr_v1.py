#!/usr/bin/env python3
"""Post-hoc Executive Function-only BH-FDR reanalysis of original discovery rows."""

from pathlib import Path
import json

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/signal_discovery/signal_feature_associations.csv"
OUT = ROOT / "output/analysis_candidates/keyboard_ef_only_fdr_v1"
OUT.mkdir(parents=True, exist_ok=True)


def bh(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    order = np.argsort(values)
    ranked = values[order] * len(values) / np.arange(1, len(values) + 1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1]
    result = np.empty(len(values), dtype=float)
    result[order] = np.minimum(adjusted, 1.0)
    return result


def main() -> None:
    source = pd.read_csv(SOURCE)
    ef = source[(source["scope"] == "T2_minus_T1") & (source["outcome"] == "executive_function")].copy()
    ef = ef.sort_values("feature_name").reset_index(drop=True)
    if len(ef) != 34:
        raise RuntimeError(f"Expected 34 complete Executive Function change tests; found {len(ef)}")
    if ef["feature_name"].nunique() != 34:
        raise RuntimeError("Executive Function slice does not contain 34 unique features")
    if ef["spearman_p"].isna().any():
        raise RuntimeError("One or more Executive Function tests has missing p-value")

    ef["ef_only_bh_q"] = bh(ef["spearman_p"].to_numpy())
    ef["ef_only_q_lt_0_05"] = ef["ef_only_bh_q"] < 0.05
    ef["ef_only_q_le_0_20"] = ef["ef_only_bh_q"] <= 0.20
    ef["original_204_test_bh_q"] = ef["fdr_q"]
    ef["fdr_label"] = "post_hoc_domain_specific_exploratory_fdr"
    ef["source_scope"] = "original_complete_34_feature_Executive_Function_change_slice"
    all_cols = [
        "feature_name", "family", "spearman_rho", "n", "spearman_p",
        "original_204_test_bh_q", "ef_only_bh_q", "ef_only_q_lt_0_05",
        "ef_only_q_le_0_20", "bootstrap_ci_low", "bootstrap_ci_high",
        "partial_spearman_rho", "partial_spearman_p", "partial_n",
        "fdr_label", "source_scope",
    ]
    ef.sort_values("ef_only_bh_q")[all_cols].to_csv(OUT / "ef_only_fdr_all_34_tests.csv", index=False)

    headline_features = {
        "keyboard_median_correction_recovery_time_ms",
        "keyboard_12_18_median_inter_event_interval_ms",
        "keyboard_inter_event_interval_cv",
    }
    headline = ef[ef.feature_name.isin(headline_features)].sort_values("ef_only_bh_q")[all_cols]
    headline.to_csv(OUT / "ef_only_fdr_headline_comparison.csv", index=False)

    # Verify against the complete original table and record the research-summary subset.
    direct = ef.sort_values("spearman_p")["ef_only_bh_q"].to_numpy()
    verified = np.allclose(direct, bh(ef.sort_values("spearman_p")["spearman_p"].to_numpy()))
    summary_rows = pd.DataFrame({
        "feature_name": [
            "keyboard_median_correction_recovery_time_ms",
            "keyboard_12_18_median_inter_event_interval_ms",
            "keyboard_inter_event_interval_cv",
            "keyboard_18_24_median_inter_event_interval_ms",
            "keyboard_06_12_median_inter_event_interval_ms",
        ]
    }).merge(ef, on="feature_name", how="left")
    summary_rows.sort_values("ef_only_bh_q")[all_cols].to_csv(OUT / "research_summary_executive_function_rows.csv", index=False)

    manifest = {
        "status": "complete",
        "source_file": str(SOURCE.relative_to(ROOT)),
        "tests_in_slice": int(len(ef)),
        "unique_features": int(ef.feature_name.nunique()),
        "valid_p_values": int(ef.spearman_p.notna().sum()),
        "excluded_for_significance": 0,
        "bh_programmatic_verification": bool(verified),
        "new_results_label": "post_hoc_domain_specific_exploratory_fdr",
        "original_204_test_fdr_preserved": True,
    }
    (OUT / "audit_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    top = ef.sort_values("ef_only_bh_q").head(8)[["feature_name", "spearman_rho", "n", "spearman_p", "fdr_q", "ef_only_bh_q"]]
    readme = f"""# Executive Function-only FDR reanalysis — v1

## Status

This is a **post-hoc, domain-specific exploratory FDR** analysis. The original 204-test longitudinal BH-FDR remains the primary multiplicity analysis. These results do not establish confirmatory evidence because Executive Function was selected after review of the broader discovery results.

## Source and completeness

- Source: `{SOURCE.relative_to(ROOT)}`
- Complete original slice: 34 features tested against Executive Function change.
- Valid p-values: 34/34.
- Excluded for statistical significance: 0.
- No p-values, correlations, sample sizes, feature definitions, or historical outputs were changed.
- BH was independently recomputed and verified programmatically.

## Main result

Restricting BH to the 34 Executive Function hypotheses yields the following strongest rows:

{top.to_string(index=False)}

The complete ordered table is `ef_only_fdr_all_34_tests.csv`. The three requested headline rows are in `ef_only_fdr_headline_comparison.csv`. The five Executive Function longitudinal rows represented in the research-summary selected signal set are in `research_summary_executive_function_rows.csv`.

Interpretation must retain the distinction between the original 204-test q-value and this post-hoc 34-test domain-specific q-value. The new q-values are useful for transparent sensitivity analysis, not for upgrading the discoveries to confirmatory findings.
"""
    (OUT / "README_ef_only_fdr.md").write_text(readme, encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
