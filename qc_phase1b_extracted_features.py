from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


OUT_DIR = Path("output/analysis_candidates/phase1_features/extracted")


def normalize_subject_id_d(v) -> str:
    s = str(v).strip()
    return s.zfill(3) if s.isdigit() else s


def to_bool(v):
    if pd.isna(v):
        return False
    s = str(v).strip().lower()
    return s in {"1", "true", "t", "yes", "y"}


def numeric_summary(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = []
    for c in columns:
        if c not in df.columns:
            continue
        s = pd.to_numeric(df[c], errors="coerce")
        non_missing = int(s.notna().sum())
        if non_missing == 0:
            rows.append({"column": c, "non_missing_count": 0, "min": np.nan, "median": np.nan, "mean": np.nan, "max": np.nan, "n_zeros": 0, "n_negative": 0})
            continue
        rows.append({
            "column": c,
            "non_missing_count": non_missing,
            "min": float(s.min()),
            "median": float(s.median()),
            "mean": float(s.mean()),
            "max": float(s.max()),
            "n_zeros": int((s == 0).sum()),
            "n_negative": int((s < 0).sum()),
        })
    return pd.DataFrame(rows)


def main() -> None:
    device_df = pd.read_csv(OUT_DIR / "phase1b_device_window_features.csv")
    subject_window_df = pd.read_csv(OUT_DIR / "phase1b_subject_window_features.csv")
    wide_df = pd.read_csv(OUT_DIR / "phase1b_subject_features_wide.csv")
    readiness_df = pd.read_csv("output/analysis_candidates/sql_coverage/top10_subject_readiness.csv")
    matrix_df = pd.read_csv("output/analysis_candidates/sql_coverage/top10_subject_table_coverage_matrix.csv")
    decline_df = pd.read_csv("output/analysis_candidates/top10_global_decline.csv")

    for df in [device_df, subject_window_df, wide_df, readiness_df, matrix_df, decline_df]:
        if "Subject_ID_D" in df.columns:
            df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id_d)

    issues = []

    device_counts = (
        device_df.groupby(["table_name", "window_name", "extraction_status"], dropna=False)
        .size().reset_index(name="n_rows")
        .sort_values(["table_name", "window_name", "n_rows"], ascending=[True, True, False])
    )
    subject_window_counts = (
        subject_window_df.groupby(["table_name", "window_name", "extraction_status"], dropna=False)
        .size().reset_index(name="n_rows")
        .sort_values(["table_name", "window_name", "n_rows"], ascending=[True, True, False])
    )

    expected_subjects = decline_df["Subject_ID_D"].nunique(dropna=True)
    actual_subjects = wide_df["Subject_ID_D"].nunique(dropna=True)
    if expected_subjects != actual_subjects:
        issues.append({"issue_type": "wide_subject_count_mismatch", "severity": "high", "details": f"expected={expected_subjects}, actual={actual_subjects}"})

    delta_rules = [
        ("keyboard", "keyboard_early_event_count", "keyboard_late_event_count", "keyboard_delta_event_count", "keyboard_pct_change_event_count", "keyboard_delta_status"),
        ("touch", "touch_early_event_count", "touch_late_event_count", "touch_delta_event_count", "touch_pct_change_event_count", "touch_delta_status"),
        ("activity", "activity_early_event_count", "activity_late_event_count", "activity_delta_event_count", "activity_pct_change_event_count", "activity_delta_status"),
    ]

    for prefix, early_col, late_col, delta_col, pct_col, status_col in delta_rules:
        if any(c not in wide_df.columns for c in [early_col, late_col, delta_col, pct_col, status_col]):
            issues.append({"issue_type": "missing_columns", "severity": "high", "details": f"{prefix} delta columns missing"})
            continue

        both_present = wide_df[early_col].notna() & wide_df[late_col].notna()
        status = wide_df[status_col].astype(str)

        # Delta/pct should exist only when both present
        bad_delta = (~both_present) & (wide_df[delta_col].notna() | wide_df[pct_col].notna())
        for _, r in wide_df[bad_delta].iterrows():
            issues.append({"issue_type": "delta_with_missing_window", "severity": "high", "details": f"{prefix} {r['Subject_ID_D']}"})

        # status must align with availability
        bad_status_computed = both_present & (~status.isin(["ok", "ok_both_windows"]))
        for _, r in wide_df[bad_status_computed].iterrows():
            issues.append({"issue_type": "delta_status_mismatch", "severity": "medium", "details": f"{prefix} {r['Subject_ID_D']} both present status={r[status_col]}"})

        bad_status_missing = (~both_present) & (status == "ok_both_windows")
        for _, r in wide_df[bad_status_missing].iterrows():
            issues.append({"issue_type": "delta_status_mismatch", "severity": "medium", "details": f"{prefix} {r['Subject_ID_D']} missing early/late but status ok_both_windows"})

    numeric_cols = [c for c in wide_df.columns if any(k in c for k in ["_count", "_days", "_diversity", "_confidence", "_pct_change", "_delta"])]
    feature_summary = numeric_summary(wide_df, numeric_cols)

    for col in [c for c in wide_df.columns if ("_count" in c or "_days" in c) and "_delta_" not in c and "pct_change" not in c]:
        s = pd.to_numeric(wide_df[col], errors="coerce")
        for _, r in wide_df[(s < 0).fillna(False)].iterrows():
            issues.append({"issue_type": "negative_count_or_days", "severity": "high", "details": f"{col} {r['Subject_ID_D']}"})

    for col in ["active_keyboard_days", "active_touch_days", "active_activity_days", "n_active_days"]:
        if col in subject_window_df.columns:
            s = pd.to_numeric(subject_window_df[col], errors="coerce")
            for _, r in subject_window_df[(s > 7).fillna(False)].iterrows():
                issues.append({"issue_type": "active_days_gt_7", "severity": "high", "details": f"{col} {r['Subject_ID_D']} {r['table_name']} {r['window_name']}"})

    for col in [c for c in wide_df.columns if "pct_change" in c]:
        s = pd.to_numeric(wide_df[col], errors="coerce")
        inf_mask = np.isinf(s.to_numpy(dtype=float, na_value=np.nan))
        for idx in np.where(inf_mask)[0]:
            r = wide_df.iloc[idx]
            issues.append({"issue_type": "pct_change_infinite", "severity": "high", "details": f"{col} {r['Subject_ID_D']}"})

    if "activity_diversity" in subject_window_df.columns:
        s = pd.to_numeric(subject_window_df["activity_diversity"], errors="coerce")
        for _, r in subject_window_df[(s < 0).fillna(False)].iterrows():
            issues.append({"issue_type": "activity_diversity_negative", "severity": "high", "details": f"{r['Subject_ID_D']} {r['window_name']}"})

    for col in ["mean_activity_confidence", "activity_early_mean_confidence", "activity_late_mean_confidence"]:
        if col in list(subject_window_df.columns) + list(wide_df.columns):
            d = subject_window_df if col in subject_window_df.columns else wide_df
            s = pd.to_numeric(d[col], errors="coerce")
            for _, r in d[((s < 0) | (s > 100)).fillna(False)].iterrows():
                issues.append({"issue_type": "confidence_out_of_range", "severity": "medium", "details": f"{col} {r['Subject_ID_D']} val={r[col]}"})

    # privacy check
    forbidden = ["current_text", "before_text", "text", "raw_text"]
    privacy_hits = []
    for name, d in [("device", device_df), ("subject_window", subject_window_df), ("wide", wide_df)]:
        for token in forbidden:
            for c in d.columns:
                if token in c.lower():
                    privacy_hits.append((name, c))
                    issues.append({"issue_type": "privacy_forbidden_column", "severity": "critical", "details": f"{name}:{c}"})

    # no_data should be NaN in primary event counts
    primary_col_by_table = {
        "keyboard": "keyboard_event_count",
        "touch": "touch_event_count",
        "plugin_google_activity_recognition": "activity_event_count",
    }
    bad_no_data_primary = []
    for _, r in subject_window_df.iterrows():
        table = str(r["table_name"])
        status = str(r["extraction_status"])
        col = primary_col_by_table.get(table)
        if not col or col not in subject_window_df.columns:
            continue
        if status in {"ok_no_data", "missing_window", "sql_error", "json_parse_error"}:
            v = pd.to_numeric(pd.Series([r.get(col)]), errors="coerce").iloc[0]
            if pd.notna(v):
                bad_no_data_primary.append((r["Subject_ID_D"], table, r["window_name"], status, v))
                issues.append({"issue_type": "no_data_encoded_as_value", "severity": "high", "details": f"{r['Subject_ID_D']} {table} {r['window_name']} status={status} value={v}"})

    rows = []
    for _, r in subject_window_df.iterrows():
        table = str(r.get("table_name"))
        window = str(r.get("window_name"))
        sid = normalize_subject_id_d(r.get("Subject_ID_D"))
        cov_col = f"{table}__{'early' if window == 'early_window' else 'late'}_has_data"
        m = matrix_df[matrix_df["Subject_ID_D"] == sid]
        cov_has_data = np.nan
        if not m.empty and cov_col in m.columns:
            cov_has_data = to_bool(m.iloc[0][cov_col])

        ext_status = str(r.get("extraction_status", ""))
        ext_rows = pd.to_numeric(pd.Series([r.get("n_raw_rows")]), errors="coerce").iloc[0]

        mismatch = False
        msg = ""
        if pd.isna(cov_has_data):
            msg = "coverage_missing"
        else:
            if cov_has_data and ext_status not in {"ok_has_data", "json_parse_error"}:
                mismatch = True
                msg = f"coverage has data but extraction_status={ext_status}"
            if (not cov_has_data) and ext_status == "ok_has_data":
                mismatch = True
                msg = "coverage no data but extraction_status=ok_has_data"
            if (not cov_has_data) and ext_status == "ok_no_data" and pd.notna(ext_rows) and ext_rows != 0:
                mismatch = True
                msg = f"coverage no data but ok_no_data with n_raw_rows={ext_rows}"

        rows.append({
            "Subject_ID_D": sid,
            "table_name": table,
            "window_name": window,
            "coverage_has_data": cov_has_data,
            "extraction_status": ext_status,
            "extraction_n_raw_rows": ext_rows,
            "coverage_extraction_mismatch": mismatch,
            "mismatch_details": msg,
        })
        if mismatch:
            issues.append({"issue_type": "coverage_extraction_mismatch", "severity": "high", "details": f"{sid} {table} {window}: {msg}"})

    sw = subject_window_df.copy()
    sw["n_raw_rows_num"] = pd.to_numeric(sw["n_raw_rows"], errors="coerce").fillna(0)

    def has_data(sub_df, table, win):
        x = sub_df[(sub_df["table_name"] == table) & (sub_df["window_name"] == win)]
        if x.empty:
            return False
        return bool(((x["extraction_status"] == "ok_has_data") & (x["n_raw_rows_num"] > 0)).any())

    usability_rows = []
    for sid in sorted(wide_df["Subject_ID_D"].astype(str).unique()):
        sub = sw[sw["Subject_ID_D"].astype(str) == sid]
        kb_e = has_data(sub, "keyboard", "early_window")
        kb_l = has_data(sub, "keyboard", "late_window")
        t_e = has_data(sub, "touch", "early_window")
        t_l = has_data(sub, "touch", "late_window")
        a_e = has_data(sub, "plugin_google_activity_recognition", "early_window")
        a_l = has_data(sub, "plugin_google_activity_recognition", "late_window")

        usability_rows.append({
            "Subject_ID_D": sid,
            "keyboard_early_has_data": kb_e,
            "keyboard_late_has_data": kb_l,
            "touch_early_has_data": t_e,
            "touch_late_has_data": t_l,
            "activity_early_has_data": a_e,
            "activity_late_has_data": a_l,
            "phase1b_baseline_usable": kb_e or t_e or a_e,
            "phase1b_change_usable": (a_e and a_l) or (kb_e and kb_l) or (t_e and t_l),
        })
    usability_df = pd.DataFrame(usability_rows)

    wide_display = wide_df.merge(decline_df[["Subject_ID_D", "global_delta"]], on="Subject_ID_D", how="left")

    key_cols = [
        "Subject_ID_D", "global_delta",
        "keyboard_early_event_count", "keyboard_late_event_count", "keyboard_delta_event_count",
        "touch_early_event_count", "touch_late_event_count", "touch_delta_event_count",
        "activity_early_event_count", "activity_late_event_count", "activity_delta_event_count",
        "activity_early_still_event_count", "activity_late_still_event_count",
        "activity_early_walking_event_count", "activity_late_walking_event_count",
        "activity_early_in_vehicle_event_count", "activity_late_in_vehicle_event_count",
    ]
    key_cols = [c for c in key_cols if c in wide_display.columns]

    summary_parts = [
        device_counts.assign(section="device_rows_by_table_window_status"),
        subject_window_counts.assign(section="subject_window_rows_by_table_window_status"),
        feature_summary.assign(section="wide_numeric_feature_summary"),
        pd.DataFrame([
            {"section": "meta", "metric": "expected_subjects", "value": expected_subjects},
            {"section": "meta", "metric": "actual_subjects_in_wide", "value": actual_subjects},
            {"section": "meta", "metric": "n_qc_issues", "value": len(issues)},
            {"section": "meta", "metric": "privacy_forbidden_columns_found", "value": len(privacy_hits)},
            {"section": "meta", "metric": "no_data_windows_with_primary_value", "value": len(bad_no_data_primary)},
        ])
    ]
    qc_summary = pd.concat(summary_parts, ignore_index=True, sort=False)

    issues_df = pd.DataFrame(issues)
    if issues_df.empty:
        issues_df = pd.DataFrame(columns=["issue_type", "severity", "details"])

    qc_summary.to_csv(OUT_DIR / "qc_phase1b_feature_summary.csv", index=False)
    usability_df.to_csv(OUT_DIR / "qc_phase1b_subject_usability.csv", index=False)
    issues_df.to_csv(OUT_DIR / "qc_phase1b_issues.csv", index=False)

    baseline_subjects = usability_df.loc[usability_df["phase1b_baseline_usable"], "Subject_ID_D"].tolist()
    change_subjects = usability_df.loc[usability_df["phase1b_change_usable"], "Subject_ID_D"].tolist()
    privacy_ok = len(privacy_hits) == 0

    with (OUT_DIR / "README_qc_phase1b.md").open("w", encoding="utf-8") as f:
        f.write("# QC Phase 1B Extracted Features\n\n")
        f.write(f"- QC issues: {len(issues)}\n")
        f.write(f"- Privacy validation: {'PASS' if privacy_ok else 'FAIL'}\n")
        f.write(f"- no_data windows with primary value (should be 0): {len(bad_no_data_primary)}\n")
        f.write(f"- Baseline-usable subjects: {baseline_subjects}\n")
        f.write(f"- Change-usable subjects: {change_subjects}\n")

    print("Loaded inputs:")
    print(f"- device rows: {len(device_df)}")
    print(f"- subject_window rows: {len(subject_window_df)}")
    print(f"- wide rows: {len(wide_df)}")

    print("\nDevice-level rows by table/window/status:")
    print(device_counts.to_string(index=False))

    print("\nSubject-window rows by table/window/status:")
    print(subject_window_counts.to_string(index=False))

    print("\nPrivacy validation:")
    print("- PASS (no forbidden keyboard text columns present)" if privacy_ok else "- FAIL")

    print("\nBaseline-usable subjects:")
    print(baseline_subjects)
    print("Change-usable subjects:")
    print(change_subjects)

    print(f"\nNumber of QC issues: {len(issues)}")
    if not issues_df.empty:
        print(issues_df.head(20).to_string(index=False))

    print("\nTop 10 rows of wide features (key columns):")
    print(wide_display[key_cols].head(10).to_string(index=False))

    print("\nGenerated files:")
    for p in [
        OUT_DIR / "qc_phase1b_feature_summary.csv",
        OUT_DIR / "qc_phase1b_subject_usability.csv",
        OUT_DIR / "qc_phase1b_issues.csv",
        OUT_DIR / "README_qc_phase1b.md",
    ]:
        print(f"- {p}")


if __name__ == "__main__":
    main()
