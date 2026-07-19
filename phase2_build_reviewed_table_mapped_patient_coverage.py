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
SUMMARY_PATH = OUT_ROOT / "phase2_reviewed_tables_mapped_patient_coverage_summary.csv"
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


def load_subject_devices() -> pd.DataFrame:
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    rows = []
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
                rows.append({"Subject_ID_D": subject_id, "device_id": device_id})
        if is_exact:
            exact_seen.add(subject_id)
    return pd.DataFrame(rows).drop_duplicates()


def safe_table(table_name: str, whitelist: set[str]) -> str:
    if table_name not in whitelist or not SAFE_TABLE_RE.match(table_name):
        raise ValueError(f"unsafe_or_unknown_table:{table_name}")
    return f"`{table_name}`"


def ms_to_local(ms: Any) -> str:
    value = pd.to_numeric(ms, errors="coerce")
    if pd.isna(value):
        return ""
    return pd.to_datetime(int(value), unit="ms", utc=True).tz_convert("Asia/Jerusalem").strftime("%Y-%m-%d %H:%M:%S%z")


def table_metadata(conn, table_name: str) -> dict[str, Any]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SHOW TABLE STATUS LIKE %s", (table_name,))
        return cur.fetchone() or {}
    finally:
        cur.close()


def mapped_device_coverage(conn, quoted_table: str, table_name: str, subject_devices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, device_row in subject_devices.iterrows():
        subject_id = str(device_row["Subject_ID_D"])
        device_id = str(device_row["device_id"])
        cur = conn.cursor()
        try:
            cur.execute(
                f"""
                SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
                FROM {quoted_table}
                WHERE device_id = %s
                """,
                (device_id,),
            )
            n_rows, first_ts, last_ts = cur.fetchone()
        finally:
            cur.close()
        n_rows = int(n_rows or 0)
        if n_rows <= 0:
            continue
        rows.append(
            {
                "table_name": table_name,
                "Subject_ID_D": subject_id,
                "device_id": device_id,
                "n_rows": n_rows,
                "first_ts": first_ts,
                "last_ts": last_ts,
                "first_local": ms_to_local(first_ts),
                "last_local": ms_to_local(last_ts),
            }
        )
    return pd.DataFrame(rows)


def subject_summary(device_df: pd.DataFrame) -> pd.DataFrame:
    if device_df.empty:
        return pd.DataFrame(
            columns=[
                "table_name",
                "Subject_ID_D",
                "n_table_rows",
                "n_devices_with_rows",
                "first_local",
                "last_local",
            ]
        )
    return (
        device_df.groupby(["table_name", "Subject_ID_D"], as_index=False)
        .agg(
            n_table_rows=("n_rows", "sum"),
            n_devices_with_rows=("device_id", "nunique"),
            first_local=("first_local", "min"),
            last_local=("last_local", "max"),
        )
        .sort_values(["n_table_rows", "Subject_ID_D"], ascending=[False, True])
    )


def coverage_markdown(table_name: str, metadata: dict[str, Any], subj_df: pd.DataFrame, device_df: pd.DataFrame) -> str:
    estimated_rows = metadata.get("Rows", "")
    data_mb = (float(metadata.get("Data_length") or 0) / 1024 / 1024) if metadata else 0
    index_mb = (float(metadata.get("Index_length") or 0) / 1024 / 1024) if metadata else 0
    mapped_patients = int(subj_df["Subject_ID_D"].nunique()) if not subj_df.empty else 0
    mapped_devices = int(device_df["device_id"].nunique()) if not device_df.empty else 0
    mapped_rows = int(device_df["n_rows"].sum()) if not device_df.empty else 0

    lines = [
        "## Global Mapped Patient Coverage",
        "",
        "Retrospective coverage summary added for the Phase 2 protocol.",
        "",
        "Coverage queries were run per mapped `device_id`; missing rows are not interpreted as zero activity.",
        "",
        f"- Estimated table rows from MySQL metadata: `{estimated_rows}`",
        f"- Approximate table data size: `{data_mb:.1f} MB`",
        f"- Approximate table index size: `{index_mb:.1f} MB`",
        f"- Mapped patients with any `{table_name}` rows: `{mapped_patients}`",
        f"- Mapped devices with any `{table_name}` rows: `{mapped_devices}`",
        f"- Rows on mapped devices: `{mapped_rows}`",
        "",
    ]
    if subj_df.empty:
        lines.append("No mapped study patients had rows in this table.")
    else:
        lines.extend(
            [
                "| Subject_ID_D | rows | devices | first row | last row |",
                "|---|---:|---:|---|---|",
            ]
        )
        for _, row in subj_df.head(20).iterrows():
            lines.append(
                f"| `{row['Subject_ID_D']}` | `{int(row['n_table_rows'])}` | "
                f"`{int(row['n_devices_with_rows'])}` | {row['first_local']} | {row['last_local']} |"
            )
        if len(subj_df) > 20:
            lines.append("")
            lines.append(f"Only the top 20 subjects by row count are shown here. Full file contains `{len(subj_df)}` subjects.")
    lines.extend(
        [
            "",
            "Coverage files:",
            "",
            f"- `output/analysis_candidates/phase2_feature_review/{table_name}/{table_name}_mapped_device_coverage.csv`",
            f"- `output/analysis_candidates/phase2_feature_review/{table_name}/{table_name}_mapped_subject_coverage.csv`",
        ]
    )
    return "\n".join(lines)


def replace_or_append_section(path: Path, section_text: str) -> None:
    marker = "## Global Mapped Patient Coverage"
    existing = path.read_text(encoding="utf-8") if path.exists() else f"# {path.stem}\n"
    if marker in existing:
        existing = existing.split(marker, 1)[0].rstrip() + "\n\n" + section_text + "\n"
    else:
        existing = existing.rstrip() + "\n\n" + section_text + "\n"
    path.write_text(existing, encoding="utf-8")


def main() -> None:
    subject_devices = load_subject_devices()
    conn = connect_sensordata_db()
    all_summary_rows = []
    try:
        cur = conn.cursor()
        try:
            cur.execute("SHOW TABLES")
            whitelist = {str(row[0]) for row in cur.fetchall()}
        finally:
            cur.close()

        for table_name in REVIEWED_TABLES:
            print(f"table={table_name}", flush=True)
            quoted = safe_table(table_name, whitelist)
            metadata = table_metadata(conn, table_name)
            table_dir = OUT_ROOT / table_name
            table_dir.mkdir(parents=True, exist_ok=True)

            device_df = mapped_device_coverage(conn, quoted, table_name, subject_devices)
            subj_df = subject_summary(device_df)

            device_path = table_dir / f"{table_name}_mapped_device_coverage.csv"
            subject_path = table_dir / f"{table_name}_mapped_subject_coverage.csv"
            device_df.to_csv(device_path, index=False)
            subj_df.to_csv(subject_path, index=False)

            estimated_rows = int(metadata.get("Rows") or 0) if metadata else 0
            data_mb = (float(metadata.get("Data_length") or 0) / 1024 / 1024) if metadata else 0
            index_mb = (float(metadata.get("Index_length") or 0) / 1024 / 1024) if metadata else 0
            all_summary_rows.append(
                {
                    "table_name": table_name,
                    "estimated_table_rows_metadata": estimated_rows,
                    "approx_data_mb": round(data_mb, 2),
                    "approx_index_mb": round(index_mb, 2),
                    "mapped_patients_with_rows": int(subj_df["Subject_ID_D"].nunique()) if not subj_df.empty else 0,
                    "mapped_devices_with_rows": int(device_df["device_id"].nunique()) if not device_df.empty else 0,
                    "rows_on_mapped_devices": int(device_df["n_rows"].sum()) if not device_df.empty else 0,
                    "first_mapped_row_local": subj_df["first_local"].min() if not subj_df.empty else "",
                    "last_mapped_row_local": subj_df["last_local"].max() if not subj_df.empty else "",
                    "device_coverage_file": str(device_path.relative_to(ROOT)),
                    "subject_coverage_file": str(subject_path.relative_to(ROOT)),
                }
            )

            section = coverage_markdown(table_name, metadata, subj_df, device_df)
            replace_or_append_section(REVIEW_ROOT / f"{table_name}.md", section)

    finally:
        conn.close()

    summary = pd.DataFrame(all_summary_rows)
    summary.to_csv(SUMMARY_PATH, index=False)
    print("generated summary:")
    print(SUMMARY_PATH)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
