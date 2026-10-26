"""Validate catalog provenance and preservation, without statistical inference."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TABLE=ROOT/'manuscript/tables'
TAG='20261021_v1'

def read(p):
    with p.open(newline='',encoding='utf-8-sig') as f: return list(csv.DictReader(f))

def num(x):
    try: return float(x)
    except (ValueError,TypeError): return float('nan')

def main():
    rows=read(TABLE/f'complete_feature_cognitive_associations_{TAG}.csv')
    defs=read(TABLE/f'complete_feature_dictionary_{TAG}.csv')
    selected=read(TABLE/f'complete_feature_cognitive_p_lt_0_05_{TAG}.csv')
    sup=read(TABLE/f'supervisor_feature_findings_{TAG}.csv')
    manifest=json.loads((TABLE/f'complete_feature_findings_manifest_{TAG}.json').read_text())
    master=read(TABLE/'master_association_table_20261020.csv')
    assert {r['historical_master_row_id'] for r in rows if r['historical_master_row_id']}=={r['master_row_id'] for r in master}
    assert len(rows)==manifest['association_rows'] and len(defs)==manifest['dictionary_definition_versions']
    assert len({r['register_row_id'] for r in rows})==len(rows)
    assert {r['register_row_id'] for r in selected}=={r['register_row_id'] for r in rows if num(r['p'])<.05}
    ids={r['feature_definition_id'] for r in defs}
    sources={r['source_file']:read(ROOT/r['source_file']) for r in rows}
    validations=0
    for r in rows:
        assert all(x in ids for x in r['feature_definition_ids'].split('; '))
        source=sources[r['source_file']][int(r['source_csv_line'])-2]
        assert json.loads(r['source_record_json'])==source
        assert r['estimate']==source[r['coefficient_field']]
        for value,field in [('p','p_source_field'),('q','q_source_field'),('ci_low','ci_low_source_field'),('ci_high','ci_high_source_field')]:
            assert r[value]==(source.get(r[field],'') if r[field] else ''),(r['register_row_id'],value)
            validations+=1
        if r['n_source_field'] in source: assert r['n']==source[r['n_source_field']]
        for value,flag,threshold in [('p','p_lt_0_05',.05),('q','q_lt_0_05',.05),('q','q_le_0_20',.20)]:
            x=num(r[value]); wanted='not available' if not math.isfinite(x) else 'yes' if (x<=threshold if flag=='q_le_0_20' else x<threshold) else 'no'
            assert r[flag]==wanted
    lookup={r['register_row_id']:r for r in rows}
    for r in sup:
        source=lookup[r['full_register_row_id']]
        for c in ['p','q','n','ci_low','ci_high']: assert r[c]==source[c]
        assert r['effect']==source['estimate']
    for rel,digest in manifest['source_hashes'].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest,rel
    print(json.dumps({'status':'passed','association_rows':len(rows),'dictionary_versions':len(defs),'source_statistic_string_checks':validations,'historical_master_rows_preserved':len(master),'unchanged_hashed_inputs':len(manifest['source_hashes']),'p_filtered_rows':len(selected),'supervisor_rows':len(sup),'new_statistical_analyses':0},indent=2))

if __name__=='__main__': main()
