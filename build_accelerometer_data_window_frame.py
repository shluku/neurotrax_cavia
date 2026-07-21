from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).parent
ACC_FRAMEWORK_DIR = ROOT / "output/analysis_candidates/phase2_accelerometer_framework"
WINDOW_VALIDATION_DIR = (
    ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation"
)
OUT_DIR = WINDOW_VALIDATION_DIR / "accelerometer_all_patient_data_window_frame"

PATIENT_QC_PATH = ACC_FRAMEWORK_DIR / "sensor_accelerometer_qc_by_patient.csv"
DEVICE_QC_PATH = ACC_FRAMEWORK_DIR / "sensor_accelerometer_qc_by_device_window.csv"
TOP10_VALIDATION_PATH = (
    WINDOW_VALIDATION_DIR
    / "accelerometer_top10_sensor_anchor_daily_jump_bounded_v3/accelerometer_top10_sensor_anchor_raw_probe_patient_windows.csv"
)
WEEKLY_MISS_PATH = (
    WINDOW_VALIDATION_DIR
    / "accelerometer_misses_weekly_backward_probe/accelerometer_misses_weekly_backward_probe.csv"
)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str)


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def normalize_subjects(df: pd.DataFrame) -> pd.DataFrame:
    if not df.empty and "Subject_ID_D" in df.columns:
        df = df.copy()
        df["Subject_ID_D"] = df["Subject_ID_D"].astype(str).str.zfill(3)
    return df


def first_row_by_subject(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.drop_duplicates("Subject_ID_D", keep="first").copy()


def build_patient_frame() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    patient_qc = normalize_subjects(read_csv(PATIENT_QC_PATH))
    device_qc = normalize_subjects(read_csv(DEVICE_QC_PATH))
    top10 = normalize_subjects(read_csv(TOP10_VALIDATION_PATH))
    weekly_miss = normalize_subjects(read_csv(WEEKLY_MISS_PATH))

    if patient_qc.empty:
        raise FileNotFoundError(f"missing required input: {PATIENT_QC_PATH}")

    if not top10.empty and "global_T1" in top10.columns:
        top10["global_T1_num"] = pd.to_numeric(top10["global_T1"], errors="coerce")
        top10 = top10.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True])
    top10 = first_row_by_subject(top10)

    likely_no_raw_subjects: set[str] = set()
    if not weekly_miss.empty and {"Subject_ID_D", "hit"}.issubset(weekly_miss.columns):
        hit_by_subject = weekly_miss.groupby("Subject_ID_D")["hit"].apply(lambda s: s.astype(str).str.lower().isin({"true", "1", "yes"}).any())
        likely_no_raw_subjects = set(hit_by_subject[~hit_by_subject].index.astype(str))

    top10_by_subject = top10.set_index("Subject_ID_D").to_dict("index") if not top10.empty else {}
    rows: list[dict[str, Any]] = []
    for _, patient in patient_qc.iterrows():
        subject_id = str(patient["Subject_ID_D"]).zfill(3)
        has_metadata = truthy(patient.get("has_sensor_accelerometer_metadata_after_T1", ""))
        validation = top10_by_subject.get(subject_id, {})
        validation_status = str(validation.get("window_status", "")).strip()
        raw_found = validation_status in {
            "raw_window_found_from_sensor_anchor_probe",
            "raw_window_found_from_sensor_daily_jump_probe",
        }

        if raw_found:
            data_window_status = "raw_24h_window_validated"
            next_action = "ready_for_raw_24h_feature_extraction"
        elif subject_id in likely_no_raw_subjects:
            data_window_status = "likely_no_usable_raw_accelerometer"
            next_action = "exclude_from_raw_accelerometer_phase_or_revisit_with_broader_manual_probe"
        elif has_metadata:
            data_window_status = "sensor_metadata_window_candidate_pending_raw_validation"
            next_action = "run_raw_probe_validation_before_feature_extraction"
        else:
            data_window_status = "no_sensor_accelerometer_metadata_after_T1"
            next_action = "not_ready_for_raw_accelerometer_phase"

        rows.append(
            {
                "Subject_ID_D": subject_id,
                "Subject_ID_N": patient.get("Subject_ID_N", ""),
                "global_T1": patient.get("global_T1", ""),
                "T1_date_iso": patient.get("T1_date_iso", ""),
                "selected_device_id": patient.get("selected_device_id", ""),
                "n_mapped_devices": patient.get("n_mapped_devices", ""),
                "has_sensor_accelerometer_metadata_after_T1": has_metadata,
                "metadata_days_first_available_after_T1": patient.get("days_first_available_after_T1", ""),
                "metadata_window_start_local": patient.get("window_start_local", ""),
                "metadata_window_end_local": patient.get("window_end_local", ""),
                "metadata_n_rows": patient.get("n_rows", ""),
                "metadata_qc_readiness_level": patient.get("qc_readiness_level", ""),
                "raw_validation_scope": "top10_pilot" if subject_id in top10_by_subject else "",
                "raw_validation_status": validation_status,
                "raw_validation_device_id": validation.get("candidate_device_id", ""),
                "raw_validation_uses_selected_device": validation.get("candidate_is_selected_device", ""),
                "raw_probe_sampled_rows_20min": validation.get("raw_probe_sampled_rows_20min", ""),
                "raw_probe_hit_sample_limit": validation.get("raw_probe_hit_sample_limit", ""),
                "candidate_raw_24h_window_start_local": validation.get("candidate_window_start_local", ""),
                "candidate_raw_24h_window_end_local": validation.get("candidate_window_end_local", ""),
                "weekly_backward_miss_probe_status": "no_raw_hits" if subject_id in likely_no_raw_subjects else "",
                "data_window_status": data_window_status,
                "next_action": next_action,
            }
        )

    patient_frame = pd.DataFrame(rows)
    patient_frame["global_T1_num"] = pd.to_numeric(patient_frame["global_T1"], errors="coerce")
    patient_frame = patient_frame.sort_values(["global_T1_num", "Subject_ID_D"], ascending=[False, True]).drop(columns=["global_T1_num"])

    summary = (
        patient_frame.groupby("data_window_status", dropna=False)
        .size()
        .reset_index(name="patient_count")
        .sort_values("patient_count", ascending=False)
    )

    readme = build_readme(patient_frame, device_qc)
    return patient_frame, summary, readme


def build_readme(patient_frame: pd.DataFrame, device_qc: pd.DataFrame) -> str:
    status_lines = "\n".join(
        f"- `{row.data_window_status}`: {int(row.patient_count)}"
        for row in patient_frame.groupby("data_window_status").size().reset_index(name="patient_count").itertuples()
    )
    return f"""# Accelerometer All-Patient Data Window Frame

Date: 2026-07-21

Purpose:

- Provide one working row per mapped T1 patient for accelerometer data-window planning.
- Use `sensor_accelerometer` metadata as the all-patient candidate-window layer.
- Overlay raw `accelerometer` validation where the top-10 pilot already tested raw data.
- Mark `007` and `013` as likely no usable raw accelerometer data based on the weekly-backward miss probe.

Inputs:

- `{PATIENT_QC_PATH}`
- `{DEVICE_QC_PATH}`
- `{TOP10_VALIDATION_PATH}`
- `{WEEKLY_MISS_PATH}`

Rows:

- Patient rows: {len(patient_frame)}
- Device-window metadata rows available for drill-down: {len(device_qc)}

Patient status counts:

{status_lines}

Interpretation:

- `raw_24h_window_validated`: raw accelerometer rows were found and a candidate 24h raw window is recorded.
- `likely_no_usable_raw_accelerometer`: metadata exists, but targeted raw probes found no raw samples.
- `sensor_metadata_window_candidate_pending_raw_validation`: metadata suggests a candidate window, but raw data has not yet been checked.
- `no_sensor_accelerometer_metadata_after_T1`: no post-T1 metadata candidate exists in the current framework.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    patient_frame, summary, readme = build_patient_frame()
    patient_csv = OUT_DIR / "accelerometer_all_patient_data_window_frame.csv"
    summary_csv = OUT_DIR / "accelerometer_all_patient_data_window_summary.csv"
    readme_path = OUT_DIR / "README_accelerometer_all_patient_data_window_frame.md"
    patient_frame.to_csv(patient_csv, index=False)
    summary.to_csv(summary_csv, index=False)
    readme_path.write_text(readme, encoding="utf-8")
    print("accelerometer_all_patient_data_window_frame_complete")
    print(f"patient_csv: {patient_csv}")
    print(f"summary_csv: {summary_csv}")
    print(f"readme: {readme_path}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
