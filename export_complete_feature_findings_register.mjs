// Export source-derived catalog strings with Artifact Tool; never replace a version.
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root=path.dirname(fileURLToPath(import.meta.url));
const dependencies=process.env.REGISTER_ARTIFACT_NODE_MODULES || path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const requireRuntime=createRequire(path.join(dependencies,'../package.json'));
const {Workbook}=await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')).href);
const staging='/tmp/complete_feature_findings_register_20261021';
const destination=path.join(root,'manuscript/tables');
const tables=JSON.parse(await fs.readFile(path.join(staging,'tables.json'),'utf8'));
const quote=x=>`"${String(x ?? '').replaceAll('"','""')}"`;

async function preserveOrWrite(filename,content) {
  try {
    const old=await fs.readFile(filename,'utf8');
    assert.equal(old,content,`Refusing to replace existing version ${filename}; choose a new version tag.`);
  } catch(error) {
    if(error.code!=='ENOENT') throw error;
    await fs.writeFile(filename,content,{flag:'wx'});
  }
}

for (const [name,table] of Object.entries(tables)) {
  const workbook=Workbook.create();
  const sheet=workbook.worksheets.add('Register');
  // Literal saved decimal strings retain all source precision in the CSV.
  const matrix=[table.columns,...table.rows].map(row=>row.map(x=>String(x ?? '')));
  const range=sheet.getRangeByIndexes(0,0,matrix.length,matrix[0].length);
  range.values=matrix;
  workbook.recalculate();
  const values=range.values;
  assert.deepEqual(values,matrix,`${name}: catalog cells changed during authoring`);
  await preserveOrWrite(path.join(destination,name+'.csv'),values.map(row=>row.map(quote).join(',')).join('\r\n')+'\r\n');
  console.log(`${name}: ${matrix.length-1} records verified`);
}
await preserveOrWrite(path.join(destination,'complete_feature_findings_manifest_20261021_v1.json'),await fs.readFile(path.join(staging,'manifest.json'),'utf8'));
