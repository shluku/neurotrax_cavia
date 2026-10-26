"""Analyze paired keyboard feature change and run descriptive T1 PCA."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr, wilcoxon
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).parent
T1_PATH = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"
T2_PATH = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv"
OUT = ROOT / "output/analysis_candidates/keyboard_t1_t2_delta_pca"
FEATURES = {
    "keyboard_median_word_completion_time_ms": "Median inferred word-completion time (ms)",
    "keyboard_inter_event_interval_iqr_ms": "Inter-keystroke interval variability (IQR, ms)",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keys = ["Subject_ID_D", "Subject_ID_N", "global_T1", "global_T2", "global_delta", *FEATURES]
    t1 = pd.read_csv(T1_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str}).reindex(columns=keys)
    t2 = pd.read_csv(T2_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str}).reindex(columns=keys)
    t1 = t1.rename(columns={feature: f"{feature}_T1" for feature in FEATURES})
    t2 = t2.rename(columns={feature: f"{feature}_T2" for feature in FEATURES})
    merged = t1[["Subject_ID_D", "Subject_ID_N", "global_T1", "global_T2", "global_delta", *[f"{f}_T1" for f in FEATURES]]].merge(
        t2[["Subject_ID_D", *[f"{f}_T2" for f in FEATURES]]], on="Subject_ID_D", how="inner"
    )
    for column in merged.columns:
        if column not in {"Subject_ID_D", "Subject_ID_N"}:
            merged[column] = pd.to_numeric(merged[column], errors="coerce")
    for feature in FEATURES:
        merged[f"{feature}_delta"] = merged[f"{feature}_T2"] - merged[f"{feature}_T1"]
    merged.to_csv(OUT / "keyboard_t1_t2_patient_data.csv", index=False)

    rows: list[dict[str, object]] = []
    for feature, label in FEATURES.items():
        paired = merged[[f"{feature}_T1", f"{feature}_T2"]].dropna()
        differences = paired[f"{feature}_T2"] - paired[f"{feature}_T1"]
        if len(differences) >= 2 and differences.nunique() > 0:
            wilcoxon_result = wilcoxon(differences, alternative="two-sided")
            p_value = wilcoxon_result.pvalue
        else:
            p_value = float("nan")
        cognitive = merged[[f"{feature}_delta", "global_delta"]].dropna()
        rho, cognitive_p = spearmanr(cognitive[f"{feature}_delta"], cognitive["global_delta"]) if len(cognitive) >= 3 else (float("nan"), float("nan"))
        rows.append(
            {
                "feature_name": feature,
                "feature_label": label,
                "n_paired_t1_t2": len(paired),
                "t1_median": paired[f"{feature}_T1"].median(),
                "t2_median": paired[f"{feature}_T2"].median(),
                "median_delta_t2_minus_t1": differences.median(),
                "mean_delta_t2_minus_t1": differences.mean(),
                "wilcoxon_p_value_delta_vs_zero": p_value,
                "n_delta_cognitive_pairs": len(cognitive),
                "spearman_rho_feature_delta_vs_global_cognitive_delta": rho,
                "spearman_p_value_feature_delta_vs_global_cognitive_delta": cognitive_p,
                "source_t1": T1_PATH.name,
                "source_t2": T2_PATH.name,
            }
        )
    pd.DataFrame(rows).to_csv(OUT / "keyboard_t1_t2_delta_summary.csv", index=False)

    pca_data = merged[["Subject_ID_D", "Subject_ID_N", "global_T1", *[f"{f}_T1" for f in FEATURES]]].dropna()
    if len(pca_data) >= 2:
        matrix = StandardScaler().fit_transform(pca_data[[f"{f}_T1" for f in FEATURES]])
        pca = PCA(n_components=2).fit(matrix)
        scores = pca.transform(matrix)
        pca_scores = pca_data[["Subject_ID_D", "Subject_ID_N", "global_T1"]].copy()
        pca_scores["PC1"] = scores[:, 0]
        pca_scores["PC2"] = scores[:, 1]
        pca_scores.to_csv(OUT / "keyboard_t1_pca_patient_scores.csv", index=False)
        loadings = pd.DataFrame(pca.components_.T, index=list(FEATURES), columns=["PC1", "PC2"]).reset_index(names="feature_name")
        loadings["feature_label"] = loadings["feature_name"].map(FEATURES)
        loadings.to_csv(OUT / "keyboard_t1_pca_loadings.csv", index=False)
        pd.DataFrame(
            {
                "component": ["PC1", "PC2"],
                "explained_variance_ratio": pca.explained_variance_ratio_,
                "n_patients": len(pca_data),
            }
        ).to_csv(OUT / "keyboard_t1_pca_summary.csv", index=False)

    (OUT / "README_keyboard_t1_t2_delta_pca.md").write_text(
        "# Keyboard T1–T2 change and T1 PCA\n\n"
        "This isolated exploratory analysis pairs the existing Phase 11 midpoint T1 and Phase 12 midpoint T2 files. "
        "Feature change is defined as T2 minus T1. It also runs a two-feature standardized PCA on complete T1 cases. "
        "No SQL query, ACC output, or existing model output was changed.\n",
        encoding="utf-8",
    )
    print(f"Wrote paired keyboard delta and T1 PCA outputs to {OUT}")


if __name__ == "__main__":
    main()
