from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt, json
OUT=Path('output/analysis_candidates/cross_modal_acc_touch_validation_v1'); OUT.mkdir(parents=True,exist_ok=True)
SRC=Path('output/analysis_candidates/cross_modal_event_export_v1/parquet')

def load(dev,date,s,mod):
 p=SRC/f'patient={dev[-6:]}/device={dev}/date={date}/modality={mod}/session_{s:02d}.parquet'
 return pd.read_parquet(p) if p.exists() else pd.DataFrame()
def get_session(dev,date,s):
 a=load(dev,date,s,'accelerometer');t=load(dev,date,s,'touch');scr=load(dev,date,s,'screen')
 if a.empty or t.empty:return None
 a=a.dropna(subset=['acc_x','acc_y','acc_z']).copy();a['mag']=np.sqrt(a.acc_x**2+a.acc_y**2+a.acc_z**2);a=a.sort_values('timestamp_ms'); ts=np.sort(a.timestamp_ms.astype(int).unique());
 return a,t,scr,ts

def vals(a, centers, rel, step=100):
 out=[]
 for c in centers:
  z=a[(a.timestamp_ms>=c+rel)&(a.timestamp_ms<c+rel+step)].mag.to_numpy()
  out.append(float(np.median(z)) if len(z) else np.nan)
 return np.array(out)
def profile(a, centers, edges):
 out=[];coverage=[]
 for lo,hi in zip(edges[:-1],edges[1:]):
  z=[]
  for c in centers:
   x=a[(a.timestamp_ms>=c+lo)&(a.timestamp_ms<c+hi)].mag.to_numpy();
   if len(x):z.append(np.median(x))
  out.append(float(np.median(z)) if z else np.nan);coverage.append(len(z))
 return np.array(out),np.array(coverage)
def controls(a,touch_ts,start,end,n):
 # Select deterministic non-touch centers with approximately matched temporal spacing.
 touch=np.array(touch_ts); candidates=np.arange(start+2000,end-2000,500,dtype=int); keep=[]
 for c in candidates:
  if len(keep)>=n:break
  if np.all(np.abs(touch-c)>1500) and np.any((a.timestamp_ms>=c-500)&(a.timestamp_ms<c+500)):keep.append(c)
 return np.array(keep,dtype=int)
def bootstrap_session(diffs,n=2000,seed=7):
 rng=np.random.default_rng(seed); x=np.array(diffs,dtype=float);x=x[np.isfinite(x)]
 if len(x)==0:return (np.nan,np.nan,np.nan)
 means=[np.mean(rng.choice(x,len(x),replace=True)) for _ in range(n)];return float(np.mean(x)),float(np.percentile(means,2.5)),float(np.percentile(means,97.5))

manifest=pd.read_csv('output/analysis_candidates/cross_modal_event_export_v1/checkpoint_manifest.csv'); rows=[]; profiles=[]; session_objs=[]
for _,m in manifest.iterrows():
 dev=m.device_anon;date=m.day
 for s in range(1,int(m.session_count)+1):
  got=get_session(dev,date,s)
  if got is None:continue
  a,t,scr,ts=got; touch=np.sort(t.timestamp_ms.astype(int).unique());start=int(scr.session_start_ms.iloc[0]) if not scr.empty else int(ts[0]);end=int(scr.session_end_ms.iloc[0]) if not scr.empty else int(ts[-1]);
  dif=np.diff(ts); med=float(np.median(dif)) if len(dif) else np.nan; p95=float(np.percentile(dif,95)) if len(dif) else np.nan
  edges=np.arange(-2000,2001,100); event_prof,cov=profile(a,touch,edges); ctrl_centers=controls(a,touch,start,end,len(touch)); ctrl_prof,ccov=profile(a,ctrl_centers,edges)
  # baseline subtract each profile using -1500 to -500 ms bins
  base_idx=(edges[:-1]>=-1500)&(edges[1:]<=-500); evbase=np.nanmedian(event_prof[base_idx]); ctbase=np.nanmedian(ctrl_prof[base_idx]); diff=event_prof-evbase-(ctrl_prof-ctbase)
  # valid pair count in the central ±500-ms window
  central=(edges[:-1]>=-500)&(edges[1:]<=500); pair_count=int(np.nanmin(np.vstack([cov[central],ccov[central]]),axis=1).max()) if np.any(central) else 0
  # motion contrast matching saved pilot concept for direct comparison
  ev500=[];ct500=[]
  for t0 in touch:
   e=a[(a.timestamp_ms>=t0-500)&(a.timestamp_ms<=t0+500)].mag
   c=controls(a,np.array([t0]),start,end,1)
   if len(e) and len(c):
    z=a[(a.timestamp_ms>=c[0]-500)&(a.timestamp_ms<=c[0]+500)].mag
    if len(z):ev500.append(float(np.median(e)));ct500.append(float(np.median(z)))
  rows.append({'device_anon':dev,'date':date,'session_index':s,'touch_events':len(touch),'matched_control_centers':len(ctrl_centers),'acc_samples':len(a),'acc_median_interval_ms':med,'acc_p95_interval_ms':p95,'acc_gap_gt1s':int((dif>1000).sum()),'event_profile_coverage_central_median':float(np.nanmedian(cov[central])),'control_profile_coverage_central_median':float(np.nanmedian(ccov[central])),'central_event_control_difference_baseline_subtracted':float(np.nanmedian(diff[central])),'direct_500ms_pair_median_difference':float(np.median(np.array(ev500)-np.array(ct500))) if ev500 else np.nan,'direct_500ms_pairs':len(ev500),'cadence_stratum':'high_rate_<=20ms' if med<=20 else ('mid_rate_20_100ms' if med<=100 else 'low_rate_>100ms')})
  profiles.append({'device_anon':dev,'date':date,'session_index':s,'edges':edges,'event':event_prof,'control':ctrl_prof,'difference':diff,'event_cov':cov,'control_cov':ccov})
  session_objs.append((dev,date,s,touch,start,end,a))
# observed and negative-control distributions at session level
obs=np.array([r['central_event_control_difference_baseline_subtracted'] for r in rows if np.isfinite(r['central_event_control_difference_baseline_subtracted'])])
neg=[]; rng=np.random.default_rng(19)
for dev,date,s,touch,start,end,a in session_objs:
 duration=end-start
 for k in range(200):
  shift=int(rng.integers(3000,max(3001,duration-3000))) if duration>7000 else 3000
  centers=[]
  for t0 in touch:
   c=start+((int(t0)-start+shift)%max(1,duration))
   if start+2000<c<end-2000 and np.all(np.abs(touch-c)>1500):centers.append(c)
  if len(centers)<3:continue
  ep,_=profile(a,np.array(centers),np.arange(-500,501,100));cc,_=profile(a,controls(a,np.array(centers),start,end,len(centers)),np.arange(-500,501,100));
  neg.append(float(np.nanmedian(ep)-np.nanmedian(cc)))
# Save profile table
prows=[]
for p in profiles:
 for i,(lo,hi) in enumerate(zip(p['edges'][:-1],p['edges'][1:])):prows.append({'device_anon':p['device_anon'],'date':p['date'],'session_index':p['session_index'],'bin_start_ms':lo,'bin_end_ms':hi,'event_median_magnitude':p['event'][i],'control_median_magnitude':p['control'][i],'baseline_subtracted_difference':p['difference'][i],'event_coverage_n':p['event_cov'][i],'control_coverage_n':p['control_cov'][i]})
pd.DataFrame(rows).to_csv(OUT/'session_validation_summary.csv',index=False);pd.DataFrame(prows).to_csv(OUT/'event_triggered_profiles.csv',index=False);pd.DataFrame({'negative_control_difference':neg}).to_csv(OUT/'negative_control_distribution.csv',index=False)
# summary stats and sensitivity
summary=[]
for tol in [500,1000]:
 x=pd.read_csv('output/analysis_candidates/cross_modal_event_export_v1/acc_touch_pilot_results.csv');x=x[x.tolerance_ms==tol];
 for strata,g in x.groupby(x.acc_median_interval_ms.map(lambda z:'high_rate_<=20ms' if z<=20 else ('mid_rate_20_100ms' if z<=100 else 'low_rate_>100ms'))): summary.append({'analysis':'saved_direct_window','tolerance_ms':tol,'cadence_stratum':strata,'sessions':len(g),'patients':g.device_anon.nunique(),'median_session_difference':g.within_session_median_difference.median(),'iqr_session_difference':g.within_session_median_difference.quantile(.75)-g.within_session_median_difference.quantile(.25)})
mean,lo,hi=bootstrap_session(obs)
summary.append({'analysis':'event_profile_central_baseline_subtracted','tolerance_ms':500,'cadence_stratum':'all','sessions':len(obs),'patients':pd.DataFrame(rows).device_anon.nunique(),'median_session_difference':float(np.median(obs)),'mean_session_difference':mean,'bootstrap95_low':lo,'bootstrap95_high':hi,'negative_control_median':float(np.median(neg)) if neg else np.nan,'negative_control_p95_abs':float(np.percentile(np.abs(neg),95)) if neg else np.nan,'negative_control_n':len(neg)})
pd.DataFrame(summary).to_csv(OUT/'sensitivity_summary.csv',index=False)
# plots
plt.style.use('seaborn-v0_8-whitegrid')
fig,ax=plt.subplots(figsize=(8,4.5));
for p in profiles: ax.plot((p['edges'][:-1]+p['edges'][1:])/2,p['difference'],alpha=.65,label=f"{p['device_anon']} {p['date']} s{p['session_index']}")
ax.axvline(0,color='k',lw=.8);ax.axhline(0,color='k',lw=.8);ax.set(xlabel='Time relative to touch (ms)',ylabel='Baseline-subtracted event minus control magnitude',title='Event-triggered ACC × Touch profile');ax.legend(fontsize=6,ncol=2);fig.tight_layout();fig.savefig(OUT/'event_triggered_motion_profile.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(6,4));ax.hist(neg,bins=30,alpha=.75,label='Shifted/negative controls');ax.axvline(np.median(obs),color='red',lw=2,label='Observed median session contrast');ax.set(xlabel='Central motion contrast',ylabel='Negative-control count',title='Temporal negative controls');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(OUT/'negative_control_distribution.png',dpi=180);plt.close(fig)
print('sessions',len(rows),'patients',len(set(r['device_anon'] for r in rows)),'negative_controls',len(neg),'observed_median',float(np.median(obs)) if len(obs) else None)
