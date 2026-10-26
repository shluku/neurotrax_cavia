"""Prepare or install project-specific launchd agents; no credentials in plists."""
import argparse
import os
import plistlib
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREPARED = ROOT / "operations/launchagents"
LOGS = ROOT / "output/operations/motion_backup"


def prepare():
    PREPARED.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    programs = {
        "local.research-dbeaver.motion-backup": [str(ROOT / ".venv/bin/python3"), "-u", str(ROOT / "supervise_motion_backup.py")],
        "local.research-dbeaver.dashboard": [str(ROOT / ".venv/bin/python3"), "-m", "streamlit", "run", str(ROOT / "streamlit_app.py"), "--server.port", "8510", "--server.address", "127.0.0.1", "--server.headless", "true"],
    }
    paths = []
    for label, arguments in programs.items():
        spec = {"Label": label, "ProgramArguments": arguments, "WorkingDirectory": str(ROOT),
                "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 60,
                "ProcessType": "Background", "ExitTimeOut": 45,
                "EnvironmentVariables": {"PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONUNBUFFERED": "1"},
                "StandardOutPath": str(LOGS / f"{label}.out.log"),
                "StandardErrorPath": str(LOGS / f"{label}.err.log")}
        path = PREPARED / f"{label}.plist"
        path.write_bytes(plistlib.dumps(spec))
        paths.append(path)
    return paths


def stop_existing(pid, expected):
    if not pid:
        return
    result = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "command="], text=True, capture_output=True)
    if result.returncode:
        return
    if expected not in result.stdout:
        raise RuntimeError(f"PID {pid} does not match the expected project process")
    os.kill(pid, signal.SIGINT)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(.5)
    raise RuntimeError(f"Process {pid} has not stopped; installation paused")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--backup-pid", type=int)
    parser.add_argument("--dashboard-pid", type=int)
    args = parser.parse_args()
    paths = prepare()
    for path in paths:
        subprocess.run(["/usr/bin/plutil", "-lint", str(path)], check=True)
    if not args.install:
        return
    target = Path.home() / "Library/LaunchAgents"
    target.mkdir(parents=True, exist_ok=True)
    # Validate that this is a first install before stopping existing work.
    for path in paths:
        if (target / path.name).exists():
            raise FileExistsError(f"Service already installed: {target / path.name}")
    stop_existing(args.backup_pid, "backup_motion_tables_to_drive.py")
    stop_existing(args.dashboard_pid, "streamlit")
    for path in paths:
        installed = target / path.name
        installed.write_bytes(path.read_bytes())
        installed.chmod(0o644)
        subprocess.run(["/bin/launchctl", "bootstrap", f"gui/{os.getuid()}", str(installed)], check=True)
        print(f"installed={installed}", flush=True)


if __name__ == "__main__":
    main()
