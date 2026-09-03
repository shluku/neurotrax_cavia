"""Extract active features across each patient's full T1-to-T2 interval.

Patients with no valid T2 use the documented T1-plus-123-day fallback window.
This phase intentionally excludes the deferred light, barometer, proximity,
and accelerometer sources from extraction and modeling.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd

import phase11_12_extract_midpoint_interval as midpoint
import phase5_extract_selected_features_all_t2_patients as phase5
from phase2_extract_selected_features_all_t1_patients import COGNITIVE_COLUMNS


ROOT = Path(__file__).parent
DATASET_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
SELECTED_PATH = ROOT / "phase2_selected_features.csv"
OUTPUT_NAME = "phase111_full_t1_t2_interval"
FALLBACK_DAYS = 123.0
DEFERRED_TABLES = {"barometer", "light", "bluetooth", "sensor_linear_accelerometer"}
EXCLUDED_SUBJECT_IDS = midpoint.EXCLUDED_SUBJECT_IDS


def output_dir() -> Path:
    return ROOT / "output/analysis_candidates" / OUTPUT_NAME


def path_for(suffix: str) -> Path:
    return output_dir() / f"{OUTPUT_NAME}_{suffix}.csv"


def checkpoint_path() -> Path:
    return output_dir() / f"{OUTPUT_NAME}_checkpoint.jsonl"


def load_patients() -> pd.DataFrame:
    patients = pd.read_csv(DATASET_PATH, dtype=str)
    patients["Subject_ID_D"] = patients["Subject_ID_D"].map(midpoint.normalize_id)
    for column in ["Subject_ID_D", "T1_date_iso", "T2_date_iso"]:
        if column in patients.columns:
            patients[column] = patients[column].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaT": pd.NA})
    patients = patients.dropna(subset=["Subject_ID_D", "T1_date_iso"]).copy()
    patients = patients[~patients["Subject_ID_D"].isin(EXCLUDED_SUBJECT_IDS)].copy()
    return patients.sort_values("Subject_ID_D").drop_duplicates("Subject_ID_D").reset_index(drop=True)


def full_interval(patient: pd.Series, fallback_days: float = FALLBACK_DAYS) -> dict[str, Any] | None:
    t1 = midpoint.local_timestamp(patient.get("T1_date_iso"))
    t2 = midpoint.local_timestamp(patient.get("T2_date_iso"))
    if t1 is None:
        return None
    if t2 is not None and t2 > t1:
        end = t2
        source = "exact_t1_t2_interval"
        interval_days = (t2 - t1).total_seconds() / 86400
    else:
        end = t1 + pd.Timedelta(days=fallback_days)
        source = f"fallback_t1_plus_{fallback_days:.3f}_days_no_valid_t2"
        interval_days = fallback_days
    if end <= t1:
        return None
    return {
        "window_rule": "t1_to_t2_all_available_or_t1_plus_123d_fallback",
        "midpoint_source": source,
        "t1_timestamp": phase5.local_to_ms(t1),
        "t2_timestamp": phase5.local_to_ms(t2) if t2 is not None else pd.NA,
        "midpoint_timestamp": pd.NA,
        "start_ms": phase5.local_to_ms(t1),
        "end_ms": phase5.local_to_ms(end),
        "interval_days_from_t1_to_t2": interval_days,
        "interval_days_in_endpoint": interval_days,
        "fallback_midpoint_days": fallback_days,
    }


def load_existing(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    frame = pd.read_csv(path, dtype=str)
    if "Subject_ID_D" in frame.columns:
        frame["Subject_ID_D"] = frame["Subject_ID_D"].map(midpoint.normalize_id)
    return frame


def append_records(path: Path, records: list[dict[str, Any]]) -> None:
    if records:
        pd.DataFrame(records).to_csv(
            path, mode="a", header=not path.exists() or path.stat().st_size == 0, index=False
        )


def checkpoint_states(path: Path) -> dict[str, str]:
    states: dict[str, str] = {}
    if not path.exists():
        return states
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        patient_id = midpoint.normalize_id(record.get("Subject_ID_D"))
        if patient_id:
            states[patient_id] = str(record.get("status", ""))
    return states


def run(max_patients: int, resume: bool, workers: int, subject_id: str | None) -> None:
    out = output_dir()
    out.mkdir(parents=True, exist_ok=True)
    long_path = path_for("features_long")
    wide_path = path_for("features_wide")
    status_path = path_for("patient_table_status")
    coverage_path = path_for("coverage")
    checkpoint = checkpoint_path()

    selected = pd.read_csv(SELECTED_PATH, dtype=str)
    selected = selected[
        selected["source_table"].isin(midpoint.ALL_SUPPORTED_TABLES)
        & ~selected["source_table"].isin(DEFERRED_TABLES)
    ].copy()
    tables = sorted(selected["source_table"].dropna().unique().tolist())
    patients = load_patients()

    if not resume:
        checkpoint.write_text("", encoding="utf-8")
        for path in (long_path, wide_path, status_path, coverage_path):
            if path.exists():
                path.unlink()
        existing_long = pd.DataFrame()
        existing_status = pd.DataFrame()
        existing_coverage = pd.DataFrame()
        states: dict[str, str] = {}
    else:
        existing_long = load_existing(long_path)
        existing_status = load_existing(status_path)
        existing_coverage = load_existing(coverage_path)
        states = checkpoint_states(checkpoint)

    completed = {patient_id for patient_id, state in states.items() if state == "completed"}
    if not existing_status.empty and "error_message" in existing_status.columns:
        contaminated = existing_status[existing_status["error_message"].fillna("").astype(str).str.strip().ne("")]
        completed -= set(contaminated["Subject_ID_D"].astype(str))
    existing_long = existing_long[existing_long.get("Subject_ID_D", pd.Series(dtype=str)).isin(completed)].copy()
    existing_status = existing_status[existing_status.get("Subject_ID_D", pd.Series(dtype=str)).isin(completed)].copy()
    existing_coverage = existing_coverage[existing_coverage.get("Subject_ID_D", pd.Series(dtype=str)).isin(completed)].copy()
    if resume:
        for frame, path in ((existing_long, long_path), (existing_status, status_path), (existing_coverage, coverage_path)):
            if not frame.empty:
                frame.to_csv(path, index=False)
            elif path.exists():
                path.unlink()

    patients = patients[~patients["Subject_ID_D"].isin(completed)].copy()
    if subject_id:
        patients = patients[patients["Subject_ID_D"].eq(midpoint.normalize_id(subject_id))].copy()
    if max_patients > 0:
        patients = patients.head(max_patients).copy()

    device_map = midpoint.load_device_map_strict()
    long_rows = existing_long.to_dict("records")
    status_rows = existing_status.to_dict("records")
    coverage_rows = existing_coverage.to_dict("records")

    for patient_index, (_, patient) in enumerate(patients.iterrows(), start=1):
        patient_id = patient["Subject_ID_D"]
        window = full_interval(patient)
        device_ids = device_map.get(patient_id, [])
        print(
            f"phase111 patient {patient_index}/{len(patients)} Subject_ID_D={patient_id} "
            f"tables={len(tables)} devices={len(device_ids)}",
            flush=True,
        )
        long_start = len(long_rows)
        status_start = len(status_rows)
        coverage_start = len(coverage_rows)
        worker_count = min(max(1, workers), max(1, len(tables)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(
                    midpoint.extract_table,
                    table_name,
                    selected[selected["source_table"].eq(table_name)],
                    patient_id,
                    device_ids,
                    window,
                )
                for table_name in tables
            ]
            table_results = {}
            for future in futures:
                result = future.result()
                table_results[result["table_name"]] = result

        for table_name in tables:
            result = table_results[table_name]
            selected_for_table = result["selected_for_table"]
            features = result["features"]
            rows = result["rows"]
            table_status = result["table_status"]
            computed_status = result["computed_status"]
            error_message = result["error_message"]
            coverage_rows.extend(result["coverage_rows"])
            status_rows.append(
                {
                    "Subject_ID_D": patient_id,
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "T2_date_iso": patient.get("T2_date_iso", ""),
                    "table_name": table_name,
                    "table_status": table_status,
                    "feature_status": computed_status,
                    "device_ids_available": ";".join(device_ids),
                    "device_ids_used": ";".join(device_ids if rows else []),
                    "window_rule": window.get("window_rule", "") if window else "",
                    "midpoint_source": window.get("midpoint_source", "") if window else "",
                    "fallback_midpoint_days": window.get("fallback_midpoint_days", FALLBACK_DAYS) if window else FALLBACK_DAYS,
                    "t1_timestamp": window.get("t1_timestamp", pd.NA) if window else pd.NA,
                    "t2_timestamp": window.get("t2_timestamp", pd.NA) if window else pd.NA,
                    "midpoint_timestamp": pd.NA,
                    "interval_days_from_t1_to_t2": window.get("interval_days_from_t1_to_t2", pd.NA) if window else pd.NA,
                    "interval_days_in_endpoint": window.get("interval_days_in_endpoint", pd.NA) if window else pd.NA,
                    "window_start_ms": window.get("start_ms", pd.NA) if window else pd.NA,
                    "window_end_ms": window.get("end_ms", pd.NA) if window else pd.NA,
                    "window_start_local": phase5.ms_to_local(window.get("start_ms")) if window else pd.NA,
                    "window_end_local": phase5.ms_to_local(window.get("end_ms")) if window else pd.NA,
                    "rows_in_window": len(rows),
                    "error_message": error_message,
                }
            )
            for _, feature in selected_for_table.iterrows():
                value = features.get(str(feature["feature_name"]), pd.NA)
                numeric_value = pd.to_numeric(value, errors="coerce")
                long_rows.append(
                    {
                        "Subject_ID_D": patient_id,
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                        "T2_date_iso": patient.get("T2_date_iso", ""),
                        "table_name": table_name,
                        "feature_name": feature["feature_name"],
                        "feature_family": feature.get("feature_family", ""),
                        "feature_value": numeric_value if not pd.isna(numeric_value) else pd.NA,
                        "feature_status": midpoint.feature_status(value, table_status, computed_status),
                        "window_rule": window.get("window_rule", "") if window else "",
                        "midpoint_source": window.get("midpoint_source", "") if window else "",
                        "fallback_midpoint_days": window.get("fallback_midpoint_days", FALLBACK_DAYS) if window else FALLBACK_DAYS,
                        "window_start_local": phase5.ms_to_local(window.get("start_ms")) if window else pd.NA,
                        "window_end_local": phase5.ms_to_local(window.get("end_ms")) if window else pd.NA,
                        "interval_days_in_endpoint": window.get("interval_days_in_endpoint", pd.NA) if window else pd.NA,
                        "rows_in_window": len(rows),
                        "device_ids_used": ";".join(device_ids if rows else []),
                        "error_message": error_message,
                    }
                )

        patient_statuses = [
            row["table_status"] for row in status_rows[status_start:] if row.get("Subject_ID_D") == patient_id
        ]
        checkpoint_status = "completed" if not set(patient_statuses).intersection({"error", "retryable_error"}) else "needs_retry"
        with checkpoint.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"Subject_ID_D": patient_id, "status": checkpoint_status}) + "\n")
        append_records(long_path, long_rows[long_start:])
        append_records(status_path, status_rows[status_start:])
        append_records(coverage_path, coverage_rows[coverage_start:])
        midpoint.build_wide(load_patients(), pd.DataFrame(long_rows)).to_csv(wide_path, index=False)

    final_long = pd.DataFrame(long_rows)
    midpoint.build_wide(load_patients(), final_long).to_csv(wide_path, index=False)
    (out / f"README_{OUTPUT_NAME}.md").write_text(
        "# Phase 111 Full T1-to-T2 Interval Ridge Cohort\n\n"
        "This exploratory cohort uses all available active-feature data in the half-open interval `[T1, T2)`. "
        "Patients without a valid T2 use `[T1, T1+123 days)` as the documented fallback window. "
        "Light, barometer, Bluetooth-proximity, and sensor-linear-accelerometer features are deferred.\n\n"
        "The target is the mean of the observed T1 and T2 score when both exist, or the observed T1 score alone when T2 is unavailable. "
        "For two observations, the standard median is identical to this mean.\n",
        encoding="utf-8",
    )
    final_status = pd.DataFrame(status_rows)
    print(f"phase111_patients_processed: {final_status['Subject_ID_D'].nunique() if not final_status.empty else 0}", flush=True)
    if not final_status.empty:
        print(final_status["table_status"].value_counts(dropna=False).to_string(), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract active features across full T1-to-T2 intervals for Phase 111.")
    parser.add_argument("--max-patients", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--subject-id")
    args = parser.parse_args()
    run(args.max_patients, args.resume, args.workers, args.subject_id)


if __name__ == "__main__":
    main()
