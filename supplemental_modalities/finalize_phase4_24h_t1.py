"""Finalize the append-only Phase 4 supplemental feature outputs.

Interrupted runs can leave an error row followed by a successful retry for the
same patient. This command keeps the last row per patient, deduplicates the
feature tables, and writes a compact summary. The JSONL checkpoint is retained
unchanged as the audit trail.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .config import MODALITIES, OUTPUT_ROOT


OUTPUT_DIR = OUTPUT_ROOT / "phase4_24h_t1"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def write_deduplicated(path: Path, keys: list[str]) -> pd.DataFrame:
    frame = read_csv(path)
    if frame.empty:
        return frame
    available_keys = [key for key in keys if key in frame.columns]
    if available_keys:
        frame = frame.drop_duplicates(available_keys, keep="last")
    if "Subject_ID_D" in frame.columns:
        frame = frame.sort_values("Subject_ID_D", kind="stable")
    frame.to_csv(path, index=False)
    return frame


def finalize(modalities: list[str]) -> pd.DataFrame:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for modality in modalities:
        status = write_deduplicated(
            OUTPUT_DIR / f"{modality}_patient_status.csv",
            ["Subject_ID_D"],
        )
        write_deduplicated(
            OUTPUT_DIR / f"{modality}_features_wide.csv",
            ["Subject_ID_D"],
        )
        write_deduplicated(
            OUTPUT_DIR / f"{modality}_features_long.csv",
            ["Subject_ID_D", "feature_name"],
        )
        write_deduplicated(
            OUTPUT_DIR / f"{modality}_coverage.csv",
            ["Subject_ID_D", "device_id", "window_rule"],
        )
        if status.empty:
            rows.append(
                {
                    "modality": modality,
                    "patients": 0,
                    "calculated": 0,
                    "missing": 0,
                    "errors": 0,
                    "rows_in_window": 0,
                }
            )
            continue
        status_values = status.get("status", pd.Series(dtype=str)).astype(str)
        rows.append(
            {
                "modality": modality,
                "patients": int(status["Subject_ID_D"].nunique()) if "Subject_ID_D" in status else len(status),
                "calculated": int(status_values.eq("calculated").sum()),
                "missing": int(status_values.str.startswith("missing").sum()),
                "errors": int(status_values.eq("error").sum()),
                "rows_in_window": int(pd.to_numeric(status.get("rows_in_window"), errors="coerce").fillna(0).sum())
                if "rows_in_window" in status
                else 0,
            }
        )
    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_DIR / "phase4_24h_t1_supplemental_summary.csv", index=False)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize Phase 4 24-hour supplemental feature outputs.")
    parser.add_argument("--modality", choices=["all", *MODALITIES.keys()], default="all")
    args = parser.parse_args()
    modalities = list(MODALITIES.keys()) if args.modality == "all" else [args.modality]
    summary = finalize(modalities)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
