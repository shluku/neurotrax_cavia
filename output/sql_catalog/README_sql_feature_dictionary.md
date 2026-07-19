# SQL Feature Dictionary Notes

This file summarizes manual feature-dictionary updates added after discovery-time query failures.

## Manual confirmations (no new SQL run)

1. `light`
- Confirmed key: `double_light_lux`
- Interpretation: ambient light in lux.
- PoC status: `optional_later`.
- Note: low lux can represent dark environment OR phone in pocket/bag.

2. `proximity`
- Confirmed key: `double_proximity`
- Interpretation: near/covered sensor context; device-dependent.
- PoC status: `optional_later`.

3. `barometer`
- Confirmed key: `double_values_0`
- Interpretation: likely atmospheric pressure (hPa/mbar).
- PoC status: `later_low_priority`.

## Generated files
- `sql_table_interpretation.csv`
- `sql_feature_dictionary.csv`

## Scope
- Discovery stage only.
- No SQL was executed for these tables in this update.
