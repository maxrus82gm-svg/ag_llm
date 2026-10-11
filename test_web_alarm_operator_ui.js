// Execute the actual shipped client in a deterministic DOM adapter, offline.
// This complements real HTTP tests and real-browser visual checks; it is not a
// substitute for a browser engine. No packages, CDN, network or project writes.
'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname,'web_alarm/ui.py'),'utf8');
const script = source.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script);

class Element {
  constructor(tag='div') {this.tag=tag;this.children=[];this.attrs={};this.dataset={};this.style={};this.hidden=false;this.disabled=false;this.open=false;this.value='';this._text='';}
  set textContent(value) {this._text=String(value);this.children=[];}
  get textContent() {return this._text+this.children.map(c=>c.textContent).join('');}
  append(...children) {this.children.push(...children);}
  replaceChildren(...children) {this._text='';this.children=children;if(this.tag==='select'&&!children.some(c=>c.value===this.value))this.value=children[0]?.value||'';}
  setAttribute(name,value) {this.attrs[name]=value;}
  getAttribute(name) {return this.attrs[name]??null;}
  removeAttribute(name) {delete this.attrs[name];}
  focus() {this.document.activeElement=this;}
}
const clone=x=>JSON.parse(JSON.stringify(x));
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject};};
const settle=async()=>{for(let i=0;i<5;i++)await new Promise(setImmediate);};
function task(tid='task_a',wid='ws_a') {
  const stages=[{microtask_id:'m1',position:1,sequence:1,title:'Verified',goal:'Goal',status:'VERIFIED',prerequisites:[],operations:[],blockers:[],events:[],recovery_reports:[],is_current:false},
    {microtask_id:'m2',position:2,sequence:2,title:'Waiting',goal:'Goal',status:'DONE',prerequisites:['m1'],operations:[],blockers:[],events:[],recovery_reports:[],is_current:true}];
  const projection={task:{location:'active'},position:{current_status:'DONE'},restore_point:{status:'VERIFIED'},blockers:[],diagnostics:[],operations:[],rollbacks:[],recovery:{state:'NORMAL'},advisory_reconciliation:{}};
  return {workspace:{workspace_id:wid,display_name:wid},task_state:{task:{task_id:tid,workspace_id:wid,title:tid,goal:'Goal',raw_task:'RAW',status:'ACTIVE'},projection,plan:{},checkpoint:null},
    operator:{coherent:true,read_at:'2026-10-11T00:00:00Z',progress:{verified:1,total:2,done:1},stages,operations:[],current_operation:null,current_operation_reason:'Not determined',recovery_reports:[],evidence_errors:[]},
    current_microtask_id:'m2',checkpoint_validation:{status:'STALE'},recovery_state:'NORMAL',next_safe_action:'SERVER NEXT · do not retry',authority_source:'lifecycle',recent_events:[],reports:[],manifest:null};
}
function harness(saved=null) {
  const h={calls:[],routes:new Map(),copied:[],confirms:[],intervals:[],events:{},clock:100000,width:1400,confirm:true};
  const elements={};
  for(const match of source.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"[^>]*>/g)){const e=new Element(match[1]);e.id=match[2];e.hidden=match[0].includes(' hidden');elements[e.id]=e;}
  const descendants=()=>{const all=new Set(Object.values(elements));const add=e=>{for(const c of e.children){all.add(c);add(c)}};Object.values(elements).forEach(add);return [...all];};
  const document={hidden:false,activeElement:null,getElementById:id=>elements[id],createElement:tag=>{const e=new Element(tag);e.document=document;return e},querySelectorAll:selector=>descendants().filter(e=>selector==='[data-stage]'?e.dataset.stage:selector==='[data-task]'?e.dataset.task:false)};
  Object.values(elements).forEach(e=>e.document=document);
  const rows=[{task_id:'task_a',workspace_id:'ws_a',title:'task_a',status:'ACTIVE',current_microtask_id:'m2',current_status:'DONE',blockers:[],recovery_state:'NORMAL',created_at:'2020-01-01'},
    {task_id:'task_b',workspace_id:'ws_b',title:'task_b',status:'PLANNED',current_microtask_id:'m1',current_status:'PLANNED',blockers:[],recovery_state:'NORMAL',created_at:'2020-01-02'}];
  const defaultRoute=(url)=>url==='/status'?{service:'WA',mode:'server',api_version:1}:url==='/workspaces'?{workspaces:[{workspace_id:'ws_a',display_name:'A',workspace_root:'temp A'},{workspace_id:'ws_b',display_name:'B',workspace_root:'temp B'}]}:url==='/ui/tasks'?{active:rows,completed:[],errors:[]}:url.includes('task_b')?task('task_b','ws_b'):task();
  h.context=vm.createContext({document,console,AbortController,setTimeout:(fn,ms)=>{const timer=setTimeout(fn,ms);timer.unref();return timer},clearTimeout,
    setInterval:fn=>h.intervals.push(fn),Date:class extends Date{static now(){return h.clock}},
    localStorage:{getItem:()=>saved?JSON.stringify(saved):null,setItem:(_,s)=>{h.saved=JSON.parse(s)}},
    window:{confirm:s=>{h.confirms.push(s);return h.confirm},matchMedia:()=>({matches:h.width<=760}),addEventListener:(e,fn)=>h.events[e]=fn},
    navigator:{clipboard:{writeText:async s=>{if(h.clipboardFail)throw Error('no clipboard');h.copied.push(s)}}},
    fetch:async(url,opts)=>{h.calls.push({url,method:opts.method||'GET',body:opts.body});const value=h.routes.has(url)?await h.routes.get(url)(opts):defaultRoute(url);if(value?.httpError)return {ok:false,status:409,json:async()=>value.data};return {ok:true,status:200,json:async()=>clone(value)}}});
  h.el=id=>elements[id];
  h.run=code=>vm.runInContext(code,h.context);
  vm.runInContext(script,h.context);
  return h;
}

test('O1 workspace filter and task selection never mix details',async()=>{
  const h=harness();await settle();await h.run("selectTask('task_a')");
  assert.equal(h.el('taskHeading').textContent,'task_a');
  h.run("selectWorkspace('ws_b')");
  assert.equal(h.el('detail').hidden,true);
  assert.equal(h.el('activeTasks').children.length,1);
  await h.run("selectTask('task_b')");
  assert.match(h.el('taskIdentity').textContent,/task_b \/ ws_b/);
});
test('O2 timeline shows persisted DONE separately from VERIFIED',async()=>{
  const h=harness();await settle();await h.run("selectTask('task_a')");
  assert.match(h.el('timeline').textContent,/VERIFIED/);
  assert.match(h.el('timeline').textContent,/DONE/);
  assert.equal(h.el('progressText').textContent,'1 / 2 VERIFIED');
  assert.equal(h.el('doneText').textContent,'1 DONE · ожидает проверки');
});
test('O3 inconsistent read has no progress value or usable copy action',async()=>{
  const h=harness();await settle();const v=task();v.operator.coherent=false;v.operator.progress.verified=null;
  h.routes.set('/tasks/task_a/ui',()=>v);await h.run("selectTask('task_a')");
  assert.equal(h.el('progressTrack').getAttribute('aria-valuenow'),null);
  assert.equal(h.el('copyNext').disabled,true);
  assert.match(h.el('freshness').textContent,/изменилось/);
});
test('O4 absent current operation stays undetermined',async()=>{
  const h=harness();await settle();await h.run("selectTask('task_a')");
  assert.match(h.el('operationDetails').textContent,/Не определена/);
});
test('O5 offline retains last snapshot visibly stale and disables copying NEXT',async()=>{
  const h=harness();await settle();await h.run("selectTask('task_a')");
  h.routes.set('/tasks/task_a/ui',()=>{throw new TypeError('offline')});await h.run('loadDetail(view.epoch)');
  assert.equal(h.el('taskHeading').textContent,'task_a');
  assert.match(h.el('freshness').textContent,/предыдущий снимок/);
  assert.equal(h.el('copyNext').disabled,true);
  await h.run("$('copyNext').onclick()");assert.equal(h.copied.length,0);
});
test('O5 ageing snapshot becomes stale without inventing runtime status',async()=>{
  const h=harness();await settle();await h.run("selectTask('task_a')");h.clock+=46000;h.intervals[0]();
  assert.equal(h.el('copyNext').disabled,true);assert.match(h.el('freshness').textContent,/45 секунд/);
  assert.equal(h.el('taskBadge').textContent,'ACTIVE');
});
test('O6 server NEXT copied exactly; no client authority decisions',async()=>{
  const h=harness();await settle();await h.run("selectTask('task_a')");await h.run("$('copyNext').onclick()");
  assert.deepEqual(h.copied,['SERVER NEXT · do not retry']);
});
test('O7 navigation refresh disclosure emit only GET',async()=>{
  const h=harness();await settle();await h.run("selectTask('task_a')");await h.run('refresh()');
  assert.ok(h.calls.every(c=>c.method==='GET'));
});
test('O8 restored browser selection still fetches server-owned state',async()=>{
  const h=harness({workspace:'ws_b',task:'task_b'});await settle();
  assert.equal(h.el('taskHeading').textContent,'task_b');
  assert.ok(h.calls.some(c=>c.url==='/tasks/task_b/ui'));
});
test('O9 old task response cannot repaint new selected task',async()=>{
  const h=harness();await settle();const d=deferred();h.routes.set('/tasks/task_a/ui',()=>d.promise);
  const a=h.run("selectTask('task_a')");await h.run("selectWorkspace('ws_b')");await h.run("selectTask('task_b')");
  d.resolve(task());await a;
  assert.equal(h.el('taskHeading').textContent,'task_b');
  assert.equal(h.saved.task,'task_b');
});
test('O9 loading clears old task details immediately',async()=>{
  const h=harness();await settle();await h.run("selectTask('task_a')");const d=deferred();h.routes.set('/tasks/task_b/ui',()=>d.promise);
  h.run("selectWorkspace('ws_b')");const pending=h.run("selectTask('task_b')");
  assert.equal(h.el('detail').hidden,true);assert.match(h.el('readTime').textContent,/Загрузка/);
  d.resolve(task('task_b','ws_b'));await pending;
});
test('O9 response identity mismatch is an error, never another workspace data',async()=>{
  const h=harness();await settle();h.routes.set('/tasks/task_a/ui',()=>task('task_b','ws_b'));await h.run("selectTask('task_a')");
  assert.equal(h.el('detail').hidden,true);assert.match(h.el('detailError').textContent,/не соответствует/);
});
test('O9 HTML and script input remains text in rendered nodes',async()=>{
  const h=harness();await settle();const v=task();v.task_state.task.title='<svg onload=alert(1)>';v.task_state.task.raw_task='<script>alert(1)</script>';
  h.routes.set('/tasks/task_a/ui',()=>v);await h.run("selectTask('task_a')");
  assert.equal(h.el('taskHeading').textContent,'<svg onload=alert(1)>');
  assert.equal(h.el('taskHeading').children.length,0);assert.equal(h.el('rawTask').children.length,0);
});
test('O9 repeated refresh is single-flight and stable ordering survives update',async()=>{
  const h=harness();await settle();const d=deferred();h.routes.set('/ui/tasks',()=>d.promise);
  const before=h.calls.length;const r=h.run('refresh()');await h.run('refresh()');
  assert.equal(h.calls.length-before,3);assert.equal(h.el('refresh').disabled,true);
  d.resolve({active:[],completed:[],errors:[]});await r;assert.equal(h.el('refresh').disabled,false);
});
test('O9 server refusal shows exact reason and refreshes facts',async()=>{
  const h=harness();await settle();h.routes.set('/tasks',()=>({httpError:true,data:{error:{code:'invalid_field',message:'goal is required'}}}));
  await h.run("create('task')");assert.match(h.el('formError').textContent,/invalid_field: goal is required/);
  assert.ok(h.calls.filter(c=>c.url==='/ui/tasks').length>=2);
});
test('O9 lost POST response never automatically reissues creation',async()=>{
  const h=harness();await settle();h.routes.set('/tasks',()=>{throw new TypeError('response lost')});
  await h.run("create('task')");assert.equal(h.calls.filter(c=>c.method==='POST').length,1);
  assert.match(h.el('formError').textContent,/Результат создания неизвестен/);
  assert.ok(h.calls.filter(c=>c.url==='/ui/tasks').length>=2);
});
test('O9 repeated creation submits once and confirmation captures intent',async()=>{
  const h=harness();await settle();const d=deferred();h.routes.set('/tasks',()=>d.promise);
  const r=h.run("create('task')");await h.run("create('task')");
  assert.equal(h.calls.filter(c=>c.method==='POST').length,1);assert.equal(h.confirms.length,1);
  d.resolve({task:{task_id:'task_a'}});await r;
});
test('O9 cancelled confirmation causes no POST',async()=>{
  const h=harness();await settle();h.confirm=false;await h.run("create('workspace')");assert.ok(h.calls.every(c=>c.method==='GET'));
});
test('O9 empty navigator and unavailable clipboard are honest',async()=>{
  const h=harness();await settle();h.routes.set('/ui/tasks',()=>({active:[],completed:[],errors:[]}));await h.run('refresh()');assert.match(h.el('activeTasks').textContent,/нет/);
  h.clipboardFail=true;await h.run("copy('text')");assert.match(h.el('copyStatus').textContent,/недоступно/);
});
test('O9 narrow selection collapses navigator; desktop resize restores it',async()=>{
  const h=harness();await settle();h.width=390;await h.run("selectTask('task_a')");assert.equal(h.el('navigatorPanel').open,false);
  h.width=1440;h.events.resize();assert.equal(h.el('navigatorPanel').open,true);
});
