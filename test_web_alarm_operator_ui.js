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
function harness(saved=null,storage=new Map(),locks=new Map()) {
  const h={calls:[],routes:new Map(),copied:[],confirms:[],intervals:[],events:{},clock:100000,width:1400,confirm:true};
  h.storage=storage;h.locks=locks;if(saved)storage.set('webAlarm.selection',JSON.stringify(saved));
  const elements={};
  for(const match of source.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"[^>]*>/g)){const e=new Element(match[1]);e.id=match[2];e.hidden=match[0].includes(' hidden');elements[e.id]=e;}
  const descendants=()=>{const all=new Set(Object.values(elements));const add=e=>{for(const c of e.children){all.add(c);add(c)}};Object.values(elements).forEach(add);return [...all];};
  const document={hidden:false,activeElement:null,getElementById:id=>elements[id],createElement:tag=>{const e=new Element(tag);e.document=document;return e},querySelectorAll:selector=>descendants().filter(e=>selector==='[data-stage]'?e.dataset.stage:selector==='[data-task]'?e.dataset.task:false)};
  Object.values(elements).forEach(e=>e.document=document);
  const rows=[{task_id:'task_a',workspace_id:'ws_a',title:'task_a',status:'ACTIVE',current_microtask_id:'m2',current_status:'DONE',blockers:[],recovery_state:'NORMAL',created_at:'2020-01-01'},
    {task_id:'task_b',workspace_id:'ws_b',title:'task_b',status:'PLANNED',current_microtask_id:'m1',current_status:'PLANNED',blockers:[],recovery_state:'NORMAL',created_at:'2020-01-02'}];
  const created=new Map();
  const defaultRoute=(url,opts)=>{
    if(url==='/tasks'&&opts.method==='POST'){
      const body=JSON.parse(opts.body),tid='task_created_'+created.size,v=task(tid,body.workspace_id);
      Object.assign(v.task_state.task,body,{task_id:tid,status:'PLANNED'});
      v.operator.stages=[];v.operator.progress={verified:0,total:0,done:0};created.set(tid,v);
      rows.push({task_id:tid,...body,status:'PLANNED',current_status:'PLANNED',recovery_state:'NORMAL',created_at:'2026-10-14'});
      return {task:v.task_state.task};
    }
    if(url==='/status')return {service:'web_alarm_server',mode:'server',api_version:1};
    if(url==='/workspaces')return {workspaces:[{workspace_id:'ws_a',display_name:'A',workspace_root:'temp A'},{workspace_id:'ws_b',display_name:'B',workspace_root:'temp B'}]};
    if(url==='/ui/tasks')return {active:rows,completed:[],errors:[]};
    const id=url.split('/')[2];return created.get(id)||(url.includes('task_b')?task('task_b','ws_b'):task());
  };
  h.context=vm.createContext({document,console,AbortController,setTimeout:(fn,ms)=>{const timer=setTimeout(fn,ms);timer.unref();return timer},clearTimeout,
    setInterval:fn=>h.intervals.push(fn),Date:class extends Date{static now(){return h.clock}},
    localStorage:{getItem:key=>{if(h.readFail)throw Error('storage read denied');return storage.get(key)??null},
      setItem:(key,s)=>{if(h.writeFail)throw Error('quota exceeded');storage.set(key,s);if(key==='webAlarm.selection')h.saved=JSON.parse(s)},
      removeItem:key=>{if(h.removeFail)throw Error('remove denied');storage.delete(key)}},
    window:{confirm:s=>{h.confirms.push(s);return h.confirm},matchMedia:()=>({matches:h.width<=760}),addEventListener:(e,fn)=>h.events[e]=fn},
    navigator:{locks:{request:async(key,opts,fn)=>{
      if(locks.has(key))return fn(null);const lock={name:key};locks.set(key,lock);
      try{return await fn(lock)}finally{if(locks.get(key)===lock)locks.delete(key)}
    }},clipboard:{writeText:async s=>{if(h.clipboardFail)throw Error('no clipboard');h.copied.push(s)}}},
    fetch:async(url,opts)=>{h.calls.push({url,method:opts.method||'GET',body:opts.body});const value=h.routes.has(url)?await h.routes.get(url)(opts):defaultRoute(url,opts);if(value?.httpError)return {ok:false,status:value.status||409,json:async()=>value.data};return {ok:true,status:200,json:async()=>clone(value)}}});
  h.el=id=>elements[id];
  h.run=code=>vm.runInContext(code,h.context);
  vm.runInContext(script,h.context);
  return h;
}
async function draft(h,value='Проверить контракт\nСохранить исходные данные.'){
  h.run('openDraft()');await settle();h.el('taskRaw').value=value;h.el('taskRaw').oninput();return h;
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
  assert.match(h.el('timeline').textContent,/Подтверждено/);
  assert.match(h.el('timeline').textContent,/ждёт проверки/);
  assert.equal(h.el('progressText').textContent,'Подтверждено 1 / 2');
  assert.equal(h.el('doneText').textContent,'1 выполнено · ожидает проверки');
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
  assert.equal(h.el('taskBadge').children[0].getAttribute('title'),'ACTIVE');
  assert.equal(h.el('taskBadge').textContent,'В работе');
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
  const h=harness();await settle();await draft(h);h.routes.set('/tasks',()=>({httpError:true,data:{error:{code:'invalid_field',message:'goal is required'}}}));
  await h.run("create('task')");assert.match(h.el('draftError').textContent,/invalid_field: goal is required/);
  assert.ok(h.calls.filter(c=>c.url==='/ui/tasks').length>=2);
});
test('O9 lost POST response never automatically reissues creation',async()=>{
  const h=harness();await settle();await draft(h);h.routes.set('/tasks',()=>{throw new TypeError('response lost')});
  await h.run("create('task')");assert.equal(h.calls.filter(c=>c.method==='POST').length,1);
  assert.match(h.el('draftError').textContent,/Исход регистрации неизвестен/);
  assert.ok(h.calls.filter(c=>c.url==='/ui/tasks').length>=2);
});
test('O9 repeated explicit registration submits once without a second form',async()=>{
  const h=harness();await settle();await draft(h);const d=deferred();h.routes.set('/tasks',()=>d.promise);
  const r=h.run("create('task')");await h.run("create('task')");
  assert.equal(h.calls.filter(c=>c.method==='POST').length,1);assert.equal(h.confirms.length,0);
  const body=JSON.parse(h.calls.find(c=>c.method==='POST').body);
  d.resolve({task:{task_id:'task_a',...body}});await r;
});
test('O9 cancelled confirmation causes no POST',async()=>{
  const h=harness();await settle();h.confirm=false;await h.run("create('workspace')");assert.ok(h.calls.every(c=>c.method==='GET'));
});
test('O9 empty navigator and unavailable clipboard are honest',async()=>{
  const h=harness();await settle();h.routes.set('/ui/tasks',()=>({active:[],completed:[],errors:[]}));await h.run('refresh()');assert.match(h.el('activeTasks').textContent,/нет/);
  h.clipboardFail=true;await h.run("copy('text')");assert.match(h.el('copyStatus').textContent,/недоступно/);
});
test('O9 narrow selection closes side panels and focuses the central card',async()=>{
  const h=harness();await settle();h.width=390;h.el('layout').className='layout show-tasks';await h.run("selectTask('task_a')");
  assert.equal(h.el('layout').className,'layout');assert.equal(h.context.document.activeElement,h.el('main'));
});

// REPAIR #1: every export containing NEXT must be gated by a fresh coherent read.
test('O6 context export is forbidden when server read is incoherent',async()=>{
  const h=harness();await settle();const v=task();v.operator.coherent=false;
  h.routes.set('/tasks/task_a/ui',()=>v);await h.run("selectTask('task_a')");
  assert.equal(h.el('copyContext').disabled,true);
  await h.run("$('copyContext').onclick()");
  assert.deepEqual(h.copied,[]);
  assert.match(h.el('copyStatus').textContent,/не скопирован/);
});
test('O5 context export is forbidden after offline response and restored on fresh read',async()=>{
  const h=harness();await settle();await h.run("selectTask('task_a')");
  assert.equal(h.el('copyContext').disabled,false);
  h.routes.set('/tasks/task_a/ui',()=>{throw new TypeError('offline')});
  await h.run('loadDetail(view.epoch)');
  assert.equal(h.el('copyContext').disabled,true);
  await h.run("$('copyContext').onclick()");
  assert.deepEqual(h.copied,[]);
  h.routes.delete('/tasks/task_a/ui');
  await h.run('loadDetail(view.epoch)');
  assert.equal(h.el('copyContext').disabled,false);
  await h.run("$('copyContext').onclick()");
  assert.equal(h.copied.length,1);
  assert.match(h.copied[0],/NEXT SAFE ACTION: SERVER NEXT/);
});
test('O9 context export is forbidden after 45-second freshness timeout',async()=>{
  const h=harness();await settle();await h.run("selectTask('task_a')");
  h.clock+=46000;h.intervals[0]();
  assert.equal(h.el('copyContext').disabled,true);
  await h.run("$('copyContext').onclick()");
  assert.deepEqual(h.copied,[]);
});

test('UX-C empty plus is ephemeral: no draft record, task or POST on leave',async()=>{
  const h=harness();await settle();h.run('openDraft()');await settle();
  assert.equal(h.el('draftPanel').hidden,false);assert.equal(h.el('detail').hidden,true);
  assert.equal(h.el('taskRaw').value,'');assert.equal(h.el('createTask').disabled,true);
  h.run("selectWorkspace('ws_b')");
  assert.equal([...h.storage.keys()].filter(k=>k.startsWith('webAlarm.draft')).length,0);
  assert.equal(h.confirms.length,0);assert.ok(h.calls.every(c=>c.method==='GET'));
});
test('UX-C autosave stores exact original text as browser draft, not server status',async()=>{
  const h=harness();await settle();const value='  Исходник\n<script>not executable</script>\n  ';await draft(h,value);
  const d=JSON.parse(h.storage.get(h.run('view.draft.key')));
  assert.equal(d.text,value);assert.equal(d.workspace_id,'ws_a');assert.equal(d.workspace_root,'temp A');
  assert.equal(d.registration,null);assert.equal(d.status,undefined);assert.equal(d.task_id,undefined);
  assert.match(h.el('draftStatus').textContent,/сохранён в этом браузере/);assert.ok(h.calls.every(c=>c.method==='GET'));
});
test('UX-C returning to draft and reload restore text without server creation',async()=>{
  const h=harness();await settle();await draft(h,'Текст A');const storage=new Map(h.storage);
  h.run("selectTask('task_a')");await settle();h.run('openDraft()');await settle();assert.equal(h.el('taskRaw').value,'Текст A');
  const reload=harness(null,storage);await settle();assert.equal(reload.el('taskRaw').value,'Текст A');
  assert.equal(reload.el('draftPanel').hidden,false);assert.ok(reload.calls.every(c=>c.method==='GET'));
});
test('UX-C drafts and task rows remain isolated across workspace switches',async()=>{
  const h=harness();await settle();await draft(h,'Проект A');h.run("selectWorkspace('ws_b')");await draft(h,'Проект B');
  assert.equal(h.el('activeTasks').children.length,1);assert.match(h.el('activeTasks').textContent,/task_b/);
  h.run("selectWorkspace('ws_a')");h.run('openDraft()');await settle();assert.equal(h.el('taskRaw').value,'Проект A');
  assert.equal([...h.storage.keys()].filter(k=>k.startsWith('webAlarm.draft')).length,2);
});
test('UX-C quota failure warns and prevents POST and accidental unsaved navigation',async()=>{
  const h=harness();await settle();h.writeFail=true;await draft(h,'Не потерять');
  assert.equal(h.run('view.draft.dirty'),true);assert.match(h.el('draftStatus').textContent,/Не сохранён/);
  const event={preventDefault(){this.prevented=true}};h.events.beforeunload(event);assert.equal(event.prevented,true);
  h.confirm=false;h.run("selectWorkspace('ws_b')");assert.equal(h.run('view.workspace'),'ws_a');
  await h.run("create('task')");assert.equal(h.calls.filter(c=>c.method==='POST').length,0);
  h.writeFail=false;h.el('taskRaw').oninput();assert.equal(h.run('view.draft.dirty'),false);
});
test('UX-C saved or empty forms do not request beforeunload confirmation',async()=>{
  const h=harness();await settle();await draft(h,'Сохранено');
  for(const value of ['Сохранено','']){h.el('taskRaw').value=value;h.el('taskRaw').oninput();const e={preventDefault(){this.prevented=true}};h.events.beforeunload(e);assert.equal(e.prevented,undefined)}
});
test('UX-C malformed draft bytes are retained and never overwritten',async()=>{
  const h=harness();await settle();const key=h.run('draftKey()');h.storage.set(key,'{broken');h.run('openDraft()');await settle();
  assert.equal(h.storage.get(key),'{broken');assert.equal(h.el('taskRaw').readOnly,true);assert.equal(h.el('createTask').disabled,true);
  h.el('taskRaw').value='new';h.el('taskRaw').oninput();assert.equal(h.storage.get(key),'{broken');assert.match(h.el('draftError').textContent,/JSON|Expected|property/);
});
test('UX-C storage read denial and missing Web Locks never authorize registration',async()=>{
  const h=harness();await settle();h.readFail=true;h.run('openDraft()');await settle();
  assert.equal(h.el('createTask').disabled,true);h.readFail=false;h.run('delete navigator.locks');h.run('openDraft()');await settle();
  assert.equal(h.el('taskRaw').readOnly,true);assert.match(h.el('draftError').textContent,/не поддерживает/);
  await h.run("create('task')");assert.equal(h.calls.filter(c=>c.method==='POST').length,0);
});
test('UX-C second tab cannot overwrite a locked draft; reopening reads latest text',async()=>{
  const a=harness();await settle();await draft(a,'Первый');const b=harness(null,a.storage,a.locks);await settle();
  b.run('openDraft()');await settle();assert.equal(b.el('taskRaw').readOnly,true);
  a.el('taskRaw').value='Последняя версия';a.el('taskRaw').oninput();
  b.el('taskRaw').value='Перезаписать';b.el('taskRaw').oninput();assert.equal(JSON.parse(a.storage.get(a.run('draftKey()'))).text,'Последняя версия');
  a.run("selectWorkspace('ws_b')");await settle();b.run('openDraft()');await settle();assert.equal(b.el('taskRaw').value,'Последняя версия');assert.equal(b.el('taskRaw').readOnly,false);
});
test('UX-C draft snapshot is reread inside acquired lock, closing the read/acquire gap',async()=>{
  const h=harness();await settle();let acquire;
  h.context.navigator.locks.request=(key,options,fn)=>{acquire=fn;return new Promise(()=>{})};
  h.run('openDraft()');const key=h.run('draftKey()');
  h.storage.set(key,JSON.stringify({schema:1,workspace_id:'ws_a',workspace_root:'temp A',text:'Changed before acquisition',registration:null,updated_at:'2026-10-14'}));
  acquire({name:key});assert.equal(h.el('taskRaw').value,'Changed before acquisition');
});
test('UX-C late lock callback cannot reopen a composer in another workspace',async()=>{
  const h=harness();await settle();let acquire;h.context.navigator.locks.request=(k,o,fn)=>{acquire=fn;return new Promise(()=>{})};
  h.run('openDraft()');h.run("selectWorkspace('ws_b')");acquire({});
  assert.equal(h.run('view.mode'),'task');assert.equal(h.el('draftPanel').hidden,true);assert.equal(h.run('view.draftWritable'),false);
});
test('UX-C registration uses one field, server ID and no planner or execution routes',async()=>{
  const h=harness();await settle();await draft(h,'  Заголовок\nПолная цель\n  ');await h.run("create('task')");
  const posts=h.calls.filter(c=>c.method==='POST');assert.equal(posts.length,1);assert.equal(posts[0].url,'/tasks');
  assert.deepEqual(JSON.parse(posts[0].body),{workspace_id:'ws_a',title:'Заголовок',goal:'Заголовок\nПолная цель',raw_task:'Заголовок\nПолная цель'});
  assert.equal(h.run('view.task'),'task_created_0');assert.equal(h.el('timeline').children[0].textContent,'План ещё не содержит этапов.');
  assert.equal([...h.storage.keys()].filter(k=>k.startsWith('webAlarm.draft')).length,0);
  h.run('openDraft()');await settle();assert.equal(h.el('taskRaw').value,'');
});
test('UX-C lost POST survives reload as unknown; never resubmit or delete automatically',async()=>{
  const h=harness();await settle();await draft(h,'Не повторять');h.routes.set('/tasks',()=>{throw Error('wire lost')});await h.run("create('task')");
  const storage=new Map(h.storage);await h.run("create('task')");h.el('discardDraft').onclick();
  assert.equal(h.calls.filter(c=>c.method==='POST').length,1);assert.match(h.el('draftStatus').textContent,/неизвестен/);
  const reload=harness(null,storage);await settle();await reload.run("create('task')");
  assert.equal(reload.el('taskRaw').value,'Не повторять');assert.equal(reload.el('taskRaw').readOnly,true);assert.ok(reload.calls.every(c=>c.method==='GET'));
});
test('UX-C server 500 or malformed acknowledgement stays unknown without second POST',async()=>{
  for(const response of [{httpError:true,status:500,data:{error:{code:'storage_error',message:'after commit unknown'}}},{task:{task_id:'wrong',workspace_id:'ws_b'}}]){
    const h=harness();await settle();await draft(h);h.routes.set('/tasks',()=>response);await h.run("create('task')");await h.run("create('task')");
    assert.equal(h.calls.filter(c=>c.method==='POST').length,1);assert.equal(h.run('view.draft.registration.state'),'unknown');
  }
});
test('UX-C in-flight registration cannot repaint or clear another workspace draft',async()=>{
  const h=harness();await settle();await draft(h,'A');const d=deferred();h.routes.set('/tasks',()=>d.promise);const pending=h.run("create('task')");
  h.run("selectWorkspace('ws_b')");await draft(h,'B');const key=h.run('view.draft.key');
  d.resolve({task:{task_id:'made_a',workspace_id:'ws_a',title:'A',goal:'A',raw_task:'A'}});await pending;
  assert.equal(h.run('view.workspace'),'ws_b');assert.equal(h.el('taskRaw').value,'B');assert.equal(JSON.parse(h.storage.get(key)).text,'B');assert.equal(h.el('detail').hidden,true);
});
test('UX-C deleting browser draft never deletes a registered TASK or emits HTTP DELETE',async()=>{
  const h=harness();await settle();await draft(h,'Удалить только черновик');h.el('discardDraft').onclick();
  assert.equal([...h.storage.keys()].filter(k=>k.startsWith('webAlarm.draft')).length,0);assert.equal(h.el('activeTasks').children.length,1);assert.ok(h.calls.every(c=>c.method==='GET'));
});
test('UX-C missing workspace blocks registration while preserving local text',async()=>{
  const h=harness();await settle();await draft(h,'Не потерять при удалении проекта');h.routes.set('/workspaces',()=>({workspaces:[]}));await h.run('refresh()');
  assert.equal(h.el('taskRaw').value,'Не потерять при удалении проекта');assert.equal(h.el('createTask').disabled,true);assert.match(h.el('navigationError').textContent,/больше не подтверждён/);
});
test('UX connection uses real health, ages explicitly and survives failure without changing enums',async()=>{
  const h=harness();await settle();assert.equal(h.el('serverStatus').getAttribute('data-state'),'online');
  h.clock+=46000;h.intervals[0]();assert.match(h.el('serverStatus').textContent,/устарела/);
  h.routes.set('/status',()=>{throw Error('offline')});await h.run('refresh()');assert.equal(h.el('serverStatus').getAttribute('data-state'),'offline');
  h.routes.delete('/status');await h.run('refresh()');assert.equal(h.el('serverStatus').getAttribute('data-state'),'online');
});
test('UX catalog failure does not mislabel reachable server or authorize POST',async()=>{
  const h=harness();await settle();await draft(h,'Local');h.routes.set('/ui/tasks',()=>{throw Error('bad catalog')});await h.run('refresh()');
  assert.equal(h.el('serverStatus').getAttribute('data-state'),'online');assert.equal(h.el('createTask').disabled,true);assert.equal(h.el('taskRaw').value,'Local');
});
test('UX task source and human stage reports are complete inert text',async()=>{
  const h=harness();await settle();const v=task(),report='<svg onload=bad()>\n'+('Длинный отчёт\n'.repeat(2000));v.task_state.task.raw_task='RAW\n'+('Длинная постановка\n'.repeat(2000));
  v.operator.stages[0].events=[{event_type:'REPORT',payload:{report}}];h.routes.set('/tasks/task_a/ui',()=>v);await h.run("selectTask('task_a')");
  assert.equal(h.el('taskDescription').textContent,v.task_state.task.raw_task);assert.match(h.el('timeline').textContent,/Длинный отчёт/);assert.ok(h.el('timeline').textContent.includes(report));
  assert.equal(h.el('taskDescription').children.length,0);assert.equal(h.el('timeline').children[0].children[1].children.find(e=>e.tag==='details').children[1].children.length,0);
});
test('UX task response arriving after plus never paints over the blank composer',async()=>{
  const h=harness();await settle();const d=deferred();h.routes.set('/tasks/task_a/ui',()=>d.promise);const pending=h.run("selectTask('task_a')");h.run('openDraft()');await settle();d.resolve(task());await pending;
  assert.equal(h.el('draftPanel').hidden,false);assert.equal(h.el('detail').hidden,true);assert.equal(h.run('view.data'),null);
});
test('UX UNKNOWN recovery is human readable without changing the machine state',async()=>{
  const h=harness();await settle();const v=task();v.recovery_state='RECONCILIATION_REQUIRED';v.operator.stages[1].status='UNKNOWN_AFTER_DISCONNECT';
  h.routes.set('/tasks/task_a/ui',()=>v);await h.run("selectTask('task_a')");
  assert.equal(h.el('recoveryBadge').textContent,'Нужна сверка состояния');assert.match(h.el('timeline').textContent,/Исход неизвестен после обрыва/);
  assert.equal(h.el('recoveryBadge').children[0].getAttribute('title'),'RECONCILIATION_REQUIRED');assert.equal(h.run('view.data.operator.stages[1].status'),'UNKNOWN_AFTER_DISCONNECT');
});
test('UX workspace registration cannot discard an unsaved active draft',async()=>{
  const h=harness();await settle();h.writeFail=true;await draft(h,'Unsaved text');h.routes.set('/workspaces',opts=>opts.method==='POST'?{workspace:{workspace_id:'new'}}:{workspaces:[{workspace_id:'ws_a',display_name:'A',workspace_root:'temp A'}]});
  await h.run("create('workspace')");assert.equal(h.el('taskRaw').value,'Unsaved text');assert.equal(h.run('view.mode'),'draft');assert.equal(h.run('view.draft.dirty'),true);
});
test('UX failed local cleanup after confirmed creation never enables duplicate registration',async()=>{
  const h=harness();await settle();await draft(h,'Known acknowledgement');h.removeFail=true;await h.run("create('task')");
  h.run('openDraft()');await settle();assert.match(h.el('draftStatus').textContent,/ранее подтвердил/);assert.equal(h.el('createTask').disabled,true);await h.run("create('task')");assert.equal(h.calls.filter(c=>c.method==='POST').length,1);
});
