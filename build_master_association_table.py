#!/usr/bin/env python3
"""Build a source-linked master table of saved direct feature–cognition results.

This is a cataloging task only. It imports saved association outputs, adds the
saved Phase 11 feature-vs-Global-T1 group contrasts, and writes a versioned
table. It never recomputes a correlation, p-value, q-value, CI, or model.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).parent
TABLE_DIR = ROOT / "manuscript/tables"
BASE = TABLE_DIR / "research_review_all_saved_direct_correlations_20261020.csv"
PHASE11 = ROOT / "output/analysis_candidates/phase11_t1_baseline/clinical_tables_baseline_severity/phase11_baseline_severity_all_features.csv"
SUPPLEMENTAL = ROOT / "output/analysis_candidates/supplemental_modalities/phase4_24h_t1/phase4_supplemental_feature_review.csv"
OUT = TABLE_DIR / "master_association_table_20261020.csv"


def source_metadata(source_file: str) -> tuple[str, str, str, str, str]:
    """Return phase, design, evidence role, coverage status and scope note."""
    if "signal_discovery" in source_file:
        return ("Keyboard Deep Dive — Signal Discovery", "feature-level Spearman screen", "original comprehensive screen", "unadjusted / demographic-adjusted variants", "FDR within a 204-hypothesis T1 or change scope")
    if "signal_validation" in source_file:
        return ("Keyboard Deep Dive — Signal Validation", "selected-feature partial Spearman", "post-selection robustness analysis", "includes recording/coverage adjustment in one scenario", "FDR within six selected signals or within adjustment scenario")
    if "t2_reliability_investigation" in source_file:
        return ("Keyboard Deep Dive — T2 Reliability", "selected-feature Spearman sensitivity", "post-selection coverage sensitivity", "predefined coverage gate", "FDR within six selected signals; not an independent screen")
    if "thirds_sensitivity_corrected_v2" in source_file:
        return ("Keyboard Deep Dive — Thirds Sensitivity", "coverage-adjusted partial Spearman", "corrected exploratory sensitivity", "canonical distinct-observation coverage adjustment", "FDR over 270 finite tests from 272 planned; no q<.05")
    if "thirds_sensitivity/third_associations" in source_file:
        return ("Keyboard Deep Dive — Thirds Sensitivity", "partial Spearman", "superseded historical sensitivity", "historical raw-row snapshot adjustment", "do not use for current inference; corrected canonical version exists")
    if "third_vs_midpoint_comparison" in source_file:
        return ("Keyboard Deep Dive — Window Comparison", "Spearman", "restricted same-patient sensitivity", "no coverage adjustment", "FDR within 40 tests per design; not an independent discovery")
    if "keyboard_two_feature" in source_file:
        return ("Keyboard Legacy Two-Feature", "Spearman", "limited preselected-feature exploratory analysis", "no saved coverage adjustment", "no q-value or CI saved")
    if "keyboard_t1_t2_delta" in source_file:
        return ("Keyboard Legacy Delta", "Spearman", "legacy duplicate summary", "no saved coverage adjustment", "no q-value or CI saved")
    if "supplemental_modalities" in source_file:
        return ("Supplemental Modalities — 24-hour T1", "Spearman/Pearson review", "exploratory feature review", "some rows are recording-volume measures", "no p-value, q-value or CI saved")
    return ("Unclassified", "saved direct association", "exploratory", "not reported", "testing context not reported")


def keyboard_family(feature: str) -> str:
    name = str(feature)
    if "correction" in name or "deletion" in name:
        return "keyboard_correction"
    if "inter_event" in name or "typing" in name or "word_completion" in name:
        return "keyboard_timing_dynamics"
    if "active" in name or "observation" in name or "session" in name or "burst" in name:
        return "keyboard_volume_sessions"
    return "keyboard"


def direct_feature_family(feature: str, source_file: str, supplemental_families: dict[str, str]) -> str:
    if source_file.endswith("phase4_supplemental_feature_review.csv"):
        return supplemental_families.get(feature, "supplemental modality / family not saved")
    if str(feature).startswith("keyboard_"):
        return keyboard_family(feature)
    return "feature family not saved in source output"


def phase11_rows() -> pd.DataFrame:
    data = pd.read_csv(PHASE11)
    result = pd.DataFrame({
        "source_file": str(PHASE11.relative_to(ROOT)),
        "source_csv_line": np.arange(2, len(data) + 2),
        "feature": data["feature_name"],
        "feature_family": data["feature_family"],
        "feature_modality": data["source_table"],
        "outcome": "global_T1_median_group",
        "outcome_timepoint": "T1",
        "estimate": pd.to_numeric(data["effect_size_cliffs_delta_higher_minus_lower"], errors="coerce"),
        "estimate_type": "Cliff's delta (higher Global T1 group minus lower group)",
        "n": pd.to_numeric(data["n_overall"], errors="coerce"),
        "p": pd.to_numeric(data["p_value"], errors="coerce"),
        "q": pd.to_numeric(data["q_value_fdr_bh"], errors="coerce"),
        "ci_low": np.nan,
        "ci_high": np.nan,
        "testing_context": "Phase 11 observed Global T1 median split; 61-feature Mann–Whitney screen; BH q within table",
        "status": "exploratory_group_contrast",
        "analysis_phase": "Phase 11 — Baseline severity table",
        "analysis_design": "Mann–Whitney feature contrast between observed Global-T1 median groups",
        "evidence_role": "exploratory group contrast; not a correlation",
        "coverage_adjustment": "not adjusted; missingness reported in source table",
        "fdr_scope": "BH q across the 61-feature table",
        "coefficient_field": "effect_size_cliffs_delta_higher_minus_lower",
    })
    return result


def base_rows() -> pd.DataFrame:
    data = pd.read_csv(BASE)
    supplemental = pd.read_csv(SUPPLEMENTAL)
    supplemental_families = supplemental.set_index("feature_name")["feature_group"].to_dict()
    mapped = data["source_file"].map(source_metadata)
    result = data.rename(columns={"context": "testing_context"}).copy()
    result["analysis_phase"] = mapped.map(lambda values: values[0])
    result["analysis_design"] = mapped.map(lambda values: values[1])
    result["evidence_role"] = mapped.map(lambda values: values[2])
    result["coverage_adjustment"] = mapped.map(lambda values: values[3])
    result["fdr_scope"] = mapped.map(lambda values: values[4])
    result["feature_family"] = [direct_feature_family(feature, source, supplemental_families) for feature, source in zip(result["feature"], result["source_file"])]
    result["feature_modality"] = result["feature_family"].str.split("_").str[0]
    result["outcome_timepoint"] = np.select(
        [result["testing_context"].str.contains("T2_minus_T1|midpoint change|first_last_third|first/last thirds|legacy keyboard midpoint change", case=False, na=False),
         result["testing_context"].str.contains("T1", case=False, na=False)],
        ["T2_minus_T1", "T1"], default="not explicitly saved",
    )
    return result


def candidate_rows(master: pd.DataFrame) -> pd.DataFrame:
    """Preserve a small, transparent POC shortlist; no score is calculated."""
    selectors = [
        ("Afternoon interval change → executive function", "signal_feature_associations.csv", "keyboard_12_18_median_inter_event_interval_ms", "executive_function", "T2_minus_T1; FDR within scope"),
        ("Correction recovery change → executive function", "signal_feature_associations.csv", "keyboard_median_correction_recovery_time_ms", "executive_function", "T2_minus_T1; FDR within scope"),
        ("IEI CV change → executive function", "signal_feature_associations.csv", "keyboard_inter_event_interval_cv", "executive_function", "T2_minus_T1; FDR within scope"),
        ("Evening interval change → executive function", "signal_feature_associations.csv", "keyboard_18_24_median_inter_event_interval_ms", "executive_function", "T2_minus_T1; FDR within scope"),
        ("Word-completion proxy → attention T1", "keyboard_two_feature_associations.csv", "keyboard_median_word_completion_time_ms", "attention_T1", "T1 midpoint"),
        ("Morning interval change → attention", "third_vs_midpoint_comparison_same_patients.csv", "keyboard_06_12_median_inter_event_interval_ms", "attention", "50_50_midpoint_same_patients"),
        ("IEI IQR → Global-T1 median group", "phase11_baseline_severity_all_features.csv", "keyboard_inter_event_interval_iqr_ms", "global_T1_median_group", "Phase 11 observed"),
    ]
    rows: list[pd.Series] = []
    for rank, (label, source_stub, feature, outcome, context_stub) in enumerate(selectors, start=1):
        matches = master.loc[
            master["source_file"].str.contains(source_stub, regex=False)
            & master["feature"].eq(feature)
            & master["outcome"].eq(outcome)
            & master["testing_context"].str.contains(context_stub, regex=False, na=False)
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one source row for {label}; found {len(matches)}")
        row = matches.iloc[0].copy()
        row["poc_rank"] = rank
        row["poc_candidate"] = label
        row["selection_basis"] = "Saved effect/statistics plus explicit robustness/limitation review; not an independent replication ranking."
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    base = base_rows()
    phase11 = phase11_rows()
    columns = [
        "source_file", "source_csv_line", "analysis_phase", "analysis_design", "evidence_role", "status",
        "feature", "feature_modality", "feature_family", "outcome", "outcome_timepoint", "estimate", "estimate_type", "n", "p", "q", "ci_low", "ci_high",
        "testing_context", "fdr_scope", "coverage_adjustment", "coefficient_field",
    ]
    master = pd.concat([base.reindex(columns=columns), phase11.reindex(columns=columns)], ignore_index=True)
    master["p_lt_0_05"] = master["p"].lt(0.05)
    master["q_lt_0_05"] = master["q"].lt(0.05)
    master["q_le_0_20"] = master["q"].le(0.20)
    master["is_superseded"] = master["status"].eq("superseded_by_canonical_snapshot_adjustment")
    master["association_key"] = master["feature"].astype(str) + " → " + master["outcome"].astype(str)
    source_count = master.groupby("association_key")["source_file"].transform("nunique")
    master["distinct_saved_source_versions_for_same_feature_outcome"] = source_count
    master["missing_statistics"] = [
        "; ".join(name for name, value in (("p", p), ("q", q), ("ci_low", low), ("ci_high", high)) if pd.isna(value)) or "none"
        for p, q, low, high in zip(master["p"], master["q"], master["ci_low"], master["ci_high"])
    ]
    master.insert(0, "master_row_id", range(1, len(master) + 1))
    master.to_csv(OUT, index=False)
    master.loc[master["p_lt_0_05"]].to_csv(TABLE_DIR / "master_associations_p_lt_0_05_20261020.csv", index=False)
    master.loc[master["q_lt_0_05"]].to_csv(TABLE_DIR / "master_associations_fdr_q_lt_0_05_20261020.csv", index=False)
    master.loc[master["q_le_0_20"]].to_csv(TABLE_DIR / "master_associations_fdr_q_le_0_20_20261020.csv", index=False)
    candidate_rows(master).to_csv(TABLE_DIR / "master_association_poc_candidates_20261020.csv", index=False)

    excluded = pd.DataFrame([
        {"output_class": "PCA/PC-score cognitive overlays", "reason_not_in_master": "Associates a derived component or outcome-ranked panel with cognition, not an individual observed digital feature.", "examples": "full_model_pca/**/correlations.csv; unsupervised cognitive_overlay_summary.csv"},
        {"output_class": "Model coefficients / feature importance", "reason_not_in_master": "Fitted model parameter, not a direct feature–outcome association; cannot be interpreted as a correlation.", "examples": "phase4*/model*/coefficients.csv; full_model_pca/**/ridge_fold_coefficients.csv"},
        {"output_class": "Technical or feature–feature associations", "reason_not_in_master": "No cognitive outcome.", "examples": "accelerometer_feature_technical_correlations.csv; validation_feature_correlations.csv"},
        {"output_class": "Reliability and coverage analyses", "reason_not_in_master": "Assesses measurement stability or recording intensity, not direct feature–cognition association.", "examples": "validation_reliability.csv; t2_reliability_thresholds.csv"},
    ])
    excluded.to_csv(TABLE_DIR / "master_association_excluded_output_classes_20261020.csv", index=False)
    summary = {
        "direct_association_rows": int(len(master)),
        "direct_association_sources": int(master["source_file"].nunique()),
        "p_lt_0_05_rows": int(master["p_lt_0_05"].sum()),
        "fdr_q_lt_0_05_rows": int(master["q_lt_0_05"].sum()),
        "fdr_q_le_0_20_rows": int(master["q_le_0_20"].sum()),
        "superseded_rows": int(master["is_superseded"].sum()),
        "rows_missing_p": int(master["p"].isna().sum()),
        "rows_missing_q": int(master["q"].isna().sum()),
        "rows_missing_any_ci_bound": int((master["ci_low"].isna() | master["ci_high"].isna()).sum()),
        "scope_note": "Rows are association estimates, not independent discoveries. FDR values are comparable only within each row's stated family.",
    }
    pd.DataFrame([summary]).to_csv(TABLE_DIR / "master_association_summary_20261020.csv", index=False)
    print(pd.Series(summary).to_string())


if __name__ == "__main__":
    main()
