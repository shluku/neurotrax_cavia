#!/usr/bin/env python3
"""Aggregate-only, source-locked exhibits and catalogs for donor report v0.2.
Never export patient-level measurements, raw text, or identifiers.
No statistical hypothesis tests are rerun by this script.
"""
from pathlib import Path
import csv, collections, html, math, json
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parents[1]
TABLES=OUT/'tables'
FIGURES=OUT/'figures'
TABLES.mkdir(parents=True,exist_ok=True)
FIGURES.mkdir(parents=True,exist_ok=True)
def readcsv(p):
    with (ROOT/p).open('r',encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))
def writecsv(p,cols,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
def num(x):
    try:return float(x)
    except:return float('nan')
def sg(x,d=3):
    v=num(x)
    return ('+' if v>0 else '−' if v<0 else '')+f'{abs(v):.{d}f}' if math.isfinite(v) else 'NA'
EF_SOURCE='output/analysis_candidates/keyboard_ef_only_fdr_v1/ef_only_fdr_all_34_tests.csv'
DICT_SOURCE='output/analysis_candidates/keyboard_deep_dive_v1/keyboard_deep_dive_feature_dictionary.csv'
MASTER_SOURCE='manuscript/tables/complete_feature_dictionary_20261021_v1.csv'
EF=readcsv(EF_SOURCE)
DIC=readcsv(DICT_SOURCE)
MAST=readcsv(MASTER_SOURCE)
D={r['feature_name']:r for r in DIC}
M=collections.defaultdict(list)
for r in MAST:M[r['exact_feature_name']].append(r)
cols=['feature_name','feature_family','definition_from_master_dictionary','definition_source','definition_version_count','definition_review_status','n_for_ef_change','rho_ef_change','p_original','q_original_204','q_ef_only_34_posthoc','bootstrap_ci_low','bootstrap_ci_high','original_204_q_lt_0_05','ef_only_q_lt_0_05','observed_record_semantics','literature_approval','source_results']
AUDIT=[]
for r in EF:
    name=r['feature_name']
    ms=M.get(name,[])
    preferred=next((x for x in ms if x['source_catalog_file']==DICT_SOURCE),ms[0] if ms else None)
    fam=r.get('family','')
    AUDIT.append({
        'feature_name':name,'feature_family':fam,
        'definition_from_master_dictionary': preferred['direct_measurement_and_formula'] if preferred else 'MISSING: inspect code',
        'definition_source':preferred['source_catalog_file'] if preferred else '',
        'definition_version_count':len(ms),
        'definition_review_status':'requires_implementation_review' if len(ms)>1 or not preferred else 'source_match_needs_code_confirmation',
        'n_for_ef_change':r['n'],'rho_ef_change':r['spearman_rho'],
        'p_original':r['spearman_p'],'q_original_204':r['original_204_test_bh_q'],
        'q_ef_only_34_posthoc':r['ef_only_bh_q'],
        'bootstrap_ci_low':r['bootstrap_ci_low'],'bootstrap_ci_high':r['bootstrap_ci_high'],
        'original_204_q_lt_0_05':str(num(r['original_204_test_bh_q'])<0.05).lower(),
        'ef_only_q_lt_0_05':str(num(r['ef_only_bh_q'])<0.05).lower(),
        'observed_record_semantics':'timestamped text-state snapshot proxy',
        'literature_approval':'pending_researcher_approval',
        'source_results':EF_SOURCE})
assert len(AUDIT)==34
writecsv(TABLES/'keyboard_discovery_complete_34_v0_2.csv',cols,AUDIT)
# 42 dictionary-level rows: 34 screened, other 8 QC/context or candidates; don't infer why excluded.
audit_by={r['feature_name']:r for r in AUDIT}
cols42=['feature_name','source','level','privacy_safe_output','dictionary_definition','screened_in_original_34','ef_n','ef_rho','ef_p','ef_q_34','ef_q_204','reference_status','method_status','dictionary_source']
CAT=[]
for r in DIC:
    e=audit_by.get(r['feature_name'],{})
    CAT.append({'feature_name':r['feature_name'],'source':r['source'],'level':r['level'],
      'privacy_safe_output':r['privacy_safe_output'],'dictionary_definition':r['definition'],
      'screened_in_original_34':str(bool(e)).lower(),'ef_n':e.get('n_for_ef_change',''),
      'ef_rho':e.get('rho_ef_change',''),'ef_p':e.get('p_original',''),
      'ef_q_34':e.get('q_ef_only_34_posthoc',''),'ef_q_204':e.get('q_original_204',''),
      'reference_status':'pending_researcher_approval','method_status':'defined_in_deep_dive_protocol',
      'dictionary_source':DICT_SOURCE})
assert len(CAT)==42
writecsv(TABLES/'keyboard_feature_dictionary_42_v0_2.csv',cols42,CAT)
# Lexical extension features; not equivalent to original discovery 34.
lexp='output/analysis_candidates/keyboard_deep_dive_v1/lexical_feature_feasibility_v1/feature_dictionary_20261021_v1.csv'
LEX=readcsv(lexp)
assert len(LEX)==7
for r in LEX:r['screened_in_original_34']='false';r['literature_approval']='pending_researcher_approval';r['source_dictionary']=lexp
writecsv(TABLES/'lexical_extension_features_v0_2.csv',list(LEX[0]),LEX)
# The research history exists as forty saved rows, not 40 independent clinical studies.
histp='manuscript/tables/research_review_chronology_20261020.csv'
HIST=readcsv(histp)
assert len(HIST)==40
writecsv(TABLES/'research_history_40_workstreams_v0_2.csv',list(HIST[0]),HIST)
# Modality counts from dictionary count version records not independently validated features
mod=collections.Counter(r['source_modality'] for r in MAST)
writecsv(TABLES/'feature_definition_version_counts_by_modality_v0_2.csv',
 ['source_modality','definition_version_records','count_semantics','original_source'],
 [{'source_modality':k,'definition_version_records':v,'count_semantics':'feature-definition/version rows, not independent biomarkers',
   'original_source':MASTER_SOURCE} for k,v in sorted(mod.items(),key=lambda t:-t[1])])
# Bibliography: externally verified bibliographic identity where indicated; historical approval deliberately unfilled.
papers=[
 ('Ning et al.','2023','Smartphone-derived Virtual Keyboard Dynamics Coupled with Accelerometer Data as a Window into Understanding Brain Health','10.1145/3544548.3580906','keyboard + motion, time-of-day','direct_source_checked','pending_researcher_approval','Custom keyboard and concurrent accelerometer; not identical to snapshot timing'),
 ('Keijzer et al.','2023','Passive logging of smartphone interactions as a feasible and reliable measure to monitor everyday cognition in Alzheimer’s Disease','10.1002/alz.071350','keystroke hold/flight; 14-day reliability','direct_source_checked','pending_researcher_approval','Neurokeys keyboard study N=16; 2023 Keijzer et al. report distinct from their later N=40 study'),
 ('Keijzer et al.','2024/2025','Passively collected smartphone behaviour as a reliable and feasible measure for global cognition in Alzheimer’s Disease','10.1002/alz.086452','typing, corrections and 28-day test–retest','direct_source_checked','pending_researcher_approval','Abstract in Alzheimer’s & Dementia; originally labeled Twose in local register although first author is Keijzer'),
 ('Covington and McFall','2010','Cutting the Gordian Knot: The Moving-Average Type–Token Ratio (MATTR)','10.1080/09296171003643098','MATTR lexical diversity','direct_source_checked','pending_researcher_approval','Validated moving-average type-token ratio method; not clinical validation'),
 ('McCarthy and Jarvis','2010','MTLD, vocd-D, and HD-D: A validation study of sophisticated approaches to lexical diversity assessment','10.3758/BRM.42.2.381','MTLD lexical diversity','direct_source_checked','pending_researcher_approval','Study validates MTLD methods outside smartphone dementia cohort'),
 ('Detection of Mild Cognitive Impairment Through Natural Language and Touchscreen Typing Processing','2020','Detection of Mild Cognitive Impairment Through Natural Language and Touchscreen Typing Processing','10.3389/fdgth.2020.567158','lexical and touchscreen features for MCI','direct_source_checked','pending_researcher_approval','Clinical population but different typing measurements; verify actual author list before citation'),
 ('Butler et al.','2025','Large-scale passive multimodal smartphone cognitive study (verify full title)','10.1038/s41591-024-03475-9','study precedent, app and multimodal sensing','repository_record_only','pending_researcher_approval','Exact bibliographic and method fields require separate source verification'),
 ('Multimodal older-adult sensing guide','2026','Multimodal passive smartphone sensing in older adults: a guide for clinical scientists','10.1093/geroni/igag007','cross-modal passive smartphone measures','repository_record_only','pending_researcher_approval','Verify final full citation and measurement definitions')
]
lcols=['lead_author','publication_year','publication_title','doi','potential_feature_family','bibliographic_verification','historical_feature_selection_approval','methodological_qualification','repository_literature_sources']
writecsv(TABLES/'literature_feature_approval_queue_v0_2.csv',lcols,[
 dict(zip(lcols,list(p)+['output/analysis_candidates/cross_modal_feature_discovery_v1/CROSS_MODAL_LITERATURE_REGISTER.md; output/analysis_candidates/keyboard_deep_dive_v1/lexical_feature_feasibility_v1/literature_review_20261021_v1.csv']))
 for p in papers])
# Chart 1: pre-existing confidence intervals. bootstrap CIs are not multiplicity-adjusted.
def xml(s):return html.escape(str(s),quote=True)
W,H=1120,570; x0,x1=335,995; ytop=140; dx=(x1-x0)/2
parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Spearman correlations and saved bootstrap intervals for five exploratory Executive Function keyboard findings">',
 f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
 '<text x="40" y="48" fill="#172439" font-size="27" font-family="Arial" font-weight="bold">Executive Function × longitudinal keyboard change</text>',
 '<text x="40" y="80" fill="#566479" font-size="16" font-family="Arial">Five highest EF-only BH results; 95% bootstrap intervals copied from discovery output</text>']
for t in [-1,-.5,0,.5,1]:
 x=x0+(t+1)*dx
 parts.append(f'<line x1="{x:.1f}" y1="118" x2="{x:.1f}" y2="455" stroke="#dfe5eb" stroke-width="1" />')
 parts.append(f'<text x="{x:.1f}" y="490" fill="#566479" text-anchor="middle" font-family="Arial" font-size="15">{t:g}</text>')
head=EF[:5]
labels=['Correction recovery','Afternoon (12–18) IEI','IEI coefficient of variation','Evening (18–24) IEI','Morning (06–12) IEI']
for i,(r,lab) in enumerate(zip(head,labels)):
 y=155+i*69
 rho=num(r['spearman_rho']);lo=num(r['bootstrap_ci_low']);hi=num(r['bootstrap_ci_high'])
 cx=x0+(rho+1)*dx; lx=x0+(lo+1)*dx; hx=x0+(hi+1)*dx
 color='#225e94' if rho>0 else '#a95650'
 parts.extend([
  f'<text x="40" y="{y+5}" font-size="17" font-family="Arial" fill="#26374b">{xml(lab)}</text>',
  f'<line x1="{lx:.1f}" y1="{y}" x2="{hx:.1f}" y2="{y}" stroke="{color}" stroke-width="3"/>',
  f'<line x1="{lx:.1f}" y1="{y-8}" x2="{lx:.1f}" y2="{y+8}" stroke="{color}" stroke-width="2"/>',
  f'<line x1="{hx:.1f}" y1="{y-8}" x2="{hx:.1f}" y2="{y+8}" stroke="{color}" stroke-width="2"/>',
  f'<circle cx="{cx:.1f}" cy="{y}" r="7" fill="{color}" stroke="white" stroke-width="2"/>',
  f'<text x="1007" y="{y+5}" font-size="14" font-family="Arial" fill="#30435b">n={r["n"]}</text>',
 ])
parts.extend(['<text x="665" y="525" font-size="17" font-family="Arial" fill="#30435b" text-anchor="middle">Spearman ρ (Late − Early vs T2 − T1)</text>',
 '<text x="40" y="556" font-size="13" font-family="Arial" fill="#67778b">Exploratory; n=28–33. Intervals are unadjusted bootstrap CIs, not simultaneous or corrected intervals. Snapshot timing ≠ keypress timing.</text>',
 '</svg>'])
(FIGURES/'ef_keyboard_bootstrap_forest_v0_2.svg').write_text('\n'.join(parts),encoding='utf-8')
# Chart 2: 5 q comparison, always original and selected-domain on one chart for transparency.
W,H=1120,520; xx0,xx1=365,1010; scale=(xx1-xx0)/.22
parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Original 204-test and post hoc Executive Function 34-test BH q comparisons for five findings">',
 f'<rect width="{W}" height="{H}" fill="#fff"/>',
 '<text x="40" y="47" font-size="26" font-family="Arial" font-weight="bold" fill="#172439">Multiplicity family changes the q-value</text>',
 '<text x="40" y="77" font-size="15" font-family="Arial" fill="#566479">The same five original p-values; BH applied within two different testing families</text>']
for t in [0,.05,.10,.15,.20]:
 x=xx0+t*scale
 parts.append(f'<line x1="{x:.1f}" y1="111" x2="{x:.1f}" y2="444" stroke="#dfe5eb"/>')
 parts.append(f'<text x="{x:.1f}" y="466" text-anchor="middle" font-size="14" fill="#5e7183" font-family="Arial">{t:.2f}</text>')
x=xx0+.05*scale
parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="105" y2="446" stroke="#8a9baa" stroke-dasharray="4 4" stroke-width="2"/>')
for i,(r,label) in enumerate(zip(head,labels)):
 y=145+i*63
 q1=num(r['original_204_test_bh_q']);q2=num(r['ef_only_bh_q'])
 parts.append(f'<text x="40" y="{y+7}" font-size="16" fill="#25384e" font-family="Arial">{xml(label)}</text>')
 for qq,dy,c in [(q1,-9,'#7a8fa5'),(q2,9,'#226e9f')]:
  width=qq*scale
  parts.append(f'<rect x="{xx0}" y="{y+dy-5}" width="{width:.1f}" height="11" rx="3" fill="{c}"/>')
  parts.append(f'<text x="{xx0+width+8:.1f}" y="{y+dy+5}" font-size="12" fill="{c}" font-family="Arial">{qq:.3f}</text>')
parts.append('<rect x="35" y="488" width="12" height="12" fill="#7a8fa5"/><text x="52" y="499" font-family="Arial" font-size="13" fill="#425366">Original full-scope: 204 tests</text>')
parts.append('<rect x="320" y="488" width="12" height="12" fill="#226e9f"/><text x="338" y="499" font-family="Arial" font-size="13" fill="#425366">Post-hoc EF-only: 34 tests</text>')
parts.append('</svg>')
(FIGURES/'ef_keyboard_fdr_family_comparison_v0_2.svg').write_text('\n'.join(parts),encoding='utf-8')
# Chart 3: definition-version rows by modality (not independent features)
groups=mod.most_common(12)
W=1120;H=610;x0=370;barmax=630;yt=99
parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="Feature definition version counts by modality">',
'<rect width="1120" height="610" fill="white"/>',
'<text x="40" y="47" font-size="26" fill="#172439" font-weight="bold" font-family="Arial">Feature-bank breadth: definition/version records by modality</text>',
'<text x="40" y="76" font-size="15" fill="#566479" font-family="Arial">Selected categories from the original 1,246-row dictionary; these are NOT independent biomarkers</text>']
maxv=max(v for _,v in groups)
for i,(name,v) in enumerate(groups):
 y=yt+i*36
 bw=v/maxv*barmax
 parts.append(f'<text x="40" y="{y+13}" font-size="15" fill="#24394d" font-family="Arial">{xml(name.replace("_"," "))}</text>')
 parts.append(f'<rect x="{x0}" y="{y}" width="{bw:.1f}" height="20" rx="3" fill="#28648f"/>')
 parts.append(f'<text x="{x0+bw+8:.1f}" y="{y+15}" font-size="14" fill="#314356" font-family="Arial">{v}</text>')
parts.append('<text x="40" y="568" font-size="13" fill="#687b8e" font-family="Arial">A feature can appear multiple times across versions and analysis outputs. Source: complete_feature_dictionary_20261021_v1.csv</text>')
parts.append('</svg>')
(FIGURES/'feature_bank_modality_coverage_v0_2.svg').write_text('\n'.join(parts),encoding='utf-8')
# Validate source locked 34
assert sum(num(r['ef_only_bh_q'])<.05 for r in EF)==5
assert sum(num(r['original_204_test_bh_q'])<.05 for r in EF)==0
assert len(DIC)==42 and len(LEX)==7 and len(MAST)==1246
meta={'report_asset_version':'v0.2','original_keyboard_feature_count':34,'keyboard_dictionary_rows':42,
'lexical_extension_rows':7,'ef_q_lt_0_05':5,'master_definition_rows':1246,
'original_research_chronology_workstreams':40,'input_files':[EF_SOURCE,DICT_SOURCE,MASTER_SOURCE,histp,lexp],
'no_patient_level_data_exported':True,'new_statistical_tests_run':False}
(OUT/'ASSET_MANIFEST_v0_2.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(json.dumps(meta,indent=2))
