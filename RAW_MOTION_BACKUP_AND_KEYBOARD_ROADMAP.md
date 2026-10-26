# Full raw motion backup and keyboard follow-up

Requested and prepared: 2026-09-14, Asia/Jerusalem.

## Work order

1. Copy the full raw `accelerometer` table to the external drive as compressed SQL archives.
2. Continue sequentially with `rotation`, `gyroscope`, and `gravity`.
3. Retain the compressed originals for conversion to Parquet later in 2026.
4. Start a separate keyboard analysis session, reviewing existing work and developing new features.

This order supersedes the earlier immediate plan to proceed directly into ACC modeling. The four multi-device aggregation issues remain recorded in the ACC completion audit for later resolution.

“Copy” preserves the source database and existing archives. Full raw backups include every device, original row, timestamp duplicate, and JSON field. The existing study-specific ACC export is a different artifact: 7,343 compressed, timestamp-deduplicated patient-day files totaling 9.60 GB, already on the drive. It does not replace the full raw backup.

## Destination and format

Destination: `/Volumes/SENSORDATA_MAIN/sensordata_backup/full_raw_motion/`

Each table has independent `.sql.zst` files covering consecutive, nonoverlapping primary-key ranges. Each file includes the table schema and original SQL values, retaining the information needed for future Parquet conversion. The current conversion parser understands this SQL format; orchestration across chunks into a partitioned Parquet dataset will be needed later.

The runner is `backup_motion_tables_to_drive.py`. It:

- Freezes minimum/maximum `_id` per table and records live metadata before extraction.
- Exports five-million-ID ranges sequentially, without the patient/device filtering used for feature extraction.
- Uses streaming `mysqldump` and Zstandard level 3 with two compressor threads.
- Checks both subprocess exit codes, verifies each compressed stream with `zstd -t`, and records SHA-256, elapsed time, and compressed bytes.
- Publishes a completed archive only after verification, then records it in `completed_chunks.jsonl`.
- Resumes completed chunks after checking presence and file size. Stored SHA-256 hashes support a subsequent integrity audit; they are not recomputed on every resume.
- Preserves interrupted partial files for inspection and refuses untracked final archives.
- Prevents concurrent runs with a filesystem lock and checks for a 100 GB free-space reserve before each chunk.

This is a full-table archival workflow explicitly requested by the user. It uses bounded indexed `_id` ranges instead of the timestamp/device restrictions of patient feature extraction. No source SQL mutations are performed.

Each chunk has its own transaction. The frozen ID upper bounds exclude later inserted rows; the backup is not a single point-in-time database snapshot if existing records change during the run. Table size/row counts from MySQL metadata are estimates, not exact reconciliation counts.

## Time and space estimate

Live metadata read on 2026-09-14:

| Table | Estimated rows, billions | Database data + indexes, decimal TB | Historical-rate estimate |
|---|---:|---:|---:|
| accelerometer | 3.900 | 1.675 | 3.33 days |
| rotation | 3.824 | 1.736 | 3.27 days |
| gyroscope | 3.758 | 1.626 | 3.21 days |
| gravity | 3.744 | 1.625 | 3.20 days |
| Total | 15.226 | 6.662 | 13.01 days |

Calibration: the successful `linear_accelerometer` backup ran from 2026-08-29 20:52 UTC to 2026-08-30 08:23 UTC: 11.5167 hours. Its validated subsequent conversion reported 561,602,194 rows. The compressed SQL archive is 21,251,552,372 bytes. Row-scaled duration equals `estimated rows / 561602194 * 11.5167 hours`.

Planning allowance: roughly **3–5 days for ACC, another 9–15 days for the other three, or 12–20 days total**, assuming continuous operation and throughput broadly comparable to the earlier export. These are provisional extrapolations, not a measured rate for the new chunked runner. Slow queries, changing server/network throughput, sleep, disconnections, or retries can extend them. Refresh the estimate using several completed representative chunks.

Row-scaled archive size is about 576 GB total; scaling by database data bytes gives roughly 645 GB. Use **about 0.6–0.7 TB as an initial space estimate**, with substantial uncertainty because compression differs by sensor. Database indexes are not materialized in the SQL archive; the 6.66 TB source footprint is not the transferred compressed size. The drive currently has roughly 1.7 TiB free. Keep space for both archived SQL and the later Parquet copy, and reassess after the pilot.

## Commands and monitoring

Started on 2026-09-14: a one-chunk ACC pilot, followed by a full sequential runner launched with `--wait-for-lock`. The full runner waits for the pilot's exclusive lock, then resumes the same frozen plan. At this update the pilot is still writing its first chunk; no completed new-run throughput measurement is available yet. Read the external status and manifest for current progress rather than treating this note as live state.

Initial measured chunk (stops after one newly completed chunk):

```bash
.venv/bin/python3 -u backup_motion_tables_to_drive.py --max-chunks 1
```

Full sequential run/resume, using the same frozen plan:

```bash
.venv/bin/python3 -u backup_motion_tables_to_drive.py
```

To queue behind an active pilot, the launched command is `.venv/bin/python3 -u backup_motion_tables_to_drive.py --wait-for-lock`. This flag waits for the existing run instead of exporting concurrently.

Current evidence is on the external drive: `backup_plan.json`, `status.json`, and `completed_chunks.jsonl`. Logs are stored under each table's directory. Do not run two copies. Keep the computer awake, connected to the database, and the drive mounted throughout the run. This process does not schedule the later Parquet conversion or run keyboard analysis automatically.

## Keyboard session handoff

Start from the existing two-feature median-timespan T1 analysis and T1/T2 keyboard delta/PCA work:

- `PHASE_KEYBOARD_TWO_FEATURE_MEDIAN_TIMESPAN_PROTOCOL.md`
- `PHASE_KEYBOARD_T1_T2_DELTA_PCA_PROTOCOL.md`
- `phase_keyboard_two_feature_median_timespan.py`
- `phase_keyboard_t1_t2_delta_pca.py`
- `output/analysis_candidates/keyboard_two_feature_median_timespan/`
- `output/analysis_candidates/keyboard_t1_t2_delta_pca/`

The prior two features were selected after an exploratory nominal p<0.10 comparison. That analysis trims one lowest and one highest observed value per feature, preserving an untrimmed copy. Revisit these choices explicitly rather than treating them as independent validation.

In the new session, inspect the available keyboard fields and define additional features, their denominators, missingness, observation windows, and sensitivity analyses before evaluating associations. Preserve earlier outputs and record the new feature definitions separately. Specific new keyboard features have not yet been selected.
