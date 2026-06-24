from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def normalize_subject_id_d(v) -> str:
    s = str(v).strip()
    return s.zfill(3) if s.isdigit() else s


def to_bool(v) -> bool:
    if pd.isna(v):
        return False
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y"}


def add_rank_pct_cat(df: pd.DataFrame, col: str) -> pd.DataFrame:
    s = pd.to_numeric(df[col], errors="coerce")
    rank_col = f"{col}__rank_desc"
    pct_col = f"{col}__percentile"
    cat_col = f"{col}__category"

    valid = s.notna()
    out = pd.DataFrame(index=df.index)
    out[rank_col] = np.nan
    out[pct_col] = np.nan
    out[cat_col] = None

    if valid.sum() == 0:
        return out

    ranks = s[valid].rank(ascending=False, method="min")
    pct = s[valid].rank(pct=True, method="average") * 100

    cats = pd.Series(index=s[valid].index, dtype="object")
    # descriptive tertiles (relative only)
    cats[pct >= 66.6667] = "high"
    cats[(pct >= 33.3333) & (pct < 66.6667)] = "medium"
    cats[pct < 33.3333] = "low"

    out.loc[valid, rank_col] = ranks
    out.loc[valid, pct_col] = pct
    out.loc[valid, cat_col] = cats
    return out


def highlight_line(row: pd.Series) -> str:
    h = []
    if row.get("screen_early_event_count__category") == "high":
        h.append("relatively high screen interaction")
    elif row.get("screen_early_event_count__category") == "low":
        h.append("relatively low screen interaction")

    if row.get("app_early_foreground_event_count__category") == "high":
        h.append("relatively high foreground app activity")

    if row.get("keyboard_early_event_count__category") == "high":
        h.append("high keyboard interaction")
    if row.get("touch_early_event_count__category") == "high":
        h.append("high touch interaction")
    if row.get("activity_early_event_count__category") == "high":
        h.append("high activity-recognition event density")

    if pd.notna(row.get("aware_log_early_rows")) and row.get("aware_log_early_rows", 0) > 0:
        h.append("aware_log supports data availability")

    if not h:
        h.append("limited digital signal in available early-window tables")
    return "; ".join(h)


def main() -> None:
    in_wide = Path("output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide.csv")
    in_use = Path("output/analysis_candidates/phase1_features/extracted/phase1_subject_usability_summary.csv")
    in_top10 = Path("output/analysis_candidates/top10_global_decline.csv")
    in_readme = Path("output/analysis_candidates/phase1_features/extracted/README_phase1_digital_phenotype.md")

    out_dir = Path("output/analysis_candidates/phase1_features/descriptive_profiles")
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(in_wide)
    use = pd.read_csv(in_use)
    top10 = pd.read_csv(in_top10)
    _ = in_readme.read_text(encoding="utf-8")

    for d in [df, use, top10]:
        d["Subject_ID_D"] = d["Subject_ID_D"].map(normalize_subject_id_d)
        if "Subject_ID_N" in d.columns:
            d["Subject_ID_N"] = d["Subject_ID_N"].astype(str).str.strip()

    for c in ["phase1_baseline_usable", "phase1_change_usable"]:
        if c in df.columns:
            df[c] = df[c].map(to_bool)

    baseline_df = df[df["phase1_baseline_usable"]].copy()
    change_df = df[df["phase1_change_usable"]].copy()
    insufficient_df = df[~df["phase1_baseline_usable"] & ~df["phase1_change_usable"]].copy()

    suggested_early_features = [
        "screen_early_event_count",
        "screen_early_night_event_count",
        "app_early_foreground_event_count",
        "app_early_unique_foreground_apps",
        "app_early_app_use_diversity",
        "keyboard_early_event_count",
        "touch_early_event_count",
        "activity_early_event_count",
        "still_early_event_count",
        "walking_early_event_count",
        "in_vehicle_early_event_count",
        "aware_log_early_rows",
    ]

    # map aliases to existing columns
    alias_map = {
        "still_early_event_count": "activity_early_still_event_count",
        "walking_early_event_count": "activity_early_walking_event_count",
        "in_vehicle_early_event_count": "activity_early_in_vehicle_event_count",
    }

    existing_features = []
    missing_suggested = []
    for f in suggested_early_features:
        actual = alias_map.get(f, f)
        if actual in baseline_df.columns:
            existing_features.append(actual)
        else:
            missing_suggested.append(f)

    # baseline summary table
    base_cols = [
        "Subject_ID_N", "Subject_ID_D", "global_T1", "global_T2", "global_delta", "global_decline_amount",
        "phase1_baseline_usable", "phase1_change_usable", "data_availability_note",
    ] + existing_features
    baseline_summary = baseline_df[base_cols].copy()

    # baseline feature ranks
    rank_df = baseline_df[["Subject_ID_N", "Subject_ID_D"] + existing_features].copy()
    for col in existing_features:
        rank_parts = add_rank_pct_cat(baseline_df, col)
        rank_df = pd.concat([rank_df, rank_parts], axis=1)

    # profile cards
    cards = []
    cards.append("# Phase 1 Subject Profile Cards\n")
    cards.append("Exploratory descriptive summaries only. Not diagnostic and not confirmatory.\n")

    card_df = baseline_df.merge(
        rank_df[["Subject_ID_D"] + [c for c in rank_df.columns if c.endswith("__category")]],
        on="Subject_ID_D", how="left"
    )

    for _, r in card_df.sort_values("Subject_ID_D").iterrows():
        sid = r["Subject_ID_D"]
        cards.append(f"## Subject {sid}")
        cards.append(f"- global_delta: {r.get('global_delta')}")
        cards.append(f"- global_decline_amount: {r.get('global_decline_amount')}")
        cards.append(f"- phase1_baseline_usable: {bool(r.get('phase1_baseline_usable'))}")
        cards.append(f"- phase1_change_usable: {bool(r.get('phase1_change_usable'))}")
        cards.append(f"- early phenotype highlights: {highlight_line(r)}")
        cards.append(f"- data availability note: {r.get('data_availability_note')}")
        cards.append("- cautious interpretation: descriptive digital behavior profile only; missing windows limit interpretation and cannot be treated as inactivity.")
        cards.append("")

    # Add minimal cards for insufficient subjects
    for _, r in insufficient_df.sort_values("Subject_ID_D").iterrows():
        sid = r["Subject_ID_D"]
        cards.append(f"## Subject {sid}")
        cards.append("- phase1_baseline_usable: False")
        cards.append("- phase1_change_usable: False")
        cards.append(f"- data availability note: {r.get('data_availability_note')}")
        cards.append("- cautious interpretation: insufficient Phase 1 data for digital phenotype profiling.")
        cards.append("")

    # change summary only 024 and 077
    target = {"024", "077"}
    change_cols = [
        "Subject_ID_N", "Subject_ID_D", "global_delta", "global_decline_amount",
        "screen_early_event_count", "screen_late_event_count", "screen_delta_event_count", "screen_delta_status",
        "app_early_foreground_event_count", "app_late_foreground_event_count", "app_delta_foreground_event_count", "app_delta_status",
        "keyboard_early_event_count", "keyboard_late_event_count", "keyboard_delta_event_count", "keyboard_delta_status",
        "touch_early_event_count", "touch_late_event_count", "touch_delta_event_count", "touch_delta_status",
        "activity_early_event_count", "activity_late_event_count", "activity_delta_event_count", "activity_delta_status",
        "aware_log_early_rows", "aware_log_late_rows", "aware_log_delta_rows", "aware_log_delta_status",
        "data_availability_note",
    ]
    change_cols = [c for c in change_cols if c in df.columns]
    change_summary = df[df["Subject_ID_D"].isin(target)][change_cols].copy()

    # interpretation helpers for change rows
    def interp_change(row: pd.Series) -> str:
        parts = []
        for fam, status_col in [
            ("screen", "screen_delta_status"),
            ("app", "app_delta_status"),
            ("keyboard", "keyboard_delta_status"),
            ("touch", "touch_delta_status"),
            ("activity", "activity_delta_status"),
        ]:
            if status_col not in row.index:
                continue
            st = row.get(status_col)
            if pd.isna(st):
                continue
            if str(st) == "ok_both_windows":
                parts.append(f"{fam}: interpretable early-late change")
            else:
                parts.append(f"{fam}: change not interpretable ({st})")
        if "aware_log_delta_status" in row.index:
            parts.append(f"aware_log (data quality): {row.get('aware_log_delta_status')}")
        return "; ".join(parts)

    if not change_summary.empty:
        change_summary["change_interpretation"] = change_summary.apply(interp_change, axis=1)

    # variability ranking across baseline usable subjects
    var_rows = []
    for c in existing_features:
        s = pd.to_numeric(baseline_df[c], errors="coerce")
        var_rows.append({
            "feature": c,
            "n_non_missing": int(s.notna().sum()),
            "std": float(s.std()) if s.notna().sum() > 1 else np.nan,
            "iqr": float(s.quantile(0.75) - s.quantile(0.25)) if s.notna().sum() > 0 else np.nan,
        })
    variability_df = pd.DataFrame(var_rows).sort_values(["std", "iqr"], ascending=False)

    # Save outputs
    p_baseline_summary = out_dir / "phase1_baseline_profile_summary.csv"
    p_ranks = out_dir / "phase1_baseline_feature_ranks.csv"
    p_change = out_dir / "phase1_change_profile_summary_024_077.csv"
    p_cards = out_dir / "phase1_subject_profile_cards.md"
    p_readme = out_dir / "README_phase1_descriptive_profiles.md"

    baseline_summary.to_csv(p_baseline_summary, index=False)
    rank_df.to_csv(p_ranks, index=False)
    change_summary.to_csv(p_change, index=False)
    p_cards.write_text("\n".join(cards), encoding="utf-8")

    exec_summary = [
        "# Phase 1 Descriptive Profiles",
        "",
        "## Executive summary",
        "- Descriptive profiling only from validated merged Phase 1 table.",
        "- No SQL queried; no new feature extraction.",
        f"- Baseline-usable subjects: {baseline_df['Subject_ID_D'].nunique()}",
        f"- Change-usable subjects: {change_df['Subject_ID_D'].nunique()}",
        "- Change interpretation is limited to subjects 024 and 077 and remains exploratory.",
        "",
        "## Data used",
        "- phase1_digital_phenotype_wide.csv",
        "- phase1_subject_usability_summary.csv",
        "- top10_global_decline.csv",
        "- README_phase1_digital_phenotype.md",
        "",
        "## Feature families included",
        "- screen",
        "- applications_foreground",
        "- keyboard",
        "- touch",
        "- plugin_google_activity_recognition",
        "- aware_log (data quality only)",
        "",
        "## Main descriptive patterns",
        "- Baseline profile available for 8/10 subjects.",
        "- Early-vs-late change interpretable only for a small subset (024, 077).",
        "- Several features have missing late windows; those deltas remain missing by design.",
        "",
        "## Subject-level summary",
        f"- baseline subjects: {sorted(baseline_df['Subject_ID_D'].tolist())}",
        f"- change subjects: {sorted(change_df['Subject_ID_D'].tolist())}",
        f"- insufficient phase1 data: {sorted(insufficient_df['Subject_ID_D'].tolist())}",
        "",
        "## Early-vs-late summary for 024 and 077",
        "- Included in phase1_change_profile_summary_024_077.csv with per-feature interpretability notes.",
        "",
        "## Suggested columns missing from current merged table",
    ]
    if missing_suggested:
        exec_summary += [f"- {m}" for m in missing_suggested]
    else:
        exec_summary.append("- none")

    exec_summary += [
        "",
        "## Limitations",
        "- n=10 only",
        "- baseline usable n=8",
        "- change usable n=2",
        "- exploratory only",
        "- missing data is not zero activity",
        "- no confirmatory statistics",
        "- aware_log is data quality only",
        "- phase 1 does not include GPS/high-frequency motion/context-social tables yet",
    ]

    p_readme.write_text("\n".join(exec_summary), encoding="utf-8")

    # requested prints
    print(f"input_table_shape={df.shape}")
    print(f"baseline_usable_subjects={sorted(baseline_df['Subject_ID_D'].tolist())}")
    print(f"change_usable_subjects={sorted(change_df['Subject_ID_D'].tolist())}")
    print(f"number_of_feature_columns_used={len(existing_features)}")
    print("top_descriptive_baseline_features_by_variability:")
    print(variability_df.head(10).to_string(index=False))
    print("short_baseline_summary_table:")
    short_cols = [c for c in ["Subject_ID_D", "global_delta", "global_decline_amount", "screen_early_event_count", "app_early_foreground_event_count", "keyboard_early_event_count", "touch_early_event_count", "activity_early_event_count", "aware_log_early_rows"] if c in baseline_summary.columns]
    print(baseline_summary[short_cols].head(10).to_string(index=False))

    print("generated_files:")
    for p in [p_baseline_summary, p_ranks, p_change, p_cards, p_readme]:
        print(f"- {p}")


if __name__ == "__main__":
    main()
