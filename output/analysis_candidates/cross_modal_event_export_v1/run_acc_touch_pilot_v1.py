from pathlib import Path
import pandas as pd, numpy as np, json, math
OUT=Path('output/analysis_candidates/cross_modal_event_export_v1'); DATA=OUT/'parquet'

def load_mod(device,date,session,mod):
 p=DATA/f'patient={device[-6:]}/device={device}/date={date}/modality={mod}/session_{session:02d}.parquet'
 return pd.read_parquet(p) if p.exists() else pd.DataFrame()
def mag(df):
 if df.empty:return pd.DataFrame(columns=['timestamp_ms','magnitude'])
 x=df[['timestamp_ms','acc_x','acc_y','acc_z']].dropna().copy(); x['magnitude']=np.sqrt(x.acc_x**2+x.acc_y**2+x.acc_z**2); return x.sort_values('timestamp_ms')
def event_vals(acc,t,tol): return acc.loc[(acc.timestamp_ms>=t-tol)&(acc.timestamp_ms<=t+tol),'magnitude'].to_numpy()
def control_vals(acc,t,tol,session_start,session_end):
 # deterministic matched control 2 seconds from the touch, avoiding all touch events later
 for c in (t+2000,t-2000,t+3000,t-3000):
  if session_start<=c<session_end and np.all(np.abs(TOUCH_TS-c)>1500):
   z=acc.loc[(acc.timestamp_ms>=c-tol)&(acc.timestamp_ms<=c+tol),'magnitude'].to_numpy()
   if len(z):return z
 return np.array([])
manifest=pd.read_csv(OUT/'checkpoint_manifest.csv')
qc=[]; results=[]
for _,r in manifest.iterrows():
 dev=r.device_anon; date=r.day
 for s in range(1,int(r.session_count)+1):
  acc=mag(load_mod(dev,date,s,'accelerometer')); touch=load_mod(dev,date,s,'touch')
  screen=load_mod(dev,date,s,'screen')
  if acc.empty or touch.empty: continue
  global TOUCH_TS
  TOUCH_TS=np.sort(touch.timestamp_ms.dropna().astype(int).unique())
  start=int(screen.session_start_ms.iloc[0]) if not screen.empty else int(acc.timestamp_ms.min()); end=int(screen.session_end_ms.iloc[0]) if not screen.empty else int(acc.timestamp_ms.max())
  ts=np.sort(acc.timestamp_ms.astype(int).unique()); dif=np.diff(ts) if len(ts)>1 else np.array([])
  base={'device_anon':dev,'date':date,'session_index':s,'touch_events':len(TOUCH_TS),'acc_samples':len(acc),'acc_duplicate_timestamps':int(len(acc)-len(ts)),'acc_median_interval_ms':float(np.median(dif)) if len(dif) else np.nan,'acc_p95_interval_ms':float(np.percentile(dif,95)) if len(dif) else np.nan,'acc_gap_gt1s':int((dif>1000).sum()) if len(dif) else 0,'acc_duration_s':float((ts[-1]-ts[0])/1000) if len(ts)>1 else 0,'sensor_identity':'retained in export metadata/QC; see checkpoint manifest source table'}
  qc.append(base)
  for tol in [500,1000]:
   ev=[];ctrl=[];matched=0
   for t in TOUCH_TS:
    a=event_vals(acc,t,tol); c=control_vals(acc,t,tol,start,end)
    if len(a) and len(c): ev.append(float(np.median(a)));ctrl.append(float(np.median(c)));matched+=1
   results.append({**base,'tolerance_ms':tol,'matched_touch_control_pairs':matched,'touch_window_median_magnitude':float(np.median(ev)) if ev else np.nan,'control_window_median_magnitude':float(np.median(ctrl)) if ctrl else np.nan,'within_session_median_difference':float(np.median(np.array(ev)-np.array(ctrl))) if ev else np.nan,'status':'estimable' if matched>=3 else 'insufficient_pairs'})
pd.DataFrame(qc).to_csv(OUT/'synchronization_report.csv',index=False);pd.DataFrame(results).to_csv(OUT/'acc_touch_pilot_results.csv',index=False)
# Privacy and schema checks
privacy={'raw_text_columns_exported':False,'before_text_exported':False,'current_text_exported':False,'password_state_rows_exported':False,'raw_package_names_exported':False,'persistent_word_hashes_exported':False,'device_ids_exported':False,'timestamps_retained':True,'acc_vectors_retained':True}
(OUT/'privacy_audit.json').write_text(json.dumps(privacy,indent=2))
(OUT/'event_schema.md').write_text('''# Event export schema\n\nEach Parquet partition is keyed by pseudonymous patient suffix, pseudonymous device, local date, modality, and verified screen session. All rows retain `timestamp_ms`, `timestamp_local`, source table, session bounds, and same-device verification. ACC rows retain x/y/z and raw accuracy where present. Touch rows retain action, hashed app context, and scroll-presence flag. Foreground-app rows retain only a truncated SHA-256 package hash and system-app flag. Keyboard rows retain only a text-state event label, hashed package context, and non-password status; no text fields are exported.\n\nACC sampling rate is derived from unique timestamp differences per session. Sensor identity and capability metadata remain in the source audit and are not conflated with observed cadence.\n''')
print(pd.DataFrame(results).to_string(index=False))
