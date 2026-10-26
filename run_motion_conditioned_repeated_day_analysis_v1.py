from pathlib import Path
import pandas as pd,numpy as np,json,math
OUT=Path('output/analysis_candidates/cross_modal_repeated_day_export_v1');OUT.mkdir(parents=True,exist_ok=True)
SRC=Path('output/analysis_candidates/cross_modal_repeated_day_export_v1/parquet')

def load(dev,date,s,mod):
 p=SRC/f'patient={dev[-6:]}/device={dev}/date={date}/modality={mod}/session_{s:02d}.parquet';return pd.read_parquet(p) if p.exists() else pd.DataFrame()
def state_bins(acc,thr):
 a=acc.dropna(subset=['acc_x','acc_y','acc_z']).sort_values('timestamp_ms').copy();vec=a[['acc_x','acc_y','acc_z']].to_numpy(float);base=np.median(vec,axis=0);res=np.linalg.norm(vec-base,axis=1);a['residual_motion']=res;a['bin_start_ms']=(a.timestamp_ms//1000)*1000
 b=a.groupby('bin_start_ms').agg(motion_median=('residual_motion','median'),acc_n=('residual_motion','size')).reset_index();b['state']=np.where(b.motion_median>=thr,'moving','stationary');return b,a
def assign(ts,b):
 if not len(b):return None
 ix=np.searchsorted(b.bin_start_ms.to_numpy(),int(ts),side='right')-1
 if ix<0 or ix>=len(b):return None
 return b.iloc[ix].state

def cadence(a):
 z=np.diff(np.sort(a.timestamp_ms.astype(int).unique()));return float(np.median(z)) if len(z) else np.nan
rows=[];event_rows=[];manifest=pd.read_csv('output/analysis_candidates/cross_modal_repeated_day_export_v1/checkpoint_manifest.csv')
for _,m in manifest.iterrows():
 dev,date=m.device_anon,m.day
 for s in range(1,int(m.session_count)+1):
  acc=load(dev,date,s,'accelerometer');touch=load(dev,date,s,'touch');key=load(dev,date,s,'keyboard');scr=load(dev,date,s,'screen');apps=load(dev,date,s,'applications_foreground')
  if acc.empty:continue
  med=cadence(acc);stratum='high_rate_<=20ms' if med<=20 else ('mid_rate_20_100ms' if med<=100 else 'low_rate_>100ms')
  for thr in [0.05,0.15,0.30]:
   bins,a=state_bins(acc,thr); t=touch.copy();t['state']=t.timestamp_ms.map(lambda x:assign(x,bins));t=t.dropna(subset=['state']).sort_values('timestamp_ms');
   # Touch intervals require both endpoints in the same state; no cross-state intervals are assigned.
   tv={}
   for (st),g in t.groupby('state'):
    z=np.diff(g.timestamp_ms.astype(int).to_numpy());z=z[z>0];tv[st]=z
   k=key.copy();
   if not k.empty:
    k['state']=k.timestamp_ms.map(lambda x:assign(x,bins));k=k.dropna(subset=['state']).sort_values('timestamp_ms');
   kv={}
   if not k.empty:
    for pkg,g in k.groupby('package_hash'):
     for st,gg in g.groupby('state'):
      z=np.diff(gg.timestamp_ms.astype(int).to_numpy());z=z[(z>0)&(z<=30000)];kv.setdefault(st,[]).extend(z.tolist())
   rows.append({'device_anon':dev,'date':date,'session_index':s,'motion_threshold_residual_units':thr,'cadence_median_ms':med,'cadence_stratum':stratum,'acc_samples':len(a),'acc_bins':len(bins),'moving_bins':int((bins.state=='moving').sum()),'stationary_bins':int((bins.state=='stationary').sum()),'touch_events_total':len(t),'touch_stationary_events':int((t.state=='stationary').sum()),'touch_moving_events':int((t.state=='moving').sum()),'touch_stationary_intervals':len(tv.get('stationary',[])),'touch_moving_intervals':len(tv.get('moving',[])),'touch_stationary_iqr_ms':float(np.percentile(tv['stationary'],75)-np.percentile(tv['stationary'],25)) if len(tv.get('stationary',[])) else np.nan,'touch_moving_iqr_ms':float(np.percentile(tv['moving'],75)-np.percentile(tv['moving'],25)) if len(tv.get('moving',[])) else np.nan,'touch_stationary_cv':float(np.std(tv['stationary'])/np.mean(tv['stationary'])) if len(tv.get('stationary',[])) and np.mean(tv['stationary'])>0 else np.nan,'touch_moving_cv':float(np.std(tv['moving'])/np.mean(tv['moving'])) if len(tv.get('moving',[])) and np.mean(tv['moving'])>0 else np.nan,'keyboard_snapshots_total':len(k),'keyboard_stationary_events':int((k.state=='stationary').sum()) if not k.empty else 0,'keyboard_moving_events':int((k.state=='moving').sum()) if not k.empty else 0,'keyboard_stationary_intervals':len(kv.get('stationary',[])),'keyboard_moving_intervals':len(kv.get('moving',[])),'keyboard_stationary_iqr_ms':float(np.percentile(kv['stationary'],75)-np.percentile(kv['stationary'],25)) if len(kv.get('stationary',[])) else np.nan,'keyboard_moving_iqr_ms':float(np.percentile(kv['moving'],75)-np.percentile(kv['moving'],25)) if len(kv.get('moving',[])) else np.nan,'keyboard_stationary_cv':float(np.std(kv['stationary'])/np.mean(kv['stationary'])) if len(kv.get('stationary',[])) and np.mean(kv['stationary'])>0 else np.nan,'keyboard_moving_cv':float(np.std(kv['moving'])/np.mean(kv['moving'])) if len(kv.get('moving',[])) and np.mean(kv['moving'])>0 else np.nan,'app_context_count':int(k.package_hash.nunique()) if not k.empty else 0})
   # aggregate state assignments without timestamps or hashes for QC counts only
   event_rows.append({'device_anon':dev,'date':date,'session_index':s,'threshold':thr,'state':'stationary','touch_events':int((t.state=='stationary').sum()),'keyboard_events':int((k.state=='stationary').sum()) if not k.empty else 0})
   event_rows.append({'device_anon':dev,'date':date,'session_index':s,'threshold':thr,'state':'moving','touch_events':int((t.state=='moving').sum()),'keyboard_events':int((k.state=='moving').sum()) if not k.empty else 0})
df=pd.DataFrame(rows);df.to_csv(OUT/'motion_conditioned_session_feasibility.csv',index=False);pd.DataFrame(event_rows).to_csv(OUT/'motion_state_event_coverage.csv',index=False)
# Eligible contrast summary uses minimum 3 intervals in each state, separately for touch and keyboard.
summ=[]
for thr,g in df.groupby('motion_threshold_residual_units'):
 for family,prefix in [('touch','touch'),('keyboard','keyboard')]:
  elig=g[(g[f'{prefix}_stationary_intervals']>=3)&(g[f'{prefix}_moving_intervals']>=3)]
  summ.append({'feature_family':family,'threshold':thr,'eligible_sessions':len(elig),'eligible_devices':elig.device_anon.nunique(),'eligible_device_days':len(elig[['device_anon','date']].drop_duplicates()),'eligible_patients':elig.device_anon.nunique(),'median_stationary_iqr_ms':elig[f'{prefix}_stationary_iqr_ms'].median() if len(elig) else np.nan,'median_moving_iqr_ms':elig[f'{prefix}_moving_iqr_ms'].median() if len(elig) else np.nan,'median_moving_minus_stationary_iqr_ms':(elig[f'{prefix}_moving_iqr_ms']-elig[f'{prefix}_stationary_iqr_ms']).median() if len(elig) else np.nan,'median_stationary_cv':elig[f'{prefix}_stationary_cv'].median() if len(elig) else np.nan,'median_moving_cv':elig[f'{prefix}_moving_cv'].median() if len(elig) else np.nan,'decision':'estimable_descriptively' if len(elig)>=2 else 'insufficient_both_state_events'})
pd.DataFrame(summ).to_csv(OUT/'motion_conditioned_contrast_feasibility.csv',index=False)
(OUT/'privacy_audit.json').write_text(json.dumps({'raw_text_exported':False,'package_names_exported':False,'timestamps_exported':False,'aggregate_state_counts_only':True},indent=2))
print(df.groupby(['motion_threshold_residual_units','cadence_stratum']).size().to_string());print(pd.DataFrame(summ).to_string(index=False))
