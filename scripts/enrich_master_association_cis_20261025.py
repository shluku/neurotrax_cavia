from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / 'manuscript/tables/master_association_table_20261020.csv'
OUT = ROOT / 'output/research_summary_20261025/all_associations_with_ci_20261025.csv'
SEED, B = 20261020, 500

def norm(s):
    return s.astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(3)

def partial_rho(vals, cov):
    ranks = np.column_stack([rankdata(vals[:, j], method='average') for j in range(vals.shape[1])])
    z = np.column_stack([np.ones(len(ranks)), cov])
    rx = ranks[:, 0] - z @ np.linalg.lstsq(z, ranks[:, 0], rcond=None)[0]
    ry = ranks[:, 1] - z @ np.linalg.lstsq(z, ranks[:, 1], rcond=None)[0]
    if np.std(rx) == 0 or np.std(ry) == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])

def ci(frame, x, y, covars, seed):
    cols = [x, y, *covars]
    z = frame[cols].apply(pd.to_numeric, errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    if len(z) < 12:
        return np.nan, np.nan, len(z)
    vals, cov = z[[x, y]].to_numpy(float), z[covars].to_numpy(float)
    rng, boot = np.random.default_rng(seed), []
    for _ in range(B):
        ix = rng.integers(0, len(z), len(z))
        boot.append(partial_rho(vals[ix], cov[ix]))
    return float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5)), len(z)

d = pd.read_csv(MASTER)
d['ci_source'] = np.where(d.ci_low.notna() & d.ci_high.notna(), 'saved_source_output', 'unavailable_exact_patient_inputs_not_found')
d['ci_method'] = np.where(d.ci_low.notna() & d.ci_high.notna(), 'saved source CI', 'not calculated')

w = pd.read_csv(ROOT / 'output/analysis_candidates/keyboard_deep_dive_v1/keyboard_deep_dive_window_features.csv', dtype={'Subject_ID_D': str})
w.Subject_ID_D = norm(w.Subject_ID_D)
t1, t2 = w[w.window_name.eq('T1')].copy(), w[w.window_name.eq('T2')].copy()
c1 = pd.read_csv(ROOT / 'output/analysis_candidates/phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_features_wide.csv', dtype={'Subject_ID_D': str})
c1.Subject_ID_D = norm(c1.Subject_ID_D)
base1 = t1.merge(c1, on='Subject_ID_D', how='inner')
base2 = t1.merge(c1, on='Subject_ID_D', how='inner').merge(t2, on='Subject_ID_D', how='inner', suffixes=('', '_T2'))
features = [f for f in w.columns if f.startswith('keyboard_') and not any(q in f for q in ('raw_rows', 'duplicate_rows', 'json_parse', 'valid_interval_count', 'distinct_observations_in_window', 'window_start', 'window_end'))]
for f in features:
    if f + '_T2' in base2:
        base2[f + '_delta'] = pd.to_numeric(base2[f + '_T2'], errors='coerce') - pd.to_numeric(base2[f], errors='coerce')
cache = {}
for i, r in d.loc[d.ci_low.isna() & d.source_file.str.contains('signal_discovery', na=False) & d.estimate_type.eq('partial Spearman rho')].iterrows():
    frame = base1 if r.outcome_timepoint == 'T1' else base2
    x = r.feature
    prefix = {'global': 'global', 'memory': 'memory', 'executive_function': 'ef', 'processing_speed': 'processing_speed', 'attention': 'attention', 'motor': 'motor'}.get(r.outcome)
    y = (prefix + '_T1') if r.outcome_timepoint == 'T1' and prefix else (prefix + '_delta' if prefix else None)
    if not y or x not in frame:
        continue
    key = ('sig', r.outcome_timepoint, x, y)
    if key not in cache:
        cache[key] = ci(frame, x, y, ['age', 'Gender (1=M, 2=F)', 'Education (years)'], SEED + len(cache))
    lo, hi, _ = cache[key]
    d.loc[i, ['ci_low', 'ci_high', 'ci_source', 'ci_method']] = [lo, hi, 'recomputed_from_saved_patient_level_inputs', '500-patient bootstrap; rank-residual partial Spearman; age/sex/education']

th = pd.read_csv(ROOT / 'output/analysis_candidates/keyboard_deep_dive_v1/thirds_sensitivity/third_patient_data_min7.csv', dtype={'Subject_ID_D': str})
th.Subject_ID_D = norm(th.Subject_ID_D)
th['mean_active_days'] = (pd.to_numeric(th.first_third_active_days, errors='coerce') + pd.to_numeric(th.last_third_active_days, errors='coerce')) / 2
th['mean_snapshots'] = (pd.to_numeric(th.first_third_snapshots, errors='coerce') + pd.to_numeric(th.last_third_snapshots, errors='coerce')) / 2
for i, r in d.loc[d.ci_low.isna() & d.source_file.str.contains('thirds_sensitivity/third_associations', na=False) & d.estimate_type.eq('partial Spearman rho')].iterrows():
    x = r.feature
    y = {'global': 'global_delta', 'memory': 'memory_delta', 'executive_function': 'ef_delta', 'processing_speed': 'processing_speed_delta', 'attention': 'attention_delta', 'motor': 'motor_delta', 'verbal': 'verbal_delta', 'iq': 'iq_delta'}.get(r.outcome)
    if not y or x not in th:
        continue
    key = ('third', x, y)
    if key not in cache:
        cache[key] = ci(th, x, y, ['age', 'Gender (1=M, 2=F)', 'Education (years)', 'mean_active_days', 'mean_snapshots'], SEED + 1000 + len(cache))
    lo, hi, _ = cache[key]
    d.loc[i, ['ci_low', 'ci_high', 'ci_source', 'ci_method']] = [lo, hi, 'recomputed_from_saved_patient_level_inputs', '500-patient bootstrap; rank-residual partial Spearman; age/sex/education/mean active days/mean snapshots']

d.to_csv(OUT, index=False)
print('rows', len(d), 'saved CI rows', int(d.ci_source.eq('saved_source_output').sum()), 'recomputed', int(d.ci_source.eq('recomputed_from_saved_patient_level_inputs').sum()), 'unavailable', int(d.ci_source.eq('unavailable_exact_patient_inputs_not_found').sum()))
