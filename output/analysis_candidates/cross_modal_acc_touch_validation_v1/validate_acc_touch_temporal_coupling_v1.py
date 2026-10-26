from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt, json
OUT=Path('output/analysis_candidates/cross_modal_acc_touch_validation_v1');OUT.mkdir(parents=True,exist_ok=True);SRC=Path('output/analysis_candidates/cross_modal_event_export_v1/parquet')
def load(dev,date,s,mod):
 p=SRC/f'patient={dev[-6:]}/device={dev}/date={date}/modality={mod}/session_{s:02d}.parquet';return pd.read_parquet(p) if p.exists() else pd.DataFrame()
def session_data(dev,date,s):
 a=load(dev,date,s,'accelerometer');t=load(dev,date,s,'touch');scr=load(dev,date,s,'screen')
 if a.empty or t.empty:return None
 a=a.dropna(subset=['acc_x','acc_y','acc_z']).sort_values('timestamp_ms'); at=np.sort(a.timestamp_ms.astype(np.int64).unique()); vals=a.groupby('timestamp_ms',sort=True)[['acc_x','acc_y','acc_z']].median(); vals=vals.loc[vals.index.intersection(at)]; mag=np.sqrt((vals**2).sum(axis=1)).to_numpy();at=vals.index.to_numpy(np.int64);tt=np.sort(t.timestamp_ms.astype(np.int64).unique());start=int(scr.session_start_ms.iloc[0]) if not scr.empty else int(at[0]);end=int(scr.session_end_ms.iloc[0]) if not scr.empty else int(at[-1]);return at,mag,tt,start,end
def med_window(at,mag,centers,lo,hi):
 out=[]
 for c in centers:
  i=np.searchsorted(at,c+lo,'left');j=np.searchsorted(at,c+hi,'left');out.append(float(np.median(mag[i:j])) if j>i else np.nan)
 return np.array(out)
def prof(at,mag,centers,edges):
 p=[];cov=[]
 for lo,hi in zip(edges[:-1],edges[1:]):
  z=med_window(at,mag,centers,lo,hi);p.append(np.nanmedian(z) if np.isfinite(z).any() else np.nan);cov.append(int(np.isfinite(z).sum()))
 return np.array(p),np.array(cov)
def controls(at,touch,start,end,n,rng=None,shift=None):
 if shift is None: shift=2000
 c=touch+shift; c=np.where(c>=end-1000,start+(c-start)%max(1,end-start),c);good=(c>=start+1000)&(c<end-1000)
 c=c[good];
 if len(c): c=c[np.array([not np.any(np.abs(touch-x)<=1500) for x in c])]
 if len(c)>=n:return c[:n]
 cand=np.arange(start+2000,end-2000,500,dtype=np.int64)
 if rng is not None:rng.shuffle(cand)
 for x in cand:
  if np.all(np.abs(touch-x)>1500) and np.any((at>=x-500)&(at<x+500)):c=np.append(c,x)
  if len(c)>=n:break
 return c[:n]
def boot(x,seed=1):
 x=np.asarray(x,float);x=x[np.isfinite(x)];
 if not len(x):return np.nan,np.nan,np.nan
 rng=np.random.default_rng(seed);m=np.array([np.mean(rng.choice(x,len(x),replace=True)) for _ in range(2000)]);return float(np.mean(x)),float(np.percentile(m,2.5)),float(np.percentile(m,97.5))
manifest=pd.read_csv('output/analysis_candidates/cross_modal_event_export_v1/checkpoint_manifest.csv'); rows=[];profiles=[];objs=[]
for _,m in manifest.iterrows():
 for s in range(1,int(m.session_count)+1):
  got=session_data(m.device_anon,m.day,s)
  if got is None:continue
  at,mag,touch,start,end=got;d=np.diff(at);edges=np.arange(-2000,2001,100);ep,ec=prof(at,mag,touch,edges);cc=controls(at,touch,start,end,len(touch));cp,xc=prof(at,mag,cc,edges);bi=(edges[:-1]>=-1500)&(edges[1:]<=-500);diff=(ep-np.nanmedian(ep[bi]))-(cp-np.nanmedian(cp[bi]));central=(edges[:-1]>=-500)&(edges[1:]<=500);direct=[]
  for t in touch:
   c=controls(at,np.array([t]),start,end,1);ev=med_window(at,mag,np.array([t]),-500,501);co=med_window(at,mag,c,-500,501)
   if np.isfinite(ev).all() and np.isfinite(co).all():direct.append(ev[0]-co[0])
  med=float(np.median(d)) if len(d) else np.nan; stratum='high_rate_<=20ms' if med<=20 else ('mid_rate_20_100ms' if med<=100 else 'low_rate_>100ms')
  rows.append({'device_anon':m.device_anon,'date':m.day,'session_index':s,'touch_events':len(touch),'matched_control_centers':len(cc),'acc_samples':len(at),'acc_median_interval_ms':med,'acc_p95_interval_ms':float(np.percentile(d,95)) if len(d) else np.nan,'acc_gap_gt1s':int((d>1000).sum()) if len(d) else 0,'event_profile_coverage_central_median':float(np.nanmedian(ec[central])),'control_profile_coverage_central_median':float(np.nanmedian(xc[central])),'central_event_control_difference_baseline_subtracted':float(np.nanmedian(diff[central])),'direct_500ms_pair_median_difference':float(np.median(direct)) if direct else np.nan,'direct_500ms_pairs':len(direct),'cadence_stratum':stratum})
  profiles.append((m.device_anon,m.day,s,edges,ep,cp,diff,ec,xc));objs.append((m.device_anon,m.day,s,at,mag,touch,start,end))
obs=np.array([r['central_event_control_difference_baseline_subtracted'] for r in rows]);rng=np.random.default_rng(19);neg=[]
for dev,date,s,at,mag,touch,start,end in objs:
 for _ in range(50):
  shift=int(rng.integers(3000,max(3001,end-start-3000))) if end-start>7000 else 3000;c=np.array([start+((int(t)-start+shift)%(end-start)) for t in touch]);c=c[(c>=start+2000)&(c<end-2000)];c=np.array([x for x in c if np.all(np.abs(touch-x)>1500)])
  if len(c)<3:continue
  ep,_=prof(at,mag,c,np.arange(-500,501,100));ctrl=controls(at,c,start,end,len(c),rng=rng);cp,_=prof(at,mag,ctrl,np.arange(-500,501,100));neg.append(float(np.nanmedian(ep)-np.nanmedian(cp)))
prows=[]
for dev,date,s,e,ep,cp,df,ec,xc in profiles:
 for i,(lo,hi) in enumerate(zip(e[:-1],e[1:])):prows.append({'device_anon':dev,'date':date,'session_index':s,'bin_start_ms':lo,'bin_end_ms':hi,'event_median_magnitude':ep[i],'control_median_magnitude':cp[i],'baseline_subtracted_difference':df[i],'event_coverage_n':ec[i],'control_coverage_n':xc[i]})
pd.DataFrame(rows).to_csv(OUT/'session_validation_summary.csv',index=False);pd.DataFrame(prows).to_csv(OUT/'event_triggered_profiles.csv',index=False);pd.DataFrame({'negative_control_difference':neg}).to_csv(OUT/'negative_control_distribution.csv',index=False)
mean,lo,hi=boot(obs); sens=pd.DataFrame(rows).groupby('cadence_stratum').agg(sessions=('session_index','count'),patients=('device_anon','nunique'),median_difference=('central_event_control_difference_baseline_subtracted','median'),median_direct_500ms=('direct_500ms_pair_median_difference','median')).reset_index();sens.to_csv(OUT/'cadence_sensitivity.csv',index=False)
pd.DataFrame([{'independent_patients':len(set(r['device_anon'] for r in rows)),'device_days':len(set((r['device_anon'],r['date']) for r in rows)),'sessions':len(rows),'touch_events':sum(r['touch_events'] for r in rows),'observed_session_median_difference':float(np.median(obs)),'observed_session_mean_difference':mean,'bootstrap95_low':lo,'bootstrap95_high':hi,'negative_control_n':len(neg),'negative_control_median':float(np.median(neg)) if neg else np.nan,'negative_control_abs_p95':float(np.percentile(np.abs(neg),95)) if neg else np.nan}]).to_csv(OUT/'validation_summary.csv',index=False)
# plots
plt.style.use('seaborn-v0_8-whitegrid');fig,ax=plt.subplots(figsize=(8,4.5))
for dev,date,s,e,ep,cp,df,ec,xc in profiles:ax.plot((e[:-1]+e[1:])/2,df,alpha=.7,label=f'{dev} {date} s{s}')
ax.axvline(0,color='k',lw=.8);ax.axhline(0,color='k',lw=.8);ax.set(xlabel='Time relative to touch (ms)',ylabel='Baseline-subtracted event − control magnitude',title='Event-triggered ACC × Touch profile');ax.legend(fontsize=6,ncol=2);fig.tight_layout();fig.savefig(OUT/'event_triggered_motion_profile.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(6,4));ax.hist(neg,bins=25,alpha=.75);ax.axvline(float(np.median(obs)),color='red',lw=2,label='Observed session median');ax.set(xlabel='Central motion contrast',ylabel='Shifted-control count',title='Temporal negative controls');ax.legend();fig.tight_layout();fig.savefig(OUT/'negative_control_distribution.png',dpi=180);plt.close(fig)
print('completed',len(rows),'sessions',len(neg),'negative controls')
