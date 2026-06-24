from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


BASE_DIR = Path("output/analysis_candidates/phase1_features")
INPUT_WIDE = BASE_DIR / "extracted" / "phase1_digital_phenotype_wide_rich.csv"
INPUT_RANKS = BASE_DIR / "descriptive_profiles" / "phase1_baseline_feature_ranks.csv"
INPUT_INTERPRETATION = BASE_DIR / "descriptive_profiles" / "phase1_subject_interpretation_summary.csv"
INPUT_USABILITY = BASE_DIR / "extracted" / "phase1_subject_usability_summary.csv"
OUT_DIR = BASE_DIR / "phenotype_profiles"


AXES = {
    "phone_engagement": {
        "features": [
            "screen_early_event_count",
            "app_early_foreground_event_count",
        ],
        "meaning": "relative early-window phone/app event engagement",
    },
    "nighttime_phone_activity": {
        "features": [
            "screen_early_night_event_count",
        ],
        "meaning": "relative early-window nighttime screen activity",
    },
    "app_use_breadth": {
        "features": [
            "app_early_unique_foreground_apps",
            "app_early_app_use_diversity",
        ],
        "meaning": "relative early-window app breadth and diversity",
    },
    "active_phone_interaction": {
        "features": [
            "keyboard_early_event_count",
            "touch_early_event_count",
        ],
        "meaning": "relative early-window keyboard and touch interaction",
    },
    "physical_activity_context": {
        "features": [
            "activity_early_event_count",
            "activity_early_still_event_count",
            "activity_early_walking_event_count",
            "activity_early_in_vehicle_event_count",
        ],
        "meaning": "relative early-window activity-recognition context signal",
    },
    "data_quality_support": {
        "features": [
            "aware_log_early_rows",
        ],
        "optional_features": [
            "aware_log_early_active_days",
        ],
        "meaning": "relative logging support for data availability; not a behavior axis",
    },
}


CHANGE_FAMILIES = {
    "screen": {
        "early": ["screen_early_event_count"],
        "late": ["screen_late_event_count"],
        "delta": ["screen_delta_event_count"],
        "pct": ["screen_pct_change_event_count"],
        "status": "screen_delta_status",
        "role": "behavior",
    },
    "app": {
        "early": ["app_early_foreground_event_count"],
        "late": ["app_late_foreground_event_count"],
        "delta": ["app_delta_foreground_event_count"],
        "pct": ["app_pct_change_foreground_event_count"],
        "status": "app_delta_status",
        "role": "behavior",
    },
    "keyboard": {
        "early": ["keyboard_early_event_count"],
        "late": ["keyboard_late_event_count"],
        "delta": ["keyboard_delta_event_count"],
        "pct": ["keyboard_pct_change_event_count"],
        "status": "keyboard_delta_status",
        "role": "behavior",
    },
    "touch": {
        "early": ["touch_early_event_count"],
        "late": ["touch_late_event_count"],
        "delta": ["touch_delta_event_count"],
        "pct": ["touch_pct_change_event_count"],
        "status": "touch_delta_status",
        "role": "behavior",
    },
    "activity": {
        "early": [
            "activity_early_event_count",
            "activity_early_still_event_count",
            "activity_early_walking_event_count",
            "activity_early_in_vehicle_event_count",
        ],
        "late": [
            "activity_late_event_count",
            "activity_late_still_event_count",
            "activity_late_walking_event_count",
            "activity_late_in_vehicle_event_count",
        ],
        "delta": ["activity_delta_event_count"],
        "pct": ["activity_pct_change_event_count"],
        "status": "activity_delta_status",
        "role": "behavior",
    },
    "aware_log": {
        "early": ["aware_log_early_rows"],
        "late": ["aware_log_late_rows"],
        "delta": ["aware_log_delta_rows"],
        "pct": [],
        "status": "aware_log_delta_status",
        "role": "data_quality_support",
    },
}


def normalize_subject_id_d(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    return s.zfill(3) if s.isdigit() else s


def to_bool(value) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def format_value(value) -> str:
    if pd.isna(value):
        return "NA"
    if isinstance(value, (float, np.floating)):
        if float(value).is_integer():
            return str(int(value))
        return f"{float(value):.3g}"
    return str(value)


def join_feature_values(row: pd.Series, columns: Iterable[str]) -> str:
    parts = []
    for col in columns:
        if col in row.index:
            parts.append(f"{col}={format_value(row.get(col))}")
    return "; ".join(parts) if parts else "not_available"


def percentile_level(series: pd.Series) -> pd.Series:
    out = pd.Series("insufficient_data", index=series.index, dtype="object")
    valid = pd.to_numeric(series, errors="coerce").notna()
    if valid.sum() == 0:
        return out
    pct = pd.to_numeric(series[valid], errors="coerce").rank(pct=True, method="average") * 100
    out.loc[pct.index[pct < 33.3333]] = "low"
    out.loc[pct.index[(pct >= 33.3333) & (pct < 66.6667)]] = "medium"
    out.loc[pct.index[pct >= 66.6667]] = "high"
    return out


def feature_percentiles(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    pct_df = pd.DataFrame(index=df.index)
    for feature in features:
        values = pd.to_numeric(df[feature], errors="coerce")
        pct_df[feature] = values.rank(pct=True, method="average") * 100
    return pct_df


def classify_axis(
    full_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    axis_name: str,
    feature_cols: list[str],
) -> tuple[pd.Series, pd.Series, list[str]]:
    missing_cols = [c for c in feature_cols if c not in full_df.columns]
    levels = pd.Series("insufficient_data", index=full_df.index, dtype="object")
    scores = pd.Series(np.nan, index=full_df.index, dtype="float64")
    if missing_cols:
        return levels, scores, missing_cols

    complete_baseline = baseline_df[feature_cols].apply(pd.to_numeric, errors="coerce").notna().all(axis=1)
    if complete_baseline.sum() == 0:
        return levels, scores, []

    baseline_complete = baseline_df.loc[complete_baseline, feature_cols].copy()
    baseline_scores = feature_percentiles(baseline_complete, feature_cols).mean(axis=1)
    baseline_levels = percentile_level(baseline_scores)
    levels.loc[baseline_scores.index] = baseline_levels
    scores.loc[baseline_scores.index] = baseline_scores
    return levels, scores, []


def behavior_label(row: pd.Series) -> str:
    if not bool(row.get("phase1_baseline_usable")):
        return "insufficient Phase 1 baseline data"

    available_axes = [
        ("phone engagement", row.get("phone_engagement_level")),
        ("nighttime phone activity", row.get("nighttime_phone_activity_level")),
        ("app-use breadth", row.get("app_use_breadth_level")),
        ("active phone interaction", row.get("active_phone_interaction_level")),
        ("physical activity context", row.get("physical_activity_context_level")),
    ]
    interpretable = [(name, level) for name, level in available_axes if level in {"low", "medium", "high"}]
    if not interpretable:
        return "insufficient interpretable baseline phenotype axes"

    high = [name for name, level in interpretable if level == "high"]
    low = [name for name, level in interpretable if level == "low"]
    medium = [name for name, level in interpretable if level == "medium"]

    parts = []
    if high:
        parts.append("higher " + ", ".join(high))
    if low:
        parts.append("lower " + ", ".join(low))
    if not parts and medium:
        parts.append("mostly medium relative digital phenotype axes")
    return "; ".join(parts)


def phenotype_sentence(row: pd.Series) -> str:
    if not bool(row.get("phase1_baseline_usable")):
        return (
            f"Subject {row['Subject_ID_D']} had global_delta={format_value(row.get('global_delta'))}, "
            "but Phase 1 baseline data were insufficient for a readable digital phenotype profile."
        )

    axes = [
        f"phone engagement {row.get('phone_engagement_level')}",
        f"nighttime phone activity {row.get('nighttime_phone_activity_level')}",
        f"app-use breadth {row.get('app_use_breadth_level')}",
        f"active interaction {row.get('active_phone_interaction_level')}",
        f"physical activity context {row.get('physical_activity_context_level')}",
    ]
    return (
        f"Subject {row['Subject_ID_D']} had global_delta={format_value(row.get('global_delta'))}; "
        f"relative baseline axes were {', '.join(axes)}. "
        f"Data-quality support was {row.get('data_quality_support_level')}."
    )


def data_limitations(row: pd.Series, axis_missing: dict[str, list[str]]) -> str:
    notes = []
    if not bool(row.get("phase1_baseline_usable")):
        notes.append("baseline phenotype unavailable from current Phase 1 outputs")
    if not bool(row.get("phase1_change_usable")):
        notes.append("early-vs-late change profile unavailable or limited by missing late windows")
    for axis, missing in axis_missing.items():
        if missing:
            notes.append(f"{axis} insufficient because missing columns: {', '.join(missing)}")
    notes.append("missing data are not interpreted as zero activity")
    return "; ".join(notes)


def change_direction(row: pd.Series, delta_cols: list[str], status: str) -> str:
    if status not in {"ok", "ok_both_windows"}:
        return "not_interpretable"
    values = [pd.to_numeric(row.get(c), errors="coerce") for c in delta_cols if c in row.index]
    values = [v for v in values if pd.notna(v)]
    if not values:
        return "not_interpretable"
    primary = float(values[0])
    if primary > 0:
        return "increase"
    if primary < 0:
        return "decrease"
    return "no_observed_change"


def build_change_profiles(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    targets = {"024", "077"}
    for _, row in df[df["Subject_ID_D"].isin(targets)].sort_values("Subject_ID_D").iterrows():
        for family, spec in CHANGE_FAMILIES.items():
            status_col = spec["status"]
            status = str(row.get(status_col)) if status_col in row.index and pd.notna(row.get(status_col)) else "not_available"
            direction = change_direction(row, spec["delta"], status)
            role = spec["role"]
            if role == "data_quality_support":
                summary = (
                    "aware_log supports judging logging availability only; it is not interpreted as behavior."
                )
            elif direction == "not_interpretable":
                summary = f"{family} early-vs-late change is not interpretable from current Phase 1 outputs ({status})."
            else:
                summary = f"{family} showed a relative {direction} among available early and late windows."

            rows.append(
                {
                    "Subject_ID_D": row["Subject_ID_D"],
                    "global_delta": row.get("global_delta"),
                    "global_decline_amount": row.get("global_decline_amount"),
                    "feature_family": family,
                    "role": role,
                    "early_values": join_feature_values(row, spec["early"]),
                    "late_values": join_feature_values(row, spec["late"]),
                    "delta_values": join_feature_values(row, spec["delta"]),
                    "pct_change_values": join_feature_values(row, spec["pct"]) if spec["pct"] else "not_applicable",
                    "delta_status": status,
                    "change_direction": direction,
                    "change_profile_summary": summary,
                    "interpretation_caution": (
                        "Exploratory limited change profile only; missing windows are not inactivity."
                    ),
                }
            )
    return pd.DataFrame(rows)


def write_cards(profiles: pd.DataFrame, path: Path) -> None:
    lines = [
        "# Phase 1 Subject Phenotype Cards v2",
        "",
        "Clinically readable exploratory profiles from existing Phase 1 outputs only. Not diagnostic and not confirmatory.",
        "",
    ]
    for _, row in profiles.sort_values("Subject_ID_D").iterrows():
        lines.extend(
            [
                f"## Subject {row['Subject_ID_D']}",
                f"- Cognitive decline: global_delta={format_value(row.get('global_delta'))}; global_decline_amount={format_value(row.get('global_decline_amount'))}.",
                "- Baseline digital phenotype axes: "
                f"phone engagement={row.get('phone_engagement_level')}; "
                f"nighttime phone activity={row.get('nighttime_phone_activity_level')}; "
                f"app-use breadth={row.get('app_use_breadth_level')}; "
                f"active phone interaction={row.get('active_phone_interaction_level')}; "
                f"physical activity context={row.get('physical_activity_context_level')}.",
                f"- Data quality: data-quality support={row.get('data_quality_support_level')}; {row.get('data_limitations')}.",
                f"- Change profile available: {bool(row.get('phase1_change_usable'))}.",
                f"- Cautious interpretation: {row.get('phenotype_summary_sentence')} {row.get('interpretation_caution')}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_readme(
    path: Path,
    baseline_subjects: list[str],
    change_subjects: list[str],
    axis_missing: dict[str, list[str]],
) -> None:
    lines = [
        "# Phase 1 Digital Phenotype Profiles v2",
        "",
        "## Scope",
        "- Uses only existing Phase 1 output files.",
        "- Does not query SQL.",
        "- Does not extract new features.",
        "- Does not modify previous outputs.",
        "- Exploratory clinical readability layer only; not diagnostic and not confirmatory.",
        "",
        "## Phenotype axes",
    ]
    for axis, spec in AXES.items():
        feature_list = ", ".join(spec["features"] + spec.get("optional_features", []))
        lines.append(f"- {axis}: {spec['meaning']}. Features: {feature_list}.")

    lines.extend(
        [
            "",
            "## Classification method",
            "- low / medium / high labels are relative to the 8 baseline-usable subjects only.",
            "- Axis scores use percentile ranks of the contributing features within baseline-usable subjects, then tertile labels on the axis score.",
            "- If a required feature column is unavailable, the axis is marked insufficient_data.",
            "- Missing values are not converted to zero activity.",
            "",
            "## Why aware_log is separate",
            "- aware_log is treated only as data-quality/logging support.",
            "- aware_log does not contribute to behavioral phenotype labels.",
            "- data_quality_support_level is reported separately from the behavioral axes.",
            "",
            "## Current sample limitations",
            "- Top-decline Phase 1 subset only.",
            "- Baseline phenotype available for 8 subjects: " + ", ".join(baseline_subjects) + ".",
            "- Change phenotype available only for 024 and 077.",
            "- Change profiles are limited summaries of existing early-vs-late feature columns.",
            "- Labels are descriptive, relative, and exploratory.",
            "",
            "## Axes with insufficient source columns",
        ]
    )
    any_missing = False
    for axis, missing in axis_missing.items():
        if missing:
            any_missing = True
            lines.append(f"- {axis}: missing {', '.join(missing)}.")
    if not any_missing:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Generated files",
            "- phase1_subject_phenotype_profiles_v2.csv",
            "- phase1_subject_phenotype_cards_v2.md",
            "- phase1_change_profiles_024_077_v2.csv",
            "- README_phase1_digital_phenotype_profiles_v2.md",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    wide = pd.read_csv(INPUT_WIDE)
    ranks = pd.read_csv(INPUT_RANKS)
    interpretation = pd.read_csv(INPUT_INTERPRETATION)
    usability = pd.read_csv(INPUT_USABILITY)

    for df in [wide, ranks, interpretation, usability]:
        if "Subject_ID_D" in df.columns:
            df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id_d)

    for col in ["phase1_baseline_usable", "phase1_change_usable"]:
        if col in wide.columns:
            wide[col] = wide[col].map(to_bool)
        if col in usability.columns:
            usability[col] = usability[col].map(to_bool)

    baseline_df = wide[wide["phase1_baseline_usable"]].copy()
    baseline_subjects = sorted(baseline_df["Subject_ID_D"].tolist())
    change_subjects = sorted(wide.loc[wide["phase1_change_usable"], "Subject_ID_D"].tolist())

    profiles = wide[
        [
            "Subject_ID_D",
            "global_delta",
            "global_decline_amount",
            "phase1_baseline_usable",
            "phase1_change_usable",
        ]
    ].copy()

    axis_missing: dict[str, list[str]] = {}
    for axis, spec in AXES.items():
        feature_cols = [c for c in spec["features"]]
        optional_available = [c for c in spec.get("optional_features", []) if c in wide.columns]
        if axis == "data_quality_support":
            feature_cols = feature_cols + optional_available
        levels, scores, missing_cols = classify_axis(wide, baseline_df, axis, feature_cols)
        profiles[f"{axis}_level"] = levels
        profiles[f"{axis}_score"] = scores
        axis_missing[axis] = missing_cols

    profiles["main_digital_phenotype_label"] = profiles.apply(behavior_label, axis=1)
    profiles["phenotype_summary_sentence"] = profiles.apply(phenotype_sentence, axis=1)
    profiles["data_limitations"] = profiles.apply(lambda r: data_limitations(r, axis_missing), axis=1)
    profiles["interpretation_caution"] = (
        "Exploratory relative profile only; not diagnostic, not confirmatory, and missing data are not zero activity. "
        "aware_log is used only as data-quality support."
    )

    output_cols = [
        "Subject_ID_D",
        "global_delta",
        "global_decline_amount",
        "phase1_baseline_usable",
        "phase1_change_usable",
        "phone_engagement_level",
        "nighttime_phone_activity_level",
        "app_use_breadth_level",
        "active_phone_interaction_level",
        "physical_activity_context_level",
        "data_quality_support_level",
        "main_digital_phenotype_label",
        "phenotype_summary_sentence",
        "data_limitations",
        "interpretation_caution",
    ]
    profiles_out = profiles[output_cols].sort_values("Subject_ID_D")

    p_profiles = OUT_DIR / "phase1_subject_phenotype_profiles_v2.csv"
    p_cards = OUT_DIR / "phase1_subject_phenotype_cards_v2.md"
    p_change = OUT_DIR / "phase1_change_profiles_024_077_v2.csv"
    p_readme = OUT_DIR / "README_phase1_digital_phenotype_profiles_v2.md"

    profiles_out.to_csv(p_profiles, index=False)
    write_cards(profiles_out, p_cards)
    change_profiles = build_change_profiles(wide)
    change_profiles.to_csv(p_change, index=False)
    write_readme(p_readme, baseline_subjects, change_subjects, axis_missing)

    print("phenotype_axes_created:")
    for axis in AXES:
        print(f"- {axis}")
    print(f"baseline_subjects_profiled={len(baseline_subjects)} -> {baseline_subjects}")
    print(f"change_subjects_profiled={len(change_subjects)} -> {change_subjects}")
    print("distribution_of_low_medium_high_per_axis:")
    for axis in AXES:
        counts = profiles_out[f"{axis}_level"].value_counts(dropna=False).to_dict()
        print(f"- {axis}: {counts}")
    print("generated_files:")
    for path in [p_profiles, p_cards, p_change, p_readme]:
        print(f"- {path}")


if __name__ == "__main__":
    main()
