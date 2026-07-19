from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db
from phase2_sample_table_exploratory_t1_week_for_feature_review import (
    ROOT,
    get_tables,
    ms_to_local,
    parse_json,
    safe_ident,
    sanitize_row,
    sanitize_value,
    value_type,
)


TABLE_NAME = "network"
OUT_DIR = ROOT / "output/analysis_candidates/phase2_feature_review/network"
LABEL_DEVICE_MAP_PATH = ROOT / "output/label_device_map.csv"


def normalize_subject_id(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def load_device_subject_lookup() -> dict[str, str]:
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    lookup: dict[str, str] = {}
    for _, row in label_map.iterrows():
        label = normalize_subject_id(row.get("label"))
        raw = "" if pd.isna(row.get("device_ids")) else str(row.get("device_ids"))
        for device_id in raw.split(";"):
            device_id = device_id.strip()
            if device_id and device_id.lower() not in {"nan", "none"}:
                lookup.setdefault(device_id, label)
    return lookup


def fetch_first_rows(limit: int = 20) -> tuple[list[str], list[dict[str, Any]]]:
    conn = connect_sensordata_db()
    try:
        whitelist = get_tables(conn)
        quoted = safe_ident(TABLE_NAME, whitelist)
        cur = conn.cursor()
        try:
            cur.execute(f"SHOW COLUMNS FROM {quoted}")
            columns = [str(row[0]) for row in cur.fetchall()]
        finally:
            cur.close()

        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                f"""
                SELECT *
                FROM {quoted}
                ORDER BY timestamp ASC
                LIMIT %s
                """,
                (int(limit),),
            )
            rows = cur.fetchall()
        finally:
            cur.close()
        return columns, rows
    finally:
        conn.close()


def write_outputs(columns: list[str], rows: list[dict[str, Any]]) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample_path = OUT_DIR / "network_sample_rows.csv"
    expanded_path = OUT_DIR / "network_sample_rows_expanded.csv"
    jsonl_path = OUT_DIR / "network_sample_rows.jsonl"
    keys_path = OUT_DIR / "network_json_key_summary.csv"
    readme_path = OUT_DIR / "README_network_feature_review.md"
    review_path = ROOT / "phase2_table_feature_reviews/network.md"

    subject_lookup = load_device_subject_lookup()
    sample_out = []
    expanded_out = []
    key_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for index, row in enumerate(rows, start=1):
        clean = sanitize_row(dict(row))
        device_id = str(row.get("device_id") or "")
        clean["sample_index"] = index
        clean["Subject_ID_D"] = subject_lookup.get(device_id, "NOT_MAPPED")
        clean["local_datetime"] = ms_to_local(row.get("timestamp"))
        clean["sample_context"] = "phase2a_network_global_earliest_20_manual_review"
        sample_out.append(clean)

        obj = parse_json(row.get("data"))
        sanitized_obj = {str(key): sanitize_value(key, value) for key, value in obj.items()} if obj else {}
        expanded = {
            "sample_index": index,
            "_id": row.get("_id"),
            "timestamp": row.get("timestamp"),
            "local_datetime": clean["local_datetime"],
            "Subject_ID_D": clean["Subject_ID_D"],
            "device_id": row.get("device_id"),
            "sample_context": "phase2a_network_global_earliest_20_manual_review",
        }
        if obj:
            for key, value in obj.items():
                key_counts[str(key)][value_type(value)] += 1
                expanded[str(key)] = sanitized_obj.get(str(key))
        expanded_out.append(expanded)

    pd.DataFrame(sample_out).to_csv(sample_path, index=False)
    pd.DataFrame(expanded_out).to_csv(expanded_path, index=False)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in sample_out:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    key_rows = [
        {
            "json_key": key,
            "n_rows_with_key": sum(counts.values()),
            "value_type_counts": "; ".join(f"{k}:{v}" for k, v in sorted(counts.items())),
        }
        for key, counts in sorted(key_counts.items())
    ]
    pd.DataFrame(key_rows).to_csv(keys_path, index=False)

    subjects = sorted({row.get("Subject_ID_D", "") for row in sample_out})
    devices = sorted({str(row.get("device_id", "")) for row in sample_out})
    first_local = sample_out[0].get("local_datetime", "") if sample_out else ""
    last_local = sample_out[-1].get("local_datetime", "") if sample_out else ""

    readme_text = f"""# network Phase 2A Feature Review Sample

This folder contains the current Phase 2A manual-review sample for `network`.

## Important Context

The standard T1-ranked T1-week 24-hour Phase 2A scan found no `network` rows:

- Bounded patient/device/window checks: 318
- Windows with any rows: 0
- Maximum rows in any checked window: 0

Because the table is not empty globally, this manual-review file now contains the first 20 chronological `network` rows in the database.

## Current Manual Sample

- sample_context: `phase2a_network_global_earliest_20_manual_review`
- sampled rows: {len(sample_out)}
- first row local time: `{first_local}`
- last row local time: `{last_local}`
- mapped subjects in sample: `{'; '.join(subjects)}`
- devices in sample: `{'; '.join(devices)}`

This sample is for manual row/JSON inspection only. It is not feature extraction, not diagnostic, and not a T1-window clinical phenotype result.

## Files

- `network_sample_rows.csv`
- `network_sample_rows_expanded.csv`
- `network_sample_rows.jsonl`
- `network_json_key_summary.csv`
- `network_phase2a_t1_ranked_coverage_scan.csv`
"""
    readme_path.write_text(readme_text, encoding="utf-8")

    review_text = f"""# network

## Phase 2A Manual Review Status

The standard Phase 2A T1-ranked T1-week 24-hour protocol found no `network` rows.

To support manual feature discovery, the current review sample uses the first 20 chronological rows from the `network` table.

## Current Manual Sample

- sample_context: `phase2a_network_global_earliest_20_manual_review`
- sampled rows: {len(sample_out)}
- first row local time: `{first_local}`
- last row local time: `{last_local}`
- mapped subjects in sample: `{'; '.join(subjects)}`
- devices in sample: `{'; '.join(devices)}`

## Standard Protocol Coverage Result

- Bounded patient/device/window checks: 318
- Windows with any rows: 0
- Maximum rows in any checked window: 0

## Feature Decision

No `network` features are selected yet. The first 20 rows are available for manual inspection before candidate features are chosen.

## Output Files

- `output/analysis_candidates/phase2_feature_review/network/network_sample_rows.csv`
- `output/analysis_candidates/phase2_feature_review/network/network_sample_rows_expanded.csv`
- `output/analysis_candidates/phase2_feature_review/network/network_json_key_summary.csv`
- `output/analysis_candidates/phase2_feature_review/network/network_phase2a_t1_ranked_coverage_scan.csv`

## Caution

This global earliest-row sample is not a T1-window phenotype result. Missing `network` rows near T1 are not interpreted as no network activity.
"""
    review_path.write_text(review_text, encoding="utf-8")

    return [sample_path, expanded_path, jsonl_path, keys_path, readme_path, review_path]


def main() -> None:
    columns, rows = fetch_first_rows(limit=20)
    paths = write_outputs(columns, rows)
    subjects = sorted({pd.read_csv(paths[0], dtype=str).iloc[i].get("Subject_ID_D", "") for i in range(len(rows))}) if rows else []
    print(f"table_name: {TABLE_NAME}")
    print(f"sampled_rows: {len(rows)}")
    print(f"columns: {columns}")
    print(f"mapped_subjects: {'; '.join(subjects)}")
    print("generated files:")
    for path in paths:
        print(f"- {path}")


if __name__ == "__main__":
    main()
