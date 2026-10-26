"""Build an exploratory T1 analysis of two preselected keyboard features."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr


ROOT = Path(__file__).parent
SOURCE = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"
OUT = ROOT / "output/analysis_candidates/keyboard_two_feature_median_timespan"
FEATURES = {
    "keyboard_median_word_completion_time_ms": "Median inferred word-completion time (ms)",
    "keyboard_inter_event_interval_iqr_ms": "Inter-keystroke interval variability (IQR, ms)",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(SOURCE, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    columns = ["Subject_ID_D", "Subject_ID_N", "global_T1", *FEATURES]
    data = source.reindex(columns=columns).copy()
    for column in ["global_T1", *FEATURES]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data.to_csv(OUT / "keyboard_two_feature_patient_data.csv", index=False)

    rows: list[dict[str, object]] = []
    for feature, label in FEATURES.items():
        paired = data[["global_T1", feature]].dropna()
        rho, p_value = spearmanr(paired[feature], paired["global_T1"])
        median_t1 = data["global_T1"].median()
        lower = paired.loc[paired["global_T1"] <= median_t1, feature]
        higher = paired.loc[paired["global_T1"] > median_t1, feature]
        rows.append(
            {
                "feature_name": feature,
                "feature_label": label,
                "n_observed": len(paired),
                "missing_percent": 100 * data[feature].isna().mean(),
                "spearman_rho": rho,
                "spearman_p_value": p_value,
                "global_t1_median_cutoff": median_t1,
                "lower_t1_group_median": lower.median(),
                "higher_t1_group_median": higher.median(),
                "direction": "decreases as Global T1 increases" if rho < 0 else "increases as Global T1 increases",
                "source_dataset": SOURCE.name,
            }
        )
    pd.DataFrame(rows).to_csv(OUT / "keyboard_two_feature_associations.csv", index=False)
    (OUT / "README_keyboard_two_feature_median_timespan.md").write_text(
        "# Two-feature keyboard analysis: median-timespan T1\n\n"
        "This output uses the existing Phase 11 midpoint/median-timespan T1 patient-level dataset. "
        "The two features were preselected from the earlier nominal p<0.10 exploratory comparison. "
        "No SQL query or existing model output was changed. Spearman associations and descriptive "
        "median-split summaries are reported in `keyboard_two_feature_associations.csv`.\n",
        encoding="utf-8",
    )
    print(f"Wrote two-feature keyboard analysis to {OUT}")


if __name__ == "__main__":
    main()
