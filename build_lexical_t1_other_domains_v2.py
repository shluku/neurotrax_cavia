"""Focused follow-up for previously untested T1 Memory, Motor and IQ outcomes."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from build_lexical_t1_cross_sectional_v1 import spearman_boot, partial_rank, bh, sanitize, SRC, WIN, ROOT

STAGE=Path('/tmp/lexical_t1_other_domains_20261021'); STAGE.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'output/analysis_candidates/keyboard_deep_dive_v1/lexical_t1_cross_sectional_v2_other_domains'; OUT.mkdir(parents=True,exist_ok=True)
SEED=20261021

def main():
 d=pd.read_csv(SRC,dtype={'Subject_ID_D':str}); base=d[d.global_T1.notna()].copy()
 specs={
  'lexical_diversity_repetition':(['word_ttr_T1','word_repetition_rate_T1','word_mattr_50_T1','word_mattr_100_T1','word_mtld_T1'],{'word_ttr_T1':20,'word_repetition_rate_T1':20,'word_mattr_50_T1':50,'word_mattr_100_T1':100,'word_mtld_T1':100}),
  'word_length':(['word_mean_length_chars_T1','word_median_length_chars_T1','word_length_sd_chars_T1'],{f:20 for f in ['word_mean_length_chars_T1','word_median_length_chars_T1','word_length_sd_chars_T1']}),
  'timing_variability':(['completion_median_ms_T1','completion_iqr_ms_T1','completion_mad_ms_T1','completion_cv_T1','len_2_3_iqr_ms_T1','len_4_5_iqr_ms_T1','len_6_8_iqr_ms_T1','len_9_plus_iqr_ms_T1','length_adjusted_iqr_equal_group_median_ms_T1','length_residual_sd_ms_T1','length_residual_iqr_ms_T1'],{f:20 for f in ['completion_median_ms_T1','completion_iqr_ms_T1','completion_mad_ms_T1','completion_cv_T1','len_2_3_iqr_ms_T1','len_4_5_iqr_ms_T1','len_6_8_iqr_ms_T1','len_9_plus_iqr_ms_T1','length_adjusted_iqr_equal_group_median_ms_T1','length_residual_sd_ms_T1','length_residual_iqr_ms_T1']})}
 outcomes=['memory_T1','motor_T1','iq_T1']; covcols=['active_days_T1','distinct_observations_in_window_T1','valid_interval_count_T1','unique_package_count_T1','unique_device_count_T1','reliable_fraction_T1']; rows=[]
 for family,(features,thresholds) in specs.items():
  for f in features:
   if f not in d: continue
   elig=base[base.reliable_completion_count_T1>=thresholds[f]]
   for out in outcomes:
    z=elig[[f,out]].replace([np.inf,-np.inf],np.nan).dropna()
    if len(z)<12 or z[f].nunique()<3 or z[out].nunique()<3: continue
    rho,p,lo,hi=spearman_boot(z[f],z[out],seed=SEED+len(z)); adj=partial_rank(z[f],z[out],elig.loc[z.index,covcols]);
    z100=base[base.reliable_completion_count_T1>=100][[f,out]].replace([np.inf,-np.inf],np.nan).dropna(); sens=spearman_boot(z100[f],z100[out],reps=1000,seed=SEED+100+len(z)) if len(z100)>=12 and z100[f].nunique()>2 and z100[out].nunique()>2 else (None,None,None,None)
    rows.append({'testing_family':family,'feature_name':f,'outcome':out,'token_threshold':thresholds[f],'eligible_feature_n':int(elig[f].notna().sum()),'n':len(z),'spearman_rho':rho,'spearman_p':p,'bootstrap_ci_low':lo,'bootstrap_ci_high':hi,'coverage_adjusted_partial_rho':adj[0] if adj else None,'coverage_adjusted_p':adj[1] if adj else None,'coverage_adjusted_n':adj[2] if adj else None,'high_coverage_100_token_n':len(z100),'high_coverage_100_token_rho':sens[0],'high_coverage_100_token_p':sens[1],'high_coverage_100_token_ci_low':sens[2],'high_coverage_100_token_ci_high':sens[3]})
 res=pd.DataFrame(rows); res['fdr_q']=np.nan; res['coverage_adjusted_fdr_q']=np.nan
 for fam in res.testing_family.unique():
  ix=res.testing_family.eq(fam); res.loc[ix,'fdr_q']=bh(res.loc[ix,'spearman_p']); res.loc[ix,'coverage_adjusted_fdr_q']=bh(res.loc[ix,'coverage_adjusted_p'])
 cov=[]
 for label,sub in [('all_valid_T1',base),('min20_reliable_tokens',base[base.reliable_completion_count_T1>=20]),('min50_reliable_tokens',base[base.reliable_completion_count_T1>=50]),('min100_reliable_tokens',base[base.reliable_completion_count_T1>=100])]: cov.append({'cohort':label,'patients_with_valid_global_T1':len(sub),'patients_with_memory_T1':int(sub.memory_T1.notna().sum()),'patients_with_motor_T1':int(sub.motor_T1.notna().sum()),'patients_with_iq_T1':int(sub.iq_T1.notna().sum()),'median_reliable_tokens':sub.reliable_completion_count_T1.median(),'median_active_days':sub.active_days_T1.median(),'median_snapshots':sub.distinct_observations_in_window_T1.median()})
 sup=res.sort_values('spearman_p').head(12).to_dict('records'); privacy=[{'check':'historical_preservation','status':'pass','detail':'separate v2 directory; v1 unchanged'},{'check':'t2_use','status':'pass','detail':'no T2 fields used'},{'check':'thresholds','status':'pass','detail':'same fixed 20/50/100 thresholds as v1'},{'check':'raw_text','status':'pass','detail':'saved aggregate tables only; no raw text/words accessed'}]
 manifest={'version':'20261021_v2_other_domains','outcomes':['memory_T1','motor_T1','iq_T1'],'results':len(res),'p_lt_05':int((res.spearman_p<.05).sum()),'historical_outputs_modified':False,'independent_validation':False}
 payload={'results':res.to_dict('records'),'significant':res[res.spearman_p<.05].to_dict('records'),'coverage':cov,'supervisor':sup,'privacy':privacy,'manifest':manifest}
 (STAGE/'payload.json').write_text(json.dumps(sanitize(payload)),encoding='utf-8')
 for i,r in res.sort_values('spearman_p').head(6).iterrows():
  x=base.loc[base.reliable_completion_count_T1>=r.token_threshold,r.feature_name]; y=base.loc[x.index,r.outcome]; ok=x.notna()&y.notna();
  if ok.sum()<12: continue
  plt.figure(figsize=(5,4)); plt.scatter(x[ok],y[ok],s=24,alpha=.75); plt.xlabel(r.feature_name); plt.ylabel(r.outcome); plt.title(f"Other-domain T1: rho={r.spearman_rho:.3f}, p={r.spearman_p:.4g}, n={int(r.n)}"); plt.grid(alpha=.2); plt.tight_layout(); plt.savefig(OUT/f'scatter_{i+1:02d}_{r.feature_name}_{r.outcome}.png',dpi=160); plt.close()
 print(json.dumps({'results':len(res),'p_lt_05':int((res.spearman_p<.05).sum()),'stage':str(STAGE/'payload.json')},indent=2))
if __name__=='__main__': main()
