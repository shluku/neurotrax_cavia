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
OUT_DIR = DATA_DIR / "model_t1_cognitive_domain_groups"
PREDICTIONS_PATH = OUT_DIR / "phase4_t1_cognitive_domain_group_predictions.csv"
PATIENT_PATH = OUT_DIR / "phase4_t1_cognitive_domain_group_patient_predictions.csv"
METRICS_PATH = OUT_DIR / "phase4_t1_cognitive_domain_group_metrics.csv"
TAXONOMY_PATH = OUT_DIR / "phase4_cognitive_domain_feature_taxonomy.csv"
README_PATH = OUT_DIR / "README_phase4_t1_cognitive_domain_groups.md"

DOMAIN_TARGETS = {
    "Memory": "memory_T1",
    "Executive function": "ef_T1",
    "Processing speed": "processing_speed_T1",
    "Attention": "attention_T1",
    "Motor": "motor_T1",
}

DOMAIN_FEATURES = {
    "Memory": [
        "app_use_diversity", "unique_foreground_apps", "gsm_cell_transition_count", "unique_gsm_cell_count",
        "unique_gsm_lac_count", "message_distinct_event_count", "outgoing_message_count",
        "activity_state_diversity", "night_screen_event_count",
    ],
    "Executive function": [
        "app_foreground_event_count", "app_use_diversity", "unique_foreground_apps", "activity_state_diversity",
        "activity_transition_count", "activity_active_hour_count", "screen_transition_count",
        "screen_active_hour_count", "touch_app_diversity", "touch_unique_app_count",
        "gsm_cell_transition_count", "telephony_event_count",
    ],
    "Processing speed": [
        "keyboard_median_inter_event_interval_ms", "keyboard_inter_event_interval_iqr_ms",
        "keyboard_long_pause_count_2s", "keyboard_typing_burst_count", "keyboard_deletion_event_count",
        "touch_scroll_event_count", "touch_scroll_index_change_median", "touch_click_event_count",
        "screen_event_count", "screen_transition_count",
    ],
    "Attention": [
        "screen_unlock_event_count", "screen_event_count", "screen_active_hour_count", "screen_on_event_count",
        "screen_off_event_count", "night_screen_event_count", "touch_active_hour_count", "touch_click_event_count",
        "touch_scroll_event_count", "keyboard_long_pause_count_2s", "activity_unknown_fraction",
        "telephony_mobile_data_enabled_fraction",
    ],
    "Motor": [
        "activity_active_hour_count", "activity_still_fraction", "activity_transition_count",
        "activity_state_diversity", "touch_active_hour_count", "touch_scroll_direction_change_count",
        "touch_scroll_index_change_median", "touch_scroll_event_count", "touch_click_event_count",
        "screen_active_hour_count",
    ],
}

N_SPLITS = 5
N_REPEATS = 20
RANDOM_STATE = 20260726
ALPHAS = np.logspace(-3, 4, 30)


def build_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scaler", StandardScaler()),
            (
                "ridge",
                RidgeCV(
                    alphas=ALPHAS,
                    cv=KFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE),
                    scoring="neg_root_mean_squared_error",
                ),
            ),
        ]
    )


def metric_row(actual: np.ndarray, predicted: np.ndarray, domain: str, model: str, repeat: int | str) -> dict[str, object]:
    return {
        "analysis_scope": "repeat" if repeat != "pooled" else "pooled",
        "repeat": repeat,
        "domain": domain,
        "model": model,
        "n_predictions": len(actual),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH, dtype={"Subject_ID_D": str, "Subject_ID_N": str})
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    primary_features = set(metadata.loc[
        metadata["primary_model_recommendation"] == "include_primary", "feature_name"
    ])
    missing_mapping_features = sorted(set().union(*DOMAIN_FEATURES.values()) - primary_features)
    if missing_mapping_features:
        raise ValueError(f"Domain taxonomy contains features outside primary set: {missing_mapping_features}")
    taxonomy_rows = [
        {"domain": domain, "feature": feature, "feature_order": index + 1}
        for domain, features in DOMAIN_FEATURES.items()
        for index, feature in enumerate(features)
    ]
    pd.DataFrame(taxonomy_rows).to_csv(TAXONOMY_PATH, index=False)

    predictions: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    for domain, target_name in DOMAIN_TARGETS.items():
        target = pd.to_numeric(dataset[target_name], errors="coerce")
        valid = target.notna()
        domain_dataset = dataset.loc[valid].reset_index(drop=True)
        X = domain_dataset[DOMAIN_FEATURES[domain]].apply(pd.to_numeric, errors="coerce")
        y = target.loc[valid].to_numpy(dtype=float)
        repeat_buffers: dict[int, dict[str, list[float]]] = {}
        outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=RANDOM_STATE)
        for split_index, (train_idx, test_idx) in enumerate(outer.split(X)):
            repeat = split_index // N_SPLITS + 1
            fold = split_index % N_SPLITS + 1
            y_train = y[train_idx]
            y_test = y[test_idx]
            baseline = np.repeat(y_train.mean(), len(test_idx))
            model = build_pipeline()
            model.fit(X.iloc[train_idx], y_train)
            prediction = model.predict(X.iloc[test_idx])
            repeat_buffers.setdefault(repeat, {"actual": [], "baseline": [], "group": []})
            repeat_buffers[repeat]["actual"].extend(y_test.tolist())
            repeat_buffers[repeat]["baseline"].extend(baseline.tolist())
            repeat_buffers[repeat]["group"].extend(prediction.tolist())
            for row_index, row_pos in enumerate(test_idx):
                predictions.append(
                    {
                        "domain": domain,
                        "target": target_name,
                        "repeat": repeat,
                        "fold": fold,
                        "Subject_ID_D": domain_dataset.loc[row_pos, "Subject_ID_D"],
                        "Subject_ID_N": domain_dataset.loc[row_pos, "Subject_ID_N"],
                        "actual_T1": y_test[row_index],
                        "mean_baseline_prediction": baseline[row_index],
                        "group_ridge_prediction": prediction[row_index],
                        "n_group_features": len(DOMAIN_FEATURES[domain]),
                        "ridge_alpha": float(model.named_steps["ridge"].alpha_),
                    }
                )
        for repeat, values in repeat_buffers.items():
            actual = np.asarray(values["actual"])
            metrics.append(metric_row(actual, np.asarray(values["baseline"]), domain, "mean_baseline", repeat))
            metrics.append(metric_row(actual, np.asarray(values["group"]), domain, "domain_group_ridge", repeat))
        pooled_actual = np.tile(y, N_REPEATS)
        domain_predictions = pd.DataFrame([row for row in predictions if row["domain"] == domain])
        metrics.append(metric_row(pooled_actual, domain_predictions["mean_baseline_prediction"].to_numpy(), domain, "mean_baseline", "pooled"))
        metrics.append(metric_row(pooled_actual, domain_predictions["group_ridge_prediction"].to_numpy(), domain, "domain_group_ridge", "pooled"))

    predictions_df = pd.DataFrame(predictions)
    patient_predictions = (
        predictions_df.groupby(["domain", "target", "Subject_ID_D", "Subject_ID_N"], dropna=False)
        .agg(
            actual_T1=("actual_T1", "first"),
            mean_baseline_prediction=("mean_baseline_prediction", "mean"),
            group_ridge_prediction=("group_ridge_prediction", "mean"),
        )
        .reset_index()
    )
    metrics_df = pd.DataFrame(metrics)
    predictions_df.to_csv(PREDICTIONS_PATH, index=False)
    patient_predictions.to_csv(PATIENT_PATH, index=False)
    metrics_df.to_csv(METRICS_PATH, index=False)
    pooled = metrics_df[metrics_df["analysis_scope"].eq("pooled")]
    lines = [
        "# Phase 4 Cognitive-Domain Feature-Group Models",
        "",
        "Each cognitive domain is modeled using its own hypothesized digital feature group. Features may appear in multiple domain groups. These are exploratory mechanistic groupings, not clinical classifications.",
        "",
        "## Pooled results",
        "",
    ]
    for row in pooled.itertuples():
        lines.append(f"- {row.domain} / {row.model}: RMSE `{row.rmse:.3f}`, MAE `{row.mae:.3f}`, R2 `{row.r2:.3f}`.")
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"prediction rows: {len(predictions_df)}")
    print(pooled[["domain", "model", "rmse", "mae", "r2"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
