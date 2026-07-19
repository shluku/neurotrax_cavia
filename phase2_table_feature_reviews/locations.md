# locations Feature Review

## Table Meaning

`locations` contains phone location observations. The Phase 2A sample shows location fields in JSON:

- `double_latitude`
- `double_longitude`
- `accuracy`
- `provider`
- `double_speed`
- `double_bearing`
- `double_altitude`
- `timestamp`
- `device_id`

This table can support mobility-context features, but raw latitude/longitude should not become direct model features. Final outputs should use aggregate movement summaries.

## Phase 2A Result

Phase 2A was run using the current T1-ranked 24-hour T1-week protocol:

- patients scanned by descending `global_T1`
- Subject_ID_D `001` skipped
- primary window: local midnight day after T1 plus 24 hours
- fallback: first complete 24-hour span inside T1 week
- SQL filtered by `device_id` and timestamp

Selected review window:

- Subject_ID_D: `085`
- Subject_ID_N: `81`
- global_T1: `100.0`
- T1_date_iso: `2025-03-04`
- device_id: `b89546ef-9f57-4fd0-ad48-638a4a783d19`
- window_rule: `exploratory_fallback_first_24h_span_within_T1_week`
- window_start_local: `2025-03-04 10:26:12+0200`
- window_end_local: `2025-03-05 10:26:12+0200`
- n_rows_in_window: `4468`

The primary day-after-T1 window had no rows for this subject. The valid review sample comes from the fallback first 24-hour span inside the T1 week.

## Duplicate/Repeated Row Issue

The first 20 raw rows were repeated copies of the same timestamp and coordinate. The raw sample is preserved, but a distinct-observation inspection file was also created:

- `output/analysis_candidates/phase2_feature_review/locations/locations_sample_rows_distinct_observations.csv`

Current distinct-observation key:

- `timestamp`
- `data`

The distinct sample is more useful for manual feature review.

## Selected Features

The following `locations` features are selected for Phase 2B exploratory calculation:

| Selected feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `location_distinct_observation_count` | Count distinct timestamp/location observations in the selected window. | Location data availability and sampling density. | Coverage support; not mobility by itself. |
| `location_total_distance_km` | Sum haversine distance between consecutive distinct valid coordinates. | Approximate phone movement distance. | GPS jitter and phone carrying behavior can inflate distance. |

## Candidate Features

Recommended major candidate features:

| Candidate feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `location_radius_of_gyration_m` | Root mean square distance from the center of observed coordinates. | Spatial spread of movement. | Sensitive to outliers and location accuracy. |
| `location_max_distance_from_start_m` | Maximum distance from first valid coordinate in the window. | How far the phone moved from the starting location. | Starting point may not be home. |
| `location_time_at_primary_location_fraction` | Fraction of observations near the most common location cluster. | Concentration near one main place. | Needs a distance threshold or clustering rule. |
| `location_gps_provider_fraction` | Fraction of distinct observations from GPS provider. | Location quality/context support. | Provider is data-quality/context, not behavior by itself. |
| `location_median_accuracy_m` | Median reported location accuracy. | Reliability of location-derived mobility features. | Accuracy is a quality feature and should support interpretation. |

## Current Decision

Proceed with Phase 2B for the two selected aggregate features. Keep raw coordinates out of model-facing outputs.

## Interpretation Rules

- Missing location data is missing data, not no movement.
- Raw latitude and longitude are allowed for authorized manual inspection, but final phenotype/model outputs should use aggregate features.
- GPS/network provider differences should be documented because they affect accuracy and movement estimates.
- Movement features describe phone movement/location context, not direct patient activity.

## Global Coverage Summary

This compact summary describes global `locations` availability across the SensorDB table, mapped back to the current study device map.

- Devices with `locations` rows: `65`
- Mapped study patients with `locations` rows: `47`
- Mapped devices with rows: `53`
- Unmapped devices with rows: `12`
- Rows mapped to study patients: `285,927`
- Rows on unmapped devices: `64,920`

Protocol note: this is a global table-coverage summary for Phase 2A planning. It is not feature extraction, not a T1-window phenotype result, and missing data is not interpreted as zero activity.
