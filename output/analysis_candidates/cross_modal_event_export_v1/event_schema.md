# Event export schema

Each Parquet partition is keyed by pseudonymous patient suffix, pseudonymous device, local date, modality, and verified screen session. All rows retain `timestamp_ms`, `timestamp_local`, source table, session bounds, and same-device verification. ACC rows retain x/y/z and raw accuracy where present. Touch rows retain action, hashed app context, and scroll-presence flag. Foreground-app rows retain only a truncated SHA-256 package hash and system-app flag. Keyboard rows retain only a text-state event label, hashed package context, and non-password status; no text fields are exported.

ACC sampling rate is derived from unique timestamp differences per session. Sensor identity and capability metadata remain in the source audit and are not conflated with observed cadence.
