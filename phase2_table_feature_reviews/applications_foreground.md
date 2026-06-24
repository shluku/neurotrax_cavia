# applications_foreground Feature Review

## Table Meaning

`applications_foreground` records foreground Android package observations or transitions for a device over time.

For the current protocol, one `applications_foreground` event means one raw row in the `applications_foreground` table within the selected device/time window.

This raw definition is intentionally preserved for now so patients can be compared using the same SensorDB logging behavior and the same extraction rule.

## Fields Seen in `data`

- `device_id`
- `timestamp`
- `package_name`
- `is_system_app`
- `application_name`

## Selected Features

| Feature | Calculation | Meaning | Important interpretation limits |
|---|---|---|---|
| `app_foreground_event_count` | Count all observed `applications_foreground` rows in the selected window. No deduplication is applied in the current selected definition. | Raw foreground-app event volume. This is useful as a relative measure of app/phone foreground activity when compared across patients using the same table and extraction rule. | A row is best understood as a logged foreground-app observation or transition, not necessarily a deliberate app opening, tap, or complete app session. The count can include duplicate database rows, system UI, launcher, keyboard, phone UI, and other operating-system foreground transitions. Therefore it should not be interpreted as the literal number of intentional app uses. |
| `unique_foreground_apps` | Count distinct `package_name` values observed in the selected window. | Breadth of observed foreground app context. Higher values suggest the foreground stream involved more distinct apps/packages. | Includes system and device-management packages unless a separate non-system version is later defined. Raw app/package names are privacy-sensitive and should not be used directly in clinical summaries. |
| `app_use_diversity` | Shannon entropy of foreground event distribution across `package_name` values in the selected window, using the same raw event rows as `app_foreground_event_count`. | Concentration versus spread of observed app foreground activity. Low diversity means events are concentrated in fewer packages; high diversity means events are more distributed across packages. | This is an aggregate distribution measure, not a content measure. It can be influenced by system apps, duplicate rows, keyboard transitions, and device-specific logging behavior. |

## Candidate Features Not Yet Selected

- `active_app_days`
- `non_system_app_event_count`
- `system_app_event_count`
- `top_app_share`
- `cavia_app_event_count` as data-quality support only

## Privacy Notes

- Raw app names and package names may reveal sensitive behavior.
- Final clinical summaries should use aggregate app-use features.
- Raw app lists should not be presented as phenotype labels without privacy review.

## Current Feature-Finding Result

The current feature-finding protocol scans patients from highest T1 score downward and uses the first patient with a valid 24-hour window inside the T1 week.

Exploratory acquisition window:

- Primary start: local midnight on the day after `T1_date_iso`.
- Timezone: Asia/Jerusalem.
- Primary end: primary start + 24 continuous hours.
- If there are no `applications_foreground` rows across the patient's mapped device IDs in the primary window, search the T1 week for the first timestamp that allows a complete 24-hour span.
- T1 week means local midnight on `T1_date_iso` through 7 days later.
- The fallback window must be marked as `exploratory_fallback_first_24h_span_within_T1_week` and not described as true day-after-T1 behavior.

Current exploratory result:

- Subject_ID_D: `041`
- global_T1: `119.4`
- window_rule: `exploratory_primary_day_after_T1`
- window_start_local: `2025-01-09 00:00:00+0200`
- window_end_local: `2025-01-10 00:00:00+0200`
- `app_foreground_event_count`: `698`
- `unique_foreground_apps`: `22`
- `app_use_diversity`: `3.593296482573857`

Important interpretation rules:

- A missing primary window is missing data, not zero app activity.
- The extracted features are based only on observed rows in the selected exploratory 24-hour acquisition window.
- The raw count remains useful for relative exploratory digital phenotyping, but it must be described as a table-derived foreground-event count rather than a direct behavioral count.

## Possible Future Derived Features

If later validation shows that duplicates or system-app transitions materially distort comparisons, add parallel derived features such as:

- deduplicated foreground events
- non-system foreground events
- system-event fraction

These would be new features, not replacements for the current raw feature.
