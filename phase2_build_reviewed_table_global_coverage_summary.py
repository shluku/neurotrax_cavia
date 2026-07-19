from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


ROOT = Path(__file__).parent
LABEL_DEVICE_MAP_PATH = ROOT / "output/label_device_map.csv"
OUT_ROOT = ROOT / "output/analysis_candidates/phase2_feature_review"
REVIEW_ROOT = ROOT / "phase2_table_feature_reviews"
SUMMARY_PATH = OUT_ROOT / "phase2_reviewed_tables_global_coverage_summary.csv"
SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")

REVIEWED_TABLES = [
    "applications_foreground",
    "battery",
    "bluetooth",
    "calls",
    "gsm",
    "keyboard",
    "light",
    "linear_accelerometer",
    "locations",
    "messages",
    "network",
]


def normalize_subject_id(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def load_device_subject_lookup() -> dict[str, str]:
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    lookup: dict[str, str] = {}
    exact_seen: set[str] = set()
    for _, row in label_map.iterrows():
        raw_label = "" if pd.isna(row.get("label")) else str(row.get("label")).strip()
        subject_id = normalize_subject_id(raw_label)
        if not subject_id or subject_id.lower() in {"nan", "none"}:
            continue
        is_exact = raw_label.isdigit() and len(raw_label) == 3
        if subject_id in exact_seen and not is_exact:
            continue
        raw_devices = "" if pd.isna(row.get("device_ids")) else str(row.get("device_ids"))
        for device_id in raw_devices.split(";"):
            device_id = device_id.strip()
            if device_id and device_id.lower() not in {"nan", "none"}:
                lookup.setdefault(device_id, subject_id)
        if is_exact:
            exact_seen.add(subject_id)
    return lookup


def safe_ident(table_name: str, whitelist: set[str]) -> str:
    if table_name not in whitelist or not SAFE_TABLE_RE.match(table_name):
        raise ValueError(f"unsafe_or_unknown_table:{table_name}")
    return f"`{table_name}`"


def query_device_counts(conn, table_name: str, whitelist: set[str]) -> pd.DataFrame:
    quoted = safe_ident(table_name, whitelist)
    cur = conn.cursor(dictionary=True)
    try:
        try:
            cur.execute("SET SESSION MAX_EXECUTION_TIME=60000")
        except Exception:
            pass
        cur.execute(
            f"""
            SELECT device_id, COUNT(*) AS n_rows
            FROM {quoted}
            GROUP BY device_id
            ORDER BY n_rows DESC
            """
        )
        return pd.DataFrame(cur.fetchall())
    finally:
        cur.close()


def table_status_rows(conn, table_name: str) -> dict[str, Any]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SHOW TABLE STATUS LIKE %s", (table_name,))
        return cur.fetchone() or {}
    finally:
        cur.close()


def summarize_table(table_name: str, counts: pd.DataFrame, lookup: dict[str, str], status: dict[str, Any]) -> dict[str, Any]:
    if counts.empty:
        counts = pd.DataFrame(columns=["device_id", "n_rows"])
    counts["device_id"] = counts["device_id"].astype(str)
    counts["n_rows"] = pd.to_numeric(counts["n_rows"], errors="coerce").fillna(0).astype("int64")
    counts["Subject_ID_D"] = counts["device_id"].map(lookup).fillna("NOT_MAPPED")
    mapped = counts[counts["Subject_ID_D"].ne("NOT_MAPPED")].copy()
    unmapped = counts[counts["Subject_ID_D"].eq("NOT_MAPPED")].copy()
    return {
        "table_name": table_name,
        "devices_with_rows": int(counts["device_id"].nunique()),
        "mapped_study_patients_with_rows": int(mapped["Subject_ID_D"].nunique()),
        "mapped_devices_with_rows": int(mapped["device_id"].nunique()),
        "unmapped_devices_with_rows": int(unmapped["device_id"].nunique()),
        "rows_mapped_to_study_patients": int(mapped["n_rows"].sum()),
        "rows_on_unmapped_devices": int(unmapped["n_rows"].sum()),
        "total_rows_from_device_grouping": int(counts["n_rows"].sum()),
        "metadata_estimated_rows": int(status.get("Rows") or 0),
        "coverage_status": "ok",
        "error_message": "",
    }


def markdown_section(summary: dict[str, Any]) -> str:
    table_name = summary["table_name"]
    if summary["coverage_status"] != "ok":
        return f"""## Global Coverage Summary

Global coverage summary failed for `{table_name}`.

- Error: `{summary['error_message']}`

This does not change the Phase 2A feature decision.
"""
    return f"""## Global Coverage Summary

This compact summary describes global `{table_name}` availability across the SensorDB table, mapped back to the current study device map.

- Devices with `{table_name}` rows: `{summary['devices_with_rows']:,}`
- Mapped study patients with `{table_name}` rows: `{summary['mapped_study_patients_with_rows']:,}`
- Mapped devices with rows: `{summary['mapped_devices_with_rows']:,}`
- Unmapped devices with rows: `{summary['unmapped_devices_with_rows']:,}`
- Rows mapped to study patients: `{summary['rows_mapped_to_study_patients']:,}`
- Rows on unmapped devices: `{summary['rows_on_unmapped_devices']:,}`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
"""


def replace_or_append(path: Path, section: str) -> None:
    marker = "## Global Coverage Summary"
    text = path.read_text(encoding="utf-8") if path.exists() else f"# {path.stem}\n"
    if marker in text:
        text = text.split(marker, 1)[0].rstrip() + "\n\n" + section.strip() + "\n"
    else:
        text = text.rstrip() + "\n\n" + section.strip() + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    lookup = load_device_subject_lookup()
    summaries = []
    conn = connect_sensordata_db()
    try:
        cur = conn.cursor()
        try:
            cur.execute("SHOW TABLES")
            whitelist = {str(row[0]) for row in cur.fetchall()}
        finally:
            cur.close()

        for table_name in REVIEWED_TABLES:
            print(f"table={table_name}", flush=True)
            table_dir = OUT_ROOT / table_name
            table_dir.mkdir(parents=True, exist_ok=True)
            status = table_status_rows(conn, table_name)
            try:
                counts = query_device_counts(conn, table_name, whitelist)
                summary = summarize_table(table_name, counts, lookup, status)
                counts["Subject_ID_D"] = counts["device_id"].astype(str).map(lookup).fillna("NOT_MAPPED")
                counts.to_csv(table_dir / f"{table_name}_global_device_coverage_summary.csv", index=False)
            except Exception as exc:
                summary = {
                    "table_name": table_name,
                    "devices_with_rows": pd.NA,
                    "mapped_study_patients_with_rows": pd.NA,
                    "mapped_devices_with_rows": pd.NA,
                    "unmapped_devices_with_rows": pd.NA,
                    "rows_mapped_to_study_patients": pd.NA,
                    "rows_on_unmapped_devices": pd.NA,
                    "total_rows_from_device_grouping": pd.NA,
                    "metadata_estimated_rows": int(status.get("Rows") or 0) if status else pd.NA,
                    "coverage_status": "error",
                    "error_message": str(exc),
                }
            summaries.append(summary)
            replace_or_append(REVIEW_ROOT / f"{table_name}.md", markdown_section(summary))
    finally:
        conn.close()

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(SUMMARY_PATH, index=False)
    print("generated:")
    print(SUMMARY_PATH)
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
