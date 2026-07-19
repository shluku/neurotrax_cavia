from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
SHARED_DIR = ROOT / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"Subject_ID_D": str})


def main() -> None:
    parser = argparse.ArgumentParser(description="Append one Phase 3 table-run output into shared all-T1 outputs.")
    parser.add_argument("table_name")
    args = parser.parse_args()

    table = args.table_name
    table_dir = SHARED_DIR / "table_runs" / table
    paths = {
        "long": SHARED_DIR / "phase2_all_t1_selected_features_long.csv",
        "wide": SHARED_DIR / "phase2_all_t1_selected_features_wide.csv",
        "coverage": SHARED_DIR / "phase2_all_t1_selected_features_coverage.csv",
        "status": SHARED_DIR / "phase2_all_t1_selected_features_patient_table_status.csv",
        "table_long": table_dir / f"phase2_all_t1_selected_features_long_{table}.csv",
        "table_wide": table_dir / f"phase2_all_t1_selected_features_wide_{table}.csv",
        "table_coverage": table_dir / f"phase2_all_t1_selected_features_coverage_{table}.csv",
        "table_status": table_dir / f"phase2_all_t1_selected_features_patient_table_status_{table}.csv",
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise SystemExit("missing files:\n" + "\n".join(missing))

    shared_long = read_csv(paths["long"])
    table_long = read_csv(paths["table_long"])
    shared_status = read_csv(paths["status"])
    table_status = read_csv(paths["table_status"])
    shared_coverage = read_csv(paths["coverage"])
    table_coverage = read_csv(paths["table_coverage"])
    shared_wide = read_csv(paths["wide"])
    table_wide = read_csv(paths["table_wide"])

    shared_long = shared_long[shared_long["table_name"].astype(str) != table].copy()
    combined_long = pd.concat([shared_long, table_long], ignore_index=True)

    shared_status = shared_status[shared_status["table_name"].astype(str) != table].copy()
    combined_status = pd.concat([shared_status, table_status], ignore_index=True)

    if "table_name" in shared_coverage.columns:
        shared_coverage = shared_coverage[shared_coverage["table_name"].astype(str) != table].copy()
    combined_coverage = pd.concat([shared_coverage, table_coverage], ignore_index=True, sort=False)

    table_feature_cols = [
        col
        for col in table_long["feature_name"].dropna().astype(str).unique().tolist()
        if col in table_wide.columns
    ]
    if not table_feature_cols:
        raise SystemExit(f"no table feature columns found for {table}")
    existing_feature_cols = [col for col in table_feature_cols if col in shared_wide.columns]
    shared_wide_for_merge = shared_wide.drop(columns=existing_feature_cols, errors="ignore")
    combined_wide = shared_wide_for_merge.merge(
        table_wide[["Subject_ID_D", *table_feature_cols]],
        on="Subject_ID_D",
        how="left",
    )

    combined_long.to_csv(paths["long"], index=False)
    combined_status.to_csv(paths["status"], index=False)
    combined_coverage.to_csv(paths["coverage"], index=False)
    combined_wide.to_csv(paths["wide"], index=False)

    print(f"merged_table: {table}")
    print(f"long_shape: {combined_long.shape}")
    print(f"status_shape: {combined_status.shape}")
    print(f"coverage_shape: {combined_coverage.shape}")
    print(f"wide_shape: {combined_wide.shape}")
    print("merged_wide_columns:")
    for col in table_feature_cols:
        print(f"- {col}")
    if existing_feature_cols:
        print("updated_existing_wide_columns:")
        for col in existing_feature_cols:
            print(f"- {col}")


if __name__ == "__main__":
    main()
