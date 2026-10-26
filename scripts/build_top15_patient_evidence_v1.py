from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/research_summary_20261025/top15_article_statistics_v1'
TOP=pd.read_csv(ROOT/'output/research_summary_20261025/top15_feature_cognition_associations_20261025.csv')

def norm(s): return s.astype(str).str.replace(r'\.0$','',regex=True).str.zfill(3)
def partial_rho(frame, x, y, covars):
    d=frame[[x,y,*covars]].apply(pd.to_numeric,errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
    if len(d)<12:return np.nan,len(d)
    ranks=d.rank(method='average'); Z=np.c_[np.ones(len(d)),ranks[covars].to_numpy(float)]
    rx=ranks[x].to_numpy(float)-Z@np.linalg.lstsq(Z,ranks[x].to_numpy(float),rcond=None)[0]
    ry=ranks[y].to_numpy(float)-Z@np.linalg.lstsq(Z,ranks[y].to_numpy(float),rcond=None)[0]
    return (float(np.corrcoef(rx,ry)[0,1]) if np.std(rx)>0 and np.std(ry)>0 else np.nan),len(d)
# Saved keyboard windows and cognition tables.
w=pd.read_csv(ROOT/'output/analysis_candidates/keyboard_deep_dive_v1/keyboard_deep_dive_window_features.csv',dtype={'Subject_ID_D':str}); w.Subject_ID_D=norm(w.Subject_ID_D)
t1w=w[w.window_name.eq('T1')].copy(); t2w=w[w.window_name.eq('T2')].copy()
c1=pd.read_csv(ROOT/'output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv',dtype={'Subject_ID_D':str}); c1.Subject_ID_D=norm(c1.Subject_ID_D)
c2=pd.read_csv(ROOT/'output/analysis_candidates/phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv',dtype={'Subject_ID_D':str}); c2.Subject_ID_D=norm(c2.Subject_ID_D)
# Keep only relevant columns and merge once.
meta=['Subject_ID_D','age','Gender (1=M, 2=F)','Education (years)']
base=t1w.merge(c1[meta+['global_T1','memory_T1','ef_T1','attention_T1','processing_speed_T1','verbal_T1','motor_T1','iq_T1']],on='Subject_ID_D',how='inner')
paired=t1w.merge(t2w,on='Subject_ID_D',how='inner',suffixes=('_T1','_T2')).merge(c2[['Subject_ID_D','global_delta','memory_delta','ef_delta','attention_delta','processing_speed_delta','verbal_delta','motor_delta','iq_delta']],on='Subject_ID_D',how='inner')
# Feature definitions available in both windows.
features=[f for f in t1w.columns if f.startswith('keyboard_')]
for f in features:
    if f+'_T1' in paired and f+'_T2' in paired:
        paired[f+'_delta']=pd.to_numeric(paired[f+'_T2'],errors='coerce')-pd.to_numeric(paired[f+'_T1'],errors='coerce')

outcome_t1={'global':'global_T1','attention':'attention_T1','executive_function':'ef_T1','processing_speed':'processing_speed_T1','memory':'memory_T1','motor':'motor_T1','verbal':'verbal_T1','iq':'iq_T1','global_T1':'global_T1','attention_T1':'attention_T1'}
outcome_delta={'global':'global_delta','attention':'attention_delta','executive_function':'ef_delta','processing_speed':'processing_speed_delta','memory':'memory_delta','motor':'motor_delta','verbal':'verbal_delta','iq':'iq_delta'}
patient_rows=[]; audits=[]; summaries=[]
for idx,r in TOP.iterrows():
    feature=str(r.feature); outcome=str(r.outcome); tp=str(r.outcome_timepoint); source=str(r.source_file)
    kind='unavailable_exact_patient_inputs'
    frame=None; x=None; y=None
    if 'signal_discovery' in source and tp=='T1' and feature in base and outcome in outcome_t1:
        frame=base; x=feature; y=outcome_t1[outcome]; kind='exact_saved_signal_discovery_inputs'
    elif 'signal_discovery' in source and tp=='T2_minus_T1' and feature+'_delta' in paired and outcome in outcome_delta:
        frame=paired; x=feature+'_delta'; y=outcome_delta[outcome]; kind='exact_saved_signal_discovery_inputs'
    elif 't2_reliability' in source and tp=='T2_minus_T1' and feature+'_delta' in paired and outcome in outcome_delta:
        frame=paired; x=feature+'_delta'; y=outcome_delta[outcome]; kind='broad_saved_inputs_threshold_cohort_not_recoverable'
    # Legacy patient-level table exists, but exact trimmed exclusions are not encoded in the association row.
    if 'keyboard_two_feature' in source:
        lp=pd.read_csv(ROOT/'output/analysis_candidates/keyboard_two_feature_median_timespan/keyboard_two_feature_patient_data.csv',dtype={'Subject_ID_D':str}); lp.Subject_ID_D=norm(lp.Subject_ID_D)
        feature_col=feature if feature in lp.columns else None; ycol=outcome if outcome in lp.columns else None
        if feature_col and ycol:
            frame=lp; x=feature_col; y=ycol; kind='broad_legacy_patient_inputs_exact_trim_rule_not_recoverable'
    if frame is None or x is None or y is None:
        audits.append({'top15_row':idx+1,'label':r.label,'source_n':r.n,'reconstructed_n':np.nan,'reconstructed_rho':np.nan,'reconstructed_p':np.nan,'cohort_match_status':kind,'rho_difference':np.nan,'p_difference':np.nan})
        continue
    d=frame[['Subject_ID_D',x,y]].copy(); d[x]=pd.to_numeric(d[x],errors='coerce'); d[y]=pd.to_numeric(d[y],errors='coerce'); d=d.replace([np.inf,-np.inf],np.nan).dropna()
    raw_rho,raw_p=(spearmanr(d[x],d[y]).statistic,spearmanr(d[x],d[y]).pvalue) if len(d)>=3 else (np.nan,np.nan)
    effective_n=len(d)
    if 'partial' in str(r.estimate_type).lower() and kind=='exact_saved_signal_discovery_inputs':
        rho,effective_n=partial_rho(frame,x,y,['age','Gender (1=M, 2=F)','Education (years)'])
        p=np.nan
    else:
        rho,p=raw_rho,raw_p
    status=kind
    # Exact match means n and estimate agree to rounding with source row.
    if kind=='exact_saved_signal_discovery_inputs':
        status='exact_reproduction' if effective_n==int(r.n) and np.isclose(rho,float(r.estimate),atol=1e-6) else 'saved_inputs_do_not_reproduce_source_row'
    audits.append({'top15_row':idx+1,'label':r.label,'source_n':r.n,'reconstructed_n':len(d),'reconstructed_rho':rho,'reconstructed_p':p,'cohort_match_status':status,'rho_difference':rho-float(r.estimate) if np.isfinite(rho) else np.nan,'p_difference':p-float(r.p) if np.isfinite(p) else np.nan})
    # Patient-level rows, privacy-safe numeric values only.
    for _,z in d.iterrows():
        patient_rows.append({'top15_row':idx+1,'label':r.label,'patient_id':z.Subject_ID_D,'feature_value_used':z[x],'outcome_value_used':z[y],'timepoint':tp,'cohort_match_status':status})
    vals=d[x]; ys=d[y]
    summaries.append({'top15_row':idx+1,'label':r.label,'cohort_status':status,'n':len(d),'feature_median':vals.median(),'feature_iqr':vals.quantile(.75)-vals.quantile(.25),'feature_min':vals.min(),'feature_max':vals.max(),'outcome_median':ys.median(),'outcome_iqr':ys.quantile(.75)-ys.quantile(.25),'outcome_min':ys.min(),'outcome_max':ys.max(),'positive_feature_count':np.nan,'negative_feature_count':np.nan,'zero_feature_count':np.nan})

pd.DataFrame(audits).to_csv(OUT/'top15_reconstruction_audit.csv',index=False)
pd.DataFrame(patient_rows).to_csv(OUT/'top15_patient_level_pairs_reconstructable.csv',index=False)
pd.DataFrame(summaries).to_csv(OUT/'top15_reconstructable_distributions.csv',index=False)
print('audit statuses')
print(pd.DataFrame(audits).cohort_match_status.value_counts().to_string())
print(pd.DataFrame(audits)[['top15_row','source_n','reconstructed_n','rho_difference','cohort_match_status']].to_string(index=False))
