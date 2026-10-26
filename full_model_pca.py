"""Window-aligned digital + ACC PCA, using local completed feature files only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import RobustScaler
from threadpoolctl import threadpool_limits

import unsupervised_phenotyping as original

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'output/analysis_candidates'
OUT = DATA / 'full_model_pca'
ACC = DATA / 'accelerometer_patient_sequential_pipeline'
ID = 'Subject_ID_D'
TZ = 'Asia/Jerusalem'
SOURCES = {
    'baseline': original.DATASET_PATH,
    'digital_loadings': original.OUTPUT_DIR / 'usable_catalog_50pct/pca_loadings.csv',
    'digital_metadata': original.METADATA_PATH,
    't2': DATA / 'phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_features_wide.csv',
    't1_windows': DATA / 'phase11_midpoint_t1_baseline/phase11_midpoint_t1_baseline_patient_table_status.csv',
    't2_windows': DATA / 'phase12_midpoint_t2_decline/phase12_midpoint_t2_decline_patient_table_status.csv',
    'acc_days': ACC / 'accelerometer_patient_sequential_device_day_features.csv',
    'acc_catalog': ACC / 'accelerometer_plugin_event_day_feature_catalog.csv',
    'completion_audit': ACC / 'completion_audit/completion_audit.json',
    'protocol': ROOT / 'FULL_MODEL_PCA_PROTOCOL.md',
    'implementation': Path(__file__).resolve(),
    'original_method': ROOT / 'unsupervised_phenotyping.py',
}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def hashes():
    return {key: {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            for key, path in SOURCES.items()}


def read_patients(path):
    frame = pd.read_csv(path, dtype={ID: str})
    ids = pd.to_numeric(frame[ID], errors='raise')
    if ids.isna().any() or (ids % 1 != 0).any():
        raise ValueError(f'Invalid patient IDs in {path}')
    frame[ID] = ids.astype(int).astype(str).str.zfill(3)
    frame = frame[frame[ID] != '001'].copy()
    if frame[ID].duplicated().any():
        raise ValueError(f'Duplicate patient IDs in {path}')
    return frame.set_index(ID)


def read_windows(path):
    frame = pd.read_csv(path, dtype={ID: str})
    cols = [ID, 'window_start_ms', 'window_end_ms']
    frame = frame[cols].dropna().drop_duplicates()
    frame[ID] = pd.to_numeric(frame[ID], errors='raise').astype(int).astype(str).str.zfill(3)
    if frame[ID].duplicated().any() or (frame.window_end_ms <= frame.window_start_ms).any():
        raise ValueError(f'Conflicting or invalid saved windows in {path}')
    return frame.set_index(ID)


def aggregate_acc(days, windows, features, policy='exclude_multi', aggregation='median'):
    """Never split a daily summary or pool overlapping devices implicitly."""
    if policy not in ('exclude_multi', 'best_device') or aggregation not in ('median', 'mean'):
        raise ValueError('Unknown aggregation policy')
    work = days.copy()
    if work.duplicated(['patient_id', 'device_id', 'local_date']).any():
        raise ValueError('Duplicate ACC device-day keys')
    work[ID] = pd.to_numeric(work.patient_id, errors='raise').astype(int).astype(str).str.zfill(3)
    work = work.merge(windows.reset_index(), on=ID, how='left', validate='many_to_one')
    # Compare timezone-aware timestamps, independent of pandas' ns/us storage unit.
    dates = pd.to_datetime(work.local_date, errors='raise')
    work['day_start'] = dates.dt.tz_localize(TZ).dt.tz_convert('UTC')
    work['day_end'] = (dates + pd.Timedelta(days=1)).dt.tz_localize(TZ).dt.tz_convert('UTC')
    start = pd.to_datetime(work.window_start_ms, unit='ms', utc=True)
    end = pd.to_datetime(work.window_end_ms, unit='ms', utc=True)
    contained = (work.day_start >= start) & (work.day_end <= end)
    overlap = (work.day_start < end) & (work.day_end > start)
    work['device_count'] = work.groupby([ID, 'local_date']).device_id.transform('nunique')
    work['reason'] = 'outside_window'
    work.loc[start.isna(), 'reason'] = 'no_saved_window'
    work.loc[overlap & ~contained, 'reason'] = 'crosses_window_boundary'
    work.loc[contained, 'reason'] = 'included'
    if policy == 'exclude_multi':
        work.loc[contained & work.device_count.gt(1), 'reason'] = 'multi_device_day_excluded'
    else:
        chosen = work[contained].sort_values(
            ['accelerometer_valid_signal_minutes', 'accelerometer_valid_numeric_row_count', 'device_id'],
            ascending=[False, False, True],
        ).drop_duplicates([ID, 'local_date']).index
        work.loc[contained & ~work.index.isin(chosen), 'reason'] = 'another_device_selected'
    selected = work[work.reason == 'included']
    prefix = {f: f'acc_median_{f}' for f in features}
    # Keep primary column names in mean sensitivity so loading/score comparisons align.
    aggregated = selected.groupby(ID)[features].agg(aggregation).rename(columns=prefix)
    quality = selected.groupby(ID).agg(
        acc_feature_days=('local_date', 'nunique'),
        acc_observed_minutes=('accelerometer_valid_signal_minutes', 'sum'),
        acc_daily_coverage_median=('accelerometer_calendar_coverage_fraction', 'median'),
        acc_raw_rows=('accelerometer_raw_row_count', 'sum'),
        acc_duplicates_removed=('accelerometer_exact_duplicate_rows_removed', 'sum'),
    )
    result = windows.join(aggregated).join(quality)
    result['acc_feature_days'] = result.acc_feature_days.fillna(0).astype(int)
    audit_cols = [ID, 'device_id', 'local_date', 'day_start', 'day_end', 'window_start_ms',
                  'window_end_ms', 'device_count', 'reason']
    return result, work[audit_cols]


def availability(frame, digital, acc):
    result = pd.DataFrame(index=frame.index)
    result['digital_coverage'] = frame[digital].notna().mean(axis=1)
    result['acc_coverage'] = frame[acc].notna().mean(axis=1)
    result['eligible'] = result.digital_coverage.ge(.5) & result.acc_coverage.ge(.5)
    result['reason'] = [
        '; '.join(reason for condition, reason in [
            (d < .5, 'fewer than half of digital features observed'),
            (a < .5, 'fewer than half of ACC features observed')
        ] if condition) or 'included'
        for d, a in zip(result.digital_coverage, result.acc_coverage)
    ]
    return result


def project_frozen(frame, model, validate=True):
    """Return scores using saved numerical parameters; never fit on these rows."""
    features = model['features']
    raw = frame.reindex(columns=features).copy()
    for feature in features:
        values = raw[feature].replace(r'^\s*$', np.nan, regex=True)
        raw[feature] = pd.to_numeric(values, errors='raise')
    if np.isinf(raw.to_numpy(dtype=float)).any():
        raise ValueError('Infinite values are not accepted.')
    if validate:
        blocks = model['blocks']
        coverage = availability(raw, blocks['digital'], blocks['acc'])
        if not coverage.eligible.all():
            raise ValueError('At least half of the digital features and half of the ACC features must be observed.')
        if model.get('endpoint') == 'T1' and raw[blocks['acc']].lt(0).any().any():
            raise ValueError('ACC movement summaries must be nonnegative.')
    for feature in model['log_features']:
        if raw[feature].dropna().lt(0).any():
            raise ValueError(f'{feature} was fitted as a nonnegative feature; negative values cannot be projected.')
        raw[feature] = np.log1p(raw[feature])
    values = raw.to_numpy(dtype=float)
    values = np.where(np.isnan(values), np.array(model['medians']), values)
    scaled = (values - np.array(model['center'])) / np.array(model['scale'])
    scores = (scaled - np.array(model['pca_mean'])) @ np.array(model['components']).T
    result = pd.DataFrame(scores, index=frame.index, columns=[f'PC{i+1}' for i in range(scores.shape[1])])
    if model['cluster_centers']:
        distances = ((scores[:, None, :] - np.array(model['cluster_centers'])[None, :, :]) ** 2).sum(axis=2)
        result['cluster_label'] = distances.argmin(axis=1)
    return result


def fit_panel(frame, digital, acc, endpoint='T1'):
    features = digital + acc
    raw = frame[features].apply(pd.to_numeric, errors='raise').replace([np.inf, -np.inf], np.nan)
    usable = [f for f in features if raw[f].nunique() > 1]
    dropped = [f for f in features if f not in usable]
    raw = raw[usable]
    if len(raw) < 3 or len(usable) < 2:
        return {'summary': {'status': 'insufficient_data', 'patients': len(raw), 'features': len(usable),
                            'reason': 'PCA requires at least 3 patients and 2 varying features.'}}
    scaled, transforms, transformed = original._prepare_feature_matrix(raw)
    medians = transformed.median().fillna(0)
    scaler = RobustScaler().fit(transformed.fillna(medians).fillna(0).to_numpy())
    pca = PCA(n_components=min(original.MAX_PCS, len(raw)-1, len(usable)), random_state=original.RANDOM_STATE).fit(scaled)
    scores = pca.transform(scaled)
    quality = pd.DataFrame()
    centers = []
    labels = None
    acceptable = False
    if len(raw) >= 12 and np.unique(scores, axis=0).shape[0] > 4:
        quality = pd.DataFrame([original._cluster_quality(scores, k) for k in original.CLUSTER_K_VALUES])
        eligible = quality[quality.min_cluster_n_reference >= 5]
        choices = eligible if not eligible.empty else quality
        sort_cols = ['mean_silhouette', 'mean_subsample_ari_vs_reference']
        if eligible.empty:
            sort_cols = ['min_cluster_n_reference'] + sort_cols
        best = choices.sort_values(sort_cols, ascending=False).iloc[0]
        cluster = KMeans(n_clusters=int(best.k), n_init=100, random_state=original.RANDOM_STATE).fit(scores)
        labels = cluster.labels_
        centers = cluster.cluster_centers_.tolist()
        # Audit the actual displayed fit as well as the reference seed runs.
        acceptable = not eligible.empty and pd.Series(labels).value_counts().min() >= 5
        quality['displayed_k'] = quality.k.eq(int(best.k))
    model = {
        'schema_version': 1, 'endpoint': endpoint, 'features': usable,
        'blocks': {'digital': [f for f in digital if f in usable], 'acc': [f for f in acc if f in usable]},
        'log_features': transforms.loc[transforms.transformation.ne('none'), 'feature_name'].tolist(),
        'medians': medians.to_list(), 'center': scaler.center_.tolist(), 'scale': scaler.scale_.tolist(),
        'pca_mean': pca.mean_.tolist(), 'components': pca.components_.tolist(),
        'cluster_centers': centers, 'fit_patient_ids': frame.index.tolist(),
    }
    coordinates = project_frozen(frame, model, validate=False)
    np.testing.assert_allclose(coordinates.filter(regex=r'^PC\d+$'), scores, atol=1e-9)
    pcs = [f'PC{i+1}' for i in range(scores.shape[1])]
    variance = pd.DataFrame({'component': pcs, 'explained_variance_percent': pca.explained_variance_ratio_*100})
    variance['cumulative_percent'] = variance.explained_variance_percent.cumsum()
    loadings = pd.DataFrame(pca.components_.T, index=pd.Index(usable, name='feature_name'), columns=pcs)
    loadings['block'] = ['ACC' if f in acc else 'Digital' for f in usable]
    summary = {'status': 'complete', 'patients': len(frame), 'features': len(usable), 'dropped_features': dropped,
               'pc1_pc2_percent': float(variance.explained_variance_percent.head(2).sum()),
               'selected_k': len(centers) or None, 'acceptable_cluster_solution': bool(acceptable),
               'cluster_sizes': pd.Series(labels).value_counts().sort_index().to_list() if labels is not None else [],
               'cluster_note': ('No cluster fit: fewer than 12 patients or insufficient distinct observations.' if labels is None
                                else 'Exploratory clusters.' if acceptable else 'Reference only: at least one displayed cluster is smaller than five.'),
               'silhouette': float(best.mean_silhouette) if labels is not None else None,
               'subsample_ari': float(best.mean_subsample_ari_vs_reference) if labels is not None else None}
    return {'summary': summary, 'model': model, 'scores': coordinates, 'variance': variance,
            'loadings': loadings, 'transformations': transforms, 'cluster_quality': quality}


def save_panel(folder, result, frame):
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / 'summary.json', result['summary'])
    if 'model' not in result:
        return
    write_json(folder / 'model.json', result['model'])
    columns = [c for c in frame if c.endswith(('_T1', '_T2', '_delta')) or c.startswith('acc_') and c not in result['model']['features']]
    # Only patient-level context; raw signals are never embedded in the UI.
    frame[columns].join(result['scores']).to_csv(folder / 'scores.csv', index_label=ID)
    for name in ('variance', 'loadings', 'transformations', 'cluster_quality'):
        result[name].to_csv(folder / (name + '.csv'), index=name == 'loadings')
    if 'cluster_label' in result['scores']:
        raw = frame[result['model']['features']].join(result['scores'][['cluster_label']])
        raw.groupby('cluster_label').median().T.to_csv(folder / 'cluster_feature_medians.csv', index_label='feature_name')
    technical = [c for c in frame if c.startswith(('acc_', 'baseline_')) and c not in result['model']['features'] and 'window' not in c]
    outcomes = [c for c in frame if c.endswith(('_T1', '_T2', '_delta'))]
    rows = []
    for name in technical + outcomes:
        for pc in ('PC1', 'PC2'):
            pairs = pd.concat([pd.to_numeric(frame[name], errors='coerce'), result['scores'][pc]], axis=1).dropna()
            rho = pairs.iloc[:, 0].corr(pairs.iloc[:, 1], method='spearman') if len(pairs) >= 3 and pairs.iloc[:, 0].nunique() > 1 else np.nan
            rows.append({'variable': name, 'role': 'Technical audit' if name in technical else 'Cognitive overlay',
                         'component': pc, 'n': len(pairs), 'spearman_rho': rho})
    pd.DataFrame(rows).to_csv(folder / 'correlations.csv', index=False)


def build(output_root=OUT):
    before = hashes()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run = output_root / 'runs' / stamp
    run.mkdir(parents=True)
    baseline = read_patients(SOURCES['baseline'])
    followup = read_patients(SOURCES['t2'])
    digital = sorted(pd.read_csv(SOURCES['digital_loadings']).feature_name.tolist())
    if len(digital) != 41 or len(set(digital)) != 41:
        raise ValueError('Expected the original frozen 41-feature digital panel')
    catalog = pd.read_csv(SOURCES['acc_catalog'])
    movement = catalog.loc[catalog.feature_group.ne('quality'), 'feature_name'].tolist()
    acc = ['acc_median_' + f for f in movement]
    days = pd.read_csv(SOURCES['acc_days'], dtype={'patient_id': str, 'device_id': str})
    windows = {e: read_windows(SOURCES[f'{e}_windows']) for e in ('t1', 't2')}
    frames = {}
    for e, base in [('t1', baseline), ('t2', followup)]:
        aggregated, audit = aggregate_acc(days, windows[e], movement)
        frames[e] = base.join(aggregated)
        frames[e].to_csv(run / f'{e}_patient_features.csv', index_label=ID)
        audit.to_csv(run / f'{e}_acc_day_audit.csv', index=False)
    available = {e: availability(frame, digital, acc) for e, frame in frames.items()}
    audit = baseline[[c for c in baseline if c.endswith(('_T1', '_T2', '_delta', '_date_iso'))]].copy()
    for e in ('t1', 't2'):
        audit = audit.join(available[e].add_prefix(e + '_'))
        audit = audit.join(frames[e][['acc_feature_days', 'window_start_ms', 'window_end_ms']].add_prefix(e+'_'))
    audit['global_decliner'] = audit.global_T2.lt(audit.global_T1)
    audit['ordered_clinical_dates'] = pd.to_datetime(audit.T2_date_iso, errors='coerce') > pd.to_datetime(audit.T1_date_iso, errors='coerce')
    audit['paired_eligible'] = (audit.global_decliner & audit.ordered_clinical_dates & audit.t1_eligible.fillna(False)
                                & audit.t2_eligible.fillna(False) & audit.t1_window_start_ms.notna() & audit.t2_window_start_ms.notna())
    audit['paired_reason'] = [
        'included' if row.paired_eligible else '; '.join(reason for condition, reason in [
            (not row.global_decliner, 'no observed global decline'),
            (not row.ordered_clinical_dates, 'missing or unordered clinical dates'),
            (pd.isna(row.t1_window_start_ms) or pd.isna(row.t2_window_start_ms), 'missing saved endpoint window'),
            (row.t1_eligible != True, 'insufficient T1 feature coverage'),
            (row.t2_eligible != True, 'insufficient T2 feature coverage')
        ] if condition) for row in audit.itertuples()
    ]
    eligible_ids = available['t1'].index[available['t1'].eligible]
    fit_frame = frames['t1'].loc[eligible_ids]
    print(f'Fitting combined T1 PCA: {len(fit_frame)} patients, {len(digital)+len(acc)} candidate features', flush=True)
    baseline_fit = fit_panel(fit_frame, digital, acc)
    if 'model' not in baseline_fit:
        raise ValueError('Insufficient data for the combined baseline model')
    save_panel(run / 'baseline', baseline_fit, fit_frame)
    comparisons = [{'panel': 'Combined median (main)', **baseline_fit['summary'], 'cluster_ari_vs_main': 1.0}]
    # Same patients for each comparison: cohort size cannot explain the differences.
    for key, title, dcols, acols, policy, agg in [
        ('digital_only', 'Digital only, same patients', digital, [], 'exclude_multi', 'median'),
        ('acc_only', 'ACC only, same patients', [], acc, 'exclude_multi', 'median'),
        ('mean_sensitivity', 'Mean ACC across days', digital, acc, 'exclude_multi', 'mean'),
        ('device_sensitivity', 'One best-covered device per day', digital, acc, 'best_device', 'median'),
    ]:
        print(f'Fitting {title}', flush=True)
        alternative, day_audit = aggregate_acc(days, windows['t1'], movement, policy, agg)
        frame = baseline.join(alternative).loc[eligible_ids]
        result = fit_panel(frame, dcols, acols)
        save_panel(run / key, result, frame)
        alt_labels = result.get('scores', pd.DataFrame()).get('cluster_label')
        main_labels = baseline_fit['scores'].get('cluster_label')
        ari = float(adjusted_rand_score(main_labels, alt_labels)) if main_labels is not None and alt_labels is not None else None
        comparisons.append({'panel': title, **result['summary'], 'cluster_ari_vs_main': ari})
        if key == 'device_sensitivity':
            day_audit.to_csv(run / 'best_device_day_audit.csv', index=False)
    pd.DataFrame(comparisons).to_csv(run / 'panel_comparison.csv', index=False)
    paired = audit.index[audit.paired_eligible]
    paired_t1, paired_t2 = frames['t1'].loc[paired], frames['t2'].loc[paired]
    t1_scores = project_frozen(paired_t1, baseline_fit['model'])
    t2_scores = project_frozen(paired_t2, baseline_fit['model'])
    displacement = audit.loc[paired, ['global_T1', 'global_T2', 'global_delta']].copy()
    for pc in t1_scores.filter(regex=r'^PC\d+$'):
        displacement[pc+'_T1'] = t1_scores[pc]
        displacement[pc+'_T2'] = t2_scores[pc]
        displacement[pc+'_change'] = t2_scores[pc] - t1_scores[pc]
    displacement.to_csv(run / 'decliner_displacements.csv', index_label=ID)
    delta = paired_t2[digital+acc] - paired_t1[digital+acc]
    # Subtraction precedes imputation: unobserved change is not assumed to be zero.
    delta_availability = availability(delta, digital, acc)
    audit['delta_eligible'] = audit.index.isin(delta_availability.index[delta_availability.eligible])
    audit['delta_pair_coverage'] = (delta.notna().mean(axis=1)).reindex(audit.index)
    delta = delta.loc[delta_availability.eligible].join(audit[['global_T1', 'global_T2', 'global_delta']])
    delta.to_csv(run / 'decliner_feature_changes.csv', index_label=ID)
    print(f'Fitting observed feature-change PCA: {len(delta)} decliners', flush=True)
    delta_fit = fit_panel(delta, digital, acc, endpoint='T2-T1')
    save_panel(run / 'decline_change', delta_fit, delta)
    audit.to_csv(run / 'patient_audit.csv', index_label=ID)
    meta = pd.read_csv(SOURCES['digital_metadata']).set_index('feature_name')
    inventory = []
    for feature in digital:
        inventory.append({'feature_name': feature, 'block': 'Digital', 'group': meta.loc[feature, 'feature_family'],
                          'definition': meta.loc[feature, 'short_description'], 'candidate_for_pca': True})
    for row in catalog.itertuples():
        inventory.append({'feature_name': 'acc_median_'+row.feature_name, 'block': 'ACC', 'group': row.feature_group,
                          'definition': row.definition, 'candidate_for_pca': row.feature_group != 'quality'})
    inventory = pd.DataFrame(inventory)
    inventory['used_in_main_pca'] = inventory.feature_name.isin(baseline_fit['model']['features'])
    inventory['t1_observed_patients'] = inventory.feature_name.map(frames['t1'].notna().sum())
    inventory.to_csv(run / 'feature_inventory.csv', index=False)
    template = pd.DataFrame([{'subject_label': '', **{f: np.nan for f in baseline_fit['model']['features']}}])
    template.to_csv(run / 'new_subject_template.csv', index=False)
    after = hashes()
    if after != before:
        raise RuntimeError('An input changed during the build; this run has not been published')
    record = {
        'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(), 'run_id': stamp,
        'seed': original.RANDOM_STATE, 'pandas_version': pd.__version__, 'sklearn_version': sklearn.__version__,
        'source_hashes': before, 'source_files_unchanged': True, 'source_patients': len(baseline),
        't1_patients_with_acc': int(frames['t1'].acc_feature_days.gt(0).sum()),
        't2_patients_with_acc': int(frames['t2'].acc_feature_days.gt(0).sum()),
        'observed_global_decliners': int(audit.global_decliner.sum()), 'paired_decliners': len(paired),
        'baseline': baseline_fit['summary'], 'decline_change': delta_fit['summary'],
        'clinical_rule': 'global_T2 < global_T1; valid ordered dates; saved Phase 11/12 windows',
        'aggregation': 'Median over fully contained single-device local days; no raw queries',
        'limitations': [
            'Exploratory representation; no validated cognitive prediction or disease subtypes.',
            'T1 windows extend toward midpoint, so features are not prospective measurements available at T1.',
            'ACC day selection depends on the plugin dictionary; unobserved days are not zero movement.',
            'Whole days crossing window boundaries are excluded; multi-device days are excluded in the main run.',
            'Motion duration and entropy can depend on collection intensity; see the technical audit.',
            'Decline-only results are conditional on observed global decline, with a small paired sample.',
        ],
    }
    write_json(run / 'run_record.json', record)
    (run / 'README_full_model_pca.md').write_text(
        '# Full Model PCA\n\n' + (ROOT / 'FULL_MODEL_PCA_PROTOCOL.md').read_text().split('\n', 1)[1]
        + f'\n## This run\n\nT1: {len(fit_frame)} patients; {baseline_fit["summary"]["features"]} varying features. '
        + f'PC1+PC2: {baseline_fit["summary"]["pc1_pc2_percent"]:.2f}%. '
        + f'Paired decliners: {len(paired)}; change PCA: {len(delta)} patients.\n'
    )
    temporary = output_root / 'current.tmp'
    write_json(temporary, {'run_id': stamp, 'status': 'complete'})
    temporary.replace(output_root / 'current.json')
    print(json.dumps({k: v for k, v in record.items() if k != 'source_hashes'}, indent=2), flush=True)
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=OUT)
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        build(args.output_root)
