from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd


def norm_str(s: object) -> str:
    if pd.isna(s):
        return ""
    return str(s).strip()


def split_device_ids(raw: object) -> List[str]:
    if pd.isna(raw):
        return []
    parts = [x.strip() for x in str(raw).split(";")]
    return [p for p in parts if p]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build top10 subject-device episode map (no SQL).")
    parser.add_argument("--top10", type=Path, default=Path("output/analysis_candidates/top10_global_decline.csv"))
    parser.add_argument("--candidates", type=Path, default=Path("output/analysis_candidates/cognitive_candidates_all.csv"))
    parser.add_argument("--label-map", type=Path, default=Path("output/label_device_map.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("output/analysis_candidates"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    top10 = pd.read_csv(args.top10, dtype=str)
    candidates = pd.read_csv(args.candidates, dtype=str)
    label_map = pd.read_csv(args.label_map, dtype=str)

    top10["Subject_ID_D"] = top10["Subject_ID_D"].astype("string")
    top10["Subject_ID_N"] = top10["Subject_ID_N"].astype("string")

    label_map["label"] = label_map["label"].astype("string")
    if "device_ids" not in label_map.columns:
        label_map["device_ids"] = ""

    label_to_devices: Dict[str, List[str]] = {}
    for _, r in label_map.iterrows():
        label = norm_str(r.get("label", ""))
        if not label:
            continue
        devices = split_device_ids(r.get("device_ids", ""))
        if label in label_to_devices:
            existing = label_to_devices[label]
            for d in devices:
                if d not in existing:
                    existing.append(d)
        else:
            label_to_devices[label] = devices

    key_cols = [
        "global_T1", "global_T2", "global_delta", "global_decline_amount",
        "T1_date_iso", "T2_date_iso",
        "T1_start_ms", "T1_end_ms", "T2_start_ms", "T2_end_ms",
        "early_window_start_ms", "early_window_end_ms", "late_window_start_ms", "late_window_end_ms",
        "early_window_start_iso", "early_window_end_iso", "late_window_start_iso", "late_window_end_iso",
        "cognitive_completeness_percent", "n_special_flags_total", "n_FP", "n_DI",
    ]
    cand_idx = candidates.set_index("Subject_ID_N", drop=False) if "Subject_ID_N" in candidates.columns else None
    for c in key_cols:
        if c not in top10.columns:
            top10[c] = pd.NA
    if cand_idx is not None:
        for i, row in top10.iterrows():
            sid_n = norm_str(row.get("Subject_ID_N", ""))
            if sid_n and sid_n in cand_idx.index:
                for c in key_cols:
                    if pd.isna(top10.at[i, c]) or str(top10.at[i, c]).strip() == "":
                        top10.at[i, c] = cand_idx.at[sid_n, c] if c in cand_idx.columns else pd.NA

    rows = []
    summary_rows = []

    for _, r in top10.iterrows():
        sid_n = norm_str(r.get("Subject_ID_N", ""))
        sid_d = norm_str(r.get("Subject_ID_D", ""))
        label = sid_d

        base = {
            "Subject_ID_N": sid_n,
            "Subject_ID_D": sid_d,
            "label": label,
            "global_T1": r.get("global_T1", ""),
            "global_T2": r.get("global_T2", ""),
            "global_delta": r.get("global_delta", ""),
            "global_decline_amount": r.get("global_decline_amount", ""),
            "T1_date_iso": r.get("T1_date_iso", ""),
            "T2_date_iso": r.get("T2_date_iso", ""),
            "T1_start_ms": r.get("T1_start_ms", ""),
            "T1_end_ms": r.get("T1_end_ms", ""),
            "T2_start_ms": r.get("T2_start_ms", ""),
            "T2_end_ms": r.get("T2_end_ms", ""),
            "early_window_start_ms": r.get("early_window_start_ms", ""),
            "early_window_end_ms": r.get("early_window_end_ms", ""),
            "late_window_start_ms": r.get("late_window_start_ms", ""),
            "late_window_end_ms": r.get("late_window_end_ms", ""),
            "early_window_start_iso": r.get("early_window_start_iso", ""),
            "early_window_end_iso": r.get("early_window_end_iso", ""),
            "late_window_start_iso": r.get("late_window_start_iso", ""),
            "late_window_end_iso": r.get("late_window_end_iso", ""),
            "cognitive_completeness_percent": r.get("cognitive_completeness_percent", ""),
            "n_special_flags_total": r.get("n_special_flags_total", ""),
            "n_FP": r.get("n_FP", ""),
            "n_DI": r.get("n_DI", ""),
        }

        summary_base = {
            "Subject_ID_N": sid_n,
            "Subject_ID_D": sid_d,
            "T1_start_ms": r.get("T1_start_ms", ""),
            "T1_end_ms": r.get("T1_end_ms", ""),
            "T2_start_ms": r.get("T2_start_ms", ""),
            "T2_end_ms": r.get("T2_end_ms", ""),
            "T1_date_iso": r.get("T1_date_iso", ""),
            "T2_date_iso": r.get("T2_date_iso", ""),
            "early_window_start_ms": r.get("early_window_start_ms", ""),
            "early_window_end_ms": r.get("early_window_end_ms", ""),
            "late_window_start_ms": r.get("late_window_start_ms", ""),
            "late_window_end_ms": r.get("late_window_end_ms", ""),
            "early_window_start_iso": r.get("early_window_start_iso", ""),
            "early_window_end_iso": r.get("early_window_end_iso", ""),
            "late_window_start_iso": r.get("late_window_start_iso", ""),
            "late_window_end_iso": r.get("late_window_end_iso", ""),
        }

        if not sid_d or sid_d not in label_to_devices:
            status = "no_label_match"
            rows.append({**base, "device_id": "", "device_episode_index": "", "n_devices_for_subject": 0, "mapping_status": status})
            summary_rows.append({**summary_base, "n_devices_for_subject": 0, "mapping_status_summary": status, "device_ids_joined": ""})
            continue

        devices = label_to_devices.get(sid_d, [])
        if len(devices) == 0:
            status = "label_found_no_device_ids"
            rows.append({**base, "device_id": "", "device_episode_index": "", "n_devices_for_subject": 0, "mapping_status": status})
            summary_rows.append({**summary_base, "n_devices_for_subject": 0, "mapping_status_summary": status, "device_ids_joined": ""})
            continue

        status = "ok"
        for i, d in enumerate(devices, start=1):
            rows.append({**base, "device_id": d, "device_episode_index": i, "n_devices_for_subject": len(devices), "mapping_status": status})

        summary_rows.append({**summary_base, "n_devices_for_subject": len(devices), "mapping_status_summary": status, "device_ids_joined": ";".join(devices)})

    episodes = pd.DataFrame(rows)
    summary = pd.DataFrame(summary_rows)

    out_episodes = args.out_dir / "top10_subject_device_episodes.csv"
    out_summary = args.out_dir / "top10_subject_device_summary.csv"

    episodes.to_csv(out_episodes, index=False)
    summary.to_csv(out_summary, index=False)

    n_top10 = len(top10)
    n_no_label = int((summary["mapping_status_summary"] == "no_label_match").sum()) if not summary.empty else 0
    n_no_devices = int((summary["mapping_status_summary"] == "label_found_no_device_ids").sum()) if not summary.empty else 0
    n_matched = n_top10 - n_no_label
    total_episodes = int((episodes["mapping_status"] == "ok").sum()) if not episodes.empty and "mapping_status" in episodes.columns else 0
    multi_device = summary[summary["n_devices_for_subject"].fillna(0).astype(float) > 1]

    print("Top10 device episode mapping summary:")
    print(f"number_of_top10_subjects={n_top10}")
    print(f"number_matched_to_label_device_map={n_matched}")
    print(f"number_without_label_match={n_no_label}")
    print(f"number_with_no_device_ids={n_no_devices}")
    print(f"total_device_episodes={total_episodes}")
    print(f"subjects_with_multiple_device_ids={len(multi_device)}")

    print("\nFull summary table:")
    if summary.empty:
        print("(empty)")
    else:
        print(summary.to_string(index=False))

    print("\nGenerated files:")
    print(out_episodes)
    print(out_summary)


if __name__ == "__main__":
    main()
