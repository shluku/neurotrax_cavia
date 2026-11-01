#!/usr/bin/env python3
"""Compute CIs for recoverable non-keyboard rows in the research-summary table."""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "output/research_summary_20261025"
SOURCE = BASE / "all_associations_with_ci_20261025.csv"
OUTPUT = BASE / "all_associations_with_ci_20261029.csv"
AUDIT = BASE / "NONKEYBOARD_CI_AUDIT_20261029.md"
BOOTSTRAPS = 2000


def finite(values: pd.Series) -> np.ndarray:
    return pd.to_numeric(values, errors="coerce").to_numpy(float)


def bootstrap_correlation(x: np.ndarray, y: np.ndarray, kind: str, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(x)
    boots = np.empty(BOOTSTRAPS, dtype=float)
    for i in range(BOOTSTRAPS):
        idx = rng.integers(0, n, n)
        if kind == "Pearson r":
            a, b = x[idx], y[idx]
            if np.std(a) == 0 or np.std(b) == 0:
                boots[i] = np.nan
            else:
                boots[i] = np.corrcoef(a, b)[0, 1]
        else:
            a, b = x[idx], y[idx]
            if np.ptp(a) == 0 or np.ptp(b) == 0:
                boots[i] = np.nan
            else:
                boots[i] = spearmanr(a, b).statistic
    boots = boots[np.isfinite(boots)]
    return float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def observed_correlation(x: np.ndarray, y: np.ndarray, kind: str) -> float:
    if kind == "Pearson r":
        return float(np.corrcoef(x, y)[0, 1])
    return float(spearmanr(x, y).statistic)


def cliffs_delta(higher: np.ndarray, lower: np.ndarray) -> float:
    comparisons = higher[:, None] - lower[None, :]
    return float((np.sum(comparisons > 0) - np.sum(comparisons < 0)) / comparisons.size)


def bootstrap_cliffs(higher: np.ndarray, lower: np.ndarray, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    boots = np.empty(BOOTSTRAPS, dtype=float)
    for i in range(BOOTSTRAPS):
        h = higher[rng.integers(0, len(higher), len(higher))]
        l = lower[rng.integers(0, len(lower), len(lower))]
        boots[i] = cliffs_delta(h, l)
    return float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def phase4_matrix(modality: str) -> pd.DataFrame:
    filename = {
        "coverage": "light_features_wide.csv",
        "behavioral": "light_features_wide.csv",
        "temporal": "light_features_wide.csv",
    }.get(modality)
    if modality == "behavioral" or modality == "coverage" or modality == "temporal":
        # The source review contains both light and proximity features. Load and combine both matrices.
        light = pd.read_csv(BASE.parent / "analysis_candidates/supplemental_modalities/phase4_24h_t1/light_features_wide.csv")
        proximity = pd.read_csv(BASE.parent / "analysis_candidates/supplemental_modalities/phase4_24h_t1/proximity_features_wide.csv")
        return pd.concat([light.set_index("Subject_ID_D"), proximity.set_index("Subject_ID_D")], axis=1, join="outer", keys=["light", "proximity"])
    raise ValueError(modality)


def get_phase4_values(row: pd.Series) -> tuple[np.ndarray, np.ndarray] | None:
    folder = ROOT / "output/analysis_candidates/supplemental_modalities/phase4_24h_t1"
    modality = str(row["feature_modality"])
    source_feature = str(row["feature"])
    if modality == "coverage" or modality == "temporal" or modality == "behavioral":
        candidates = [folder / "light_features_wide.csv", folder / "proximity_features_wide.csv"]
        frames = [pd.read_csv(p) for p in candidates]
        frame = next((f for f in frames if source_feature in f.columns), None)
        if frame is None:
            return None
        y_name = "global_T1"
        if source_feature not in frame.columns or y_name not in frame.columns:
            return None
        x = pd.to_numeric(frame[source_feature], errors="coerce")
        y = pd.to_numeric(frame[y_name], errors="coerce")
        ok = x.notna() & y.notna()
        if int(ok.sum()) < 3:
            return None
        return x[ok].to_numpy(float), y[ok].to_numpy(float)
    return None


def get_phase11_values(row: pd.Series, phase11: pd.DataFrame, assignments: pd.DataFrame) -> tuple[np.ndarray, np.ndarray] | None:
    feature = str(row["feature"])
    if feature not in phase11.columns:
        return None
    x = pd.to_numeric(phase11[feature], errors="coerce")
    group_map = assignments.set_index("Subject_ID_N")["baseline_severity_group"]
    groups = phase11["Subject_ID_N"].map(group_map)
    ok = x.notna() & groups.notna()
    x = x[ok]
    groups = groups[ok]
    higher = x[groups.eq("Higher observed T1")].to_numpy(float)
    lower = x[groups.eq("Lower observed T1")].to_numpy(float)
    if len(higher) < 2 or len(lower) < 2:
        return None
    return higher, lower


def main() -> None:
    table = pd.read_csv(SOURCE)
    missing = table["ci_low"].isna() | table["ci_high"].isna()
    phase11 = pd.read_csv(ROOT / "output/analysis_candidates/phase11_t1_baseline/phase11_t1_baseline_patient_dataset.csv")
    assignments = pd.read_csv(ROOT / "output/analysis_candidates/phase11_t1_baseline/clinical_tables_baseline_severity/phase11_baseline_severity_group_assignments.csv")
    computed = []
    for idx, row in table.loc[missing & (table["feature_modality"] != "keyboard")].iterrows():
        lo = hi = observed = None
        method = None
        values = None
        if "supplemental_modalities/phase4_24h_t1/phase4_supplemental_feature_review.csv" in str(row["source_file"]):
            values = get_phase4_values(row)
            if values is not None:
                observed = observed_correlation(values[0], values[1], str(row["estimate_type"]))
                lo, hi = bootstrap_correlation(values[0], values[1], str(row["estimate_type"]), 20261029 + int(row["master_row_id"]))
                method = f"{BOOTSTRAPS}-resample paired bootstrap of saved Phase 4 patient-level feature/cognitive inputs"
        elif "phase11_t1_baseline/clinical_tables_baseline_severity/phase11_baseline_severity_all_features.csv" in str(row["source_file"]):
            phase11_values = get_phase11_values(row, phase11, assignments)
            if phase11_values is not None:
                observed = cliffs_delta(phase11_values[0], phase11_values[1])
                lo, hi = bootstrap_cliffs(phase11_values[0], phase11_values[1], 20261029 + int(row["master_row_id"]))
                method = f"{BOOTSTRAPS}-resample stratified bootstrap of saved Phase 11 patient-level Cliff's delta inputs"
        if lo is not None and hi is not None:
            table.at[idx, "ci_low"] = lo
            table.at[idx, "ci_high"] = hi
            table.at[idx, "ci_source"] = "recomputed_from_saved_patient_level_inputs"
            table.at[idx, "ci_method"] = method
            table.at[idx, "missing_statistics"] = str(row["missing_statistics"]).replace("ci_low; ci_high", "")
            computed.append({"master_row_id": int(row["master_row_id"]), "feature_modality": row["feature_modality"], "feature": row["feature"], "outcome": row["outcome"], "estimate_type": row["estimate_type"], "n": row["n"], "estimate_saved": row["estimate"], "estimate_recomputed": observed, "estimate_difference": observed - float(row["estimate"]), "ci_low": lo, "ci_high": hi, "ci_method": method})

    table.to_csv(OUTPUT, index=False)
    done = pd.DataFrame(computed)
    done.to_csv(BASE / "nonkeyboard_ci_recomputed_rows_20261029.csv", index=False)
    remaining = table["ci_low"].isna() | table["ci_high"].isna()
    before_missing = int(missing.sum())
    after_missing = int(remaining.sum())
    nonkeyboard_before = int((missing & (table["feature_modality"] != "keyboard")).sum())
    nonkeyboard_after = int((remaining & (table["feature_modality"] != "keyboard")).sum())
    source_counts = done.groupby("feature_modality").size().to_dict() if not done.empty else {}
    AUDIT.write_text(f"""# Non-keyboard CI computation audit — 2026-10-29

The dated table `all_associations_with_ci_20261029.csv` preserves the 2025 source table and fills confidence intervals only when the exact saved patient-level matrix and estimand were recoverable.

- Missing CIs before: {before_missing} of {len(table)} rows.
- Missing CIs after: {after_missing} of {len(table)} rows.
- Non-keyboard missing CIs before: {nonkeyboard_before}.
- Non-keyboard CIs recomputed: {len(done)} ({source_counts}).
- Non-keyboard CIs still unavailable: {nonkeyboard_after}.

Phase 4 supplemental rows use paired patient-level bootstrap resampling for the saved Pearson or Spearman estimand. Phase 11 baseline-severity rows use stratified patient bootstrap resampling of Cliff's delta, preserving the observed Global-T1 median split. Rows with no exact saved feature matrix remain unavailable; no substitute cohort or new database extraction was used.

The Streamlit research-summary forest view now prefers the 2026-10-29 table when present and falls back to the 2025 table otherwise.
""", encoding="utf-8")
    print(f"recomputed={len(done)} nonkeyboard_before={nonkeyboard_before} nonkeyboard_after={nonkeyboard_after}")
    print(done.groupby("feature_modality").size().to_string() if not done.empty else "no rows")


if __name__ == "__main__":
    main()
