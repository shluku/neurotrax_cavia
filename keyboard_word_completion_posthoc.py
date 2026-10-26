"""Post-process the saved word-completion aggregates without reading raw text."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr, t

ROOT=Path(__file__).parent
OUT=ROOT/'output/analysis_candidates/keyboard_deep_dive_v1/word_completion_timing_v1'

def partial(x,y,cov):
    z=pd.concat([x.rename('x'),y.rename('y'),cov],axis=1).apply(pd.to_numeric,errors='coerce').replace([np.inf,-np.inf],np.nan).dropna(); n=len(z)
    if n<15: return np.nan,np.nan,n
    r=z.rank(method='average'); C=np.column_stack([np.ones(n),r.iloc[:,2:].to_numpy()])
    rx=r.iloc[:,0].to_numpy()-C@np.linalg.lstsq(C,r.iloc[:,0].to_numpy(),rcond=None)[0]
    ry=r.iloc[:,1].to_numpy()-C@np.linalg.lstsq(C,r.iloc[:,1].to_numpy(),rcond=None)[0]
    rho=float(np.corrcoef(rx,ry)[0,1]) if rx.std()>0 and ry.std()>0 else np.nan; df=max(n-C.shape[1]-1,1)
    p=float(2*t.sf(abs(rho*np.sqrt(df/max(1-rho*rho,1e-12))),df)) if np.isfinite(rho) else np.nan
    return rho,p,n

def main():
    p=pd.read_csv(OUT/'word_completion_patient_table.csv',dtype={'Subject_ID_D':str})
    cov1=p[['active_days_T1','snapshot_rate_per_active_minute_T1','valid_interval_count_T1']]
    covd=p[['active_days_delta','snapshot_rate_per_active_minute_delta','valid_interval_count_delta']]
    targets=[('T1','global_T1',cov1),('T1','memory_T1',cov1),('T1','ef_T1',cov1),('T1','attention_T1',cov1),('delta','global_delta',covd),('delta','ef_delta',covd),('delta','attention_delta',covd)]
    features=[c for c in p.columns if c.startswith('word_completion_') and (c.endswith('_T1') or c.endswith('_delta')) and not c.endswith('_rate_per_active_minute_T1') and not c.endswith('_rate_per_active_minute_delta')]
    rows=[]
    for scope,y,cov in targets:
        suffix='_T1' if scope=='T1' else '_delta'
        for f in features:
            if not f.endswith(suffix): continue
            rho,pp,n=partial(p[f],p[y],cov)
            if np.isfinite(rho): rows.append({'scope':scope,'outcome':y,'feature_name':f,'partial_spearman_rho':rho,'partial_spearman_p':pp,'n':n,'covariates':'active_days,snapshot_rate_per_active_minute,valid_interval_count'})
    adj=pd.DataFrame(rows); adj.to_csv(OUT/'word_completion_recording_adjusted_associations.csv',index=False)
    audit=Path('output/analysis_candidates/keyboard_deep_dive_v1/afternoon_interval_mechanism_audit_20261020/patient_level_mechanism_audit.csv')
    if audit.exists():
        a=pd.read_csv(audit,dtype={'Subject_ID_D':str}); m=p.merge(a[['Subject_ID_D','afternoon_iei_delta_ms']],on='Subject_ID_D',how='inner')
        comp=[]
        for name,col in [('word_completion_median_delta','word_completion_median_ms_delta'),('word_completion_iqr_delta','word_completion_iqr_ms_delta'),('snapshot_IEI_delta','afternoon_iei_delta_ms')]:
            z=m[[col,'ef_delta']].apply(pd.to_numeric,errors='coerce').dropna()
            if len(z)>=3:
                r,pp=spearmanr(z.iloc[:,0],z.iloc[:,1]); comp.append({'feature_name':name,'outcome':'ef_delta','n':len(z),'spearman_rho':r,'spearman_p':pp})
        pd.DataFrame(comp).to_csv(OUT/'word_completion_vs_snapshot_iei_matched.csv',index=False)
    print({'adjusted_rows':len(adj),'matched_patients':int(len(m)) if audit.exists() else 0})
if __name__=='__main__': main()
