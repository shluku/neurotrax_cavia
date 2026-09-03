"""Build patient-level ACC summaries and a model-readiness audit from pilot outputs.

This script is deliberately SQL-free. It operates on the saved plugin-anchored
ACC pilot tables so the audit can be rerun after later extraction batches without
changing the raw-data extraction logic or existing patient-level cohorts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).parent
PILOT_DIR = ROOT / "output/analysis_candidates/accelerometer_plugin_event_day_pilot"
OUT_DIR = ROOT / "output/analysis_candidates/accelerometer_feature_audit"

CATALOG_PATH = PILOT_DIR / "accelerometer_plugin_event_day_feature_catalog.csv"
CANDIDATES_PATH = PILOT_DIR / "accelerometer_plugin_event_day_candidates.csv"
WIDE_PATH = PILOT_DIR / "accelerometer_plugin_event_day_features_wide.csv"
PATIENT_DAY_PATH = PILOT_DIR / "accelerometer_plugin_event_day_patient_day_features.csv"
RUN_SUMMARY_PATH = PILOT_DIR / "accelerometer_plugin_event_day_run_summary.csv"

PATIENT_DAY_AUGMENTED_PATH = OUT_DIR / "accelerometer_patient_day_features_audited.csv"
PATIENT_LEVEL_PATH = OUT_DIR / "accelerometer_patient_level_features.csv"
FEATURE_AUDIT_PATH = OUT_DIR / "accelerometer_feature_audit.csv"
TECHNICAL_PATH = OUT_DIR / "accelerometer_feature_technical_correlations.csv"
GROUP_SUMMARY_PATH = OUT_DIR / "accelerometer_feature_group_summary.csv"
SUMMARY_PATH = OUT_DIR / "accelerometer_feature_audit_summary.csv"
README_PATH = OUT_DIR / "README_accelerometer_feature_audit.md"

TECHNICAL_VARIABLES = [
    "accelerometer_raw_row_count",
    "accelerometer_valid_signal_minutes",
    "accelerometer_calendar_coverage_fraction",
    "accelerometer_observed_span_hours",
]


def numeric_column(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[name], errors="coerce")


def feature_role(feature_group: str) -> tuple[str, str]:
    if feature_group == "quality":
        return (
            "qc_only",
            "Use to audit collection intensity, missingness, sampling, and fragmentation; exclude from the primary behavior panel.",
        )
    if feature_group == "signal_level":
        return (
            "sensitivity_only",
            "Review as a sensitivity feature because gravity, phone orientation, and phone placement can affect the signal.",
        )
    return (
        "primary_behavior_candidate",
        "Candidate behavioral feature after coverage and technical-confounding review; this is not a final selection.",
    )


def transform_recommendation(feature_name: str, role: str) -> str:
    if role == "qc_only":
        return "Retain for QC; do not use as a primary behavioral predictor."
    if feature_name.endswith("_count") or feature_name.endswith("_minutes"):
        return "Consider per-observed-hour normalization; fit robust scaling inside each training fold."
    if "fraction" in feature_name or "ratio" in feature_name or "entropy" in feature_name:
        return "Inspect bounds and skew; fit scaling inside each training fold."
    return "Inspect skew and outliers; fit robust scaling inside each training fold."


def safe_correlations(x: pd.Series, y: pd.Series) -> tuple[float, float, int]:
    paired = pd.DataFrame({"x": x, "y": y}).apply(pd.to_numeric, errors="coerce").dropna()
    if len(paired) < 3 or paired["x"].nunique() < 2 or paired["y"].nunique() < 2:
        return float("nan"), float("nan"), len(paired)
    return float(paired["x"].corr(paired["y"])), float(paired["x"].corr(paired["y"], method="spearman")), len(paired)


def summarize_distribution(values: pd.Series) -> dict[str, float | int]:
    values = pd.to_numeric(values, errors="coerce").dropna()
    if values.empty:
        return {
            "observed_count": 0,
            "mean": np.nan,
            "sd": np.nan,
            "median": np.nan,
            "q1": np.nan,
            "q3": np.nan,
            "iqr": np.nan,
            "minimum": np.nan,
            "maximum": np.nan,
        }
    q1, q3 = values.quantile([0.25, 0.75])
    return {
        "observed_count": int(values.size),
        "mean": float(values.mean()),
        "sd": float(values.std(ddof=1)) if len(values) > 1 else np.nan,
        "median": float(values.median()),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(q3 - q1),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
    }


def add_observed_time_normalized_features(patient_days: pd.DataFrame, feature_names: list[str]) -> tuple[pd.DataFrame, list[str]]:
    frame = patient_days.copy()
    valid_minutes = numeric_column(frame, "accelerometer_valid_signal_minutes")
    observed_hours = valid_minutes / 60.0
    frame["accelerometer_observed_hours"] = observed_hours

    normalized_names: list[str] = []
    for feature_name in feature_names:
        if not (feature_name.endswith("_count") or feature_name.endswith("_minutes")):
            continue
        if feature_name.startswith("accelerometer_raw_") or feature_name.startswith("accelerometer_valid_"):
            continue
        values = numeric_column(frame, feature_name)
        normalized_name = f"{feature_name}_per_observed_hour"
        frame[normalized_name] = values.div(observed_hours.where(observed_hours > 0))
        normalized_names.append(normalized_name)
    return frame, normalized_names


def build_patient_level_table(
    candidates: pd.DataFrame,
    patient_days: pd.DataFrame,
    feature_names: list[str],
    normalized_names: list[str],
) -> pd.DataFrame:
    candidate_patients = sorted(candidates["patient_id"].astype(str).unique().tolist()) if not candidates.empty else []
    all_feature_names = feature_names + normalized_names
    rows: list[dict[str, object]] = []
    for patient_id in candidate_patients:
        group = patient_days[patient_days["patient_id"].astype(str).eq(patient_id)].copy()
        row: dict[str, object] = {
            "patient_id": patient_id,
            "candidate_device_day_count": int(candidates["patient_id"].astype(str).eq(patient_id).sum()),
            "completed_patient_day_count": int(len(group)),
            "completed_device_day_count": int(numeric_column(group, "source_device_day_count").sum()) if not group.empty else 0,
            "total_valid_signal_minutes": int(numeric_column(group, "accelerometer_valid_signal_minutes").sum()) if not group.empty else 0,
            "median_daily_coverage_fraction": float(numeric_column(group, "accelerometer_calendar_coverage_fraction").median()) if not group.empty else np.nan,
            "mean_daily_coverage_fraction": float(numeric_column(group, "accelerometer_calendar_coverage_fraction").mean()) if not group.empty else np.nan,
            "aggregation_rule": "median across completed patient-local days",
        }
        for feature_name in all_feature_names:
            values = numeric_column(group, feature_name)
            row[f"acc_median_{feature_name}"] = float(values.median()) if values.notna().any() else np.nan
            row[f"acc_mean_{feature_name}"] = float(values.mean()) if values.notna().any() else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def build_audit_tables(
    catalog: pd.DataFrame,
    patient_days: pd.DataFrame,
    patient_level: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    feature_names = catalog["feature_name"].astype(str).tolist()
    audit_rows: list[dict[str, object]] = []
    technical_rows: list[dict[str, object]] = []
    for catalog_row in catalog.to_dict("records"):
        feature_name = str(catalog_row["feature_name"])
        group = str(catalog_row.get("feature_group", ""))
        role, role_reason = feature_role(group)
        values = numeric_column(patient_days, feature_name)
        distribution = summarize_distribution(values)
        patient_column = f"acc_median_{feature_name}"
        patient_values = numeric_column(patient_level, patient_column)
        patient_observed = int(patient_values.notna().sum())
        technical_associations: list[tuple[str, float]] = []
        for technical_name in TECHNICAL_VARIABLES:
            feature_series = values
            technical_series = numeric_column(patient_days, technical_name)
            if feature_name == technical_name:
                pearson, spearman, pairwise_n = np.nan, np.nan, 0
            else:
                pearson, spearman, pairwise_n = safe_correlations(feature_series, technical_series)
            technical_rows.append(
                {
                    "feature_name": feature_name,
                    "feature_group": group,
                    "feature_role": role,
                    "technical_variable": technical_name,
                    "pairwise_n": pairwise_n,
                    "pearson_correlation": pearson,
                    "spearman_correlation": spearman,
                    "pilot_flag_threshold": 0.70,
                    "technical_confounding_flag": "review" if pairwise_n >= 5 and abs(spearman) >= 0.70 else (
                        "insufficient_pilot_n" if pairwise_n < 5 else "not_flagged"
                    ),
                }
            )
            if pd.notna(spearman):
                technical_associations.append((technical_name, abs(float(spearman))))
        if technical_associations:
            strongest_technical = max(technical_associations, key=lambda item: item[1])[0]
            strongest_abs_corr = max(item[1] for item in technical_associations)
        else:
            strongest_technical = ""
            strongest_abs_corr = np.nan
        audit_rows.append(
            {
                **catalog_row,
                "feature_role": role,
                "role_reason": role_reason,
                "recommended_transform": transform_recommendation(feature_name, role),
                "recommended_patient_aggregation": "median across completed patient-local days",
                "patient_day_count_total": len(patient_days),
                "patient_day_observed_count": distribution["observed_count"],
                "patient_day_missingness_percent": 100.0 * (1 - distribution["observed_count"] / len(patient_days)) if len(patient_days) else np.nan,
                "patient_count_total": len(patient_level),
                "patient_observed_count": patient_observed,
                "patient_level_missingness_percent": 100.0 * (1 - patient_observed / len(patient_level)) if len(patient_level) else np.nan,
                "mean": distribution["mean"],
                "sd": distribution["sd"],
                "median": distribution["median"],
                "q1": distribution["q1"],
                "q3": distribution["q3"],
                "iqr": distribution["iqr"],
                "minimum": distribution["minimum"],
                "maximum": distribution["maximum"],
                "strongest_technical_variable": strongest_technical,
                "strongest_abs_spearman_correlation": strongest_abs_corr,
                "technical_review_status": "review" if pd.notna(strongest_abs_corr) and strongest_abs_corr >= 0.70 and distribution["observed_count"] >= 5 else (
                    "insufficient_pilot_n" if distribution["observed_count"] < 5 else "not_flagged"
                ),
                "pilot_selection_allowed": "no",
            }
        )
    audit = pd.DataFrame(audit_rows)
    technical = pd.DataFrame(technical_rows)
    group_summary = (
        audit.groupby(["feature_group", "feature_role"], dropna=False)
        .agg(
            feature_count=("feature_name", "size"),
            mean_patient_day_coverage_percent=("patient_day_observed_count", lambda values: 100.0 * values.mean() / len(patient_days) if len(patient_days) else np.nan),
            mean_patient_level_coverage_percent=("patient_observed_count", lambda values: 100.0 * values.mean() / len(patient_level) if len(patient_level) else np.nan),
            technical_review_feature_count=("technical_review_status", lambda values: int(values.eq("review").sum())),
        )
        .reset_index()
    )
    return audit, technical, group_summary


def write_readme(summary: dict[str, object], audit: pd.DataFrame, readme_path: Path) -> None:
    primary_count = int(audit["feature_role"].eq("primary_behavior_candidate").sum()) if not audit.empty else 0
    sensitivity_count = int(audit["feature_role"].eq("sensitivity_only").sum()) if not audit.empty else 0
    quality_count = int(audit["feature_role"].eq("qc_only").sum()) if not audit.empty else 0
    readme_path.write_text(
        f"""# Accelerometer Feature Audit and Patient-Level Aggregation

This is a SQL-free audit of the saved plugin-anchored general-accelerometer pilot. It does not overwrite the raw ACC pilot outputs or any existing patient-level cohort.

## Current scope

- Source patients: `{summary['pilot_patients']}`.
- Candidate device-days: `{summary['candidate_device_days']}`.
- Completed patient-local days: `{summary['completed_patient_days']}`.
- Completed device-day feature rows: `{summary['completed_device_days']}`.
- Feature definitions audited: `{summary['feature_count']}`.
- Patient-level aggregation: median across completed patient-local days.

The patient-level table is a model-ready shape, but it is not yet suitable for model fitting while extraction coverage remains incomplete.

## Feature roles

- `{primary_count}` primary behavioral candidates: dynamic motion, temporal pattern, circadian pattern, and rapid signal-change features.
- `{sensitivity_count}` sensitivity-only signal-level features: vector magnitude summaries can be affected by gravity, phone orientation, and placement.
- `{quality_count}` QC-only features: raw/valid counts, coverage, duration, sampling intervals, gap burden, and duplicate counts. These describe collection quality and are excluded from the primary behavioral panel.

Count and minute features also receive per-observed-hour versions. These are intended to reduce recording-intensity effects, but their usefulness must be checked on the larger cohort.

## Technical-confounding audit

Each feature is compared with raw row count, valid signal minutes, calendar coverage, and observed span. Correlations are descriptive only. A large absolute Spearman correlation is marked `review`; it does not prove confounding. No p-values are reported from this exploratory extraction.

## Model handoff protocol

After extraction is available for the intended patient cohort, repeat the audit and then compare the following on exactly the same patients and validation folds:

1. Fold-local mean baseline.
2. Existing digital phenotype model.
3. ACC behavioral candidates alone.
4. Existing features plus ACC behavioral candidates.
5. Coverage-normalized sensitivity model.

Median imputation, missingness indicators, scaling, feature selection, and Ridge alpha selection must be fit inside each training fold. The two-patient pilot must not be used to choose final features or to claim predictive evidence.
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit saved ACC pilot features and build patient-level tables.")
    parser.add_argument("--pilot-dir", type=Path, default=PILOT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    pilot_dir = args.pilot_dir
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    catalog = pd.read_csv(pilot_dir / CATALOG_PATH.name, dtype=str)
    candidates = pd.read_csv(pilot_dir / CANDIDATES_PATH.name, dtype=str)
    wide_path = pilot_dir / WIDE_PATH.name
    patient_day_path = pilot_dir / PATIENT_DAY_PATH.name
    run_summary_path = pilot_dir / RUN_SUMMARY_PATH.name
    wide = pd.read_csv(wide_path, dtype=str) if wide_path.exists() else pd.DataFrame()
    if patient_day_path.exists():
        patient_days = pd.read_csv(patient_day_path, dtype=str)
    else:
        patient_days = wide.copy()
    feature_names = catalog["feature_name"].astype(str).tolist()
    patient_days, normalized_names = add_observed_time_normalized_features(patient_days, feature_names)
    patient_level = build_patient_level_table(candidates, patient_days, feature_names, normalized_names)
    audit, technical, group_summary = build_audit_tables(catalog, patient_days, patient_level)

    summary_lookup = {}
    if run_summary_path.exists():
        run_summary = pd.read_csv(run_summary_path, dtype=str)
        summary_lookup = dict(zip(run_summary["metric"], run_summary["value"]))
    summary = {
        "pilot_patients": int(candidates["patient_id"].nunique()) if not candidates.empty else 0,
        "candidate_device_days": len(candidates),
        "completed_patient_days": len(patient_days),
        "completed_device_days": len(wide),
        "feature_count": len(feature_names),
        "primary_behavioral_candidate_count": int(audit["feature_role"].eq("primary_behavior_candidate").sum()),
        "sensitivity_feature_count": int(audit["feature_role"].eq("sensitivity_only").sum()),
        "quality_qc_feature_count": int(audit["feature_role"].eq("qc_only").sum()),
        "patient_level_rows": len(patient_level),
        "pilot_selection_allowed": "no",
        "model_comparison_status": "deferred_until_larger_patient_cohort",
        "pilot_run_pending_device_days": summary_lookup.get("pending_device_days", ""),
    }

    patient_days.to_csv(out_dir / PATIENT_DAY_AUGMENTED_PATH.name, index=False)
    patient_level.to_csv(out_dir / PATIENT_LEVEL_PATH.name, index=False)
    audit.to_csv(out_dir / FEATURE_AUDIT_PATH.name, index=False)
    technical.to_csv(out_dir / TECHNICAL_PATH.name, index=False)
    group_summary.to_csv(out_dir / GROUP_SUMMARY_PATH.name, index=False)
    pd.DataFrame([{"metric": key, "value": value} for key, value in summary.items()]).to_csv(out_dir / SUMMARY_PATH.name, index=False)
    write_readme(summary, audit, out_dir / README_PATH.name)
    print("accelerometer_feature_audit_complete", flush=True)
    print(f"patient_level_rows: {len(patient_level)}", flush=True)
    print(f"feature_count: {len(feature_names)}", flush=True)
    print(f"primary_behavior_candidates: {summary['primary_behavioral_candidate_count']}", flush=True)
    print(f"output_directory: {out_dir}", flush=True)


if __name__ == "__main__":
    main()
