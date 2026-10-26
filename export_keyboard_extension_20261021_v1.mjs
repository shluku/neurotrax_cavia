import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const deps = process.env.REGISTER_ARTIFACT_NODE_MODULES || path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const req = createRequire(path.join(deps, '../package.json'));
const { Workbook } = await import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
const payload = JSON.parse(await fs.readFile('/tmp/keyboard_extension_20261021/payload.json', 'utf8'));
const dirs = {
  word: path.join(root, 'output/analysis_candidates/keyboard_deep_dive_v1/word_length_adjusted_completion_v1'),
  lexical: path.join(root, 'output/analysis_candidates/keyboard_deep_dive_v1/lexical_feature_feasibility_v1'),
};
await Promise.all(Object.values(dirs).map((d) => fs.mkdir(d, { recursive: true })));
const quote = (x) => `"${String(x ?? '').replaceAll('"', '""')}"`;
async function writeNew(file, content) {
  try { await fs.access(file); throw new Error(`Refusing to overwrite existing version: ${file}`); }
  catch (e) { if (e.code !== 'ENOENT') throw e; await fs.writeFile(file, content, { flag: 'wx' }); }
}
async function writeTable(dir, filename, records, defaultColumns = []) {
  const columns = Object.keys(records[0] || {}).length ? Object.keys(records[0]) : defaultColumns;
  const matrix = [columns, ...records.map((r) => columns.map((c) => String(r[c] ?? '')))];
  const wb = Workbook.create(); const sheet = wb.worksheets.add('Aggregate');
  const range = sheet.getRangeByIndexes(0, 0, matrix.length, Math.max(columns.length, 1));
  range.values = matrix.length && columns.length ? matrix : [['status'], ['no rows']];
  wb.recalculate(); assert.deepEqual(range.values, range.values, `${filename}: authored values readable`);
  await writeNew(path.join(dir, filename), matrix.map((r) => r.map(quote).join(',')).join('\r\n') + '\r\n');
  console.log(`${filename}: ${records.length} records`);
}
const wordCols = [
  'Subject_ID_D','window_name','window_start_ms','window_end_ms','raw_rows_in_window','distinct_observations_in_window','duplicate_rows_removed','json_parse_errors','password_rows_excluded','active_days','active_minutes','valid_interval_count','long_pause_count_2s','unique_package_count','unique_device_count','reconstructed_completion_count_all','reliable_completion_count','ambiguous_completion_count','reliable_fraction','continuity_break_count','multi_character_jump_count','repeated_state_count','incomplete_word_start_count','correction_transition_count','paste_like_jump_count','completion_mean_ms','completion_median_ms','completion_sd_ms','completion_iqr_ms','completion_mad_ms','completion_cv','completion_per_character_median_ms','len_2_3_count','len_2_3_median_ms','len_2_3_iqr_ms','len_2_3_mad_ms','len_2_3_cv','len_4_5_count','len_4_5_median_ms','len_4_5_iqr_ms','len_4_5_mad_ms','len_4_5_cv','len_6_8_count','len_6_8_median_ms','len_6_8_iqr_ms','len_6_8_mad_ms','len_6_8_cv','len_9_plus_count','len_9_plus_median_ms','len_9_plus_iqr_ms','len_9_plus_mad_ms','len_9_plus_cv','length_adjusted_iqr_equal_group_median_ms','length_residual_sd_ms','length_residual_iqr_ms'
];
const lexCols = [
  'Subject_ID_D','window_name','active_days','distinct_observations_in_window','valid_interval_count','unique_package_count','unique_device_count','word_token_count','word_type_count','word_ttr','word_repetition_rate','word_mean_length_chars','word_median_length_chars','word_length_sd_chars','word_mattr_50','word_mattr_100','word_mtld','ttr50_subsample_sd','language_latin_token_count','language_hebrew_token_count','language_mixed_token_count','language_other_token_count','reliable_completion_count','ambiguous_completion_count','reliable_fraction','continuity_break_count','multi_character_jump_count','repeated_state_count','incomplete_word_start_count','password_rows_excluded'
];
const supervisor = payload.supervisor_results.length ? payload.supervisor_results : [{family:'word_length_adjusted_and_lexical',status:'not_run',gate_passed:payload.gate.gate_passed,paired_patients_min100_tokens_each:payload.gate.paired_patients_min100_tokens_each,reason:'No cognitive screen run because the prespecified paired-token feasibility gate was not met; this is not a null cognitive result.'}];
await writeTable(dirs.word, 'word_length_window_features_20261021_v1.csv', payload.word_length_windows, wordCols);
await writeTable(dirs.word, 'word_length_daily_features_20261021_v1.csv', payload.word_length_daily);
await writeTable(dirs.word, 'word_length_quality_summary_20261021_v1.csv', payload.quality);
await writeTable(dirs.word, 'word_length_patient_table_20261021_v1.csv', payload.patient_table);
await writeTable(dirs.word, 'feature_dictionary_20261021_v1.csv', payload.feature_dictionary);
await writeTable(dirs.word, 'supervisor_results_20261021_v1.csv', supervisor);
await writeTable(dirs.word, 'comparison_existing_word_features_20261021_v1.csv', payload.comparison);
await writeTable(dirs.lexical, 'lexical_window_features_20261021_v1.csv', payload.word_length_windows, lexCols);
await writeTable(dirs.lexical, 'lexical_daily_features_20261021_v1.csv', payload.word_length_daily);
await writeTable(dirs.lexical, 'lexical_quality_summary_20261021_v1.csv', payload.quality);
await writeTable(dirs.lexical, 'lexical_patient_table_20261021_v1.csv', payload.patient_table);
await writeTable(dirs.lexical, 'feature_dictionary_20261021_v1.csv', payload.feature_dictionary);
await writeTable(dirs.lexical, 'supervisor_results_20261021_v1.csv', supervisor);
await writeTable(dirs.lexical, 'privacy_validation_report_20261021_v1.csv', payload.privacy_report);
await writeTable(dirs.lexical, 'literature_review_20261021_v1.csv', payload.literature_review);
await writeTable(dirs.lexical, 'comparison_existing_word_features_20261021_v1.csv', payload.comparison);
const manifest = {...payload.manifest, gate:payload.gate, output_directories:Object.values(dirs).map(String), privacy:'No raw words, text, word lists, hashes, or embeddings persisted.'};
for (const dir of Object.values(dirs)) await writeNew(path.join(dir, 'manifest_20261021_v1.json'), JSON.stringify(manifest, null, 2)+'\n');
console.log(JSON.stringify({dirs, windows:payload.word_length_windows.length, gate:payload.gate}, null, 2));
