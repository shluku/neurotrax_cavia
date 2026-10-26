from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output/research_summary_20261025/top15_article_statistics_v1'
TOP=pd.read_csv(ROOT/'output/research_summary_20261025/top15_feature_cognition_associations_20261025.csv')
AUD=pd.read_csv(OUT/'top15_reconstruction_audit.csv')
exact=AUD[AUD.cohort_match_status.eq('exact_reproduction')].top15_row.astype(int).tolist()

def norm(s): return s.astype(str).str.replace(r'\.0$','',regex=True).str.zfill(3)
w=pd.read_csv(ROOT/'output/analysis_candidates/keyboard_deep_dive_v1/keyboard_deep_dive_window_features.csv',dtype={'Subject_ID_D':str}); w.Subject_ID_D=norm(w.Subject_ID_D)
t1=w[w.window_name.eq('T1')].copy(); t2=w[w.window_name.eq('T2')].copy()
c1=pd.read_csv(ROOT/'output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv',dtype={'Subject_ID_D':str}); c1.Subject_ID_D=norm(c1.Subject_ID_D)
c2=pd.read_csv(ROOT/'output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv',dtype={'Subject_ID_D':str}); c2.Subject_ID_D=norm(c2.Subject_ID_D)
base=t1.merge(c1,on='Subject_ID_D',how='inner',suffixes=('','_cog'))
paired=t1.merge(t2,on='Subject_ID_D',how='inner',suffixes=('_T1','_T2')).merge(c1,on='Subject_ID_D',how='inner').merge(c2,on='Subject_ID_D',how='inner',suffixes=('','_T2cog'))

def val(d,c): return pd.to_numeric(d[c],errors='coerce') if c in d else pd.Series(np.nan,index=d.index)
def stats(s):
    s=pd.to_numeric(s,errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
    if len(s)==0:return (np.nan,np.nan,np.nan,np.nan,len(s))
    return (s.median(),s.quantile(.75)-s.quantile(.25),s.min(),s.max(),len(s))
rows=[]; summaries=[]
for rownum in exact:
    r=TOP.iloc[rownum-1]; feat=str(r.feature); outcome=str(r.outcome); tp=str(r.outcome_timepoint); long=tp=='T2_minus_T1'
    if long:
        d=paired.copy(); fx=feat+'_T1'; fl=feat+'_T2'; fy=({'global':'global','attention':'attention','executive_function':'ef','processing_speed':'processing_speed','memory':'memory','motor':'motor','verbal':'verbal','iq':'iq'}[outcome])
        y1,y2,yd=fy+'_T1',fy+'_T2',fy+'_delta'
        d['feature_early']=val(d,fx); d['feature_late']=val(d,fl); d['feature_delta']=d.feature_late-d.feature_early
        d['cognitive_t1']=val(d,y1); d['cognitive_t2']=val(d,y2); d['cognitive_delta']=val(d,yd)
        d['coverage_active_days_early']=val(d,'keyboard_active_days_T1'); d['coverage_active_days_late']=val(d,'keyboard_active_days_T2')
        d['coverage_snapshots_early']=val(d,'keyboard_distinct_observation_count_T1'); d['coverage_snapshots_late']=val(d,'keyboard_distinct_observation_count_T2')
        d['coverage_valid_intervals_early']=val(d,'keyboard_valid_interval_count_T1'); d['coverage_valid_intervals_late']=val(d,'keyboard_valid_interval_count_T2')
    else:
        d=base.copy(); fy=({'global':'global','attention':'attention','executive_function':'ef','processing_speed':'processing_speed','memory':'memory','motor':'motor','verbal':'verbal','iq':'iq','global_T1':'global','attention_T1':'attention'}[outcome])
        y1=fy+'_T1'; d['feature_early']=val(d,feat); d['feature_late']=np.nan; d['feature_delta']=np.nan; d['cognitive_t1']=val(d,y1); d['cognitive_t2']=np.nan; d['cognitive_delta']=np.nan
        d['coverage_active_days_early']=val(d,'keyboard_active_days'); d['coverage_active_days_late']=np.nan; d['coverage_snapshots_early']=val(d,'keyboard_distinct_observation_count'); d['coverage_snapshots_late']=np.nan; d['coverage_valid_intervals_early']=val(d,'keyboard_valid_interval_count'); d['coverage_valid_intervals_late']=np.nan
    keep=['Subject_ID_D','feature_early','feature_late','feature_delta','cognitive_t1','cognitive_t2','cognitive_delta','coverage_active_days_early','coverage_active_days_late','coverage_snapshots_early','coverage_snapshots_late','coverage_valid_intervals_early','coverage_valid_intervals_late']
    d=d[keep].copy(); d.insert(0,'top15_row',rownum); d.insert(1,'label',r.label); rows.append(d)
    summary={'top15_row':rownum,'label':r.label,'n':len(d),'timepoint':tp}
    for prefix, col in [('feature_early','feature_early'),('feature_late','feature_late'),('feature_delta','feature_delta'),('cognitive_t1','cognitive_t1'),('cognitive_t2','cognitive_t2'),('cognitive_delta','cognitive_delta')]:
        med,iqr,mi,ma,n=stats(d[col]); summary.update({prefix+'_median':med,prefix+'_iqr':iqr,prefix+'_min':mi,prefix+'_max':ma,prefix+'_n':n})
    ch=pd.to_numeric(d.feature_delta,errors='coerce').dropna(); summary.update({'positive_feature_changes':int((ch>0).sum()),'negative_feature_changes':int((ch<0).sum()),'zero_feature_changes':int((ch==0).sum()),'early_active_days_median':stats(d.coverage_active_days_early)[0],'late_active_days_median':stats(d.coverage_active_days_late)[0],'early_snapshots_median':stats(d.coverage_snapshots_early)[0],'late_snapshots_median':stats(d.coverage_snapshots_late)[0],'early_valid_intervals_median':stats(d.coverage_valid_intervals_early)[0],'late_valid_intervals_median':stats(d.coverage_valid_intervals_late)[0]})
    summaries.append(summary)
pd.concat(rows,ignore_index=True).to_csv(OUT/'top15_exact_patient_level_table.csv',index=False)
pd.DataFrame(summaries).to_csv(OUT/'top15_exact_distribution_summary.csv',index=False)
print('exact rows',exact,'patients',len(pd.concat(rows,ignore_index=True)))
print(pd.DataFrame(summaries)[['top15_row','n','positive_feature_changes','negative_feature_changes']].to_string(index=False))
