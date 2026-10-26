import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const deps=process.env.REGISTER_ARTIFACT_NODE_MODULES||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const req=createRequire(path.join(deps,'../package.json')); const {Workbook}=await import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
const dir=path.join(root,'output/analysis_candidates/keyboard_deep_dive_v1/word_length_adjusted_completion_v1');
const rows=[
 {feature_name:'completion_median_ms',family:'word_length_adjusted',definition:'Median duration from reliable observable word start to delimiter completion',units:'ms',privacy:'aggregate only',status:'exploratory'},
 {feature_name:'completion_per_character_median_ms',family:'word_length_adjusted',definition:'Median observable completion duration divided by normalized completed-token character length',units:'ms/character; not typing speed',privacy:'aggregate only',status:'descriptive'},
 {feature_name:'len_2_3_iqr_ms',family:'word_length_adjusted',definition:'IQR of reliable completion durations for normalized token lengths 2–3',units:'ms',privacy:'aggregate only',status:'exploratory'},
 {feature_name:'len_4_5_iqr_ms',family:'word_length_adjusted',definition:'IQR of reliable completion durations for normalized token lengths 4–5',units:'ms',privacy:'aggregate only',status:'exploratory'},
 {feature_name:'len_6_8_iqr_ms',family:'word_length_adjusted',definition:'IQR of reliable completion durations for normalized token lengths 6–8',units:'ms',privacy:'aggregate only',status:'exploratory'},
 {feature_name:'len_9_plus_iqr_ms',family:'word_length_adjusted',definition:'IQR of reliable completion durations for normalized token lengths 9+',units:'ms',privacy:'aggregate only',status:'exploratory'},
 {feature_name:'length_adjusted_iqr_equal_group_median_ms',family:'word_length_adjusted',definition:'Median of available fixed-length-group IQRs, giving each observed group equal weight',units:'ms',privacy:'aggregate only',status:'exploratory'},
 {feature_name:'length_residual_iqr_ms',family:'word_length_adjusted',definition:'IQR of residuals from descriptive within-window duration ~ length + length squared model',units:'ms',privacy:'aggregate only',status:'exploratory; requires >=20 reliable completions'},
 {feature_name:'length_residual_sd_ms',family:'word_length_adjusted',definition:'SD of residuals from descriptive within-window duration ~ length + length squared model',units:'ms',privacy:'aggregate only',status:'exploratory; requires >=20 reliable completions'},
 {feature_name:'word_ttr',family:'lexical',definition:'Unique normalized observable completed tokens divided by reliable completed tokens',units:'ratio',privacy:'aggregate only',status:'feasibility'},
 {feature_name:'word_mattr_50',family:'lexical',definition:'Mean type-token ratio across fixed 50-token moving windows',units:'ratio',privacy:'aggregate only',status:'feasibility'},
 {feature_name:'word_mattr_100',family:'lexical',definition:'Mean type-token ratio across fixed 100-token moving windows',units:'ratio',privacy:'aggregate only',status:'feasibility'},
 {feature_name:'word_mtld',family:'lexical',definition:'MTLD factor-based lexical-diversity estimate when at least 100 reliable tokens exist',units:'tokens per factor',privacy:'aggregate only',status:'feasibility'},
];
const cols=Object.keys(rows[0]); const matrix=[cols,...rows.map(r=>cols.map(c=>String(r[c]??'')))]; const wb=Workbook.create(); const sh=wb.worksheets.add('Dictionary'); const rg=sh.getRangeByIndexes(0,0,matrix.length,cols.length); rg.values=matrix; wb.recalculate(); assert.deepEqual(rg.values,matrix); const q=x=>`"${String(x??'').replaceAll('"','""')}"`; const file=path.join(dir,'feature_dictionary_word_length_extension_20261021_v1.csv'); try{await fs.access(file);throw new Error('refusing overwrite')}catch(e){if(e.code!=='ENOENT')throw e;await fs.writeFile(file,matrix.map(r=>r.map(q).join(',')).join('\r\n')+'\r\n',{flag:'wx'})}; console.log(file);
