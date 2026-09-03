"""Exploratory unsupervised phenotyping for the median-timespan T1 cohort.

This analysis is intentionally separate from the supervised T1/T2 models. The
observed cognitive scores are carried into the output for post-hoc description,
but they are never used to create the PCA representation or cluster labels.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import RobustScaler


ROOT = Path(__file__).parent
INPUT_DIR = ROOT / "output/analysis_candidates/phase11_t1_baseline"
DATASET_PATH = INPUT_DIR / "phase11_t1_baseline_patient_dataset.csv"
METADATA_PATH = INPUT_DIR / "phase11_t1_baseline_feature_metadata.csv"
OUTPUT_DIR = ROOT / "output/analysis_candidates/unsupervised_phenotyping_median_span"

RANDOM_STATE = 20260826
MAX_PCS = 10
CLUSTER_K_VALUES = range(2, 5)
N_SEEDS = 20
N_RESAMPLES = 100
PATIENT_FEATURE_COVERAGE_THRESHOLD = 0.50

ID_COLUMNS = ["Subject_ID_N", "Subject_ID_D"]
OUTCOME_COLUMNS = [
    "global_T1",
    "memory_T1",
    "ef_T1",
    "processing_speed_T1",
    "attention_T1",
    "motor_T1",
]
AUDIT_COLUMNS = [
    "baseline_feature_missing_count",
    "baseline_feature_missing_fraction",
    "baseline_table_coverage_fraction",
]

PANEL_DEFINITIONS = {
    "usable_catalog_50pct": {
        "label": "Usable feature catalog (>=50% patient coverage)",
        "description": "All catalog features observed in at least half of the 81 source patients.",
        "coverage_threshold": 50.0,
    },
    "primary_37": {
        "label": "Primary 37 features",
        "description": "The predefined primary baseline feature set.",
        "recommendation": "include_primary",
    },
    "expanded_catalog_10pct": {
        "label": "Expanded catalog (>=10% patient coverage)",
        "description": "Catalog features observed in at least 10% of the source patients; sensitivity analysis only.",
        "coverage_threshold": 10.0,
    },
}


def _safe_text(value: object) -> str:
    return "" if pd.isna(value) else str(value)


def _format_median_iqr(values: pd.Series) -> str:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return "NA"
    return f"{numeric.median():.2f} ({numeric.quantile(0.25):.2f}-{numeric.quantile(0.75):.2f})"


def _is_fraction_like(feature: str) -> bool:
    lowered = feature.lower()
    return any(token in lowered for token in ("fraction", "ratio", "diversity"))


def _prepare_feature_matrix(
    raw: pd.DataFrame,
) -> tuple[np.ndarray, pd.DataFrame, pd.DataFrame]:
    """Transform, impute, and robust-scale a patient-by-feature matrix."""

    transformed = pd.DataFrame(index=raw.index)
    transform_rows: list[dict[str, object]] = []
    for feature in raw.columns:
        values = pd.to_numeric(raw[feature], errors="coerce")
        valid = values.dropna()
        transform = "none"
        if (
            not valid.empty
            and (valid >= 0).all()
            and not _is_fraction_like(feature)
            and valid.nunique() > 1
            and abs(float(valid.skew())) > 1.5
        ):
            transformed[feature] = np.log1p(values)
            transform = "log1p_nonnegative_skewed"
        else:
            transformed[feature] = values
        transform_rows.append(
            {
                "feature_name": feature,
                "transformation": transform,
                "n_observed_before_imputation": int(valid.size),
                "missing_percent_before_imputation": float(values.isna().mean() * 100),
            }
        )

    medians = transformed.median(numeric_only=True)
    imputed = transformed.fillna(medians)
    # A selected feature must have observations in the source cohort, but the
    # fallback keeps the pipeline explicit if a future input contains a blank
    # or constant column.
    imputed = imputed.fillna(0.0)
    scaler = RobustScaler(quantile_range=(25.0, 75.0))
    scaled = scaler.fit_transform(imputed.to_numpy(dtype=float))
    transform_table = pd.DataFrame(transform_rows)
    imputation_table = pd.DataFrame(
        {
            "feature_name": raw.columns,
            "imputation_value_after_transformation": [float(medians.get(feature, 0.0)) for feature in raw.columns],
        }
    )
    return scaled, transform_table.merge(imputation_table, on="feature_name"), transformed


def _select_features(dataset: pd.DataFrame, metadata: pd.DataFrame, panel_name: str) -> tuple[list[str], pd.DataFrame]:
    panel = PANEL_DEFINITIONS[panel_name]
    metadata = metadata.drop_duplicates("feature_name").copy()
    present = set(dataset.columns)
    metadata = metadata[metadata["feature_name"].isin(present)].copy()
    coverage = dataset[metadata["feature_name"].tolist()].notna().mean().mul(100)
    metadata["source_patient_coverage_percent"] = metadata["feature_name"].map(coverage)
    if "recommendation" in panel:
        selected = metadata[metadata["primary_model_recommendation"].eq(panel["recommendation"])]
    else:
        selected = metadata[metadata["source_patient_coverage_percent"].ge(panel["coverage_threshold"])]
    selected = selected.sort_values("feature_name").copy()
    selected["selected_for_panel"] = True
    return selected["feature_name"].tolist(), selected


def _cluster_quality(scores: np.ndarray, k: int) -> dict[str, object]:
    seed_labels: list[np.ndarray] = []
    silhouettes: list[float] = []
    for offset in range(N_SEEDS):
        labels = KMeans(
            n_clusters=k,
            n_init=50,
            random_state=RANDOM_STATE + offset,
        ).fit_predict(scores)
        seed_labels.append(labels)
        silhouettes.append(float(silhouette_score(scores, labels)))

    seed_ari = [
        adjusted_rand_score(seed_labels[left], seed_labels[right])
        for left in range(len(seed_labels))
        for right in range(left + 1, len(seed_labels))
    ]

    rng = np.random.default_rng(RANDOM_STATE + k)
    resample_ari: list[float] = []
    n_resample = max(k * 3, int(round(scores.shape[0] * 0.80)))
    for _ in range(N_RESAMPLES):
        indices = rng.choice(scores.shape[0], size=n_resample, replace=False)
        resampled_model = KMeans(
            n_clusters=k,
            n_init=25,
            random_state=int(rng.integers(0, 2**31 - 1)),
        ).fit(scores[indices])
        resample_ari.append(float(adjusted_rand_score(seed_labels[0], resampled_model.predict(scores))))

    final_labels = seed_labels[0]
    counts = pd.Series(final_labels).value_counts()
    return {
        "k": k,
        "n_seeds": N_SEEDS,
        "n_resamples": N_RESAMPLES,
        "mean_silhouette": float(np.mean(silhouettes)),
        "sd_silhouette": float(np.std(silhouettes)),
        "mean_pairwise_seed_ari": float(np.mean(seed_ari)),
        "min_pairwise_seed_ari": float(np.min(seed_ari)),
        "mean_subsample_ari_vs_reference": float(np.mean(resample_ari)),
        "min_subsample_ari_vs_reference": float(np.min(resample_ari)),
        "min_cluster_n_reference": int(counts.min()),
        "max_cluster_n_reference": int(counts.max()),
    }


def _cluster_feature_profiles(
    raw: pd.DataFrame,
    scaled: np.ndarray,
    labels: np.ndarray,
    feature_metadata: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    features = raw.columns.tolist()
    metadata_lookup = feature_metadata.set_index("feature_name", drop=False)
    for cluster in sorted(np.unique(labels)):
        mask = labels == cluster
        for index, feature in enumerate(features):
            values = raw.loc[mask, feature]
            meta = metadata_lookup.loc[feature]
            rows.append(
                {
                    "cluster_label": int(cluster),
                    "feature_name": feature,
                    "source_table": _safe_text(meta.get("source_table")),
                    "feature_family": _safe_text(meta.get("feature_family")),
                    "source_patient_coverage_percent": float(meta.get("source_patient_coverage_percent", np.nan)),
                    "cluster_n_patients": int(mask.sum()),
                    "cluster_median_iqr": _format_median_iqr(values),
                    "cluster_mean_scaled": float(np.mean(scaled[mask, index])),
                    "cluster_missing_percent": float(values.isna().mean() * 100),
                }
            )
    profiles = pd.DataFrame(rows)
    profiles["absolute_cluster_mean_scaled"] = profiles["cluster_mean_scaled"].abs()
    profiles["within_cluster_rank"] = profiles.groupby("cluster_label")["absolute_cluster_mean_scaled"].rank(
        method="first", ascending=False
    )
    return profiles.sort_values(["cluster_label", "within_cluster_rank", "feature_name"])


def _write_panel(dataset: pd.DataFrame, metadata: pd.DataFrame, panel_name: str) -> dict[str, object]:
    panel_dir = OUTPUT_DIR / panel_name
    panel_dir.mkdir(parents=True, exist_ok=True)
    features, selected_metadata = _select_features(dataset, metadata, panel_name)
    if len(features) < 2:
        raise RuntimeError(f"Panel {panel_name} has fewer than two usable features")

    raw_source = dataset[features].apply(pd.to_numeric, errors="coerce")
    patient_feature_coverage = raw_source.notna().mean(axis=1)
    included = patient_feature_coverage.ge(PATIENT_FEATURE_COVERAGE_THRESHOLD)
    if int(included.sum()) < 12:
        raise RuntimeError(f"Panel {panel_name} has fewer than 12 analyzable patients")

    raw = raw_source.loc[included].reset_index(drop=True)
    cohort = dataset.loc[included].reset_index(drop=True)
    scaled, transform_table, transformed = _prepare_feature_matrix(raw)
    n_pcs = min(MAX_PCS, scaled.shape[0] - 1, scaled.shape[1])
    pca = PCA(n_components=n_pcs, random_state=RANDOM_STATE)
    scores = pca.fit_transform(scaled)
    pc_columns = [f"PC{i}" for i in range(1, n_pcs + 1)]

    variance = pd.DataFrame(
        {
            "component": pc_columns,
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "explained_variance_percent": pca.explained_variance_ratio_ * 100,
            "cumulative_explained_variance_percent": np.cumsum(pca.explained_variance_ratio_) * 100,
        }
    )
    variance.to_csv(panel_dir / "pca_variance.csv", index=False)

    loadings = pd.DataFrame(pca.components_.T, columns=pc_columns)
    loadings.insert(0, "feature_name", features)
    loadings["source_table"] = loadings["feature_name"].map(selected_metadata.set_index("feature_name")["source_table"])
    loadings["feature_family"] = loadings["feature_name"].map(selected_metadata.set_index("feature_name")["feature_family"])
    loadings["maximum_absolute_loading"] = loadings[pc_columns].abs().max(axis=1)
    loadings = loadings.sort_values("maximum_absolute_loading", ascending=False)
    loadings.to_csv(panel_dir / "pca_loadings.csv", index=False)

    quality = pd.DataFrame([_cluster_quality(scores, k) for k in CLUSTER_K_VALUES])
    eligible_quality = quality[quality["min_cluster_n_reference"].ge(5)]
    if eligible_quality.empty:
        eligible_quality = quality
    selected_row = eligible_quality.sort_values(
        ["mean_silhouette", "mean_subsample_ari_vs_reference"], ascending=False
    ).iloc[0]
    selected_k = int(selected_row["k"])
    quality["selected_solution"] = quality["k"].eq(selected_k)
    quality.to_csv(panel_dir / "cluster_quality.csv", index=False)

    final_model = KMeans(n_clusters=selected_k, n_init=100, random_state=RANDOM_STATE)
    labels = final_model.fit_predict(scores)
    scores_frame = cohort[ID_COLUMNS + OUTCOME_COLUMNS + AUDIT_COLUMNS].copy()
    scores_frame["patient_feature_coverage_fraction"] = patient_feature_coverage.loc[included].to_numpy()
    scores_frame["cluster_k"] = selected_k
    scores_frame["cluster_label"] = labels
    for index, column in enumerate(pc_columns):
        scores_frame[column] = scores[:, index]
    scores_frame.to_csv(panel_dir / "pca_patient_scores.csv", index=False)

    feature_profiles = _cluster_feature_profiles(raw, scaled, labels, selected_metadata)
    feature_profiles.to_csv(panel_dir / "cluster_feature_profiles.csv", index=False)

    profile_rows: list[dict[str, object]] = []
    for cluster in sorted(np.unique(labels)):
        group = cohort.loc[labels == cluster]
        row: dict[str, object] = {
            "cluster_k": selected_k,
            "cluster_label": int(cluster),
            "n_patients": int(len(group)),
            "patient_feature_coverage_mean_percent": float(patient_feature_coverage.loc[included].iloc[labels == cluster].mean() * 100),
            "baseline_feature_missing_fraction_mean_percent": float(
                pd.to_numeric(group["baseline_feature_missing_fraction"], errors="coerce").mean() * 100
            ),
            "global_T1_median_iqr": _format_median_iqr(group["global_T1"]),
            "memory_T1_median_iqr": _format_median_iqr(group["memory_T1"]),
            "executive_function_T1_median_iqr": _format_median_iqr(group["ef_T1"]),
            "processing_speed_T1_median_iqr": _format_median_iqr(group["processing_speed_T1"]),
            "attention_T1_median_iqr": _format_median_iqr(group["attention_T1"]),
            "motor_T1_median_iqr": _format_median_iqr(group["motor_T1"]),
        }
        top = feature_profiles[feature_profiles["cluster_label"].eq(cluster)].head(8)
        row["largest_absolute_cluster_features"] = ";".join(top["feature_name"].tolist())
        profile_rows.append(row)
    pd.DataFrame(profile_rows).to_csv(panel_dir / "cluster_profiles.csv", index=False)

    audit = dataset[ID_COLUMNS + OUTCOME_COLUMNS + AUDIT_COLUMNS].copy()
    audit["panel_feature_count"] = len(features)
    audit["panel_feature_observed_count"] = raw_source.notna().sum(axis=1).to_numpy()
    audit["panel_feature_coverage_fraction"] = patient_feature_coverage.to_numpy()
    audit["included_in_pca_and_clustering"] = included.to_numpy()
    audit.to_csv(panel_dir / "patient_cohort_audit.csv", index=False)

    inventory = metadata.copy()
    inventory["selected_for_panel"] = inventory["feature_name"].isin(features)
    inventory["transformation"] = inventory["feature_name"].map(
        transform_table.set_index("feature_name")["transformation"]
    )
    inventory["imputation_value_after_transformation"] = inventory["feature_name"].map(
        transform_table.set_index("feature_name")["imputation_value_after_transformation"]
    )
    inventory.to_csv(panel_dir / "feature_inventory.csv", index=False)
    transform_table.to_csv(panel_dir / "feature_transformations.csv", index=False)

    selected_summary = {
        "panel_name": panel_name,
        "panel_label": PANEL_DEFINITIONS[panel_name]["label"],
        "panel_description": PANEL_DEFINITIONS[panel_name]["description"],
        "source_patients": int(len(dataset)),
        "analyzed_patients": int(included.sum()),
        "excluded_patients_for_panel_availability": int((~included).sum()),
        "selected_features": int(len(features)),
        "n_pcs": int(n_pcs),
        "selected_k": selected_k,
        "pc1_pc2_explained_variance_percent": float(variance.head(2)["explained_variance_percent"].sum()),
        "mean_silhouette_selected_k": float(selected_row["mean_silhouette"]),
        "mean_subsample_ari_selected_k": float(selected_row["mean_subsample_ari_vs_reference"]),
        "patient_feature_coverage_threshold_percent": PATIENT_FEATURE_COVERAGE_THRESHOLD * 100,
        "feature_coverage_threshold_percent": PANEL_DEFINITIONS[panel_name].get("coverage_threshold", np.nan),
    }
    (panel_dir / "panel_summary.json").write_text(json.dumps(selected_summary, indent=2), encoding="utf-8")
    return selected_summary


def _write_readme(summaries: list[dict[str, object]]) -> None:
    default = next(summary for summary in summaries if summary["panel_name"] == "usable_catalog_50pct")
    lines = [
        "# Exploratory Unsupervised Phenotyping: Median-Timespan T1 Cohort",
        "",
        "This is a separate, exploratory unsupervised analysis of the largest currently available patient-level baseline cohort. The source cohort contains 81 patients from the median-timespan baseline extraction.",
        "",
        "## Primary Representation",
        "",
        f"The default representation uses {default['selected_features']} catalog features observed in at least 50% of source patients. Patients must have at least 50% of the selected features observed to enter PCA and clustering; this produced {default['analyzed_patients']} analyzable patients while retaining all 81 source patients in the audit.",
        "",
        "- Counts and other highly right-skewed non-fraction features use log1p when skewness exceeds 1.5.",
        "- Remaining missing feature values are imputed with the feature median after transformation.",
        "- Features are robust-scaled using the 25th and 75th percentiles before PCA.",
        "- Missingness and coverage are not clustering inputs; they are retained for post-hoc audit.",
        "- The observed cognitive scores are not used to build PCA or clusters. They are overlaid afterward for interpretation.",
        "",
        "## Dimension Reduction and Clustering",
        "",
        "PCA is used to describe the main axes of variation. K-means clustering is evaluated for k=2, 3, and 4 on the first 10 PCA components, or fewer when the matrix requires it. Candidate solutions are compared using silhouette, repeated-seed adjusted Rand index, and 100 80%-subsample refits. Cluster labels are arbitrary and do not represent clinical diagnoses.",
        "",
        "## Sensitivity Panels",
        "",
        "- `primary_37`: predefined primary feature set.",
        "- `usable_catalog_50pct`: default catalog panel with at least 50% source-patient coverage.",
        "- `expanded_catalog_10pct`: exploratory sensitivity panel allowing features observed in at least 10% of source patients.",
        "",
        "The panels are run separately because changing the acquisition window or coverage rule changes the feature matrix. They should not be pooled into one model.",
        "",
        "## Interpretation Boundary",
        "",
        "A visually separated PCA plot or a high silhouette does not establish a clinical subtype. Any apparent structure must be checked against coverage, missingness, device availability, feature transformations, and sensitivity panels before it is described as a digital phenotype.",
        "",
        "## Outputs",
        "",
        "Each panel directory contains patient PCA scores, loadings, cluster quality, cluster profiles, feature profiles, cohort audit, feature inventory, and transformation records.",
    ]
    (OUTPUT_DIR / "README_unsupervised_phenotyping.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    summaries = [_write_panel(dataset, metadata, panel_name) for panel_name in PANEL_DEFINITIONS]
    pd.DataFrame(summaries).to_csv(OUTPUT_DIR / "panel_summary.csv", index=False)
    _write_readme(summaries)
    print(pd.DataFrame(summaries).round(4).to_string(index=False))
    print(f"outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
