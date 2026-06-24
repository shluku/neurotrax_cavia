import argparse
import json
from pathlib import Path
import pandas as pd

CORE = [
    "screen", "applications_foreground", "keyboard", "touch", "plugin_google_activity_recognition"
]
OPTIONAL = ["gsm", "gsm_neighbor", "telephony", "messages"]
DQ = ["aware_log"]


def parse_examples(val):
    if pd.isna(val):
        return ""
    s = str(val)
    return s[:220]


def has_key(keys, candidates):
    ks = set(keys)
    for c in candidates:
        if c in ks:
            return True
    return False


def table_ready(keys, table):
    ks = set(keys)
    if table == "screen":
        return "timestamp" in ks and has_key(ks, ["screen_status", "screen_state"])
    if table == "applications_foreground":
        return "timestamp" in ks and has_key(ks, ["package_name", "application_name"])
    if table == "keyboard":
        return "timestamp" in ks
    if table == "touch":
        return "timestamp" in ks
    if table == "plugin_google_activity_recognition":
        return "timestamp" in ks and has_key(ks, ["activity_type", "activity_name", "activities"])
    if table in {"gsm", "gsm_neighbor", "telephony", "messages", "aware_log"}:
        return "timestamp" in ks
    return False


def base_feature(feature_name, source_table, role, req_keys, agg, unit, interp, hi_means, min_rows, min_days, miss_interp, qflag, pri):
    return {
        "feature_name": feature_name,
        "source_table": source_table,
        "phase1_role": role,
        "required_json_keys": req_keys,
        "window_level": "early_and_late",
        "aggregation_logic_plain_english": agg,
        "expected_unit": unit,
        "behavioral_interpretation": interp,
        "higher_value_means": hi_means,
        "minimum_required_rows": min_rows,
        "minimum_required_days": min_days,
        "missing_data_interpretation": miss_interp,
        "quality_flag_needed": qflag,
        "extraction_priority": pri,
        "extraction_status": "planned",
    }


def main():
    ap = argparse.ArgumentParser(description="Review phase1 JSON keys and build feature plan (no SQL).")
    ap.add_argument("--shortlist", default="output/analysis_candidates/sql_coverage/phase1_feature_table_shortlist.csv")
    ap.add_argument("--json-key-catalog", default="output/sql_catalog/json_key_catalog.csv")
    ap.add_argument("--json-sample-values", default="output/sql_catalog/json_sample_values.json")
    ap.add_argument("--feature-dict", default="output/sql_catalog/sql_feature_dictionary.csv")
    ap.add_argument("--table-interpret", default="output/sql_catalog/sql_table_interpretation.csv")
    ap.add_argument("--table-readiness", default="output/analysis_candidates/sql_coverage/top10_table_readiness.csv")
    ap.add_argument("--subject-readiness", default="output/analysis_candidates/sql_coverage/top10_subject_readiness.csv")
    ap.add_argument("--out-dir", default="output/analysis_candidates/phase1_features")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    shortlist = pd.read_csv(args.shortlist, dtype=str)
    json_cat = pd.read_csv(args.json_key_catalog, dtype=str)
    table_ready_df = pd.read_csv(args.table_readiness, dtype=str)
    subj_ready = pd.read_csv(args.subject_readiness, dtype=str)

    if Path(args.json_sample_values).exists():
        _ = json.loads(Path(args.json_sample_values).read_text())
    _ = pd.read_csv(args.feature_dict, dtype=str) if Path(args.feature_dict).exists() else pd.DataFrame()
    _ = pd.read_csv(args.table_interpret, dtype=str) if Path(args.table_interpret).exists() else pd.DataFrame()

    shortlist = shortlist[shortlist["include_in_phase1"].astype(str).str.lower() == "yes"].copy()

    tr_idx = table_ready_df.set_index("table_name", drop=False)
    table_reviews = []

    features = []

    for _, r in shortlist.iterrows():
        t = r["table_name"]
        role = r["phase1_role"]
        domain = r["phenotype_domain"]
        sub = json_cat[json_cat["table_name"] == t].copy()
        keys = sub["json_key"].dropna().astype(str).tolist()
        key_join = ";".join(sorted(set(keys)))

        important = []
        needed = []
        interp = ""
        concerns = ""
        priority = "medium"

        if t == "screen":
            important = [k for k in ["screen_status", "timestamp", "device_id"] if k in keys]
            needed = [k for k in ["screen_status", "timestamp"] if k in keys]
            interp = "Screen interaction/state events; proxy for phone engagement timing."
            concerns = "Screen state semantics can vary by OS/device; not equal to active cognition."
            priority = "high"

            features += [
                base_feature("screen_event_count", t, role, "timestamp", "Count rows per window.", "count", "Overall screen interaction intensity.", "more screen-related events", 30, 2, "Missing rows may be sensor/logging missingness.", "aware_log_coverage_flag", "high"),
                base_feature("active_screen_days", t, role, "timestamp", "Count distinct days with >=1 row.", "days", "Regularity of screen activity.", "more active days", 30, 2, "Do not treat missing as inactivity.", "aware_log_coverage_flag", "high"),
                base_feature("night_screen_event_count", t, role, "timestamp(+local hour)", "Count events in local night hours.", "count", "Possible night-time phone activity pattern.", "more night events", 30, 2, "Sparse logs can bias night estimates.", "aware_log_coverage_flag", "medium"),
                base_feature("screen_events_per_active_day", t, role, "timestamp", "screen_event_count / active_screen_days.", "count/day", "Daily intensity on active days.", "higher event density", 30, 2, "Undefined if no active days.", "aware_log_coverage_flag", "high"),
            ]
        elif t == "applications_foreground":
            important = [k for k in ["package_name", "application_name", "timestamp"] if k in keys]
            needed = [k for k in ["timestamp"] if k in keys]
            interp = "Foreground app events; proxy for app-use behavior and routine."
            concerns = "Foreground does not equal intentional use; system/app noise present."
            priority = "high"

            features += [
                base_feature("app_foreground_event_count", t, role, "timestamp", "Count foreground events.", "count", "Overall app engagement intensity.", "more app events", 30, 2, "May reflect background/system activity.", "aware_log_coverage_flag", "high"),
                base_feature("active_app_days", t, role, "timestamp", "Count distinct days with foreground events.", "days", "Regular app usage days.", "more active days", 30, 2, "Missing rows not equal no app use.", "aware_log_coverage_flag", "high"),
                base_feature("unique_foreground_apps", t, role, "package_name or application_name", "Count unique app identifiers.", "count", "Breadth/diversity of app usage.", "higher diversity", 30, 2, "Depends on availability of package/application key.", "aware_log_coverage_flag", "medium"),
                base_feature("app_use_diversity", t, role, "package_name or application_name", "Compute entropy/diversity from app event distribution.", "index", "Behavioral diversity of app interactions.", "higher diversity", 50, 2, "Unstable for low counts.", "aware_log_coverage_flag", "medium"),
            ]
        elif t == "keyboard":
            important = [k for k in ["timestamp", "current_text", "before_text", "is_password"] if k in keys]
            needed = [k for k in ["timestamp"] if k in keys]
            interp = "Keyboard interactions; proxy for active text input behavior."
            concerns = "Keyboard provider/settings affect logs; privacy-safe aggregation only."
            priority = "high"

            features += [
                base_feature("keyboard_event_count", t, role, "timestamp", "Count keyboard rows.", "count", "Text-input interaction intensity.", "more keyboard activity", 20, 2, "Do not infer inactivity from missing rows.", "aware_log_coverage_flag", "high"),
                base_feature("active_keyboard_days", t, role, "timestamp", "Count distinct days with keyboard events.", "days", "Regularity of keyboard use.", "more active days", 20, 2, "Sparse days reduce comparability.", "aware_log_coverage_flag", "high"),
                base_feature("keyboard_events_per_active_day", t, role, "timestamp", "keyboard_event_count / active_keyboard_days.", "count/day", "Daily keyboard intensity.", "higher typing intensity", 20, 2, "Undefined if no active days.", "aware_log_coverage_flag", "high"),
            ]
        elif t == "touch":
            important = [k for k in ["timestamp", "touch_action", "touch_app"] if k in keys]
            needed = [k for k in ["timestamp"] if k in keys]
            interp = "Touch interactions; broad proxy for phone interaction volume."
            concerns = "Touch event granularity differs across devices/apps."
            priority = "high"

            features += [
                base_feature("touch_event_count", t, role, "timestamp", "Count touch events.", "count", "Phone interaction intensity.", "more interaction", 30, 2, "Missing rows may be logging gaps.", "aware_log_coverage_flag", "high"),
                base_feature("active_touch_days", t, role, "timestamp", "Count distinct days with touch events.", "days", "Regularity of interaction.", "more active days", 30, 2, "Not comparable when sparse.", "aware_log_coverage_flag", "high"),
                base_feature("touch_events_per_active_day", t, role, "timestamp", "touch_event_count / active_touch_days.", "count/day", "Daily interaction density.", "higher density", 30, 2, "Undefined if no active days.", "aware_log_coverage_flag", "high"),
            ]
        elif t == "plugin_google_activity_recognition":
            important = [k for k in ["activity_type", "activity_name", "activities", "timestamp"] if k in keys]
            needed = [k for k in ["timestamp", "activity_type", "activity_name", "activities"] if k in keys]
            interp = "Model-derived physical activity states over time."
            concerns = "Activity labels are classifier outputs and device/model dependent."
            priority = "high"

            features += [
                base_feature("activity_event_count", t, role, "timestamp", "Count activity recognition events.", "count", "Sampling density of inferred activity states.", "more observed activity events", 20, 2, "No events may be missing logging.", "aware_log_coverage_flag", "high"),
                base_feature("active_activity_days", t, role, "timestamp", "Count distinct days with activity events.", "days", "Days with inferred movement context.", "more active days", 20, 2, "Sparse coverage limits change analysis.", "aware_log_coverage_flag", "high"),
                base_feature("still_event_count", t, role, "activity_name/activity_type", "Count events labeled still.", "count", "Sedentary context proportion/intensity.", "more still-state observations", 20, 2, "Depends on key semantics.", "aware_log_coverage_flag", "medium"),
                base_feature("walking_event_count", t, role, "activity_name/activity_type", "Count events labeled walking.", "count", "Walking-related activity signal.", "more walking-state observations", 20, 2, "Depends on label availability.", "aware_log_coverage_flag", "medium"),
                base_feature("in_vehicle_event_count", t, role, "activity_name/activity_type", "Count events labeled in_vehicle.", "count", "Mobility-by-transport context.", "more in-vehicle observations", 20, 2, "Can reflect travel routine differences.", "aware_log_coverage_flag", "medium"),
                base_feature("activity_diversity", t, role, "activity_name/activity_type", "Entropy/diversity over activity labels.", "index", "Behavioral variety of inferred activity states.", "higher activity variety", 30, 2, "Unstable under low event counts.", "aware_log_coverage_flag", "medium"),
            ]
        elif t in ["gsm", "gsm_neighbor"]:
            important = [k for k in ["timestamp", "cid", "lac", "psc", "signal_strength"] if k in keys]
            needed = [k for k in ["timestamp"] if k in keys]
            interp = "Cellular context and tower-level mobility proxy."
            concerns = "Network infrastructure differences can bias comparability."
            priority = "medium"

            features += [
                base_feature(f"{t}_event_count", t, role, "timestamp", "Count events.", "count", "Cellular context sampling intensity.", "more observed events", 20, 2, "Sparse events limit interpretation.", "aware_log_coverage_flag", "medium"),
                base_feature(f"{t}_active_days", t, role, "timestamp", "Count active days.", "days", "Days with cellular context observations.", "more active days", 20, 2, "Missing not equal no mobility.", "aware_log_coverage_flag", "medium"),
                base_feature(f"{t}_cellular_context_diversity", t, role, "cid/lac/psc if present", "Count/entropy of unique cell identifiers.", "index", "Potential movement/context diversity proxy.", "higher context diversity", 30, 2, "Heavily network-dependent.", "aware_log_coverage_flag", "low"),
            ]
        elif t == "telephony":
            important = [k for k in ["timestamp", "network_type", "sim_state", "phone_type"] if k in keys]
            needed = [k for k in ["timestamp"] if k in keys]
            interp = "Telephony/network state context, not direct behavior alone."
            concerns = "More state than action; combine with behavioral tables."
            priority = "medium"

            features += [
                base_feature("telephony_event_count", t, role, "timestamp", "Count telephony state rows.", "count", "Availability of telephony context observations.", "more observed state events", 20, 2, "Not direct activity measure.", "aware_log_coverage_flag", "medium"),
                base_feature("active_social_days", t, role, "timestamp", "Count distinct days with telephony/message context events.", "days", "Potential communication context regularity.", "more context days", 20, 2, "Use jointly with messages/calls.", "aware_log_coverage_flag", "medium"),
            ]
        elif t == "messages":
            important = [k for k in ["timestamp", "message_type", "trace"] if k in keys]
            needed = [k for k in ["timestamp"] if k in keys]
            interp = "Messaging events; proxy for social communication activity."
            concerns = "Sparse coverage in current top10; direction/type may be limited."
            priority = "low"

            features += [
                base_feature("message_event_count", t, role, "timestamp", "Count message events.", "count", "Message-related communication activity.", "more messaging activity", 10, 2, "Sparse data may be unstable.", "aware_log_coverage_flag", "low"),
                base_feature("active_social_days", t, role, "timestamp", "Count distinct days with message events.", "days", "Communication-activity days.", "more social-active days", 10, 2, "Missing rows not equal social inactivity.", "aware_log_coverage_flag", "low"),
            ]
        elif t == "aware_log":
            important = [k for k in ["timestamp", "log_message"] if k in keys]
            needed = [k for k in ["timestamp", "log_message"] if k in keys]
            interp = "System/data-sync logs used as denominator and quality flag source."
            concerns = "Not a phenotype endpoint; interpret only as data quality context."
            priority = "high"

            features += [
                base_feature("aware_log_rows", t, role, "timestamp", "Count aware_log rows.", "count", "Logging/system activity density.", "higher logging density", 20, 2, "Does not imply patient behavior.", "none", "high"),
                base_feature("aware_log_active_days", t, role, "timestamp", "Count days with aware_log rows.", "days", "Observed logging coverage days.", "more coverage days", 20, 2, "Coverage proxy only.", "none", "high"),
                base_feature("data_logging_coverage_days", t, role, "timestamp", "Distinct days with any logging markers.", "days", "Denominator for feature reliability checks.", "better observability", 20, 2, "Not a behavioral construct.", "none", "high"),
                base_feature("system_log_density", t, role, "timestamp", "aware_log_rows per active day.", "rows/day", "Operational logging intensity.", "more system logging", 20, 2, "Use only to qualify other features.", "none", "high"),
            ]

        readiness = "yes" if table_ready(keys, t) else "manual_review"
        if t == "aware_log":
            readiness = "yes"

        cov_status = tr_idx.loc[t, "readiness_status"] if t in tr_idx.index else "unknown"
        table_reviews.append({
            "table_name": t,
            "phase1_role": role,
            "phenotype_domain": domain,
            "coverage_readiness_status": cov_status,
            "json_keys_found": key_join,
            "most_important_keys": ";".join(important),
            "keys_needed_for_phase1_features": ";".join(needed),
            "interpretation_summary": interp,
            "data_quality_concerns": concerns,
            "recommended_feature_priority": priority,
            "proceed_to_extraction": readiness,
        })

    reviews_df = pd.DataFrame(table_reviews)
    reviews_path = out_dir / "phase1_table_json_key_review.csv"
    reviews_df.to_csv(reviews_path, index=False)

    feat_df = pd.DataFrame(features)
    feat_path = out_dir / "phase1_feature_plan.csv"
    feat_df.to_csv(feat_path, index=False)

    baseline_ready_n = int((subj_ready["baseline_phenotype_ready"].astype(str).str.lower() == "true").sum())
    change_ready_n = int((subj_ready["change_analysis_ready"].astype(str).str.lower() == "true").sum())

    md = []
    md.append("# Phase 1 Feature Plan (Pre-Extraction)")
    md.append("")
    md.append("## Executive Summary")
    md.append("- This is pre-extraction planning only.")
    md.append(f"- Baseline phenotype is possible for {baseline_ready_n}/10 subjects.")
    md.append(f"- Early-vs-late change is currently possible for {change_ready_n}/10 subjects (024 and 077).")
    md.append("- Missing data must not be interpreted as zero activity.")
    md.append("- aware_log is data-quality denominator, not direct phenotype.")
    md.append("")
    md.append("## Table-by-Table Review")

    for _, rr in reviews_df.iterrows():
        md.append(f"### {rr['table_name']}")
        md.append(f"- Role: {rr['phase1_role']}")
        md.append(f"- Coverage readiness: {rr['coverage_readiness_status']}")
        md.append(f"- Likely measures: {rr['interpretation_summary']}")
        md.append(f"- JSON keys found: {rr['json_keys_found']}")
        md.append(f"- Important keys: {rr['most_important_keys']}")
        md.append(f"- Proposed features: {', '.join(feat_df[feat_df['source_table']==rr['table_name']]['feature_name'].tolist())}")
        md.append(f"- Interpretation warnings: {rr['data_quality_concerns']}")
        md.append(f"- Ready for extraction: {rr['proceed_to_extraction']}")
        md.append("")

    md.append("## Phenotype vs Data-Quality Distinction")
    md.append("- Phenotype tables: screen, applications_foreground, keyboard, touch, plugin_google_activity_recognition, gsm, gsm_neighbor, telephony, messages.")
    md.append("- Data-quality table: aware_log only.")

    readme_path = out_dir / "README_phase1_feature_plan.md"
    readme_path.write_text("\n".join(md))

    ready_tables = reviews_df[reviews_df["proceed_to_extraction"] == "yes"]["table_name"].tolist()
    manual_tables = reviews_df[reviews_df["proceed_to_extraction"] != "yes"]["table_name"].tolist()

    print("tables_reviewed:", reviews_df["table_name"].tolist())
    print("tables_ready_for_extraction:", ready_tables)
    print("tables_requiring_manual_review:", manual_tables)
    print("number_of_proposed_features:", len(feat_df))
    print("top_20_proposed_features:")
    print(feat_df[["feature_name", "source_table", "extraction_priority"]].head(20).to_string(index=False))

    print("generated_files:")
    print("-", reviews_path)
    print("-", feat_path)
    print("-", readme_path)


if __name__ == "__main__":
    main()
