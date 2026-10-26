"""Export one untouched ACC range beside the supervised worker for a speed test."""
from pathlib import Path
from time import monotonic

from backup_accelerometer_by_day import make_mysql_defaults_file
from backup_motion_tables_to_drive import dump_chunk

ROOT = Path("/Volumes/SENSORDATA_MAIN/sensordata_backup/full_raw_motion")
TABLE = "accelerometer"
LOWER, UPPER = 85_000_001, 90_000_001


def main():
    destination = ROOT / TABLE / f"{TABLE}_id_{LOWER}_to_{UPPER}_exclusive.sql.zst"
    if destination.exists() or destination.with_suffix(destination.suffix + ".partial").exists():
        raise SystemExit(f"Probe range already exists or is active: {destination}")
    defaults = make_mysql_defaults_file()
    started = monotonic()
    try:
        print(f"probe_start table={TABLE} lower={LOWER} upper_exclusive={UPPER}", flush=True)
        result = dump_chunk(TABLE, LOWER, UPPER, destination, defaults, ROOT / TABLE / "parallel_probe.log")
        elapsed = monotonic() - started
        print(f"probe_complete elapsed_seconds={elapsed:.3f} result={result}", flush=True)
    finally:
        defaults.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
