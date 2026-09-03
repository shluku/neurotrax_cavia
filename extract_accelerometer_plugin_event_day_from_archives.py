"""Export mapped ACC event-days and calculate features from local SQL archives.

The remote ACC table is indexed by timestamp first and is too slow for
device-specific Python queries. This workflow exports one local calendar day
at a time with mysqldump, keeps the compressed archive on the external drive,
and performs feature calculation locally. It is resumable at the
patient-device-day level.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import backup_accelerometer_by_day as backup
import extract_accelerometer_plugin_event_day_pilot as pilot
from convert_sql_zst_backup_to_parquet import parse_values


ROOT = Path(__file__).parent
DEFAULT_OUTPUT_DIR = ROOT / "output/analysis_candidates/accelerometer_all_mapped_event_day_features"
DEFAULT_ARCHIVE_DIR = Path(
    "/Volumes/SENSORDATA_MAIN/sensordata_backup/motion_accelerometer/plugin_event_day_sql_zst"
)


def iter_dump_rows(source: Path):
    process = subprocess.Popen([str(backup.ZSTD), "-dc", str(source)], stdout=subprocess.PIPE)
    assert process.stdout is not None
    try:
        for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace")
            if "INSERT INTO" not in line or "VALUES" not in line:
                continue
            yield from parse_values(line)
    finally:
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"zstd failed for {source} with return code {return_code}")


def archive_name(local_date: str) -> str:
    end_date = (pd.Timestamp(local_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    return f"accelerometer_{local_date}_to_{end_date}_mapped81.sql.zst"


def parse_archive(
    source: Path,
    candidates: list[pd.Series],
    batch_points: int,
) -> dict[str, tuple[np.ndarray, np.ndarray, dict[str, int]]]:
    """Parse one daily dump into compact arrays keyed by candidate ID."""
    device_to_ids: dict[str, list[str]] = {}
    for candidate in candidates:
        device_to_ids.setdefault(str(candidate["device_id"]), []).append(str(candidate["candidate_id"]))

    timestamp_parts: dict[str, list[np.ndarray]] = {str(c["candidate_id"]): [] for c in candidates}
    magnitude_parts: dict[str, list[np.ndarray]] = {str(c["candidate_id"]): [] for c in candidates}
    timestamps_pending: dict[str, list[int]] = {str(c["candidate_id"]): [] for c in candidates}
    magnitudes_pending: dict[str, list[float]] = {str(c["candidate_id"]): [] for c in candidates}
    counters: dict[str, Counter[str]] = {str(c["candidate_id"]): Counter() for c in candidates}
    seen_timestamps: dict[str, set[int]] = {str(c["device_id"]): set() for c in candidates}

    def flush(candidate_id: str) -> None:
        if not timestamps_pending[candidate_id]:
            return
        timestamp_parts[candidate_id].append(np.asarray(timestamps_pending[candidate_id], dtype=np.int64))
        magnitude_parts[candidate_id].append(np.asarray(magnitudes_pending[candidate_id], dtype=float))
        timestamps_pending[candidate_id].clear()
        magnitudes_pending[candidate_id].clear()

    for row in iter_dump_rows(source):
        if len(row) < 4:
            continue
        device_id = str(row[2] or "").strip()
        candidate_ids = device_to_ids.get(device_id, [])
        if not candidate_ids:
            continue
        try:
            timestamp = float(row[1])
        except (TypeError, ValueError):
            timestamp = float("nan")
        payload: dict[str, Any]
        try:
            payload = json.loads(str(row[3])) if row[3] not in (None, "") else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
        try:
            x = float(payload.get("double_values_0"))
            y = float(payload.get("double_values_1"))
            z = float(payload.get("double_values_2"))
        except (TypeError, ValueError):
            x = y = z = float("nan")
        invalid_timestamp = not np.isfinite(timestamp)
        invalid_signal = not all(np.isfinite(value) for value in (x, y, z))
        for candidate_id in candidate_ids:
            candidate_counters = counters[candidate_id]
            candidate_counters["raw_rows"] += 1
            if invalid_timestamp:
                candidate_counters["invalid_timestamp_rows"] += 1
                continue
            if invalid_signal:
                candidate_counters["invalid_signal_rows"] += 1
                continue
            timestamp_int = int(timestamp)
            if timestamp_int in seen_timestamps[device_id]:
                candidate_counters["duplicate_rows"] += 1
                continue
            seen_timestamps[device_id].add(timestamp_int)
            existing_first = candidate_counters.get("first_raw_timestamp_ms")
            existing_last = candidate_counters.get("last_raw_timestamp_ms")
            candidate_counters["first_raw_timestamp_ms"] = (
                timestamp_int if existing_first is None else min(int(existing_first), timestamp_int)
            )
            candidate_counters["last_raw_timestamp_ms"] = (
                timestamp_int if existing_last is None else max(int(existing_last), timestamp_int)
            )
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
            dict(counters[candidate_id]),
        )
    return result


def local_status_row(
    candidate: pd.Series,
    timestamps: np.ndarray,
    counters: dict[str, int],
    error_message: str = "",
) -> dict[str, Any]:
    raw_rows = int(counters.get("raw_rows", 0))
    valid_rows = int(len(timestamps))
    if error_message:
        status = "error"
    elif valid_rows:
        status = "features_calculated"
    elif raw_rows:
        status = "no_valid_numeric_signal"
    else:
        status = "no_raw_rows"
    return {
        "candidate_id": candidate["candidate_id"],
        "patient_id": candidate["patient_id"],
        "device_id": candidate["device_id"],
        "local_date": candidate["local_date"],
        "window_start_local": candidate["window_start_local"],
        "window_end_local_exclusive": candidate["window_end_local_exclusive"],
        "plugin_event_count": candidate.get("plugin_event_count", ""),
        "plugin_dominant_movement_evidence_class": candidate.get("dominant_movement_evidence_class", ""),
        "preflight_raw_row_count": raw_rows,
        "status": status,
        "raw_rows": raw_rows,
        "valid_numeric_rows": valid_rows,
        "invalid_timestamp_rows": counters.get("invalid_timestamp_rows", 0),
        "invalid_signal_rows": counters.get("invalid_signal_rows", 0),
        "duplicates_removed": counters.get("duplicate_rows", 0),
        "valid_signal_minutes": 0,
        "error_message": error_message,
    }


def run(args: argparse.Namespace) -> None:
    pilot.configure_output_dir(args.output_dir)
    pilot.OUT_DIR.mkdir(parents=True, exist_ok=True)
    args.archive_dir.mkdir(parents=True, exist_ok=True)
    candidates = pilot.load_candidates(0)
    candidates.to_csv(pilot.CANDIDATE_PATH, index=False)
    pilot.write_catalog()

    status_df = pd.read_csv(pilot.STATUS_PATH, dtype=str) if pilot.STATUS_PATH.exists() else pd.DataFrame()
    wide_df = pd.read_csv(pilot.FEATURE_WIDE_PATH, dtype=str) if pilot.FEATURE_WIDE_PATH.exists() else pd.DataFrame()
    preflight_df = pd.read_csv(pilot.PREFLIGHT_PATH, dtype=str) if pilot.PREFLIGHT_PATH.exists() else pd.DataFrame()
    feature_rows = wide_df.to_dict("records") if not wide_df.empty else []
    status_rows = status_df.to_dict("records") if not status_df.empty else []
    completed_ids = set()
    if not status_df.empty:
        completed_ids |= set(status_df.loc[status_df["status"].eq("features_calculated"), "candidate_id"])
        completed_ids |= set(status_df.loc[status_df["status"].eq("no_raw_rows"), "candidate_id"])
    if not wide_df.empty and "candidate_id" in wide_df.columns:
        completed_ids |= set(wide_df["candidate_id"].astype(str))

    preflight_rows: dict[str, dict[str, Any]] = {
        str(row["candidate_id"]): {
            "candidate_id": row["candidate_id"],
            "patient_id": row["patient_id"],
            "device_id": row["device_id"],
            "local_date": row["local_date"],
            "window_start_local": row["window_start_local"],
            "window_end_local_exclusive": row["window_end_local_exclusive"],
            "plugin_event_count": row.get("plugin_event_count", ""),
            "plugin_dominant_movement_evidence_class": row.get("dominant_movement_evidence_class", ""),
            "raw_row_count": "",
            "first_raw_time_local": "",
            "last_raw_time_local": "",
            "raw_data_available": "",
            "preflight_status": "pending",
            "error_message": "",
        }
        for _, row in candidates.iterrows()
    }
    if not preflight_df.empty and "candidate_id" in preflight_df.columns:
        for row in preflight_df.to_dict("records"):
            if str(row.get("candidate_id", "")) in preflight_rows:
                preflight_rows[str(row["candidate_id"])].update(row)

    def persist() -> None:
        current_preflight = pd.DataFrame(list(preflight_rows.values()))
        current_status = pd.DataFrame(status_rows).drop_duplicates("candidate_id", keep="last") if status_rows else pd.DataFrame()
        current_wide = pd.DataFrame(feature_rows).drop_duplicates("candidate_id", keep="last") if feature_rows else pd.DataFrame()
        current_preflight.to_csv(pilot.PREFLIGHT_PATH, index=False)
        current_status.to_csv(pilot.STATUS_PATH, index=False)
        current_wide.to_csv(pilot.FEATURE_WIDE_PATH, index=False)
        pilot.build_patient_day_features(current_wide).to_csv(pilot.PATIENT_DAY_PATH, index=False)
        pilot.write_summary(candidates, current_preflight, current_status, current_wide)
        pilot.write_readme(candidates, current_preflight, current_status)

    unresolved = candidates[~candidates["candidate_id"].isin(completed_ids)].copy()
    unresolved_dates = sorted(unresolved["local_date"].astype(str).unique())
    if args.max_days > 0:
        unresolved = unresolved[unresolved["local_date"].astype(str).isin(unresolved_dates[: args.max_days])].copy()
    candidate_positions = {row["candidate_id"]: index for index, (_, row) in enumerate(candidates.iterrows(), start=1)}
    for local_date, day_group in unresolved.groupby("local_date", sort=True):
        day_candidates = [row for _, row in day_group.sort_values(["device_id", "candidate_id"]).iterrows()]
        archive_path = args.archive_dir / archive_name(str(local_date))
        log_path = args.archive_dir / f"{archive_path.stem}.log"
        print(
            f"day_start {local_date} candidates={len(day_candidates)} devices={day_group['device_id'].nunique()} archive={archive_path}",
            flush=True,
        )
        try:
            if not archive_path.exists():
                partial_path = archive_path.with_suffix(archive_path.suffix + ".partial")
                if partial_path.exists():
                    if not args.retry_partials:
                        raise RuntimeError(f"partial archive exists; inspect before retrying: {partial_path}")
                    preserved_path = partial_path.with_name(partial_path.name + ".preserved")
                    partial_path.replace(preserved_path)
                    print(f"preserved_interrupted_archive={preserved_path}", flush=True)
                defaults_file = backup.make_mysql_defaults_file()
                try:
                    dump_rc, compressor_rc, output_bytes = backup.dump_day(
                        defaults_file,
                        int(day_candidates[0]["window_start_ms"]),
                        int(day_candidates[0]["window_end_ms_exclusive"]),
                        archive_path,
                        log_path,
                        True,
                        sorted(day_group["device_id"].astype(str).unique()),
                    )
                finally:
                    defaults_file.unlink(missing_ok=True)
                if dump_rc != 0 or compressor_rc != 0 or not archive_path.exists() or output_bytes <= 0:
                    raise RuntimeError(
                        f"archive export failed dump_rc={dump_rc} compressor_rc={compressor_rc} bytes={output_bytes}"
                    )
            parsed = parse_archive(archive_path, day_candidates, args.batch_points)
            for candidate in day_candidates:
                candidate_id = str(candidate["candidate_id"])
                timestamps, magnitudes, counters = parsed[candidate_id]
                feature_row = None
                status_row = local_status_row(candidate, timestamps, counters)
                if len(timestamps):
                    feature_row, chunk = pilot.analyze_day_arrays(candidate, timestamps, magnitudes, counters)
                    status_row["valid_signal_minutes"] = feature_row.get("accelerometer_valid_signal_minutes", 0)
                    status_row["duplicates_removed"] = feature_row.get("accelerometer_exact_duplicate_rows_removed", 0)
                    if not chunk.empty:
                        pilot.append_frame(pilot.CHUNK_PATH, chunk)
                    feature_rows.append(feature_row)
                preflight_rows[candidate_id].update(
                    {
                        "raw_row_count": counters.get("raw_rows", 0),
                        "first_raw_time_local": pilot.local_text(counters.get("first_raw_timestamp_ms")),
                        "last_raw_time_local": pilot.local_text(counters.get("last_raw_timestamp_ms")),
                        "raw_data_available": int(counters.get("raw_rows", 0) > 0),
                        "preflight_status": "has_raw_rows" if counters.get("raw_rows", 0) else "no_raw_rows",
                        "error_message": "",
                    }
                )
                status_rows.append(status_row)
                completed_ids.add(candidate_id)
                persist()
                print(
                    f"complete {candidate_positions[candidate_id]}/{len(candidates)} patient={candidate['patient_id']} date={local_date} raw={counters.get('raw_rows', 0):,} valid_minutes={status_row['valid_signal_minutes']}",
                    flush=True,
                )
        except Exception as exc:  # noqa: BLE001
            error_text = str(exc)
            print(f"day_error local_date={local_date}: {error_text}", flush=True)
            for candidate in day_candidates:
                candidate_id = str(candidate["candidate_id"])
                status_rows.append(local_status_row(candidate, np.array([], dtype=np.int64), {}, error_text))
                preflight_rows[candidate_id].update(
                    {"preflight_status": "error", "error_message": error_text}
                )
            persist()

    final_status = pd.DataFrame(status_rows).drop_duplicates("candidate_id", keep="last") if status_rows else pd.DataFrame()
    final_wide = pd.DataFrame(feature_rows).drop_duplicates("candidate_id", keep="last") if feature_rows else pd.DataFrame()
    final_preflight = pd.DataFrame(list(preflight_rows.values()))
    final_status.to_csv(pilot.STATUS_PATH, index=False)
    final_wide.to_csv(pilot.FEATURE_WIDE_PATH, index=False)
    final_preflight.to_csv(pilot.PREFLIGHT_PATH, index=False)
    if not final_wide.empty:
        final_long = pd.DataFrame(
            [
                {
                    "candidate_id": row["candidate_id"],
                    "patient_id": row["patient_id"],
                    "device_id": row["device_id"],
                    "local_date": row["local_date"],
                    "feature_name": name,
                    "feature_group": pilot.FEATURE_GROUPS[name],
                    "value": row.get(name, float("nan")),
                }
                for _, row in final_wide.iterrows()
                for name in pilot.FEATURE_NAMES
            ]
        )
        final_long.to_csv(pilot.FEATURE_LONG_PATH, index=False)
    pilot.build_patient_day_features(final_wide).to_csv(pilot.PATIENT_DAY_PATH, index=False)
    pilot.write_summary(candidates, final_preflight, final_status, final_wide)
    pilot.write_readme(candidates, final_preflight, final_status)
    print("accelerometer_plugin_event_day_archive_extraction_complete", flush=True)
    print(f"candidate_device_days: {len(candidates)}", flush=True)
    print(
        f"features_calculated: {int(final_status['status'].eq('features_calculated').sum()) if not final_status.empty else 0}",
        flush=True,
    )
    print(f"output_directory: {pilot.OUT_DIR}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--batch-points", type=int, default=100_000)
    parser.add_argument("--max-days", type=int, default=0, help="Optional bounded date count for a resumable test run.")
    parser.add_argument(
        "--retry-partials",
        action="store_true",
        help="Preserve interrupted .partial archives with a .preserved suffix, then retry the export.",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
