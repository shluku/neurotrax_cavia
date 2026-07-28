"""Extract selected digital features using availability-anchored 10-day windows."""

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
OUT_DIR = ROOT / "output/analysis_candidates/phase7_10day_window"
WINDOW_MS = 10 * 24 * 60 * 60 * 1000
SEARCH_BACK_MS = 30 * 24 * 60 * 60 * 1000
ENDPOINTS = {
    "t1": {"date_column": "T1_date_iso", "direction": "forward"},
    "t2": {"date_column": "T2_date_iso", "direction": "backward"},
}
ALL_SUPPORTED_TABLES = sorted(phase5.ALL_SUPPORTED_TABLES)
EXCLUDED_SUBJECT_IDS = EXCLUDED_COHORT_SUBJECT_IDS


def endpoint_dir(endpoint: str) -> Path:
    return OUT_DIR / endpoint


def path_for(endpoint: str, suffix: str) -> Path:
    return endpoint_dir(endpoint) / f"phase7_{endpoint}_10day_{suffix}.csv"


def checkpoint_path(endpoint: str) -> Path:
    return endpoint_dir(endpoint) / f"phase7_{endpoint}_10day_checkpoint.jsonl"


def normalize_id(value: Any) -> str:
    return phase5.normalize_subject_id_d(value)


def load_patients(endpoint: str) -> pd.DataFrame:
    patients = pd.read_csv(DATASET_PATH, dtype=str)
    patients["Subject_ID_D"] = patients["Subject_ID_D"].map(normalize_id)
    date_column = ENDPOINTS[endpoint]["date_column"]
    patients = patients.dropna(subset=["Subject_ID_D", date_column]).copy()
    patients = patients[~patients["Subject_ID_D"].isin(EXCLUDED_SUBJECT_IDS)].copy()
    return patients.sort_values("Subject_ID_D").reset_index(drop=True)


def select_window(
    conn: Any,
    table_name: str,
    patient: pd.Series,
    device_ids: list[str],
    endpoint: str,
) -> dict[str, Any]:
    date_column = ENDPOINTS[endpoint]["date_column"]
    anchor_ms = phase5.local_to_ms(pd.Timestamp(str(patient[date_column])).tz_localize(phase5.TZ))
    candidates: list[tuple[int, str, int]] = []
    coverage: list[dict[str, Any]] = []
    for device_id in device_ids:
        if endpoint == "t1":
            search_start, search_end = anchor_ms, anchor_ms + WINDOW_MS
            first_or_last = phase5.fetch_first_timestamp(conn, table_name, device_id, search_start, search_end, latest=False)
            window_start = first_or_last
            window_end = first_or_last + WINDOW_MS if first_or_last is not None else None
        else:
            search_start, search_end = anchor_ms - SEARCH_BACK_MS, anchor_ms
            first_or_last = phase5.fetch_first_timestamp(conn, table_name, device_id, search_start, search_end, latest=True)
            window_start = first_or_last - WINDOW_MS if first_or_last is not None else None
            window_end = first_or_last + 1 if first_or_last is not None else None
        rows = 0
        if window_start is not None and window_end is not None:
            rows = phase5.count_rows(conn, table_name, device_id, window_start, window_end)[0]
            candidates.append((first_or_last, device_id, rows))
        coverage.append(
            {
                "Subject_ID_D": patient["Subject_ID_D"],
                "endpoint": endpoint,
                "table_name": table_name,
                "device_id": device_id,
                "anchor_date_iso": patient[date_column],
                "anchor_timestamp": anchor_ms,
                "candidate_timestamp": first_or_last,
                "candidate_rows": rows,
            }
        )
    if not candidates:
        return {"coverage_rows": coverage}
    chosen = sorted(candidates, key=lambda row: row[0], reverse=endpoint == "t2")[0]
    candidate_ts, device_id, rows = chosen
    if endpoint == "t1":
        start_ms, end_ms = candidate_ts, candidate_ts + WINDOW_MS
        rule = "t1_first_available_10d_after_anchor"
    else:
        start_ms, end_ms = candidate_ts - WINDOW_MS, candidate_ts + 1
        rule = "t2_last_available_10d_before_anchor"
    return {
        "window_rule": rule,
        "anchor_timestamp": anchor_ms,
        "candidate_timestamp": candidate_ts,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "device_ids_used": [device_id],
        "n_rows": rows,
        "coverage_rows": coverage,
    }


def append_records(path: Path, records: list[dict[str, Any]]) -> None:
    if records:
        pd.DataFrame(records).to_csv(path, mode="a", header=not path.exists() or path.stat().st_size == 0, index=False)


def load_existing(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    frame = pd.read_csv(path, dtype=str)
    if "Subject_ID_D" in frame.columns:
        frame["Subject_ID_D"] = frame["Subject_ID_D"].map(normalize_id)
    return frame


def build_wide(patients: pd.DataFrame, long_df: pd.DataFrame) -> pd.DataFrame:
    base_columns = [column for column in COGNITIVE_COLUMNS if column in patients.columns]
    base = patients[base_columns].drop_duplicates("Subject_ID_D")
    if long_df.empty:
        return base
    values = long_df.copy()
    values["feature_value"] = pd.to_numeric(values["feature_value"], errors="coerce")
    pivot = values.pivot_table(index="Subject_ID_D", columns="feature_name", values="feature_value", aggfunc="first").reset_index()
    pivot.columns.name = None
    return base.merge(pivot, on="Subject_ID_D", how="left")


def run_endpoint(endpoint: str, max_patients: int, resume: bool) -> None:
    out = endpoint_dir(endpoint)
    out.mkdir(parents=True, exist_ok=True)
    long_path, wide_path = path_for(endpoint, "features_long"), path_for(endpoint, "features_wide")
    status_path, coverage_path = path_for(endpoint, "patient_table_status"), path_for(endpoint, "coverage")
    checkpoint = checkpoint_path(endpoint)
    selected = pd.read_csv(SELECTED_PATH, dtype=str)
    selected = selected[selected["source_table"].isin(ALL_SUPPORTED_TABLES)].copy()
    tables = selected["source_table"].dropna().unique().tolist()
    patients = load_patients(endpoint)
    existing_long = load_existing(long_path) if resume else pd.DataFrame()
    existing_status = load_existing(status_path) if resume else pd.DataFrame()
    existing_coverage = load_existing(coverage_path) if resume else pd.DataFrame()
    completed: set[str] = set()
    if resume and checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            subject_id = normalize_id(row.get("Subject_ID_D"))
            if row.get("status") != "completed" or not subject_id or existing_status.empty:
                continue
            subject_status = existing_status[existing_status["Subject_ID_D"].eq(subject_id)]
            statuses = set(subject_status.get("table_status", pd.Series(dtype=str)).astype(str))
            if len(subject_status) == len(tables) and not statuses.intersection({"error", "retryable_error"}):
                completed.add(subject_id)
    if not resume:
        checkpoint.write_text("", encoding="utf-8")
        for path in (long_path, wide_path, status_path, coverage_path):
            if path.exists():
                path.unlink()
        existing_long, existing_status, existing_coverage = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    else:
        for frame, path in ((existing_long, long_path), (existing_status, status_path), (existing_coverage, coverage_path)):
            frame[frame["Subject_ID_D"].isin(completed)].to_csv(path, index=False)
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
            device_ids = device_map.get(subject_id, [])
            print(f"{endpoint} patient {patient_index}/{len(patients)} Subject_ID_D={subject_id} tables={len(tables)}", flush=True)
            long_start, status_start, coverage_start = len(long_rows), len(status_rows), len(coverage_rows)
            for table_name in tables:
                selected_for_table = selected[selected["source_table"].eq(table_name)]
                window, rows, features, used_ids = {}, [], {}, []
                table_status, error_message = "not_started", ""
                for attempt in range(3):
                    try:
                        try:
                            conn.close()
                        except Exception:
                            pass
                        conn = phase5.connect_sensordata_db()
                        conn.ping(reconnect=True, attempts=3, delay=1)
                        if not device_ids:
                            table_status = "missing_no_mapped_device"
                        else:
                            window = select_window(conn, table_name, patient, device_ids, endpoint)
                            if "start_ms" not in window:
                                table_status = "missing_no_availability_anchored_window"
                            else:
                                used_ids = window["device_ids_used"]
                                rows = phase5.fetch_table_rows(conn, table_name, used_ids, window["start_ms"], window["end_ms"])
                                if rows:
                                    features = phase5.calculate_features(table_name, rows)
                                    table_status = "calculated"
                                else:
                                    table_status = "missing_selected_window_no_rows"
                        break
                    except Exception as exc:
                        error_message = str(exc)
                        if attempt < 2 and is_retryable_db_error(exc):
                            continue
                        table_status = "retryable_error" if is_retryable_db_error(exc) else "error"
                        break
                coverage_rows.extend(window.get("coverage_rows", []))
                computed_status = str(features.get("feature_status", table_status))
                date_column = ENDPOINTS[endpoint]["date_column"]
                status_rows.append(
                    {
                        "Subject_ID_D": subject_id,
                        "endpoint": endpoint,
                        "anchor_date_iso": patient.get(date_column, ""),
                        "table_name": table_name,
                        "table_status": table_status,
                        "feature_status": computed_status,
                        "device_ids_available": ";".join(device_ids),
                        "device_ids_used": ";".join(used_ids),
                        "window_rule": window.get("window_rule", ""),
                        "anchor_timestamp": window.get("anchor_timestamp", pd.NA),
                        "candidate_timestamp": window.get("candidate_timestamp", pd.NA),
                        "window_start_ms": window.get("start_ms", pd.NA),
                        "window_end_ms": window.get("end_ms", pd.NA),
                        "window_start_local": phase5.ms_to_local(window.get("start_ms")),
                        "window_end_local": phase5.ms_to_local(window.get("end_ms")),
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
                            "endpoint": endpoint,
                            "anchor_date_iso": patient.get(date_column, ""),
                            "table_name": table_name,
                            "feature_name": feature["feature_name"],
                            "feature_family": feature.get("feature_family", ""),
                            "feature_value": numeric_value if not pd.isna(numeric_value) else pd.NA,
                            "feature_status": feature_status(value, table_status, computed_status),
                            "window_rule": window.get("window_rule", ""),
                            "window_start_local": phase5.ms_to_local(window.get("start_ms")),
                            "window_end_local": phase5.ms_to_local(window.get("end_ms")),
                            "rows_in_window": len(rows),
                            "device_ids_used": ";".join(used_ids),
                            "error_message": error_message,
                        }
                    )
            statuses = [row["table_status"] for row in status_rows if row.get("Subject_ID_D") == subject_id]
            checkpoint_status = "completed" if not set(statuses).intersection({"error", "retryable_error"}) else "needs_retry"
            with checkpoint.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"Subject_ID_D": subject_id, "status": checkpoint_status}) + "\n")
            append_records(long_path, long_rows[long_start:])
            append_records(status_path, status_rows[status_start:])
            append_records(coverage_path, coverage_rows[coverage_start:])
            build_wide(patients if not completed else load_patients(endpoint), pd.DataFrame(long_rows)).to_csv(wide_path, index=False)
    finally:
        conn.close()
    long_df = pd.DataFrame(long_rows)
    status_df = pd.DataFrame(status_rows)
    build_wide(load_patients(endpoint), long_df).to_csv(wide_path, index=False)
    (out / "README_phase7_10day_" + endpoint + ".md").write_text(
        f"# Phase 7 {endpoint.upper()} 10-Day Availability-Anchored Extraction\n\n"
        f"The window starts from the first available post-{endpoint.upper()} anchor for T1 or the latest available pre-T2 timestamp for T2, then includes 10 days of data. "
        "The light table is excluded. Feature functions are unchanged from the prior extraction.\n",
        encoding="utf-8",
    )
    print(f"{endpoint}_patients_processed: {status_df['Subject_ID_D'].nunique() if not status_df.empty else 0}", flush=True)
    print(status_df["table_status"].value_counts(dropna=False).to_string(), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 7 availability-anchored 10-day T1/T2 extraction")
    parser.add_argument("--endpoint", choices=["t1", "t2", "both"], default="both")
    parser.add_argument("--max-patients", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    endpoints = ["t1", "t2"] if args.endpoint == "both" else [args.endpoint]
    for endpoint in endpoints:
        run_endpoint(endpoint, args.max_patients, args.resume)


if __name__ == "__main__":
    main()
