from __future__ import annotations

from pathlib import Path
import pandas as pd


def normalize_subject_id_d(v) -> str:
    s = str(v).strip()
    return s.zfill(3) if s.isdigit() else s


def to_bool(v) -> bool:
    if pd.isna(v):
        return False
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y"}


def main() -> None:
    in_wide = Path("output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide.csv")
    in_use = Path("output/analysis_candidates/phase1_features/extracted/phase1_subject_usability_summary.csv")
    in_base = Path("output/analysis_candidates/phase1_features/descriptive_profiles/phase1_baseline_profile_summary.csv")
    in_ranks = Path("output/analysis_candidates/phase1_features/descriptive_profiles/phase1_baseline_feature_ranks.csv")
    in_change = Path("output/analysis_candidates/phase1_features/descriptive_profiles/phase1_change_profile_summary_024_077.csv")
    in_interp = Path("output/analysis_candidates/phase1_features/descriptive_profiles/phase1_subject_interpretation_summary.csv")
    in_interp_md = Path("output/analysis_candidates/phase1_features/descriptive_profiles/README_phase1_interpretation_summary.md")
    in_project = Path("README_CURRENT_PROJECT_STATUS_PHASE1.md")

    out_dir = Path("output/analysis_candidates/phase1_features/reviewer_pack")
    out_dir.mkdir(parents=True, exist_ok=True)

    wide = pd.read_csv(in_wide)
    use = pd.read_csv(in_use)
    base = pd.read_csv(in_base)
    ranks = pd.read_csv(in_ranks)
    change = pd.read_csv(in_change)
    interp = pd.read_csv(in_interp)
    _ = in_interp_md.read_text(encoding="utf-8")
    _ = in_project.read_text(encoding="utf-8")

    for d in [wide, use, base, ranks, change, interp]:
        if "Subject_ID_D" in d.columns:
            d["Subject_ID_D"] = d["Subject_ID_D"].map(normalize_subject_id_d)

    if "phase1_baseline_usable" in wide.columns:
        wide["phase1_baseline_usable"] = wide["phase1_baseline_usable"].map(to_bool)
    if "phase1_change_usable" in wide.columns:
        wide["phase1_change_usable"] = wide["phase1_change_usable"].map(to_bool)

    baseline_subjects = sorted(wide.loc[wide["phase1_baseline_usable"], "Subject_ID_D"].tolist())
    change_subjects = sorted(wide.loc[wide["phase1_change_usable"], "Subject_ID_D"].tolist())

    # Key numbers
    metrics = [
        ("cognitive_subjects_total", 83),
        ("top_decline_subjects", 10),
        ("device_episodes", 22),
        ("baseline_usable_subjects", int(len(baseline_subjects))),
        ("change_usable_subjects", int(len(change_subjects))),
        ("merged_phase1_rows", int(wide.shape[0])),
        ("merged_phase1_columns", int(wide.shape[1])),
        ("digital_feature_columns", 37),
        ("phase1a_qc_issues", 0),
        ("phase1b_qc_issues", 0),
        ("real_sql_coverage_errors", 0),
    ]
    key_numbers = pd.DataFrame(metrics, columns=["metric", "value"])

    # Subject overview for review: ensure global_decline_amount/global_delta available
    cog = wide[["Subject_ID_D", "global_delta", "global_decline_amount", "phase1_baseline_usable", "phase1_change_usable"]].copy()
    cog = cog.rename(columns={"phase1_baseline_usable": "baseline_usable", "phase1_change_usable": "change_usable"})

    interp_keep = [
        "Subject_ID_D",
        "main_digital_profile_pattern",
        "strongest_relative_features",
        "weakest_relative_features",
        "data_quality_note",
        "interpretation_caution",
    ]
    interp_keep = [c for c in interp_keep if c in interp.columns]
    subject_overview = cog.merge(interp[interp_keep], on="Subject_ID_D", how="left")
    subject_overview = subject_overview[[
        "Subject_ID_D",
        "global_delta",
        "global_decline_amount",
        "baseline_usable",
        "change_usable",
        "main_digital_profile_pattern",
        "strongest_relative_features",
        "weakest_relative_features",
        "data_quality_note",
        "interpretation_caution",
    ]].sort_values("Subject_ID_D")

    # Feature family summary
    feature_families = [
        {
            "feature_family": "screen",
            "source_table": "screen",
            "role": "core_phenotype",
            "number_of_features": 4,
            "baseline_available": "yes",
            "change_available": "limited",
            "interpretation_strength": "moderate",
            "key_limitations": "late-window missingness for most subjects",
        },
        {
            "feature_family": "applications_foreground",
            "source_table": "applications_foreground",
            "role": "core_phenotype",
            "number_of_features": 4,
            "baseline_available": "yes",
            "change_available": "limited",
            "interpretation_strength": "moderate",
            "key_limitations": "late-window missingness for most subjects",
        },
        {
            "feature_family": "keyboard",
            "source_table": "keyboard",
            "role": "core_phenotype",
            "number_of_features": 4,
            "baseline_available": "yes",
            "change_available": "very_limited",
            "interpretation_strength": "moderate",
            "key_limitations": "late-window sparse; privacy-restricted to non-text metrics",
        },
        {
            "feature_family": "touch",
            "source_table": "touch",
            "role": "core_phenotype",
            "number_of_features": 4,
            "baseline_available": "yes",
            "change_available": "no",
            "interpretation_strength": "moderate",
            "key_limitations": "no late touch coverage in current top10",
        },
        {
            "feature_family": "activity_recognition",
            "source_table": "plugin_google_activity_recognition",
            "role": "core_phenotype",
            "number_of_features": 10,
            "baseline_available": "yes",
            "change_available": "yes_for_024_077_only",
            "interpretation_strength": "moderate",
            "key_limitations": "activity label availability varies; change sample very small",
        },
        {
            "feature_family": "aware_log",
            "source_table": "aware_log",
            "role": "data_quality_only",
            "number_of_features": 4,
            "baseline_available": "yes",
            "change_available": "yes_for_024_077_only",
            "interpretation_strength": "supporting_only",
            "key_limitations": "not a behavioral endpoint",
        },
    ]
    family_df = pd.DataFrame(feature_families)

    # Executive summary markdown
    exec_md = out_dir / "phase1_reviewer_executive_summary.md"
    exec_md.write_text(
        "\n".join([
            "# Phase 1 Reviewer Executive Summary",
            "",
            "## Project purpose",
            "Link NeuroTrax cognitive decline metrics with SensorDB digital phenotype signals in a constrained exploratory PoC.",
            "",
            "## What was built",
            "- Cognitive master and QC pipeline.",
            "- Top10 decline subject selection and time-window alignment.",
            "- Device-episode mapping (multiple device IDs per subject).",
            "- SQL coverage and readiness mapping.",
            "- Phase 1A extraction: screen + applications_foreground + aware_log.",
            "- Phase 1B extraction: keyboard + touch + activity recognition.",
            "- Merged Phase 1 digital phenotype table and descriptive interpretation outputs.",
            "",
            "## What data was used",
            "- Validated merged Phase 1 table and descriptive profile outputs only.",
            "- No new SQL queries and no new extraction in this reviewer package step.",
            "",
            "## What Phase 1 includes",
            "- screen",
            "- applications_foreground",
            "- keyboard",
            "- touch",
            "- activity_recognition",
            "- aware_log (data quality only)",
            "",
            "## Main current results",
            f"- Baseline phenotype feasibility: {len(baseline_subjects)}/10 subjects.",
            f"- Change analysis feasibility: {len(change_subjects)}/10 subjects ({', '.join(change_subjects)}).",
            "- Merged Phase 1 table: 10 rows × 56 columns.",
            "",
            "## Key methodological safeguards",
            "- Missing data is not zero activity.",
            "- no_data remains NaN.",
            "- Privacy-sensitive keyboard text was not used.",
            "- Subject_ID_D leading zeros preserved.",
            "- No confirmatory statistics.",
            "",
            "## Recommended next step",
            "Continue interpreting current Phase 1 core phenotype before Phase 1C.",
        ]),
        encoding="utf-8",
    )

    # Next-steps recommendation markdown
    next_md = out_dir / "phase1_next_steps_recommendation.md"
    next_md.write_text(
        "\n".join([
            "# Phase 1 Next Steps Recommendation",
            "",
            "## Option A (Recommended now)",
            "Continue interpreting the current Phase 1 core phenotype outputs.",
            "",
            "Rationale:",
            "- Current outputs already support a useful baseline phenotype story (8/10 subjects).",
            "- Existing change signals for 024 and 077 are ready for cautious exploratory discussion.",
            "- Interpretation can be stabilized before adding more dimensions.",
            "",
            "## Option B (After review)",
            "Proceed to Phase 1C optional/context extraction:",
            "- gsm",
            "- gsm_neighbor",
            "- telephony",
            "- messages",
            "",
            "Rationale:",
            "- May add context/social/environmental proxies.",
            "- Increases complexity and potential interpretation drift if added too early.",
            "",
            "## Recommendation",
            "Choose Option A first, then move to Option B only after supervisor/reviewer confirms current core phenotype outputs are useful and interpretable.",
        ]),
        encoding="utf-8",
    )

    # Save CSV outputs
    key_numbers_path = out_dir / "phase1_key_numbers.csv"
    subject_overview_path = out_dir / "phase1_subject_overview_for_review.csv"
    family_path = out_dir / "phase1_feature_family_summary.csv"

    key_numbers.to_csv(key_numbers_path, index=False)
    subject_overview.to_csv(subject_overview_path, index=False)
    family_df.to_csv(family_path, index=False)

    # Prints
    print(f"output_folder={out_dir}")
    print("key_metrics:")
    print(key_numbers.to_string(index=False))
    print(f"baseline_usable_subjects={baseline_subjects}")
    print(f"change_usable_subjects={change_subjects}")
    print("recommended_next_action=Option A: continue interpreting current Phase 1 core phenotype before Phase 1C")
    print("generated_files:")
    print(f"- {exec_md}")
    print(f"- {key_numbers_path}")
    print(f"- {subject_overview_path}")
    print(f"- {family_path}")
    print(f"- {next_md}")


if __name__ == "__main__":
    main()
