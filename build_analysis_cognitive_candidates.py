from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd


TZ = "Asia/Jerusalem"


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def excel_serial_to_local_date(serial_s: pd.Series) -> pd.Series:
    # Excel 1900 date system; convert to local calendar date first.
    num = pd.to_numeric(serial_s, errors="coerce")
    dt = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="coerce")
    return dt.dt.date


def local_midnight_from_date(date_s: pd.Series) -> pd.Series:
    # Localize each date at local midnight to avoid DST hour drift.
    dt = pd.to_datetime(date_s, errors="coerce")
    return dt.dt.tz_localize(TZ, nonexistent="shift_forward", ambiguous="NaT")


def local_start_ms(dt_local: pd.Series) -> pd.Series:
    tmp = dt_local.dt.tz_convert("UTC")
    ms = tmp.apply(lambda x: int(x.timestamp() * 1000) if pd.notna(x) else pd.NA)
    return ms.astype("Int64")


def local_end_ms_inclusive(start_local: pd.Series) -> pd.Series:
    next_start = start_local + pd.Timedelta(days=1)
    tmp = next_start.dt.tz_convert("UTC")
    ms = tmp.apply(lambda x: int(x.timestamp() * 1000) - 1 if pd.notna(x) else pd.NA)
    return ms.astype("Int64")


def to_iso(local_midnight_s: pd.Series) -> pd.Series:
    return local_midnight_s.dt.strftime("%Y-%m-%d")


def to_iso_dt(dt_local: pd.Series) -> pd.Series:
    return dt_local.dt.strftime("%Y-%m-%d %H:%M:%S%z")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build analysis-ready cognitive candidates table (no SQL).")
    parser.add_argument("--master", type=Path, default=Path("output/cognitive_master/master_cognitive_wide.csv"))
    parser.add_argument("--flags", type=Path, default=Path("output/cognitive_master/cognitive_code_flags_long.csv"))
    parser.add_argument("--completeness", type=Path, default=Path("output/cognitive_master/qc_subject_completeness.csv"))
    parser.add_argument("--missing-label", type=Path, default=Path("output/cognitive_master/subjects_missing_device_label_id.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("output/analysis_candidates"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    master = pd.read_csv(args.master, dtype=str)
    flags = pd.read_csv(args.flags, dtype=str)
    completeness = pd.read_csv(args.completeness, dtype=str)
    missing_label_df = pd.read_csv(args.missing_label, dtype=str)

    # 1) base select
    keep_demo = [
        "Initials",
        "Subject_ID_N",
        "Subject_ID_D",
        "age",
        "Gender (1=M, 2=F)",
        "Education (years)",
        "T1 date",
        "T2 date",
        "Time lap",
    ]

    outcome_map: Dict[str, str] = {
        "overall_Global score T1": "global_T1",
        "overall_Global score T2": "global_T2",
        "overall_Global score Δ": "global_delta",
        "overall_Memory T1": "memory_T1",
        "overall_Memory T2": "memory_T2",
        "overall_Memory Δ": "memory_delta",
        "overall_EF T1": "ef_T1",
        "overall_EF T2": "ef_T2",
        "overall_EF Δ": "ef_delta",
        "overall_Attention T1": "attention_T1",
        "overall_Attention T2": "attention_T2",
        "overall_Attention Δ": "attention_delta",
        "overall_Processing speed T1": "processing_speed_T1",
        "overall_Processing speed T2": "processing_speed_T2",
        "overall_Processing speed Δ": "processing_speed_delta",
        "overall_Verbal fun T1": "verbal_T1",
        "overall_Verbal fun T2": "verbal_T2",
        "overall_Verbal fun Δ": "verbal_delta",
        "overall_Motor T1": "motor_T1",
        "overall_Motor T2": "motor_T2",
        "overall_Motor Δ": "motor_delta",
        "overall_IQ T1": "iq_T1",
        "overall_IQ T2": "iq_T2",
        "overall_IQ Δ": "iq_delta",
    }

    cols = [c for c in keep_demo if c in master.columns] + [c for c in outcome_map if c in master.columns]
    cand = master[cols].copy().rename(columns=outcome_map)

    # 2) numeric conversion for outcomes and some demographics
    for c in [v for v in outcome_map.values() if v in cand.columns]:
        cand[c] = to_num(cand[c])
    for c in ["age", "Education (years)", "Time lap"]:
        if c in cand.columns:
            cand[c] = to_num(cand[c])

    # 3) date conversion T1/T2 from Excel serial to local calendar date, then local midnight
    t1_date = excel_serial_to_local_date(cand["T1 date"]) if "T1 date" in cand.columns else pd.Series([pd.NaT] * len(cand))
    t2_date = excel_serial_to_local_date(cand["T2 date"]) if "T2 date" in cand.columns else pd.Series([pd.NaT] * len(cand))

    t1_start_local = local_midnight_from_date(t1_date)
    t2_start_local = local_midnight_from_date(t2_date)

    cand["T1_date_iso"] = to_iso(t1_start_local)
    cand["T2_date_iso"] = to_iso(t2_start_local)

    # Full-day boundaries for T1/T2
    cand["T1_start_ms"] = local_start_ms(t1_start_local)
    cand["T1_end_ms"] = local_end_ms_inclusive(t1_start_local)
    cand["T2_start_ms"] = local_start_ms(t2_start_local)
    cand["T2_end_ms"] = local_end_ms_inclusive(t2_start_local)

    # 4) planned windows (calendar-day arithmetic, half-open intervals [start_ms, end_ms))
    early_start_date = t1_date
    early_end_date = pd.to_datetime(t1_date, errors="coerce") + pd.Timedelta(days=7)
    early_end_date = early_end_date.dt.date

    late_start_date = pd.to_datetime(t2_date, errors="coerce") - pd.Timedelta(days=7)
    late_start_date = late_start_date.dt.date
    late_end_date = t2_date

    early_start_local = local_midnight_from_date(early_start_date)
    early_end_local = local_midnight_from_date(early_end_date)
    late_start_local = local_midnight_from_date(late_start_date)
    late_end_local = local_midnight_from_date(late_end_date)

    cand["early_window_start_ms"] = local_start_ms(early_start_local)
    cand["early_window_end_ms"] = local_start_ms(early_end_local)
    cand["late_window_start_ms"] = local_start_ms(late_start_local)
    cand["late_window_end_ms"] = local_start_ms(late_end_local)

    cand["early_window_start_iso"] = to_iso_dt(early_start_local)
    cand["early_window_end_iso"] = to_iso_dt(early_end_local)
    cand["late_window_start_iso"] = to_iso_dt(late_start_local)
    cand["late_window_end_iso"] = to_iso_dt(late_end_local)

    # 5) quality columns
    comp = completeness[["Subject_ID_N", "percent_complete"]].copy() if "percent_complete" in completeness.columns else pd.DataFrame(columns=["Subject_ID_N", "percent_complete"])
    comp["percent_complete"] = to_num(comp["percent_complete"])
    cand = cand.merge(comp, on="Subject_ID_N", how="left")
    cand = cand.rename(columns={"percent_complete": "cognitive_completeness_percent"})

    flags_norm = flags.copy()
    if "raw_value" in flags_norm.columns:
        flags_norm["raw_value"] = flags_norm["raw_value"].astype(str).str.strip().str.upper()
    flag_counts_total = flags_norm.groupby("Subject_ID_N").size().rename("n_special_flags_total") if not flags_norm.empty else pd.Series(dtype=int)
    flag_counts_fp = flags_norm[flags_norm["raw_value"] == "FP"].groupby("Subject_ID_N").size().rename("n_FP") if not flags_norm.empty else pd.Series(dtype=int)
    flag_counts_di = flags_norm[flags_norm["raw_value"] == "DI"].groupby("Subject_ID_N").size().rename("n_DI") if not flags_norm.empty else pd.Series(dtype=int)

    fdf = pd.concat([flag_counts_total, flag_counts_fp, flag_counts_di], axis=1).fillna(0).reset_index()
    cand = cand.merge(fdf, on="Subject_ID_N", how="left")
    for c in ["n_special_flags_total", "n_FP", "n_DI"]:
        cand[c] = cand[c].fillna(0).astype(int)

    missing_set = set(missing_label_df["Subject_ID_N"].astype(str).str.strip()) if not missing_label_df.empty and "Subject_ID_N" in missing_label_df.columns else set()
    sid_d_missing = cand["Subject_ID_D"].isna() | (cand["Subject_ID_D"].astype(str).str.strip().isin(["", "-"]))
    cand["missing_device_label_id"] = sid_d_missing | cand["Subject_ID_N"].astype(str).str.strip().isin(missing_set)

    # 6) decline ranking
    cand["global_decline_amount"] = -cand["global_delta"]
    cand["abs_global_delta"] = cand["global_delta"].abs()

    # outputs
    out_all = args.out_dir / "cognitive_candidates_all.csv"
    out_top_decline = args.out_dir / "top10_global_decline.csv"
    out_top_abs = args.out_dir / "top10_global_abs_change.csv"

    cand.to_csv(out_all, index=False)

    valid_global = cand[cand["global_delta"].notna()].copy()
    top_decline = valid_global.sort_values("global_decline_amount", ascending=False).head(10)
    top_abs = valid_global.sort_values("abs_global_delta", ascending=False).head(10)

    top_decline.to_csv(out_top_decline, index=False)
    top_abs.to_csv(out_top_abs, index=False)

    # prints
    n_candidates = len(cand)
    n_non_missing_global_delta = int(cand["global_delta"].notna().sum())
    valid_t1_t2 = int(cand["T1_start_ms"].notna().sum() & cand["T2_start_ms"].notna().sum())

    print("Candidates summary:")
    print(f"number_of_candidate_subjects={n_candidates}")
    print(f"number_with_non_missing_global_delta={n_non_missing_global_delta}")
    print(f"number_with_valid_T1_and_T2_dates={int((cand['T1_start_ms'].notna() & cand['T2_start_ms'].notna()).sum())}")

    print("\nTop 10 global decline:")
    show_cols = [c for c in ["Subject_ID_N", "Subject_ID_D", "global_T1", "global_T2", "global_delta", "global_decline_amount", "n_FP", "n_DI", "missing_device_label_id"] if c in top_decline.columns]
    print(top_decline[show_cols].to_string(index=False))

    top10_missing_sid_d = top_decline[top_decline["Subject_ID_D"].isna() | (top_decline["Subject_ID_D"].astype(str).str.strip().isin(["", "-"]))]
    top10_with_flags = top_decline[(top_decline["n_FP"] > 0) | (top_decline["n_DI"] > 0)]

    print(f"\nAny top10 missing Subject_ID_D: {not top10_missing_sid_d.empty}")
    if not top10_missing_sid_d.empty:
        print(top10_missing_sid_d[[c for c in ["Subject_ID_N", "Subject_ID_D", "global_delta"] if c in top10_missing_sid_d.columns]].to_string(index=False))

    print(f"Any top10 with FP/DI flags: {not top10_with_flags.empty}")
    if not top10_with_flags.empty:
        print(top10_with_flags[[c for c in ["Subject_ID_N", "Subject_ID_D", "n_FP", "n_DI", "global_delta"] if c in top10_with_flags.columns]].to_string(index=False))

    print("\nDate conversion examples (first 10 rows):")
    ex_cols = [c for c in ["Subject_ID_N", "Subject_ID_D", "T1 date", "T2 date", "T1_date_iso", "T2_date_iso", "T1_start_ms", "T2_start_ms", "early_window_start_iso", "late_window_end_iso"] if c in cand.columns]
    print(cand[ex_cols].head(10).to_string(index=False))

    print("\nGenerated files:")
    print(out_all)
    print(out_top_decline)
    print(out_top_abs)


if __name__ == "__main__":
    main()
