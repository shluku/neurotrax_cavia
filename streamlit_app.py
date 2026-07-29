from __future__ import annotations

import json
import sys
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from result_explorer import render_result_explorer

PATHS = {
    "protocol_summary": ROOT / "README_PROTOCOL_PROJECT_SUMMARY.md",
    "phase2_feature_protocol": ROOT / "PHASE2_FEATURE_ANALYSIS_PROTOCOL.md",
    "phase2_table_feature_reviews": ROOT / "phase2_table_feature_reviews",
    "phase2_output_feature_reviews": ROOT / "output/analysis_candidates/phase2_feature_review",
    "phase2_tracking": ROOT / "phase2_table_tracking.csv",
    "phase2_feature_plan": ROOT / "phase2_candidate_feature_plan.csv",
    "phase2_selected_features": ROOT / "phase2_selected_features.csv",
    "phase2_highest_t1_calculated_feature_values": ROOT / "phase2_highest_t1_calculated_feature_values.csv",
    "phase2_reviewed_tables_global_coverage_summary": ROOT
    / "output/analysis_candidates/phase2_feature_review/phase2_reviewed_tables_global_coverage_summary.csv",
    "global_patient_coverage_preview": ROOT
    / "output/analysis_candidates/phase2_feature_review/streamlit_global_patient_coverage_preview.csv",
    "global_patient_coverage_status": ROOT
    / "output/analysis_candidates/phase2_feature_review/streamlit_global_patient_coverage_status.csv",
    "timeout_table_patient_counts": ROOT
    / "output/analysis_candidates/phase2_feature_review/streamlit_timeout_table_patient_counts.csv",
    "large_table_t1_t2_bounded_counts": ROOT
    / "output/analysis_candidates/phase2_feature_review/streamlit_large_table_t1_t2_bounded_patient_counts.csv",
    "large_sensor_metadata": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/phase2_large_sensor_table_metadata.csv",
    "large_sensor_columns": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/phase2_large_sensor_table_columns.csv",
    "large_sensor_indexes": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/phase2_large_sensor_table_indexes.csv",
    "large_sensor_availability": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/phase2_large_sensor_bounded_patient_availability.csv",
    "large_sensor_summary": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/phase2_large_sensor_bounded_patient_summary.csv",
    "large_sensor_readme": ROOT
    / "output/analysis_candidates/phase2_large_sensor_metadata/README_phase2_large_sensor_table_metadata_scan.md",
    "accelerometer_framework_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/README_accelerometer_framework.md",
    "sensor_linear_accelerometer_qc_by_patient": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/sensor_linear_accelerometer_qc_by_patient.csv",
    "sensor_linear_accelerometer_qc_by_device": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/sensor_linear_accelerometer_qc_by_device_window.csv",
    "sensor_accelerometer_qc_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/README_sensor_accelerometer_qc.md",
    "sensor_accelerometer_qc_by_patient": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_patient.csv",
    "sensor_accelerometer_qc_by_device": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/sensor_accelerometer_qc_by_device_window.csv",
    "accelerometer_raw_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/README_accelerometer_raw_signal_framework.md",
    "accelerometer_raw_sample_expanded": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_sample_rows_expanded.csv",
    "accelerometer_raw_keys": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_json_key_summary.csv",
    "accelerometer_raw_window_summary": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/accelerometer_raw_phase2a_candidate_window_summary.csv",
    "accelerometer_24h_pilot_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot/README_accelerometer_24h_pilot.md",
    "accelerometer_24h_pilot_manifest": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot/accelerometer_24h_pilot_manifest.csv",
    "accelerometer_24h_pilot_chunk_log": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot/accelerometer_24h_pilot_chunk_log.csv",
    "accelerometer_24h_pilot_candidate_scan": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/raw_24h_pilot/accelerometer_24h_pilot_candidate_scan.csv",
    "accelerometer_tomorrow_work_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/README_ACCELEROMETER_TOMORROW_WORK.md",
    "accelerometer_all_patient_window_frame": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_all_patient_data_window_frame/accelerometer_all_patient_data_window_frame.csv",
    "accelerometer_all_patient_window_summary": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_all_patient_data_window_frame/accelerometer_all_patient_data_window_summary.csv",
    "accelerometer_all_patient_window_readme": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_all_patient_data_window_frame/README_accelerometer_all_patient_data_window_frame.md",
    "accelerometer_top10_window_candidates": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_top10_sensor_anchor_daily_jump_bounded_v3/accelerometer_top10_sensor_anchor_raw_probe_candidates.csv",
    "accelerometer_miss_weekly_backward_probe": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_misses_weekly_backward_probe/accelerometer_misses_weekly_backward_probe.csv",
    "accelerometer_pending_raw_validation_windows": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_pending_raw_validation/accelerometer_pending_raw_validation_patient_windows.csv",
    "accelerometer_pending_raw_validation_probes": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_pending_raw_validation/accelerometer_pending_raw_validation_probes.csv",
    "accelerometer_no_raw_38_weekly_t1_t2_windows": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_no_raw_38_weekly_t1_t2_probe/accelerometer_no_raw_38_weekly_t1_t2_patient_windows.csv",
    "accelerometer_no_raw_38_weekly_t1_t2_probes": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/window_validation/accelerometer_no_raw_38_weekly_t1_t2_probe/accelerometer_no_raw_38_weekly_t1_t2_probes.csv",
    "accelerometer_local_24h_readme": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/README_accelerometer_24h_local_signal_analysis.md",
    "accelerometer_local_24h_features": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_overall_features.csv",
    "accelerometer_local_24h_chunks": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_chunk_summary.csv",
    "accelerometer_local_24h_hourly": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_hourly_summary.csv",
    "accelerometer_local_24h_states": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_state_summary.csv",
    "accelerometer_local_24h_thresholds": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_threshold_sensitivity.csv",
    "accelerometer_local_24h_bandpass_features": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_bandpass_feature_summary.csv",
    "accelerometer_local_24h_bandpass_hourly": ROOT
    / "output/analysis_candidates/phase2_accelerometer_framework/local_24h_analysis/accelerometer_24h_local_pilot_bandpass_hourly_summary.csv",
    "phase2_exploratory_feature_dir": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/exploratory_t1_week_24h",
    "phase3_all_t1_feature_dir": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features",
    "phase3_all_t1_long": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/phase2_all_t1_selected_features_long.csv",
    "phase3_all_t1_wide": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/phase2_all_t1_selected_features_wide.csv",
    "phase3_all_t1_status": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/phase2_all_t1_selected_features_patient_table_status.csv",
    "phase3_all_t1_coverage": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/phase2_all_t1_selected_features_coverage.csv",
    "phase3_all_t1_readme": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/README_phase2_all_t1_selected_features.md",
    "phase4_protocol": ROOT / "PHASE4_T1_BASELINE_DIGITAL_PHENOTYPE_PROTOCOL.md",
    "phase5_protocol": ROOT / "PHASE5_T2_FEATURE_EXTRACTION_PROTOCOL.md",
    "phase5_long": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_selected_features_long.csv",
    "phase5_wide": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_selected_features_wide.csv",
    "phase5_status": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_selected_features_patient_table_status.csv",
    "phase5_coverage": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_selected_features_coverage.csv",
    "phase5_feature_coverage_summary": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_feature_coverage_summary.csv",
    "phase5_table_coverage_summary": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_table_coverage_summary.csv",
    "phase5_patient_feature_matrix": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_patient_feature_coverage_matrix.csv",
    "phase5_working_features": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_working_features_10pct.csv",
    "phase5_sensitivity_features": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_sensitivity_features_below_10pct.csv",
    "phase5_checkpoint": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/phase5_t2_selected_features_checkpoint.jsonl",
    "phase5_readme": ROOT / "output/analysis_candidates/phase5_t2_feature_extraction/README_phase5_t2_selected_features.md",
    "phase6_protocol": ROOT / "PHASE6_T1_T2_DECLINE_DIGITAL_PHENOTYPING_PROTOCOL.md",
    "phase6_predictions": ROOT / "output/analysis_candidates/phase6_t1_t2_decline/phase6_t1_t2_decline_predictions.csv",
    "phase6_patient_predictions": ROOT / "output/analysis_candidates/phase6_t1_t2_decline/phase6_t1_t2_decline_patient_predictions.csv",
    "phase6_metrics": ROOT / "output/analysis_candidates/phase6_t1_t2_decline/phase6_t1_t2_decline_metrics.csv",
    "phase6_feature_sets": ROOT / "output/analysis_candidates/phase6_t1_t2_decline/phase6_t1_t2_decline_feature_sets.csv",
    "phase6_domain_taxonomy": ROOT / "output/analysis_candidates/phase6_t1_t2_decline/phase6_t1_t2_decline_domain_taxonomy.csv",
    "phase6_readme": ROOT / "output/analysis_candidates/phase6_t1_t2_decline/README_phase6_t1_t2_decline.md",
    "phase7_protocol": ROOT / "PHASE7_10_DAY_WINDOW_PROTOCOL.md",
    "phase7_t1_long": ROOT / "output/analysis_candidates/phase7_10day_window/t1/phase7_t1_10day_features_long.csv",
    "phase7_t1_wide": ROOT / "output/analysis_candidates/phase7_10day_window/t1/phase7_t1_10day_features_wide.csv",
    "phase7_t1_status": ROOT / "output/analysis_candidates/phase7_10day_window/t1/phase7_t1_10day_patient_table_status.csv",
    "phase7_t1_coverage": ROOT / "output/analysis_candidates/phase7_10day_window/t1/phase7_t1_10day_coverage.csv",
    "phase7_t1_checkpoint": ROOT / "output/analysis_candidates/phase7_10day_window/t1/phase7_t1_10day_checkpoint.jsonl",
    "phase7_t2_long": ROOT / "output/analysis_candidates/phase7_10day_window/t2/phase7_t2_10day_features_long.csv",
    "phase7_t2_wide": ROOT / "output/analysis_candidates/phase7_10day_window/t2/phase7_t2_10day_features_wide.csv",
    "phase7_t2_status": ROOT / "output/analysis_candidates/phase7_10day_window/t2/phase7_t2_10day_patient_table_status.csv",
    "phase7_t2_coverage": ROOT / "output/analysis_candidates/phase7_10day_window/t2/phase7_t2_10day_coverage.csv",
    "phase7_t2_checkpoint": ROOT / "output/analysis_candidates/phase7_10day_window/t2/phase7_t2_10day_checkpoint.jsonl",
    "phase7_comparison_readme": ROOT / "output/analysis_candidates/phase7_10day_window/comparison/README_phase7_comparison_24h_vs_10d.md",
    "phase7_feature_comparison": ROOT / "output/analysis_candidates/phase7_10day_window/comparison/phase7_feature_coverage_comparison_24h_vs_10d.csv",
    "phase7_patient_comparison": ROOT / "output/analysis_candidates/phase7_10day_window/comparison/phase7_patient_feature_count_comparison_24h_vs_10d.csv",
    "phase7_table_comparison": ROOT / "output/analysis_candidates/phase7_10day_window/comparison/phase7_table_coverage_comparison_24h_vs_10d.csv",
    "phase4_baseline_dataset": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/phase4_t1_baseline_patient_dataset.csv",
    "phase4_feature_metadata": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/phase4_t1_baseline_feature_metadata.csv",
    "phase4_missingness": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/phase4_t1_baseline_missingness_summary.csv",
    "phase4_table_coverage": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/phase4_t1_baseline_table_coverage.csv",
    "phase4_readme": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/README_phase4_t1_baseline_dataset.md",
    "phase4_model_predictions": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/phase4_t1_ridge_predictions.csv",
    "phase4_model_metrics": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/phase4_t1_ridge_metrics.csv",
    "phase4_model_feature_set": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/phase4_t1_ridge_feature_set.csv",
    "phase4_model_readme": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/README_phase4_t1_ridge.md",
    "phase4_model_coefficients": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/phase4_t1_ridge_coefficients.csv",
    "phase4_score_calibration": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/phase4_t1_score_calibration_by_patient.csv",
    "phase4_score_calibration_bins": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/phase4_t1_score_calibration_bins.csv",
    "phase4_score_calibration_metrics": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/phase4_t1_score_calibration_metrics.csv",
    "phase4_coefficient_summary": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/phase4_t1_ridge_coefficient_summary.csv",
    "phase4_score_calibration_readme": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_ridge/README_phase4_t1_score_calibration.md",
    "phase4_gradient_patient_predictions": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_gradient_weighted/phase4_t1_gradient_weighted_patient_predictions.csv",
    "phase4_gradient_metrics": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_gradient_weighted/phase4_t1_gradient_weighted_metrics.csv",
    "phase4_slope_selected_patient_predictions": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_slope_selected/phase4_t1_slope_selected_patient_predictions.csv",
    "phase4_slope_selected_metrics": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_slope_selected/phase4_t1_slope_selected_metrics.csv",
    "phase4_direction_constrained_patient_predictions": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_direction_constrained/phase4_t1_direction_constrained_patient_predictions.csv",
    "phase4_direction_constrained_metrics": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_direction_constrained/phase4_t1_direction_constrained_metrics.csv",
    "phase4_alternative_patient_predictions": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_alternatives/phase4_t1_alternative_patient_predictions.csv",
    "phase4_alternative_metrics": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_alternatives/phase4_t1_alternative_metrics.csv",
    "other_models_predictions": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/other_models/phase4_10day_other_models_predictions.csv",
    "other_models_patient_predictions": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/other_models/phase4_10day_other_models_patient_predictions.csv",
    "other_models_metrics": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/other_models/phase4_10day_other_models_metrics.csv",
    "other_models_importance": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/other_models/phase4_10day_other_models_permutation_importance.csv",
    "other_models_readme": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/other_models/README_phase4_10day_other_models.md",
    "other_models_protocol": ROOT / "OTHER_MODELS_PHASE_PROTOCOL.md",
    "other_models_metadata": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/phase4_10day_t1_baseline_feature_metadata.csv",
    "suggestions_metrics": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_coverage_metrics.csv",
    "suggestions_patient_predictions": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_coverage_patient_predictions.csv",
    "suggestions_predictions": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_coverage_predictions.csv",
    "suggestions_cohorts": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_coverage_cohorts.csv",
    "suggestions_readme": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/suggestions/README_suggestions_10day_coverage_models.md",
    "suggestions_protocol": ROOT / "SUGGESTIONS_PHASE_PROTOCOL.md",
    "suggestions_domain_metrics": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_cognitive_domain_metrics.csv",
    "suggestions_domain_patient_predictions": ROOT
    / "output/analysis_candidates/phase4_10day_t1_baseline/suggestions/suggestions_10day_cognitive_domain_patient_predictions.csv",
    "phase4_domain_patient_predictions": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_cognitive_domains/phase4_t1_cognitive_domain_patient_predictions.csv",
    "phase4_domain_metrics": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_cognitive_domains/phase4_t1_cognitive_domain_metrics.csv",
    "phase4_domain_group_patient_predictions": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_cognitive_domain_groups/phase4_t1_cognitive_domain_group_patient_predictions.csv",
    "phase4_domain_group_metrics": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/model_t1_cognitive_domain_groups/phase4_t1_cognitive_domain_group_metrics.csv",
    "phase4_cluster_assignments": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_t1_cluster_assignments.csv",
    "phase4_cluster_quality": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_t1_cluster_quality.csv",
    "phase4_cluster_feature_summary": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_t1_cluster_feature_summary.csv",
    "phase4_cluster_pca_loadings": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_t1_cluster_pca_loadings.csv",
    "phase4_cluster_patient_audit": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_cluster_patient_audit.csv",
    "phase4_cluster_audit_summary": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_cluster_audit_summary.csv",
    "phase4_cluster_feature_differences": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_cluster_feature_differences.csv",
    "phase4_cluster_pca_scatter": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_cluster_pca_scatter.csv",
    "phase4_cluster_high_assignments": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_cluster_high_coverage_assignments.csv",
    "phase4_cluster_high_quality": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_cluster_high_coverage_quality.csv",
    "phase4_cluster_profiles": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_cluster_profiles.csv",
    "phase4_cluster_profile_features": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_cluster_profile_features.csv",
    "phase4_cluster_stability": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/phase4_cluster_stability.csv",
    "phase4_cluster_profiles_readme": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/README_phase4_cluster_profiles.md",
    "phase4_cluster_readme": ROOT
    / "output/analysis_candidates/phase4_t1_baseline/cluster_t1_baseline/README_phase4_t1_clustering.md",
    "phase3_accelerometer_pilot_readme": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/README_phase3_accelerometer_24h_pilot.md",
    "phase3_accelerometer_pilot_wide": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/phase3_accelerometer_24h_pilot_features_wide.csv",
    "phase3_accelerometer_pilot_status": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/phase3_accelerometer_24h_pilot_patient_status.csv",
    "phase3_accelerometer_pilot_bandpass": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/phase3_accelerometer_24h_pilot_bandpass_summary.csv",
    "phase3_accelerometer_pilot_thresholds": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/phase3_accelerometer_24h_pilot_threshold_sensitivity.csv",
    "phase3_accelerometer_pilot_download": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/all_t1_patients_selected_features/table_runs/accelerometer/phase3_accelerometer_24h_pilot/phase3_accelerometer_24h_pilot_download_chunk_log.csv",
    "rd_calls_t1_week_long": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_week_any_data_pilot/phase3_rd_calls_t1_week_any_data_long.csv",
    "rd_calls_t1_week_wide": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_week_any_data_pilot/phase3_rd_calls_t1_week_any_data_wide.csv",
    "rd_calls_t1_week_status": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_week_any_data_pilot/phase3_rd_calls_t1_week_any_data_status.csv",
    "rd_calls_t1_week_readme": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_week_any_data_pilot/README_phase3_rd_calls_t1_week_any_data.md",
    "rd_calls_t1_2week_long": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_2week_any_data_pilot/phase3_rd_calls_t1_2week_any_data_long.csv",
    "rd_calls_t1_2week_wide": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_2week_any_data_pilot/phase3_rd_calls_t1_2week_any_data_wide.csv",
    "rd_calls_t1_2week_status": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_2week_any_data_pilot/phase3_rd_calls_t1_2week_any_data_status.csv",
    "rd_calls_t1_2week_readme": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_2week_any_data_pilot/README_phase3_rd_calls_t1_2week_any_data.md",
    "rd_calls_t1_30day_long": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_30day_any_data_pilot/phase3_rd_calls_t1_30day_any_data_long.csv",
    "rd_calls_t1_30day_wide": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_30day_any_data_pilot/phase3_rd_calls_t1_30day_any_data_wide.csv",
    "rd_calls_t1_30day_status": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_30day_any_data_pilot/phase3_rd_calls_t1_30day_any_data_status.csv",
    "rd_calls_t1_30day_readme": ROOT
    / "output/analysis_candidates/phase3_rd/calls_t1_30day_any_data_pilot/README_phase3_rd_calls_t1_30day_any_data.md",
    "rd_bluetooth_t1_week_long": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_week_any_data_pilot/phase3_rd_bluetooth_t1_week_any_data_long.csv",
    "rd_bluetooth_t1_week_wide": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_week_any_data_pilot/phase3_rd_bluetooth_t1_week_any_data_wide.csv",
    "rd_bluetooth_t1_week_status": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_week_any_data_pilot/phase3_rd_bluetooth_t1_week_any_data_status.csv",
    "rd_bluetooth_t1_week_readme": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_week_any_data_pilot/README_phase3_rd_bluetooth_t1_week_any_data.md",
    "rd_bluetooth_t1_30day_long": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_30day_any_data_pilot/phase3_rd_bluetooth_t1_30day_any_data_long.csv",
    "rd_bluetooth_t1_30day_wide": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_30day_any_data_pilot/phase3_rd_bluetooth_t1_30day_any_data_wide.csv",
    "rd_bluetooth_t1_30day_status": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_30day_any_data_pilot/phase3_rd_bluetooth_t1_30day_any_data_status.csv",
    "rd_bluetooth_t1_30day_readme": ROOT
    / "output/analysis_candidates/phase3_rd/bluetooth_t1_30day_any_data_pilot/README_phase3_rd_bluetooth_t1_30day_any_data.md",
    "cognitive_candidates": ROOT / "output/analysis_candidates/cognitive_candidates_all.csv",
    "cognitive_master": ROOT / "output/cognitive_master/master_cognitive_wide.csv",
    "label_device_map": ROOT / "output/label_device_map.csv",
    "top10": ROOT / "output/analysis_candidates/top10_global_decline.csv",
    "top10_device_summary": ROOT / "output/analysis_candidates/top10_subject_device_summary.csv",
    "device_episodes": ROOT / "output/analysis_candidates/top10_subject_device_episodes.csv",
    "phase1_profiles": ROOT
    / "output/analysis_candidates/phase1_features/phenotype_profiles/phase1_subject_phenotype_profiles_v2.csv",
    "phase1_cards": ROOT
    / "output/analysis_candidates/phase1_features/phenotype_profiles/phase1_subject_phenotype_cards_v2.md",
    "phase1_change": ROOT
    / "output/analysis_candidates/phase1_features/phenotype_profiles/phase1_change_profiles_024_077_v2.csv",
    "rich_wide": ROOT
    / "output/analysis_candidates/phase1_features/extracted/phase1_digital_phenotype_wide_rich.csv",
    "table_inventory": ROOT / "output/sql_catalog/table_inventory.csv",
    "column_inventory": ROOT / "output/sql_catalog/column_inventory.csv",
    "sample_summary": ROOT
    / "output/analysis_candidates/phase2_sql_fieldwork_samples/sensordb_10_rows_per_table_summary.csv",
    "sample_rows": ROOT
    / "output/analysis_candidates/phase2_sql_fieldwork_samples/sensordb_10_rows_per_table_sample.csv",
    "applications_foreground_review_sample": ROOT
    / "output/analysis_candidates/phase2_feature_review/applications_foreground/applications_foreground_sample_rows.csv",
    "applications_foreground_json_keys": ROOT
    / "output/analysis_candidates/phase2_feature_review/applications_foreground/applications_foreground_json_key_summary.csv",
    "applications_foreground_highest_t1_36h_features": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/applications_foreground_highest_t1_36h/applications_foreground_highest_t1_36h_features.csv",
    "applications_foreground_highest_t1_36h_rows": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/applications_foreground_highest_t1_36h/applications_foreground_highest_t1_36h_rows.csv",
    "applications_foreground_highest_t1_36h_coverage": ROOT
    / "output/analysis_candidates/phase2_feature_extraction/applications_foreground_highest_t1_36h/applications_foreground_highest_t1_36h_window_coverage.csv",
}

AXIS_COLS = [
    "phone_engagement_level",
    "nighttime_phone_activity_level",
    "app_use_breadth_level",
    "active_phone_interaction_level",
    "physical_activity_context_level",
    "data_quality_support_level",
]


st.set_page_config(
    page_title="NeuroTrax-SensorDB Fieldwork",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(1) p,
    [data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(6) p,
    [data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(7) p {
        font-size: 1.08rem;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"Subject_ID_D": str})


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def file_status(path: Path) -> str:
    return "available" if path.exists() else "missing"


def metric_row(items: list[tuple[str, str | int | float]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def show_dataframe(df: pd.DataFrame, *, height: int = 420) -> None:
    if df.empty:
        st.info("No file/data available yet.")
        return
    st.dataframe(df, use_container_width=True, height=height)


def show_feature_plan(df: pd.DataFrame, *, height: int = 520) -> None:
    if df.empty:
        st.info("No file/data available yet.")
        return
    if "selected_for_extraction" not in df.columns:
        show_dataframe(df, height=height)
        return

    display_df = df.copy()
    is_selected = display_df["selected_for_extraction"].astype(str).str.strip().str.lower().eq("yes")
    display_df.insert(0, "selection", is_selected.map({True: "SELECTED", False: ""}))
    display_df["_selected_sort"] = is_selected.astype(int)
    display_df = display_df.sort_values(["_selected_sort", "source_table", "feature_name"], ascending=[False, True, True])
    display_df = display_df.drop(columns=["_selected_sort"])

    def highlight_selected(row):
        selected = str(row.get("selected_for_extraction", "")).strip().lower() == "yes"
        if selected:
            return [
                "background-color: #0d6efd; color: white; font-weight: 900; "
                "border-top: 3px solid #003f88; border-bottom: 3px solid #003f88"
                for _ in row
            ]
        return ["" for _ in row]

    st.dataframe(display_df.style.apply(highlight_selected, axis=1), use_container_width=True, height=height)


def normalize_subject_id_d(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    return s.zfill(3) if s.isdigit() else s


def date_span(df: pd.DataFrame, start_col: str, end_col: str) -> tuple[str, str, str]:
    if df.empty or start_col not in df.columns or end_col not in df.columns:
        return "n/a", "n/a", "n/a"
    starts = pd.to_datetime(df[start_col], errors="coerce")
    ends = pd.to_datetime(df[end_col], errors="coerce")
    min_start = starts.min()
    max_end = ends.max()
    if pd.isna(min_start) or pd.isna(max_end):
        return "n/a", "n/a", "n/a"
    return min_start.date().isoformat(), max_end.date().isoformat(), f"{int((max_end - min_start).days)} days"


def median_followup_days(df: pd.DataFrame) -> str:
    if df.empty or "T1_date_iso" not in df.columns or "T2_date_iso" not in df.columns:
        return "n/a"
    t1 = pd.to_datetime(df["T1_date_iso"], errors="coerce")
    t2 = pd.to_datetime(df["T2_date_iso"], errors="coerce")
    days = (t2 - t1).dt.days.dropna()
    if days.empty:
        return "n/a"
    return f"{int(days.median())} days"


def device_counts_from_label_map(label_map: pd.DataFrame) -> pd.DataFrame:
    if label_map.empty or "label" not in label_map.columns or "device_ids" not in label_map.columns:
        return pd.DataFrame()
    rows = []
    for _, row in label_map.iterrows():
        raw_ids = str(row.get("device_ids", "") or "")
        device_ids = [x.strip() for x in raw_ids.split(";") if x.strip() and x.strip().lower() != "nan"]
        rows.append(
            {
                "Subject_ID_D": str(row["label"]).zfill(3) if str(row["label"]).isdigit() else str(row["label"]),
                "n_devices": len(device_ids),
                "device_ids": ";".join(device_ids),
            }
        )
    return pd.DataFrame(rows).sort_values("Subject_ID_D")


def simplify_applications_foreground_sample(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "data" not in df.columns:
        return df
    rows = []
    for _, row in df.iterrows():
        parsed = {}
        raw = row.get("data")
        if pd.notna(raw):
            try:
                parsed = json.loads(str(raw))
            except Exception:
                parsed = {}
        rows.append(
            {
                "sample_index": row.get("sample_index"),
                "_id": row.get("_id"),
                "timestamp": row.get("timestamp"),
                "local_datetime": row.get("local_datetime"),
                "package_name": parsed.get("package_name"),
                "application_name": parsed.get("application_name"),
                "is_system_app": parsed.get("is_system_app"),
            }
        )
    return pd.DataFrame(rows)


def available_table_reviews() -> dict[str, Path]:
    reviews: dict[str, Path] = {}
    review_dir = PATHS["phase2_table_feature_reviews"]
    if review_dir.exists():
        reviews.update({path.stem: path for path in sorted(review_dir.glob("*.md"))})

    output_review_dir = PATHS["phase2_output_feature_reviews"]
    if output_review_dir.exists():
        for path in sorted(output_review_dir.glob("*/README_*_feature_review.md")):
            table_name = path.parent.name
            reviews.setdefault(table_name, path)
    return reviews


def table_review_output_paths(table_name: str) -> dict[str, Path]:
    out_dir = ROOT / "output/analysis_candidates/phase2_feature_review" / table_name
    extraction_dir = ROOT / "output/analysis_candidates/phase2_feature_extraction" / f"{table_name}_highest_t1_36h"
    phase_b_features = extraction_dir / f"{table_name}_highest_t1_36h_features.csv"
    phase_b_coverage = extraction_dir / f"{table_name}_highest_t1_36h_window_coverage.csv"
    phase_b_rows = extraction_dir / f"{table_name}_highest_t1_36h_rows_expanded.csv"
    phase_b_readme = extraction_dir / f"README_{table_name}_highest_t1_36h.md"
    if table_name == "applications_foreground":
        extraction_dir = ROOT / "output/analysis_candidates/phase2_feature_extraction/applications_foreground_highest_t1_36h"
        phase_b_features = extraction_dir / "applications_foreground_highest_t1_36h_features.csv"
        phase_b_coverage = extraction_dir / "applications_foreground_highest_t1_36h_window_coverage.csv"
        phase_b_rows = extraction_dir / "applications_foreground_highest_t1_36h_rows.csv"
        phase_b_readme = extraction_dir / "README_applications_foreground_highest_t1_36h.md"
    if table_name == "bluetooth":
        phase_b_rows = extraction_dir / "bluetooth_highest_t1_36h_distinct_rows.csv"
        sample_feature_check = out_dir / "bluetooth_selected_feature_check.csv"
    elif table_name == "battery":
        sample_feature_check = out_dir / "battery_first_100_selected_feature_check.csv"
    else:
        sample_feature_check = out_dir / f"{table_name}_selected_feature_check.csv"
    if not sample_feature_check.exists():
        candidate_checks = sorted(out_dir.glob("*selected_feature_check.csv"))
        if candidate_checks:
            sample_feature_check = candidate_checks[0]
    return {
        "sample_rows": out_dir / f"{table_name}_sample_rows.csv",
        "sample_rows_expanded": out_dir / f"{table_name}_sample_rows_expanded.csv",
        "sample_rows_distinct": out_dir / f"{table_name}_sample_rows_distinct_observations.csv",
        "sample_feature_check": sample_feature_check,
        "json_keys": out_dir / f"{table_name}_json_key_summary.csv",
        "readme": out_dir / f"README_{table_name}_feature_review.md",
        "phase_b_features": phase_b_features,
        "phase_b_coverage": phase_b_coverage,
        "phase_b_rows": phase_b_rows,
        "phase_b_readme": phase_b_readme,
        "exploratory_features": PATHS["phase2_exploratory_feature_dir"]
        / f"phase2_exploratory_t1_week_24h_selected_features_{table_name}.csv",
        "exploratory_coverage": PATHS["phase2_exploratory_feature_dir"]
        / f"phase2_exploratory_t1_week_24h_coverage_scan_{table_name}.csv",
    }


def selected_feature_names_for_table(selected_features: pd.DataFrame, table_name: str) -> list[str]:
    if selected_features.empty:
        return []
    if "source_table" in selected_features.columns:
        view = selected_features[selected_features["source_table"].astype(str) == table_name]
    elif "table_name" in selected_features.columns:
        view = selected_features[selected_features["table_name"].astype(str) == table_name]
    else:
        return []
    if "feature_name" not in view.columns:
        return []
    return view["feature_name"].dropna().astype(str).tolist()


def format_feature_values(feature_names: list[str], values_df: pd.DataFrame) -> str:
    if not feature_names:
        return ""
    if values_df.empty:
        return "not calculated"

    if {"feature_name", "feature_value"}.issubset(values_df.columns):
        parts = []
        for feature_name in feature_names:
            matches = values_df[values_df["feature_name"].astype(str) == feature_name]
            if matches.empty:
                continue
            value = matches.iloc[0].get("feature_value")
            if pd.isna(value) or value == "":
                value_text = "missing"
            else:
                value_text = str(value)
            parts.append(f"{feature_name}={value_text}")
        return "; ".join(parts) if parts else "not calculated"

    row = values_df.iloc[0]
    parts = []
    for feature_name in feature_names:
        if feature_name not in values_df.columns:
            continue
        value = row.get(feature_name)
        if pd.isna(value) or value == "":
            value_text = "missing"
        else:
            value_text = str(value)
        parts.append(f"{feature_name}={value_text}")
    return "; ".join(parts) if parts else "not calculated"


def table_review_status(
    tracking: pd.DataFrame,
    selected_features: pd.DataFrame,
    feature_plan: pd.DataFrame,
    reviews: dict[str, Path],
) -> pd.DataFrame:
    table_names = set(reviews)
    for df, col in [
        (tracking, "table_name"),
        (selected_features, "table_name"),
        (feature_plan, "source_table"),
    ]:
        if not df.empty and col in df.columns:
            table_names.update(df[col].dropna().astype(str))

    rows = []
    selected_table_col = ""
    if not selected_features.empty:
        if "table_name" in selected_features.columns:
            selected_table_col = "table_name"
        elif "source_table" in selected_features.columns:
            selected_table_col = "source_table"

    for table_name in sorted(table_names):
        selected_n = 0
        candidate_n = 0
        review_file = reviews.get(table_name)
        output_paths = table_review_output_paths(table_name)
        selected_feature_names = selected_feature_names_for_table(selected_features, table_name)
        if selected_table_col:
            selected_n = int((selected_features[selected_table_col].astype(str) == table_name).sum())
        if not feature_plan.empty and "source_table" in feature_plan.columns:
            candidate_n = int((feature_plan["source_table"].astype(str) == table_name).sum())
        sample_feature_values = "not calculated"
        if output_paths["sample_feature_check"].exists():
            sample_feature_values = format_feature_values(
                selected_feature_names,
                load_csv(output_paths["sample_feature_check"]),
            )
        phase_b_feature_values = "not calculated"
        if output_paths["exploratory_features"].exists():
            phase_b_feature_values = format_feature_values(
                selected_feature_names,
                load_csv(output_paths["exploratory_features"]),
            )
            if sample_feature_values == "not calculated" and phase_b_feature_values != "not calculated":
                sample_feature_values = "calculated-no csv"
        rows.append(
            {
                "table_name": table_name,
                "has_review_file": "yes" if review_file else "no",
                "selected_features": selected_n,
                "selected_feature_names": "; ".join(selected_feature_names),
                "review_sample_feature_values": sample_feature_values,
                "phase_b_feature_values": phase_b_feature_values,
                "candidate_features": candidate_n,
                "review_file": str(review_file.relative_to(ROOT)) if review_file else "",
            }
        )
    return pd.DataFrame(rows)


def overview_page() -> None:
    st.title("NeuroTrax-SensorDB Project Dashboard")
    st.caption("A lightweight control panel for the current dementia digital phenotyping fieldwork.")

    candidates = load_csv(PATHS["cognitive_candidates"])
    label_map = load_csv(PATHS["label_device_map"])
    device_counts = device_counts_from_label_map(label_map)
    phase2_tracking = load_csv(PATHS["phase2_tracking"])
    phase2_inventory = load_csv(PATHS["table_inventory"])
    phase2_feature_plan = load_csv(PATHS["phase2_feature_plan"])
    phase2_selected_features = load_csv(PATHS["phase2_selected_features"])
    phase3_long = load_csv(PATHS["phase3_all_t1_long"])
    phase3_wide = load_csv(PATHS["phase3_all_t1_wide"])
    phase3_status = load_csv(PATHS["phase3_all_t1_status"])
    global_patient_coverage = load_csv(PATHS["global_patient_coverage_preview"])
    global_patient_coverage_status = load_csv(PATHS["global_patient_coverage_status"])
    timeout_table_patient_counts = load_csv(PATHS["timeout_table_patient_counts"])
    large_table_t1_t2_counts = load_csv(PATHS["large_table_t1_t2_bounded_counts"])
    large_sensor_metadata = load_csv(PATHS["large_sensor_metadata"])
    large_sensor_summary = load_csv(PATHS["large_sensor_summary"])
    phase2_reviews = available_table_reviews()

    n_total = len(candidates)
    n_t1 = int(pd.to_datetime(candidates.get("T1_date_iso", pd.Series(dtype=str)), errors="coerce").notna().sum())
    t1_dates = pd.to_datetime(candidates.get("T1_date_iso", pd.Series(dtype=str)), errors="coerce")
    t2_dates = pd.to_datetime(candidates.get("T2_date_iso", pd.Series(dtype=str)), errors="coerce")
    n_t1_t2 = int((t1_dates.notna() & t2_dates.notna()).sum())
    n_with_global_delta = int(pd.to_numeric(candidates.get("global_delta", pd.Series(dtype=str)), errors="coerce").notna().sum())
    n_cognitive_with_device_label = 0
    if not candidates.empty and not label_map.empty and "Subject_ID_D" in candidates.columns and "label" in label_map.columns:
        candidate_labels = set(candidates["Subject_ID_D"].dropna().astype(str).map(normalize_subject_id_d))
        mapped_labels = set(label_map["label"].dropna().astype(str).map(normalize_subject_id_d))
        n_cognitive_with_device_label = len(candidate_labels & mapped_labels)

    metric_row(
        [
            ("Patients total", n_total),
            ("Patients with T1", n_t1),
            ("Patients with T1 and T2", n_t1_t2),
            ("Patients with global delta", n_with_global_delta),
            ("Cognitive patients with device label", n_cognitive_with_device_label),
            ("Median T1-to-T2 gap", median_followup_days(candidates)),
        ]
    )

    st.subheader("Phase 2 Work Underway")
    metric_row(
        [
            ("Phase 2 tracked tables", len(phase2_tracking)),
            ("Reviewed table pages", len(phase2_reviews)),
            ("Selected features", len(phase2_selected_features)),
            ("Candidate feature rows", len(phase2_feature_plan)),
        ]
    )

    if not phase3_long.empty or not phase3_wide.empty:
        st.subheader("Phase 3 Algorithm Implementation")
        phase3_patients = (
            phase3_wide["Subject_ID_D"].nunique()
            if not phase3_wide.empty and "Subject_ID_D" in phase3_wide.columns
            else 0
        )
        phase3_tables = (
            phase3_status["table_name"].nunique()
            if not phase3_status.empty and "table_name" in phase3_status.columns
            else 0
        )
        phase3_features = (
            phase3_long["feature_name"].nunique()
            if not phase3_long.empty and "feature_name" in phase3_long.columns
            else 0
        )
        phase3_calculated = (
            int(phase3_long["feature_status"].astype(str).eq("calculated").sum())
            if not phase3_long.empty and "feature_status" in phase3_long.columns
            else 0
        )
        metric_row(
            [
                ("T1 patients implemented", phase3_patients),
                ("Tables implemented", phase3_tables),
                ("Selected algorithms", phase3_features),
                ("Calculated feature values", phase3_calculated),
            ]
        )

    st.subheader("Two Main Project Outcomes")
    left, right = st.columns(2)
    with left:
        st.markdown(
            """
            **Outcome 1: T1 baseline digital phenotype**

            Build T1 baseline digital phenotype features using the exploratory T1-ranked first-valid 24-hour T1-week protocol for feature finding, then later apply the finalized features to patient-level baseline analyses.
            """
        )
    with right:
        st.markdown(
            """
            **Outcome 2: T1-to-T2 digital phenotype delta**

            Describe the digital phenotype change between T1 and T2. Later, test whether T1 phenotype plus digital change can help predict the patient's NeuroTrax overall/global T2 score.
            """
        )

    st.subheader("Experiment Time Span")
    all_t1, all_t2, all_days = date_span(candidates, "T1_date_iso", "T2_date_iso")
    metric_row(
        [
            ("All candidates first T1", all_t1),
            ("All candidates last T2", all_t2),
            ("All candidates span", all_days),
        ]
    )

    st.subheader("Global Coverage Summary")
    if global_patient_coverage.empty:
        st.info("Global patient coverage preview is not available yet.")
    else:
        patient_denominator = n_cognitive_with_device_label or n_t1 or n_total
        table_summary = (
            global_patient_coverage.groupby("table_name", as_index=False)
            .agg(number_of_patients_with_data=("Subject_ID_D", "nunique"))
            .sort_values(["number_of_patients_with_data", "table_name"], ascending=[False, True])
        )
        table_summary["percentage"] = (
            100 * table_summary["number_of_patients_with_data"] / patient_denominator
        ).round(1)
        table_summary = table_summary.rename(columns={"table_name": "table name"})
        if not timeout_table_patient_counts.empty:
            timeout_summary = timeout_table_patient_counts.copy()
            timeout_summary["number_of_patients_with_data"] = pd.to_numeric(
                timeout_summary["number_of_patients_with_data"], errors="coerce"
            )
            timeout_summary["percentage"] = pd.NA
            has_count = timeout_summary["number_of_patients_with_data"].notna()
            timeout_summary.loc[has_count, "number_of_patients_with_data"] = timeout_summary.loc[
                has_count, "number_of_patients_with_data"
            ].astype(int)
            timeout_summary.loc[has_count, "percentage"] = (
                100 * timeout_summary.loc[has_count, "number_of_patients_with_data"] / patient_denominator
            ).round(1)
            timeout_summary["number_of_patients_with_data"] = timeout_summary[
                "number_of_patients_with_data"
            ].astype("object")
            timeout_summary.loc[~has_count, "number_of_patients_with_data"] = "unavailable"
            timeout_summary["percentage"] = timeout_summary["percentage"].astype("object")
            timeout_summary.loc[~has_count, "percentage"] = ""
            timeout_summary = timeout_summary.rename(columns={"table_name": "table name"})
            timeout_summary = timeout_summary[["table name", "number_of_patients_with_data", "percentage"]]
            table_summary = pd.concat([table_summary, timeout_summary], ignore_index=True)
            table_summary["_sort_count"] = pd.to_numeric(
                table_summary["number_of_patients_with_data"], errors="coerce"
            ).fillna(-1)
            table_summary = (
                table_summary.sort_values(["_sort_count", "table name"], ascending=[False, True])
                .drop_duplicates("table name", keep="first")
                .drop(columns=["_sort_count"])
                .reset_index(drop=True)
            )
        st.dataframe(table_summary, use_container_width=True, height=300)

        table_options = sorted(global_patient_coverage["table_name"].dropna().astype(str).unique().tolist())
        selected_table = st.selectbox("Table", table_options, index=table_options.index("network") if "network" in table_options else 0)
        coverage_view = global_patient_coverage[
            global_patient_coverage["table_name"].astype(str) == selected_table
        ].copy()
        coverage_view = coverage_view[["Subject_ID_D", "rows", "devices", "first row", "last row"]]
        if "rows" in coverage_view.columns:
            coverage_view["rows"] = pd.to_numeric(coverage_view["rows"], errors="coerce").astype("Int64")
        if "devices" in coverage_view.columns:
            coverage_view["devices"] = pd.to_numeric(coverage_view["devices"], errors="coerce").astype("Int64")
        show_dataframe(coverage_view, height=300)
        if not global_patient_coverage_status.empty:
            skipped = global_patient_coverage_status[
                global_patient_coverage_status["status"].astype(str).str.startswith("skipped")
                | global_patient_coverage_status["status"].astype(str).eq("error")
            ]
            if not skipped.empty:
                with st.expander("Skipped or unavailable tables"):
                    show_dataframe(skipped, height=260)

        if not large_table_t1_t2_counts.empty:
            st.subheader("T1/T2 Bounded Coverage for Large Tables")
            bounded_view = large_table_t1_t2_counts[
                [
                    "table_name",
                    "t1_day_after_patients_with_data",
                    "t1_day_after_percentage",
                    "t2_day_before_patients_with_data",
                    "t2_day_before_percentage",
                ]
            ].copy()
            show_dataframe(bounded_view, height=300)

        if not large_sensor_metadata.empty:
            st.subheader("Large Sensor Metadata")
            st.caption("Metadata-only scan for large/raw sensor tables. Approximate size comes from database table status; availability uses bounded patient/window EXISTS checks.")
            metadata_cols = [
                col
                for col in [
                    "table_name",
                    "metadata_estimated_rows",
                    "total_size_gb",
                    "has_device_id",
                    "has_timestamp",
                    "has_data",
                    "metadata_status",
                ]
                if col in large_sensor_metadata.columns
            ]
            show_dataframe(large_sensor_metadata[metadata_cols], height=260)
            if not large_sensor_summary.empty:
                st.caption("Bounded availability summary around T1/T2 windows.")
                show_dataframe(large_sensor_summary, height=260)

    st.subheader("NeuroTrax Feature Domains")
    neurotrax_domains = pd.DataFrame(
        [
            {"domain": "overall/global score", "columns": "global_T1, global_T2, global_delta"},
            {"domain": "memory", "columns": "memory_T1, memory_T2, memory_delta"},
            {"domain": "executive function", "columns": "ef_T1, ef_T2, ef_delta"},
            {"domain": "attention", "columns": "attention_T1, attention_T2, attention_delta"},
            {
                "domain": "processing speed",
                "columns": "processing_speed_T1, processing_speed_T2, processing_speed_delta",
            },
            {"domain": "verbal", "columns": "verbal_T1, verbal_T2, verbal_delta"},
            {"domain": "motor", "columns": "motor_T1, motor_T2, motor_delta"},
            {"domain": "IQ", "columns": "iq_T1, iq_T2, iq_delta"},
        ]
    )
    st.dataframe(neurotrax_domains, use_container_width=True, height=300)

    with st.expander("Device numbers per patient"):
        st.caption("Source file: output/label_device_map.csv")
        show_dataframe(device_counts, height=420)

    st.subheader("Current Protocol Summary")
    text = load_text(PATHS["protocol_summary"])
    if text:
        st.markdown(text)
    else:
        st.warning("Protocol summary README is missing.")


def phase1_profiles_page() -> None:
    st.title("Phase 1 Digital Phenotype Profiles")
    profiles = load_csv(PATHS["phase1_profiles"])
    if profiles.empty:
        st.info("Phase 1 phenotype profile CSV is not available.")
        return

    baseline_n = int(profiles.get("phase1_baseline_usable", pd.Series(dtype=str)).astype(str).str.lower().eq("true").sum())
    change_n = int(profiles.get("phase1_change_usable", pd.Series(dtype=str)).astype(str).str.lower().eq("true").sum())
    metric_row(
        [
            ("Subjects", len(profiles)),
            ("Baseline usable", baseline_n),
            ("Change usable", change_n),
        ]
    )

    st.subheader("Axis Distributions")
    dist_rows = []
    for col in AXIS_COLS:
        if col not in profiles.columns:
            continue
        counts = profiles[col].value_counts(dropna=False).reset_index()
        counts.columns = ["level", "n_subjects"]
        counts.insert(0, "axis", col.replace("_level", ""))
        dist_rows.append(counts)
    if dist_rows:
        dist = pd.concat(dist_rows, ignore_index=True)
        left, right = st.columns([1, 1])
        with left:
            st.dataframe(dist, use_container_width=True, height=360)
        with right:
            chart_df = dist.pivot(index="axis", columns="level", values="n_subjects").fillna(0)
            st.bar_chart(chart_df)

    st.subheader("Subject Profiles")
    subjects = ["All"] + sorted(profiles["Subject_ID_D"].dropna().astype(str).tolist())
    selected = st.selectbox("Subject", subjects)
    view = profiles if selected == "All" else profiles[profiles["Subject_ID_D"].astype(str) == selected]
    show_dataframe(view, height=440)

    cards = load_text(PATHS["phase1_cards"])
    with st.expander("Markdown phenotype cards"):
        st.markdown(cards if cards else "No phenotype cards file available.")


def phase1_change_page() -> None:
    st.title("Phase 1 Early-vs-Late Change Profiles")
    change = load_csv(PATHS["phase1_change"])
    if change.empty:
        st.info("Change profile CSV is not available.")
        return

    subjects = ["All"] + sorted(change["Subject_ID_D"].dropna().astype(str).unique().tolist())
    families = ["All"] + sorted(change["feature_family"].dropna().astype(str).unique().tolist())
    left, right = st.columns([1, 1])
    selected_subject = left.selectbox("Subject", subjects)
    selected_family = right.selectbox("Feature family", families)

    view = change.copy()
    if selected_subject != "All":
        view = view[view["Subject_ID_D"].astype(str) == selected_subject]
    if selected_family != "All":
        view = view[view["feature_family"].astype(str) == selected_family]
    show_dataframe(view, height=520)


def phase2_tables_page() -> None:
    st.title("Phase 2 Tables and Feature Fieldwork")
    tracking = load_csv(PATHS["phase2_tracking"])
    inventory = load_csv(PATHS["table_inventory"])
    sample_summary = load_csv(PATHS["sample_summary"])
    feature_plan = load_csv(PATHS["phase2_feature_plan"])
    selected_features = load_csv(PATHS["phase2_selected_features"])
    highest_t1_calculated_values = load_csv(PATHS["phase2_highest_t1_calculated_feature_values"])
    global_coverage_summary = load_csv(PATHS["phase2_reviewed_tables_global_coverage_summary"])
    large_sensor_metadata = load_csv(PATHS["large_sensor_metadata"])
    large_sensor_columns = load_csv(PATHS["large_sensor_columns"])
    large_sensor_indexes = load_csv(PATHS["large_sensor_indexes"])
    large_sensor_availability = load_csv(PATHS["large_sensor_availability"])
    large_sensor_summary = load_csv(PATHS["large_sensor_summary"])
    sensor_linear_qc_patient = load_csv(PATHS["sensor_linear_accelerometer_qc_by_patient"])
    sensor_linear_qc_device = load_csv(PATHS["sensor_linear_accelerometer_qc_by_device"])
    sensor_acc_qc_patient = load_csv(PATHS["sensor_accelerometer_qc_by_patient"])
    sensor_acc_qc_device = load_csv(PATHS["sensor_accelerometer_qc_by_device"])
    accelerometer_raw_sample = load_csv(PATHS["accelerometer_raw_sample_expanded"])
    accelerometer_raw_keys = load_csv(PATHS["accelerometer_raw_keys"])
    accelerometer_raw_window_summary = load_csv(PATHS["accelerometer_raw_window_summary"])
    accelerometer_24h_manifest = load_csv(PATHS["accelerometer_24h_pilot_manifest"])
    accelerometer_24h_chunk_log = load_csv(PATHS["accelerometer_24h_pilot_chunk_log"])
    accelerometer_24h_candidate_scan = load_csv(PATHS["accelerometer_24h_pilot_candidate_scan"])
    accelerometer_local_24h_features = load_csv(PATHS["accelerometer_local_24h_features"])
    accelerometer_local_24h_chunks = load_csv(PATHS["accelerometer_local_24h_chunks"])
    accelerometer_local_24h_hourly = load_csv(PATHS["accelerometer_local_24h_hourly"])
    accelerometer_local_24h_states = load_csv(PATHS["accelerometer_local_24h_states"])
    accelerometer_local_24h_thresholds = load_csv(PATHS["accelerometer_local_24h_thresholds"])
    accelerometer_local_24h_bandpass_features = load_csv(PATHS["accelerometer_local_24h_bandpass_features"])
    accelerometer_local_24h_bandpass_hourly = load_csv(PATHS["accelerometer_local_24h_bandpass_hourly"])
    accelerometer_all_patient_window_frame = load_csv(PATHS["accelerometer_all_patient_window_frame"])
    accelerometer_all_patient_window_summary = load_csv(PATHS["accelerometer_all_patient_window_summary"])
    accelerometer_top10_window_candidates = load_csv(PATHS["accelerometer_top10_window_candidates"])
    accelerometer_miss_weekly_backward_probe = load_csv(PATHS["accelerometer_miss_weekly_backward_probe"])
    accelerometer_pending_raw_validation_windows = load_csv(PATHS["accelerometer_pending_raw_validation_windows"])
    accelerometer_pending_raw_validation_probes = load_csv(PATHS["accelerometer_pending_raw_validation_probes"])
    accelerometer_no_raw_38_weekly_t1_t2_windows = load_csv(PATHS["accelerometer_no_raw_38_weekly_t1_t2_windows"])
    accelerometer_no_raw_38_weekly_t1_t2_probes = load_csv(PATHS["accelerometer_no_raw_38_weekly_t1_t2_probes"])
    review_sample = load_csv(PATHS["applications_foreground_review_sample"])
    json_keys = load_csv(PATHS["applications_foreground_json_keys"])
    highest_t1_features = load_csv(PATHS["applications_foreground_highest_t1_36h_features"])
    highest_t1_rows = load_csv(PATHS["applications_foreground_highest_t1_36h_rows"])
    highest_t1_coverage = load_csv(PATHS["applications_foreground_highest_t1_36h_coverage"])
    table_reviews = available_table_reviews()
    review_status = table_review_status(tracking, selected_features, feature_plan, table_reviews)

    metric_row(
        [
            ("Tracked tables", len(tracking)),
            ("Reviewed table pages", len(table_reviews)),
            ("Selected features", len(selected_features)),
            ("Candidate feature rows", len(feature_plan)),
        ]
    )

    tabs = st.tabs(
        [
            "Table Overview",
            "Reviewed Table Detail",
            "Selected Features",
            "Feature Analysis Protocol",
            "Candidate Features",
            "SQL Inventory",
            "Large Sensor Metadata",
            "Accelerometer Framework",
            "Sampling Summary",
        ]
    )
    with tabs[0]:
        if st.button("Refresh Phase 2 files"):
            st.rerun()

        st.subheader("Current Feature Values")
        st.caption("Current feature rows use only the exploratory T1-ranked first-valid 24h T1-week protocol. Missing values mean no protocol-valid patient/window was found for that table.")
        show_dataframe(highest_t1_calculated_values, height=260)

        st.subheader("Table Review Status")
        st.caption("One row per reviewed or feature-planned SensorDB table. Current feature values use the exploratory T1-week 24h protocol.")
        show_dataframe(review_status, height=360)

        st.subheader("Global Coverage Summary")
        st.caption("Compact table-level availability summary added to the Phase 2A protocol. This is global coverage, not T1-window feature extraction.")
        show_dataframe(global_coverage_summary, height=360)
    with tabs[1]:
        st.markdown(
            "<div style='font-size:2rem;font-weight:900;margin:0.2rem 0 1rem 0;'>Reviewed Table Detail</div>",
            unsafe_allow_html=True,
        )
        if not table_reviews:
            st.info("No reviewed table markdown files are available yet.")
        else:
            selected_review_table = st.selectbox("Reviewed table", sorted(table_reviews))
            st.markdown(load_text(table_reviews[selected_review_table]))
            output_paths = table_review_output_paths(selected_review_table)

            table_selected = pd.DataFrame()
            if not selected_features.empty:
                if "table_name" in selected_features.columns:
                    table_selected = selected_features[selected_features["table_name"].astype(str) == selected_review_table]
                elif "source_table" in selected_features.columns:
                    table_selected = selected_features[selected_features["source_table"].astype(str) == selected_review_table]
            st.subheader("Selected Features for This Table")
            show_dataframe(table_selected, height=220)

            table_candidates = pd.DataFrame()
            if not feature_plan.empty and "source_table" in feature_plan.columns:
                table_candidates = feature_plan[feature_plan["source_table"].astype(str) == selected_review_table]
            st.subheader("Candidate Feature Plan for This Table")
            show_feature_plan(table_candidates, height=320)

            if selected_review_table == "applications_foreground":
                st.subheader("Review Sample")
                st.caption("Cleaned view for feature decisions. Repeated device_id and JSON timestamp are hidden; raw file remains unchanged.")
                show_dataframe(simplify_applications_foreground_sample(review_sample), height=280)
                with st.expander("Raw sampled rows"):
                    show_dataframe(review_sample, height=320)
                st.subheader("JSON Key Summary")
                show_dataframe(json_keys, height=220)
                st.subheader("Exploratory T1-Ranked 24h Selected Features")
                show_dataframe(load_csv(output_paths["exploratory_features"]), height=180)
                with st.expander("Exploratory T1-week 24h coverage scan"):
                    show_dataframe(load_csv(output_paths["exploratory_coverage"]), height=260)
            else:
                st.subheader("Review Sample")
                sample_df = load_csv(output_paths["sample_rows_expanded"])
                if sample_df.empty:
                    sample_df = load_csv(output_paths["sample_rows"])
                if sample_df.empty and output_paths["sample_rows"].exists():
                    st.info("Sample file exists, but it contains no sampled rows under the current protocol.")
                distinct_df = load_csv(output_paths["sample_rows_distinct"])
                if not distinct_df.empty:
                    st.subheader("Distinct Observation Sample")
                    st.caption("Deduplicated inspection view for duplicate-heavy tables. This is for manual review only.")
                    show_dataframe(distinct_df, height=280)
                    if selected_review_table == "bluetooth":
                        st.caption("For Bluetooth, this distinct-observation sample is the primary Phase A inspection view.")
                if selected_review_table != "bluetooth" or distinct_df.empty:
                    show_dataframe(sample_df, height=280)
                with st.expander("Raw sample rows with original JSON"):
                    show_dataframe(load_csv(output_paths["sample_rows"]), height=320)
                st.subheader("JSON Key Summary")
                show_dataframe(load_csv(output_paths["json_keys"]), height=220)
                st.subheader("Selected Feature Check on Review Sample")
                show_dataframe(load_csv(output_paths["sample_feature_check"]), height=180)
                st.subheader("Exploratory T1-Ranked 24h Selected Features")
                show_dataframe(load_csv(output_paths["exploratory_features"]), height=180)
                with st.expander("Exploratory T1-week 24h coverage scan"):
                    show_dataframe(load_csv(output_paths["exploratory_coverage"]), height=260)
                readme_text = load_text(output_paths["readme"])
                if readme_text:
                    with st.expander("Review output README"):
                        st.markdown(readme_text)
    with tabs[2]:
        st.caption("Manual source of truth for features selected for future extraction.")
        show_dataframe(selected_features, height=420)
    with tabs[3]:
        st.subheader("Phase A / Phase B Flow")
        st.markdown(
            """
            **Phase A: Manual inspection of 20 raw rows**  
            For each new SensorDB table, inspect 20 chronological raw rows from the highest-T1 patient's day-after-T1 inspection window when available. This phase is only for understanding rows and JSON structure. No aggregation, no feature extraction, and no clinical interpretation.

            **Feature finding: exploratory T1-ranked 24h protocol**  
            After Phase A is understood, choose candidate features, then scan patients from highest T1 score downward until the first protocol-valid 24-hour window inside that patient's T1 week is found. If no valid patient/window exists, keep the selected features visible as missing rather than converting missing data to zero.

            **High-frequency sensor tables**  
            Motion tables such as `linear_accelerometer` need stricter handling. If no T1-week 24-hour protocol window exists, defer the table rather than widening SQL searches. Fourier-style features require confirmed x/y/z fields, timestamp regularity, duplicate handling, vector magnitude, and consistent resampling/segmentation.
            """
        )
        st.divider()
        st.markdown(load_text(PATHS["phase2_feature_protocol"]) or "No Phase 2 feature analysis protocol file available.")
    with tabs[4]:
        st.caption("Working list of features we may extract from each SensorDB table. This starts with applications_foreground and will grow table by table.")
        if not feature_plan.empty and "source_table" in feature_plan.columns:
            tables = ["All"] + sorted(feature_plan["source_table"].dropna().astype(str).unique().tolist())
            selected_table = st.selectbox("Source table", tables)
            view = feature_plan if selected_table == "All" else feature_plan[feature_plan["source_table"].astype(str) == selected_table]
            if "selected_for_extraction" in view.columns:
                selected_view = view[view["selected_for_extraction"].astype(str).str.strip().str.lower().eq("yes")]
                if not selected_view.empty:
                    st.markdown("#### Selected Features")
                    card_cols = st.columns(min(3, len(selected_view)))
                    for idx, (_, feature_row) in enumerate(selected_view.iterrows()):
                        with card_cols[idx % len(card_cols)]:
                            st.markdown(
                                f"""
                                <div style="background:#0d6efd;color:white;padding:14px 16px;border-radius:8px;
                                            border:3px solid #003f88;font-weight:800;margin-bottom:10px;">
                                    {feature_row['feature_name']}<br>
                                    <span style="font-weight:500;font-size:0.9rem;">{feature_row['short_description']}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
            show_feature_plan(view, height=520)
        else:
            show_dataframe(feature_plan, height=520)
    with tabs[5]:
        show_dataframe(inventory, height=520)
    with tabs[6]:
        st.subheader("Large Sensor Table Metadata")
        st.caption("Cheap metadata and bounded availability for large/raw sensor tables. No full-table grouped counts and no raw extraction.")
        show_dataframe(large_sensor_metadata, height=320)

        st.subheader("Bounded Patient Availability")
        show_dataframe(large_sensor_summary, height=260)

        if not large_sensor_availability.empty and "table_name" in large_sensor_availability.columns:
            table_options = ["All"] + sorted(large_sensor_availability["table_name"].dropna().astype(str).unique().tolist())
            selected_large_sensor_table = st.selectbox("Large sensor table", table_options)
            availability_view = large_sensor_availability.copy()
            if selected_large_sensor_table != "All":
                availability_view = availability_view[
                    availability_view["table_name"].astype(str) == selected_large_sensor_table
                ]
            show_dataframe(availability_view, height=360)
        else:
            show_dataframe(large_sensor_availability, height=360)

        with st.expander("Columns"):
            show_dataframe(large_sensor_columns, height=420)
        with st.expander("Indexes"):
            show_dataframe(large_sensor_indexes, height=420)
        readme = load_text(PATHS["large_sensor_readme"])
        if readme:
            with st.expander("Metadata scan README"):
                st.markdown(readme)
    with tabs[7]:
        st.subheader("Accelerometer Framework")
        st.caption(
            "Sensor metadata tables are QC/device-context layers. Raw `accelerometer` and "
            "`linear_accelerometer` motion streams come later."
        )

        def qc_summary_row(table_name: str, df: pd.DataFrame, device_df: pd.DataFrame, has_col: str) -> dict[str, object]:
            metadata_count = 0
            available_count = 0
            sparse_count = 0
            very_sparse_count = 0
            no_metadata_count = 0
            if not df.empty:
                if has_col in df.columns:
                    metadata_count = int(df[has_col].astype(str).str.lower().isin(["true", "1", "yes"]).sum())
                if "qc_readiness_level" in df.columns:
                    levels = df["qc_readiness_level"].astype(str)
                    available_count = int(levels.eq("metadata_available_for_device_context").sum())
                    sparse_count = int(levels.eq("sparse_metadata").sum())
                    very_sparse_count = int(levels.eq("very_sparse_metadata").sum())
                    no_metadata_count = int(levels.eq("no_metadata_after_T1").sum())
            return {
                "table_name": table_name,
                "patients_checked": len(df),
                "patients_with_metadata_after_T1": metadata_count,
                "metadata_available_for_device_context": available_count,
                "sparse_metadata": sparse_count,
                "very_sparse_metadata": very_sparse_count,
                "no_metadata_after_T1": no_metadata_count,
                "device_window_rows": len(device_df),
            }

        qc_comparison = pd.DataFrame(
            [
                qc_summary_row(
                    "sensor_accelerometer",
                    sensor_acc_qc_patient,
                    sensor_acc_qc_device,
                    "has_sensor_accelerometer_metadata_after_T1",
                ),
                qc_summary_row(
                    "sensor_linear_accelerometer",
                    sensor_linear_qc_patient,
                    sensor_linear_qc_device,
                    "has_sensor_linear_accelerometer_metadata_after_T1",
                ),
            ]
        )
        metric_row(
            [
                (
                    "General acc metadata patients",
                    int(
                        qc_comparison.loc[
                            qc_comparison["table_name"].eq("sensor_accelerometer"),
                            "patients_with_metadata_after_T1",
                        ].iloc[0]
                    )
                    if not qc_comparison.empty
                    else 0,
                ),
                (
                    "Linear acc metadata patients",
                    int(
                        qc_comparison.loc[
                            qc_comparison["table_name"].eq("sensor_linear_accelerometer"),
                            "patients_with_metadata_after_T1",
                        ].iloc[0]
                    )
                    if not qc_comparison.empty
                    else 0,
                ),
                ("General acc device windows", len(sensor_acc_qc_device)),
                ("Linear acc device windows", len(sensor_linear_qc_device)),
            ]
        )
        readme = load_text(PATHS["accelerometer_framework_readme"])
        if readme:
            st.markdown(readme)
        st.subheader("QC Comparison")
        show_dataframe(qc_comparison, height=180)

        acc_tabs = st.tabs(["General Accelerometer Metadata", "Linear Accelerometer Metadata"])
        with acc_tabs[0]:
            tomorrow_readme = load_text(PATHS["accelerometer_tomorrow_work_readme"])
            if tomorrow_readme:
                with st.expander("Accelerometer tomorrow work summary", expanded=True):
                    st.markdown(tomorrow_readme)
            readme = load_text(PATHS["sensor_accelerometer_qc_readme"])
            if readme:
                st.markdown(readme)
            st.subheader("Patient-Level QC")
            show_dataframe(sensor_acc_qc_patient, height=360)
            st.subheader("Device-Window QC")
            show_dataframe(sensor_acc_qc_device, height=360)
            st.subheader("All-Patient Raw ACC Window Frame")
            st.caption(
                "One planning row per mapped T1 patient. Metadata windows come from `sensor_accelerometer`; "
                "raw 24h windows are filled only where bounded raw `accelerometer` validation has already succeeded."
            )
            if accelerometer_all_patient_window_frame.empty:
                st.info("All-patient accelerometer data-window frame is not available yet.")
                st.code(".venv/bin/python3 build_accelerometer_data_window_frame.py")
            else:
                status_counts = (
                    accelerometer_all_patient_window_frame["data_window_status"].astype(str).value_counts().to_dict()
                    if "data_window_status" in accelerometer_all_patient_window_frame.columns
                    else {}
                )
                metric_row(
                    [
                        ("All patients", len(accelerometer_all_patient_window_frame)),
                        ("Raw validated", int(status_counts.get("raw_24h_window_validated", 0))),
                        ("Likely no raw ACC", int(status_counts.get("likely_no_usable_raw_accelerometer", 0))),
                        ("No raw in broad weekly T1-T2 probe", int(status_counts.get("no_raw_rows_in_broad_weekly_t1_t2_probe", 0))),
                        (
                            "Pending raw validation",
                            int(status_counts.get("sensor_metadata_window_candidate_pending_raw_validation", 0)),
                        ),
                    ]
                )
                show_dataframe(accelerometer_all_patient_window_summary, height=180)

                frame_view = accelerometer_all_patient_window_frame.copy()
                if "data_window_status" in frame_view.columns:
                    status_options = ["All"] + sorted(frame_view["data_window_status"].dropna().astype(str).unique().tolist())
                    selected_window_status = st.selectbox("ACC window status", status_options)
                    if selected_window_status != "All":
                        frame_view = frame_view[frame_view["data_window_status"].astype(str).eq(selected_window_status)]
                display_cols = [
                    "Subject_ID_D",
                    "global_T1",
                    "T1_date_iso",
                    "selected_device_id",
                    "metadata_window_start_local",
                    "metadata_window_end_local",
                    "metadata_n_rows",
                    "raw_validation_status",
                    "candidate_raw_24h_window_start_local",
                    "candidate_raw_24h_window_end_local",
                    "data_window_status",
                    "next_action",
                ]
                display_cols = [col for col in display_cols if col in frame_view.columns]
                show_dataframe(frame_view[display_cols] if display_cols else frame_view, height=420)

            frame_readme = load_text(PATHS["accelerometer_all_patient_window_readme"])
            if frame_readme:
                with st.expander("All-patient ACC window frame README"):
                    st.markdown(frame_readme)
            with st.expander("Top-10 raw validation candidate probes"):
                show_dataframe(accelerometer_top10_window_candidates, height=320)
            with st.expander("67 pending-window raw validation results"):
                show_dataframe(accelerometer_pending_raw_validation_windows, height=320)
            with st.expander("67 pending-window raw validation probe details"):
                show_dataframe(accelerometer_pending_raw_validation_probes, height=360)
            with st.expander("38 no-raw metadata-week patients: broad weekly T1-T2 validation"):
                show_dataframe(accelerometer_no_raw_38_weekly_t1_t2_windows, height=320)
            with st.expander("38 no-raw metadata-week patients: broad weekly T1-T2 probe details"):
                show_dataframe(accelerometer_no_raw_38_weekly_t1_t2_probes, height=360)
            with st.expander("Weekly-backward probes for likely raw misses"):
                show_dataframe(accelerometer_miss_weekly_backward_probe, height=220)
            st.subheader("Raw Accelerometer Phase 2A Targeted Sample")
            raw_readme = load_text(PATHS["accelerometer_raw_readme"])
            if raw_readme:
                st.markdown(raw_readme)
            st.caption(
                "First bounded raw-signal sample anchored to a known sensor_accelerometer metadata timestamp. "
                "This is manual fieldwork, not feature extraction."
            )
            show_dataframe(accelerometer_raw_sample, height=300)
            st.subheader("Raw Accelerometer JSON Keys")
            show_dataframe(accelerometer_raw_keys, height=180)
            with st.expander("Raw accelerometer targeted window summary"):
                show_dataframe(accelerometer_raw_window_summary, height=220)
            st.subheader("Raw Accelerometer 24h Local Pilot")
            pilot_readme = load_text(PATHS["accelerometer_24h_pilot_readme"])
            if pilot_readme:
                st.markdown(pilot_readme)
            if not accelerometer_24h_manifest.empty:
                row = accelerometer_24h_manifest.iloc[0]
                metric_row(
                    [
                        ("Pilot subject", row.get("Subject_ID_D", "")),
                        ("Downloaded rows", int(row.get("downloaded_rows", 0)) if pd.notna(row.get("downloaded_rows", pd.NA)) else 0),
                        ("Raw file MB", f"{float(row.get('raw_size_mb', 0)):.1f}" if pd.notna(row.get("raw_size_mb", pd.NA)) else ""),
                        (
                            "Signal file MB",
                            f"{float(row.get('signal_size_mb', 0)):.1f}" if pd.notna(row.get("signal_size_mb", pd.NA)) else "",
                        ),
                    ]
                )
                show_dataframe(accelerometer_24h_manifest, height=180)
            if not accelerometer_24h_chunk_log.empty:
                st.caption("Chunk-level download log. The million-row raw/signal files are kept on disk and are not loaded into Streamlit.")
                show_dataframe(accelerometer_24h_chunk_log.tail(30), height=260)
            with st.expander("24h pilot candidate scan"):
                show_dataframe(accelerometer_24h_candidate_scan, height=180)
            st.subheader("24h Local Signal Analysis")
            local_readme = load_text(PATHS["accelerometer_local_24h_readme"])
            if local_readme:
                st.markdown(local_readme)
            if not accelerometer_local_24h_features.empty:
                row = accelerometer_local_24h_features.iloc[0]
                metric_row(
                    [
                        ("Rows after QC", int(row.get("accelerometer_total_rows_loaded", 0))),
                        ("Duplicates removed", int(row.get("accelerometer_exact_duplicate_rows_removed", 0))),
                        ("Valid minutes", int(float(row.get("accelerometer_valid_signal_minutes", 0)))),
                        ("Still-phone minutes", int(float(row.get("accelerometer_still_phone_minutes", 0)))),
                        ("Handling minutes", int(float(row.get("accelerometer_phone_handling_minutes", 0)))),
                    ]
                )
                show_dataframe(accelerometer_local_24h_features, height=180)
            cols = st.columns(2)
            with cols[0]:
                st.subheader("Phone-State Candidate Summary")
                show_dataframe(accelerometer_local_24h_states, height=180)
            with cols[1]:
                st.subheader("Threshold Sensitivity")
                show_dataframe(accelerometer_local_24h_thresholds, height=240)
            st.subheader("Bandpass Candidate Feature Summary")
            st.caption(
                "Frequency-band outputs are phone-state candidates. Sampling feasibility is shown per band before interpreting candidate minutes."
            )
            show_dataframe(accelerometer_local_24h_bandpass_features, height=260)
            with st.expander("Bandpass candidate minutes by hour"):
                show_dataframe(accelerometer_local_24h_bandpass_hourly, height=320)
            st.subheader("Hourly Motion Summary")
            show_dataframe(accelerometer_local_24h_hourly, height=260)
            with st.expander("Top 20 chunks by dynamic magnitude"):
                if not accelerometer_local_24h_chunks.empty and "dynamic_magnitude_mean" in accelerometer_local_24h_chunks.columns:
                    top_chunks = accelerometer_local_24h_chunks.sort_values("dynamic_magnitude_mean", ascending=False).head(20)
                    show_dataframe(top_chunks, height=360)
                else:
                    show_dataframe(accelerometer_local_24h_chunks, height=360)
        with acc_tabs[1]:
            st.subheader("Patient-Level QC")
            show_dataframe(sensor_linear_qc_patient, height=360)
            st.subheader("Device-Window QC")
            show_dataframe(sensor_linear_qc_device, height=360)
    with tabs[8]:
        st.caption("This may be partial if a sampling run was stopped.")
        show_dataframe(sample_summary, height=520)


def phase3_algorithm_page() -> None:
    st.title("Phase 3 algorithm implementation")
    st.caption("Current selected-feature algorithms applied across T1 patients using the bounded T1-week 24-hour protocol.")

    long_df = load_csv(PATHS["phase3_all_t1_long"])
    wide_df = load_csv(PATHS["phase3_all_t1_wide"])
    status_df = load_csv(PATHS["phase3_all_t1_status"])
    coverage_df = load_csv(PATHS["phase3_all_t1_coverage"])
    acc_pilot_wide = load_csv(PATHS["phase3_accelerometer_pilot_wide"])
    acc_pilot_status = load_csv(PATHS["phase3_accelerometer_pilot_status"])
    acc_pilot_bandpass = load_csv(PATHS["phase3_accelerometer_pilot_bandpass"])
    acc_pilot_thresholds = load_csv(PATHS["phase3_accelerometer_pilot_thresholds"])
    acc_pilot_download = load_csv(PATHS["phase3_accelerometer_pilot_download"])

    if long_df.empty and wide_df.empty and status_df.empty:
        st.info("The all-patient selected-feature extraction output is not available yet.")
        st.code(".venv/bin/python3 phase2_extract_selected_features_all_t1_patients.py")
        return

    n_patients = wide_df["Subject_ID_D"].nunique() if not wide_df.empty and "Subject_ID_D" in wide_df.columns else 0
    n_features = long_df["feature_name"].nunique() if not long_df.empty and "feature_name" in long_df.columns else 0
    n_tables = status_df["table_name"].nunique() if not status_df.empty and "table_name" in status_df.columns else 0
    n_calculated = int(long_df["feature_status"].astype(str).eq("calculated").sum()) if "feature_status" in long_df.columns else 0
    n_total_feature_rows = len(long_df)
    pct_calculated = f"{100 * n_calculated / n_total_feature_rows:.1f}%" if n_total_feature_rows else "n/a"

    metric_row(
        [
            ("T1 patients processed", n_patients),
            ("Reviewed tables implemented", n_tables),
            ("Selected algorithms", n_features),
            ("Calculated feature values", n_calculated),
            ("Feature rows", n_total_feature_rows),
            ("Calculated share", pct_calculated),
        ]
    )

    st.subheader("Implementation Meaning")
    st.markdown(
        """
        This phase takes the features already selected during Phase 2 table review and applies them patient-by-patient.
        It is the first model-facing implementation layer: one long table for auditability and one wide table for future statistical modeling.

        Missing values mean the selected table did not have a protocol-valid 24-hour window for that patient/table, or the required feature signal was not available. Missing is not zero activity.
        """
    )

    tabs = st.tabs(
        [
            "Cohort Feature Overview",
            "Model-Ready Wide Table",
            "Patient-Table Status",
            "Coverage Audit",
            "Special Accelerometer Pilot",
            "README",
        ]
    )

    with tabs[0]:
        if long_df.empty:
            st.info("No long feature table available.")
        else:
            st.subheader("Calculated Values by Table")
            if {"table_name", "feature_status"}.issubset(long_df.columns):
                table_summary = (
                    long_df.assign(calculated=long_df["feature_status"].astype(str).eq("calculated"))
                    .groupby("table_name", dropna=False)
                    .agg(
                        calculated_feature_values=("calculated", "sum"),
                        total_feature_rows=("feature_name", "count"),
                        selected_features=("feature_name", "nunique"),
                        patients_seen=("Subject_ID_D", "nunique"),
                    )
                    .reset_index()
                )
                table_summary["calculated_percent"] = (
                    100 * table_summary["calculated_feature_values"] / table_summary["total_feature_rows"]
                ).round(1)
                show_dataframe(table_summary, height=320)
                st.bar_chart(table_summary.set_index("table_name")["calculated_feature_values"])

            st.subheader("Feature Availability")
            if {"feature_name", "feature_status", "table_name"}.issubset(long_df.columns):
                feature_summary = (
                    long_df.assign(calculated=long_df["feature_status"].astype(str).eq("calculated"))
                    .groupby(["table_name", "feature_name"], dropna=False)
                    .agg(
                        calculated_patients=("calculated", "sum"),
                        total_patients=("Subject_ID_D", "nunique"),
                    )
                    .reset_index()
                )
                feature_summary["calculated_percent"] = (
                    100 * feature_summary["calculated_patients"] / feature_summary["total_patients"]
                ).round(1)
                show_dataframe(feature_summary, height=420)

            st.subheader("Long Feature Table")
            show_dataframe(long_df, height=520)

    with tabs[1]:
        st.caption("One row per patient. Selected features become columns for later modeling.")
        show_dataframe(wide_df, height=620)

    with tabs[2]:
        st.caption("One row per patient-table showing whether the algorithm found a protocol-valid window and calculated values.")
        if not status_df.empty and "table_status" in status_df.columns:
            status_counts = status_df["table_status"].value_counts(dropna=False).reset_index()
            status_counts.columns = ["table_status", "n_patient_table_blocks"]
            show_dataframe(status_counts, height=180)
        show_dataframe(status_df, height=520)

    with tabs[3]:
        st.caption("Bounded coverage checks used to choose primary or fallback 24-hour T1-week windows.")
        show_dataframe(coverage_df, height=620)

    with tabs[4]:
        st.subheader("Special Accelerometer Phase 3 Pilot")
        st.caption("Isolated pilot only. These accelerometer rows are not merged into the shared Phase 3 matrix yet.")
        acc_readme = load_text(PATHS["phase3_accelerometer_pilot_readme"])
        if acc_readme:
            st.markdown(acc_readme)
        if not acc_pilot_status.empty:
            calculated = int(acc_pilot_status["table_status"].astype(str).eq("calculated").sum())
            attempted = len(acc_pilot_status)
            raw_rows = pd.to_numeric(acc_pilot_status.get("raw_rows_downloaded", pd.Series(dtype=str)), errors="coerce").fillna(0).sum()
            metric_row(
                [
                    ("Candidates attempted", attempted),
                    ("Calculated patients", calculated),
                    ("Raw rows downloaded", f"{int(raw_rows):,}"),
                    ("Feature rows", len(acc_pilot_wide)),
                ]
            )
        st.subheader("Pilot Patient Status")
        show_dataframe(acc_pilot_status, height=300)
        st.subheader("Pilot Feature Values")
        show_dataframe(acc_pilot_wide, height=220)
        st.subheader("Pilot Bandpass Summary")
        show_dataframe(acc_pilot_bandpass, height=320)
        with st.expander("Pilot threshold sensitivity"):
            show_dataframe(acc_pilot_thresholds, height=280)
        with st.expander("Pilot download chunk log"):
            show_dataframe(acc_pilot_download.tail(80), height=360)

    with tabs[5]:
        readme = load_text(PATHS["phase3_all_t1_readme"])
        st.markdown(readme if readme else "No README available yet.")


def phase4_baseline_page(
    title: str = "Phase 4 T1 Baseline Digital Phenotype",
    caption: str = "Patient-level baseline dataset for Outcome 1 using the first valid 24-hour T1-week protocol.",
    include_all_feature_trend_explorer: bool = False,
) -> None:
    st.markdown(
        '<h1 style="font-size: 2.6rem; font-weight: 800; margin-bottom: 0.25rem;">'
        + title
        + "</h1>",
        unsafe_allow_html=True,
    )
    st.caption(caption)

    dataset = load_csv(PATHS["phase4_baseline_dataset"])
    metadata = load_csv(PATHS["phase4_feature_metadata"])
    missingness = load_csv(PATHS["phase4_missingness"])
    coverage = load_csv(PATHS["phase4_table_coverage"])
    readme = load_text(PATHS["phase4_readme"])
    model_predictions = load_csv(PATHS["phase4_model_predictions"])
    model_metrics = load_csv(PATHS["phase4_model_metrics"])
    model_feature_set = load_csv(PATHS["phase4_model_feature_set"])
    model_readme = load_text(PATHS["phase4_model_readme"])
    model_coefficients = load_csv(PATHS["phase4_model_coefficients"])
    score_calibration = load_csv(PATHS["phase4_score_calibration"])
    score_calibration_bins = load_csv(PATHS["phase4_score_calibration_bins"])
    score_calibration_metrics = load_csv(PATHS["phase4_score_calibration_metrics"])
    coefficient_summary = load_csv(PATHS["phase4_coefficient_summary"])
    score_calibration_readme = load_text(PATHS["phase4_score_calibration_readme"])
    gradient_patient_predictions = load_csv(PATHS["phase4_gradient_patient_predictions"])
    gradient_metrics = load_csv(PATHS["phase4_gradient_metrics"])
    slope_selected_patient_predictions = load_csv(PATHS["phase4_slope_selected_patient_predictions"])
    slope_selected_metrics = load_csv(PATHS["phase4_slope_selected_metrics"])
    direction_constrained_patient_predictions = load_csv(PATHS["phase4_direction_constrained_patient_predictions"])
    direction_constrained_metrics = load_csv(PATHS["phase4_direction_constrained_metrics"])
    all_direction_patient_predictions = load_csv(
        PATHS.get("phase4_all_direction_patient_predictions", Path("__missing_phase4_all_direction_predictions__.csv"))
    )
    all_direction_metrics = load_csv(
        PATHS.get("phase4_all_direction_metrics", Path("__missing_phase4_all_direction_metrics__.csv"))
    )
    alternative_patient_predictions = load_csv(PATHS["phase4_alternative_patient_predictions"])
    alternative_metrics = load_csv(PATHS["phase4_alternative_metrics"])
    domain_patient_predictions = load_csv(PATHS["phase4_domain_patient_predictions"])
    domain_metrics = load_csv(PATHS["phase4_domain_metrics"])
    domain_group_patient_predictions = load_csv(PATHS["phase4_domain_group_patient_predictions"])
    domain_group_metrics = load_csv(PATHS["phase4_domain_group_metrics"])
    cluster_assignments = load_csv(PATHS["phase4_cluster_assignments"])
    cluster_quality = load_csv(PATHS["phase4_cluster_quality"])
    cluster_feature_summary = load_csv(PATHS["phase4_cluster_feature_summary"])
    cluster_pca_loadings = load_csv(PATHS["phase4_cluster_pca_loadings"])
    cluster_patient_audit = load_csv(PATHS["phase4_cluster_patient_audit"])
    cluster_audit_summary = load_csv(PATHS["phase4_cluster_audit_summary"])
    cluster_feature_differences = load_csv(PATHS["phase4_cluster_feature_differences"])
    cluster_pca_scatter = load_csv(PATHS["phase4_cluster_pca_scatter"])
    cluster_high_assignments = load_csv(PATHS["phase4_cluster_high_assignments"])
    cluster_high_quality = load_csv(PATHS["phase4_cluster_high_quality"])
    cluster_profiles = load_csv(PATHS["phase4_cluster_profiles"])
    cluster_profile_features = load_csv(PATHS["phase4_cluster_profile_features"])
    cluster_stability = load_csv(PATHS["phase4_cluster_stability"])
    cluster_profiles_readme = load_text(PATHS["phase4_cluster_profiles_readme"])
    cluster_readme = load_text(PATHS["phase4_cluster_readme"])

    if dataset.empty:
        st.info("The Phase 4 baseline dataset is not available yet.")
        st.code(".venv/bin/python3 build_phase4_t1_baseline_dataset.py")
        st.markdown(load_text(PATHS["phase4_protocol"]))
        return

    feature_columns = metadata["feature_name"].tolist() if "feature_name" in metadata.columns else []
    primary_count = int(metadata["primary_model_recommendation"].eq("include_primary").sum()) if "primary_model_recommendation" in metadata.columns else 0
    sensitivity_count = int((~metadata["primary_model_recommendation"].eq("include_primary")).sum()) if "primary_model_recommendation" in metadata.columns else 0
    mean_missing = float(dataset["baseline_feature_missing_fraction"].mean() * 100) if "baseline_feature_missing_fraction" in dataset.columns else float("nan")

    metric_row(
        [
            ("Patients", dataset["Subject_ID_D"].nunique() if "Subject_ID_D" in dataset.columns else len(dataset)),
            ("Selected features", len(feature_columns)),
            ("Primary-model features", primary_count),
            ("Sensitivity-only features", sensitivity_count),
            ("Mean feature missingness", f"{mean_missing:.1f}%"),
        ]
    )

    def show_fit_legend(metrics_frame: pd.DataFrame, model_name: str, label: str) -> None:
        if metrics_frame.empty or "analysis_scope" not in metrics_frame.columns:
            return
        pooled_rows = metrics_frame[metrics_frame["analysis_scope"].astype(str).eq("pooled")]
        model_rows = pooled_rows[pooled_rows["model"].astype(str).eq(model_name)]
        if model_rows.empty:
            return
        row = model_rows.iloc[0]
        baseline_rows = pooled_rows[pooled_rows["model"].astype(str).eq("mean_baseline")]
        baseline_rmse = float(baseline_rows.iloc[0]["rmse"]) if not baseline_rows.empty else float("nan")
        delta = float(row["rmse"]) - baseline_rmse if not np.isnan(baseline_rmse) else float("nan")
        delta_text = f"{delta:+.2f} vs mean baseline" if not np.isnan(delta) else "baseline unavailable"
        st.caption(
            f"Fit summary ({label}): RMSE {float(row['rmse']):.2f} | "
            f"MAE {float(row['mae']):.2f} | R2 {float(row['r2']):.2f} | {delta_text}"
        )

    st.subheader("Outcome 1: Digital phenotype estimate of T1 score")
    primary_patients = score_calibration[
        score_calibration["feature_scope"] == "primary_37"
    ].copy()
    if primary_patients.empty:
        st.info("The primary T1 score prediction graph is not available yet.")
    else:
        primary_patients = primary_patients.sort_values("actual_global_T1").reset_index(drop=True)
        primary_patients["patient_rank"] = range(1, len(primary_patients) + 1)
        plot_data = primary_patients.rename(
            columns={
                "Subject_ID_D": "Patient ID",
                "actual_global_T1": "Observed T1 score",
                "ridge_prediction": "Digital estimate",
            }
        )[["patient_rank", "Patient ID", "Observed T1 score", "Digital estimate"]].melt(
            id_vars=["patient_rank", "Patient ID"],
            var_name="score_type",
            value_name="t1_score",
        )
        st.caption(
            "Each position represents one patient, ordered from lowest to highest observed T1 score. "
            "The two lines show the observed score and the cross-validated digital estimate. "
            "Closer lines indicate a closer patient-level estimate."
        )
        plot_min = int(
            plot_data["t1_score"].min()
        ) - 1
        plot_max = int(
            plot_data["t1_score"].max()
        ) + 1
        plot_domain = [plot_min, plot_max]
        chart = (
            alt.Chart(plot_data)
            .mark_line(point=alt.OverlayMarkDef(size=45))
            .encode(
                x=alt.X(
                    "patient_rank:Q",
                    title="Patients ordered by observed T1 score",
                    axis=alt.Axis(format="d"),
                ),
                y=alt.Y(
                    "t1_score:Q",
                    title="T1 score",
                    scale=alt.Scale(domain=plot_domain),
                ),
                color=alt.Color(
                    "score_type:N",
                    title="Measure",
                    scale=alt.Scale(
                        domain=["Observed T1 score", "Digital estimate"],
                        range=["#111827", "#2563eb"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                    alt.Tooltip("Patient ID:N", title="Patient ID"),
                    alt.Tooltip("score_type:N", title="Measure"),
                    alt.Tooltip("t1_score:Q", title="T1 score", format=".2f"),
                ],
            )
        )
        st.altair_chart(chart.properties(height=430), use_container_width=True)
        primary_metrics = score_calibration_metrics[
            (score_calibration_metrics["feature_scope"] == "primary_37")
            & (score_calibration_metrics["model"] == "ridge")
        ]
        if not primary_metrics.empty:
            row = primary_metrics.iloc[0]
            metric_row(
                [
                    ("Digital prediction RMSE", f"{float(row['rmse']):.2f}"),
                    ("Digital prediction MAE", f"{float(row['mae']):.2f}"),
                    ("Actual-predicted correlation", f"{float(row['actual_predicted_correlation']):.2f}"),
                ]
            )
        primary_model_metrics = model_metrics[
            (model_metrics["feature_scope"] == "primary_37")
            & (model_metrics["model"].isin(["mean_baseline", "ridge"]))
        ]
        show_fit_legend(primary_model_metrics, "ridge", "primary 37-feature Ridge")

    st.markdown("**Slope-selected 8-feature digital estimate**")
    if slope_selected_patient_predictions.empty:
        st.info("The slope-selected comparison is not available yet.")
    else:
        selected_patients = slope_selected_patient_predictions.sort_values("actual_global_T1").reset_index(drop=True)
        selected_patients["patient_rank"] = range(1, len(selected_patients) + 1)
        selected_plot_data = selected_patients.rename(
            columns={
                "Subject_ID_D": "Patient ID",
                "actual_global_T1": "Observed T1 score",
                "slope_selected_prediction": "Slope-selected estimate",
            }
        )[["patient_rank", "Patient ID", "Observed T1 score", "Slope-selected estimate"]].melt(
            id_vars=["patient_rank", "Patient ID"],
            var_name="score_type",
            value_name="t1_score",
        )
        st.caption(
            "Same patient order and graph interpretation as the main result. This model uses only eight features: "
            "the five highest positive and three lowest negative fold-local linear slopes."
        )
        selected_plot_min = int(selected_plot_data["t1_score"].min()) - 1
        selected_plot_max = int(selected_plot_data["t1_score"].max()) + 1
        selected_chart = (
            alt.Chart(selected_plot_data)
            .mark_line(point=alt.OverlayMarkDef(size=45))
            .encode(
                x=alt.X(
                    "patient_rank:Q",
                    title="Patients ordered by observed T1 score",
                    axis=alt.Axis(format="d"),
                ),
                y=alt.Y(
                    "t1_score:Q",
                    title="T1 score",
                    scale=alt.Scale(domain=[selected_plot_min, selected_plot_max]),
                ),
                color=alt.Color(
                    "score_type:N",
                    title="Measure",
                    scale=alt.Scale(
                        domain=["Observed T1 score", "Slope-selected estimate"],
                        range=["#111827", "#7c3aed"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                    alt.Tooltip("Patient ID:N", title="Patient ID"),
                    alt.Tooltip("score_type:N", title="Measure"),
                    alt.Tooltip("t1_score:Q", title="T1 score", format=".2f"),
                ],
            )
        )
        st.altair_chart(selected_chart.properties(height=430), use_container_width=True)
        show_fit_legend(slope_selected_metrics, "slope_selected_ridge", "slope-selected 8-feature Ridge")

    st.markdown("**Direction-constrained slope model**")
    if direction_constrained_patient_predictions.empty:
        st.info("The direction-constrained comparison is not available yet.")
    else:
        constrained_patients = direction_constrained_patient_predictions.sort_values("actual_global_T1").reset_index(drop=True)
        constrained_patients["patient_rank"] = range(1, len(constrained_patients) + 1)
        constrained_plot_data = constrained_patients.rename(
            columns={
                "Subject_ID_D": "Patient ID",
                "actual_global_T1": "Observed T1 score",
                "direction_constrained_prediction": "Direction-constrained estimate",
            }
        )[["patient_rank", "Patient ID", "Observed T1 score", "Direction-constrained estimate"]].melt(
            id_vars=["patient_rank", "Patient ID"],
            var_name="score_type",
            value_name="t1_score",
        )
        st.caption(
            "This version uses the same eight slope-selected features, but constrains positive-slope features "
            "to raise predicted T1 and negative-slope features to lower predicted T1."
        )
        constrained_plot_min = int(constrained_plot_data["t1_score"].min()) - 1
        constrained_plot_max = int(constrained_plot_data["t1_score"].max()) + 1
        constrained_chart = (
            alt.Chart(constrained_plot_data)
            .mark_line(point=alt.OverlayMarkDef(size=45))
            .encode(
                x=alt.X(
                    "patient_rank:Q",
                    title="Patients ordered by observed T1 score",
                    axis=alt.Axis(format="d"),
                ),
                y=alt.Y(
                    "t1_score:Q",
                    title="T1 score",
                    scale=alt.Scale(domain=[constrained_plot_min, constrained_plot_max]),
                ),
                color=alt.Color(
                    "score_type:N",
                    title="Measure",
                    scale=alt.Scale(
                        domain=["Observed T1 score", "Direction-constrained estimate"],
                        range=["#111827", "#0891b2"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                    alt.Tooltip("Patient ID:N", title="Patient ID"),
                    alt.Tooltip("score_type:N", title="Measure"),
                    alt.Tooltip("t1_score:Q", title="T1 score", format=".2f"),
                ],
            )
        )
        st.altair_chart(constrained_chart.properties(height=430), use_container_width=True)
        show_fit_legend(
            direction_constrained_metrics,
            "direction_constrained_ridge",
            "direction-constrained Ridge",
        )

    if include_all_feature_trend_explorer:
        st.markdown("**All-feature direction-constrained slope model**")
        if all_direction_patient_predictions.empty:
            st.info("The all-feature direction-constrained comparison is not available yet.")
        else:
            all_direction_patients = all_direction_patient_predictions.sort_values("actual_global_T1").reset_index(drop=True)
            all_direction_patients["patient_rank"] = range(1, len(all_direction_patients) + 1)
            all_direction_plot_data = all_direction_patients.rename(
                columns={
                    "Subject_ID_D": "Patient ID",
                    "actual_global_T1": "Observed T1 score",
                    "all_direction_constrained_prediction": "All-feature direction-constrained estimate",
                }
            )[[
                "patient_rank",
                "Patient ID",
                "Observed T1 score",
                "All-feature direction-constrained estimate",
            ]].melt(
                id_vars=["patient_rank", "Patient ID"],
                var_name="score_type",
                value_name="t1_score",
            )
            st.caption(
                "Exploratory model using every selected feature with usable fold-local variation. "
                "Positive-slope features are constrained to raise the estimate and negative-slope features "
                "are constrained to lower it; all constraints are learned within each validation fold."
            )
            all_direction_plot_min = int(all_direction_plot_data["t1_score"].min()) - 1
            all_direction_plot_max = int(all_direction_plot_data["t1_score"].max()) + 1
            all_direction_chart = (
                alt.Chart(all_direction_plot_data)
                .mark_line(point=alt.OverlayMarkDef(size=45))
                .encode(
                    x=alt.X(
                        "patient_rank:Q",
                        title="Patients ordered by observed T1 score",
                        axis=alt.Axis(format="d"),
                    ),
                    y=alt.Y(
                        "t1_score:Q",
                        title="T1 score",
                        scale=alt.Scale(domain=[all_direction_plot_min, all_direction_plot_max]),
                    ),
                    color=alt.Color(
                        "score_type:N",
                        title="Measure",
                        scale=alt.Scale(
                            domain=["Observed T1 score", "All-feature direction-constrained estimate"],
                            range=["#111827", "#0f766e"],
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                        alt.Tooltip("Patient ID:N", title="Patient ID"),
                        alt.Tooltip("score_type:N", title="Measure"),
                        alt.Tooltip("t1_score:Q", title="T1 score", format=".2f"),
                    ],
                )
            )
            st.altair_chart(all_direction_chart.properties(height=430), use_container_width=True)
            show_fit_legend(
                all_direction_metrics,
                "all_direction_constrained_ridge",
                "all-feature direction-constrained Ridge",
            )

    st.markdown("**Gradient-weighted digital estimate**")
    if gradient_patient_predictions.empty:
        st.info("The gradient-weighted comparison is not available yet.")
    else:
        weighted_patients = gradient_patient_predictions.sort_values("actual_global_T1").reset_index(drop=True)
        weighted_patients["patient_rank"] = range(1, len(weighted_patients) + 1)
        weighted_plot_data = weighted_patients.rename(
            columns={
                "Subject_ID_D": "Patient ID",
                "actual_global_T1": "Observed T1 score",
                "gradient_weighted_prediction": "Gradient-weighted estimate",
            }
        )[["patient_rank", "Patient ID", "Observed T1 score", "Gradient-weighted estimate"]].melt(
            id_vars=["patient_rank", "Patient ID"],
            var_name="score_type",
            value_name="t1_score",
        )
        st.caption(
            "Same patient order and interpretation as the main graph. This version gives more influence "
            "to features with stronger fold-local monotonic association with T1; it is an exploratory comparison."
        )
        weighted_plot_min = int(weighted_plot_data["t1_score"].min()) - 1
        weighted_plot_max = int(weighted_plot_data["t1_score"].max()) + 1
        weighted_chart = (
            alt.Chart(weighted_plot_data)
            .mark_line(point=alt.OverlayMarkDef(size=45))
            .encode(
                x=alt.X(
                    "patient_rank:Q",
                    title="Patients ordered by observed T1 score",
                    axis=alt.Axis(format="d"),
                ),
                y=alt.Y(
                    "t1_score:Q",
                    title="T1 score",
                    scale=alt.Scale(domain=[weighted_plot_min, weighted_plot_max]),
                ),
                color=alt.Color(
                    "score_type:N",
                    title="Measure",
                    scale=alt.Scale(
                        domain=["Observed T1 score", "Gradient-weighted estimate"],
                        range=["#111827", "#d97706"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                    alt.Tooltip("Patient ID:N", title="Patient ID"),
                    alt.Tooltip("score_type:N", title="Measure"),
                    alt.Tooltip("t1_score:Q", title="T1 score", format=".2f"),
                ],
            )
        )
        st.altair_chart(weighted_chart.properties(height=430), use_container_width=True)
        show_fit_legend(gradient_metrics, "gradient_weighted_ridge", "gradient-weighted Ridge")

    st.subheader("Alternative model estimates")
    st.caption(
        "These are additional exploratory models using the same 37 primary features and validation design. "
        "They do not replace the original Outcome 1 model."
    )
    alternative_models = [
        ("elastic_net_prediction", "Elastic Net estimate", "#16a34a", "elastic_net"),
        ("pls_prediction", "PLS estimate", "#ea580c", "pls"),
        ("spline_ridge_prediction", "Spline Ridge estimate", "#9333ea", "spline_ridge"),
    ]
    for prediction_column, prediction_label, prediction_color, metric_model_name in alternative_models:
        if alternative_patient_predictions.empty:
            st.info("Alternative model comparisons are not available yet.")
            break
        alternative_patients = alternative_patient_predictions.sort_values("actual_global_T1").reset_index(drop=True)
        alternative_patients["patient_rank"] = range(1, len(alternative_patients) + 1)
        alternative_plot_data = alternative_patients.rename(
            columns={
                "Subject_ID_D": "Patient ID",
                "actual_global_T1": "Observed T1 score",
                prediction_column: prediction_label,
            }
        )[["patient_rank", "Patient ID", "Observed T1 score", prediction_label]].melt(
            id_vars=["patient_rank", "Patient ID"],
            var_name="score_type",
            value_name="t1_score",
        )
        st.markdown(f"**{prediction_label}**")
        st.caption(
            "Same patient ordering as the main graph. The colored line is the model estimate; "
            "the black line is the observed T1 score."
        )
        alternative_plot_min = int(alternative_plot_data["t1_score"].min()) - 1
        alternative_plot_max = int(alternative_plot_data["t1_score"].max()) + 1
        alternative_chart = (
            alt.Chart(alternative_plot_data)
            .mark_line(point=alt.OverlayMarkDef(size=45))
            .encode(
                x=alt.X(
                    "patient_rank:Q",
                    title="Patients ordered by observed T1 score",
                    axis=alt.Axis(format="d"),
                ),
                y=alt.Y(
                    "t1_score:Q",
                    title="T1 score",
                    scale=alt.Scale(domain=[alternative_plot_min, alternative_plot_max]),
                ),
                color=alt.Color(
                    "score_type:N",
                    title="Measure",
                    scale=alt.Scale(
                        domain=["Observed T1 score", prediction_label],
                        range=["#111827", prediction_color],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                    alt.Tooltip("Patient ID:N", title="Patient ID"),
                    alt.Tooltip("score_type:N", title="Measure"),
                    alt.Tooltip("t1_score:Q", title="T1 score", format=".2f"),
                ],
            )
        )
        st.altair_chart(alternative_chart.properties(height=360), use_container_width=True)
        show_fit_legend(alternative_metrics, metric_model_name, prediction_label)

    comparison_rows = []
    comparison_sources = [
        (model_metrics, "ridge", "Primary Ridge"),
        (gradient_metrics, "gradient_weighted_ridge", "Gradient-weighted"),
        (slope_selected_metrics, "slope_selected_ridge", "Slope-selected"),
        (direction_constrained_metrics, "direction_constrained_ridge", "Direction-constrained"),
        (alternative_metrics, "elastic_net", "Elastic Net"),
        (alternative_metrics, "pls", "PLS"),
        (alternative_metrics, "spline_ridge", "Spline Ridge"),
    ]
    for metrics_frame, model_name, display_name in comparison_sources:
        rows = metrics_frame[
            metrics_frame["analysis_scope"].astype(str).eq("pooled")
            & metrics_frame["model"].astype(str).eq(model_name)
        ]
        if metrics_frame is model_metrics:
            rows = rows[rows["feature_scope"].astype(str).eq("primary_37")]
        if not rows.empty:
            row = rows.iloc[0]
            comparison_rows.append(
                {
                    "model": display_name,
                    "RMSE": float(row["rmse"]),
                    "MAE": float(row["mae"]),
                }
            )
    baseline_comparison = model_metrics[
        (model_metrics["analysis_scope"].astype(str) == "pooled")
        & (model_metrics["feature_scope"].astype(str) == "primary_37")
        & (model_metrics["model"].astype(str) == "mean_baseline")
    ]
    if not baseline_comparison.empty:
        row = baseline_comparison.iloc[0]
        comparison_rows.append({"model": "Mean baseline", "RMSE": float(row["rmse"]), "MAE": float(row["mae"])})
    comparison_frame = pd.DataFrame(comparison_rows)
    if not comparison_frame.empty:
        st.markdown("**Fit comparison across models**")
        st.caption("Lower RMSE and MAE indicate smaller prediction errors. All values use the same pooled repeated cross-validation design.")
        comparison_plot = comparison_frame.melt("model", var_name="metric", value_name="error")
        comparison_chart = (
            alt.Chart(comparison_plot)
            .mark_bar()
            .encode(
                x=alt.X("error:Q", title="Error (lower is better)"),
                y=alt.Y("model:N", title=None, sort="-x"),
                color=alt.Color("metric:N", title="Metric"),
                tooltip=[
                    alt.Tooltip("model:N", title="Model"),
                    alt.Tooltip("metric:N", title="Metric"),
                    alt.Tooltip("error:Q", title="Value", format=".2f"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(comparison_chart, use_container_width=True)

    st.subheader("Exploratory feature patterns")
    st.caption(
        "These graphs describe associations in the current T1 cohort. They do not change the model, "
        "and they should not be interpreted as causal or clinical effects."
    )
    primary_features = metadata.loc[
        metadata["primary_model_recommendation"] == "include_primary", "feature_name"
    ].tolist()
    association_rows: list[dict[str, object]] = []
    for feature in primary_features:
        values = pd.to_numeric(dataset[feature], errors="coerce")
        paired = pd.DataFrame({"feature": values, "t1": dataset["global_T1"]}).dropna()
        if len(paired) < 5 or paired["feature"].nunique() < 2:
            continue
        association_rows.append(
            {
                "feature": feature,
                "spearman_rho": float(paired["feature"].corr(paired["t1"], method="spearman")),
                "n_observed": len(paired),
                "missing_percent": float(values.isna().mean() * 100),
            }
        )
    associations = pd.DataFrame(association_rows)
    if associations.empty:
        st.info("Feature association graphs are not available yet.")
    else:
        associations["absolute_rho"] = associations["spearman_rho"].abs()
        strongest = associations.nlargest(12, "absolute_rho").sort_values("spearman_rho")
        strongest["direction"] = strongest["spearman_rho"].map(
            lambda value: "Increases with T1" if value >= 0 else "Decreases with T1"
        )
        st.markdown("**Features that move with observed T1**")
        st.caption(
            "Positive values indicate that a feature tends to increase as T1 increases; "
            "negative values indicate the opposite. Spearman correlation is used because it captures monotonic patterns."
        )
        association_chart = (
            alt.Chart(strongest)
            .mark_bar()
            .encode(
                x=alt.X(
                    "spearman_rho:Q",
                    title="Association with observed T1 (Spearman rho)",
                    scale=alt.Scale(domain=[-1, 1]),
                ),
                y=alt.Y("feature:N", title=None, sort=None),
                color=alt.Color(
                    "direction:N",
                    title="Direction",
                    scale=alt.Scale(
                        domain=["Increases with T1", "Decreases with T1"],
                        range=["#2563eb", "#dc2626"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("feature:N", title="Feature"),
                    alt.Tooltip("direction:N", title="Direction"),
                    alt.Tooltip("spearman_rho:Q", title="Spearman rho", format=".2f"),
                    alt.Tooltip("n_observed:Q", title="Patients with data"),
                    alt.Tooltip("missing_percent:Q", title="Missing", format=".1f"),
                ],
            )
            .properties(height=360)
        )
        st.altair_chart(association_chart, use_container_width=True)

        trend_features = strongest.nlargest(8, "absolute_rho")["feature"].tolist()
        t1_values = pd.to_numeric(dataset["global_T1"], errors="coerce")
        trend_source = dataset.assign(
            t1_quartile=pd.qcut(t1_values, q=4, labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"], duplicates="drop")
        )
        trend_rows: list[dict[str, object]] = []
        for feature in trend_features:
            values = pd.to_numeric(trend_source[feature], errors="coerce")
            standard_deviation = values.std()
            if pd.isna(standard_deviation) or standard_deviation == 0:
                continue
            z_values = (values - values.mean()) / standard_deviation
            for quartile, group in z_values.groupby(trend_source["t1_quartile"], observed=False):
                if pd.isna(quartile):
                    continue
                trend_rows.append(
                    {
                        "feature": feature,
                        "t1_quartile": str(quartile),
                        "median_z_score": float(group.median()),
                    }
                )
        trends = pd.DataFrame(trend_rows)
        if not trends.empty:
            st.markdown("**Do the strongest features follow the T1 gradient?**")
            st.caption(
                "Each line shows the feature median after standardization, across four T1 groups. "
                "An upward line means the feature generally grows with T1; a downward line means it shrinks."
            )
            trend_chart = (
                alt.Chart(trends)
                .mark_line(point=True)
                .encode(
                    x=alt.X(
                        "t1_quartile:N",
                        title="Observed T1 group",
                        sort=["Q1 lowest", "Q2", "Q3", "Q4 highest"],
                    ),
                    y=alt.Y("median_z_score:Q", title="Feature median (standardized)"),
                    color=alt.Color("feature:N", title="Feature"),
                    tooltip=[
                        alt.Tooltip("feature:N", title="Feature"),
                        alt.Tooltip("t1_quartile:N", title="T1 group"),
                        alt.Tooltip("median_z_score:Q", title="Median standardized value", format=".2f"),
                    ],
                )
                .properties(height=380)
            )
            st.altair_chart(trend_chart, use_container_width=True)

    primary_coverage = dataset.copy()
    primary_coverage["observed_primary_features"] = primary_coverage[primary_features].notna().sum(axis=1)
    primary_coverage["primary_feature_coverage_percent"] = (
        primary_coverage["observed_primary_features"] / len(primary_features) * 100
    )
    primary_coverage = primary_coverage.sort_values("global_T1").reset_index(drop=True)
    primary_coverage["patient_rank"] = range(1, len(primary_coverage) + 1)
    st.markdown("**How much primary digital data did each patient have?**")
    st.caption(
        "Patients use the same low-to-high observed T1 order as the main graph. "
        "Coverage is the percentage of the 37 primary features that were observed for that patient."
    )
    coverage_chart = (
        alt.Chart(primary_coverage)
        .mark_line(point=alt.OverlayMarkDef(size=45), color="#059669")
        .encode(
            x=alt.X("patient_rank:Q", title="Patients ordered by observed T1 score", axis=alt.Axis(format="d")),
            y=alt.Y(
                "primary_feature_coverage_percent:Q",
                title="Primary-feature coverage (%)",
                scale=alt.Scale(domain=[0, 100]),
            ),
            tooltip=[
                alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                alt.Tooltip("Subject_ID_D:N", title="Patient ID"),
                alt.Tooltip("global_T1:Q", title="Observed T1 score", format=".2f"),
                alt.Tooltip("observed_primary_features:Q", title="Observed primary features"),
                alt.Tooltip("primary_feature_coverage_percent:Q", title="Coverage", format=".1f"),
            ],
        )
        .properties(height=300)
    )
    st.altair_chart(coverage_chart, use_container_width=True)

    gradient_slope_rows: list[dict[str, object]] = []
    for feature in primary_features:
        feature_values = pd.to_numeric(dataset[feature], errors="coerce")
        feature_trend = pd.DataFrame(
            {"feature_value": feature_values, "observed_T1": pd.to_numeric(dataset["global_T1"], errors="coerce")}
        ).dropna()
        if len(feature_trend) < 8 or feature_trend["feature_value"].nunique() < 4:
            continue
        feature_trend["feature_group_number"] = pd.qcut(
            feature_trend["feature_value"], q=4, labels=False, duplicates="drop"
        )
        medians = feature_trend.groupby("feature_group_number", observed=False)["observed_T1"].median().dropna()
        if len(medians) < 3:
            continue
        slope = float(np.polyfit(medians.index.to_numpy(dtype=float) + 1, medians.to_numpy(dtype=float), 1)[0])
        association = associations.loc[associations["feature"].eq(feature)]
        gradient_slope_rows.append(
            {
                "feature": feature,
                "linear_slope": slope,
                "direction": "Positive slope" if slope >= 0 else "Negative slope",
                "spearman_rho": float(association["spearman_rho"].iloc[0]) if not association.empty else np.nan,
                "n_observed": len(feature_trend),
            }
        )
    gradient_slopes = pd.DataFrame(gradient_slope_rows)

    st.markdown("**Individual feature trend explorer**")
    if associations.empty:
        st.info("The individual feature trend graph is not available yet.")
    else:
        feature_options = associations.sort_values("absolute_rho", ascending=False)["feature"].tolist()
        selected_feature = st.selectbox(
            "Choose a primary feature",
            feature_options,
            key="phase4_feature_trend_selector",
        )
        selected_values = pd.to_numeric(dataset[selected_feature], errors="coerce")
        feature_trend = pd.DataFrame(
            {
                "Patient ID": dataset["Subject_ID_D"],
                "feature_value": selected_values,
                "observed_T1": pd.to_numeric(dataset["global_T1"], errors="coerce"),
            }
        ).dropna()
        if len(feature_trend) < 5 or feature_trend["feature_value"].nunique() < 2:
            st.info("This feature does not have enough variation for a trend graph.")
        else:
            feature_trend["feature_group_number"] = pd.qcut(
                feature_trend["feature_value"], q=4, labels=False, duplicates="drop"
            )
            group_names = {0: "Q1 lowest", 1: "Q2", 2: "Q3", 3: "Q4 highest"}
            group_order = {name: number for number, name in group_names.items()}
            feature_trend["feature_group"] = feature_trend["feature_group_number"].map(group_names)
            medians = (
                feature_trend.groupby("feature_group", observed=False)
                .agg(
                    median_feature_value=("feature_value", "median"),
                    median_T1=("observed_T1", "median"),
                    n_patients=("observed_T1", "size"),
                )
                .reset_index()
            )
            medians["feature_group_order"] = medians["feature_group"].map(group_order)
            selected_slope = float(
                np.polyfit(
                    medians["feature_group_order"].to_numpy(dtype=float) + 1,
                    medians["median_T1"].to_numpy(dtype=float),
                    1,
                )[0]
            )
            medians["linear_slope"] = selected_slope
            st.caption(
                "Each faint point is one patient. The orange line connects the median T1 score within "
                "four increasing feature-value groups. "
                f"Linear slope: {selected_slope:+.2f} T1 points per feature group."
            )
            points = (
                alt.Chart(feature_trend)
                .mark_circle(size=55, opacity=0.45, color="#6b7280")
                .encode(
                    x=alt.X("feature_value:Q", title=selected_feature),
                    y=alt.Y("observed_T1:Q", title="Observed T1 score"),
                    tooltip=[
                        alt.Tooltip("Patient ID:N", title="Patient ID"),
                        alt.Tooltip("feature_value:Q", title="Feature value", format=".3f"),
                        alt.Tooltip("observed_T1:Q", title="Observed T1", format=".2f"),
                    ],
                )
            )
            median_line = (
                alt.Chart(medians)
                .mark_line(point=alt.OverlayMarkDef(size=100), color="#d97706", strokeWidth=3)
                .encode(
                    x=alt.X("median_feature_value:Q", title=selected_feature),
                    y=alt.Y("median_T1:Q", title="Observed T1 score"),
                    order=alt.Order("feature_group_order:N"),
                    tooltip=[
                        alt.Tooltip("feature_group:N", title="Feature group"),
                        alt.Tooltip("median_feature_value:Q", title="Median feature value", format=".3f"),
                        alt.Tooltip("median_T1:Q", title="Median observed T1", format=".2f"),
                        alt.Tooltip("n_patients:Q", title="Patients"),
                        alt.Tooltip("linear_slope:Q", title="Linear slope", format="+.2f"),
                    ],
                )
            )
            st.altair_chart((points + median_line).properties(height=420), use_container_width=True)

    if include_all_feature_trend_explorer:
        st.markdown("**All-feature individual trend explorer: 10-day data**")
        st.caption(
            "This view uses every active selected feature, without quartile aggregation. "
            "Patients are ordered from lowest to highest observed T1 score; each point is one patient."
        )
        all_features = [
            feature for feature in metadata.get("feature_name", pd.Series(dtype=str)).dropna().tolist()
            if feature in dataset.columns
        ]
        if not all_features:
            st.info("No 10-day feature columns are available for the explorer.")
        else:
            default_feature = "telephony_mobile_data_enabled_fraction"
            default_index = all_features.index(default_feature) if default_feature in all_features else 0
            selected_all_feature = st.selectbox(
                "Choose any active selected feature",
                all_features,
                index=default_index,
                key="phase4_10day_all_feature_trend_selector",
            )
            ordered = dataset[["Subject_ID_D", "global_T1", selected_all_feature]].copy()
            ordered["observed_T1"] = pd.to_numeric(ordered["global_T1"], errors="coerce")
            ordered["feature_value"] = pd.to_numeric(ordered[selected_all_feature], errors="coerce")
            ordered = ordered.dropna(subset=["observed_T1"]).sort_values("observed_T1").reset_index(drop=True)
            ordered["patient_rank"] = range(1, len(ordered) + 1)
            observed = ordered.dropna(subset=["feature_value"]).copy()
            if len(observed) < 2 or observed["feature_value"].nunique() < 2:
                st.info("This feature has fewer than two distinct observed values in the 10-day cohort.")
            else:
                slope, intercept = np.polyfit(observed["patient_rank"], observed["feature_value"], 1)
                observed["linear_trend"] = slope * observed["patient_rank"] + intercept
                rho = observed["feature_value"].corr(observed["observed_T1"], method="spearman")
                metric_row(
                    [
                        ("Patients with feature data", len(observed)),
                        ("Feature missingness", f"{100 * (1 - len(observed) / len(ordered)):.1f}%"),
                        ("Spearman rho vs T1", f"{rho:.2f}" if pd.notna(rho) else "n/a"),
                        ("Linear slope by T1 order", f"{slope:+.4g}"),
                    ]
                )
                actual_trace = (
                    alt.Chart(observed)
                    .mark_line(point=alt.OverlayMarkDef(size=60), color="#d97706")
                    .encode(
                        x=alt.X("patient_rank:Q", title="Patients ordered by observed T1 score", axis=alt.Axis(format="d")),
                        y=alt.Y("feature_value:Q", title=selected_all_feature),
                        order=alt.Order("patient_rank:Q", sort="ascending"),
                        tooltip=[
                            alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                            alt.Tooltip("Subject_ID_D:N", title="Patient ID"),
                            alt.Tooltip("observed_T1:Q", title="Observed T1", format=".2f"),
                            alt.Tooltip("feature_value:Q", title="Feature value", format=".4g"),
                        ],
                    )
                )
                fit_line = (
                    alt.Chart(observed)
                    .mark_line(color="#2563eb", strokeDash=[6, 4], strokeWidth=2)
                    .encode(
                        x=alt.X("patient_rank:Q", title="Patients ordered by observed T1 score"),
                        y=alt.Y("linear_trend:Q", title=selected_all_feature),
                        order=alt.Order("patient_rank:Q", sort="ascending"),
                        tooltip=[alt.Tooltip("linear_trend:Q", title="Linear trend", format=".4g")],
                    )
                )
                st.altair_chart((actual_trace + fit_line).properties(height=430), use_container_width=True)
                st.caption("Orange: raw patient values in T1 order. Blue dashed: ordinary linear trend across patient order. Missing patients are left blank.")

    if not gradient_slopes.empty:
        st.markdown("**Linear slopes across all primary features**")
        st.caption(
            "For each feature, the slope is fitted across its four orange median T1 values. "
            "Positive values indicate higher median T1 in higher feature groups; negative values indicate lower median T1."
        )
        slope_chart_data = gradient_slopes.sort_values("linear_slope")
        slope_chart = (
            alt.Chart(slope_chart_data)
            .mark_bar()
            .encode(
                x=alt.X("linear_slope:Q", title="Linear slope (T1 points per feature group)"),
                y=alt.Y("feature:N", title=None, sort=None),
                color=alt.Color(
                    "direction:N",
                    title="Direction",
                    scale=alt.Scale(
                        domain=["Positive slope", "Negative slope"],
                        range=["#2563eb", "#dc2626"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("feature:N", title="Feature"),
                    alt.Tooltip("linear_slope:Q", title="Linear slope", format="+.2f"),
                    alt.Tooltip("spearman_rho:Q", title="Spearman rho", format="+.2f"),
                    alt.Tooltip("n_observed:Q", title="Patients with data"),
                ],
            )
            .properties(height=650)
        )
        st.altair_chart(slope_chart, use_container_width=True)

    st.markdown(readme if readme else "")
    tabs = st.tabs(["Cognitive Domain Models", "Patient Dataset", "Feature Metadata", "Missingness", "Table Coverage", "Model Results", "Clustering", "Protocol"])

    with tabs[0]:
        st.subheader("Cognitive domain digital phenotype estimates")
        st.caption(
            "Each graph uses the same 37 primary digital features and the same cross-validation design as Outcome 1, "
            "but predicts one T1 cognitive domain at a time."
        )
        domain_colors = {
            "Memory": "#2563eb",
            "Executive function": "#16a34a",
            "Processing speed": "#d97706",
            "Attention": "#9333ea",
            "Motor": "#0891b2",
        }
        if domain_patient_predictions.empty:
            st.info("Cognitive domain models are not available yet.")
            st.code(".venv/bin/python3 phase4_model_t1_cognitive_domains.py")
        else:
            for domain, color in domain_colors.items():
                domain_frame = domain_patient_predictions[
                    domain_patient_predictions["domain"].astype(str).eq(domain)
                ].copy()
                if domain_frame.empty:
                    continue
                domain_group_frame = domain_group_patient_predictions[
                    domain_group_patient_predictions["domain"].astype(str).eq(domain)
                ][["Subject_ID_D", "Subject_ID_N", "group_ridge_prediction"]].copy()
                domain_frame = domain_frame.merge(
                    domain_group_frame,
                    on=["Subject_ID_D", "Subject_ID_N"],
                    how="left",
                )
                domain_frame = domain_frame.sort_values("actual_T1").reset_index(drop=True)
                domain_frame["patient_rank"] = range(1, len(domain_frame) + 1)
                domain_plot = domain_frame.rename(
                    columns={
                        "Subject_ID_D": "Patient ID",
                        "actual_T1": "Observed domain T1 score",
                        "ridge_prediction": "All 37-feature estimate",
                        "group_ridge_prediction": "Domain feature-group estimate",
                    }
                )[[
                    "patient_rank",
                    "Patient ID",
                    "Observed domain T1 score",
                    "All 37-feature estimate",
                    "Domain feature-group estimate",
                ]].melt(
                    id_vars=["patient_rank", "Patient ID"],
                    var_name="score_type",
                    value_name="score",
                )
                st.markdown(f"**{domain} T1**")
                st.caption(
                    "Patients are ordered from lowest to highest observed domain score. "
                    "The black line is observed, the colored line uses all 37 features, and the red line uses "
                    "only the hypothesized feature group for this domain."
                )
                domain_min = int(domain_plot["score"].min()) - 1
                domain_max = int(domain_plot["score"].max()) + 1
                domain_chart = (
                    alt.Chart(domain_plot)
                    .mark_line(point=alt.OverlayMarkDef(size=45))
                    .encode(
                        x=alt.X(
                            "patient_rank:Q",
                            title="Patients ordered by observed domain score",
                            axis=alt.Axis(format="d"),
                        ),
                        y=alt.Y(
                            "score:Q",
                            title=f"{domain} T1 score",
                            scale=alt.Scale(domain=[domain_min, domain_max]),
                        ),
                        color=alt.Color(
                            "score_type:N",
                            title="Measure",
                            scale=alt.Scale(
                                domain=[
                                    "Observed domain T1 score",
                                    "All 37-feature estimate",
                                    "Domain feature-group estimate",
                                ],
                                range=["#111827", color, "#dc2626"],
                            ),
                        ),
                        tooltip=[
                            alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                            alt.Tooltip("Patient ID:N", title="Patient ID"),
                            alt.Tooltip("score_type:N", title="Measure"),
                            alt.Tooltip("score:Q", title="Score", format=".2f"),
                        ],
                    )
                )
                st.altair_chart(domain_chart.properties(height=360), use_container_width=True)
                domain_metric_frame = domain_metrics[domain_metrics["domain"].astype(str).eq(domain)]
                show_fit_legend(domain_metric_frame, "ridge", domain)
                domain_group_metric_frame = domain_group_metrics[
                    domain_group_metrics["domain"].astype(str).eq(domain)
                ]
                show_fit_legend(domain_group_metric_frame, "domain_group_ridge", f"{domain} feature group")
    with tabs[1]:
        st.caption("Raw patient-level values are preserved. Missingness indicators and coverage summaries are included for modeling audit.")
        show_dataframe(dataset, height=650)
    with tabs[2]:
        show_dataframe(metadata, height=520)
    with tabs[3]:
        if not missingness.empty and {"feature_name", "missing_percent"}.issubset(missingness.columns):
            st.bar_chart(missingness.set_index("feature_name")["missing_percent"])
        show_dataframe(missingness, height=520)
    with tabs[4]:
        if not coverage.empty and {"table_name", "table_status"}.issubset(coverage.columns):
            summary = (
                coverage.assign(calculated=coverage["table_status"].astype(str).eq("calculated"))
                .groupby("table_name", dropna=False)
                .agg(patient_table_blocks=("table_status", "size"), calculated_blocks=("calculated", "sum"))
                .reset_index()
            )
            summary["calculated_percent"] = (100 * summary["calculated_blocks"] / summary["patient_table_blocks"]).round(1)
            show_dataframe(summary, height=260)
        show_dataframe(coverage, height=520)
    with tabs[5]:
        if model_metrics.empty:
            st.info("The ridge model has not been run yet.")
            st.code(".venv/bin/python3 phase4_model_t1_ridge.py")
        else:
            pooled = model_metrics[model_metrics.get("analysis_scope", pd.Series(dtype=str)).astype(str).eq("pooled")]
            if not pooled.empty and {"model", "rmse", "mae", "r2"}.issubset(pooled.columns):
                st.subheader("Pooled repeated cross-validation metrics")
                show_dataframe(pooled, height=180)
                chart = pooled.set_index("model")[["rmse", "mae"]]
                st.bar_chart(chart)
            st.subheader("Model report")
            st.markdown(model_readme if model_readme else "")
            with st.expander("Feature inclusion decisions"):
                show_dataframe(model_feature_set, height=420)
            with st.expander("Fold-level predictions"):
                show_dataframe(model_predictions, height=520)
            with st.expander("Calibration and score interpretation"):
                st.markdown(score_calibration_readme if score_calibration_readme else "")
                primary_calibration = score_calibration[score_calibration["feature_scope"].eq("primary_37")]
                if not primary_calibration.empty:
                    st.scatter_chart(primary_calibration, x="actual_global_T1", y=["ridge_prediction", "actual_global_T1"])
                show_dataframe(score_calibration_metrics, height=360)
                st.subheader("Predicted-score bins")
                show_dataframe(score_calibration_bins, height=360)
                st.subheader("Coefficient stability")
                show_dataframe(coefficient_summary, height=520)
                with st.expander("Raw fold coefficients"):
                    show_dataframe(model_coefficients, height=520)
    with tabs[6]:
        if cluster_quality.empty:
            st.info("The exploratory clustering analysis has not been run yet.")
            st.code(".venv/bin/python3 phase4_cluster_t1_baseline.py")
        else:
            st.markdown(cluster_readme if cluster_readme else "")
            st.subheader("Candidate cluster quality")
            show_dataframe(cluster_quality, height=240)
            if {"k", "mean_silhouette", "mean_pairwise_ari"}.issubset(cluster_quality.columns):
                st.line_chart(cluster_quality.set_index("k")[["mean_silhouette", "mean_pairwise_ari"]])
            st.subheader("Patient assignments")
            show_dataframe(cluster_assignments, height=440)
            st.subheader("PCA coordinates")
            if {"PC1", "PC2", "cluster_label"}.issubset(cluster_pca_scatter.columns):
                st.scatter_chart(cluster_pca_scatter, x="PC1", y="PC2", color="cluster_label")
            show_dataframe(cluster_pca_scatter, height=360)
            st.subheader("Cluster audit summary")
            show_dataframe(cluster_audit_summary, height=260)
            st.subheader("High-coverage sensitivity clustering")
            st.caption("Subset rule: feature missingness <= 50% and table coverage >= 50%.")
            if {"PC1", "PC2", "cluster_label"}.issubset(cluster_high_assignments.columns):
                st.scatter_chart(cluster_high_assignments, x="PC1", y="PC2", color="cluster_label")
            show_dataframe(cluster_high_quality, height=220)
            show_dataframe(cluster_high_assignments, height=360)
            with st.expander("PCA loadings"):
                show_dataframe(cluster_pca_loadings, height=440)
            with st.expander("Ranked standardized feature differences"):
                show_dataframe(cluster_feature_differences, height=520)
            st.subheader("Exploratory phenotype profiles")
            st.markdown(cluster_profiles_readme if cluster_profiles_readme else "")
            show_dataframe(cluster_profiles, height=280)
            st.subheader("Coverage-controlled cluster stability")
            show_dataframe(cluster_stability, height=280)
            with st.expander("Profile feature details"):
                show_dataframe(cluster_profile_features, height=520)
            with st.expander("Patient acquisition audit"):
                show_dataframe(cluster_patient_audit, height=520)
            with st.expander("Feature summaries by cluster"):
                show_dataframe(cluster_feature_summary, height=520)
    with tabs[7]:
        st.markdown(load_text(PATHS["phase4_protocol"]) or "No Phase 4 protocol available.")


def other_models_page() -> None:
    st.markdown(
        '<h1 style="font-size: 2.6rem; font-weight: 800; margin-bottom: 0.25rem;">'
        "Other Models: exploratory Phase 4 10-day T1"
        "</h1>",
        unsafe_allow_html=True,
    )
    st.caption(
        "An isolated search for nonlinear, interaction, latent-domain, and regularized patterns. "
        "These models do not replace the primary Phase 4 phenotype."
    )
    predictions = load_csv(PATHS["other_models_predictions"])
    patients = load_csv(PATHS["other_models_patient_predictions"])
    metrics = load_csv(PATHS["other_models_metrics"])
    importance = load_csv(PATHS["other_models_importance"])
    metadata = load_csv(PATHS["other_models_metadata"])
    readme = load_text(PATHS["other_models_readme"])
    protocol = load_text(PATHS["other_models_protocol"])
    if metrics.empty or patients.empty:
        st.info("The Other Models outputs are not available yet.")
        st.code("DYLD_LIBRARY_PATH=/opt/homebrew/opt/libomp/lib .venv/bin/python3 other_models_phase4_10day.py")
        return

    pooled = metrics[metrics["analysis_scope"].astype(str).eq("pooled")].copy()
    baseline = pooled[pooled["model"].eq("mean_baseline")]
    baseline_rmse = float(baseline["rmse"].iloc[0]) if not baseline.empty else float("nan")
    metric_row(
        [
            ("Patients", patients["Subject_ID_D"].nunique() if "Subject_ID_D" in patients.columns else len(patients)),
            ("Selected features", len(metadata) if not metadata.empty else 67),
            ("Validation repeats", metrics[metrics["analysis_scope"].astype(str).eq("repeat")]["repeat"].nunique()),
            ("Mean baseline RMSE", f"{baseline_rmse:.2f}"),
        ]
    )

    model_labels = {
        "mean_baseline": "Mean baseline",
        "elastic_net": "Elastic Net",
        "pls": "PLS",
        "spline_ridge": "Spline Ridge",
        "random_forest": "Random Forest",
        "extra_trees": "Extra Trees",
        "hist_gradient_boosting": "HistGradientBoosting",
        "xgboost": "XGBoost",
    }
    model_colors = {
        "mean_baseline": "#111827",
        "elastic_net": "#2563eb",
        "pls": "#ea580c",
        "spline_ridge": "#9333ea",
        "random_forest": "#16a34a",
        "extra_trees": "#0891b2",
        "hist_gradient_boosting": "#dc2626",
        "xgboost": "#7c2d12",
    }
    pooled["model_label"] = pooled["model"].map(model_labels).fillna(pooled["model"])
    pooled["delta_vs_baseline"] = pooled["rmse"] - baseline_rmse
    pooled_display = pooled[["model_label", "n_predictions", "rmse", "mae", "r2", "delta_vs_baseline"]].sort_values("rmse")

    st.subheader("1. Same-baseline model comparison")
    st.caption(
        "Lower RMSE is better. Every value is pooled repeated cross-validation performance; the mean baseline "
        "is recalculated inside each training fold."
    )
    bar_data = pooled[["model_label", "rmse", "model"]].sort_values("rmse")
    bar_chart = (
        alt.Chart(bar_data)
        .mark_bar()
        .encode(
            y=alt.Y("model_label:N", sort="-x", title=None),
            x=alt.X("rmse:Q", title="Pooled repeated-CV RMSE"),
            color=alt.Color(
                "model:N",
                legend=None,
                scale=alt.Scale(domain=list(model_colors), range=[model_colors[key] for key in model_colors]),
            ),
            tooltip=[
                alt.Tooltip("model_label:N", title="Model"),
                alt.Tooltip("rmse:Q", title="RMSE", format=".2f"),
            ],
        )
    )
    if not np.isnan(baseline_rmse):
        baseline_rule = alt.Chart(pd.DataFrame({"baseline_rmse": [baseline_rmse]})).mark_rule(
            color="#111827", strokeDash=[5, 4]
        ).encode(x=alt.X("baseline_rmse:Q"))
        st.altair_chart((bar_chart + baseline_rule).properties(height=310), use_container_width=True)
    else:
        st.altair_chart(bar_chart.properties(height=310), use_container_width=True)
    show_dataframe(pooled_display, height=300)

    st.subheader("2. Patient-order estimate graph")
    available_models = [name for name in model_labels if name != "mean_baseline" and f"{name}_prediction" in patients.columns]
    selected_model = st.selectbox(
        "Model estimate",
        available_models,
        format_func=lambda name: model_labels.get(name, name),
    )
    ordered = patients.sort_values("actual_global_T1").reset_index(drop=True)
    ordered["patient_rank"] = range(1, len(ordered) + 1)
    estimate_label = f"{model_labels[selected_model]} estimate"
    plot_data = ordered.rename(
        columns={
            "Subject_ID_D": "Patient ID",
            "actual_global_T1": "Observed T1 score",
            f"{selected_model}_prediction": estimate_label,
        }
    )[["patient_rank", "Patient ID", "Observed T1 score", estimate_label]].melt(
        id_vars=["patient_rank", "Patient ID"], var_name="score_type", value_name="t1_score"
    )
    chart = (
        alt.Chart(plot_data)
        .mark_line(point=alt.OverlayMarkDef(size=45))
        .encode(
            x=alt.X("patient_rank:Q", title="Patients ordered by observed T1 score", axis=alt.Axis(format="d")),
            y=alt.Y("t1_score:Q", title="T1 score"),
            color=alt.Color(
                "score_type:N",
                title="Measure",
                scale=alt.Scale(domain=["Observed T1 score", estimate_label], range=["#111827", model_colors[selected_model]]),
            ),
            tooltip=[
                alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                alt.Tooltip("Patient ID:N", title="Patient ID"),
                alt.Tooltip("score_type:N", title="Measure"),
                alt.Tooltip("t1_score:Q", title="T1 score", format=".2f"),
            ],
        )
    )
    st.altair_chart(chart.properties(height=430), use_container_width=True)
    selected_metrics = pooled[pooled["model"].eq(selected_model)]
    if not selected_metrics.empty:
        row = selected_metrics.iloc[0]
        delta = float(row["rmse"]) - baseline_rmse
        st.caption(
            f"Fit summary ({model_labels[selected_model]}): RMSE {float(row['rmse']):.2f} | "
            f"MAE {float(row['mae']):.2f} | R2 {float(row['r2']):.2f} | "
            f"{delta:+.2f} RMSE versus mean baseline"
        )

    st.subheader("3. Held-out tree permutation patterns")
    st.caption(
        "These importance values were calculated on held-out folds from the first repeated-CV pass only. "
        "They are descriptive and were not used to select or refit models. Positive values indicate that "
        "permuting a feature worsened held-out RMSE."
    )
    if importance.empty:
        st.info("Permutation importance is not available yet.")
    else:
        importance_model = st.selectbox(
            "Tree model",
            sorted(importance["model"].unique().tolist()),
            format_func=lambda name: model_labels.get(name, name),
        )
        top_importance = (
            importance[importance["model"].eq(importance_model)]
            .groupby("feature", as_index=False)["importance_mean"]
            .mean()
            .sort_values("importance_mean", ascending=False)
            .head(15)
        )
        importance_chart = (
            alt.Chart(top_importance)
            .mark_bar()
            .encode(
                y=alt.Y("feature:N", sort="-x", title=None),
                x=alt.X("importance_mean:Q", title="Held-out RMSE improvement after feature permutation"),
                tooltip=[alt.Tooltip("feature:N", title="Feature"), alt.Tooltip("importance_mean:Q", format=".3f")],
            )
        )
        st.altair_chart(importance_chart.properties(height=420), use_container_width=True)

    with st.expander("Protocol and interpretation"):
        st.markdown(protocol or readme or "No protocol README available yet.")


def suggestions_page() -> None:
    st.markdown(
        '<h1 style="font-size: 2.6rem; font-weight: 800; margin-bottom: 0.25rem;">'
        "Suggestions: high-coverage 10-day T1 baseline"
        "</h1>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Exploratory sensitivity analysis restricted to patients with the most complete 10-day feature coverage. "
        "This does not replace the full-cohort model."
    )
    metrics = load_csv(PATHS["suggestions_metrics"])
    patient_predictions = load_csv(PATHS["suggestions_patient_predictions"])
    domain_metrics = load_csv(PATHS["suggestions_domain_metrics"])
    domain_patient_predictions = load_csv(PATHS["suggestions_domain_patient_predictions"])
    cohorts = load_csv(PATHS["suggestions_cohorts"])
    readme = load_text(PATHS["suggestions_readme"])
    protocol = load_text(PATHS["suggestions_protocol"])
    if metrics.empty or patient_predictions.empty:
        st.info("The Suggestions outputs are not available yet.")
        st.code("DYLD_LIBRARY_PATH=/opt/homebrew/opt/libomp/lib .venv/bin/python3 suggestions_10day_coverage_models.py")
        return

    model_labels = {
        "mean_baseline": "Mean baseline",
        "elastic_net": "Elastic Net",
        "pls": "PLS",
        "spline_ridge": "Spline Ridge",
        "random_forest": "Random Forest",
        "extra_trees": "Extra Trees",
        "hist_gradient_boosting": "HistGradientBoosting",
        "xgboost": "XGBoost",
    }
    model_colors = {
        "mean_baseline": "#111827",
        "elastic_net": "#2563eb",
        "pls": "#ea580c",
        "spline_ridge": "#9333ea",
        "random_forest": "#16a34a",
        "extra_trees": "#0891b2",
        "hist_gradient_boosting": "#dc2626",
        "xgboost": "#7c2d12",
    }
    pooled = metrics[metrics["analysis_scope"].astype(str).eq("pooled")].copy()
    top30 = pooled[pooled["cohort_size"].astype(int).eq(30) & pooled["model"].eq("mean_baseline")]
    top30_rmse = float(top30["rmse"].iloc[0]) if not top30.empty else float("nan")
    metric_row(
        [
            ("Full cohort", 81),
            ("Top-30 mean missingness", f"{100 * cohorts.head(30)['baseline_feature_missing_fraction'].mean():.1f}%"),
            ("Top-20 mean missingness", f"{100 * cohorts.head(20)['baseline_feature_missing_fraction'].mean():.1f}%"),
            ("Top-30 baseline RMSE", f"{top30_rmse:.2f}"),
        ]
    )
    st.warning(
        "Top 30 is the main exploratory cohort. Top 20 is sensitivity analysis. Top 10 is descriptive only; "
        "its apparent model improvements are too unstable to interpret as predictive evidence."
    )

    st.subheader("1. Coverage-ranked cohort summary")
    cohort_summary_rows = []
    for size in [30, 20, 10, len(cohorts)]:
        frame = cohorts.head(size)
        cohort_summary_rows.append(
            {
                "cohort": f"Top {size}" if size != len(cohorts) else "Full cohort",
                "patients": len(frame),
                "mean_feature_missingness": frame["baseline_feature_missing_fraction"].mean(),
                "mean_table_coverage": frame["baseline_table_coverage_fraction"].mean(),
                "observed_T1_sd": pd.to_numeric(frame["global_T1"], errors="coerce").std(),
                "observed_T1_min": pd.to_numeric(frame["global_T1"], errors="coerce").min(),
                "observed_T1_max": pd.to_numeric(frame["global_T1"], errors="coerce").max(),
            }
        )
    cohort_summary = pd.DataFrame(cohort_summary_rows)
    cohort_summary["mean_feature_missingness"] = (100 * cohort_summary["mean_feature_missingness"]).round(1)
    cohort_summary["mean_table_coverage"] = (100 * cohort_summary["mean_table_coverage"]).round(1)
    cohort_summary = cohort_summary.sort_values("patients", ascending=False)
    show_dataframe(cohort_summary, height=220)
    with st.expander("Coverage ranking and selected patients"):
        show_dataframe(cohorts, height=420)

    st.subheader("2. Same-baseline model comparison")
    cohort_choice = st.selectbox(
        "Coverage cohort",
        [30, 20, 10],
        format_func=lambda n: f"Top {n} patients" + (" (main exploratory cohort)" if n == 30 else ""),
    )
    selected_pooled = pooled[pooled["cohort_size"].astype(int).eq(cohort_choice)].copy()
    baseline_rows = selected_pooled[selected_pooled["model"].eq("mean_baseline")]
    baseline_rmse = float(baseline_rows["rmse"].iloc[0]) if not baseline_rows.empty else float("nan")
    selected_pooled["model_label"] = selected_pooled["model"].map(model_labels).fillna(selected_pooled["model"])
    selected_pooled["delta_vs_baseline"] = selected_pooled["rmse"] - baseline_rmse
    selected_display = selected_pooled[["model_label", "n_predictions", "rmse", "mae", "r2", "delta_vs_baseline"]].sort_values("rmse")
    bar_data = selected_pooled[["model_label", "rmse", "model"]].sort_values("rmse")
    bar_chart = (
        alt.Chart(bar_data)
        .mark_bar()
        .encode(
            y=alt.Y("model_label:N", sort="-x", title=None),
            x=alt.X("rmse:Q", title="Pooled repeated-CV RMSE"),
            color=alt.Color(
                "model:N",
                legend=None,
                scale=alt.Scale(domain=list(model_colors), range=[model_colors[key] for key in model_colors]),
            ),
            tooltip=[alt.Tooltip("model_label:N", title="Model"), alt.Tooltip("rmse:Q", title="RMSE", format=".2f")],
        )
    )
    if not np.isnan(baseline_rmse):
        baseline_rule = alt.Chart(pd.DataFrame({"baseline_rmse": [baseline_rmse]})).mark_rule(
            color="#111827", strokeDash=[5, 4]
        ).encode(x=alt.X("baseline_rmse:Q"))
        st.altair_chart((bar_chart + baseline_rule).properties(height=310), use_container_width=True)
    else:
        st.altair_chart(bar_chart.properties(height=310), use_container_width=True)
    show_dataframe(selected_display, height=300)

    st.subheader("3. Patient-order estimate graph")
    selected_patients = patient_predictions[patient_predictions["cohort_size"].astype(int).eq(cohort_choice)].copy()
    available_models = [name for name in model_labels if name != "mean_baseline" and f"{name}_prediction" in selected_patients.columns]
    selected_model = st.selectbox("Model estimate", available_models, format_func=lambda name: model_labels.get(name, name))
    ordered = selected_patients.sort_values("actual_global_T1").reset_index(drop=True)
    ordered["patient_rank"] = range(1, len(ordered) + 1)
    patient_x_domain = [0.5, len(ordered) + 0.5]

    def focused_y_domain(values: pd.Series) -> list[float]:
        numeric = pd.to_numeric(values, errors="coerce").dropna()
        low = float(numeric.min())
        high = float(numeric.max())
        spread = high - low
        padding = max(0.5, spread * 0.08)
        if spread == 0:
            padding = max(1.0, abs(low) * 0.05)
        return [low - padding, high + padding]

    estimate_label = f"{model_labels[selected_model]} estimate"
    plot_data = ordered.rename(
        columns={
            "Subject_ID_D": "Patient ID",
            "actual_global_T1": "Observed T1 score",
            f"{selected_model}_prediction": estimate_label,
        }
    )[["patient_rank", "Patient ID", "Observed T1 score", estimate_label]].melt(
        id_vars=["patient_rank", "Patient ID"], var_name="score_type", value_name="t1_score"
    )
    chart = (
        alt.Chart(plot_data)
        .mark_line(point=alt.OverlayMarkDef(size=45))
        .encode(
            x=alt.X(
                "patient_rank:Q",
                title="Patients ordered by observed T1 score",
                axis=alt.Axis(format="d"),
                scale=alt.Scale(domain=patient_x_domain),
            ),
            y=alt.Y("t1_score:Q", title="T1 score", scale=alt.Scale(domain=focused_y_domain(plot_data["t1_score"]))),
            color=alt.Color(
                "score_type:N",
                title="Measure",
                scale=alt.Scale(domain=["Observed T1 score", estimate_label], range=["#111827", model_colors[selected_model]]),
            ),
            tooltip=[
                alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                alt.Tooltip("Patient ID:N", title="Patient ID"),
                alt.Tooltip("score_type:N", title="Measure"),
                alt.Tooltip("t1_score:Q", title="T1 score", format=".2f"),
            ],
        )
    )
    st.altair_chart(chart.properties(height=430), use_container_width=True)

    st.subheader("4. Outcome 1: Phase 4-style model graphs")
    st.caption(
        "Each graph uses the same selected coverage cohort, with patients ordered from lowest to highest observed T1 score. "
        "The black line is observed T1; the colored line is the model estimate."
    )
    for model_name in available_models:
        estimate_label = f"{model_labels[model_name]} estimate"
        model_plot_data = ordered.rename(
            columns={
                "Subject_ID_D": "Patient ID",
                "actual_global_T1": "Observed T1 score",
                f"{model_name}_prediction": estimate_label,
            }
        )[["patient_rank", "Patient ID", "Observed T1 score", estimate_label]].melt(
            id_vars=["patient_rank", "Patient ID"],
            var_name="score_type",
            value_name="t1_score",
        )
        model_chart = (
            alt.Chart(model_plot_data)
            .mark_line(point=alt.OverlayMarkDef(size=45))
        .encode(
            x=alt.X(
                "patient_rank:Q",
                title="Patients ordered by observed T1 score",
                axis=alt.Axis(format="d"),
                scale=alt.Scale(domain=patient_x_domain),
            ),
                y=alt.Y("t1_score:Q", title="T1 score", scale=alt.Scale(domain=focused_y_domain(model_plot_data["t1_score"]))),
                color=alt.Color(
                    "score_type:N",
                    title="Measure",
                    scale=alt.Scale(
                        domain=["Observed T1 score", estimate_label],
                        range=["#111827", model_colors[model_name]],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                    alt.Tooltip("Patient ID:N", title="Patient ID"),
                    alt.Tooltip("score_type:N", title="Measure"),
                    alt.Tooltip("t1_score:Q", title="T1 score", format=".2f"),
                ],
            )
        )
        st.markdown(f"**{model_labels[model_name]}**")
        st.altair_chart(model_chart.properties(height=380), use_container_width=True)
        model_metric = selected_pooled[selected_pooled["model"].eq(model_name)]
        if not model_metric.empty:
            row = model_metric.iloc[0]
            delta = float(row["rmse"]) - baseline_rmse
            st.caption(
                f"RMSE {float(row['rmse']):.2f} | MAE {float(row['mae']):.2f} | "
                f"R2 {float(row['r2']):.2f} | {delta:+.2f} RMSE versus mean baseline"
            )

    st.markdown("**Mean baseline**")
    baseline_plot_data = ordered.rename(
        columns={
            "Subject_ID_D": "Patient ID",
            "actual_global_T1": "Observed T1 score",
            "mean_baseline_prediction": "Mean baseline estimate",
        }
    )[["patient_rank", "Patient ID", "Observed T1 score", "Mean baseline estimate"]].melt(
        id_vars=["patient_rank", "Patient ID"],
        var_name="score_type",
        value_name="t1_score",
    )
    baseline_chart = (
        alt.Chart(baseline_plot_data)
        .mark_line(point=alt.OverlayMarkDef(size=45))
        .encode(
            x=alt.X(
                "patient_rank:Q",
                title="Patients ordered by observed T1 score",
                axis=alt.Axis(format="d"),
                scale=alt.Scale(domain=patient_x_domain),
            ),
            y=alt.Y("t1_score:Q", title="T1 score", scale=alt.Scale(domain=focused_y_domain(baseline_plot_data["t1_score"]))),
            color=alt.Color(
                "score_type:N",
                title="Measure",
                scale=alt.Scale(
                    domain=["Observed T1 score", "Mean baseline estimate"],
                    range=["#111827", "#6b7280"],
                ),
            ),
            tooltip=[
                alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                alt.Tooltip("Patient ID:N", title="Patient ID"),
                alt.Tooltip("score_type:N", title="Measure"),
                alt.Tooltip("t1_score:Q", title="T1 score", format=".2f"),
            ],
        )
    )
    st.altair_chart(baseline_chart.properties(height=380), use_container_width=True)
    st.caption(
        f"The gray line is the within-training-fold mean-baseline prediction averaged for each patient. "
        f"Pooled baseline RMSE for this cohort: {baseline_rmse:.2f}."
    )

    st.subheader("5. Cognitive domain graphs")
    st.caption(
        "Each domain is ordered independently by its own observed domain T1 score. The black line is observed, "
        "the domain-colored line uses all selected features, and the red line uses the hypothesized domain feature group."
    )
    domain_colors = {
        "Memory": "#2563eb",
        "Executive function": "#16a34a",
        "Processing speed": "#d97706",
        "Attention": "#9333ea",
        "Motor": "#0891b2",
    }
    if domain_patient_predictions.empty:
        st.info("Cognitive-domain Suggestions outputs are not available yet.")
    else:
        for domain, domain_color in domain_colors.items():
            domain_frame = domain_patient_predictions[
                domain_patient_predictions["cohort_size"].astype(int).eq(cohort_choice)
                & domain_patient_predictions["domain"].astype(str).eq(domain)
            ].copy()
            if domain_frame.empty:
                continue
            domain_frame = domain_frame.sort_values("actual_T1").reset_index(drop=True)
            domain_frame["patient_rank"] = range(1, len(domain_frame) + 1)
            domain_plot = domain_frame.rename(
                columns={
                    "Subject_ID_D": "Patient ID",
                    "actual_T1": "Observed domain T1 score",
                    "ridge_prediction": "All-feature domain estimate",
                    "group_ridge_prediction": "Domain feature-group estimate",
                }
            )[[
                "patient_rank",
                "Patient ID",
                "Observed domain T1 score",
                "All-feature domain estimate",
                "Domain feature-group estimate",
            ]].melt(
                id_vars=["patient_rank", "Patient ID"],
                var_name="score_type",
                value_name="score",
            )
            domain_chart = (
                alt.Chart(domain_plot)
                .mark_line(point=alt.OverlayMarkDef(size=45))
                .encode(
                    x=alt.X(
                        "patient_rank:Q",
                        title=f"Patients ordered by observed {domain} T1 score",
                        axis=alt.Axis(format="d"),
                        scale=alt.Scale(domain=[0.5, len(domain_frame) + 0.5]),
                    ),
                    y=alt.Y(
                        "score:Q",
                        title=f"{domain} T1 score",
                        scale=alt.Scale(domain=focused_y_domain(domain_plot["score"])),
                    ),
                    color=alt.Color(
                        "score_type:N",
                        title="Measure",
                        scale=alt.Scale(
                            domain=[
                                "Observed domain T1 score",
                                "All-feature domain estimate",
                                "Domain feature-group estimate",
                            ],
                            range=["#111827", domain_color, "#dc2626"],
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                        alt.Tooltip("Patient ID:N", title="Patient ID"),
                        alt.Tooltip("score_type:N", title="Measure"),
                        alt.Tooltip("score:Q", title="Score", format=".2f"),
                    ],
                )
            )
            st.markdown(f"**{domain}**")
            st.altair_chart(domain_chart.properties(height=380), use_container_width=True)
            domain_fit = domain_metrics[
                domain_metrics["cohort_size"].astype(int).eq(cohort_choice)
                & domain_metrics["domain"].astype(str).eq(domain)
                & domain_metrics["analysis_scope"].astype(str).eq("pooled")
            ]
            if not domain_fit.empty:
                fit_text = " | ".join(
                    f"{row.model}: RMSE {float(row.rmse):.2f}"
                    for row in domain_fit.itertuples()
                    if row.model != "mean_baseline"
                )
                st.caption(fit_text)

    with st.expander("Protocol and interpretation"):
        st.markdown(protocol or readme or "No protocol README available yet.")


def result_explorer_page() -> None:
    render_result_explorer(ROOT)


def _render_with_path_overrides(overrides: dict[str, Path], render) -> None:
    missing = object()
    previous = {key: PATHS.get(key, missing) for key in overrides}
    PATHS.update(overrides)
    try:
        render()
    finally:
        for key, value in previous.items():
            if value is missing:
                PATHS.pop(key, None)
            else:
                PATHS[key] = value


def phase4_10day_page() -> None:
    root = ROOT / "output/analysis_candidates/phase4_10day_t1_baseline"
    model = root / "model_t1_ridge"
    cluster = root / "cluster_t1_baseline"
    overrides = {
        "phase4_protocol": ROOT / "PHASE4_10_DAY_BASELINE_PROTOCOL.md",
        "phase4_baseline_dataset": root / "phase4_10day_t1_baseline_patient_dataset.csv",
        "phase4_feature_metadata": root / "phase4_10day_t1_baseline_feature_metadata.csv",
        "phase4_missingness": root / "phase4_10day_t1_baseline_missingness_summary.csv",
        "phase4_table_coverage": root / "phase4_10day_t1_baseline_table_coverage.csv",
        "phase4_readme": root / "README_phase4_10day_t1_baseline.md",
        "phase4_model_predictions": model / "phase4_t1_ridge_predictions.csv",
        "phase4_model_metrics": model / "phase4_t1_ridge_metrics.csv",
        "phase4_model_feature_set": model / "phase4_t1_ridge_feature_set.csv",
        "phase4_model_readme": model / "README_phase4_t1_ridge.md",
        "phase4_model_coefficients": model / "phase4_t1_ridge_coefficients.csv",
        "phase4_score_calibration": model / "phase4_t1_score_calibration_by_patient.csv",
        "phase4_score_calibration_bins": model / "phase4_t1_score_calibration_bins.csv",
        "phase4_score_calibration_metrics": model / "phase4_t1_score_calibration_metrics.csv",
        "phase4_coefficient_summary": model / "phase4_t1_ridge_coefficient_summary.csv",
        "phase4_score_calibration_readme": model / "README_phase4_t1_score_calibration.md",
        "phase4_gradient_patient_predictions": root / "model_t1_gradient_weighted/phase4_t1_gradient_weighted_patient_predictions.csv",
        "phase4_gradient_metrics": root / "model_t1_gradient_weighted/phase4_t1_gradient_weighted_metrics.csv",
        "phase4_slope_selected_patient_predictions": root / "model_t1_slope_selected/phase4_t1_slope_selected_patient_predictions.csv",
        "phase4_slope_selected_metrics": root / "model_t1_slope_selected/phase4_t1_slope_selected_metrics.csv",
        "phase4_direction_constrained_patient_predictions": root / "model_t1_direction_constrained/phase4_t1_direction_constrained_patient_predictions.csv",
        "phase4_direction_constrained_metrics": root / "model_t1_direction_constrained/phase4_t1_direction_constrained_metrics.csv",
        "phase4_all_direction_patient_predictions": root / "model_t1_all_direction_constrained/phase4_10day_all_direction_constrained_patient_predictions.csv",
        "phase4_all_direction_metrics": root / "model_t1_all_direction_constrained/phase4_10day_all_direction_constrained_metrics.csv",
        "phase4_alternative_patient_predictions": root / "model_t1_alternatives/phase4_t1_alternative_patient_predictions.csv",
        "phase4_alternative_metrics": root / "model_t1_alternatives/phase4_t1_alternative_metrics.csv",
        "phase4_domain_patient_predictions": root / "model_t1_cognitive_domains/phase4_t1_cognitive_domain_patient_predictions.csv",
        "phase4_domain_metrics": root / "model_t1_cognitive_domains/phase4_t1_cognitive_domain_metrics.csv",
        "phase4_domain_group_patient_predictions": root / "model_t1_cognitive_domain_groups/phase4_t1_cognitive_domain_group_patient_predictions.csv",
        "phase4_domain_group_metrics": root / "model_t1_cognitive_domain_groups/phase4_t1_cognitive_domain_group_metrics.csv",
        "phase4_cluster_assignments": cluster / "phase4_t1_cluster_assignments.csv",
        "phase4_cluster_quality": cluster / "phase4_t1_cluster_quality.csv",
        "phase4_cluster_feature_summary": cluster / "phase4_t1_cluster_feature_summary.csv",
        "phase4_cluster_pca_loadings": cluster / "phase4_t1_cluster_pca_loadings.csv",
        "phase4_cluster_patient_audit": cluster / "phase4_cluster_patient_audit.csv",
        "phase4_cluster_audit_summary": cluster / "phase4_cluster_audit_summary.csv",
        "phase4_cluster_feature_differences": cluster / "phase4_cluster_feature_differences.csv",
        "phase4_cluster_pca_scatter": cluster / "phase4_cluster_pca_scatter.csv",
        "phase4_cluster_high_assignments": cluster / "phase4_cluster_high_coverage_assignments.csv",
        "phase4_cluster_high_quality": cluster / "phase4_cluster_high_coverage_quality.csv",
        "phase4_cluster_profiles": cluster / "phase4_cluster_profiles.csv",
        "phase4_cluster_profile_features": cluster / "phase4_cluster_profile_features.csv",
        "phase4_cluster_stability": cluster / "phase4_cluster_stability.csv",
        "phase4_cluster_profiles_readme": cluster / "README_phase4_cluster_profiles.md",
        "phase4_cluster_readme": cluster / "README_phase4_t1_clustering.md",
    }
    _render_with_path_overrides(
        overrides,
        lambda: phase4_baseline_page(
            title="Phase 4 10-Day T1 Baseline Digital Phenotype",
            caption="Phase 4-equivalent baseline workflow using the Phase 7 availability-anchored 10-day T1 data.",
            include_all_feature_trend_explorer=True,
        ),
    )


@st.fragment(run_every="10s")
def phase5_t2_live_panel() -> None:
    status = load_csv(PATHS["phase5_status"])
    checkpoint_path = PATHS["phase5_checkpoint"]
    checkpoint_states: dict[str, str] = {}
    if checkpoint_path.exists():
        for line in checkpoint_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            subject_id = str(record.get("Subject_ID_D", ""))
            if subject_id:
                checkpoint_states[subject_id] = str(record.get("status", ""))
    checkpoint_count = sum(state == "completed" for state in checkpoint_states.values())
    retry_checkpoint_count = sum(state == "needs_retry" for state in checkpoint_states.values())
    calculated = int(status["table_status"].astype(str).eq("calculated").sum()) if not status.empty and "table_status" in status.columns else 0
    retryable_errors = int(status["table_status"].astype(str).eq("retryable_error").sum()) if not status.empty and "table_status" in status.columns else 0
    total = len(status) if not status.empty else 0
    patients = int(status["Subject_ID_D"].nunique()) if not status.empty and "Subject_ID_D" in status.columns else 0
    wide = load_csv(PATHS["phase5_wide"])
    coverage = load_csv(PATHS["phase5_coverage"])
    feature_summary = load_csv(PATHS["phase5_feature_coverage_summary"])
    selected_count = int(feature_summary["feature_name"].nunique()) if "feature_name" in feature_summary else 0
    primary_count = int(feature_summary["t2_analysis_role"].eq("primary_eligible_10pct").sum()) if "t2_analysis_role" in feature_summary else 0
    sensitivity_count = int(feature_summary["t2_analysis_role"].eq("sensitivity_only_below_10pct").sum()) if "t2_analysis_role" in feature_summary else 0
    t2_patients = int(wide["Subject_ID_D"].nunique()) if not wide.empty and "Subject_ID_D" in wide else patients
    if not feature_summary.empty and "t2_missingness_percent" in feature_summary:
        mean_missingness = f"{feature_summary['t2_missingness_percent'].mean():.1f}%"
    else:
        mean_missingness = "n/a"

    st.subheader("T2 feature summary")
    metric_row(
        [
            ("T2 source patients", t2_patients),
            ("Selected features", selected_count),
            ("Primary-model features", primary_count),
            ("Sensitivity-only features", sensitivity_count),
            ("Mean T2 feature missingness", mean_missingness),
        ]
    )
    st.caption(
        "Light is excluded from the active T2 set. Primary-model features are T1-primary features that meet the 10% T2 coverage rule. "
        "Features below 10% are sensitivity-only; other non-primary features meeting the threshold remain support features."
    )
    st.info(
        f"Each T2 patient is checked against 17 selected sensor tables, giving approximately {t2_patients * 17:,} expected patient-table attempts. "
        "'No usable pre-T2 window' means the extractor found no eligible data in the T2-7-day window or the documented T2-30-day fallback window; it does not mean that many patients are missing."
    )

    st.subheader("Live extraction progress")
    metric_row(
        [
            ("Patients with status", patients),
            ("Table statuses", total),
            ("Calculated tables", calculated),
            ("Completed patients", checkpoint_count),
            ("Patients needing retry", retry_checkpoint_count),
        ]
    )
    if retryable_errors:
        st.error(
            f"This extraction is incomplete: {retryable_errors} table attempts ended with database connection errors. "
            "Do not use the feature tables for analysis until the run completes without retryable errors."
        )
    if total:
        expected_attempts = patients * 17
        st.caption(
            f"Current table accounting: {total} recorded rows out of approximately {expected_attempts} expected patient-table attempts. "
            "Calculated table results are usable table-level outputs; missing-window results reflect acquisition coverage."
        )
    if total == 0:
        st.info("The T2 extraction has not produced status output yet.")
        st.code(".venv/bin/python3 phase5_extract_selected_features_all_t2_patients.py --resume")
        return

    st.caption("This panel refreshes automatically every 10 seconds. CSV rows are appended after each patient completes.")
    if not wide.empty:
        with st.expander("Current all-features patient CSV", expanded=True):
            show_dataframe(wide, height=360)
    st.subheader("Download current CSV outputs")
    download_frames = [
        ("Download all-features CSV", wide, "phase5_t2_selected_features_wide.csv"),
        ("Download long features CSV", load_csv(PATHS["phase5_long"]), "phase5_t2_selected_features_long.csv"),
        ("Download status CSV", status, "phase5_t2_selected_features_patient_table_status.csv"),
        ("Download coverage CSV", coverage, "phase5_t2_selected_features_coverage.csv"),
        ("Download feature audit CSV", feature_summary, "phase5_t2_feature_coverage_summary.csv"),
        ("Download 10% working features CSV", load_csv(PATHS["phase5_working_features"]), "phase5_t2_working_features_10pct.csv"),
        ("Download sensitivity features CSV", load_csv(PATHS["phase5_sensitivity_features"]), "phase5_t2_sensitivity_features_below_10pct.csv"),
    ]
    download_columns = st.columns(2)
    for index, (label, frame, filename) in enumerate(download_frames):
        with download_columns[index % 2]:
            if not frame.empty:
                st.download_button(
                    label,
                    data=frame.to_csv(index=False).encode("utf-8"),
                    file_name=filename,
                    mime="text/csv",
                    key=f"phase5_live_download_{filename}",
                )
    with st.expander("Current table status and coverage audit"):
        show_dataframe(status, height=420)
        if not status.empty and "table_status" in status.columns:
            st.bar_chart(status["table_status"].value_counts())
        if not coverage.empty:
            show_dataframe(coverage, height=420)
    table_summary = load_csv(PATHS["phase5_table_coverage_summary"])
    if not table_summary.empty:
        with st.expander("Table-level coverage summary"):
            show_dataframe(table_summary, height=420)
    if not feature_summary.empty:
        with st.expander("Feature-level coverage and 10% classification"):
            show_dataframe(feature_summary, height=520)


def phase5_t2_page() -> None:
    st.markdown(
        '<h1 style="font-size: 2.6rem; font-weight: 800; margin-bottom: 0.25rem;">'
        "Phase 5 T2 Feature Extraction"
        + "</h1>",
        unsafe_allow_html=True,
    )
    st.caption("T2-anchored extraction of the manually selected Phase 2 digital features.")
    phase5_t2_live_panel()
    st.markdown("---")
    st.markdown(load_text(PATHS["phase5_protocol"]) or "No Phase 5 protocol available.")


def _phase7_checkpoint_counts(path: Path) -> tuple[int, int]:
    completed = 0
    needs_retry = 0
    if not path.exists():
        return completed, needs_retry
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            state = json.loads(line).get("status", "")
        except json.JSONDecodeError:
            continue
        if state == "completed":
            completed += 1
        elif state == "needs_retry":
            needs_retry += 1
    return completed, needs_retry


@st.fragment(run_every="10s")
def phase7_10day_live_panel() -> None:
    selected = load_csv(PATHS["phase2_selected_features"])
    selected = selected[selected.get("source_table", pd.Series(dtype=str)).astype(str).ne("light")] if not selected.empty else selected
    st.subheader("Phase 7 extraction progress")
    st.caption("The panel refreshes every 10 seconds. Results are appended after each completed patient.")
    for endpoint, label in [("t1", "T1 first available 10-day window"), ("t2", "T2 last available 10-day window")]:
        status = load_csv(PATHS[f"phase7_{endpoint}_status"])
        wide = load_csv(PATHS[f"phase7_{endpoint}_wide"])
        coverage = load_csv(PATHS[f"phase7_{endpoint}_coverage"])
        completed, retry = _phase7_checkpoint_counts(PATHS[f"phase7_{endpoint}_checkpoint"])
        calculated = int(status["table_status"].astype(str).eq("calculated").sum()) if not status.empty and "table_status" in status else 0
        patients = int(status["Subject_ID_D"].nunique()) if not status.empty and "Subject_ID_D" in status else 0
        st.markdown(f"**{label}**")
        metric_row(
            [
                ("Patients with status", patients),
                ("Completed patients", completed),
                ("Calculated tables", calculated),
                ("Patients needing retry", retry),
            ]
        )
        if retry:
            st.warning(f"{retry} patient checkpoints need retry. The outputs remain usable for audit but not for final modeling.")
        if not wide.empty:
            with st.expander(f"Current {endpoint.upper()} wide CSV", expanded=True):
                show_dataframe(wide, height=280)
        with st.expander(f"{endpoint.upper()} status and coverage"):
            show_dataframe(status, height=320)
            show_dataframe(coverage, height=320)
        downloads = [
            (f"Download {endpoint.upper()} wide CSV", wide, f"phase7_{endpoint}_10day_features_wide.csv"),
            (f"Download {endpoint.upper()} long CSV", load_csv(PATHS[f"phase7_{endpoint}_long"]), f"phase7_{endpoint}_10day_features_long.csv"),
            (f"Download {endpoint.upper()} status CSV", status, f"phase7_{endpoint}_10day_patient_table_status.csv"),
        ]
        columns = st.columns(3)
        for index, (label_text, frame, filename) in enumerate(downloads):
            with columns[index]:
                if not frame.empty:
                    st.download_button(label_text, frame.to_csv(index=False).encode("utf-8"), filename, "text/csv", key=f"phase7_{endpoint}_{filename}")


def phase7_10day_page() -> None:
    st.markdown(
        '<h1 style="font-size: 2.6rem; font-weight: 800; margin-bottom: 0.25rem;">'
        "Phase 7 10-Day Window"
        "</h1>",
        unsafe_allow_html=True,
    )
    st.caption("Availability-anchored 10-day T1 and T2 feature extraction using the same selected tables and algorithms as earlier phases.")
    phase7_10day_live_panel()
    comparison_readme = load_text(PATHS["phase7_comparison_readme"])
    feature_comparison = load_csv(PATHS["phase7_feature_comparison"])
    patient_comparison = load_csv(PATHS["phase7_patient_comparison"])
    table_comparison = load_csv(PATHS["phase7_table_comparison"])
    if comparison_readme or not feature_comparison.empty:
        st.markdown("---")
        st.subheader("10-day versus 24-hour data audit")
        st.markdown(comparison_readme)
        with st.expander("Feature-level coverage changes", expanded=True):
            show_dataframe(feature_comparison, height=420)
        with st.expander("Patient-level available feature counts"):
            show_dataframe(patient_comparison, height=360)
        with st.expander("Table-level coverage comparison"):
            show_dataframe(table_comparison, height=420)
    st.markdown("---")
    st.markdown(load_text(PATHS["phase7_protocol"]) or "No Phase 7 protocol available.")


def phase6_decline_page(
    title: str = "Phase 6 T1-to-T2 Decline Phenotyping",
    caption: str = "Exploratory independent T1/T2 digital phenotype estimates; digital change is estimated T2 minus estimated T1.",
) -> None:
    st.markdown(
        '<h1 style="font-size: 2.6rem; font-weight: 800; margin-bottom: 0.25rem;">'
        + title
        + "</h1>",
        unsafe_allow_html=True,
    )
    st.caption(caption)
    st.markdown(load_text(PATHS["phase6_protocol"]) or "No Phase 6 protocol available.")

    patient_predictions = load_csv(PATHS["phase6_patient_predictions"])
    metrics = load_csv(PATHS["phase6_metrics"])
    taxonomy = load_csv(PATHS["phase6_domain_taxonomy"])
    feature_sets = load_csv(PATHS["phase6_feature_sets"])
    if patient_predictions.empty or metrics.empty:
        st.info("Phase 6 model outputs are not available yet.")
        st.code(".venv/bin/python3 phase6_model_t1_t2_decline.py")
        return

    pooled = metrics[metrics["analysis_scope"].astype(str).eq("pooled")].copy()
    st.subheader("Paired cohort and model summary")
    metric_row(
        [
            ("Paired patients", patient_predictions["Subject_ID_D"].nunique()),
            ("Working features", feature_sets["feature_name"].nunique() if not feature_sets.empty else 0),
            ("Domain groups", taxonomy["domain"].nunique() if not taxonomy.empty else 0),
            ("Cross-validation repeats", metrics["repeat"].astype(str).nunique() - (1 if "pooled" in metrics["repeat"].astype(str).unique() else 0)),
        ]
    )

    t1_dataset = load_csv(PATHS["phase4_baseline_dataset"])
    t2_dataset = load_csv(PATHS["phase5_wide"])
    domain_prefixes = {
        "Global": "global",
        "Memory": "memory",
        "Executive function": "ef",
        "Processing speed": "processing_speed",
        "Attention": "attention",
        "Motor": "motor",
    }

    def score_frame(outcome: str, model: str) -> pd.DataFrame:
        prefix = domain_prefixes[outcome]
        t1_col = f"{prefix}_T1"
        t2_col = f"{prefix}_T2"
        if t1_dataset.empty or t1_col not in t1_dataset.columns:
            return pd.DataFrame()
        plot = t1_dataset[["Subject_ID_D", t1_col]].copy()
        plot["t1_score"] = pd.to_numeric(plot[t1_col], errors="coerce")
        plot = plot[plot["t1_score"].notna()].drop(columns=[t1_col])
        if not t2_dataset.empty and t2_col in t2_dataset.columns:
            observed_t2 = t2_dataset[["Subject_ID_D", t2_col]].copy()
            observed_t2["t2_score"] = pd.to_numeric(observed_t2[t2_col], errors="coerce")
            plot = plot.merge(observed_t2[["Subject_ID_D", "t2_score"]], on="Subject_ID_D", how="left")
        else:
            plot["t2_score"] = np.nan
        predictions = patient_predictions[
            (patient_predictions["outcome"].eq(outcome)) & (patient_predictions["model"].eq(model))
        ][["Subject_ID_D", "estimated_T1", "estimated_T2", "estimated_change"]].copy()
        for column in ["estimated_T1", "estimated_T2", "estimated_change"]:
            predictions[column] = pd.to_numeric(predictions[column], errors="coerce")
        plot = plot.merge(predictions, on="Subject_ID_D", how="left")
        plot["estimate_score"] = plot["estimated_T2"]
        plot["t1_estimate_score"] = plot["estimated_T1"]
        plot = plot.sort_values("t1_score").reset_index(drop=True)
        plot["patient_rank"] = range(1, len(plot) + 1)
        plot["observed_change"] = plot["t2_score"] - plot["t1_score"]
        return plot

    def change_chart(
        frame: pd.DataFrame,
        title: str,
        estimate_label: str,
        estimate_color: str = "#2563eb",
        order_label: str = "T1 score",
    ) -> None:
        if frame.empty:
            st.info(f"{title} is not available.")
            return
        plot_long = frame[["patient_rank", "Subject_ID_D", "observed_change", "estimated_change"]].rename(
            columns={"observed_change": "Observed change", "estimated_change": estimate_label}
        ).melt(
            id_vars=["patient_rank", "Subject_ID_D"], var_name="score_type", value_name="change"
        )
        plot_long = plot_long[plot_long["change"].notna()].copy()
        y_min = float(plot_long["change"].min()) - 1
        y_max = float(plot_long["change"].max()) + 1
        chart = (
            alt.Chart(plot_long)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "patient_rank:Q",
                    title=f"Patients ordered by observed {order_label}",
                    axis=alt.Axis(format="d"),
                ),
                y=alt.Y("change:Q", title="Cognitive change (T2 - T1)", scale=alt.Scale(domain=[y_min, y_max])),
                order=alt.Order("patient_rank:Q", sort="ascending"),
                color=alt.Color(
                    "score_type:N",
                    title="Measure",
                    scale=alt.Scale(domain=["Observed change", estimate_label], range=["#111827", estimate_color]),
                ),
                tooltip=[
                    alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                    alt.Tooltip("Subject_ID_D:N", title="Patient ID"),
                    alt.Tooltip("score_type:N", title="Measure"),
                    alt.Tooltip("change:Q", title="Change", format="+.2f"),
                ],
            )
            .properties(title=title, height=380)
        )
        st.altair_chart(chart, use_container_width=True)

    def score_alignment_chart(
        frame: pd.DataFrame,
        title: str,
        estimate_label: str,
        estimate_color: str = "#2563eb",
        order_label: str = "T1 score",
    ) -> None:
        if frame.empty:
            st.info(f"{title} is not available.")
            return
        plot = frame.rename(
            columns={"t1_score": "Observed T1 score", "t2_score": "Observed T2 score", "estimate_score": estimate_label}
        )
        plot_long = plot[["patient_rank", "Subject_ID_D", "Observed T1 score", "Observed T2 score", estimate_label]].melt(
            id_vars=["patient_rank", "Subject_ID_D"], var_name="score_type", value_name="score"
        )
        # Drop unavailable observations from the line input so each category's
        # available dots remain connected across blank patient positions.
        plot_long = plot_long[plot_long["score"].notna()].copy()
        y_min = float(plot_long["score"].min()) - 1
        y_max = float(plot_long["score"].max()) + 1
        chart = (
            alt.Chart(plot_long)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "patient_rank:Q",
                    title=f"Patients ordered by observed {order_label}",
                    axis=alt.Axis(format="d"),
                ),
                y=alt.Y("score:Q", title=f"{title} score", scale=alt.Scale(domain=[y_min, y_max])),
                order=alt.Order("patient_rank:Q", sort="ascending"),
                color=alt.Color(
                    "score_type:N",
                    title="Measure",
                    scale=alt.Scale(
                        domain=["Observed T1 score", "Observed T2 score", estimate_label],
                        range=["#111827", "#dc2626", estimate_color],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                    alt.Tooltip("Subject_ID_D:N", title="Patient ID"),
                    alt.Tooltip("score_type:N", title="Measure"),
                    alt.Tooltip("score:Q", title="Score", format=".2f"),
                ],
            )
            .properties(title=f"{title}: observed T1 and T2 scores", height=380)
        )
        st.altair_chart(chart, use_container_width=True)

    def t2_estimate_chart(
        frame: pd.DataFrame,
        title: str,
        estimate_label: str,
        estimate_color: str = "#2563eb",
        order_label: str = "T1 score",
    ) -> None:
        if frame.empty:
            st.info(f"{title} is not available.")
            return
        plot = frame.rename(
            columns={
                "t2_score": "Observed T2 score",
                "estimate_score": estimate_label,
                "t1_estimate_score": "Estimated T1 score",
            }
        )
        plot_long = plot[["patient_rank", "Subject_ID_D", "Observed T2 score", estimate_label, "Estimated T1 score"]].melt(
            id_vars=["patient_rank", "Subject_ID_D"], var_name="score_type", value_name="score"
        )
        plot_long = plot_long[plot_long["score"].notna()].copy()
        y_min = float(plot_long["score"].min()) - 1
        y_max = float(plot_long["score"].max()) + 1
        chart = (
            alt.Chart(plot_long)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "patient_rank:Q",
                    title=f"Patients ordered by observed {order_label}",
                    axis=alt.Axis(format="d"),
                ),
                y=alt.Y("score:Q", title=f"{title} T2 score", scale=alt.Scale(domain=[y_min, y_max])),
                order=alt.Order("patient_rank:Q", sort="ascending"),
                color=alt.Color(
                    "score_type:N",
                    title="Measure",
                    scale=alt.Scale(
                        domain=["Observed T2 score", estimate_label, "Estimated T1 score"],
                        range=["#dc2626", estimate_color, "#111827"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("patient_rank:Q", title="Patient order", format="d"),
                    alt.Tooltip("Subject_ID_D:N", title="Patient ID"),
                    alt.Tooltip("score_type:N", title="Measure"),
                    alt.Tooltip("score:Q", title="T2 score", format=".2f"),
                ],
            )
            .properties(title=f"{title}: observed versus estimated T2", height=360)
        )
        st.altair_chart(chart, use_container_width=True)

    st.subheader("Outcome 2: Global T1-to-T2 digital phenotype")
    global_frame = score_frame("Global", "working_10pct_independent_t2_ridge")
    st.markdown("**1. Observed T1, T2, and estimated T2 scores in the same patient order**")
    score_alignment_chart(global_frame, "Global cognitive", "Working-feature digital T2 estimate", order_label="Global T1 score")
    st.markdown("**2. Observed T2 versus estimated T2 only**")
    t2_estimate_chart(global_frame, "Global cognitive", "Working-feature digital T2 estimate", order_label="Global T1 score")
    st.markdown("**3. Observed versus estimated cognitive change**")
    change_chart(
        global_frame,
        "Global cognitive change: working 10% feature model",
        "Working-feature change estimate",
        order_label="Global T1 score",
    )

    st.subheader("Model fit comparison")
    global_metrics = pooled[pooled["outcome"].eq("Global")][["model", "n_predictions", "rmse", "mae", "r2"]].drop_duplicates()
    show_dataframe(global_metrics, height=220)

    st.subheader("Cognitive domain decline models")
    st.caption("Each domain uses the relevant Phase 4 feature-group union after the same T2 10% coverage filter. Features may appear in multiple domain groups.")
    domain_colors = {
        "Memory": "#2563eb",
        "Executive function": "#16a34a",
        "Processing speed": "#d97706",
        "Attention": "#9333ea",
        "Motor": "#0891b2",
    }
    for domain in ["Memory", "Executive function", "Processing speed", "Attention", "Motor"]:
        domain_frame = score_frame(domain, f"{domain}_domain_independent_t2_ridge")
        st.markdown(f"**{domain}**")
        st.markdown("**1. Observed T1, T2, and estimated T2 scores in the same patient order**")
        score_alignment_chart(
            domain_frame,
            domain,
            "Domain-group digital T2 estimate",
            domain_colors[domain],
            order_label=f"{domain} T1 score",
        )
        st.markdown("**2. Observed T2 versus estimated T2 only**")
        t2_estimate_chart(
            domain_frame,
            domain,
            "Domain-group digital T2 estimate",
            domain_colors[domain],
            order_label=f"{domain} T1 score",
        )
        st.markdown("**3. Observed versus estimated cognitive change**")
        change_chart(
            domain_frame,
            f"{domain} change: domain feature-group model",
            "Domain-group change estimate",
            domain_colors[domain],
            order_label=f"{domain} T1 score",
        )
        domain_features = taxonomy[taxonomy["domain"].eq(domain)] if not taxonomy.empty else pd.DataFrame()
        if not domain_features.empty:
            with st.expander(f"{domain} feature group"):
                show_dataframe(domain_features, height=220)
        domain_metrics = pooled[pooled["outcome"].eq(domain)][["model", "n_predictions", "rmse", "mae", "r2"]].drop_duplicates()
        show_dataframe(domain_metrics, height=170)

    with st.expander("Phase 6 feature-set audit"):
        show_dataframe(feature_sets, height=420)
    with st.expander("Download Phase 6 outputs"):
        for path_key, filename in [
            ("phase6_patient_predictions", "phase6_t1_t2_decline_patient_predictions.csv"),
            ("phase6_metrics", "phase6_t1_t2_decline_metrics.csv"),
            ("phase6_feature_sets", "phase6_t1_t2_decline_feature_sets.csv"),
        ]:
            frame = load_csv(PATHS[path_key])
            if not frame.empty:
                st.download_button(f"Download {filename}", frame.to_csv(index=False).encode("utf-8"), filename, "text/csv", key=f"phase6_{filename}")


def phase6_10day_decline_page() -> None:
    root = ROOT / "output/analysis_candidates/phase6_10day_t1_t2_decline"
    overrides = {
        "phase6_protocol": ROOT / "PHASE6_10_DAY_DECLINE_PROTOCOL.md",
        "phase6_patient_predictions": root / "phase6_10day_t1_t2_decline_patient_predictions.csv",
        "phase6_metrics": root / "phase6_10day_t1_t2_decline_metrics.csv",
        "phase6_feature_sets": root / "phase6_10day_t1_t2_decline_feature_sets.csv",
        "phase6_domain_taxonomy": root / "phase6_10day_t1_t2_decline_domain_taxonomy.csv",
        "phase4_baseline_dataset": ROOT / "output/analysis_candidates/phase4_10day_t1_baseline/phase4_10day_t1_baseline_patient_dataset.csv",
        "phase5_wide": ROOT / "output/analysis_candidates/phase7_10day_window/t2/phase7_t2_10day_features_wide.csv",
    }
    _render_with_path_overrides(
        overrides,
        lambda: phase6_decline_page(
            title="Phase 6 10-Day T1-to-T2 Decline Phenotyping",
            caption="Phase 6-equivalent independent T1/T2 estimates using the new 10-day T1 and T2 data.",
        ),
    )


def rd_page() -> None:
    st.title("R&D")
    st.caption("Protocol experiments that test alternative acquisition rules without overwriting Phase 3 outputs.")

    calls_long = load_csv(PATHS["rd_calls_t1_week_long"])
    calls_wide = load_csv(PATHS["rd_calls_t1_week_wide"])
    calls_status = load_csv(PATHS["rd_calls_t1_week_status"])
    calls_2week_long = load_csv(PATHS["rd_calls_t1_2week_long"])
    calls_2week_wide = load_csv(PATHS["rd_calls_t1_2week_wide"])
    calls_2week_status = load_csv(PATHS["rd_calls_t1_2week_status"])
    calls_30day_long = load_csv(PATHS["rd_calls_t1_30day_long"])
    calls_30day_wide = load_csv(PATHS["rd_calls_t1_30day_wide"])
    calls_30day_status = load_csv(PATHS["rd_calls_t1_30day_status"])
    bluetooth_week_long = load_csv(PATHS["rd_bluetooth_t1_week_long"])
    bluetooth_week_wide = load_csv(PATHS["rd_bluetooth_t1_week_wide"])
    bluetooth_week_status = load_csv(PATHS["rd_bluetooth_t1_week_status"])
    bluetooth_30day_long = load_csv(PATHS["rd_bluetooth_t1_30day_long"])
    bluetooth_30day_wide = load_csv(PATHS["rd_bluetooth_t1_30day_wide"])
    bluetooth_30day_status = load_csv(PATHS["rd_bluetooth_t1_30day_status"])
    strict_long = load_csv(PATHS["phase3_all_t1_long"])
    strict_status = load_csv(PATHS["phase3_all_t1_status"])

    st.subheader("Calls: Window-Length R&D")
    st.markdown(
        """
        This pilot tests a relaxed acquisition rule for sparse event tables:
        use a longer post-T1 window and calculate call features if any `calls` rows exist.

        This is separate from the strict Phase 3 rule, which requires a protocol-valid 24-hour span.
        """
    )

    if (
        calls_long.empty
        and calls_status.empty
        and calls_2week_long.empty
        and calls_2week_status.empty
        and calls_30day_long.empty
        and calls_30day_status.empty
    ):
        st.info("R&D calls pilot outputs are not available yet.")
        st.code(".venv/bin/python3 phase3_rd_calls_t1_week_any_data_pilot.py")
        st.code(".venv/bin/python3 phase3_rd_calls_t1_2week_any_data_pilot.py")
        st.code(".venv/bin/python3 phase3_rd_calls_t1_30day_any_data_pilot.py")
        return

    rd_patients = calls_status["Subject_ID_D"].nunique() if "Subject_ID_D" in calls_status.columns else 0
    rd_calculated_patients = (
        int(calls_status["table_status"].astype(str).eq("calculated").sum())
        if "table_status" in calls_status.columns
        else 0
    )
    rd_calculated_features = (
        int(calls_long["feature_status"].astype(str).eq("calculated").sum())
        if "feature_status" in calls_long.columns
        else 0
    )
    rd_2week_patients = calls_2week_status["Subject_ID_D"].nunique() if "Subject_ID_D" in calls_2week_status.columns else 0
    rd_2week_calculated_patients = (
        int(calls_2week_status["table_status"].astype(str).eq("calculated").sum())
        if "table_status" in calls_2week_status.columns
        else 0
    )
    rd_2week_calculated_features = (
        int(calls_2week_long["feature_status"].astype(str).eq("calculated").sum())
        if "feature_status" in calls_2week_long.columns
        else 0
    )
    rd_30day_patients = calls_30day_status["Subject_ID_D"].nunique() if "Subject_ID_D" in calls_30day_status.columns else 0
    rd_30day_calculated_patients = (
        int(calls_30day_status["table_status"].astype(str).eq("calculated").sum())
        if "table_status" in calls_30day_status.columns
        else 0
    )
    rd_30day_calculated_features = (
        int(calls_30day_long["feature_status"].astype(str).eq("calculated").sum())
        if "feature_status" in calls_30day_long.columns
        else 0
    )

    strict_calls = pd.DataFrame()
    if not strict_long.empty and "table_name" in strict_long.columns:
        strict_calls = strict_long[strict_long["table_name"].astype(str) == "calls"].copy()
    strict_call_patients = (
        int(
            strict_status[
                (strict_status.get("table_name", pd.Series(dtype=str)).astype(str) == "calls")
                & (strict_status.get("table_status", pd.Series(dtype=str)).astype(str) == "calculated")
            ].shape[0]
        )
        if not strict_status.empty and {"table_name", "table_status"}.issubset(strict_status.columns)
        else 0
    )
    strict_call_feature_values = (
        int(strict_calls["feature_status"].astype(str).eq("calculated").sum())
        if not strict_calls.empty and "feature_status" in strict_calls.columns
        else 0
    )

    metric_row(
        [
            ("Patients tested", max(rd_patients, rd_2week_patients, rd_30day_patients)),
            ("Strict calls patients", strict_call_patients),
            ("1-week calls patients", rd_calculated_patients),
            ("2-week calls patients", rd_2week_calculated_patients),
            ("30-day calls patients", rd_30day_calculated_patients),
            ("30-day call values", rd_30day_calculated_features),
        ]
    )

    call_tabs = st.tabs(
        [
            "Comparison",
            "1-Week Long",
            "1-Week Wide",
            "1-Week Status",
            "2-Week Long",
            "2-Week Wide",
            "2-Week Status",
            "30-Day Long",
            "30-Day Wide",
            "30-Day Status",
            "README",
        ]
    )
    with call_tabs[0]:
        comparison = pd.DataFrame(
            [
                {
                    "rule": "strict_phase3_24h_valid_span",
                    "patients_with_calculated_calls": strict_call_patients,
                    "calculated_call_feature_values": strict_call_feature_values,
                    "window": "first valid 24h span inside T1 week",
                },
                {
                    "rule": "rd_t1_week_any_calls_data",
                    "patients_with_calculated_calls": rd_calculated_patients,
                    "calculated_call_feature_values": rd_calculated_features,
                    "window": "entire first week after T1 if any rows exist",
                },
                {
                    "rule": "rd_t1_2week_any_calls_data",
                    "patients_with_calculated_calls": rd_2week_calculated_patients,
                    "calculated_call_feature_values": rd_2week_calculated_features,
                    "window": "first 14 days after T1 if any rows exist",
                },
                {
                    "rule": "rd_t1_30day_any_calls_data",
                    "patients_with_calculated_calls": rd_30day_calculated_patients,
                    "calculated_call_feature_values": rd_30day_calculated_features,
                    "window": "first 30 days after T1 if any rows exist",
                },
            ]
        )
        show_dataframe(comparison, height=160)
        st.bar_chart(comparison.set_index("rule")["patients_with_calculated_calls"])

        if not calls_long.empty and {"feature_name", "feature_status", "Subject_ID_D"}.issubset(calls_long.columns):
            feature_summary = (
                calls_long.assign(calculated=calls_long["feature_status"].astype(str).eq("calculated"))
                .groupby("feature_name", dropna=False)
                .agg(calculated_patients=("calculated", "sum"), total_patients=("Subject_ID_D", "nunique"))
                .reset_index()
            )
            feature_summary["calculated_percent"] = (
                100 * feature_summary["calculated_patients"] / feature_summary["total_patients"]
            ).round(1)
            st.subheader("R&D Calls Feature Availability")
            show_dataframe(feature_summary, height=260)

    with call_tabs[1]:
        show_dataframe(calls_long, height=560)
    with call_tabs[2]:
        show_dataframe(calls_wide, height=560)
    with call_tabs[3]:
        show_dataframe(calls_status, height=560)
    with call_tabs[4]:
        show_dataframe(calls_2week_long, height=560)
    with call_tabs[5]:
        show_dataframe(calls_2week_wide, height=560)
    with call_tabs[6]:
        show_dataframe(calls_2week_status, height=560)
    with call_tabs[7]:
        show_dataframe(calls_30day_long, height=560)
    with call_tabs[8]:
        show_dataframe(calls_30day_wide, height=560)
    with call_tabs[9]:
        show_dataframe(calls_30day_status, height=560)
    with call_tabs[10]:
        st.markdown("### 1-Week Pilot")
        st.markdown(load_text(PATHS["rd_calls_t1_week_readme"]) or "No 1-week README available yet.")
        st.markdown("### 2-Week Pilot")
        st.markdown(load_text(PATHS["rd_calls_t1_2week_readme"]) or "No 2-week README available yet.")
        st.markdown("### 30-Day Pilot")
        st.markdown(load_text(PATHS["rd_calls_t1_30day_readme"]) or "No 30-day README available yet.")

    st.divider()
    st.subheader("Bluetooth: T1-Week and 30-Day Any-Data Pilots")
    st.markdown(
        """
        This pilot tests whether Bluetooth coverage improves when the first T1 week is used directly,
        instead of requiring a strict protocol-valid 24-hour span.
        """
    )

    if bluetooth_week_long.empty and bluetooth_week_status.empty and bluetooth_30day_long.empty and bluetooth_30day_status.empty:
        st.info("Bluetooth R&D pilot output is not available yet.")
        st.code(".venv/bin/python3 phase3_rd_bluetooth_t1_week_any_data_pilot.py")
        st.code(".venv/bin/python3 phase3_rd_bluetooth_t1_30day_any_data_pilot.py")
    else:
        strict_bluetooth = pd.DataFrame()
        if not strict_long.empty and "table_name" in strict_long.columns:
            strict_bluetooth = strict_long[strict_long["table_name"].astype(str) == "bluetooth"].copy()
        strict_bluetooth_patients = (
            int(
                strict_status[
                    (strict_status.get("table_name", pd.Series(dtype=str)).astype(str) == "bluetooth")
                    & (strict_status.get("table_status", pd.Series(dtype=str)).astype(str) == "calculated")
                ].shape[0]
            )
            if not strict_status.empty and {"table_name", "table_status"}.issubset(strict_status.columns)
            else 0
        )
        strict_bluetooth_values = (
            int(strict_bluetooth["feature_status"].astype(str).eq("calculated").sum())
            if not strict_bluetooth.empty and "feature_status" in strict_bluetooth.columns
            else 0
        )
        bluetooth_week_patients = (
            int(bluetooth_week_status["table_status"].astype(str).eq("calculated").sum())
            if "table_status" in bluetooth_week_status.columns
            else 0
        )
        bluetooth_week_values = (
            int(bluetooth_week_long["feature_status"].astype(str).eq("calculated").sum())
            if "feature_status" in bluetooth_week_long.columns
            else 0
        )
        bluetooth_30day_patients = (
            int(bluetooth_30day_status["table_status"].astype(str).eq("calculated").sum())
            if "table_status" in bluetooth_30day_status.columns
            else 0
        )
        bluetooth_30day_values = (
            int(bluetooth_30day_long["feature_status"].astype(str).eq("calculated").sum())
            if "feature_status" in bluetooth_30day_long.columns
            else 0
        )

        metric_row(
            [
                ("Strict Bluetooth patients", strict_bluetooth_patients),
                ("1-week Bluetooth patients", bluetooth_week_patients),
                ("30-day Bluetooth patients", bluetooth_30day_patients),
                ("1-week Bluetooth values", bluetooth_week_values),
                ("30-day Bluetooth values", bluetooth_30day_values),
            ]
        )

        bluetooth_tabs = st.tabs(
            [
                "Comparison",
                "1-Week Long",
                "1-Week Wide",
                "1-Week Status",
                "30-Day Long",
                "30-Day Wide",
                "30-Day Status",
                "README",
            ]
        )
        with bluetooth_tabs[0]:
            bluetooth_comparison = pd.DataFrame(
                [
                    {
                        "rule": "strict_phase3_24h_valid_span",
                        "patients_with_calculated_bluetooth": strict_bluetooth_patients,
                        "calculated_bluetooth_feature_values": strict_bluetooth_values,
                        "window": "first valid 24h span inside T1 week",
                    },
                    {
                        "rule": "rd_t1_week_any_bluetooth_data",
                        "patients_with_calculated_bluetooth": bluetooth_week_patients,
                        "calculated_bluetooth_feature_values": bluetooth_week_values,
                        "window": "entire first week after T1 if any rows exist",
                    },
                    {
                        "rule": "rd_t1_30day_any_bluetooth_data",
                        "patients_with_calculated_bluetooth": bluetooth_30day_patients,
                        "calculated_bluetooth_feature_values": bluetooth_30day_values,
                        "window": "first 30 days after T1 if any rows exist",
                    },
                ]
            )
            show_dataframe(bluetooth_comparison, height=160)
            st.bar_chart(bluetooth_comparison.set_index("rule")["patients_with_calculated_bluetooth"])

            if not bluetooth_week_long.empty and {"feature_name", "feature_status", "Subject_ID_D"}.issubset(
                bluetooth_week_long.columns
            ):
                feature_summary = (
                    bluetooth_week_long.assign(
                        calculated=bluetooth_week_long["feature_status"].astype(str).eq("calculated")
                    )
                    .groupby("feature_name", dropna=False)
                    .agg(calculated_patients=("calculated", "sum"), total_patients=("Subject_ID_D", "nunique"))
                    .reset_index()
                )
                feature_summary["calculated_percent"] = (
                    100 * feature_summary["calculated_patients"] / feature_summary["total_patients"]
                ).round(1)
                st.subheader("Bluetooth Feature Availability")
                show_dataframe(feature_summary, height=220)
        with bluetooth_tabs[1]:
            show_dataframe(bluetooth_week_long, height=560)
        with bluetooth_tabs[2]:
            show_dataframe(bluetooth_week_wide, height=560)
        with bluetooth_tabs[3]:
            show_dataframe(bluetooth_week_status, height=560)
        with bluetooth_tabs[4]:
            show_dataframe(bluetooth_30day_long, height=560)
        with bluetooth_tabs[5]:
            show_dataframe(bluetooth_30day_wide, height=560)
        with bluetooth_tabs[6]:
            show_dataframe(bluetooth_30day_status, height=560)
        with bluetooth_tabs[7]:
            st.markdown("### 1-Week Pilot")
            st.markdown(load_text(PATHS["rd_bluetooth_t1_week_readme"]) or "No Bluetooth README available yet.")
            st.markdown("### 30-Day Pilot")
            st.markdown(load_text(PATHS["rd_bluetooth_t1_30day_readme"]) or "No Bluetooth 30-day README available yet.")


def neurotrax_page() -> None:
    st.title("NeuroTrax Columns and Analysis Targets")
    candidates = load_csv(PATHS["cognitive_candidates"])
    master = load_csv(PATHS["cognitive_master"])

    if candidates.empty and master.empty:
        st.info("NeuroTrax files are not available.")
        return

    st.subheader("Main Columns for Future Analysis")
    main_cols = [
        "Subject_ID_N",
        "Subject_ID_D",
        "age",
        "Gender (1=M, 2=F)",
        "Education (years)",
        "T1_date_iso",
        "T2_date_iso",
        "global_T1",
        "global_T2",
        "global_delta",
        "memory_T1",
        "memory_T2",
        "memory_delta",
        "ef_T1",
        "ef_T2",
        "ef_delta",
        "attention_T1",
        "attention_T2",
        "attention_delta",
        "processing_speed_T1",
        "processing_speed_T2",
        "processing_speed_delta",
        "verbal_T1",
        "verbal_T2",
        "verbal_delta",
        "motor_T1",
        "motor_T2",
        "motor_delta",
        "iq_T1",
        "iq_T2",
        "iq_delta",
    ]
    available_main = [c for c in main_cols if c in candidates.columns]
    st.dataframe(pd.DataFrame({"column_name": available_main}), use_container_width=True, height=260)

    st.subheader("Candidate Cognitive Table Preview")
    show_dataframe(candidates[available_main] if available_main else candidates, height=420)

    st.subheader("All NeuroTrax Master Headers")
    query = st.text_input("Filter NeuroTrax headers", "")
    headers = master.columns.astype(str).tolist()
    if query:
        headers = [h for h in headers if query.lower() in h.lower()]
    show_dataframe(pd.DataFrame({"column_name": headers}), height=520)


def rich_wide_page() -> None:
    st.title("Rich Phase 1 Wide Table")
    rich = load_csv(PATHS["rich_wide"])
    if rich.empty:
        st.info("Rich wide table is not available.")
        return

    metric_row(
        [
            ("Rows", rich.shape[0]),
            ("Columns", rich.shape[1]),
            ("Subjects", rich["Subject_ID_D"].nunique() if "Subject_ID_D" in rich else 0),
        ]
    )

    st.subheader("Column Search")
    query = st.text_input("Filter columns", "")
    cols = rich.columns.tolist()
    if query:
        cols = [c for c in cols if query.lower() in c.lower()]
    st.write(f"{len(cols)} matching columns")
    st.code("\n".join(cols[:250]))

    st.subheader("Table Preview")
    show_cols = st.multiselect("Columns to display", rich.columns.tolist(), default=rich.columns[:12].tolist())
    if show_cols:
        show_dataframe(rich[show_cols], height=480)


def samples_page() -> None:
    st.title("Manual SQL Samples")
    sample_rows = load_csv(PATHS["sample_rows"])
    sample_summary = load_csv(PATHS["sample_summary"])

    st.caption("Manual-review samples only. These are not feature extraction outputs.")
    show_dataframe(sample_summary, height=260)

    if sample_rows.empty:
        st.info("No sample rows are available.")
        return

    table_options = ["All"] + sorted(sample_rows["table_name"].dropna().astype(str).unique().tolist())
    selected_table = st.selectbox("Sample table", table_options)
    view = sample_rows if selected_table == "All" else sample_rows[sample_rows["table_name"].astype(str) == selected_table]
    show_dataframe(view, height=520)


def files_page() -> None:
    st.title("Project Files")
    rows = []
    for name, path in PATHS.items():
        rows.append(
            {
                "name": name,
                "status": file_status(path),
                "path": str(path.relative_to(ROOT)),
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
        )
    show_dataframe(pd.DataFrame(rows), height=520)


PAGES = {
    "Overview": overview_page,
    "Phase 1 Profiles": phase1_profiles_page,
    "Phase 1 Change": phase1_change_page,
    "NeuroTrax Columns": neurotrax_page,
    "Rich Wide Table": rich_wide_page,
    "Phase 2 Tables": phase2_tables_page,
    "Phase 3 algorithm implementation": phase3_algorithm_page,
    "Phase 4 T1 Baseline": phase4_baseline_page,
    "Phase 4 10-Day T1 Baseline": phase4_10day_page,
    "Other Models": other_models_page,
    "Suggestions": suggestions_page,
    "Phase 5 T2 Extraction": phase5_t2_page,
    "Phase 7 10-Day Window": phase7_10day_page,
    "Phase 6 T1-T2 Decline": phase6_decline_page,
    "Phase 6 10-Day T1-T2 Decline": phase6_10day_decline_page,
    "Result Explorer": result_explorer_page,
    "R&D": rd_page,
    "SQL Samples": samples_page,
    "Files": files_page,
}


def main() -> None:
    st.sidebar.title("NeuroTrax-SensorDB")
    st.sidebar.markdown(
        """
        <style>
        [data-testid="stSidebar"] [role="radiogroup"] > label:nth-child(8) p {
            font-size: 1.18rem !important;
            font-weight: 800 !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label:nth-child(8) {
            padding-top: 0.18rem;
            padding-bottom: 0.18rem;
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label:nth-child(9) p {
            font-size: 1.18rem !important;
            font-weight: 800 !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label:nth-child(9) {
            padding-top: 0.18rem;
            padding-bottom: 0.18rem;
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label:nth-child(15) p,
        [data-testid="stSidebar"] [role="radiogroup"] > label:nth-child(16) p {
            font-size: 1.18rem !important;
            font-weight: 800 !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] > label:nth-child(15),
        [data-testid="stSidebar"] [role="radiogroup"] > label:nth-child(16) {
            padding-top: 0.18rem;
            padding-bottom: 0.18rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    page = st.sidebar.radio("View", list(PAGES.keys()))
    st.sidebar.divider()
    st.sidebar.caption("Local dashboard over existing project outputs.")
    st.sidebar.caption("No SQL queries are executed by this app.")
    PAGES[page]()


if __name__ == "__main__":
    main()
