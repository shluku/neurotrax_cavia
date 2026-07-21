from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from download_accelerometer_24h_pilot import ms_to_local
from main import connect_sensordata_db


ROOT = Path(__file__).parent
DEVICE_QC_PATH = ROOT / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_device_window.csv"
OUT_DIR = (
    ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_misses_weekly_backward_probe"
)
TABLE_NAME = "accelerometer"
MINUTE_MS = 60 * 1000
DAY_MS = 24 * 60 * 60 * 1000
WEEK_MS = 7 * DAY_MS


def as_int_ms(value: Any) -> int | None:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return int(parsed)


def load_candidate_windows(subjects: list[str]) -> pd.DataFrame:
    df = pd.read_csv(DEVICE_QC_PATH, dtype=str)
    df["Subject_ID_D"] = df["Subject_ID_D"].astype(str).str.zfill(3)
    subjects = [subject.zfill(3) for subject in subjects]
    df = df[df["Subject_ID_D"].isin(subjects)].copy()
    df = df[df["has_metadata_after_T1"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    df["window_start_ms_num"] = pd.to_numeric(df["window_start_ms"], errors="coerce")
    df["window_end_ms_num"] = pd.to_numeric(df["window_end_ms"], errors="coerce")
    df["days_first_available_num"] = pd.to_numeric(df["days_first_available_after_T1"], errors="coerce")
    df = df.dropna(subset=["window_start_ms_num", "window_end_ms_num"]).copy()
    return df.sort_values(["Subject_ID_D", "days_first_available_num", "window_start_ms_num"]).copy()


def probe_window(cur, device_id: str, start_ms: int, end_ms: int, sample_limit: int) -> dict[str, Any]:
    cur.execute(
        f"""
        SELECT timestamp
        FROM `{TABLE_NAME}`
        WHERE timestamp >= %s
          AND timestamp < %s
          AND device_id = %s
        ORDER BY timestamp DESC
        LIMIT {int(sample_limit)}
        """,
        (int(start_ms), int(end_ms), device_id),
    )
    timestamps = [as_int_ms(row.get("timestamp")) for row in cur.fetchall()]
    timestamps = [value for value in timestamps if value is not None]
    timestamps_ascending = sorted(timestamps)
    first_ts = timestamps_ascending[0] if timestamps_ascending else None
    last_ts = timestamps_ascending[-1] if timestamps_ascending else None
    return {
        "sampled_rows": len(timestamps),
        "hit": bool(timestamps),
        "hit_sample_limit": len(timestamps) >= sample_limit,
        "first_sample_ts": first_ts or "",
        "first_sample_local": ms_to_local(first_ts),
        "last_sample_ts": last_ts or "",
        "last_sample_local": ms_to_local(last_ts),
    }


def probe_candidate(cur, candidate: pd.Series, sample_limit: int, probe_minutes: int) -> list[dict[str, Any]]:
    subject_id = str(candidate["Subject_ID_D"]).zfill(3)
    device_id = str(candidate["device_id"]).strip()
    window_start_ms = int(candidate["window_start_ms_num"])
    window_end_ms = int(candidate["window_end_ms_num"])
    probe_width_ms = probe_minutes * MINUTE_MS
    rows: list[dict[str, Any]] = []

    jump_index = 0
    anchor_end_ms = window_end_ms
    while anchor_end_ms > window_start_ms:
        probe_end_ms = anchor_end_ms
        probe_start_ms = max(window_start_ms, probe_end_ms - probe_width_ms)
        result = probe_window(cur, device_id, probe_start_ms, probe_end_ms, sample_limit)
        rows.append(
            {
                "Subject_ID_D": subject_id,
                "device_id": device_id,
                "metadata_days_first_available_after_T1": candidate.get("days_first_available_after_T1", ""),
                "metadata_window_start_ms": window_start_ms,
                "metadata_window_start_local": candidate.get("window_start_local", ""),
                "metadata_window_end_ms": window_end_ms,
                "metadata_window_end_local": candidate.get("window_end_local", ""),
                "metadata_n_rows": candidate.get("n_rows", ""),
                "metadata_qc_readiness_level": candidate.get("qc_readiness_level", ""),
                "backward_week_jump_index": jump_index,
                "probe_start_ms": probe_start_ms,
                "probe_end_ms": probe_end_ms,
                "probe_start_local": ms_to_local(probe_start_ms),
                "probe_end_local": ms_to_local(probe_end_ms),
                "sample_limit": sample_limit,
                **result,
            }
        )
        if result["hit"]:
            break
        jump_index += 1
        anchor_end_ms -= WEEK_MS

    return rows


def build_readme(probe_df: pd.DataFrame, out_csv: Path) -> str:
    hit_subjects = sorted(probe_df.loc[probe_df["hit"].eq(True), "Subject_ID_D"].astype(str).unique())
    return f"""# Accelerometer Misses Weekly Backward Probe

Date: 2026-07-21

Purpose:

- Test whether previous accelerometer misses `007` and `013` have any raw `accelerometer` samples near their metadata windows.
- For each post-T1 `sensor_accelerometer` metadata window, probe backward from the window end in 7-day jumps.
- Each probe is bounded to a short window and returns at most 10 raw samples.

Output:

- Probe CSV: `{out_csv}`

Result:

- Probe rows: {len(probe_df)}
- Subjects with any raw hit: {', '.join(hit_subjects) if hit_subjects else 'none'}

Interpretation:

- This is still not a full raw-table absence proof.
- It is a low-cost diagnostic: if raw sampling exists near the end of the metadata week, this should usually catch it.
- No hit means no raw samples were found in the bounded weekly-backward probe locations.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Weekly backward raw accelerometer probes for prior miss patients.")
    parser.add_argument("--subjects", nargs="+", default=["007", "013"])
    parser.add_argument("--sample-limit", type=int, default=10)
    parser.add_argument("--probe-minutes", type=int, default=20)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.out_dir / "accelerometer_misses_weekly_backward_probe.csv"
    readme_path = args.out_dir / "README_accelerometer_misses_weekly_backward_probe.md"

    candidates = load_candidate_windows(args.subjects)
    rows: list[dict[str, Any]] = []
    conn = connect_sensordata_db()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            for idx, (_, candidate) in enumerate(candidates.iterrows(), start=1):
                subject_id = str(candidate["Subject_ID_D"]).zfill(3)
                print(f"probing {idx}/{len(candidates)} Subject_ID_D={subject_id} device_id={candidate['device_id']}", flush=True)
                rows.extend(probe_candidate(cur, candidate, args.sample_limit, args.probe_minutes))
                probe_df = pd.DataFrame(rows)
                probe_df.to_csv(out_csv, index=False)
                readme_path.write_text(build_readme(probe_df, out_csv), encoding="utf-8")
        finally:
            cur.close()
    finally:
        conn.close()

    probe_df = pd.DataFrame(rows)
    probe_df.to_csv(out_csv, index=False)
    readme_path.write_text(build_readme(probe_df, out_csv), encoding="utf-8")
    print("accelerometer_misses_weekly_backward_probe_complete")
    print(f"probe_csv: {out_csv}")
    print(f"readme: {readme_path}")
    if not probe_df.empty:
        print(probe_df.groupby("Subject_ID_D")["hit"].any().to_string())


if __name__ == "__main__":
    main()
