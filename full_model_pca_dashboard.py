"""Display saved Full Model PCA runs and project new feature rows without fitting."""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from full_model_pca import ID, OUT, project_frozen


@st.cache_data(show_spinner=False)
def load_table(run: str, name: str):
    path = Path(run) / name
    if not path.exists() or path.stat().st_size < 3:
        return pd.DataFrame()
    return pd.read_csv(path, dtype={ID: str})


def read_json(run, name):
    return json.loads((run / name).read_text())


def patient_map(scores, variance, key, title):
    if scores.empty or 'PC2' not in scores:
        st.info('There are not enough eligible observations for this map.')
        return
    choices = [c for c in ['cluster_label', 'global_T1', 'memory_T1', 'ef_T1', 'processing_speed_T1',
                           'attention_T1', 'motor_T1', 'global_delta', 'acc_feature_days',
                           'acc_daily_coverage_median'] if c in scores and scores[c].notna().any()]
    labels = {'cluster_label': 'Exploratory cluster', 'global_T1': 'Global T1', 'memory_T1': 'Memory T1',
              'ef_T1': 'Executive function T1', 'processing_speed_T1': 'Processing speed T1',
              'attention_T1': 'Attention T1', 'motor_T1': 'Motor T1', 'global_delta': 'Global T2 − T1',
              'acc_feature_days': 'Observed ACC days', 'acc_daily_coverage_median': 'Median ACC day coverage'}
    left, right = st.columns([2, 1])
    color = left.selectbox('Color patients by', choices, format_func=lambda c: labels[c], key=key+'_color') if choices else None
    dimensions = right.radio('Map', ['2D', '3D'] if 'PC3' in scores else ['2D'], horizontal=True, key=key+'_dim')
    plot = scores.copy()
    if color == 'cluster_label':
        plot[color] = plot[color].astype('Int64').astype(str).map(lambda n: 'Cluster '+n)
    ratios = variance.set_index('component').explained_variance_percent
    axis_labels = {pc: f'{pc} · {ratios[pc]:.1f}%' for pc in ratios.index}
    hover = [c for c in ['acc_feature_days', 'global_T1', 'global_delta'] if c in plot]
    kwargs = dict(data_frame=plot, x='PC1', y='PC2', color=color, hover_name=ID,
                  hover_data=hover, labels={**labels, **axis_labels}, title=title)
    fig = px.scatter_3d(z='PC3', **kwargs) if dimensions == '3D' else px.scatter(**kwargs)
    fig.update_traces(marker_size=7 if dimensions == '3D' else 11)
    fig.update_layout(height=530, margin=dict(l=15, r=15, t=55, b=15))
    st.plotly_chart(fig, width='stretch', key=key+'_chart')
    if color:
        absent = int(scores[color].isna().sum())
        if absent:
            st.caption(f'{absent} mapped patients have no observed value for this color overlay.')


def feature_details(run, panel, key):
    loadings = load_table(str(run), panel+'/loadings.csv')
    if loadings.empty:
        return
    component = st.selectbox('Feature contributions to', [c for c in loadings if c.startswith('PC')], key=key+'_pc')
    top = loadings.assign(weight=loadings[component].abs()).nlargest(15, 'weight').sort_values(component)
    fig = px.bar(top, x=component, y='feature_name', color='block', orientation='h',
                 title='Largest PCA loadings', color_discrete_map={'Digital': '#4568b0', 'ACC': '#239b85'})
    fig.update_layout(height=530, yaxis_title=None, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, width='stretch', key=key+'_loadings')
    st.caption('Loadings describe axes of variation. Their sign is arbitrary; they are not clinical effect sizes.')
    with st.expander('All loadings, preprocessing and cluster profiles'):
        for name in ['loadings', 'transformations', 'cluster_quality', 'cluster_feature_medians']:
            table = load_table(str(run), panel+'/'+name+'.csv')
            if not table.empty:
                st.markdown('**'+name.replace('_', ' ').capitalize()+'**')
                st.dataframe(table, hide_index=True, width='stretch')


def decline_view(run, record):
    displacement = load_table(str(run), 'decliner_displacements.csv')
    st.write('Only patients with **global T2 < T1**, valid saved windows and sufficient digital and ACC data at both endpoints enter this view.')
    a, b, c = st.columns(3)
    a.metric('Observed global decliners', record['observed_global_decliners'])
    b.metric('Eligible paired patients', record['paired_decliners'])
    c.metric('Observed-change PCA patients', record['decline_change']['patients'])
    st.caption('The same patients supply both endpoints. T2 features use the existing midpoint→T2 window.')
    if displacement.empty:
        st.info('No decliners have sufficient data at both endpoints. See the patient audit for exclusions.')
        return
    st.subheader('T1 → T2 on the fixed combined T1 axes')
    selected = st.selectbox('Follow a patient', ['All']+displacement[ID].tolist(), key='full_decline_subject')
    visible = displacement if selected == 'All' else displacement[displacement[ID].eq(selected)]
    fig = go.Figure()
    for row in visible.to_dict('records'):
        fig.add_trace(go.Scatter(x=[row['PC1_T1'], row['PC1_T2']], y=[row['PC2_T1'], row['PC2_T2']],
                                mode='lines', line=dict(color='#a1b1c9'), showlegend=False, hoverinfo='skip'))
        fig.add_annotation(x=row['PC1_T2'], y=row['PC2_T2'], ax=row['PC1_T1'], ay=row['PC2_T1'],
                           xref='x', yref='y', axref='x', ayref='y', text='', showarrow=True,
                           arrowhead=3, arrowwidth=1, arrowcolor='#a1b1c9')
    for endpoint, color, symbol in [('T1', '#4568b0', 'circle'), ('T2', '#d47644', 'diamond')]:
        fig.add_trace(go.Scatter(x=visible['PC1_'+endpoint], y=visible['PC2_'+endpoint], mode='markers',
                                name=endpoint, text=visible[ID], marker=dict(color=color, symbol=symbol, size=11),
                                hovertemplate='Subject %{text}<br>PC1: %{x:.2f}<br>PC2: %{y:.2f}<extra>'+endpoint+'</extra>'))
    fig.update_layout(xaxis_title='PC1 · fixed T1 axes', yaxis_title='PC2 · fixed T1 axes', height=500)
    st.plotly_chart(fig, width='stretch', key='full_displacements')
    st.caption('T2 uses the saved T1 transformation, imputation, scale and PCA. Arrow direction does not itself indicate cognitive improvement or decline.')
    st.subheader('PCA of observed T2 − T1 feature changes')
    summary = record['decline_change']
    if summary['status'] != 'complete':
        st.info(summary['reason'])
    else:
        st.write(f"PC1 + PC2 explain **{summary['pc1_pc2_percent']:.1f}%** of change-feature variation.")
        st.caption('This separate PCA has its own axes. A feature change is missing if either endpoint is unobserved.')
        st.info(summary['cluster_note'])
        patient_map(load_table(str(run), 'decline_change/scores.csv'),
                    load_table(str(run), 'decline_change/variance.csv'), 'full_delta', 'Decliners · observed feature-change PCA')
        feature_details(run, 'decline_change', 'full_delta_features')


def projection_view(run, baseline_scores):
    model = read_json(run, 'baseline/model.json')
    st.write('Place a new subject onto the saved combined T1 map. Supply one row of patient-level features calculated with the same definitions and clinical window.')
    st.caption('The axes and training cohort stay fixed. At least half of each feature block must be observed; leave unavailable values blank.')
    st.download_button('Download blank feature template', (run/'new_subject_template.csv').read_bytes(),
                       'full_model_pca_subject_template.csv', mime='text/csv')
    mode = st.radio('Provide features', ['Upload CSV', 'Enter values'], horizontal=True, key='full_projection_mode')
    candidate = None
    label = 'New subject'
    if mode == 'Upload CSV':
        uploaded = st.file_uploader('One subject per CSV; use the template column names', type=['csv'], key='full_projection_upload')
        if uploaded is not None:
            try:
                candidate = pd.read_csv(io.BytesIO(uploaded.getvalue()))
                if len(candidate) != 1:
                    raise ValueError('Upload exactly one subject row.')
                label = str(candidate.get('subject_label', pd.Series(['New subject'])).fillna('New subject').iloc[0])
                ignored = [c for c in candidate if c not in model['features'] and c not in ('subject_label', ID)]
                if ignored:
                    st.caption('Columns outside the fitted panel are ignored: '+', '.join(ignored))
            except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as exc:
                st.error(str(exc))
                candidate = None
    else:
        label = st.text_input('Subject label', value='New subject', key='full_projection_label')
        entry = pd.DataFrame({'Feature': model['features'], 'Value': np.full(len(model['features']), np.nan)})
        edited = st.data_editor(entry, hide_index=True, disabled=['Feature'], width='stretch', height=450,
                                key='full_projection_editor', column_config={'Value': st.column_config.NumberColumn('Observed value')})
        candidate = pd.DataFrame([dict(zip(edited.Feature, edited.Value))])
    if st.button('Project onto fixed PCA', type='primary', key='full_project_button', disabled=candidate is None):
        try:
            projected = project_frozen(candidate, model)
            fig = px.scatter(baseline_scores, x='PC1', y='PC2', hover_name=ID, opacity=.4)
            fig.add_trace(go.Scatter(x=projected.PC1, y=projected.PC2, mode='markers+text', text=[label],
                                    textposition='top center', name='New subject', marker=dict(size=18, symbol='star', color='#dd634c')))
            fig.update_layout(title='New subject on the fixed combined T1 map', height=500)
            st.plotly_chart(fig, width='stretch', key='full_new_subject_map')
            result = projected.copy()
            result.insert(0, 'subject_label', label)
            st.dataframe(result, hide_index=True, width='stretch')
            st.caption('The assigned cluster is a descriptive nearest-centroid label, not a diagnosis or cognitive prediction.')
            st.download_button('Download projection', result.to_csv(index=False), 'full_model_projection.csv', mime='text/csv')
        except (ValueError, TypeError) as exc:
            st.error(f'Cannot project this row: {exc}')


def full_model_pca_page():
    st.title('Full Model PCA')
    st.caption('Digital behavior + completed accelerometer movement features · existing clinical windows')
    current = OUT/'current.json'
    if not current.exists():
        st.info('The first analysis run is being prepared.')
        return
    try:
        run_id = json.loads(current.read_text())['run_id']
        if Path(run_id).name != run_id:
            raise ValueError('Invalid run path')
        run = OUT/'runs'/run_id
        record = read_json(run, 'run_record.json')
    except (OSError, ValueError, KeyError) as exc:
        st.error(f'The saved analysis run is unavailable: {exc}')
        return
    summary = record['baseline']
    a, b, c, d = st.columns(4)
    a.metric('Combined T1 patients', f"{summary['patients']} / {record['source_patients']}")
    b.metric('Features in PCA', summary['features'])
    c.metric('PC1 + PC2', f"{summary['pc1_pc2_percent']:.1f}%")
    d.metric('Paired decliners', record['paired_decliners'])
    st.write('The original 41 digital features are combined with 15 ACC movement features. Row counts, sampling quality and coverage are retained for audit. Each patient needs observed values for at least half of each feature block.')
    st.caption('Exploratory research map. T1 features summarize T1→midpoint observations; they are not measurements available prospectively at the T1 visit.')
    scores = load_table(str(run), 'baseline/scores.csv')
    tabs = st.tabs(['T1 combined map', 'T2 − T1 · decliners', 'Features & comparisons', 'Coverage & audit', 'New subject', 'Methods & downloads'])
    with tabs[0]:
        st.info(summary['cluster_note'])
        if not summary['acceptable_cluster_solution'] and summary['cluster_sizes']:
            counts = scores.cluster_label.value_counts()
            small = scores[scores.cluster_label.isin(counts[counts < 5].index)]
            st.warning('The combined map contains a very small reference cluster. High explained variance or silhouette does not establish a useful subgroup; inspect its ACC coverage and feature values.')
            st.dataframe(small[[c for c in [ID, 'cluster_label', 'acc_feature_days', 'acc_observed_minutes',
                                           'acc_daily_coverage_median', 'PC1', 'PC2'] if c in small]],
                         hide_index=True, width='stretch')
        patient_map(scores, load_table(str(run), 'baseline/variance.csv'), 'full_baseline', 'Combined digital + ACC · T1')
        st.caption('Cognitive domains color the same fixed map; they do not enter the PCA fit.')
        st.write('Cluster sizes: '+', '.join(map(str, summary['cluster_sizes'])) if summary['cluster_sizes'] else summary['cluster_note'])
        variance = load_table(str(run), 'baseline/variance.csv')
        st.plotly_chart(px.bar(variance, x='component', y='explained_variance_percent', title='Variation captured by each component'), width='stretch', key='full_variance')
    with tabs[1]:
        decline_view(run, record)
    with tabs[2]:
        st.subheader('Does ACC change the representation?')
        st.write('Every comparison below uses the same eligible T1 patients. The mean and device-choice checks test aggregation choices.')
        comparison = load_table(str(run), 'panel_comparison.csv')
        st.dataframe(comparison[[c for c in ['panel', 'patients', 'features', 'pc1_pc2_percent', 'selected_k', 'cluster_sizes',
                                            'silhouette', 'subsample_ari', 'cluster_ari_vs_main', 'acceptable_cluster_solution'] if c in comparison]],
                     hide_index=True, width='stretch')
        st.caption('Higher explained variance is not better clinical prediction. ARI measures agreement between cluster assignments; 1 means identical membership.')
        feature_details(run, 'baseline', 'full_baseline_features')
        with st.expander('Feature definitions and inclusion'):
            st.dataframe(load_table(str(run), 'feature_inventory.csv'), hide_index=True, width='stretch')
    with tabs[3]:
        st.write('ACC days must fit completely inside the saved clinical window. The main analysis excludes multi-device days. Every source patient remains listed here.')
        audit = load_table(str(run), 'patient_audit.csv')
        show_excluded = st.checkbox('Only patients excluded from the combined T1 map', key='full_excluded')
        view = audit[audit.t1_eligible.eq(False)] if show_excluded else audit
        columns = [ID, 't1_acc_feature_days', 't2_acc_feature_days', 't1_digital_coverage', 't1_acc_coverage',
                   't1_eligible', 't1_reason', 'global_decliner', 'paired_eligible', 'paired_reason', 'delta_eligible']
        st.dataframe(view[columns], hide_index=True, width='stretch')
        st.subheader('Technical and cognitive overlays')
        correlations = load_table(str(run), 'baseline/correlations.csv')
        role = st.radio('Inspect', ['Technical audit', 'Cognitive overlay'], horizontal=True, key='full_correlation_role')
        st.dataframe(correlations[correlations.role.eq(role)], hide_index=True, width='stretch')
        st.caption('Pairwise Spearman correlations are descriptive. A strong technical correlation can indicate collection effects.')
        with st.expander('ACC day inclusion decisions'):
            endpoint = st.selectbox('Window', ['t1', 't2'], key='full_day_window')
            days = load_table(str(run), endpoint+'_acc_day_audit.csv')
            st.dataframe(days.groupby('reason').size().rename('Device-days').reset_index(), hide_index=True, width='stretch')
            st.dataframe(days, hide_index=True, width='stretch')
    with tabs[4]:
        projection_view(run, scores)
    with tabs[5]:
        st.caption('Run completed: '+record['created_at'])
        st.markdown((run/'README_full_model_pca.md').read_text())
        for name in ['patient_audit.csv', 'feature_inventory.csv', 'panel_comparison.csv', 't1_patient_features.csv',
                     't2_patient_features.csv', 'decliner_displacements.csv', 'decliner_feature_changes.csv',
                     'baseline/scores.csv', 'baseline/loadings.csv', 'baseline/model.json', 'run_record.json']:
            st.download_button('Download '+name, (run/name).read_bytes(), name.replace('/', '_'), key='full_download_'+name)
