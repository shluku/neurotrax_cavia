# Independent motion backup and remote follow-up

Installed 2026-09-14 on this Mac. The backup and Streamlit are managed by macOS launchd, independently of the Codex/chat terminal process.

## Services and recovery

| Service | Purpose |
|---|---|
| `local.research-dbeaver.motion-backup` | Runs `supervise_motion_backup.py`, which owns one backup worker |
| `local.research-dbeaver.dashboard` | Keeps Streamlit available on 127.0.0.1:8510 |

Installed definitions: `~/Library/LaunchAgents/local.research-dbeaver.motion-backup.plist` and `~/Library/LaunchAgents/local.research-dbeaver.dashboard.plist`. Reviewable definitions and installer are in `operations/launchagents/` and `install_motion_backup_services.py`.

- Closing this chat, Codex, ChatGPT, or the terminal does not stop these services.
- macOS restarts a failed supervisor or dashboard, with a 60-second launch throttle.
- The supervisor retries an unsuccessful worker after 1–15 minutes, waits for the drive to return, and restarts a worker after 30 minutes without checkpoint/file-size progress.
- Completed, verified chunks are retained. An interrupted current chunk restarts; its partial file is preserved.
- A verified receipt recovers a chunk if interruption occurs between final file publication and manifest append. A torn final manifest line is preserved separately and recovered on resume.
- `caffeinate -is` prevents idle sleep while exporting; system sleep prevention applies on AC power.
- These are user LaunchAgents: after a reboot, log into this macOS account and unlock/mount the drive. They do not run before login or while the Mac is shut down. Keep the lid open, power and networking connected, and the drive attached. Hardware failure, full disks, unavailable credentials, and source-data integrity problems can still require intervention.
- Export progress is observed, not a substitute for an end-to-end row-count reconciliation. `zstd -t` validates each compressed stream, and SHA-256 is stored for future integrity checking.

No public dashboard endpoint has been created. The Streamlit address is local to this Mac.

## Live progress

Open [Raw Motion Backup](http://127.0.0.1:8510/?page=Raw%20Motion%20Backup).

The page refreshes every 10 seconds and shows verified chunk completion overall and per table, compressed bytes, the current partial file size, free disk space, service heartbeat, retry count, and a provisional ETA after three completed chunks. Chunk completion is not a row-count or byte-count percentage. Different tables and primary-key ranges can export at different speeds.

Primary evidence:

- External drive: `/Volumes/SENSORDATA_MAIN/sensordata_backup/full_raw_motion/backup_plan.json`, `completed_chunks.jsonl`, and `status.json`.
- Local supervisor heartbeat: `output/operations/motion_backup/supervisor_status.json`.
- Local worker log: `output/operations/motion_backup/worker.log`.
- Launchd logs: `output/operations/motion_backup/local.research-dbeaver.*.log`.

Read-only command for future validation:

```bash
.venv/bin/python3 motion_backup_status.py
```

The user can deliberately pause by creating `output/operations/motion_backup/PAUSE`; the supervisor stops the active worker at its next check. Remove that marker to allow it to resume. Do not run another manual backup alongside the service.

## Connect the ChatGPT phone app

Official instructions: [Remote](https://learn.chatgpt.com/docs/remote) and [Remote connections](https://learn.chatgpt.com/docs/remote-connections), checked 2026-09-14.

On this Mac, open ChatGPT Settings → Connections → Control this Mac → Set up/Add. Enable remote access and complete verification. Scan the displayed QR code with the phone, using the same ChatGPT account and workspace. In the phone app, open Remote, select this Mac, then an existing task or a new task in `research_dbeaver`. Availability depends on rollout and workspace policy.

Pairing requires the user on the phone and has not been completed by this installation. Remote chat needs the host's ChatGPT app running, awake, and online; the backup services continue independently. This setup does not publish Streamlit or automatically forward localhost to the phone.

The official docs support continuing existing host tasks. Visibility of this particular CLI-origin conversation in the desktop/mobile task list has not been verified. If it is absent, create a new Remote task on this Mac in the same project and use the handoff below. Do not move execution to a different/cloud host: the drive and database setup are on this Mac.

## Paste into a future Remote chat

> Open `/Users/ofirfizitsky/PycharmProjects/research_dbeaver`. Read `README_PROJECT_HANDOFF.md`, `RAW_MOTION_BACKUP_AND_KEYBOARD_ROADMAP.md`, and `RAW_MOTION_BACKUP_SERVICE.md`. Validate the existing launchd-managed full raw motion backup without starting a second worker. Check the supervisor heartbeat, verified manifests, current file growth, archive integrity records, disk space, and recent errors. Report ACC, rotation, gyroscope, and gravity progress and a qualified ETA. Preserve source data and all completed archives. Keyboard feature development is the next research session; Parquet conversion is deferred until later in 2026.
