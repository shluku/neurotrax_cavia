from pathlib import Path
import pandas as pd, numpy as np
out=Path('output/analysis_candidates/cross_modal_interaction_features_v1');out.mkdir(parents=True,exist_ok=True)
acc=pd.read_csv('output/analysis_candidates/cross_modal_acc_priority_v1/acc_synchronized_segments.csv')
sess=pd.read_csv('output/analysis_candidates/cross_modal_feature_discovery_v2/pilot_session_feature_table.csv')
# Join the saved synchronized ACC segments to the verified same-day event sessions.
acc['patient_anon']=acc.device_anon.map({'dev_d74f7a':'patient_041','dev_72e21d':'patient_039'})
sess2=sess.merge(acc[['patient_anon','day','session_index','acc_n','acc_duration_s','sampling_median_ms','sampling_p95_ms','gap_fraction_gt1s','mag_mean','mag_sd','moving_fraction','gravity_like','acc_segment_type']],on=['patient_anon','day','session_index'],how='left')
sess2['touch_rate_per_min']=sess2.touch_events/sess2.session_minutes.replace(0,np.nan)
sess2['touch_motion_product']=sess2.touch_rate_per_min*sess2.moving_fraction
sess2['touch_rate_stationary_proxy']=sess2.touch_rate_per_min*(1-sess2.moving_fraction)
sess2.to_csv(out/'interaction_session_proxy_table.csv',index=False)
# Aggregate device/session coverage, retaining native cadence and hardware identity from v2 metadata audit.
meta=pd.DataFrame([
 {'device_anon':'dev_d74f7a','sensor_name':'accelerometer-lsm6dsm','sensor_vendor':'st','sensor_version':'1','minimum_delay_us':2000,'observed_rate_hz_approx':5.0},
 {'device_anon':'dev_72e21d','sensor_name':'BMI120 Accelerometer','sensor_vendor':'BOSCH','sensor_version':'2062701','minimum_delay_us':2500,'observed_rate_hz_approx':125.0},])
coverage=sess2.merge(meta,on='device_anon',how='left')
coverage['acc_verified']=coverage.acc_n.notna()
coverage.to_csv(out/'patient_device_day_coverage.csv',index=False)
# compact feature summary
rows=[]
for name,col,definition,status in [
 ('touch_motion_coupling_proxy','touch_motion_product','session touch rate per minute multiplied by ACC moving fraction; coarse session proxy, not event-centered','proxy_estimable'),
 ('stationary_touch_rate_proxy','touch_rate_stationary_proxy','session touch rate per minute multiplied by one minus ACC moving fraction','proxy_estimable'),
 ('touch_motion_event_centered','', 'ACC magnitude in a prespecified window around touch events versus matched no-touch windows','not_estimable_saved_outputs'),
 ('motion_conditioned_touch_variability','', 'within-burst touch interval variability stratified by ACC stationary/moving bins','not_estimable_saved_outputs'),
 ('app_switch_interruption_cost','', 'keyboard IEI after minus before foreground-app transitions with same-app controls','not_estimable_saved_outputs')]:
 x=coverage[col].dropna() if col else pd.Series(dtype=float)
 rows.append({'feature':name,'status':status,'n_sessions':len(x) if col else 0,'n_patients':coverage.loc[coverage[col].notna(),'patient_anon'].nunique() if col else 0,'median':x.median() if len(x) else np.nan,'iqr':x.quantile(.75)-x.quantile(.25) if len(x) else np.nan,'definition':definition})
pd.DataFrame(rows).to_csv(out/'pilot_feature_distributions.csv',index=False)
# novelty/provenance matrix
pd.DataFrame([
 {'feature_family':'Touch–Motion Coupling','phase4_feature':'event-centered ACC magnitude contrast around touch vs matched non-touch periods','existing_duplicate':'No','literature_provenance':'Inspired by synchronized keyboard/accelerometer interaction studies; exact project implementation is new','current_status':'Blocked at event-level ACC retrieval; coarse session proxy retained separately'},
 {'feature_family':'Motion-Conditioned Touch Variability','phase4_feature':'touch interval IQR/CV separately in stationary and moving ACC bins','existing_duplicate':'No','literature_provenance':'Novel project hypothesis','current_status':'Not estimable from saved summaries'},
 {'feature_family':'App-Switch Interruption Cost','phase4_feature':'post-transition minus pre-transition keyboard IEI with uninterrupted same-app control windows','existing_duplicate':'No','literature_provenance':'Novel project hypothesis; uses existing app and keyboard streams','current_status':'Not estimable from saved summaries'},
 {'feature_family':'Screen×Touch rate/intervals','phase4_feature':'touch rate, median/IQR intervals in screen sessions','existing_duplicate':'Yes','literature_provenance':'Phase 2/3 implementation','current_status':'Excluded from novelty shortlist'},
 {'feature_family':'Screen×App transitions','phase4_feature':'app transition rate/fraction/distinct apps','existing_duplicate':'Yes','literature_provenance':'Phase 2/3 implementation','current_status':'Excluded from novelty shortlist'},
 {'feature_family':'Keyboard×App IEI','phase4_feature':'same-app keyboard snapshot IEI median/IQR','existing_duplicate':'Yes','literature_provenance':'Phase 2/3 implementation','current_status':'Excluded from novelty shortlist'},
],).to_csv(out/'novelty_literature_provenance_matrix.csv',index=False)
