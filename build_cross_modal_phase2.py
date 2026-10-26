from pathlib import Path
import pandas as pd, json, hashlib
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output/analysis_candidates/cross_modal_feature_discovery_v2'; OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'output/analysis_candidates/phase2_feature_review'
files={
 'keyboard':BASE/'keyboard/keyboard_sample_rows.csv',
 'screen':BASE/'screen/screen_sample_rows.csv',
 'touch':BASE/'touch/touch_sample_rows.csv',
 'applications_foreground':BASE/'applications_foreground/applications_foreground_sample_rows.csv',
 'plugin_activity':BASE/'plugin_google_activity_recognition/plugin_google_activity_recognition_sample_rows.csv',
}
rows=[]
for name,p in files.items():
 d=pd.read_csv(p)
 raw=d.get('data',pd.Series(dtype=str)).astype(str)
 device=d['device_id'].dropna().astype(str).iloc[0] if len(d) else ''
 rows.append({'table':name,'saved_source':str(p.relative_to(ROOT)),'saved_rows':len(d),'distinct_timestamp_device_rows':int(d[['timestamp','device_id']].drop_duplicates().shape[0]) if len(d) else 0,'timestamp_unit':'milliseconds since epoch','local_timezone':'Asia/Jerusalem in archived local_datetime','device_id_scope':'one selected device' if device else 'none','device_anon':'device_01' if device else 'none','raw_text_exported':'no','event_level_sufficient_for_session_reconstruction':'no','status':'review sample only; insufficient for pilot'})
pd.DataFrame(rows).to_csv(OUT/'synchronization_audit.csv',index=False)
# Timeline with no raw text or package labels; first 20 saved sample records only.
timeline=[]
all_events=[]
for name,p in files.items():
 d=pd.read_csv(p)
 if not len(d): continue
 d=d.head(20).copy(); d['timestamp']=pd.to_numeric(d['timestamp'],errors='coerce')
 t0=d['timestamp'].min()
 for _,r in d.iterrows():
  all_events.append({'event_type':name,'relative_seconds':round((r['timestamp']-t0)/1000,3),'timestamp_ms':int(r['timestamp']),'device_anon':'device_01'})
for e in sorted(all_events,key=lambda z:z['timestamp_ms']): timeline.append(e)
pd.DataFrame(timeline).to_csv(OUT/'example_anonymized_timeline.csv',index=False)
# Requested features are deliberately blocked until full event-level rows are available.
features=['touch_events_per_screen_active_minute','within_session_touch_interval_median_ms','within_session_touch_interval_iqr_ms','long_inactive_gaps_within_screen_active_session','foreground_app_transitions_per_screen_active_minute','median_observed_foreground_app_episode_duration_ms','keyboard_snapshot_interval_by_application']
pd.DataFrame([{'feature':f,'status':'not computed','eligible_patients':None,'eligible_sessions':None,'median_events_per_session':None,'match_rate':None,'missingness':None,'reason':'Saved files are small review samples; SensorDB unavailable for bounded full-event query; session boundaries and censoring cannot be established.'} for f in features]).to_csv(OUT/'pilot_feature_table.csv',index=False)
# Window comparison blocked for same reason.
pd.DataFrame([{'window_minutes':w,'status':'not computed','eligible_patients':None,'eligible_sessions':None,'recording_frequency_dependence':'not estimable','reason':'No complete event-level synchronized episodes available.'} for w in [1,5,10,15]]).to_csv(OUT/'short_window_coverage_stability.csv',index=False)
# ACC assessment
pd.DataFrame([{'source':'accelerometer','status':'blocked','evidence':'Archived pilot has dense raw sample (~3,202 rows/5 min) but no keyboard/app episode event-level join; live DB unavailable.','jerk_calculated':False,'next_step':'bounded same-device query; deduplicate timestamps; estimate sampling; choose raw vs gravity-compensated signal before jerk.'},{'source':'linear_accelerometer','status':'blocked','evidence':'No rows in checked T1-week windows.','jerk_calculated':False,'next_step':'do not treat missing as zero; locate a protocol-valid raw window first.'}]).to_csv(OUT/'accelerometer_synchronization_assessment.csv',index=False)
# Literature implementation-status copy
lit=pd.read_csv(ROOT/'output/analysis_candidates/cross_modal_feature_discovery_v1/literature_to_feature_matrix.csv')
lit['phase2_implementation_status']='not implemented; synchronization pilot blocked by unavailable SensorDB and insufficient saved event-level samples'
lit['phase2_limitation']='No true timestamp-level overlap was claimed; literature features use richer key-event/proprietary streams.'
lit.to_csv(OUT/'literature_to_feature_matrix_v2.csv',index=False)
readme='''# Cross-Modal Phase 2 — Timestamp Synchronization Pilot\n\n## Decision\nThe synchronization pilot was stopped before feature calculation. The saved event-level files are small review samples, not complete patient episodes: keyboard, screen, touch, foreground-app and activity-recognition files each contain only the archived sample rows. They cannot support session reconstruction, censoring, patient-level overlap, or 1/5/10/15-minute stability estimates.\n\nA bounded SensorDB connection was attempted and failed with: `DatabaseError 2005: Unknown MySQL server host applebaum-sensor-data-prod-db-1.ch6c2iwae148.us-west-2.rds.amazonaws.com`. Because timestamp-level synchronization could not be verified, no cross-table feature was calculated and no same-calendar-day availability was treated as simultaneous recording.\n\n## What was verified\nArchived records use millisecond epoch timestamps and preserve Asia/Jerusalem local timestamps. They contain device identifiers; the review samples are from one selected device. Duplicate handling is possible using timestamp + device ID, but the saved samples are too sparse and censored to infer complete sessions. Keyboard text and app labels were not exported into the Phase 2 outputs.\n\n## Feature status\nAll seven requested feature rows are marked `not computed` in `pilot_feature_table.csv`. The requested 1-, 5-, 10- and 15-minute comparison is marked `not computed` in `short_window_coverage_stability.csv`. The example timeline is anonymized and descriptive only; it is not an episode reconstruction.\n\n## ACC assessment\nThe archived accelerometer pilot contains approximately 3,202 rows in five minutes (~10.7 Hz), but no event-level keyboard/app episode join. Jerk was not calculated. Linear accelerometer remains blocked because no rows were found in checked T1-week windows. Any future jerk feature must first define raw versus gravity-compensated acceleration, deduplicate timestamps, quantify irregular sampling and resample only within valid continuous chunks.\n\n## Next executable step\nRestore SensorDB connectivity, then run a bounded same-device query for a coverage-diverse sample selected without cognition. Retrieve complete keyboard, screen, touch and foreground-app rows for one 24-hour T1 window, reconstruct only semantically supported screen-unlocked sessions, and calculate the seven features with explicit boundary censoring.\n'''
(OUT/'README_cross_modal_phase2.md').write_text(readme)
(OUT/'episode_definitions.md').write_text('''# Episode definitions (prespecified, pending data access)\n\n- Screen-active session: begin only after a verified screen-unlocked/on event; end at the next verified lock/off event; censor at window boundaries.\n- Touch within session: retain same-device touch timestamps in the half-open session interval; deduplicate exact timestamp/device/action rows.\n- Foreground-app episode: contiguous same-package observations inside a verified screen-active session; do not infer duration from a single isolated package row.\n- Keyboard application context: retain same-device keyboard text-state snapshots only when package context is present; compute snapshot intervals after duplicate removal; do not call them keypress intervals.\n- Long inactive gap: a gap between consecutive matched events inside a session, reported only after complete event retrieval; threshold must be prespecified before analysis.\n''')
# Add phase2 implementation note to the v1 register without altering its table.
reg=ROOT/'output/analysis_candidates/cross_modal_feature_discovery_v1/CROSS_MODAL_LITERATURE_REGISTER.md'
with reg.open('a') as f:
 f.write('''\n## Phase 2 implementation status — 2026-10-22\n\nThe timestamp synchronization pilot was attempted using saved event samples and a bounded SensorDB connection. Saved files were review samples rather than complete episodes, and the database host was unreachable (`Unknown MySQL server host`). Therefore no literature-derived cross-table feature was implemented, no simultaneous overlap was claimed, and no ACC jerk was calculated. The implementation-status copy is `cross_modal_feature_discovery_v2/literature_to_feature_matrix_v2.csv`.\n''')
print('wrote',OUT)
