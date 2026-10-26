from pathlib import Path
import pandas as pd,numpy as np
OUT=Path('output/analysis_candidates/cross_modal_motion_conditioned_v1');SRC=Path('output/analysis_candidates/cross_modal_event_export_v1/parquet')
def load(dev,date,s,mod):
 p=SRC/f'patient={dev[-6:]}/device={dev}/date={date}/modality={mod}/session_{s:02d}.parquet';return pd.read_parquet(p) if p.exists() else pd.DataFrame()
rows=[];manifest=pd.read_csv('output/analysis_candidates/cross_modal_event_export_v1/checkpoint_manifest.csv')
for _,m in manifest.iterrows():
 for s in range(1,int(m.session_count)+1):
  a=load(m.device_anon,m.day,s,'accelerometer');t=load(m.device_anon,m.day,s,'touch');k=load(m.device_anon,m.day,s,'keyboard')
  if a.empty:continue
  a=a.dropna(subset=['acc_x','acc_y','acc_z']).sort_values('timestamp_ms');v=a[['acc_x','acc_y','acc_z']].to_numpy(float);res=np.linalg.norm(v-np.median(v,axis=0),axis=1);a['bin']=(a.timestamp_ms//1000)*1000;a['res']=res;b=a.groupby('bin').res.median();q30,q70=np.quantile(b,[.3,.7]);
  def st(x):
   z=b.loc[(b.index<=x)].iloc[-1] if any(b.index<=x) else np.nan
   return 'stationary' if z<=q30 else ('moving' if z>=q70 else 'middle')
  ts=t.timestamp_ms.astype(int).sort_values().to_numpy() if not t.empty else np.array([]);ks=k.timestamp_ms.astype(int).sort_values().to_numpy() if not k.empty else np.array([])
  out={'device_anon':m.device_anon,'date':m.day,'session_index':s,'cadence_median_ms':float(np.median(np.diff(np.sort(a.timestamp_ms.unique())))) if len(a)>1 else np.nan,'q30':q30,'q70':q70,'touch_stationary':int(sum(st(x)=='stationary' for x in ts)),'touch_moving':int(sum(st(x)=='moving' for x in ts)),'keyboard_stationary':int(sum(st(x)=='stationary' for x in ks)),'keyboard_moving':int(sum(st(x)=='moving' for x in ks))}
  # state-specific intervals
  for fam,arr in [('touch',ts),('keyboard',ks)]:
   for state in ['stationary','moving']:
    z=[x for x in arr if st(x)==state];di=np.diff(z) if len(z)>1 else np.array([]);out[f'{fam}_{state}_intervals']=len(di);out[f'{fam}_{state}_iqr_ms']=float(np.percentile(di,75)-np.percentile(di,25)) if len(di) else np.nan;out[f'{fam}_{state}_cv']=float(np.std(di)/np.mean(di)) if len(di) and np.mean(di)>0 else np.nan
  rows.append(out)
pd.DataFrame(rows).to_csv(OUT/'quantile_motion_state_sensitivity.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
