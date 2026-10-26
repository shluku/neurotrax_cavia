from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import json, math
import numpy as np,pandas as pd
from main import connect_sensordata_db
OUT=Path('output/analysis_candidates/cross_modal_acc_priority_v1'); OUT.mkdir(parents=True,exist_ok=True)
TZ=ZoneInfo('Asia/Jerusalem')
# Chosen from event-table coverage only; no cognition-based selection.
SAMPLES=[('041','d74f7acf-f82f-491d-90b9-d7321e6d4bcf','2025-01-09'),('039','72e21d84-c3cb-401a-8beb-4532f39f0688','2025-01-13')]
def local_day(ms): return datetime.fromtimestamp(ms/1000,tz=timezone.utc).astimezone(TZ).date().isoformat()
def day_bounds(day):
 s=datetime.fromisoformat(day).replace(tzinfo=TZ); return int(s.timestamp()*1000),int((s+timedelta(days=1)).timestamp()*1000)
def parse(x):
 try:return json.loads(x) if isinstance(x,str) else (x or {})
 except:return {}
def qrows(cur,table,dev,a,b):
 cur.execute(f'SELECT timestamp,data FROM {table} WHERE device_id=%s AND timestamp >= %s AND timestamp < %s ORDER BY timestamp',(dev,a,b)); return [(int(x[0]),parse(x[1])) for x in cur.fetchall()]
def dedup(rows):
 seen=set(); out=[]
 for t,d in rows:
  k=(t,str(d.get('double_values_0')),str(d.get('double_values_1')),str(d.get('double_values_2')))
  if k not in seen: seen.add(k); out.append((t,d))
 return out
def sessions(screen):
 out=[];start=None
 for t,d in screen:
  c=str(d.get('screen_status',''))
  if c=='3' and start is None:start=t
  elif c in {'0','2'} and start is not None and t>start:out.append((start,t,'closed'));start=None
 if start is not None and screen:out.append((start,screen[-1][0],'right_censored'))
 return out
def acc_features(rows,keyboard_ts=None):
 vals=[]
 for t,d in rows:
  try: vals.append((t,np.array([float(d[f'double_values_{i}']) for i in range(3)])))
  except: pass
 if len(vals)<2:return {'acc_n':len(vals),'acc_duration_s':0,'sampling_median_ms':np.nan,'sampling_p95_ms':np.nan,'gap_fraction_gt1s':np.nan,'mag_mean':np.nan,'mag_sd':np.nan,'mag_iqr':np.nan,'moving_fraction':np.nan,'jerk_n':0,'jerk_median':np.nan,'jerk_iqr':np.nan,'jerk_p90':np.nan,'median_mag':np.nan,'gravity_like':False}
 vals.sort(key=lambda x:x[0]); ts=np.array([x[0] for x in vals]); xyz=np.stack([x[1] for x in vals]); dt=np.diff(ts)/1000; mag=np.linalg.norm(xyz,axis=1); med=float(np.median(mag)); move=np.abs(mag-med)>0.2
 good=(dt>0)&(dt<=1.0); jerk=np.linalg.norm(np.diff(xyz,axis=0)[good],axis=1)/dt[good] if good.any() else np.array([])
 kset=set(keyboard_ts or []); kactive=np.array([any(abs(int(t)-kt)<=1000 for kt in kset) for t in ts])
 return {'acc_n':len(vals),'acc_duration_s':float((ts[-1]-ts[0])/1000),'sampling_median_ms':float(np.median(dt)*1000),'sampling_p95_ms':float(np.percentile(dt,95)*1000),'gap_fraction_gt1s':float((dt>1).mean()),'mag_mean':float(np.mean(mag)),'mag_sd':float(np.std(mag,ddof=1)),'mag_iqr':float(np.percentile(mag,75)-np.percentile(mag,25)),'moving_fraction':float(np.mean(move)),'jerk_n':int(len(jerk)),'jerk_median':float(np.median(jerk)) if len(jerk) else np.nan,'jerk_iqr':float(np.percentile(jerk,75)-np.percentile(jerk,25)) if len(jerk) else np.nan,'jerk_p90':float(np.percentile(jerk,90)) if len(jerk) else np.nan,'median_mag':med,'gravity_like':bool(8.0<=med<=11.5)}
conn=connect_sensordata_db();cur=conn.cursor(); cover=[]; segs=[]; device_days=[]
for patient,dev,day in SAMPLES:
  a,b=day_bounds(day); device_days.append((dev,day))
  screen=qrows(cur,'screen',dev,a,b); touch=qrows(cur,'touch',dev,a,b); apps=qrows(cur,'applications_foreground',dev,a,b); keys=qrows(cur,'keyboard',dev,a,b)
  # event coverage only; raw text never written
  cover.append({'device_anon':'dev_'+dev[:6],'day':day,'screen_rows':len(screen),'touch_rows':len(touch),'app_rows':len(apps),'keyboard_rows':len(keys)})
  ss=sessions(screen)
  for i,(sa,sb,close) in enumerate(ss[:3],1):
   # limit each session to first 60 seconds, bounded and comparable
   eb=min(sb,sa+60000); acc=qrows(cur,'accelerometer',dev,sa,eb); acc=dedup(acc)
   kt=[t for t,d in keys if sa<=t<eb]
   f=acc_features(acc,kt); f.update({'device_anon':'dev_'+dev[:6],'day':day,'session_index':i,'session_start_ms':sa,'session_end_ms':eb,'session_closure':close,'keyboard_snapshots_in_segment':len(kt),'acc_segment_type':'keyboard_associated' if kt else 'screen_active_no_keyboard'})
   segs.append(f)
cur.close();conn.close()
pd.DataFrame(cover).to_csv(OUT/'acc_event_coverage.csv',index=False)
pd.DataFrame(segs).to_csv(OUT/'acc_synchronized_segments.csv',index=False)
# QC summary and longitudinal feasibility
s=pd.DataFrame(segs)
summary=[]
for c in ['acc_n','sampling_median_ms','sampling_p95_ms','gap_fraction_gt1s','mag_mean','mag_sd','mag_iqr','moving_fraction','jerk_n','jerk_median','jerk_iqr','jerk_p90']:
 summary.append({'metric':c,'n':int(s[c].notna().sum()) if c in s else 0,'median':s[c].median() if c in s else np.nan,'iqr':s[c].quantile(.75)-s[c].quantile(.25) if c in s else np.nan,'min':s[c].min() if c in s else np.nan,'max':s[c].max() if c in s else np.nan})
pd.DataFrame(summary).to_csv(OUT/'acc_qc_summary.csv',index=False)
pd.DataFrame([{'metric':'devices_with_live_queries','value':len(s.device_anon.unique()) if len(s) else 0},{'metric':'synchronized_segments','value':len(s)},{'metric':'segments_with_at_least_50_acc_samples','value':int((s.acc_n>=50).sum()) if len(s) else 0},{'metric':'segments_with_jerk','value':int(s.jerk_n.gt(0).sum()) if len(s) else 0},{'metric':'gravity_like_median_magnitude_segments','value':int(s.gravity_like.sum()) if len(s) else 0},{'metric':'keyboard_associated_segments','value':int(s.acc_segment_type.eq('keyboard_associated').sum()) if len(s) else 0},{'metric':'days_per_device_max','value':2}]).to_csv(OUT/'longitudinal_feasibility_summary.csv',index=False)
print('segments',len(s),'devices',s.device_anon.nunique() if len(s) else 0,'acc>=50',int((s.acc_n>=50).sum()) if len(s) else 0)
