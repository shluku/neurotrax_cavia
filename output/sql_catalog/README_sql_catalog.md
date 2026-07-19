# SQL Catalog Discovery

This is a lightweight discovery run (no feature extraction, no large raw download).

## Databases/Schemas Found
- information_schema: tables=81, rows_est=0, total_size_mb=0.0
- performance_schema: tables=8, rows_est=133623, total_size_mb=0.0
- sensordata: tables=44, rows_est=17156126863, total_size_mb=7026543.0156

## Largest Tables (approx)
- rotation: total_size_mb=1655389.9688, rows_est=3832771332
- accelerometer: total_size_mb=1597213.9688, rows_est=3899894130
- gyroscope: total_size_mb=1550460.9688, rows_est=3758319628
- gravity: total_size_mb=1549821.9844, rows_est=3753182543
- light: total_size_mb=261052.9688, rows_est=813602413
- linear_accelerometer: total_size_mb=211844.0, rows_est=539195233
- magnetometer: total_size_mb=134914.0, rows_est=346894235
- proximity: total_size_mb=28957.9844, rows_est=106477137
- aware_log: total_size_mb=18394.7969, rows_est=55096302
- barometer: total_size_mb=7706.0, rows_est=25763375
- touch: total_size_mb=1990.9844, rows_est=4207084
- keyboard: total_size_mb=1819.0, rows_est=3716016
- wifi: total_size_mb=1427.0, rows_est=3507726
- gsm_neighbor: total_size_mb=1280.0, rows_est=3576689
- plugin_google_activity_recognition: total_size_mb=1193.0, rows_est=2481335
- applications_foreground: total_size_mb=871.0, rows_est=2168874
- telephony: total_size_mb=705.9844, rows_est=995098
- gsm: total_size_mb=382.7656, rows_est=1054791
- screen: total_size_mb=297.6562, rows_est=1114168
- bluetooth: total_size_mb=204.3906, rows_est=539084

## Likely Useful Tables For Digital Phenotyping (now)
- applications_foreground (phone_usage)
- aware_device (metadata)
- aware_log (metadata)
- barometer (environment)
- battery (environment)
- battery_charges (environment)
- battery_discharges (environment)
- bluetooth (location_context)
- calls (phone_usage)
- gsm (location_context)
- gsm_neighbor (location_context)
- keyboard (phone_usage)
- light (environment)
- locations (location_context)
- messages (phone_usage)
- network (location_context)
- network_traffic (location_context)
- plugin_google_activity_recognition (system)
- proximity (environment)
- screen (phone_usage)
- telephony (phone_usage)
- timezone (location_context)
- touch (phone_usage)
- wifi (location_context)

## Ignored For Now
Operational sensor_* and excluded tables are listed here.
- sensor_accelerometer (category=operational, use=ignore)
- sensor_barometer (category=operational, use=ignore)
- sensor_bluetooth (category=operational, use=ignore)
- sensor_gravity (category=operational, use=ignore)
- sensor_gyroscope (category=operational, use=ignore)
- sensor_light (category=operational, use=ignore)
- sensor_linear_accelerometer (category=operational, use=ignore)
- sensor_magnetometer (category=operational, use=ignore)
- sensor_proximity (category=operational, use=ignore)
- sensor_rotation (category=operational, use=ignore)
- sensor_temperature (category=operational, use=ignore)
- sensor_wifi (category=operational, use=ignore)

## High-Frequency Tables (postponed)
- accelerometer
- gravity
- gyroscope
- linear_accelerometer
- magnetometer
- rotation

## JSON Key Discovery Notes
- JSON sampling limited to top10 subject device episodes and T1-to-T2 windows.
- Up to 200 sampled rows per table.
- information_schema row counts/sizes are approximate.

## Feature-Relevant JSON Tables (simple interpretation)
### applications_foreground
- JSON keys found (sample): application_name, device_id, is_system_app, package_name, timestamp
- Possible feature families: unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### aware_device
- JSON keys found (sample): board, brand, build_id, device, device_id, hardware, label, manufacturer, model, product, release, release_type, sdk, serial, timestamp
- Possible feature families: unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### aware_log
- JSON keys found (sample): device_id, log_message, timestamp
- Possible feature families: social_behavior, unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### battery
- JSON keys found (sample): battery_adaptor, battery_health, battery_level, battery_scale, battery_status, battery_technology, battery_temperature, battery_voltage, device_id, timestamp
- Possible feature families: mobility, phone_use_state, unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### calls
- JSON keys found (sample): call_duration, call_type, device_id, timestamp, trace
- Possible feature families: social_behavior, unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### gsm
- JSON keys found (sample): bit_error_rate, cid, device_id, lac, psc, signal_strength, timestamp
- Possible feature families: unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### gsm_neighbor
- JSON keys found (sample): cid, device_id, lac, psc, signal_strength, timestamp
- Possible feature families: unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### keyboard
- JSON keys found (sample): before_text, current_text, device_id, is_password, package_name, timestamp
- Possible feature families: unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### locations
- JSON keys found (sample): accuracy, device_id, double_altitude, double_bearing, double_latitude, double_longitude, double_speed, label, provider, timestamp
- Possible feature families: mobility, unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### messages
- JSON keys found (sample): device_id, message_type, timestamp, trace
- Possible feature families: social_behavior, unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### plugin_google_activity_recognition
- JSON keys found (sample): activities, activity_name, activity_type, confidence, device_id, timestamp
- Possible feature families: activity_pattern, unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### screen
- JSON keys found (sample): device_id, screen_status, timestamp
- Possible feature families: sleep_circadian, unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### telephony
- JSON keys found (sample): data_enabled, device_id, imei_meid_esn, line_number, network_country_iso_mcc, network_operator_code, network_operator_name, network_type, phone_type, sim_operator_code, sim_operator_name, sim_serial, sim_state, software_version, subscriber_id, timestamp
- Possible feature families: social_environment, unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### touch
- JSON keys found (sample): device_id, scroll_from_index, scroll_items, scroll_to_index, timestamp, touch_action, touch_action_text, touch_app
- Possible feature families: unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.
### wifi
- JSON keys found (sample): bssid, device_id, frequency, label, rssi, security, ssid, timestamp
- Possible feature families: social_environment, unknown
- Data quality concerns: sampled subset only; key prevalence may vary by device/time.

## Manual JSON Key Confirmations (Post-Discovery)
These updates were added from manual single-row inspection and **without new SQL execution**.

### light
- Confirmed key: `double_light_lux`
- Interpretation: ambient light (lux), useful for circadian/day-night exposure and routine patterns.
- Caveat: low lux can also indicate phone in pocket/bag.
- PoC status: `optional_later` (safe day-level probing required).

### proximity
- Confirmed key: `double_proximity`
- Interpretation: proximity distance/state (near/covered); device-dependent.
- PoC status: `optional_later` (distribution check + safe day-level probing required).

### barometer
- Confirmed key: `double_values_0`
- Interpretation: likely pressure (hPa/mbar), weak context/altitude proxy.
- PoC status: `later_low_priority` (exclude from initial PoC).
