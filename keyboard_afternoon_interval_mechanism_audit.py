#!/usr/bin/env python3
"""Privacy-preserving mechanism audit for the afternoon snapshot-interval signal.

Reads the saved discovery cohort/window summaries and re-queries only its
keyboard rows to create aggregate technical measures. Raw text, package names,
and device identifiers are never written to disk.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, t

from keyboard_deep_dive import (
    BURST_GAP_MS,
    LONG_PAUSE_MS,
    T1_STATUS,
    T2_STATUS,
    canonical_events,
    fetch_keyboard_rows,
)
from main import connect_sensordata_db


ROOT = Path(__file__).parent
DEEP = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1"
OUT = DEEP / "afternoon_interval_mechanism_audit_20261020"
WINDOW = DEEP / "keyboard_deep_dive_window_features.csv"
T1 = ROOT / "output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv"
T2 = ROOT / "output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv"
FEATURE = "keyboard_12_18_median_inter_event_interval_ms"
SEED = 20261020
BOOTSTRAPS = 2000


def normalize_id(value: object) -> str:
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def local_hour(ts_ms: int) -> int:
    return pd.to_datetime(int(ts_ms), unit="ms", utc=True).tz_convert("Asia/Jerusalem").hour


def local_day(ts_ms: int) -> str:
    return str(pd.to_datetime(int(ts_ms), unit="ms", utc=True).tz_convert("Asia/Jerusalem").date())


def partial_spearman(data: pd.DataFrame, outcome: str, predictor: str, covariates: list[str]) -> tuple[float, float, int]:
    frame = data[[predictor, outcome, *covariates]].apply(pd.to_numeric, errors="coerce").dropna()
    n = len(frame)
    if n < 12:
        return np.nan, np.nan, n
    ranks = frame.rank(method="average")
    design = np.column_stack([np.ones(n), ranks.iloc[:, 2:].to_numpy(dtype=float)])
    x = ranks.iloc[:, 0].to_numpy(dtype=float)
    y = ranks.iloc[:, 1].to_numpy(dtype=float)
    x_resid = x - design @ np.linalg.lstsq(design, x, rcond=None)[0]
    y_resid = y - design @ np.linalg.lstsq(design, y, rcond=None)[0]
    rho = float(np.corrcoef(x_resid, y_resid)[0, 1])
    df = max(n - len(covariates) - 2, 1)
    statistic = rho * math.sqrt(df / max(1 - rho * rho, 1e-12))
    return rho, float(2 * t.sf(abs(statistic), df)), n


def bootstrap_ci(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    frame = pd.concat([x, y], axis=1).dropna()
    rng = np.random.default_rng(SEED)
    values = []
    for _ in range(BOOTSTRAPS):
        sampled = frame.iloc[rng.integers(0, len(frame), len(frame))]
        values.append(spearmanr(sampled.iloc[:, 0], sampled.iloc[:, 1]).statistic)
    return float(np.nanpercentile(values, 2.5)), float(np.nanpercentile(values, 97.5))


def aggregate_window(events: list[dict[str, object]]) -> tuple[dict[str, float | int | None], set[str], set[str]]:
    """Recreate afternoon pairing rules and return only non-identifying summaries."""
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for event in events:
        grouped.setdefault((str(event["device_id"]), str(event["package_name"])), []).append(event)

    afternoon_events = [event for event in events if 12 <= local_hour(int(event["timestamp"])) < 18]
    package_counts: dict[str, int] = {}
    device_counts: dict[str, int] = {}
    for event in afternoon_events:
        package = str(event["package_name"])
        device = str(event["device_id"])
        package_counts[package] = package_counts.get(package, 0) + 1
        device_counts[device] = device_counts.get(device, 0) + 1

    intervals: list[float] = []
    absolute_text_changes: list[float] = []
    signed_text_changes: list[float] = []
    long_pauses = 0
    for group in grouped.values():
        previous = group[0]
        for event in group[1:]:
            delta = int(event["timestamp"]) - int(previous["timestamp"])
            # Exact IEI eligibility in keyboard_deep_dive.py: same device/package;
            # positive delta; no burst break (>30 seconds); bucket on later snapshot.
            if 0 < delta <= BURST_GAP_MS and 12 <= local_hour(int(event["timestamp"])) < 18:
                intervals.append(float(delta))
                length_change = int(event["current_len"]) - int(previous["current_len"])
                absolute_text_changes.append(abs(float(length_change)))
                signed_text_changes.append(float(length_change))
                if delta > LONG_PAUSE_MS:
                    long_pauses += 1
            previous = event

    total_packages = sum(package_counts.values())
    total_devices = sum(device_counts.values())
    package_shares = np.asarray([count / total_packages for count in package_counts.values()], dtype=float) if total_packages else np.asarray([])
    package_entropy = float(-np.sum(package_shares * np.log(package_shares))) if len(package_shares) else np.nan
    active_days = len({local_day(int(event["timestamp"])) for event in afternoon_events})
    metrics: dict[str, float | int | None] = {
        "afternoon_event_count": len(afternoon_events),
        "afternoon_active_days": active_days,
        "afternoon_events_per_active_day": len(afternoon_events) / active_days if active_days else np.nan,
        "afternoon_valid_interval_count_recomputed": len(intervals),
        "afternoon_median_iei_ms_recomputed": float(np.median(intervals)) if intervals else np.nan,
        "afternoon_long_pause_count_gt2s": long_pauses if intervals else np.nan,
        "afternoon_long_pause_rate_gt2s": long_pauses / len(intervals) if intervals else np.nan,
        "afternoon_median_abs_text_length_change": float(np.median(absolute_text_changes)) if absolute_text_changes else np.nan,
        "afternoon_median_signed_text_length_change": float(np.median(signed_text_changes)) if signed_text_changes else np.nan,
        "afternoon_unique_package_count": len(package_counts),
        "afternoon_dominant_package_share": max(package_counts.values()) / total_packages if total_packages else np.nan,
        "afternoon_package_entropy": package_entropy,
        "afternoon_unique_device_count": len(device_counts),
        "afternoon_dominant_device_share": max(device_counts.values()) / total_devices if total_devices else np.nan,
    }
    return metrics, set(package_counts), set(device_counts)


def status_specs() -> pd.DataFrame:
    frames = []
    for path, name in ((T1_STATUS, "Early"), (T2_STATUS, "Late")):
        data = pd.read_csv(path, dtype=str)
        data = data.loc[data["table_name"].eq("keyboard")].drop_duplicates(["Subject_ID_D", "window_start_ms", "window_end_ms"]).copy()
        data["Subject_ID_D"] = data["Subject_ID_D"].map(normalize_id)
        data["period"] = name
        data["device_ids_used"] = data["device_ids_used"].fillna(data["device_ids_available"])
        frames.append(data)
    return pd.concat(frames, ignore_index=True)


def cohort() -> pd.DataFrame:
    windows = pd.read_csv(WINDOW, dtype={"Subject_ID_D": str})
    windows["Subject_ID_D"] = windows["Subject_ID_D"].map(normalize_id)
    early = windows.loc[windows["window_name"].eq("T1")].set_index("Subject_ID_D")
    late = windows.loc[windows["window_name"].eq("T2")].set_index("Subject_ID_D")
    t1 = pd.read_csv(T1, dtype={"Subject_ID_D": str}); t1["Subject_ID_D"] = t1["Subject_ID_D"].map(normalize_id)
    t2 = pd.read_csv(T2, dtype={"Subject_ID_D": str}); t2["Subject_ID_D"] = t2["Subject_ID_D"].map(normalize_id)
    data = t1[["Subject_ID_D", "ef_T1"]].merge(t2[["Subject_ID_D", "ef_T2", "ef_delta"]], on="Subject_ID_D", how="inner")
    data = data.merge(early[[FEATURE, "keyboard_active_days", "distinct_observations_in_window", "keyboard_valid_interval_count", "keyboard_12_18_valid_interval_count", "window_start_local", "window_end_local"]], left_on="Subject_ID_D", right_index=True, how="left", suffixes=("", "_early"))
    data = data.merge(late[[FEATURE, "keyboard_active_days", "distinct_observations_in_window", "keyboard_valid_interval_count", "keyboard_12_18_valid_interval_count", "window_start_local", "window_end_local"]], left_on="Subject_ID_D", right_index=True, how="left", suffixes=("_early", "_late"))
    data = data.rename(columns={FEATURE + "_early": "afternoon_iei_early_ms", FEATURE + "_late": "afternoon_iei_late_ms"})
    data["afternoon_iei_delta_ms"] = pd.to_numeric(data["afternoon_iei_late_ms"], errors="coerce") - pd.to_numeric(data["afternoon_iei_early_ms"], errors="coerce")
    data = data.loc[data[["afternoon_iei_early_ms", "afternoon_iei_late_ms", "ef_delta"]].notna().all(axis=1)].copy()
    return data.sort_values("Subject_ID_D").reset_index(drop=True)


def technical_associations(data: pd.DataFrame) -> pd.DataFrame:
    factors = [
        "delta_afternoon_active_days", "delta_log_afternoon_interval_count", "delta_afternoon_events_per_active_day",
        "delta_afternoon_median_abs_text_length_change", "delta_afternoon_long_pause_rate_gt2s",
        "package_jaccard_similarity", "device_set_changed",
    ]
    rows = []
    for factor in factors:
        for outcome in ("afternoon_iei_delta_ms", "ef_delta"):
            frame = data[[factor, outcome]].apply(pd.to_numeric, errors="coerce").dropna()
            rho, p = spearmanr(frame[factor], frame[outcome])
            low, high = bootstrap_ci(frame[factor], frame[outcome])
            rows.append({"technical_factor": factor, "outcome": outcome, "n": len(frame), "spearman_rho": rho, "p": p, "bootstrap_ci_low": low, "bootstrap_ci_high": high})
    return pd.DataFrame(rows)


def plot_scatter(data: pd.DataFrame) -> None:
    rho, p = spearmanr(data["afternoon_iei_delta_ms"], data["ef_delta"])
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(data["afternoon_iei_delta_ms"], data["ef_delta"], color="#2563eb", alpha=.85)
    for row in data.itertuples():
        ax.annotate(str(row.Subject_ID_D), (row.afternoon_iei_delta_ms, row.ef_delta), xytext=(4, 4), textcoords="offset points", fontsize=7)
    ax.axhline(0, color="#6b7280", linewidth=.9); ax.axvline(0, color="#6b7280", linewidth=.9)
    ax.set_xlabel("Late − Early afternoon snapshot IEI (ms)")
    ax.set_ylabel("Executive Function T2 − T1")
    ax.set_title(f"Original discovery cohort (n={len(data)}): Spearman ρ={rho:.3f}, p={p:.4f}")
    fig.tight_layout(); fig.savefig(OUT / "afternoon_iei_vs_executive_function_scatter.png", dpi=180); plt.close(fig)


def plot_technical(associations: pd.DataFrame) -> None:
    table = associations.pivot(index="technical_factor", columns="outcome", values="spearman_rho")
    fig, ax = plt.subplots(figsize=(10, 5))
    table.plot(kind="bar", ax=ax, color=["#2563eb", "#f97316"])
    ax.axhline(0, color="black", linewidth=.8); ax.set_ylabel("Spearman correlation")
    ax.set_title("Exploratory technical-factor correlations")
    ax.legend(["IEI delta", "EF delta"])
    fig.tight_layout(); fig.savefig(OUT / "technical_factor_correlations.png", dpi=180); plt.close(fig)


def main(reuse_saved_patient_table: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    patients = cohort()
    if len(patients) != 28:
        raise ValueError(f"Expected original discovery cohort n=28; found {len(patients)}")
    original_rho, original_p = spearmanr(patients["afternoon_iei_delta_ms"], patients["ef_delta"])
    if not (abs(original_rho - 0.5928561708728188) < 1e-12 and abs(original_p - 0.0008854663078159199) < 1e-12):
        raise ValueError("Saved cohort does not reproduce the recorded discovery association.")

    if reuse_saved_patient_table:
        patients = pd.read_csv(OUT / "patient_level_mechanism_audit.csv", dtype={"Subject_ID_D": str})
    else:
        specs = status_specs().set_index(["Subject_ID_D", "period"])
        raw_audit: dict[tuple[str, str], tuple[dict[str, float | int | None], set[str], set[str]]] = {}
        conn = connect_sensordata_db()
        try:
            for sid in patients["Subject_ID_D"]:
                for period in ("Early", "Late"):
                    spec = specs.loc[(sid, period)]
                    device_ids = [value for value in str(spec["device_ids_used"] or "").split(";") if value and value.lower() != "nan"]
                    raw = fetch_keyboard_rows(conn, device_ids, int(float(spec["window_start_ms"])), int(float(spec["window_end_ms"])))
                    events, _, _ = canonical_events(raw)
                    raw_audit[(sid, period)] = aggregate_window(events)
        finally:
            conn.close()

        for period in ("Early", "Late"):
            period_rows = []
            for sid in patients["Subject_ID_D"]:
                metrics, _, _ = raw_audit[(sid, period)]
                period_rows.append({"Subject_ID_D": sid, **{f"{period.lower()}_{key}": value for key, value in metrics.items()}})
            patients = patients.merge(pd.DataFrame(period_rows), on="Subject_ID_D", how="left")
        for sid in patients["Subject_ID_D"]:
            early_packages = raw_audit[(sid, "Early")][1]; late_packages = raw_audit[(sid, "Late")][1]
            early_devices = raw_audit[(sid, "Early")][2]; late_devices = raw_audit[(sid, "Late")][2]
            union = early_packages | late_packages
            patients.loc[patients.Subject_ID_D.eq(sid), "package_jaccard_similarity"] = len(early_packages & late_packages) / len(union) if union else np.nan
            patients.loc[patients.Subject_ID_D.eq(sid), "device_set_changed"] = int(early_devices != late_devices)
        for metric in ("afternoon_active_days", "afternoon_events_per_active_day", "afternoon_median_abs_text_length_change", "afternoon_long_pause_rate_gt2s"):
            patients[f"delta_{metric}"] = pd.to_numeric(patients[f"late_{metric}"], errors="coerce") - pd.to_numeric(patients[f"early_{metric}"], errors="coerce")
        patients["delta_log_afternoon_interval_count"] = np.log1p(pd.to_numeric(patients["late_afternoon_valid_interval_count_recomputed"], errors="coerce")) - np.log1p(pd.to_numeric(patients["early_afternoon_valid_interval_count_recomputed"], errors="coerce"))

        # Recalculation from raw aggregate metadata must reproduce the saved feature.
        patients["early_iei_matches_saved"] = np.isclose(patients["afternoon_iei_early_ms"], patients["early_afternoon_median_iei_ms_recomputed"], equal_nan=True)
        patients["late_iei_matches_saved"] = np.isclose(patients["afternoon_iei_late_ms"], patients["late_afternoon_median_iei_ms_recomputed"], equal_nan=True)
        patients.to_csv(OUT / "patient_level_mechanism_audit.csv", index=False)

    technical = technical_associations(patients)
    technical.to_csv(OUT / "technical_factor_associations.csv", index=False)
    models = []
    for label, covariates in (
        ("unadjusted", []),
        ("coverage_and_frequency", ["delta_afternoon_active_days", "delta_log_afternoon_interval_count", "delta_afternoon_events_per_active_day"]),
        ("sampling_behavior_structure", ["delta_afternoon_median_abs_text_length_change", "delta_afternoon_long_pause_rate_gt2s", "package_jaccard_similarity", "device_set_changed"]),
        ("all_audited_technical_factors", ["delta_afternoon_active_days", "delta_log_afternoon_interval_count", "delta_afternoon_events_per_active_day", "delta_afternoon_median_abs_text_length_change", "delta_afternoon_long_pause_rate_gt2s", "package_jaccard_similarity", "device_set_changed"]),
    ):
        rho, p, n = partial_spearman(patients, "ef_delta", "afternoon_iei_delta_ms", covariates)
        models.append({"analysis": label, "covariates": ";".join(covariates) or "none", "partial_spearman_rho": rho, "p": p, "n": n, "exploratory": True})
    pd.DataFrame(models).to_csv(OUT / "exploratory_adjusted_associations.csv", index=False)
    plot_scatter(patients); plot_technical(technical)
    manifest = {
        "status": "complete", "cohort_n": len(patients), "feature": FEATURE,
        "saved_discovery_rho": original_rho, "saved_discovery_p": original_p,
        "raw_text_saved": False, "package_names_saved": False, "device_ids_saved": False,
        "new_analyses_exploratory": True, "existing_outputs_modified": False,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-saved-patient-table", action="store_true", help="Recalculate audit statistics/plots from the already privacy-aggregated patient table without querying raw snapshots.")
    args = parser.parse_args()
    main(reuse_saved_patient_table=args.reuse_saved_patient_table)
