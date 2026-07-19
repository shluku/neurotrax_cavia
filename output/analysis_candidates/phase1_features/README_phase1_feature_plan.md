# Phase 1 Feature Plan (Pre-Extraction)

## Executive Summary
- This is pre-extraction planning only.
- Baseline phenotype is possible for 8/10 subjects.
- Early-vs-late change is currently possible for 2/10 subjects (024 and 077).
- Missing data must not be interpreted as zero activity.
- aware_log is data-quality denominator, not direct phenotype.

## Table-by-Table Review
### screen
- Role: core_phenotype
- Coverage readiness: high_priority_feature_candidate
- Likely measures: Screen interaction/state events; proxy for phone engagement timing.
- JSON keys found: device_id;screen_status;timestamp
- Important keys: screen_status;timestamp;device_id
- Proposed features: screen_event_count, active_screen_days, night_screen_event_count, screen_events_per_active_day
- Interpretation warnings: Screen state semantics can vary by OS/device; not equal to active cognition.
- Ready for extraction: yes

### applications_foreground
- Role: core_phenotype
- Coverage readiness: high_priority_feature_candidate
- Likely measures: Foreground app events; proxy for app-use behavior and routine.
- JSON keys found: application_name;device_id;is_system_app;package_name;timestamp
- Important keys: package_name;application_name;timestamp
- Proposed features: app_foreground_event_count, active_app_days, unique_foreground_apps, app_use_diversity
- Interpretation warnings: Foreground does not equal intentional use; system/app noise present.
- Ready for extraction: yes

### keyboard
- Role: core_phenotype
- Coverage readiness: high_priority_feature_candidate
- Likely measures: Keyboard interactions; proxy for active text input behavior.
- JSON keys found: before_text;current_text;device_id;is_password;package_name;timestamp
- Important keys: timestamp;current_text;before_text;is_password
- Proposed features: keyboard_event_count, active_keyboard_days, keyboard_events_per_active_day
- Interpretation warnings: Keyboard provider/settings affect logs; privacy-safe aggregation only.
- Ready for extraction: yes

### touch
- Role: core_phenotype
- Coverage readiness: baseline_only_candidate
- Likely measures: Touch interactions; broad proxy for phone interaction volume.
- JSON keys found: device_id;scroll_from_index;scroll_items;scroll_to_index;timestamp;touch_action;touch_action_text;touch_app
- Important keys: timestamp;touch_action;touch_app
- Proposed features: touch_event_count, active_touch_days, touch_events_per_active_day
- Interpretation warnings: Touch event granularity differs across devices/apps.
- Ready for extraction: yes

### plugin_google_activity_recognition
- Role: core_phenotype
- Coverage readiness: high_priority_feature_candidate
- Likely measures: Model-derived physical activity states over time.
- JSON keys found: activities;activity_name;activity_type;confidence;device_id;timestamp
- Important keys: activity_type;activity_name;activities;timestamp
- Proposed features: activity_event_count, active_activity_days, still_event_count, walking_event_count, in_vehicle_event_count, activity_diversity
- Interpretation warnings: Activity labels are classifier outputs and device/model dependent.
- Ready for extraction: yes

### gsm
- Role: optional_context
- Coverage readiness: baseline_only_candidate
- Likely measures: Cellular context and tower-level mobility proxy.
- JSON keys found: bit_error_rate;cid;device_id;lac;psc;signal_strength;timestamp
- Important keys: timestamp;cid;lac;psc;signal_strength
- Proposed features: gsm_event_count, gsm_active_days, gsm_cellular_context_diversity
- Interpretation warnings: Network infrastructure differences can bias comparability.
- Ready for extraction: yes

### gsm_neighbor
- Role: optional_context
- Coverage readiness: baseline_only_candidate
- Likely measures: Cellular context and tower-level mobility proxy.
- JSON keys found: cid;device_id;lac;psc;signal_strength;timestamp
- Important keys: timestamp;cid;lac;psc;signal_strength
- Proposed features: gsm_neighbor_event_count, gsm_neighbor_active_days, gsm_neighbor_cellular_context_diversity
- Interpretation warnings: Network infrastructure differences can bias comparability.
- Ready for extraction: yes

### telephony
- Role: optional_context
- Coverage readiness: baseline_only_candidate
- Likely measures: Telephony/network state context, not direct behavior alone.
- JSON keys found: data_enabled;device_id;imei_meid_esn;line_number;network_country_iso_mcc;network_operator_code;network_operator_name;network_type;phone_type;sim_operator_code;sim_operator_name;sim_serial;sim_state;software_version;subscriber_id;timestamp
- Important keys: timestamp;network_type;sim_state;phone_type
- Proposed features: telephony_event_count, active_social_days
- Interpretation warnings: More state than action; combine with behavioral tables.
- Ready for extraction: yes

### messages
- Role: optional_context
- Coverage readiness: limited_candidate
- Likely measures: Messaging events; proxy for social communication activity.
- JSON keys found: device_id;message_type;timestamp;trace
- Important keys: timestamp;message_type;trace
- Proposed features: message_event_count, active_social_days
- Interpretation warnings: Sparse coverage in current top10; direction/type may be limited.
- Ready for extraction: yes

### aware_log
- Role: data_quality_denominator
- Coverage readiness: high_priority_feature_candidate
- Likely measures: System/data-sync logs used as denominator and quality flag source.
- JSON keys found: device_id;log_message;timestamp
- Important keys: timestamp;log_message
- Proposed features: aware_log_rows, aware_log_active_days, data_logging_coverage_days, system_log_density
- Interpretation warnings: Not a phenotype endpoint; interpret only as data quality context.
- Ready for extraction: yes

## Phenotype vs Data-Quality Distinction
- Phenotype tables: screen, applications_foreground, keyboard, touch, plugin_google_activity_recognition, gsm, gsm_neighbor, telephony, messages.
- Data-quality table: aware_log only.