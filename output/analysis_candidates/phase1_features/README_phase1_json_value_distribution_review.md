# Phase 1 JSON Value Distribution Review

Interpretation/QC review only. No SQL queried. No new feature extraction performed.

## Table Checks
- screen: state key present (`screen_status`) -> state-aware features possible with code validation.
- applications_foreground: app identifier keys present (`package_name`, `application_name`).
- plugin_google_activity_recognition: activity label structures present (`activity_name`, `activity_type`, `activities`).
- messages/telephony: type/state keys present but code semantics need validation.
- gsm/gsm_neighbor: tower/context identifiers present (`cid`, `lac`, `psc`).
- aware_log: system/log messages present; remains data-quality only.

## Safe Keys
- applications_foreground.application_name, applications_foreground.device_id, applications_foreground.is_system_app, applications_foreground.package_name, applications_foreground.timestamp, aware_log.log_message, aware_log.timestamp, gsm.cid, gsm.lac, gsm.psc, gsm.signal_strength, gsm.timestamp, gsm_neighbor.cid, gsm_neighbor.lac, gsm_neighbor.psc, gsm_neighbor.signal_strength, gsm_neighbor.timestamp, keyboard.package_name, keyboard.timestamp, messages.message_type, messages.timestamp, plugin_google_activity_recognition.activities, plugin_google_activity_recognition.activity_name, plugin_google_activity_recognition.activity_type, plugin_google_activity_recognition.confidence, plugin_google_activity_recognition.timestamp, screen.device_id, screen.screen_status, screen.timestamp, telephony.data_enabled, telephony.network_operator_code, telephony.network_operator_name, telephony.network_type, telephony.phone_type, telephony.sim_state, telephony.timestamp, touch.timestamp, touch.touch_action, touch.touch_app

## Manual Review Keys
- aware_log.device_id, gsm.bit_error_rate, gsm.device_id, gsm_neighbor.device_id, keyboard.before_text, keyboard.current_text, keyboard.device_id, keyboard.is_password, messages.device_id, messages.trace, plugin_google_activity_recognition.device_id, telephony.device_id, telephony.imei_meid_esn, telephony.line_number, telephony.network_country_iso_mcc, telephony.sim_operator_code, telephony.sim_operator_name, telephony.sim_serial, telephony.software_version, telephony.subscriber_id, touch.device_id, touch.scroll_from_index, touch.scroll_items, touch.scroll_to_index, touch.touch_action_text

## Feature Plan Adjustments
### Downgrade/Keep Cautious
- messages: incoming/outgoing features require explicit code mapping for message_type
- aware_log: keep as data-quality denominator only, not behavioral phenotype
### Upgrade Candidates
- screen: can upgrade to state-aware features (e.g., per-status counts) after code mapping validation
- applications_foreground: unique app and app diversity features are supported
- activity_recognition: specific still/walking/in_vehicle features are supported
- telephony: context-state features can be used (network/sim state), not direct social behavior