"""Build a local patient/device accelerometer coverage and mapping audit.

This report deliberately does not scan the multi-billion-row SQL ``accelerometer``
table. It combines the completed hardware inventory, the local raw linear-ACC
inventory, and the existing bounded raw-ACC probes. General raw ACC remains
explicitly marked as not fully audited until it is exported locally.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).parent
HARDWARE_DIR = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/device_hardware_timeline"
OUT_DIR = HARDWARE_DIR / "data_coverage"
CROSSWALK_PATH = HARDWARE_DIR / "patient_device_crosswalk.csv"
TIMELINE_PATH = HARDWARE_DIR / "accelerometer_device_hardware_timeline.csv"
SENSOR_SUMMARY_PATH = HARDWARE_DIR / "sensor_device_summary_long.csv"
RAW_LINEAR_SUMMARY_PATH = HARDWARE_DIR / "raw_linear_device_summary.csv"
UNMATCHED_PATH = HARDWARE_DIR / "unmatched_device_ids.csv"
COGNITIVE_CANDIDATES_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
RAW_ACC_PROBE_ROOT = ROOT / "output/analysis_candidates/phase2_accelerometer_framework"
CUTOFF = pd.Timestamp("2025-12-31 00:00:00", tz="Asia/Jerusalem")
CUTOFF_LABEL = "2025-12-30 inclusive"
TIMEZONE = "Asia/Jerusalem"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def clean(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "<na>"} else text


def truthy(value: Any) -> bool:
    return clean(value).lower() in {"yes", "true", "1"}


def numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(0, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(0)


def parse_timestamp_series(values: pd.Series) -> pd.Series:
    return pd.to_datetime(pd.Series(values).replace("", pd.NA), errors="coerce", utc=True)


def local_min_max(values: pd.Series) -> tuple[str, str]:
    parsed = parse_timestamp_series(values)
    parsed = parsed.dropna()
    if parsed.empty:
        return "", ""
    return (
        parsed.min().tz_convert(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S%z"),
        parsed.max().tz_convert(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S%z"),
    )


def local_min_date(values: pd.Series) -> str:
    first, _ = local_min_max(values)
    return first[:10] if first else ""


def unique_join(values: pd.Series, limit: int = 12) -> str:
    items = sorted({clean(value) for value in values if clean(value)})
    if len(items) > limit:
        return "; ".join(items[:limit]) + f"; ... (+{len(items) - limit} more)"
    return "; ".join(items)


def current_81_patient_ids() -> list[str]:
    candidates = read_csv(COGNITIVE_CANDIDATES_PATH)
    if candidates.empty or "Subject_ID_D" not in candidates:
        raise FileNotFoundError(f"Cannot identify the 81-person cohort: {COGNITIVE_CANDIDATES_PATH}")
    ids = candidates["Subject_ID_D"].map(clean)
    return sorted({value for value in ids if value and value != "001"})


def load_crosswalk() -> pd.DataFrame:
    crosswalk = read_csv(CROSSWALK_PATH)
    required = {"device_id", "patient_id", "cohort_membership"}
    missing = required - set(crosswalk.columns)
    if missing:
        raise ValueError(f"Crosswalk is missing columns: {sorted(missing)}")
    crosswalk["device_id"] = crosswalk["device_id"].map(clean)
    crosswalk = crosswalk[crosswalk["device_id"].ne("")].copy()
    return crosswalk.drop_duplicates("device_id", keep="first")


def probe_raw_acc_evidence() -> pd.DataFrame:
    """Collect only existing bounded raw-ACC evidence; do not infer no-data."""
    records: list[dict[str, Any]] = []
    for path in sorted(RAW_ACC_PROBE_ROOT.rglob("median_day_minute_raw_samples.csv")):
        frame = read_csv(path)
        if frame.empty or "table_name" not in frame or "device_id" not in frame:
            continue
        frame = frame[frame["table_name"].astype(str).eq("accelerometer")].copy()
        for device_id, group in frame.groupby(frame["device_id"].map(clean)):
            if not device_id:
                continue
            first, last = local_min_max(group.get("timestamp_local", pd.Series(dtype=str)))
            records.append(
                {
                    "device_id": device_id,
                    "raw_acc_probe_evidence_level": "bounded_SQL_minute_sample",
                    "raw_acc_probe_sources": path.parent.name,
                    "raw_acc_probe_sample_rows": len(group),
                    "raw_acc_probe_first_seen_local": first,
                    "raw_acc_probe_last_seen_local": last,
                }
            )

    expanded = read_csv(RAW_ACC_PROBE_ROOT / "accelerometer_raw_phase2a_sample_rows_expanded.csv")
    if not expanded.empty and "device_id" in expanded:
        for device_id, group in expanded.groupby(expanded["device_id"].map(clean)):
            if not device_id:
                continue
            first, last = local_min_max(group.get("local_datetime", pd.Series(dtype=str)))
            records.append(
                {
                    "device_id": device_id,
                    "raw_acc_probe_evidence_level": "bounded_SQL_targeted_sample",
                    "raw_acc_probe_sources": "accelerometer_raw_phase2a_sample_rows_expanded.csv",
                    "raw_acc_probe_sample_rows": len(group),
                    "raw_acc_probe_first_seen_local": first,
                    "raw_acc_probe_last_seen_local": last,
                }
            )

    status_paths = list(RAW_ACC_PROBE_ROOT.rglob("phase3_accelerometer_24h_all_t1_streaming_patient_status.csv"))
    for path in status_paths:
        frame = read_csv(path)
        if frame.empty or "device_id" not in frame or "table_status" not in frame:
            continue
        calculated = frame[frame["table_status"].astype(str).eq("calculated")].copy()
        for _, row in calculated.iterrows():
            device_id = clean(row.get("device_id"))
            if not device_id:
                continue
            records.append(
                {
                    "device_id": device_id,
                    "raw_acc_probe_evidence_level": "bounded_SQL_24h_download",
                    "raw_acc_probe_sources": path.parent.name,
                    "raw_acc_probe_sample_rows": clean(row.get("raw_rows_downloaded")),
                    "raw_acc_probe_first_seen_local": clean(row.get("window_start_local")),
                    "raw_acc_probe_last_seen_local": clean(row.get("window_end_local")),
                }
            )

    manifest = read_csv(RAW_ACC_PROBE_ROOT / "raw_24h_pilot/accelerometer_24h_pilot_manifest.csv")
    if not manifest.empty and "device_id" in manifest:
        complete = manifest[manifest.get("status", pd.Series(index=manifest.index)).astype(str).eq("download_complete")]
        for _, row in complete.iterrows():
            device_id = clean(row.get("device_id"))
            if not device_id:
                continue
            records.append(
                {
                    "device_id": device_id,
                    "raw_acc_probe_evidence_level": "bounded_SQL_24h_download",
                    "raw_acc_probe_sources": "accelerometer_24h_pilot_manifest.csv",
                    "raw_acc_probe_sample_rows": clean(row.get("downloaded_rows")),
                    "raw_acc_probe_first_seen_local": clean(row.get("candidate_window_start_local")),
                    "raw_acc_probe_last_seen_local": clean(row.get("candidate_window_end_local")),
                }
            )

    if not records:
        return pd.DataFrame(
            columns=[
                "device_id",
                "raw_acc_probe_evidence_level",
                "raw_acc_probe_sources",
                "raw_acc_probe_sample_rows",
                "raw_acc_probe_first_seen_local",
                "raw_acc_probe_last_seen_local",
            ]
        )

    probes = pd.DataFrame(records)
    probes["raw_acc_probe_sample_rows_numeric"] = pd.to_numeric(
        probes["raw_acc_probe_sample_rows"], errors="coerce"
    ).fillna(0)
    output: list[dict[str, Any]] = []
    for device_id, group in probes.groupby("device_id"):
        first, last = local_min_max(group["raw_acc_probe_first_seen_local"].tolist() + group["raw_acc_probe_last_seen_local"].tolist())
        output.append(
            {
                "device_id": device_id,
                "raw_acc_probe_evidence_level": unique_join(group["raw_acc_probe_evidence_level"]),
                "raw_acc_probe_sources": unique_join(group["raw_acc_probe_sources"]),
                "raw_acc_probe_sample_rows": int(group["raw_acc_probe_sample_rows_numeric"].max()),
                "raw_acc_probe_first_seen_local": first,
                "raw_acc_probe_last_seen_local": last,
            }
        )
    return pd.DataFrame(output)


def add_source_metadata(crosswalk: pd.DataFrame, sensor_summary: pd.DataFrame) -> pd.DataFrame:
    if sensor_summary.empty:
        return crosswalk.copy()
    frame = sensor_summary.merge(
        crosswalk[["device_id", "patient_id", "belongs_to_81_person_cohort", "cohort_membership"]],
        on="device_id",
        how="left",
    )
    frame["source_table"] = frame["source_table"].map(clean)
    rows: list[dict[str, Any]] = []
    for (patient_id, source_table), group in frame.groupby(["patient_id", "source_table"], dropna=False):
        if not clean(patient_id) or not clean(source_table):
            continue
        first, _ = local_min_max(group["metadata_first_seen_local"])
        _, last = local_min_max(group["metadata_last_seen_local"])
        rows.append(
            {
                "patient_id": clean(patient_id),
                "source_table": clean(source_table),
                "metadata_device_count": int(group["device_id"].nunique()),
                "metadata_rows": int(numeric_series(group, "metadata_rows").sum()),
                "metadata_first_seen_local": first,
                "metadata_last_seen_local": last,
                "metadata_sensor_names": unique_join(group.get("sensor_names", pd.Series(dtype=str))),
                "metadata_sensor_vendors": unique_join(group.get("sensor_vendors", pd.Series(dtype=str))),
                "metadata_sensor_types": unique_join(group.get("sensor_types", pd.Series(dtype=str))),
            }
        )
    return pd.DataFrame(rows)


def build_outputs() -> None:
    for path in [CROSSWALK_PATH, TIMELINE_PATH, SENSOR_SUMMARY_PATH, RAW_LINEAR_SUMMARY_PATH]:
        if not path.exists():
            raise FileNotFoundError(f"Missing prerequisite: {path}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    crosswalk = load_crosswalk()
    active_ids = current_81_patient_ids()
    active = crosswalk[crosswalk["belongs_to_81_person_cohort"].map(truthy)].copy()
    active = active[active["patient_id"].isin(active_ids)].copy()
    if active["patient_id"].nunique() != 81:
        raise ValueError(f"Expected 81 active patients in crosswalk, found {active['patient_id'].nunique()}")

    sensor_summary = read_csv(SENSOR_SUMMARY_PATH)
    raw_linear = read_csv(RAW_LINEAR_SUMMARY_PATH)
    raw_linear["device_id"] = raw_linear.get("device_id", pd.Series(dtype=str)).map(clean)
    raw_linear["raw_linear_accelerometer_rows_numeric"] = numeric_series(raw_linear, "raw_linear_accelerometer_rows")
    raw_linear["raw_linear_first_ts"] = parse_timestamp_series(raw_linear.get("raw_linear_first_seen_local", pd.Series(dtype=str)))
    raw_linear["raw_linear_last_ts"] = parse_timestamp_series(raw_linear.get("raw_linear_last_seen_local", pd.Series(dtype=str)))
    probes = probe_raw_acc_evidence()

    coverage = crosswalk.merge(
        sensor_summary[["device_id", "source_table", "metadata_rows", "metadata_first_seen_local", "metadata_last_seen_local", "sensor_names", "sensor_vendors", "sensor_types"]],
        on="device_id",
        how="left",
    )
    source_pivot = coverage.pivot_table(
        index="device_id",
        columns="source_table",
        values="metadata_rows",
        aggfunc="sum",
    ).reset_index() if not coverage.empty else pd.DataFrame(columns=["device_id"])
    for source in ["sensor_accelerometer", "sensor_linear_accelerometer"]:
        source_col = f"{source}_metadata_rows"
        if source in source_pivot:
            source_pivot = source_pivot.rename(columns={source: source_col})
        elif source_col not in source_pivot:
            source_pivot[source_col] = 0
    source_dates = []
    for device_id, group in coverage.groupby("device_id"):
        row = {"device_id": device_id}
        for source in ["sensor_accelerometer", "sensor_linear_accelerometer"]:
            subset = group[group["source_table"].eq(source)]
            first, last = local_min_max(subset["metadata_first_seen_local"])
            row[f"{source}_first_seen_local"] = first
            row[f"{source}_last_seen_local"] = last
            row[f"{source}_metadata_device_present"] = "yes" if not subset.empty else "no"
        source_dates.append(row)
    source_dates_df = pd.DataFrame(source_dates)

    coverage = crosswalk.merge(raw_linear, on="device_id", how="left", suffixes=("", "_raw_linear"))
    coverage = coverage.merge(probes, on="device_id", how="left")
    coverage = coverage.merge(source_dates_df, on="device_id", how="left")
    for source in ["sensor_accelerometer", "sensor_linear_accelerometer"]:
        coverage[f"{source}_first_seen_local"] = coverage[f"{source}_first_seen_local"].fillna("")
        coverage[f"{source}_last_seen_local"] = coverage[f"{source}_last_seen_local"].fillna("")
        coverage[f"{source}_metadata_device_present"] = coverage[f"{source}_metadata_device_present"].fillna("no")
    coverage["raw_linear_accelerometer_rows"] = numeric_series(coverage, "raw_linear_accelerometer_rows")
    coverage["raw_linear_accelerometer_available"] = coverage["raw_linear_accelerometer_rows"].gt(0).map({True: "yes", False: "no"})
    coverage["raw_acc_probe_available"] = coverage["raw_acc_probe_evidence_level"].fillna("").ne("").map({True: "yes", False: "no"})
    coverage["raw_acc_full_audit_status"] = "not_fully_scanned_sql_accelerometer_table"
    coverage["raw_acc_no_data_conclusion_allowed"] = "yes"
    coverage["metadata_or_raw_linear_first_seen_local"] = coverage.apply(
        lambda row: min(
            [value for value in [
                row.get("sensor_accelerometer_first_seen_local", ""),
                row.get("sensor_linear_accelerometer_first_seen_local", ""),
                row.get("raw_linear_first_seen_local", ""),
            ] if clean(value)] or [""]
        ),
        axis=1,
    )
    coverage["local_evidence_before_2025_12_30"] = coverage.apply(
        lambda row: "yes" if any(
            ts < CUTOFF
            for ts in [
                parse_timestamp_series(pd.Series([row.get("sensor_accelerometer_first_seen_local", "")])).iloc[0],
                parse_timestamp_series(pd.Series([row.get("sensor_linear_accelerometer_first_seen_local", "")])).iloc[0],
                row.get("raw_linear_first_ts", pd.NaT),
                parse_timestamp_series(pd.Series([row.get("raw_acc_probe_first_seen_local", "")])).iloc[0],
            ]
            if pd.notna(ts)
        ) else "no",
        axis=1,
    )
    coverage["local_evidence_status"] = coverage.apply(
        lambda row: "raw_ACC_probe_and_linear_ACC" if row["raw_acc_probe_available"] == "yes" and row["raw_linear_accelerometer_available"] == "yes" else
        "raw_ACC_probe_only" if row["raw_acc_probe_available"] == "yes" else
        "raw_linear_ACC_only" if row["raw_linear_accelerometer_available"] == "yes" else
        "sensor_metadata_only" if row["sensor_accelerometer_metadata_device_present"] == "yes" or row["sensor_linear_accelerometer_metadata_device_present"] == "yes" else
        "no_local_evidence_in_completed_inventory",
        axis=1,
    )
    coverage = coverage.sort_values(["belongs_to_81_person_cohort", "patient_id", "device_id"], ascending=[False, True, True])
    coverage.to_csv(OUT_DIR / "patient_device_accelerometer_evidence.csv", index=False)

    metadata_by_patient = add_source_metadata(active, sensor_summary)
    patient_rows: list[dict[str, Any]] = []
    for patient_id in active_ids:
        patient_devices = active[active["patient_id"].eq(patient_id)]
        patient_coverage = coverage[coverage["patient_id"].eq(patient_id)]
        acc_metadata = metadata_by_patient[(metadata_by_patient["patient_id"].eq(patient_id)) & metadata_by_patient["source_table"].eq("sensor_accelerometer")]
        linear_metadata = metadata_by_patient[(metadata_by_patient["patient_id"].eq(patient_id)) & metadata_by_patient["source_table"].eq("sensor_linear_accelerometer")]
        def meta_value(frame: pd.DataFrame, column: str, default: Any = "") -> Any:
            return frame.iloc[0][column] if not frame.empty and column in frame else default
        probe_devices = patient_coverage[patient_coverage["raw_acc_probe_available"].eq("yes")]
        patient_rows.append(
            {
                "patient_id": patient_id,
                "mapped_device_count": int(patient_devices["device_id"].nunique()),
                "observed_mapped_device_count": int(
                    patient_devices["hardware_observation_status"].astype(str).eq("observed_in_local_hardware_timeline").sum()
                ),
                "mapped_device_ids": ";".join(patient_devices["device_id"].astype(str)),
                "general_acc_metadata_device_count": int(meta_value(acc_metadata, "metadata_device_count", 0)),
                "general_acc_metadata_rows": int(float(meta_value(acc_metadata, "metadata_rows", 0) or 0)),
                "general_acc_metadata_first_seen_local": meta_value(acc_metadata, "metadata_first_seen_local"),
                "general_acc_metadata_last_seen_local": meta_value(acc_metadata, "metadata_last_seen_local"),
                "general_acc_sensor_names": meta_value(acc_metadata, "metadata_sensor_names"),
                "general_acc_sensor_vendors": meta_value(acc_metadata, "metadata_sensor_vendors"),
                "linear_acc_metadata_device_count": int(meta_value(linear_metadata, "metadata_device_count", 0)),
                "linear_acc_metadata_rows": int(float(meta_value(linear_metadata, "metadata_rows", 0) or 0)),
                "linear_acc_metadata_first_seen_local": meta_value(linear_metadata, "metadata_first_seen_local"),
                "linear_acc_metadata_last_seen_local": meta_value(linear_metadata, "metadata_last_seen_local"),
                "linear_acc_sensor_names": meta_value(linear_metadata, "metadata_sensor_names"),
                "linear_acc_sensor_vendors": meta_value(linear_metadata, "metadata_sensor_vendors"),
                "raw_linear_acc_device_count": int(patient_coverage["raw_linear_accelerometer_available"].eq("yes").sum()),
                "raw_linear_acc_rows": int(numeric_series(patient_coverage, "raw_linear_accelerometer_rows").sum()),
                "raw_linear_acc_first_seen_local": local_min_max(patient_coverage["raw_linear_first_seen_local"])[0],
                "raw_linear_acc_last_seen_local": local_min_max(patient_coverage["raw_linear_last_seen_local"])[1],
                "confirmed_raw_acc_probe_device_count": int(probe_devices["device_id"].nunique()),
                "confirmed_raw_acc_probe_first_seen_local": local_min_max(probe_devices["raw_acc_probe_first_seen_local"])[0],
                "confirmed_raw_acc_probe_last_seen_local": local_min_max(probe_devices["raw_acc_probe_last_seen_local"])[1],
                "has_general_acc_metadata": "yes" if not acc_metadata.empty else "no",
                "has_linear_acc_metadata": "yes" if not linear_metadata.empty else "no",
                "has_raw_linear_acc": "yes" if (numeric_series(patient_coverage, "raw_linear_accelerometer_rows") > 0).any() else "no",
                "has_confirmed_raw_acc_probe": "yes" if not probe_devices.empty else "no",
                "has_any_completed_accelerometer_evidence": "yes" if any([
                    not acc_metadata.empty,
                    not linear_metadata.empty,
                    not probe_devices.empty,
                    (numeric_series(patient_coverage, "raw_linear_accelerometer_rows") > 0).any(),
                ]) else "no",
                "mapped_devices_with_local_evidence_through_2025_12_30": int(patient_coverage["local_evidence_before_2025_12_30"].eq("yes").sum()),
                "has_local_evidence_through_2025_12_30": "yes" if patient_coverage["local_evidence_before_2025_12_30"].eq("yes").any() else "no",
                "raw_acc_full_audit_status": "not_fully_scanned_sql_accelerometer_table",
            }
        )
    patient_summary = pd.DataFrame(patient_rows)
    patient_summary.to_csv(OUT_DIR / "patient_accelerometer_data_summary.csv", index=False)

    unmatched = coverage[coverage["cohort_membership"].eq("unmatched_device_id")].copy()
    unmatched_hints = read_csv(UNMATCHED_PATH)
    if not unmatched_hints.empty:
        unmatched = unmatched.merge(unmatched_hints, on="device_id", how="left", suffixes=("", "_crosswalk_audit"))
    unmatched["unmatched_device_interpretation"] = unmatched.apply(
        lambda row: "confirmed_raw_ACC_in_existing_probe; investigate patient linkage" if row["raw_acc_probe_available"] == "yes" else
        "raw_linear_ACC_present; investigate patient linkage" if row["raw_linear_accelerometer_available"] == "yes" else
        "sensor_metadata_present_only; investigate label/device history",
        axis=1,
    )
    unmatched_cols = [
        "device_id", "patient_id_from_label_map", "mapping_source_label", "hardware_observation_status",
        "first_observed_date", "last_observed_date", "observation_sources", "general_accelerometer_configuration",
        "linear_accelerometer_configuration", "raw_linear_accelerometer_rows", "raw_linear_first_seen_local",
        "raw_linear_last_seen_local", "raw_acc_probe_available", "raw_acc_probe_evidence_level",
        "raw_acc_probe_first_seen_local", "raw_acc_probe_last_seen_local", "local_evidence_before_2025_12_30",
        "unmatched_device_interpretation",
    ]
    unmatched = unmatched[[column for column in unmatched_cols if column in unmatched.columns]].sort_values("device_id")
    unmatched.to_csv(OUT_DIR / "unmatched_device_data_investigation.csv", index=False)

    cutoff = coverage[coverage["patient_id"].isin(active_ids)].copy()
    cutoff_cols = [
        "patient_id", "device_id", "number_of_devices_for_patient", "observation_sources", "first_observed_date",
        "last_observed_date", "sensor_accelerometer_first_seen_local", "sensor_accelerometer_last_seen_local",
        "sensor_linear_accelerometer_first_seen_local", "sensor_linear_accelerometer_last_seen_local",
        "raw_linear_first_seen_local", "raw_linear_last_seen_local", "raw_linear_accelerometer_rows",
        "raw_acc_probe_available", "raw_acc_probe_first_seen_local", "raw_acc_probe_last_seen_local",
        "local_evidence_before_2025_12_30", "local_evidence_status",
    ]
    cutoff = cutoff[[column for column in cutoff_cols if column in cutoff.columns]].sort_values(["patient_id", "device_id"])
    cutoff.to_csv(OUT_DIR / "mapped_device_data_through_2025_12_30.csv", index=False)

    mapped = coverage[coverage["patient_id"].isin(active_ids)].copy()
    summary_rows = [
        {"metric": "active_81_person_cohort_patients", "value": 81},
        {"metric": "mapped_device_ids_for_active_81", "value": int(mapped["device_id"].nunique())},
        {"metric": "active_81_patients_with_general_acc_metadata", "value": int(patient_summary["has_general_acc_metadata"].eq("yes").sum())},
        {"metric": "active_81_patients_with_linear_acc_metadata", "value": int(patient_summary["has_linear_acc_metadata"].eq("yes").sum())},
        {"metric": "active_81_patients_with_raw_linear_acc", "value": int(patient_summary["has_raw_linear_acc"].eq("yes").sum())},
        {"metric": "active_81_patients_with_confirmed_raw_acc_probe", "value": int(patient_summary["has_confirmed_raw_acc_probe"].eq("yes").sum())},
        {"metric": "mapped_devices_with_raw_linear_acc", "value": int(mapped["raw_linear_accelerometer_available"].eq("yes").sum())},
        {"metric": "mapped_devices_with_confirmed_raw_acc_probe", "value": int(mapped["raw_acc_probe_available"].eq("yes").sum())},
        {"metric": "mapped_devices_with_any_local_evidence_through_2025_12_30", "value": int(mapped["local_evidence_before_2025_12_30"].eq("yes").sum())},
        {"metric": "active_81_patients_with_local_evidence_through_2025_12_30", "value": int(patient_summary["has_local_evidence_through_2025_12_30"].eq("yes").sum())},
        {"metric": "unmatched_observed_devices", "value": int(len(unmatched))},
        {"metric": "unmatched_devices_with_raw_linear_acc", "value": int(unmatched.get("raw_linear_accelerometer_rows", pd.Series(dtype=str)).pipe(pd.to_numeric, errors="coerce").fillna(0).gt(0).sum())},
        {"metric": "unmatched_devices_with_confirmed_raw_acc_probe", "value": int(unmatched.get("raw_acc_probe_available", pd.Series(dtype=str)).eq("yes").sum())},
        {"metric": "raw_acc_full_scan_completed", "value": "no"},
    ]
    pd.DataFrame(summary_rows).to_csv(OUT_DIR / "accelerometer_data_coverage_summary.csv", index=False)

    metadata_patient_summary = add_source_metadata(active, sensor_summary)
    metadata_patient_summary.to_csv(OUT_DIR / "active_patient_accelerometer_metadata_summary.csv", index=False)
    probes.to_csv(OUT_DIR / "confirmed_raw_acc_probe_devices.csv", index=False)

    readme = f"""# Patient Accelerometer Data Coverage and Mapping Audit

This local audit answers three questions:

1. Which of the active 81 patients have accelerometer evidence, and when was it observed?
2. Which observed device IDs are not mapped to a current patient, and do they contain data that should be investigated?
3. How many mapped devices/patients have local evidence from the first project date through **{CUTOFF_LABEL}**?

## Evidence layers

- **General ACC metadata**: `sensor_accelerometer` hardware metadata. It identifies a device and its sensor configuration, but it is not a count of raw movement rows.
- **Linear ACC metadata**: `sensor_linear_accelerometer` hardware metadata.
- **Raw linear ACC**: exact device-level row counts and first/last dates from the completed local Parquet inventory.
- **Confirmed raw ACC probes**: devices observed in the existing bounded SQL minute samples or the completed bounded 24-hour pilot. This is confirmation of raw ACC existence, not a full-table audit.

The 81-person cohort is the current cognitive candidate set with Subject `001` excluded. Patient rows are retained even when the completed local inventory has no evidence for a patient.

## Cutoff definition

The cutoff is a half-open local-time boundary at `2025-12-31 00:00:00` in `{TIMEZONE}`. Therefore, "through 2025-12-30" includes all evidence before that boundary.

## Main outputs

- `patient_accelerometer_data_summary.csv`: exactly one row per active patient.
- `patient_device_accelerometer_evidence.csv`: one row per mapped or unmatched observed device, with source-specific evidence and dates.
- `unmatched_device_data_investigation.csv`: observed device IDs without a current numeric patient mapping.
- `mapped_device_data_through_2025_12_30.csv`: active-cohort device-level cutoff view.
- `accelerometer_data_coverage_summary.csv`: headline counts.
- `active_patient_accelerometer_metadata_summary.csv`: source-table metadata summarized by patient.
- `confirmed_raw_acc_probe_devices.csv`: raw ACC devices confirmed by existing bounded probes.

## Critical interpretation boundary

The SQL `accelerometer` table was not fully scanned in this audit because it is a multi-billion-row table with a timestamp-first index and per-device aggregation is too slow and unstable for an unbounded remote pass. Consequently, a patient or device marked `raw_acc_probe_available=no` is **not** evidence of no raw ACC data. It means no confirmation exists in the completed probes. The next definitive step is a local raw-ACC export/Parquet conversion, after which this same report can be rerun with exact raw ACC counts and dates.

No source SQL tables, source Parquet files, mappings, or patient-level modeling datasets were modified.
"""
    (OUT_DIR / "README_accelerometer_patient_data_coverage.md").write_text(readme, encoding="utf-8")

    print(f"active_81_patients={patient_summary['patient_id'].nunique()}")
    print(f"mapped_devices_active_81={mapped['device_id'].nunique()}")
    print(f"patients_general_acc_metadata={patient_summary['has_general_acc_metadata'].eq('yes').sum()}")
    print(f"patients_linear_acc_metadata={patient_summary['has_linear_acc_metadata'].eq('yes').sum()}")
    print(f"patients_raw_linear_acc={patient_summary['has_raw_linear_acc'].eq('yes').sum()}")
    print(f"patients_confirmed_raw_acc_probe={patient_summary['has_confirmed_raw_acc_probe'].eq('yes').sum()}")
    print(f"mapped_devices_through_2025_12_30={mapped['local_evidence_before_2025_12_30'].eq('yes').sum()}")
    print(f"patients_through_2025_12_30={patient_summary['has_local_evidence_through_2025_12_30'].eq('yes').sum()}")
    print(f"unmatched_devices={len(unmatched)}")


if __name__ == "__main__":
    build_outputs()
