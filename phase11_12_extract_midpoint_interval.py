"""Extract selected features from patient-level intervals split at the T1/T2 midpoint.

Phase 11 uses the interval from T1 to the midpoint between T1 and T2. Patients
without a valid T2 use the documented 123-day fallback midpoint. Phase 12 uses
the second half of the same interval, from midpoint to T2, and therefore
requires both valid T1 and T2 dates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

import phase5_extract_selected_features_all_t2_patients as phase5
from phase2_extract_selected_features_all_t1_patients import (
    COGNITIVE_COLUMNS,
    EXCLUDED_COHORT_SUBJECT_IDS,
    feature_status,
    is_retryable_db_error,
    load_device_map_strict,
)


ROOT = Path(__file__).parent
DATASET_PATH = ROOT / "output/analysis_candidates/cognitive_candidates_all.csv"
SELECTED_PATH = ROOT / "phase2_selected_features.csv"
FALLBACK_MIDPOINT_DAYS = 123
ENDPOINTS = {"t1": "phase11_midpoint_t1_baseline", "t2": "phase12_midpoint_t2_decline"}
ALL_SUPPORTED_TABLES = sorted(phase5.ALL_SUPPORTED_TABLES)
EXCLUDED_SUBJECT_IDS = EXCLUDED_COHORT_SUBJECT_IDS | {"001"}


def endpoint_dir(endpoint: str) -> Path:
    return ROOT / "output/analysis_candidates" / ENDPOINTS[endpoint]


def path_for(endpoint: str, suffix: str) -> Path:
    return endpoint_dir(endpoint) / f"{ENDPOINTS[endpoint]}_{suffix}.csv"


def checkpoint_path(endpoint: str) -> Path:
    return endpoint_dir(endpoint) / f"{ENDPOINTS[endpoint]}_checkpoint.jsonl"


def normalize_id(value: Any) -> str:
    return phase5.normalize_subject_id_d(value)


def valid_value(value: Any) -> bool:
    return not pd.isna(value) and str(value).strip().lower() not in {"", "nan", "none", "nat"}


def local_timestamp(value: Any) -> pd.Timestamp | None:
    if not valid_value(value):
        return None
    timestamp = pd.Timestamp(str(value))
    if timestamp.tzinfo is None:
        return timestamp.tz_localize(phase5.TZ)
    return timestamp.tz_convert(phase5.TZ)


def load_patients(endpoint: str) -> pd.DataFrame:
    patients = pd.read_csv(DATASET_PATH, dtype=str)
    patients["Subject_ID_D"] = patients["Subject_ID_D"].map(normalize_id)
    for column in ["Subject_ID_D", "T1_date_iso", "T2_date_iso"]:
        if column in patients.columns:
            patients[column] = patients[column].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaT": pd.NA})
    patients = patients.dropna(subset=["Subject_ID_D", "T1_date_iso"]).copy()
    patients = patients[~patients["Subject_ID_D"].isin(EXCLUDED_SUBJECT_IDS)].copy()
    if endpoint == "t2":
        patients = patients.dropna(subset=["T2_date_iso"]).copy()
    return patients.sort_values("Subject_ID_D").drop_duplicates("Subject_ID_D").reset_index(drop=True)


def patient_interval(
    endpoint: str, patient: pd.Series, fallback_midpoint_days: float = FALLBACK_MIDPOINT_DAYS
) -> dict[str, Any] | None:
    t1 = local_timestamp(patient.get("T1_date_iso"))
    t2 = local_timestamp(patient.get("T2_date_iso"))
    if t1 is None:
        return None
    exact_midpoint = t2 is not None and t2 > t1
    if exact_midpoint:
        midpoint = t1 + (t2 - t1) / 2
        midpoint_source = "exact_t1_t2_midpoint"
        interval_days = (t2 - t1).total_seconds() / 86400
    else:
        if endpoint == "t2":
            return None
        midpoint = t1 + pd.Timedelta(days=fallback_midpoint_days)
        midpoint_source = f"fallback_{fallback_midpoint_days:.3f}_days_no_valid_t2"
        interval_days = fallback_midpoint_days

    start = t1 if endpoint == "t1" else midpoint
    end = midpoint if endpoint == "t1" else t2
    if end is None or end <= start:
        return None
    start_ms = phase5.local_to_ms(start)
    end_ms = phase5.local_to_ms(end)
    return {
        "window_rule": "t1_to_patient_midpoint" if endpoint == "t1" else "patient_midpoint_to_t2",
        "midpoint_source": midpoint_source,
        "t1_timestamp": phase5.local_to_ms(t1),
        "t2_timestamp": phase5.local_to_ms(t2) if t2 is not None else pd.NA,
        "midpoint_timestamp": phase5.local_to_ms(midpoint),
        "start_ms": start_ms,
        "end_ms": end_ms,
        "interval_days_from_t1_to_t2": interval_days,
        "interval_days_in_endpoint": (end - start).total_seconds() / 86400,
        "fallback_midpoint_days": fallback_midpoint_days,
    }


def cohort_fallback_midpoint_days(patients: pd.DataFrame) -> float:
    t1 = pd.to_datetime(patients["T1_date_iso"], errors="coerce")
    t2 = pd.to_datetime(patients["T2_date_iso"], errors="coerce")
    half_intervals = (t2 - t1).dt.total_seconds().div(86400).div(2)
    median = float(half_intervals.dropna().median()) if half_intervals.notna().any() else float(FALLBACK_MIDPOINT_DAYS)
    return median if median > 0 else float(FALLBACK_MIDPOINT_DAYS)


def coverage_for_devices(conn: Any, table_name: str, subject_id: str, device_ids: list[str], window: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for device_id in device_ids:
        n_rows, first_ts, last_ts = phase5.count_rows(
            conn, table_name, device_id, int(window["start_ms"]), int(window["end_ms"])
        )
        rows.append(
            {
                "Subject_ID_D": subject_id,
                "table_name": table_name,
                "device_id": device_id,
                "window_start_local": phase5.ms_to_local(window["start_ms"]),
                "window_end_local": phase5.ms_to_local(window["end_ms"]),
                "rows_in_window": n_rows,
                "first_data_timestamp": first_ts,
                "last_data_timestamp": last_ts,
                "midpoint_source": window["midpoint_source"],
            }
        )
    return rows


def build_wide(patients: pd.DataFrame, long_df: pd.DataFrame) -> pd.DataFrame:
    base_columns = [column for column in COGNITIVE_COLUMNS if column in patients.columns]
    base = patients[base_columns].drop_duplicates("Subject_ID_D")
    if long_df.empty:
        return base
    values = long_df.copy()
    values["feature_value"] = pd.to_numeric(values["feature_value"], errors="coerce")
    pivot = values.pivot_table(
        index="Subject_ID_D", columns="feature_name", values="feature_value", aggfunc="first"
    ).reset_index()
    pivot.columns.name = None
    return base.merge(pivot, on="Subject_ID_D", how="left")


def load_existing(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    frame = pd.read_csv(path, dtype=str)
    if "Subject_ID_D" in frame.columns:
        frame["Subject_ID_D"] = frame["Subject_ID_D"].map(normalize_id)
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
        subject_id = normalize_id(record.get("Subject_ID_D"))
        if subject_id:
            states[subject_id] = str(record.get("status", ""))
    return states


def run_endpoint(endpoint: str, max_patients: int, resume: bool) -> None:
    out = endpoint_dir(endpoint)
    out.mkdir(parents=True, exist_ok=True)
    long_path = path_for(endpoint, "features_long")
    wide_path = path_for(endpoint, "features_wide")
    status_path = path_for(endpoint, "patient_table_status")
    coverage_path = path_for(endpoint, "coverage")
    checkpoint = checkpoint_path(endpoint)
    selected = pd.read_csv(SELECTED_PATH, dtype=str)
    selected = selected[selected["source_table"].isin(ALL_SUPPORTED_TABLES)].copy()
    tables = sorted(selected["source_table"].dropna().unique().tolist())
    patients = load_patients(endpoint)
    fallback_midpoint_days = cohort_fallback_midpoint_days(pd.read_csv(DATASET_PATH, dtype=str))

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

    completed = {subject_id for subject_id, state in states.items() if state == "completed"}
    # Keep only complete patient records. Partial/error records are removed from
    # the in-memory outputs before that patient is retried and appended again.
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
    if max_patients > 0:
        patients = patients.head(max_patients).copy()
    device_map = load_device_map_strict()
    long_rows = existing_long.to_dict("records")
    status_rows = existing_status.to_dict("records")
    coverage_rows = existing_coverage.to_dict("records")
    conn = phase5.connect_sensordata_db()
    try:
        for patient_index, (_, patient) in enumerate(patients.iterrows(), start=1):
            subject_id = patient["Subject_ID_D"]
            window = patient_interval(endpoint, patient, fallback_midpoint_days)
            device_ids = device_map.get(subject_id, [])
            print(
                f"{endpoint} patient {patient_index}/{len(patients)} Subject_ID_D={subject_id} "
                f"tables={len(tables)} devices={len(device_ids)}",
                flush=True,
            )
            long_start = len(long_rows)
            status_start = len(status_rows)
            coverage_start = len(coverage_rows)
            for table_name in tables:
                selected_for_table = selected[selected["source_table"].eq(table_name)]
                features: dict[str, Any] = {}
                rows: list[dict[str, Any]] = []
                table_status = "not_started"
                error_message = ""
                for attempt in range(3):
                    try:
                        try:
                            conn.close()
                        except Exception:
                            pass
                        conn = phase5.connect_sensordata_db()
                        conn.ping(reconnect=True, attempts=3, delay=1)
                        if window is None:
                            table_status = "missing_invalid_patient_interval"
                        elif not device_ids:
                            table_status = "missing_no_mapped_device"
                        else:
                            coverage_rows.extend(
                                coverage_for_devices(conn, table_name, subject_id, device_ids, window)
                            )
                            rows = phase5.fetch_table_rows(
                                conn, table_name, device_ids, int(window["start_ms"]), int(window["end_ms"])
                            )
                            if rows:
                                features = phase5.calculate_features(table_name, rows)
                                table_status = "calculated"
                            else:
                                table_status = "missing_no_data_in_patient_interval"
                        break
                    except Exception as exc:
                        error_message = str(exc)
                        if attempt < 2 and is_retryable_db_error(exc):
                            continue
                        table_status = "retryable_error" if is_retryable_db_error(exc) else "error"
                        break

                computed_status = str(features.get("feature_status", table_status))
                status_rows.append(
                    {
                        "Subject_ID_D": subject_id,
                        "T1_date_iso": patient.get("T1_date_iso", ""),
                        "T2_date_iso": patient.get("T2_date_iso", ""),
                        "table_name": table_name,
                        "table_status": table_status,
                        "feature_status": computed_status,
                        "device_ids_available": ";".join(device_ids),
                        "device_ids_used": ";".join(device_ids if rows else []),
                        "window_rule": window.get("window_rule", "") if window else "",
                        "midpoint_source": window.get("midpoint_source", "") if window else "",
                        "fallback_midpoint_days": window.get("fallback_midpoint_days", fallback_midpoint_days) if window else fallback_midpoint_days,
                        "t1_timestamp": window.get("t1_timestamp", pd.NA) if window else pd.NA,
                        "t2_timestamp": window.get("t2_timestamp", pd.NA) if window else pd.NA,
                        "midpoint_timestamp": window.get("midpoint_timestamp", pd.NA) if window else pd.NA,
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
                            "Subject_ID_D": subject_id,
                            "T1_date_iso": patient.get("T1_date_iso", ""),
                            "T2_date_iso": patient.get("T2_date_iso", ""),
                            "table_name": table_name,
                            "feature_name": feature["feature_name"],
                            "feature_family": feature.get("feature_family", ""),
                            "feature_value": numeric_value if not pd.isna(numeric_value) else pd.NA,
                            "feature_status": feature_status(value, table_status, computed_status),
                            "window_rule": window.get("window_rule", "") if window else "",
                            "midpoint_source": window.get("midpoint_source", "") if window else "",
                            "fallback_midpoint_days": window.get("fallback_midpoint_days", fallback_midpoint_days) if window else fallback_midpoint_days,
                            "window_start_local": phase5.ms_to_local(window.get("start_ms")) if window else pd.NA,
                            "window_end_local": phase5.ms_to_local(window.get("end_ms")) if window else pd.NA,
                            "interval_days_in_endpoint": window.get("interval_days_in_endpoint", pd.NA) if window else pd.NA,
                            "rows_in_window": len(rows),
                            "device_ids_used": ";".join(device_ids if rows else []),
                            "error_message": error_message,
                        }
                    )
                print(f"  table done={table_name} status={table_status} rows={len(rows)}", flush=True)

            patient_statuses = [
                row["table_status"] for row in status_rows[status_start:] if row.get("Subject_ID_D") == subject_id
            ]
            checkpoint_status = "completed" if not set(patient_statuses).intersection({"error", "retryable_error"}) else "needs_retry"
            with checkpoint.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"Subject_ID_D": subject_id, "status": checkpoint_status}) + "\n")
            append_records(long_path, long_rows[long_start:])
            append_records(status_path, status_rows[status_start:])
            append_records(coverage_path, coverage_rows[coverage_start:])
            build_wide(load_patients(endpoint), pd.DataFrame(long_rows)).to_csv(wide_path, index=False)
    finally:
        conn.close()

    final_status = pd.DataFrame(status_rows)
    build_wide(load_patients(endpoint), pd.DataFrame(long_rows)).to_csv(wide_path, index=False)
    (out / f"README_{ENDPOINTS[endpoint]}.md").write_text(
        f"# {ENDPOINTS[endpoint]}\n\n"
        f"This exploratory cohort uses the patient-level interval split at the midpoint between T1 and T2. "
        f"The {endpoint.upper()} interval is half-open: `[start, end)`. All valid mapped devices are pooled "
        f"for each patient and table. The light, proximity, and accelerometer work remains outside this phase.\n\n"
        f"For Phase 11 patients without a valid T2, the midpoint fallback is T1 plus the current paired-cohort median half-interval "
        f"({fallback_midpoint_days:.3f} days, approximately 123 days). "
        "The status CSV records exact versus fallback midpoint provenance and interval duration.\n",
        encoding="utf-8",
    )
    print(f"{endpoint}_patients_processed: {final_status['Subject_ID_D'].nunique() if not final_status.empty else 0}", flush=True)
    if not final_status.empty:
        print(final_status["table_status"].value_counts(dropna=False).to_string(), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract selected features from patient-level midpoint intervals.")
    parser.add_argument("--endpoint", choices=["t1", "t2", "both"], default="both")
    parser.add_argument("--max-patients", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    endpoints = ["t1", "t2"] if args.endpoint == "both" else [args.endpoint]
    for endpoint in endpoints:
        run_endpoint(endpoint, args.max_patients, args.resume)


if __name__ == "__main__":
    main()
