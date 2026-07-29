"""Compare Phase 7 10-day feature outputs with the prior 24-hour outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
SELECTED_PATH = ROOT / "phase2_selected_features.csv"
OUT_DIR = ROOT / "output/analysis_candidates/phase7_10day_window/comparison"

WIDE_PATHS = {
    "T1": {
        "24h": ROOT / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/phase2_all_t1_selected_features_wide.csv",
        "10d": ROOT / "output/analysis_candidates/phase7_10day_window/t1/phase7_t1_10day_features_wide.csv",
    },
    "T2": {
        "24h": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_selected_features_wide.csv",
        "10d": ROOT / "output/analysis_candidates/phase7_10day_window/t2/phase7_t2_10day_features_wide.csv",
    },
}
STATUS_PATHS = {
    "T1": {
        "24h": ROOT / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/phase2_all_t1_selected_features_patient_table_status.csv",
        "10d": ROOT / "output/analysis_candidates/phase7_10day_window/t1/phase7_t1_10day_patient_table_status.csv",
    },
    "T2": {
        "24h": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_selected_features_patient_table_status.csv",
        "10d": ROOT / "output/analysis_candidates/phase7_10day_window/t2/phase7_t2_10day_patient_table_status.csv",
    },
}


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str) if path.exists() else pd.DataFrame()


def clean_values(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.replace({"": pd.NA, "None": pd.NA, "nan": pd.NA, "<NA>": pd.NA})


def compare_wide(endpoint: str, selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    old = read(WIDE_PATHS[endpoint]["24h"])
    new = read(WIDE_PATHS[endpoint]["10d"])
    if old.empty or new.empty:
        return pd.DataFrame(), pd.DataFrame()
    features = [feature for feature in selected["feature_name"].dropna().unique() if feature in old.columns and feature in new.columns]
    old = clean_values(old.set_index("Subject_ID_D"))
    new = clean_values(new.set_index("Subject_ID_D"))
    patients = sorted(set(old.index) & set(new.index))
    old, new = old.reindex(patients), new.reindex(patients)
    rows = []
    for feature in features:
        old_n = int(old[feature].notna().sum())
        new_n = int(new[feature].notna().sum())
        source = selected.loc[selected["feature_name"].eq(feature), "source_table"].iloc[0]
        rows.append(
            {
                "endpoint": endpoint,
                "feature_name": feature,
                "source_table": source,
                "patients_compared": len(patients),
                "available_24h": old_n,
                "available_10d": new_n,
                "coverage_24h_percent": round(100 * old_n / len(patients), 2) if patients else 0,
                "coverage_10d_percent": round(100 * new_n / len(patients), 2) if patients else 0,
                "coverage_change_percentage_points": round(100 * (new_n - old_n) / len(patients), 2) if patients else 0,
            }
        )
    feature_df = pd.DataFrame(rows).sort_values(["coverage_change_percentage_points", "feature_name"])
    old_count = old[features].notna().sum(axis=1)
    new_count = new[features].notna().sum(axis=1)
    patient_df = pd.DataFrame(
        {
            "endpoint": endpoint,
            "Subject_ID_D": patients,
            "features_available_24h": old_count.to_numpy(),
            "features_available_10d": new_count.to_numpy(),
        }
    )
    patient_df["feature_count_change"] = patient_df["features_available_10d"] - patient_df["features_available_24h"]
    return feature_df, patient_df


def compare_status(endpoint: str) -> pd.DataFrame:
    rows = []
    for table_window in ["24h", "10d"]:
        frame = read(STATUS_PATHS[endpoint][table_window])
        if frame.empty or "table_name" not in frame or "table_status" not in frame:
            continue
        summary = frame.groupby("table_name", dropna=False)["table_status"].value_counts().unstack(fill_value=0).reset_index()
        summary["window"] = table_window
        summary["endpoint"] = endpoint
        for column in ["calculated", "missing_no_pre_t2_window", "missing_no_availability_anchored_window", "error", "retryable_error"]:
            if column not in summary:
                summary[column] = 0
        summary["patient_table_attempts"] = summary[[column for column in summary.columns if column in {"calculated", "missing_no_pre_t2_window", "missing_no_availability_anchored_window", "error", "retryable_error"}]].sum(axis=1)
        rows.append(summary[["endpoint", "window", "table_name", "patient_table_attempts", "calculated", "missing_no_pre_t2_window", "missing_no_availability_anchored_window", "error", "retryable_error"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    selected = read(SELECTED_PATH)
    selected = selected[selected["source_table"].ne("light")].copy()
    feature_frames, patient_frames, status_frames = [], [], []
    for endpoint in ["T1", "T2"]:
        features, patients = compare_wide(endpoint, selected)
        if not features.empty:
            feature_frames.append(features)
        if not patients.empty:
            patient_frames.append(patients)
        status = compare_status(endpoint)
        if not status.empty:
            status_frames.append(status)
    feature_comparison = pd.concat(feature_frames, ignore_index=True)
    patient_comparison = pd.concat(patient_frames, ignore_index=True)
    status_comparison = pd.concat(status_frames, ignore_index=True)
    feature_comparison.to_csv(OUT_DIR / "phase7_feature_coverage_comparison_24h_vs_10d.csv", index=False)
    patient_comparison.to_csv(OUT_DIR / "phase7_patient_feature_count_comparison_24h_vs_10d.csv", index=False)
    status_comparison.to_csv(OUT_DIR / "phase7_table_coverage_comparison_24h_vs_10d.csv", index=False)
    lines = [
        "# Phase 7 Comparison: 24-Hour Versus 10-Day Windows",
        "",
        "This is a data-quality and coverage audit only. No models are run here.",
        "",
    ]
    for endpoint in ["T1", "T2"]:
        subset = feature_comparison[feature_comparison["endpoint"].eq(endpoint)]
        patients = patient_comparison[patient_comparison["endpoint"].eq(endpoint)]
        if subset.empty:
            continue
        mean_old = 100 - subset["coverage_24h_percent"].mean()
        mean_new = 100 - subset["coverage_10d_percent"].mean()
        lines.extend(
            [
                f"## {endpoint}",
                "",
                f"Common selected features compared: `{len(subset)}`.",
                f"Mean feature missingness: 24-hour `{mean_old:.1f}%`; 10-day `{mean_new:.1f}%`.",
                f"Mean change in available features per patient: `{patients['feature_count_change'].mean():.2f}`.",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            "A wider window can improve the number of observations used to calculate a feature without increasing the number of patients who have any data in that table. Table availability and feature-level missingness must therefore be reported separately.",
            "",
        ]
    )
    (OUT_DIR / "README_phase7_comparison_24h_vs_10d.md").write_text("\n".join(lines), encoding="utf-8")
    print("comparison_outputs:", OUT_DIR)
    print(feature_comparison.groupby("endpoint")["coverage_change_percentage_points"].agg(["count", "mean", "min", "max"]).to_string())


if __name__ == "__main__":
    main()
