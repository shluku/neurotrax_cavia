from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).parent

PATHS = {
    "protocol_summary": ROOT / "README_PROTOCOL_PROJECT_SUMMARY.md",
    "phase2_feature_protocol": ROOT / "PHASE2_FEATURE_ANALYSIS_PROTOCOL.md",
    "phase2_table_feature_reviews": ROOT / "phase2_table_feature_reviews",
    "phase2_output_feature_reviews": ROOT / "output/analysis_candidates/phase2_feature_review",
    "phase2_tracking": ROOT / "phase2_table_tracking.csv",
    "phase2_feature_plan": ROOT / "phase2_candidate_feature_plan.csv",
    "phase2_selected_features": ROOT / "phase2_selected_features.csv",
    "phase2_highest_t1_calculated_feature_values": ROOT / "phase2_highest_t1_calculated_feature_values.csv",
    "phase2_reviewed_tables_global_coverage_summary": ROOT
    / "output/analysis_candidates/phase2_feature_review/phase2_reviewed_tables_global_coverage_summary.csv",
    "global_patient_coverage_preview": ROOT
    / "output/analysis_candidates/phase2_feature_review/streamlit_global_patient_coverage_preview.csv",
    "global_patient_coverage_status": ROOT
    / "output/analysis_candidates/phase2_feature_review/streamlit_global_patient_coverage_status.csv",
    "timeout_table_patient_counts": ROOT
    / "output/analysis_candidates/phase2_feature_review/streamlit_timeout_table_patient_counts.csv",
    "large_table_t1_t2_bounded_counts": ROOT
    / "output/analysis_candidates/phase2_feature_review/streamlit_large_table_t1_t2_bounded_patient_counts.csv",
    "large_sensor_metadata": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/phase2_large_sensor_table_metadata.csv",
    "large_sensor_columns": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/phase2_large_sensor_table_columns.csv",
    "large_sensor_indexes": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/phase2_large_sensor_table_indexes.csv",
    "large_sensor_availability": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/phase2_large_sensor_bounded_patient_availability.csv",
    "large_sensor_summary": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/phase2_large_sensor_bounded_patient_summary.csv",
    "large_sensor_readme": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/README_phase2_large_sensor_table_metadata_scan.md",
    "accelerometer_framework_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/README_accelerometer_framework.md",
    "sensor_linear_accelerometer_qc_by_patient": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/sensor_linear_accelerometer_qc_by_patient.csv",
    "sensor_linear_accelerometer_qc_by_device": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/sensor_linear_accelerometer_qc_by_device_window.csv",
    "sensor_accelerometer_qc_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/README_sensor_accelerometer_qc.md",
    "sensor_accelerometer_qc_by_patient": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_patient.csv",
    "sensor_accelerometer_qc_by_device": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_device_window.csv",
    "accelerometer_raw_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/README_accelerometer_raw_signal_framework.md",
    "accelerometer_raw_sample_expanded": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_sample_rows_expanded.csv",
    "accelerometer_raw_keys": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_json_key_summary.csv",
    "accelerometer_raw_window_summary": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_candidate_window_summary.csv",
    "accelerometer_24h_pilot_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot/README_accelerometer_24h_pilot.md",
    "accelerometer_24h_pilot_manifest": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot/accelerometer_24h_pilot_manifest.csv",
    "accelerometer_24h_pilot_chunk_log": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot/accelerometer_24h_pilot_chunk_log.csv",
    "accelerometer_24h_pilot_candidate_scan": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot/accelerometer_24h_pilot_candidate_scan.csv",
    "accelerometer_tomorrow_work_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/README_ACCELEROMETER_TOMORROW_WORK.md",
    "accelerometer_local_24h_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/README_accelerometer_24h_local_signal_analysis.md",
    "accelerometer_local_24h_features": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_overall_features.csv",
    "accelerometer_local_24h_chunks": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_chunk_summary.csv",
    "accelerometer_local_24h_hourly": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_hourly_summary.csv",
    "accelerometer_local_24h_states": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_state_summary.csv",
    "accelerometer_local_24h_thresholds": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_threshold_sensitivity.csv",
    "accelerometer_local_24h_bandpass_features": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_bandpass_feature_summary.csv",
    "accelerometer_local_24h_bandpass_hourly": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_bandpass_hourly_summary.csv",
    "phase2_exploratory_feature_dir": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/exploratory_t1_week_24h",
    "phase3_all_t1_feature_dir": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features",
    "phase3_all_t1_long": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/phase2_all_t1_selected_features_long.csv",
    "phase3_all_t1_wide": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/phase2_all_t1_selected_features_wide.csv",
    "phase3_all_t1_status": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/phase2_all_t1_selected_features_patient_table_status.csv",
    "phase3_all_t1_coverage": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/phase2_all_t1_selected_features_coverage.csv",
    "phase3_all_t1_readme": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/README_phase2_all_t1_selected_features.md",
    "phase3_accelerometer_pilot_readme": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/README_phase3_accelerometer_24h_pilot.md",
    "phase3_accelerometer_pilot_wide": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/phase3_accelerometer_24h_pilot_features_wide.csv",
    "phase3_accelerometer_pilot_status": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/phase3_accelerometer_24h_pilot_patient_status.csv",
    "phase3_accelerometer_pilot_bandpass": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/phase3_accelerometer_24h_pilot_bandpass_summary.csv",
    "phase3_accelerometer_pilot_thresholds": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/phase3_accelerometer_24h_pilot_threshold_sensitivity.csv",
    "phase3_accelerometer_pilot_download": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/phase3_accelerometer_24h_pilot_download_chunk_log.csv",
    "rd_calls_t1_week_long": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_week_any_data_pilot/phase3_rd_calls_t1_week_any_data_long.csv",
    "rd_calls_t1_week_wide": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_week_any_data_pilot/phase3_rd_calls_t1_week_any_data_wide.csv",
    "rd_calls_t1_week_status": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_week_any_data_pilot/phase3_rd_calls_t1_week_any_data_status.csv",
    "rd_calls_t1_week_readme": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_week_any_data_pilot/README_phase3_rd_calls_t1_week_any_data.md",
    "rd_calls_t1_2week_long": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_2week_any_data_pilot/phase3_rd_calls_t1_2week_any_data_long.csv",
    "rd_calls_t1_2week_wide": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_2week_any_data_pilot/phase3_rd_calls_t1_2week_any_data_wide.csv",
    "rd_calls_t1_2week_status": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_2week_any_data_pilot/phase3_rd_calls_t1_2week_any_data_status.csv",
    "rd_calls_t1_2week_readme": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_2week_any_data_pilot/README_phase3_rd_calls_t1_2week_any_data.md",
    "rd_calls_t1_30day_long": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_30day_any_data_pilot/phase3_rd_calls_t1_30day_any_data_long.csv",
    "rd_calls_t1_30day_wide": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_30day_any_data_pilot/phase3_rd_calls_t1_30day_any_data_wide.csv",
    "rd_calls_t1_30day_status": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_30day_any_data_pilot/phase3_rd_calls_t1_30day_any_data_status.csv",
    "rd_calls_t1_30day_readme": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_30day_any_data_pilot/README_phase3_rd_calls_t1_30day_any_data.md",
    "rd_bluetooth_t1_week_long": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_week_any_data_pilot/phase3_rd_bluetooth_t1_week_any_data_long.csv",
    "rd_bluetooth_t1_week_wide": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_week_any_data_pilot/phase3_rd_bluetooth_t1_week_any_data_wide.csv",
    "rd_bluetooth_t1_week_status": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_week_any_data_pilot/phase3_rd_bluetooth_t1_week_any_data_status.csv",
    "rd_bluetooth_t1_week_readme": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_week_any_data_pilot/README_phase3_rd_bluetooth_t1_week_any_data.md",
    "rd_bluetooth_t1_30day_long": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_30day_any_data_pilot/phase3_rd_bluetooth_t1_30day_any_data_long.csv",
    "rd_bluetooth_t1_30day_wide": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_30day_any_data_pilot/phase3_rd_bluetooth_t1_30day_any_data_wide.csv",
    "rd_bluetooth_t1_30day_status": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_30day_any_data_pilot/phase3_rd_bluetooth_t1_30day_any_data_status.csv",
    "rd_bluetooth_t1_30day_readme": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_30day_any_data_pilot/README_phase3_rd_bluetooth_t1_30day_any_data.md",
    "cognitive_candidates": ROOT / "output/analysis_candidates/cognitive_candidates_all.csv",
    "cognitive_master": ROOT / "output/cognitive_master/master_cognitive_wide.csv",
    "label_device_map": ROOT / "output/label_device_map.csv",
    "top10": ROOT / "output/analysis_candidates/top10_global_decline.csv",
    "top10_device_summary": ROOT / "output/analysis_candidates/top10_subject_device_summary.csv",
    "device_episodes": ROOT / "output/analysis_candidates/top10_subject_device_episodes.csv",
    "phase1_profiles": ROOT
    / "output/analysis_candidates/phase1_features/phenotype_profiles/phase1_subject_phenotype_profiles_v2.csv",
    "phase1_cards": ROOT
    / "output/analysis_candidates/phase1_features/phenotype_profiles/phase1_subject_phenotype_cards_v2.md",
    "phase1_change": ROOT
    / "output/analysis_candidates/phase1_features/phenotype_profiles/phase1_change_profiles_024_077_v2.csv",
    "rich_wide": ROOT
    / "output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide_rich.csv",
    "table_inventory": ROOT / "output/sql_catalog/table_inventory.csv",
    "column_inventory": ROOT / "output/sql_catalog/column_inventory.csv",
    "sample_summary": ROOT
    / "output/analysis_candidates/phase2_sql_fieldwork_samples/sensordb_10_rows_per_table_summary.csv",
    "sample_rows": ROOT
    / "output/analysis_candidates/phase2_sql_fieldwork_samples/sensordb_10_rows_per_table_sample.csv",
    "applications_foreground_review_sample": ROOT
    / "output/analysis_candidates/phase2_feature_review/applications_foreground/applications_foreground_sample_rows.csv",
    "applications_foreground_json_keys": ROOT
    / "output/analysis_candidates/phase2_feature_review/applications_foreground/applications_foreground_json_key_summary.csv",
    "applications_foreground_highest_t1_36h_features": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/applications_foreground_highest_t1_36h/applications_foreground_highest_t1_36h_features.csv",
    "applications_foreground_highest_t1_36h_rows": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/applications_foreground_highest_t1_36h/applications_foreground_highest_t1_36h_rows.csv",
    "applications_foreground_highest_t1_36h_coverage": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/applications_foreground_highest_t1_36h/applications_foreground_highest_t1_36h_window_coverage.csv",
}

AXIS_COLS = [
    "phone_engagement_level",
    "nighttime_phone_activity_level",
    "app_use_breadth_level",
    "active_phone_interaction_level",
    "physical_activity_context_level",
    "data_quality_support_level",
]


st.set_page_config(
    page_title="NeuroTrax-SensorDB Fieldwork",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(1) p,
    [data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(6) p,
    [data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(7) p {
        font-size: 1.08rem;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"Subject_ID_D": str})


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def file_status(path: Path) -> str:
    return "available" if path.exists() else "missing"


def metric_row(items: list[tuple[str, str | int | float]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def show_dataframe(df: pd.DataFrame, *, height: int = 420) -> None:
    if df.empty:
        st.info("No file/data available yet.")
        return
    st.dataframe(df, use_container_width=True, height=height)


def show_feature_plan(df: pd.DataFrame, *, height: int = 520) -> None:
    if df.empty:
        st.info("No file/data available yet.")
        return
    if "selected_for_extraction" not in df.columns:
        show_dataframe(df, height=height)
        return

    display_df = df.copy()
    is_selected = display_df["selected_for_extraction"].astype(str).str.strip().str.lower().eq("yes")
    display_df.insert(0, "selection", is_selected.map({True: "SELECTED", False: ""}))
    display_df["_selected_sort"] = is_selected.astype(int)
    display_df = display_df.sort_values(["_selected_sort", "source_table", "feature_name"], ascending=[False, True, True])
    display_df = display_df.drop(columns=["_selected_sort"])

    def highlight_selected(row):
        selected = str(row.get("selected_for_extraction", "")).strip().lower() == "yes"
        if selected:
            return [
                "background-color: #0d6efd; color: white; font-weight: 900; "
                "border-top: 3px solid #003f88; border-bottom: 3px solid #003f88"
                for _ in row
            ]
        return ["" for _ in row]

    st.dataframe(display_df.style.apply(highlight_selected, axis=1), use_container_width=True, height=height)


def normalize_subject_id_d(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    return s.zfill(3) if s.isdigit() else s


def date_span(df: pd.DataFrame, start_col: str, end_col: str) -> tuple[str, str, str]:
    if df.empty or start_col not in df.columns or end_col not in df.columns:
        return "n/a", "n/a", "n/a"
    starts = pd.to_datetime(df[start_col], errors="coerce")
    ends = pd.to_datetime(df[end_col], errors="coerce")
    min_start = starts.min()
    max_end = ends.max()
    if pd.isna(min_start) or pd.isna(max_end):
        return "n/a", "n/a", "n/a"
    return min_start.date().isoformat(), max_end.date().isoformat(), f"{int((max_end - min_start).days)} days"


def median_followup_days(df: pd.DataFrame) -> str:
    if df.empty or "T1_date_iso" not in df.columns or "T2_date_iso" not in df.columns:
        return "n/a"
    t1 = pd.to_datetime(df["T1_date_iso"], errors="coerce")
    t2 = pd.to_datetime(df["T2_date_iso"], errors="coerce")
    days = (t2 - t1).dt.days.dropna()
    if days.empty:
        return "n/a"
    return f"{int(days.median())} days"


def device_counts_from_label_map(label_map: pd.DataFrame) -> pd.DataFrame:
    if label_map.empty or "label" not in label_map.columns or "device_ids" not in label_map.columns:
        return pd.DataFrame()
    rows = []
    for _, row in label_map.iterrows():
        raw_ids = str(row.get("device_ids", "") or "")
        device_ids = [x.strip() for x in raw_ids.split(";") if x.strip() and x.strip().lower() != "nan"]
        rows.append(
            {
                "Subject_ID_D": str(row["label"]).zfill(3) if str(row["label"]).isdigit() else str(row["label"]),
                "n_devices": len(device_ids),
                "device_ids": ";".join(device_ids),
            }
        )
    return pd.DataFrame(rows).sort_values("Subject_ID_D")


def simplify_applications_foreground_sample(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "data" not in df.columns:
        return df
    rows = []
    for _, row in df.iterrows():
        parsed = {}
        raw = row.get("data")
        if pd.notna(raw):
            try:
                parsed = json.loads(str(raw))
            except Exception:
                parsed = {}
        rows.append(
            {
                "sample_index": row.get("sample_index"),
                "_id": row.get("_id"),
                "timestamp": row.get("timestamp"),
                "local_datetime": row.get("local_datetime"),
                "package_name": parsed.get("package_name"),
                "application_name": parsed.get("application_name"),
                "is_system_app": parsed.get("is_system_app"),
            }
        )
    return pd.DataFrame(rows)


def available_table_reviews() -> dict[str, Path]:
    reviews: dict[str, Path] = {}
    review_dir = PATHS["phase2_table_feature_reviews"]
    if review_dir.exists():
        reviews.update({path.stem: path for path in sorted(review_dir.glob("*.md"))})

    output_review_dir = PATHS["phase2_output_feature_reviews"]
    if output_review_dir.exists():
        for path in sorted(output_review_dir.glob("*/README_*_feature_review.md")):
            table_name = path.parent.name
            reviews.setdefault(table_name, path)
    return reviews


def table_review_output_paths(table_name: str) -> dict[str, Path]:
    out_dir = ROOT / "output/analysis_candidates/phase2_feature_review" / table_name
    extraction_dir = ROOT / "output/analysis_candidates/phase2_feature_extraction" / f"{table_name}_highest_t1_36h"
    phase_b_features = extraction_dir / f"{table_name}_highest_t1_36h_features.csv"
    phase_b_coverage = extraction_dir / f"{table_name}_highest_t1_36h_window_coverage.csv"
    phase_b_rows = extraction_dir / f"{table_name}_highest_t1_36h_rows_expanded.csv"
    phase_b_readme = extraction_dir / f"README_{table_name}_highest_t1_36h.md"
    if table_name == "applications_foreground":
        extraction_dir = ROOT / "output/analysis_candidates/phase2_feature_extraction/applications_foreground_highest_t1_36h"
        phase_b_features = extraction_dir / "applications_foreground_highest_t1_36h_features.csv"
        phase_b_coverage = extraction_dir / "applications_foreground_highest_t1_36h_window_coverage.csv"
        phase_b_rows = extraction_dir / "applications_foreground_highest_t1_36h_rows.csv"
        phase_b_readme = extraction_dir / "README_applications_foreground_highest_t1_36h.md"
    if table_name == "bluetooth":
        phase_b_rows = extraction_dir / "bluetooth_highest_t1_36h_distinct_rows.csv"
        sample_feature_check = out_dir / "bluetooth_selected_feature_check.csv"
    elif table_name == "battery":
        sample_feature_check = out_dir / "battery_first_100_selected_feature_check.csv"
    else:
        sample_feature_check = out_dir / f"{table_name}_selected_feature_check.csv"
    if not sample_feature_check.exists():
        candidate_checks = sorted(out_dir.glob("*selected_feature_check.csv"))
        if candidate_checks:
            sample_feature_check = candidate_checks[0]
    return {
        "sample_rows": out_dir / f"{table_name}_sample_rows.csv",
        "sample_rows_expanded": out_dir / f"{table_name}_sample_rows_expanded.csv",
        "sample_rows_distinct": out_dir / f"{table_name}_sample_rows_distinct_observations.csv",
        "sample_feature_check": sample_feature_check,
        "json_keys": out_dir / f"{table_name}_json_key_summary.csv",
        "readme": out_dir / f"README_{table_name}_feature_review.md",
        "phase_b_features": phase_b_features,
        "phase_b_coverage": phase_b_coverage,
        "phase_b_rows": phase_b_rows,
        "phase_b_readme": phase_b_readme,
        "exploratory_features": PATHS["phase2_exploratory_feature_dir"]
        / f"phase2_exploratory_t1_week_24h_selected_features_{table_name}.csv",
        "exploratory_coverage": PATHS["phase2_exploratory_feature_dir"]
        / f"phase2_exploratory_t1_week_24h_coverage_scan_{table_name}.csv",
    }


def selected_feature_names_for_table(selected_features: pd.DataFrame, table_name: str) -> list[str]:
    if selected_features.empty:
        return []
    if "source_table" in selected_features.columns:
        view = selected_features[selected_features["source_table"].astype(str) == table_name]
    elif "table_name" in selected_features.columns:
        view = selected_features[selected_features["table_name"].astype(str) == table_name]
    else:
        return []
    if "feature_name" not in view.columns:
        return []
    return view["feature_name"].dropna().astype(str).tolist()


def format_feature_values(feature_names: list[str], values_df: pd.DataFrame) -> str:
    if not feature_names:
        return ""
    if values_df.empty:
        return "not calculated"

    if {"feature_name", "feature_value"}.issubset(values_df.columns):
        parts = []
        for feature_name in feature_names:
            matches = values_df[values_df["feature_name"].astype(str) == feature_name]
            if matches.empty:
                continue
            value = matches.iloc[0].get("feature_value")
            if pd.isna(value) or value == "":
                value_text = "missing"
            else:
                value_text = str(value)
            parts.append(f"{feature_name}={value_text}")
        return "; ".join(parts) if parts else "not calculated"

    row = values_df.iloc[0]
    parts = []
    for feature_name in feature_names:
        if feature_name not in values_df.columns:
            continue
        value = row.get(feature_name)
        if pd.isna(value) or value == "":
            value_text = "missing"
        else:
            value_text = str(value)
        parts.append(f"{feature_name}={value_text}")
    return "; ".join(parts) if parts else "not calculated"


def table_review_status(
    tracking: pd.DataFrame,
    selected_features: pd.DataFrame,
    feature_plan: pd.DataFrame,
    reviews: dict[str, Path],
) -> pd.DataFrame:
    table_names = set(reviews)
    for df, col in [
        (tracking, "table_name"),
        (selected_features, "table_name"),
        (feature_plan, "source_table"),
    ]:
        if not df.empty and col in df.columns:
            table_names.update(df[col].dropna().astype(str))

    rows = []
    selected_table_col = ""
    if not selected_features.empty:
        if "table_name" in selected_features.columns:
            selected_table_col = "table_name"
        elif "source_table" in selected_features.columns:
            selected_table_col = "source_table"

    for table_name in sorted(table_names):
        selected_n = 0
        candidate_n = 0
        review_file = reviews.get(table_name)
        output_paths = table_review_output_paths(table_name)
        selected_feature_names = selected_feature_names_for_table(selected_features, table_name)
        if selected_table_col:
            selected_n = int((selected_features[selected_table_col].astype(str) == table_name).sum())
        if not feature_plan.empty and "source_table" in feature_plan.columns:
            candidate_n = int((feature_plan["source_table"].astype(str) == table_name).sum())
        sample_feature_values = "not calculated"
        if output_paths["sample_feature_check"].exists():
            sample_feature_values = format_feature_values(
                selected_feature_names,
                load_csv(output_paths["sample_feature_check"]),
            )
        phase_b_feature_values = "not calculated"
        if output_paths["exploratory_features"].exists():
            phase_b_feature_values = format_feature_values(
                selected_feature_names,
                load_csv(output_paths["exploratory_features"]),
            )
            if sample_feature_values == "not calculated" and phase_b_feature_values != "not calculated":
                sample_feature_values = "calculated-no csv"
        rows.append(
            {
                "table_name": table_name,
                "has_review_file": "yes" if review_file else "no",
                "selected_features": selected_n,
                "selected_feature_names": "; ".join(selected_feature_names),
                "review_sample_feature_values": sample_feature_values,
                "phase_b_feature_values": phase_b_feature_values,
                "candidate_features": candidate_n,
                "review_file": str(review_file.relative_to(ROOT)) if review_file else "",
            }
        )
    return pd.DataFrame(rows)


def overview_page() -> None:
    st.title("NeuroTrax-SensorDB Project Dashboard")
    st.caption("A lightweight control panel for the current dementia digital phenotyping fieldwork.")

    candidates = load_csv(PATHS["cognitive_candidates"])
    label_map = load_csv(PATHS["label_device_map"])
    device_counts = device_counts_from_label_map(label_map)
    phase2_tracking = load_csv(PATHS["phase2_tracking"])
    phase2_inventory = load_csv(PATHS["table_inventory"])
    phase2_feature_plan = load_csv(PATHS["phase2_feature_plan"])
    phase2_selected_features = load_csv(PATHS["phase2_selected_features"])
    phase3_long = load_csv(PATHS["phase3_all_t1_long"])
    phase3_wide = load_csv(PATHS["phase3_all_t1_wide"])
    phase3_status = load_csv(PATHS["phase3_all_t1_status"])
    global_patient_coverage = load_csv(PATHS["global_patient_coverage_preview"])
    global_patient_coverage_status = load_csv(PATHS["global_patient_coverage_status"])
    timeout_table_patient_counts = load_csv(PATHS["timeout_table_patient_counts"])
    large_table_t1_t2_counts = load_csv(PATHS["large_table_t1_t2_bounded_counts"])
    large_sensor_metadata = load_csv(PATHS["large_sensor_metadata"])
    large_sensor_summary = load_csv(PATHS["large_sensor_summary"])
    phase2_reviews = available_table_reviews()

    n_total = len(candidates)
    n_t1 = int(pd.to_datetime(candidates.get("T1_date_iso", pd.Series(dtype=str)), errors="coerce").notna().sum())
    t1_dates = pd.to_datetime(candidates.get("T1_date_iso", pd.Series(dtype=str)), errors="coerce")
    t2_dates = pd.to_datetime(candidates.get("T2_date_iso", pd.Series(dtype=str)), errors="coerce")
    n_t1_t2 = int((t1_dates.notna() & t2_dates.notna()).sum())
    n_with_global_delta = int(pd.to_numeric(candidates.get("global_delta", pd.Series(dtype=str)), errors="coerce").notna().sum())
    n_cognitive_with_device_label = 0
    if not candidates.empty and not label_map.empty and "Subject_ID_D" in candidates.columns and "label" in label_map.columns:
        candidate_labels = set(candidates["Subject_ID_D"].dropna().astype(str).map(normalize_subject_id_d))
        mapped_labels = set(label_map["label"].dropna().astype(str).map(normalize_subject_id_d))
        n_cognitive_with_device_label = len(candidate_labels & mapped_labels)

    metric_row(
        [
            ("Patients total", n_total),
            ("Patients with T1", n_t1),
            ("Patients with T1 and T2", n_t1_t2),
            ("Patients with global delta", n_with_global_delta),
            ("Cognitive patients with device label", n_cognitive_with_device_label),
            ("Median T1-to-T2 gap", median_followup_days(candidates)),
        ]
    )

    st.subheader("Phase 2 Work Underway")
    metric_row(
        [
            ("Phase 2 tracked tables", len(phase2_tracking)),
            ("Reviewed table pages", len(phase2_reviews)),
            ("Selected features", len(phase2_selected_features)),
            ("Candidate feature rows", len(phase2_feature_plan)),
        ]
    )

    if not phase3_long.empty or not phase3_wide.empty:
        st.subheader("Phase 3 Algorithm Implementation")
        phase3_patients = (
            phase3_wide["Subject_ID_D"].nunique()
            if not phase3_wide.empty and "Subject_ID_D" in phase3_wide.columns
            else 0
        )
        phase3_tables = (
            phase3_status["table_name"].nunique()
            if not phase3_status.empty and "table_name" in phase3_status.columns
            else 0
        )
        phase3_features = (
            phase3_long["feature_name"].nunique()
            if not phase3_long.empty and "feature_name" in phase3_long.columns
            else 0
        )
        phase3_calculated = (
            int(phase3_long["feature_status"].astype(str).eq("calculated").sum())
            if not phase3_long.empty and "feature_status" in phase3_long.columns
            else 0
        )
        metric_row(
            [
                ("T1 patients implemented", phase3_patients),
                ("Tables implemented", phase3_tables),
                ("Selected algorithms", phase3_features),
                ("Calculated feature values", phase3_calculated),
            ]
        )

    st.subheader("Two Main Project Outcomes")
    left, right = st.columns(2)
    with left:
        st.markdown(
            """
            **Outcome 1: T1 baseline digital phenotype**

            Build T1 baseline digital phenotype features using the exploratory T1-ranked first-valid 24-hour T1-week protocol for feature finding, then later apply the finalized features to patient-level baseline analyses.
            """
        )
    with right:
        st.markdown(
            """
            **Outcome 2: T1-to-T2 digital phenotype delta**

            Describe the digital phenotype change between T1 and T2. Later, test whether T1 phenotype plus digital change can help predict the patient's NeuroTrax overall/global T2 score.
            """
        )

    st.subheader("Experiment Time Span")
    all_t1, all_t2, all_days = date_span(candidates, "T1_date_iso", "T2_date_iso")
    metric_row(
        [
            ("All candidates first T1", all_t1),
            ("All candidates last T2", all_t2),
            ("All candidates span", all_days),
        ]
    )

    st.subheader("Global Coverage Summary")
    if global_patient_coverage.empty:
        st.info("Global patient coverage preview is not available yet.")
    else:
        patient_denominator = n_cognitive_with_device_label or n_t1 or n_total
        table_summary = (
            global_patient_coverage.groupby("table_name", as_index=False)
            .agg(number_of_patients_with_data=("Subject_ID_D", "nunique"))
            .sort_values(["number_of_patients_with_data", "table_name"], ascending=[False, True])
        )
        table_summary["percentage"] = (
            100 * table_summary["number_of_patients_with_data"] / patient_denominator
        ).round(1)
        table_summary = table_summary.rename(columns={"table_name": "table name"})
        if not timeout_table_patient_counts.empty:
            timeout_summary = timeout_table_patient_counts.copy()
            timeout_summary["number_of_patients_with_data"] = pd.to_numeric(
                timeout_summary["number_of_patients_with_data"], errors="coerce"
            )
            timeout_summary["percentage"] = pd.NA
            has_count = timeout_summary["number_of_patients_with_data"].notna()
            timeout_summary.loc[has_count, "number_of_patients_with_data"] = timeout_summary.loc[
                has_count, "number_of_patients_with_data"
            ].astype(int)
            timeout_summary.loc[has_count, "percentage"] = (
                100 * timeout_summary.loc[has_count, "number_of_patients_with_data"] / patient_denominator
            ).round(1)
            timeout_summary["number_of_patients_with_data"] = timeout_summary[
                "number_of_patients_with_data"
            ].astype("object")
            timeout_summary.loc[~has_count, "number_of_patients_with_data"] = "unavailable"
            timeout_summary["percentage"] = timeout_summary["percentage"].astype("object")
            timeout_summary.loc[~has_count, "percentage"] = ""
            timeout_summary = timeout_summary.rename(columns={"table_name": "table name"})
            timeout_summary = timeout_summary[["table name", "number_of_patients_with_data", "percentage"]]
            table_summary = pd.concat([table_summary, timeout_summary], ignore_index=True)
            table_summary["_sort_count"] = pd.to_numeric(
                table_summary["number_of_patients_with_data"], errors="coerce"
            ).fillna(-1)
            table_summary = (
                table_summary.sort_values(["_sort_count", "table name"], ascending=[False, True])
                .drop_duplicates("table name", keep="first")
                .drop(columns=["_sort_count"])
                .reset_index(drop=True)
            )
        st.dataframe(table_summary, use_container_width=True, height=300)

        table_options = sorted(global_patient_coverage["table_name"].dropna().astype(str).unique().tolist())
        selected_table = st.selectbox("Table", table_options, index=table_options.index("network") if "network" in table_options else 0)
        coverage_view = global_patient_coverage[
            global_patient_coverage["table_name"].astype(str) == selected_table
        ].copy()
        coverage_view = coverage_view[["Subject_ID_D", "rows", "devices", "first row", "last row"]]
        if "rows" in coverage_view.columns:
            coverage_view["rows"] = pd.to_numeric(coverage_view["rows"], errors="coerce").astype("Int64")
        if "devices" in coverage_view.columns:
            coverage_view["devices"] = pd.to_numeric(coverage_view["devices"], errors="coerce").astype("Int64")
        show_dataframe(coverage_view, height=300)
        if not global_patient_coverage_status.empty:
            skipped = global_patient_coverage_status[
                global_patient_coverage_status["status"].astype(str).str.startswith("skipped")
                | global_patient_coverage_status["status"].astype(str).eq("error")
            ]
            if not skipped.empty:
                with st.expander("Skipped or unavailable tables"):
                    show_dataframe(skipped, height=260)

        if not large_table_t1_t2_counts.empty:
            st.subheader("T1/T2 Bounded Coverage for Large Tables")
            bounded_view = large_table_t1_t2_counts[
                [
                    "table_name",
                    "t1_day_after_patients_with_data",
                    "t1_day_after_percentage",
                    "t2_day_before_patients_with_data",
                    "t2_day_before_percentage",
                ]
            ].copy()
            show_dataframe(bounded_view, height=300)

        if not large_sensor_metadata.empty:
            st.subheader("Large Sensor Metadata")
            st.caption("Metadata-only scan for large/raw sensor tables. Approximate size comes from database table status; availability uses bounded patient/window EXISTS checks.")
            metadata_cols = [
                col
                for col in [
                    "table_name",
                    "metadata_estimated_rows",
                    "total_size_gb",
                    "has_device_id",
                    "has_timestamp",
                    "has_data",
                    "metadata_status",
                ]
                if col in large_sensor_metadata.columns
            ]
            show_dataframe(large_sensor_metadata[metadata_cols], height=260)
            if not large_sensor_summary.empty:
                st.caption("Bounded availability summary around T1/T2 windows.")
                show_dataframe(large_sensor_summary, height=260)

    st.subheader("NeuroTrax Feature Domains")
    neurotrax_domains = pd.DataFrame(
        [
            {"domain": "overall/global score", "columns": "global_T1, global_T2, global_delta"},
            {"domain": "memory", "columns": "memory_T1, memory_T2, memory_delta"},
            {"domain": "executive function", "columns": "ef_T1, ef_T2, ef_delta"},
            {"domain": "attention", "columns": "attention_T1, attention_T2, attention_delta"},
            {
                "domain": "processing speed",
                "columns": "processing_speed_T1, processing_speed_T2, processing_speed_delta",
            },
            {"domain": "verbal", "columns": "verbal_T1, verbal_T2, verbal_delta"},
            {"domain": "motor", "columns": "motor_T1, motor_T2, motor_delta"},
            {"domain": "IQ", "columns": "iq_T1, iq_T2, iq_delta"},
        ]
    )
    st.dataframe(neurotrax_domains, use_container_width=True, height=300)

    with st.expander("Device numbers per patient"):
        st.caption("Source file: output/label_device_map.csv")
        show_dataframe(device_counts, height=420)

    st.subheader("Current Protocol Summary")
    text = load_text(PATHS["protocol_summary"])
    if text:
        st.markdown(text)
    else:
        st.warning("Protocol summary README is missing.")


def phase1_profiles_page() -> None:
    st.title("Phase 1 Digital Phenotype Profiles")
    profiles = load_csv(PATHS["phase1_profiles"])
    if profiles.empty:
        st.info("Phase 1 phenotype profile CSV is not available.")
        return

    baseline_n = int(profiles.get("phase1_baseline_usable", pd.Series(dtype=str)).astype(str).str.lower().eq("true").sum())
    change_n = int(profiles.get("phase1_change_usable", pd.Series(dtype=str)).astype(str).str.lower().eq("true").sum())
    metric_row(
        [
            ("Subjects", len(profiles)),
            ("Baseline usable", baseline_n),
            ("Change usable", change_n),
        ]
    )

    st.subheader("Axis Distributions")
    dist_rows = []
    for col in AXIS_COLS:
        if col not in profiles.columns:
            continue
        counts = profiles[col].value_counts(dropna=False).reset_index()
        counts.columns = ["level", "n_subjects"]
        counts.insert(0, "axis", col.replace("_level", ""))
        dist_rows.append(counts)
    if dist_rows:
        dist = pd.concat(dist_rows, ignore_index=True)
        left, right = st.columns([1, 1])
        with left:
            st.dataframe(dist, use_container_width=True, height=360)
        with right:
            chart_df = dist.pivot(index="axis", columns="level", values="n_subjects").fillna(0)
            st.bar_chart(chart_df)

    st.subheader("Subject Profiles")
    subjects = ["All"] + sorted(profiles["Subject_ID_D"].dropna().astype(str).tolist())
    selected = st.selectbox("Subject", subjects)
    view = profiles if selected == "All" else profiles[profiles["Subject_ID_D"].astype(str) == selected]
    show_dataframe(view, height=440)

    cards = load_text(PATHS["phase1_cards"])
    with st.expander("Markdown phenotype cards"):
        st.markdown(cards if cards else "No phenotype cards file available.")


def phase1_change_page() -> None:
    st.title("Phase 1 Early-vs-Late Change Profiles")
    change = load_csv(PATHS["phase1_change"])
    if change.empty:
        st.info("Change profile CSV is not available.")
        return

    subjects = ["All"] + sorted(change["Subject_ID_D"].dropna().astype(str).unique().tolist())
    families = ["All"] + sorted(change["feature_family"].dropna().astype(str).unique().tolist())
    left, right = st.columns([1, 1])
    selected_subject = left.selectbox("Subject", subjects)
    selected_family = right.selectbox("Feature family", families)

    view = change.copy()
    if selected_subject != "All":
        view = view[view["Subject_ID_D"].astype(str) == selected_subject]
    if selected_family != "All":
        view = view[view["feature_family"].astype(str) == selected_family]
    show_dataframe(view, height=520)


def phase2_tables_page() -> None:
    st.title("Phase 2 Tables and Feature Fieldwork")
    tracking = load_csv(PATHS["phase2_tracking"])
    inventory = load_csv(PATHS["table_inventory"])
    sample_summary = load_csv(PATHS["sample_summary"])
    feature_plan = load_csv(PATHS["phase2_feature_plan"])
    selected_features = load_csv(PATHS["phase2_selected_features"])
    highest_t1_calculated_values = load_csv(PATHS["phase2_highest_t1_calculated_feature_values"])
    global_coverage_summary = load_csv(PATHS["phase2_reviewed_tables_global_coverage_summary"])
    large_sensor_metadata = load_csv(PATHS["large_sensor_metadata"])
    large_sensor_columns = load_csv(PATHS["large_sensor_columns"])
    large_sensor_indexes = load_csv(PATHS["large_sensor_indexes"])
    large_sensor_availability = load_csv(PATHS["large_sensor_availability"])
    large_sensor_summary = load_csv(PATHS["large_sensor_summary"])
    sensor_linear_qc_patient = load_csv(PATHS["sensor_linear_accelerometer_qc_by_patient"])
    sensor_linear_qc_device = load_csv(PATHS["sensor_linear_accelerometer_qc_by_device"])
    sensor_acc_qc_patient = load_csv(PATHS["sensor_accelerometer_qc_by_patient"])
    sensor_acc_qc_device = load_csv(PATHS["sensor_accelerometer_qc_by_device"])
    accelerometer_raw_sample = load_csv(PATHS["accelerometer_raw_sample_expanded"])
    accelerometer_raw_keys = load_csv(PATHS["accelerometer_raw_keys"])
    accelerometer_raw_window_summary = load_csv(PATHS["accelerometer_raw_window_summary"])
    accelerometer_24h_manifest = load_csv(PATHS["accelerometer_24h_pilot_manifest"])
    accelerometer_24h_chunk_log = load_csv(PATHS["accelerometer_24h_pilot_chunk_log"])
    accelerometer_24h_candidate_scan = load_csv(PATHS["accelerometer_24h_pilot_candidate_scan"])
    accelerometer_local_24h_features = load_csv(PATHS["accelerometer_local_24h_features"])
    accelerometer_local_24h_chunks = load_csv(PATHS["accelerometer_local_24h_chunks"])
    accelerometer_local_24h_hourly = load_csv(PATHS["accelerometer_local_24h_hourly"])
    accelerometer_local_24h_states = load_csv(PATHS["accelerometer_local_24h_states"])
    accelerometer_local_24h_thresholds = load_csv(PATHS["accelerometer_local_24h_thresholds"])
    accelerometer_local_24h_bandpass_features = load_csv(PATHS["accelerometer_local_24h_bandpass_features"])
    accelerometer_local_24h_bandpass_hourly = load_csv(PATHS["accelerometer_local_24h_bandpass_hourly"])
    review_sample = load_csv(PATHS["applications_foreground_review_sample"])
    json_keys = load_csv(PATHS["applications_foreground_json_keys"])
    highest_t1_features = load_csv(PATHS["applications_foreground_highest_t1_36h_features"])
    highest_t1_rows = load_csv(PATHS["applications_foreground_highest_t1_36h_rows"])
    highest_t1_coverage = load_csv(PATHS["applications_foreground_highest_t1_36h_coverage"])
    table_reviews = available_table_reviews()
    review_status = table_review_status(tracking, selected_features, feature_plan, table_reviews)

    metric_row(
        [
            ("Tracked tables", len(tracking)),
            ("Reviewed table pages", len(table_reviews)),
            ("Selected features", len(selected_features)),
            ("Candidate feature rows", len(feature_plan)),
        ]
    )

    tabs = st.tabs(
        [
            "Table Overview",
            "Reviewed Table Detail",
            "Selected Features",
            "Feature Analysis Protocol",
            "Candidate Features",
            "SQL Inventory",
            "Large Sensor Metadata",
            "Accelerometer Framework",
            "Sampling Summary",
        ]
    )
    with tabs[0]:
        if st.button("Refresh Phase 2 files"):
            st.rerun()

        st.subheader("Current Feature Values")
        st.caption("Current feature rows use only the exploratory T1-ranked first-valid 24h T1-week protocol. Missing values mean no protocol-valid patient/window was found for that table.")
        show_dataframe(highest_t1_calculated_values, height=260)

        st.subheader("Table Review Status")
        st.caption("One row per reviewed or feature-planned SensorDB table. Current feature values use the exploratory T1-week 24h protocol.")
        show_dataframe(review_status, height=360)

        st.subheader("Global Coverage Summary")
        st.caption("Compact table-level availability summary added to the Phase 2A protocol. This is global coverage, not T1-window feature extraction.")
        show_dataframe(global_coverage_summary, height=360)
    with tabs[1]:
        st.markdown(
            "<div style='font-size:2rem;font-weight:900;margin:0.2rem 0 1rem 0;'>Reviewed Table Detail</div>",
            unsafe_allow_html=True,
        )
        if not table_reviews:
            st.info("No reviewed table markdown files are available yet.")
        else:
            selected_review_table = st.selectbox("Reviewed table", sorted(table_reviews))
            st.markdown(load_text(table_reviews[selected_review_table]))
            output_paths = table_review_output_paths(selected_review_table)

            table_selected = pd.DataFrame()
            if not selected_features.empty:
                if "table_name" in selected_features.columns:
                    table_selected = selected_features[selected_features["table_name"].astype(str) == selected_review_table]
                elif "source_table" in selected_features.columns:
                    table_selected = selected_features[selected_features["source_table"].astype(str) == selected_review_table]
            st.subheader("Selected Features for This Table")
            show_dataframe(table_selected, height=220)

            table_candidates = pd.DataFrame()
            if not feature_plan.empty and "source_table" in feature_plan.columns:
                table_candidates = feature_plan[feature_plan["source_table"].astype(str) == selected_review_table]
            st.subheader("Candidate Feature Plan for This Table")
            show_feature_plan(table_candidates, height=320)

            if selected_review_table == "applications_foreground":
                st.subheader("Review Sample")
                st.caption("Cleaned view for feature decisions. Repeated device_id and JSON timestamp are hidden; raw file remains unchanged.")
                show_dataframe(simplify_applications_foreground_sample(review_sample), height=280)
                with st.expander("Raw sampled rows"):
                    show_dataframe(review_sample, height=320)
                st.subheader("JSON Key Summary")
                show_dataframe(json_keys, height=220)
                st.subheader("Exploratory T1-Ranked 24h Selected Features")
                show_dataframe(load_csv(output_paths["exploratory_features"]), height=180)
                with st.expander("Exploratory T1-week 24h coverage scan"):
                    show_dataframe(load_csv(output_paths["exploratory_coverage"]), height=260)
            else:
                st.subheader("Review Sample")
                sample_df = load_csv(output_paths["sample_rows_expanded"])
                if sample_df.empty:
                    sample_df = load_csv(output_paths["sample_rows"])
                if sample_df.empty and output_paths["sample_rows"].exists():
                    st.info("Sample file exists, but it contains no sampled rows under the current protocol.")
                distinct_df = load_csv(output_paths["sample_rows_distinct"])
                if not distinct_df.empty:
                    st.subheader("Distinct Observation Sample")
                    st.caption("Deduplicated inspection view for duplicate-heavy tables. This is for manual review only.")
                    show_dataframe(distinct_df, height=280)
                    if selected_review_table == "bluetooth":
                        st.caption("For Bluetooth, this distinct-observation sample is the primary Phase A inspection view.")
                if selected_review_table != "bluetooth" or distinct_df.empty:
                    show_dataframe(sample_df, height=280)
                with st.expander("Raw sample rows with original JSON"):
                    show_dataframe(load_csv(output_paths["sample_rows"]), height=320)
                st.subheader("JSON Key Summary")
                show_dataframe(load_csv(output_paths["json_keys"]), height=220)
                st.subheader("Selected Feature Check on Review Sample")
                show_dataframe(load_csv(output_paths["sample_feature_check"]), height=180)
                st.subheader("Exploratory T1-Ranked 24h Selected Features")
                show_dataframe(load_csv(output_paths["exploratory_features"]), height=180)
                with st.expander("Exploratory T1-week 24h coverage scan"):
                    show_dataframe(load_csv(output_paths["exploratory_coverage"]), height=260)
                readme_text = load_text(output_paths["readme"])
                if readme_text:
                    with st.expander("Review output README"):
                        st.markdown(readme_text)
    with tabs[2]:
        st.caption("Manual source of truth for features selected for future extraction.")
        show_dataframe(selected_features, height=420)
    with tabs[3]:
        st.subheader("Phase A / Phase B Flow")
        st.markdown(
            """
            **Phase A: Manual inspection of 20 raw rows**  
            For each new SensorDB table, inspect 20 chronological raw rows from the highest-T1 patient's day-after-T1 inspection window when available. This phase is only for understanding rows and JSON structure. No aggregation, no feature extraction, and no clinical interpretation.

            **Feature finding: exploratory T1-ranked 24h protocol**  
            After Phase A is understood, choose candidate features, then scan patients from highest T1 score downward until the first protocol-valid 24-hour window inside that patient's T1 week is found. If no valid patient/window exists, keep the selected features visible as missing rather than converting missing data to zero.

            **High-frequency sensor tables**  
            Motion tables such as `linear_accelerometer` need stricter handling. If no T1-week 24-hour protocol window exists, defer the table rather than widening SQL searches. Fourier-style features require confirmed x/y/z fields, timestamp regularity, duplicate handling, vector magnitude, and consistent resampling/segmentation.
            """
        )
        st.divider()
        st.markdown(load_text(PATHS["phase2_feature_protocol"]) or "No Phase 2 feature analysis protocol file available.")
    with tabs[4]:
        st.caption("Working list of features we may extract from each SensorDB table. This starts with applications_foreground and will grow table by table.")
        if not feature_plan.empty and "source_table" in feature_plan.columns:
            tables = ["All"] + sorted(feature_plan["source_table"].dropna().astype(str).unique().tolist())
            selected_table = st.selectbox("Source table", tables)
            view = feature_plan if selected_table == "All" else feature_plan[feature_plan["source_table"].astype(str) == selected_table]
            if "selected_for_extraction" in view.columns:
                selected_view = view[view["selected_for_extraction"].astype(str).str.strip().str.lower().eq("yes")]
                if not selected_view.empty:
                    st.markdown("#### Selected Features")
                    card_cols = st.columns(min(3, len(selected_view)))
                    for idx, (_, feature_row) in enumerate(selected_view.iterrows()):
                        with card_cols[idx % len(card_cols)]:
                            st.markdown(
                                f"""
                                <div style="background:#0d6efd;color:white;padding:14px 16px;border-radius:8px;
                                            border:3px solid #003f88;font-weight:800;margin-bottom:10px;">
                                    {feature_row['feature_name']}<br>
                                    <span style="font-weight:500;font-size:0.9rem;">{feature_row['short_description']}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
            show_feature_plan(view, height=520)
        else:
            show_dataframe(feature_plan, height=520)
    with tabs[5]:
        show_dataframe(inventory, height=520)
    with tabs[6]:
        st.subheader("Large Sensor Table Metadata")
        st.caption("Cheap metadata and bounded availability for large/raw sensor tables. No full-table grouped counts and no raw extraction.")
        show_dataframe(large_sensor_metadata, height=320)

        st.subheader("Bounded Patient Availability")
        show_dataframe(large_sensor_summary, height=260)

        if not large_sensor_availability.empty and "table_name" in large_sensor_availability.columns:
            table_options = ["All"] + sorted(large_sensor_availability["table_name"].dropna().astype(str).unique().tolist())
            selected_large_sensor_table = st.selectbox("Large sensor table", table_options)
            availability_view = large_sensor_availability.copy()
            if selected_large_sensor_table != "All":
                availability_view = availability_view[
                    availability_view["table_name"].astype(str) == selected_large_sensor_table
                ]
            show_dataframe(availability_view, height=360)
        else:
            show_dataframe(large_sensor_availability, height=360)

        with st.expander("Columns"):
            show_dataframe(large_sensor_columns, height=420)
        with st.expander("Indexes"):
            show_dataframe(large_sensor_indexes, height=420)
        readme = load_text(PATHS["large_sensor_readme"])
        if readme:
            with st.expander("Metadata scan README"):
                st.markdown(readme)
    with tabs[7]:
        st.subheader("Accelerometer Framework")
        st.caption(
            "Sensor metadata tables are QC/device-context layers. Raw `accelerometer` and "
            "`linear_accelerometer` motion streams come later."
        )

        def qc_summary_row(table_name: str, df: pd.DataFrame, device_df: pd.DataFrame, has_col: str) -> dict[str, object]:
            metadata_count = 0
            available_count = 0
            sparse_count = 0
            very_sparse_count = 0
            no_metadata_count = 0
            if not df.empty:
                if has_col in df.columns:
                    metadata_count = int(df[has_col].astype(str).str.lower().isin(["true", "1", "yes"]).sum())
                if "qc_readiness_level" in df.columns:
                    levels = df["qc_readiness_level"].astype(str)
                    available_count = int(levels.eq("metadata_available_for_device_context").sum())
                    sparse_count = int(levels.eq("sparse_metadata").sum())
                    very_sparse_count = int(levels.eq("very_sparse_metadata").sum())
                    no_metadata_count = int(levels.eq("no_metadata_after_T1").sum())
            return {
                "table_name": table_name,
                "patients_checked": len(df),
                "patients_with_metadata_after_T1": metadata_count,
                "metadata_available_for_device_context": available_count,
                "sparse_metadata": sparse_count,
                "very_sparse_metadata": very_sparse_count,
                "no_metadata_after_T1": no_metadata_count,
                "device_window_rows": len(device_df),
            }

        qc_comparison = pd.DataFrame(
            [
                qc_summary_row(
                    "sensor_accelerometer",
                    sensor_acc_qc_patient,
                    sensor_acc_qc_device,
                    "has_sensor_accelerometer_metadata_after_T1",
                ),
                qc_summary_row(
                    "sensor_linear_accelerometer",
                    sensor_linear_qc_patient,
                    sensor_linear_qc_device,
                    "has_sensor_linear_accelerometer_metadata_after_T1",
                ),
            ]
        )
        metric_row(
            [
                (
                    "General acc metadata patients",
                    int(
                        qc_comparison.loc[
                            qc_comparison["table_name"].eq("sensor_accelerometer"),
                            "patients_with_metadata_after_T1",
                        ].iloc[0]
                    )
                    if not qc_comparison.empty
                    else 0,
                ),
                (
                    "Linear acc metadata patients",
                    int(
                        qc_comparison.loc[
                            qc_comparison["table_name"].eq("sensor_linear_accelerometer"),
                            "patients_with_metadata_after_T1",
                        ].iloc[0]
                    )
                    if not qc_comparison.empty
                    else 0,
                ),
                ("General acc device windows", len(sensor_acc_qc_device)),
                ("Linear acc device windows", len(sensor_linear_qc_device)),
            ]
        )
        readme = load_text(PATHS["accelerometer_framework_readme"])
        if readme:
            st.markdown(readme)
        st.subheader("QC Comparison")
        show_dataframe(qc_comparison, height=180)

        acc_tabs = st.tabs(["General Accelerometer Metadata", "Linear Accelerometer Metadata"])
        with acc_tabs[0]:
            tomorrow_readme = load_text(PATHS["accelerometer_tomorrow_work_readme"])
            if tomorrow_readme:
                with st.expander("Accelerometer tomorrow work summary", expanded=True):
                    st.markdown(tomorrow_readme)
            readme = load_text(PATHS["sensor_accelerometer_qc_readme"])
            if readme:
                st.markdown(readme)
            st.subheader("Patient-Level QC")
            show_dataframe(sensor_acc_qc_patient, height=360)
            st.subheader("Device-Window QC")
            show_dataframe(sensor_acc_qc_device, height=360)
            st.subheader("Raw Accelerometer Phase 2A Targeted Sample")
            raw_readme = load_text(PATHS["accelerometer_raw_readme"])
            if raw_readme:
                st.markdown(raw_readme)
            st.caption(
                "First bounded raw-signal sample anchored to a known sensor_accelerometer metadata timestamp. "
                "This is manual fieldwork, not feature extraction."
            )
            show_dataframe(accelerometer_raw_sample, height=300)
            st.subheader("Raw Accelerometer JSON Keys")
            show_dataframe(accelerometer_raw_keys, height=180)
            with st.expander("Raw accelerometer targeted window summary"):
                show_dataframe(accelerometer_raw_window_summary, height=220)
            st.subheader("Raw Accelerometer 24h Local Pilot")
            pilot_readme = load_text(PATHS["accelerometer_24h_pilot_readme"])
            if pilot_readme:
                st.markdown(pilot_readme)
            if not accelerometer_24h_manifest.empty:
                row = accelerometer_24h_manifest.iloc[0]
                metric_row(
                    [
                        ("Pilot subject", row.get("Subject_ID_D", "")),
                        ("Downloaded rows", int(row.get("downloaded_rows", 0)) if pd.notna(row.get("downloaded_rows", pd.NA)) else 0),
                        ("Raw file MB", f"{float(row.get('raw_size_mb', 0)):.1f}" if pd.notna(row.get("raw_size_mb", pd.NA)) else ""),
                        (
                            "Signal file MB",
                            f"{float(row.get('signal_size_mb', 0)):.1f}" if pd.notna(row.get("signal_size_mb", pd.NA)) else "",
                        ),
                    ]
                )
                show_dataframe(accelerometer_24h_manifest, height=180)
            if not accelerometer_24h_chunk_log.empty:
                st.caption("Chunk-level download log. The million-row raw/signal files are kept on disk and are not loaded into Streamlit.")
                show_dataframe(accelerometer_24h_chunk_log.tail(30), height=260)
            with st.expander("24h pilot candidate scan"):
                show_dataframe(accelerometer_24h_candidate_scan, height=180)
            st.subheader("24h Local Signal Analysis")
            local_readme = load_text(PATHS["accelerometer_local_24h_readme"])
            if local_readme:
                st.markdown(local_readme)
            if not accelerometer_local_24h_features.empty:
                row = accelerometer_local_24h_features.iloc[0]
                metric_row(
                    [
                        ("Rows after QC", int(row.get("accelerometer_total_rows_loaded", 0))),
                        ("Duplicates removed", int(row.get("accelerometer_exact_duplicate_rows_removed", 0))),
                        ("Valid minutes", int(float(row.get("accelerometer_valid_signal_minutes", 0)))),
                        ("Still-phone minutes", int(float(row.get("accelerometer_still_phone_minutes", 0)))),
                        ("Handling minutes", int(float(row.get("accelerometer_phone_handling_minutes", 0)))),
                    ]
                )
                show_dataframe(accelerometer_local_24h_features, height=180)
            cols = st.columns(2)
            with cols[0]:
                st.subheader("Phone-State Candidate Summary")
                show_dataframe(accelerometer_local_24h_states, height=180)
            with cols[1]:
                st.subheader("Threshold Sensitivity")
                show_dataframe(accelerometer_local_24h_thresholds, height=240)
            st.subheader("Bandpass Candidate Feature Summary")
            st.caption(
                "Frequency-band outputs are phone-state candidates. Sampling feasibility is shown per band before interpreting candidate minutes."
            )
            show_dataframe(accelerometer_local_24h_bandpass_features, height=260)
            with st.expander("Bandpass candidate minutes by hour"):
                show_dataframe(accelerometer_local_24h_bandpass_hourly, height=320)
            st.subheader("Hourly Motion Summary")
            show_dataframe(accelerometer_local_24h_hourly, height=260)
            with st.expander("Top 20 chunks by dynamic magnitude"):
                if not accelerometer_local_24h_chunks.empty and "dynamic_magnitude_mean" in accelerometer_local_24h_chunks.columns:
                    top_chunks = accelerometer_local_24h_chunks.sort_values("dynamic_magnitude_mean", ascending=False).head(20)
                    show_dataframe(top_chunks, height=360)
                else:
                    show_dataframe(accelerometer_local_24h_chunks, height=360)
        with acc_tabs[1]:
            st.subheader("Patient-Level QC")
            show_dataframe(sensor_linear_qc_patient, height=360)
            st.subheader("Device-Window QC")
            show_dataframe(sensor_linear_qc_device, height=360)
    with tabs[8]:
        st.caption("This may be partial if a sampling run was stopped.")
        show_dataframe(sample_summary, height=520)


def phase3_algorithm_page() -> None:
    st.title("Phase 3 algorithm implementation")
    st.caption("Current selected-feature algorithms applied across T1 patients using the bounded T1-week 24-hour protocol.")

    long_df = load_csv(PATHS["phase3_all_t1_long"])
    wide_df = load_csv(PATHS["phase3_all_t1_wide"])
    status_df = load_csv(PATHS["phase3_all_t1_status"])
    coverage_df = load_csv(PATHS["phase3_all_t1_coverage"])
    acc_pilot_wide = load_csv(PATHS["phase3_accelerometer_pilot_wide"])
    acc_pilot_status = load_csv(PATHS["phase3_accelerometer_pilot_status"])
    acc_pilot_bandpass = load_csv(PATHS["phase3_accelerometer_pilot_bandpass"])
    acc_pilot_thresholds = load_csv(PATHS["phase3_accelerometer_pilot_thresholds"])
    acc_pilot_download = load_csv(PATHS["phase3_accelerometer_pilot_download"])

    if long_df.empty and wide_df.empty and status_df.empty:
        st.info("The all-patient selected-feature extraction output is not available yet.")
        st.code(".venv/bin/python3 phase2_extract_selected_features_all_t1_patients.py")
        return

    n_patients = wide_df["Subject_ID_D"].nunique() if not wide_df.empty and "Subject_ID_D" in wide_df.columns else 0
    n_features = long_df["feature_name"].nunique() if not long_df.empty and "feature_name" in long_df.columns else 0
    n_tables = status_df["table_name"].nunique() if not status_df.empty and "table_name" in status_df.columns else 0
    n_calculated = int(long_df["feature_status"].astype(str).eq("calculated").sum()) if "feature_status" in long_df.columns else 0
    n_total_feature_rows = len(long_df)
    pct_calculated = f"{100 * n_calculated / n_total_feature_rows:.1f}%" if n_total_feature_rows else "n/a"

    metric_row(
        [
            ("T1 patients processed", n_patients),
            ("Reviewed tables implemented", n_tables),
            ("Selected algorithms", n_features),
            ("Calculated feature values", n_calculated),
            ("Feature rows", n_total_feature_rows),
            ("Calculated share", pct_calculated),
        ]
    )

    st.subheader("Implementation Meaning")
    st.markdown(
        """
        This phase takes the features already selected during Phase 2 table review and applies them patient-by-patient.
        It is the first model-facing implementation layer: one long table for auditability and one wide table for future statistical modeling.

        Missing values mean the selected table did not have a protocol-valid 24-hour window for that patient/table, or the required feature signal was not available. Missing is not zero activity.
        """
    )

    tabs = st.tabs(
        [
            "Cohort Feature Overview",
            "Model-Ready Wide Table",
            "Patient-Table Status",
            "Coverage Audit",
            "Special Accelerometer Pilot",
            "README",
        ]
    )

    with tabs[0]:
        if long_df.empty:
            st.info("No long feature table available.")
        else:
            st.subheader("Calculated Values by Table")
            if {"table_name", "feature_status"}.issubset(long_df.columns):
                table_summary = (
                    long_df.assign(calculated=long_df["feature_status"].astype(str).eq("calculated"))
                    .groupby("table_name", dropna=False)
                    .agg(
                        calculated_feature_values=("calculated", "sum"),
                        total_feature_rows=("feature_name", "count"),
                        selected_features=("feature_name", "nunique"),
                        patients_seen=("Subject_ID_D", "nunique"),
                    )
                    .reset_index()
                )
                table_summary["calculated_percent"] = (
                    100 * table_summary["calculated_feature_values"] / table_summary["total_feature_rows"]
                ).round(1)
                show_dataframe(table_summary, height=320)
                st.bar_chart(table_summary.set_index("table_name")["calculated_feature_values"])

            st.subheader("Feature Availability")
            if {"feature_name", "feature_status", "table_name"}.issubset(long_df.columns):
                feature_summary = (
                    long_df.assign(calculated=long_df["feature_status"].astype(str).eq("calculated"))
                    .groupby(["table_name", "feature_name"], dropna=False)
                    .agg(
                        calculated_patients=("calculated", "sum"),
                        total_patients=("Subject_ID_D", "nunique"),
                    )
                    .reset_index()
                )
                feature_summary["calculated_percent"] = (
                    100 * feature_summary["calculated_patients"] / feature_summary["total_patients"]
                ).round(1)
                show_dataframe(feature_summary, height=420)

            st.subheader("Long Feature Table")
            show_dataframe(long_df, height=520)

    with tabs[1]:
        st.caption("One row per patient. Selected features become columns for later modeling.")
        show_dataframe(wide_df, height=620)

    with tabs[2]:
        st.caption("One row per patient-table showing whether the algorithm found a protocol-valid window and calculated values.")
        if not status_df.empty and "table_status" in status_df.columns:
            status_counts = status_df["table_status"].value_counts(dropna=False).reset_index()
            status_counts.columns = ["table_status", "n_patient_table_blocks"]
            show_dataframe(status_counts, height=180)
        show_dataframe(status_df, height=520)

    with tabs[3]:
        st.caption("Bounded coverage checks used to choose primary or fallback 24-hour T1-week windows.")
        show_dataframe(coverage_df, height=620)

    with tabs[4]:
        st.subheader("Special Accelerometer Phase 3 Pilot")
        st.caption("Isolated pilot only. These accelerometer rows are not merged into the shared Phase 3 matrix yet.")
        acc_readme = load_text(PATHS["phase3_accelerometer_pilot_readme"])
        if acc_readme:
            st.markdown(acc_readme)
        if not acc_pilot_status.empty:
            calculated = int(acc_pilot_status["table_status"].astype(str).eq("calculated").sum())
            attempted = len(acc_pilot_status)
            raw_rows = pd.to_numeric(acc_pilot_status.get("raw_rows_downloaded", pd.Series(dtype=str)), errors="coerce").fillna(0).sum()
            metric_row(
                [
                    ("Candidates attempted", attempted),
                    ("Calculated patients", calculated),
                    ("Raw rows downloaded", f"{int(raw_rows):,}"),
                    ("Feature rows", len(acc_pilot_wide)),
                ]
            )
        st.subheader("Pilot Patient Status")
        show_dataframe(acc_pilot_status, height=300)
        st.subheader("Pilot Feature Values")
        show_dataframe(acc_pilot_wide, height=220)
        st.subheader("Pilot Bandpass Summary")
        show_dataframe(acc_pilot_bandpass, height=320)
        with st.expander("Pilot threshold sensitivity"):
            show_dataframe(acc_pilot_thresholds, height=280)
        with st.expander("Pilot download chunk log"):
            show_dataframe(acc_pilot_download.tail(80), height=360)

    with tabs[5]:
        readme = load_text(PATHS["phase3_all_t1_readme"])
        st.markdown(readme if readme else "No README available yet.")


def rd_page() -> None:
    st.title("R&D")
    st.caption("Protocol experiments that test alternative acquisition rules without overwriting Phase 3 outputs.")

    calls_long = load_csv(PATHS["rd_calls_t1_week_long"])
    calls_wide = load_csv(PATHS["rd_calls_t1_week_wide"])
    calls_status = load_csv(PATHS["rd_calls_t1_week_status"])
    calls_2week_long = load_csv(PATHS["rd_calls_t1_2week_long"])
    calls_2week_wide = load_csv(PATHS["rd_calls_t1_2week_wide"])
    calls_2week_status = load_csv(PATHS["rd_calls_t1_2week_status"])
    calls_30day_long = load_csv(PATHS["rd_calls_t1_30day_long"])
    calls_30day_wide = load_csv(PATHS["rd_calls_t1_30day_wide"])
    calls_30day_status = load_csv(PATHS["rd_calls_t1_30day_status"])
    bluetooth_week_long = load_csv(PATHS["rd_bluetooth_t1_week_long"])
    bluetooth_week_wide = load_csv(PATHS["rd_bluetooth_t1_week_wide"])
    bluetooth_week_status = load_csv(PATHS["rd_bluetooth_t1_week_status"])
    bluetooth_30day_long = load_csv(PATHS["rd_bluetooth_t1_30day_long"])
    bluetooth_30day_wide = load_csv(PATHS["rd_bluetooth_t1_30day_wide"])
    bluetooth_30day_status = load_csv(PATHS["rd_bluetooth_t1_30day_status"])
    strict_long = load_csv(PATHS["phase3_all_t1_long"])
    strict_status = load_csv(PATHS["phase3_all_t1_status"])

    st.subheader("Calls: Window-Length R&D")
    st.markdown(
        """
        This pilot tests a relaxed acquisition rule for sparse event tables:
        use a longer post-T1 window and calculate call features if any `calls` rows exist.

        This is separate from the strict Phase 3 rule, which requires a protocol-valid 24-hour span.
        """
    )

    if (
        calls_long.empty
        and calls_status.empty
        and calls_2week_long.empty
        and calls_2week_status.empty
        and calls_30day_long.empty
        and calls_30day_status.empty
    ):
        st.info("R&D calls pilot outputs are not available yet.")
        st.code(".venv/bin/python3 phase3_rd_calls_t1_week_any_data_pilot.py")
        st.code(".venv/bin/python3 phase3_rd_calls_t1_2week_any_data_pilot.py")
        st.code(".venv/bin/python3 phase3_rd_calls_t1_30day_any_data_pilot.py")
        return

    rd_patients = calls_status["Subject_ID_D"].nunique() if "Subject_ID_D" in calls_status.columns else 0
    rd_calculated_patients = (
        int(calls_status["table_status"].astype(str).eq("calculated").sum())
        if "table_status" in calls_status.columns
        else 0
    )
    rd_calculated_features = (
        int(calls_long["feature_status"].astype(str).eq("calculated").sum())
        if "feature_status" in calls_long.columns
        else 0
    )
    rd_2week_patients = calls_2week_status["Subject_ID_D"].nunique() if "Subject_ID_D" in calls_2week_status.columns else 0
    rd_2week_calculated_patients = (
        int(calls_2week_status["table_status"].astype(str).eq("calculated").sum())
        if "table_status" in calls_2week_status.columns
        else 0
    )
    rd_2week_calculated_features = (
        int(calls_2week_long["feature_status"].astype(str).eq("calculated").sum())
        if "feature_status" in calls_2week_long.columns
        else 0
    )
    rd_30day_patients = calls_30day_status["Subject_ID_D"].nunique() if "Subject_ID_D" in calls_30day_status.columns else 0
    rd_30day_calculated_patients = (
        int(calls_30day_status["table_status"].astype(str).eq("calculated").sum())
        if "table_status" in calls_30day_status.columns
        else 0
    )
    rd_30day_calculated_features = (
        int(calls_30day_long["feature_status"].astype(str).eq("calculated").sum())
        if "feature_status" in calls_30day_long.columns
        else 0
    )

    strict_calls = pd.DataFrame()
    if not strict_long.empty and "table_name" in strict_long.columns:
        strict_calls = strict_long[strict_long["table_name"].astype(str) == "calls"].copy()
    strict_call_patients = (
        int(
            strict_status[
                (strict_status.get("table_name", pd.Series(dtype=str)).astype(str) == "calls")
                & (strict_status.get("table_status", pd.Series(dtype=str)).astype(str) == "calculated")
            ].shape[0]
        )
        if not strict_status.empty and {"table_name", "table_status"}.issubset(strict_status.columns)
        else 0
    )
    strict_call_feature_values = (
        int(strict_calls["feature_status"].astype(str).eq("calculated").sum())
        if not strict_calls.empty and "feature_status" in strict_calls.columns
        else 0
    )

    metric_row(
        [
            ("Patients tested", max(rd_patients, rd_2week_patients, rd_30day_patients)),
            ("Strict calls patients", strict_call_patients),
            ("1-week calls patients", rd_calculated_patients),
            ("2-week calls patients", rd_2week_calculated_patients),
            ("30-day calls patients", rd_30day_calculated_patients),
            ("30-day call values", rd_30day_calculated_features),
        ]
    )

    call_tabs = st.tabs(
        [
            "Comparison",
            "1-Week Long",
            "1-Week Wide",
            "1-Week Status",
            "2-Week Long",
            "2-Week Wide",
            "2-Week Status",
            "30-Day Long",
            "30-Day Wide",
            "30-Day Status",
            "README",
        ]
    )
    with call_tabs[0]:
        comparison = pd.DataFrame(
            [
                {
                    "rule": "strict_phase3_24h_valid_span",
                    "patients_with_calculated_calls": strict_call_patients,
                    "calculated_call_feature_values": strict_call_feature_values,
                    "window": "first valid 24h span inside T1 week",
                },
                {
                    "rule": "rd_t1_week_any_calls_data",
                    "patients_with_calculated_calls": rd_calculated_patients,
                    "calculated_call_feature_values": rd_calculated_features,
                    "window": "entire first week after T1 if any rows exist",
                },
                {
                    "rule": "rd_t1_2week_any_calls_data",
                    "patients_with_calculated_calls": rd_2week_calculated_patients,
                    "calculated_call_feature_values": rd_2week_calculated_features,
                    "window": "first 14 days after T1 if any rows exist",
                },
                {
                    "rule": "rd_t1_30day_any_calls_data",
                    "patients_with_calculated_calls": rd_30day_calculated_patients,
                    "calculated_call_feature_values": rd_30day_calculated_features,
                    "window": "first 30 days after T1 if any rows exist",
                },
            ]
        )
        show_dataframe(comparison, height=160)
        st.bar_chart(comparison.set_index("rule")["patients_with_calculated_calls"])

        if not calls_long.empty and {"feature_name", "feature_status", "Subject_ID_D"}.issubset(calls_long.columns):
            feature_summary = (
                calls_long.assign(calculated=calls_long["feature_status"].astype(str).eq("calculated"))
                .groupby("feature_name", dropna=False)
                .agg(calculated_patients=("calculated", "sum"), total_patients=("Subject_ID_D", "nunique"))
                .reset_index()
            )
            feature_summary["calculated_percent"] = (
                100 * feature_summary["calculated_patients"] / feature_summary["total_patients"]
            ).round(1)
            st.subheader("R&D Calls Feature Availability")
            show_dataframe(feature_summary, height=260)

    with call_tabs[1]:
        show_dataframe(calls_long, height=560)
    with call_tabs[2]:
        show_dataframe(calls_wide, height=560)
    with call_tabs[3]:
        show_dataframe(calls_status, height=560)
    with call_tabs[4]:
        show_dataframe(calls_2week_long, height=560)
    with call_tabs[5]:
        show_dataframe(calls_2week_wide, height=560)
    with call_tabs[6]:
        show_dataframe(calls_2week_status, height=560)
    with call_tabs[7]:
        show_dataframe(calls_30day_long, height=560)
    with call_tabs[8]:
        show_dataframe(calls_30day_wide, height=560)
    with call_tabs[9]:
        show_dataframe(calls_30day_status, height=560)
    with call_tabs[10]:
        st.markdown("### 1-Week Pilot")
        st.markdown(load_text(PATHS["rd_calls_t1_week_readme"]) or "No 1-week README available yet.")
        st.markdown("### 2-Week Pilot")
        st.markdown(load_text(PATHS["rd_calls_t1_2week_readme"]) or "No 2-week README available yet.")
        st.markdown("### 30-Day Pilot")
        st.markdown(load_text(PATHS["rd_calls_t1_30day_readme"]) or "No 30-day README available yet.")

    st.divider()
    st.subheader("Bluetooth: T1-Week and 30-Day Any-Data Pilots")
    st.markdown(
        """
        This pilot tests whether Bluetooth coverage improves when the first T1 week is used directly,
        instead of requiring a strict protocol-valid 24-hour span.
        """
    )

    if bluetooth_week_long.empty and bluetooth_week_status.empty and bluetooth_30day_long.empty and bluetooth_30day_status.empty:
        st.info("Bluetooth R&D pilot output is not available yet.")
        st.code(".venv/bin/python3 phase3_rd_bluetooth_t1_week_any_data_pilot.py")
        st.code(".venv/bin/python3 phase3_rd_bluetooth_t1_30day_any_data_pilot.py")
    else:
        strict_bluetooth = pd.DataFrame()
        if not strict_long.empty and "table_name" in strict_long.columns:
            strict_bluetooth = strict_long[strict_long["table_name"].astype(str) == "bluetooth"].copy()
        strict_bluetooth_patients = (
            int(
                strict_status[
                    (strict_status.get("table_name", pd.Series(dtype=str)).astype(str) == "bluetooth")
                    & (strict_status.get("table_status", pd.Series(dtype=str)).astype(str) == "calculated")
                ].shape[0]
            )
            if not strict_status.empty and {"table_name", "table_status"}.issubset(strict_status.columns)
            else 0
        )
        strict_bluetooth_values = (
            int(strict_bluetooth["feature_status"].astype(str).eq("calculated").sum())
            if not strict_bluetooth.empty and "feature_status" in strict_bluetooth.columns
            else 0
        )
        bluetooth_week_patients = (
            int(bluetooth_week_status["table_status"].astype(str).eq("calculated").sum())
            if "table_status" in bluetooth_week_status.columns
            else 0
        )
        bluetooth_week_values = (
            int(bluetooth_week_long["feature_status"].astype(str).eq("calculated").sum())
            if "feature_status" in bluetooth_week_long.columns
            else 0
        )
        bluetooth_30day_patients = (
            int(bluetooth_30day_status["table_status"].astype(str).eq("calculated").sum())
            if "table_status" in bluetooth_30day_status.columns
            else 0
        )
        bluetooth_30day_values = (
            int(bluetooth_30day_long["feature_status"].astype(str).eq("calculated").sum())
            if "feature_status" in bluetooth_30day_long.columns
            else 0
        )

        metric_row(
            [
                ("Strict Bluetooth patients", strict_bluetooth_patients),
                ("1-week Bluetooth patients", bluetooth_week_patients),
                ("30-day Bluetooth patients", bluetooth_30day_patients),
                ("1-week Bluetooth values", bluetooth_week_values),
                ("30-day Bluetooth values", bluetooth_30day_values),
            ]
        )

        bluetooth_tabs = st.tabs(
            [
                "Comparison",
                "1-Week Long",
                "1-Week Wide",
                "1-Week Status",
                "30-Day Long",
                "30-Day Wide",
                "30-Day Status",
                "README",
            ]
        )
        with bluetooth_tabs[0]:
            bluetooth_comparison = pd.DataFrame(
                [
                    {
                        "rule": "strict_phase3_24h_valid_span",
                        "patients_with_calculated_bluetooth": strict_bluetooth_patients,
                        "calculated_bluetooth_feature_values": strict_bluetooth_values,
                        "window": "first valid 24h span inside T1 week",
                    },
                    {
                        "rule": "rd_t1_week_any_bluetooth_data",
                        "patients_with_calculated_bluetooth": bluetooth_week_patients,
                        "calculated_bluetooth_feature_values": bluetooth_week_values,
                        "window": "entire first week after T1 if any rows exist",
                    },
                    {
                        "rule": "rd_t1_30day_any_bluetooth_data",
                        "patients_with_calculated_bluetooth": bluetooth_30day_patients,
                        "calculated_bluetooth_feature_values": bluetooth_30day_values,
                        "window": "first 30 days after T1 if any rows exist",
                    },
                ]
            )
            show_dataframe(bluetooth_comparison, height=160)
            st.bar_chart(bluetooth_comparison.set_index("rule")["patients_with_calculated_bluetooth"])

            if not bluetooth_week_long.empty and {"feature_name", "feature_status", "Subject_ID_D"}.issubset(
                bluetooth_week_long.columns
            ):
                feature_summary = (
                    bluetooth_week_long.assign(
                        calculated=bluetooth_week_long["feature_status"].astype(str).eq("calculated")
                    )
                    .groupby("feature_name", dropna=False)
                    .agg(calculated_patients=("calculated", "sum"), total_patients=("Subject_ID_D", "nunique"))
                    .reset_index()
                )
                feature_summary["calculated_percent"] = (
                    100 * feature_summary["calculated_patients"] / feature_summary["total_patients"]
                ).round(1)
                st.subheader("Bluetooth Feature Availability")
                show_dataframe(feature_summary, height=220)
        with bluetooth_tabs[1]:
            show_dataframe(bluetooth_week_long, height=560)
        with bluetooth_tabs[2]:
            show_dataframe(bluetooth_week_wide, height=560)
        with bluetooth_tabs[3]:
            show_dataframe(bluetooth_week_status, height=560)
        with bluetooth_tabs[4]:
            show_dataframe(bluetooth_30day_long, height=560)
        with bluetooth_tabs[5]:
            show_dataframe(bluetooth_30day_wide, height=560)
        with bluetooth_tabs[6]:
            show_dataframe(bluetooth_30day_status, height=560)
        with bluetooth_tabs[7]:
            st.markdown("### 1-Week Pilot")
            st.markdown(load_text(PATHS["rd_bluetooth_t1_week_readme"]) or "No Bluetooth README available yet.")
            st.markdown("### 30-Day Pilot")
            st.markdown(load_text(PATHS["rd_bluetooth_t1_30day_readme"]) or "No Bluetooth 30-day README available yet.")


def neurotrax_page() -> None:
    st.title("NeuroTrax Columns and Analysis Targets")
    candidates = load_csv(PATHS["cognitive_candidates"])
    master = load_csv(PATHS["cognitive_master"])

    if candidates.empty and master.empty:
        st.info("NeuroTrax files are not available.")
        return

    st.subheader("Main Columns for Future Analysis")
    main_cols = [
        "Subject_ID_N",
        "Subject_ID_D",
        "age",
        "Gender (1=M, 2=F)",
        "Education (years)",
        "T1_date_iso",
        "T2_date_iso",
        "global_T1",
        "global_T2",
        "global_delta",
        "memory_T1",
        "memory_T2",
        "memory_delta",
        "ef_T1",
        "ef_T2",
        "ef_delta",
        "attention_T1",
        "attention_T2",
        "attention_delta",
        "processing_speed_T1",
        "processing_speed_T2",
        "processing_speed_delta",
        "verbal_T1",
        "verbal_T2",
        "verbal_delta",
        "motor_T1",
        "motor_T2",
        "motor_delta",
        "iq_T1",
        "iq_T2",
        "iq_delta",
    ]
    available_main = [c for c in main_cols if c in candidates.columns]
    st.dataframe(pd.DataFrame({"column_name": available_main}), use_container_width=True, height=260)

    st.subheader("Candidate Cognitive Table Preview")
    show_dataframe(candidates[available_main] if available_main else candidates, height=420)

    st.subheader("All NeuroTrax Master Headers")
    query = st.text_input("Filter NeuroTrax headers", "")
    headers = master.columns.astype(str).tolist()
    if query:
        headers = [h for h in headers if query.lower() in h.lower()]
    show_dataframe(pd.DataFrame({"column_name": headers}), height=520)


def rich_wide_page() -> None:
    st.title("Rich Phase 1 Wide Table")
    rich = load_csv(PATHS["rich_wide"])
    if rich.empty:
        st.info("Rich wide table is not available.")
        return

    metric_row(
        [
            ("Rows", rich.shape[0]),
            ("Columns", rich.shape[1]),
            ("Subjects", rich["Subject_ID_D"].nunique() if "Subject_ID_D" in rich else 0),
        ]
    )

    st.subheader("Column Search")
    query = st.text_input("Filter columns", "")
    cols = rich.columns.tolist()
    if query:
        cols = [c for c in cols if query.lower() in c.lower()]
    st.write(f"{len(cols)} matching columns")
    st.code("\n".join(cols[:250]))

    st.subheader("Table Preview")
    show_cols = st.multiselect("Columns to display", rich.columns.tolist(), default=rich.columns[:12].tolist())
    if show_cols:
        show_dataframe(rich[show_cols], height=480)


def samples_page() -> None:
    st.title("Manual SQL Samples")
    sample_rows = load_csv(PATHS["sample_rows"])
    sample_summary = load_csv(PATHS["sample_summary"])

    st.caption("Manual-review samples only. These are not feature extraction outputs.")
    show_dataframe(sample_summary, height=260)

    if sample_rows.empty:
        st.info("No sample rows are available.")
        return

    table_options = ["All"] + sorted(sample_rows["table_name"].dropna().astype(str).unique().tolist())
    selected_table = st.selectbox("Sample table", table_options)
    view = sample_rows if selected_table == "All" else sample_rows[sample_rows["table_name"].astype(str) == selected_table]
    show_dataframe(view, height=520)


def files_page() -> None:
    st.title("Project Files")
    rows = []
    for name, path in PATHS.items():
        rows.append(
            {
                "name": name,
                "status": file_status(path),
                "path": str(path.relative_to(ROOT)),
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
        )
    show_dataframe(pd.DataFrame(rows), height=520)


PAGES = {
    "Overview": overview_page,
    "Phase 1 Profiles": phase1_profiles_page,
    "Phase 1 Change": phase1_change_page,
    "NeuroTrax Columns": neurotrax_page,
    "Rich Wide Table": rich_wide_page,
    "Phase 2 Tables": phase2_tables_page,
    "Phase 3 algorithm implementation": phase3_algorithm_page,
    "R&D": rd_page,
    "SQL Samples": samples_page,
    "Files": files_page,
}


def main() -> None:
    st.sidebar.title("NeuroTrax-SensorDB")
    page = st.sidebar.radio("View", list(PAGES.keys()))
    st.sidebar.divider()
    st.sidebar.caption("Local dashboard over existing project outputs.")
    st.sidebar.caption("No SQL queries are executed by this app.")
    PAGES[page]()


if __name__ == "__main__":
    main()
