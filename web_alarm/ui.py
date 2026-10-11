"""WA4-O operator panel; all execution facts come from server read models."""

INDEX_HTML = r'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Web Alarm Workspace</title>
<style>
:root{color-scheme:dark;--bg:#10151d;--panel:#17212c;--line:#344454;--text:#edf3fa;--muted:#adbdcd;--blue:#8ec9ff;--green:#8ee0ba;--amber:#ffd28e;--red:#ffaaaa;--purple:#d1b4ff;font-family:system-ui,Segoe UI,sans-serif;background:var(--bg);color:var(--text)}

*{box-sizing:border-box}
body{margin:0}
button,input,select,textarea{font:inherit}
button{cursor:pointer}
button,input,select,textarea,summary{border-radius:8px}
button{background:#243748;color:var(--text);border:1px solid #506579;padding:9px 12px}
button:hover{background:#304c63}
button:disabled{opacity:.55;cursor:default}
:focus-visible{outline:3px solid var(--blue);outline-offset:3px}
input,select,textarea{width:100%;padding:10px;border:1px solid #506579;background:#111b26;color:var(--text)}
textarea{min-height:110px;resize:vertical}
label{display:block;margin:12px 0 5px;font-size:13px}
h1,h2,h3,p{margin:0}
h1{font-size:18px}
h2{font-size:18px}
h3{font-size:15px}
p{line-height:1.55}
small,.muted{color:var(--muted);font-size:13px;line-height:1.5}
.top{position:sticky;top:0;z-index:3;background:#111b26;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 24px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:12px}
.logo{display:grid;place-items:center;background:#263e52;border:1px solid #557893;border-radius:12px;width:38px;height:38px;color:var(--blue);font-weight:800}
.top-actions,.row{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.top label{display:flex;align-items:center;gap:7px;margin:0}
.top input{width:auto}
.layout{display:grid;grid-template-columns:300px minmax(0,1fr);max-width:1700px;margin:auto;min-height:calc(100vh - 73px)}
aside{padding:22px 16px;border-right:1px solid var(--line);background:#121c27}
main{min-width:0;padding:26px 30px 44px}
.eyebrow{color:var(--blue);font-size:11px;font-weight:700;letter-spacing:.13em;text-transform:uppercase}
.section-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:16px}
.section-head h2{font-size:16px}
.card{border:1px solid var(--line);background:var(--panel);padding:20px;border-radius:14px;margin-bottom:18px;min-width:0}
.task-list{display:grid;gap:9px;margin:12px 0 20px}
.task-button{width:100%;text-align:left;background:#182431;border:1px solid #344454;padding:13px;line-height:1.4;overflow-wrap:anywhere}
.task-button[aria-current=true]{background:#213b50;border-color:var(--blue);box-shadow:inset 3px 0 var(--blue)}
.task-button strong,.task-button small{display:block}
.task-button small{margin-top:6px}
.tag{display:inline-block;padding:4px 8px;border-radius:6px;border:1px solid #506579;background:#1c2b38;font:600 11px ui-monospace,Consolas,monospace;letter-spacing:.03em;color:var(--text);overflow-wrap:anywhere}
.tag.good{color:var(--green);background:#19362d;border-color:#3b7360}
.tag.active{color:var(--blue);background:#1c3650}
.tag.warn{color:var(--amber);background:#39301e;border-color:#7b6439}
.tag.bad{color:var(--red);background:#3b242b;border-color:#86505b}
.tag.unknown{color:var(--purple);background:#30283f;border-color:#705687}
.overview-top{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}
.overview h2{font-size:27px;line-height:1.25;margin:9px 0 12px;overflow-wrap:anywhere}
.overview .goal{color:#d0ddea;max-width:850px;margin:12px 0 20px}
.meta{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.id{font:12px ui-monospace,Consolas,monospace;overflow-wrap:anywhere}
.progress-line{display:flex;gap:20px;justify-content:space-between;margin:18px 0 8px;font-size:13px}
.track{height:7px;background:#0c131a;border-radius:20px;overflow:hidden}
.track span{display:block;height:100%;background:var(--green);width:0}
.facts{display:flex;gap:20px;flex-wrap:wrap;margin-top:18px}
.facts>div{display:grid;gap:6px;min-width:150px}
.facts .tag{width:fit-content}
.next-card{border-color:#5c7995;background:linear-gradient(115deg,#1a3042,#182532);position:relative}
.next-card h2{font:700 12px ui-monospace,Consolas,monospace;letter-spacing:.09em;color:var(--blue);margin-bottom:14px}
.next-text{font-size:16px;line-height:1.6;white-space:pre-wrap;overflow-wrap:anywhere}
.next-footer{display:flex;gap:12px;justify-content:space-between;align-items:center;margin-top:16px;flex-wrap:wrap}
.columns{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:18px}
.stage{border:1px solid var(--line);border-radius:10px;margin:9px 0;background:#131e29;overflow:hidden}
.stage.current{border-color:#81b7e4}
.stage summary{display:flex;align-items:center;gap:12px;padding:13px;cursor:pointer;list-style:none}
.stage summary::after{content:'⌄';color:var(--muted);margin-left:auto}
.stage summary .title{flex:1;min-width:0;overflow-wrap:anywhere}
.stage-number{display:grid;place-items:center;width:29px;height:29px;flex-shrink:0;border:1px solid #64768a;border-radius:50%;font-size:12px}
.stage-body{padding:0 16px 16px 54px;line-height:1.55}
.stage-body p{margin-bottom:9px;overflow-wrap:anywhere}
.stage-body details{margin-top:12px}
.operation-grid{display:grid;grid-template-columns:110px minmax(0,1fr);gap:10px;font-size:13px;margin:16px 0}
.operation-grid dt{color:var(--muted)}
.operation-grid dd{margin:0;overflow-wrap:anywhere}
.notice{padding:12px 14px;border:1px solid #795d37;background:#31291c;color:var(--amber);border-radius:9px;font-size:13px;line-height:1.5;margin:12px 0;white-space:pre-wrap;overflow-wrap:anywhere}
.notice.error{border-color:#8b5661;background:#322129;color:#ffbbbb}
.notice.info{border-color:#526c85;background:#1b2d3c;color:#c4def7}
.empty{padding:44px 24px;text-align:center;color:var(--muted);border:1px dashed #526579;border-radius:14px}
.empty h2{color:var(--text);margin-bottom:12px}
.evidence details{border-top:1px solid var(--line);padding:13px 0}
.evidence details:first-of-type{margin-top:12px}
summary{cursor:pointer;font-size:14px;line-height:1.45}
pre{font:12px/1.55 ui-monospace,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:350px;overflow:auto;background:#101821;padding:14px;border-radius:8px;margin-bottom:0}
.creation{border-top:1px solid var(--line);padding:16px 0}
.creation button{margin-top:14px;width:100%}
.creation summary{font-weight:600}
.recovery-list{padding-left:20px;font-size:13px;line-height:1.6;overflow-wrap:anywhere}
.spaced{margin-top:12px}
.live{font-size:12px;color:var(--muted)}
[hidden]{display:none!important}
.skip{position:absolute;left:12px;top:-80px}
.skip:focus{top:12px;z-index:10;background:var(--panel);padding:12px;color:var(--text)}

.mobile-nav{display:none}

@media(max-width:1150px){.columns{grid-template-columns:1fr}
.layout{grid-template-columns:260px minmax(0,1fr)}
main{padding:22px 20px}
}

@media(max-width:760px){.mobile-nav{display:list-item;font-weight:700;padding:8px 0}
#navigatorPanel:not([open])>*:not(summary){display:none}
.top{position:static;padding:14px 16px;align-items:flex-start;flex-wrap:wrap}
.top-actions{width:100%;justify-content:space-between}
.layout{grid-template-columns:1fr}
aside{border-right:0;border-bottom:1px solid var(--line);padding:18px}
.task-list{max-height:270px;overflow:auto}
main{padding:20px 14px}
.card{padding:16px}
.overview h2{font-size:23px}
.overview-top{flex-wrap:wrap}
.stage summary{gap:8px;flex-wrap:wrap}
.stage summary .title{flex-basis:45%}
.stage-body{padding-left:16px}
.facts{gap:14px}
.operation-grid{grid-template-columns:90px minmax(0,1fr)}
}

</style>
</head>
<body>
<a class="skip" href="#main">К состоянию TASK</a>
<header class="top">
<div class="brand">
<span class="logo" aria-hidden="true">WA</span>
<div>
<h1>Web Alarm Workspace</h1>
<div class="live" id="serverStatus" role="status">Подключение…</div>
</div>
</div>
<div class="top-actions">
<label>
<input type="checkbox" id="autoRefresh"> Наблюдать · 15 с</label>
<button id="refresh">↻ Обновить</button>
</div>
</header>
<div class="layout">
<aside aria-label="Workspace и TASK">
<details id="navigatorPanel" open>
<summary class="mobile-nav">Навигатор Workspace / TASK</summary>
<div class="section-head">
<h2>Рабочие пространства</h2>
<span class="eyebrow">Навигатор</span>
</div>
<label for="workspaceSelect">Workspace</label>
<select id="workspaceSelect">
<option value="">Загрузка…</option>
</select>
<p class="muted spaced" id="workspacePath">
</p>
<div id="navigationError" class="notice error" role="alert" hidden>
</div>
<h3 class="spaced">Активные TASK</h3>
<div id="activeTasks" class="task-list">
</div>
<details id="completedGroup">
<summary>Завершённые TASK <span id="completedCount">
</span>
</summary>
<div id="completedTasks" class="task-list">
</div>
</details>
<details class="creation">
<summary>Добавить Workspace</summary>
<form id="workspaceForm">
<label for="wsName">Название</label>
<input id="wsName" required maxlength="300" placeholder="Название проекта">
<label for="wsRoot">Локальный путь</label>
<input id="wsRoot" required placeholder="M:\Projects\project">
<button id="createWorkspace" type="submit">Добавить Workspace</button>
</form>
</details>
<details class="creation">
<summary>Новая TASK</summary>
<form id="taskForm">
<label for="taskWorkspace">Workspace</label>
<select id="taskWorkspace" required>
</select>
<label for="taskTitle">Название</label>
<input id="taskTitle" required maxlength="500">
<label for="taskGoal">Цель</label>
<textarea id="taskGoal" required>
</textarea>
<label for="taskRaw">RAW TASK</label>
<textarea id="taskRaw" required placeholder="Исходная постановка целиком">
</textarea>
<button id="createTask" type="submit">Создать TASK</button>
</form>
</details>
<div id="formError" class="notice error" role="alert" hidden>
</div>
<p class="muted spaced">Создание — после подтверждения. Состояние исполнения управляется сервером.</p>
</details>
</aside>
<main id="main" tabindex="-1">
<div class="section-head">
<span class="eyebrow">Операторская панель</span>
<span id="readTime" class="live" role="status">Нет выбранной TASK</span>
</div>
<div id="detailError" class="notice error" role="alert" hidden>
</div>
<div id="freshness" class="notice" role="status" hidden>
</div>
<div id="emptyDetail" class="empty">
<h2>Выберите TASK</h2>
<p>Откройте рабочее пространство и задачу слева.<br>Прогресс, текущая операция и безопасный следующий шаг появятся здесь.</p>
</div>
<div id="detail" hidden aria-busy="false">
<section class="card overview" aria-labelledby="taskHeading">
<div class="overview-top">
<div>
<p class="eyebrow" id="taskLocation">
</p>
<h2 id="taskHeading">
</h2>
<p class="id muted" id="taskIdentity">
</p>
</div>
<div id="taskBadge">
</div>
</div>
<p class="goal" id="taskGoalText">
</p>
<div class="progress-line">
<strong id="progressText">
</strong>
<span class="muted" id="doneText">
</span>
</div>
<div id="progressTrack" class="track" role="progressbar" aria-label="Подтверждённые этапы" aria-valuemin="0">
<span id="progressFill">
</span>
</div>
<div class="facts">
<div>
<small>Текущий этап · RC-5</small>
<strong id="currentStage">
</strong>
</div>
<div>
<small>Checkpoint · validation</small>
<div id="checkpointBadge">
</div>
</div>
<div>
<small>Restore point · integrity</small>
<div id="snapshotBadge">
</div>
</div>
</div>
</section>
<section class="card next-card" aria-labelledby="nextHeading">
<h2 id="nextHeading">NEXT SAFE ACTION</h2>
<p id="nextSafeAction" class="next-text">
</p>
<div class="next-footer">
<small id="nextSource">
</small>
<button id="copyNext">Копировать шаг</button>
</div>
<p class="muted spaced">Это серверная рекомендация. Панель не выполняет её автоматически.</p>
</section>
<div class="columns">
<section class="card" aria-labelledby="timelineHeading">
<div class="section-head">
<h2 id="timelineHeading">Этапы TASK</h2>
<span class="muted">По порядку плана</span>
</div>
<p class="muted">DONE — ожидает проверки. VERIFIED — подтверждённый этап.</p>
<div id="timeline">
</div>
</section>
<div>
<section class="card" aria-labelledby="operationHeading">
<div class="section-head">
<h2 id="operationHeading">Текущая операция</h2>
<div id="operationBadge">
</div>
</div>
<p class="muted" id="operationReason">
</p>
<dl id="operationDetails" class="operation-grid">
</dl>
</section>
<section class="card" aria-labelledby="recoveryHeading">
<div class="section-head">
<h2 id="recoveryHeading">Recovery state</h2>
<div id="recoveryBadge">
</div>
</div>
<p class="muted">Обрыв ответа не означает FAILED. UNKNOWN требует reconciliation; автоматического retry здесь нет.</p>
<div id="recoveryFacts">
</div>
</section>
</div>
</div>
<section class="card evidence" aria-labelledby="evidenceHeading">
<div class="section-head">
<h2 id="evidenceHeading">Доказательства и диагностика</h2>
<button id="copyContext">Копировать контекст</button>
</div>
<p class="muted">Исторические события и receipts не заменяют текущую Projection.</p>
<details>
<summary>Manifest / Snapshot</summary>
<pre id="manifest">
</pre>
</details>
<details>
<summary>Checkpoint и validation</summary>
<pre id="checkpoint">
</pre>
</details>
<details>
<summary>Recent events · история</summary>
<pre id="events">
</pre>
</details>
<details>
<summary>Operation history / receipt</summary>
<pre id="operations">
</pre>
</details>
<details>
<summary>Recovery reports / Resolver</summary>
<pre id="recovery">
</pre>
</details>
<details>
<summary>Отчёты этапов</summary>
<pre id="reports">
</pre>
</details>
<details>
<summary>RAW TASK</summary>
<pre id="rawTask">
</pre>
</details>
<details>
<summary>План и диагностика Projection</summary>
<pre id="plan">
</pre>
</details>
</section>
</div>
<div id="copyStatus" class="live" role="status">
</div>
</main>
</div>
<script>
'use strict';
const $=id=>document.getElementById(id);
const view={
  workspace:null,task:null,data:null,loadedAt:0,fresh:false,epoch:0,refreshing:false,creating:false,workspaces:[],tasks:null
}
;
function text(id,value){
  $(id).textContent=value==null?'—':String(value)
}
function notice(id,value){
  text(id,value);
  $(id).hidden=!value
}
function element(tag,value,cls){
  const e=document.createElement(tag);
  if(value!=null)e.textContent=String(value);
  if(cls)e.className=cls;
  return e
}
function statusClass(s){
  return s==='VERIFIED'||s==='VALID'?'good':['ACTIVE','READY','STARTED'].includes(s)?'active':['FAILED','FAILED_VERIFICATION','CORRUPT','INCONSISTENT','PROJECTION_BLOCKED','BLOCKED_PREPARE'].includes(s)?'bad':s.includes('UNKNOWN')||s.includes('PARTIAL')?'unknown':['STALE','DONE','RECOVERY_REQUIRED','NOT_VERIFIED'].includes(s)?'warn':''
}
function badge(s){
  const value=String(s??'Неизвестно');
  return element('span',value,'tag '+statusClass(value))
}
async function api(path,options={
}
){
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),15000);
  try{
    const opts={
      ...options,signal:controller.signal,cache:'no-store'
    }
    ;
    if(opts.body){
      opts.body=JSON.stringify(opts.body);
      opts.headers={
        'Content-Type':'application/json'
      }
    }
    const r=await fetch(path,opts);
    let data;
    try{
      data=await r.json()
    }
    catch(_){
      throw new Error('Некорректный ответ сервера · HTTP '+r.status)
    }
    if(!r.ok){
      const e=new Error((data.error?.code||'HTTP '+r.status)+': '+(data.error?.message||'Запрос отклонён'));
      e.details=data.error?.details;
      e.serverRejected=true;
      throw e
    }
    return data
  }
  finally{
    clearTimeout(timer)
  }
}
function saveSelection(){
  try{
    localStorage.setItem('webAlarm.selection',JSON.stringify({
      workspace:view.workspace,task:view.task
    }
    ))
  }
  catch(_){
  }
}
function setFresh(fresh,message=''){
  view.fresh=fresh;
  notice('freshness',message);
  // Context also contains NEXT SAFE ACTION; never export it from a stale read.
  const canCopy=fresh&&Boolean(view.data?.operator.coherent);
  $('copyNext').disabled=!canCopy;
  $('copyContext').disabled=!canCopy
}
function clearDetail(){
  view.data=null;
  view.loadedAt=0;
  setFresh(false);
  $('detail').hidden=true;
  $('emptyDetail').hidden=false;
  notice('detailError','');
  text('readTime',view.task?'Загрузка выбранной TASK…':'Нет выбранной TASK')
}
function selectWorkspace(id){
  view.epoch++;
  view.workspace=id||null;
  view.task=null;
  saveSelection();
  clearDetail();
  renderNavigation()
}
async function selectTask(id){
  view.epoch++;
  view.task=id;
  saveSelection();
  clearDetail();
  renderNavigation();
  if(window.matchMedia('(max-width:760px)').matches){
    $('navigatorPanel').open=false;
    $('main').focus({
      preventScroll:true
    }
    );
  }
  await loadDetail(view.epoch)
}
function taskButton(t){
  const b=element('button',null,'task-button');
  b.type='button';
  b.dataset.task=t.task_id;
  b.setAttribute('aria-current',String(view.task===t.task_id));
  b.append(element('strong',t.title),element('small',t.task_id,'id'),badge(t.status),element('small','Этап: '+(t.current_microtask_id||'не определён')+' · '+t.current_status));
  if(t.blockers?.length)b.append(element('small','Блокер: '+t.blockers[0].code));
  else if(t.recovery_state!=='NORMAL')b.append(element('small','Recovery: '+t.recovery_state));
  b.onclick=()=>selectTask(t.task_id);
  return b
}
function renderNavigation(){
  const focused=document.activeElement?.dataset?.task;
  const ws=view.workspaces.find(w=>w.workspace_id===view.workspace);
  text('workspacePath',ws?.workspace_root||'Нет зарегистрированных Workspace');
  $('workspaceSelect').value=view.workspace||'';
  const rows=view.tasks||{
    active:[],completed:[],errors:[]
  }
  ;
  const stable=a=>a.filter(t=>t.workspace_id===view.workspace).sort((a,b)=>a.created_at.localeCompare(b.created_at)||a.task_id.localeCompare(b.task_id));
  for(const key of ['active','completed']){
    const tasks=stable(rows[key]);
    $(key+'Tasks').replaceChildren(...(tasks.length?tasks.map(taskButton):[element('p',key==='active'?'Активных TASK нет':'Завершённых TASK нет','muted')]));
    if(key==='completed'){
      text('completedCount','('+tasks.length+')');
      if(tasks.some(t=>t.task_id===view.task))$('completedGroup').open=true
    }
  }
  if(focused){
    for(const b of document.querySelectorAll('[data-task]'))if(b.dataset.task===focused)b.focus({
      preventScroll:true
    }
    )
  }
  if(rows.errors?.length)notice('navigationError','Недоступные TASK (Workspace не подтверждён):\n'+rows.errors.map(e=>e.task_id+': '+e.reason).join('\n'))
}
function field(dl,name,value){
  dl.append(element('dt',name),element('dd',value??'Не определено'))
}
function render(v){
  const o=v.operator,p=v.task_state.projection,t=v.task_state.task;
  const opened=new Set([...document.querySelectorAll('[data-stage]')].filter(e=>e.open).map(e=>e.dataset.stage));
  $('emptyDetail').hidden=true;
  $('detail').hidden=false;
  text('taskLocation',v.workspace.display_name+' · '+(p.task.location==='active'?'Активная TASK':'Историческая TASK'));
  text('taskHeading',t.title);
  text('taskIdentity',t.task_id+' / '+t.workspace_id);
  text('taskGoalText',t.goal);
  $('taskBadge').replaceChildren(badge(t.status));
  text('progressText',o.progress.verified==null?'VERIFIED-прогресс не подтверждён':o.progress.verified+' / '+o.progress.total+' VERIFIED');
  text('doneText',o.progress.done+' DONE · ожидает проверки');
  const known=o.progress.verified!=null&&o.progress.total>0;
  text('progressFill','');
  $('progressFill').style.width=known?(100*o.progress.verified/o.progress.total)+'%':'0%';
  $('progressTrack').setAttribute('aria-valuemax',String(o.progress.total||1));
  if(known){
    $('progressTrack').setAttribute('aria-valuenow',String(o.progress.verified));
    $('progressTrack').removeAttribute('aria-valuetext')
  }
  else{
    $('progressTrack').removeAttribute('aria-valuenow');
    $('progressTrack').setAttribute('aria-valuetext','Подтверждённый прогресс неизвестен')
  }
  text('currentStage',v.current_microtask_id?(v.current_microtask_id+' · '+p.position.current_status):'Не определён');
  $('checkpointBadge').replaceChildren(badge(v.checkpoint_validation.status));
  $('snapshotBadge').replaceChildren(badge(p.restore_point.status));
  text('nextSafeAction',v.next_safe_action);
  text('nextSource','Источник: '+v.authority_source+' · RC-5');
  $('timeline').replaceChildren();
  for(const m of o.stages){
    const d=element('details',null,'stage'+(m.is_current?' current':''));
    d.dataset.stage=m.microtask_id;
    d.open=opened.has(m.microtask_id);
    const s=element('summary');
    s.append(element('span',m.position,'stage-number'),element('span',m.title+(m.is_current?' · текущий':''),'title'),badge(m.status));
    const body=element('div',null,'stage-body');
    body.append(element('p',m.goal),element('p',m.microtask_id,'id muted'),element('p','Предыдущие этапы плана: '+(m.prerequisites.join(', ')||'нет'),'muted'));
    if(m.blockers.length)body.append(element('p',m.blockers.map(b=>b.code+': '+b.reason).join('\n'),'notice error'));
    for(const op of m.operations)body.append(element('p',op.record.operation_id+' · '+op.record.action+' → '+op.record.target+' · '+op.record.status,'id'));
    const e=element('details');
    e.append(element('summary','Evidence этапа ('+m.events.length+' событий)'),element('pre',JSON.stringify({
      events:m.events,operations:m.operations,recovery_reports:m.recovery_reports
    }
    ,null,2)));
    body.append(e);
    d.append(s,body);
    $('timeline').append(d)
  }
  if(!o.stages.length)$('timeline').append(element('p','План ещё не содержит этапов.','empty'));
  const current=o.current_operation;
  $('operationBadge').replaceChildren(...(current?[badge(current.record.status)]:[]));
  text('operationReason',o.current_operation_reason);
  const dl=$('operationDetails');
  dl.replaceChildren();
  if(current){
    const r=current.record;
    field(dl,'operation_id',r.operation_id);
    field(dl,'Этап',r.microtask_id);
    field(dl,'Действие',r.action);
    field(dl,'Target',r.target);
    field(dl,'Receipt',r.receipt?(r.receipt.receipt_type||r.receipt.proof_kind||'Persistent receipt')+' · исторический':'Отсутствует');
    field(dl,'Post-state',r.receipt?'Proof при записи receipt: '+String(r.receipt.matches_expected_post)+'; текущие bytes не проверены':'Не доказан');
    field(dl,'Replay',current.replay_confirmed?'Подтверждённое событие OPERATION_REPLAY в истории':'Нет подтверждающего события; доставка ответа неизвестна');
    field(dl,'Reconciliation',current.projection.recovery?.state||'Нет требования в Projection')
  }
  else{
    field(dl,'Операция','Не определена');
    field(dl,'История',o.operations.length+' операций · раскрывается ниже')
  }
  $('recoveryBadge').replaceChildren(badge(v.recovery_state));
  const facts=$('recoveryFacts');
  facts.replaceChildren();
  for(const b of [...p.blockers,...p.diagnostics,...o.evidence_errors.map(e=>({
    code:'EVIDENCE_UNAVAILABLE / '+e.source,reason:e.reason
  }
  ))])facts.append(element('p',b.code+': '+b.reason,'notice'));
  for(const op of p.operations.filter(op=>op.recovery)){
    facts.append(element('p',op.operation_id+' · '+op.recovery.state+' · '+(op.recovery.next_safe_action||v.next_safe_action),'notice info'));
    for(const r of op.resolutions||[])facts.append(element('p','Resolver: '+r.action+' · '+r.result+' · '+(r.fresh?'fresh':r.freshness_code||'stale'),'muted spaced'))
  }
  for(const rb of p.rollbacks)facts.append(element('p','Rollback '+rb.rollback_id+' · '+rb.status,'notice'));
  facts.append(element('p','Recovery evidence: '+o.recovery_reports.length+' отчётов · исторические сведения','muted spaced'));
  const j=(id,x)=>text(id,JSON.stringify(x,null,2));
  j('manifest',{
    manifest:v.manifest,integrity:p.restore_point
  }
  );
  j('checkpoint',{
    persisted:v.task_state.checkpoint,validation:v.checkpoint_validation
  }
  );
  j('events',v.recent_events);
  j('operations',o.operations);
  j('recovery',{
    projection:p.recovery,rollbacks:p.rollbacks,advisory:p.advisory_reconciliation,reports:o.recovery_reports
  }
  );
  j('reports',v.reports);
  text('rawTask',t.raw_task);
  j('plan',{
    plan:v.task_state.plan,projection:p,read:{
      coherent:o.coherent,note:o.consistency_note,errors:o.evidence_errors
    }
  }
  );
  text('readTime','Серверный снимок: '+new Date(o.read_at).toLocaleTimeString('ru-RU'));
}
async function loadDetail(epoch){
  if(!view.task)return;
  const task=view.task,workspace=view.workspace;
  $('detail').setAttribute('aria-busy','true');
  try{
    const v=await api('/tasks/'+encodeURIComponent(task)+'/ui');
    if(epoch!==view.epoch)return;
    if(v.task_state?.task.task_id!==task||v.workspace?.workspace_id!==workspace||!v.operator)throw new Error('Ответ не соответствует выбранным Workspace / TASK');
    view.data=v;
    view.loadedAt=Date.now();
    render(v);
    notice('detailError','');
    setFresh(v.operator.coherent,v.operator.coherent?'':'Состояние изменилось во время чтения. Этот снимок не подтверждён; обновите данные.')
  }
  catch(e){
    if(epoch!==view.epoch)return;
    notice('detailError',e.message+(e.details?'\n'+JSON.stringify(e.details):''));
    setFresh(false,view.data?'Нет свежего ответа. Показан предыдущий снимок; NEXT SAFE ACTION устарел.':'Состояние TASK неизвестно: свежий ответ недоступен.')
  }
  finally{
    if(epoch===view.epoch)$('detail').setAttribute('aria-busy','false')
  }
}
async function refresh(){
  if(view.refreshing)return;
  view.refreshing=true;
  $('refresh').disabled=true;
  const epoch=view.epoch;
  try{
    const [s,w,t]=await Promise.all([api('/status'),api('/workspaces'),api('/ui/tasks')]);
    if(epoch!==view.epoch)return;
    text('serverStatus',s.service+' · '+s.mode+' · API '+s.api_version);
    view.workspaces=w.workspaces;
    view.tasks=t;
    for(const id of ['workspaceSelect','taskWorkspace']){
      const old=$(id).value;
      $(id).replaceChildren(...w.workspaces.map(ws=>{
        const opt=element('option',ws.display_name);
        opt.value=ws.workspace_id;
        return opt
      }
      ));
      if(w.workspaces.some(ws=>ws.workspace_id===old))$(id).value=old
    }
    if(!w.workspaces.some(ws=>ws.workspace_id===view.workspace)){
      view.workspace=w.workspaces[0]?.workspace_id||null;
      view.task=null;
      clearDetail()
    }
    $('workspaceSelect').value=view.workspace||'';
    if(!$('taskWorkspace').value)$('taskWorkspace').value=view.workspace||'';
    notice('navigationError','');
    renderNavigation();
    saveSelection();
    await loadDetail(epoch)
  }
  catch(e){
    if(epoch!==view.epoch)return;
    text('serverStatus','Нет свежего соединения');
    notice('navigationError',e.message);
    setFresh(false,view.data?'Связь недоступна. Показан предыдущий снимок; NEXT SAFE ACTION устарел.':'Данные сервера недоступны. Обновите после восстановления связи.')
  }
  finally{
    view.refreshing=false;
    $('refresh').disabled=false
  }
}
async function create(kind){
  if(view.creating)return;
  if(view.refreshing){
    notice('formError','Дождитесь завершения обновления.');
    return;
  }
  const ws=kind==='workspace';
  const body=ws?{
    display_name:$('wsName').value,workspace_root:$('wsRoot').value
  }
  :{
    workspace_id:$('taskWorkspace').value,title:$('taskTitle').value,goal:$('taskGoal').value,raw_task:$('taskRaw').value
  }
  ;
  if(!window.confirm(ws?'Добавить Workspace «'+body.display_name+'» по пути '+body.workspace_root+'?':'Создать TASK «'+body.title+'» в Workspace '+body.workspace_id+'?'))return;
  view.creating=true;
  $('createWorkspace').disabled=true;
  $('createTask').disabled=true;
  notice('formError','');
  try{
    const data=await api(ws?'/workspaces':'/tasks',{
      method:'POST',body
    }
    );
    view.epoch++;
    view.workspace=ws?data.workspace.workspace_id:body.workspace_id;
    view.task=ws?null:data.task.task_id;
    clearDetail();
    saveSelection();
    await refresh();
    notice('formError','Сервер подтвердил создание '+(ws?data.workspace.workspace_id:data.task.task_id)+'.')
  }
  catch(e){
    notice('formError',e.message+(e.serverRejected?'\nСервер отклонил запрос.':'\nРезультат создания неизвестен. Проверьте список перед повторным созданием; автоматического повтора нет.'));
    await refresh()
  }
  finally{
    view.creating=false;
    $('createWorkspace').disabled=false;
    $('createTask').disabled=false
  }
}
async function copy(value){
  try{
    await navigator.clipboard.writeText(value);
    text('copyStatus','Скопировано')
  }
  catch(_){
    text('copyStatus','Копирование недоступно. Выделите текст и скопируйте вручную.')
  }
}
$('workspaceSelect').onchange=e=>selectWorkspace(e.target.value);
$('refresh').onclick=refresh;
$('workspaceForm').onsubmit=e=>{
  e.preventDefault();
  create('workspace')
}
;
$('taskForm').onsubmit=e=>{
  e.preventDefault();
  create('task')
}
;
$('copyNext').onclick=()=>{
  if(view.fresh&&view.data?.operator.coherent)copy(view.data.next_safe_action)
}
;
$('copyContext').onclick=()=>{
  if(!view.fresh||!view.data?.operator.coherent){
    text('copyStatus','Контекст не скопирован: снимок недостоверен или устарел. Обновите данные.');
    return
  }
  const v=view.data;
  copy(['TASK: '+v.task_state.task.task_id,'Workspace: '+v.workspace.workspace_id,'Снимок: '+v.operator.read_at,'Свежий: '+view.fresh,'Статус: '+v.task_state.task.status,'Этап: '+v.current_microtask_id,'Recovery: '+v.recovery_state,'NEXT SAFE ACTION: '+v.next_safe_action].join('\n'))
}
;
try{
  const saved=JSON.parse(localStorage.getItem('webAlarm.selection')||'{}');
  if(typeof saved.workspace==='string')view.workspace=saved.workspace;
  if(typeof saved.task==='string')view.task=saved.task
}
catch(_){
}
window.addEventListener('resize',()=>{
  if(!window.matchMedia('(max-width:760px)').matches)$('navigatorPanel').open=true;
});
setInterval(()=>{
  if($('autoRefresh').checked&&!document.hidden&&!view.creating)refresh();
  if(view.loadedAt&&Date.now()-view.loadedAt>45000&&view.fresh)setFresh(false,'Снимок старше 45 секунд. Обновите перед использованием NEXT SAFE ACTION.')
}
,15000);
refresh();
</script>
</body></html>
'''
