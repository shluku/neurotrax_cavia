"""Read backup progress without accessing SQL or sensor contents."""
from __future__ import annotations

import json
import math
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP = Path("/Volumes/SENSORDATA_MAIN/sensordata_backup/full_raw_motion")
SERVICE = ROOT / "output/operations/motion_backup"


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def snapshot(root=BACKUP, service=SERVICE):
    plan = read_json(root / "backup_plan.json")
    state = read_json(root / "status.json")
    supervisor = read_json(service / "supervisor_status.json")
    records, warnings = {}, []
    try:
        for line in (root / "completed_chunks.jsonl").read_text().splitlines():
            try:
                record = json.loads(line)
                records[record["relative_path"]] = record
            except (ValueError, KeyError):
                warnings.append("A checkpoint record is incomplete; it is excluded from progress.")
    except OSError:
        pass
    rows = []
    for table in plan.get("tables", []):
        meta = plan["metadata"][table]
        span = max(0, (meta["max_id"] or 0) - (meta["min_id"] or 0) + 1)
        expected = math.ceil(span / plan["chunk_id_span"])
        done = [r for r in records.values() if r["table"] == table]
        verified = []
        for r in done:
            path = root / r["relative_path"]
            try:
                if path.stat().st_size == r["compressed_bytes"]:
                    verified.append(r)
                else:
                    warnings.append(f"Archive size changed: {path.name}")
            except OSError:
                warnings.append(f"Archive unavailable: {path.name}")
        n = len(verified)
        rows.append({"table": table, "completed": n, "total": expected,
                     "fraction": n / expected if expected else 0,
                     "compressed_bytes": sum(r["compressed_bytes"] for r in verified),
                     "status": "Complete" if n == expected else ("In progress" if state.get("table") == table and state.get("status") == "running" else "Queued")})
    active = root / state.get("relative_path", "nonexistent")
    if "relative_path" not in state and state.get("table") and "lower_id" in state:
        table = state["table"]
        active = root / table / f"{table}_id_{state['lower_id']}_to_{state['upper_id_exclusive']}_exclusive.sql.zst"
    partial = active.with_suffix(active.suffix + ".partial")
    try:
        stats = partial.stat()
        active_bytes, age = stats.st_size, max(0, time.time() - stats.st_mtime)
    except OSError:
        active_bytes, age = 0, None
    times = [r["elapsed_seconds"] for r in records.values() if not r.get("recovered_verified_archive") and r.get("elapsed_seconds", 0) > 0]
    total, completed = sum(r["total"] for r in rows), sum(r["completed"] for r in rows)
    # A deliberately provisional extrapolation by chunk, not row or byte percentage.
    eta = (total - completed) * sum(times[-20:]) / len(times[-20:]) if len(times) >= 3 else None
    try:
        free = shutil.disk_usage(root).free
    except OSError:
        free = None
    return {"plan": plan, "state": state, "supervisor": supervisor, "tables": rows,
            "total_chunks": total, "completed_chunks": completed,
            "fraction": completed / total if total else 0,
            "compressed_bytes": sum(r["compressed_bytes"] for r in rows),
            "active_bytes": active_bytes, "active_write_age_seconds": age,
            "free_bytes": free, "estimated_remaining_seconds": eta, "warnings": warnings}


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
