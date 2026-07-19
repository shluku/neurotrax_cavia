from __future__ import annotations

from pathlib import Path

import pandas as pd

from main import connect_sensordata_db


ROOT = Path(__file__).parent
TZ = "Asia/Jerusalem"
TABLE_NAME = "significant"
COGNITIVE_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
GLOBAL_COVERAGE_PATH = ROOT / "output/analysis_candidates/phase2_feature_review/streamlit_global_patient_coverage_preview.csv"


def normalize_subject_id(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def ms_to_local_date(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.to_datetime(int(value), unit="ms", utc=True).tz_convert(TZ).strftime("%Y-%m-%d")


def table_aggregate() -> dict:
    conn = connect_sensordata_db()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                f"""
                SELECT
                    COUNT(*) AS n_rows,
                    COUNT(DISTINCT device_id) AS n_devices,
                    MIN(timestamp) AS first_ts,
                    MAX(timestamp) AS last_ts
                FROM `{TABLE_NAME}`
                """
            )
            row = cur.fetchone() or {}
        finally:
            cur.close()
    finally:
        conn.close()

    row["first_local_date"] = ms_to_local_date(row.get("first_ts"))
    row["last_local_date"] = ms_to_local_date(row.get("last_ts"))
    return row


def mapped_patient_timing() -> pd.DataFrame:
    coverage = pd.read_csv(GLOBAL_COVERAGE_PATH, dtype={"Subject_ID_D": str})
    coverage = coverage[coverage["table_name"].astype(str).eq(TABLE_NAME)].copy()
    coverage["Subject_ID_D"] = coverage["Subject_ID_D"].map(normalize_subject_id)
    coverage["first_row_date"] = pd.to_datetime(coverage["first row"], errors="coerce")
    coverage["last_row_date"] = pd.to_datetime(coverage["last row"], errors="coerce")

    cognitive = pd.read_csv(COGNITIVE_PATH, dtype=str)
    cognitive["Subject_ID_D"] = cognitive["Subject_ID_D"].map(normalize_subject_id)
    cognitive = cognitive[cognitive["Subject_ID_D"].astype(str).ne("")].copy()
    cognitive["T1_date"] = pd.to_datetime(cognitive["T1_date_iso"], errors="coerce")
    cognitive["T2_date"] = pd.to_datetime(cognitive["T2_date_iso"], errors="coerce")

    merged = coverage.merge(
        cognitive[["Subject_ID_D", "Subject_ID_N", "global_T1", "T1_date_iso", "T2_date_iso", "T1_date", "T2_date"]],
        on="Subject_ID_D",
        how="left",
    )
    merged["days_first_after_T1"] = (merged["first_row_date"] - merged["T1_date"]).dt.days
    merged["days_first_after_T2"] = (merged["first_row_date"] - merged["T2_date"]).dt.days
    merged["days_last_after_T2"] = (merged["last_row_date"] - merged["T2_date"]).dt.days

    def timing(row) -> str:
        first = row["first_row_date"]
        t1 = row["T1_date"]
        t2 = row["T2_date"]
        if pd.isna(first) or pd.isna(t1):
            return "missing_dates"
        if first < t1:
            return "starts_before_T1"
        if pd.notna(t2) and first <= t2:
            return "starts_between_T1_and_T2"
        if pd.notna(t2) and first > t2:
            return "starts_after_T2"
        return "starts_after_T1_no_T2"

    merged["timing_vs_neurotrax"] = merged.apply(timing, axis=1)
    return merged


def main() -> None:
    agg = table_aggregate()
    mapped = mapped_patient_timing()

    print("significant_table_sql_aggregate")
    print(f"rows: {agg.get('n_rows')}")
    print(f"distinct_devices: {agg.get('n_devices')}")
    print(f"first_timestamp_ms: {agg.get('first_ts')}")
    print(f"last_timestamp_ms: {agg.get('last_ts')}")
    print(f"first_local_date: {agg.get('first_local_date')}")
    print(f"last_local_date: {agg.get('last_local_date')}")

    print("\nmapped_patient_coverage_summary")
    print(f"mapped_subjects_with_rows: {mapped['Subject_ID_D'].nunique()}")
    print(f"mapped_rows_in_preview: {int(pd.to_numeric(mapped['rows'], errors='coerce').fillna(0).sum())}")
    print("timing_vs_neurotrax:")
    print(mapped["timing_vs_neurotrax"].value_counts(dropna=False).to_string())

    print("\nfirst_row_delay_from_T1_days")
    delays = pd.to_numeric(mapped["days_first_after_T1"], errors="coerce").dropna()
    if not delays.empty:
        print(f"min: {int(delays.min())}")
        print(f"median: {float(delays.median()):.1f}")
        print(f"max: {int(delays.max())}")
        print(f"subjects_starting_within_30d_after_T1: {int((delays <= 30).sum())}")
        print(f"subjects_starting_after_30d_from_T1: {int((delays > 30).sum())}")

    print("\ntop_mapped_subjects")
    view_cols = [
        "Subject_ID_D",
        "Subject_ID_N",
        "global_T1",
        "T1_date_iso",
        "T2_date_iso",
        "rows",
        "devices",
        "first row",
        "last row",
        "days_first_after_T1",
        "days_first_after_T2",
        "timing_vs_neurotrax",
    ]
    print(mapped[view_cols].head(25).to_string(index=False))


if __name__ == "__main__":
    main()
