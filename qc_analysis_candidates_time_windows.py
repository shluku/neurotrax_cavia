from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd


MIN_MS = 1704067200000  # 2024-01-01 UTC
MAX_MS = 1830211199000  # 2027-12-31 23:59:59 UTC


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def add_issue(issues: List[dict], row: pd.Series, issue: str) -> None:
    issues.append(
        {
            "Subject_ID_N": row.get("Subject_ID_N", ""),
            "Subject_ID_D": row.get("Subject_ID_D", ""),
            "issue": issue,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="QC for analysis candidate time windows.")
    parser.add_argument("--all", type=Path, default=Path("output/analysis_candidates/cognitive_candidates_all.csv"))
    parser.add_argument("--top-decline", type=Path, default=Path("output/analysis_candidates/top10_global_decline.csv"))
    parser.add_argument("--top-abs", type=Path, default=Path("output/analysis_candidates/top10_global_abs_change.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("output/analysis_candidates"))
    args = parser.parse_args()

    all_df = pd.read_csv(args.all, dtype=str)
    top_decline = pd.read_csv(args.top_decline, dtype=str)
    top_abs = pd.read_csv(args.top_abs, dtype=str)

    print("Input dimensions:")
    print(f"cognitive_candidates_all.csv: {all_df.shape}")
    print(f"top10_global_decline.csv: {top_decline.shape}")
    print(f"top10_global_abs_change.csv: {top_abs.shape}")

    ms_cols = [
        "T1_start_ms", "T1_end_ms", "T2_start_ms", "T2_end_ms",
        "early_window_start_ms", "early_window_end_ms",
        "late_window_start_ms", "late_window_end_ms",
    ]
    for c in ms_cols:
        if c in all_df.columns:
            all_df[c] = to_num(all_df[c])

    issues: List[dict] = []

    # 2) ms range checks
    invalid_ms_mask = pd.Series([False] * len(all_df), index=all_df.index)
    for c in ms_cols:
        if c not in all_df.columns:
            continue
        v = all_df[c]
        bad = v.notna() & ((v < MIN_MS) | (v > MAX_MS))
        invalid_ms_mask = invalid_ms_mask | bad
        for i in all_df[bad].index:
            add_issue(issues, all_df.loc[i], f"invalid_ms_range:{c}")

    # 3) ordering validations
    def check_lt(a: str, b: str, issue_name: str) -> pd.Series:
        if a not in all_df.columns or b not in all_df.columns:
            return pd.Series([False] * len(all_df), index=all_df.index)
        sa, sb = all_df[a], all_df[b]
        bad = sa.notna() & sb.notna() & ~(sa < sb)
        for i in all_df[bad].index:
            add_issue(issues, all_df.loc[i], issue_name)
        return bad

    bad_t1_order = check_lt("T1_start_ms", "T1_end_ms", "T1_start_not_before_T1_end")
    bad_t2_order = check_lt("T2_start_ms", "T2_end_ms", "T2_start_not_before_T2_end")
    bad_t1_t2_order = check_lt("T1_start_ms", "T2_start_ms", "T2_before_or_equal_T1")
    bad_early_order = check_lt("early_window_start_ms", "early_window_end_ms", "early_window_start_not_before_end")
    bad_late_order = check_lt("late_window_start_ms", "late_window_end_ms", "late_window_start_not_before_end")

    # 4) overlap between early and late windows
    overlap_mask = pd.Series([False] * len(all_df), index=all_df.index)
    if all(c in all_df.columns for c in ["early_window_start_ms", "early_window_end_ms", "late_window_start_ms", "late_window_end_ms"]):
        es, ee = all_df["early_window_start_ms"], all_df["early_window_end_ms"]
        ls, le = all_df["late_window_start_ms"], all_df["late_window_end_ms"]
        valid = es.notna() & ee.notna() & ls.notna() & le.notna()
        overlap_mask = valid & (es <= le) & (ls <= ee)
        for i in all_df[overlap_mask].index:
            add_issue(issues, all_df.loc[i], "early_late_window_overlap")

    # 5) missing critical windows
    critical_missing = pd.Series([False] * len(all_df), index=all_df.index)
    critical_cols = ["T1_start_ms", "T1_end_ms", "T2_start_ms", "T2_end_ms", "early_window_start_ms", "early_window_end_ms", "late_window_start_ms", "late_window_end_ms"]
    for c in critical_cols:
        if c in all_df.columns:
            m = all_df[c].isna()
            critical_missing = critical_missing | m
            for i in all_df[m].index:
                add_issue(issues, all_df.loc[i], f"missing:{c}")

    issues_df = pd.DataFrame(issues).drop_duplicates()

    # 6) preview for top10 decline
    preview_cols = [
        "Subject_ID_N", "Subject_ID_D", "T1 date", "T1_date_iso", "T1_start_ms",
        "T2 date", "T2_date_iso", "T2_start_ms",
        "early_window_start_iso", "early_window_end_iso",
        "late_window_start_iso", "late_window_end_iso",
    ]
    preview_cols = [c for c in preview_cols if c in top_decline.columns]
    top_decline_preview = top_decline[preview_cols].copy()

    print("\nRows with invalid/missing time windows (sample up to 30):")
    if issues_df.empty:
        print("(none)")
    else:
        print(issues_df.head(30).to_string(index=False))

    print("\nTop10 global decline date conversion preview:")
    print(top_decline_preview.to_string(index=False))

    # Save outputs
    out_issues = args.out_dir / "qc_time_window_issues.csv"
    out_preview = args.out_dir / "top10_global_decline_time_windows_preview.csv"
    issues_df.to_csv(out_issues, index=False)
    top_decline_preview.to_csv(out_preview, index=False)

    # 8) final summary
    valid_t1_t2 = (all_df.get("T1_start_ms").notna() & all_df.get("T1_end_ms").notna() & all_df.get("T2_start_ms").notna() & all_df.get("T2_end_ms").notna()).sum() if all(c in all_df.columns for c in ["T1_start_ms","T1_end_ms","T2_start_ms","T2_end_ms"]) else 0
    top10_valid_windows = 0
    if all(c in top_decline.columns for c in ["T1_start_ms","T1_end_ms","T2_start_ms","T2_end_ms"]):
        td = top_decline.copy()
        for c in ["T1_start_ms","T1_end_ms","T2_start_ms","T2_end_ms"]:
            td[c] = to_num(td[c])
        top10_valid_windows = int((td["T1_start_ms"].notna() & td["T1_end_ms"].notna() & td["T2_start_ms"].notna() & td["T2_end_ms"].notna()).sum())

    print("\nFinal QC summary:")
    print(f"total_subjects={len(all_df)}")
    print(f"valid_T1_T2_windows={int(valid_t1_t2)}")
    print(f"invalid_ms_range_count={int(invalid_ms_mask.sum())}")
    print(f"T2_before_T1_count={int(bad_t1_t2_order.sum())}")
    print(f"early_late_overlap_count={int(overlap_mask.sum())}")
    print(f"top10_subjects_with_valid_windows={int(top10_valid_windows)}")

    print("\nGenerated files:")
    print(out_issues)
    print(out_preview)


if __name__ == "__main__":
    main()
