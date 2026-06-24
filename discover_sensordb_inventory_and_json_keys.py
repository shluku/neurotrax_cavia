from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from main import connect_sensordata_db


CANDIDATE_JSON_TABLES = [
    "aware_log",
    "aware_device",
    "battery",
    "battery_charges",
    "battery_discharges",
    "screen",
    "wifi",
    "bluetooth",
    "calls",
    "messages",
    "locations",
    "applications_foreground",
    "keyboard",
    "touch",
    "network",
    "network_traffic",
    "telephony",
    "gsm",
    "gsm_neighbor",
    "plugin_google_activity_recognition",
    "timezone",
    "light",
    "proximity",
    "barometer",
]

HIGH_FREQ_TABLES = {
    "accelerometer",
    "linear_accelerometer",
    "gyroscope",
    "rotation",
    "gravity",
    "magnetometer",
}


def mb(v: Optional[int]) -> float:
    return round((float(v or 0) / (1024 * 1024)), 4)


def infer_type(vals: List[Any]) -> str:
    kinds = set(type(v).__name__ for v in vals if v is not None)
    if not kinds:
        return "unknown"
    if len(kinds) == 1:
        k = next(iter(kinds))
        if k == "str":
            return "string"
        if k in {"int", "float"}:
            return "number"
        if k == "bool":
            return "boolean"
        if k == "dict":
            return "object"
        if k == "list":
            return "array"
        return k
    return "mixed"


def feature_family_for_key(table: str, key: str) -> Tuple[str, str]:
    k = key.lower()
    if any(x in k for x in ["lat", "lon", "alt", "speed", "bearing"]):
        return "mobility", "location/movement related key"
    if any(x in k for x in ["screen", "interactive", "is_screen", "brightness"]):
        return "sleep_circadian", "screen/light timing behavior"
    if any(x in k for x in ["wifi", "ssid", "bssid", "rssi", "network"]):
        return "social_environment", "connectivity/context exposure"
    if any(x in k for x in ["battery", "level", "charging", "voltage", "temperature"]):
        return "phone_use_state", "battery/phone usage proxy"
    if any(x in k for x in ["call", "message", "sms", "duration"]):
        return "social_behavior", "communication-related key"
    if any(x in k for x in ["activity", "still", "walking", "running", "in_vehicle"]):
        return "activity_pattern", "activity-recognition related"
    return "unknown", f"table={table} key={key}"


def classify_table(name: str) -> Tuple[str, bool, bool, str]:
    n = name.lower()
    is_oper = n.startswith("sensor_")
    is_hf = n in HIGH_FREQ_TABLES

    if is_oper:
        return "operational", True, is_hf, "ignore"
    if is_hf:
        return "motion", False, True, "later"

    if n in {"locations", "wifi", "bluetooth", "timezone", "gsm", "gsm_neighbor", "network", "network_traffic"}:
        return "location_context", False, False, "yes"
    if n in {"screen", "applications_foreground", "keyboard", "touch", "calls", "messages", "telephony"}:
        return "phone_usage", False, False, "yes"
    if n in {"aware_device", "aware_log"}:
        return "metadata", False, False, "yes"
    if n in {"battery", "battery_charges", "battery_discharges", "light", "proximity", "barometer"}:
        return "environment", False, False, "yes"
    if n.startswith("plugin_"):
        return "system", False, False, "yes"
    return "unknown", False, False, "later"


def main() -> None:
    parser = argparse.ArgumentParser(description="SensorDB inventory + JSON key discovery (lightweight).")
    parser.add_argument("--episodes", type=Path, default=Path("output/analysis_candidates/top10_subject_device_episodes.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("output/sql_catalog"))
    parser.add_argument("--main-schema", default="sensordata")
    parser.add_argument("--sample-limit-per-table", type=int, default=200)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    episodes = pd.read_csv(args.episodes, dtype=str)
    episodes = episodes[episodes.get("mapping_status", "").astype(str).eq("ok")].copy()
    for c in ["early_window_start_ms", "late_window_end_ms"]:
        episodes[c] = pd.to_numeric(episodes[c], errors="coerce")
    episodes = episodes.dropna(subset=["device_id", "early_window_start_ms", "late_window_end_ms"])

    conn = connect_sensordata_db()
    cur = conn.cursor()

    errored_tables: Dict[str, str] = {}
    sampled_tables_ok: List[str] = []
    sampled_tables_no_rows: List[str] = []

    try:
        # Part A: database inventory
        cur.execute(
            """
            SELECT
              t.table_schema,
              COUNT(*) AS table_count,
              COALESCE(SUM(t.table_rows),0) AS total_rows_estimate,
              COALESCE(SUM(t.data_length),0) AS data_len,
              COALESCE(SUM(t.index_length),0) AS idx_len
            FROM information_schema.tables t
            GROUP BY t.table_schema
            ORDER BY t.table_schema
            """
        )
        db_rows = cur.fetchall()
        db_inv = []
        for schema, table_count, total_rows, data_len, idx_len in db_rows:
            db_inv.append(
                {
                    "schema_name": schema,
                    "table_count": int(table_count or 0),
                    "total_rows_estimate": int(total_rows or 0),
                    "total_size_mb": mb((data_len or 0) + (idx_len or 0)),
                    "data_size_mb": mb(data_len),
                    "index_size_mb": mb(idx_len),
                }
            )
        db_df = pd.DataFrame(db_inv)
        db_df.to_csv(args.out_dir / "database_inventory.csv", index=False)

        # Part B: table inventory (main schema)
        cur.execute(
            """
            SELECT
              table_name, table_type, engine, table_rows, data_length, index_length, create_time, update_time
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
            """,
            (args.main_schema,),
        )
        tbl_rows = cur.fetchall()

        table_inv = []
        table_names = []
        for name, ttype, engine, rows_est, dlen, ilen, ctime, utime in tbl_rows:
            cat, is_oper, is_hf, use_for_now = classify_table(name)
            table_names.append(name)
            table_inv.append(
                {
                    "table_name": name,
                    "table_type": ttype,
                    "engine": engine,
                    "table_rows_estimate": int(rows_est or 0),
                    "data_length_mb": mb(dlen),
                    "index_length_mb": mb(ilen),
                    "total_size_mb": mb((dlen or 0) + (ilen or 0)),
                    "create_time": ctime,
                    "update_time": utime,
                    "table_category_guess": cat,
                    "is_sensor_operational_table": is_oper,
                    "is_high_frequency_table": is_hf,
                    "use_for_now": use_for_now,
                }
            )
        table_df = pd.DataFrame(table_inv)
        table_df.to_csv(args.out_dir / "table_inventory.csv", index=False)

        # Part C: column inventory
        cur.execute(
            """
            SELECT table_name, column_name, data_type, column_type, is_nullable, column_key, ordinal_position
            FROM information_schema.columns
            WHERE table_schema = %s
            ORDER BY table_name, ordinal_position
            """,
            (args.main_schema,),
        )
        col_rows = cur.fetchall()
        col_df = pd.DataFrame(
            col_rows,
            columns=[
                "table_name",
                "column_name",
                "data_type",
                "column_type",
                "is_nullable",
                "column_key",
                "ordinal_position",
            ],
        )
        tbl_has_ts = col_df.groupby("table_name")["column_name"].apply(lambda s: "timestamp" in set(s)).to_dict()
        tbl_has_device = col_df.groupby("table_name")["column_name"].apply(lambda s: "device_id" in set(s)).to_dict()
        tbl_has_data = col_df.groupby("table_name")["column_name"].apply(lambda s: "data" in set(s)).to_dict()
        col_df["has_timestamp_column"] = col_df["table_name"].map(tbl_has_ts)
        col_df["has_device_id_column"] = col_df["table_name"].map(tbl_has_device)
        col_df["has_data_json_column"] = col_df["table_name"].map(tbl_has_data)
        col_df.to_csv(args.out_dir / "column_inventory.csv", index=False)

        # Part D: JSON key discovery
        key_stats: Dict[Tuple[str, str], Dict[str, Any]] = {}
        sample_values: Dict[str, Dict[str, List[Any]]] = defaultdict(lambda: defaultdict(list))

        existing_tables = set(table_names)
        for table in CANDIDATE_JSON_TABLES:
            if table not in existing_tables:
                errored_tables[table] = "table_not_found"
                continue

            has_ts = bool(tbl_has_ts.get(table, False))
            has_device = bool(tbl_has_device.get(table, False))
            has_data = bool(tbl_has_data.get(table, False))
            if not (has_ts and has_device and has_data):
                errored_tables[table] = "missing_required_columns"
                continue

            if table in HIGH_FREQ_TABLES or table.startswith("sensor_"):
                errored_tables[table] = "excluded_highfreq_or_operational"
                continue

            sampled_count = 0
            table_rows_data = []
            try:
                for _, ep in episodes.iterrows():
                    if sampled_count >= args.sample_limit_per_table:
                        break
                    remain = int(args.sample_limit_per_table - sampled_count)
                    device_id = str(ep["device_id"])
                    start_ms = int(ep["early_window_start_ms"])
                    end_ms = int(ep["late_window_end_ms"])

                    q = f"SELECT data FROM `{args.main_schema}`.`{table}` WHERE device_id = %s AND timestamp >= %s AND timestamp < %s LIMIT {remain}"
                    cur.execute(q, (device_id, start_ms, end_ms))
                    rows = cur.fetchall()
                    sampled_count += len(rows)
                    table_rows_data.extend([r[0] for r in rows])

                if sampled_count == 0:
                    sampled_tables_no_rows.append(table)
                    continue

                sampled_tables_ok.append(table)

                parsed = []
                for raw in table_rows_data:
                    if raw is None:
                        continue
                    try:
                        obj = json.loads(raw) if isinstance(raw, str) else raw
                        if isinstance(obj, dict):
                            parsed.append(obj)
                    except Exception:
                        continue

                n_sampled_rows = len(parsed)
                if n_sampled_rows == 0:
                    sampled_tables_no_rows.append(table)
                    continue

                for obj in parsed:
                    for k, v in obj.items():
                        kk = (table, str(k))
                        if kk not in key_stats:
                            key_stats[kk] = {
                                "table_name": table,
                                "json_key": str(k),
                                "n_sampled_rows": n_sampled_rows,
                                "n_rows_with_key": 0,
                                "values": [],
                            }
                        key_stats[kk]["n_rows_with_key"] += 1
                        if len(key_stats[kk]["values"]) < 50:
                            key_stats[kk]["values"].append(v)

                for (t, k), st in list(key_stats.items()):
                    if t != table:
                        continue
                    vals = st["values"]
                    examples = []
                    seen = set()
                    for v in vals:
                        vv = v
                        try:
                            repr_v = json.dumps(vv, ensure_ascii=False)
                        except Exception:
                            repr_v = str(vv)
                        if repr_v not in seen:
                            seen.add(repr_v)
                            examples.append(repr_v)
                        if len(examples) >= 20:
                            break
                    sample_values[table][k] = examples

            except Exception as e:
                errored_tables[table] = f"query_or_parse_error:{e}"
                continue

        json_rows = []
        for (_, _), st in key_stats.items():
            table = st["table_name"]
            key = st["json_key"]
            n_sampled_rows = int(st["n_sampled_rows"])
            n_rows_with_key = int(st["n_rows_with_key"])
            pct = (n_rows_with_key / n_sampled_rows * 100.0) if n_sampled_rows else 0.0
            vals = st["values"]
            inferred = infer_type(vals)
            fam, notes = feature_family_for_key(table, key)
            ex = sample_values.get(table, {}).get(key, [])
            json_rows.append(
                {
                    "table_name": table,
                    "json_key": key,
                    "n_sampled_rows": n_sampled_rows,
                    "n_rows_with_key": n_rows_with_key,
                    "percent_rows_with_key": round(pct, 4),
                    "inferred_value_type": inferred,
                    "example_values_compact": " | ".join(ex),
                    "possible_feature_family": fam,
                    "possible_feature_notes": notes,
                }
            )

        json_df = pd.DataFrame(json_rows).sort_values(["table_name", "json_key"]) if json_rows else pd.DataFrame(
            columns=[
                "table_name",
                "json_key",
                "n_sampled_rows",
                "n_rows_with_key",
                "percent_rows_with_key",
                "inferred_value_type",
                "example_values_compact",
                "possible_feature_family",
                "possible_feature_notes",
            ]
        )
        json_df.to_csv(args.out_dir / "json_key_catalog.csv", index=False)

        with (args.out_dir / "json_sample_values.json").open("w", encoding="utf-8") as f:
            json.dump(sample_values, f, ensure_ascii=False, indent=2)

        # Part E README
        largest = table_df.sort_values("total_size_mb", ascending=False).head(20)
        useful = table_df[(table_df["use_for_now"] == "yes") & (~table_df["is_high_frequency_table"]) & (~table_df["is_sensor_operational_table"]) ]
        ignored = table_df[(table_df["use_for_now"] == "ignore") | (table_df["is_sensor_operational_table"]) ]
        hf = table_df[table_df["is_high_frequency_table"]]

        lines = []
        lines.append("# SQL Catalog Discovery\n")
        lines.append("This is a lightweight discovery run (no feature extraction, no large raw download).")
        lines.append("")
        lines.append("## Databases/Schemas Found")
        for _, r in db_df.iterrows():
            lines.append(f"- {r['schema_name']}: tables={r['table_count']}, rows_est={r['total_rows_estimate']}, total_size_mb={r['total_size_mb']}")
        lines.append("")
        lines.append("## Largest Tables (approx)")
        for _, r in largest.iterrows():
            lines.append(f"- {r['table_name']}: total_size_mb={r['total_size_mb']}, rows_est={r['table_rows_estimate']}")
        lines.append("")
        lines.append("## Likely Useful Tables For Digital Phenotyping (now)")
        for _, r in useful.iterrows():
            lines.append(f"- {r['table_name']} ({r['table_category_guess']})")
        lines.append("")
        lines.append("## Ignored For Now")
        lines.append("Operational sensor_* and excluded tables are listed here.")
        for _, r in ignored.iterrows():
            lines.append(f"- {r['table_name']} (category={r['table_category_guess']}, use={r['use_for_now']})")
        lines.append("")
        lines.append("## High-Frequency Tables (postponed)")
        for _, r in hf.iterrows():
            lines.append(f"- {r['table_name']}")
        lines.append("")
        lines.append("## JSON Key Discovery Notes")
        lines.append("- JSON sampling limited to top10 subject device episodes and T1-to-T2 windows.")
        lines.append("- Up to 200 sampled rows per table.")
        lines.append("- information_schema row counts/sizes are approximate.")
        lines.append("")

        if not json_df.empty:
            lines.append("## Feature-Relevant JSON Tables (simple interpretation)")
            for table in sorted(json_df['table_name'].unique().tolist()):
                lines.append(f"### {table}")
                tdf = json_df[json_df['table_name'] == table]
                keys = ", ".join(tdf['json_key'].head(30).tolist())
                lines.append(f"- JSON keys found (sample): {keys}")
                fams = ", ".join(sorted(set(tdf['possible_feature_family'].dropna().tolist())))
                lines.append(f"- Possible feature families: {fams}")
                lines.append("- Data quality concerns: sampled subset only; key prevalence may vary by device/time.")

        (args.out_dir / "README_sql_catalog.md").write_text("\n".join(lines), encoding="utf-8")

        # Part F print summary
        schemas = db_df['schema_name'].tolist() if not db_df.empty else []
        hf_tables = sorted(table_df[table_df['is_high_frequency_table'] == True]['table_name'].tolist())
        oper_ignored = sorted(table_df[table_df['is_sensor_operational_table'] == True]['table_name'].tolist())
        data_json_tables = sorted(col_df[col_df['has_data_json_column'] == True]['table_name'].unique().tolist())
        largest20 = largest[['table_name', 'total_size_mb']]

        print("Schemas/databases found:")
        print(schemas)
        print(f"Total number of tables in {args.main_schema}: {len(table_df)}")
        print("Top 20 largest tables by total_size_mb:")
        print(largest20.to_string(index=False))
        print("High-frequency tables:")
        print(hf_tables)
        print("Operational sensor_* tables (ignored):")
        print(oper_ignored)
        print("Tables with data JSON column:")
        print(data_json_tables)
        print("Tables successfully sampled for JSON keys:")
        print(sorted(sampled_tables_ok))
        print("Tables with no sampled rows in top10 T1-T2 windows:")
        print(sorted(sampled_tables_no_rows))
        print("Tables that errored:")
        print(errored_tables)

        print("Generated files:")
        for fn in [
            "database_inventory.csv",
            "table_inventory.csv",
            "column_inventory.csv",
            "json_key_catalog.csv",
            "json_sample_values.json",
            "README_sql_catalog.md",
        ]:
            print(args.out_dir / fn)

    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
