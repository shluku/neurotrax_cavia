from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import signal


ROOT = Path(__file__).parent
PILOT_DIR = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot"
OUT_DIR = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis"
MANIFEST_PATH = PILOT_DIR / "accelerometer_24h_pilot_manifest.csv"

CHUNK_MINUTES = 5
LARGE_GAP_SECONDS = 1.0
MIN_SAMPLES_PER_CHUNK = 100
RESAMPLE_HZ = 10.0
STILLNESS_DYNAMIC_THRESHOLD = 0.10
HANDLING_DYNAMIC_THRESHOLD = 0.20
HIGH_MOTION_DYNAMIC_THRESHOLD = 0.75
WALKING_BAND = (1.0, 3.0)
SHAKING_BAND = (3.0, 8.0)
WALKING_RATIO_THRESHOLD = 0.35
SHAKING_RATIO_THRESHOLD = 0.35

BANDS = {
    "very_low_lt_0_3hz": (0.0, 0.3),
    "handling_0_3_1hz": (0.3, 1.0),
    "walking_like_1_3hz": WALKING_BAND,
    "vigorous_2_5_4hz": (2.5, 4.0),
    "shaking_like_3_8hz": SHAKING_BAND,
    "high_freq_8_12hz": (8.0, 12.0),
}
CLINICAL_BAND_LABELS = {
    "very_low_lt_0_3hz": "slow orientation/drift",
    "handling_0_3_1hz": "irregular phone handling",
    "walking_like_1_3hz": "walking-like rhythmic phone motion",
    "vigorous_2_5_4hz": "vigorous rhythmic phone motion",
    "shaking_like_3_8hz": "shaking/tremor-like phone motion",
    "high_freq_8_12hz": "high-frequency vibration check",
}


def load_manifest() -> dict[str, Any]:
    manifest = pd.read_csv(MANIFEST_PATH, dtype=str)
    if manifest.empty:
        raise RuntimeError(f"Empty manifest: {MANIFEST_PATH}")
    return manifest.iloc[0].to_dict()


def load_signal_data(signal_path: Path) -> pd.DataFrame:
    usecols = ["timestamp", "local_datetime", "device_id", "x", "y", "z", "magnitude"]
    df = pd.read_csv(signal_path, compression="gzip", usecols=usecols)
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    for col in ["x", "y", "z", "magnitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["timestamp", "x", "y", "z", "magnitude"]).copy()
    df["timestamp"] = df["timestamp"].astype("int64")
    df = df.sort_values("timestamp")
    before = len(df)
    df = df.drop_duplicates(subset=["timestamp", "x", "y", "z"], keep="first").copy()
    df.attrs["dropped_exact_duplicate_rows"] = before - len(df)
    df["dt_utc"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["dt_local"] = df["dt_utc"].dt.tz_convert("Asia/Jerusalem")
    return df


def bandpower(freq: np.ndarray, power: np.ndarray, low: float, high: float) -> float:
    mask = (freq >= low) & (freq < high)
    if not mask.any():
        return float("nan")
    return float(np.trapezoid(power[mask], freq[mask]))


def safe_entropy(values: pd.Series) -> float:
    counts = values.value_counts(dropna=True)
    total = counts.sum()
    if total == 0:
        return float("nan")
    p = counts / total
    return float(-(p * np.log2(p)).sum())


def chunk_iter(df: pd.DataFrame, start_ms: int, end_ms: int):
    chunk_ms = CHUNK_MINUTES * 60 * 1000
    chunk_index = 0
    t = start_ms
    while t < end_ms:
        t_next = min(t + chunk_ms, end_ms)
        chunk = df[(df["timestamp"] >= t) & (df["timestamp"] < t_next)].copy()
        yield chunk_index, t, t_next, chunk
        chunk_index += 1
        t = t_next


def classify_chunk(row: dict[str, Any]) -> str:
    if row["valid_sample_count"] < MIN_SAMPLES_PER_CHUNK:
        return "insufficient_signal"
    if row["gap_burden_fraction"] > 0.50:
        return "fragmented_signal"
    if row["dynamic_magnitude_median"] <= STILLNESS_DYNAMIC_THRESHOLD:
        return "still_phone_candidate"
    if (
        row.get("walking_like_power_ratio", 0) >= WALKING_RATIO_THRESHOLD
        and row["dominant_frequency_hz"] >= WALKING_BAND[0]
        and row["dominant_frequency_hz"] < WALKING_BAND[1]
    ):
        return "walking_like_phone_motion_candidate"
    if (
        row.get("shaking_like_power_ratio", 0) >= SHAKING_RATIO_THRESHOLD
        and row["dominant_frequency_hz"] >= SHAKING_BAND[0]
        and row["dominant_frequency_hz"] < SHAKING_BAND[1]
    ):
        return "shaking_like_phone_motion_candidate"
    if row["dynamic_magnitude_median"] >= HANDLING_DYNAMIC_THRESHOLD:
        return "phone_handling_motion_candidate"
    return "low_motion_phone_candidate"


def analyze_chunk(chunk_index: int, start_ms: int, end_ms: int, chunk: pd.DataFrame) -> dict[str, Any]:
    start_local = pd.to_datetime(start_ms, unit="ms", utc=True).tz_convert("Asia/Jerusalem")
    end_local = pd.to_datetime(end_ms, unit="ms", utc=True).tz_convert("Asia/Jerusalem")
    row: dict[str, Any] = {
        "chunk_index": chunk_index,
        "chunk_start_ms": start_ms,
        "chunk_end_ms": end_ms,
        "chunk_start_local": start_local.strftime("%Y-%m-%d %H:%M:%S%z"),
        "chunk_end_local": end_local.strftime("%Y-%m-%d %H:%M:%S%z"),
        "local_hour": int(start_local.hour),
        "is_night_22_06": bool(start_local.hour >= 22 or start_local.hour < 6),
        "valid_sample_count": len(chunk),
    }
    if chunk.empty:
        row.update(
            {
                "status": "no_rows",
                "observed_span_seconds": 0.0,
                "median_interval_ms": np.nan,
                "p95_interval_ms": np.nan,
                "max_gap_seconds": np.nan,
                "gap_count_gt_1s": 0,
                "gap_burden_fraction": np.nan,
                "gravity_baseline_median": np.nan,
                "magnitude_mean": np.nan,
                "magnitude_sd": np.nan,
                "dynamic_magnitude_mean": np.nan,
                "dynamic_magnitude_median": np.nan,
                "dynamic_magnitude_sd": np.nan,
                "high_motion_fraction": np.nan,
                "dominant_frequency_hz": np.nan,
                "total_power": np.nan,
            }
        )
        for name in BANDS:
            row[f"{name}_power"] = np.nan
            row[f"{name}_power_ratio"] = np.nan
        row["chunk_state_candidate"] = "insufficient_signal"
        return row

    ts = chunk["timestamp"].to_numpy(dtype=np.int64)
    intervals_ms = np.diff(ts)
    positive_intervals = intervals_ms[intervals_ms > 0]
    gap_seconds = positive_intervals / 1000.0
    observed_span_seconds = max((int(ts[-1]) - int(ts[0])) / 1000.0, 0.0)
    gap_burden_seconds = float(gap_seconds[gap_seconds > LARGE_GAP_SECONDS].sum()) if len(gap_seconds) else 0.0
    gap_burden_fraction = gap_burden_seconds / (CHUNK_MINUTES * 60)
    magnitude = chunk["magnitude"].to_numpy(dtype=float)
    baseline = float(np.nanmedian(magnitude))
    dynamic = np.abs(magnitude - baseline)

    row.update(
        {
            "status": "ok" if len(chunk) >= MIN_SAMPLES_PER_CHUNK else "too_few_samples",
            "observed_span_seconds": observed_span_seconds,
            "median_interval_ms": float(np.nanmedian(positive_intervals)) if len(positive_intervals) else np.nan,
            "p95_interval_ms": float(np.nanpercentile(positive_intervals, 95)) if len(positive_intervals) else np.nan,
            "max_gap_seconds": float(np.nanmax(gap_seconds)) if len(gap_seconds) else np.nan,
            "gap_count_gt_1s": int((gap_seconds > LARGE_GAP_SECONDS).sum()) if len(gap_seconds) else 0,
            "gap_burden_fraction": gap_burden_fraction,
            "gravity_baseline_median": baseline,
            "magnitude_mean": float(np.nanmean(magnitude)),
            "magnitude_sd": float(np.nanstd(magnitude)),
            "dynamic_magnitude_mean": float(np.nanmean(dynamic)),
            "dynamic_magnitude_median": float(np.nanmedian(dynamic)),
            "dynamic_magnitude_sd": float(np.nanstd(dynamic)),
            "high_motion_fraction": float(np.mean(dynamic >= HIGH_MOTION_DYNAMIC_THRESHOLD)),
        }
    )

    total_power = np.nan
    dominant_frequency = np.nan
    band_values: dict[str, float] = {name: np.nan for name in BANDS}
    if len(chunk) >= MIN_SAMPLES_PER_CHUNK and observed_span_seconds >= 30 and row["gap_burden_fraction"] <= 0.50:
        effective_hz = 1000.0 / row["median_interval_ms"] if row["median_interval_ms"] and not math.isnan(row["median_interval_ms"]) else np.nan
        nyquist_hz = effective_hz / 2.0 if effective_hz and not math.isnan(effective_hz) else np.nan
        row["effective_sampling_hz_from_median_interval"] = effective_hz
        row["effective_nyquist_hz_from_median_interval"] = nyquist_hz
        series = pd.Series(dynamic, index=chunk["dt_utc"])
        resampled = series.resample(f"{int(1000 / RESAMPLE_HZ)}ms").mean().interpolate(limit_direction="both")
        values = resampled.to_numpy(dtype=float)
        if len(values) >= int(30 * RESAMPLE_HZ):
            values = signal.detrend(values)
            nperseg = min(len(values), int(60 * RESAMPLE_HZ))
            freq, power = signal.welch(values, fs=RESAMPLE_HZ, nperseg=nperseg)
            valid = freq > 0
            total_power = float(np.trapezoid(power[valid], freq[valid])) if valid.any() else np.nan
            if valid.any():
                dominant_frequency = float(freq[valid][np.argmax(power[valid])])
            for name, (low, high) in BANDS.items():
                high = min(high, RESAMPLE_HZ / 2)
                band_values[name] = bandpower(freq, power, low, high) if low < high else np.nan
    else:
        row["effective_sampling_hz_from_median_interval"] = np.nan
        row["effective_nyquist_hz_from_median_interval"] = np.nan

    row["dominant_frequency_hz"] = dominant_frequency
    row["total_power"] = total_power
    for name, value in band_values.items():
        row[f"{name}_power"] = value
        row[f"{name}_power_ratio"] = value / total_power if total_power and total_power > 0 and not math.isnan(value) else np.nan
    row["walking_like_power_ratio"] = row.get("walking_like_1_3hz_power_ratio", np.nan)
    row["shaking_like_power_ratio"] = row.get("shaking_like_3_8hz_power_ratio", np.nan)
    row["chunk_state_candidate"] = classify_chunk(row)
    return row


def summarize_features(chunk_df: pd.DataFrame, manifest: dict[str, Any], total_rows: int, duplicate_rows: int) -> pd.DataFrame:
    valid = chunk_df[chunk_df["status"].eq("ok")].copy()
    duration_minutes = CHUNK_MINUTES
    state_minutes = valid.groupby("chunk_state_candidate").size() * duration_minutes if not valid.empty else pd.Series(dtype=float)
    night = valid[valid["is_night_22_06"].astype(bool)] if not valid.empty else valid
    day = valid[~valid["is_night_22_06"].astype(bool)] if not valid.empty else valid
    night_motion = float((night["dynamic_magnitude_median"] >= HANDLING_DYNAMIC_THRESHOLD).sum() * duration_minutes) if not night.empty else 0.0
    day_motion = float((day["dynamic_magnitude_median"] >= HANDLING_DYNAMIC_THRESHOLD).sum() * duration_minutes) if not day.empty else 0.0
    feature_row = {
        "Subject_ID_D": manifest.get("Subject_ID_D", ""),
        "Subject_ID_N": manifest.get("Subject_ID_N", ""),
        "global_T1": manifest.get("global_T1", ""),
        "T1_date_iso": manifest.get("T1_date_iso", ""),
        "device_id": manifest.get("device_id", ""),
        "window_start_local": manifest.get("candidate_window_start_local", ""),
        "window_end_local": manifest.get("candidate_window_end_local", ""),
        "accelerometer_total_rows_loaded": total_rows,
        "accelerometer_exact_duplicate_rows_removed": duplicate_rows,
        "accelerometer_valid_signal_minutes": float(len(valid) * duration_minutes),
        "accelerometer_valid_chunk_count": int(len(valid)),
        "accelerometer_median_sampling_interval_ms": float(valid["median_interval_ms"].median()) if not valid.empty else np.nan,
        "accelerometer_gap_burden_fraction": float(valid["gap_burden_fraction"].mean()) if not valid.empty else np.nan,
        "accelerometer_dynamic_magnitude_mean": float(valid["dynamic_magnitude_mean"].mean()) if not valid.empty else np.nan,
        "accelerometer_dynamic_magnitude_sd": float(valid["dynamic_magnitude_sd"].mean()) if not valid.empty else np.nan,
        "accelerometer_still_phone_minutes": float(state_minutes.get("still_phone_candidate", 0.0)),
        "accelerometer_stillness_fraction": float(state_minutes.get("still_phone_candidate", 0.0) / (len(valid) * duration_minutes))
        if len(valid)
        else np.nan,
        "accelerometer_phone_handling_minutes": float(state_minutes.get("phone_handling_motion_candidate", 0.0)),
        "accelerometer_walking_like_minutes": float(state_minutes.get("walking_like_phone_motion_candidate", 0.0)),
        "accelerometer_shaking_like_minutes": float(state_minutes.get("shaking_like_phone_motion_candidate", 0.0)),
        "accelerometer_high_motion_chunk_fraction": float(valid["high_motion_fraction"].mean()) if not valid.empty else np.nan,
        "accelerometer_tremor_band_power_mean": float(valid["shaking_like_3_8hz_power"].mean()) if not valid.empty else np.nan,
        "accelerometer_day_motion_minutes": day_motion,
        "accelerometer_night_motion_minutes": night_motion,
        "accelerometer_day_night_motion_ratio": day_motion / night_motion if night_motion > 0 else np.nan,
        "accelerometer_hourly_motion_entropy": safe_entropy(
            valid.loc[valid["dynamic_magnitude_median"] >= HANDLING_DYNAMIC_THRESHOLD, "local_hour"]
        )
        if not valid.empty
        else np.nan,
    }
    return pd.DataFrame([feature_row])


def build_threshold_sensitivity(chunk_df: pd.DataFrame) -> pd.DataFrame:
    valid = chunk_df[chunk_df["status"].eq("ok")].copy()
    rows: list[dict[str, Any]] = []
    if valid.empty:
        return pd.DataFrame(rows)
    for threshold in [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.75, 1.00]:
        median_active = valid["dynamic_magnitude_median"] >= threshold
        mean_active = valid["dynamic_magnitude_mean"] >= threshold
        rows.append(
            {
                "dynamic_magnitude_threshold": threshold,
                "chunks_active_by_median": int(median_active.sum()),
                "minutes_active_by_median": float(median_active.sum() * CHUNK_MINUTES),
                "fraction_active_by_median": float(median_active.mean()),
                "chunks_active_by_mean": int(mean_active.sum()),
                "minutes_active_by_mean": float(mean_active.sum() * CHUNK_MINUTES),
                "fraction_active_by_mean": float(mean_active.mean()),
                "day_minutes_active_by_median": float(
                    (median_active & ~valid["is_night_22_06"].astype(bool)).sum() * CHUNK_MINUTES
                ),
                "night_minutes_active_by_median": float(
                    (median_active & valid["is_night_22_06"].astype(bool)).sum() * CHUNK_MINUTES
                ),
            }
        )
    return pd.DataFrame(rows)


def build_bandpass_feature_summary(chunk_df: pd.DataFrame) -> pd.DataFrame:
    valid = chunk_df[chunk_df["status"].eq("ok")].copy()
    rows: list[dict[str, Any]] = []
    if valid.empty:
        return pd.DataFrame(rows)
    band_ratio_cols = {name: f"{name}_power_ratio" for name in BANDS}
    candidate_band_names = list(BANDS.keys())
    ratio_frame = valid[[band_ratio_cols[name] for name in candidate_band_names]].copy()
    ratio_frame.columns = candidate_band_names
    dominant_band = ratio_frame.idxmax(axis=1)
    for name, (low, high) in BANDS.items():
        ratio_col = band_ratio_cols[name]
        power_col = f"{name}_power"
        analysis_nyquist_hz = min(RESAMPLE_HZ / 2.0, high)
        nyquist_ok = (valid["effective_nyquist_hz_from_median_interval"] >= high) & ((RESAMPLE_HZ / 2.0) >= high)
        dynamic_gate = valid["dynamic_magnitude_mean"] >= HANDLING_DYNAMIC_THRESHOLD
        dominant_gate = dominant_band.eq(name)
        ratio_gate = valid[ratio_col] >= 0.35
        selected = nyquist_ok & dynamic_gate & dominant_gate & ratio_gate
        rows.append(
            {
                "band_name": name,
                "clinical_candidate_label": CLINICAL_BAND_LABELS[name],
                "frequency_low_hz": low,
                "frequency_high_hz": high,
                "resample_hz": RESAMPLE_HZ,
                "analysis_nyquist_hz": analysis_nyquist_hz,
                "full_band_measurable_with_current_resampling": bool((RESAMPLE_HZ / 2.0) >= high),
                "chunks_with_sampling_feasible": int(nyquist_ok.sum()),
                "minutes_with_sampling_feasible": float(nyquist_ok.sum() * CHUNK_MINUTES),
                "mean_power_ratio_all_valid_chunks": float(valid[ratio_col].mean()),
                "median_power_ratio_all_valid_chunks": float(valid[ratio_col].median()),
                "mean_power_all_valid_chunks": float(valid[power_col].mean()),
                "candidate_chunks_after_dynamic_and_frequency_gates": int(selected.sum()),
                "candidate_minutes_after_dynamic_and_frequency_gates": float(selected.sum() * CHUNK_MINUTES),
                "day_candidate_minutes": float((selected & ~valid["is_night_22_06"].astype(bool)).sum() * CHUNK_MINUTES),
                "night_candidate_minutes": float((selected & valid["is_night_22_06"].astype(bool)).sum() * CHUNK_MINUTES),
                "interpretation_caution": "phone-state candidate only; sampling feasibility and phone placement limit clinical interpretation",
            }
        )
    return pd.DataFrame(rows)


def build_bandpass_hourly_summary(chunk_df: pd.DataFrame) -> pd.DataFrame:
    valid = chunk_df[chunk_df["status"].eq("ok")].copy()
    rows: list[dict[str, Any]] = []
    if valid.empty:
        return pd.DataFrame(rows)
    ratio_frame = valid[[f"{name}_power_ratio" for name in BANDS]].copy()
    ratio_frame.columns = list(BANDS.keys())
    valid = valid.assign(dominant_band=ratio_frame.idxmax(axis=1))
    for hour, group in valid.groupby("local_hour"):
        row: dict[str, Any] = {
            "local_hour": int(hour),
            "valid_chunks": len(group),
            "valid_minutes": float(len(group) * CHUNK_MINUTES),
            "mean_dynamic_magnitude": float(group["dynamic_magnitude_mean"].mean()),
            "median_dynamic_magnitude": float(group["dynamic_magnitude_median"].median()),
        }
        for name, (_, high) in BANDS.items():
            feasible = (group["effective_nyquist_hz_from_median_interval"] >= high) & ((RESAMPLE_HZ / 2.0) >= high)
            selected = (
                feasible
                & (group["dynamic_magnitude_mean"] >= HANDLING_DYNAMIC_THRESHOLD)
                & group["dominant_band"].eq(name)
                & (group[f"{name}_power_ratio"] >= 0.35)
            )
            row[f"{name}_candidate_minutes"] = float(selected.sum() * CHUNK_MINUTES)
            row[f"{name}_mean_power_ratio"] = float(group[f"{name}_power_ratio"].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def build_readme(manifest: dict[str, Any], feature_df: pd.DataFrame) -> str:
    row = feature_df.iloc[0].to_dict() if not feature_df.empty else {}
    return f"""# Accelerometer 24h Local Signal Analysis Pilot

This analysis used only the local 24-hour pilot signal file. No SQL was queried.

Pilot window:

- Subject_ID_D: `{manifest.get("Subject_ID_D", "")}`
- Subject_ID_N: `{manifest.get("Subject_ID_N", "")}`
- global_T1: `{manifest.get("global_T1", "")}`
- T1 date: `{manifest.get("T1_date_iso", "")}`
- device_id: `{manifest.get("device_id", "")}`
- window: `{manifest.get("candidate_window_start_local", "")}` to `{manifest.get("candidate_window_end_local", "")}`
- loaded rows after numeric x/y/z filtering: `{row.get("accelerometer_total_rows_loaded", "")}`
- valid signal minutes: `{row.get("accelerometer_valid_signal_minutes", "")}`

Processing:

- Loaded local `*_signal.csv.gz`.
- Sorted rows chronologically.
- Removed exact duplicate timestamp/x/y/z rows.
- Computed raw magnitude as `sqrt(x^2 + y^2 + z^2)`.
- Used each 5-minute chunk's median magnitude as a first-pass gravity/static baseline.
- Computed `dynamic_magnitude = abs(magnitude - chunk_median_magnitude)`.
- Computed sampling gaps and marked chunks with too few samples or heavy gaps.
- Resampled valid chunks to `10 Hz` for Welch frequency-band power.

Frequency bands tested:

- `<0.3 Hz`: very low frequency drift/orientation
- `0.3-1 Hz`: handling/non-walking motion
- `1-3 Hz`: walking-like rhythmic phone motion
- `2.5-4 Hz`: vigorous rhythmic phone motion
- `3-8 Hz`: shaking/tremor-like phone motion
- `8-12 Hz`: high-frequency check

Initial exploratory thresholds:

- chunk length: `{CHUNK_MINUTES}` minutes
- large gap: `{LARGE_GAP_SECONDS}` second
- minimum samples per chunk: `{MIN_SAMPLES_PER_CHUNK}`
- still-phone dynamic threshold: `{STILLNESS_DYNAMIC_THRESHOLD}` m/s^2
- handling dynamic threshold: `{HANDLING_DYNAMIC_THRESHOLD}` m/s^2
- high-motion dynamic threshold: `{HIGH_MOTION_DYNAMIC_THRESHOLD}` m/s^2
- walking-like power ratio threshold: `{WALKING_RATIO_THRESHOLD}`
- shaking-like power ratio threshold: `{SHAKING_RATIO_THRESHOLD}`

Important interpretation:

- These are phone-state candidate labels, not clinical activity labels.
- `walking-like` does not prove walking.
- `shaking-like` does not prove tremor.
- A still phone does not prove a still patient.
- Missing accelerometer signal remains missing, not no activity.

Generated files:

- `accelerometer_24h_local_pilot_overall_features.csv`
- `accelerometer_24h_local_pilot_chunk_summary.csv`
- `accelerometer_24h_local_pilot_hourly_summary.csv`
- `accelerometer_24h_local_pilot_state_summary.csv`
- `accelerometer_24h_local_pilot_bandpower_summary.csv`
- `accelerometer_24h_local_pilot_threshold_sensitivity.csv`
- `accelerometer_24h_local_pilot_bandpass_feature_summary.csv`
- `accelerometer_24h_local_pilot_bandpass_hourly_summary.csv`
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    signal_path = Path(str(manifest["signal_path"]))
    df = load_signal_data(signal_path)
    duplicate_rows = int(df.attrs.get("dropped_exact_duplicate_rows", 0))
    start_ms = int(float(manifest["candidate_window_start_ms"]))
    end_ms = int(float(manifest["candidate_window_end_ms"]))

    chunk_rows = [analyze_chunk(i, start, end, chunk) for i, start, end, chunk in chunk_iter(df, start_ms, end_ms)]
    chunk_df = pd.DataFrame(chunk_rows)
    features_df = summarize_features(chunk_df, manifest, len(df), duplicate_rows)

    hourly_df = (
        chunk_df[chunk_df["status"].eq("ok")]
        .groupby("local_hour", as_index=False)
        .agg(
            valid_chunks=("chunk_index", "count"),
            valid_minutes=("chunk_index", lambda x: len(x) * CHUNK_MINUTES),
            median_dynamic_magnitude=("dynamic_magnitude_median", "median"),
            mean_dynamic_magnitude=("dynamic_magnitude_mean", "mean"),
            high_motion_fraction=("high_motion_fraction", "mean"),
            walking_like_minutes=(
                "chunk_state_candidate",
                lambda s: float((s == "walking_like_phone_motion_candidate").sum() * CHUNK_MINUTES),
            ),
            shaking_like_minutes=(
                "chunk_state_candidate",
                lambda s: float((s == "shaking_like_phone_motion_candidate").sum() * CHUNK_MINUTES),
            ),
        )
    )
    state_df = (
        chunk_df.groupby(["chunk_state_candidate"], dropna=False, as_index=False)
        .agg(chunks=("chunk_index", "count"))
        .assign(minutes=lambda x: x["chunks"] * CHUNK_MINUTES)
        .sort_values("minutes", ascending=False)
    )
    band_cols = [f"{name}_power_ratio" for name in BANDS]
    threshold_df = build_threshold_sensitivity(chunk_df)
    bandpass_feature_df = build_bandpass_feature_summary(chunk_df)
    bandpass_hourly_df = build_bandpass_hourly_summary(chunk_df)
    bandpower_df = (
        chunk_df[chunk_df["status"].eq("ok")][["chunk_index", "chunk_start_local", "chunk_state_candidate", "dominant_frequency_hz", *band_cols]]
        .copy()
    )

    outputs = {
        "features": OUT_DIR / "accelerometer_24h_local_pilot_overall_features.csv",
        "chunks": OUT_DIR / "accelerometer_24h_local_pilot_chunk_summary.csv",
        "hourly": OUT_DIR / "accelerometer_24h_local_pilot_hourly_summary.csv",
        "states": OUT_DIR / "accelerometer_24h_local_pilot_state_summary.csv",
        "bandpower": OUT_DIR / "accelerometer_24h_local_pilot_bandpower_summary.csv",
        "thresholds": OUT_DIR / "accelerometer_24h_local_pilot_threshold_sensitivity.csv",
        "bandpass_features": OUT_DIR / "accelerometer_24h_local_pilot_bandpass_feature_summary.csv",
        "bandpass_hourly": OUT_DIR / "accelerometer_24h_local_pilot_bandpass_hourly_summary.csv",
        "readme": OUT_DIR / "README_accelerometer_24h_local_signal_analysis.md",
    }
    features_df.to_csv(outputs["features"], index=False)
    chunk_df.to_csv(outputs["chunks"], index=False)
    hourly_df.to_csv(outputs["hourly"], index=False)
    state_df.to_csv(outputs["states"], index=False)
    bandpower_df.to_csv(outputs["bandpower"], index=False)
    threshold_df.to_csv(outputs["thresholds"], index=False)
    bandpass_feature_df.to_csv(outputs["bandpass_features"], index=False)
    bandpass_hourly_df.to_csv(outputs["bandpass_hourly"], index=False)
    outputs["readme"].write_text(build_readme(manifest, features_df), encoding="utf-8")

    print("accelerometer_24h_local_analysis_complete")
    print(f"subject: {manifest.get('Subject_ID_D', '')}")
    print(f"device: {manifest.get('device_id', '')}")
    print(f"rows_loaded: {len(df):,}")
    print(f"duplicates_removed: {duplicate_rows:,}")
    print(f"valid_chunks: {int(chunk_df['status'].eq('ok').sum())}")
    print(f"valid_signal_minutes: {features_df.iloc[0]['accelerometer_valid_signal_minutes']}")
    print("state_summary:")
    print(state_df.to_string(index=False))
    print("generated_files:")
    for path in outputs.values():
        print(path)


if __name__ == "__main__":
    main()
