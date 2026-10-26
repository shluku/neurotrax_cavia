"""Leakage-aware discovery screen for keyboard features.

This is a candidate-generation analysis. It ranks robust keyboard associations
with T1 scores and T2-minus-T1 change, estimates bootstrap stability, and
compares small feature families with a mean-score baseline. It never modifies
the main Feature Bank or existing model outputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, t
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import RepeatedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler


ROOT = Path(__file__).parent
DEEP = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1"
OUT = DEEP / "signal_discovery"
WINDOW = DEEP / "keyboard_deep_dive_window_features.csv"
T1_PATH = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"
T2_PATH = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv"
SEED = 20261020
BOOTSTRAPS = 500

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


def feature_columns(columns: list[str]) -> list[str]:
    excluded = ("raw_rows", "duplicate_rows", "json_parse", "valid_interval_count", "distinct_observations_in_window", "window_start", "window_end")
    return [c for c in columns if c.startswith("keyboard_") and not any(token in c for token in excluded)]


def family(name: str) -> str:
    if any(x in name for x in ("deletion", "correction", "pre_correction", "post_correction", "recovery")):
        return "Corrections"
    if any(x in name for x in ("06_12", "12_18", "18_24", "00_06")):
        return "Circadian"
    if any(x in name for x in ("pause", "interval", "rhythm", "variability", "iqr", "mad", "sd", "spread", "cv")):
        return "Timing and variability"
    if any(x in name for x in ("session", "active", "burst")):
        return "Sessions and fragmentation"
    return "Typing volume and production"


def build_data() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    windows = pd.read_csv(WINDOW, dtype={"Subject_ID_D": str})
    windows["Subject_ID_D"] = windows["Subject_ID_D"].map(normalize_id)
    t1 = pd.read_csv(T1_PATH, dtype={"Subject_ID_D": str})
    t2 = pd.read_csv(T2_PATH, dtype={"Subject_ID_D": str})
    for frame in (t1, t2):
        frame["Subject_ID_D"] = frame["Subject_ID_D"].map(normalize_id)
    features = feature_columns(windows.columns.tolist())
    t1k = windows[windows.window_name.eq("T1")][["Subject_ID_D", *features]].rename(columns={f: f + "_T1" for f in features})
    t2k = windows[windows.window_name.eq("T2")][["Subject_ID_D", *features]].rename(columns={f: f + "_T2" for f in features})
    targets = [f"{p}_T1" for p in OUTCOMES.values()]
    deltas = [f"{p}_delta" for p in OUTCOMES.values()]
    base = t1[["Subject_ID_D", "age", "Gender (1=M, 2=F)", "Education (years)", *targets]].merge(t1k, on="Subject_ID_D", how="left")
    paired = base.merge(t2[["Subject_ID_D", *deltas]], on="Subject_ID_D", how="left").merge(t2k, on="Subject_ID_D", how="left")
    for f in features:
        paired[f + "_delta"] = pd.to_numeric(paired[f + "_T2"], errors="coerce") - pd.to_numeric(paired[f + "_T1"], errors="coerce")
    return base, paired, features


def partial_spearman(x: pd.Series, y: pd.Series, covariates: pd.DataFrame) -> tuple[float, float, int]:
    frame = pd.concat([x.rename("x"), y.rename("y"), covariates], axis=1).apply(pd.to_numeric, errors="coerce").dropna()
    n = len(frame)
    if n < 12:
        return np.nan, np.nan, n
    ranks = frame.rank(method="average")
    z = ranks.iloc[:, 2:].to_numpy(dtype=float)
    design = np.column_stack([np.ones(n), z])
    rx = ranks.iloc[:, 0].to_numpy(dtype=float) - design @ np.linalg.lstsq(design, ranks.iloc[:, 0].to_numpy(dtype=float), rcond=None)[0]
    ry = ranks.iloc[:, 1].to_numpy(dtype=float) - design @ np.linalg.lstsq(design, ranks.iloc[:, 1].to_numpy(dtype=float), rcond=None)[0]
    rho = float(np.corrcoef(rx, ry)[0, 1]) if np.std(rx) > 0 and np.std(ry) > 0 else np.nan
    df = max(n - z.shape[1] - 2, 1)
    stat = rho * np.sqrt(df / max(1 - rho * rho, 1e-12)) if np.isfinite(rho) else np.nan
    p = float(2 * t.sf(abs(stat), df)) if np.isfinite(stat) else np.nan
    return rho, p, n


def bh_fdr(values: pd.Series) -> np.ndarray:
    p = values.to_numpy(dtype=float)
    q = np.full(len(p), np.nan)
    valid = np.isfinite(p)
    order = np.argsort(p[valid])
    ranked = p[valid][order]
    adjusted = np.minimum.accumulate((ranked * len(ranked) / np.arange(1, len(ranked) + 1))[::-1])[::-1]
    result = np.empty(len(ranked)); result[order] = np.minimum(adjusted, 1.0)
    q[valid] = result
    return q


def association_table(data: pd.DataFrame, features: list[str], scope: str, suffix: str, targets: dict[str, str]) -> pd.DataFrame:
    rows = []
    covars = data[["age", "Gender (1=M, 2=F)", "Education (years)"]]
    rng = np.random.default_rng(SEED + (0 if scope == "T1" else 1))
    for outcome, target in targets.items():
        for f in features:
            x = pd.to_numeric(data[f + suffix], errors="coerce")
            y = pd.to_numeric(data[target], errors="coerce")
            valid = pd.concat([x.rename("x"), y.rename("y")], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
            if len(valid) < 12 or valid.x.nunique() < 3 or valid.y.nunique() < 3:
                continue
            rho, p = spearmanr(valid.x, valid.y)
            bootstrap = []
            for _ in range(BOOTSTRAPS):
                idx = rng.integers(0, len(valid), len(valid))
                bootstrap.append(spearmanr(valid.x.iloc[idx], valid.y.iloc[idx]).statistic)
            boot = np.asarray(bootstrap, dtype=float)
            partial, partial_p, partial_n = partial_spearman(x, y, covars)
            rows.append({
                "scope": scope, "outcome": outcome, "target": target, "feature_name": f,
                "family": family(f), "n": len(valid), "spearman_rho": float(rho), "spearman_p": float(p),
                "bootstrap_ci_low": float(np.nanpercentile(boot, 2.5)), "bootstrap_ci_high": float(np.nanpercentile(boot, 97.5)),
                "bootstrap_sign_stability": float(np.mean(np.sign(boot) == np.sign(rho))),
                "bootstrap_abs_ge_020": float(np.mean(np.abs(boot) >= 0.20)),
                "partial_spearman_rho": partial, "partial_spearman_p": partial_p, "partial_n": partial_n,
            })
    result = pd.DataFrame(rows)
    if not result.empty:
        result["fdr_q"] = bh_fdr(result["spearman_p"])
        result["candidate_flag"] = (
            result["n"].ge(20) & result["fdr_q"].le(0.20) & result["bootstrap_sign_stability"].ge(0.80) &
            (result["bootstrap_ci_low"] * result["bootstrap_ci_high"] > 0)
        )
    return result


def family_cv(data: pd.DataFrame, features: list[str], scope: str, suffix: str, targets: dict[str, str]) -> pd.DataFrame:
    rows = []
    families = {g: [f for f in features if family(f) == g] for g in sorted({family(f) for f in features})}
    for outcome, target in targets.items():
        for group, group_features in families.items():
            frame = data[[target, *[f + suffix for f in group_features]]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna(subset=[target])
            if len(frame) < 20:
                continue
            X, y = frame.iloc[:, 1:], frame.iloc[:, 0].to_numpy()
            cv = RepeatedKFold(n_splits=5, n_repeats=10, random_state=SEED)
            model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), RobustScaler(), Ridge(alpha=10.0))
            rmses = []; baseline_rmses = []
            for train, test in cv.split(X):
                model.fit(X.iloc[train], y[train]); pred = model.predict(X.iloc[test])
                rmses.append(mean_squared_error(y[test], pred) ** 0.5)
                baseline_rmses.append(mean_squared_error(y[test], np.repeat(y[train].mean(), len(test))) ** 0.5)
            rows.append({"scope": scope, "outcome": outcome, "family": group, "n": len(frame), "family_rmse": np.mean(rmses), "baseline_rmse": np.mean(baseline_rmses), "rmse_improvement": np.mean(baseline_rmses) - np.mean(rmses)})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t1, paired, features = build_data()
    t1_targets = {k: f"{v}_T1" for k, v in OUTCOMES.items()}
    delta_targets = {k: f"{v}_delta" for k, v in OUTCOMES.items()}
    t1_assoc = association_table(t1, features, "T1", "_T1", t1_targets)
    delta_assoc = association_table(paired, features, "T2_minus_T1", "_delta", delta_targets)
    assoc = pd.concat([t1_assoc, delta_assoc], ignore_index=True)
    assoc.to_csv(OUT / "signal_feature_associations.csv", index=False)
    top = assoc.sort_values(["candidate_flag", "fdr_q", "bootstrap_sign_stability", "spearman_rho"], ascending=[False, True, False, False]).groupby("scope", sort=False).head(50)
    top.to_csv(OUT / "signal_top_candidates.csv", index=False)
    family_summary = assoc.groupby(["scope", "outcome", "family"], as_index=False).agg(
        n_features=("feature_name", "count"), mean_abs_rho=("spearman_rho", lambda x: np.nanmean(np.abs(x))),
        best_abs_rho=("spearman_rho", lambda x: np.nanmax(np.abs(x))), candidate_count=("candidate_flag", "sum"),
    )
    family_summary.to_csv(OUT / "signal_family_summary.csv", index=False)
    cv = pd.concat([
        family_cv(t1, features, "T1", "_T1", t1_targets),
        family_cv(paired, features, "T2_minus_T1", "_delta", delta_targets),
    ], ignore_index=True)
    cv.to_csv(OUT / "signal_family_cv.csv", index=False)
    manifest = {"status": "complete", "features_tested": len(features), "t1_patients": len(t1), "paired_patients": len(paired), "association_rows": len(assoc), "bootstrap_replicates": BOOTSTRAPS, "candidate_rule": "n>=20, FDR q<=0.20, bootstrap sign stability>=0.80, CI excludes zero", "existing_outputs_modified": False, "main_feature_bank_modified": False}
    (OUT / "signal_discovery_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
