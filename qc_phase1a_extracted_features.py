import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def to_num(s):
    return pd.to_numeric(s, errors="coerce")


def feature_stats(df, col):
    x = to_num(df[col])
    return {
        "feature": col,
        "non_missing": int(x.notna().sum()),
        "min": x.min(skipna=True),
        "median": x.median(skipna=True),
        "mean": x.mean(skipna=True),
        "max": x.max(skipna=True),
        "zeros": int((x == 0).sum(skipna=True)),
        "negative_values": int((x < 0).sum(skipna=True)),
    }


def main():
    ap = argparse.ArgumentParser(description="QC for Phase 1A extracted features (no SQL).")
    ap.add_argument("--device", default="output/analysis_candidates/phase1_features/extracted/phase1a_device_window_features.csv")
    ap.add_argument("--subject_window", default="output/analysis_candidates/phase1_features/extracted/phase1a_subject_window_features.csv")
    ap.add_argument("--wide", default="output/analysis_candidates/phase1_features/extracted/phase1a_subject_features_wide.csv")
    ap.add_argument("--subject_readiness", default="output/analysis_candidates/sql_coverage/top10_subject_readiness.csv")
    ap.add_argument("--coverage_matrix", default="output/analysis_candidates/sql_coverage/top10_subject_table_coverage_matrix.csv")
    ap.add_argument("--top10", default="output/analysis_candidates/top10_global_decline.csv")
    ap.add_argument("--out_dir", default="output/analysis_candidates/phase1_features/extracted")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dev = pd.read_csv(args.device, dtype=str)
    sw = pd.read_csv(args.subject_window, dtype=str)
    wide = pd.read_csv(args.wide, dtype=str)
    sr = pd.read_csv(args.subject_readiness, dtype=str)
    cm = pd.read_csv(args.coverage_matrix, dtype=str)
    top10 = pd.read_csv(args.top10, dtype=str)

    issues = []

    # 1) row-count validations
    device_counts = dev.groupby(["table_name", "window_name", "extraction_status"], dropna=False).size().reset_index(name="n_rows")
    subject_counts = sw.groupby(["table_name", "window_name", "extraction_status"], dropna=False).size().reset_index(name="n_rows")

    if wide["Subject_ID_D"].nunique() != len(wide):
        issues.append({"issue_type": "duplicate_subject_in_wide", "detail": "wide table does not have unique Subject_ID_D"})

    # 2) delta/missingness rules
    for _, r in wide.iterrows():
        sid = r["Subject_ID_D"]
        se = to_num(pd.Series([r.get("screen_early_event_count")])).iloc[0]
        sl = to_num(pd.Series([r.get("screen_late_event_count")])).iloc[0]
        sd = to_num(pd.Series([r.get("screen_delta_event_count")])).iloc[0]
        sp = to_num(pd.Series([r.get("screen_pct_change_event_count")])).iloc[0]
        sstat = str(r.get("screen_delta_status", ""))

        ae = to_num(pd.Series([r.get("app_early_foreground_event_count")])).iloc[0]
        al = to_num(pd.Series([r.get("app_late_foreground_event_count")])).iloc[0]
        ad = to_num(pd.Series([r.get("app_delta_foreground_event_count")])).iloc[0]
        apct = to_num(pd.Series([r.get("app_pct_change_foreground_event_count")])).iloc[0]
        astat = str(r.get("app_delta_status", ""))

        screen_both = pd.notna(se) and pd.notna(sl) and se > 0 and sl > 0
        app_both = pd.notna(ae) and pd.notna(al) and ae > 0 and al > 0

        if not screen_both and (pd.notna(sd) or pd.notna(sp) or sstat == "ok"):
            issues.append({"issue_type": "screen_delta_rule", "Subject_ID_D": sid, "detail": "screen delta computed without both windows"})
        if screen_both and sstat != "ok":
            issues.append({"issue_type": "screen_delta_status_mismatch", "Subject_ID_D": sid, "detail": "both windows exist but status not ok"})

        if not app_both and (pd.notna(ad) or pd.notna(apct) or astat == "ok"):
            issues.append({"issue_type": "app_delta_rule", "Subject_ID_D": sid, "detail": "app delta computed without both windows"})
        if app_both and astat != "ok":
            issues.append({"issue_type": "app_delta_status_mismatch", "Subject_ID_D": sid, "detail": "both windows exist but status not ok"})

    # 3) ranges/impossible values
    numeric_cols = [
        "screen_early_event_count", "screen_late_event_count", "screen_delta_event_count", "screen_pct_change_event_count",
        "app_early_foreground_event_count", "app_late_foreground_event_count", "app_delta_foreground_event_count", "app_pct_change_foreground_event_count",
        "aware_log_early_rows", "aware_log_late_rows", "aware_log_delta_rows",
    ]

    stats_rows = []
    for c in numeric_cols:
        if c in wide.columns:
            stats_rows.append(feature_stats(wide, c))

    # impossible checks in subject-window table
    for _, r in sw.iterrows():
        sid = r["Subject_ID_D"]
        t = r["table_name"]
        w = r["window_name"]
        n_rows = to_num(pd.Series([r.get("n_raw_rows")])).iloc[0]
        n_days = to_num(pd.Series([r.get("n_active_days")])).iloc[0]

        if pd.notna(n_rows) and n_rows < 0:
            issues.append({"issue_type": "negative_count", "Subject_ID_D": sid, "table": t, "window": w, "detail": "negative n_raw_rows"})
        if pd.notna(n_days) and n_days < 0:
            issues.append({"issue_type": "negative_days", "Subject_ID_D": sid, "table": t, "window": w, "detail": "negative n_active_days"})
        if pd.notna(n_days) and n_days > 7:
            issues.append({"issue_type": "days_above_window", "Subject_ID_D": sid, "table": t, "window": w, "detail": f"n_active_days={n_days} > 7"})

    # pct infinities/nonsensical
    for c in ["screen_pct_change_event_count", "app_pct_change_foreground_event_count"]:
        x = to_num(wide[c]) if c in wide.columns else pd.Series(dtype=float)
        if np.isinf(x).any():
            issues.append({"issue_type": "pct_infinite", "detail": f"{c} has infinite values"})

    # 4) compare extraction with coverage matrix (early/late has_data expectations)
    # map coverage matrix columns -> expected boolean
    def cov_bool(v):
        return str(v).strip().lower() in {"true", "1", "yes"}

    # build quick lookup from subject-window table
    sw_idx = {}
    for _, r in sw.iterrows():
        sw_idx[(str(r["Subject_ID_D"]), str(r["table_name"]), str(r["window_name"]))] = r

    # only tables in phase1a
    map_cols = {
        "screen": ("screen__early_has_data", "screen__late_has_data"),
        "applications_foreground": ("applications_foreground__early_has_data", "applications_foreground__late_has_data"),
        "aware_log": ("aware_log__early_has_data", "aware_log__late_has_data"),
    }

    for _, r in cm.iterrows():
        sid = str(r["Subject_ID_D"])
        for t, (c_e, c_l) in map_cols.items():
            for w, c in [("early_window", c_e), ("late_window", c_l)]:
                if c not in r.index:
                    continue
                expected_has = cov_bool(r[c])
                got = sw_idx.get((sid, t, w))
                if got is None:
                    issues.append({"issue_type": "missing_subject_window_row", "Subject_ID_D": sid, "table": t, "window": w, "detail": "row missing in subject-window extraction"})
                    continue
                status = str(got.get("extraction_status", ""))
                n_rows = to_num(pd.Series([got.get("n_raw_rows")])).iloc[0]
                if expected_has and status not in {"ok_has_data", "json_parse_error"}:
                    issues.append({"issue_type": "coverage_mismatch_expected_data", "Subject_ID_D": sid, "table": t, "window": w, "detail": f"coverage says has data, extraction status={status}"})
                if (not expected_has) and (pd.notna(n_rows) and n_rows > 0) and status == "ok_has_data":
                    issues.append({"issue_type": "coverage_mismatch_expected_no_data", "Subject_ID_D": sid, "table": t, "window": w, "detail": "coverage says no data, extraction found rows"})

    # 5) subject usability
    merged = wide.merge(top10[["Subject_ID_D", "global_delta"]], on="Subject_ID_D", how="left")

    se = to_num(merged.get("screen_early_event_count", pd.Series(dtype=float)))
    sl = to_num(merged.get("screen_late_event_count", pd.Series(dtype=float)))
    ae = to_num(merged.get("app_early_foreground_event_count", pd.Series(dtype=float)))
    al = to_num(merged.get("app_late_foreground_event_count", pd.Series(dtype=float)))
    le = to_num(merged.get("aware_log_early_rows", pd.Series(dtype=float)))
    ll = to_num(merged.get("aware_log_late_rows", pd.Series(dtype=float)))

    merged["usable_phase1a_baseline"] = ((se > 0) | (ae > 0))
    merged["usable_phase1a_change"] = ((se > 0) & (sl > 0) | (ae > 0) & (al > 0))
    merged["aware_log_early_support"] = (le > 0)
    merged["aware_log_late_support"] = (ll > 0)
    merged["aware_log_change_support"] = (le > 0) & (ll > 0)

    # subject usability export
    subj_usability_cols = [
        "Subject_ID_D", "global_delta",
        "screen_early_event_count", "screen_late_event_count",
        "app_early_foreground_event_count", "app_late_foreground_event_count",
        "aware_log_early_rows", "aware_log_late_rows",
        "usable_phase1a_baseline", "usable_phase1a_change",
        "aware_log_early_support", "aware_log_late_support", "aware_log_change_support",
    ]
    subj_usability = merged[subj_usability_cols].copy()

    # 6) outputs
    pd.DataFrame(stats_rows).to_csv(out_dir / "qc_phase1a_feature_summary.csv", index=False)
    subj_usability.to_csv(out_dir / "qc_phase1a_subject_usability.csv", index=False)
    pd.DataFrame(issues).to_csv(out_dir / "qc_phase1a_issues.csv", index=False)

    readme = out_dir / "README_qc_phase1a.md"
    readme.write_text(
        """# QC Phase 1A

This QC checks Phase 1A extracted outputs only (no new SQL extraction).

Checks performed:
- row-count consistency
- delta/missingness rules
- feature range sanity
- extraction-vs-coverage consistency
- baseline/change usability flags
"""
    )

    # prints requested
    baseline_subjects = subj_usability[subj_usability["usable_phase1a_baseline"] == True]["Subject_ID_D"].astype(str).tolist()
    change_subjects = subj_usability[(subj_usability["usable_phase1a_change"] == True) & (subj_usability["aware_log_change_support"] == True)]["Subject_ID_D"].astype(str).tolist()

    print(f"number_of_qc_issues={len(issues)}")
    print("baseline_usable_subjects=", baseline_subjects)
    print("change_usable_subjects=", change_subjects)

    show_cols = [
        "Subject_ID_D", "global_delta", "screen_early_event_count", "screen_late_event_count", "screen_delta_event_count",
        "app_early_foreground_event_count", "app_late_foreground_event_count", "app_delta_foreground_event_count",
        "aware_log_early_rows", "aware_log_late_rows",
    ]
    show_df = merged[show_cols].copy()
    print("top_10_rows_wide_key_columns:")
    print(show_df.head(10).to_string(index=False))

    print("generated_files:")
    print("-", out_dir / "qc_phase1a_feature_summary.csv")
    print("-", out_dir / "qc_phase1a_subject_usability.csv")
    print("-", out_dir / "qc_phase1a_issues.csv")
    print("-", readme)


if __name__ == "__main__":
    main()
