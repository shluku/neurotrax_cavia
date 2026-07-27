from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "output/analysis_candidates/phase4_t1_baseline"
DATASET_PATH = DATA_DIR / "phase4_t1_baseline_patient_dataset.csv"
METADATA_PATH = DATA_DIR / "phase4_t1_baseline_feature_metadata.csv"
OUT_DIR = DATA_DIR / "model_t1_ridge"

PREDICTIONS_PATH = OUT_DIR / "phase4_t1_ridge_predictions.csv"
METRICS_PATH = OUT_DIR / "phase4_t1_ridge_metrics.csv"
FEATURE_SET_PATH = OUT_DIR / "phase4_t1_ridge_feature_set.csv"
COEFFICIENTS_PATH = OUT_DIR / "phase4_t1_ridge_coefficients.csv"
README_PATH = OUT_DIR / "README_phase4_t1_ridge.md"

TARGET = "global_T1"
N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260726
ALPHAS = np.logspace(-3, 4, 30)


def metric_row(
    y_true: np.ndarray,
    prediction: np.ndarray,
    model: str,
    feature_scope: str,
    repeat: int | str,
) -> dict[str, object]:
    return {
        "analysis_scope": "repeat" if repeat != "pooled" else "pooled",
        "repeat": repeat,
        "feature_scope": feature_scope,
        "model": model,
        "n_predictions": len(y_true),
        "rmse": float(np.sqrt(mean_squared_error(y_true, prediction))),
        "mae": float(mean_absolute_error(y_true, prediction)),
        "r2": float(r2_score(y_true, prediction)),
    }


def build_pipeline() -> Pipeline:
    inner_cv = KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE)
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scaler", StandardScaler()),
            ("ridge", RidgeCV(alphas=ALPHAS, cv=inner_cv, scoring="neg_root_mean_squared_error")),
        ]
    )


def get_feature_scopes(metadata: pd.DataFrame) -> dict[str, list[str]]:
    observed = metadata[metadata["primary_model_recommendation"] != "exclude_no_observed_data"].copy()
    primary = observed[observed["primary_model_recommendation"] == "include_primary"]["feature_name"].tolist()
    t1_week = observed[observed["window_class"] == "t1_week_first_valid_24h"]["feature_name"].tolist()
    adjusted = observed[observed["window_class"] == "adjusted_first_available_7d"]["feature_name"].tolist()
    return {
        "primary_37": primary,
        "t1_week_all_available": t1_week,
        "primary_plus_adjusted": primary + adjusted,
        "all_available": t1_week + adjusted,
    }


def build_readme(feature_set: pd.DataFrame, metrics: pd.DataFrame, n_patients: int) -> str:
    pooled = metrics[metrics["analysis_scope"] == "pooled"].copy()
    lines = [
        "# Phase 4 T1 Ridge Sensitivity Models",
        "",
        "This run compares four baseline feature scopes against the same training-fold mean predictor for continuous `global_T1`.",
        "",
        "## Design",
        "",
        f"- Patients with non-missing `global_T1`: `{n_patients}`.",
        f"- Outer validation: repeated `{N_SPLITS}`-fold cross-validation, `{N_REPEATS}` repeats.",
        "- Every scope uses the same outer splits and the same mean-baseline predictions within each split.",
        "- Ridge alpha is selected inside each outer training fold using 4-fold inner cross-validation.",
        "- Preprocessing is fit inside each training fold: median imputation, missingness indicators, then standardization.",
        "",
        "## Feature Scopes",
        "",
        "- `primary_37`: the 37 T1-week features observed in at least 50% of patients.",
        "- `t1_week_all_available`: primary plus lower-coverage T1-week features; adjusted-window features excluded.",
        "- `primary_plus_adjusted`: primary plus adjusted first-available features; lower-coverage T1-week features excluded.",
        "- `all_available`: all observed T1-week and adjusted-window features except zero-coverage features.",
        "",
        "## Pooled Cross-Validated Results",
        "",
    ]
    for scope in pooled["feature_scope"].drop_duplicates().tolist():
        rows = pooled[pooled["feature_scope"] == scope].set_index("model")
        ridge = rows.loc["ridge"]
        mean = rows.loc["mean_baseline"]
        lines.append(
            f"- `{scope}`: mean RMSE `{mean['rmse']:.3f}`, ridge RMSE `{ridge['rmse']:.3f}`, "
            f"ridge minus mean `{ridge['rmse'] - mean['rmse']:.3f}`, ridge R2 `{ridge['r2']:.3f}`."
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "These are exploratory POC comparisons, not independent validation estimates. Adding features with lower coverage or a different acquisition rule can improve apparent fit while reducing interpretability and increasing instability.",
            "",
            "The mean baseline is deliberately identical in meaning across all four comparisons: it predicts the training-fold mean `global_T1`. The results should be read as whether each feature scope adds value beyond that reference under the same resampling design.",
            "",
            "## Files",
            "",
            "- `phase4_t1_ridge_predictions.csv`: repeated outer-fold predictions for every scope and model.",
            "- `phase4_t1_ridge_metrics.csv`: per-repeat and pooled metrics.",
            "- `phase4_t1_ridge_feature_set.csv`: feature membership by scope.",
            "- `phase4_t1_ridge_coefficients.csv`: outer-fold coefficient stability for ridge terms.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    target = pd.to_numeric(dataset[TARGET], errors="coerce")
    valid = target.notna()
    dataset = dataset.loc[valid].reset_index(drop=True)
    y = target.loc[valid].to_numpy(dtype=float)
    scopes = get_feature_scopes(metadata)

    feature_set_rows: list[dict[str, object]] = []
    for scope, features in scopes.items():
        for feature in features:
            source = metadata.loc[metadata["feature_name"] == feature].iloc[0]
            feature_set_rows.append(
                {
                    "feature_scope": scope,
                    "source_table": source["source_table"],
                    "feature_name": feature,
                    "feature_family": source["feature_family"],
                    "window_class": source["window_class"],
                    "missing_percent": source["missing_percent"],
                    "primary_model_recommendation": source["primary_model_recommendation"],
                }
            )
    feature_set = pd.DataFrame(feature_set_rows)

    outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
    predictions: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    coefficient_rows: list[dict[str, object]] = []
    repeat_buffers: dict[tuple[int, str], dict[str, list[float]]] = {}

    for split_index, (train_idx, test_idx) in enumerate(outer.split(dataset), start=0):
        repeat = split_index // N_SPLITS + 1
        fold = split_index % N_SPLITS + 1
        y_train = y[train_idx]
        y_test = y[test_idx]
        mean_prediction = np.repeat(y_train.mean(), len(test_idx))

        for scope, features in scopes.items():
            X = dataset[features].apply(pd.to_numeric, errors="coerce")
            model = build_pipeline()
            model.fit(X.iloc[train_idx], y_train)
            ridge_prediction = model.predict(X.iloc[test_idx])
            ridge_alpha = float(model.named_steps["ridge"].alpha_)
            coefficient_names = model.named_steps["imputer"].get_feature_names_out(features)
            for term_name, coefficient in zip(coefficient_names, model.named_steps["ridge"].coef_):
                coefficient_rows.append(
                    {
                        "repeat": repeat,
                        "fold": fold,
                        "feature_scope": scope,
                        "term_name": term_name,
                        "coefficient": float(coefficient),
                        "ridge_alpha": ridge_alpha,
                    }
                )
            key = (repeat, scope)
            repeat_buffers.setdefault(key, {"actual": [], "mean": [], "ridge": []})
            repeat_buffers[key]["actual"].extend(y_test.tolist())
            repeat_buffers[key]["mean"].extend(mean_prediction.tolist())
            repeat_buffers[key]["ridge"].extend(ridge_prediction.tolist())

            for row_index, row_pos in enumerate(test_idx):
                predictions.append(
                    {
                        "repeat": repeat,
                        "fold": fold,
                        "feature_scope": scope,
                        "Subject_ID_D": dataset.loc[row_pos, "Subject_ID_D"],
                        "Subject_ID_N": dataset.loc[row_pos, "Subject_ID_N"],
                        "actual_global_T1": y_test[row_index],
                        "mean_baseline_prediction": mean_prediction[row_index],
                        "ridge_prediction": ridge_prediction[row_index],
                        "ridge_alpha": ridge_alpha,
                        "n_features": len(features),
                        "n_train": len(train_idx),
                        "n_test": len(test_idx),
                    }
                )

    predictions_df = pd.DataFrame(predictions)
    for (repeat, scope), values in repeat_buffers.items():
        actual = np.asarray(values["actual"])
        metric_rows.append(metric_row(actual, np.asarray(values["mean"]), "mean_baseline", scope, repeat))
        metric_rows.append(metric_row(actual, np.asarray(values["ridge"]), "ridge", scope, repeat))

    for scope in scopes:
        scoped = predictions_df[predictions_df["feature_scope"] == scope]
        pooled_actual = np.tile(y, N_REPEATS)
        metric_rows.append(
            metric_row(
                pooled_actual,
                scoped["mean_baseline_prediction"].to_numpy(dtype=float),
                "mean_baseline",
                scope,
                "pooled",
            )
        )
        metric_rows.append(
            metric_row(
                pooled_actual,
                scoped["ridge_prediction"].to_numpy(dtype=float),
                "ridge",
                scope,
                "pooled",
            )
        )

    metrics_df = pd.DataFrame(metric_rows)
    coefficients_df = pd.DataFrame(coefficient_rows)
    predictions_df.to_csv(PREDICTIONS_PATH, index=False)
    metrics_df.to_csv(METRICS_PATH, index=False)
    feature_set.to_csv(FEATURE_SET_PATH, index=False)
    coefficients_df.to_csv(COEFFICIENTS_PATH, index=False)
    README_PATH.write_text(build_readme(feature_set, metrics_df, len(dataset)), encoding="utf-8")

    pooled = metrics_df[metrics_df["analysis_scope"] == "pooled"]
    comparison = pooled.pivot(index="feature_scope", columns="model", values="rmse")
    comparison["ridge_minus_mean_rmse"] = comparison["ridge"] - comparison["mean_baseline"]
    print(f"patients: {len(dataset)}")
    print(f"predictions: {len(predictions_df)}")
    print(comparison.round(4).to_string())
    print(f"outputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
