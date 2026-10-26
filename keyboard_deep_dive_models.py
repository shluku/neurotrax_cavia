"""Keyboard-only supervised and unsupervised analyses.

This workstream consumes only the isolated Keyboard Deep Dive v1 window output.
It writes to a separate models directory and never changes the existing digital,
ACC, or Full Model PCA outputs.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import TransformedTargetRegressor
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, ElasticNetCV, Ridge, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, silhouette_score
from sklearn.model_selection import RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler


ROOT = Path(__file__).parent
DEEP_DIR = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1"
OUT = DEEP_DIR / "models"
WINDOW_PATH = DEEP_DIR / "keyboard_deep_dive_window_features.csv"
T1_PATH = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"
T2_PATH = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv"
RANDOM_STATE = 20261020

OUTCOMES = {
    "global": "global",
    "memory": "memory",
    "executive_function": "ef",
    "processing_speed": "processing_speed",
    "attention": "attention",
    "motor": "motor",
}


def normalize_id(value: object) -> str:
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def keyboard_features(columns: list[str]) -> list[str]:
    excluded = (
        "raw_rows", "duplicate_rows", "json_parse", "valid_interval_count",
        "distinct_observations_in_window", "window_start", "window_end",
    )
    return [
        c for c in columns
        if c.startswith("keyboard_") and not any(token in c for token in excluded)
    ]


def build_datasets() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    windows = pd.read_csv(WINDOW_PATH, dtype={"Subject_ID_D": str})
    windows["Subject_ID_D"] = windows["Subject_ID_D"].map(normalize_id)
    t1 = pd.read_csv(T1_PATH, dtype={"Subject_ID_D": str})
    t2 = pd.read_csv(T2_PATH, dtype={"Subject_ID_D": str})
    t1["Subject_ID_D"] = t1["Subject_ID_D"].map(normalize_id)
    t2["Subject_ID_D"] = t2["Subject_ID_D"].map(normalize_id)
    features = keyboard_features(windows.columns.tolist())
    t1k = windows[windows["window_name"].eq("T1")][["Subject_ID_D", *features]].copy()
    t2k = windows[windows["window_name"].eq("T2")][["Subject_ID_D", *features]].copy()
    t1k = t1k.rename(columns={c: f"{c}_T1" for c in features})
    t2k = t2k.rename(columns={c: f"{c}_T2" for c in features})
    t1_base = t1[["Subject_ID_D", *[f"{v}_T1" for v in OUTCOMES.values()]]].copy()
    t2_base = t2[["Subject_ID_D", *[f"{v}_delta" for v in OUTCOMES.values()]]].copy()
    t1_base = t1_base.merge(t1k, on="Subject_ID_D", how="left")
    paired = t1_base.merge(t2_base, on="Subject_ID_D", how="left").merge(t2k, on="Subject_ID_D", how="left")
    for feature in features:
        paired[f"{feature}_delta"] = pd.to_numeric(paired[f"{feature}_T2"], errors="coerce") - pd.to_numeric(paired[f"{feature}_T1"], errors="coerce")
    return t1_base, paired, features


def model_pipelines(seed: int) -> dict[str, Pipeline]:
    common = [
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", RobustScaler()),
    ]
    return {
        "ridge": Pipeline(common + [("model", RidgeCV(alphas=np.logspace(-3, 3, 25)))]) ,
        "elastic_net": Pipeline(common + [("model", ElasticNetCV(l1_ratio=[.1, .5, .9, 1.0], alphas=np.logspace(-3, 2, 20), cv=3, max_iter=20000, random_state=seed))]),
        "random_forest": Pipeline([("imputer", SimpleImputer(strategy="median", add_indicator=True)), ("model", RandomForestRegressor(n_estimators=300, min_samples_leaf=4, max_features="sqrt", random_state=seed, n_jobs=1))]),
    }


def evaluate_target(data: pd.DataFrame, feature_columns: list[str], target: str, task: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = data[["Subject_ID_D", target, *feature_columns]].copy()
    frame[target] = pd.to_numeric(frame[target], errors="coerce")
    for col in feature_columns:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=[target]).reset_index(drop=True)
    if len(frame) < 12:
        return pd.DataFrame([{"task": task, "target": target, "status": "insufficient_target_n", "n": len(frame)}]), pd.DataFrame()
    X = frame[feature_columns]
    y = frame[target].to_numpy(dtype=float)
    n_splits = min(5, max(2, len(frame) // 5))
    cv = RepeatedKFold(n_splits=n_splits, n_repeats=20, random_state=RANDOM_STATE)
    predictions: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    for repeat, (train_idx, test_idx) in enumerate(cv.split(X), start=1):
        y_train = y[train_idx]
        baseline = float(np.mean(y_train))
        for model_name, model in {"mean_baseline": None, **model_pipelines(RANDOM_STATE + repeat)}.items():
            if model_name == "mean_baseline":
                pred = np.full(len(test_idx), baseline)
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model.fit(X.iloc[train_idx], y_train)
                pred = model.predict(X.iloc[test_idx])
            for idx, actual, estimate in zip(test_idx, y[test_idx], pred):
                predictions.append({"task": task, "target": target, "model": model_name, "repeat": repeat, "Subject_ID_D": frame.iloc[idx]["Subject_ID_D"], "actual": actual, "prediction": float(estimate)})
            metrics.append({"task": task, "target": target, "model": model_name, "repeat": repeat, "n_train": len(train_idx), "n_test": len(test_idx), "rmse": float(mean_squared_error(y[test_idx], pred) ** 0.5), "mae": float(mean_absolute_error(y[test_idx], pred)), "r2": float(r2_score(y[test_idx], pred)) if len(test_idx) > 1 else np.nan, "baseline_train_mean": baseline})
    return pd.DataFrame(metrics), pd.DataFrame(predictions)


def write_supervised(t1: pd.DataFrame, paired: pd.DataFrame, features: list[str]) -> dict[str, object]:
    rows: list[pd.DataFrame] = []
    prediction_rows: list[pd.DataFrame] = []
    for name, prefix in OUTCOMES.items():
        t1_target = f"{prefix}_T1"
        metrics, predictions = evaluate_target(t1, [f"{f}_T1" for f in features], t1_target, f"T1_{name}")
        rows.append(metrics); prediction_rows.append(predictions)
        delta_target = f"{prefix}_delta"
        metrics, predictions = evaluate_target(paired, [f"{f}_delta" for f in features], delta_target, f"T2_minus_T1_{name}")
        rows.append(metrics); prediction_rows.append(predictions)
    metrics_df = pd.concat(rows, ignore_index=True)
    predictions_df = pd.concat(prediction_rows, ignore_index=True)
    metrics_df.to_csv(OUT / "supervised_fold_metrics.csv", index=False)
    predictions_df.to_csv(OUT / "supervised_predictions.csv", index=False)
    summary = metrics_df.groupby(["task", "target", "model"], dropna=False).agg(
        n_folds=("repeat", "count"), rmse_mean=("rmse", "mean"), rmse_sd=("rmse", "std"), mae_mean=("mae", "mean"), r2_mean=("r2", "mean")
    ).reset_index()
    summary.to_csv(OUT / "supervised_summary.csv", index=False)
    return {"tasks": int(metrics_df["task"].nunique()), "fold_metric_rows": int(len(metrics_df))}


def unsupervised_keyboard(t1: pd.DataFrame, features: list[str]) -> dict[str, object]:
    cols = [f"{f}_T1" for f in features]
    raw = t1[cols].apply(pd.to_numeric, errors="coerce")
    included = raw.notna().mean(axis=1).ge(0.50)
    raw = raw.loc[included].reset_index(drop=True)
    cohort = t1.loc[included].reset_index(drop=True)
    if len(raw) < 12 or len(cols) < 2:
        return {"status": "insufficient_keyboard_cohort", "n": len(raw)}
    transformed = raw.copy()
    for col in transformed.columns:
        valid = transformed[col].dropna()
        if not valid.empty and (valid >= 0).all() and valid.nunique() > 1 and abs(float(valid.skew())) > 1.5:
            transformed[col] = np.log1p(transformed[col])
    matrix = SimpleImputer(strategy="median").fit_transform(transformed)
    scaled = RobustScaler().fit_transform(matrix)
    pca = PCA(n_components=min(10, scaled.shape[0] - 1, scaled.shape[1]), random_state=RANDOM_STATE)
    scores = pca.fit_transform(scaled)
    variance = pd.DataFrame({"component": [f"PC{i}" for i in range(1, len(pca.explained_variance_ratio_) + 1)], "explained_variance_percent": pca.explained_variance_ratio_ * 100})
    variance.to_csv(OUT / "unsupervised_pca_variance.csv", index=False)
    loadings = pd.DataFrame(pca.components_.T, columns=variance["component"])
    loadings.insert(0, "feature_name", features)
    loadings.to_csv(OUT / "unsupervised_pca_loadings.csv", index=False)
    quality_rows = []
    selected = None
    for k in range(2, min(4, len(raw) - 1) + 1):
        labels = KMeans(n_clusters=k, n_init=50, random_state=RANDOM_STATE).fit_predict(scores)
        quality_rows.append({"k": k, "silhouette": float(silhouette_score(scores, labels)), "min_cluster_n": int(pd.Series(labels).value_counts().min()), "max_cluster_n": int(pd.Series(labels).value_counts().max())})
    quality = pd.DataFrame(quality_rows)
    eligible = quality[quality["min_cluster_n"].ge(5)]
    if not eligible.empty:
        selected = int(eligible.sort_values("silhouette", ascending=False).iloc[0]["k"])
    else:
        selected = int(quality.sort_values(["min_cluster_n", "silhouette"], ascending=[False, False]).iloc[0]["k"])
    quality["selected_solution"] = quality["k"].eq(selected) & bool(not eligible.empty)
    quality.to_csv(OUT / "unsupervised_cluster_quality.csv", index=False)
    labels = KMeans(n_clusters=selected, n_init=100, random_state=RANDOM_STATE).fit_predict(scores)
    score_frame = cohort[["Subject_ID_D", *[f"{prefix}_T1" for prefix in OUTCOMES.values()]]].copy()
    score_frame["cluster_k"] = selected
    score_frame["cluster_label"] = labels
    for idx in range(scores.shape[1]):
        score_frame[f"PC{idx + 1}"] = scores[:, idx]
    score_frame.to_csv(OUT / "unsupervised_patient_scores.csv", index=False)
    return {"status": "complete", "n_patients": len(raw), "n_features": len(features), "selected_k": selected, "pc1_pc2_percent": float(variance.head(2)["explained_variance_percent"].sum()), "acceptable_cluster_solution": bool(not eligible.empty)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t1, paired, features = build_datasets()
    pd.DataFrame({"feature_name": features, "t1_column": [f"{f}_T1" for f in features], "delta_column": [f"{f}_delta" for f in features]}).to_csv(OUT / "keyboard_model_feature_set.csv", index=False)
    qc = pd.DataFrame({"feature_name": features, "t1_coverage_percent": [t1[f"{f}_T1"].notna().mean() * 100 for f in features], "delta_coverage_percent": [paired[f"{f}_delta"].notna().mean() * 100 for f in features]})
    qc.to_csv(OUT / "keyboard_model_feature_coverage.csv", index=False)
    supervised = write_supervised(t1, paired, features)
    unsupervised = unsupervised_keyboard(t1, features)
    manifest = {"status": "complete", "feature_count": len(features), "t1_patients": len(t1), "paired_patients": len(paired), "supervised": supervised, "unsupervised": unsupervised, "keyboard_only": True, "existing_outputs_modified": False, "model_integration_into_main_bank": False}
    (OUT / "models_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
