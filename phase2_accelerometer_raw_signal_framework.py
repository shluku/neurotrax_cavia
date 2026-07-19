from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db
from phase2_sample_table_exploratory_t1_week_for_feature_review import (
    ms_to_local,
    parse_json,
    sanitize_row,
    value_type,
)


ROOT = Path(__file__).parent
TABLE_NAME = "accelerometer"
OUT_DIR = ROOT / "output/analysis_candidates/phase2_accelerometer_framework"
SENSOR_ACCELEROMETER_QC_PATH = OUT_DIR / "sensor_accelerometer_qc_by_patient.csv"
SAMPLE_PATH = OUT_DIR / "accelerometer_raw_phase2a_sample_rows.csv"
EXPANDED_PATH = OUT_DIR / "accelerometer_raw_phase2a_sample_rows_expanded.csv"
JSONL_PATH = OUT_DIR / "accelerometer_raw_phase2a_sample_rows.jsonl"
KEYS_PATH = OUT_DIR / "accelerometer_raw_phase2a_json_key_summary.csv"
WINDOW_PATH = OUT_DIR / "accelerometer_raw_phase2a_candidate_window_summary.csv"
README_PATH = OUT_DIR / "README_accelerometer_raw_signal_framework.md"
SAMPLE_LIMIT = 20
DENSITY_WINDOW_MINUTES = 5
TARGETED_WINDOW_MINUTES = 10


def first_existing_between(conn, device_id: str, start_ms: int, end_ms: int) -> int | None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT timestamp
            FROM `accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        cur.close()


def count_rows(conn, device_id: str, start_ms: int, end_ms: int) -> dict[str, Any]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
            FROM `accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            """,
            (device_id, int(start_ms), int(end_ms)),
        )
        return cur.fetchone() or {"n_rows": 0, "first_ts": None, "last_ts": None}
    finally:
        cur.close()


def fetch_sample(conn, device_id: str, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT _id, timestamp, device_id, data
            FROM `accelerometer`
            WHERE device_id = %s
              AND timestamp >= %s
              AND timestamp < %s
            ORDER BY timestamp ASC
            LIMIT %s
            """,
            (device_id, int(start_ms), int(end_ms), SAMPLE_LIMIT),
        )
        return cur.fetchall()
    finally:
        cur.close()


def numeric(value: Any) -> float | None:
    out = pd.to_numeric(value, errors="coerce")
    if pd.isna(out):
        return None
    return float(out)


def row_magnitude(obj: dict[str, Any] | None) -> float | pd._libs.missing.NAType:
    if not obj:
        return pd.NA
    values = [numeric(obj.get(f"double_values_{index}")) for index in range(3)]
    if any(value is None for value in values):
        return pd.NA
    return float(sum(float(value) ** 2 for value in values if value is not None) ** 0.5)


def expand_rows(rows: list[dict[str, Any]], window: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sample_out: list[dict[str, Any]] = []
    expanded_out: list[dict[str, Any]] = []
    key_counts: dict[str, Counter[str]] = defaultdict(Counter)

    previous_ts: int | None = None
    for index, row in enumerate(rows, start=1):
        clean = sanitize_row(dict(row))
        clean["sample_index"] = index
        clean["local_datetime"] = ms_to_local(row.get("timestamp"))
        sample_out.append(clean)

        obj = parse_json(row.get("data"))
        timestamp = pd.to_numeric(row.get("timestamp"), errors="coerce")
        delta_ms = pd.NA
        if pd.notna(timestamp) and previous_ts is not None:
            delta_ms = int(timestamp) - previous_ts
        if pd.notna(timestamp):
            previous_ts = int(timestamp)

        expanded = {
            "sample_index": index,
            "_id": row.get("_id"),
            "timestamp": row.get("timestamp"),
            "local_datetime": clean["local_datetime"],
            "device_id": row.get("device_id"),
            "Subject_ID_D": window.get("Subject_ID_D", ""),
            "window_rule": window.get("window_rule", ""),
            "delta_from_previous_ms": delta_ms,
            "accel_magnitude": row_magnitude(obj),
        }
        if obj:
            for key, value in obj.items():
                key_counts[str(key)][value_type(value)] += 1
                expanded[str(key)] = value
        expanded_out.append(expanded)

    key_df = pd.DataFrame(
        [
            {
                "json_key": key,
                "n_rows_with_key": sum(counts.values()),
                "value_type_counts": "; ".join(f"{kind}:{count}" for kind, count in sorted(counts.items())),
            }
            for key, counts in sorted(key_counts.items())
        ]
    )
    return pd.DataFrame(sample_out), pd.DataFrame(expanded_out), key_df


def local_string_to_ms(value: Any) -> int | None:
    if pd.isna(value) or not str(value).strip():
        return None
    ts = pd.to_datetime(str(value), errors="coerce")
    if pd.isna(ts):
        return None
    return int(ts.tz_convert("UTC").timestamp() * 1000)


def load_sensor_accelerometer_qc_ranked() -> pd.DataFrame:
    df = pd.read_csv(SENSOR_ACCELEROMETER_QC_PATH, dtype=str)
    df["global_T1_num"] = pd.to_numeric(df.get("global_T1"), errors="coerce")
    if "has_sensor_accelerometer_metadata_after_T1" in df.columns:
        has_metadata = df["has_sensor_accelerometer_metadata_after_T1"].astype(str).str.lower().isin(["true", "1", "yes"])
        df = df[has_metadata].copy()
    df = df.dropna(subset=["global_T1_num", "selected_device_id", "window_start_local"]).copy()
    df = df[df["selected_device_id"].astype(str).str.strip().ne("")]
    return df.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True])


def find_sample_window(conn) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    ranked = load_sensor_accelerometer_qc_ranked()
    checked_rows: list[dict[str, Any]] = []

    for _, patient in ranked.iterrows():
        subject_id = str(patient["Subject_ID_D"])
        device_id = str(patient["selected_device_id"]).strip()
        start_ms = local_string_to_ms(patient.get("window_start_local"))
        if start_ms is None:
            continue
        end_ms = int((pd.to_datetime(start_ms, unit="ms", utc=True) + pd.Timedelta(minutes=TARGETED_WINDOW_MINUTES)).timestamp() * 1000)
        print(
            f"patient={subject_id} global_T1={patient.get('global_T1', '')} device={device_id} targeted_minutes={TARGETED_WINDOW_MINUTES}",
            flush=True,
        )
        first_ts = first_existing_between(conn, device_id, start_ms, end_ms)
        checked_rows.append(
            {
                "Subject_ID_D": subject_id,
                "Subject_ID_N": patient.get("Subject_ID_N", ""),
                "global_T1": patient.get("global_T1", ""),
                "T1_date_iso": patient.get("T1_date_iso", ""),
                "device_id": device_id,
                "window_rule_checked": "targeted_around_sensor_accelerometer_metadata_10min",
                "window_start_local": ms_to_local(start_ms),
                "window_end_local": ms_to_local(end_ms),
                "first_row_ts": first_ts,
                "first_row_local": ms_to_local(first_ts),
                "has_rows": first_ts is not None,
            }
        )
        if first_ts is not None:
            return (
                {
                    "Subject_ID_D": subject_id,
                    "Subject_ID_N": patient.get("Subject_ID_N", ""),
                    "global_T1": patient.get("global_T1", ""),
                    "T1_date_iso": patient.get("T1_date_iso", ""),
                    "device_id": device_id,
                    "window_rule": "targeted_around_sensor_accelerometer_metadata_10min",
                    "window_start_ms": start_ms,
                    "window_end_ms": end_ms,
                    "window_start_local": ms_to_local(start_ms),
                    "window_end_local": ms_to_local(end_ms),
                    "first_row_ts": first_ts,
                    "first_row_local": ms_to_local(first_ts),
                },
                checked_rows,
            )
    return None, checked_rows


def build_readme(window: dict[str, Any] | None, density: dict[str, Any], sample_rows: int) -> str:
    if window:
        window_text = f"""
- Subject_ID_D: `{window["Subject_ID_D"]}`
- Subject_ID_N: `{window["Subject_ID_N"]}`
- global_T1: `{window["global_T1"]}`
- T1_date_iso: `{window["T1_date_iso"]}`
- device_id: `{window["device_id"]}`
- window_rule: `{window["window_rule"]}`
- window_start_local: `{window["window_start_local"]}`
- window_end_local: `{window["window_end_local"]}`
- first_raw_row_local: `{window["first_row_local"]}`
- sampled rows: `{sample_rows}`
- 5-minute density rows: `{density.get("n_rows", "")}`
"""
    else:
        window_text = "No bounded T1-week raw accelerometer sample window was found."

    return f"""# General Accelerometer Raw Signal Framework

This is the first bounded raw-signal step after the `sensor_accelerometer` metadata QC.

Why general accelerometer now:

- `sensor_accelerometer` metadata was found for 77 of 81 mapped T1 patients.
- `sensor_linear_accelerometer` metadata was found for 31 of 81 mapped T1 patients.
- Therefore general `accelerometer` is currently the better first raw motion stream to investigate.

What this script did:

- Used mapped T1 patients only.
- Excluded Subject_ID_D `001` through the shared ranked-patient loader.
- Scanned patients by descending T1 global score among patients with `sensor_accelerometer` metadata.
- Queried only bounded device/time windows anchored to known `sensor_accelerometer` metadata.
- Used a targeted 10-minute raw `accelerometer` window rather than scanning full 24-hour raw windows.
- Fetched only the first 20 chronological raw rows.
- Ran only a small 5-minute density count from the first raw row.
- Did not extract full raw data and did not compute model-facing features.

Selected raw sample window:

{window_text}

Interpretation:

- This is manual fieldwork for row structure and sampling feasibility.
- The raw `accelerometer` table is approximately 1.56 TB, so future work must be chunked.
- General accelerometer includes gravity plus phone motion.
- Phone motion is not direct body movement.
- Missing raw accelerometer rows are missing data, not no movement.

Generated files:

- `accelerometer_raw_phase2a_sample_rows.csv`
- `accelerometer_raw_phase2a_sample_rows_expanded.csv`
- `accelerometer_raw_phase2a_sample_rows.jsonl`
- `accelerometer_raw_phase2a_json_key_summary.csv`
- `accelerometer_raw_phase2a_candidate_window_summary.csv`
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect_sensordata_db()
    try:
        window, checked_rows = find_sample_window(conn)
        rows = fetch_sample(conn, window["device_id"], window["window_start_ms"], window["window_end_ms"]) if window else []
        density = {}
        if window:
            density_end = int(
                (pd.to_datetime(window["first_row_ts"], unit="ms", utc=True) + pd.Timedelta(minutes=DENSITY_WINDOW_MINUTES)).timestamp()
                * 1000
            )
            density = count_rows(conn, window["device_id"], int(window["first_row_ts"]), density_end)
    finally:
        conn.close()

    sample_df, expanded_df, key_df = expand_rows(rows, window or {})
    sample_df.to_csv(SAMPLE_PATH, index=False)
    expanded_df.to_csv(EXPANDED_PATH, index=False)
    key_df.to_csv(KEYS_PATH, index=False)
    with JSONL_PATH.open("w", encoding="utf-8") as handle:
        for row in sample_df.to_dict(orient="records"):
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    summary_rows = checked_rows.copy()
    if window:
        summary_rows.append(
            {
                **window,
                "window_rule_checked": "selected_sample_window",
                "sampled_rows": len(rows),
                "density_window_minutes": DENSITY_WINDOW_MINUTES,
                "density_n_rows": density.get("n_rows", pd.NA),
                "density_first_local": ms_to_local(density.get("first_ts")),
                "density_last_local": ms_to_local(density.get("last_ts")),
            }
        )
    pd.DataFrame(summary_rows).to_csv(WINDOW_PATH, index=False)
    README_PATH.write_text(build_readme(window, density, len(rows)), encoding="utf-8")

    print(f"selected_subject: {window.get('Subject_ID_D') if window else ''}")
    print(f"selected_device: {window.get('device_id') if window else ''}")
    print(f"window_rule: {window.get('window_rule') if window else ''}")
    print(f"sampled_rows: {len(rows)}")
    print(f"density_5min_rows: {density.get('n_rows', '')}")
    print("generated_files:")
    for path in [SAMPLE_PATH, EXPANDED_PATH, JSONL_PATH, KEYS_PATH, WINDOW_PATH, README_PATH]:
        print(path)


if __name__ == "__main__":
    main()
