"""Focused MATTR-100 coverage/selection audit from saved T1 aggregates."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import matplotlib.pyplot as plt
from build_lexical_t1_cross_sectional_v1 import SRC, ROOT, spearman_boot, partial_rank, sanitize

STAGE=Path('/tmp/mattr100_validation_audit_20261021'); STAGE.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'output/analysis_candidates/keyboard_deep_dive_v1/mattr100_validation_audit_20261021'; OUT.mkdir(parents=True,exist_ok=True)

def main():
 d=pd.read_csv(SRC,dtype={'Subject_ID_D':str}); d['high_100']=d.reliable_completion_count_T1>=100; high=d[d.high_100].copy(); low=d[~d.high_100].copy();
 vars=['age','Gender (1=M, 2=F)','Education (years)','global_T1','memory_T1','ef_T1','attention_T1','processing_speed_T1','verbal_T1','motor_T1','word_mattr_100_T1','word_token_count_T1','active_days_T1','active_minutes_T1','distinct_observations_in_window_T1','valid_interval_count_T1','reliable_fraction_T1','unique_package_count_T1','unique_device_count_T1','language_latin_token_count_T1','language_other_token_count_T1']
 cohort=[]
 for label,sub in [('>=100_reliable_tokens',high),('<100_reliable_tokens',low)]:
  for v in vars:
   x=pd.to_numeric(sub[v],errors='coerce'); cohort.append({'cohort':label,'variable':v,'n':int(x.notna().sum()),'missing':int(x.isna().sum()),'median':float(x.median()) if x.notna().any() else None,'iqr':float(x.quantile(.75)-x.quantile(.25)) if x.notna().any() else None,'min':float(x.min()) if x.notna().any() else None,'max':float(x.max()) if x.notna().any() else None,'mean':float(x.mean()) if x.notna().any() else None})
 coverage_vars=['word_token_count_T1','active_days_T1','active_minutes_T1','distinct_observations_in_window_T1','valid_interval_count_T1','reliable_fraction_T1','unique_package_count_T1','unique_device_count_T1','language_latin_token_count_T1','language_other_token_count_T1']
 coverage=[]
 for v in coverage_vars:
  z=high[['word_mattr_100_T1',v]].replace([np.inf,-np.inf],np.nan).dropna()
  if len(z)>=8 and z[v].nunique()>2:
   rho,p,lo,hi=spearman_boot(z.word_mattr_100_T1,z[v],reps=2000,seed=20261021+len(z)); coverage.append({'feature':'word_mattr_100_T1','coverage_variable':v,'n':len(z),'rho':rho,'p':p,'ci_low':lo,'ci_high':hi})
  else: coverage.append({'feature':'word_mattr_100_T1','coverage_variable':v,'n':len(z),'rho':None,'p':None,'ci_low':None,'ci_high':None})
 def assoc(out):
  z=high[['word_mattr_100_T1',out]].replace([np.inf,-np.inf],np.nan).dropna(); rho,p,lo,hi=spearman_boot(z.word_mattr_100_T1,z[out],reps=2000,seed=20261021+len(z));
  # parsimonious rank adjustment: log token volume, active days, age, sex, education.
  c=pd.DataFrame({'log_tokens':np.log1p(high.loc[z.index,'word_token_count_T1']),'active_days':high.loc[z.index,'active_days_T1'],'age':high.loc[z.index,'age'],'sex':high.loc[z.index,'Gender (1=M, 2=F)'],'education':high.loc[z.index,'Education (years)']},index=z.index)
  adj=partial_rank(z.word_mattr_100_T1,z[out],c)
  return {'outcome':out,'n':len(z),'rho':rho,'p':p,'ci_low':lo,'ci_high':hi,'adjusted_partial_rho':adj[0] if adj else None,'adjusted_p':adj[1] if adj else None,'adjusted_n':adj[2] if adj else None,'adjustment':'log1p(total reliable tokens); active days; age; sex; education'}
 associations=[assoc('verbal_T1'),assoc('motor_T1')]
 loo=[]
 for out in ['verbal_T1','motor_T1']:
  z=high[['Subject_ID_D','word_mattr_100_T1',out]].replace([np.inf,-np.inf],np.nan).dropna(); full=spearmanr(z.word_mattr_100_T1,z[out]).statistic
  for idx,row in z.iterrows():
   zz=z.drop(index=idx); rho,p=spearmanr(zz.word_mattr_100_T1,zz[out]); loo.append({'outcome':out,'excluded_subject_id':row.Subject_ID_D,'remaining_n':len(zz),'rho':float(rho),'p':float(p),'rho_change':float(rho-full),'excluded_mattr100':float(row.word_mattr_100_T1),'excluded_cognitive_score':float(row[out])})
 # Overlap among the same MATTR-eligible patients with both outcomes.
 ov=high[['word_mattr_100_T1','verbal_T1','motor_T1']].dropna(); rr,pp,lo,hi=spearman_boot(ov.verbal_T1,ov.motor_T1,reps=2000,seed=20261021+len(ov)); overlap=[{'comparison':'Verbal T1 vs Motor T1 among MATTR-100 eligible patients','n':len(ov),'rho':rr,'p':pp,'ci_low':lo,'ci_high':hi}]
 lang=[]
 for v in ['language_latin_token_count_T1','language_other_token_count_T1','unique_package_count_T1','unique_device_count_T1']:
  z=high[['word_mattr_100_T1',v]].dropna(); r,p=spearmanr(z.word_mattr_100_T1,z[v]) if len(z)>5 and z[v].nunique()>2 else (None,None); lang.append({'variable':v,'n':len(z),'rho':float(r) if r is not None else None,'p':float(p) if p is not None else None,'median_high':float(high[v].median())})
 privacy=[{'check':'raw_text','status':'pass','detail':'saved aggregate tables only; no raw text or words accessed'},{'check':'persistent_vocabularies','status':'pass','detail':'none used'},{'check':'patient_selection','status':'documented','detail':'fixed >=100 reliable-token threshold; no cognitive optimization'},{'check':'historical_preservation','status':'pass','detail':'separate audit directory'}]
 payload={'cohort_comparison':cohort,'coverage_associations':coverage,'associations':associations,'loo':loo,'domain_overlap':overlap,'language_application':lang,'privacy':privacy,'manifest':{'version':'20261021_v1','high_token_patients':len(high),'low_token_patients':len(low),'verbal_association_n':associations[0]['n'],'motor_association_n':associations[1]['n'],'historical_outputs_modified':False}}
 (STAGE/'payload.json').write_text(json.dumps(sanitize(payload)),encoding='utf-8')
 for out, title in [('verbal_T1','MATTR-100 vs Verbal T1'),('motor_T1','MATTR-100 vs Motor T1')]:
  z=high[['word_mattr_100_T1',out]].dropna(); r=[x for x in associations if x['outcome']==out][0]; plt.figure(figsize=(5,4)); plt.scatter(z.word_mattr_100_T1,z[out],s=30,alpha=.8); plt.xlabel('MATTR-100'); plt.ylabel(out); plt.title(f'{title}\nrho={r["rho"]:.3f}, p={r["p"]:.4g}, n={r["n"]}'); plt.grid(alpha=.2); plt.tight_layout(); plt.savefig(OUT/f'scatter_mattr100_{out}.png',dpi=170); plt.close()
 print(json.dumps({'high':len(high),'low':len(low),'associations':associations,'stage':str(STAGE/'payload.json')},indent=2))
if __name__=='__main__': main()
