from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np


def normalize_subject_id_d(v) -> str:
    s = str(v).strip()
    return s.zfill(3) if s.isdigit() else s


def to_bool(v) -> bool:
    if pd.isna(v):
        return False
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y"}


def main() -> None:
    base_dir = Path("output/analysis_candidates/phase1_features/descriptive_profiles")
    in_wide = Path("output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide.csv")
    in_base_summary = base_dir / "phase1_baseline_profile_summary.csv"
    in_ranks = base_dir / "phase1_baseline_feature_ranks.csv"
    in_change = base_dir / "phase1_change_profile_summary_024_077.csv"
    in_cards = base_dir / "phase1_subject_profile_cards.md"
    in_desc_readme = base_dir / "README_phase1_descriptive_profiles.md"

    wide = pd.read_csv(in_wide)
    base = pd.read_csv(in_base_summary)
    ranks = pd.read_csv(in_ranks)
    change = pd.read_csv(in_change)
    cards_text = in_cards.read_text(encoding="utf-8")
    desc_readme_text = in_desc_readme.read_text(encoding="utf-8")

    for df in [wide, base, ranks, change]:
        if "Subject_ID_D" in df.columns:
            df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id_d)

    if "phase1_baseline_usable" in wide.columns:
        wide["phase1_baseline_usable"] = wide["phase1_baseline_usable"].map(to_bool)
    if "phase1_change_usable" in wide.columns:
        wide["phase1_change_usable"] = wide["phase1_change_usable"].map(to_bool)

    n_top = wide["Subject_ID_D"].nunique()
    baseline_subjects = sorted(wide.loc[wide["phase1_baseline_usable"], "Subject_ID_D"].tolist())
    change_subjects = sorted(wide.loc[wide["phase1_change_usable"], "Subject_ID_D"].tolist())

    # Detect available early features used in baseline profile
    excluded = {
        "Subject_ID_N", "Subject_ID_D", "global_T1", "global_T2", "global_delta", "global_decline_amount",
        "phase1_baseline_usable", "phase1_change_usable", "data_availability_note",
    }
    early_features = [c for c in base.columns if c not in excluded and c.endswith("_early_event_count") or c == "aware_log_early_rows" or c.startswith("activity_early_")]
    # dedupe preserving order
    seen = set(); early_features = [x for x in early_features if not (x in seen or seen.add(x))]

    # variability from ranks table if present, otherwise compute from baseline summary
    rank_cat_cols = [c for c in ranks.columns if c.endswith("__category")]
    root_features = [c.replace("__category", "") for c in rank_cat_cols]
    variability_rows = []
    for f in root_features:
        if f not in base.columns:
            continue
        s = pd.to_numeric(base[f], errors="coerce")
        variability_rows.append({
            "feature": f,
            "std": float(s.std()) if s.notna().sum() > 1 else np.nan,
            "iqr": float(s.quantile(0.75) - s.quantile(0.25)) if s.notna().sum() > 0 else np.nan,
            "n_non_missing": int(s.notna().sum()),
        })
    variability_df = pd.DataFrame(variability_rows).sort_values(["std", "iqr"], ascending=False)

    # subject-level interpretation table
    subjects = sorted(wide["Subject_ID_D"].tolist())
    interp_rows = []
    for sid in subjects:
        w = wide[wide["Subject_ID_D"] == sid].iloc[0]
        b = base[base["Subject_ID_D"] == sid]
        r = ranks[ranks["Subject_ID_D"] == sid]

        strongest = []
        weakest = []
        if not r.empty:
            rr = r.iloc[0]
            for c in rank_cat_cols:
                cat = rr.get(c)
                feat = c.replace("__category", "")
                if pd.isna(cat):
                    continue
                if str(cat) == "high":
                    strongest.append(feat)
                elif str(cat) == "low":
                    weakest.append(feat)

        if strongest:
            profile_pattern = "relatively higher interaction on selected early digital features"
        elif weakest:
            profile_pattern = "relatively lower interaction on selected early digital features"
        else:
            profile_pattern = "limited interpretable baseline digital signal"

        data_note = str(w.get("data_availability_note", ""))
        caution = "exploratory descriptive interpretation only; missing windows are not inactivity"

        interp_rows.append({
            "Subject_ID_D": sid,
            "global_delta": w.get("global_delta"),
            "baseline_usable": bool(w.get("phase1_baseline_usable")),
            "change_usable": bool(w.get("phase1_change_usable")),
            "main_digital_profile_pattern": profile_pattern,
            "strongest_relative_features": "; ".join(strongest) if strongest else "",
            "weakest_relative_features": "; ".join(weakest) if weakest else "",
            "data_quality_note": data_note,
            "interpretation_caution": caution,
        })

    interp_df = pd.DataFrame(interp_rows)
    interp_csv = base_dir / "phase1_subject_interpretation_summary.csv"
    interp_df.to_csv(interp_csv, index=False)

    # Build project-level interpretation README
    top5 = variability_df.head(5)["feature"].tolist() if not variability_df.empty else []

    rec_next = (
        "Option A is recommended now: continue interpreting current Phase 1 core phenotype outputs first. "
        "Option B (Phase 1C: gsm/gsm_neighbor/telephony/messages) should proceed only after confirming current summaries are useful and interpretable."
    )

    readme_out = base_dir / "README_phase1_interpretation_summary.md"
    lines = [
        "# Phase 1 Interpretation Summary",
        "",
        "## Executive summary",
        f"- Top-decline subjects analyzed: {n_top}",
        f"- Baseline-usable subjects: {len(baseline_subjects)} ({', '.join(baseline_subjects)})",
        f"- Change-usable subjects: {len(change_subjects)} ({', '.join(change_subjects)})",
        "- Phase 1 supports descriptive baseline profiling for most subjects, and limited early-vs-late change review for 024 and 077.",
        "",
        "## What Phase 1 currently supports",
        "- Descriptive baseline digital phenotype across core feature families.",
        "- Relative ranking (low/medium/high) within baseline-usable subjects.",
        "- Exploratory change summaries for subjects with both windows.",
        "",
        "## What Phase 1 does not support yet",
        "- Confirmatory inference, hypothesis testing, or causal claims.",
        "- Robust change modeling beyond the 2 subjects with both windows.",
        "- Context/social augmentation from optional tables (Phase 1C not yet integrated).",
        "",
        "## Main descriptive findings",
        f"- Highest variability features (descriptive): {', '.join(top5) if top5 else 'n/a'}.",
        "- Baseline interaction patterns are heterogeneous across subjects.",
        "- Late-window missingness substantially limits change interpretation for most subjects.",
        "",
        "## Baseline phenotype summary (8 subjects)",
        f"- Subjects: {', '.join(baseline_subjects)}",
        "- Core families used: screen, applications_foreground, keyboard, touch, activity_recognition.",
        "- aware_log included only as data-quality support.",
        "",
        "## Change summary (024 and 077)",
        "- Change interpretation is possible only for available deltas with both windows.",
        "- Missing deltas indicate non-interpretable feature change, not true zero change.",
        "",
        "## Data quality and missingness interpretation",
        "- Missing data is not zero activity.",
        "- no_data windows remain NaN by design.",
        "- aware_log rows help assess logging availability but are not behavior endpoints.",
        "",
        "## Why no confirmatory statistics",
        "- Sample size is small (n=10; baseline n=8; change n=2).",
        "- Coverage heterogeneity and missingness preclude stable inferential conclusions.",
        "- This phase is exploratory profiling only.",
        "",
        "## Recommended next step",
        "### Option A",
        "Continue interpretation of the current Phase 1 core phenotype outputs and validate utility with domain stakeholders.",
        "",
        "### Option B",
        "Proceed to Phase 1C optional/context extraction: gsm, gsm_neighbor, telephony, messages.",
        "",
        "### Recommendation",
        rec_next,
    ]
    readme_out.write_text("\n".join(lines), encoding="utf-8")

    # Console output
    print("executive_summary:")
    print(f"- top_decline_subjects_analyzed={n_top}")
    print(f"- baseline_usable={len(baseline_subjects)} -> {baseline_subjects}")
    print(f"- change_usable={len(change_subjects)} -> {change_subjects}")
    print("top_5_most_variable_features:")
    if variability_df.empty:
        print("- none")
    else:
        print(variability_df.head(5).to_string(index=False))
    print(f"recommended_next_action={rec_next}")

    print("generated_files:")
    print(f"- {interp_csv}")
    print(f"- {readme_out}")


if __name__ == "__main__":
    main()
