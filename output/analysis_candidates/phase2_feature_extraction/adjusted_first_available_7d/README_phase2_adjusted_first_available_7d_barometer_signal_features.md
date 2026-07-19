# Barometer Adjusted First-Available 7-Day Signal Features

This adjusted Phase 2B extraction calculates selected `barometer` signal features for the first ranked patient/device with at least `20` rows in the first available 7-day window after T1.

Selected window:

- Subject_ID_D: `045`
- Subject_ID_N: `51`
- global_T1: `93.4`
- T1_date_iso: `2025-01-21`
- device_id: `fdce7e53-e549-45b0-a477-8c300329c656`
- window_rule: `adjusted_first_available_7d_after_T1`
- window_start_local: `2025-07-10 10:36:07+0300`
- window_end_local: `2025-07-17 10:36:07+0300`
- rows in window: `2750`
- days_first_available_after_T1: `169`


Signal processing thresholds and constants:

- pressure source: `data.double_values_0`
- pressure accepted range: `300.0` to `1100.0` hPa
- resampling grid: `1s`
- short-gap interpolation limit: `5` seconds
- first smoothing step: centered rolling median, `10` seconds
- second smoothing step: Butterworth low-pass when segment length permits
- Butterworth order: `2`
- Butterworth cutoff: `0.05` Hz
- Butterworth sampling frequency: `1.0` Hz
- minimum Butterworth segment length: `30` seconds
- pressure-to-elevation approximation: `-8.3 * pressure_delta_hPa`
- large vertical shift threshold: `3.0` meters
- minimum transition duration: `10` seconds
- transition refractory/collapse window: `30` seconds

Selected features:

- `barometer_pressure_range`
- `barometer_pressure_sd`
- `barometer_large_vertical_shift_count`
- `barometer_estimated_elevation_change_m`
- `barometer_upward_transition_count`
- `barometer_downward_transition_count`

Interpretation limits:

- This is a delayed adjusted first-available window, not a T1 baseline week.
- Barometer pressure can reflect altitude, weather, device hardware, and sampling conditions.
- These are exploratory vertical-context support features, not posture features and not diagnostic markers.
- Missing data remains missing and must not be converted to zero.

QC summary:

raw_rows                                                               2750
parsed_pressure_rows                                                   2750
json_parse_errors                                                         0
pressure_min_threshold_hpa                                            300.0
pressure_max_threshold_hpa                                           1100.0
resample_rule                                                            1s
short_gap_interpolate_limit_seconds                                       5
rolling_median_seconds                                                   10
butterworth_order                                                         2
butterworth_cutoff_hz                                                  0.05
large_vertical_shift_threshold_m                                        3.0
min_transition_duration_seconds                                          10
transition_refractory_seconds                                            30
elevation_meters_per_hpa                                                8.3
clean_pressure_rows                                                    2750
removed_pressure_outlier_rows                                             0
signal_start_local                                 2025-07-10 10:36:07+0300
signal_end_local                                   2025-07-10 17:07:06+0300
observed_duration_seconds                                         23459.391
resampled_points                                                      23460
smoothed_valid_points                                                   510
smoothing_method                                                butterworth
Subject_ID_D                                                            045
Subject_ID_N                                                             51
device_id                              fdce7e53-e549-45b0-a477-8c300329c656
global_T1                                                              93.4
T1_date_iso                                                      2025-01-21
window_start_local                                 2025-07-10 10:36:07+0300
window_end_local                                   2025-07-17 10:36:07+0300
days_first_available_after_T1                                           169
