import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url)); const deps=process.env.REGISTER_ARTIFACT_NODE_MODULES||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'); const req=createRequire(path.join(deps,'../package.json')); const {Workbook}=await import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
const p=JSON.parse(await fs.readFile('/tmp/lexical_t1_other_domains_20261021/payload.json','utf8')); const dest=path.join(root,'output/analysis_candidates/keyboard_deep_dive_v1/lexical_t1_cross_sectional_v2_other_domains'); await fs.mkdir(dest,{recursive:true}); const q=x=>`"${String(x??'').replaceAll('"','""')}"`;
async function writeNew(f,c){try{await fs.access(f);throw new Error('refusing overwrite')}catch(e){if(e.code!=='ENOENT')throw e;await fs.writeFile(f,c,{flag:'wx'})}}
async function table(name,rows){const cols=Object.keys(rows[0]||{});const m=[cols,...rows.map(r=>cols.map(c=>String(r[c]??'')))];const wb=Workbook.create();const sh=wb.worksheets.add('OtherDomains');const rg=sh.getRangeByIndexes(0,0,m.length,cols.length||1);rg.values=m;wb.recalculate();assert.deepEqual(rg.values,m);await writeNew(path.join(dest,name),m.map(r=>r.map(q).join(',')).join('\r\n')+'\r\n');console.log(name,rows.length)}
await table('statistical_results_20261021_v2.csv',p.results); await table('significant_results_p_lt_0_05_20261021_v2.csv',p.significant); await table('t1_eligibility_coverage_20261021_v2.csv',p.coverage); await table('supervisor_results_20261021_v2.csv',p.supervisor); await table('privacy_reproducibility_checks_20261021_v2.csv',p.privacy); await writeNew(path.join(dest,'manifest_20261021_v2.json'),JSON.stringify(p.manifest,null,2)+'\n'); console.log(JSON.stringify(p.manifest,null,2));
