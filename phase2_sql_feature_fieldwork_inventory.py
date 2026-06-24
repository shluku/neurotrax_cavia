from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from main import connect_sensordata_db


OUT_DIR = Path("output/analysis_candidates/phase2_sql_fieldwork")
EPISODES_PATH = Path("output/analysis_candidates/top10_subject_device_episodes.csv")
RICH_WIDE_PATH = Path("output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide_rich.csv")
PHENOTYPE_PROFILES_PATH = Path(
    "output/analysis_candidates/phase1_features/phenotype_profiles/phase1_subject_phenotype_profiles_v2.csv"
)
SQL_FEATURE_DICT_PATH = Path("output/sql_catalog/sql_feature_dictionary.csv")
SQL_TABLE_INTERPRET_PATH = Path("output/sql_catalog/sql_table_interpretation.csv")

HIGH_FREQUENCY_TABLES = {
    "accelerometer",
    "linear_accelerometer",
    "gyroscope",
    "rotation",
    "gravity",
    "magnetometer",
}

DATA_QUALITY_TABLES = {
    "aware_log",
    "aware_device",
    "aware_studies",
    "significant",
}

PHASE1_NOW_TABLES = {
    "screen",
    "applications_foreground",
    "keyboard",
    "touch",
    "plugin_google_activity_recognition",
}

PHASE2_NOW_TABLES = {
    "battery",
    "battery_charges",
    "battery_discharges",
    "light",
    "proximity",
    "barometer",
    "timezone",
}

CAUTION_TABLES = {
    "wifi",
    "bluetooth",
    "locations",
    "network",
    "network_traffic",
    "gsm",
    "gsm_neighbor",
    "telephony",
    "calls",
    "messages",
}

PRIVACY_TABLES_HIGH = {
    "locations",
    "wifi",
    "bluetooth",
    "calls",
    "messages",
    "telephony",
    "gsm",
    "gsm_neighbor",
    "network",
    "network_traffic",
}

PRIVACY_KEY_PATTERNS = [
    "text",
    "body",
    "message",
    "phone",
    "number",
    "address",
    "contact",
    "subscriber",
    "imei",
    "imsi",
    "sim",
    "serial",
    "ssid",
    "bssid",
    "mac",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "location",
    "cell",
    "lac",
    "cid",
    "operator",
    "network_operator",
]

SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+$")


def normalize_subject_id_d(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    return s.zfill(3) if s.isdigit() else s


def safe_ident(name: str, whitelist: set[str]) -> str:
    if name not in whitelist or not SAFE_TABLE_RE.match(name):
        raise ValueError(f"unsafe_or_unknown_table_name:{name}")
    return f"`{name}`"


def type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        if math.isnan(value):
            return "null"
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def parse_json(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="ignore")
        obj = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def privacy_status(table: str, key_or_col: str = "") -> str:
    t = table.lower()
    k = key_or_col.lower()
    if t in PRIVACY_TABLES_HIGH:
        if any(p in k for p in PRIVACY_KEY_PATTERNS):
            return "high_sensitive_do_not_use_raw"
        return "privacy_sensitive_aggregate_only"
    if any(p in k for p in PRIVACY_KEY_PATTERNS):
        return "sensitive_do_not_save_raw"
    return "privacy_safe_aggregate"


def table_decision(table: str, has_device_ts: bool, has_data: bool, total_rows: int, total_windows_with_data: int) -> dict[str, str]:
    t = table.lower()
    if t.startswith("sensor_"):
        decision = "exclude"
        relevance = "operational ingestion metadata, not subject phenotype"
        query_risk = "avoid"
        interpretability = "low"
        family = "operational"
    elif t in HIGH_FREQUENCY_TABLES:
        decision = "phase2_later"
        relevance = "raw high-frequency motion signal"
        query_risk = "high"
        interpretability = "requires separate signal-processing design"
        family = "high_frequency_motion"
    elif t in DATA_QUALITY_TABLES:
        decision = "data_quality_only"
        relevance = "logging or device metadata support"
        query_risk = "medium" if total_rows > 0 else "low"
        interpretability = "supportive only"
        family = "data_quality"
    elif not has_device_ts:
        decision = "exclude"
        relevance = "missing device_id/timestamp window keys"
        query_risk = "not_scanned"
        interpretability = "not usable for current top10 windows"
        family = "unknown"
    elif t in PHASE1_NOW_TABLES:
        decision = "include_now"
        relevance = "already validated Phase 1 behavioral family"
        query_risk = "low_to_medium"
        interpretability = "high"
        family = {
            "screen": "phone_engagement_sleep_circadian",
            "applications_foreground": "app_use",
            "keyboard": "active_phone_interaction",
            "touch": "active_phone_interaction",
            "plugin_google_activity_recognition": "physical_activity_context",
        }.get(t, "behavior")
    elif t in PHASE2_NOW_TABLES:
        decision = "include_now"
        relevance = "contextual passive sensing candidate"
        query_risk = "medium" if t in {"light", "proximity", "barometer"} else "low"
        interpretability = "medium"
        family = {
            "battery": "phone_use_state",
            "battery_charges": "phone_use_state",
            "battery_discharges": "phone_use_state",
            "light": "ambient_context",
            "proximity": "phone_context",
            "barometer": "environment_context",
            "timezone": "temporal_context",
        }.get(t, "context")
    elif t in CAUTION_TABLES:
        decision = "include_with_caution"
        relevance = "potential contextual or communication metadata"
        query_risk = "medium"
        interpretability = "medium_to_low"
        family = {
            "calls": "communication_metadata",
            "messages": "communication_metadata",
            "telephony": "cellular_context",
            "gsm": "cellular_context",
            "gsm_neighbor": "cellular_context",
            "wifi": "connectivity_context",
            "bluetooth": "nearby_device_context",
            "locations": "mobility_context",
            "network": "network_context",
            "network_traffic": "network_context",
        }.get(t, "privacy_sensitive_context")
    else:
        decision = "phase2_later" if has_data else "exclude"
        relevance = "unclassified table requiring manual review"
        query_risk = "unknown"
        interpretability = "unknown"
        family = "unclassified"

    if total_windows_with_data == 0 and decision in {"include_now", "include_with_caution"}:
        decision = "phase2_later"
        interpretability = f"{interpretability}; no top10 early/late coverage observed"

    return {
        "decision": decision,
        "behavioral_relevance": relevance,
        "privacy_risk": "high" if t in PRIVACY_TABLES_HIGH else ("low" if decision != "include_with_caution" else "medium"),
        "query_risk": query_risk,
        "interpretability": interpretability,
        "recommended_feature_family": family,
    }


def feature_templates(table: str, family: str, decision: str) -> list[dict[str, str]]:
    if decision not in {"include_now", "include_with_caution", "data_quality_only"}:
        return []

    t = table.lower()
    common = {
        "source_table": table,
        "window": "early_and_late",
        "aggregation_level": "subject_window",
        "implementation_status": "proposed_phase2_fieldwork",
    }

    def row(name: str, keys: str, interp: str, limitation: str, privacy: str | None = None) -> dict[str, str]:
        return {
            "feature_name": name,
            "source_keys_or_columns": keys,
            "interpretation": interp,
            "limitation": limitation,
            "privacy_status": privacy or privacy_status(table, keys),
            **common,
        }

    if t == "battery":
        return [
            row("battery_event_count", "timestamp", "battery logging density/context availability", "device/vendor logging rates vary"),
            row("battery_level_summary", "battery level keys if present", "phone use and charging context proxy", "must confirm key semantics"),
        ]
    if t in {"battery_charges", "battery_discharges"}:
        return [
            row(f"{t}_event_count", "timestamp", "charging/discharging event density", "not direct behavior"),
            row(f"{t}_active_days", "timestamp", "days with charging state observations", "logging-dependent"),
        ]
    if t == "light":
        return [
            row("light_rows", "timestamp", "ambient light data availability", "sensor placement/device dependent"),
            row("night_mean_light_lux", "double_light_lux or numeric JSON key", "nighttime light exposure context", "requires numeric key confirmation"),
        ]
    if t == "proximity":
        return [
            row("proximity_rows", "timestamp", "proximity sensor data availability", "device dependent"),
            row("near_sensor_percent", "double_proximity or numeric JSON key", "near/covered phone context", "requires per-device distribution check"),
        ]
    if t == "barometer":
        return [
            row("barometer_rows", "timestamp", "barometer data availability", "low clinical priority"),
            row("pressure_variability", "double_values_0 or pressure key", "environmental pressure variability", "not direct behavior"),
        ]
    if t == "timezone":
        return [
            row("timezone_change_count", "timezone JSON keys", "timezone changes/travel or device setting changes", "sensitive contextual signal; aggregate only"),
        ]
    if t in {"calls", "messages"}:
        return [
            row(f"{t}_event_count", "timestamp only; no raw content/phone numbers", "communication metadata event density", "privacy-sensitive; no raw values", "privacy_sensitive_aggregate_only"),
            row(f"{t}_active_days", "timestamp only; no raw content/phone numbers", "days with communication metadata", "privacy-sensitive; no raw values", "privacy_sensitive_aggregate_only"),
        ]
    if t in {"wifi", "bluetooth", "gsm", "gsm_neighbor", "telephony", "network", "network_traffic", "locations"}:
        return [
            row(f"{t}_event_count", "timestamp only or non-identifying aggregates", "context availability/event density", "privacy-sensitive; identifiers and raw location excluded", "privacy_sensitive_aggregate_only"),
            row(f"{t}_active_days", "timestamp only or non-identifying aggregates", "days with contextual observations", "privacy-sensitive; identifiers and raw location excluded", "privacy_sensitive_aggregate_only"),
        ]
    if t in DATA_QUALITY_TABLES:
        return [
            row(f"{t}_rows", "timestamp", "data-quality/logging support only", "not a behavioral phenotype endpoint", "data_quality_only"),
            row(f"{t}_active_days", "timestamp", "logging coverage support only", "not a behavioral phenotype endpoint", "data_quality_only"),
        ]
    if t in PHASE1_NOW_TABLES:
        return [
            row(f"{t}_event_count", "timestamp", f"{family} event density", "already represented in Phase 1 where applicable"),
            row(f"{t}_active_days", "timestamp", f"{family} active-day coverage", "logging/device dependent"),
        ]
    return [
        row(f"{t}_event_count", "timestamp", f"{family} event density", "requires manual feature design"),
    ]


def append_csv(path: Path, row: dict[str, Any], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in fieldnames})


def table_columns(cur, table: str, whitelist: set[str]) -> list[dict[str, Any]]:
    cur.execute(f"SHOW COLUMNS FROM {safe_ident(table, whitelist)}")
    rows = cur.fetchall()
    out = []
    for r in rows:
        # Field, Type, Null, Key, Default, Extra
        out.append(
            {
                "column_name": r[0],
                "column_type": r[1],
                "is_nullable": r[2],
                "column_key": r[3],
                "default_value": r[4],
                "extra": r[5],
            }
        )
    return out


def table_indexes(cur, table: str, whitelist: set[str]) -> list[dict[str, Any]]:
    cur.execute(f"SHOW INDEX FROM {safe_ident(table, whitelist)}")
    rows = cur.fetchall()
    out = []
    for r in rows:
        # Table, Non_unique, Key_name, Seq_in_index, Column_name, Collation, Cardinality, ...
        out.append(
            {
                "index_name": r[2],
                "seq_in_index": r[3],
                "column_name": r[4],
                "non_unique": r[1],
                "cardinality": r[6],
            }
        )
    return out


def load_optional_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path, dtype=str)
    return pd.DataFrame()


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 SQL feature fieldwork inventory.")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--sample-limit-per-table-window", type=int, default=5)
    parser.add_argument("--sample-limit-per-table-total", type=int, default=80)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    coverage_path = args.out_dir / "phase2_sql_coverage_by_table_subject_window.csv"
    if coverage_path.exists():
        coverage_path.unlink()

    episodes = pd.read_csv(EPISODES_PATH, dtype=str)
    episodes = episodes[episodes["mapping_status"].astype(str).eq("ok")].copy()
    episodes["Subject_ID_D"] = episodes["Subject_ID_D"].map(normalize_subject_id_d)
    for col in ["early_window_start_ms", "early_window_end_ms", "late_window_start_ms", "late_window_end_ms"]:
        episodes[col] = pd.to_numeric(episodes[col], errors="coerce")
    episodes = episodes.dropna(
        subset=["device_id", "early_window_start_ms", "early_window_end_ms", "late_window_start_ms", "late_window_end_ms"]
    )

    _ = pd.read_csv(RICH_WIDE_PATH, dtype=str)
    _ = pd.read_csv(PHENOTYPE_PROFILES_PATH, dtype=str)
    feature_dict_existing = load_optional_csv(SQL_FEATURE_DICT_PATH)
    table_interpret_existing = load_optional_csv(SQL_TABLE_INTERPRET_PATH)

    conn = connect_sensordata_db()
    cur = conn.cursor()

    coverage_fields = [
        "table_name",
        "Subject_ID_N",
        "Subject_ID_D",
        "device_episode_index",
        "device_id",
        "window_name",
        "window_start_ms",
        "window_end_ms",
        "n_rows",
        "first_ts",
        "last_ts",
        "query_status",
        "error_message",
    ]
    coverage_attempts = 0
    coverage_errors = 0
    json_errors = 0

    try:
        cur.execute("SHOW TABLES")
        table_names = sorted(str(r[0]) for r in cur.fetchall())
        whitelist = set(table_names)

        inventory_rows = []
        column_rows = []
        table_has = {}

        for table in table_names:
            cols = table_columns(cur, table, whitelist)
            idx = table_indexes(cur, table, whitelist)
            col_names = {c["column_name"] for c in cols}
            numeric_cols = [
                c["column_name"]
                for c in cols
                if any(x in str(c["column_type"]).lower() for x in ["int", "double", "float", "decimal", "bigint"])
                and c["column_name"] not in {"_id", "timestamp"}
            ]
            index_summary = "; ".join(
                f"{i['index_name']}:{i['column_name']}" for i in idx if i.get("column_name") in {"device_id", "timestamp"}
            )
            has_device_ts = "device_id" in col_names and "timestamp" in col_names
            has_data = "data" in col_names
            has_double_or_numeric = any("double_values" in c for c in col_names) or bool(numeric_cols)
            table_has[table] = {
                "has_device_id": "device_id" in col_names,
                "has_timestamp": "timestamp" in col_names,
                "has_data": has_data,
                "has_double_or_numeric": has_double_or_numeric,
                "numeric_columns": numeric_cols,
                "index_summary": index_summary,
                "has_device_ts": has_device_ts,
            }
            inventory_rows.append(
                {
                    "table_name": table,
                    "n_columns": len(cols),
                    "has_device_id": "device_id" in col_names,
                    "has_timestamp": "timestamp" in col_names,
                    "has_data": has_data,
                    "has_double_values_or_numeric_sensor_columns": has_double_or_numeric,
                    "numeric_sensor_columns": "; ".join(numeric_cols),
                    "device_timestamp_index_summary": index_summary,
                    "is_high_frequency_table": table in HIGH_FREQUENCY_TABLES,
                    "is_operational_sensor_table": table.startswith("sensor_"),
                }
            )
            for c in cols:
                column_rows.append({"table_name": table, **c})

        inventory_df = pd.DataFrame(inventory_rows).sort_values("table_name")
        inventory_df.to_csv(args.out_dir / "phase2_sql_table_inventory.csv", index=False)
        pd.DataFrame(column_rows).to_csv(args.out_dir / "phase2_sql_column_inventory_detail.csv", index=False)

        scannable_tables = [t for t in table_names if table_has[t]["has_device_ts"]]
        for table in scannable_tables:
            quoted = safe_ident(table, whitelist)
            for _, ep in episodes.iterrows():
                for window_name, start_col, end_col in [
                    ("early", "early_window_start_ms", "early_window_end_ms"),
                    ("late", "late_window_start_ms", "late_window_end_ms"),
                ]:
                    coverage_attempts += 1
                    row = {
                        "table_name": table,
                        "Subject_ID_N": ep["Subject_ID_N"],
                        "Subject_ID_D": ep["Subject_ID_D"],
                        "device_episode_index": ep["device_episode_index"],
                        "device_id": ep["device_id"],
                        "window_name": window_name,
                        "window_start_ms": int(ep[start_col]),
                        "window_end_ms": int(ep[end_col]),
                        "n_rows": pd.NA,
                        "first_ts": pd.NA,
                        "last_ts": pd.NA,
                        "query_status": "ok",
                        "error_message": "",
                    }
                    try:
                        cur.execute(
                            f"""
                            SELECT COUNT(*) AS n_rows, MIN(timestamp) AS first_ts, MAX(timestamp) AS last_ts
                            FROM {quoted}
                            WHERE device_id = %s
                              AND timestamp >= %s
                              AND timestamp < %s
                            """,
                            (str(ep["device_id"]), int(ep[start_col]), int(ep[end_col])),
                        )
                        n_rows, first_ts, last_ts = cur.fetchone()
                        row.update({"n_rows": int(n_rows or 0), "first_ts": first_ts, "last_ts": last_ts})
                    except Exception as exc:
                        coverage_errors += 1
                        row.update({"query_status": "error", "error_message": str(exc)[:500]})
                    append_csv(coverage_path, row, coverage_fields)

        coverage_df = pd.read_csv(coverage_path, dtype=str)
        coverage_df["n_rows_num"] = pd.to_numeric(coverage_df["n_rows"], errors="coerce")

        json_key_stats: dict[tuple[str, str], dict[str, Any]] = {}
        json_sampled_counts: Counter[str] = Counter()
        json_tables = [t for t in scannable_tables if table_has[t]["has_data"]]
        windows_with_data = coverage_df[
            (coverage_df["query_status"] == "ok") & (coverage_df["n_rows_num"] > 0)
        ].copy()

        for table in json_tables:
            if json_sampled_counts[table] >= args.sample_limit_per_table_total:
                continue
            quoted = safe_ident(table, whitelist)
            t_cov = windows_with_data[windows_with_data["table_name"] == table]
            for _, cov in t_cov.iterrows():
                if json_sampled_counts[table] >= args.sample_limit_per_table_total:
                    break
                limit = min(
                    args.sample_limit_per_table_window,
                    args.sample_limit_per_table_total - json_sampled_counts[table],
                )
                if limit <= 0:
                    break
                try:
                    cur.execute(
                        f"""
                        SELECT data
                        FROM {quoted}
                        WHERE device_id = %s
                          AND timestamp >= %s
                          AND timestamp < %s
                        LIMIT {int(limit)}
                        """,
                        (str(cov["device_id"]), int(cov["window_start_ms"]), int(cov["window_end_ms"])),
                    )
                    rows = cur.fetchall()
                    json_sampled_counts[table] += len(rows)
                    for (raw,) in rows:
                        obj = parse_json(raw)
                        if obj is None:
                            continue
                        for key, value in obj.items():
                            key = str(key)
                            st = json_key_stats.setdefault(
                                (table, key),
                                {
                                    "table_name": table,
                                    "json_key": key,
                                    "n_sampled_rows_with_table": 0,
                                    "n_rows_with_key": 0,
                                    "value_type_counts": Counter(),
                                    "privacy_status": privacy_status(table, key),
                                },
                            )
                            st["n_rows_with_key"] += 1
                            st["value_type_counts"][type_name(value)] += 1
                except Exception as exc:
                    json_errors += 1
                    key = (table, "__QUERY_ERROR__")
                    st = json_key_stats.setdefault(
                        key,
                        {
                            "table_name": table,
                            "json_key": "__QUERY_ERROR__",
                            "n_sampled_rows_with_table": 0,
                            "n_rows_with_key": 0,
                            "value_type_counts": Counter(),
                            "privacy_status": "not_applicable",
                            "error_message": str(exc)[:500],
                        },
                    )
                    st["error_message"] = str(exc)[:500]

        json_rows = []
        for (_, _), st in json_key_stats.items():
            table = st["table_name"]
            total_sampled = int(json_sampled_counts.get(table, 0))
            type_counts = st["value_type_counts"]
            json_rows.append(
                {
                    "table_name": table,
                    "json_key": st["json_key"],
                    "n_sampled_rows_with_table": total_sampled,
                    "n_rows_with_key": int(st["n_rows_with_key"]),
                    "percent_sampled_rows_with_key": round((int(st["n_rows_with_key"]) / total_sampled * 100), 4)
                    if total_sampled
                    else 0.0,
                    "example_value_types": "; ".join(f"{k}:{v}" for k, v in sorted(type_counts.items())),
                    "privacy_status": st["privacy_status"],
                    "raw_values_saved": False,
                    "error_message": st.get("error_message", ""),
                }
            )
        json_df = pd.DataFrame(json_rows)
        if json_df.empty:
            json_df = pd.DataFrame(
                columns=[
                    "table_name",
                    "json_key",
                    "n_sampled_rows_with_table",
                    "n_rows_with_key",
                    "percent_sampled_rows_with_key",
                    "example_value_types",
                    "privacy_status",
                    "raw_values_saved",
                    "error_message",
                ]
            )
        json_df.sort_values(["table_name", "json_key"]).to_csv(
            args.out_dir / "phase2_sql_json_key_inventory.csv", index=False
        )

        table_cov = (
            coverage_df.groupby("table_name", dropna=False)
            .agg(
                total_window_rows=("n_rows_num", "sum"),
                windows_with_data=("n_rows_num", lambda s: int((s.fillna(0) > 0).sum())),
                subjects_with_data=("Subject_ID_D", lambda s: 0),
            )
            .reset_index()
        )
        subjects_by_table = (
            coverage_df[coverage_df["n_rows_num"].fillna(0) > 0]
            .groupby("table_name")["Subject_ID_D"]
            .nunique()
            .to_dict()
        )
        table_cov["subjects_with_data"] = table_cov["table_name"].map(subjects_by_table).fillna(0).astype(int)
        table_cov_map = table_cov.set_index("table_name").to_dict("index")

        decision_rows = []
        for _, inv in inventory_df.iterrows():
            table = str(inv["table_name"])
            cov = table_cov_map.get(table, {"total_window_rows": 0, "windows_with_data": 0, "subjects_with_data": 0})
            dec = table_decision(
                table,
                bool(inv["has_device_id"]) and bool(inv["has_timestamp"]),
                bool(inv["has_data"]),
                int(cov.get("total_window_rows") or 0),
                int(cov.get("windows_with_data") or 0),
            )
            existing_note = ""
            if not table_interpret_existing.empty and "table_name" in table_interpret_existing.columns:
                hit = table_interpret_existing[table_interpret_existing["table_name"].astype(str) == table]
                if not hit.empty:
                    existing_note = str(hit.iloc[0].get("table_interpretation", ""))
            decision_rows.append(
                {
                    "table_name": table,
                    "decision": dec["decision"],
                    "behavioral_relevance": dec["behavioral_relevance"],
                    "privacy_risk": dec["privacy_risk"],
                    "query_risk": dec["query_risk"],
                    "interpretability": dec["interpretability"],
                    "recommended_feature_family": dec["recommended_feature_family"],
                    "has_device_id": inv["has_device_id"],
                    "has_timestamp": inv["has_timestamp"],
                    "has_data": inv["has_data"],
                    "is_high_frequency_table": inv["is_high_frequency_table"],
                    "is_operational_sensor_table": inv["is_operational_sensor_table"],
                    "total_top10_early_late_rows": int(cov.get("total_window_rows") or 0),
                    "windows_with_data": int(cov.get("windows_with_data") or 0),
                    "subjects_with_data": int(cov.get("subjects_with_data") or 0),
                    "existing_interpretation_note": existing_note,
                }
            )
        decision_df = pd.DataFrame(decision_rows).sort_values(["decision", "table_name"])
        decision_df.to_csv(args.out_dir / "phase2_sql_table_decision_matrix.csv", index=False)

        feature_rows = []
        for _, dec in decision_df.iterrows():
            feature_rows.extend(
                feature_templates(
                    str(dec["table_name"]),
                    str(dec["recommended_feature_family"]),
                    str(dec["decision"]),
                )
            )

        feature_df = pd.DataFrame(feature_rows)
        if not feature_dict_existing.empty and "table_name" in feature_dict_existing.columns:
            # Keep a lightweight link to prior dictionary coverage without copying raw examples.
            prior_counts = feature_dict_existing.groupby("table_name").size().to_dict()
            if not feature_df.empty:
                feature_df["prior_sql_feature_dictionary_keys"] = feature_df["source_table"].map(prior_counts).fillna(0).astype(int)
        if feature_df.empty:
            feature_df = pd.DataFrame(
                columns=[
                    "feature_name",
                    "source_table",
                    "source_keys_or_columns",
                    "window",
                    "aggregation_level",
                    "interpretation",
                    "limitation",
                    "privacy_status",
                    "implementation_status",
                ]
            )
        feature_df.sort_values(["source_table", "feature_name"]).to_csv(
            args.out_dir / "phase2_candidate_feature_dictionary.csv", index=False
        )

        safe_now = decision_df[decision_df["decision"] == "include_now"]["table_name"].tolist()
        later = decision_df[decision_df["decision"] == "phase2_later"]["table_name"].tolist()
        high_freq = decision_df[decision_df["is_high_frequency_table"].astype(bool)]["table_name"].tolist()
        privacy_sensitive = decision_df[decision_df["privacy_risk"].isin(["high", "medium"])]["table_name"].tolist()
        top_coverage = table_cov.sort_values("total_window_rows", ascending=False).head(12)

        readme_lines = [
            "# Phase 2 SQL Feature Fieldwork Inventory",
            "",
            "## Scope",
            "- Systematic SensorDB table fieldwork for the current top-10 subject/device/window mapping.",
            "- SQL coverage scans used early and late windows only.",
            "- Every coverage and JSON sampling query was filtered by device_id and timestamp.",
            "- No full raw data extraction was performed.",
            "- No full T1-to-T2 windows were queried.",
            "- No full-table COUNT(*) queries were run.",
            "- Phase 1 outputs were read as context only and were not modified.",
            "",
            "## What was scanned",
            f"- SensorDB tables found: {len(table_names)}.",
            f"- Tables with device_id + timestamp: {len(scannable_tables)}.",
            f"- Tables with data JSON column: {sum(1 for t in table_names if table_has[t]['has_data'])}.",
            "- Top-10 device episodes with early and late windows.",
            "",
            "## What was intentionally not extracted",
            "- Full raw rows.",
            "- Full T1-to-T2 windows.",
            "- Keyboard text.",
            "- Phone numbers.",
            "- Subscriber IDs, IMEI, IMSI, SIM serials.",
            "- Raw message text.",
            "- Raw location, Wi-Fi/Bluetooth/cell identifiers as phenotype features.",
            "",
            "## Tables safe now",
        ]
        readme_lines.extend([f"- {t}" for t in safe_now] or ["- none"])
        readme_lines.extend(["", "## High-frequency/heavy tables"])
        readme_lines.extend([f"- {t}" for t in high_freq] or ["- none"])
        readme_lines.extend(["", "## Privacy-sensitive tables/fields"])
        readme_lines.extend([f"- {t}" for t in privacy_sensitive] or ["- none"])
        readme_lines.extend(
            [
                "- Sensitive JSON keys are flagged in phase2_sql_json_key_inventory.csv.",
                "- Raw sensitive values were not saved.",
                "",
                "## Candidate features to implement next",
            ]
        )
        if not feature_df.empty:
            for _, r in feature_df.head(40).iterrows():
                readme_lines.append(f"- {r['feature_name']} from {r['source_table']}: {r['interpretation']}")
        else:
            readme_lines.append("- none")
        readme_lines.extend(
            [
                "",
                "## Recommended next scripts",
                "- extract_phase2_phone_state_context_features.py for battery, charging, light, proximity, barometer, and timezone.",
                "- extract_phase2_privacy_safe_communication_context_features.py for calls/messages metadata only, if approved.",
                "- extract_phase2_connectivity_context_features.py for Wi-Fi/Bluetooth/GSM aggregate-only context, if approved.",
                "- qc_phase2_extracted_features.py to enforce missing-data and privacy rules.",
                "",
                "## Generated files",
                "- phase2_sql_table_inventory.csv",
                "- phase2_sql_coverage_by_table_subject_window.csv",
                "- phase2_sql_json_key_inventory.csv",
                "- phase2_sql_table_decision_matrix.csv",
                "- phase2_candidate_feature_dictionary.csv",
                "- README_phase2_sql_feature_fieldwork.md",
            ]
        )
        (args.out_dir / "README_phase2_sql_feature_fieldwork.md").write_text(
            "\n".join(readme_lines), encoding="utf-8"
        )

        print(f"total_tables_found={len(table_names)}")
        print(f"tables_with_device_id_and_timestamp={len(scannable_tables)}")
        print(f"tables_with_data_json={sum(1 for t in table_names if table_has[t]['has_data'])}")
        print(f"total_safe_coverage_queries_attempted={coverage_attempts}")
        print(f"total_errors={coverage_errors + json_errors}")
        print("top_tables_by_early_late_coverage:")
        print(top_coverage[["table_name", "total_window_rows", "windows_with_data", "subjects_with_data"]].to_string(index=False))
        print("tables_recommended_for_implementation_now:")
        print(safe_now)
        print("tables_recommended_for_later:")
        print(later)
        print("generated_files:")
        for p in [
            args.out_dir / "phase2_sql_table_inventory.csv",
            args.out_dir / "phase2_sql_coverage_by_table_subject_window.csv",
            args.out_dir / "phase2_sql_json_key_inventory.csv",
            args.out_dir / "phase2_sql_table_decision_matrix.csv",
            args.out_dir / "phase2_candidate_feature_dictionary.csv",
            args.out_dir / "README_phase2_sql_feature_fieldwork.md",
        ]:
            print(f"- {p}")

    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
