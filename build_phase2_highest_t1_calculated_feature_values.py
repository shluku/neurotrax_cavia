from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError


ROOT = Path(__file__).parent
SELECTED_FEATURES_PATH = ROOT / "phase2_selected_features.csv"
OUT_PATH = ROOT / "phase2_highest_t1_calculated_feature_values.csv"
EXPLORATORY_T1_WEEK_24H_DIR = (
    ROOT / "output/analysis_candidates/phase2_feature_extraction/exploratory_t1_week_24h"
)
ADJUSTED_FIRST_AVAILABLE_7D_DIR = (
    ROOT / "output/analysis_candidates/phase2_feature_extraction/adjusted_first_available_7d"
)


def is_calculated_number(value) -> bool:
    if pd.isna(value) or str(value).strip() == "":
        return False
    return pd.notna(pd.to_numeric(value, errors="coerce"))


def main() -> None:
    rows = []

    # Exploratory protocol-valid layer: when no specific patient is requested,
    # use the highest-T1-ranked patient who has a valid 24h span inside the T1
    # week for that table. This supports table exploration without replacing
    # missing values for a specifically requested patient.
    if EXPLORATORY_T1_WEEK_24H_DIR.exists():
        exploratory_paths = sorted(
            EXPLORATORY_T1_WEEK_24H_DIR.glob("phase2_exploratory_t1_week_24h_selected_features_*.csv")
        )
        combined_path = EXPLORATORY_T1_WEEK_24H_DIR / "phase2_exploratory_t1_week_24h_selected_features.csv"
        if combined_path.exists():
            exploratory_paths.append(combined_path)
        for exploratory_path in exploratory_paths:
            try:
                exploratory = pd.read_csv(exploratory_path, dtype=str)
            except EmptyDataError:
                continue
            if exploratory.empty:
                continue
            for _, feature_row in exploratory.iterrows():
                value = feature_row.get("feature_value")
                rows.append(
                    {
                        "table_name": feature_row.get("table_name", ""),
                        "feature_name": feature_row.get("feature_name", ""),
                        "feature_value": pd.to_numeric(value, errors="coerce") if is_calculated_number(value) else pd.NA,
                        "calculation_context": feature_row.get(
                            "calculation_context", "exploratory_t1_ranked_first_valid_24h_in_T1_week"
                        ),
                        "Subject_ID_D": feature_row.get("Subject_ID_D", ""),
                        "Subject_ID_N": feature_row.get("Subject_ID_N", ""),
                        "device_id_used": feature_row.get("device_id_used", ""),
                        "global_T1": feature_row.get("global_T1", ""),
                        "T1_date_iso": feature_row.get("T1_date_iso", ""),
                        "window_rule": feature_row.get("window_rule", ""),
                        "window_start_local": feature_row.get("window_start_local", ""),
                        "window_end_local": feature_row.get("window_end_local", ""),
                        "feature_status": feature_row.get("feature_status", "calculated"),
                        "source_file": str(exploratory_path.relative_to(ROOT)),
                    }
                )

    # Table-specific adjusted layer. These rows are intentionally separate
    # from the standard T1-week protocol and carry their own calculation_context.
    if ADJUSTED_FIRST_AVAILABLE_7D_DIR.exists():
        adjusted_paths = sorted(
            ADJUSTED_FIRST_AVAILABLE_7D_DIR.glob("phase2_adjusted_first_available_7d_selected_features_*.csv")
        )
        for adjusted_path in adjusted_paths:
            try:
                adjusted = pd.read_csv(adjusted_path, dtype=str)
            except EmptyDataError:
                continue
            if adjusted.empty:
                continue
            for _, feature_row in adjusted.iterrows():
                value = feature_row.get("feature_value")
                rows.append(
                    {
                        "table_name": feature_row.get("table_name", ""),
                        "feature_name": feature_row.get("feature_name", ""),
                        "feature_value": pd.to_numeric(value, errors="coerce") if is_calculated_number(value) else pd.NA,
                        "calculation_context": feature_row.get("calculation_context", "adjusted_first_available_7d"),
                        "Subject_ID_D": feature_row.get("Subject_ID_D", ""),
                        "Subject_ID_N": feature_row.get("Subject_ID_N", ""),
                        "device_id_used": feature_row.get("device_id_used", ""),
                        "global_T1": feature_row.get("global_T1", ""),
                        "T1_date_iso": feature_row.get("T1_date_iso", ""),
                        "window_rule": feature_row.get("window_rule", ""),
                        "window_start_local": feature_row.get("window_start_local", ""),
                        "window_end_local": feature_row.get("window_end_local", ""),
                        "feature_status": feature_row.get("feature_status", "calculated"),
                        "source_file": str(adjusted_path.relative_to(ROOT)),
                    }
                )

    out = pd.DataFrame(
        rows,
        columns=[
            "table_name",
            "feature_name",
            "feature_value",
            "calculation_context",
            "Subject_ID_D",
            "Subject_ID_N",
            "device_id_used",
            "global_T1",
            "T1_date_iso",
            "window_rule",
            "window_start_local",
            "window_end_local",
            "feature_status",
            "source_file",
        ],
    )
    out = out.fillna("")
    out.to_csv(OUT_PATH, index=False)
    print(f"exploratory_feature_rows: {len(out)}")
    print(OUT_PATH)
    if not out.empty:
        print(out.to_string(index=False))


if __name__ == "__main__":
    main()
