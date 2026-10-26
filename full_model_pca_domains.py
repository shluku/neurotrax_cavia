"""Separate outcome-informed top-five panels drawn from digital + ACC features."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import RepeatedKFold

from full_model_pca import ID, fit_panel, project_frozen, save_panel, write_json
from pca_cognitive_trends import cognitive_trends
from unsupervised_phenotyping_domain_top5 import DOMAIN_TARGETS, RANDOM_STATE, _build_ridge_pipeline, _slug


def rank_features(frame, features, target, n_splits=5, n_repeats=20, top_n=5):
    """Reproduce the previous repeated-fold Ridge ranking on the expanded panel."""
    usable = frame.loc[pd.to_numeric(frame[target], errors='coerce').notna()]
    X = usable[features].apply(pd.to_numeric, errors='raise')
    y = pd.to_numeric(usable[target]).to_numpy()
    folds = []
    splitter = RepeatedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=RANDOM_STATE)
    for split, (train, _) in enumerate(splitter.split(X)):
        pipeline = _build_ridge_pipeline()
        pipeline.fit(X.iloc[train], y[train])
        terms = pipeline.named_steps['imputer'].get_feature_names_out(features)
        for term, coef in zip(terms, pipeline.named_steps['ridge'].coef_):
            folds.append({'target': target, 'repeat': split//n_splits+1, 'fold': split % n_splits+1,
                          'feature_name': term, 'coefficient': float(coef),
                          'alpha': float(pipeline.named_steps['ridge'].alpha_)})
    folds = pd.DataFrame(folds)
    real = folds[folds.feature_name.isin(features)]
    ranked = real.groupby('feature_name').coefficient.agg(
        coefficient_mean='mean', coefficient_sd='std', n_folds='size',
        direction_stability=lambda s: max(s.gt(0).mean(), s.lt(0).mean()),
    ).reset_index()
    ranked['absolute_mean_coefficient'] = ranked.coefficient_mean.abs()
    ranked = ranked.sort_values(['absolute_mean_coefficient', 'direction_stability', 'feature_name'],
                                ascending=[False, False, True]).reset_index(drop=True)
    ranked['rank'] = np.arange(1, len(ranked)+1)
    ranked['selected'] = ranked['rank'] <= top_n
    ranked['target'] = target
    ranked['selection_patients'] = len(usable)
    return ranked, folds


def save_trends(folder, points, outcome):
    summary, lines = cognitive_trends(points, outcome)
    summary.to_csv(folder/'cognitive_trend_summary.csv', index=False)
    lines.to_csv(folder/'cognitive_trend_lines.csv', index=False)


def build_domain_panels(run, frames, eligible_ids, digital, acc, audit):
    summary_rows, selection_rows = [], []
    candidates = digital + acc
    candidate_frame = frames['t1'].loc[eligible_ids]
    excluded = set(audit.index[audit.excluded_by_request])
    for domain, target in DOMAIN_TARGETS.items():
        print(f'Domain {domain}: ranking {len(candidates)} candidates across 100 Ridge folds', flush=True)
        ranked, folds = rank_features(candidate_frame, candidates, target)
        ranked.insert(0, 'domain', domain)
        ranked['block'] = np.where(ranked.feature_name.isin(acc), 'ACC', 'Digital')
        selected = ranked.loc[ranked.selected, 'feature_name'].tolist()
        dcols, acols = [f for f in selected if f in digital], [f for f in selected if f in acc]
        domain_audit = pd.DataFrame(index=frames['t1'].index)
        domain_audit['combined_cohort_eligible'] = domain_audit.index.isin(eligible_ids)
        domain_audit['excluded_by_request'] = domain_audit.index.isin(excluded)
        domain_audit['has_domain_t1_score'] = frames['t1'][target].notna()
        domain_audit['selected_feature_coverage'] = frames['t1'][selected].notna().mean(axis=1)
        domain_audit['included'] = (domain_audit.combined_cohort_eligible & domain_audit.has_domain_t1_score
                                    & domain_audit.selected_feature_coverage.ge(.5))
        ids = domain_audit.index[domain_audit.included]
        frame = frames['t1'].loc[ids]
        print(f'Domain {domain}: fitting {len(ids)} patients with {selected}', flush=True)
        result = fit_panel(frame, dcols, acols)
        if 'model' not in result:
            raise ValueError(f'Insufficient data for domain {domain}')
        result['model'].update(domain=domain, target=target, coverage_rule='selected_panel_half',
                               selection_uses_outcome=True, selected_features=selected)
        root = run/'domains'/_slug(domain)
        save_panel(root/'baseline', result, frame)
        folds.to_csv(root/'ridge_fold_coefficients.csv', index=False)
        ranked.to_csv(root/'feature_ranking.csv', index=False)
        save_trends(root/'baseline', frame[[target]].join(result['scores']), target)
        pd.DataFrame([{'subject_label': '', **{f: np.nan for f in result['model']['features']}}]).to_csv(
            root/'new_subject_template.csv', index=False)

        # Keep the approved global-decline rule and original window eligibility.
        paired = ids.intersection(audit.index[audit.paired_eligible])
        paired = paired[frames['t2'].loc[paired, selected].notna().mean(axis=1).ge(.5)]
        first, second = frames['t1'].loc[paired], frames['t2'].loc[paired]
        start = project_frozen(first, result['model'])
        end = project_frozen(second, result['model'])
        t2_target = target.replace('_T1', '_T2')
        delta_target = target.replace('_T1', '_delta')
        outcomes = list(dict.fromkeys(['global_T1', 'global_T2', 'global_delta', target, t2_target, delta_target]))
        context = first[outcomes].copy()
        context[delta_target] = context[t2_target] - context[target]
        t2_points = context.join(end)
        t2_points.to_csv(root/'t2_projected_scores.csv', index_label=ID)
        save_trends(root, t2_points, t2_target)
        displacement = context.copy()
        for pc in start.filter(regex=r'^PC\d+$'):
            displacement[pc+'_T1'] = start[pc]
            displacement[pc+'_T2'] = end[pc]
            displacement[pc+'_change'] = end[pc]-start[pc]
        displacement.to_csv(root/'decliner_displacements.csv', index_label=ID)
        changes = second[selected]-first[selected]
        delta_ids = changes.index[changes.notna().mean(axis=1).ge(.5)]
        delta_frame = changes.loc[delta_ids].join(context)
        delta_result = fit_panel(delta_frame, dcols, acols, endpoint='T2-T1')
        if 'model' in delta_result:
            delta_result['model'].update(domain=domain, target=delta_target, coverage_rule='selected_panel_half',
                                        selection_uses_outcome=True, selected_features=selected)
        save_panel(root/'decline_change', delta_result, delta_frame)
        delta_frame.to_csv(root/'decliner_feature_changes.csv', index_label=ID)
        if 'scores' in delta_result:
            save_trends(root/'decline_change', delta_frame[[delta_target]].join(delta_result['scores']), delta_target)
        domain_audit['paired_eligible'] = domain_audit.index.isin(paired)
        domain_audit['delta_eligible'] = domain_audit.index.isin(delta_ids)
        domain_audit.to_csv(root/'patient_audit.csv', index_label=ID)
        record = {'domain': domain, 'target': target, 't2_target': t2_target, 'delta_target': delta_target,
                  'features': selected, 'selection_patients': int(ranked.selection_patients.iloc[0]),
                  'excluded_patient_ids': sorted(excluded), 'selection_uses_outcome': True,
                  'availability_rule': 'Existing combined cohort, observed domain T1 score, >=50% of selected five features',
                  'paired_decliners': len(paired), 'baseline': result['summary'], 'decline_change': delta_result['summary']}
        write_json(root/'domain_record.json', record)
        summary_rows.append({'domain': domain, 'target': target, 'selected_features': ';'.join(selected),
                             'paired_decliners': len(paired), **result['summary']})
        selection_rows.append(ranked)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(run/'domain_summary.csv', index=False)
    pd.concat(selection_rows, ignore_index=True).to_csv(run/'domain_feature_ranking.csv', index=False)
    return summary[['domain', 'patients', 'features', 'paired_decliners', 'pc1_pc2_percent']].to_dict('records')
