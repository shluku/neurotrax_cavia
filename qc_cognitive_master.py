from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd


PREFIXES = ["overall_", "mem_", "ef_", "attn_", "ps_", "verbal_", "motor_"]
SPECIAL_CODES = {"FP", "DI", "NA", "N/A"}


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    try:
        return pd.read_csv(path, dtype=str)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def to_numeric_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def group_columns(columns: List[str]) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {"subject/base": []}
    for p in PREFIXES:
        groups[p] = []

    for c in columns:
        matched = False
        for p in PREFIXES:
            if c.startswith(p):
                groups[p].append(c)
                matched = True
                break
        if not matched:
            groups["subject/base"].append(c)

    return groups


def main() -> None:
    parser = argparse.ArgumentParser(description="QC for cognitive master outputs.")
    parser.add_argument("--input-dir", type=Path, default=Path("output/cognitive_master"))
    args = parser.parse_args()

    in_dir = args.input_dir
    master_path = in_dir / "master_cognitive_wide.csv"
    flags_path = in_dir / "cognitive_code_flags_long.csv"
    dict_path = in_dir / "cognitive_data_dictionary.csv"
    delta_path = in_dir / "delta_consistency_report.csv"

    # 1) load all four files
    master = safe_read_csv(master_path)
    flags = safe_read_csv(flags_path)
    data_dict = safe_read_csv(dict_path)
    delta = safe_read_csv(delta_path)

    # 2) print dimensions
    print("Input dimensions:")
    print(f"master_cognitive_wide.csv: {master.shape}")
    print(f"cognitive_code_flags_long.csv: {flags.shape}")
    print(f"cognitive_data_dictionary.csv: {data_dict.shape}")
    print(f"delta_consistency_report.csv: {delta.shape}")

    # 3) Subject_ID_N uniqueness
    if "Subject_ID_N" not in master.columns:
        raise RuntimeError("Subject_ID_N missing from master_cognitive_wide.csv")
    sid_n = master["Subject_ID_N"].astype(str).str.strip()
    dup_mask = sid_n.duplicated(keep=False)
    dup_count = int(dup_mask.sum())
    is_unique = dup_count == 0

    # 4) Subject_ID_D string and leading-zero examples
    if "Subject_ID_D" not in master.columns:
        print("Warning: Subject_ID_D missing from master.")
        sid_d = pd.Series([], dtype="string")
    else:
        sid_d = master["Subject_ID_D"].astype("string")

    non_null_d = sid_d.dropna().astype(str)
    leading_zero_examples = non_null_d[non_null_d.str.match(r"^0+\d+")].head(5).tolist()
    general_examples = non_null_d.head(10).tolist()

    print("\nSubject ID checks:")
    print(f"Subject_ID_N unique: {is_unique}")
    print(f"Duplicated Subject_ID_N rows: {dup_count}")
    print(f"Subject_ID_D dtype after load/coerce: {sid_d.dtype}")
    print(f"Subject_ID_D examples: {general_examples}")
    print(f"Subject_ID_D leading-zero examples: {leading_zero_examples}")

    # 5) print columns grouped by prefix
    groups = group_columns(list(master.columns))
    print("\nColumns grouped by prefix:")
    for gname, cols in groups.items():
        print(f"{gname} ({len(cols)}):")
        print(cols)

    # Cognitive columns (all prefixed)
    cognitive_cols: List[str] = []
    for p in PREFIXES:
        cognitive_cols.extend(groups[p])

    # 6) per-column stats
    rows = []
    n_rows = len(master)
    for c in master.columns:
        s = master[c]
        missing_mask = s.isna() | (s.astype(str).str.strip() == "")
        missing_count = int(missing_mask.sum())
        non_missing_count = int(n_rows - missing_count)
        missing_pct = (missing_count / n_rows * 100.0) if n_rows else 0.0

        num = to_numeric_series(s)
        numeric_non_missing = int(num.notna().sum())
        if numeric_non_missing > 0:
            c_min = float(num.min())
            c_mean = float(num.mean())
            c_max = float(num.max())
        else:
            c_min = None
            c_mean = None
            c_max = None

        rows.append(
            {
                "column": c,
                "non_missing_count": non_missing_count,
                "missing_count": missing_count,
                "missing_percent": round(missing_pct, 4),
                "numeric_non_missing_count": numeric_non_missing,
                "numeric_min": c_min,
                "numeric_mean": c_mean,
                "numeric_max": c_max,
            }
        )

    missingness_df = pd.DataFrame(rows)

    # 7) compact missingness report
    miss_out = in_dir / "qc_missingness_report.csv"
    missingness_df.to_csv(miss_out, index=False)

    # 8) subject-level completeness
    if cognitive_cols:
        cog_df = master[cognitive_cols]
        cog_missing = cog_df.isna() | (cog_df.astype(str).apply(lambda col: col.str.strip()) == "")
        missing_cog = cog_missing.sum(axis=1)
        non_missing_cog = len(cognitive_cols) - missing_cog
        pct_complete = (non_missing_cog / len(cognitive_cols) * 100.0).round(4)
    else:
        missing_cog = pd.Series([0] * len(master))
        non_missing_cog = pd.Series([0] * len(master))
        pct_complete = pd.Series([0.0] * len(master))

    sub_comp = pd.DataFrame(
        {
            "Subject_ID_N": master["Subject_ID_N"],
            "Subject_ID_D": master["Subject_ID_D"] if "Subject_ID_D" in master.columns else "",
            "non_missing_cognitive_columns": non_missing_cog,
            "missing_cognitive_columns": missing_cog,
            "percent_complete": pct_complete,
        }
    )
    comp_out = in_dir / "qc_subject_completeness.csv"
    sub_comp.to_csv(comp_out, index=False)

    # 9) special code summaries
    summaries = []
    if not flags.empty:
        code_col = "raw_value" if "raw_value" in flags.columns else None
        if code_col:
            flags = flags.copy()
            flags[code_col] = flags[code_col].astype(str).str.strip().str.upper()
            flags = flags[flags[code_col].isin(SPECIAL_CODES)].copy()
            by_code = flags.groupby(code_col).size().reset_index(name="count")
            by_code["summary_type"] = "by_code"
            by_code = by_code.rename(columns={code_col: "key"})
            summaries.append(by_code[["summary_type", "key", "count"]])

        if "source_sheet" in flags.columns:
            by_sheet = flags.groupby("source_sheet").size().reset_index(name="count")
            by_sheet["summary_type"] = "by_source_sheet"
            by_sheet = by_sheet.rename(columns={"source_sheet": "key"})
            summaries.append(by_sheet[["summary_type", "key", "count"]])

        if "source_column" in flags.columns:
            by_col = flags.groupby("source_column").size().reset_index(name="count")
            by_col["summary_type"] = "by_source_column"
            by_col = by_col.rename(columns={"source_column": "key"})
            summaries.append(by_col[["summary_type", "key", "count"]])

    if summaries:
        flag_summary = pd.concat(summaries, ignore_index=True)
    else:
        flag_summary = pd.DataFrame(columns=["summary_type", "key", "count"])

    flag_out = in_dir / "qc_special_code_summary.csv"
    flag_summary.to_csv(flag_out, index=False)

    # suspicious subject rows
    sid_n_missing = master["Subject_ID_N"].isna() | (master["Subject_ID_N"].astype(str).str.strip() == "")
    sid_d_missing = ("Subject_ID_D" not in master.columns)
    if "Subject_ID_D" in master.columns:
        sid_d_str = master["Subject_ID_D"].astype("string")
        sid_d_missing_mask = sid_d_str.isna() | (sid_d_str.astype(str).str.strip() == "")
        sid_d_dash_mask = sid_d_str.astype(str).str.strip().eq("-")
        sid_d_non_normal = ~sid_d_str.astype(str).str.match(r"^\d{1,4}$", na=False)
    else:
        sid_d_missing_mask = pd.Series([True] * len(master))
        sid_d_dash_mask = pd.Series([False] * len(master))
        sid_d_non_normal = pd.Series([True] * len(master))

    if cognitive_cols:
        almost_all_missing_mask = sub_comp["percent_complete"] <= 10
    else:
        almost_all_missing_mask = pd.Series([False] * len(master))

    suspicious_mask = sid_n_missing | sid_d_missing_mask | sid_d_dash_mask | sid_d_non_normal | almost_all_missing_mask
    suspicious = master[suspicious_mask].copy()
    if len(suspicious) > 0:
        suspicious = suspicious.copy()
        suspicious["reason_sid_n_missing"] = sid_n_missing[suspicious_mask].values
        suspicious["reason_sid_d_missing"] = sid_d_missing_mask[suspicious_mask].values
        suspicious["reason_sid_d_dash"] = sid_d_dash_mask[suspicious_mask].values
        suspicious["reason_sid_d_non_normal"] = sid_d_non_normal[suspicious_mask].values
        suspicious["reason_almost_all_cognitive_missing"] = almost_all_missing_mask[suspicious_mask].values
    suspicious_out = in_dir / "qc_suspicious_subject_rows.csv"
    suspicious.to_csv(suspicious_out, index=False)

    # 10) delta report empty?
    delta_mismatch_count = int(len(delta))
    delta_ok = delta_mismatch_count == 0

    # 11) final QC summary
    cols_over_50_missing = missingness_df.loc[missingness_df["missing_percent"] > 50, "column"].tolist()
    subj_under_50_complete = int((sub_comp["percent_complete"] < 50).sum()) if len(sub_comp) else 0

    total_flags = int(len(flags))
    flags_by_code = {}
    if "raw_value" in flags.columns and not flags.empty:
        _codes = flags["raw_value"].astype(str).str.strip().str.upper()
        _codes = _codes[_codes.isin(SPECIAL_CODES)]
        flags_by_code = _codes.value_counts(dropna=False).to_dict()

    print("\nFinal QC summary:")
    print(f"number_of_subjects={len(master)}")
    print(f"subject_id_n_unique={is_unique}")
    print(f"duplicated_subject_id_n_rows={dup_count}")
    print(f"total_cognitive_columns={len(cognitive_cols)}")
    print(f"columns_over_50pct_missing_count={len(cols_over_50_missing)}")
    print(f"columns_over_50pct_missing={cols_over_50_missing}")
    print(f"subjects_below_50pct_completeness={subj_under_50_complete}")
    print(f"special_code_flag_total={total_flags}")
    print(f"special_code_counts={flags_by_code}")
    print(f"delta_mismatch_count={delta_mismatch_count}")
    print(f"delta_report_ok={delta_ok}")
    print(f"suspicious_subject_rows_count={len(suspicious)}")

    if len(suspicious) > 0:
        print("\nSuspicious subject rows preview:")
        cols_preview = [c for c in ["Subject_ID_N", "Subject_ID_D", "reason_sid_n_missing", "reason_sid_d_missing", "reason_sid_d_dash", "reason_sid_d_non_normal", "reason_almost_all_cognitive_missing"] if c in suspicious.columns]
        print(suspicious[cols_preview].head(20).to_string(index=False))

    print("\nGenerated QC files:")
    print(miss_out)
    print(comp_out)
    print(flag_out)
    print(suspicious_out)


if __name__ == "__main__":
    main()
