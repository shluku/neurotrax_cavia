"""Interactive read-only explorer over existing phenotype outputs."""

from __future__ import annotations

from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


DOMAINS = ["Memory", "Executive function", "Processing speed", "Attention", "Motor"]
DOMAIN_LABELS = {"Global": "Global cognitive", **{domain: domain for domain in DOMAINS}}
MODEL_LABELS = {
    "mean_baseline_prediction": "Mean baseline",
    "group_ridge_prediction": "Domain feature-group Ridge",
    "ridge_prediction": "Primary Ridge",
    "gradient_weighted_prediction": "Gradient-weighted Ridge",
    "slope_selected_prediction": "Slope-selected Ridge",
    "direction_constrained_prediction": "Direction-constrained Ridge",
    "all_direction_constrained_prediction": "All-feature direction-constrained Ridge",
    "elastic_net_prediction": "Elastic Net",
    "pls_prediction": "PLS",
    "spline_ridge_prediction": "Spline Ridge",
    "random_forest_prediction": "Random Forest",
    "extra_trees_prediction": "Extra Trees",
    "hist_gradient_boosting_prediction": "HistGradientBoosting",
    "xgboost_prediction": "XGBoost",
}
MODEL_COLORS = {
    "mean_baseline_prediction": "#6b7280",
    "group_ridge_prediction": "#dc2626",
    "ridge_prediction": "#2563eb",
    "gradient_weighted_prediction": "#d97706",
    "slope_selected_prediction": "#7c3aed",
    "direction_constrained_prediction": "#0891b2",
    "all_direction_constrained_prediction": "#0f766e",
    "elastic_net_prediction": "#16a34a",
    "pls_prediction": "#ea580c",
    "spline_ridge_prediction": "#9333ea",
    "random_forest_prediction": "#15803d",
    "extra_trees_prediction": "#0e7490",
    "hist_gradient_boosting_prediction": "#dc2626",
    "xgboost_prediction": "#7c2d12",
}


def _csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"Subject_ID_D": str, "Subject_ID_N": str})


def _source_paths(root: Path, source: str) -> dict[str, Path]:
    phase4 = root / "output/analysis_candidates/phase4_t1_baseline"
    phase4_10 = root / "output/analysis_candidates/phase4_10day_t1_baseline"
    phase6 = root / "output/analysis_candidates/phase6_t1_t2_decline"
    phase6_10 = root / "output/analysis_candidates/phase6_10day_t1_t2_decline"
    if source == "Phase 4 24-hour T1 baseline":
        base = phase4
        return {
            "kind": "t1",
            "base": base / "phase4_t1_baseline_patient_dataset.csv",
            "domain": base / "model_t1_cognitive_domains/phase4_t1_cognitive_domain_patient_predictions.csv",
            "group": base / "model_t1_cognitive_domain_groups/phase4_t1_cognitive_domain_group_patient_predictions.csv",
            "global": [
                base / "model_t1_ridge/phase4_t1_score_calibration_by_patient.csv",
                base / "model_t1_gradient_weighted/phase4_t1_gradient_weighted_patient_predictions.csv",
                base / "model_t1_slope_selected/phase4_t1_slope_selected_patient_predictions.csv",
                base / "model_t1_direction_constrained/phase4_t1_direction_constrained_patient_predictions.csv",
                base / "model_t1_alternatives/phase4_t1_alternative_patient_predictions.csv",
            ],
        }
    if source == "Suggestions: 10-day coverage cohorts":
        return {
            "kind": "t1_suggestions",
            "base": phase4_10 / "phase4_10day_t1_baseline_patient_dataset.csv",
            "domain": phase4_10 / "suggestions/suggestions_10day_cognitive_domain_patient_predictions.csv",
            "group": None,
            "suggestion_global": phase4_10 / "suggestions/suggestions_10day_coverage_patient_predictions.csv",
        }
    if source == "Phase 4 10-day T1 baseline":
        base = phase4_10
        return {
            "kind": "t1",
            "base": base / "phase4_10day_t1_baseline_patient_dataset.csv",
            "domain": base / "model_t1_cognitive_domains/phase4_t1_cognitive_domain_patient_predictions.csv",
            "group": base / "model_t1_cognitive_domain_groups/phase4_t1_cognitive_domain_group_patient_predictions.csv",
            "global": [
                base / "model_t1_ridge/phase4_t1_score_calibration_by_patient.csv",
                base / "model_t1_gradient_weighted/phase4_t1_gradient_weighted_patient_predictions.csv",
                base / "model_t1_slope_selected/phase4_t1_slope_selected_patient_predictions.csv",
                base / "model_t1_direction_constrained/phase4_t1_direction_constrained_patient_predictions.csv",
                base / "model_t1_all_direction_constrained/phase4_10day_all_direction_constrained_patient_predictions.csv",
                base / "model_t1_alternatives/phase4_t1_alternative_patient_predictions.csv",
                base / "other_models/phase4_10day_other_models_patient_predictions.csv",
            ],
        }
    if source == "Phase 6 24-hour T1-T2":
        return {
            "kind": "t2",
            "base": phase4 / "phase4_t1_baseline_patient_dataset.csv",
            "decline": phase6 / "phase6_t1_t2_decline_patient_predictions.csv",
        }
    return {
        "kind": "t2",
        "base": phase4_10 / "phase4_10day_t1_baseline_patient_dataset.csv",
        "decline": phase6_10 / "phase6_10day_t1_t2_decline_patient_predictions.csv",
    }


def _add_coverage(base: pd.DataFrame) -> pd.DataFrame:
    frame = base.copy()
    if frame.empty:
        return frame
    for column, default in [
        ("baseline_feature_missing_fraction", 1.0),
        ("baseline_table_coverage_fraction", 0.0),
    ]:
        if column not in frame.columns:
            frame[column] = default
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(default)
    frame = frame.sort_values(
        ["baseline_feature_missing_fraction", "baseline_table_coverage_fraction", "Subject_ID_D"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    frame["coverage_rank"] = range(1, len(frame) + 1)
    n = len(frame)
    frame["coverage_band"] = np.select(
        [frame["coverage_rank"] <= max(1, int(np.ceil(n * 0.25))), frame["coverage_rank"] <= max(1, int(np.ceil(n * 0.75)))],
        ["Highest coverage quartile", "Middle coverage"],
        default="Lowest coverage quartile",
    )
    return frame


def _merge_coverage(frame: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    coverage_cols = [
        "Subject_ID_D", "Subject_ID_N", "baseline_feature_missing_fraction",
        "baseline_table_coverage_fraction", "coverage_rank", "coverage_band",
    ]
    available = [column for column in coverage_cols if column in base.columns]
    return frame.merge(base[available].drop_duplicates("Subject_ID_D"), on="Subject_ID_D", how="left")


def _t1_wide(root: Path, source: str, outcome: str) -> pd.DataFrame:
    paths = _source_paths(root, source)
    base = _add_coverage(_csv(paths["base"]))
    if base.empty:
        return pd.DataFrame()
    if outcome == "Global":
        wide = base[["Subject_ID_D", "Subject_ID_N", "global_T1", "baseline_feature_missing_fraction", "baseline_table_coverage_fraction", "coverage_rank", "coverage_band"]].rename(columns={"global_T1": "observed"})
        if paths["kind"] == "t1_suggestions":
            predictions = _csv(paths["suggestion_global"])
            keep = ["Subject_ID_D", "Subject_ID_N", "cohort_size", "actual_global_T1"] + [column for column in predictions.columns if column.endswith("_prediction")]
            return _merge_coverage(predictions[keep].rename(columns={"actual_global_T1": "observed"}), base)
        for path in paths["global"]:
            predictions = _csv(path)
            if predictions.empty:
                continue
            prediction_columns = [column for column in predictions.columns if column.endswith("_prediction")]
            if not prediction_columns:
                continue
            keep = ["Subject_ID_D"] + [column for column in prediction_columns if column not in wide.columns]
            if len(keep) == 1:
                continue
            wide = wide.merge(predictions[keep], on="Subject_ID_D", how="left")
        return wide

    domain_predictions = _csv(paths["domain"])
    if domain_predictions.empty:
        return pd.DataFrame()
    domain_predictions = domain_predictions[domain_predictions["domain"].astype(str).eq(outcome)].copy()
    if domain_predictions.empty:
        return pd.DataFrame()
    domain_columns = ["Subject_ID_D", "Subject_ID_N", "actual_T1", "mean_baseline_prediction", "ridge_prediction"]
    if "group_ridge_prediction" in domain_predictions.columns:
        domain_columns.append("group_ridge_prediction")
    wide = domain_predictions[domain_columns].rename(
        columns={"actual_T1": "observed", "ridge_prediction": "ridge_prediction"}
    )
    if paths.get("group") is not None:
        group = _csv(paths["group"])
        if not group.empty:
            group = group[group["domain"].astype(str).eq(outcome)]
            if not group.empty:
                wide = wide.merge(group[["Subject_ID_D", "group_ridge_prediction"]], on="Subject_ID_D", how="left")
    return _merge_coverage(wide, base)


def _t2_wide(root: Path, source: str, outcome: str) -> pd.DataFrame:
    paths = _source_paths(root, source)
    decline = _csv(paths["decline"])
    if decline.empty:
        return pd.DataFrame()
    decline = decline[decline["outcome"].astype(str).eq(outcome)].copy()
    if decline.empty:
        return pd.DataFrame()
    id_columns = ["Subject_ID_D", "observed_T1", "observed_T2", "actual_change"]
    wide = decline.groupby("Subject_ID_D", as_index=False)[id_columns[1:]].first()
    for model in sorted(decline["model"].dropna().astype(str).unique()):
        model_frame = decline[decline["model"].astype(str).eq(model)].drop_duplicates("Subject_ID_D")
        model_key = "".join(character if character.isalnum() else "_" for character in model).strip("_")
        wide = wide.merge(
            model_frame[["Subject_ID_D", "estimated_T1", "estimated_T2", "estimated_change"]].rename(
                columns={
                    "estimated_T1": f"estimated_T1__{model_key}",
                    "estimated_T2": f"estimated_T2__{model_key}",
                    "estimated_change": f"estimated_change__{model_key}",
                }
            ),
            on="Subject_ID_D",
            how="left",
        )
    return _merge_coverage(wide, _add_coverage(_csv(paths["base"])))


def _quartile_filter(frame: pd.DataFrame, column: str, selected: list[str]) -> pd.Series:
    if not selected or "All" in selected:
        return pd.Series(True, index=frame.index)
    values = pd.to_numeric(frame[column], errors="coerce")
    q1, q2, q3 = values.quantile([0.25, 0.5, 0.75]).tolist()
    masks = {
        "Low": values <= q1,
        "Lower-middle": (values > q1) & (values <= q2),
        "Upper-middle": (values > q2) & (values <= q3),
        "High": values > q3,
    }
    result = pd.Series(False, index=frame.index)
    for label in selected:
        result |= masks.get(label, False)
    return result


def _focused_domain(values: pd.Series) -> list[float]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return [0.0, 1.0]
    low, high = float(numeric.min()), float(numeric.max())
    padding = max(0.5, (high - low) * 0.08)
    if low == high:
        padding = max(1.0, abs(low) * 0.05)
    return [low - padding, high + padding]


def _plot_lines(frame: pd.DataFrame, line_columns: list[tuple[str, str, str]], order_column: str, title: str) -> None:
    if frame.empty:
        st.info("No patients match the selected filters.")
        return
    ordered = frame.sort_values(order_column, na_position="last").reset_index(drop=True).copy()
    ordered["patient_rank"] = range(1, len(ordered) + 1)
    lines = []
    for column, label, color in line_columns:
        if column not in ordered.columns:
            continue
        lines.append(ordered[["patient_rank", "Subject_ID_D", column]].rename(columns={column: "value"}).assign(measure=label, color=color))
    if not lines:
        st.info("No selected measures are available for this graph.")
        return
    plot = pd.concat(lines, ignore_index=True).dropna(subset=["value"])
    chart = (
        alt.Chart(plot)
        .mark_line(point=alt.OverlayMarkDef(size=48))
        .encode(
            x=alt.X("patient_rank:Q", title=f"{title} patient order", axis=alt.Axis(format="d"), scale=alt.Scale(domain=[0.5, len(ordered) + 0.5])),
            y=alt.Y("value:Q", title="Score", scale=alt.Scale(domain=_focused_domain(plot["value"]))),
            color=alt.Color("measure:N", title="Measure", scale=alt.Scale(domain=[row[1] for row in line_columns], range=[row[2] for row in line_columns])),
            order=alt.Order("patient_rank:Q", sort="ascending"),
            tooltip=[
                alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                alt.Tooltip("Subject_ID_D:N", title="Patient ID"),
                alt.Tooltip("measure:N", title="Measure"),
                alt.Tooltip("value:Q", title="Value", format=".2f"),
            ],
        )
        .properties(title=title, height=410)
    )
    st.altair_chart(chart, use_container_width=True)


def render_result_explorer(root: Path) -> None:
    st.markdown(
        '<h1 style="font-size: 2.6rem; font-weight: 800; margin-bottom: 0.25rem;">Result Explorer</h1>',
        unsafe_allow_html=True,
    )
    st.caption("Build a custom descriptive view from the existing T1, T2, coverage, domain, and model outputs.")
    sources = [
        "Phase 4 24-hour T1 baseline",
        "Phase 4 10-day T1 baseline",
        "Suggestions: 10-day coverage cohorts",
        "Phase 6 24-hour T1-T2",
        "Phase 6 10-day T1-T2",
    ]
    source_preview = st.selectbox("Data source", sources)
    source_kind = _source_paths(root, source_preview)["kind"]
    is_t2 = source_kind == "t2"
    outcome_options = ["Global"] + DOMAINS if is_t2 else ["Global"] + DOMAINS
    available_models = []
    if is_t2:
        decline = _csv(_source_paths(root, source_preview)["decline"])
        available_models = sorted(decline["model"].dropna().astype(str).unique().tolist()) if not decline.empty else []
    else:
        probe = _t1_wide(root, source_preview, "Global")
        available_models = [column for column in probe.columns if column.endswith("_prediction")]
        if "group_ridge_prediction" not in available_models:
            available_models.append("group_ridge_prediction")

    with st.form("result_explorer_form"):
        selected_outcomes = st.multiselect("Outcomes or cognitive domains", outcome_options, default=["Global"])
        if is_t2:
            selected_models = st.multiselect("Statistical models", available_models, default=available_models[:1], format_func=lambda value: value)
            selected_measures = st.multiselect(
                "Lines to plot",
                ["Observed T1", "Observed T2", "Observed change", "Estimated T1", "Estimated T2", "Estimated change"],
                default=["Observed T1", "Observed T2", "Estimated T2"],
            )
        else:
            selected_models = st.multiselect(
                "Statistical models",
                available_models,
                default=available_models[:1],
                format_func=lambda value: MODEL_LABELS.get(value, value),
            )
            selected_measures = []
        coverage_options = ["All available", "Top 10", "Top 20", "Top 30"]
        selected_coverage = st.multiselect("Coverage cohort", coverage_options, default=["All available"])
        coverage_band = st.multiselect(
            "Coverage band",
            ["All", "Highest coverage quartile", "Middle coverage", "Lowest coverage quartile"],
            default=["All"],
        )
        t1_category = st.multiselect("T1 level", ["All", "Low", "Lower-middle", "Upper-middle", "High"], default=["All"])
        if is_t2:
            change_category = st.multiselect(
                "T1-to-T2 category",
                ["All", "Declined", "Stable or improved", "Strong decline", "Strong improvement"],
                default=["All"],
            )
        else:
            change_category = ["All"]
        max_missing = st.slider("Maximum feature missingness (%)", min_value=0, max_value=100, value=100)
        order_by = st.selectbox("Patient order", ["Observed score", "Coverage rank", "Patient ID"])
        submitted = st.form_submit_button("PLOT")

    if not submitted:
        st.info("Choose the variables, then press PLOT.")
        return
    if not selected_outcomes:
        st.warning("Select at least one outcome or cognitive domain.")
        return
    if is_t2 and not selected_models:
        st.warning("Select at least one statistical model.")
        return

    for outcome in selected_outcomes:
        frame = _t2_wide(root, source_preview, outcome) if is_t2 else _t1_wide(root, source_preview, outcome)
        if frame.empty:
            st.info(f"{DOMAIN_LABELS.get(outcome, outcome)} is not available for this source.")
            continue
        if "cohort_size" in frame.columns and "All available" not in selected_coverage:
            allowed_sizes = [int(value.split()[-1]) for value in selected_coverage if value != "All available"]
            frame = frame[frame["cohort_size"].isin(allowed_sizes)]
        elif "cohort_size" in frame.columns:
            frame = frame[frame["cohort_size"].eq(frame["cohort_size"].max())]
        elif "All available" not in selected_coverage:
            allowed_sizes = [int(value.split()[-1]) for value in selected_coverage if value != "All available"]
            frame = frame[frame["coverage_rank"].le(max(allowed_sizes))]
        if coverage_band and "All" not in coverage_band:
            frame = frame[frame["coverage_band"].isin(coverage_band)]
        frame = frame[pd.to_numeric(frame["baseline_feature_missing_fraction"], errors="coerce").le(max_missing / 100)]
        frame = frame[_quartile_filter(frame, "observed" if not is_t2 else "observed_T1", t1_category)]
        if is_t2 and change_category and "All" not in change_category:
            change = pd.to_numeric(frame["actual_change"], errors="coerce")
            q25, q75 = change.quantile([0.25, 0.75]).tolist()
            mask = pd.Series(False, index=frame.index)
            for category in change_category:
                if category == "Declined":
                    mask |= change < 0
                elif category == "Stable or improved":
                    mask |= change >= 0
                elif category == "Strong decline":
                    mask |= change <= q25
                elif category == "Strong improvement":
                    mask |= change >= q75
            frame = frame[mask]
        if frame.empty:
            st.info(f"No patients match the filters for {DOMAIN_LABELS.get(outcome, outcome)}.")
            continue
        st.subheader(DOMAIN_LABELS.get(outcome, outcome))
        metric_row = st.columns(4)
        metric_row[0].metric("Patients", len(frame))
        metric_row[1].metric("Mean missingness", f"{100 * frame['baseline_feature_missing_fraction'].mean():.1f}%")
        metric_row[2].metric("Observed T1 SD", f"{pd.to_numeric(frame['observed' if not is_t2 else 'observed_T1'], errors='coerce').std():.2f}")
        metric_row[3].metric("Mean coverage", f"{100 * frame['baseline_table_coverage_fraction'].mean():.1f}%")
        order_column = "coverage_rank" if order_by == "Coverage rank" else "Subject_ID_D" if order_by == "Patient ID" else "observed" if not is_t2 else "observed_T1"
        if is_t2:
            line_columns = []
            if "Observed T1" in selected_measures:
                line_columns.append(("observed_T1", "Observed T1", "#111827"))
            if "Observed T2" in selected_measures:
                line_columns.append(("observed_T2", "Observed T2", "#dc2626"))
            if "Observed change" in selected_measures:
                line_columns.append(("actual_change", "Observed change", "#111827"))
            model_key = {model: "".join(character if character.isalnum() else "_" for character in model).strip("_") for model in selected_models}
            for measure, prefix, color in [("Estimated T1", "estimated_T1", "#2563eb"), ("Estimated T2", "estimated_T2", "#2563eb"), ("Estimated change", "estimated_change", "#2563eb")]:
                if measure in selected_measures:
                    for model in selected_models:
                        line_columns.append((f"{prefix}__{model_key[model]}", f"{measure}: {model}", color))
        else:
            line_columns = [("observed", "Observed T1", "#111827")]
            if "Mean baseline" in selected_models:
                line_columns.append(("mean_baseline_prediction", "Mean baseline", "#6b7280"))
            line_columns.extend(
                (model, MODEL_LABELS.get(model, model), MODEL_COLORS.get(model, "#2563eb"))
                for model in selected_models
            )
        _plot_lines(frame, line_columns, order_column, f"{DOMAIN_LABELS.get(outcome, outcome)} result explorer")
        with st.expander("Filtered statistics and data"):
            show = frame.copy()
            show["coverage_percentile"] = (100 * (1 - show["coverage_rank"] / max(1, len(show)))).round(1)
            st.dataframe(show, use_container_width=True, height=300)
