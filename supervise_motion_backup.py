"""Run under launchd; wait for the drive, retry failures, and publish a heartbeat."""
from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from motion_backup_status import BACKUP, ROOT, SERVICE, read_json, snapshot

STOP = False


def stopping(signum, frame):
    global STOP
    STOP = True


def publish(status, **fields):
    record = {"status": status, "heartbeat_unix": time.time(), "supervisor_pid": os.getpid(), **fields}
    tmp = SERVICE / "supervisor_status.tmp"
    tmp.write_text(json.dumps(record, indent=2) + "\n")
    tmp.replace(SERVICE / "supervisor_status.json")


def pause(seconds):
    until = time.monotonic() + seconds
    while not STOP and time.monotonic() < until:
        time.sleep(min(1, max(0, until-time.monotonic())))


def stop_child(child):
    if child is None or child.poll() is not None:
        return
    os.killpg(child.pid, signal.SIGINT)
    try:
        child.wait(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait()


def main():
    SERVICE.mkdir(parents=True, exist_ok=True)
    lock = (SERVICE / "supervisor.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, stopping)
    child = awake = None
    retries = 0
    try:
        while not STOP:
            if (SERVICE / "PAUSE").exists():
                publish("paused_by_user", retries=retries)
                pause(15)
                continue
            if not Path("/Volumes/SENSORDATA_MAIN").is_mount():
                publish("waiting_for_drive", retries=retries)
                pause(15)
                continue
            if read_json(BACKUP / "status.json").get("status") == "complete":
                publish("complete", retries=retries)
                pause(60)
                continue
            # Run independently from the chat and prevent idle system sleep.
            awake = subprocess.Popen(["/usr/bin/caffeinate", "-is", "-w", str(os.getpid())])
            with (SERVICE / "worker.log").open("ab") as log:
                child = subprocess.Popen([str(ROOT / ".venv/bin/python3"), "-u",
                                          str(ROOT / "backup_motion_tables_to_drive.py")],
                                         cwd=ROOT, stdout=log, stderr=log, start_new_session=True)
                signature, last_change = None, time.monotonic()
                while child.poll() is None and not STOP:
                    try:
                        snap = snapshot()
                        new_signature = (snap["completed_chunks"], snap["active_bytes"], snap["state"].get("lower_id"))
                        if new_signature != signature:
                            signature, last_change = new_signature, time.monotonic()
                        publish("running", worker_pid=child.pid, retries=retries,
                                completed_chunks=snap["completed_chunks"], active_bytes=snap["active_bytes"])
                        if (SERVICE / "PAUSE").exists() or not Path("/Volumes/SENSORDATA_MAIN").is_mount():
                            stop_child(child)
                            break
                        if time.monotonic() - last_change > 1800:
                            publish("restarting_stalled_worker", worker_pid=child.pid, retries=retries)
                            stop_child(child)
                            break
                    except OSError:
                        stop_child(child)
                        break
                    pause(15)
                stop_child(child)
            awake.terminate()
            awake.wait()
            awake = None
            if STOP:
                break
            if read_json(BACKUP / "status.json").get("status") == "complete":
                continue
            retries += 1
            delay = min(900, 60 * 2 ** min(retries - 1, 4))
            publish("retry_wait", worker_returncode=child.returncode, retries=retries,
                    next_retry_unix=time.time()+delay)
            pause(delay)
    finally:
        stop_child(child)
        if awake is not None:
            awake.terminate()
            awake.wait()
        publish("supervisor_stopped", retries=retries)
        lock.close()


if __name__ == "__main__":
    main()
