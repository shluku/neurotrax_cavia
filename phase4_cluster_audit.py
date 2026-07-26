from __future__ import annotations

import os
from itertools import combinations
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
CLUSTER_DIR = DATA_DIR / "cluster_t1_baseline"
DATASET_PATH = DATA_DIR / "phase4_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_t1_baseline_feature_metadata.csv"
DEVICE_MAP_PATH = ROOT / "output/label_device_map.csv"

PCA_SCATTER_PATH = CLUSTER_DIR / "phase4_cluster_pca_scatter.csv"
AUDIT_SUMMARY_PATH = CLUSTER_DIR / "phase4_cluster_audit_summary.csv"
FEATURE_DIFF_PATH = CLUSTER_DIR / "phase4_cluster_feature_differences.csv"
HIGH_ASSIGNMENTS_PATH = CLUSTER_DIR / "phase4_cluster_high_coverage_assignments.csv"
HIGH_QUALITY_PATH = CLUSTER_DIR / "phase4_cluster_high_coverage_quality.csv"
README_PATH = CLUSTER_DIR / "README_phase4_clustering_audit.md"

RANDOM_STATE = 20260726
N_SEEDS = 20


def normalize_subject(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def cluster_representation(data: pd.DataFrame, features: list[str], k_values: range) -> tuple[pd.DataFrame, pd.DataFrame, PCA, StandardScaler]:
    raw = data[features].apply(pd.to_numeric, errors="coerce")
    imputed = SimpleImputer(strategy="median").fit_transform(raw)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(imputed)
    n_pcs = min(10, scaled.shape[0] - 1, scaled.shape[1])
    pca = PCA(n_components=n_pcs, random_state=RANDOM_STATE)
    scores = pca.fit_transform(scaled)

    quality_rows = []
    for k in k_values:
        labels_list = []
        silhouettes = []
        for seed_offset in range(N_SEEDS):
            labels = KMeans(n_clusters=k, n_init=50, random_state=RANDOM_STATE + seed_offset).fit_predict(scores)
            labels_list.append(labels)
            silhouettes.append(silhouette_score(scores, labels))
        ari = [adjusted_rand_score(a, b) for a, b in combinations(labels_list, 2)]
        quality_rows.append(
            {
                "k": k,
                "mean_silhouette": np.mean(silhouettes),
                "sd_silhouette": np.std(silhouettes),
                "mean_pairwise_ari": np.mean(ari),
                "min_pairwise_ari": np.min(ari),
            }
        )
    quality = pd.DataFrame(quality_rows)
    best_k = int(quality.sort_values(["mean_silhouette", "mean_pairwise_ari"], ascending=False).iloc[0]["k"])
    labels = KMeans(n_clusters=best_k, n_init=100, random_state=RANDOM_STATE).fit_predict(scores)
    assignments = pd.DataFrame({"cluster_k": best_k, "cluster_label": labels})
    for index in range(scores.shape[1]):
        assignments[f"PC{index + 1}"] = scores[:, index]
    return assignments, quality, pca, scaler


def main() -> None:
    CLUSTER_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    features = metadata.loc[metadata["primary_model_recommendation"] == "include_primary", "feature_name"].tolist()
    base_assignments = pd.read_csv(CLUSTER_DIR / "phase4_t1_cluster_assignments.csv", dtype={"Subject_ID_D": str})

    full_points, full_quality, _, scaler = cluster_representation(dataset, features, range(2, 6))
    full_points.insert(0, "Subject_ID_D", dataset["Subject_ID_D"].map(normalize_subject))
    full_points = full_points.merge(dataset[["Subject_ID_D", "global_T1", "baseline_feature_missing_fraction", "baseline_table_coverage_fraction"]], on="Subject_ID_D", how="left")
    full_points.to_csv(PCA_SCATTER_PATH, index=False)

    device_map = pd.read_csv(DEVICE_MAP_PATH, dtype=str)
    device_counts = {}
    for _, row in device_map.iterrows():
        subject = normalize_subject(row.get("label"))
        raw_ids = "" if pd.isna(row.get("device_ids")) else str(row.get("device_ids"))
        device_counts[subject] = len({x.strip() for x in raw_ids.split(";") if x.strip() and x.strip().lower() not in {"nan", "none"}})
    audit = base_assignments[["Subject_ID_D", "cluster_label"]].copy()
    audit["Subject_ID_D"] = audit["Subject_ID_D"].map(normalize_subject)
    audit = audit.merge(
        dataset[["Subject_ID_D", "age", "global_T1", "baseline_feature_missing_fraction", "baseline_table_coverage_fraction"]],
        on="Subject_ID_D",
        how="left",
    )
    audit["device_episode_count"] = audit["Subject_ID_D"].map(device_counts).fillna(0)
    audit.to_csv(CLUSTER_DIR / "phase4_cluster_patient_audit.csv", index=False)

    summary_rows = []
    for cluster, group in audit.groupby("cluster_label"):
        row = {"cluster_label": cluster, "n_patients": len(group)}
        for column in ["age", "global_T1", "baseline_feature_missing_fraction", "baseline_table_coverage_fraction", "device_episode_count"]:
            values = pd.to_numeric(group[column], errors="coerce")
            row[f"{column}_mean"] = values.mean()
            row[f"{column}_median"] = values.median()
        summary_rows.append(row)
    audit_summary = pd.DataFrame(summary_rows)
    audit_summary.to_csv(AUDIT_SUMMARY_PATH, index=False)

    raw = dataset[features].apply(pd.to_numeric, errors="coerce")
    imputed = SimpleImputer(strategy="median").fit_transform(raw)
    standardized = scaler.transform(imputed)
    cluster_labels = base_assignments["cluster_label"].to_numpy()
    feature_rows = []
    for index, feature in enumerate(features):
        means = [standardized[cluster_labels == cluster, index].mean() for cluster in sorted(set(cluster_labels))]
        feature_rows.append(
            {
                "feature_name": feature,
                "feature_family": metadata.loc[metadata["feature_name"] == feature, "feature_family"].iloc[0],
                "cluster_0_mean_z": means[0] if len(means) > 0 else np.nan,
                "cluster_1_mean_z": means[1] if len(means) > 1 else np.nan,
                "cluster_mean_difference_z": means[1] - means[0] if len(means) > 1 else np.nan,
                "absolute_difference_z": abs(means[1] - means[0]) if len(means) > 1 else np.nan,
                "cohort_missing_percent": 100 * raw[feature].isna().mean(),
            }
        )
    feature_differences = pd.DataFrame(feature_rows).sort_values("absolute_difference_z", ascending=False)
    feature_differences["rank"] = range(1, len(feature_differences) + 1)
    feature_differences.to_csv(FEATURE_DIFF_PATH, index=False)

    high_mask = (dataset["baseline_feature_missing_fraction"] <= 0.50) & (dataset["baseline_table_coverage_fraction"] >= 0.50)
    high_data = dataset.loc[high_mask].reset_index(drop=True)
    if len(high_data) < 12:
        raise RuntimeError(f"High-coverage subset has only {len(high_data)} patients; clustering requires at least 12.")
    high_points, high_quality, _, _ = cluster_representation(high_data, features, range(2, min(5, len(high_data) - 1)))
    high_points.insert(0, "Subject_ID_D", high_data["Subject_ID_D"].map(normalize_subject))
    high_points["baseline_feature_missing_fraction"] = high_data["baseline_feature_missing_fraction"].to_numpy()
    high_points["baseline_table_coverage_fraction"] = high_data["baseline_table_coverage_fraction"].to_numpy()
    high_points.to_csv(HIGH_ASSIGNMENTS_PATH, index=False)
    high_quality.to_csv(HIGH_QUALITY_PATH, index=False)

    best_high = high_quality.sort_values(["mean_silhouette", "mean_pairwise_ari"], ascending=False).iloc[0]
    best_full = full_quality.sort_values(["mean_silhouette", "mean_pairwise_ari"], ascending=False).iloc[0]
    README_PATH.write_text(
        f"""# Phase 4 Clustering Audit

This audit covers the first five clustering checks for Outcome 1.

## Full Cohort

- PCA scatter coordinates: `phase4_cluster_pca_scatter.csv`; the Streamlit page renders the scatter plot.
- Cluster quality: k=2 through k=5, with 20 seeds per k.
- Selected full-cohort k: `{int(best_full['k'])}`.

## Cluster Audit

`phase4_cluster_patient_audit.csv` and `phase4_cluster_audit_summary.csv` compare clusters on age, global T1, missingness, table coverage, and mapped device-episode count. `phase4_cluster_feature_differences.csv` ranks standardized feature differences between clusters.

## High-Coverage Re-clustering

The predefined high-coverage subset includes patients with:

- `baseline_feature_missing_fraction <= 0.50`
- `baseline_table_coverage_fraction >= 0.50`

Subset size: `{len(high_data)}` patients. The best subset solution is k=`{int(best_high['k'])}` with mean silhouette `{best_high['mean_silhouette']:.3f}` and mean pairwise ARI `{best_high['mean_pairwise_ari']:.3f}`.

The subset analysis is a sensitivity check. It does not prove that the full-cohort clusters are clinical or behavioral phenotypes.
""",
        encoding="utf-8",
    )
    print(f"full_patients: {len(dataset)}")
    print(f"high_coverage_patients: {len(high_data)}")
    print(f"full_selected_k: {int(best_full['k'])}")
    print(f"high_coverage_selected_k: {int(best_high['k'])}")
    print(f"outputs: {CLUSTER_DIR}")


if __name__ == "__main__":
    main()
