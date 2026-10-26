"""T1-only exploratory lexical/word-timing analysis from saved strict aggregates.

No raw text is accessed. The saved v1 extractor output is used, with fixed
feature thresholds and prespecified feature/outcome families. Stages JSON and
PNG figures; CSV authoring is performed by the companion Artifact Tool exporter.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'output/analysis_candidates/keyboard_deep_dive_v1/word_length_adjusted_completion_v1/word_length_patient_table_20261021_v1.csv'
WIN=ROOT/'output/analysis_candidates/keyboard_deep_dive_v1/word_length_adjusted_completion_v1/word_length_window_features_20261021_v1.csv'
OUT=ROOT/'output/analysis_candidates/keyboard_deep_dive_v1/lexical_t1_cross_sectional_v1'
STAGE=Path('/tmp/lexical_t1_cross_sectional_20261021'); STAGE.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
SEED=20261021

def clean(v):
    if v is None or (isinstance(v,float) and not math.isfinite(v)): return None
    if isinstance(v,(np.floating,np.integer)): return v.item()
    return v
def sanitize(v):
    if isinstance(v,dict): return {str(k):sanitize(x) for k,x in v.items()}
    if isinstance(v,list): return [sanitize(x) for x in v]
    if isinstance(v,(float,np.floating)) and not math.isfinite(float(v)): return None
    if isinstance(v,(np.integer,np.floating)): return v.item()
    return v
def bh(vals):
    p=np.asarray(vals,float); q=np.full(len(p),np.nan); ok=np.isfinite(p)
    if ok.any():
        idx=np.where(ok)[0]; order=idx[np.argsort(p[idx])]; a=p[order]*len(order)/np.arange(1,len(order)+1); a=np.minimum.accumulate(a[::-1])[::-1]; q[order]=np.minimum(a,1.)
    return q
def spearman_boot(x,y,reps=2000,seed=SEED):
    x=np.asarray(x,float); y=np.asarray(y,float); rho,p=spearmanr(x,y); rng=np.random.default_rng(seed); vals=[]
    for _ in range(reps):
        ix=rng.integers(0,len(x),len(x));
        if len(np.unique(x[ix]))>1 and len(np.unique(y[ix]))>1: vals.append(spearmanr(x[ix],y[ix]).statistic)
    return float(rho),float(p),float(np.quantile(vals,.025)) if vals else None,float(np.quantile(vals,.975)) if vals else None
def partial_rank(x,y,covs):
    z=pd.concat([x.rename('x'),y.rename('y'),covs],axis=1).replace([np.inf,-np.inf],np.nan).dropna()
    if len(z)<max(15,2+len(covs.columns)) or z.x.nunique()<3 or z.y.nunique()<3: return None
    ranks=z.rank(method='average'); X=np.column_stack([np.ones(len(ranks)),ranks[covs.columns].to_numpy()]);
    rx=ranks.x.to_numpy()-X@np.linalg.lstsq(X,ranks.x.to_numpy(),rcond=None)[0]; ry=ranks.y.to_numpy()-X@np.linalg.lstsq(X,ranks.y.to_numpy(),rcond=None)[0]
    rho,p=spearmanr(rx,ry); return float(rho),float(p),int(len(z))

def main():
    d=pd.read_csv(SRC,dtype={'Subject_ID_D':str}); w=pd.read_csv(WIN,dtype={'Subject_ID_D':str})
    cognitive=['verbal_T1','global_T1','attention_T1','processing_speed_T1','ef_T1']
    base=d[d.global_T1.notna()].copy(); t1win=w[w.window_name.eq('T1')]
    # Prespecified thresholds: short lexical/timing summaries 20 reliable tokens;
    # MATTR-50 50; MATTR-100 and MTLD 100.
    specs={
      'lexical_diversity_repetition':{
        'features':['word_ttr_T1','word_repetition_rate_T1','word_mattr_50_T1','word_mattr_100_T1','word_mtld_T1'],
        'outcomes':['verbal_T1','global_T1'],'thresholds':{'word_ttr_T1':20,'word_repetition_rate_T1':20,'word_mattr_50_T1':50,'word_mattr_100_T1':100,'word_mtld_T1':100}},
      'word_length':{
        'features':['word_mean_length_chars_T1','word_median_length_chars_T1','word_length_sd_chars_T1'],
        'outcomes':['verbal_T1','global_T1'],'thresholds':{'word_mean_length_chars_T1':20,'word_median_length_chars_T1':20,'word_length_sd_chars_T1':20}},
      'timing_variability':{
        'features':['completion_median_ms_T1','completion_iqr_ms_T1','completion_mad_ms_T1','completion_cv_T1','len_2_3_iqr_ms_T1','len_4_5_iqr_ms_T1','len_6_8_iqr_ms_T1','len_9_plus_iqr_ms_T1','length_adjusted_iqr_equal_group_median_ms_T1','length_residual_sd_ms_T1','length_residual_iqr_ms_T1'],
        'outcomes':['attention_T1','processing_speed_T1','ef_T1'],'thresholds':{f:20 for f in ['completion_median_ms_T1','completion_iqr_ms_T1','completion_mad_ms_T1','completion_cv_T1','len_2_3_iqr_ms_T1','len_4_5_iqr_ms_T1','len_6_8_iqr_ms_T1','len_9_plus_iqr_ms_T1','length_adjusted_iqr_equal_group_median_ms_T1','length_residual_sd_ms_T1','length_residual_iqr_ms_T1']}}
    }
    covcols=['active_days_T1','distinct_observations_in_window_T1','valid_interval_count_T1','unique_package_count_T1','unique_device_count_T1','reliable_fraction_T1']
    rows=[]
    for family,s in specs.items():
      for f in s['features']:
        if f not in d: continue
        threshold=s['thresholds'][f]; eligible=base[pd.to_numeric(base['reliable_completion_count_T1'],errors='coerce')>=threshold]
        for out in s['outcomes']:
          z=eligible[[f,out]].replace([np.inf,-np.inf],np.nan).dropna(); n=len(z)
          if n>=12 and z[f].nunique()>2 and z[out].nunique()>2:
            rho,p,lo,hi=spearman_boot(z[f],z[out],seed=SEED+n); cov=eligible.loc[z.index,covcols]; adj=partial_rank(z[f],z[out],cov)
            # fixed high-coverage sensitivity, defined before inspecting outcomes
            z100=base[(base.reliable_completion_count_T1>=100)][[f,out]].replace([np.inf,-np.inf],np.nan).dropna(); sens=spearman_boot(z100[f],z100[out],reps=1000,seed=SEED+100+n) if len(z100)>=12 and z100[f].nunique()>2 and z100[out].nunique()>2 else (None,None,None,None)
            rows.append({'testing_family':family,'feature_name':f,'outcome':out,'token_threshold':threshold,'eligible_feature_n':int(eligible[f].notna().sum()),'n':n,'spearman_rho':rho,'spearman_p':p,'bootstrap_ci_low':lo,'bootstrap_ci_high':hi,'coverage_adjusted_partial_rho':adj[0] if adj else None,'coverage_adjusted_p':adj[1] if adj else None,'coverage_adjusted_n':adj[2] if adj else None,'high_coverage_100_token_n':int(len(z100)),'high_coverage_100_token_rho':sens[0],'high_coverage_100_token_p':sens[1],'high_coverage_100_token_ci_low':sens[2],'high_coverage_100_token_ci_high':sens[3]})
    res=pd.DataFrame(rows); res['fdr_q']=np.nan; res['coverage_adjusted_fdr_q']=np.nan
    if not res.empty:
      for fam in res.testing_family.unique():
        ix=res.testing_family.eq(fam); res.loc[ix,'fdr_q']=bh(res.loc[ix,'spearman_p']); res.loc[ix,'coverage_adjusted_fdr_q']=bh(res.loc[ix,'coverage_adjusted_p'])
    # Coverage report: full T1 cohort and fixed 20/50/100-token subsets.
    covrows=[]
    for label,sub in [('all_valid_T1',base),('min20_reliable_tokens',base[base.reliable_completion_count_T1>=20]),('min50_reliable_tokens',base[base.reliable_completion_count_T1>=50]),('min100_reliable_tokens',base[base.reliable_completion_count_T1>=100])]:
      covrows.append({'cohort':label,'patients_with_valid_global_T1':int(len(sub)),'patients_with_any_reliable_tokens':int((sub.reliable_completion_count_T1>0).sum()),'median_reliable_tokens':float(sub.reliable_completion_count_T1.median()),'median_active_days':float(sub.active_days_T1.median()),'median_snapshots':float(sub.distinct_observations_in_window_T1.median()),'median_continuity_breaks':float(sub.continuity_break_count_T1.median()),'median_reliable_fraction':float(sub.reliable_fraction_T1.median()),'median_unique_packages':float(sub.unique_package_count_T1.median()),'median_unique_devices':float(sub.unique_device_count_T1.median())})
    # Approximate assessment-to-recording timing from saved window timestamps where available.
    time_report=[]
    if 'T1_date_iso' in d and 'window_start_ms' in t1win:
      dates=d[['Subject_ID_D','T1_date_iso']].drop_duplicates().copy(); dates['assessment']=pd.to_datetime(dates.T1_date_iso,errors='coerce',utc=True)
      starts=t1win[['Subject_ID_D','window_start_ms']].copy(); starts['window_start']=pd.to_datetime(starts.window_start_ms,unit='ms',errors='coerce',utc=True)
      gg=dates.merge(starts,on='Subject_ID_D',how='inner'); gap=(gg.window_start-gg.assessment).dt.total_seconds()/86400; gap=gap.dropna()
      if len(gap): time_report=[{'metric':'assessment_to_T1_window_start_days','n':int(len(gap)),'median':float(gap.median()),'iqr':float(gap.quantile(.75)-gap.quantile(.25)),'min':float(gap.min()),'max':float(gap.max())}]
    # Feature dictionary and comparison/status tables.
    definitions=[
      ('word_ttr_T1','lexical','unique observable normalized token types / reliable tokens','ratio',20),('word_repetition_rate_T1','lexical','1 − TTR','ratio',20),('word_mattr_50_T1','lexical','mean TTR across fixed 50-token moving windows','ratio',50),('word_mattr_100_T1','lexical','mean TTR across fixed 100-token moving windows','ratio',100),('word_mtld_T1','lexical','MTLD estimate; only with >=100 reliable tokens','tokens/factor',100),('word_mean_length_chars_T1','word_length','mean normalized observable token length','characters',20),('word_median_length_chars_T1','word_length','median normalized observable token length','characters',20),('word_length_sd_chars_T1','word_length','SD of normalized observable token length','characters',20),('completion_median_ms_T1','timing','median reliable observable completion duration','ms',20),('completion_iqr_ms_T1','timing','IQR of reliable completion duration','ms',20),('completion_mad_ms_T1','timing','MAD of reliable completion duration','ms',20),('completion_cv_T1','timing','SD/mean reliable completion duration','ratio',20),('length_adjusted_iqr_equal_group_median_ms_T1','timing','equal-weight median of IQRs across fixed length groups','ms',20),('length_residual_iqr_ms_T1','timing','IQR of residuals from duration ~ length + length²','ms',20),('length_residual_sd_ms_T1','timing','SD of residuals from duration ~ length + length²','ms',20)]
    fd=[{'feature_name':a,'family':b,'definition':c,'units':e,'token_threshold':f,'source':'saved lexical_feature_feasibility_v1 / word_length_adjusted_completion_v1','privacy':'aggregate only','availability':'available from saved T1 window output'} for a,b,c,e,f in definitions]
    privacy=[{'check':'raw_text_export','status':'pass','detail':'T1 analysis reads aggregate saved tables only; no raw text accessed'},{'check':'raw_words_or_vocabularies','status':'pass','detail':'No words, sets, hashes, or embeddings in T1 outputs'},{'check':'thresholds','status':'pass','detail':'20/50/100 token rules fixed before outcome testing'},{'check':'T2_requirement','status':'pass','detail':'No T2 data required or used'},{'check':'time_of_day','status':'limited','detail':'Saved v1 T1 output does not contain time-of-day lexical fields; none were imputed'}]
    # Compact supervisor table: smallest p per family, or gate/availability rows.
    sup=[]
    if not res.empty:
      for fam in res.testing_family.unique():
        q=res[res.testing_family.eq(fam)].sort_values('spearman_p').head(3)
        sup.extend(q.to_dict('records'))
    manifest={'version':'20261021_v1','source_tables':[str(SRC),str(WIN)],'t1_patients_with_valid_global':int(len(base)),'t1_patients_with_any_reliable_tokens':int((base.reliable_completion_count_T1>0).sum()),'new_cognitive_screen':True,'t2_used':False,'historical_outputs_modified':False,'privacy':'aggregate tables only'}
    payload={'results':res.to_dict('records'),'significant':res[res.spearman_p<.05].to_dict('records'),'coverage':covrows,'assessment_timing':time_report,'feature_dictionary':fd,'privacy':privacy,'supervisor':sup,'manifest':manifest}
    (STAGE/'payload.json').write_text(json.dumps(sanitize(payload),ensure_ascii=False),encoding='utf-8')
    # Plot leading results by smallest nominal p, without changing tested families.
    if not res.empty:
      for i,r in res.sort_values('spearman_p').head(6).iterrows():
        x=base.loc[(base.reliable_completion_count_T1>=r.token_threshold),r.feature_name]; y=base.loc[x.index,r.outcome]; ok=x.notna()&y.notna();
        if ok.sum()<12: continue
        plt.figure(figsize=(5,4)); plt.scatter(x[ok],y[ok],s=24,alpha=.75); plt.xlabel(r.feature_name); plt.ylabel(r.outcome); plt.title(f"T1 exploratory: rho={r.spearman_rho:.3f}, p={r.spearman_p:.4g}, n={int(r.n)}"); plt.grid(alpha=.2); plt.tight_layout(); plt.savefig(OUT/f"scatter_{i+1:02d}_{r.feature_name}_{r.outcome}.png",dpi=160); plt.close()
    print(json.dumps({'results':len(res),'p_lt_05':int((res.spearman_p<.05).sum()),'t1_valid_global':len(base),'stage':str(STAGE/'payload.json'),'timing':time_report},indent=2))

if __name__=='__main__': main()
