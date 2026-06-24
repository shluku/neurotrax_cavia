from __future__ import annotations

from pathlib import Path
import pandas as pd


def normalize_subject_id_d(v) -> str:
    s = str(v).strip()
    return s.zfill(3) if s.isdigit() else s


def to_bool(v) -> bool:
    if pd.isna(v):
        return False
    s = str(v).strip().lower()
    return s in {"1", "true", "t", "yes", "y"}


def main() -> None:
    out_dir = Path("output/analysis_candidates/phase1_features/extracted")
    out_dir.mkdir(parents=True, exist_ok=True)

    p1a_wide = pd.read_csv(out_dir / "phase1a_subject_features_wide.csv")
    p1b_wide = pd.read_csv(out_dir / "phase1b_subject_features_wide.csv")
    p1a_use = pd.read_csv(out_dir / "qc_phase1a_subject_usability.csv")
    p1b_use = pd.read_csv(out_dir / "qc_phase1b_subject_usability.csv")
    top10 = pd.read_csv("output/analysis_candidates/top10_global_decline.csv")
    readiness = pd.read_csv("output/analysis_candidates/sql_coverage/top10_subject_readiness.csv")

    # Preserve zero-padded Subject_ID_D everywhere
    for df in [p1a_wide, p1b_wide, p1a_use, p1b_use, top10, readiness]:
        if "Subject_ID_D" in df.columns:
            df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id_d)

    # Normalize Subject_ID_N key type
    for df in [p1a_wide, p1b_wide, top10, readiness]:
        if "Subject_ID_N" in df.columns:
            df["Subject_ID_N"] = df["Subject_ID_N"].astype(str).str.strip()

    # Usability harmonization
    p1a_use = p1a_use.rename(columns={
        "usable_phase1a_baseline": "phase1a_baseline_usable",
        "usable_phase1a_change": "phase1a_change_usable",
    })

    for col in ["phase1a_baseline_usable", "phase1a_change_usable"]:
        if col in p1a_use.columns:
            p1a_use[col] = p1a_use[col].map(to_bool)
        else:
            p1a_use[col] = False

    for col in ["phase1b_baseline_usable", "phase1b_change_usable"]:
        if col in p1b_use.columns:
            p1b_use[col] = p1b_use[col].map(to_bool)
        else:
            p1b_use[col] = False

    # Merge Phase 1A + 1B features
    merged = p1a_wide.merge(
        p1b_wide,
        on=["Subject_ID_N", "Subject_ID_D"],
        how="outer",
        validate="one_to_one",
    )

    # Add cognitive columns
    cog_cols = [
        "Subject_ID_N", "Subject_ID_D",
        "global_T1", "global_T2", "global_delta", "global_decline_amount",
        "T1_date_iso", "T2_date_iso",
    ]
    merged = merged.merge(top10[cog_cols], on=["Subject_ID_N", "Subject_ID_D"], how="left")

    # Add usability columns
    merged = merged.merge(
        p1a_use[["Subject_ID_D", "phase1a_baseline_usable", "phase1a_change_usable"]],
        on="Subject_ID_D",
        how="left",
    )
    merged = merged.merge(
        p1b_use[["Subject_ID_D", "phase1b_baseline_usable", "phase1b_change_usable"]],
        on="Subject_ID_D",
        how="left",
    )

    for c in ["phase1a_baseline_usable", "phase1a_change_usable", "phase1b_baseline_usable", "phase1b_change_usable"]:
        merged[c] = merged[c].map(to_bool)

    merged["phase1_baseline_usable"] = merged["phase1a_baseline_usable"] | merged["phase1b_baseline_usable"]
    merged["phase1_change_usable"] = merged["phase1a_change_usable"] | merged["phase1b_change_usable"]

    # Interpretation columns
    merged["baseline_profile_available"] = merged["phase1_baseline_usable"]
    merged["change_profile_available"] = merged["phase1_change_usable"]

    def scope(row):
        b = bool(row["phase1_baseline_usable"])
        c = bool(row["phase1_change_usable"])
        if b and c:
            return "baseline_and_change_available"
        if b and not c:
            return "baseline_only"
        if (not b) and c:
            return "change_only_unusual"
        return "insufficient_phase1_data"

    def note(row):
        if row["phase1_change_usable"]:
            return "change analysis exploratory and limited; do not use as confirmatory evidence"
        if row["phase1_baseline_usable"]:
            return "baseline phenotype available; missing late windows limit change analysis"
        return "insufficient early/late digital coverage in Phase 1 tables"

    merged["interpretation_scope"] = merged.apply(scope, axis=1)
    merged["data_availability_note"] = merged.apply(note, axis=1)

    # Optional add readiness context
    merged = merged.merge(
        readiness[["Subject_ID_N", "Subject_ID_D", "early_late_coverage_group"]],
        on=["Subject_ID_N", "Subject_ID_D"],
        how="left",
    )

    # Subject usability summary
    use_cols = [
        "Subject_ID_N", "Subject_ID_D", "global_delta", "global_decline_amount",
        "phase1a_baseline_usable", "phase1a_change_usable",
        "phase1b_baseline_usable", "phase1b_change_usable",
        "phase1_baseline_usable", "phase1_change_usable",
        "baseline_profile_available", "change_profile_available",
        "interpretation_scope", "data_availability_note", "early_late_coverage_group",
    ]
    subject_usability = merged[use_cols].copy()

    # Save outputs
    wide_out = out_dir / "phase1_digital_phenotype_wide.csv"
    use_out = out_dir / "phase1_subject_usability_summary.csv"
    readme_out = out_dir / "README_phase1_digital_phenotype.md"

    merged.to_csv(wide_out, index=False)
    subject_usability.to_csv(use_out, index=False)

    baseline_subjects = merged.loc[merged["phase1_baseline_usable"], "Subject_ID_D"].tolist()
    change_subjects = merged.loc[merged["phase1_change_usable"], "Subject_ID_D"].tolist()

    readme_out.write_text(
        """# Phase 1 Digital Phenotype (Merged)

This is the first merged Phase 1 digital phenotype table.

Scope:
- Combines only Phase 1A + Phase 1B validated outputs.
- No new SQL was queried.
- No missing data was converted to zero.
- aware_log is treated as data-quality only (not direct behavior).

Readiness:
- Baseline phenotype available for 8/10 subjects.
- Change analysis available only for 024 and 077, and is exploratory.
- This table is for descriptive profiling, not confirmatory statistics.
""",
        encoding="utf-8",
    )

    # Console summary
    feature_cols = [c for c in merged.columns if c not in {
        "Subject_ID_N", "Subject_ID_D", "global_T1", "global_T2", "global_delta", "global_decline_amount",
        "T1_date_iso", "T2_date_iso", "phase1a_baseline_usable", "phase1a_change_usable",
        "phase1b_baseline_usable", "phase1b_change_usable", "phase1_baseline_usable", "phase1_change_usable",
        "baseline_profile_available", "change_profile_available", "interpretation_scope", "data_availability_note",
        "early_late_coverage_group",
    }]

    print(f"final_merged_shape={merged.shape}")
    print(f"baseline_usable_subjects={baseline_subjects}")
    print(f"change_usable_subjects={change_subjects}")
    print(f"number_of_feature_columns={len(feature_cols)}")
    print("main_feature_families_included=['screen','applications_foreground','aware_log(data_quality)','keyboard','touch','activity_recognition']")

    key_cols = [
        "Subject_ID_D",
        "global_delta",
        "phase1_baseline_usable",
        "phase1_change_usable",
        "screen_early_event_count",
        "app_early_foreground_event_count",
        "keyboard_early_event_count",
        "touch_early_event_count",
        "activity_early_event_count",
        "aware_log_early_rows",
    ]
    key_cols = [c for c in key_cols if c in merged.columns]
    print("top_10_rows_key_columns:")
    print(merged[key_cols].head(10).to_string(index=False))

    print("generated_files:")
    print(f"- {wide_out}")
    print(f"- {use_out}")
    print(f"- {readme_out}")


if __name__ == "__main__":
    main()
