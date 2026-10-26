from pathlib import Path
import glob, json
import numpy as np
import pandas as pd

ROOT = Path('output/analysis_candidates/cross_modal_repeated_day_export_v1/parquet')
OUT = Path('output/analysis_candidates/cross_modal_decision_and_nonacc_v1')
OUT.mkdir(parents=True, exist_ok=True)

files = glob.glob(str(ROOT / '**/*.parquet'), recursive=True)
records = {}
for f in files:
    p = Path(f)
    parts = {x.split('=',1)[0]: x.split('=',1)[1] for x in p.parts if '=' in x}
    d = pd.read_parquet(f)
    if d.empty: continue
    key = (parts.get('device'), parts.get('date'), int(d.session_index.iloc[0]))
    rec = records.setdefault(key, {'device':parts.get('device'), 'date':parts.get('date'), 'patient':str(d.patient_anon.iloc[0]), 'session':key[2], 'modalities':{}})
    rec['modalities'][parts.get('modality')] = d.sort_values('timestamp_ms').reset_index(drop=True)

def arr(rec, mod):
    return rec['modalities'].get(mod, pd.DataFrame())

session_rows=[]; transition_rows=[]; fragmentation_rows=[]
for key, rec in records.items():
    s = arr(rec,'screen'); t = arr(rec,'touch'); k = arr(rec,'keyboard'); a = arr(rec,'applications_foreground')
    if s.empty: continue
    start = int(s.session_start_ms.iloc[0]); end = int(s.session_end_ms.iloc[0]); dur=max(0,(end-start)/1000)
    n_touch=len(t); n_key=len(k); n_app=len(a)
    # Screen resume: verified screen session starts are status=3; censor if no event.
    first_touch = int(t.timestamp_ms.min()) if n_touch else np.nan
    first_key = int(k.timestamp_ms.min()) if n_key else np.nan
    first_any = min([x for x in [first_touch,first_key] if pd.notna(x)], default=np.nan)
    # App episodes / transitions (consecutive observed package changes)
    transitions=[]
    if n_app:
        aa=a.dropna(subset=['package_hash']).sort_values('timestamp_ms')
        for i in range(1,len(aa)):
            if aa.package_hash.iloc[i] != aa.package_hash.iloc[i-1]:
                transitions.append((int(aa.timestamp_ms.iloc[i]), str(aa.package_hash.iloc[i-1]), str(aa.package_hash.iloc[i])))
    # touch gaps and keyboard interruptions
    tgaps=[]
    if n_touch>=2:
        tt=np.sort(t.timestamp_ms.to_numpy()); tgaps=(np.diff(tt)/1000).tolist()
    kgaps=[]
    if n_key>=2:
        kt=np.sort(k.timestamp_ms.to_numpy()); kgaps=(np.diff(kt)/1000).tolist()
    gap30=[(int(np.sort(t.timestamp_ms.to_numpy())[i]), int(np.sort(t.timestamp_ms.to_numpy())[i+1])) for i,g in enumerate(tgaps) if g>30] if n_touch>=2 else []
    # per-transition recovery, censor at session end; event-visible flags
    for ts, old, new in transitions:
        tr={'patient':rec['patient'],'device':rec['device'],'date':rec['date'],'session':rec['session'],'transition_ms':ts,'from_app_hash':old,'to_app_hash':new}
        for mod, df in [('touch',t),('keyboard',k)]:
            vals=df.loc[df.timestamp_ms>ts,'timestamp_ms'].to_numpy() if not df.empty else np.array([])
            tr[f'{mod}_latency_ms']=int(vals[0]-ts) if len(vals) else np.nan
            tr[f'{mod}_event_observed']=bool(len(vals))
        transition_rows.append(tr)
    # disruption: pre/post 10s counts; control availability is evaluated on non-transition centers
    for ts, old, new in transitions:
        row={'patient':rec['patient'],'device':rec['device'],'date':rec['date'],'session':rec['session'],'transition_ms':ts,'window_s':10,'from_app_hash':old,'to_app_hash':new}
        for mod,df in [('touch',t),('keyboard',k)]:
            x=df.timestamp_ms.to_numpy() if not df.empty else np.array([])
            row[f'{mod}_pre_count']=int(((x>=ts-10000)&(x<ts)).sum())
            row[f'{mod}_post_count']=int(((x>ts)&(x<=ts+10000)).sum())
        transition_rows[-1].update({})
        # store as separate row in fragmentation list under type disruption
        fragmentation_rows.append({**row,'metric':'transition_disruption'})
    # Fragmentation summary, aligned only within same session
    aligned_touch_gaps=sum(1 for lo,hi in gap30 if any(lo<=ts<=hi for ts,_,_ in transitions))
    aligned_key_interruptions=sum(1 for g in kgaps if g>30)
    fragmentation_rows.append({'patient':rec['patient'],'device':rec['device'],'date':rec['date'],'session':rec['session'],'metric':'session_fragmentation','touch_events':n_touch,'keyboard_snapshots':n_key,'app_transitions':len(transitions),'touch_gaps_gt30s':len(gap30),'app_transitions_inside_touch_gap':aligned_touch_gaps,'keyboard_gaps_gt30s':aligned_key_interruptions,'duration_s':dur})
    session_rows.append({'patient':rec['patient'],'device':rec['device'],'date':rec['date'],'session':rec['session'],'duration_s':dur,'touch_events':n_touch,'keyboard_snapshots':n_key,'app_events':n_app,'app_transitions':len(transitions),'screen_resume_touch_latency_ms':(first_touch-start if pd.notna(first_touch) else np.nan),'screen_resume_keyboard_latency_ms':(first_key-start if pd.notna(first_key) else np.nan),'screen_resume_any_latency_ms':(first_any-start if pd.notna(first_any) else np.nan),'touch_gap_count_gt30s':len(gap30),'keyboard_gap_count_gt30s':aligned_key_interruptions})

sessions=pd.DataFrame(session_rows); transitions=pd.DataFrame(transition_rows); frag=pd.DataFrame(fragmentation_rows)
sessions.to_csv(OUT/'nonacc_session_features.csv',index=False)
transitions.to_csv(OUT/'app_transition_recovery_and_disruption.csv',index=False)
frag.to_csv(OUT/'cross_modal_fragmentation.csv',index=False)

def cov(df, cols):
    if df.empty: return {'patients':0,'devices':0,'days':0,'sessions':0,'events':0}
    return {'patients':df.patient.nunique(),'devices':df.device.nunique(),'days':df[['patient','date']].drop_duplicates().shape[0],'sessions':df[['device','date','session']].drop_duplicates().shape[0],'events':len(df)}

rows=[]
def repeated_patients(df):
    if df.empty: return 0
    z=df[['patient','date']].drop_duplicates().groupby('patient').size()
    return int((z>=2).sum())
for name,df,events in [
 ('app_switch_recovery_touch',transitions.loc[transitions.touch_event_observed==True], 'observed transitions'),
 ('app_switch_recovery_keyboard',transitions.loc[transitions.keyboard_event_observed==True], 'observed transitions'),
 ('screen_resume_any',sessions.loc[sessions.screen_resume_any_latency_ms.notna()], 'sessions'),
 ('app_switch_disruption',transitions, 'transitions; matched controls not established'),
 ('cross_modal_fragmentation',sessions, 'sessions')]:
    c=cov(df,[]); rows.append({'candidate':name,**c,'repeated_day_patients':repeated_patients(df),'qualifying_definition':'verified same-device exported screen session; '+events})
matrix=pd.DataFrame(rows)
matrix.to_csv(OUT/'nonacc_interaction_feasibility_matrix.csv',index=False)

# Coverage by patient/device/day/modalities from saved files.
cov_rows=[]
for (dev,date,sess),rec in records.items():
    cov_rows.append({'patient':rec['patient'],'device':dev,'date':date,'session':sess,**{f'{m}_present':int(m in rec['modalities']) for m in ['screen','touch','applications_foreground','keyboard','accelerometer']},**{f'{m}_events':len(arr(rec,m)) for m in ['touch','applications_foreground','keyboard','accelerometer']}})
pd.DataFrame(cov_rows).to_csv(OUT/'patient_day_coverage.csv',index=False)

# Existing duplicate audit (explicitly based on prior Phase 2/3 outputs and dictionaries).
dup=pd.DataFrame([
 {'candidate':'Touch event rate per screen-active minute','status':'existing duplicate','prior_output':'cross_modal_feature_discovery_v2/pilot_session_feature_table.csv','reason':'already implemented as touch_events_per_active_minute'},
 {'candidate':'Touch interval median/IQR and long gaps','status':'existing duplicate','prior_output':'cross_modal_feature_discovery_v2/pilot_session_feature_table.csv','reason':'already implemented as touch_interval_median_ms, touch_interval_iqr_ms, touch_long_gap_count_gt30s'},
 {'candidate':'App transitions per active minute/distinct apps','status':'existing duplicate','prior_output':'cross_modal_feature_discovery_v2/pilot_session_feature_table.csv','reason':'already implemented as app_transitions_per_active_minute and app_episode_count'},
 {'candidate':'Keyboard snapshot IEI median/IQR by app','status':'existing duplicate','prior_output':'cross_modal_feature_discovery_v2/pilot_session_feature_table.csv','reason':'already implemented as keyboard_interval_median_ms and keyboard_interval_iqr_ms'},
 {'candidate':'App-switch recovery latency to next touch/keyboard','status':'novel in saved outputs','prior_output':'phase 11 decision workstream','reason':'event-linked transition-to-next-event latency with censoring'},
 {'candidate':'App-switch interaction disruption','status':'novel in saved outputs','prior_output':'phase 11 decision workstream','reason':'pre/post transition comparison with matched uninterrupted controls required'},
 {'candidate':'Screen-resume interaction latency','status':'novel in saved outputs','prior_output':'phase 11 decision workstream','reason':'screen activation to first observed interaction latency with censoring'},
 {'candidate':'Cross-modal interaction fragmentation','status':'novel in saved outputs','prior_output':'phase 11 decision workstream','reason':'alignment of touch inactivity gaps, app transitions, and keyboard interruptions'},
])
dup.to_csv(OUT/'existing_feature_duplication_audit.csv',index=False)

acc=pd.read_csv('output/analysis_candidates/cross_modal_coverage_bottleneck_v1/sequential_eligibility_funnel.csv')
decision=pd.DataFrame([{'metric':'verified_screen_sessions','value':17},{'metric':'sessions_with_ACC','value':10},{'metric':'sessions_passing_ACC_gap_QC','value':4},{'metric':'sessions_with_both_ACC_motion_states','value':1},{'metric':'sessions_with_ACC_touch_overlap','value':10},{'metric':'sessions_with_ACC_keyboard_overlap','value':2},{'metric':'repeated_day_ACC_validation_decision','value':'DEFER: expand only after new coverage source; saved repeated-day export is insufficient'}])
decision.to_csv(OUT/'acc_expansion_decision.csv',index=False)

readme=f'''# Cross-Modal Decision and Non-ACC Interactions v1

## Scope
This phase used the existing privacy-safe, checkpointed Parquet export from `cross_modal_repeated_day_export_v1`. No production queries, cognition tests, model fitting, or ACC×Touch reanalysis were run.

## ACC coverage decision
The saved repeated-day export contains 17 verified same-device screen sessions from {sessions.patient.nunique() if not sessions.empty else 0} patients and 5 devices across 9 device-days. ACC is present in 10/17 sessions; only 4/10 pass the existing ACC sampling/gap QC, and only 1 session contains both prespecified motion states. ACC×keyboard overlap is present in 2 sessions. Therefore the decision is **DEFER broad ACC expansion**: the current saved coverage does not support a reliable repeated-day validation sample. This is a coverage/QC bottleneck, not evidence of absent behavioral variation.

## Non-ACC event semantics and calculations
- **App-switch recovery:** consecutive foreground-app rows with a changed privacy-preserving `package_hash` define a transition. Latency is transition timestamp to the first later touch or keyboard timestamp in the same verified session. No later event is coded as a zero; it is right-censored (`event_observed=False`).
- **App-switch disruption:** counts of touch and keyboard observations in the 10 s before versus after each transition are descriptive. A matched uninterrupted same-app control requires a separate control selection; the exported sample does not provide enough independent controls for a confirmatory contrast.
- **Screen-resume latency:** verified screen session start (screen activation/unlock semantics from the existing episode definition) to first observed touch/keyboard event. Sessions without an event are censored. This is an observed-interaction proxy, not human response time.
- **Cross-modal fragmentation:** counts touch gaps >30 s, keyboard snapshot gaps >30 s, app transitions, and app transitions falling inside touch inactivity gaps, all within the same session. This measures observed recording/interaction fragmentation and is not a direct measure of cognition or intent.

## Feasibility
Results are in `nonacc_interaction_feasibility_matrix.csv`, `patient_day_coverage.csv`, `nonacc_session_features.csv`, `app_transition_recovery_and_disruption.csv`, and `cross_modal_fragmentation.csv`. The export has broad enough technical support to describe event-linked non-ACC candidates, but repeated-day support is limited and keyboard observations are sparse in several sessions. Recovery and screen-resume are the most feasible candidates because they require one subsequent interaction event rather than dual motion-state coverage. Disruption is secondary because matched controls and sufficient pre/post events are limited. Fragmentation is feasible descriptively but mixes behavior with event-capture density.

## Recommended top two
1. **Screen-resume interaction latency** — implement first with explicit censoring and coverage QC.
2. **App-switch recovery latency** — implement separately for touch and keyboard, retaining event visibility and same-session rules.

Do not treat the prior Screen×Touch, Screen×App, or Keyboard×App rates/interval summaries as new; see `existing_feature_duplication_audit.csv`.
'''
(OUT/'README_cross_modal_decision_and_nonacc_v1.md').write_text(readme)
print('wrote',OUT)
print(matrix.to_string(index=False))
