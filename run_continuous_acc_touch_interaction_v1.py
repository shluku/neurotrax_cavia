from pathlib import Path
import pandas as pd,numpy as np
OUT=Path('output/analysis_candidates/cross_modal_continuous_interaction_v1');OUT.mkdir(parents=True,exist_ok=True)
SRC=Path('output/analysis_candidates/cross_modal_repeated_day_export_v1/parquet');MAN=pd.read_csv('output/analysis_candidates/cross_modal_repeated_day_export_v1/checkpoint_manifest.csv')
def load(dev,date,s,mod):
 p=SRC/f'patient={dev[-6:]}/device={dev}/date={date}/modality={mod}/session_{s:02d}.parquet';return pd.read_parquet(p) if p.exists() else pd.DataFrame()
rows=[]
for _,m in MAN.iterrows():
 for s in sorted(int(p.stem.split('_')[-1]) for p in (SRC/f'patient={m.device_anon[-6:]}/device={m.device_anon}/date={m.day}/modality=screen').glob('session_*.parquet')):
  a=load(m.device_anon,m.day,s,'accelerometer');t=load(m.device_anon,m.day,s,'touch');scr=load(m.device_anon,m.day,s,'screen')
  if a.empty or scr.empty:continue
  a=a.dropna(subset=['acc_x','acc_y','acc_z']).sort_values('timestamp_ms');v=a[['acc_x','acc_y','acc_z']].to_numpy(float);base=np.median(v,axis=0);a['motion_residual']=np.linalg.norm(v-base,axis=1);ts=np.sort(a.timestamp_ms.astype(int).unique());dt=np.diff(ts);st=int(scr.session_start_ms.iloc[0]);en=int(scr.session_end_ms.iloc[0]);
  for w in [30,60]:
   n=int((en-st)//(w*1000))
   for i in range(n):
    x=st+i*w*1000;y=x+w*1000;aa=a[(a.timestamp_ms>=x)&(a.timestamp_ms<y)];tt=t[(t.timestamp_ms>=x)&(t.timestamp_ms<y)] if not t.empty else t
    ats=np.sort(aa.timestamp_ms.astype(int).unique());di=np.diff(ats) if len(ats)>1 else np.array([]);ti=np.sort(tt.timestamp_ms.astype(int).unique()) if not tt.empty else np.array([]);td=np.diff(ti) if len(ti)>1 else np.array([])
    rows.append({'device_anon':m.device_anon,'day':m.day,'session_index':s,'window_s':w,'window_index':i,'window_start_ms':x,'window_end_ms':y,'session_duration_s':(en-st)/1000,'acc_samples':len(aa),'acc_coverage_s':float((ats[-1]-ats[0])/1000) if len(ats)>1 else 0,'acc_median_interval_ms':float(np.median(di)) if len(di) else np.nan,'acc_p95_interval_ms':float(np.percentile(di,95)) if len(di) else np.nan,'acc_gap_gt1s':int((di>1000).sum()) if len(di) else 0,'motion_median_residual':float(np.median(aa.motion_residual)) if len(aa) else np.nan,'motion_sd_residual':float(np.std(aa.motion_residual)) if len(aa) else np.nan,'motion_iqr_residual':float(np.percentile(aa.motion_residual,75)-np.percentile(aa.motion_residual,25)) if len(aa) else np.nan,'touch_events':len(ti),'touch_density_per_min':len(ti)/(w/60),'touch_interval_iqr_ms':float(np.percentile(td,75)-np.percentile(td,25)) if len(td) else np.nan,'touch_interval_cv':float(np.std(td)/np.mean(td)) if len(td) and np.mean(td)>0 else np.nan,'touch_app_contexts':int(tt.touch_app_hash.nunique()) if not tt.empty and 'touch_app_hash' in tt else 0})
df=pd.DataFrame(rows);df['cadence_stratum']=pd.cut(df.acc_median_interval_ms,bins=[-np.inf,20,100,np.inf],labels=['high_rate_<=20ms','mid_rate_20_100ms','low_rate_>100ms'])
# Prespecified window eligibility: >=50 ACC samples, no >1s gap, and nonempty touch window.
df['acc_qc_pass']=(df.acc_samples>=50)&(df.acc_gap_gt1s==0);df['density_eligible']=df.touch_events>=2;df['variability_eligible']=df.touch_events>=3;df['coupling_eligible']=df.acc_qc_pass&df.density_eligible;df['variability_coupling_eligible']=df.acc_qc_pass&df.variability_eligible
df.to_csv(OUT/'window_level_qc_and_features.csv',index=False)
# within-session descriptive correlations, no p values; require >=3 eligible windows and variation in both variables
out=[]
for (dev,day,s,w),g in df.groupby(['device_anon','day','session_index','window_s']):
 for kind,x,y,elig in [('density','touch_density_per_min','motion_median_residual','coupling_eligible'),('variability','touch_interval_iqr_ms','motion_iqr_residual','variability_coupling_eligible')]:
  z=g[g[elig]].dropna(subset=[x,y]);rho=float(z[x].corr(z[y],method='spearman')) if len(z)>=3 and z[x].nunique()>1 and z[y].nunique()>1 else np.nan
  out.append({'device_anon':dev,'day':day,'session_index':s,'window_s':w,'analysis':kind,'eligible_windows':len(z),'x_feature':x,'y_feature':y,'spearman_rho_descriptive':rho,'x_unique':z[x].nunique(),'y_unique':z[y].nunique(),'estimable_without_pvalue':bool(np.isfinite(rho))})
pd.DataFrame(out).to_csv(OUT/'within_session_descriptive_associations.csv',index=False)
# repeated-day feasibility by device/day
rd=df[df.coupling_eligible].groupby(['device_anon','day','window_s']).agg(eligible_windows=('window_index','count'),sessions=('session_index','nunique'),touch_events=('touch_events','sum')).reset_index();rd.to_csv(OUT/'repeated_day_feature_feasibility.csv',index=False)
# summaries and funnel
summ=[]
for w,g in df.groupby('window_s'):
 for stage,mask in [('all_windows',np.ones(len(g),bool)),('ACC_QC',g.acc_qc_pass),('density_eligible',g.coupling_eligible),('variability_eligible',g.variability_coupling_eligible)]:
  z=g[mask];summ.append({'window_s':w,'stage':stage,'windows':len(z),'sessions':z.session_index.nunique() if len(z) else 0,'device_days':len(z[['device_anon','day']].drop_duplicates()) if len(z) else 0,'devices':z.device_anon.nunique() if len(z) else 0,'touch_events':int(z.touch_events.sum()) if len(z) else 0})
pd.DataFrame(summ).to_csv(OUT/'window_eligibility_summary.csv',index=False)
print(pd.DataFrame(summ).to_string(index=False));print('\nAssoc\n',pd.DataFrame(out).to_string(index=False))
