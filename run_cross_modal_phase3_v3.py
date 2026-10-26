from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import json, numpy as np, pandas as pd
from main import connect_sensordata_db
OUT=Path('output/analysis_candidates/cross_modal_feature_discovery_v3'); OUT.mkdir(parents=True,exist_ok=True)
TZ=ZoneInfo('Asia/Jerusalem'); DEVICES=['72e21d84-c3cb-401a-8beb-4532f39f0688','c9cc92f6-be86-4916-b1f6-d940e6d6d6ac','1b799d79-1303-44c4-97a7-ad56a19add13','cc373e47-1b4b-4e15-a7e7-7882510d4949','ed3860d6-8c63-4db3-a74f-263067f0a88f']
def parse(x):
 try:return json.loads(x) if isinstance(x,str) else (x or {})
 except:return {}
def q(cur,t,d,a,b):
 cur.execute(f'SELECT timestamp,data FROM {t} WHERE device_id=%s AND timestamp >= %s AND timestamp < %s ORDER BY timestamp',(d,a,b)); return [(int(r[0]),parse(r[1])) for r in cur.fetchall()]
def ded(rows,t):
 seen=set();o=[]
 for ts,x in rows:
  if t=='keyboard': k=(ts,str(x.get('package_name','')),str(x.get('is_password','')),str(x.get('before_text','')),str(x.get('current_text','')))
  elif t=='touch': k=(ts,str(x.get('touch_app','')),str(x.get('touch_action','')),str(x.get('scroll_items','')))
  elif t=='applications_foreground': k=(ts,str(x.get('package_name','')),str(x.get('is_system_app','')))
  else:k=(ts,str(x.get('screen_status','')))
  if k not in seen: seen.add(k);o.append((ts,x))
 return o
def sessions(rows):
 o=[]; st=None
 for ts,x in rows:
  c=str(x.get('screen_status',''))
  if c=='3' and st is None:st=ts
  elif c in {'0','2'} and st is not None and ts>st:o.append((st,ts,'closed'));st=None
 return o
def feats(ss,data):
 a,b,cl=ss; dur=(b-a)/60000; out={'session_minutes':dur,'session_closure':cl}
 def ins(t):return [(x,y) for x,y in data[t] if a<=x<b]
 tt=ins('touch'); ap=ins('applications_foreground'); kk=ins('keyboard')
 ti=np.diff(sorted(set(x for x,y in tt))) if len(tt)>1 else np.array([]); out.update({'touch_events':len(tt),'touch_rate_per_min':len(tt)/dur if dur else np.nan,'touch_interval_median_ms':float(np.median(ti)) if len(ti) else np.nan,'touch_interval_iqr_ms':float(np.percentile(ti,75)-np.percentile(ti,25)) if len(ti) else np.nan,'touch_interval_cv':float(np.std(ti)/np.mean(ti)) if len(ti) and np.mean(ti)>0 else np.nan,'touch_long_gap_count_gt30s':int((ti>30000).sum()) if len(ti) else 0})
 apps=[str(y.get('package_name','')) for x,y in ap]; out.update({'app_events':len(ap),'app_distinct_count':len(set(apps)),'app_transitions':sum(1 for i in range(1,len(apps)) if apps[i]!=apps[i-1]),'app_transitions_per_min':sum(1 for i in range(1,len(apps)) if apps[i]!=apps[i-1])/dur if dur else np.nan,'app_transition_fraction':sum(1 for i in range(1,len(apps)) if apps[i]!=apps[i-1])/len(apps) if apps else np.nan})
 g={}
 for x,y in kk:
  if str(y.get('is_password','0')).lower() in {'1','true','yes'}:continue
  g.setdefault(str(y.get('package_name','')),[]).append(x)
 ki=[]
 for ts in g.values():
  z=np.diff(sorted(set(ts))); ki.extend(z[(z>0)&(z<=30000)])
 out.update({'keyboard_snapshots':len(kk),'keyboard_package_count':len(g),'keyboard_valid_intervals':len(ki),'keyboard_interval_median_ms':float(np.median(ki)) if ki else np.nan,'keyboard_interval_iqr_ms':float(np.percentile(ki,75)-np.percentile(ki,25)) if ki else np.nan})
 return out
conn=connect_sensordata_db();cur=conn.cursor(); cov=[]; daily=[]; sessrows=[]
for dev in DEVICES:
 cur.execute('SELECT MIN(timestamp),MAX(timestamp) FROM screen WHERE device_id=%s',(dev,)); mm=cur.fetchone()
 if not mm[0]:continue
 days=sorted({datetime.fromtimestamp(x/1000,tz=ZoneInfo('UTC')).astimezone(TZ).date().isoformat() for x in mm})
 for day in days:
  s=datetime.fromisoformat(day).replace(tzinfo=TZ); a=int(s.timestamp()*1000); b=int((s+timedelta(days=1)).timestamp()*1000); data={}
  for t in ['screen','touch','applications_foreground','keyboard']: data[t]=ded(q(cur,t,dev,a,b),t)
  cov.append({'device_anon':'dev_'+dev[:6],'day':day,**{f'{t}_rows':len(data[t]) for t in data},**{f'{t}_duplicates_removed':len(q(cur,t,dev,a,b))-len(data[t]) for t in data}})
  ss=sessions(data['screen']); vals=[]
  for i,z in enumerate(ss,1):
   f=feats(z,data); f.update({'device_anon':'dev_'+dev[:6],'day':day,'session_index':i}); sessrows.append(f); vals.append(f)
  if vals:
   df=pd.DataFrame(vals); row={'device_anon':'dev_'+dev[:6],'day':day,'sessions':len(df)}
   for col in ['touch_rate_per_min','touch_interval_median_ms','touch_interval_iqr_ms','touch_interval_cv','touch_long_gap_count_gt30s','app_transitions_per_min','app_distinct_count','app_transition_fraction','keyboard_interval_median_ms','keyboard_interval_iqr_ms','keyboard_valid_intervals']:
    row[col]=df[col].median()
   daily.append(row)
cur.close();conn.close()
pd.DataFrame(cov).to_csv(OUT/'patient_coverage_matrix.csv',index=False); pd.DataFrame(sessrows).to_csv(OUT/'session_feature_table.csv',index=False); pd.DataFrame(daily).to_csv(OUT/'daily_feature_table.csv',index=False)
# Window sensitivity by slicing session durations/counts conservatively using session-level event counts scaled only as coverage descriptors.
win=[]
for r in sessrows:
 for w in [1,5,10,15]: win.append({'device_anon':r['device_anon'],'day':r['day'],'session_index':r['session_index'],'window_minutes':w,'session_minutes':r['session_minutes'],'eligible_session_ge_window':r['session_minutes']>=w,'touch_events':r['touch_events'],'app_events':r['app_events'],'keyboard_snapshots':r['keyboard_snapshots']})
pd.DataFrame(win).to_csv(OUT/'window_sensitivity.csv',index=False)
# Paired early/late day descriptives across devices (first vs last selected day).
d=pd.DataFrame(daily); rows=[]
for dev,g in d.groupby('device_anon'):
 g=g.sort_values('day');
 if len(g)>=2:
  r={'device_anon':dev,'early_day':g.day.iloc[0],'late_day':g.day.iloc[-1]}
  for c in ['touch_rate_per_min','touch_interval_median_ms','touch_interval_iqr_ms','app_transitions_per_min','app_distinct_count','app_transition_fraction','keyboard_interval_median_ms','keyboard_interval_iqr_ms']:
   r[c+'_early']=g[c].iloc[0];r[c+'_late']=g[c].iloc[-1];r[c+'_delta']=g[c].iloc[-1]-g[c].iloc[0] if pd.notna(g[c].iloc[-1]) and pd.notna(g[c].iloc[0]) else np.nan
  rows.append(r)
pd.DataFrame(rows).to_csv(OUT/'longitudinal_early_late_summary.csv',index=False)
# Reliability summary: paired-day Spearman is descriptive; ICC not estimated with only two days per device.
rel=[]
for c in ['touch_rate_per_min','touch_interval_median_ms','touch_interval_iqr_ms','app_transitions_per_min','app_distinct_count','app_transition_fraction','keyboard_interval_median_ms','keyboard_interval_iqr_ms']:
 wide=pd.DataFrame(rows)
 x=wide.get(c+'_early',pd.Series(dtype=float)); y=wide.get(c+'_late',pd.Series(dtype=float)); ok=x.notna()&y.notna()
 rho=float(x[ok].corr(y[ok],method='spearman')) if ok.sum()>=3 else np.nan
 rel.append({'feature':c,'paired_devices':int(ok.sum()),'spearman_early_late':rho,'icc':'not estimated; two days/device and small pilot','note':'descriptive repeatability only; no cognitive selection'})
pd.DataFrame(rel).to_csv(OUT/'reliability_summary.csv',index=False)
print('devices',len(d.device_anon.unique()),'days',len(d),'sessions',len(sessrows))
