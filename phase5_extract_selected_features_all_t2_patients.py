from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db
from phase2_extract_exploratory_t1_week_24h_selected_features import (
    SAFE_TABLES,
    TZ,
    compute_features,
    fetch_light_lux_values,
    fetch_rows,
    local_to_ms,
    ms_to_local,
    normalize_subject_id_d,
)
from phase2_extract_barometer_adjusted_first_available_7d_selected_features import (
    compute_barometer_signal_features,
    fetch_rows as fetch_barometer_rows,
)
from phase2_extract_significant_adjusted_first_available_7d_selected_features import (
    compute_significant,
    fetch_rows as fetch_significant_rows,
)
from phase2_extract_sensor_linear_accelerometer_adjusted_first_available_7d_selected_features import (
    compute_sensor_linear_accelerometer,
    fetch_rows as fetch_sensor_linear_rows,
)
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
OUT_DIR = ROOT / "output/analysis_candidates/phase5_t2_feature_extraction"
LONG_PATH = OUT_DIR / "phase5_t2_selected_features_long.csv"
WIDE_PATH = OUT_DIR / "phase5_t2_selected_features_wide.csv"
COVERAGE_PATH = OUT_DIR / "phase5_t2_selected_features_coverage.csv"
STATUS_PATH = OUT_DIR / "phase5_t2_selected_features_patient_table_status.csv"
CHECKPOINT_PATH = OUT_DIR / "phase5_t2_selected_features_checkpoint.jsonl"
README_PATH = OUT_DIR / "README_phase5_t2_selected_features.md"

ADJUSTED_TABLES = {"barometer", "significant", "sensor_linear_accelerometer"}
ALL_SUPPORTED_TABLES = SAFE_TABLES | ADJUSTED_TABLES
EXCLUDED_SUBJECT_IDS = EXCLUDED_COHORT_SUBJECT_IDS


def load_t2_patients() -> pd.DataFrame:
    patients = pd.read_csv(DATASET_PATH, dtype=str)
    patients["Subject_ID_D"] = patients["Subject_ID_D"].map(normalize_subject_id_d)
    patients["Subject_ID_D"] = patients["Subject_ID_D"].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    patients = patients.dropna(subset=["Subject_ID_D", "T2_date_iso"]).copy()
    patients = patients[~patients["Subject_ID_D"].isin(EXCLUDED_SUBJECT_IDS)].copy()
    return patients.sort_values("Subject_ID_D").reset_index(drop=True)


def fetch_first_timestamp(conn, table_name: str, device_id: str, start_ms: int, end_ms: int, latest: bool = False) -> int | None:
    direction = "DESC" if latest else "ASC"
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT timestamp FROM `{table_name}`
            WHERE device_id = %s AND timestamp >= %s AND timestamp <= %s
            ORDER BY timestamp {direction} LIMIT 1
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        cur.close()


def count_rows(conn, table_name: str, device_id: str, start_ms: int, end_ms: int) -> tuple[int, int | None, int | None]:
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM `{table_name}`
            WHERE device_id = %s AND timestamp >= %s AND timestamp < %s
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        n_rows, first_ts, last_ts = cur.fetchone()
        return int(n_rows or 0), int(first_ts) if first_ts is not None else None, int(last_ts) if last_ts is not None else None
    finally:
        cur.close()


def window_for_table(conn, table_name: str, patient: pd.Series, device_ids: list[str], hours: int = 24) -> dict[str, Any]:
    t2 = pd.Timestamp(str(patient["T2_date_iso"])).tz_localize(TZ)
    t2_ms = local_to_ms(t2)
    week_start = t2 - pd.Timedelta(days=7)
    month_start = t2 - pd.Timedelta(days=30)
    if table_name in ADJUSTED_TABLES:
        primary_start_ms, primary_end_ms = local_to_ms(week_start), t2_ms
        fallback_start_ms, fallback_end_ms = local_to_ms(month_start), t2_ms
        window_days = 7
    else:
        primary_start_ms, primary_end_ms = local_to_ms(week_start), local_to_ms(t2 - pd.Timedelta(hours=hours))
        fallback_start_ms, fallback_end_ms = local_to_ms(month_start), local_to_ms(t2 - pd.Timedelta(hours=hours))
        window_days = 0

    coverage: list[dict[str, Any]] = []
    primary_candidates: list[tuple[int, str, int]] = []
    fallback_candidates: list[tuple[int, str, int]] = []
    for device_id in device_ids:
        primary_first = fetch_first_timestamp(conn, table_name, device_id, primary_start_ms, primary_end_ms)
        primary_rows = 0
        if primary_first is not None:
            primary_end = t2_ms if table_name in ADJUSTED_TABLES else primary_first + hours * 3600 * 1000
            primary_rows = count_rows(conn, table_name, device_id, primary_first, primary_end)[0]
            primary_candidates.append((primary_first, device_id, primary_rows))
        fallback_latest = fetch_first_timestamp(conn, table_name, device_id, fallback_start_ms, fallback_end_ms, latest=True)
        fallback_rows = 0
        if fallback_latest is not None:
            fallback_start = max(fallback_start_ms, fallback_latest - (window_days or hours / 24) * 24 * 3600 * 1000)
            fallback_rows = count_rows(conn, table_name, device_id, fallback_start, fallback_latest + 1)[0]
            fallback_candidates.append((fallback_latest, device_id, fallback_rows))
        coverage.append(
            {
                "table_name": table_name,
                "Subject_ID_D": patient["Subject_ID_D"],
                "Subject_ID_N": patient.get("Subject_ID_N", ""),
                "T2_date_iso": patient.get("T2_date_iso", ""),
                "device_id": device_id,
                "week_first_ts": primary_first,
                "week_rows": primary_rows,
                "fallback_latest_ts": fallback_latest,
                "fallback_rows": fallback_rows,
            }
        )

    if primary_candidates:
        first_ts, device_id, n_rows = sorted(primary_candidates, key=lambda row: row[0])[0]
        if table_name in ADJUSTED_TABLES:
            start_ms, end_ms = local_to_ms(week_start), t2_ms
        else:
            start_ms, end_ms = first_ts, first_ts + hours * 3600 * 1000
        return {
            "window_rule": "t2_week_first_valid_24h" if table_name not in ADJUSTED_TABLES else "t2_week_pre_assessment_7d",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "device_ids_used": [device_id],
            "n_rows": n_rows,
            "coverage_rows": coverage,
        }
    if fallback_candidates:
        latest_ts, device_id, n_rows = sorted(fallback_candidates, key=lambda row: row[0], reverse=True)[0]
        if table_name in ADJUSTED_TABLES:
            start_ms, end_ms = max(fallback_start_ms, latest_ts - 7 * 24 * 3600 * 1000), latest_ts + 1
        else:
            start_ms, end_ms = latest_ts - hours * 3600 * 1000, latest_ts + 1
        return {
            "window_rule": "t2_30day_latest_pre_t2_fallback",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "device_ids_used": [device_id],
            "n_rows": n_rows,
            "coverage_rows": coverage,
        }
    return {"coverage_rows": coverage}


def fetch_table_rows(conn, table_name: str, device_ids: list[str], start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for device_id in device_ids:
        if table_name == "light":
            # Light is a high-volume JSON table. Smaller scans avoid the RDS
            # read timeout seen when querying a full 24-hour interval at once.
            chunk_ms = 60 * 60 * 1000
            chunk_start = int(start_ms)
            while chunk_start < int(end_ms):
                chunk_end = min(chunk_start + chunk_ms, int(end_ms))
                rows.extend(fetch_light_lux_values(conn, device_id, chunk_start, chunk_end))
                chunk_start = chunk_end
        elif table_name == "barometer":
            rows.extend(fetch_barometer_rows(conn, device_id, start_ms, end_ms))
        elif table_name == "significant":
            rows.extend(fetch_significant_rows(conn, device_id, start_ms, end_ms))
        elif table_name == "sensor_linear_accelerometer":
            rows.extend(fetch_sensor_linear_rows(conn, device_id, start_ms, end_ms))
        else:
            rows.extend(fetch_rows(conn, table_name, device_id, start_ms, end_ms))
    return sorted(rows, key=lambda row: int(row.get("timestamp", 0)))


def calculate_features(table_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if table_name == "barometer":
        return compute_barometer_signal_features(rows)[0]
    if table_name == "significant":
        return compute_significant(rows)
    if table_name == "sensor_linear_accelerometer":
        return compute_sensor_linear_accelerometer(rows)
    return compute_features(table_name, rows)


def load_existing_output(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    frame = pd.read_csv(path, dtype=str)
    if "Subject_ID_D" in frame.columns:
        frame["Subject_ID_D"] = frame["Subject_ID_D"].map(normalize_subject_id_d)
    return frame


def append_records(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    pd.DataFrame(records).to_csv(path, mode="a", header=not path.exists() or path.stat().st_size == 0, index=False)


def build_wide_frame(all_patients: pd.DataFrame, long_df: pd.DataFrame) -> pd.DataFrame:
    base_cols = [column for column in COGNITIVE_COLUMNS if column in all_patients.columns]
    base = all_patients[base_cols].drop_duplicates("Subject_ID_D")
    if long_df.empty:
        return base.copy()
    values = long_df.copy()
    values["feature_value"] = pd.to_numeric(values["feature_value"], errors="coerce")
    pivot = values.pivot_table(index="Subject_ID_D", columns="feature_name", values="feature_value", aggfunc="first").reset_index()
    pivot.columns.name = None
    return base.merge(pivot, on="Subject_ID_D", how="left")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract selected Phase 2 features around T2.")
    parser.add_argument("--max-patients", type=int, default=0)
    parser.add_argument("--resume", action="store_true", help="Skip patients already recorded in the checkpoint file.")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    selected = pd.read_csv(SELECTED_PATH, dtype=str)
    selected = selected[selected["source_table"].isin(ALL_SUPPORTED_TABLES)].copy()
    tables = selected["source_table"].dropna().unique().tolist()
    all_patients = load_t2_patients()
    resumable_subjects: set[str] = set()
    existing_long = pd.DataFrame()
    existing_status = pd.DataFrame()
    existing_coverage = pd.DataFrame()
    if args.resume:
        existing_long = load_existing_output(LONG_PATH)
        existing_status = load_existing_output(STATUS_PATH)
        existing_coverage = load_existing_output(COVERAGE_PATH)
    if args.resume and CHECKPOINT_PATH.exists():
        for line in CHECKPOINT_PATH.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            subject_id = normalize_subject_id_d(record.get("Subject_ID_D"))
            if record.get("status") != "completed" or not subject_id or existing_status.empty:
                continue
            subject_status = existing_status[existing_status["Subject_ID_D"].eq(subject_id)]
            table_statuses = set(subject_status.get("table_status", pd.Series(dtype=str)).astype(str))
            if len(subject_status) == len(tables) and not table_statuses.intersection({"error", "retryable_error"}):
                resumable_subjects.add(subject_id)
    elif not args.resume:
        CHECKPOINT_PATH.write_text("", encoding="utf-8")
    if args.resume:
        existing_long = existing_long[existing_long["Subject_ID_D"].isin(resumable_subjects)].copy()
        existing_status = existing_status[existing_status["Subject_ID_D"].isin(resumable_subjects)].copy()
        existing_coverage = existing_coverage[existing_coverage["Subject_ID_D"].isin(resumable_subjects)].copy()
        # Remove only rows belonging to interrupted/failed patients. Completed
        # patient rows remain intact and new patients are appended below.
        existing_long.to_csv(LONG_PATH, index=False)
        existing_status.to_csv(STATUS_PATH, index=False)
        existing_coverage.to_csv(COVERAGE_PATH, index=False)
    else:
        for path in (LONG_PATH, STATUS_PATH, COVERAGE_PATH, WIDE_PATH):
            if path.exists():
                path.unlink()
    patients = all_patients[~all_patients["Subject_ID_D"].isin(resumable_subjects)].copy()
    if args.max_patients > 0:
        patients = patients.head(args.max_patients).copy()
    device_map = load_device_map_strict()
    long_rows: list[dict[str, Any]] = existing_long.to_dict("records")
    status_rows: list[dict[str, Any]] = existing_status.to_dict("records")
    coverage_rows: list[dict[str, Any]] = existing_coverage.to_dict("records")
    conn = connect_sensordata_db()
    try:
        for patient_index, (_, patient) in enumerate(patients.iterrows(), start=1):
            subject_id = patient["Subject_ID_D"]
            device_ids = device_map.get(subject_id, [])
            print(f"patient {patient_index}/{len(patients)} Subject_ID_D={subject_id} tables={len(tables)}", flush=True)
            long_start = len(long_rows)
            status_start = len(status_rows)
            coverage_start = len(coverage_rows)
            for table_name in tables:
                selected_for_table = selected[selected["source_table"].eq(table_name)]
                window: dict[str, Any] = {}
                rows: list[dict[str, Any]] = []
                features: dict[str, Any] = {}
                device_ids_used: list[str] = []
                table_status = "not_started"
                error_message = ""
                for attempt in range(3):
                    try:
                        # Use a short-lived connection per table so one server-side
                        # disconnect cannot poison the rest of the cohort.
                        if attempt == 0:
                            try:
                                conn.close()
                            except Exception:
                                pass
                            conn = connect_sensordata_db()
                        try:
                            conn.ping(reconnect=True, attempts=3, delay=1)
                        except Exception:
                            try:
                                conn.close()
                            except Exception:
                                pass
                            conn = connect_sensordata_db()
                        if not device_ids:
                            table_status = "missing_no_mapped_device"
                        else:
                            window = window_for_table(conn, table_name, patient, device_ids)
                            if "start_ms" not in window:
                                table_status = "missing_no_pre_t2_window"
                            else:
                                device_ids_used = window.get("device_ids_used", device_ids)
                                rows = fetch_table_rows(conn, table_name, device_ids_used, int(window["start_ms"]), int(window["end_ms"]))
                                if rows:
                                    features = calculate_features(table_name, rows)
                                    table_status = "calculated"
                                else:
                                    table_status = "missing_selected_window_no_rows"
                        error_message = ""
                        break
                    except Exception as exc:
                        error_message = str(exc)
                        if attempt < 2 and is_retryable_db_error(exc):
                            print(f"  reconnecting table={table_name} attempt={attempt + 1} error={error_message}", flush=True)
                            try:
                                conn.close()
                            except Exception:
                                pass
                            conn = connect_sensordata_db()
                            continue
                        table_status = "retryable_error" if is_retryable_db_error(exc) else "error"
                        break
                coverage_rows.extend(window.get("coverage_rows", []))
                computed_status = str(features.get("feature_status", table_status))
                status_rows.append(
                    {
                        "Subject_ID_D": subject_id,
                        "Subject_ID_N": patient.get("Subject_ID_N", ""),
                        "T2_date_iso": patient.get("T2_date_iso", ""),
                        "table_name": table_name,
                        "table_status": table_status,
                        "feature_status": computed_status,
                        "device_ids_available": ";".join(device_ids),
                        "device_ids_used": ";".join(device_ids_used),
                        "window_rule": window.get("window_rule", ""),
                        "window_start_ms": window.get("start_ms", pd.NA),
                        "window_end_ms": window.get("end_ms", pd.NA),
                        "window_start_local": ms_to_local(window.get("start_ms")),
                        "window_end_local": ms_to_local(window.get("end_ms")),
                        "rows_in_window": len(rows),
                        "error_message": error_message,
                    }
                )
                for _, feature in selected_for_table.iterrows():
                    feature_name = str(feature["feature_name"])
                    value = features.get(feature_name, pd.NA)
                    numeric_value = pd.to_numeric(value, errors="coerce")
                    long_rows.append(
                        {
                            "Subject_ID_D": subject_id,
                            "Subject_ID_N": patient.get("Subject_ID_N", ""),
                            "T2_date_iso": patient.get("T2_date_iso", ""),
                            "table_name": table_name,
                            "feature_name": feature_name,
                            "feature_family": feature.get("feature_family", ""),
                            "feature_value": numeric_value if not pd.isna(numeric_value) else pd.NA,
                            "feature_status": feature_status(value, table_status, computed_status),
                            "window_rule": window.get("window_rule", ""),
                            "window_start_local": ms_to_local(window.get("start_ms")),
                            "window_end_local": ms_to_local(window.get("end_ms")),
                            "rows_in_window": len(rows),
                            "device_ids_used": ";".join(device_ids_used),
                            "error_message": error_message,
                        }
                    )
            patient_statuses = [row["table_status"] for row in status_rows if row.get("Subject_ID_D") == subject_id]
            checkpoint_status = "completed" if not set(patient_statuses).intersection({"error", "retryable_error"}) else "needs_retry"
            with CHECKPOINT_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"Subject_ID_D": subject_id, "patient_index": patient_index, "status": checkpoint_status}) + "\n")
            append_records(LONG_PATH, long_rows[long_start:])
            append_records(STATUS_PATH, status_rows[status_start:])
            append_records(COVERAGE_PATH, coverage_rows[coverage_start:])
            build_wide_frame(all_patients, pd.DataFrame(long_rows)).to_csv(WIDE_PATH, index=False)
    finally:
        conn.close()

    long_df = pd.DataFrame(long_rows)
    status_df = pd.DataFrame(status_rows)
    coverage_df = pd.DataFrame(coverage_rows)
    wide = build_wide_frame(all_patients, long_df)
    wide.to_csv(WIDE_PATH, index=False)
    README_PATH.write_text(
        f"# Phase 5 T2 Selected Feature Extraction\n\nPatients represented: `{status_df['Subject_ID_D'].nunique() if not status_df.empty else 0}`. Tables: `{len(tables)}`. Selected features: `{len(selected)}`.\n\n"
        "Standard features use the first valid pre-T2 24-hour window within the preceding week. If unavailable, the latest pre-T2 fallback is searched back to 30 days. Adjusted sensor tables retain a 7-day pre-assessment calculation window.\n",
        encoding="utf-8",
    )
    print(f"patients_processed: {status_df['Subject_ID_D'].nunique() if not status_df.empty else 0}")
    print(f"tables_processed: {len(tables)}")
    print(f"feature_rows: {len(long_df)}")
    print(status_df["table_status"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
