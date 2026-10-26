import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook } from '@oai/artifact-tool';

const payloadPath = '/tmp/mattr100_validation_audit_20261021/payload.json';
const outDir = path.resolve('output/analysis_candidates/keyboard_deep_dive_v1/mattr100_validation_audit_20261021');
const payload = JSON.parse(await fs.readFile(payloadPath, 'utf8'));
await fs.mkdir(outDir, { recursive: true });

const safe = v => (v === undefined || v === null || Number.isNaN(v) ? '' : v);
function csv(rows) {
  if (!rows.length) return '';
  const cols = [...new Set(rows.flatMap(r => Object.keys(r)))];
  const esc = v => {
    const s = String(safe(v));
    return /[",\n]/.test(s) ? `"${s.replaceAll('"','""')}"` : s;
  };
  return [cols.join(','), ...rows.map(r => cols.map(c => esc(r[c])).join(','))].join('\n') + '\n';
}

const cohortRows = payload.cohort_comparison;
const coverageRows = [
  ...payload.coverage_associations.map(r => ({section:'coverage', ...r})),
  ...payload.language_application.map(r => ({section:'language_application', ...r})),
];
const associations = payload.associations.map(r => ({
  result_type: 'new_demographic_coverage_sensitivity', ...r,
}));
const summary = [
  ...associations,
  {result_type:'historical_saved_coverage_adjusted', outcome:'verbal_T1', n:22, rho:0.607002, p:0.002739, q:0.027392, note:'Prior v1 coverage-only partial Spearman; same MATTR-100 cohort; not independent replication.'},
  {result_type:'historical_saved_coverage_adjusted', outcome:'motor_T1', n:21, rho:0.562338, p:0.007967, q:0.119506, note:'Prior v2 coverage-only partial Spearman; same MATTR-100 cohort; not independent replication.'},
  ...payload.domain_overlap.map(r => ({result_type:'domain_overlap', ...r, note:'Verbal and Motor scores are not materially correlated in the shared MATTR-100 eligible cohort.'})),
];
const loo = payload.loo;
const looSummary = ['verbal_T1','motor_T1'].map(outcome => {
  const rows = loo.filter(r => r.outcome === outcome);
  const ps = rows.map(r=>r.p), rs=rows.map(r=>r.rho);
  return {outcome, exclusions:rows.length, min_p:Math.min(...ps), max_p:Math.max(...ps), min_rho:Math.min(...rs), max_rho:Math.max(...rs), positive_rho_exclusions:rs.filter(x=>x>0).length, note:'Leave-one-patient-out range; all re-estimated correlations retained the positive direction.'};
});
summary.push(...looSummary.map(r=>({result_type:'leave_one_out_summary', ...r})));

const privacy = payload.privacy;
const manifest = {
  analysis: 'MATTR-100 focused validation audit', version: '20261021_v1',
  source: 'word_length_patient_table_20261021_v1.csv', source_mode: 'saved aggregate numeric table only',
  high_coverage_definition: 'reliable_completion_count_T1 >= 100', high_n:22, low_n:59,
  raw_text_exported:false, raw_words_exported:false, patient_vocabularies_exported:false,
  files:['mattr100_audit_summary_20261021_v1.csv','mattr100_cohort_comparison_20261021_v1.csv','mattr100_coverage_language_application_20261021_v1.csv','mattr100_leave_one_out_20261021_v1.csv','mattr100_privacy_checks_20261021_v1.csv']
};

const files = {
  'mattr100_audit_summary_20261021_v1.csv': csv(summary),
  'mattr100_cohort_comparison_20261021_v1.csv': csv(cohortRows),
  'mattr100_coverage_language_application_20261021_v1.csv': csv(coverageRows),
  'mattr100_leave_one_out_20261021_v1.csv': csv(loo),
  'mattr100_privacy_checks_20261021_v1.csv': csv([privacy]),
};
for (const [name, text] of Object.entries(files)) await fs.writeFile(path.join(outDir,name), text);
await fs.writeFile(path.join(outDir,'manifest_20261021_v1.json'), JSON.stringify(manifest,null,2)+'\n');

// Artifact-tool verification: import each CSV and inspect its populated range.
for (const [name, text] of Object.entries(files)) {
  const wb = await Workbook.fromCSV(text, { sheetName: 'data' });
  wb.recalculate();
  const check = await wb.inspect({ kind:'table', sheetId:'data', range:'A1:Z20', include:'values', tableMaxRows:3, tableMaxCols:8, maxChars:2000 });
  if (!check || !check.ndjson) throw new Error(`Artifact verification failed for ${name}`);
}
console.log(JSON.stringify({outDir, files:Object.keys(files), manifest:'manifest_20261021_v1.json'}, null, 2));
