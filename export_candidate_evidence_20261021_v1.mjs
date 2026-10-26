// Versioned evidence-table export through Artifact Tool. Historical files are never replaced.
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
const staging = '/tmp/candidate_evidence_completeness_20261021';
const destination = path.join(root, 'output/analysis_candidates/keyboard_deep_dive_v1/candidate_evidence_completeness_20261021');
await fs.mkdir(destination, { recursive: true });
const payload = JSON.parse(await fs.readFile(path.join(staging, 'tables.json'), 'utf8'));
const quote = (x) => `"${String(x ?? '').replaceAll('"', '""')}"`;
const writeNew = async (file, content) => {
  try { await fs.access(file); throw new Error(`Refusing to overwrite existing version: ${file}`); }
  catch (e) { if (e.code !== 'ENOENT') throw e; await fs.writeFile(file, content, { flag: 'wx' }); }
};
const writeTable = async (filename, records) => {
  const columns = Object.keys(records[0] || {});
  const matrix = [columns, ...records.map((r) => columns.map((c) => String(r[c] ?? '')))];
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add('Evidence');
  const range = sheet.getRangeByIndexes(0, 0, matrix.length, columns.length);
  range.values = matrix;
  workbook.recalculate();
  assert.deepEqual(range.values, matrix, `${filename}: values changed during authoring`);
  await writeNew(path.join(destination, filename), matrix.map((r) => r.map(quote).join(',')).join('\r\n') + '\r\n');
  console.log(`${filename}: ${records.length} records verified`);
};
await writeTable('candidate_evidence_completeness_table_20261021_v1.csv', payload.evidence);
await writeTable('candidate_evidence_descriptive_distributions_20261021_v1.csv', payload.distributions);
await writeTable('candidate_evidence_source_index_20261021_v1.csv', payload.sources);
const manifest = { ...payload.metadata, generated_at: new Date().toISOString(), files: [
  'candidate_evidence_completeness_table_20261021_v1.csv',
  'candidate_evidence_descriptive_distributions_20261021_v1.csv',
  'candidate_evidence_source_index_20261021_v1.csv',
] };
await writeNew(path.join(destination, 'candidate_evidence_manifest_20261021_v1.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify({ destination, evidence_rows: payload.evidence.length, distribution_rows: payload.distributions.length, source_rows: payload.sources.length }, null, 2));
