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
    "phase2_tracking": ROOT / "phase2_table_tracking.csv",
    "phase2_feature_plan": ROOT / "phase2_candidate_feature_plan.csv",
    "phase2_selected_features": ROOT / "phase2_selected_features.csv",
    "phase2_highest_t1_calculated_feature_values": ROOT / "phase2_highest_t1_calculated_feature_values.csv",
    "phase2_exploratory_feature_dir": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/exploratory_t1_week_24h",
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
    [data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(2) p,
    [data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(3) p,
    [data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(6) p {
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
    review_dir = PATHS["phase2_table_feature_reviews"]
    if not review_dir.exists():
        return {}
    return {path.stem: path for path in sorted(review_dir.glob("*.md"))}


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
    st.title("Phase 2 Table Tracking")
    tracking = load_csv(PATHS["phase2_tracking"])
    inventory = load_csv(PATHS["table_inventory"])
    sample_summary = load_csv(PATHS["sample_summary"])
    feature_plan = load_csv(PATHS["phase2_feature_plan"])
    selected_features = load_csv(PATHS["phase2_selected_features"])
    highest_t1_calculated_values = load_csv(PATHS["phase2_highest_t1_calculated_feature_values"])
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
            ("Reviewed table files", len(table_reviews)),
            ("Selected features", len(selected_features)),
            ("Inventory rows", len(inventory)),
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
    with tabs[1]:
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
        st.caption("This may be partial if a sampling run was stopped.")
        show_dataframe(sample_summary, height=520)


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
