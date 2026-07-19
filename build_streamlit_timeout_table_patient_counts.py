from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db
from build_streamlit_global_patient_coverage_preview import (
    ROOT,
    safe_ident,
    table_columns,
)


LABEL_DEVICE_MAP_PATH = ROOT / "output/label_device_map.csv"
STATUS_PATH = ROOT / "output/analysis_candidates/phase2_feature_review/streamlit_global_patient_coverage_status.csv"
OUT_PATH = ROOT / "output/analysis_candidates/phase2_feature_review/streamlit_timeout_table_patient_counts.csv"


def normalize_subject_id(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text.zfill(3) if text.isdigit() else text


def load_subject_devices() -> pd.DataFrame:
    label_map = pd.read_csv(LABEL_DEVICE_MAP_PATH, dtype=str)
    rows = []
    numeric_seen = set()
    for _, row in label_map.iterrows():
        raw_label = "" if pd.isna(row.get("label")) else str(row.get("label")).strip()
        subject_id = normalize_subject_id(raw_label)
        if not subject_id or subject_id.lower() in {"nan", "none"}:
            continue
        raw_devices = "" if pd.isna(row.get("device_ids")) else str(row.get("device_ids"))
        is_numeric = raw_label.isdigit()
        if is_numeric:
            numeric_seen.add(subject_id)
        elif subject_id in numeric_seen:
            continue
        for device_id in raw_devices.split(";"):
            device_id = device_id.strip()
            if device_id and device_id.lower() not in {"nan", "none"}:
                rows.append({"Subject_ID_D": subject_id, "device_id": device_id, "label_is_numeric": is_numeric})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["_priority"] = df["label_is_numeric"].astype(int)
    df = df.sort_values("_priority", ascending=False).drop_duplicates("device_id")
    return df.drop(columns=["_priority", "label_is_numeric"])


def device_has_rows(conn, table_name: str, quoted_table: str, device_id: str) -> bool:
    cur = conn.cursor()
    try:
        try:
            cur.execute("SET SESSION MAX_EXECUTION_TIME=10000")
        except Exception:
            pass
        cur.execute(
            f"""
            SELECT 1
            FROM {quoted_table}
            WHERE device_id = %s
            LIMIT 1
            """,
            (device_id,),
        )
        return cur.fetchone() is not None
    finally:
        cur.close()


def main() -> None:
    if not STATUS_PATH.exists():
        raise SystemExit(f"Missing status file: {STATUS_PATH}")

    status = pd.read_csv(STATUS_PATH, dtype=str)
    target_tables = status[status["status"].astype(str).ne("ok")]["table_name"].dropna().astype(str).tolist()
    subject_devices = load_subject_devices()

    rows = []
    conn = connect_sensordata_db()
    try:
        cur = conn.cursor()
        try:
            cur.execute("SHOW TABLES")
            whitelist = {str(row[0]) for row in cur.fetchall()}
        finally:
            cur.close()

        for table_name in target_tables:
            print(f"table={table_name}", flush=True)
            table_status = status[status["table_name"].astype(str).eq(table_name)].iloc[0].to_dict()
            try:
                cols = table_columns(conn, table_name, whitelist)
                if "device_id" not in cols:
                    raise ValueError("missing_device_id_column")
                quoted = safe_ident(table_name, whitelist)
                subjects_with_rows = set()
                devices_checked = 0
                devices_with_rows = 0
                for _, row in subject_devices.iterrows():
                    devices_checked += 1
                    if device_has_rows(conn, table_name, quoted, str(row["device_id"])):
                        devices_with_rows += 1
                        subjects_with_rows.add(str(row["Subject_ID_D"]))
                rows.append(
                    {
                        "table_name": table_name,
                        "number_of_patients_with_data": len(subjects_with_rows),
                        "mapped_devices_with_data": devices_with_rows,
                        "mapped_devices_checked": devices_checked,
                        "source_status": table_status.get("status", ""),
                        "coverage_method": "per_mapped_device_exists_query",
                        "error_message": "",
                    }
                )
            except Exception as exc:
                rows.append(
                    {
                        "table_name": table_name,
                        "number_of_patients_with_data": pd.NA,
                        "mapped_devices_with_data": pd.NA,
                        "mapped_devices_checked": len(subject_devices),
                        "source_status": table_status.get("status", ""),
                        "coverage_method": "per_mapped_device_exists_query",
                        "error_message": str(exc),
                    }
                )
    finally:
        conn.close()

    out = pd.DataFrame(rows)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print("generated:")
    print(OUT_PATH)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
