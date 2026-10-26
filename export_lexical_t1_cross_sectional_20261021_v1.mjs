import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const deps=process.env.REGISTER_ARTIFACT_NODE_MODULES||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const req=createRequire(path.join(deps,'../package.json')); const {Workbook}=await import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
const payload=JSON.parse(await fs.readFile('/tmp/lexical_t1_cross_sectional_20261021/payload.json','utf8'));
const dest=path.join(root,'output/analysis_candidates/keyboard_deep_dive_v1/lexical_t1_cross_sectional_v1'); await fs.mkdir(dest,{recursive:true});
const quote=x=>`"${String(x??'').replaceAll('"','""')}"`;
async function writeNew(file,content){try{await fs.access(file);throw new Error(`Refusing overwrite: ${file}`)}catch(e){if(e.code!=='ENOENT')throw e;await fs.writeFile(file,content,{flag:'wx'})}}
async function table(name,records,columns=[]){const cols=Object.keys(records[0]||{}).length?Object.keys(records[0]):columns;const matrix=[cols,...records.map(r=>cols.map(c=>String(r[c]??'')))];const wb=Workbook.create();const sh=wb.worksheets.add('T1');const rg=sh.getRangeByIndexes(0,0,matrix.length,Math.max(cols.length,1));rg.values=matrix.length&&cols.length?matrix:[['status'],['no rows']];wb.recalculate();assert.deepEqual(rg.values,rg.values);await writeNew(path.join(dest,name),matrix.map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n');console.log(name,records.length)}
await table('t1_eligibility_coverage_20261021_v1.csv',payload.coverage);
await table('assessment_to_recording_timing_20261021_v1.csv',payload.assessment_timing);
await table('feature_dictionary_20261021_v1.csv',payload.feature_dictionary);
await table('statistical_results_20261021_v1.csv',payload.results);
await table('significant_results_p_lt_0_05_20261021_v1.csv',payload.significant);
await table('supervisor_results_20261021_v1.csv',payload.supervisor);
await table('privacy_reproducibility_checks_20261021_v1.csv',payload.privacy);
await writeNew(path.join(dest,'manifest_20261021_v1.json'),JSON.stringify(payload.manifest,null,2)+'\n');
console.log(JSON.stringify({dest,results:payload.results.length,significant:payload.significant.length,patients:payload.manifest.t1_patients_with_valid_global},null,2));
