from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import hashlib,json,time,os
import pandas as pd, numpy as np
from main import connect_sensordata_db

OUT=Path('output/analysis_candidates/cross_modal_repeated_day_export_v1'); DATA=OUT/'parquet'; DATA.mkdir(parents=True,exist_ok=True)
TZ=ZoneInfo('Asia/Jerusalem')
# Chosen only from the existing technical coverage matrix, never cognition scores.
TARGETS=[
 ('dev_72e21d','72e21d84-c3cb-401a-8beb-4532f39f0688','2025-01-13'),('dev_72e21d','72e21d84-c3cb-401a-8beb-4532f39f0688','2025-07-08'),
 ('dev_c9cc92','c9cc92f6-be86-4916-b1f6-d940e6d6d6ac','2025-01-13'),('dev_c9cc92','c9cc92f6-be86-4916-b1f6-d940e6d6d6ac','2025-07-10'),
 ('dev_1b799d','1b799d79-1303-44c4-97a7-ad56a19add13','2025-02-12'),('dev_1b799d','1b799d79-1303-44c4-97a7-ad56a19add13','2026-06-22'),
 ('dev_cc373e','cc373e47-1b4b-4e15-a7e7-7882510d4949','2025-01-06'),('dev_cc373e','cc373e47-1b4b-4e15-a7e7-7882510d4949','2025-04-20'),
 ('dev_ed3860','ed3860d6-8c63-4db3-a74f-263067f0a88f','2025-03-02'),('dev_ed3860','ed3860d6-8c63-4db3-a74f-263067f0a88f','2025-06-30')]
MAX_SESSIONS_PER_DAY=2; MAX_SESSION_SECONDS=600; RETRIES=2

def ms_bounds(day):
 a=datetime.fromisoformat(day).replace(tzinfo=TZ); b=a+timedelta(days=1); return int(a.timestamp()*1000),int(b.timestamp()*1000)
def parse(x):
 try:return json.loads(x) if isinstance(x,str) else (x or {})
 except:return {}
def package_hash(x):
 if not x:return None
 return hashlib.sha256(str(x).encode()).hexdigest()[:16]
def fetch(cur,t,dev,a,b,limit=200000):
 q=f"SELECT timestamp,device_id,data FROM {t} WHERE timestamp >= %s AND timestamp < %s AND device_id=%s ORDER BY timestamp LIMIT %s"
 cur.execute(q,(a,b,dev,limit)); return [(int(ts),did,parse(dat)) for ts,did,dat in cur.fetchall()]
def dedup(rows,t):
 seen=set();out=[]
 for ts,did,d in rows:
  if t=='screen': k=(ts,str(d.get('screen_status','')))
  elif t=='touch': k=(ts,str(d.get('touch_app','')),str(d.get('touch_action','')),str(d.get('scroll_items','')))
  elif t=='applications_foreground': k=(ts,str(d.get('package_name','')),str(d.get('is_system_app','')))
  elif t=='keyboard': k=(ts,str(d.get('package_name','')),str(d.get('is_password','')),str(d.get('before_text','')),str(d.get('current_text','')))
  else: k=(ts,str(d.get('double_values_0','')),str(d.get('double_values_1','')),str(d.get('double_values_2','')))
  if k not in seen: seen.add(k);out.append((ts,did,d))
 return out
def sessions(screen):
 out=[];s=None
 for ts,did,d in sorted(screen):
  code=str(d.get('screen_status',''))
  if code=='3' and s is None:s=ts
  elif code in {'0','2'} and s is not None and ts>s:out.append((s,ts,'closed'));s=None
 return out
def iso(ts): return datetime.fromtimestamp(ts/1000,timezone.utc).astimezone(TZ).isoformat()
def write_partition(rows, modality, patient, device, day, session_index):
 if not rows:return None
 p=DATA/f'patient={patient}/device={device}/date={day}/modality={modality}'
 p.mkdir(parents=True,exist_ok=True); path=p/f'session_{session_index:02d}.parquet'; pd.DataFrame(rows).to_parquet(path,index=False); return str(path)

manifest=[]; all_rows=[]; conn=connect_sensordata_db();cur=conn.cursor()
for device_anon,dev,day in TARGETS:
 key=f'{device_anon}_{day}'; marker=OUT/f'.checkpoint_{key}.json'
 if marker.exists(): manifest.append(json.loads(marker.read_text())); continue
 a,b=ms_bounds(day); rec={'target':key,'device_anon':device_anon,'day':day,'status':'started','started_at':datetime.now(timezone.utc).isoformat(),'session_count':0,'files':[]}
 try:
  raw={t:fetch(cur,t,dev,a,b) for t in ['screen','touch','applications_foreground','keyboard']}
  clean={t:dedup(raw[t],t) for t in raw}; ss=sessions(clean['screen'])
  eligible=[]
  for i,(s,e,cl) in enumerate(ss,1):
   if e-s>MAX_SESSION_SECONDS*1000:continue
   if not any(s<=x<e for x,_,_ in clean['touch']):continue
   eligible.append((i,s,e,cl))
  eligible=eligible[:MAX_SESSIONS_PER_DAY]
  rec['screen_sessions_total']=len(ss);rec['eligible_sessions']=len(eligible)
  for i,s,e,cl in eligible:
   rec['session_count']+=1
   # only query ACC inside selected verified sessions
   accraw=fetch(cur,'accelerometer',dev,s,e,limit=250000); acc=dedup(accraw,'accelerometer')
   qmap={'screen':[(x,did,d) for x,did,d in clean['screen'] if s<=x<e], 'touch':[(x,did,d) for x,did,d in clean['touch'] if s<=x<e], 'applications_foreground':[(x,did,d) for x,did,d in clean['applications_foreground'] if s<=x<e], 'keyboard':[(x,did,d) for x,did,d in clean['keyboard'] if s<=x<e], 'accelerometer':acc}
   for mod,rows in qmap.items():
    out=[]
    for ts,did,d in rows:
     base={'timestamp_ms':ts,'timestamp_local':iso(ts),'patient_anon':f'patient_{device_anon[-6:]}','device_anon':device_anon,'date_local':day,'session_index':i,'session_start_ms':s,'session_end_ms':e,'session_closure':cl,'source_table':mod,'same_device_verified':True}
     if mod=='accelerometer':
      try: base.update({'acc_x':float(d.get('double_values_0')),'acc_y':float(d.get('double_values_1')),'acc_z':float(d.get('double_values_2')),'acc_accuracy':d.get('accuracy')})
      except: continue
     elif mod=='screen': base.update({'screen_status':d.get('screen_status')})
     elif mod=='touch': base.update({'touch_action':d.get('touch_action'),'touch_app_hash':package_hash(d.get('touch_app')),'scroll_items_present':d.get('scroll_items') is not None})
     elif mod=='applications_foreground': base.update({'package_hash':package_hash(d.get('package_name')),'is_system_app':d.get('is_system_app')})
     elif mod=='keyboard':
      if str(d.get('is_password','0')).lower() in {'1','true','yes'}: continue
      base.update({'package_hash':package_hash(d.get('package_name')),'is_password':False,'keyboard_event_type':'text_state_snapshot'})
     out.append(base)
    path=write_partition(out,mod,f'{device_anon[-6:]}',device_anon,day,i)
    if path: rec['files'].append(path)
    rec.setdefault('rows_by_modality',{})[mod]=rec.setdefault('rows_by_modality',{}).get(mod,0)+len(out)
   rec.setdefault('acc_sampling_median_ms',[]).append(float(np.median(np.diff(sorted(set(x for x,_,_ in acc))))) if len(acc)>1 else None)
  rec['status']='completed';rec['completed_at']=datetime.now(timezone.utc).isoformat()
 except Exception as exc:
  rec['status']='failed';rec['error']=type(exc).__name__+': '+str(exc)
 marker.write_text(json.dumps(rec,indent=2)); manifest.append(rec)
cur.close();conn.close()
pd.DataFrame(manifest).to_json(OUT/'checkpoint_manifest.json',orient='records',indent=2)
# flattened checkpoint CSV with only aggregate counts
flat=[]
for r in manifest:
 flat.append({'target':r.get('target'),'device_anon':r.get('device_anon'),'day':r.get('day'),'status':r.get('status'),'screen_sessions_total':r.get('screen_sessions_total'),'eligible_sessions':r.get('eligible_sessions'),'session_count':r.get('session_count'),'rows_by_modality':json.dumps(r.get('rows_by_modality',{}),sort_keys=True),'acc_sampling_median_ms':json.dumps(r.get('acc_sampling_median_ms',[])),'error':r.get('error','')})
pd.DataFrame(flat).to_csv(OUT/'checkpoint_manifest.csv',index=False)
print(pd.DataFrame(flat).to_string(index=False))
