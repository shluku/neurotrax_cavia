from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from download_accelerometer_24h_pilot import ms_to_local
from main import connect_sensordata_db


ROOT = Path(__file__).parent
PATIENT_QC_PATH = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_patient.csv"
DEVICE_QC_PATH = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_device_window.csv"
OUT_DIR = (
    ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_top10_sensor_anchor_raw_probe"
)
EXCLUDED_SUBJECTS = {"001"}
TABLE_NAME = "accelerometer"
DAY_MS = 24 * 60 * 60 * 1000
HOUR_MS = 60 * 60 * 1000
MINUTE_MS = 60 * 1000


def as_int_ms(value: Any) -> int | None:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return int(parsed)


def load_top_patients(limit: int) -> pd.DataFrame:
    df = pd.read_csv(PATIENT_QC_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].astype(str).str.zfill(3)
    df["global_T1_num"] = pd.to_numeric(df["global_T1"], errors="coerce")
    df = df.dropna(subset=["Subject_ID_D", "global_T1_num", "T1_date_iso", "selected_device_id"]).copy()
    df = df[~df["Subject_ID_D"].isin(EXCLUDED_SUBJECTS)].copy()
    df = df[df["has_sensor_accelerometer_metadata_after_T1"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    df = df[df["selected_device_id"].astype(str).str.strip().ne("")]
    return df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True]).head(limit).copy()


def load_metadata_candidates(subject_id: str, selected_device_id: str, max_candidates: int) -> pd.DataFrame:
    df = pd.read_csv(DEVICE_QC_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].astype(str).str.zfill(3)
    df = df[df["Subject_ID_D"].eq(subject_id)].copy()
    df = df[df["has_metadata_after_T1"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    df["window_start_ms_num"] = pd.to_numeric(df["window_start_ms"], errors="coerce")
    df["days_first_available_num"] = pd.to_numeric(df["days_first_available_after_T1"], errors="coerce")
    df["n_rows_num"] = pd.to_numeric(df["n_rows"], errors="coerce").fillna(0)
    df["selected_device_priority"] = (df["device_id"].astype(str) != selected_device_id).astype(int)
    df = df.dropna(subset=["window_start_ms_num"]).copy()
    df = df.sort_values(
        ["selected_device_priority", "days_first_available_num", "window_start_ms_num", "n_rows_num"],
        ascending=[True, True, True, False],
    )
    return df.head(max_candidates).copy()


def fetch_raw_probe(cur, device_id: str, start_ms: int, end_ms: int, sample_limit: int = 1000) -> dict[str, Any]:
    cur.execute(
        f"""
        SELECT timestamp
        FROM `{TABLE_NAME}`
        WHERE timestamp >= %s
          AND timestamp < %s
          AND device_id = %s
        ORDER BY timestamp ASC
        LIMIT {int(sample_limit)}
        """,
        (int(start_ms), int(end_ms), device_id),
    )
    timestamps = [as_int_ms(row.get("timestamp")) for row in cur.fetchall()]
    timestamps = [value for value in timestamps if value is not None]
    sample_rows = len(timestamps)
    first_ts = timestamps[0] if timestamps else None
    last_ts = timestamps[-1] if timestamps else None
    return {
        "sampled_rows": sample_rows,
        "sample_limit": sample_limit,
        "probe_hit_limit": sample_rows >= sample_limit,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "first_local": ms_to_local(first_ts),
        "last_local": ms_to_local(last_ts),
    }


def fetch_daily_jump_probe(cur, device_id: str, start_ms: int, end_ms: int, sample_limit: int = 1000) -> dict[str, Any]:
    for day_index, anchor_ms in enumerate(range(int(start_ms), int(end_ms), DAY_MS), start=1):
        probe_start_ms = max(anchor_ms - 5 * MINUTE_MS, int(start_ms))
        probe_end_ms = min(anchor_ms + 15 * MINUTE_MS, int(end_ms))
        if probe_start_ms >= probe_end_ms:
            continue
        cur.execute(
            f"""
            SELECT timestamp
            FROM `{TABLE_NAME}`
            WHERE timestamp >= %s
              AND timestamp < %s
              AND device_id = %s
            ORDER BY timestamp ASC
            LIMIT {int(sample_limit)}
            """,
            (int(probe_start_ms), int(probe_end_ms), device_id),
        )
        timestamps = [as_int_ms(row.get("timestamp")) for row in cur.fetchall()]
        timestamps = [value for value in timestamps if value is not None]
        if timestamps:
            first_ts = timestamps[0]
            return {
                "hit": True,
                "day_index": day_index,
                "sampled_rows": len(timestamps),
                "sample_limit": sample_limit,
                "hit_sample_limit": len(timestamps) >= sample_limit,
                "probe_start_ms": probe_start_ms,
                "probe_end_ms": probe_end_ms,
                "probe_start_local": ms_to_local(probe_start_ms),
                "probe_end_local": ms_to_local(probe_end_ms),
                "day_start_ms": first_ts,
                "day_end_ms": first_ts + DAY_MS,
                "day_start_local": ms_to_local(first_ts),
                "day_end_local": ms_to_local(first_ts + DAY_MS),
                "first_ts": first_ts,
                "first_local": ms_to_local(first_ts),
            }
    return {
        "hit": False,
        "day_index": "",
        "sampled_rows": "",
        "sample_limit": sample_limit,
        "hit_sample_limit": "",
        "probe_start_ms": "",
        "probe_end_ms": "",
        "probe_start_local": "",
        "probe_end_local": "",
        "day_start_ms": "",
        "day_end_ms": "",
        "day_start_local": "",
        "day_end_local": "",
        "first_ts": "",
        "first_local": "",
    }


def hourly_existence_probes(cur, subject_id: str, device_id: str, window_start_ms: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hour_index in range(24):
        start_ms = window_start_ms + hour_index * HOUR_MS
        end_ms = start_ms + HOUR_MS
        cur.execute(
            f"""
            SELECT timestamp
            FROM `{TABLE_NAME}`
            WHERE timestamp >= %s
              AND timestamp < %s
              AND device_id = %s
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (int(start_ms), int(end_ms), device_id),
        )
        first = cur.fetchone()
        first_ts = as_int_ms(first.get("timestamp")) if first else None
        rows.append(
            {
                "Subject_ID_D": subject_id,
                "device_id": device_id,
                "candidate_window_start_ms": window_start_ms,
                "hour_index": hour_index,
                "hour_start_ms": start_ms,
                "hour_end_ms": end_ms,
                "hour_start_local": ms_to_local(start_ms),
                "hour_end_local": ms_to_local(end_ms),
                "has_raw_rows": first_ts is not None,
                "first_raw_ts_in_hour": first_ts or "",
                "first_raw_local_in_hour": ms_to_local(first_ts),
            }
        )
    return rows


def validate_patient(
    conn,
    patient: pd.Series,
    max_candidates: int,
    run_hourly_probes: bool,
    run_daily_jump_fallback: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    subject_id = str(patient["Subject_ID_D"])
    selected_device_id = str(patient["selected_device_id"]).strip()
    candidates = load_metadata_candidates(subject_id, selected_device_id, max_candidates=max_candidates)
    base = {
        "Subject_ID_D": subject_id,
        "Subject_ID_N": patient.get("Subject_ID_N", ""),
        "global_T1": patient.get("global_T1", ""),
        "T1_date_iso": patient.get("T1_date_iso", ""),
        "selected_device_id": selected_device_id,
        "metadata_candidates_checked": len(candidates),
    }
    candidate_rows: list[dict[str, Any]] = []
    hourly_rows: list[dict[str, Any]] = []
    if candidates.empty:
        return {**base, "window_status": "missing_no_sensor_accelerometer_metadata_candidates"}, candidate_rows, hourly_rows

    cur = conn.cursor(dictionary=True)
    try:
        daily_fallback_candidates: list[tuple[int, pd.Series, str, dict[str, Any], int, int, dict[str, Any]]] = []
        for candidate_index, (_, candidate) in enumerate(candidates.iterrows(), start=1):
            device_id = str(candidate["device_id"]).strip()
            anchor_ms = as_int_ms(candidate.get("first_ts")) or as_int_ms(candidate.get("window_start_ms"))
            metadata_window_start_ms = as_int_ms(candidate.get("window_start_ms"))
            metadata_window_end_ms = as_int_ms(candidate.get("window_end_ms"))
            if anchor_ms is None:
                continue
            probe_start = anchor_ms - 5 * MINUTE_MS
            probe_end = anchor_ms + 15 * MINUTE_MS
            raw_probe = fetch_raw_probe(cur, device_id, probe_start, probe_end)
            candidate_row = {
                **base,
                "candidate_index": candidate_index,
                "candidate_device_id": device_id,
                "candidate_is_selected_device": device_id == selected_device_id,
                "metadata_days_first_available_after_T1": candidate.get("days_first_available_after_T1", ""),
                "metadata_window_start_ms": metadata_window_start_ms or "",
                "metadata_window_start_local": candidate.get("window_start_local", ""),
                "metadata_window_end_ms": metadata_window_end_ms or "",
                "metadata_window_end_local": candidate.get("window_end_local", ""),
                "metadata_n_rows": candidate.get("n_rows", ""),
                "metadata_qc_readiness_level": candidate.get("qc_readiness_level", ""),
                "raw_probe_start_ms": probe_start,
                "raw_probe_end_ms": probe_end,
                "raw_probe_start_local": ms_to_local(probe_start),
                "raw_probe_end_local": ms_to_local(probe_end),
                "raw_probe_sampled_rows_20min": raw_probe["sampled_rows"],
                "raw_probe_sample_limit": raw_probe["sample_limit"],
                "raw_probe_hit_sample_limit": raw_probe["probe_hit_limit"],
                "raw_probe_first_ts": raw_probe["first_ts"] or "",
                "raw_probe_first_local": raw_probe["first_local"],
                "raw_probe_last_ts": raw_probe["last_ts"] or "",
                "raw_probe_last_local": raw_probe["last_local"],
                "daily_jump_fallback_used": False,
                "daily_jump_hit": "",
                "daily_jump_day_index": "",
                "daily_jump_day_start_ms": "",
                "daily_jump_day_start_local": "",
                "daily_jump_day_end_ms": "",
                "daily_jump_day_end_local": "",
                "daily_jump_probe_start_ms": "",
                "daily_jump_probe_start_local": "",
                "daily_jump_probe_end_ms": "",
                "daily_jump_probe_end_local": "",
                "daily_jump_sampled_rows": "",
                "daily_jump_hit_sample_limit": "",
                "daily_jump_first_raw_ts": "",
                "daily_jump_first_raw_local": "",
            }
            if raw_probe["first_ts"] is None:
                if run_daily_jump_fallback and metadata_window_start_ms is not None and metadata_window_end_ms is not None:
                    daily_fallback_candidates.append(
                        (
                            candidate_index,
                            candidate,
                            device_id,
                            candidate_row,
                            metadata_window_start_ms,
                            metadata_window_end_ms,
                            raw_probe,
                        )
                    )
                candidate_rows.append(candidate_row)
                continue
            candidate_rows.append(candidate_row)

            window_start_ms = int(raw_probe["first_ts"])
            window_end_ms = window_start_ms + DAY_MS
            active_hours: int | str = ""
            quality = "raw_window_anchor_validated_hourly_probe_deferred"
            if run_hourly_probes:
                hourly = hourly_existence_probes(cur, subject_id, device_id, window_start_ms)
                hourly_rows.extend(hourly)
                active_hours = sum(1 for row in hourly if row["has_raw_rows"])
                quality = "valid_raw_24h_window_candidate" if active_hours >= 6 else "limited_hour_coverage_raw_window"
            return {
                **base,
                "window_status": "raw_window_found_from_sensor_anchor_probe",
                "window_quality": quality,
                "candidate_device_id": device_id,
                "candidate_is_selected_device": device_id == selected_device_id,
                "metadata_candidate_index_used": candidate_index,
                "metadata_days_first_available_after_T1": candidate.get("days_first_available_after_T1", ""),
                "metadata_window_start_ms": as_int_ms(candidate.get("window_start_ms")) or "",
                "metadata_window_start_local": candidate.get("window_start_local", ""),
                "metadata_window_end_ms": as_int_ms(candidate.get("window_end_ms")) or "",
                "metadata_window_end_local": candidate.get("window_end_local", ""),
                "raw_probe_sampled_rows_20min": raw_probe["sampled_rows"],
                "raw_probe_sample_limit": raw_probe["sample_limit"],
                "raw_probe_hit_sample_limit": raw_probe["probe_hit_limit"],
                "candidate_window_start_ms": window_start_ms,
                "candidate_window_end_ms": window_end_ms,
                "candidate_window_start_local": ms_to_local(window_start_ms),
                "candidate_window_end_local": ms_to_local(window_end_ms),
                "active_hour_bins_in_24h_probe": active_hours,
                "raw_rows_in_24h": "",
                "raw_rows_count_status": "deferred_exact_24h_count",
                "interpretation": "validated by sensor_accelerometer metadata anchor plus short raw accelerometer probes",
            }, candidate_rows, hourly_rows

        for (
            candidate_index,
            candidate,
            device_id,
            candidate_row,
            metadata_window_start_ms,
            metadata_window_end_ms,
            raw_probe,
        ) in daily_fallback_candidates:
            daily_probe = fetch_daily_jump_probe(cur, device_id, metadata_window_start_ms, metadata_window_end_ms)
            candidate_row.update(
                {
                    "daily_jump_fallback_used": True,
                    "daily_jump_hit": daily_probe["hit"],
                    "daily_jump_day_index": daily_probe["day_index"],
                    "daily_jump_day_start_ms": daily_probe["day_start_ms"],
                    "daily_jump_day_start_local": daily_probe["day_start_local"],
                    "daily_jump_day_end_ms": daily_probe["day_end_ms"],
                    "daily_jump_day_end_local": daily_probe["day_end_local"],
                    "daily_jump_probe_start_ms": daily_probe["probe_start_ms"],
                    "daily_jump_probe_start_local": daily_probe["probe_start_local"],
                    "daily_jump_probe_end_ms": daily_probe["probe_end_ms"],
                    "daily_jump_probe_end_local": daily_probe["probe_end_local"],
                    "daily_jump_sampled_rows": daily_probe["sampled_rows"],
                    "daily_jump_hit_sample_limit": daily_probe["hit_sample_limit"],
                    "daily_jump_first_raw_ts": daily_probe["first_ts"],
                    "daily_jump_first_raw_local": daily_probe["first_local"],
                }
            )
            if not daily_probe["hit"]:
                continue

            window_start_ms = int(daily_probe["day_start_ms"])
            window_end_ms = int(daily_probe["day_end_ms"])
            return {
                **base,
                "window_status": "raw_window_found_from_sensor_daily_jump_probe",
                "window_quality": "raw_window_day_validated_hourly_probe_deferred",
                "candidate_device_id": device_id,
                "candidate_is_selected_device": device_id == selected_device_id,
                "metadata_candidate_index_used": candidate_index,
                "metadata_days_first_available_after_T1": candidate.get("days_first_available_after_T1", ""),
                "metadata_window_start_ms": metadata_window_start_ms or "",
                "metadata_window_start_local": candidate.get("window_start_local", ""),
                "metadata_window_end_ms": metadata_window_end_ms or "",
                "metadata_window_end_local": candidate.get("window_end_local", ""),
                "raw_probe_sampled_rows_20min": raw_probe["sampled_rows"],
                "raw_probe_sample_limit": raw_probe["sample_limit"],
                "raw_probe_hit_sample_limit": raw_probe["probe_hit_limit"],
                "daily_jump_day_index": daily_probe["day_index"],
                "daily_jump_sampled_rows": daily_probe["sampled_rows"],
                "daily_jump_hit_sample_limit": daily_probe["hit_sample_limit"],
                "daily_jump_first_raw_ts": daily_probe["first_ts"],
                "daily_jump_first_raw_local": daily_probe["first_local"],
                "candidate_window_start_ms": window_start_ms,
                "candidate_window_end_ms": window_end_ms,
                "candidate_window_start_local": ms_to_local(window_start_ms),
                "candidate_window_end_local": ms_to_local(window_end_ms),
                "active_hour_bins_in_24h_probe": "",
                "raw_rows_in_24h": "",
                "raw_rows_count_status": "deferred_exact_24h_count",
                "interpretation": "validated by sensor_accelerometer metadata window plus 24h raw accelerometer jump probe",
            }, candidate_rows, hourly_rows
    finally:
        cur.close()

    return {
        **base,
        "window_status": "missing_no_raw_rows_near_checked_sensor_accelerometer_anchors",
        "window_quality": "no_raw_window_found_in_metadata_probe",
        "raw_rows_in_24h": "",
        "raw_rows_count_status": "not_applicable_no_raw_probe_hit",
    }, candidate_rows, hourly_rows


def build_readme(patient_df: pd.DataFrame, candidate_df: pd.DataFrame, hourly_df: pd.DataFrame, patient_csv: Path) -> str:
    status_counts = patient_df["window_status"].value_counts().to_dict() if "window_status" in patient_df else {}
    status_text = "\n".join(f"- `{key}`: {value}" for key, value in status_counts.items())
    return f"""# Accelerometer Top-10 Sensor-Anchor Raw Probe Pilot

Date: 2026-07-21

Purpose:

- Validate candidate raw `accelerometer` 24-hour windows for the top 10 T1-score patients.
- Use lightweight `sensor_accelerometer` metadata as the candidate-window generator.
- Probe raw `accelerometer` only in short bounded windows around metadata timestamps.
- Avoid full raw-table discovery scans and avoid exact 24-hour row counts in this phase.

Output:

- Patient-level table: `{patient_csv}`
- Metadata candidate probe table: `accelerometer_top10_sensor_anchor_raw_probe_candidates.csv`
- Hourly raw existence detail: `accelerometer_top10_sensor_anchor_raw_probe_hourly.csv`

Rows:

- Patient rows: {len(patient_df)}
- Metadata candidates probed: {len(candidate_df)}
- Hourly probe rows: {len(hourly_df)}

Patient window status counts:

{status_text}

Window rule:

- Rank patients by descending `global_T1`.
- For each patient, read post-T1 `sensor_accelerometer` metadata candidates from `sensor_accelerometer_qc_by_device_window.csv`.
- Prefer the patient-level selected device first, then other patient devices by earliest metadata availability.
- For each metadata anchor, run a raw `accelerometer` probe from 5 minutes before to 15 minutes after the metadata timestamp.
- If raw rows are found, start the candidate 24-hour window at the first raw row in that short probe.
- If the short probe misses for every checked candidate, jump the same bounded probe forward in 24-hour steps; if a jump hits, use the first raw timestamp as the candidate 24-hour window start.
    - By default, record the candidate 24-hour start/end timestamps and defer deeper hourly coverage checks.
    - Optional hourly probes can be enabled later for selected candidate windows.

Important interpretation:

- `raw_probe_sampled_rows_20min` is a bounded sample count, not an exact count.
- `raw_probe_hit_sample_limit=True` means at least `raw_probe_sample_limit` rows exist in the 20-minute probe window.
- `daily_jump_fallback_used=True` means the short probe missed and the script tried bounded 24-hour-spaced probes within the metadata window.
- `active_hour_bins_in_24h_probe` is blank when hourly probes were deferred.
- `raw_rows_in_24h` is intentionally blank because exact 24-hour counts are deferred to the selected-window download/analysis phase.
- Missing raw rows near a metadata anchor means that metadata alone is not enough to prove raw accelerometer signal.
"""


def write_outputs(
    patient_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    hourly_rows: list[dict[str, Any]],
    patient_csv: Path,
    candidate_csv: Path,
    hourly_csv: Path,
    readme_path: Path,
) -> None:
    patient_df = pd.DataFrame(patient_rows)
    candidate_df = pd.DataFrame(candidate_rows)
    hourly_df = pd.DataFrame(hourly_rows)
    patient_df.to_csv(patient_csv, index=False)
    candidate_df.to_csv(candidate_csv, index=False)
    hourly_df.to_csv(hourly_csv, index=False)
    readme_path.write_text(build_readme(patient_df, candidate_df, hourly_df, patient_csv), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Top-10 accelerometer window validation using sensor metadata anchors and short raw probes.")
    parser.add_argument("--limit-patients", type=int, default=10)
    parser.add_argument("--max-candidates-per-patient", type=int, default=2)
    parser.add_argument("--hourly-probes", action="store_true", help="Run 24 hourly raw existence probes after a raw anchor hit.")
    parser.add_argument("--no-daily-jump-fallback", action="store_true", help="Disable 24-hour jump probes after a missed 20-minute probe.")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    patient_csv = args.out_dir / "accelerometer_top10_sensor_anchor_raw_probe_patient_windows.csv"
    candidate_csv = args.out_dir / "accelerometer_top10_sensor_anchor_raw_probe_candidates.csv"
    hourly_csv = args.out_dir / "accelerometer_top10_sensor_anchor_raw_probe_hourly.csv"
    readme_path = args.out_dir / "README_accelerometer_top10_sensor_anchor_raw_probe.md"

    patients = load_top_patients(args.limit_patients)
    patient_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    hourly_rows: list[dict[str, Any]] = []

    conn = connect_sensordata_db()
    try:
        for idx, (_, patient) in enumerate(patients.iterrows(), start=1):
            subject_id = str(patient["Subject_ID_D"])
            print(f"validating {idx}/{len(patients)} Subject_ID_D={subject_id} global_T1={patient.get('global_T1', '')}", flush=True)
            patient_row, patient_candidate_rows, patient_hourly_rows = validate_patient(
                conn,
                patient,
                max_candidates=args.max_candidates_per_patient,
                run_hourly_probes=args.hourly_probes,
                run_daily_jump_fallback=not args.no_daily_jump_fallback,
            )
            patient_rows.append(patient_row)
            candidate_rows.extend(patient_candidate_rows)
            hourly_rows.extend(patient_hourly_rows)
            write_outputs(patient_rows, candidate_rows, hourly_rows, patient_csv, candidate_csv, hourly_csv, readme_path)
    finally:
        conn.close()

    write_outputs(patient_rows, candidate_rows, hourly_rows, patient_csv, candidate_csv, hourly_csv, readme_path)
    patient_df = pd.DataFrame(patient_rows)

    print("accelerometer_top10_sensor_anchor_raw_probe_complete")
    print(f"patient_csv: {patient_csv}")
    print(f"candidate_csv: {candidate_csv}")
    print(f"hourly_csv: {hourly_csv}")
    print(f"readme: {readme_path}")
    if "window_status" in patient_df:
        print(patient_df["window_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
