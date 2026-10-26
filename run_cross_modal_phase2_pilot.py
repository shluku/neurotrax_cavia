from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import json, hashlib, math
import numpy as np, pandas as pd
from main import connect_sensordata_db

OUT=Path('output/analysis_candidates/cross_modal_feature_discovery_v2'); OUT.mkdir(parents=True,exist_ok=True)
# Coverage-selected without cognitive scores: archived pilot device 041 plus high multi-table device 039.
SAMPLES=[{'patient':'041','device':'d74f7acf-f82f-491d-90b9-d7321e6d4bcf','day':'2025-01-09'}, {'patient':'039','device':'72e21d84-c3cb-401a-8beb-4532f39f0688','day':'2025-01-13'}]
TZ=ZoneInfo('Asia/Jerusalem'); TABLES=['keyboard','screen','touch','applications_foreground']

def msday(day):
 s=datetime.fromisoformat(day).replace(tzinfo=TZ); return int(s.timestamp()*1000),int((s+timedelta(days=1)).timestamp()*1000)
def parse(data):
 try: return json.loads(data) if isinstance(data,str) else (data or {})
 except Exception: return {}
def fetch(cur,table,dev,start,end):
 if table=='applications_foreground': q="SELECT timestamp,device_id,data FROM applications_foreground WHERE device_id=%s AND timestamp >= %s AND timestamp < %s ORDER BY timestamp"
 else: q=f"SELECT timestamp,device_id,data FROM {table} WHERE device_id=%s AND timestamp >= %s AND timestamp < %s ORDER BY timestamp"
 cur.execute(q,(dev,start,end)); return [{'timestamp':int(r[0]),'device_id':r[1],'data':parse(r[2])} for r in cur.fetchall()]
def dedup(rows,table):
 seen=set(); out=[]
 for r in rows:
  d=r['data'];
  if table=='keyboard': key=(r['timestamp'],r['device_id'],str(d.get('package_name','')),str(d.get('is_password','')),str(d.get('before_text','')),str(d.get('current_text','')))
  elif table=='applications_foreground': key=(r['timestamp'],r['device_id'],str(d.get('package_name','')),str(d.get('is_system_app','')))
  elif table=='touch': key=(r['timestamp'],r['device_id'],str(d.get('touch_app','')),str(d.get('touch_action','')),str(d.get('scroll_items','')))
  else: key=(r['timestamp'],r['device_id'],str(d.get('screen_status','')))
  if key not in seen: seen.add(key); out.append(r)
 return out

def sessions(screen):
 # Verified unlock sessions only: status 3 opens; status 2/0 closes. Status 1 alone is not treated as unlocked.
 s=sorted(screen,key=lambda r:r['timestamp']); out=[]; st=None
 for r in s:
  code=str(r['data'].get('screen_status',''))
  if code=='3' and st is None: st=r['timestamp']
  elif code in {'0','2'} and st is not None:
   if r['timestamp']>st: out.append((st,r['timestamp'],'closed'))
   st=None
 if st is not None: out.append((st,s[-1]['timestamp'],'right_censored'))
 return out

def inside(rows,a,b): return [r for r in rows if a<=r['timestamp']<b]
def intervals(ts):
 x=sorted(set(int(t) for t in ts)); return np.diff(x) if len(x)>1 else np.array([])

def session_features(sess,rows):
 a,b,closure=sess; t=inside(rows['touch'],a,b); apps=inside(rows['applications_foreground'],a,b); keys=inside(rows['keyboard'],a,b)
 ti=intervals([r['timestamp'] for r in t]);
 # app transitions and same-package episodes (episode duration requires >=2 observations)
 ap=sorted(apps,key=lambda r:r['timestamp']); transitions=0; episodes=[]; prev=None; cur_start=None; cur_last=None
 for r in ap:
  pkg=str(r['data'].get('package_name',''))
  if prev is None: prev=pkg; cur_start=cur_last=r['timestamp']
  elif pkg!=prev:
   transitions+=1
   if cur_last>cur_start: episodes.append(cur_last-cur_start)
   prev=pkg; cur_start=cur_last=r['timestamp']
  else: cur_last=r['timestamp']
 if cur_last is not None and cur_last>cur_start: episodes.append(cur_last-cur_start)
 # keyboard intervals by package, password excluded; raw text is not written
 kgrp={}
 for r in keys:
  d=r['data'];
  if str(d.get('is_password','0')).lower() in {'1','true','yes'}: continue
  pkg=str(d.get('package_name',''))
  kgrp.setdefault(pkg,[]).append(r['timestamp'])
 ki=[]
 for ts in kgrp.values():
  z=intervals(ts); ki.extend(z[(z>0)&(z<=30000)])
 dur=max(0,b-a)/60000
 return {'session_start_ms':a,'session_end_ms':b,'session_closure':closure,'session_minutes':dur,'touch_events':len(t),'touch_events_per_active_minute':len(t)/dur if dur else np.nan,'touch_interval_median_ms':float(np.median(ti)) if len(ti) else np.nan,'touch_interval_iqr_ms':float(np.percentile(ti,75)-np.percentile(ti,25)) if len(ti) else np.nan,'touch_long_gap_count_gt30s':int((ti>30000).sum()) if len(ti) else 0,'app_events':len(apps),'app_transitions':transitions,'app_transitions_per_active_minute':transitions/dur if dur else np.nan,'app_episode_median_ms':float(np.median(episodes)) if episodes else np.nan,'app_episode_count':len(episodes),'keyboard_snapshots':len(keys),'keyboard_interval_median_ms':float(np.median(ki)) if len(ki) else np.nan,'keyboard_interval_iqr_ms':float(np.percentile(ki,75)-np.percentile(ki,25)) if len(ki) else np.nan,'keyboard_valid_intervals':len(ki),'keyboard_package_count':len(kgrp)}

conn=connect_sensordata_db(); cur=conn.cursor(); coverage=[]; feature_rows=[]; window_rows=[]; timeline=[]
for s in SAMPLES:
 start,end=msday(s['day']); data={}
 for t in TABLES:
  raw=fetch(cur,t,s['device'],start,end); clean=dedup(raw,t); data[t]=clean; coverage.append({'patient':s['patient'],'device_anon':'device_'+s['patient'],'day':s['day'],'table':t,'raw_rows':len(raw),'deduplicated_rows':len(clean),'duplicate_rows_removed':len(raw)-len(clean),'first_timestamp_ms':min([r['timestamp'] for r in clean],default=np.nan),'last_timestamp_ms':max([r['timestamp'] for r in clean],default=np.nan)})
 for r in data['screen'][:100]: timeline.append({'patient_anon':'patient_'+s['patient'],'device_anon':'device_'+s['patient'],'event_type':'screen','relative_seconds':round((r['timestamp']-start)/1000,3),'status_code':str(r['data'].get('screen_status',''))})
 sess=sessions(data['screen'])
 for i,ss in enumerate(sess,1):
  f=session_features(ss,data); f.update({'patient_anon':'patient_'+s['patient'],'device_anon':'device_'+s['patient'],'day':s['day'],'session_index':i}); feature_rows.append(f)
  a,b,closure=ss
  for w in [1,5,10,15]:
   k=0; cur_a=a
   while cur_a < b:
    cur_b=min(cur_a+w*60000,b)
    wf=session_features((cur_a,cur_b,'window_censored' if cur_b==b and cur_b-cur_a<w*60000 else 'closed'),data)
    wf.update({'patient_anon':'patient_'+s['patient'],'device_anon':'device_'+s['patient'],'day':s['day'],'session_index':i,'window_minutes':w,'window_index':k})
    window_rows.append(wf); k+=1; cur_a=cur_b
cur.close(); conn.close()
pd.DataFrame(coverage).to_csv(OUT/'pilot_event_coverage.csv',index=False)
pd.DataFrame(feature_rows).to_csv(OUT/'pilot_session_feature_table.csv',index=False)
pd.DataFrame(timeline).to_csv(OUT/'example_anonymized_timelines_live.csv',index=False)
pd.DataFrame(window_rows).to_csv(OUT/'pilot_window_sensitivity.csv',index=False)
# Summary and reproducibility status.
pd.DataFrame([{'metric':'patients_with_verified_unlocked_sessions','value':len(set((f['patient_anon'] for f in feature_rows))),'definition':'at least one screen status 3 followed by status 2/0 or right censoring'}, {'metric':'verified_sessions','value':len(feature_rows),'definition':'same-device screen-unlocked sessions in two coverage-selected days'}, {'metric':'raw_text_exported','value':False,'definition':'keyboard text parsed only in memory and discarded'}, {'metric':'cognitive_outcomes_used_for_selection','value':False,'definition':'sample selected from event coverage, not cognition'}]).to_csv(OUT/'pilot_summary.csv',index=False)
print('patients',len(set(f['patient_anon'] for f in feature_rows)),'sessions',len(feature_rows))
