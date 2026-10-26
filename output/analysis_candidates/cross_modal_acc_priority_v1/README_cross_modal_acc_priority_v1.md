# Cross-Modal Phase 3A — Accelerometer × Phone Usage

## Scope and connection

This bounded pilot used read-only SensorDB queries and two devices selected from event-table coverage, without cognitive outcomes. It retrieved the first three verified screen-unlocked sessions on one day for each device, limiting each ACC query to the first 60 seconds of the session. Six synchronized segments were obtained, all with at least 50 accelerometer samples and calculable jerk.

The raw accelerometer table exposes `double_values_0`, `double_values_1`, and `double_values_2` with millisecond timestamps. The median vector magnitude was near 9.8–10.0 in all segments, consistent with acceleration units that include gravity. This is an empirical unit check, not a formal sensor-calibration validation.

## Definitions

- Magnitude: `sqrt(x²+y²+z²)` using raw accelerometer axes, including gravity.
- Moving fraction: proportion of samples where `abs(magnitude - segment_median_magnitude) > 0.2` in the bounded segment. This is a phone-motion proxy, not body movement.
- Jerk magnitude: `||a(i+1)-a(i)|| / ((t(i+1)-t(i))/1000)` using the actual timestamp gap in seconds. Intervals must be positive and no more than 1 second; larger gaps are excluded from jerk.
- Sampling QC: median and 95th-percentile timestamp interval, duplicate removal, and fraction of gaps over one second.
- Keyboard-associated segment: a verified screen session segment containing at least one keyboard snapshot. The snapshot is a text-state observation, not a keypress.
- Screen-active-no-keyboard segment: a verified screen session segment with no keyboard snapshot in the bounded interval.

Jerk is a newly proposed feature in this project. It is not labeled tremor, gait, or hand-motor impairment.

## Results

All six segments had zero gaps over one second after timestamp ordering. Sampling was highly device-dependent: one device had a median interval near 200 ms, while the other had much denser sub-10-ms intervals. This difference makes raw jerk magnitudes incomparable without device-specific sampling QC and resampling. All six segments had gravity-like median magnitudes.

Three segments contained keyboard snapshots and three did not. Keyboard-associated segments showed median jerk values of approximately 1.39, 9.10 and 14.56 in the reported units; non-keyboard screen-active segments showed approximately 34.35, 51.66 and 3.88. With only two patients and three segments per class, this is descriptive only and does not support a behavioral conclusion.

The bounded event windows covered two patients, two days and six sessions. There is no day-to-day or early/late reliability estimate yet. The pilot demonstrates that ACC samples can be retrieved during verified phone-use episodes, but not that jerk is repeatable across devices or time.

## Retention decision

Retain acceleration magnitude SD/IQR and sampling-QC metrics for a larger synchronized pilot. Retain jerk only after device-stratified resampling/filtering and a prespecified minimum contiguous duration are validated. Do not compare raw jerk values across devices using the current implementation. Orientation, handling, walking and vehicle movement remain potential confounders.

## Files

- `acc_event_coverage.csv`
- `acc_synchronized_segments.csv`
- `acc_qc_summary.csv`
- `longitudinal_feasibility_summary.csv`
- `acc_segment_summary_plot.png`

No raw accelerometer waveforms, keyboard text, or app content were exported.
