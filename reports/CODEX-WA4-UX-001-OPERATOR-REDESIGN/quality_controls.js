'use strict';
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
const root=process.env.WA4UX_SOURCE_ROOT||process.cwd(),out=path.resolve(process.argv[2]||path.join(require('node:os').tmpdir(),'wa4ux-quality-'+Date.now()));
const relative=path.relative(require('node:os').tmpdir(),out);if(!relative||relative.startsWith('..')||path.isAbsolute(relative)||fs.existsSync(out))throw Error('quality output must be a new disposable TEMP child');fs.mkdirSync(out,{recursive:true});
const tests=fs.readFileSync(path.join(root,'test_web_alarm_operator_ui.js'),'utf8');
const ui=fs.readFileSync(path.join(root,'web_alarm/ui.py'),'utf8');
const cases=[
 ['read-under-lock','UX-C draft snapshot is reread inside acquired lock',
  'view.draft=readDraft(ws)||view.draft','view.draft=view.draft'],
 ['durable-pending-before-post','UX-C quota failure warns and prevents POST',
  'if(!persistDraft()){d.registration=null;showDraft();return}','persistDraft()'],
 ['fresh-copy','O5 offline retains last snapshot visibly stale',
  'if(view.fresh&&view.data?.operator.coherent)copy(view.data.next_safe_action)','if(view.data)copy(view.data.next_safe_action)'],
 ['unknown-blocks-repeat','UX-C lost POST survives reload as unknown',
  '!d.text.trim()||d.registration||!view.catalogFresh','!d.text.trim()||!view.catalogFresh']
];
const results=[];
for(const [id,selector,before,after] of cases){
 if(!ui.includes(before))throw Error('mutation point absent: '+id);
 let source=tests.replace("path.join(__dirname,'web_alarm/ui.py')",JSON.stringify(path.join(root,'web_alarm/ui.py')))
   .replace('const script = source.match','let script = source.match')
   .replace('new vm.Script(script);',`script=script.replace(${JSON.stringify(before)},${JSON.stringify(after)});new vm.Script(script);`);
 const file=path.join(out,'quality-'+id+'.js');fs.writeFileSync(file,source);
 const run=cp.spawnSync(process.execPath,['--test','--test-name-pattern='+selector,file],{encoding:'utf8',timeout:15000,cwd:root});
 const stdout=run.stdout||'',stderr=run.stderr||'';
 fs.writeFileSync(path.join(out,'quality-'+id+'.log'),stdout+stderr);
 const fail=Number(stdout.match(/# fail (\d+)/)?.[1]),pass=Number(stdout.match(/# pass (\d+)/)?.[1]);
 const result={id,selector,expected:'one targeted inner assertion FAIL',exit:run.status,pass,fail,
  skipped:Number(stdout.match(/# skipped (\d+)/)?.[1]||0),trigger_reached:stdout.includes('not ok')&&stdout.includes(selector),
  error_excerpt:stdout.slice(stdout.indexOf('not ok'),stdout.indexOf('not ok')+1700),stderr};
 result.control_passed=run.status===1&&fail===1&&pass===0&&result.trigger_reached&&!stderr;
 results.push(result);console.log(id,result.control_passed?'PASS':'FAIL');
}
fs.writeFileSync(path.join(out,'quality.json'),JSON.stringify({controls:results,passed:results.filter(r=>r.control_passed).length,source_sha256:Object.fromEntries(['web_alarm/ui.py','test_web_alarm_operator_ui.js'].map(n=>[n,require('node:crypto').createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex')]))},null,2));
if(results.some(r=>!r.control_passed))process.exitCode=1;
