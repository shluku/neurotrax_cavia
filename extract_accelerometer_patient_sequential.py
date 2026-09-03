"""Extract mapped ACC candidate days in patient-sequential order.

The workflow intentionally completes one patient's candidate movement days,
merges that patient's daily rows, and only then advances to the next patient.
It uses daily compressed SQL archives so interrupted work can be resumed
without changing the source database or the earlier pilot outputs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import backup_accelerometer_by_day as backup
import extract_accelerometer_plugin_event_day_from_archives as archive_extractor
import extract_accelerometer_plugin_event_day_pilot as pilot


ROOT = Path(__file__).parent
DEFAULT_OUTPUT_DIR = ROOT / "output/analysis_candidates/accelerometer_patient_sequential_pipeline"
DEFAULT_ARCHIVE_DIR = Path(
    "/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_accelerometer/plugin_event_day_sql_zst"
)
MYSQL = Path("/opt/homebrew/opt/mysql-client/bin/mysql")


def atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def normalize_patient_id(value: Any) -> str:
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def patient_archive_name(patient_id: str, local_date: str) -> str:
    end_date = (pd.Timestamp(local_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    return f"accelerometer_patient_{patient_id}_{local_date}_to_{end_date}.tsv.zst"


def find_archive(archive_dir: Path, patient_id: str, local_date: str) -> Path | None:
    patient_path = archive_dir / patient_archive_name(patient_id, local_date)
    if patient_path.exists() and patient_path.stat().st_size > 0:
        return patient_path
    return None


def dump_day_first_per_timestamp(
    defaults_file: Path,
    start_ms: int,
    end_ms: int,
    output_path: Path,
    log_path: Path,
    device_ids: list[str],
) -> tuple[int, int, int]:
    """Export one first-by-_id row per device/timestamp as compressed TSV."""
    if not device_ids:
        raise ValueError("At least one device ID is required")
    quoted_ids = ",".join("'" + value.replace("'", "\\'") + "'" for value in device_ids)
    sql = f"""
        SELECT first_row._id,
               first_row.timestamp,
               first_row.device_id,
               first_row.data->>'$.double_values_0' AS x,
               first_row.data->>'$.double_values_1' AS y,
               first_row.data->>'$.double_values_2' AS z,
               grouped_rows.timestamp_row_count
        FROM (
            SELECT device_id, timestamp, MIN(_id) AS first_id, COUNT(*) AS timestamp_row_count
            FROM sensordata.accelerometer
            WHERE timestamp >= {int(start_ms)}
              AND timestamp < {int(end_ms)}
              AND device_id IN ({quoted_ids})
            GROUP BY device_id, timestamp
        ) AS grouped_rows
        INNER JOIN sensordata.accelerometer AS first_row
            ON first_row._id = grouped_rows.first_id
        ORDER BY first_row.timestamp, first_row._id
    """
    args = [
        str(MYSQL),
        f"--defaults-extra-file={defaults_file}",
        "--batch",
        "--raw",
        "--skip-column-names",
        "--binary-mode",
        "-e",
        sql,
    ]
    partial_path = output_path.with_suffix(output_path.suffix + ".partial")
    with log_path.open("ab") as log_handle, partial_path.open("wb") as output_handle:
        query = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=log_handle)
        assert query.stdout is not None
        compressor = subprocess.Popen(
            [str(backup.ZSTD), "-T0", "-3", "-q", "-c"],
            stdin=query.stdout,
            stdout=output_handle,
            stderr=log_handle,
        )
        query.stdout.close()
        compressor_rc = compressor.wait()
        query_rc = query.wait()

    output_bytes = partial_path.stat().st_size if partial_path.exists() else 0
    if query_rc == 0 and compressor_rc == 0 and output_bytes > 0:
        integrity_rc = subprocess.run([str(backup.ZSTD), "-q", "-t", str(partial_path)], check=False).returncode
    else:
        integrity_rc = 1
    if query_rc != 0 or compressor_rc != 0 or integrity_rc != 0:
        return query_rc, compressor_rc, output_bytes
    partial_path.replace(output_path)
    return query_rc, compressor_rc, output_path.stat().st_size


def iter_tsv_rows(source: Path):
    process = subprocess.Popen([str(backup.ZSTD), "-dc", str(source)], stdout=subprocess.PIPE)
    assert process.stdout is not None
    try:
        for raw_line in process.stdout:
            yield raw_line.decode("utf-8", errors="replace").rstrip("\n").split("\t")
    finally:
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"zstd failed for {source} with return code {return_code}")


def parse_first_timestamp_archive(
    source: Path,
    candidates: list[pd.Series],
    batch_points: int,
) -> dict[str, tuple[np.ndarray, np.ndarray, dict[str, int]]]:
    """Parse one-row-per-timestamp TSV archives produced by MySQL."""
    device_to_ids: dict[str, list[str]] = {}
    for candidate in candidates:
        device_to_ids.setdefault(str(candidate["device_id"]), []).append(str(candidate["candidate_id"]))
    timestamp_parts: dict[str, list[np.ndarray]] = {str(c["candidate_id"]): [] for c in candidates}
    magnitude_parts: dict[str, list[np.ndarray]] = {str(c["candidate_id"]): [] for c in candidates}
    timestamps_pending: dict[str, list[int]] = {str(c["candidate_id"]): [] for c in candidates}
    magnitudes_pending: dict[str, list[float]] = {str(c["candidate_id"]): [] for c in candidates}
    counters: dict[str, dict[str, int]] = {str(c["candidate_id"]): {} for c in candidates}

    def flush(candidate_id: str) -> None:
        if not timestamps_pending[candidate_id]:
            return
        timestamp_parts[candidate_id].append(np.asarray(timestamps_pending[candidate_id], dtype=np.int64))
        magnitude_parts[candidate_id].append(np.asarray(magnitudes_pending[candidate_id], dtype=float))
        timestamps_pending[candidate_id].clear()
        magnitudes_pending[candidate_id].clear()

    for fields in iter_tsv_rows(source):
        if len(fields) < 7:
            continue
        device_id = fields[2].strip()
        candidate_ids = device_to_ids.get(device_id, [])
        if not candidate_ids:
            continue
        try:
            timestamp = float(fields[1])
            timestamp_int = int(timestamp)
        except (TypeError, ValueError):
            timestamp_int = None
        try:
            row_multiplicity = max(int(float(fields[6])), 1)
        except (TypeError, ValueError):
            row_multiplicity = 1
        for candidate_id in candidate_ids:
            candidate_counters = counters[candidate_id]
            candidate_counters["raw_rows"] = candidate_counters.get("raw_rows", 0) + row_multiplicity
            candidate_counters["duplicate_rows"] = candidate_counters.get("duplicate_rows", 0) + row_multiplicity - 1
            if timestamp_int is None:
                candidate_counters["invalid_timestamp_rows"] = candidate_counters.get("invalid_timestamp_rows", 0) + row_multiplicity
                continue
            try:
                x, y, z = (float(fields[index]) for index in (3, 4, 5))
            except (TypeError, ValueError):
                candidate_counters["invalid_signal_rows"] = candidate_counters.get("invalid_signal_rows", 0) + 1
                continue
            first_timestamp = candidate_counters.get("first_raw_timestamp_ms")
            last_timestamp = candidate_counters.get("last_raw_timestamp_ms")
            candidate_counters["first_raw_timestamp_ms"] = timestamp_int if first_timestamp is None else min(first_timestamp, timestamp_int)
            candidate_counters["last_raw_timestamp_ms"] = timestamp_int if last_timestamp is None else max(last_timestamp, timestamp_int)
            timestamps_pending[candidate_id].append(timestamp_int)
            magnitudes_pending[candidate_id].append(float(np.sqrt(x * x + y * y + z * z)))
            if len(timestamps_pending[candidate_id]) >= batch_points:
                flush(candidate_id)

    result: dict[str, tuple[np.ndarray, np.ndarray, dict[str, int]]] = {}
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        flush(candidate_id)
        result[candidate_id] = (
            np.concatenate(timestamp_parts[candidate_id]) if timestamp_parts[candidate_id] else np.array([], dtype=np.int64),
            np.concatenate(magnitude_parts[candidate_id]) if magnitude_parts[candidate_id] else np.array([], dtype=float),
            counters[candidate_id],
        )
    return result


def export_patient_day(
    archive_dir: Path,
    patient_id: str,
    local_date: str,
    candidates: list[pd.Series],
) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    output_path = archive_dir / patient_archive_name(patient_id, local_date)
    log_path = archive_dir / f"{output_path.stem}.log"
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path

    partial_path = output_path.with_suffix(output_path.suffix + ".partial")
    if partial_path.exists():
        preserved_path = partial_path.with_name(partial_path.name + ".preserved")
        partial_path.replace(preserved_path)
        print(f"preserved_interrupted_archive={preserved_path}", flush=True)

    defaults_file = backup.make_mysql_defaults_file()
    try:
        dump_rc, compressor_rc, output_bytes = dump_day_first_per_timestamp(
            defaults_file,
            int(candidates[0]["window_start_ms"]),
            int(candidates[0]["window_end_ms_exclusive"]),
            output_path,
            log_path,
            sorted({str(row["device_id"]) for row in candidates}),
        )
    finally:
        defaults_file.unlink(missing_ok=True)
    if dump_rc != 0 or compressor_rc != 0 or not output_path.exists() or output_bytes <= 0:
        raise RuntimeError(
            f"archive export failed dump_rc={dump_rc} compressor_rc={compressor_rc} bytes={output_bytes}"
        )
    return output_path


def build_patient_level_table(candidates: pd.DataFrame, patient_days: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for patient_id in sorted(candidates["patient_id"].astype(str).unique()):
        candidate_group = candidates[candidates["patient_id"].astype(str).eq(patient_id)]
        day_group = patient_days[patient_days["patient_id"].astype(str).eq(patient_id)].copy()
        row: dict[str, Any] = {
            "patient_id": patient_id,
            "candidate_device_day_count": int(len(candidate_group)),
            "candidate_local_day_count": int(candidate_group["local_date"].nunique()),
            "completed_patient_day_count": int(len(day_group)),
            "completed_device_day_count": int(
                pd.to_numeric(day_group.get("source_device_day_count"), errors="coerce").sum()
            ) if not day_group.empty else 0,
            "total_valid_signal_minutes": int(
                pd.to_numeric(day_group.get("accelerometer_valid_signal_minutes"), errors="coerce").sum()
            ) if not day_group.empty else 0,
            "median_daily_coverage_fraction": float(
                pd.to_numeric(day_group.get("accelerometer_calendar_coverage_fraction"), errors="coerce").median()
            ) if not day_group.empty else np.nan,
            "mean_daily_coverage_fraction": float(
                pd.to_numeric(day_group.get("accelerometer_calendar_coverage_fraction"), errors="coerce").mean()
            ) if not day_group.empty else np.nan,
            "aggregation_rule": "median across completed patient-local days",
        }
        for feature_name in pilot.FEATURE_NAMES:
            values = pd.to_numeric(day_group.get(feature_name), errors="coerce") if not day_group.empty else pd.Series(dtype=float)
            row[f"acc_median_{feature_name}"] = float(values.median()) if values.notna().any() else np.nan
            row[f"acc_mean_{feature_name}"] = float(values.mean()) if values.notna().any() else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def build_patient_progress(candidates: pd.DataFrame, status: pd.DataFrame) -> pd.DataFrame:
    status_latest = status.drop_duplicates("candidate_id", keep="last") if not status.empty else status
    rows: list[dict[str, Any]] = []
    for patient_id, group in candidates.groupby("patient_id", sort=True):
        candidate_ids = set(group["candidate_id"].astype(str))
        current = status_latest[status_latest["candidate_id"].astype(str).isin(candidate_ids)] if not status_latest.empty else pd.DataFrame()
        counts = current.get("status", pd.Series(dtype=str)).astype(str).value_counts()
        completed = int(counts.get("features_calculated", 0))
        no_raw = int(counts.get("no_raw_rows", 0))
        errors = int(counts.get("error", 0))
        pending = int(len(group) - completed - no_raw)
        if pending > 0:
            patient_status = "pending"
        elif errors > 0:
            patient_status = "complete_with_errors"
        else:
            patient_status = "complete"
        rows.append(
            {
                "patient_id": patient_id,
                "candidate_device_day_count": len(group),
                "candidate_local_day_count": group["local_date"].nunique(),
                "completed_feature_days": completed,
                "candidate_days_without_raw_acc": no_raw,
                "failed_days": errors,
                "pending_days": pending,
                "patient_status": patient_status,
            }
        )
    return pd.DataFrame(rows)


def run(args: argparse.Namespace) -> None:
    output_dir = args.output_dir
    archive_dir = args.archive_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    pilot.configure_output_dir(output_dir)

    candidates = pilot.load_candidates(0)
    candidates["patient_id"] = candidates["patient_id"].map(normalize_patient_id)
    requested = {normalize_patient_id(value) for value in args.patient_ids} if args.patient_ids else set()
    if requested:
        candidates = candidates[candidates["patient_id"].isin(requested)].copy()
    candidates = candidates.sort_values(["patient_id", "local_date", "device_id"]).reset_index(drop=True)
    if candidates.empty:
        raise ValueError("No candidate movement days match the requested patient IDs")

    candidate_path = output_dir / "accelerometer_patient_sequential_candidates.csv"
    status_path = output_dir / "accelerometer_patient_sequential_status.csv"
    wide_path = output_dir / "accelerometer_patient_sequential_device_day_features.csv"
    long_path = output_dir / "accelerometer_patient_sequential_features_long.csv"
    patient_day_path = output_dir / "accelerometer_patient_sequential_patient_day_features.csv"
    patient_level_path = output_dir / "accelerometer_patient_sequential_patient_level_features.csv"
    progress_path = output_dir / "accelerometer_patient_sequential_patient_progress.csv"
    summary_path = output_dir / "accelerometer_patient_sequential_run_summary.csv"
    checkpoint_path = output_dir / "accelerometer_patient_sequential_checkpoint.json"
    readme_path = output_dir / "README_accelerometer_patient_sequential_pipeline.md"

    atomic_write_csv(candidates, candidate_path)
    pilot.write_catalog()
    status_rows = pd.read_csv(status_path, dtype=str).to_dict("records") if status_path.exists() else []
    wide_rows = pd.read_csv(wide_path, dtype=str).to_dict("records") if wide_path.exists() else []
    status_latest = pd.DataFrame(status_rows).drop_duplicates("candidate_id", keep="last") if status_rows else pd.DataFrame()
    completed_ids = set()
    if not status_latest.empty:
        completed_ids = set(
            status_latest.loc[
                status_latest["status"].astype(str).isin(["features_calculated", "no_raw_rows"]),
                "candidate_id",
            ].astype(str)
        )
    completed_ids |= {str(row["candidate_id"]) for row in wide_rows if row.get("candidate_id")}
    if args.force:
        selected_ids = set(candidates["candidate_id"].astype(str))
        completed_ids -= selected_ids
        status_rows = [row for row in status_rows if str(row.get("candidate_id", "")) not in selected_ids]
        wide_rows = [row for row in wide_rows if str(row.get("candidate_id", "")) not in selected_ids]

    def persist(current_patient: str = "") -> None:
        status_frame = pd.DataFrame(status_rows).drop_duplicates("candidate_id", keep="last") if status_rows else pd.DataFrame()
        wide_frame = pd.DataFrame(wide_rows).drop_duplicates("candidate_id", keep="last") if wide_rows else pd.DataFrame()
        patient_days = pilot.build_patient_day_features(wide_frame)
        patient_level = build_patient_level_table(candidates, patient_days)
        progress = build_patient_progress(candidates, status_frame)
        atomic_write_csv(status_frame, status_path)
        atomic_write_csv(wide_frame, wide_path)
        atomic_write_csv(patient_days, patient_day_path)
        atomic_write_csv(patient_level, patient_level_path)
        atomic_write_csv(progress, progress_path)
        if not wide_frame.empty:
            long_frame = pd.concat(
                [pilot.build_long(row) for row in wide_frame.to_dict("records")], ignore_index=True
            )
        else:
            long_frame = pd.DataFrame()
        atomic_write_csv(long_frame, long_path)
        status_counts = status_frame.get("status", pd.Series(dtype=str)).astype(str).value_counts().to_dict()
        summary = pd.DataFrame(
            [
                {"metric": "selected_patient_count", "value": candidates["patient_id"].nunique()},
                {"metric": "selected_patients", "value": ", ".join(sorted(candidates["patient_id"].unique()))},
                {"metric": "candidate_device_day_count", "value": len(candidates)},
                {"metric": "completed_device_day_features", "value": int(status_frame.get("status", pd.Series(dtype=str)).astype(str).eq("features_calculated").sum())},
                {"metric": "candidate_days_without_raw_acc", "value": int(status_frame.get("status", pd.Series(dtype=str)).astype(str).eq("no_raw_rows").sum())},
                {"metric": "failed_device_day_extractions", "value": int(status_frame.get("status", pd.Series(dtype=str)).astype(str).eq("error").sum())},
                {"metric": "pending_device_days", "value": len(candidates) - len(status_frame)},
                {"metric": "patient_level_rows", "value": len(patient_level)},
                {"metric": "current_patient", "value": current_patient},
                {"metric": "status_counts", "value": json.dumps(status_counts, sort_keys=True)},
                {"metric": "feature_count", "value": len(pilot.FEATURE_NAMES)},
            ]
        )
        atomic_write_csv(summary, summary_path)
        checkpoint_path.write_text(
            json.dumps(
                {
                    "current_patient": current_patient,
                    "completed_candidate_device_days": len(completed_ids),
                    "updated_at": pd.Timestamp.now(tz="UTC").isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    readme_path.write_text(
        """# Patient-Sequential General Accelerometer Pipeline

This workflow uses the plugin movement dictionary to select candidate
patient-device-local days. It processes patients sequentially: all candidate
days for one patient are extracted and merged into patient-level features before
the next patient begins.

For each candidate day, the complete local calendar day is exported, valid JSON
axes are parsed, vector and dynamic magnitude features are calculated, and
quality variables are retained. Missing time is not converted to zero movement.
The raw export keeps the first row by database `_id` for each `device_id +
timestamp` and records the number of rows collapsed at that timestamp. The
output contains no raw ACC rows; compressed timestamp-deduplicated archives are
retained on the external drive and feature files are written locally in this
directory.

The patient-level table uses the median across completed patient-local days and
also retains the mean. A patient can be marked `complete_with_errors` when every
candidate day was attempted but one or more days failed and require retry.
""",
        encoding="utf-8",
    )

    for patient_id, patient_group in candidates.groupby("patient_id", sort=True):
        print(
            f"patient_start patient={patient_id} candidate_days={patient_group['local_date'].nunique()} candidate_device_days={len(patient_group)}",
            flush=True,
        )
        for local_date, day_group in patient_group.groupby("local_date", sort=True):
            if args.through_date and str(local_date) > args.through_date:
                continue
            day_candidates = [row for _, row in day_group.iterrows()]
            if all(str(row["candidate_id"]) in completed_ids for row in day_candidates):
                print(f"day_skip patient={patient_id} date={local_date} reason=already_complete", flush=True)
                continue
            print(
                f"day_start patient={patient_id} date={local_date} devices={day_group['device_id'].nunique()}",
                flush=True,
            )
            try:
                source = find_archive(archive_dir, str(patient_id), str(local_date))
                if source is None:
                    source = export_patient_day(archive_dir, str(patient_id), str(local_date), day_candidates)
                parsed = (
                    parse_first_timestamp_archive(source, day_candidates, args.batch_points)
                    if source.name.endswith(".tsv.zst")
                    else archive_extractor.parse_archive(source, day_candidates, args.batch_points)
                )
                for candidate in day_candidates:
                    candidate_id = str(candidate["candidate_id"])
                    timestamps, magnitudes, counters = parsed[candidate_id]
                    status_row = archive_extractor.local_status_row(candidate, timestamps, counters)
                    if len(timestamps):
                        feature_row, chunk = pilot.analyze_day_arrays(candidate, timestamps, magnitudes, counters)
                        wide_rows.append(feature_row)
                        status_row["valid_signal_minutes"] = feature_row.get("accelerometer_valid_signal_minutes", 0)
                        status_row["duplicates_removed"] = feature_row.get("accelerometer_exact_duplicate_rows_removed", 0)
                    status_rows.append(status_row)
                    completed_ids.add(candidate_id)
                persist(str(patient_id))
                print(
                    f"day_complete patient={patient_id} date={local_date} device_days={len(day_candidates)}",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001
                error_text = str(exc)
                print(f"day_error patient={patient_id} date={local_date}: {error_text}", flush=True)
                for candidate in day_candidates:
                    status_rows.append(
                        archive_extractor.local_status_row(
                            candidate, np.array([], dtype=np.int64), {}, error_text
                        )
                    )
                persist(str(patient_id))
        persist(str(patient_id))
        patient_progress = build_patient_progress(candidates, pd.DataFrame(status_rows))
        patient_row = patient_progress[patient_progress["patient_id"].astype(str).eq(str(patient_id))]
        print(f"patient_complete {patient_row.to_dict('records')}", flush=True)

    persist("")
    print(f"output_directory: {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patient-id", dest="patient_ids", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--batch-points", type=int, default=100_000)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess selected patients even when their candidate days already have saved status rows.",
    )
    parser.add_argument(
        "--through-date",
        help="Optional inclusive local date limit for a bounded sequential run, formatted YYYY-MM-DD.",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
