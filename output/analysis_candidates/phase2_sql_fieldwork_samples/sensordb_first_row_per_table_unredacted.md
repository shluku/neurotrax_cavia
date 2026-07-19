# SensorDB First Row Per Table - Unredacted

This file contains one first available row per non-heavy table with no field-level redaction.
Known high-frequency raw tables are skipped for query safety only.

## accelerometer
- status: skipped_high_frequency_heavy_table
- error_message: known high-frequency/heavy raw sensor table; skipped to avoid unsafe slow query

## applications_foreground
- status: ok
- timestamp_ms: 1733821677574.0
- device_id: 1fc14012-3b9d-4413-a841-5c775e1bba42
```json
{"_id": 1, "timestamp": 1733821677574.0, "device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "data": {"device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "timestamp": 1733821677574, "package_name": "com.aware.phone", "is_system_app": "0", "application_name": "CAVIA"}}
```

## aware_device
- status: ok
- timestamp_ms: 1736145495944.0
- device_id: 72c92feb-2f80-4659-82ff-f49feba9e15f
```json
{"_id": 3, "timestamp": 1736145495944.0, "device_id": "72c92feb-2f80-4659-82ff-f49feba9e15f", "data": {"sdk": "34", "board": "moon", "brand": "POCO", "label": "", "model": "2404APC5FG", "device": "moon", "serial": "unknown", "product": "moon_p_global", "release": "14", "build_id": "UP1A.231005.007", "hardware": "mt6768", "device_id": "72c92feb-2f80-4659-82ff-f49feba9e15f", "timestamp": 1736145495944, "manufacturer": "Xiaomi", "release_type": "user"}}
```

## aware_log
- status: ok
- timestamp_ms: 1728793063672.0
- device_id: bcc113f0-6826-4424-8e1c-b6d67a99e094
```json
{"_id": 46035279, "timestamp": 1728793063672.0, "device_id": "bcc113f0-6826-4424-8e1c-b6d67a99e094", "data": {"device_id": "bcc113f0-6826-4424-8e1c-b6d67a99e094", "timestamp": 1728793063672, "log_message": {"table": "aware_log", "last_sync_timestamp": 1728793061963}}}
```

## aware_studies
- status: ok
- timestamp_ms: 1748431709574.0
- device_id: eabbf942-13cb-4cd6-ae80-3777e74e7f5e
```json
{"_id": 1, "timestamp": 1748431709574.0, "device_id": "eabbf942-13cb-4cd6-ae80-3777e74e7f5e", "data": {"study_pi": "Gal Iffargan\nContact: galif@clalit.org.il", "device_id": "eabbf942-13cb-4cd6-ae80-3777e74e7f5e", "study_api": "4lph4num3ric", "study_key": "1", "study_url": "http://www.neuro-starlighters.com:8080/index.php/1/4lph4num3ric", "timestamp": 1748431709574, "double_exit": 0, "double_join": 1748431662506, "study_title": "Applebaum Research", "study_config": [{"sensors": [{"setting": "status_accelerometer", "value": "true"}, {"setting": "frequency_accelerometer", "value": "200000"}, {"setting": "threshold_accelerometer", "value": "0"}, {"setting": "frequency_accelerometer_enforce", "value": "false"}, {"setting": "status_applications", "value": "true"}, {"setting": "frequency_applications", "value": "0"}, {"setting": "status_installations", "value": "false"}, {"setting": "status_keyboard", "value": "true"}, {"setting": "mask_keyboard", "value": "true"}, {"setting": "status_notifications", "value": "false"}, {"setting": "status_crashes", "value": "false"}, {"setting": "status_barometer", "value": "false"}, {"setting": "frequency_barometer", "value": "200000"}, {"setting": "threshold_barometer", "value": "0"}, {"setting": "frequency_barometer_enforce", "value": "false"}, {"setting": "status_battery", "value": "false"}, {"setting": "status_bluetooth", "value": "false"}, {"setting": "frequency_bluetooth", "value": "60"}, {"setting": "status_calls", "value": "true"}, {"setting": "status_messages", "value": "true"}, {"setting": "status_esm", "value": "false"}, {"setting": "status_gravity", "value": "true"}, {"setting": "frequency_gravity", "value": "200000"}, {"setting": "threshold_gravity", "value": "0"}, {"setting": "frequency_gravity_enforce", "value": "false"}, {"setting": "status_gyroscope", "value": "true"}, {"setting": "frequency_gyroscope", "value": "200000"}, {"setting": "threshold_gyroscope", "value": "0"}, {"setting": "frequency_gyroscope_enforce", "value": "false"}, {"setting": "status_location_gps", "value": "false"}, {"setting": "frequency_location_gps", "value": "180"}, {"setting": "min_location_gps_accuracy", "value": "150"}, {"setting": "status_location_network", "value": "false"}, {"setting": "frequency_location_network", "value": "300"}, {"setting": "min_location_network_accuracy", "value": "1500"}, {"setting": "status_location_passive", "value": "false"}, {"setting": "location_expiration_time", "value": "300"}, {"setting": "location_save_all", "value": "false"}, {"setting": "status_light", "value": "true"}, {"setting": "frequency_light", "value": "200000"}, {"setting": "threshold_light", "value": "0"}, {"setting": "frequency_light_enforce", "value": "false"}, {"setting": "status_linear_accelerometer", "value": "false"}, {"setting": "frequency_linear_accelerometer", "value": "200000"}, {"setting": "threshold_linear_accelerometer", "value": "0"}, {"setting": "frequency_linear_accelerometer_enforce", "value": "false"}, {"setting": "status_network_events", "value": "false"}, {"setting": "status_network_traffic", "value": "false"}, {"setting": "status_magnetometer", "value": "false"}, {"setting": "frequency_magnetometer", "value": "200000"}, {"setting": "threshold_magnetometer", "value": "0"}, {"setting": "frequency_magnetometer_enforce", "value": "false"}, {"setting": "status_processor", "value": "false"}, {"setting": "frequency_processor", "value": "10"}, {"setting": "status_timezone", "value": "false"}, {"setting": "status_proximity", "value": "true"}, {"setting": "frequency_proximity", "value": "200000"}, {"setting": "threshold_proximity", "value": "0"}, {"setting": "frequency_proximity_enforce", "value": "false"}, {"setting": "status_rotation", "value": "true"}, {"setting": "frequency_rotation", "value": "200000"}, {"setting": "threshold_rotation", "value": "0"}, {"setting": "frequency_rotation_enforce", "value": "false"}, {"setting": "status_screen", "value": "true"}, {"setting": "status_touch", "value": "true"}, {"setting": "mask_touch_text", "value": "true"}, {"setting": "status_significant_motion", "value": "false"}, {"setting": "status_temperature", "value": "false"}, {"setting": "frequency_temperature", "value": "200000"}, {"setting": "threshold_temperature", "value": "0"}, {"setting": "frequency_temperature_enforce", "value": "false"}, {"setting": "status_telephony", "value": "true"}, {"setting": "status_wifi", "value": "false"}, {"setting": "frequency_wifi", "value": "60"}, {"setting": "status_websocket", "value": "false"}, {"setting": "status_mqtt", "value": "false"}, {"setting": "mqtt_port", "value": "1883"}, {"setting": "mqtt_keep_alive", "value": "600"}, {"setting": "mqtt_qos", "value": "2"}, {"setting": "status_webservice", "value": "true"}, {"setting": "webservice_server", "value": "http://www.neuro-starlighters.com:8080/index.php/1/4lph4num3ric"}, {"setting": "webservice_wifi_only", "value": "false"}, {"setting": "fallback_network", "value": "0"}, {"setting": "webservice_charging", "value": "false"}, {"setting": "frequency_webservice", "value": "30"}, {"setting": "frequency_clean_old_data", "value": "3"}, {"setting": "webservice_silent", "value": "false"}, {"setting": "remind_to_charge", "value": "false"}, {"setting": "foreground_priority", "value": "true"}, {"setting": "debug_flag", "value": "false"}, {"setting": "debug_tag", "value": "AWARE"}, {"setting": "debug_db_slow", "value": "false"}, {"setting": "webservice_simple", "value": "false"}, {"setting": "webservice_remove_data", "value": "false"}, {"setting": "interface_locked", "value": "false"}, {"setting": "frequency_enforce_all", "value": "false"}, {"setting": "study_id", "value": "4lph4num3ric"}, {"setting": "study_start", "value": 1720091155167}], "plugins": [{"plugin": "com.aware.plugin.ambient_noise", "settings": [{"setting": "status_plugin_ambient_noise", "value": "false"}, {"setting": "frequency_plugin_ambient_noise", "value": "5"}, {"setting": "plugin_ambient_noise_sample_size", "value": "30"}, {"setting": "plugin_ambient_noise_silence_threshold", "value": "50"}, {"setting": "plugin_ambient_noise_no_raw", "value": "true"}]}, {"plugin": "com.aware.plugin.google.activity_recognition", "settings": [{"setting": "status_plugin_google_activity_recognition", "value": "true"}, {"setting": "frequency_plugin_google_activity_recognition", "value": "60"}]}, {"plugin": "com.aware.plugin.sentimental", "settings": [{"setting": "status_plugin_sentimental", "value": "false"}]}, {"plugin": "com.aware.plugin.openweather", "settings": [{"setting": "status_plugin_openweather", "value": "false"}, {"setting": "units_plugin_openweather", "value": "metric"}, {"setting": "plugin_openweather_frequency", "value": "60"}, {"setting": "api_key_plugin_openweather", "value": "ada11fb870974565377df238f3046aa9"}]}, {"plugin": "com.aware.plugin.esm.scheduler", "settings": [{"setting": "status_plugin_esm_scheduler", "value": "false"}]}, {"plugin": "com.aware.plugin.fitbit", "settings": [{"setting": "status_plugin_fitbit", "value": "false"}, {"setting": "units_plugin_fitbit", "value": "metric"}, {"setting": "fitbit_granularity", "value": "15min"}, {"setting": "fitbit_hr_granularity", "value": "1sec"}, {"setting": "plugin_fitbit_frequency", "value": "15"}, {"setting": "api_key_plugin_fitbit", "value": "227YG3"}, {"setting": "api_secret_plugin_fitbit", "value": "033ed2a3710c0cde04343d073c09e378"}]}, {"plugin": "com.aware.plugin.sensortag", "settings": [{"setting": "status_plugin_sensortag", "value": "false"}, {"setting": "frequency_plugin_sensortag", "value": "30"}]}, {"plugin": "com.aware.plugin.contacts_list", "settings": [{"setting": "status_plugin_contacts", "value": "false"}, {"setting": "frequency_plugin_contacts", "value": "1"}]}, {"plugin": "com.aware.plugin.google.auth", "settings": [{"setting": "status_plugin_google_login", "value": "false"}]}, {"plugin": "com.aware.plugin.google.fused_location", "settings": [{"setting": "status_google_fused_location", "value": "false"}, {"setting": "frequency_google_fused_location", "value": "300"}, {"setting": "max_frequency_google_fused_location", "value": "60"}, {"setting": "fallback_location_timeout", "value": "20"}, {"setting": "location_sensitivity", "value": "5"}, {"setting": "accuracy_google_fused_location", "value": "102"}]}, {"plugin": "com.aware.plugin.device_usage", "settings": [{"setting": "status_plugin_device_usage", "value": "false"}]}, {"plugin": "com.aware.plugin.studentlife.audio_final", "settings": [{"setting": "status_plugin_studentlife_audio", "value": "false"}, {"setting": "plugin_conversations_delay", "value": "1"}, {"setting": "plugin_conversations_off_duty", "value": "3"}, {"setting": "plugin_conversations_length", "value": "1"}]}]}], "study_compliance": "attempt to quit study", "study_description": "This is a research which assess cognitive recognition according to phone sensor data. All data is saved annonymously."}}
```

## barometer
- status: ok
- timestamp_ms: 1748001703267.0
- device_id: 40244c82-0b7d-41a1-804d-6f3279efe348
```json
{"_id": 1, "timestamp": 1748001703267.0, "device_id": "40244c82-0b7d-41a1-804d-6f3279efe348", "data": {"label": "", "accuracy": "3", "device_id": "40244c82-0b7d-41a1-804d-6f3279efe348", "timestamp": 1748001703267, "double_values_0": 1007.3660278320312}}
```

## battery
- status: ok
- timestamp_ms: 1741084125332.0
- device_id: 536902cf-31b5-4ac7-ac7a-f50783d635c9
```json
{"_id": 1, "timestamp": 1741084125332.0, "device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "data": {"device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "timestamp": 1741084125332, "battery_level": "75", "battery_scale": "100", "battery_health": "2", "battery_status": "3", "battery_adaptor": "0", "battery_voltage": "3905", "battery_technology": "Li-ion", "battery_temperature": "30"}}
```

## battery_charges
- status: ok
- timestamp_ms: 1741430985471.0
- device_id: 536902cf-31b5-4ac7-ac7a-f50783d635c9
```json
{"_id": 1, "timestamp": 1741430985471.0, "device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "data": {"device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "timestamp": 1741430985471, "battery_end": "85", "battery_start": "84", "double_end_timestamp": 1741432067084}}
```

## battery_discharges
- status: ok
- timestamp_ms: 1741429892614.0
- device_id: 536902cf-31b5-4ac7-ac7a-f50783d635c9
```json
{"_id": 1, "timestamp": 1741429892614.0, "device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "data": {"device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "timestamp": 1741429892614, "battery_end": "84", "battery_start": "85", "double_end_timestamp": 1741430985467}}
```

## bluetooth
- status: ok
- timestamp_ms: 1741075652743.0
- device_id: 5278bdbc-c56d-43c8-b543-ad75bab7aca8
```json
{"_id": 1, "timestamp": 1741075652743.0, "device_id": "5278bdbc-c56d-43c8-b543-ad75bab7aca8", "data": {"label": "1741075652611", "bt_name": "", "bt_rssi": "-83", "device_id": "5278bdbc-c56d-43c8-b543-ad75bab7aca8", "timestamp": 1741075652743, "bt_address": "00:FA:FA:CE:9E:0C"}}
```

## calls
- status: ok
- timestamp_ms: 1736155801352.0
- device_id: dffdd7f7-4fad-4c26-b499-70586d6d0d09
```json
{"_id": 1, "timestamp": 1736155801352.0, "device_id": "dffdd7f7-4fad-4c26-b499-70586d6d0d09", "data": {"trace": "5ef9d34cd54d70e1076cebb3c248ad3cb9e075dd", "call_type": "1", "device_id": "dffdd7f7-4fad-4c26-b499-70586d6d0d09", "timestamp": 1736155801352, "call_duration": "79"}}
```

## gravity
- status: skipped_high_frequency_heavy_table
- error_message: known high-frequency/heavy raw sensor table; skipped to avoid unsafe slow query

## gsm
- status: ok
- timestamp_ms: 1736095540043.0
- device_id: b8230289-312f-4583-9e72-b7078e493e71
```json
{"_id": 1, "timestamp": 1736095540043.0, "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "data": {"cid": "9280021", "lac": "19311", "psc": "0", "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "timestamp": 1736095540043, "bit_error_rate": "2147483647", "signal_strength": "99"}}
```

## gsm_neighbor
- status: ok
- timestamp_ms: 1736098975461.0
- device_id: b8230289-312f-4583-9e72-b7078e493e71
```json
{"_id": 1, "timestamp": 1736098975461.0, "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "data": {"cid": "1281442", "lac": "10193", "psc": "44", "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "timestamp": 1736098975461, "signal_strength": "96"}}
```

## gyroscope
- status: skipped_high_frequency_heavy_table
- error_message: known high-frequency/heavy raw sensor table; skipped to avoid unsafe slow query

## keyboard
- status: ok
- timestamp_ms: 1736095685948.0
- device_id: b8230289-312f-4583-9e72-b7078e493e71
```json
{"_id": 1, "timestamp": 1736095685948.0, "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "data": {"device_id": "b8230289-312f-4583-9e72-b7078e493e71", "timestamp": 1736095685948, "before_text": "", "is_password": "0", "current_text": "[a]", "package_name": "com.sec.android.app.launcher"}}
```

## light
- status: ok
- timestamp_ms: 1733821675811.0
- device_id: 1fc14012-3b9d-4413-a841-5c775e1bba42
```json
{"_id": 1, "timestamp": 1733821675811.0, "device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "data": {"label": "", "accuracy": "3", "device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "timestamp": 1733821675811, "double_light_lux": 33}}
```

## linear_accelerometer
- status: skipped_high_frequency_heavy_table
- error_message: known high-frequency/heavy raw sensor table; skipped to avoid unsafe slow query

## locations
- status: ok
- timestamp_ms: 1741075560690.0
- device_id: 5278bdbc-c56d-43c8-b543-ad75bab7aca8
```json
{"_id": 1, "timestamp": 1741075560690.0, "device_id": "5278bdbc-c56d-43c8-b543-ad75bab7aca8", "data": {"label": "", "accuracy": "10.5042", "provider": "gps", "device_id": "5278bdbc-c56d-43c8-b543-ad75bab7aca8", "timestamp": 1741075560690, "double_speed": 0.6299999952316284, "double_bearing": 297, "double_altitude": 975.8343505859376, "double_latitude": 31.71709704, "double_longitude": 35.99938172}}
```

## magnetometer
- status: skipped_high_frequency_heavy_table
- error_message: known high-frequency/heavy raw sensor table; skipped to avoid unsafe slow query

## messages
- status: ok
- timestamp_ms: 1736098259544.0
- device_id: b8230289-312f-4583-9e72-b7078e493e71
```json
{"_id": 1, "timestamp": 1736098259544.0, "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "data": {"trace": "aefe32ee79443cb13fee987f18e4fe99b61f2b6e", "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "timestamp": 1736098259544, "message_type": "1"}}
```

## network
- status: ok
- timestamp_ms: 1747993844606.0
- device_id: afed394e-f4e2-4372-89b9-df56506976b3
```json
{"_id": 1, "timestamp": 1747993844606.0, "device_id": "afed394e-f4e2-4372-89b9-df56506976b3", "data": {"device_id": "afed394e-f4e2-4372-89b9-df56506976b3", "timestamp": 1747993844606, "network_type": "1", "network_state": "1", "network_subtype": "WIFI"}}
```

## network_traffic
- status: ok
- timestamp_ms: 1747999938706.0
- device_id: a182f886-53f6-4d1f-a535-ae20e5a2060e
```json
{"_id": 1, "timestamp": 1747999938706.0, "device_id": "a182f886-53f6-4d1f-a535-ae20e5a2060e", "data": {"device_id": "a182f886-53f6-4d1f-a535-ae20e5a2060e", "timestamp": 1747999938706, "network_type": "2", "double_sent_bytes": 55199272, "double_sent_packets": 169353, "double_received_bytes": 435876639, "double_received_packets": 430286}}
```

## plugin_google_activity_recognition
- status: ok
- timestamp_ms: 1728794133655.0
- device_id: bcc113f0-6826-4424-8e1c-b6d67a99e094
```json
{"_id": 2381433, "timestamp": 1728794133655.0, "device_id": "bcc113f0-6826-4424-8e1c-b6d67a99e094", "data": {"device_id": "bcc113f0-6826-4424-8e1c-b6d67a99e094", "timestamp": 1728794133655, "activities": [{"activity": "still", "confidence": 100}], "confidence": "100", "activity_name": "still", "activity_type": "3"}}
```

## proximity
- status: ok
- timestamp_ms: 1736095538570.0
- device_id: b8230289-312f-4583-9e72-b7078e493e71
```json
{"_id": 1, "timestamp": 1736095538570.0, "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "data": {"label": "", "accuracy": "3", "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "timestamp": 1736095538570, "double_proximity": 5}}
```

## rotation
- status: skipped_high_frequency_heavy_table
- error_message: known high-frequency/heavy raw sensor table; skipped to avoid unsafe slow query

## screen
- status: ok
- timestamp_ms: 1733821675559.0
- device_id: 1fc14012-3b9d-4413-a841-5c775e1bba42
```json
{"_id": 1, "timestamp": 1733821675559.0, "device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "data": {"device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "timestamp": 1733821675559, "screen_status": "1"}}
```

## sensor_accelerometer
- status: ok
- timestamp_ms: 1733821675463.0
- device_id: 1fc14012-3b9d-4413-a841-5c775e1bba42
```json
{"_id": 1, "timestamp": 1733821675463.0, "device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "data": {"device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "timestamp": 1733821675463, "sensor_name": "LSM6DSVTR Accelerometer", "sensor_type": "1", "sensor_vendor": "STM", "sensor_version": "15933", "double_sensor_power_ma": 0.15000000596046448, "double_sensor_resolution": 0.004788403399288654, "double_sensor_maximum_range": 156.90640258789062, "double_sensor_minimum_delay": 2000}}
```

## sensor_barometer
- status: ok
- timestamp_ms: 1748000546362.0
- device_id: a182f886-53f6-4d1f-a535-ae20e5a2060e
```json
{"_id": 1, "timestamp": 1748000546362.0, "device_id": "a182f886-53f6-4d1f-a535-ae20e5a2060e", "data": {"device_id": "a182f886-53f6-4d1f-a535-ae20e5a2060e", "timestamp": 1748000546362, "sensor_name": "ICP10101 Pressure Sensor", "sensor_type": "6", "sensor_vendor": "InvenSense", "sensor_version": "1", "double_sensor_power_ma": 0.0010000000474974513, "double_sensor_resolution": 9.999999747378752e-05, "double_sensor_maximum_range": 1100, "double_sensor_minimum_delay": 20000}}
```

## sensor_bluetooth
- status: ok
- timestamp_ms: 1741075563733.0
- device_id: 5278bdbc-c56d-43c8-b543-ad75bab7aca8
```json
{"_id": 1, "timestamp": 1741075563733.0, "device_id": "5278bdbc-c56d-43c8-b543-ad75bab7aca8", "data": {"bt_name": "u05D4-u05D2u05D3u05E2u05D5u05DF u05E9u05DC A52", "device_id": "5278bdbc-c56d-43c8-b543-ad75bab7aca8", "timestamp": 1741075563733, "bt_address": "02:00:00:00:00:00"}}
```

## sensor_gravity
- status: ok
- timestamp_ms: 1733821675895.0
- device_id: 1fc14012-3b9d-4413-a841-5c775e1bba42
```json
{"_id": 1, "timestamp": 1733821675895.0, "device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "data": {"device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "timestamp": 1733821675895, "sensor_name": "Gravity Sensor", "sensor_type": "9", "sensor_vendor": "Samsung Electronics", "sensor_version": "3", "double_sensor_power_ma": 1.100000023841858, "double_sensor_resolution": 5.960464477539063e-08, "double_sensor_maximum_range": 19.613300323486328, "double_sensor_minimum_delay": 10000}}
```

## sensor_gyroscope
- status: ok
- timestamp_ms: 1733821675680.0
- device_id: 1fc14012-3b9d-4413-a841-5c775e1bba42
```json
{"_id": 1, "timestamp": 1733821675680.0, "device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "data": {"device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "timestamp": 1733821675680, "sensor_name": "LSM6DSVTR Gyroscope", "sensor_type": "4", "sensor_vendor": "STM", "sensor_version": "1", "double_sensor_power_ma": 0.6499999761581421, "double_sensor_resolution": 0.0012217304902151227, "double_sensor_maximum_range": 34.906063079833984, "double_sensor_minimum_delay": 2000}}
```

## sensor_light
- status: ok
- timestamp_ms: 1733821675793.0
- device_id: 1fc14012-3b9d-4413-a841-5c775e1bba42
```json
{"_id": 1, "timestamp": 1733821675793.0, "device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "data": {"device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "timestamp": 1733821675793, "sensor_name": "STK33F11 Light", "sensor_type": "5", "sensor_vendor": "Sitronix", "sensor_version": "3002", "double_sensor_power_ma": 0.75, "double_sensor_resolution": 1, "double_sensor_maximum_range": 60000, "double_sensor_minimum_delay": 200000}}
```

## sensor_linear_accelerometer
- status: ok
- timestamp_ms: 1741084142230.0
- device_id: 536902cf-31b5-4ac7-ac7a-f50783d635c9
```json
{"_id": 1, "timestamp": 1741084142230.0, "device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "data": {"device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "timestamp": 1741084142230, "sensor_name": "linear_acceleration", "sensor_type": "10", "sensor_vendor": "qualcomm", "sensor_version": "1", "double_sensor_power_ma": 0.5149999856948853, "double_sensor_resolution": 0.009999999776482582, "double_sensor_maximum_range": 156.99008178710938, "double_sensor_minimum_delay": 5000}}
```

## sensor_magnetometer
- status: ok
- timestamp_ms: 1745923839893.0
- device_id: 4c117a46-b964-4c89-9e9d-5c08ac50c19c
```json
{"_id": 1, "timestamp": 1745923839893.0, "device_id": "4c117a46-b964-4c89-9e9d-5c08ac50c19c", "data": {"device_id": "4c117a46-b964-4c89-9e9d-5c08ac50c19c", "timestamp": 1745923839893, "sensor_name": "AK09918C Magnetometer", "sensor_type": "2", "sensor_vendor": "Asahi Kasei Microdevices", "sensor_version": "2", "double_sensor_power_ma": 1.100000023841858, "double_sensor_resolution": 0.05999999865889549, "double_sensor_maximum_range": 4900.02001953125, "double_sensor_minimum_delay": 8000}}
```

## sensor_proximity
- status: ok
- timestamp_ms: 1733821675842.0
- device_id: 1fc14012-3b9d-4413-a841-5c775e1bba42
```json
{"_id": 1, "timestamp": 1733821675842.0, "device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "data": {"device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "timestamp": 1733821675842, "sensor_name": "Palm Proximity Sensor version 2", "sensor_type": "8", "sensor_vendor": "Samsung", "sensor_version": "1000", "double_sensor_power_ma": 0.75, "double_sensor_resolution": 1, "double_sensor_maximum_range": 5, "double_sensor_minimum_delay": 0}}
```

## sensor_rotation
- status: ok
- timestamp_ms: 1733821675745.0
- device_id: 1fc14012-3b9d-4413-a841-5c775e1bba42
```json
{"_id": 1, "timestamp": 1733821675745.0, "device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "data": {"device_id": "1fc14012-3b9d-4413-a841-5c775e1bba42", "timestamp": 1733821675745, "sensor_name": "Samsung Rotation Vector", "sensor_type": "11", "sensor_vendor": "Samsung Inc.", "sensor_version": "1", "double_sensor_power_ma": 1.100000023841858, "double_sensor_resolution": 5.960464477539063e-08, "double_sensor_maximum_range": 1, "double_sensor_minimum_delay": 10000}}
```

## sensor_temperature
- status: ok
- timestamp_ms: 1748005465044.0
- device_id: 13594c10-ce08-4b81-8b17-e941b69ac95e
```json
{"_id": 1, "timestamp": 1748005465044.0, "device_id": "13594c10-ce08-4b81-8b17-e941b69ac95e", "data": {"device_id": "13594c10-ce08-4b81-8b17-e941b69ac95e", "timestamp": 1748005465044, "sensor_name": "Goldfish Ambient Temperature sensor", "sensor_type": "13", "sensor_vendor": "The Android Open Source Project", "sensor_version": "1", "double_sensor_power_ma": 0.0010000000474974513, "double_sensor_resolution": 1, "double_sensor_maximum_range": 80, "double_sensor_minimum_delay": 0}}
```

## sensor_wifi
- status: ok
- timestamp_ms: 1664194605764.0
- device_id: 536902cf-31b5-4ac7-ac7a-f50783d635c9
```json
{"_id": 5495, "timestamp": 1664194605764.0, "device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "data": {"ssid": "<unknown ssid>", "bssid": "", "device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "timestamp": 1664194605764, "mac_address": "02:00:00:00:00:00"}}
```

## significant
- status: ok
- timestamp_ms: 1745923837987.0
- device_id: 4c117a46-b964-4c89-9e9d-5c08ac50c19c
```json
{"_id": 1, "timestamp": 1745923837987.0, "device_id": "4c117a46-b964-4c89-9e9d-5c08ac50c19c", "data": {"device_id": "4c117a46-b964-4c89-9e9d-5c08ac50c19c", "is_moving": "1", "timestamp": 1745923837987}}
```

## telephony
- status: ok
- timestamp_ms: 1736095540165.0
- device_id: b8230289-312f-4583-9e72-b7078e493e71
```json
{"_id": 1, "timestamp": 1736095540165.0, "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "data": {"device_id": "b8230289-312f-4583-9e72-b7078e493e71", "sim_state": "5", "timestamp": 1736095540165, "phone_type": "1", "sim_serial": "", "line_number": "", "data_enabled": "2", "network_type": "13", "imei_meid_esn": "", "subscriber_id": "", "software_version": "01", "sim_operator_code": "42501", "sim_operator_name": "Partner Communications Co. Ltd.", "network_operator_code": "42501", "network_operator_name": "Partner", "network_country_iso_mcc": "il"}}
```

## timezone
- status: ok
- timestamp_ms: 1747993877914.0
- device_id: afed394e-f4e2-4372-89b9-df56506976b3
```json
{"_id": 1, "timestamp": 1747993877914.0, "device_id": "afed394e-f4e2-4372-89b9-df56506976b3", "data": {"timezone": "Europe/Kiev", "device_id": "afed394e-f4e2-4372-89b9-df56506976b3", "timestamp": 1747993877914}}
```

## touch
- status: ok
- timestamp_ms: 1736095548384.0
- device_id: b8230289-312f-4583-9e72-b7078e493e71
```json
{"_id": 1, "timestamp": 1736095548384.0, "device_id": "b8230289-312f-4583-9e72-b7078e493e71", "data": {"device_id": "b8230289-312f-4583-9e72-b7078e493e71", "timestamp": 1736095548384, "touch_app": "com.aware.phone", "scroll_items": "35", "touch_action": "ACTION_AWARE_TOUCH_SCROLLED_DOWN", "scroll_to_index": "10", "scroll_from_index": "2", "touch_action_text": ""}}
```

## wifi
- status: ok
- timestamp_ms: 1741084223483.0
- device_id: 536902cf-31b5-4ac7-ac7a-f50783d635c9
```json
{"_id": 1, "timestamp": 1741084223483.0, "device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "data": {"rssi": "0", "ssid": "", "bssid": "", "label": "disabled", "security": "", "device_id": "536902cf-31b5-4ac7-ac7a-f50783d635c9", "frequency": "0", "timestamp": 1741084223483}}
```
