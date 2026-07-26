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

PROFILES_PATH = CLUSTER_DIR / "phase4_cluster_profiles.csv"
PROFILE_FEATURES_PATH = CLUSTER_DIR / "phase4_cluster_profile_features.csv"
STABILITY_PATH = CLUSTER_DIR / "phase4_cluster_stability.csv"
README_PATH = CLUSTER_DIR / "README_phase4_cluster_profiles.md"

RANDOM_STATE = 20260726
N_SEEDS = 20


def prepare_matrix(data: pd.DataFrame, features: list[str]) -> tuple[np.ndarray, np.ndarray]:
    raw = data[features].apply(pd.to_numeric, errors="coerce")
    imputed = SimpleImputer(strategy="median").fit_transform(raw)
    scaled = StandardScaler().fit_transform(imputed)
    return raw.to_numpy(dtype=float), scaled


def run_fixed_k(data: pd.DataFrame, features: list[str], k: int = 2) -> tuple[np.ndarray, float, float]:
    _, scaled = prepare_matrix(data, features)
    pca = PCA(n_components=min(10, scaled.shape[0] - 1, scaled.shape[1]), random_state=RANDOM_STATE)
    scores = pca.fit_transform(scaled)
    labels_list = []
    silhouettes = []
    for seed_offset in range(N_SEEDS):
        labels = KMeans(n_clusters=k, n_init=50, random_state=RANDOM_STATE + seed_offset).fit_predict(scores)
        labels_list.append(labels)
        silhouettes.append(silhouette_score(scores, labels))
    ari_values = [adjusted_rand_score(a, b) for a, b in combinations(labels_list, 2)]
    final_labels = KMeans(n_clusters=k, n_init=100, random_state=RANDOM_STATE).fit_predict(scores)
    return final_labels, float(np.mean(silhouettes)), float(np.mean(ari_values))


def feature_profile(data: pd.DataFrame, features: list[str], labels: np.ndarray) -> pd.DataFrame:
    raw, scaled = prepare_matrix(data, features)
    rows = []
    for index, feature in enumerate(features):
        means = {cluster: float(scaled[labels == cluster, index].mean()) for cluster in sorted(set(labels))}
        rows.append(
            {
                "feature_name": feature,
                "cluster_0_mean_z": means.get(0, np.nan),
                "cluster_1_mean_z": means.get(1, np.nan),
                "cluster_difference_z": means.get(1, np.nan) - means.get(0, np.nan),
                "absolute_difference_z": abs(means.get(1, np.nan) - means.get(0, np.nan)),
                "cohort_missing_percent": 100 * np.isnan(raw[:, index]).mean(),
            }
        )
    return pd.DataFrame(rows).sort_values("absolute_difference_z", ascending=False)


def main() -> None:
    cluster_dir = CLUSTER_DIR
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    features = metadata.loc[metadata["primary_model_recommendation"] == "include_primary", "feature_name"].tolist()
    full_assignments = pd.read_csv(cluster_dir / "phase4_t1_cluster_assignments.csv", dtype={"Subject_ID_D": str})
    full_labels = full_assignments["cluster_label"].to_numpy()

    profiles_features = feature_profile(dataset, features, full_labels)
    metadata_family = metadata.set_index("feature_name")["feature_family"].to_dict()
    profiles_features["feature_family"] = profiles_features["feature_name"].map(metadata_family)
    profiles_features["rank"] = range(1, len(profiles_features) + 1)
    profiles_features.to_csv(PROFILE_FEATURES_PATH, index=False)

    profile_rows = []
    for cluster in sorted(set(full_labels)):
        group = dataset.loc[full_labels == cluster]
        top = profiles_features.head(8)
        cluster_mean_column = f"cluster_{cluster}_mean_z"
        top_positive = profiles_features.sort_values(cluster_mean_column, ascending=False).head(5)["feature_name"].tolist()
        top_negative = profiles_features.sort_values(cluster_mean_column, ascending=True).head(5)["feature_name"].tolist()
        profile_rows.append(
            {
                "cluster_label": cluster,
                "n_patients": len(group),
                "global_T1_mean": pd.to_numeric(group["global_T1"], errors="coerce").mean(),
                "global_T1_median": pd.to_numeric(group["global_T1"], errors="coerce").median(),
                "missing_fraction_mean": group["baseline_feature_missing_fraction"].mean(),
                "table_coverage_mean": group["baseline_table_coverage_fraction"].mean(),
                "profile_interpretation": "descriptive feature pattern only; not a clinical subtype",
                "largest_absolute_feature_differences": ";".join(top["feature_name"].tolist()),
                "features_higher_in_this_cluster": ";".join(top_positive),
                "features_lower_in_this_cluster": ";".join(top_negative),
            }
        )
    profiles = pd.DataFrame(profile_rows)
    profiles.to_csv(PROFILES_PATH, index=False)

    high_patient_mask = (dataset["baseline_feature_missing_fraction"] <= 0.50) & (dataset["baseline_table_coverage_fraction"] >= 0.50)
    high_data = dataset.loc[high_patient_mask].reset_index(drop=True)
    high_full_labels = full_labels[high_patient_mask.to_numpy()]
    strict_features = metadata.loc[
        (metadata["primary_model_recommendation"] == "include_primary")
        & (pd.to_numeric(metadata["missing_percent"], errors="coerce") <= 25),
        "feature_name",
    ].tolist()

    methods = [
        ("full_primary_features", dataset, features, full_labels),
        ("high_coverage_patients_primary_features", high_data, features, None),
        ("strict_feature_coverage_full_patients", dataset, strict_features, None),
    ]
    stability_rows = []
    for method, method_data, method_features, known_labels in methods:
        labels, silhouette, seed_ari = run_fixed_k(method_data, method_features, k=2)
        if method == "full_primary_features":
            ari_vs_full = 1.0
        elif method == "high_coverage_patients_primary_features":
            ari_vs_full = adjusted_rand_score(high_full_labels, labels)
        else:
            ari_vs_full = adjusted_rand_score(full_labels, labels)
        counts = pd.Series(labels).value_counts().sort_index()
        stability_rows.append(
            {
                "method": method,
                "n_patients": len(method_data),
                "n_features": len(method_features),
                "cluster_0_n": int(counts.get(0, 0)),
                "cluster_1_n": int(counts.get(1, 0)),
                "mean_silhouette": silhouette,
                "mean_pairwise_seed_ari": seed_ari,
                "ari_vs_full_primary_solution": ari_vs_full,
                "coverage_rule": "none" if method == "full_primary_features" else "patients missing <=50%, table coverage >=50%" if method.startswith("high_") else "features missing <=25%",
            }
        )
    stability = pd.DataFrame(stability_rows)
    stability.to_csv(STABILITY_PATH, index=False)

    README_PATH.write_text(
        f"""# Phase 4 Exploratory Cluster Profiles and Stability

This stage creates interpretable descriptive profiles for the full-cohort exploratory clusters and tests whether the two-cluster solution remains similar after reducing coverage-related effects.

## Profile Rule

Profiles use standardized feature means and ranked absolute cluster differences. They describe relative digital feature patterns only. They are not clinical subtypes.

## Stability Checks

- `full_primary_features`: all 81 patients and 37 primary features.
- `high_coverage_patients_primary_features`: patients with feature missingness <=50% and table coverage >=50%.
- `strict_feature_coverage_full_patients`: all patients, limited to primary features missing in <=25% of the cohort.

`ari_vs_full_primary_solution` compares each controlled solution with the original full-cohort labels. Low or moderate ARI means the original clusters are sensitive to coverage restrictions and should not be treated as stable phenotypes.

## Outputs

- `phase4_cluster_profiles.csv`: patient-level cluster profile summaries.
- `phase4_cluster_profile_features.csv`: ranked standardized feature patterns.
- `phase4_cluster_stability.csv`: coverage-control stability comparisons.
""",
        encoding="utf-8",
    )
    print(f"profiles: {PROFILES_PATH}")
    print(stability.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
