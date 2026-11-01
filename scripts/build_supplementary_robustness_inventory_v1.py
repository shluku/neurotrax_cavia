#!/usr/bin/env python3
"""Inventory saved robustness evidence for the nine supplementary top-15 rows."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "output/research_summary_20261025/top15_article_statistics_v1"
OUT = BASE / "top15_supplementary_robustness_inventory_v1.csv"
REPORT = ROOT / "manuscript/supplementary_robustness_inventory_20261026.md"


def main() -> None:
    audit = pd.read_csv(BASE / "top15_article_inferential_audit_v1.csv")
    saved = pd.read_csv(BASE / "top15_restricted_legacy_robustness_v1.csv")
    supplementary = audit[~audit["top15_row"].isin([2, 3, 4, 5, 7, 11])].copy()
    saved = saved.rename(columns={"rho": "robustness_rho", "p": "robustness_p"})
    keep = ["top15_row", "loo_min_rho", "loo_max_rho", "loo_sign_consistency", "outlier_filtered_n", "outlier_filtered_rho", "permutation_replicates", "permutation_p", "interpretation"]
    result = supplementary.merge(saved[["top15_row", *keep[1:]]], on="top15_row", how="left")
    result["saved_loo_outlier_permutation"] = result["loo_min_rho"].notna()
    result["robustness_status"] = result["saved_loo_outlier_permutation"].map({True: "partial_saved_robustness", False: "not_saved"})
    result["remaining_need"] = result["saved_loo_outlier_permutation"].map({True: "reliability, coverage-adjustment, and independent validation remain missing", False: "LOPO, outlier, permutation, reliability, and alternate-window sensitivity"})
    result.to_csv(OUT, index=False)

    saved_n = int(result["saved_loo_outlier_permutation"].sum())
    missing_n = int((~result["saved_loo_outlier_permutation"]).sum())
    report = f"""# Supplementary robustness inventory — 2026-10-26

The nine supplementary top-15 rows were checked against the saved restricted/legacy robustness output. This inventory reports availability; it does not treat saved robustness as independent validation.

- {saved_n}/9 supplementary rows have saved leave-one-out, outlier-filtered, and permutation outputs: restricted rows 1 and 6, and legacy trimmed rows 12 and 14.
- {missing_n}/9 rows have no equivalent saved robustness output: baseline word-completion rows 8–10, morning IEI-IQR row 13, and active-days row 15.
- None of the nine rows has independent validation or complete test–retest reliability evidence.

The machine-readable inventory is `output/research_summary_20261025/top15_article_statistics_v1/top15_supplementary_robustness_inventory_v1.csv`.

## Reporting consequence

Rows with saved robustness may be described as having exploratory robustness checks only. Rows without saved robustness should be reported with their association estimate, confidence interval, cohort rule, and limitations, but not as robust findings. The entire set remains supplementary and exploratory.
"""
    REPORT.write_text(report)
    print(result[["top15_row", "label", "robustness_status", "remaining_need"]].to_string(index=False))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
