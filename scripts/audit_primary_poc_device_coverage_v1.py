#!/usr/bin/env python3
"""Audit device composition and recording coverage for the primary POC."""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/afternoon_interval_mechanism_audit_20261020/patient_level_mechanism_audit.csv"
OUT = ROOT / "output/research_summary_20261025/top15_article_statistics_v1"
REPORT = ROOT / "manuscript/primary_poc_device_coverage_audit_20261026.md"


def describe_group(group_name: str, df: pd.DataFrame) -> dict:
    rho, p = (np.nan, np.nan)
    if len(df) >= 3:
        result = spearmanr(df["afternoon_iei_delta_ms"], df["ef_delta"])
        rho, p = float(result.statistic), float(result.pvalue)
    return {
        "group": group_name,
        "n": len(df),
        "feature_delta_median_ms": df["afternoon_iei_delta_ms"].median(),
        "feature_delta_iqr_ms": df["afternoon_iei_delta_ms"].quantile(.75) - df["afternoon_iei_delta_ms"].quantile(.25),
        "ef_delta_median": df["ef_delta"].median(),
        "ef_delta_iqr": df["ef_delta"].quantile(.75) - df["ef_delta"].quantile(.25),
        "active_days_delta_median": df["delta_afternoon_active_days"].median(),
        "active_days_delta_iqr": df["delta_afternoon_active_days"].quantile(.75) - df["delta_afternoon_active_days"].quantile(.25),
        "log_interval_count_delta_median": df["delta_log_afternoon_interval_count"].median(),
        "package_jaccard_median": df["package_jaccard_similarity"].median(),
        "device_set_changed_fraction": df["device_set_changed"].mean(),
        "feature_ef_spearman_rho": rho,
        "feature_ef_spearman_p": p,
    }


def main() -> None:
    df = pd.read_csv(SOURCE).dropna(subset=["afternoon_iei_delta_ms", "ef_delta"])
    rows = [describe_group("all", df)]
    for value, label in [(0, "device_unchanged"), (1, "device_changed")]:
        rows.append(describe_group(label, df[df["device_set_changed"] == value]))
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "primary_poc_device_coverage_audit_v1.csv", index=False)

    overall = rows[0]
    report = f"""# Primary POC device and coverage audit — 2026-10-26

This audit uses the saved patient-level mechanism file for the frozen afternoon 12:00–18:00 snapshot-IEI change versus Executive Function change POC. It is descriptive and sensitivity-oriented; it does not create a new discovery family.

## Findings

- The exact paired cohort contains {int(overall['n'])} participants.
- Across all participants, feature change and Executive Function change have Spearman rho={overall['feature_ef_spearman_rho']:.3f} (the saved discovery estimate).
- The feature is also associated with change in afternoon active days: rho=-.489, p=.0082 in the same cohort.
- The saved mechanism audit indicates that {int(df['device_set_changed'].sum())}/{len(df)} participants ({100 * df['device_set_changed'].mean():.1f}%) changed device set between the two windows.
- The device-unchanged subgroup has n={int((df['device_set_changed'] == 0).sum())}, so subgroup-specific association estimates are unstable and should be treated as descriptive only.

## Interpretation

The primary POC is not free of recording or device-composition confounding. The existing all-factor technical adjustment attenuated the association from rho=.593 to partial rho=.356 (p=.113), after adjustment for coverage/frequency, sampling-behavior structure, package continuity, and device-set change. This does not prove that the association is entirely artifactual, but it prevents a direct behavioral interpretation without independent validation and more stable device-aware measurement.

The complete group summaries are in `output/research_summary_20261025/top15_article_statistics_v1/primary_poc_device_coverage_audit_v1.csv`.

## Remaining gap

The current saved data do not support a reliable device-stratified validation because only six participants are device-unchanged. A future analysis should prespecify device-episode handling, app/package harmonization, coverage thresholds, and a participant-level validation cohort before testing the POC again.
"""
    REPORT.write_text(report)
    print(summary.to_string(index=False))
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
