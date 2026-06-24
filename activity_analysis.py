import argparse
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, welch
import matplotlib.pyplot as plt


def parse_bands(spec: str) -> Dict[str, Tuple[float, float]]:
    bands: Dict[str, Tuple[float, float]] = {}
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        lo_s, hi_s = chunk.split("-")
        lo = float(lo_s)
        hi = float(hi_s)
        if lo < 0 or hi <= lo:
            raise ValueError(f"Invalid band: {chunk}")
        bands[f"{lo:g}-{hi:g}Hz"] = (lo, hi)
    if not bands:
        raise ValueError("No valid bands were provided.")
    return bands


def estimate_fs(timestamps_ms: np.ndarray) -> Tuple[float, Dict[str, float]]:
    timestamps_ms = np.asarray(timestamps_ms, dtype=np.float64)
    dt_s = np.diff(timestamps_ms) / 1000.0
    dt_s = dt_s[np.isfinite(dt_s) & (dt_s > 0)]
    if dt_s.size == 0:
        raise ValueError("Not enough valid timestamps to estimate sampling rate.")
    stats = {
        "median": float(np.median(dt_s)),
        "mean": float(np.mean(dt_s)),
        "std": float(np.std(dt_s)),
        "min": float(np.min(dt_s)),
        "max": float(np.max(dt_s)),
    }
    fs = 1.0 / stats["median"]
    return fs, stats


def bandpass_filter(signal: np.ndarray, fs: float) -> np.ndarray:
    if fs <= 0:
        raise ValueError("Sampling rate must be positive.")
    low = 0.3
    high = min(8.0, 0.4 * fs)
    if high <= low:
        return signal
    b, a = butter(4, [low, high], btype="bandpass", fs=fs)
    return filtfilt(b, a, signal)


def compute_window_powers(
    signal: np.ndarray,
    fs: float,
    win_sec: float = 5.0,
    overlap: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray]:
    if fs <= 0:
        raise ValueError("Sampling rate must be positive.")
    win_len = int(round(win_sec * fs))
    if win_len < 8:
        raise ValueError("Window length too short for Welch PSD.")
    step = max(1, int(round(win_len * (1.0 - overlap))))
    n = len(signal)
    powers = []
    times_ms = []
    for start in range(0, n - win_len + 1, step):
        segment = signal[start:start + win_len]
        f, pxx = welch(segment, fs=fs, nperseg=win_len, scaling="density")
        mask = (f >= 0.5) & (f <= 5.0)
        power = float(np.sum(pxx[mask]))
        powers.append(power)
        times_ms.append(start)
    return np.asarray(times_ms), np.asarray(powers)


def compute_window_band_powers(
    signal: np.ndarray,
    fs: float,
    bands: Dict[str, Tuple[float, float]],
    win_sec: float = 5.0,
    overlap: float = 0.5,
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    win_len = int(round(win_sec * fs))
    if win_len < 8:
        raise ValueError("Window length too short for Welch PSD.")
    step = max(1, int(round(win_len * (1.0 - overlap))))
    n = len(signal)
    times_samples = []
    out = {name: [] for name in bands}
    for start in range(0, n - win_len + 1, step):
        segment = signal[start:start + win_len]
        f, pxx = welch(segment, fs=fs, nperseg=win_len, scaling="density")
        for name, (lo, hi) in bands.items():
            mask = (f >= lo) & (f <= hi)
            out[name].append(float(np.sum(pxx[mask])))
        times_samples.append(start)
    return np.asarray(times_samples), {k: np.asarray(v) for k, v in out.items()}


def summarize_by_day(
    timestamps_ms: np.ndarray,
    window_times_samples: np.ndarray,
    window_powers: np.ndarray,
) -> Dict[str, Dict[str, float]]:
    t0 = float(timestamps_ms[0])
    # Map sample indices to timestamps by linear interpolation.
    sample_to_time = np.interp(
        window_times_samples,
        np.arange(len(timestamps_ms)),
        timestamps_ms.astype(np.float64),
    )
    day_ms = 24 * 60 * 60 * 1000.0
    d1_mask = (sample_to_time >= t0) & (sample_to_time < t0 + day_ms)
    d2_mask = (sample_to_time >= t0 + day_ms) & (sample_to_time < t0 + 2 * day_ms)
    summaries = {}
    for label, mask in [("day1", d1_mask), ("day2", d2_mask)]:
        vals = window_powers[mask]
        if vals.size == 0:
            summaries[label] = {"median": np.nan, "p75": np.nan, "iqr": np.nan}
        else:
            q25 = np.percentile(vals, 25)
            q75 = np.percentile(vals, 75)
            summaries[label] = {
                "median": float(np.median(vals)),
                "p75": float(q75),
                "iqr": float(q75 - q25),
            }
    return summaries


def split_day_masks(
    timestamps_ms: np.ndarray,
    window_times_samples: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    t0 = float(timestamps_ms[0])
    sample_to_time = np.interp(
        window_times_samples,
        np.arange(len(timestamps_ms)),
        timestamps_ms.astype(np.float64),
    )
    day_ms = 24 * 60 * 60 * 1000.0
    d1_mask = (sample_to_time >= t0) & (sample_to_time < t0 + day_ms)
    d2_mask = (sample_to_time >= t0 + day_ms) & (sample_to_time < t0 + 2 * day_ms)
    return sample_to_time, d1_mask, d2_mask


def summarize_band_day_compare(
    band_powers: Dict[str, np.ndarray],
    d1_mask: np.ndarray,
    d2_mask: np.ndarray,
) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for name, vals in band_powers.items():
        d1 = vals[d1_mask]
        d2 = vals[d2_mask]
        d1_med = float(np.median(d1)) if d1.size else np.nan
        d2_med = float(np.median(d2)) if d2.size else np.nan
        ratio = d2_med / d1_med if np.isfinite(d1_med) and d1_med > 0 and np.isfinite(d2_med) else np.nan
        out[name] = {
            "day1_median": d1_med,
            "day2_median": d2_med,
            "delta_day2_minus_day1": d2_med - d1_med if np.isfinite(d1_med) and np.isfinite(d2_med) else np.nan,
            "ratio_day2_div_day1": ratio,
        }
    return out


def main():
    parser = argparse.ArgumentParser(description="AWARE accelerometer activity analysis.")
    parser.add_argument("csv_path", type=Path, help="Path to CSV with timestamp, device_id, x, y, z")
    parser.add_argument("--no-plots", action="store_true", help="Skip plotting for faster runs")
    parser.add_argument(
        "--bands",
        default="0.3-1,1-3,3-5,5-8",
        help="Comma-separated frequency bands in Hz, e.g. '0.3-1,1-3,3-5,5-8'",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.csv_path)
    df = df.sort_values("timestamp")
    df = df.dropna(subset=["x", "y", "z"])

    timestamps_ms = df["timestamp"].to_numpy()
    fs, stats = estimate_fs(timestamps_ms)
    print("dt_s stats:", stats)
    print("Estimated fs:", fs)
    if fs < 16:
        print("Warning: fs is below 16 Hz, so full 0.3-8 Hz may be clipped by Nyquist/filtering.")

    t0_utc = pd.to_datetime(timestamps_ms[0], unit="ms", utc=True)
    t1_utc = pd.to_datetime(timestamps_ms[-1], unit="ms", utc=True)
    print("Start UTC:", t0_utc)
    print("End UTC:", t1_utc)
    print("Start Asia/Jerusalem:", t0_utc.tz_convert("Asia/Jerusalem"))
    print("End Asia/Jerusalem:", t1_utc.tz_convert("Asia/Jerusalem"))
    print("Day 2 boundary Asia/Jerusalem:", (t0_utc + pd.Timedelta(days=1)).tz_convert("Asia/Jerusalem"))

    dt_s = np.diff(timestamps_ms) / 1000.0
    if not args.no_plots:
        plt.figure()
        plt.hist(dt_s[np.isfinite(dt_s) & (dt_s > 0)], bins=200)
        plt.title("dt_s Histogram")
        plt.xlabel("dt (s)")
        plt.ylabel("count")

    x = df["x"].to_numpy(dtype=np.float64)
    y = df["y"].to_numpy(dtype=np.float64)
    z = df["z"].to_numpy(dtype=np.float64)
    a = np.sqrt(x * x + y * y + z * z)
    a = a - np.mean(a)
    a_f = bandpass_filter(a, fs)

    window_times_samples, window_powers = compute_window_powers(a_f, fs, win_sec=5.0, overlap=0.5)
    summaries = summarize_by_day(timestamps_ms, window_times_samples, window_powers)
    print("Day 1:", summaries["day1"])
    print("Day 2:", summaries["day2"])

    bands = parse_bands(args.bands)
    window_times_samples_b, band_powers = compute_window_band_powers(a_f, fs, bands, win_sec=5.0, overlap=0.5)
    sample_to_time, d1_mask, d2_mask = split_day_masks(timestamps_ms, window_times_samples_b)
    band_compare = summarize_band_day_compare(band_powers, d1_mask, d2_mask)
    print("\nBand comparison (median window power):")
    for name, s in band_compare.items():
        print(
            f"{name}: day1={s['day1_median']:.6g}, "
            f"day2={s['day2_median']:.6g}, "
            f"delta={s['delta_day2_minus_day1']:.6g}, "
            f"ratio={s['ratio_day2_div_day1']:.6g}"
        )

    if not args.no_plots:
        plt.figure()
        d1 = window_powers[d1_mask]
        d2 = window_powers[d2_mask]
        plt.boxplot([d1, d2], labels=["Day 1", "Day 2"])
        plt.title("Window Power Distribution by Day")

        plt.figure()
        plt.plot(window_powers)
        plt.title("Window Power Over Time")
        plt.xlabel("Window index")
        plt.ylabel("Power")

        plt.figure()
        labels = list(bands.keys())
        day1_vals = [np.median(band_powers[k][d1_mask]) if np.any(d1_mask) else np.nan for k in labels]
        day2_vals = [np.median(band_powers[k][d2_mask]) if np.any(d2_mask) else np.nan for k in labels]
        x_idx = np.arange(len(labels))
        w = 0.35
        plt.bar(x_idx - w / 2, day1_vals, width=w, label="Day 1")
        plt.bar(x_idx + w / 2, day2_vals, width=w, label="Day 2")
        plt.xticks(x_idx, labels, rotation=20)
        plt.ylabel("Median window power")
        plt.title("Band Power Comparison")
        plt.legend()

        plt.show()


if __name__ == "__main__":
    main()
