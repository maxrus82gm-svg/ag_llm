'use strict';
// Preserve the original six controls and add four UX-002 mutations, in memory.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),cp=require('node:child_process');
const root=process.env.WA4UX_SOURCE_ROOT||process.cwd(),out=path.resolve(process.argv[2]||'');
const rel=path.relative(os.tmpdir(),out);
if(!rel||rel.startsWith('..')||path.isAbsolute(rel)||fs.existsSync(out))throw Error('new TEMP output required');
const base=fs.readFileSync(path.join(root,'reports/CODEX-WA4-UX-001-OPERATOR-REDESIGN/quality_controls.js'),'utf8');
const extra=`const cases=[
 ['draft-workspace-submit','UX-001-A submit guard independently',
  '!view.catalogFresh||!draftWorkspaceConfirmed()))return','!view.catalogFresh))return'],
 ['incoherent-empty-timeline','UX incoherent empty plan',
  "o.coherent?'План ещё не содержит этапов.':'Состав плана не подтверждён. Обновите состояние.'","'План ещё не содержит этапов.'"],
 ['success-severity','UX-002-A workspace success is central green',
  "operationNotice('success',ws?","operationNotice('error',ws?"],
 ['unknown-severity','UX-002-A lost workspace response is a warning',
  "operationNotice(rejected?'error':'warning'","operationNotice(rejected?'error':'success'"],
 ['late-folder-response','UX-002-B late selection cannot replace',
  "revision!==view.wsRootRevision||$('wsRoot').value!==previous","false"],
 ['preserve-picker-token','UX-002-B selected path uses protected',
  "...opts.headers,'Content-Type':'application/json'","'Content-Type':'application/json'"],`;
if(!base.includes('const cases=['))throw Error('original format changed');
const generated=path.join(path.dirname(out),'expanded-controls.js');
fs.writeFileSync(generated,base.replace('const cases=[',extra),{flag:'wx'});
const result=cp.spawnSync(process.execPath,[generated,out],{cwd:root,encoding:'utf8',timeout:60000});
process.stdout.write(result.stdout||'');process.stderr.write(result.stderr||'');
if(result.error)throw result.error;
if(result.status!==0)process.exitCode=result.status||1;
else{const q=JSON.parse(fs.readFileSync(path.join(out,'quality.json'),'utf8'));if(q.controls.length!==10||q.passed!==10)throw Error('expected ten controls');}
