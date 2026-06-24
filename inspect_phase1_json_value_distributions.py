import argparse
import json
import re
from pathlib import Path

import pandas as pd

PHASE1_TABLES = [
    "screen",
    "applications_foreground",
    "keyboard",
    "touch",
    "plugin_google_activity_recognition",
    "gsm",
    "gsm_neighbor",
    "telephony",
    "messages",
    "aware_log",
]


def split_examples(example_text: str):
    if not isinstance(example_text, str) or not example_text.strip():
        return []
    parts = [p.strip() for p in example_text.split("|")]
    out = []
    for p in parts:
        p = p.strip().strip('"').strip()
        if p:
            out.append(p)
    return out


def classify_key(table: str, key: str, examples: list[str]):
    key_l = key.lower()
    ex_join = " ".join(examples).lower()

    safe = False
    likely_meaning = ""
    supports = ""
    warning = ""

    if table == "screen":
        if key_l in {"screen_status", "screen_state"}:
            safe = True
            likely_meaning = "Screen status/state code"
            supports = "state-aware screen event features; possible on/off state counts"
            warning = "Numeric codes require mapping validation before semantic labels."
        elif key_l == "timestamp":
            safe = True
            likely_meaning = "Event timestamp"
            supports = "event count, active days, night events"
            warning = "None"
        elif key_l == "device_id":
            safe = True
            likely_meaning = "Device identifier"
            supports = "episode aggregation only"
            warning = "Not a behavior signal."

    elif table == "applications_foreground":
        if key_l in {"package_name", "application_name"}:
            safe = True
            likely_meaning = "App identifier"
            supports = "unique apps, app diversity, app mix"
            warning = "System-app noise should be filtered where possible."
        elif key_l == "is_system_app":
            safe = True
            likely_meaning = "System app indicator"
            supports = "split user vs system app events"
            warning = "Value coding should be validated (0/1 vs text)."
        elif key_l == "timestamp":
            safe = True
            likely_meaning = "Event timestamp"
            supports = "event count, active days"
            warning = "None"
        elif key_l == "device_id":
            safe = True
            likely_meaning = "Device identifier"
            supports = "episode aggregation only"
            warning = "Not a behavior signal."

    elif table == "plugin_google_activity_recognition":
        if key_l in {"activity_name", "activity_type", "activities"}:
            safe = True
            likely_meaning = "Recognized activity label/code"
            supports = "still/walking/in_vehicle counts, activity diversity"
            warning = "Classifier-derived; device/model dependent confidence."
        elif key_l == "confidence":
            safe = True
            likely_meaning = "Recognition confidence"
            supports = "confidence-weighted metrics / filtering"
            warning = "Scale and reliability may vary by OS/version."
        elif key_l == "timestamp":
            safe = True
            likely_meaning = "Event timestamp"
            supports = "event count, active days"
            warning = "None"

    elif table == "messages":
        if key_l in {"message_type", "type", "direction"}:
            safe = True
            likely_meaning = "Message type/direction code"
            supports = "incoming/outgoing split if mapping known"
            warning = "Need mapping for code semantics before interpretation."
        elif key_l in {"trace"}:
            safe = False
            likely_meaning = "Trace/hash identifier"
            supports = "de-duplication only"
            warning = "Not directly interpretable behavior."
        elif key_l == "timestamp":
            safe = True
            likely_meaning = "Event timestamp"
            supports = "event count, active days"
            warning = "Sparse in current PoC."

    elif table == "telephony":
        if key_l in {"network_type", "sim_state", "phone_type", "data_enabled", "network_operator_name", "network_operator_code"}:
            safe = True
            likely_meaning = "Telephony/network state"
            supports = "context/state stability metrics"
            warning = "Contextual, not direct behavior."
        elif key_l in {"subscriber_id", "line_number", "imei_meid_esn", "sim_serial"}:
            safe = False
            likely_meaning = "Identifier/PII-like field"
            supports = "none for phenotype"
            warning = "Avoid using as feature."
        elif key_l == "timestamp":
            safe = True
            likely_meaning = "Event timestamp"
            supports = "event count, active days"
            warning = "None"

    elif table in {"gsm", "gsm_neighbor"}:
        if key_l in {"cid", "lac", "psc", "signal_strength"}:
            safe = True
            likely_meaning = "Cell/tower context fields"
            supports = "context diversity and stability proxies"
            warning = "Network infrastructure confounding likely."
        elif key_l == "bit_error_rate":
            safe = False
            likely_meaning = "Radio quality metric"
            supports = "optional quality context"
            warning = "May have sentinel values; validate before use."
        elif key_l == "timestamp":
            safe = True
            likely_meaning = "Event timestamp"
            supports = "event count, active days"
            warning = "None"

    elif table == "aware_log":
        if key_l == "log_message":
            safe = True
            likely_meaning = "System/logging message"
            supports = "data quality denominator features"
            warning = "Not direct phenotype; keep data-quality only."
        elif key_l == "timestamp":
            safe = True
            likely_meaning = "Log timestamp"
            supports = "coverage days, logging density"
            warning = "Data-quality only usage."

    elif table in {"keyboard", "touch"}:
        if key_l == "timestamp":
            safe = True
            likely_meaning = "Event timestamp"
            supports = "event count, active days"
            warning = "None"
        elif table == "touch" and key_l in {"touch_action", "touch_app"}:
            safe = True
            likely_meaning = "Touch action/app context"
            supports = "action-type mix"
            warning = "App/UI implementation differences."
        elif table == "keyboard" and key_l in {"package_name"}:
            safe = True
            likely_meaning = "App package during typing"
            supports = "typing context breadth"
            warning = "Do not use raw text content fields as phenotype."
        elif table == "keyboard" and key_l in {"current_text", "before_text"}:
            safe = False
            likely_meaning = "Raw typed text content"
            supports = "none in phase-1 due privacy/interpretability"
            warning = "Privacy-sensitive; avoid direct use."

    if not likely_meaning:
        likely_meaning = "Unclear / generic metadata"
    if not supports:
        supports = "manual review required"
    if not warning:
        warning = "Needs manual key mapping/validation."

    return safe, likely_meaning, supports, warning


def main():
    ap = argparse.ArgumentParser(description="Inspect phase-1 JSON value distributions (no SQL).")
    ap.add_argument("--table-review", default="output/analysis_candidates/phase1_features/phase1_table_json_key_review.csv")
    ap.add_argument("--json-key-catalog", default="output/sql_catalog/json_key_catalog.csv")
    ap.add_argument("--json-sample-values", default="output/sql_catalog/json_sample_values.json")
    ap.add_argument("--feature-plan", default="output/analysis_candidates/phase1_features/phase1_feature_plan.csv")
    ap.add_argument("--out-dir", default="output/analysis_candidates/phase1_features")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    table_review = pd.read_csv(args.table_review, dtype=str)
    json_cat = pd.read_csv(args.json_key_catalog, dtype=str)
    feature_plan = pd.read_csv(args.feature_plan, dtype=str)

    # Load sample json blob for completeness; currently not required for parsing because catalog has examples
    if Path(args.json_sample_values).exists():
        _ = json.loads(Path(args.json_sample_values).read_text())

    sub = json_cat[json_cat["table_name"].isin(PHASE1_TABLES)].copy()

    rows = []
    safe_keys = []
    manual_keys = []

    for _, r in sub.iterrows():
        table = str(r["table_name"])
        key = str(r["json_key"])
        inferred = str(r.get("inferred_value_type", ""))
        examples_text = str(r.get("example_values_compact", ""))
        examples = split_examples(examples_text)
        distinct_n = len(set(examples))

        safe, meaning, supports, warning = classify_key(table, key, examples)

        rows.append({
            "table_name": table,
            "json_key": key,
            "inferred_value_type": inferred,
            "example_values_compact": examples_text,
            "n_distinct_example_values": distinct_n,
            "likely_meaning": meaning,
            "safe_for_feature_extraction": "yes" if safe else "manual_review",
            "features_supported": supports,
            "interpretation_warning": warning,
        })

        if safe:
            safe_keys.append((table, key))
        else:
            manual_keys.append((table, key))

    review_df = pd.DataFrame(rows).sort_values(["table_name", "json_key"])
    review_path = out_dir / "phase1_json_value_distribution_review.csv"
    review_df.to_csv(review_path, index=False)

    # downgrade/upgrade recommendations from key evidence vs plan
    downgrade = []
    upgrade = []

    # screen state-specific upgrade
    screen_keys = set(review_df[(review_df["table_name"] == "screen") & (review_df["safe_for_feature_extraction"] == "yes")]["json_key"].tolist())
    if "screen_status" in screen_keys or "screen_state" in screen_keys:
        upgrade.append("screen: can upgrade to state-aware features (e.g., per-status counts) after code mapping validation")

    # app id upgrade
    app_keys = set(review_df[(review_df["table_name"] == "applications_foreground") & (review_df["safe_for_feature_extraction"] == "yes")]["json_key"].tolist())
    if "package_name" in app_keys or "application_name" in app_keys:
        upgrade.append("applications_foreground: unique app and app diversity features are supported")

    # activity labels upgrade
    act_keys = set(review_df[(review_df["table_name"] == "plugin_google_activity_recognition") & (review_df["safe_for_feature_extraction"] == "yes")]["json_key"].tolist())
    if {"activity_name", "activity_type", "activities"} & act_keys:
        upgrade.append("activity_recognition: specific still/walking/in_vehicle features are supported")

    # messages/telephony direction caution
    msg_keys = set(review_df[review_df["table_name"] == "messages"]["json_key"].tolist())
    if "message_type" in msg_keys:
        downgrade.append("messages: incoming/outgoing features require explicit code mapping for message_type")

    tel_keys = set(review_df[review_df["table_name"] == "telephony"]["json_key"].tolist())
    if "network_type" in tel_keys:
        upgrade.append("telephony: context-state features can be used (network/sim state), not direct social behavior")

    # aware_log always data quality only
    downgrade.append("aware_log: keep as data-quality denominator only, not behavioral phenotype")

    # markdown summary
    md = []
    md.append("# Phase 1 JSON Value Distribution Review")
    md.append("")
    md.append("Interpretation/QC review only. No SQL queried. No new feature extraction performed.")
    md.append("")
    md.append("## Table Checks")
    md.append("- screen: state key present (`screen_status`) -> state-aware features possible with code validation.")
    md.append("- applications_foreground: app identifier keys present (`package_name`, `application_name`).")
    md.append("- plugin_google_activity_recognition: activity label structures present (`activity_name`, `activity_type`, `activities`).")
    md.append("- messages/telephony: type/state keys present but code semantics need validation.")
    md.append("- gsm/gsm_neighbor: tower/context identifiers present (`cid`, `lac`, `psc`).")
    md.append("- aware_log: system/log messages present; remains data-quality only.")
    md.append("")
    md.append("## Safe Keys")
    md.append("- " + ", ".join([f"{t}.{k}" for t, k in safe_keys[:80]]) if safe_keys else "- none")
    md.append("")
    md.append("## Manual Review Keys")
    md.append("- " + ", ".join([f"{t}.{k}" for t, k in manual_keys[:80]]) if manual_keys else "- none")
    md.append("")
    md.append("## Feature Plan Adjustments")
    md.append("### Downgrade/Keep Cautious")
    for d in downgrade:
        md.append(f"- {d}")
    md.append("### Upgrade Candidates")
    for u in upgrade:
        md.append(f"- {u}")

    readme_path = out_dir / "README_phase1_json_value_distribution_review.md"
    readme_path.write_text("\n".join(md))

    # requested prints
    print("keys_safe_for_interpretation:")
    print([f"{t}.{k}" for t, k in safe_keys])
    print("\nkeys_requiring_manual_review:")
    print([f"{t}.{k}" for t, k in manual_keys])
    print("\nfeatures_to_downgrade_or_remove:")
    print(downgrade)
    print("\nfeatures_upgrade_candidates:")
    print(upgrade)
    print("\ngenerated_files:")
    print("-", review_path)
    print("-", readme_path)


if __name__ == "__main__":
    main()
