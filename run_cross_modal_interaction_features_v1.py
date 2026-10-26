from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import json, math
import numpy as np, pandas as pd
from main import connect_sensordata_db

OUT=Path('output/analysis_candidates/cross_modal_interaction_features_v1'); OUT.mkdir(parents=True,exist_ok=True)
SAMPLES=[('041','d74f7acf-f82f-491d-90b9-d7321e6d4bcf','2025-01-09'),('039','72e21d84-c3cb-401a-8beb-4532f39f0688','2025-01-13')]
TZ=ZoneInfo('Asia/Jerusalem')

def bounds(day):
 a=datetime.fromisoformat(day).replace(tzinfo=TZ); b=a+timedelta(days=1); return int(a.timestamp()*1000),int(b.timestamp()*1000)
def parse(x):
 try:return json.loads(x) if isinstance(x,str) else (x or {})
 except:return {}
def fetch(cur,table,dev,a,b):
 cur.execute(f"SELECT timestamp,device_id,data FROM {table} WHERE device_id=%s AND timestamp >= %s AND timestamp < %s ORDER BY timestamp",(dev,a,b))
 return [{'timestamp':int(r[0]),'device_id':r[1],'data':parse(r[2])} for r in cur.fetchall()]
def dedup(rows,table):
 seen=set();out=[]
 for r in rows:
  d=r['data'];
  if table=='keyboard': k=(r['timestamp'],str(d.get('package_name','')),str(d.get('is_password','')),str(d.get('before_text','')),str(d.get('current_text','')))
  elif table=='touch': k=(r['timestamp'],str(d.get('touch_app','')),str(d.get('touch_action','')),str(d.get('scroll_items','')))
  elif table=='applications_foreground': k=(r['timestamp'],str(d.get('package_name','')),str(d.get('is_system_app','')))
  elif table=='screen': k=(r['timestamp'],str(d.get('screen_status','')))
  else: k=(r['timestamp'],str(d.get('double_values_0','')),str(d.get('double_values_1','')),str(d.get('double_values_2','')))
  if k not in seen:seen.add(k);out.append(r)
 return out
def sessions(rows):
 out=[];start=None
 for r in sorted(rows,key=lambda z:z['timestamp']):
  s=str(r['data'].get('screen_status',''))
  if s=='3' and start is None:start=r['timestamp']
  elif s in {'0','2'} and start is not None:
   if r['timestamp']>start:out.append((start,r['timestamp'],'closed'))
   start=None
 return out
def inside(rows,a,b): return [r for r in rows if a<=r['timestamp']<b]
def acc_mag(rows):
 out=[]
 for r in rows:
  d=r['data']
  try:
   x=float(d['double_values_0']);y=float(d['double_values_1']);z=float(d['double_values_2']);out.append((r['timestamp'],math.sqrt(x*x+y*y+z*z)))
  except:continue
 return sorted(out)
def intervals(ts):
 x=sorted(set(int(t) for t in ts)); return np.diff(x) if len(x)>1 else np.array([])
def pct(x,q): return float(np.percentile(x,q)) if len(x) else np.nan

def bins(a,b,width,acc,touches):
 out=[]
 for s in range(a,b,width):
  e=min(s+width,b); av=[v for t,v in acc if s<=t<e]; tt=[t for t in touches if s<=t<e]
  if av: out.append({'start':s,'end':e,'acc_n':len(av),'mag_mean':float(np.mean(av)),'mag_sd':float(np.std(av)),'touch_n':len(tt)})
 return out

def k_intervals(rows):
 g={}
 for r in rows:
  d=r['data']
  if str(d.get('is_password','0')).lower() in {'1','true','yes'}:continue
  g.setdefault(str(d.get('package_name','')),[]).append(r['timestamp'])
 vals=[]
 for ts in g.values():
  x=intervals(ts); vals.extend([float(v) for v in x if 0<v<=30000])
 return np.array(vals)

conn=connect_sensordata_db();cur=conn.cursor(); coverage=[]; sessrows=[]; touchmotion=[]; motiontouch=[]; appcost=[]; novelty=[]
for patient,dev,day in SAMPLES:
 print('START',patient,flush=True)
 a,b=bounds(day); raw={}
 for t in ['screen','touch','applications_foreground','keyboard']:
  rr=fetch(cur,t,dev,a,b); print('FETCH',t,len(rr),flush=True); raw[t]=dedup(rr,t)
  coverage.append({'patient_anon':f'patient_{patient}','device_anon':f'dev_{dev[:6]}','day':day,'table':t,'raw_rows':len(rr),'deduplicated_rows':len(raw[t]),'duplicate_rows_removed':len(rr)-len(raw[t])})
 cur.execute("SELECT data FROM sensor_accelerometer WHERE device_id=%s ORDER BY timestamp LIMIT 1",(dev,)); mr=cur.fetchone(); md=parse(mr[0]) if mr else {}
 ss=sessions(raw['screen'])
 for i,(st,en,close) in enumerate(ss,1):
  pre_touches=inside(raw['touch'],st,en); pre_keys=inside(raw['keyboard'],st,en)
  # Bounded interaction pilot: retain sessions with observed interaction and cap
  # ACC retrieval to 15 minutes; this is a feasibility sample, not a cohort scan.
  if (not pre_touches and not pre_keys) or (en-st)>15*60*1000:
   continue
  print('SESSION',i,st,en,flush=True)
  acc_rows=dedup(fetch(cur,'accelerometer',dev,st,en),'accelerometer'); print('ACC',len(acc_rows),flush=True)
  acc=acc_mag(acc_rows)
  coverage.append({'patient_anon':f'patient_{patient}','device_anon':f'dev_{dev[:6]}','day':day,'table':'accelerometer','raw_rows':len(acc_rows),'deduplicated_rows':len(acc_rows),'duplicate_rows_removed':0})
  touches=inside(raw['touch'],st,en); apps=inside(raw['applications_foreground'],st,en); keys=inside(raw['keyboard'],st,en); accs=[x for x in acc if st<=x[0]<en]
  touch_ts=[r['timestamp'] for r in touches]; bns=bins(st,en,5000,accs,touch_ts)
  # A/B: 1-second event-centered versus no-touch bins; use 500-ms tolerance and equal session-local controls.
  for tol in [500,1000]:
   event_vals=[];control_vals=[]
   for t in touch_ts:
    vals=[v for x,v in accs if t-tol<=x<=t+tol]
    if vals:event_vals.extend(vals)
   for bn in bns:
    if bn['touch_n']==0: control_vals.extend([v for x,v in accs if bn['start']<=x<bn['end']])
   touchmotion.append({'patient_anon':f'patient_{patient}','device_anon':f'dev_{dev[:6]}','day':day,'session_index':i,'tolerance_ms':tol,'session_duration_s':(en-st)/1000,'touch_events':len(touch_ts),'acc_samples':len(accs),'observed_sampling_median_ms':float(np.median(np.diff([x for x,v in accs]))) if len(accs)>1 else np.nan,'touch_acc_n':len(event_vals),'control_acc_n':len(control_vals),'touch_motion_median':float(np.median(event_vals)) if event_vals else np.nan,'control_motion_median':float(np.median(control_vals)) if control_vals else np.nan,'within_session_difference':float(np.median(event_vals)-np.median(control_vals)) if event_vals and control_vals else np.nan,'sensor_name':md.get('sensor_name'),'sensor_vendor':md.get('sensor_vendor'),'sensor_version':md.get('sensor_version'),'minimum_delay_us':md.get('double_sensor_minimum_delay')})
  # B: 5-second bins classified stationary/moving by ACC magnitude SD; threshold sensitivity.
  for thr in [0.05,0.15,0.30]:
   states=[]
   for bn in bns:
    if bn['touch_n']>0: states.append((bn['start'], 'moving' if bn['mag_sd']>=thr else 'stationary'))
   # touch intervals assigned by preceding 5s bin, with both endpoints classified.
   lab={s:l for s,l in states}; pairs=[]
   for x,y in zip(touch_ts,touch_ts[1:]):
    bx=((x-st)//5000)*5000+st; by=((y-st)//5000)*5000+st
    if bx in lab and by in lab and lab[bx]==lab[by]:pairs.append((y-x,lab[bx]))
   for state in ['stationary','moving']:
    vals=np.array([v for v,l in pairs if l==state],float)
    motiontouch.append({'patient_anon':f'patient_{patient}','device_anon':f'dev_{dev[:6]}','day':day,'session_index':i,'motion_threshold_mag_sd':thr,'stationary_or_moving':state,'touch_event_count':sum(1 for _,l in pairs if l==state),'touch_interval_median_ms':float(np.median(vals)) if len(vals) else np.nan,'touch_interval_iqr_ms':float(np.percentile(vals,75)-np.percentile(vals,25)) if len(vals) else np.nan,'touch_interval_cv':float(np.std(vals)/np.mean(vals)) if len(vals) and np.mean(vals)>0 else np.nan,'acc_samples':len(accs),'sensor_name':md.get('sensor_name'),'observed_sampling_median_ms':float(np.median(np.diff([x for x,v in accs]))) if len(accs)>1 else np.nan})
  # C: app-switch interruption cost; keyboard IEI in 10s pre/post, matched same-app controls between transitions.
  ap=sorted(apps,key=lambda r:r['timestamp']); trans=[]
  for prev,nxt in zip(ap,ap[1:]):
   p=str(prev['data'].get('package_name','')); q=str(nxt['data'].get('package_name',''))
   if p and q and p!=q:trans.append(nxt['timestamp'])
  for t in trans:
   pre=k_intervals([r for r in keys if t-10000<=r['timestamp']<t]); post=k_intervals([r for r in keys if t<=r['timestamp']<t+10000])
   appcost.append({'patient_anon':f'patient_{patient}','device_anon':f'dev_{dev[:6]}','day':day,'session_index':i,'transition_time_relative_s':(t-st)/1000,'pre_keyboard_intervals_n':len(pre),'post_keyboard_intervals_n':len(post),'pre_keyboard_iei_median_ms':float(np.median(pre)) if len(pre) else np.nan,'post_keyboard_iei_median_ms':float(np.median(post)) if len(post) else np.nan,'post_minus_pre_ms':float(np.median(post)-np.median(pre)) if len(pre) and len(post) else np.nan,'acc_samples_session':len(accs),'sensor_name':md.get('sensor_name'),'observed_sampling_median_ms':float(np.median(np.diff([x for x,v in accs]))) if len(accs)>1 else np.nan})
  sessrows.append({'patient_anon':f'patient_{patient}','device_anon':f'dev_{dev[:6]}','day':day,'session_index':i,'session_duration_s':(en-st)/1000,'touch_events':len(touches),'app_events':len(apps),'app_transitions':sum(1 for x,y in zip(apps,apps[1:]) if str(x['data'].get('package_name',''))!=str(y['data'].get('package_name',''))),'keyboard_snapshots':len(keys),'acc_samples':len(accs),'acc_metadata_present':bool(md),'sensor_name':md.get('sensor_name'),'sensor_vendor':md.get('sensor_vendor'),'sensor_version':md.get('sensor_version'),'minimum_delay_us':md.get('double_sensor_minimum_delay'),'observed_sampling_median_ms':float(np.median(np.diff([x for x,v in accs]))) if len(accs)>1 else np.nan,'acc_gap_gt1s':int(sum(1 for x,y in zip([x for x,v in accs],[x for x,v in accs][1:]) if y-x>1000)) if len(accs)>1 else np.nan})
cur.close();conn.close()
pd.DataFrame(coverage).to_csv(OUT/'patient_device_day_coverage.csv',index=False)
pd.DataFrame(sessrows).to_csv(OUT/'session_interaction_coverage.csv',index=False)
pd.DataFrame(touchmotion).to_csv(OUT/'touch_motion_coupling.csv',index=False)
pd.DataFrame(motiontouch).to_csv(OUT/'motion_conditioned_touch_variability.csv',index=False)
pd.DataFrame(appcost).to_csv(OUT/'app_switch_interruption_cost.csv',index=False)
print('sessions',len(sessrows),'touch-motion rows',len(touchmotion),'motion-touch rows',len(motiontouch),'appcost',len(appcost))
