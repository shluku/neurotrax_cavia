"""Descriptive 3D directions and separate score associations for fixed PCA maps."""
from __future__ import annotations

import numpy as np
import pandas as pd


def trend_summary(points, score_column, scale=None):
    columns = ['PC1', 'PC2', score_column]
    data = points[columns].apply(pd.to_numeric, errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    values = data.to_numpy(dtype=float)
    n = len(values)
    stats = {'n': n, 'score_mean': float(data[score_column].mean()) if n else np.nan,
             'score_median': float(data[score_column].median()) if n else np.nan,
             'score_sd': float(data[score_column].std()) if n > 1 else np.nan,
             'pc1_score_pearson': np.nan, 'pc2_score_pearson': np.nan,
             'pc1_score_spearman': np.nan, 'pc2_score_spearman': np.nan,
             'pc1_score_slope': np.nan, 'pc2_score_slope': np.nan,
             'score_on_pc1_pc2_r2_in_sample': np.nan, 'line_status': 'fewer than three complete observations'}
    empty = pd.DataFrame(columns=['PC1', 'PC2', 'score'])
    if n < 3:
        return stats, empty
    if data[score_column].nunique() < 2:
        stats['line_status'] = 'cognitive score is constant'
        return stats, empty
    for pc in ['PC1', 'PC2']:
        if data[pc].nunique() > 1:
            stats[pc.lower()+'_score_pearson'] = data[pc].corr(data[score_column])
            stats[pc.lower()+'_score_spearman'] = data[pc].corr(data[score_column], method='spearman')
            stats[pc.lower()+'_score_slope'] = np.linalg.lstsq(
                np.column_stack([np.ones(n), data[pc]]), data[score_column], rcond=None)[0][1]
    design = np.column_stack([np.ones(n), values[:, :2]])
    if n >= 4 and np.linalg.matrix_rank(design) == 3:
        fitted = design @ np.linalg.lstsq(design, values[:, 2], rcond=None)[0]
        stats['score_on_pc1_pc2_r2_in_sample'] = 1 - ((values[:, 2]-fitted)**2).sum()/((values[:, 2]-values[:, 2].mean())**2).sum()
    center = values.mean(axis=0)
    scale = values.std(axis=0) if scale is None else np.asarray(scale, dtype=float)
    scale = np.where(scale > 1e-12, scale, 1.)
    standardized = (values-center)/scale
    _, singular, vectors = np.linalg.svd(standardized, full_matrices=False)
    if singular[0] < 1e-12 or np.isclose(singular[0], singular[1], rtol=1e-6, atol=1e-12):
        stats['line_status'] = 'no unique dominant 3D direction'
        return stats, empty
    direction = vectors[0]
    if direction[2] < 0:
        direction = -direction
    extent = standardized @ direction
    line = center + np.outer([extent.min(), extent.max()], direction)*scale
    stats['line_status'] = 'standardized dominant 3D direction (descriptive)'
    return stats, pd.DataFrame(line, columns=['PC1', 'PC2', 'score'])


def cognitive_trends(points, score_column):
    """Use a common coordinate scale for overall and within-cluster lines."""
    numeric = points[['PC1', 'PC2', score_column]].apply(pd.to_numeric, errors='coerce')
    clean = points.loc[np.isfinite(numeric).all(axis=1)].copy()
    scale = numeric.loc[clean.index].std(ddof=0).to_numpy()
    groups = [('All patients', clean)]
    if 'cluster_label' in clean:
        groups += [('Cluster '+str(int(label)), group) for label, group in clean.groupby('cluster_label')]
    summaries, lines = [], []
    for label, group in groups:
        stats, line = trend_summary(group, score_column, scale=scale)
        summaries.append({'group': label, 'outcome': score_column, **stats})
        if not line.empty:
            lines.append(line.assign(group=label, outcome=score_column))
    return pd.DataFrame(summaries), (pd.concat(lines, ignore_index=True) if lines else
                                    pd.DataFrame(columns=['PC1', 'PC2', 'score', 'group', 'outcome']))
