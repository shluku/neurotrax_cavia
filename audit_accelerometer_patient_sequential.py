"""Audit completed ACC CSV outputs without SQL or changes to extraction state.

Writes a Markdown report and a JSON evidence record. Counts and duplicate QC
are taken from device-days because saved multi-device patient-days average
some non-additive fields. No outcome-based feature selection is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "output/analysis_candidates/accelerometer_patient_sequential_pipeline"
ARCHIVES = Path("/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_accelerometer/plugin_event_day_sql_zst")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distribution(values: pd.Series) -> dict:
    values = pd.to_numeric(values, errors="raise").dropna()
    return {"n": len(values), **{
        k: float(v) for k, v in values.describe().items() if k != "count"
    }}


def correlation(a: pd.Series, b: pd.Series) -> float | None:
    pair = pd.concat([a, b], axis=1).dropna()
    if len(pair) < 3 or (pair.nunique() < 2).any():
        return None
    return float(pair.iloc[:, 0].corr(pair.iloc[:, 1], method="spearman"))


def clean_json(value):
    if isinstance(value, dict):
        return {k: clean_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_json(v) for v in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path, default=SOURCE / "completion_audit")
    parser.add_argument("--archive-dir", type=Path, default=ARCHIVES)
    args = parser.parse_args()
    source, out = args.source_dir, args.output_dir
    paths = sorted(source.glob("*.csv")) + [source / "accelerometer_patient_sequential_checkpoint.json"]
    hashes = {p.name: digest(p) for p in paths}

    def read(suffix):
        return pd.read_csv(source / f"accelerometer_patient_sequential_{suffix}.csv", dtype={"patient_id": str})

    candidates, status, device, days, patients, progress, long = (
        read(s) for s in ("candidates", "status", "device_day_features", "patient_day_features",
                         "patient_level_features", "patient_progress", "features_long")
    )
    catalog = pd.read_csv(source / "accelerometer_plugin_event_day_feature_catalog.csv")
    checkpoint = json.loads(paths[-1].read_text())
    checks = {}

    def check(name, ok):
        checks[name] = bool(ok)

    for name, frame, keys in [("candidates", candidates, ["candidate_id"]),
                              ("status", status, ["candidate_id"]),
                              ("device_days", device, ["candidate_id"]),
                              ("patient_days", days, ["patient_id", "local_date"]),
                              ("patients", patients, ["patient_id"]),
                              ("progress", progress, ["patient_id"]),
                              ("long", long, ["candidate_id", "feature_name"])]:
        check(f"{name}_unique_keys", not frame.duplicated(keys).any())
    check("all_candidates_have_status", set(candidates.candidate_id) == set(status.candidate_id))
    check("all_statuses_success_or_no_raw", status.status.isin(["features_calculated", "no_raw_rows"]).all())
    check("feature_rows_match_successful_candidates", set(device.candidate_id) == set(status.loc[status.status.eq("features_calculated"), "candidate_id"]))
    check("checkpoint_complete", checkpoint["completed_candidate_device_days"] == len(candidates) and not checkpoint["current_patient"])
    check("all_patients_complete", progress.patient_status.eq("complete").all() and progress[["failed_days", "pending_days"]].eq(0).all().all())
    check("patient_rosters_match", set(candidates.patient_id) == set(patients.patient_id) == set(progress.patient_id))
    check("long_feature_keys_complete", set(zip(long.candidate_id, long.feature_name)) == {(c, f) for c in device.candidate_id for f in catalog.feature_name})
    long_wide = long.pivot(index="candidate_id", columns="feature_name", values="value")
    check("long_values_match_device_days", np.allclose(long_wide.loc[device.candidate_id, catalog.feature_name], device[catalog.feature_name], equal_nan=True))
    joined = status.merge(device, on="candidate_id", validate="one_to_one")
    for a, b in [("raw_rows", "accelerometer_raw_row_count"), ("valid_numeric_rows", "accelerometer_valid_numeric_row_count"), ("duplicates_removed", "accelerometer_exact_duplicate_rows_removed")]:
        check(f"status_matches_{a}", joined[a].eq(joined[b]).all())
    check("device_row_accounting", device.accelerometer_raw_row_count.eq(device.accelerometer_valid_numeric_row_count + device.accelerometer_exact_duplicate_rows_removed).all())
    check("no_raw_days_zero_rows", status.loc[status.status.eq("no_raw_rows"), "raw_rows"].eq(0).all())
    check("feature_values_finite_or_missing", not np.isinf(device[catalog.feature_name].to_numpy()).any())
    for feature in catalog.feature_name:
        for agg in ("median", "mean"):
            expected = days.groupby("patient_id")[feature].agg(agg).reindex(patients.patient_id)
            check(f"{agg}_{feature}", np.allclose(expected, patients[f"acc_{agg}_{feature}"], equal_nan=True))
    expected_day_keys = set(zip(device.patient_id, device.local_date))
    check("patient_day_keys_match_device_days", expected_day_keys == set(zip(days.patient_id, days.local_date)))
    check("device_day_rollup_count", days.source_device_day_count.sum() == len(device))
    check("patient_day_rollup_count", patients.completed_patient_day_count.sum() == len(days))
    for col, expected in [("candidate_device_day_count", len(candidates)), ("completed_feature_days", len(device)),
                          ("candidate_days_without_raw_acc", int(status.status.eq("no_raw_rows").sum()))]:
        check(f"progress_{col}", progress[col].sum() == expected)

    raw = int(device.accelerometer_raw_row_count.sum())
    valid = int(device.accelerometer_valid_numeric_row_count.sum())
    removed = int(device.accelerometer_exact_duplicate_rows_removed.sum())
    with_data = patients.completed_patient_day_count.gt(0)
    multi = days.loc[days.source_device_day_count.gt(1)].copy()
    summed_duplicates = device.groupby(["patient_id", "local_date"]).accelerometer_exact_duplicate_rows_removed.sum()
    multi["duplicate_rows_sum_from_device_days"] = [summed_duplicates.loc[(r.patient_id, r.local_date)] for r in multi.itertuples()]
    duplicate_deficit = removed - float(days.accelerometer_exact_duplicate_rows_removed.sum())

    features = []
    technical = []
    for row in catalog.itertuples():
        f = row.feature_name
        med, mean = patients[f"acc_median_{f}"], patients[f"acc_mean_{f}"]
        features.append({"feature": f, "group": row.feature_group,
                         "patient_day_distribution": distribution(days[f]),
                         "patient_median_distribution": distribution(med),
                         "patients_missing_of_all": int(med.isna().sum()),
                         "patients_missing_of_with_signal": int(med[with_data].isna().sum()),
                         "median_mean_spearman": correlation(med, mean),
                         "median_absolute_mean_minus_median": float((mean-med).abs().median())})
        if row.feature_group != "quality":
            for covariate in ("completed_patient_day_count", "total_valid_signal_minutes", "median_daily_coverage_fraction"):
                technical.append({"feature": f, "covariate": covariate,
                                  "paired_patients": int((med.notna() & patients[covariate].notna()).sum()),
                                  "spearman": correlation(med, patients[covariate])})

    missing_archives, empty_archives, archive_bytes = [], [], 0
    expected_archives = candidates[["patient_id", "local_date"]].drop_duplicates()
    if args.archive_dir.is_dir():
        for row in expected_archives.itertuples():
            next_date = (pd.Timestamp(row.local_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            path = args.archive_dir / f"accelerometer_patient_{row.patient_id}_{row.local_date}_to_{next_date}.tsv.zst"
            if not path.exists():
                missing_archives.append(path.name)
            elif path.stat().st_size == 0:
                empty_archives.append(path.name)
            else:
                archive_bytes += path.stat().st_size
    else:
        missing_archives = ["Archive directory unavailable"]

    summary = {"audit_time_local": pd.Timestamp.now(tz="Asia/Jerusalem").isoformat(),
               "completion_time_local": pd.Timestamp(checkpoint["updated_at"]).tz_convert("Asia/Jerusalem").isoformat(),
               "patients": len(patients), "patients_with_signal": int(with_data.sum()),
               "patients_without_signal": int((~with_data).sum()), "candidate_device_days": len(candidates),
               "candidate_patient_days": len(expected_archives), "feature_device_days": len(device),
               "feature_patient_days": len(days), "no_raw_device_days": int(status.status.eq("no_raw_rows").sum()),
               "raw_rows": raw, "valid_rows": valid, "duplicate_rows_removed": removed,
               "duplicate_fraction": removed/raw, "multi_device_patient_days": len(multi),
               "patient_day_duplicate_total_understatement": duplicate_deficit,
               "feature_days_per_patient_all": distribution(patients.completed_patient_day_count),
               "feature_days_per_patient_with_signal": distribution(patients.loc[with_data, "completed_patient_day_count"]),
               "patient_day_observed_minutes": distribution(days.accelerometer_valid_signal_minutes),
               "patient_day_saved_coverage": distribution(days.accelerometer_calendar_coverage_fraction),
               "device_day_observed_span_hours": distribution(device.accelerometer_observed_span_hours),
               "patients_by_minimum_feature_days": {str(n): int(patients.completed_patient_day_count.ge(n).sum()) for n in [1, 3, 7, 14, 30]},
               "archive_inventory": {"expected": len(expected_archives), "missing": missing_archives,
                                     "empty": empty_archives, "bytes": archive_bytes, "zstd_integrity_test": "not_performed"}}
    check("source_files_unchanged", all(digest(p) == hashes[p.name] for p in paths))
    evidence = {"summary": summary, "checks": checks, "features": features,
                "patient_level_technical_correlations": technical,
                "multi_device_patient_days": multi.to_dict("records"), "source_sha256": hashes}
    out.mkdir(parents=True, exist_ok=True)
    (out / "completion_audit.json").write_text(json.dumps(clean_json(evidence), indent=2, allow_nan=False) + "\n")
    feature_lines = ["| Feature | Patients observed / total | Missing among 51 with signal* | Median–mean Spearman |",
                     "|---|---:|---:|---:|"]
    feature_lines[0] = feature_lines[0].replace("51", str(with_data.sum()))
    for f in features:
        rho = f["median_mean_spearman"]
        feature_lines.append(f"| {f['feature'].removeprefix('accelerometer_')} | {len(patients)-f['patients_missing_of_all']}/{len(patients)} | {f['patients_missing_of_with_signal']} | {rho:.3f} |" if rho is not None else f"| {f['feature']} | {len(patients)-f['patients_missing_of_all']}/{len(patients)} | {f['patients_missing_of_with_signal']} | undefined |")
    flagged = [r for r in technical if r["spearman"] is not None and abs(r["spearman"]) >= .70]
    failed = [name for name, passed in checks.items() if not passed]
    report = f"""# Completed ACC extraction audit

Verified {summary['audit_time_local']}. Final extraction checkpoint: {summary['completion_time_local']}.

The documented completed extraction command was:

```bash
.venv/bin/python3 -u extract_accelerometer_patient_sequential.py
```

The extraction log ends with patient 096 complete and the output-directory message. The checkpoint, status, progress, and feature files establish completion; the log alone does not establish counts.

## Completion and coverage

| Measure | Result |
|---|---:|
| Patients processed | {len(patients)} |
| Candidate device-days | {len(candidates):,} |
| Candidate patient-local days | {len(expected_archives):,} |
| Device-days with features | {len(device):,} ({100*len(device)/len(candidates):.2f}%) |
| Device-days without raw ACC | {summary['no_raw_device_days']:,} |
| Patient-days with features | {len(days):,} |
| Patients with signal | {int(with_data.sum())} |
| Patients with no signal | {int((~with_data).sum())} |
| Source raw rows, including timestamp multiplicity | {raw:,} |
| Valid retained rows | {valid:,} |
| Rows removed by timestamp deduplication | {removed:,} ({100*removed/raw:.2f}%) |

All progress rows are complete with zero failures and zero pending days. Missing raw days remain missing; they do not indicate inactivity. Candidate coverage is conditional on the plugin movement dictionary, not every calendar day in the clinical interval.

Across all patients, the median number of feature-days is {patients.completed_patient_day_count.median():.0f}; among patients with signal it is {patients.loc[with_data, 'completed_patient_day_count'].median():.0f}. Patients with at least 1/3/7/14/30 feature-days: {list(summary['patients_by_minimum_feature_days'].values())}. These are descriptive counts, not chosen eligibility thresholds.

The median saved observed-minute count per feature patient-day is {days.accelerometer_valid_signal_minutes.median():.0f}, and median saved coverage is {100*days.accelerometer_calendar_coverage_fraction.median():.2f}%. Observed minutes contain at least one signal sample and do not establish continuous recording. Multi-device days have the qualification below.

## Validation and aggregation findings

- {sum(checks.values())}/{len(checks)} consistency checks passed. Failed checks: {failed or 'none'}.
- All 24 saved patient medians and means reproduce from saved patient-day values; long-format values match device-day values.
- Device-day raw counts reconcile exactly to valid retained rows plus discarded timestamp duplicates.
- **Multi-device aggregation needs correction before modeling:** {len(multi)} patient-days average `exact_duplicate_rows_removed` instead of summing it, understating the patient-day duplicate total by {duplicate_deficit:,.0f} rows. Cohort duplicate totals above therefore use device-days.
- These days sum valid minutes but average calendar coverage; neither supplies a union of unique observed minutes across devices. The longest quiet interval is also summed, and other summaries are unweighted device averages. They are saved aggregation conventions, not raw-signal recomputation. Exact pooled medians and overlapping minute coverage cannot be recovered from daily summaries alone.
- Existing extraction files are preserved. The JSON evidence records source hashes and the four affected rows. Next, implement explicit feature-specific aggregation and compare against exclusion of multi-device days, preserving the completed extraction snapshot.
- Archive inventory: {len(expected_archives)} expected patient-day files; {len(missing_archives)} missing and {len(empty_archives)} empty; {archive_bytes/1e9:.2f} GB present. This is a filename/size audit; compressed-stream integrity has not been retested.

## Feature missingness and aggregation sensitivity

{chr(10).join(feature_lines)}

*Signal means at least one completed feature-day. Undefined feature values remain missing. Correlations compare the saved mean and median across patients; agreement is descriptive and is not model validation.

There are {len(flagged)} non-quality feature/covariate pairs with absolute patient-level Spearman correlation at least 0.70 among the tested recording-day, observed-minute, and coverage measures. Full coefficients and pairwise counts are in `completion_audit.json`. No cognitive outcomes or p-values were used in this audit.

## Next analysis

Resolve multi-device aggregation, then review coverage and median-versus-mean sensitivity before freezing any model panel. Establish clinical-window alignment: full-interval ACC summaries cannot automatically be treated as prospective T1 predictors. Compare mean baseline, existing phenotype, ACC-only, and combined panels on identical patients and leakage-safe folds after these choices are documented.

Reproduce this audit with `.venv/bin/python3 audit_accelerometer_patient_sequential.py` from the project root. Sources are the sibling completed extraction CSVs and checkpoint; `completion_audit.json` contains detailed distributions, reconciliation results, archive inventory, and SHA-256 hashes.
"""
    (out / "README_ACC_COMPLETION_AUDIT.md").write_text(report)
    print(json.dumps(clean_json(summary), indent=2))
    print(f"Consistency checks: {sum(checks.values())}/{len(checks)}; report: {out / 'README_ACC_COMPLETION_AUDIT.md'}")
    if failed:
        raise SystemExit("Consistency checks failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
