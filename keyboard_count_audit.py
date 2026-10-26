"""Audit snapshot and interval denominators in saved keyboard outputs."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent
OUT = ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/count_audit"
SOURCES = {
    "midpoint_windows": ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/keyboard_deep_dive_window_features.csv",
    "first_last_thirds": ROOT / "output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity/third_window_features.csv",
}


def audit(name: str, path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    d = pd.read_csv(path, dtype={"Subject_ID_D": str})
    observations = pd.to_numeric(d["distinct_observations_in_window"], errors="coerce")
    intervals = pd.to_numeric(d["keyboard_valid_interval_count"], errors="coerce")
    valid = observations.notna() & intervals.notna()
    excess = valid & (intervals > observations)
    paired_medians = d.loc[valid, ["distinct_observations_in_window", "keyboard_valid_interval_count"]].median(numeric_only=True)
    independent_median_excess = float(paired_medians["keyboard_valid_interval_count"] - paired_medians["distinct_observations_in_window"])
    rows = d[["Subject_ID_D", "window_name", "raw_rows_in_window", "distinct_observations_in_window", "keyboard_valid_interval_count", "duplicate_rows_removed", "json_parse_errors", "window_status"]].copy()
    rows["interval_minus_observations"] = intervals - observations
    rows["invariant_ok"] = ~excess
    rows["source"] = name
    summary = {
        "source": name,
        "rows": len(d),
        "rows_with_nonmissing_counts": int(valid.sum()),
        "patient_window_violations": int(excess.sum()),
        "max_interval_minus_observations": float((intervals[valid] - observations[valid]).max()) if valid.any() else None,
        "median_observations": float(observations.median()),
        "median_valid_intervals": float(intervals.median()),
        "median_difference_independent": float(intervals.median() - observations.median()),
        "paired_median_observations": float(paired_medians["distinct_observations_in_window"]),
        "paired_median_valid_intervals": float(paired_medians["keyboard_valid_interval_count"]),
        "paired_median_difference": independent_median_excess,
    }
    return rows, summary


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_rows, summaries = [], []
    for name, path in SOURCES.items():
        rows, summary = audit(name, path)
        rows.to_csv(OUT / f"{name}_patient_window_audit.csv", index=False)
        all_rows.append(rows); summaries.append(summary)
    pd.DataFrame(summaries).to_csv(OUT / "count_audit_summary.csv", index=False)
    violations = pd.concat(all_rows, ignore_index=True)
    violations[~violations.invariant_ok].to_csv(OUT / "count_audit_violations.csv", index=False)
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__ == "__main__":
    main()
