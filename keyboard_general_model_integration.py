"""Leakage-safe comparison of the existing Feature Bank and expanded keyboard bank.

Outputs are isolated.  T1 and T2-minus-T1 tasks use separate cohorts and target
values, but each variant within a task receives the exact same repeated folds.
Imputation, robust scaling, univariate feature selection, and Ridge alpha
tuning are fitted inside each outer training fold.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from keyboard_signal_discovery import OUTCOMES, feature_columns, normalize_id

GENERAL_OUTCOMES = {**OUTCOMES, "verbal": "verbal", "iq": "iq"}

ROOT = Path(__file__).parent
OUT = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/general_model_integration_v1"
T1_PATH = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"
T2_PATH = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv"
DEEP = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/keyboard_deep_dive_window_features.csv"
RANDOM_STATE = 20261020
N_REPEATS = 3
warnings.filterwarnings("ignore", message="Skipping features without any observed values")


def numeric_features(frame: pd.DataFrame) -> list[str]:
    excluded = {"Subject_ID_N", "Subject_ID_D", "age", "Gender (1=M, 2=F)", "Education (years)", "T1_date_iso", "T2_date_iso"}
    excluded.update(c for c in frame.columns if any(c.startswith(f"{x}_") for x in GENERAL_OUTCOMES) or c in {f"{x}_{suffix}" for x in GENERAL_OUTCOMES for suffix in ("T1", "T2", "delta")})
    return [c for c in frame.columns if c not in excluded and not c.endswith(("_T1", "_T2", "_delta")) and pd.api.types.is_numeric_dtype(frame[c])]


def load() -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    t1 = pd.read_csv(T1_PATH, dtype={"Subject_ID_D": str}); t2 = pd.read_csv(T2_PATH, dtype={"Subject_ID_D": str})
    for d in (t1, t2): d["Subject_ID_D"] = d["Subject_ID_D"].map(normalize_id)
    existing = numeric_features(t1)
    deep = pd.read_csv(DEEP, dtype={"Subject_ID_D": str}); deep.Subject_ID_D = deep.Subject_ID_D.map(normalize_id)
    deep_features = feature_columns(deep.columns.tolist())
    d1 = deep[deep.window_name.eq("T1")][["Subject_ID_D", *deep_features]].drop_duplicates("Subject_ID_D").set_index("Subject_ID_D")
    d2 = deep[deep.window_name.eq("T2")][["Subject_ID_D", *deep_features]].drop_duplicates("Subject_ID_D").set_index("Subject_ID_D")
    t1 = t1.join(d1.add_suffix("__deep"), on="Subject_ID_D")
    t2 = t2.join(d2.add_suffix("__deep"), on="Subject_ID_D")
    return t1, t2, existing, deep_features


def coverage_frame(t1: pd.DataFrame, t2: pd.DataFrame, deep_features: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    cols = ["Subject_ID_D", "window_name", "active_local_days", "distinct_observations_in_window", "keyboard_valid_interval_count"]
    d = pd.read_csv(DEEP, dtype={"Subject_ID_D": str}); d.Subject_ID_D = d.Subject_ID_D.map(normalize_id)
    c = d[cols].drop_duplicates(["Subject_ID_D", "window_name"])
    p = c.pivot(index="Subject_ID_D", columns="window_name")
    p.columns = [f"coverage_{metric}_{window}" for metric, window in p.columns]
    p = p.reset_index()
    for window in ("T1", "T2"):
        p[f"coverage_recording_intensity_{window}"] = p[f"coverage_distinct_observations_in_window_{window}"] / p[f"coverage_active_local_days_{window}"].replace(0, np.nan)
    cov_t1 = p[["Subject_ID_D", *[c for c in p if c.endswith("_T1")]]].copy()
    cov_t2 = p[["Subject_ID_D", *[c for c in p if c.endswith("_T2")]]].copy()
    cov_t1.columns = [c.removesuffix("_T1") for c in cov_t1.columns]
    cov_t2.columns = [c.removesuffix("_T2") for c in cov_t2.columns]
    cov_delta = cov_t2.set_index("Subject_ID_D").subtract(cov_t1.set_index("Subject_ID_D"), fill_value=np.nan).reset_index()
    coverage_names = [c for c in cov_t1.columns if c != "Subject_ID_D"]
    return cov_t1, cov_delta, coverage_names


def make_data(t1: pd.DataFrame, t2: pd.DataFrame, existing: list[str], deep_features: list[str], cov_t1: pd.DataFrame, cov_delta: pd.DataFrame) -> dict[str, tuple[pd.DataFrame, list[str], dict[str, str]]]:
    old_keyboard = {f for f in existing if f.startswith("keyboard_")}
    expanded = [f for f in existing if f not in old_keyboard] + deep_features
    # Coverage fields are included in both variants as technical covariates.
    cov_names = [c for c in cov_t1.columns if c != "Subject_ID_D"]
    feature_bank = pd.DataFrame({"feature_name": expanded, "source": ["existing_feature_bank" if f in existing else "keyboard_deep_dive_34" for f in expanded], "replaces_existing_keyboard_feature": [f in old_keyboard for f in expanded]})
    feature_bank.to_csv(OUT / "expanded_feature_bank_inventory.csv", index=False)
    t1i = t1.set_index("Subject_ID_D"); t2i = t2.set_index("Subject_ID_D")
    c1 = cov_t1.set_index("Subject_ID_D"); cd = cov_delta.set_index("Subject_ID_D")
    out: dict[str, tuple[pd.DataFrame, list[str], dict[str, str]]] = {}
    for task in ("T1", "T2_minus_T1"):
        source = t1i if task == "T1" else t1i.join(t2i, lsuffix="_T1", rsuffix="_T2", how="inner")
        ids = source.index
        if task == "T1":
            baseline = pd.DataFrame(index=ids); expanded_frame = pd.DataFrame(index=ids)
            for f in existing: baseline[f] = t1i[f];
            for f in [f for f in existing if f not in old_keyboard]: expanded_frame[f] = t1i[f]
            for f in deep_features: expanded_frame[f] = t1i.get(f + "__deep", pd.Series(index=ids)).reindex(ids)
            base_cov = c1.reindex(ids); baseline = baseline.join(base_cov); expanded_frame = expanded_frame.join(base_cov)
            targets = {k: f"{v}_T1" for k, v in GENERAL_OUTCOMES.items()}
        else:
            ids = t1i.index.intersection(t2i.index)
            baseline = pd.DataFrame(index=ids); expanded_frame = pd.DataFrame(index=ids)
            for f in existing: baseline[f] = pd.to_numeric(t2i.loc[ids, f], errors="coerce") - pd.to_numeric(t1i.loc[ids, f], errors="coerce")
            for f in [f for f in existing if f not in old_keyboard]: expanded_frame[f] = baseline[f]
            for f in deep_features: expanded_frame[f] = pd.to_numeric(t2i.get(f + "__deep", pd.Series(index=t2i.index)).reindex(ids), errors="coerce") - pd.to_numeric(t1i.get(f + "__deep", pd.Series(index=t1i.index)).reindex(ids), errors="coerce")
            base_cov = cd.reindex(ids); baseline = baseline.join(base_cov); expanded_frame = expanded_frame.join(base_cov)
            targets = {k: f"{v}_delta" for k, v in GENERAL_OUTCOMES.items()}
        target_frame = pd.DataFrame({"Subject_ID_D": ids, **{col: source.loc[ids, col] if task == "T1" else t1i.loc[ids, col] for col in targets.values()}}).set_index("Subject_ID_D")
        out[task] = (target_frame.join(baseline, rsuffix="__duplicate"), list(baseline.columns), targets)
        # Store expanded separately by a private key while keeping the public tuple compact.
        out[task + "__expanded"] = (target_frame.join(expanded_frame, rsuffix="__duplicate"), list(expanded_frame.columns), targets)
    return out


def pipeline(n_features: int, seed: int) -> GridSearchCV:
    ks = sorted(set(["all", min(20, n_features)]), key=str)
    pipe = Pipeline([("imputer", SimpleImputer(strategy="median", add_indicator=True)), ("scaler", RobustScaler()), ("select", SelectKBest(f_regression)), ("ridge", Ridge())])
    inner = KFold(n_splits=3, shuffle=True, random_state=seed)
    return GridSearchCV(pipe, {"select__k": ks, "ridge__alpha": np.logspace(-2, 3, 5)}, cv=inner, scoring="neg_root_mean_squared_error", n_jobs=-1, refit=True)


def run_task(task: str, frame: pd.DataFrame, features: list[str], targets: dict[str, str]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    metrics: list[dict[str, object]] = []; predictions: list[dict[str, object]] = []; folds: list[dict[str, object]] = []
    task_name = task.split("__", 1)[0]
    for outcome, target in targets.items():
        work = frame[[target, *features]].apply(pd.to_numeric, errors="coerce"); work = work.replace([np.inf, -np.inf], np.nan).dropna(subset=[target]); ids = frame.loc[work.index, "Subject_ID_D"] if "Subject_ID_D" in frame else pd.Series(work.index, index=work.index)
        if len(work) < 12: continue
        n_splits = min(5, max(2, len(work) // 5)); X = work[features]; y = work[target].to_numpy(float)
        for repeat in range(N_REPEATS):
            splitter = KFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE + repeat)
            for fold, (train, test) in enumerate(splitter.split(X)):
                for idx in test: folds.append({"task": task_name, "outcome": outcome, "repeat": repeat, "fold": fold, "Subject_ID_D": ids.iloc[idx]})
                baseline = float(np.mean(y[train])); pred = np.full(len(test), baseline)
                metrics.append({"task": task_name, "outcome": outcome, "variant": "mean_baseline", "repeat": repeat, "fold": fold, "n": len(work), "n_train": len(train), "n_test": len(test), "rmse": mean_squared_error(y[test], pred) ** .5, "mae": mean_absolute_error(y[test], pred), "r2": r2_score(y[test], pred) if len(test) > 1 else np.nan, "selected_k": np.nan, "alpha": np.nan})
                model = pipeline(X.shape[1], RANDOM_STATE + repeat)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore"); model.fit(X.iloc[train], y[train])
                pred = model.predict(X.iloc[test])
                params = model.best_params_; metrics.append({"task": task_name, "outcome": outcome, "variant": task.split("__")[-1] if "__" in task else "existing", "repeat": repeat, "fold": fold, "n": len(work), "n_train": len(train), "n_test": len(test), "rmse": mean_squared_error(y[test], pred) ** .5, "mae": mean_absolute_error(y[test], pred), "r2": r2_score(y[test], pred) if len(test) > 1 else np.nan, "selected_k": params.get("select__k"), "alpha": params.get("ridge__alpha")})
                variant = task.split("__")[-1] if "__" in task else "existing"
                predictions.extend({"task": task_name, "outcome": outcome, "variant": variant, "repeat": repeat, "fold": fold, "Subject_ID_D": ids.iloc[idx], "actual": y[idx], "prediction": float(pred[j])} for j, idx in enumerate(test))
    return metrics, predictions, folds


def simple_plot(summary: pd.DataFrame, path: Path) -> None:
    views = summary[summary.variant.isin(["mean_baseline", "existing", "expanded"])]
    outcomes = views.outcome.unique().tolist(); im = Image.new("RGB", (1100, max(420, len(outcomes) * 70)), "white"); draw = ImageDraw.Draw(im)
    for i, outcome in enumerate(outcomes):
        sub = views[views.outcome.eq(outcome)].groupby("variant").rmse_mean.first(); y = 40 + i * 65; draw.text((10, y), outcome, fill="black")
        for j, variant in enumerate(["mean_baseline", "existing", "expanded"]):
            v = float(sub.get(variant, np.nan)); x = 200 + j * 280; draw.rectangle((x, y, x + int(120 * v / max(1, summary.rmse_mean.max())), y + 22), fill=[(148, 163, 184), (37, 99, 235), (22, 163, 74)][j]); draw.text((x, y + 26), f"{variant}: {v:.2f}", fill="black")
    im.save(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); t1, t2, existing, deep = load(); cov_t1, cov_delta, _ = coverage_frame(t1, t2, deep); datasets = make_data(t1, t2, existing, deep, cov_t1, cov_delta)
    all_metrics = []; all_predictions = []; all_folds = []
    for task in ("T1", "T2_minus_T1"):
        for key, variant in ((task, "existing"), (task + "__expanded", "expanded")):
            frame, feats, targets = datasets[key]; frame = frame.reset_index().rename(columns={"index": "Subject_ID_D"}); m, p, f = run_task(task + "__" + variant, frame, feats, targets); all_metrics.extend(m); all_predictions.extend(p); all_folds.extend(f)
    metrics = pd.DataFrame(all_metrics); metrics = metrics.drop_duplicates(subset=["task", "outcome", "variant", "repeat", "fold"]); predictions = pd.DataFrame(all_predictions); folds = pd.DataFrame(all_folds); metrics.to_csv(OUT / "fold_metrics.csv", index=False); predictions.to_csv(OUT / "predictions.csv", index=False); folds.to_csv(OUT / "fold_assignments.csv", index=False)
    summary = metrics.groupby(["task", "outcome", "variant"], as_index=False).agg(n=("n", "first"), folds=("rmse", "count"), rmse_mean=("rmse", "mean"), rmse_sd=("rmse", "std"), rmse_ci_low=("rmse", lambda x: x.quantile(.025)), rmse_ci_high=("rmse", lambda x: x.quantile(.975)), mae_mean=("mae", "mean"), mae_sd=("mae", "std"), r2_mean=("r2", "mean"), selected_k_median=("selected_k", lambda x: pd.to_numeric(x, errors="coerce").median()), alpha_median=("alpha", "median")); summary.to_csv(OUT / "model_summary.csv", index=False)
    pivot = summary.pivot_table(index=["task", "outcome"], columns="variant", values="rmse_mean").reset_index();
    for variant in ("existing", "expanded"): pivot[variant + "_rmse_improvement_vs_mean"] = pivot.get("mean_baseline", np.nan) - pivot.get(variant, np.nan)
    pivot["expanded_minus_existing_rmse"] = pivot.get("expanded", np.nan) - pivot.get("existing", np.nan); pivot.to_csv(OUT / "model_comparison.csv", index=False)
    simple_plot(summary, OUT / "model_comparison.png")
    (OUT / "integration_manifest.json").write_text(json.dumps({"status": "complete", "t1_existing_features": len(existing), "keyboard_features_total": len(deep), "expanded_feature_count_excluding_replaced_old_keyboard": len([f for f in existing if not f.startswith("keyboard_")]) + len(deep), "t1_and_longitudinal_separate": True, "outer_repeats": N_REPEATS, "leakage_control": "imputation, robust scaling, SelectKBest feature selection, and Ridge alpha tuning fit within each training fold", "identical_folds_within_task": True, "models_trained": True, "existing_outputs_modified": False}, indent=2), encoding="utf-8")


if __name__ == "__main__": main()
