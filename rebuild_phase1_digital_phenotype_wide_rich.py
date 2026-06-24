from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


OUT_DIR = Path("output/analysis_candidates/phase1_features/extracted")
P1A_SUBJECT_WINDOW = OUT_DIR / "phase1a_subject_window_features.csv"
P1B_SUBJECT_WINDOW = OUT_DIR / "phase1b_subject_window_features.csv"
USABILITY = OUT_DIR / "phase1_subject_usability_summary.csv"
TOP10 = Path("output/analysis_candidates/top10_global_decline.csv")
READINESS = Path("output/analysis_candidates/sql_coverage/top10_subject_readiness.csv")
OLD_WIDE = OUT_DIR / "phase1_digital_phenotype_wide.csv"
RICH_WIDE = OUT_DIR / "phase1_digital_phenotype_wide_rich.csv"
RICH_README = OUT_DIR / "README_phase1_digital_phenotype_wide_rich.md"


P1A_FEATURES = {
    "screen": {
        "screen_event_count": "screen_{window}_event_count",
        "active_screen_days": "screen_{window}_active_days",
        "night_screen_event_count": "screen_{window}_night_event_count",
        "screen_events_per_active_day": "screen_{window}_events_per_active_day",
    },
    "applications_foreground": {
        "app_foreground_event_count": "app_{window}_foreground_event_count",
        "active_app_days": "app_{window}_active_days",
        "unique_foreground_apps": "app_{window}_unique_foreground_apps",
        "app_use_diversity": "app_{window}_app_use_diversity",
        "app_events_per_active_day": "app_{window}_events_per_active_day",
    },
    "aware_log": {
        "aware_log_rows": "aware_log_{window}_rows",
        "aware_log_active_days": "aware_log_{window}_active_days",
        "data_logging_coverage_days": "aware_log_{window}_data_logging_coverage_days",
        "system_log_density": "aware_log_{window}_system_log_density",
    },
}


P1B_FEATURES = {
    "keyboard": {
        "keyboard_event_count": "keyboard_{window}_event_count",
        "active_keyboard_days": "keyboard_{window}_active_days",
        "keyboard_events_per_active_day": "keyboard_{window}_events_per_active_day",
    },
    "touch": {
        "touch_event_count": "touch_{window}_event_count",
        "active_touch_days": "touch_{window}_active_days",
        "touch_events_per_active_day": "touch_{window}_events_per_active_day",
    },
    "plugin_google_activity_recognition": {
        "activity_event_count": "activity_{window}_event_count",
        "active_activity_days": "activity_{window}_active_days",
        "still_event_count": "activity_{window}_still_event_count",
        "walking_event_count": "activity_{window}_walking_event_count",
        "in_vehicle_event_count": "activity_{window}_in_vehicle_event_count",
        "activity_diversity": "activity_{window}_activity_diversity",
        "high_confidence_activity_event_count": "activity_{window}_high_confidence_event_count",
        "mean_activity_confidence": "activity_{window}_mean_confidence",
    },
}


DELTA_SPECS = {
    "screen": {
        "early": "screen_early_event_count",
        "late": "screen_late_event_count",
        "delta": "screen_delta_event_count",
        "status": "screen_delta_status",
    },
    "app": {
        "early": "app_early_foreground_event_count",
        "late": "app_late_foreground_event_count",
        "delta": "app_delta_foreground_event_count",
        "status": "app_delta_status",
    },
    "keyboard": {
        "early": "keyboard_early_event_count",
        "late": "keyboard_late_event_count",
        "delta": "keyboard_delta_event_count",
        "status": "keyboard_delta_status",
    },
    "touch": {
        "early": "touch_early_event_count",
        "late": "touch_late_event_count",
        "delta": "touch_delta_event_count",
        "status": "touch_delta_status",
    },
    "activity": {
        "early": "activity_early_event_count",
        "late": "activity_late_event_count",
        "delta": "activity_delta_event_count",
        "status": "activity_delta_status",
    },
    "aware_log": {
        "early": "aware_log_early_rows",
        "late": "aware_log_late_rows",
        "delta": "aware_log_delta_rows",
        "status": "aware_log_delta_status",
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


def window_label(value) -> str:
    s = str(value).strip()
    if s == "early_window":
        return "early"
    if s == "late_window":
        return "late"
    return s.replace("_window", "")


def normalize_ids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Subject_ID_D" in df.columns:
        df["Subject_ID_D"] = df["Subject_ID_D"].map(normalize_subject_id_d)
    if "Subject_ID_N" in df.columns:
        df["Subject_ID_N"] = df["Subject_ID_N"].astype(str).str.strip()
    return df


def usable_feature_value(row: pd.Series, source_col: str):
    has_data = to_bool(row.get("table_has_data"))
    status = str(row.get("extraction_status", "")).strip()
    if not has_data or status == "ok_no_data":
        return np.nan
    return pd.to_numeric(row.get(source_col), errors="coerce")


def pivot_subject_windows(df: pd.DataFrame, feature_map: dict[str, dict[str, str]]) -> pd.DataFrame:
    df = normalize_ids(df)
    rows = {}

    for _, row in df.iterrows():
        sid_n = str(row["Subject_ID_N"]).strip()
        sid_d = normalize_subject_id_d(row["Subject_ID_D"])
        key = (sid_n, sid_d)
        out = rows.setdefault(key, {"Subject_ID_N": sid_n, "Subject_ID_D": sid_d})

        table = str(row.get("table_name", "")).strip()
        window = window_label(row.get("window_name", ""))
        if table not in feature_map or window not in {"early", "late"}:
            continue

        for source_col, out_template in feature_map[table].items():
            if source_col not in row.index:
                continue
            out[out_template.format(window=window)] = usable_feature_value(row, source_col)

    return pd.DataFrame(rows.values())


def add_delta_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for spec in DELTA_SPECS.values():
        early = pd.to_numeric(df.get(spec["early"]), errors="coerce")
        late = pd.to_numeric(df.get(spec["late"]), errors="coerce")
        ok = early.notna() & late.notna()
        df[spec["delta"]] = np.where(ok, late - early, np.nan)
        df[spec["status"]] = np.where(ok, "ok_both_windows", "missing_early_or_late")
    return df


def ordered_feature_columns(columns: list[str]) -> list[str]:
    ordered = []
    for table_map in [P1A_FEATURES, P1B_FEATURES]:
        for feature_map in table_map.values():
            for out_template in feature_map.values():
                for window in ["early", "late"]:
                    col = out_template.format(window=window)
                    if col in columns and col not in ordered:
                        ordered.append(col)

    for spec in DELTA_SPECS.values():
        for col in [spec["delta"], spec["status"]]:
            if col in columns and col not in ordered:
                ordered.append(col)

    remaining = [
        c
        for c in columns
        if c not in ordered
        and c
        not in {
            "Subject_ID_N",
            "Subject_ID_D",
            "global_T1",
            "global_T2",
            "global_delta",
            "global_decline_amount",
            "T1_date_iso",
            "T2_date_iso",
            "phase1_baseline_usable",
            "phase1_change_usable",
            "interpretation_scope",
            "data_availability_note",
            "early_late_coverage_group",
        }
    ]
    return ordered + remaining


def write_readme(old_shape: tuple[int, int], rich_shape: tuple[int, int], added_cols: list[str]) -> None:
    text = f"""# Phase 1 Digital Phenotype Wide Rich

This richer wide table was rebuilt from existing extracted Phase 1 subject-window outputs.

Scope:
- Input tables: phase1a_subject_window_features.csv and phase1b_subject_window_features.csv.
- No SQL was queried.
- No new feature extraction was performed.
- Previous outputs were not modified.
- Missing/no_data remains NaN in the rich wide table.
- aware_log is retained as data-quality support only, not a behavioral phenotype feature.

Why this table exists:
- The previous merged wide table omitted some already-extracted Phase 1A subject-window features.
- This rebuild includes safe existing fields such as screen nighttime counts, active-day counts, app breadth, and app-use diversity.

Shape:
- old wide table: {old_shape[0]} rows x {old_shape[1]} columns.
- rich wide table: {rich_shape[0]} rows x {rich_shape[1]} columns.
- columns added compared with old wide table: {len(added_cols)}.

Delta rules:
- Primary count deltas are computed only when both early and late values are non-missing.
- If either window is missing, delta remains NaN and delta_status is missing_early_or_late.
- If both windows exist, delta is late minus early and delta_status is ok_both_windows.

Generated file:
- phase1_digital_phenotype_wide_rich.csv
"""
    RICH_README.write_text(text, encoding="utf-8")


def main() -> None:
    p1a = pd.read_csv(P1A_SUBJECT_WINDOW)
    p1b = pd.read_csv(P1B_SUBJECT_WINDOW)
    usability = normalize_ids(pd.read_csv(USABILITY))
    top10 = normalize_ids(pd.read_csv(TOP10))
    readiness = normalize_ids(pd.read_csv(READINESS))
    old = pd.read_csv(OLD_WIDE)

    p1a_wide = pivot_subject_windows(p1a, P1A_FEATURES)
    p1b_wide = pivot_subject_windows(p1b, P1B_FEATURES)

    keys = ["Subject_ID_N", "Subject_ID_D"]
    rich = top10[
        [
            "Subject_ID_N",
            "Subject_ID_D",
            "global_T1",
            "global_T2",
            "global_delta",
            "global_decline_amount",
            "T1_date_iso",
            "T2_date_iso",
        ]
    ].copy()

    rich = rich.merge(p1a_wide, on=keys, how="left", validate="one_to_one")
    rich = rich.merge(p1b_wide, on=keys, how="left", validate="one_to_one")
    rich = add_delta_columns(rich)

    usability_cols = [
        "Subject_ID_N",
        "Subject_ID_D",
        "phase1_baseline_usable",
        "phase1_change_usable",
        "interpretation_scope",
        "data_availability_note",
        "early_late_coverage_group",
    ]
    rich = rich.merge(usability[usability_cols], on=keys, how="left", validate="one_to_one")

    if "early_late_coverage_group" not in rich.columns or rich["early_late_coverage_group"].isna().any():
        rich = rich.merge(
            readiness[["Subject_ID_N", "Subject_ID_D", "early_late_coverage_group"]],
            on=keys,
            how="left",
            suffixes=("", "_readiness"),
        )
        if "early_late_coverage_group_readiness" in rich.columns:
            rich["early_late_coverage_group"] = rich["early_late_coverage_group"].fillna(
                rich["early_late_coverage_group_readiness"]
            )
            rich = rich.drop(columns=["early_late_coverage_group_readiness"])

    for col in ["phase1_baseline_usable", "phase1_change_usable"]:
        rich[col] = rich[col].map(to_bool)

    id_cog_cols = [
        "Subject_ID_N",
        "Subject_ID_D",
        "global_T1",
        "global_T2",
        "global_delta",
        "global_decline_amount",
        "T1_date_iso",
        "T2_date_iso",
    ]
    usability_out_cols = [
        "phase1_baseline_usable",
        "phase1_change_usable",
        "interpretation_scope",
        "data_availability_note",
        "early_late_coverage_group",
    ]
    feature_cols = ordered_feature_columns(list(rich.columns))
    rich = rich[id_cog_cols + feature_cols + usability_out_cols].sort_values("Subject_ID_D")

    rich.to_csv(RICH_WIDE, index=False)

    old_cols = set(old.columns)
    rich_cols = set(rich.columns)
    added_cols = sorted(rich_cols - old_cols)
    write_readme(old.shape, rich.shape, added_cols)

    required_check = [
        "screen_early_night_event_count",
        "app_early_unique_foreground_apps",
        "app_early_app_use_diversity",
        "screen_early_active_days",
        "app_early_active_days",
    ]

    print(f"rich_wide_table_shape={rich.shape}")
    print(f"old_wide_table_shape={old.shape}")
    print(f"columns_added_compared_with_old_wide={len(added_cols)}")
    print("required_columns_exist:")
    for col in required_check:
        print(f"- {col}: {col in rich.columns}")
    print("baseline_subjects_profiled=" + str(sorted(rich.loc[rich["phase1_baseline_usable"], "Subject_ID_D"].tolist())))
    print("change_subjects_profiled=" + str(sorted(rich.loc[rich["phase1_change_usable"], "Subject_ID_D"].tolist())))
    print("generated_files:")
    print(f"- {RICH_WIDE}")
    print(f"- {RICH_README}")


if __name__ == "__main__":
    main()
