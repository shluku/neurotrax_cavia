from __future__ import annotations

from itertools import combinations
import os
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "output/analysis_candidates/phase4_t1_baseline"
DATASET_PATH = DATA_DIR / "phase4_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_t1_baseline_feature_metadata.csv"
OUT_DIR = DATA_DIR / "cluster_t1_baseline"

ASSIGNMENTS_PATH = OUT_DIR / "phase4_t1_cluster_assignments.csv"
QUALITY_PATH = OUT_DIR / "phase4_t1_cluster_quality.csv"
FEATURE_SUMMARY_PATH = OUT_DIR / "phase4_t1_cluster_feature_summary.csv"
PCA_LOADINGS_PATH = OUT_DIR / "phase4_t1_cluster_pca_loadings.csv"
README_PATH = OUT_DIR / "README_phase4_t1_clustering.md"

RANDOM_STATE = 20260726
K_VALUES = range(2, 6)
N_SEEDS = 20
MAX_PCS = 10


def build_readme(
    n_patients: int,
    n_features: int,
    n_pcs: int,
    quality: pd.DataFrame,
    best_k: int,
) -> str:
    best = quality[quality["k"] == best_k].iloc[0]
    return f"""# Phase 4 Exploratory T1 Baseline Clustering

This is an exploratory unsupervised analysis of the patient-level T1 baseline phenotype.

## Design

- Patients: `{n_patients}`.
- Features: `{n_features}` primary T1-week features only.
- Missing numeric feature values: cohort-median imputation for this descriptive clustering run.
- Scaling: standardized feature values.
- Dimension reduction: PCA to `{n_pcs}` components before clustering.
- Candidate cluster counts: `k=2` through `k=5`.
- Stability: 20 K-means seeds per candidate k, assessed with silhouette variation and pairwise adjusted Rand index.

## Selected Exploratory Solution

- Selected k by highest mean silhouette score: `{best_k}`.
- Mean silhouette at selected k: `{best['mean_silhouette']:.3f}`.
- Mean pairwise adjusted Rand stability at selected k: `{best['mean_pairwise_ari']:.3f}`.

Cluster labels are arbitrary identifiers, not clinical classes. The clustering should be interpreted alongside missingness, table coverage, device episodes, and the original feature distributions. It must not be presented as a validated patient taxonomy.

## Important Limitation

Median imputation and PCA are used here to create an analyzable exploratory representation. Missingness indicators were not included in the clustering input because that would encourage clusters to represent data availability rather than digital phenotype. Coverage variables remain in the assignment output for post hoc audit.

## Files

- `phase4_t1_cluster_assignments.csv`: patient cluster labels, PCA scores, and coverage audit fields.
- `phase4_t1_cluster_quality.csv`: silhouette and stability results for each candidate k.
- `phase4_t1_cluster_feature_summary.csv`: feature summaries by cluster.
- `phase4_t1_cluster_pca_loadings.csv`: PCA feature loadings for interpretation.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    features = metadata.loc[metadata["primary_model_recommendation"] == "include_primary", "feature_name"].tolist()
    X_raw = dataset[features].apply(pd.to_numeric, errors="coerce")
    imputed = SimpleImputer(strategy="median").fit_transform(X_raw)
    scaled = StandardScaler().fit_transform(imputed)
    n_pcs = min(MAX_PCS, scaled.shape[0] - 1, scaled.shape[1])
    pca = PCA(n_components=n_pcs, random_state=RANDOM_STATE)
    scores = pca.fit_transform(scaled)

    pca_columns = [f"PC{i}" for i in range(1, n_pcs + 1)]
    loadings = pd.DataFrame(pca.components_.T, columns=pca_columns)
    loadings.insert(0, "feature_name", features)
    loadings.to_csv(PCA_LOADINGS_PATH, index=False)

    quality_rows: list[dict[str, object]] = []
    labels_by_k: dict[int, list[np.ndarray]] = {}
    for k in K_VALUES:
        silhouettes: list[float] = []
        labels_list: list[np.ndarray] = []
        for seed_offset in range(N_SEEDS):
            model = KMeans(n_clusters=k, n_init=50, random_state=RANDOM_STATE + seed_offset)
            labels = model.fit_predict(scores)
            labels_list.append(labels)
            silhouettes.append(float(silhouette_score(scores, labels)))
        labels_by_k[k] = labels_list
        ari_values = [adjusted_rand_score(a, b) for a, b in combinations(labels_list, 2)]
        quality_rows.append(
            {
                "k": k,
                "n_seeds": N_SEEDS,
                "mean_silhouette": np.mean(silhouettes),
                "sd_silhouette": np.std(silhouettes),
                "min_silhouette": np.min(silhouettes),
                "max_silhouette": np.max(silhouettes),
                "mean_pairwise_ari": np.mean(ari_values),
                "min_pairwise_ari": np.min(ari_values),
                "max_pairwise_ari": np.max(ari_values),
            }
        )

    quality = pd.DataFrame(quality_rows).sort_values("k")
    best_k = int(quality.sort_values(["mean_silhouette", "mean_pairwise_ari"], ascending=False).iloc[0]["k"])
    final_model = KMeans(n_clusters=best_k, n_init=100, random_state=RANDOM_STATE)
    final_labels = final_model.fit_predict(scores)

    assignments = dataset[["Subject_ID_D", "Subject_ID_N", "global_T1", "baseline_feature_missing_fraction", "baseline_table_coverage_fraction"]].copy()
    assignments["cluster_k"] = best_k
    assignments["cluster_label"] = final_labels
    for index, column in enumerate(pca_columns):
        assignments[column] = scores[:, index]
    assignments.to_csv(ASSIGNMENTS_PATH, index=False)

    summary_rows: list[dict[str, object]] = []
    for cluster, group in assignments.groupby("cluster_label"):
        row = {"cluster_k": best_k, "cluster_label": cluster, "n_patients": len(group)}
        for column in ["global_T1", "baseline_feature_missing_fraction", "baseline_table_coverage_fraction"]:
            values = pd.to_numeric(group[column], errors="coerce")
            row[f"{column}_mean"] = values.mean()
            row[f"{column}_median"] = values.median()
        summary_rows.append(row)
    cluster_overview = pd.DataFrame(summary_rows)
    cluster_overview.to_csv(OUT_DIR / "phase4_t1_cluster_overview.csv", index=False)

    feature_summary_rows: list[dict[str, object]] = []
    for cluster, group in assignments.groupby("cluster_label"):
        indices = group.index
        for feature in features:
            values = X_raw.loc[indices, feature]
            feature_summary_rows.append(
                {
                    "cluster_k": best_k,
                    "cluster_label": cluster,
                    "n_patients": len(group),
                    "feature_name": feature,
                    "feature_mean": values.mean(),
                    "feature_median": values.median(),
                    "feature_missing_percent": 100 * values.isna().mean(),
                }
            )
    pd.DataFrame(feature_summary_rows).to_csv(FEATURE_SUMMARY_PATH, index=False)
    quality.to_csv(QUALITY_PATH, index=False)
    README_PATH.write_text(build_readme(len(dataset), len(features), n_pcs, quality, best_k), encoding="utf-8")

    print(f"patients: {len(dataset)}")
    print(f"primary_features: {len(features)}")
    print(f"pca_components: {n_pcs}")
    print(f"selected_k: {best_k}")
    print(quality.round(4).to_string(index=False))
    print(f"outputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
