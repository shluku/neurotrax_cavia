from pathlib import Path
import pandas as pd,numpy as np,json
OUT=Path('output/analysis_candidates/cross_modal_coverage_bottleneck_v1');OUT.mkdir(parents=True,exist_ok=True)
SRC=Path('output/analysis_candidates/cross_modal_repeated_day_export_v1/parquet')
MAN=pd.read_csv('output/analysis_candidates/cross_modal_repeated_day_export_v1/checkpoint_manifest.csv')
def load(dev,date,s,mod):
 p=SRC/f'patient={dev[-6:]}/device={dev}/date={date}/modality={mod}/session_{s:02d}.parquet';return pd.read_parquet(p) if p.exists() else pd.DataFrame()
# Build selected-session rows from manifest and parquet. All selected episodes are verified screen sessions by extractor construction.
rows=[]
for _,m in MAN.iterrows():
 screen_dir=SRC/f'patient={m.device_anon[-6:]}/device={m.device_anon}/date={m.day}/modality=screen'
 session_ids=sorted(int(p.stem.split('_')[-1]) for p in screen_dir.glob('session_*.parquet'))
 for s in session_ids:
  scr=load(m.device_anon,m.day,s,'screen');a=load(m.device_anon,m.day,s,'accelerometer');t=load(m.device_anon,m.day,s,'touch');k=load(m.device_anon,m.day,s,'keyboard');app=load(m.device_anon,m.day,s,'applications_foreground')
  if scr.empty:continue
  st=int(scr.session_start_ms.iloc[0]);en=int(scr.session_end_ms.iloc[0]);
  if a.empty: med=np.nan;p95=np.nan;gaps=np.nan;dur=0;bins=0;moving=0;stationary=0;acc_samples=0;longest=0
  else:
   ts=np.sort(a.timestamp_ms.astype(int).unique());di=np.diff(ts);med=float(np.median(di)) if len(di) else np.nan;p95=float(np.percentile(di,95)) if len(di) else np.nan;gaps=int((di>1000).sum());dur=float((ts[-1]-ts[0])/1000) if len(ts)>1 else 0;acc_samples=len(ts)
   seg=[];cur=0
   for x in di:
    if x<=1000:cur+=x/1000
    else:seg.append(cur);cur=0
   seg.append(cur);longest=max(seg) if seg else 0
   v=a[['acc_x','acc_y','acc_z']].dropna().to_numpy(float);res=np.linalg.norm(v-np.median(v,axis=0),axis=1);bs=pd.DataFrame({'bin':(a.timestamp_ms.astype(int)//1000)*1000,'res':res}).groupby('bin').res.median();bins=len(bs)
   moving=int((bs>=0.15).sum());stationary=int((bs<0.15).sum())
  # events in motion states at fixed 0.15
  touch_n=len(t);key_n=len(k);app_n=len(app)
  rows.append({'device_anon':m.device_anon,'day':m.day,'session_index':s,'session_seconds':(en-st)/1000,'acc_present':not a.empty,'acc_samples':acc_samples,'acc_duration_s':dur,'acc_median_interval_ms':med,'acc_p95_interval_ms':p95,'acc_gap_gt1s':gaps,'longest_contiguous_acc_s':longest,'screen_verified':True,'touch_events':touch_n,'keyboard_snapshots':key_n,'app_events':app_n,'synchronized_touch':bool(not a.empty and touch_n>0),'synchronized_keyboard':bool(not a.empty and key_n>0),'motion_bins':bins,'moving_bins':moving,'stationary_bins':stationary,'both_motion_states':bool(moving>0 and stationary>0)})
df=pd.DataFrame(rows)
# sequential funnel, separate touch and keyboard minimum count (3 intervals each) approximated from Phase 7 output when matching rows available
motion=pd.read_csv('output/analysis_candidates/cross_modal_repeated_day_export_v1/motion_conditioned_session_feasibility.csv')
m15=motion[motion.motion_threshold_residual_units==0.15][['device_anon','date','session_index','touch_moving_intervals','touch_stationary_intervals','keyboard_moving_intervals','keyboard_stationary_intervals']]
df=df.merge(m15,left_on=['device_anon','day','session_index'],right_on=['device_anon','date','session_index'],how='left').drop(columns=['date'])
df['touch_minimum_both_states']=(df.touch_moving_intervals.fillna(0)>=3)&(df.touch_stationary_intervals.fillna(0)>=3)
df['keyboard_minimum_both_states']=(df.keyboard_moving_intervals.fillna(0)>=3)&(df.keyboard_stationary_intervals.fillna(0)>=3)
# funnel rows with explicit denominator and reason counts
funnel=[]
def add(stage,mask,reason):
 sub=df[mask];funnel.append({'feature_target':reason.split('_')[0],'stage':stage,'sessions_remaining':int(mask.sum()),'devices_remaining':sub.device_anon.nunique(),'device_days_remaining':len(sub[['device_anon','day']].drop_duplicates()),'touch_events_remaining':int(sub.touch_events.sum()),'keyboard_snapshots_remaining':int(sub.keyboard_snapshots.sum()),'exclusion_reason_at_stage':reason})
base=np.ones(len(df),dtype=bool);add('verified_screen_session',base,'none_selected_verified')
mask=base&df.acc_present;add('ACC_present',mask,'missing_ACC_recording')
mask2=mask&df.synchronized_touch;add('ACC_plus_touch_synchronized',mask2,'missing_touch_or_ACC_overlap')
mask3=mask2&(df.acc_samples>=50)&(df.acc_gap_gt1s==0);add('ACC_sampling_gap_QC',mask3,'insufficient_ACC_samples_or_gaps')
mask4=mask3&df.both_motion_states;add('both_motion_states',mask4,'no_stationary_or_moving_variation')
add('touch_minimum_intervals',mask4&df.touch_minimum_both_states,'insufficient_touch_intervals_in_both_states')
maskk=mask&df.synchronized_keyboard;add('ACC_plus_keyboard_synchronized',maskk,'missing_keyboard_or_ACC_overlap')
maskk2=maskk&(df.acc_samples>=50)&(df.acc_gap_gt1s==0);add('keyboard_ACC_sampling_gap_QC',maskk2,'insufficient_ACC_samples_or_gaps')
add('keyboard_both_state_minimum',maskk2&df.keyboard_minimum_both_states,'insufficient_keyboard_intervals_in_both_states')
pd.DataFrame(funnel).to_csv(OUT/'sequential_eligibility_funnel.csv',index=False)
df.to_csv(OUT/'session_coverage_diagnostics.csv',index=False)
# distribution summaries
summ=[]
for c in ['acc_duration_s','longest_contiguous_acc_s','acc_median_interval_ms','acc_p95_interval_ms','acc_samples','touch_events','keyboard_snapshots','moving_bins','stationary_bins']:
 x=pd.to_numeric(df[c],errors='coerce').dropna();summ.append({'metric':c,'n_sessions':len(x),'median':x.median(),'iqr':x.quantile(.75)-x.quantile(.25),'min':x.min(),'max':x.max()})
pd.DataFrame(summ).to_csv(OUT/'coverage_distributions.csv',index=False)
# counterfactual fixed windows, non-overlapping from session start, with ACC and touch/keyboard counts
wr=[]
for _,r in df.iterrows():
 for w in [30,60,300,600]:
  a=load(r.device_anon,r.day,r.session_index,'accelerometer');t=load(r.device_anon,r.day,r.session_index,'touch');k=load(r.device_anon,r.day,r.session_index,'keyboard');
  if a.empty: n=0; accw=0;tw=0;kw=0
  else:
   st=int(a.timestamp_ms.min());en=int(a.timestamp_ms.max());n=int(np.floor((en-st)/1000/w));accw=tw=kw=0
   for i in range(n):
    x=st+i*w*1000;y=x+w*1000;aa=a[(a.timestamp_ms>=x)&(a.timestamp_ms<y)];
    if len(aa):accw+=1
    if not t.empty and ((t.timestamp_ms>=x)&(t.timestamp_ms<y)).any():tw+=1
    if not k.empty and ((k.timestamp_ms>=x)&(k.timestamp_ms<y)).any():kw+=1
  wr.append({'device_anon':r.device_anon,'day':r.day,'session_index':r.session_index,'window_s':w,'windows_total':n,'windows_with_ACC':accw,'windows_with_touch':tw,'windows_with_keyboard':kw})
pd.DataFrame(wr).to_csv(OUT/'counterfactual_window_feasibility.csv',index=False)
# alternatives
alt=[]
for name,definition,dup,status,req in [
 ('ACC magnitude during touch-active vs matched screen-control','session ACC magnitude in windows containing touch events vs non-touch windows','new cross-table feature','feasible_on_ACC_plus_touch_sessions','ACC+touch overlap; no dual-state requirement'),
 ('Motion magnitude × interaction density','within-session correlation of ACC residual magnitude and touch counts per fixed time bin','new cross-table feature','pilot-feasible_if>=3_binned_events','ACC+touch bins; rate/gap QC'),
 ('ACC variability conditional on app context','ACC residual SD/IQR within observed foreground-app hash episodes','new cross-table feature','feasible_on_ACC_plus_app_sessions_but_sparse','ACC+app overlap and repeated app context'),
 ('Touch interval variability by motion state','Phase 7 moving-minus-stationary touch IQR','new cross-table feature','blocked_by_dual_state_eligibility','both states and >=3 intervals each'),
 ('Keyboard snapshot interval variability by motion state','Phase 7 moving-minus-stationary keyboard snapshot IQR','new cross-table proxy','blocked_by_keyboard_coverage','keyboard events in both states'),
 ('Touch rate / interval summaries','existing Screen×Touch session summaries','existing single-table/session context','already_implemented','not novel'),
 ('App transitions / keyboard IEI','existing Screen×App and Keyboard×App summaries','existing single-table/session context','already_implemented','not novel')]:alt.append({'feature':name,'definition':definition,'novelty_status':dup,'feasibility_status':status,'minimum_data_requirement':req,'sessions_ACC_touch':int(df.synchronized_touch.sum()),'sessions_ACC_keyboard':int(df.synchronized_keyboard.sum()),'sessions_ACC_app':int((df.acc_present&(df.app_events>0)).sum())})
pd.DataFrame(alt).to_csv(OUT/'alternative_feature_feasibility_matrix.csv',index=False)
print(pd.DataFrame(funnel).to_string(index=False));print('\nDIST\n',pd.DataFrame(summ).to_string(index=False))
