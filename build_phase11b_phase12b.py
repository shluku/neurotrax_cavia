"""Build additive Phase 11 B and Phase 12 B patient-level feature tables.

The supplemental proximity/light values currently available are Phase 4-style
24-hour T1 baseline measurements. They are added as explicitly named T1
baseline context to both cohorts. They are not relabeled as T1-to-T2 changes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from supplemental_modalities.review_phase4_features import RECOMMENDED_FEATURES


ROOT = Path(__file__).parent
SUPPLEMENTAL_ROOT = ROOT / "output/analysis_candidates/supplemental_modalities/phase4_24h_t1"
PHASE11_ROOT = ROOT / "output/analysis_candidates/phase11_t1_baseline"
PHASE12_ROOT = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline"
PHASE11_B_ROOT = ROOT / "output/analysis_candidates/phase11_b_t1_baseline"
PHASE12_B_ROOT = ROOT / "output/analysis_candidates/phase12_b_t1_t2_change"


def normalize_id(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def selected_feature_names() -> list[tuple[str, str]]:
    return [(modality, feature) for modality in ["proximity", "light"] for feature in sorted(RECOMMENDED_FEATURES[modality])]


def load_supplemental() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    merged: pd.DataFrame | None = None
    status_frames: list[pd.DataFrame] = []
    metadata = pd.read_csv(SUPPLEMENTAL_ROOT / "phase4_supplemental_feature_review.csv", dtype=str)
    selected = set(selected_feature_names())
    metadata = metadata[
        metadata.apply(lambda row: (str(row["modality"]), str(row["feature_name"])) in selected, axis=1)
    ].copy()
    for modality in ["proximity", "light"]:
        wide = pd.read_csv(SUPPLEMENTAL_ROOT / f"{modality}_features_wide.csv", dtype=str)
        wide["Subject_ID_D"] = wide["Subject_ID_D"].map(normalize_id)
        feature_map: dict[str, str] = {}
        for _, feature in selected_feature_names():
            if _ == modality:
                feature_map[feature] = f"supplemental_t1_{feature}"
        keep = ["Subject_ID_D", "status", "window_rule", *feature_map.keys()]
        keep = [column for column in keep if column in wide.columns]
        part = wide[keep].copy()
        part = part.rename(
            columns={
                "status": f"supplemental_t1_{modality}_status",
                "window_rule": f"supplemental_t1_{modality}_window_rule",
                **feature_map,
            }
        )
        for column in part.columns:
            if column not in {"Subject_ID_D", f"supplemental_t1_{modality}_status", f"supplemental_t1_{modality}_window_rule"}:
                part[column] = pd.to_numeric(part[column], errors="coerce")
        merged = part if merged is None else merged.merge(part, on="Subject_ID_D", how="outer")
        status_frames.append(part[["Subject_ID_D", f"supplemental_t1_{modality}_status", f"supplemental_t1_{modality}_window_rule"]])
    assert merged is not None
    feature_columns = [f"supplemental_t1_{feature}" for _, feature in selected_feature_names()]
    merged["supplemental_t1_feature_missing_count"] = merged[feature_columns].isna().sum(axis=1)
    merged["supplemental_t1_feature_missing_fraction"] = merged[feature_columns].isna().mean(axis=1)
    return merged, pd.concat(status_frames, ignore_index=True), metadata


def build_dataset(source_path: Path, output_root: Path, phase_label: str, context_note: str) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(source_path, dtype=str)
    base["Subject_ID_D"] = base["Subject_ID_D"].map(normalize_id)
    supplemental, _, review_metadata = load_supplemental()
    dataset = base.merge(supplemental, on="Subject_ID_D", how="left", validate="one_to_one")
    dataset["supplemental_source_window"] = "phase4_primary_day_after_T1_or_first_available_24h_in_T1_week"
    dataset["supplemental_context_role"] = context_note
    dataset.to_csv(output_root / f"{phase_label}_patient_dataset.csv", index=False)

    feature_columns = [f"supplemental_t1_{feature}" for _, feature in selected_feature_names()]
    metadata_rows: list[dict[str, object]] = []
    for _, row in review_metadata.iterrows():
        feature = str(row["feature_name"])
        metadata_rows.append(
            {
                "feature_name": f"supplemental_t1_{feature}",
                "original_feature_name": feature,
                "source_modality": row["modality"],
                "source_phase": "Phase 4 24-hour T1 supplemental extraction",
                "source_window": "T1 24-hour primary/fallback window",
                "feature_group": row["feature_group"],
                "coverage_percent_in_source": row["coverage_percent"],
                "phase11_b_phase12_b_role": context_note,
                "feature_definition": row["feature_definition"],
            }
        )
    pd.DataFrame(metadata_rows).to_csv(output_root / f"{phase_label}_feature_metadata.csv", index=False)
    pd.DataFrame(
        {
            "feature_name": feature_columns,
            "n_patients": [int(pd.to_numeric(dataset[column], errors="coerce").notna().sum()) for column in feature_columns],
            "missing_percent": [round(100 - 100 * pd.to_numeric(dataset[column], errors="coerce").notna().mean(), 2) for column in feature_columns],
        }
    ).to_csv(output_root / f"{phase_label}_missingness_summary.csv", index=False)
    (output_root / f"README_{phase_label}.md").write_text(
        f"# {phase_label}\n\n"
        f"This additive table starts from the existing {phase_label} cohort and adds all nine recommended proximity/light features.\n\n"
        "The supplemental values were extracted using the Phase 4-style T1 24-hour primary/fallback window. "
        "They are prefixed with `supplemental_t1_` and remain T1 baseline context. "
        f"For this cohort, their role is: {context_note}.\n\n"
        "The original Phase 11/12 files are unchanged. No models are run by this builder.\n",
        encoding="utf-8",
    )


def write_selection_manifest() -> None:
    pd.DataFrame(
        [
            {
                "modality": modality,
                "feature_name": feature,
                "selection_source": "user_requested_all_suggested_features",
            }
            for modality, feature in selected_feature_names()
        ]
    ).to_csv(SUPPLEMENTAL_ROOT / "phase4_supplemental_feature_selection.csv", index=False)


def main() -> None:
    write_selection_manifest()
    build_dataset(
        PHASE11_ROOT / "phase11_t1_baseline_patient_dataset.csv",
        PHASE11_B_ROOT,
        "phase11_b_t1_baseline",
        "T1 supplemental features for baseline phenotype exploration",
    )
    build_dataset(
        PHASE12_ROOT / "phase12_midpoint_t2_decline_features_wide.csv",
        PHASE12_B_ROOT,
        "phase12_b_t1_t2_change",
        "T1 supplemental baseline context for midpoint T1-to-T2 change exploration",
    )
    print(f"Phase 11 B output: {PHASE11_B_ROOT}")
    print(f"Phase 12 B output: {PHASE12_B_ROOT}")


if __name__ == "__main__":
    main()
