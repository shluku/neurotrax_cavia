"""Phase 2 validation for the six longitudinal keyboard signals.

This workstream is deliberately separate from feature extraction and prediction.
It validates reliability, coverage sensitivity, leave-one-patient-out stability,
outlier sensitivity, permutation nulls, and dependence among the six discovery
features. It never overwrites existing outputs or trains a predictive model.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, t


ROOT = Path(__file__).parent
DEEP = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1"
OUT = DEEP / "signal_validation"
WINDOW = DEEP / "keyboard_deep_dive_window_features.csv"
DAILY = DEEP / "keyboard_deep_dive_daily_features.csv"
T1_STATUS = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_patient_table_status.csv"
T2_STATUS = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_patient_table_status.csv"
T1_PATH = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"
T2_PATH = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv"
SEED = 20261020
BOOTSTRAPS = 500
PERMUTATIONS = 2000

SIGNALS = [
    ("keyboard_median_correction_recovery_time_ms", "executive_function"),
    ("keyboard_12_18_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_inter_event_interval_cv", "executive_function"),
    ("keyboard_18_24_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_06_12_median_inter_event_interval_ms", "executive_function"),
    ("keyboard_12_18_median_inter_event_interval_ms", "attention"),
]
OUTCOME_PREFIX = {"global": "global", "memory": "memory", "executive_function": "ef", "processing_speed": "processing_speed", "attention": "attention", "motor": "motor"}


def norm_id(v: object) -> str:
    s = str(v).strip()
    return s.zfill(3) if s.isdigit() else s


def bh(p: pd.Series) -> np.ndarray:
    values = p.to_numpy(dtype=float)
    result = np.full(len(values), np.nan)
    valid = np.isfinite(values)
    if not valid.any():
        return result
    order = np.argsort(values[valid])
    ranked = values[valid][order]
    adj = np.minimum.accumulate((ranked * len(ranked) / np.arange(1, len(ranked) + 1))[::-1])[::-1]
    restored = np.empty(len(ranked)); restored[order] = np.minimum(adj, 1.0)
    result[valid] = restored
    return result


def status_quality(path: Path, label: str) -> pd.DataFrame:
    d = pd.read_csv(path, dtype={"Subject_ID_D": str})
    d = d[d.table_name.eq("keyboard")].copy()
    d["Subject_ID_D"] = d["Subject_ID_D"].map(norm_id)
    d = d.drop_duplicates(subset=["Subject_ID_D", "window_start_ms", "window_end_ms"])
    d["window_name"] = label
    d["device_ids_used"] = d["device_ids_used"].fillna(d["device_ids_available"])
    d["duration_days"] = (pd.to_numeric(d.window_end_ms) - pd.to_numeric(d.window_start_ms)) / 86_400_000
    d["device_count"] = d["device_ids_used"].fillna("").map(lambda x: len([v for v in str(x).split(";") if v and v.lower() != "nan"]))
    d["device_signature"] = d["device_ids_used"].fillna("").map(lambda x: ";".join(sorted(v for v in str(x).split(";") if v and v.lower() != "nan")))
    keep = ["Subject_ID_D", "window_name", "window_start_ms", "window_end_ms", "duration_days", "device_count", "device_signature", "table_status", "feature_status"]
    return d[keep]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    windows = pd.read_csv(WINDOW, dtype={"Subject_ID_D": str})
    windows["Subject_ID_D"] = windows["Subject_ID_D"].map(norm_id)
    windows = windows.merge(pd.concat([status_quality(T1_STATUS, "T1"), status_quality(T2_STATUS, "T2")]), on=["Subject_ID_D", "window_name"], how="left", suffixes=("", "_status"))
    t1 = pd.read_csv(T1_PATH, dtype={"Subject_ID_D": str}); t2 = pd.read_csv(T2_PATH, dtype={"Subject_ID_D": str})
    t1["Subject_ID_D"] = t1["Subject_ID_D"].map(norm_id); t2["Subject_ID_D"] = t2["Subject_ID_D"].map(norm_id)
    t1k = windows[windows.window_name.eq("T1")].copy(); t2k = windows[windows.window_name.eq("T2")].copy()
    paired = t1k.merge(t2k, on="Subject_ID_D", suffixes=("_T1", "_T2"), how="inner")
    paired = paired.merge(t1[["Subject_ID_D", "age", "Gender (1=M, 2=F)", "Education (years)", *[f"{p}_T1" for p in OUTCOME_PREFIX.values()]]], on="Subject_ID_D", how="left")
    paired = paired.merge(t2[["Subject_ID_D", *[f"{p}_delta" for p in OUTCOME_PREFIX.values()]]], on="Subject_ID_D", how="left")
    for f in sorted({f for f, _ in SIGNALS}):
        paired[f + "_delta"] = pd.to_numeric(paired[f + "_T2"], errors="coerce") - pd.to_numeric(paired[f + "_T1"], errors="coerce")
        paired[f + "_snapshot_rate_delta"] = pd.to_numeric(paired["distinct_observations_in_window_T2"], errors="coerce") / paired["duration_days_T2"] - pd.to_numeric(paired["distinct_observations_in_window_T1"], errors="coerce") / paired["duration_days_T1"]
        paired[f + "_valid_interval_rate_delta"] = pd.to_numeric(paired["keyboard_valid_interval_count_T2"], errors="coerce") / paired["duration_days_T2"] - pd.to_numeric(paired["keyboard_valid_interval_count_T1"], errors="coerce") / paired["duration_days_T1"]
    paired["active_days_delta"] = pd.to_numeric(paired["active_local_days_T2"], errors="coerce") - pd.to_numeric(paired["active_local_days_T1"], errors="coerce")
    paired["device_changed"] = paired.apply(lambda r: int(str(r.get("device_signature_T1", "")) != str(r.get("device_signature_T2", ""))), axis=1)
    paired["device_count_delta"] = pd.to_numeric(paired["device_count_T2"], errors="coerce") - pd.to_numeric(paired["device_count_T1"], errors="coerce")
    paired["duration_difference_days"] = paired["duration_days_T2"] - paired["duration_days_T1"]
    return windows, paired, t1, t2


def partial_rank(frame: pd.DataFrame, x: str, y: str, covars: list[str]) -> tuple[float, float, int]:
    cols = [x, y, *covars]
    d = frame[cols].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    n = len(d)
    if n < max(12, len(covars) + 5): return np.nan, np.nan, n
    r = d.rank(method="average")
    z = r[covars].to_numpy(float) if covars else np.empty((n, 0))
    design = np.column_stack([np.ones(n), z])
    rx = r[x].to_numpy(float) - design @ np.linalg.lstsq(design, r[x].to_numpy(float), rcond=None)[0]
    ry = r[y].to_numpy(float) - design @ np.linalg.lstsq(design, r[y].to_numpy(float), rcond=None)[0]
    rho = float(np.corrcoef(rx, ry)[0, 1]) if np.std(rx) and np.std(ry) else np.nan
    df = max(n - len(covars) - 2, 1)
    stat = rho * np.sqrt(df / max(1 - rho * rho, 1e-12)) if np.isfinite(rho) else np.nan
    p = float(2 * t.sf(abs(stat), df)) if np.isfinite(stat) else np.nan
    return rho, p, n


def bootstrap_partial(frame: pd.DataFrame, x: str, y: str, covars: list[str], rng: np.random.Generator) -> tuple[float, float]:
    d = frame[[x, y, *covars]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    if len(d) < 12: return np.nan, np.nan
    values = []
    for _ in range(BOOTSTRAPS):
        idx = rng.integers(0, len(d), len(d))
        sample = d.iloc[idx].reset_index(drop=True)
        values.append(partial_rank(sample, x, y, covars)[0])
    return float(np.nanpercentile(values, 2.5)), float(np.nanpercentile(values, 97.5))


def original_validation(paired: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(SEED)
    for i, (feature, outcome) in enumerate(SIGNALS):
        target = OUTCOME_PREFIX[outcome] + "_delta"
        x = feature + "_delta"
        d = paired[[x, target]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        rho, p = spearmanr(d[x], d[target])
        bootstrap = []
        for _ in range(BOOTSTRAPS):
            idx = rng.integers(0, len(d), len(d)); bootstrap.append(spearmanr(d[x].iloc[idx], d[target].iloc[idx]).statistic)
        rows.append({"feature_name": feature, "outcome": outcome, "n": len(d), "rho": rho, "p": p, "ci_low": np.nanpercentile(bootstrap, 2.5), "ci_high": np.nanpercentile(bootstrap, 97.5), "source": "recomputed_from_saved_inputs"})
    out = pd.DataFrame(rows); out["fdr_q"] = bh(out.p); return out


def adjusted_validation(paired: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(SEED + 11)
    for feature, outcome in SIGNALS:
        target = OUTCOME_PREFIX[outcome] + "_delta"; x = feature + "_delta"; baseline = OUTCOME_PREFIX[outcome] + "_T1"
        covar_sets = {
            "core_age_sex_education": ["age", "Gender (1=M, 2=F)", "Education (years)"],
            "core_plus_baseline": ["age", "Gender (1=M, 2=F)", "Education (years)", baseline],
            "core_baseline_recording": ["age", "Gender (1=M, 2=F)", "Education (years)", baseline, "active_days_delta", x.replace("_delta", "_snapshot_rate_delta"), x.replace("_delta", "_valid_interval_rate_delta"), "device_changed"],
        }
        for adjustment, covars in covar_sets.items():
            rho, p, n = partial_rank(paired, x, target, covars)
            lo, hi = bootstrap_partial(paired, x, target, covars, rng)
            rows.append({"feature_name": feature, "outcome": outcome, "adjustment": adjustment, "covariates": ";".join(covars), "n": n, "partial_rho": rho, "partial_p": p, "bootstrap_ci_low": lo, "bootstrap_ci_high": hi})
    out = pd.DataFrame(rows); out["fdr_q_within_adjustment"] = out.groupby("adjustment")["partial_p"].transform(bh); return out


def robustness(paired: pd.DataFrame) -> pd.DataFrame:
    rows = []; rng = np.random.default_rng(SEED + 22)
    for feature, outcome in SIGNALS:
        target = OUTCOME_PREFIX[outcome] + "_delta"; x = feature + "_delta"
        d = paired[["Subject_ID_D", x, target]].apply(pd.to_numeric, errors="coerce") if False else paired[["Subject_ID_D", x, target]].copy()
        d[x] = pd.to_numeric(d[x], errors="coerce"); d[target] = pd.to_numeric(d[target], errors="coerce"); d = d.replace([np.inf, -np.inf], np.nan).dropna()
        rho = spearmanr(d[x], d[target]).statistic
        loo = []
        for sid in d.Subject_ID_D:
            keep = d.Subject_ID_D.ne(sid); loo.append(spearmanr(d.loc[keep, x], d.loc[keep, target]).statistic)
        q1x, q3x = d[x].quantile([.25, .75]); q1y, q3y = d[target].quantile([.25, .75])
        keep = d[x].between(q1x - 1.5 * (q3x - q1x), q3x + 1.5 * (q3x - q1x)) & d[target].between(q1y - 1.5 * (q3y - q1y), q3y + 1.5 * (q3y - q1y))
        outlier_rho = spearmanr(d.loc[keep, x], d.loc[keep, target]).statistic if keep.sum() >= 12 else np.nan
        null = []
        y = d[target].to_numpy(float); xvals = d[x].to_numpy(float)
        for _ in range(PERMUTATIONS): null.append(spearmanr(xvals, rng.permutation(y)).statistic)
        perm_p = (1 + np.sum(np.abs(null) >= abs(rho))) / (PERMUTATIONS + 1)
        rows.append({"feature_name": feature, "outcome": outcome, "n": len(d), "original_rho": rho, "loo_min_rho": np.min(loo), "loo_max_rho": np.max(loo), "loo_sign_consistency": np.mean(np.sign(loo) == np.sign(rho)), "max_abs_loo_change": np.max(np.abs(np.asarray(loo) - rho)), "outlier_filtered_n": int(keep.sum()), "outlier_filtered_rho": outlier_rho, "permutation_replicates": PERMUTATIONS, "permutation_p": perm_p})
    out = pd.DataFrame(rows); out["permutation_fdr_q"] = bh(out.permutation_p); return out


def feature_correlations(paired: pd.DataFrame) -> pd.DataFrame:
    rows = []
    cols = sorted({feature for feature, _ in SIGNALS})
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            d = paired[[a + "_delta", b + "_delta"]].apply(pd.to_numeric, errors="coerce").dropna()
            rho, p = spearmanr(d.iloc[:, 0], d.iloc[:, 1]) if len(d) >= 4 else (np.nan, np.nan)
            rows.append({"feature_a": a, "feature_b": b, "n": len(d), "spearman_rho": rho, "p": p})
    out = pd.DataFrame(rows); out["fdr_q"] = bh(out.p); return out


def reliability() -> pd.DataFrame:
    daily = pd.read_csv(DAILY, dtype={"Subject_ID_D": str}); daily["Subject_ID_D"] = daily["Subject_ID_D"].map(norm_id)
    win = pd.read_csv(WINDOW, dtype={"Subject_ID_D": str}); win["Subject_ID_D"] = win["Subject_ID_D"].map(norm_id)
    rows = []
    for _, w in win.iterrows():
        d = daily[daily.Subject_ID_D.eq(w.Subject_ID_D) & daily.window_name.eq(w.window_name)].copy()
        if d.empty: continue
        midpoint = (float(w.window_start_ms) + float(w.window_end_ms)) / 2
        dates = pd.to_datetime(d.local_date).astype("int64") // 10**6
        d["half"] = np.where(dates < midpoint, "first_half", "second_half")
        for f in sorted({f for f, _ in SIGNALS}):
            vals = d.groupby("half")[f].median(numeric_only=True)
            if "first_half" in vals and "second_half" in vals:
                rows.append({"method": "calendar_midpoint_split", "Subject_ID_D": w.Subject_ID_D, "window_name": w.window_name, "feature_name": f, "first_half": vals["first_half"], "second_half": vals["second_half"], "first_days": int((d.half == "first_half").sum()), "second_days": int((d.half == "second_half").sum())})
            # The saved keyboard data are concentrated in one side of most
            # long clinical windows. Following the cited reliability design,
            # add a first/last observed-period test-retest estimate when at
            # least 28 active days are available.
            observed = d.sort_values("local_date").reset_index(drop=True)
            if len(observed) >= 28:
                first = observed.iloc[:14][f].median()
                last = observed.iloc[-14:][f].median()
                if pd.notna(first) and pd.notna(last):
                    rows.append({"method": "first_last_14_observed_days", "Subject_ID_D": w.Subject_ID_D, "window_name": w.window_name, "feature_name": f, "first_half": first, "second_half": last, "first_days": 14, "second_days": 14})
    half = pd.DataFrame(rows)
    out = []
    if half.empty:
        return pd.DataFrame(columns=["method", "window_name", "feature_name", "n_patients", "first_half_days_median", "second_half_days_median", "icc_2_1_absolute_agreement", "split_half_spearman_rho", "split_half_p"])
    for (method, window, feature), d in half.groupby(["method", "window_name", "feature_name"]):
        d = d.dropna(subset=["first_half", "second_half"]); n = len(d)
        if n < 4: continue
        a = d.first_half.to_numpy(float); b = d.second_half.to_numpy(float); rho, p = spearmanr(a, b)
        frame = np.column_stack([a, b]); nsub, k = frame.shape; mean_subject = frame.mean(axis=1); mean_rater = frame.mean(axis=0); grand = frame.mean(); ms_subject = k * np.sum((mean_subject - grand) ** 2) / (nsub - 1); ms_rater = nsub * np.sum((mean_rater - grand) ** 2) / (k - 1); residual = frame - mean_subject[:, None] - mean_rater[None, :] + grand; ms_error = np.sum(residual ** 2) / ((nsub - 1) * (k - 1)); icc = (ms_subject - ms_error) / (ms_subject + (k - 1) * ms_error + k * (ms_rater - ms_error) / nsub) if np.isfinite(ms_error) else np.nan
        out.append({"method": method, "window_name": window, "feature_name": feature, "n_patients": n, "first_half_days_median": d.first_days.median(), "second_half_days_median": d.second_days.median(), "icc_2_1_absolute_agreement": icc, "split_half_spearman_rho": rho, "split_half_p": p})
    return pd.DataFrame(out)


def comparability(windows: pd.DataFrame, paired: pd.DataFrame) -> pd.DataFrame:
    cols = ["Subject_ID_D", "duration_days_T1", "duration_days_T2", "duration_difference_days", "active_local_days_T1", "active_local_days_T2", "distinct_observations_in_window_T1", "distinct_observations_in_window_T2", "keyboard_valid_interval_count_T1", "keyboard_valid_interval_count_T2", "device_count_T1", "device_count_T2", "device_changed"]
    return paired[[c for c in cols if c in paired.columns]].copy()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    windows, paired, _, _ = load_data()
    original = original_validation(paired); original.to_csv(OUT / "validation_original_associations.csv", index=False)
    adjusted = adjusted_validation(paired); adjusted.to_csv(OUT / "validation_adjusted_associations.csv", index=False)
    robust = robustness(paired); robust.to_csv(OUT / "validation_robustness.csv", index=False)
    corr = feature_correlations(paired); corr.to_csv(OUT / "validation_feature_correlations.csv", index=False)
    rel = reliability(); rel.to_csv(OUT / "validation_reliability.csv", index=False)
    comp = comparability(windows, paired); comp.to_csv(OUT / "validation_window_comparability.csv", index=False)
    summary = original.merge(robust, on=["feature_name", "outcome", "n"], how="left")
    summary.to_csv(OUT / "validation_summary.csv", index=False)
    manifest = {"status": "complete", "signals": len(SIGNALS), "paired_patients": int(len(paired)), "bootstrap_replicates": BOOTSTRAPS, "permutation_replicates": PERMUTATIONS, "reliability_method": "calendar midpoint split where both halves have observations; otherwise first and last 14 observed keyboard days when at least 28 days are available; median daily feature value; ICC(2,1) absolute agreement and Spearman", "device_change_available": True, "predictive_models_trained": False, "existing_outputs_modified": False}
    (OUT / "validation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
