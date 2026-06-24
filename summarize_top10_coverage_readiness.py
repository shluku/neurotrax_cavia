import argparse
from pathlib import Path
import pandas as pd

DOMAIN_GUESS = {
    "screen": "phone_usage",
    "applications_foreground": "phone_usage / app_use",
    "keyboard": "phone_interaction",
    "touch": "phone_interaction",
    "battery": "device_routine / data_quality",
    "wifi": "environment_context",
    "locations": "mobility",
    "plugin_google_activity_recognition": "activity_pattern",
    "calls": "social_communication",
    "messages": "social_communication",
    "telephony": "social_communication",
    "gsm": "cellular_context / mobility_proxy",
    "gsm_neighbor": "cellular_context / mobility_proxy",
    "aware_log": "data_quality/system_log",
}


def as_bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in {"1", "true", "yes"}


def map_recommended_use(has_early, has_late):
    if has_early and has_late:
        return "baseline_and_change"
    if has_early and not has_late:
        return "baseline_only"
    if (not has_early) and has_late:
        return "late_only_not_baseline"
    return "exclude_current_poc_no_data"


def table_readiness_status(early_subjects, late_subjects, total_rows):
    if early_subjects >= 5 and late_subjects >= 2:
        return "high_priority_feature_candidate"
    if early_subjects >= 5 and late_subjects < 2:
        return "baseline_only_candidate"
    if total_rows > 0:
        return "limited_candidate"
    return "not_useful_current_poc"


def table_next_action(status):
    return {
        "high_priority_feature_candidate": "extract baseline + early_late change features first",
        "baseline_only_candidate": "extract baseline features now; postpone change features",
        "limited_candidate": "keep optional; use only if clinically motivated",
        "not_useful_current_poc": "skip for current top10 poc",
    }[status]


def main():
    ap = argparse.ArgumentParser(description="Summarize top10 SQL coverage readiness (no SQL).")
    ap.add_argument("--coverage-long", default="output/analysis_candidates/sql_coverage/top10_sql_coverage_long.csv")
    ap.add_argument("--early-late-summary", default="output/analysis_candidates/sql_coverage/top10_sql_coverage_early_late_summary.csv")
    ap.add_argument("--subject-summary", default="output/analysis_candidates/sql_coverage/top10_sql_coverage_summary_by_subject.csv")
    ap.add_argument("--table-summary", default="output/analysis_candidates/sql_coverage/top10_sql_coverage_summary_by_table.csv")
    ap.add_argument("--episodes", default="output/analysis_candidates/top10_subject_device_episodes.csv")
    ap.add_argument("--feature-dict", default="output/sql_catalog/sql_feature_dictionary.csv")
    ap.add_argument("--table-interpret", default="output/sql_catalog/sql_table_interpretation.csv")
    ap.add_argument("--out-dir", default="output/analysis_candidates/sql_coverage")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df_long = pd.read_csv(args.coverage_long, dtype=str)
    df_el = pd.read_csv(args.early_late_summary, dtype=str)
    df_sub = pd.read_csv(args.subject_summary, dtype=str)
    df_tab = pd.read_csv(args.table_summary, dtype=str)
    df_ep = pd.read_csv(args.episodes, dtype=str)
    # optional context loads
    _ = pd.read_csv(args.feature_dict, dtype=str) if Path(args.feature_dict).exists() else pd.DataFrame()
    _ = pd.read_csv(args.table_interpret, dtype=str) if Path(args.table_interpret).exists() else pd.DataFrame()

    # 1) subject readiness
    s = df_el.copy()
    s["has_early_data"] = s["has_early_data"].map(as_bool)
    s["has_late_data"] = s["has_late_data"].map(as_bool)
    s["baseline_phenotype_ready"] = s["has_early_data"]
    s["change_analysis_ready"] = s["has_early_data"] & s["has_late_data"]
    s["recommended_use"] = [map_recommended_use(e, l) for e, l in zip(s["has_early_data"], s["has_late_data"])]

    subj_cols = [
        "Subject_ID_N", "Subject_ID_D", "n_devices_for_subject", "early_total_rows", "late_total_rows",
        "early_tables_with_data", "late_tables_with_data", "has_early_data", "has_late_data",
        "early_late_coverage_group", "baseline_phenotype_ready", "change_analysis_ready", "recommended_use",
    ]
    s = s[subj_cols].sort_values(["change_analysis_ready", "baseline_phenotype_ready", "Subject_ID_D"], ascending=[False, False, True])
    s.to_csv(out_dir / "top10_subject_readiness.csv", index=False)

    # 2) table readiness from long early/late only
    d = df_long[df_long["window_name"].isin(["early_window", "late_window"])].copy()
    d["n_rows_num"] = pd.to_numeric(d["n_rows"], errors="coerce").fillna(0)
    d["has_data"] = d["coverage_status"] == "ok_has_data"

    rows = []
    for table, g in d.groupby("table_name", dropna=False):
        ge = g[g["window_name"] == "early_window"]
        gl = g[g["window_name"] == "late_window"]

        early_total = int(ge["n_rows_num"].sum())
        late_total = int(gl["n_rows_num"].sum())

        early_sub = int(ge.loc[ge["has_data"], "Subject_ID_D"].nunique())
        late_sub = int(gl.loc[gl["has_data"], "Subject_ID_D"].nunique())

        early_dev = int(ge.loc[ge["has_data"], "device_id"].nunique())
        late_dev = int(gl.loc[gl["has_data"], "device_id"].nunique())

        # subjects with both early+late for this table
        early_set = set(ge.loc[ge["has_data"], "Subject_ID_D"].astype(str))
        late_set = set(gl.loc[gl["has_data"], "Subject_ID_D"].astype(str))
        both = len(early_set & late_set)

        total_rows = early_total + late_total
        status = table_readiness_status(early_sub, late_sub, total_rows)

        rows.append({
            "table_name": table,
            "early_total_rows": early_total,
            "late_total_rows": late_total,
            "early_subjects_with_data": early_sub,
            "late_subjects_with_data": late_sub,
            "subjects_with_both_early_and_late": both,
            "early_devices_with_data": early_dev,
            "late_devices_with_data": late_dev,
            "total_rows_early_late": total_rows,
            "phenotype_domain_guess": DOMAIN_GUESS.get(table, "unknown"),
            "readiness_status": status,
            "recommended_next_action": table_next_action(status),
        })

    tr = pd.DataFrame(rows).sort_values(["total_rows_early_late", "table_name"], ascending=[False, True])
    tr.to_csv(out_dir / "top10_table_readiness.csv", index=False)

    # 3) subject x table matrix
    m = d[["Subject_ID_D", "table_name", "window_name", "n_rows_num", "has_data"]].copy()
    piv_rows = []
    for sid, gs in m.groupby("Subject_ID_D", dropna=False):
        row = {"Subject_ID_D": sid}
        for table in sorted(d["table_name"].dropna().unique()):
            gse = gs[(gs["table_name"] == table) & (gs["window_name"] == "early_window")]
            gsl = gs[(gs["table_name"] == table) & (gs["window_name"] == "late_window")]
            e_rows = int(gse["n_rows_num"].sum()) if not gse.empty else 0
            l_rows = int(gsl["n_rows_num"].sum()) if not gsl.empty else 0
            e_has = bool(gse["has_data"].any()) if not gse.empty else False
            l_has = bool(gsl["has_data"].any()) if not gsl.empty else False
            row[f"{table}__early_n_rows"] = e_rows
            row[f"{table}__late_n_rows"] = l_rows
            row[f"{table}__early_has_data"] = e_has
            row[f"{table}__late_has_data"] = l_has
        piv_rows.append(row)
    mat = pd.DataFrame(piv_rows).sort_values("Subject_ID_D")
    mat.to_csv(out_dir / "top10_subject_table_coverage_matrix.csv", index=False)

    # 4) markdown report
    baseline_ready = s[s["baseline_phenotype_ready"] == True]["Subject_ID_D"].astype(str).tolist()
    change_ready = s[s["change_analysis_ready"] == True]["Subject_ID_D"].astype(str).tolist()
    limited = s[s["recommended_use"].isin(["late_only_not_baseline", "exclude_current_poc_no_data"])]["Subject_ID_D"].astype(str).tolist()

    top_high = tr[tr["readiness_status"] == "high_priority_feature_candidate"]["table_name"].astype(str).tolist()
    top_baseline_only = tr[tr["readiness_status"] == "baseline_only_candidate"]["table_name"].astype(str).tolist()
    top_not_useful = tr[tr["readiness_status"] == "not_useful_current_poc"]["table_name"].astype(str).tolist()

    md = []
    md.append("# Top10 Coverage Readiness")
    md.append("")
    md.append("## Executive Summary")
    md.append(f"- Baseline-ready subjects: {len(baseline_ready)} / {len(s)}")
    md.append(f"- Change-analysis-ready subjects: {len(change_ready)} / {len(s)}")
    md.append("- This is exploratory only (top10 PoC).")
    md.append("")
    md.append("## Baseline-Ready Subjects")
    md.append("- " + (", ".join(baseline_ready) if baseline_ready else "none"))
    md.append("")
    md.append("## Change-Analysis-Ready Subjects")
    md.append("- " + (", ".join(change_ready) if change_ready else "none"))
    md.append("")
    md.append("## Excluded or Limited Subjects")
    md.append("- " + (", ".join(limited) if limited else "none"))
    md.append("")
    md.append("## Top Candidate Tables for First Feature Extraction")
    md.append("- " + (", ".join(top_high) if top_high else "none"))
    md.append("")
    md.append("## Baseline-Only Tables")
    md.append("- " + (", ".join(top_baseline_only) if top_baseline_only else "none"))
    md.append("")
    md.append("## Not Useful in Current PoC")
    md.append("- " + (", ".join(top_not_useful) if top_not_useful else "none"))
    md.append("")
    md.append("## Warning")
    md.append("- n=10 is exploratory. Only 2 subjects currently support early-vs-late change analysis.")

    (out_dir / "README_top10_coverage_readiness.md").write_text("\n".join(md))

    print("Subject readiness table:")
    print(s.to_string(index=False))
    print("\nTable readiness table:")
    print(tr.to_string(index=False))
    print("\nBaseline-ready subjects:", baseline_ready)
    print("Change-analysis-ready subjects:", change_ready)
    print("Recommended first feature tables:", top_high)

    print("\nGenerated files:")
    for p in [
        out_dir / "top10_subject_readiness.csv",
        out_dir / "top10_table_readiness.csv",
        out_dir / "top10_subject_table_coverage_matrix.csv",
        out_dir / "README_top10_coverage_readiness.md",
    ]:
        print(f"- {p}")


if __name__ == "__main__":
    main()
