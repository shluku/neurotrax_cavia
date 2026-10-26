"""Catalog saved evidence only: no extraction, statistical estimation, or models.

Exact CSV statistic strings are retained. Code is parsed as text/AST, never
imported or executed. Deliverables are new versioned files; historical sources
are hashed before and after catalog construction. JSON is an authoring
intermediate for the CSV exporter, not a new research documentation system.
"""
from __future__ import annotations
import ast
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TAG = '20261021_v1'
DEST = ROOT / 'manuscript/tables'
STAGING = Path('/tmp/complete_feature_findings_register_20261021')
MASTER = 'manuscript/tables/master_association_table_20261020.csv'
K = 'output/analysis_candidates/keyboard_deep_dive_v1/'
W = K + 'word_completion_timing_v1/'
SHARED = 'phase2_extract_exploratory_t1_week_24h_selected_features.py'
WC = 'keyboard_word_completion_deep_dive.py'
DEEP = 'keyboard_deep_dive.py'
INPUTS = {}


def remember(path):
    p = ROOT / path
    INPUTS[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p


def read(path):
    p = remember(path)
    with p.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def number(s):
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError):
        return None


def finite(s):
    return number(s) is not None


def flag(s, limit, inclusive=False):
    x = number(s)
    return 'not available' if x is None else ('yes' if (x <= limit if inclusive else x < limit) else 'no')


def base_feature(f):
    aliases = {'word_completion_median_delta': 'word_completion_median_ms',
               'word_completion_iqr_delta': 'word_completion_iqr_ms',
               'snapshot_IEI_delta': 'keyboard_12_18_median_inter_event_interval_ms',
               'afternoon_iei_delta_ms': 'keyboard_12_18_median_inter_event_interval_ms'}
    f = aliases.get(f, f)
    return re.sub(r'(_first14|_last14)?_delta$|_T1$|_T2$', '', f)


def outcome_name(s):
    s = s.lower().replace(' ', '_')
    s = re.sub(r'_t1_median_group$|_t1$|_t2$|_delta$', '', s)
    return {'ef': 'executive_function', 'global_cognitive': 'global'}.get(s, s)


def modality(f):
    f = base_feature(f).removeprefix('supplemental_t1_')
    if f.startswith('acc_'): return 'accelerometer'
    if f.startswith('aware_') or f in {'system_log_density','data_logging_coverage_days'}: return 'aware_log'
    if f in {'usable_feature_count_all_available','baseline_feature_missing_fraction','baseline_table_coverage_fraction'}: return 'cross_modality_recording_coverage'
    if f.startswith('active_'):
        for token,mod in [('keyboard','keyboard'),('touch','touch'),('activity','plugin_google_activity_recognition'),('screen','screen'),('app','applications_foreground')]:
            if token in f: return mod
    if f.startswith(('keyboard', 'word_completion', 'afternoon', 'delta_afternoon', 'delta_log_afternoon')) or f in {'device_set_changed','package_jaccard_similarity','high_confidence_fraction','active_days','active_minutes','valid_interval_count','long_pause_count_2s','snapshot_rate_per_active_minute','unique_package_count','distinct_observations_in_window','duplicate_rows_removed','raw_rows_in_window','json_parse_errors'}: return 'keyboard'
    if f.startswith(('activity_', 'plugin_')): return 'plugin_google_activity_recognition'
    if f.startswith(('app_', 'unique_foreground')): return 'applications_foreground'
    if f.startswith(('night_screen','median_unlocked','screen_')): return 'screen'
    if f.startswith(('median_light','night_mean_light','percent_dark','light_')): return 'light'
    if 'bluetooth' in f: return 'bluetooth'
    if 'gsm_neighbor' in f: return 'gsm_neighbor'
    if 'gsm' in f: return 'gsm'
    if 'battery' in f or 'charging' in f: return 'battery'
    if 'call' in f: return 'calls'
    if 'message' in f: return 'messages'
    if f.startswith('sensor_linear_accelerometer'): return 'sensor_linear_accelerometer'
    if f.startswith(('location_', 'locations_')): return 'locations'
    return f.split('_')[0]


WINDOW_HALF = 'Early=[T1, clinical midpoint); Late=[midpoint,T2); delta=Late-Early. Participant-specific calendar spans; Early fallback for missing valid T2. T1 outcome associations use post-T1 observations and are concurrent/retrospective.'
WINDOW_THIRD = 'First=[T1,T1+(T2-T1)/3); Last=[T1+2*(T2-T1)/3,T2); middle excluded; delta=Last-First. Both periods require >=7 observed days for primary screen.'
WORD_ISSUES = ('Word Completion Timing v1 requires technical clarification: append-only is checked within each row, not current_text[i-1]==before_text[i]; no single-character increment requirement; multi-character paste/prediction can pass. edits state can carry across abandoned candidates/burst resets. Literal ASCII space only; no general delimiter parser. Source permits zero completion duration. The saved 27-vs-28 comparison is not identical-patient comparison. Password exclusion was added after the saved extraction in the session history; saved-file exclusion is not verified. No saved missing-snapshot simulation, word-length/app adjustment or test-retest reliability.')
KEY_ISSUES = ('Text-state snapshots, not key-down/up events. Timing depends on collection cadence, OS/app/device, missing states and sampling. Counts depend on exposure/coverage. Absent observations are not no typing. App grouping does not verify uninterrupted foreground application use.')
FAMILY_NOTES = {
 'keyboard': ('Possible communication production, pausing or editing rhythm; behavioral attribution requires event/sampling validation.', KEY_ISSUES),
 'touch': ('Possible phone interaction volume, scrolling strategy or app breadth; not a direct motor or executive-function test.', 'Accessibility actions are not exact finger taps; app UI/index conventions, missingness and logging frequency affect counts. Shared direction changes are not reset by app/device.'),
 'screen': ('Possible phone access and engagement pattern; no direct measure of task completion or sleep.', 'OS state codes and missing/repeated unlock/off events affect durations and counts; active hours count observed clock bins, not continuous use.'),
 'applications_foreground': ('Possible breadth/concentration of foreground app use; not task performance.', 'Counts reflect logged foreground records; system apps, duplicates and event frequency can dominate. Entropy uses event shares, not usage durations.'),
 'plugin_google_activity_recognition': ('Possible phone-carried activity context; still/unknown are labels, not clinical inactivity or sleep.', 'Recognition-model error, confidence thresholds, phone carriage and event-triggered sampling affect label distributions.'),
 'accelerometer': ('Possible variation/motion of the phone; not validated gait, tremor or body activity.', 'Includes gravity, device placement, irregular sampling, selected plugin-event days and threshold choices. Four multi-device days have documented aggregation issues. No comparable individual feature-cognition screen saved.'),
 'sensor_linear_accelerometer': ('Hardware/recording context only; no direct patient movement interpretation.', 'These are sensor capability metadata (resolution/range/power), not the raw linear-acceleration signal.'),
 'light': ('Possible ambient light/phone placement context; not evidence of sleep or circadian disorder.', 'Pocket/bag/covered phone and sensor/device differences dominate; supplemental quantiles use deterministic subsampling rather than all samples.'),
 'proximity': ('Possible near-object/covered-phone context; not social proximity.', 'Sensor units/range vary by hardware; near threshold and duplicate logging affect state counts; sampled quantiles and sparse coverage.'),
 'locations': ('Possible extent of phone displacement; not necessarily walking or independent mobility.', 'GPS jitter, invalid/missing coordinates, long gaps and phone transport affect summed distance; location may span devices.'),
 'barometer': ('Possible pressure/vertical phone movement context; not posture or clinical mobility.', 'Weather, elevation and device drift; smoothing, sparse gaps and delayed windows affect transition thresholds.'),
 'calls': ('Possible telephone communication volume; not social quality or cognition itself.', 'Logged call types/duration units, duplication and observation span affect totals; no content is evaluated.'),
 'messages': ('Possible logged SMS communication volume; not total messaging or social quality.', 'Message type/trace deduplication, non-SMS app coverage, missingness and exposure affect counts.'),
 'bluetooth': ('Possible device/environment breadth; not count of people encountered.', 'Scan cadence, MAC randomization, hardware and repeated beacons change diversity; no reliable social-contact inference.'),
 'gsm': ('Possible cellular-context change; not direct mobility distance.', 'Tower handoff, reception and repeated rows can change identifiers without movement.'),
 'gsm_neighbor': ('Possible breadth/change of nearby cellular context; not direct mobility.', 'Invalid IDs, handoff, scanning and reception affect recorded neighbors; identifiers are not clinical behavior.'),
 'battery': ('Possible charging/phone management context; not direct engagement.', 'Battery health, hardware, sampling intensity and duplicate records affect counts; these are samples, not charging episodes.'),
 'telephony': ('Connectivity availability/context, not amount of internet use.', 'Android state-code mapping, device configuration and sampling affect enabled fraction/network entropy.'),
 'aware_log': ('Recording-system activity and quality; no direct clinical interpretation.', 'System log volume is instrumentation-dependent, not user activity.'),
}


def unit(f, saved=''):
    if saved: return saved
    if f.endswith('_ms_per_day'): return 'milliseconds/calendar day'
    if f.endswith('_ms') or 'interval_ms' in f: return 'milliseconds'
    if 'per_active_minute' in f: return 'count/observed active recording minute'
    if 'per_active_hour' in f: return 'bursts/observed active recording hour'
    if f.endswith('_seconds'): return 'seconds'
    if f.endswith('_km'): return 'kilometers'
    if f.endswith('_power_ma'): return 'mA (sensor metadata)'
    if 'lux' in f: return 'lux'
    if f.startswith('percent_') or f.endswith('_percent'): return 'percent'
    if any(t in f for t in ['fraction','ratio','share','_cv','jaccard']): return 'dimensionless'
    if any(t in f for t in ['entropy','diversity']) and not f.endswith('_ratio'): return 'bits for shared log2 entropy; catalog-only variants require verification'
    if 'hour' in f and 'count' not in f: return 'hours'
    if 'minute' in f and 'count' not in f: return 'minutes'
    if 'days' in f: return 'observed days'
    if any(t in f for t in ['count','rows','observations','unique_','errors','removed']): return 'count'
    if 'pressure' in f: return 'pressure sensor units (hPa assumed in elevation conversion)'
    if f.endswith('_m'): return 'meters (estimated)'
    if 'jerk' in f: return 'input acceleration units/second; calibration not verified'
    if 'accelerometer' in f: return 'input acceleration units; calibration not verified'
    return 'not verified; see calculation and source definition'


def interpretation(f, definition, mod):
    if 'cv' in f: direct = 'Higher means larger SD relative to the mean of the measured distribution; lower means less relative dispersion.'
    elif any(t in f for t in ['_sd','_iqr','_mad','spread']): direct = 'Higher means greater dispersion of the measured quantity; lower means a narrower distribution.'
    elif 'slope' in f: direct = 'Positive means the observed daily timing summary increases over calendar time; negative means it decreases. Gaps remain unobserved.'
    elif 'word_completion' in f and any(t in f for t in ['_median_ms','_mean_ms','_p10_ms','_p90_ms']): direct = 'Higher means more elapsed time between the algorithm-defined observable word-start and trailing-space states; lower means less. True typing duration is not established.'
    elif mod=='keyboard' and any(t in f for t in ['interval','pause','recovery','duration']): direct = 'Higher means longer or more dispersed/countable snapshot-defined intervals/episodes according to the definition; lower means the reverse. This does not establish slower/faster keystrokes.'
    elif 'fraction' in f or 'percent' in f or 'share' in f: direct = 'Higher means a greater proportion of eligible recorded observations meets the stated condition; lower means a smaller proportion, not necessarily less time in that state.'
    elif 'diversity' in f or 'entropy' in f: direct = 'Higher means a broader/more even distribution of recorded categories; lower means more concentration, subject to the specified entropy/ratio definition.'
    elif 'per_active' in f: direct = 'Higher means more qualifying events per observed active recording time; lower means fewer. Recording coverage is part of the denominator.'
    elif 'count' in f or 'rows' in f or 'unique' in f: direct = 'Higher means more qualifying recorded events/categories/bins in the stated window; lower means fewer. Equal observation exposure is required for a behavioral comparison.'
    elif 'distance' in f: direct = 'Higher means greater summed displacement between recorded phone locations; lower means less recorded displacement.'
    else: direct = 'Higher/lower refers to the measured quantity in the definition; no universal better/worse clinical direction is established.'
    possible, limits = FAMILY_NOTES.get(mod, ('Clinical meaning not established; verify this source-specific measure before interpretation.', 'Definition/units and sampling artifacts require source-specific clarification.'))
    if f.startswith('word_completion') or f=='high_confidence_fraction': limits += ' '+WORD_ISSUES
    return direct, possible, limits


# Code evidence: literal output expressions are stored alongside readable definitions.
def code_index():
    patterns = ['*extract*.py', 'keyboard_deep_dive.py', WC, 'keyboard_afternoon_interval_mechanism_audit.py', 'build_plugin_activity_movement_dictionary.py', 'full_model_pca.py']
    paths = set()
    for pat in patterns: paths.update(ROOT.glob(pat))
    paths.update((ROOT/'supplemental_modalities').glob('*.py'))
    index=defaultdict(list)
    for p in sorted(paths):
        rel=str(p.relative_to(ROOT)); text=remember(rel).read_text(); tree=ast.parse(text)
        parents={child:parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        def evidence(node, val):
            parent=node; func='module'
            while parent in parents:
                parent=parents[parent]
                if isinstance(parent,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    func=parent.name; break
            return {'path':rel,'line':node.lineno,'function':func,'expression':ast.get_source_segment(text,val) or ast.unparse(val)}
        for node in ast.walk(tree):
            if isinstance(node,ast.Dict):
                for key,val in zip(node.keys,node.values):
                    if isinstance(key,ast.Constant) and isinstance(key.value,str) and '_' in key.value:
                        index[key.value].append(evidence(node,val))
            if isinstance(node,ast.Assign):
                for target in node.targets:
                    if isinstance(target,ast.Subscript) and isinstance(target.slice,ast.Constant) and isinstance(target.slice.value,str):
                        index[target.slice.value].append(evidence(node,node.value))
    return index


def preferred_code(path, f):
    if path.endswith('.py'): return path
    if 'word_completion_timing' in path: return WC
    if 'keyboard_deep_dive' in path: return DEEP
    if 'phase1_features' in path: return 'extract_phase1a_screen_app_log_features.py' if modality(f) in {'screen','applications_foreground','aware_log'} else 'extract_phase1b_interaction_activity_features.py'
    if 'supplemental' in path: return 'supplemental_modalities/extract_phase4_24h_t1.py'
    if 'accelerometer_' in path and 'catalog' in path: return 'extract_accelerometer_plugin_event_day_pilot.py'
    mod=modality(f)
    return {'barometer':'phase2_extract_barometer_adjusted_first_available_7d_selected_features.py','significant':'phase2_extract_significant_adjusted_first_available_7d_selected_features.py','sensor_linear_accelerometer':'phase2_extract_sensor_linear_accelerometer_adjusted_first_available_7d_selected_features.py'}.get(mod,SHARED)


def code_evidence(idx, f, path):
    f=base_feature(f); pref=preferred_code(path,f)
    if f.startswith('acc_median_'):
        return 'full_model_pca.py:78; full_model_pca.py:109', 'Median across eligible fully-contained device-days; primary excludes multi-device days. mean_sensitivity uses mean under the same acc_median_ column name; best-device sensitivity selects by valid minutes then numeric rows.', 'aggregation code verified; median/mean alternatives must retain variant label'
    matches=[x for x in idx.get(f,[]) if x['path']==pref]
    if not matches and f.startswith('supplemental_t1_'): matches=[x for x in idx.get(f.removeprefix('supplemental_t1_'),[]) if 'supplemental' in x['path']]
    # Dynamic circadian keys are implemented in a shared loop, not literal names.
    if not matches and pref==DEEP and re.match(r'keyboard_\d\d_\d\d_',f):
        return f'{DEEP}:244; {DEEP}:133', 'group_features: local_timestamp(later_snapshot).hour//6; median or Q75-Q25 of 0<dt<=30000 ms within same device/package', 'verified dynamic circadian calculation'
    if not matches and f.startswith('word_completion'):
        return f'{WC}:43; {WC}:106; {WC}:234', 'stats(high-confidence observable durations): mean, median, sample SD(ddof=1), Q75-Q25, median(abs(x-median(x))), P10/P90, SD/mean; extract() defines eligible durations. Daily median slope uses polyfit(calendar_day, daily_median,1); weekly count SD groups by ISO week number without year.', 'dynamic summary verified; v1 eligibility/provenance unresolved'
    if not matches:
        return '', '', 'catalog definition only; exact historical calculation not verified'
    # Keep all non-placeholder expressions; do not pretend literal references alone prove historical provenance.
    nonempty=[x for x in matches if x['expression'] not in {'pd.NA','0','0.0','float("nan")'}]
    matches=nonempty or matches
    refs='; '.join(dict.fromkeys(f"{x['path']}:{x['line']} ({x['function']})" for x in matches))
    expr='; '.join(dict.fromkeys(x['expression'].replace('\n',' ') for x in matches))
    return refs,expr,'current code expression located; historical run equivalence not independently verified'


def dictionary(associations, idx):
    entries=[]
    catalogs=[Path('phase2_selected_features.csv')]
    for p in (ROOT/'output/analysis_candidates').rglob('*.csv'):
        if any(t in p.name for t in ('feature_metadata','feature_catalog','feature_plan','feature_dictionary','feature_inventory','feature_config')):
            catalogs.append(p.relative_to(ROOT))
    seen_catalog=set()
    def add(f,path,line,original='',mod='',fam='',window='',saved_unit='',saved_meaning='',state='cataloged feature'):
        mod=mod or modality(f); refs,expr,verification=code_evidence(idx,f,path)
        direct,possible,limits=interpretation(base_feature(f),original,mod)
        if saved_meaning: possible=saved_meaning+' [source interpretation, hypothesis only]. '+possible
        definition=original if original and not original.startswith('See ') else readable_definition(base_feature(f),mod)
        entries.append({'feature_definition_id':f'FD{len(entries)+1:05d}', 'exact_feature_name':f,
                        'feature_version':path+':'+str(line), 'source_modality':mod,'feature_family':fam or mod,
                        'direct_measurement_and_formula':definition, 'units':unit(base_feature(f),saved_unit),
                        'verified_calculation_clarification':readable_definition(base_feature(f),mod),
                        'observation_window':window or window_for_catalog(path),
                        'higher_and_lower_values_mean':direct,'possible_behavioral_clinical_interpretation':possible,
                        'measurement_limitations':limits,'definition_verification':verification,
                        'implementation_source_lines':refs,'implementation_expression':expr,
                        'source_catalog_file':path,'source_catalog_csv_line':line,
                        'original_definition_verbatim':original,'feature_status':state,
                        'feature_transformation':('Late minus Early of this base feature; observed-day first14/last14 summaries when explicitly named.' if f.endswith('_delta') else 'Early clinical-half value' if f.endswith('_T1') else 'Late clinical-half value' if f.endswith('_T2') else 'No name-level endpoint transformation; consult source version/window.'),
                        'association_status':'not yet linked'})
    for p in sorted(set(catalogs)):
        rel=str(p)
        for n,r in enumerate(read(rel),2):
            f=r.get('feature_name','')
            if not f: continue
            original=next((r[x] for x in ['feature_definition','definition','aggregation_logic_plain_english','short_description'] if r.get(x)), '')
            add(f,rel,n,original,r.get('source_table',r.get('source_modality',r.get('modality',r.get('source','')))),r.get('feature_family',r.get('feature_group',r.get('group',''))),
                r.get('source_window','') or ' / '.join(str(r[x]) for x in ['window_class','acquisition_window_class','window_level'] if r.get(x)),r.get('expected_unit',''),r.get('interpretation',r.get('behavioral_interpretation','')),r.get('extraction_status','cataloged; catalog inclusion alone does not prove extraction'))
            entries[-1]['original_catalog_metadata_json']=json.dumps(r,ensure_ascii=False,sort_keys=True)
            seen_catalog.add((f,rel))
    # Saved headers are used only for feature names, never patient values/text.
    header_sources=[(W+'word_completion_window_features.csv','window'),(W+'word_completion_daily_features.csv','daily'),(K+'keyboard_deep_dive_window_features.csv','window')]
    metadata={'Subject_ID_D','window_name','window_start_ms','window_end_ms','window_start_local','window_end_local','local_date','window_status'}
    for rel,level in header_sources:
        with remember(rel).open() as f: cols=next(csv.reader(f))
        for c in cols:
            if c in metadata: continue
            add(c,rel,1,window=WINDOW_HALF+(' Local-day aggregate assigned by completion timestamp.' if level=='daily' else ''),state='saved aggregate '+level+' feature')
    # Preserve source-code output variants (incl. early engineering/QC features not in later banks).
    prefixes=('keyboard_','touch_','screen_','app_','activity_','accelerometer_','barometer_','light_','proximity_','sensor_linear_accelerometer_','significant_','telephony_','bluetooth_','gsm_','location_','message_','aware_log_')
    for f,found in sorted(idx.items()):
        if not f.startswith(prefixes) or any(t in f for t in ['_path','_status','_rule','_method','timestamp','device_id','package_name','feature_name','feature_values','_column','_counter','_conf_vals']): continue
        for path in sorted({x['path'] for x in found}):
            if not any(x['function'].startswith(('compute','analyze','finish','extract')) or x['function']=='main' for x in found if x['path']==path): continue
            if any(x['exact_feature_name']==f and path in x['implementation_source_lines'] for x in entries): continue
            add(f,path,next(x['line'] for x in found if x['path']==path),state='code-defined output; saved use not established by code alone')
    known={x['exact_feature_name'] for x in entries}
    for a in associations:
        f=a['feature']
        if f not in known:
            add(f,a['source_file'],a['source_csv_line'],window=a['observation_window'],state='feature appears in saved cognitive association');known.add(f)
    linked=defaultdict(list)
    for a in associations: linked[base_feature(a['feature'])].append(a)
    for e in entries:
        rows=linked.get(base_feature(e['exact_feature_name']),[])
        e['association_status']=f'{len(rows)} saved estimates for this name/base name; consult version link before comparison' if rows else 'No direct feature-cognition result located; not evidence of no effect'
    return entries


def readable_definition(f, mod):
    if f.startswith('word_completion'):
        if 'rate_per_active_minute' in f: return 'Algorithm high-confidence completion count / sum within-device/app burst spans in minutes; bursts split at gaps >30s. Not true words per typing minute.'
        if 'daily_median_slope' in f: return 'OLS polyfit slope of nonmissing daily completion-time medians against elapsed calendar days, >=3 observed daily values; no weighting for word counts.'
        if 'daily_median_sd' in f: return 'Sample SD (ddof=1) of nonmissing daily completion-time medians; observed days equally weighted.'
        if 'weekly_count_sd' in f: return 'Sample SD of weekly sums of accepted completion counts, grouping ISO week NUMBER only; years not separated and unobserved weeks absent. Count variability, not timing variability.'
        if 'week_count' in f: return 'Number of ISO week-number groups in observed daily rows; no requirement for accepted words in each week and no year key.'
        if 'count' in f or f.endswith('days'): return 'Count of algorithm-identified completions/observed days in the named quality class; zero counts in no-observation windows are instrumentation counts, not zero behavior.'
        return 'Named summary of snapshot completion durations (end timestamp minus first observable non-space state timestamp), selected by the v1 quality flags. Timing statistics in ms; CV is sample SD/mean. Circadian bins use completion hour: night 00-06, morning 06-12, afternoon 12-18, evening 18-24 (Asia/Jerusalem).'
    if f=='high_confidence_fraction': return 'Number classified high_confidence_observable / all algorithm-identified completion candidates. Denominator does not include unobserved real words; not a validated accuracy or recall estimate.'
    if f.startswith('keyboard_'):
        if 'word_completion' in f: return 'Legacy literal-space heuristic: start at observed nonempty non-space text; reset at before_text ending in space or gap >30s; finish when current_text ends in space and before_text does not. Median duration/count; no continuity/append/first-character validation.'
        if 'inter_event_interval' in f or 'valid_interval' in f: return 'Named summary/count of positive intervals <=30000ms between consecutive canonical snapshots in the same device/package. Circadian assignment by later snapshot local hour; SD ddof=1, IQR=Q75-Q25, MAD=median absolute deviation, CV=SD/mean, spread=P95-P05.'
        if 'deletion' in f or 'correction' in f: return 'Length-decrease event when current length < before length OR previous current length. Pre/post pause are adjacent timestamp differences within 30s; recovery is first later text growth within 30s. Deletion rate=count/canonical events. Deletion-burst grouping uses collected timestamps without global resort across groups (technical caveat).'
        if 'active_minutes' in f or 'burst' in f or 'fragmentation' in f: return 'Device/package bursts split by gaps >30000ms; duration=end-start, active minutes=sum durations/60000; fragmentation=burst count/(active_minutes/60). Singleton bursts have duration zero.'
        if 'long_pause' in f: return 'Count of accepted consecutive-snapshot gaps >2000ms and <=30000ms, or count divided by valid interval count for rate.'
    return 'Exact output expression and source-specific window are provided where located. No independent behavioral meaning is assigned from the feature name alone.'


def window_for_catalog(path):
    if 'phase1_features' in path: return 'Phase1 Early/Late extraction windows; see source cohort window table; not interchangeable with clinical midpoint phases.'
    if '10day' in path: return 'Historical first-available 10-day post-assessment window; adjusted/fallback modalities may differ; source catalog window fields govern.'
    if 'phase111' in path: return 'Full T1-T2 interval; historical source window labels may describe earlier extraction provenance.'
    if any(x in path for x in ['phase11','phase12','median_span','full_model_pca']): return WINDOW_HALF+' Catalog may retain older window_class labels; PCA variants may aggregate event days.'
    if 'accelerometer' in path: return 'Plugin-selected local calendar device-days; later patient aggregation is a distinct version. Not continuous whole-interval coverage.'
    if 'supplemental' in path or 'phase4_' in path: return 'T1 24-hour primary/fallback window; adjusted 7-day modalities remain separately labeled.'
    if 'keyboard_deep_dive' in path: return WINDOW_HALF
    return 'Multiple historical windows; use source protocol/status window metadata. No fixed universal patient window inferred.'


def normalize_associations():
    # Start with every historical master row, including repeated and superseded estimates.
    rows=read(MASTER); index={}; cache={}
    for r in rows:
        r['historical_master_row_id']=r.pop('master_row_id')
        r['historical_master_p']=r.get('p','');r['historical_master_q']=r.get('q','')
        key=(r['source_file'],str(r['source_csv_line']),r['coefficient_field'])
        assert key not in index; index[key]=r
    def ingest(path, coefficient, pfield='', qfield='', nfield='n', low='', high='', scope='', featurefield='feature_name', outfield='outcome', feature='', outcome='', est='Spearman rho', role='', adjustment='', context='', predicate=None):
        src=read(path);cache[path]=src
        for line,s in enumerate(src,2):
            if predicate and not predicate(s): continue
            key=(path,str(line),coefficient)
            r=index.get(key)
            if r is None:
                r={'historical_master_row_id':'','source_file':path,'source_csv_line':str(line),'coefficient_field':coefficient};rows.append(r);index[key]=r
            r.update({'feature':feature or s.get(featurefield,''),'outcome':outcome or s.get(outfield,''),
                      'estimate':s.get(coefficient,''),'estimate_type':est,'p':s.get(pfield,'') if pfield else '',
                      'q':s.get(qfield,'') if qfield else '', 'n':s.get(nfield,'') if nfield else '',
                      'ci_low':s.get(low,'') if low else '', 'ci_high':s.get(high,'') if high else '',
                      'p_source_field':pfield,'q_source_field':qfield,'n_source_field':nfield,
                      'ci_low_source_field':low,'ci_high_source_field':high,
                      'source_scope':s.get('scope',scope), 'adjustment':s.get('adjustment',adjustment),
                      'covariates':s.get('covariates',adjustment),
                      'scenario':s.get('scenario',s.get('window_design',s.get('analysis',''))),
                      'source_record_json':json.dumps(s,ensure_ascii=False,sort_keys=True),
                      'evidence_role':role or r.get('evidence_role','exploratory saved result'),
                      'testing_context':context or r.get('testing_context',''),
                      'fdr_scope':context if qfield else 'No matching q-value saved for this estimator',
                      'statistics_policy':'Exact strings copied from original saved output; no inference recomputed.'})
    d=K+'signal_discovery/signal_feature_associations.csv'
    ingest(d,'spearman_rho','spearman_p','fdr_q',low='bootstrap_ci_low',high='bootstrap_ci_high',context='BH separately within T1 and T2_minus_T1: 34 features x 6 outcomes = 204 tests per scope.',role='original comprehensive discovery screen')
    ingest(d,'partial_spearman_rho','partial_spearman_p',nfield='partial_n',adjustment='age; sex; education',role='demographic adjustment of same screen')
    d=K+'thirds_sensitivity/third_associations.csv'
    ingest(d,'spearman_rho','spearman_p','fdr_q',low='bootstrap_ci_low',high='bootstrap_ci_high',scope='delta',context='BH over 270 finite unadjusted tests (34 features x 8 outcomes planned); >=7 active days in both thirds.',role='historical unadjusted thirds sensitivity')
    ingest(d,'partial_spearman_rho','partial_spearman_p',nfield='partial_n',scope='delta',adjustment='age; sex; education; mean active days; historical raw SQL row count',role='superseded historical raw-row-adjusted thirds sensitivity')
    d=K+'thirds_sensitivity_corrected_v2/corrected_coverage_adjusted_associations.csv'
    ingest(d,'partial_spearman_rho_corrected','partial_spearman_p_corrected','fdr_q_corrected','n_corrected','bootstrap_ci_low_corrected','bootstrap_ci_high_corrected',scope='delta',adjustment='age; sex; education; mean active days; mean canonical distinct observations',context='BH over 270 finite tests from 272 planned; canonical coverage adjustment.',role='corrected exploratory thirds sensitivity')
    ingest(K+'thirds_sensitivity/third_vs_midpoint_comparison_same_patients.csv','rho','p','fdr_q_within_design',scope='delta',context='BH within each 40-test design; selected five features x eight outcomes.',role='same-patient restricted window sensitivity; not replication')
    ingest(K+'signal_validation/validation_adjusted_associations.csv','partial_rho','partial_p','fdr_q_within_adjustment',low='bootstrap_ci_low',high='bootstrap_ci_high',scope='delta',context='BH within six selected associations per adjustment set; post-selection, not 204-test discovery FDR.',role='selected-signal technical/demographic sensitivity')
    ingest(K+'signal_validation/validation_original_associations.csv','rho','p','fdr_q',low='ci_low',high='ci_high',scope='delta',context='BH within six already selected associations; not independent discovery.',role='selected-signal recomputation')
    for file in ['t2_reliability_signal_sensitivity.csv','t2_reliability_comparable_periods.csv']:
        ingest(K+'t2_reliability_investigation/'+file,'rho','p','fdr_q',low='ci_low',high='ci_high',scope='delta',context='BH within scenario over estimable members of six selected signals; nonestimable rows retained.',role='coverage/observed-period sensitivity')
    ingest(K+'signal_validation/validation_summary.csv','rho','permutation_p','permutation_fdr_q',scope='delta',context='2000 permutations; BH over six selected signals. Estimate is observed rho, not a second independent estimate.',role='selected-signal permutation sensitivity')
    ingest(K+'signal_validation/validation_summary.csv','outlier_filtered_rho',nfield='outlier_filtered_n',scope='delta',role='selected-signal outlier sensitivity')
    ingest(W+'word_completion_cognitive_associations.csv','spearman_rho','spearman_p','fdr_q',low='bootstrap_ci_low',high='bootstrap_ci_high',context='BH separately over 168 finite T1 and 102 finite change tests in saved v1; not 256 total.',role='new exploratory word-completion v1 screen; technical clarification required')
    ingest(W+'word_completion_recording_adjusted_associations.csv','partial_spearman_rho','partial_spearman_p',role='exploratory v1 recording adjustment; no q/CI saved')
    ingest(W+'word_completion_vs_snapshot_iei_matched.csv','spearman_rho','spearman_p',scope='delta',role='restricted shared source cohort, not identical complete cases: word n=27 versus IEI n=28')
    ingest(K+'afternoon_interval_mechanism_audit_20261020/exploratory_adjusted_associations.csv','partial_spearman_rho','p',scope='delta',feature='keyboard_12_18_median_inter_event_interval_ms',outcome='executive_function',est='partial Spearman rho (unadjusted row is Spearman)',role='28-patient technical-mechanism sensitivity')
    ingest(K+'afternoon_interval_mechanism_audit_20261020/technical_factor_associations.csv','spearman_rho','p',low='bootstrap_ci_low',high='bootstrap_ci_high',scope='delta',featurefield='technical_factor',predicate=lambda s: s['outcome']=='ef_delta',role='technical factor vs cognition; potential measurement confounder')
    ingest('output/analysis_candidates/keyboard_two_feature_median_timespan/keyboard_two_feature_associations.csv','spearman_rho','spearman_p_value',nfield='n_observed',outfield='outcome_column',role='legacy two-feature screen; extreme feature values removed in source')
    ingest('output/analysis_candidates/keyboard_two_feature_median_timespan/keyboard_two_feature_associations.csv','linear_slope_outcome_per_feature_unit',nfield='n_observed',outfield='outcome_column',est='Univariate fitted slope (cognitive score / feature unit); not cross-validated prediction',role='legacy same-data fitted line; slope p/CI not saved')
    ingest('output/analysis_candidates/keyboard_t1_t2_delta_pca/keyboard_t1_t2_delta_summary.csv','spearman_rho_feature_delta_vs_global_cognitive_delta','spearman_p_value_feature_delta_vs_global_cognitive_delta',nfield='n_delta_cognitive_pairs',scope='delta',outcome='global',role='legacy delta summary; same-cohort re-expression')
    path='output/analysis_candidates/phase11_t1_baseline/clinical_tables_baseline_severity/phase11_baseline_severity_all_features.csv'
    ingest(path,'effect_size_cliffs_delta_higher_minus_lower','p_value','q_value_fdr_bh','n_overall',scope='T1',outcome='global_T1_median_group',est="Cliff's delta, feature values in higher-minus-lower Global T1 group",context='Mann-Whitney; BH within 61-feature median-split table.',role='exploratory cognitive-group feature contrast, not correlation')
    clinical='output/analysis_candidates/phase11_t1_baseline/clinical_tables_baseline_severity/phase11_baseline_severity_clinical_table1.csv'
    for label,field in [('Usable digital features','usable_feature_count_all_available'),('Patient-level feature missingness','baseline_feature_missing_fraction'),('Patient-level table coverage','baseline_table_coverage_fraction')]:
        ingest(clinical,'effect_size_cliffs_delta_higher_minus_lower','p_value','q_value_fdr_bh','n_overall',scope='T1',feature=field,outcome='global_T1_median_group',est="Cliff's delta, higher-minus-lower Global T1 group",context='Mann-Whitney; BH within clinical Table 1 nonmissing tests (includes demographics/cognitive scores), not the separate 61-feature family.',role='recording-coverage measure vs cognitive median group',predicate=lambda s,label=label:s['variable']==label)
    path='output/analysis_candidates/phase_exploratory_empirical_findings_1_4/exploratory_empirical_1_4_feature_comparison.csv'
    ingest(path,'extreme_effect_cliffs_delta_highest_minus_lowest','extreme_p_value','extreme_q_value',nfield='',scope='T1',outcome='global_T1_extreme_groups',est="Cliff's delta, highest-minus-lowest Global T1 groups",context='Mann-Whitney; BH within 61-feature extreme-group table.',role='extreme cognitive-group sensitivity, outcome-selected tails')
    for r in rows:
        if r['source_file']==path:
            s=json.loads(r['source_record_json']); r['n']=str(int(s['n_lowest_20'])+int(s['n_highest_20']));r['n_source_field']='n_lowest_20+n_highest_20 (metadata count sum only)'
    path='output/analysis_candidates/supplemental_modalities/phase4_24h_t1/phase4_supplemental_feature_review.csv'
    for c,est in [('exploratory_spearman_global_T1','Spearman rho'),('exploratory_pearson_global_T1','Pearson r')]:
        ingest(path,c,nfield='paired_global_T1_n',scope='T1',outcome='global_T1',est=est,role='supplemental 24h engineering review; missing p/q/CI')
    # Preserve unrecognized inherited metadata and resolve source scope/window explicitly.
    for i,r in enumerate(rows,1):
        r['register_row_id']=f'A{i:05d}'
        path=r['source_file']; sc=r.get('source_scope',''); outcome=r.get('outcome','')
        if not outcome: raise ValueError(f'Unmapped outcome {path}:{r["source_csv_line"]}')
        delta=('delta' in sc.lower() or 't2_minus' in sc.lower() or outcome.endswith('_delta') or any(t in path for t in ['thirds_','t2_reliability','signal_validation','mechanism_audit','keyboard_t1_t2']))
        r['outcome_timepoint']='T2-T1' if delta else 'T1'
        if 'two_feature' in path: r['outcome_timepoint']='T2-T1' if outcome.endswith('_delta') else 'T1'
        r['cognitive_outcome_normalized']=outcome_name(outcome)
        r['feature_base_name']=base_feature(r['feature'])
        r['feature_modality']=modality(r['feature'])
        r['feature_version']='word_completion_timing_v1' if path.startswith(W) and r['feature']!='snapshot_IEI_delta' else ('keyboard_deep_dive_v1' if path.startswith(K) else 'legacy_shared_extraction' if r['feature_modality']=='keyboard' else 'source_specific')
        r['observation_window']=WINDOW_THIRD if ('third' in path and r.get('scenario')!='50_50_midpoint_same_patients') else (WINDOW_HALF if r['feature_modality']=='keyboard' or 'phase11_' in path or 'empirical_findings' in path else 'T1 24-hour primary/fallback supplemental window')
        if r.get('scenario') in {'first14_observed_days','last14_observed_days'}: r['observation_window']+=' Features summarized from '+r['scenario']+' within each clinical half; these are not adjacent calendar fortnights.'
        r['analysis_phase']=r.get('analysis_phase') or ('Word Completion Timing v1' if path.startswith(W) else Path(path).parent.name)
        r['effect_direction']='positive' if number(r['estimate']) is not None and number(r['estimate'])>0 else 'negative' if number(r['estimate']) is not None and number(r['estimate'])<0 else 'zero' if number(r['estimate'])==0 else 'not estimable'
        r['p_lt_0_05']=flag(r['p'],.05);r['q_lt_0_05']=flag(r['q'],.05);r['q_le_0_20']=flag(r['q'],.20,True)
        r['missing_statistics']='; '.join(c for c in ['estimate','p','q','n','ci_low','ci_high'] if not finite(r.get(c))) or 'none'
        r['is_superseded']='yes' if 'superseded historical' in r['evidence_role'] else 'no'
        r['unique_candidate_key']=' | '.join([r['feature_version'],r['feature_base_name'],r['cognitive_outcome_normalized'],r['outcome_timepoint']])
        r['independence_note']='Same project/cohort; different windows, estimators, adjustments and selected subsets are repeated evidence, not independent discoveries.'
        r['technical_clarification']=WORD_ISSUES if r['feature_version']=='word_completion_timing_v1' else ('Only current code verified; historical provenance/units require clarification; p/q/CI unavailable.' if 'supplemental' in path else '')
        r['observed_relationship']=relationship(r)
    return rows


def relationship(r):
    direction=r['effect_direction']; task=r['outcome_timepoint']; f=r['feature']; o=r['cognitive_outcome_normalized'].replace('_',' ')
    if direction=='not estimable': return 'Association was not estimable or effect size not saved; no direction can be inferred.'
    if direction=='zero': return 'Saved estimate is zero; this does not prove absence of association.'
    if "Cliff" in r['estimate_type']:
        return f"{f} tended to be {'higher' if direction=='positive' else 'lower'} in the higher {o} score group. Group contrast, not a correlation or causal effect."
    x='Larger Late-minus-Early change in '+f if task=='T2-T1' else 'Higher observed '+f
    y=(('more positive cognitive change (greater improvement or less decline)' if direction=='positive' else 'more negative cognitive change (greater decline or less improvement)') if task=='T2-T1' else ('higher cognitive score' if direction=='positive' else 'lower cognitive score'))
    return f'{x} was associated with {y} for {o}. NeuroTrax T2-T1 coding: positive=score increase. Association is observational; higher digital values are not inherently healthier.'


def evidence_links(rows):
    groups=defaultdict(list)
    for r in rows: groups[r['unique_candidate_key']].append(r)
    reliability=read(K+'signal_validation/validation_reliability.csv')
    robustness=read(K+'signal_validation/validation_summary.csv')
    road=[]
    for key,g in groups.items():
        f=g[0]['feature_base_name']; outcome=g[0]['cognitive_outcome_normalized']; word=g[0]['feature_version']=='word_completion_timing_v1'
        rel=[x for x in reliability if x['feature_name']==f]
        rob=[x for x in robustness if x['feature_name']==f and outcome_name(x['outcome'])==outcome and g[0]['outcome_timepoint']=='T2-T1']
        reltext='; '.join(f"{x['window_name']} ICC(2,1)={x['icc_2_1_absolute_agreement']}, n={x['n_patients']}, {x['method']}" for x in rel) or 'Not evaluated in a saved reliability output for this feature version; absence is not a failed test.'
        robtext='; '.join(f"LOO rho {x['loo_min_rho']} to {x['loo_max_rho']}, sign consistency={x['loo_sign_consistency']}, outlier-filtered rho={x['outlier_filtered_rho']} n={x['outlier_filtered_n']}" for x in rob) or 'No matching saved LOO/outlier evidence.'
        adjusted=[r for r in g if 'corrected_v2' in r['source_file'] or 'recording_adjusted' in r['source_file'] or 'mechanism_audit' in r['source_file'] or (r.get('covariates','') and any(t in r['covariates'] for t in ['active_days','snapshot','device']))]
        adjtext='; '.join(f"{r['register_row_id']}: effect={r['estimate'] or 'NA'}, p={r['p'] or 'NA'}, q={r['q'] or 'NA'}, n={r['n']}, {r.get('adjustment') or r.get('scenario') or 'recording adjusted'}" for r in adjusted) or 'No saved technical/coverage adjustment located.'
        sens=[r for r in g if any(t in r['source_file'] for t in ['thirds','t2_reliability']) and r['is_superseded']!='yes']
        senstext='; '.join(f"{r['register_row_id']}: {r.get('scenario') or r.get('source_scope')}, effect={r['estimate'] or 'NA'}, p={r['p'] or 'NA'}, q={r['q'] or 'NA'}, n={r['n']}" for r in sens) or 'No matching saved window/coverage sensitivity.'
        original=[r for r in g if r['evidence_role']=='original comprehensive discovery screen' and r['coefficient_field']=='spearman_rho']
        word_original=[r for r in g if r['source_file']==W+'word_completion_cognitive_associations.csv']
        eligible=[r for r in g if finite(r['p']) and r['is_superseded']!='yes']
        # Representative preference is source design, not best post-hoc p across variants.
        rep=(original or word_original or sorted(eligible,key=lambda r:number(r['p'])) or g)[0]
        nominal=any(r['p_lt_0_05']=='yes' for r in g)
        weakened=bool(original and original[0]['p_lt_0_05']=='yes' and any(number(r['p']) is not None and number(r['p'])>=.05 and finite(r['estimate']) and abs(number(r['estimate']))<abs(number(original[0]['estimate'])) for r in adjusted))
        promising=any(r['q_le_0_20']=='yes' and finite(r['n']) and number(r['n'])>=20 for r in original)
        if word or not any(finite(r['p']) for r in g): category='4. Requires technical clarification'
        elif weakened: category='3. Weakened by recording/coverage adjustment'
        elif promising: category='1. Promising exploratory POC candidate'
        elif nominal: category='2. Nominal finding / restricted FDR only'
        else: category='5. Negative or unsupported association'
        memberships=[]
        if promising: memberships.append('1. Promising exploratory POC candidate (original selected screen; unvalidated)')
        if any(r['p_lt_0_05']=='yes' and r['q_lt_0_05']!='yes' for r in g): memberships.append('2. Nominal p<.05 without matching q<.05')
        if weakened: memberships.append('3. Weakened by recording/coverage adjustment')
        if word or not any(finite(r['p']) for r in g): memberships.append('4. Requires technical clarification')
        if not nominal: memberships.append('5. Negative or unsupported associations; missing tests distinguished')
        step=('Repair and freeze sequence continuity/quality classification; verify saved password filtering and provenance; validate against labeled snapshot sequences; then assess recording-density/word-length/app effects before any cognitive retesting.' if word else
              'Validate sampling cadence and device/app comparability with an independent recording-quality cohort; prespecify coverage and baseline cognition adjustment, then test the frozen hypothesis in new patients.' if weakened or promising else
              'Verify calibration, units and feature-level estimand; retain as feasibility evidence until a prespecified independent dataset supports inference.' if not eligible else
              'Prespecify this feature/outcome and observation window in an independent cohort with technical covariates and multiplicity control; do not tune thresholds on these outcomes.' if nominal else
              'Do not promote from current evidence; improve coverage/reliability and justify an independently prespecified hypothesis before further testing.')
        for r in g:
            r.update({'candidate_category':category,'promising_exploratory_flag':'yes' if promising else 'no','weakened_by_adjustment':'yes' if weakened else 'not demonstrated / untested',
                      'candidate_group_memberships':'; '.join(memberships),
                      'reliability_evidence':reltext if not word else 'Not assessed: daily SD/trends are variability descriptors, not test-retest reliability.',
                      'robustness_evidence':robtext,'technical_adjustment_evidence':adjtext,'sensitivity_evidence':senstext,
                      'validation_status':'Exploratory; no independent replication or clinical validation established.',
                      'next_validation_step':step,'saved_estimate_count_for_candidate':str(len(g))})
        road.append({'unique_candidate_key':key,'category':category,'feature_name':rep['feature'],'outcome':outcome,'timepoint':rep['outcome_timepoint'],
                     'candidate_group_memberships':'; '.join(memberships),
                     'representative_row_id':rep['register_row_id'],'representative_p':rep['p'],'representative_q':rep['q'],'representative_effect':rep['estimate'],'representative_n':rep['n'],
                     'representative_selection':'Original comprehensive unadjusted discovery preferred; otherwise smallest saved eligible p for descriptive triage only. Not an unbiased discovery ranking.',
                     'promising_exploratory_flag':'yes' if promising else 'no','nominal_any':'yes' if nominal else 'no',
                     'saved_estimate_count':len(g),'independent_replications_established':0,
                     'technical_adjustment_evidence':adjtext,'reliability_evidence':reltext,'sensitivity_evidence':senstext,'next_validation_step':step})
    return road


def main():
    STAGING.mkdir(parents=True,exist_ok=True)
    associations=normalize_associations()
    idx=code_index(); definitions=dictionary(associations,idx)
    byname=defaultdict(list)
    for d in definitions: byname[base_feature(d['exact_feature_name'])].append(d)
    for r in associations:
        defs=byname[r['feature_base_name']]
        if r['feature_version']=='word_completion_timing_v1': chosen=[d for d in defs if d['source_catalog_file'].startswith(W)]
        elif r['feature_version']=='keyboard_deep_dive_v1': chosen=[d for d in defs if d['source_catalog_file'].startswith(K) and not d['source_catalog_file'].startswith(W)]
        else: chosen=[d for d in defs if not d['source_catalog_file'].startswith(W)]
        chosen=chosen or defs
        r['feature_definition_ids']='; '.join(d['feature_definition_id'] for d in chosen)
        r['feature_units']=chosen[0]['units']
        r['practical_meaning']=chosen[0]['higher_and_lower_values_mean']
        r['possible_clinical_interpretation']=chosen[0]['possible_behavioral_clinical_interpretation']
        r['measurement_limitations']=chosen[0]['measurement_limitations']
    roadmap=evidence_links(associations)
    # Supervisor table chooses one candidate per named question, with linked repeats.
    selectors=[('keyboard_12_18_median_inter_event_interval_ms','executive_function','T2-T1','keyboard_deep_dive_v1'),
               ('keyboard_median_correction_recovery_time_ms','executive_function','T2-T1','keyboard_deep_dive_v1'),
               ('keyboard_inter_event_interval_cv','executive_function','T2-T1','keyboard_deep_dive_v1'),
               ('keyboard_18_24_median_inter_event_interval_ms','executive_function','T2-T1','keyboard_deep_dive_v1'),
               ('keyboard_06_12_median_inter_event_interval_ms','executive_function','T2-T1','keyboard_deep_dive_v1'),
               ('keyboard_12_18_median_inter_event_interval_ms','attention','T2-T1','keyboard_deep_dive_v1'),
               ('keyboard_06_12_median_inter_event_interval_ms','attention','T2-T1','keyboard_deep_dive_v1'),
               ('keyboard_median_word_completion_time_ms','attention','T1','legacy_shared_extraction'),
               ('word_completion_evening_median_ms','attention','T1','word_completion_timing_v1'),
               ('word_completion_iqr_ms','global','T2-T1','word_completion_timing_v1')]
    supervisor=[]
    byid={r['register_row_id']:r for r in associations}
    for f,o,t,v in selectors:
        key=' | '.join([v,f,o,t]); match=next((c for c in roadmap if c['unique_candidate_key']==key),None)
        if match is None: raise ValueError('Missing supervisor candidate '+key)
        r=byid[match['representative_row_id']]
        supervisor.append(r)
    for mod in ['touch','screen','applications_foreground','plugin_google_activity_recognition']:
        eligible=[r for r in associations if r['source_file'].endswith('phase11_baseline_severity_all_features.csv') and r['feature_modality']==mod and finite(r['p'])]
        supervisor.append(min(eligible,key=lambda r:number(r['p'])))
    compact=[]
    for r in supervisor:
        word=r['feature_version']=='word_completion_timing_v1'
        status=('Technical clarification required; no v1 FDR-positive screen result; adjusted q/CI absent.' if word else
                'Exploratory selected discovery; attenuated in recording/window sensitivities.' if r['promising_exploratory_flag']=='yes' else
                'No evidence in full-cohort discovery; large restricted-cohort estimate is post-hoc.' if r['feature']=='keyboard_06_12_median_inter_event_interval_ms' and r['cognitive_outcome_normalized']=='attention' else
                'Nominal only; no q/CI saved in legacy two-feature source.' if r['feature_version']=='legacy_shared_extraction' else
                'Unsupported in 61-feature cognitive-group screen; not a correlation.')
        limitations=('No inter-snapshot text continuity check; autocorrect/paste ambiguous; password-filter provenance unresolved.' if word else KEY_ISSUES if r['feature_modality']=='keyboard' else FAMILY_NOTES.get(r['feature_modality'],('','No independent clinical validation.'))[1])
        compact.append({'p':r['p'],'q':r['q'],'n':r['n'],'effect':r['estimate'],'effect_type':r['estimate_type'],'ci_low':r['ci_low'],'ci_high':r['ci_high'],
                        'feature':r['feature'],'outcome':r['cognitive_outcome_normalized'],'timepoint':r['outcome_timepoint'],
                        'practical_interpretation':r['observed_relationship'],'validation_status':status,'limitations':limitations,
                        'next_validation_step':r['next_validation_step'],'full_register_row_id':r['register_row_id'],
                        'source':r['source_file']+':'+r['source_csv_line']})
    supervisor=compact
    inventory=[]
    imported={r['source_file'] for r in associations}
    # Enumerate every saved CSV with statistical fields, including excluded composites and copies.
    for p in sorted((ROOT/'output').rglob('*.csv')):
        with p.open(encoding='utf-8-sig',newline='') as f:
            h=next(csv.reader(f),[])
        fields=[x for x in h if any(t in x.lower() for t in ['spearman','pearson','p_value','cliffs','fdr','partial_rho']) or x in ['rho','p','q']]
        if not fields: continue
        rel=str(p.relative_to(ROOT));remember(rel)
        role='included individual digital-feature/cognitive result' if rel in imported else 'supporting/non-direct output; not an individual feature-cognition estimate'
        if any(t in p.name for t in ['top_candidates','validation_summary','clinical_table1','feature_config','corrected_vs_historical']): role='selected summary/copy or demographics; source result already cataloged where applicable'
        if any(t in rel for t in ['full_model_pca','unsupervised']): role='composite PCA/cluster/selection or feature-to-cluster evidence; not individual digital-feature cognitive correlation'
        if any(t in p.name for t in ['technical','reliability_threshold','feature_correlations']): role='technical or reliability support; cognition rows included separately where present'
        inventory.append({'source_file':rel,'statistical_fields':'; '.join(fields),'register_disposition':role,'sha256':INPUTS[rel]})
    tables={
        'complete_feature_dictionary_'+TAG:definitions,
        'complete_feature_cognitive_associations_'+TAG:associations,
        'complete_feature_cognitive_p_lt_0_05_'+TAG:[r for r in associations if r['p_lt_0_05']=='yes'],
        'poc_validation_roadmap_'+TAG:roadmap,
        'supervisor_feature_findings_'+TAG:supervisor,
        'feature_findings_source_inventory_'+TAG:inventory,
    }
    preferred=['register_row_id','p','p_lt_0_05','q','q_lt_0_05','q_le_0_20','n','estimate','estimate_type','ci_low','ci_high','feature','feature_version','cognitive_outcome_normalized','outcome_timepoint','observed_relationship']
    payload={}
    for name,rs in tables.items():
        keys=list(dict.fromkeys(k for r in rs for k in r))
        if name.startswith('complete_feature_cognitive'): keys=[k for k in preferred if k in keys]+[k for k in keys if k not in preferred]
        payload[name]={'columns':keys,'rows':[[r.get(k,'') for k in keys] for r in rs]}
    summary={'dictionary_definition_versions':len(definitions),'distinct_exact_feature_names':len({r['exact_feature_name'] for r in definitions}),
             'association_rows':len(associations),'historical_master_rows_preserved':sum(bool(r['historical_master_row_id']) for r in associations),
             'unique_candidate_groups':len(roadmap),'nominal_p_lt_05_rows':sum(r['p_lt_0_05']=='yes' for r in associations),
             'q_lt_05_rows':sum(r['q_lt_0_05']=='yes' for r in associations),'q_le_20_rows':sum(r['q_le_0_20']=='yes' for r in associations),
             'nonestimable_effect_rows':sum(not finite(r['estimate']) for r in associations),
             'word_cognitive_screen_rows':sum(r['source_file']==W+'word_completion_cognitive_associations.csv' for r in associations),
             'source_files':len(imported),'statistics_recomputed':False,'data_extracted':False,'models_trained':False,
             'source_hashes':INPUTS,'category_counts':dict(Counter(c['category'] for c in roadmap)),
             'promising_original_screen_candidate_groups':sum(c['promising_exploratory_flag']=='yes' for c in roadmap),
             'missing_p_rows':sum(not finite(r['p']) for r in associations),'missing_q_rows':sum(not finite(r['q']) for r in associations)}
    assert summary['historical_master_rows_preserved']==1871
    assert len({r['register_row_id'] for r in associations})==len(associations)
    assert all(r['feature_definition_ids'] for r in associations)
    for p,h in INPUTS.items(): assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h, 'Changed source: '+p
    (STAGING/'tables.json').write_text(json.dumps(payload,ensure_ascii=False))
    (STAGING/'manifest.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!='source_hashes'},indent=2))


if __name__=='__main__': main()
