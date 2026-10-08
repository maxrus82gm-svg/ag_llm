"""Static minimal UI for Web Alarm Workspace WA-2.3."""

INDEX_HTML = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Web Alarm Workspace</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color-scheme:dark;background:#101216;color:#eef1f6}
*{box-sizing:border-box} body{margin:0} button,input,textarea,select{font:inherit}
header{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid #30343b;background:#171a20;position:sticky;top:0;z-index:2}
header h1{font-size:18px;margin:0}.status{font-size:12px;color:#9fb0c5}
main{display:grid;grid-template-columns:320px 360px minmax(420px,1fr);min-height:calc(100vh - 55px)}
.panel{padding:14px;border-right:1px solid #2c3038;overflow:auto}.panel:last-child{border-right:0}
.card{background:#171a20;border:1px solid #30343b;border-radius:10px;padding:12px;margin-bottom:12px}
h2{font-size:15px;margin:0 0 10px}h3{font-size:13px;margin:12px 0 6px;color:#b9c4d3}
label{display:block;font-size:12px;color:#aeb9c7;margin:8px 0 4px}
input,textarea,select{width:100%;background:#0f1115;color:#eef1f6;border:1px solid #343943;border-radius:7px;padding:8px}
textarea{min-height:110px;resize:vertical}
button{border:1px solid #3e4654;background:#252a33;color:#f4f7fb;border-radius:7px;padding:8px 10px;cursor:pointer}
button:hover{background:#303745}.row{display:flex;gap:8px}.row>*{flex:1}
.list button{display:block;width:100%;text-align:left;margin:5px 0}.muted{color:#8f9bab;font-size:12px}
pre{white-space:pre-wrap;word-break:break-word;background:#0d0f13;border-radius:7px;padding:10px;max-height:260px;overflow:auto}
.next{background:#16251c;border-color:#2f6c44;font-size:16px;line-height:1.4}
.badge{display:inline-block;padding:2px 7px;border:1px solid #46505f;border-radius:999px;font-size:11px;margin-right:5px}
.error{color:#ff9f9f;white-space:pre-wrap;font-size:12px}
@media(max-width:1100px){main{grid-template-columns:1fr}.panel{border-right:0;border-bottom:1px solid #2c3038}}
</style>
</head>
<body>
<header><h1>Web Alarm Workspace</h1><div id="serverStatus" class="status">connecting…</div></header>
<main>
<section class="panel">
  <div class="card">
    <h2>Workspace</h2>
    <div id="workspaceList" class="list"></div>
    <h3>Добавить Workspace</h3>
    <label>Название</label><input id="wsName" placeholder="ag_llm">
    <label>Путь</label><input id="wsRoot" placeholder="M:\GitHub\ag_llm">
    <button id="createWorkspace">Добавить</button>
  </div>
  <div class="card">
    <h2>Новая TASK</h2>
    <label>Workspace</label><select id="taskWorkspace"></select>
    <label>Название</label><input id="taskTitle" placeholder="TASK title">
    <label>Цель</label><input id="taskGoal" placeholder="Что должно получиться">
    <label>RAW TASK</label><textarea id="taskRaw" placeholder="Вставь исходную задачу целиком"></textarea>
    <button id="createTask">Создать TASK</button>
  </div>
  <div id="formError" class="error"></div>
</section>

<section class="panel">
  <div class="card">
    <div class="row"><h2 style="flex:1">TASK</h2><button id="refresh">Обновить</button></div>
    <h3>Active</h3><div id="activeTasks" class="list"></div>
    <h3>Completed</h3><div id="completedTasks" class="list"></div>
  </div>
</section>

<section class="panel">
  <div id="emptyDetail" class="card muted">Выбери TASK слева.</div>
  <div id="detail" hidden>
    <div class="card next"><h2>NEXT SAFE ACTION</h2><div id="nextSafeAction">—</div></div>
    <div class="card"><h2>Состояние</h2><div id="badges"></div><pre id="checkpoint"></pre></div>
    <div class="card"><h2>RAW TASK</h2><pre id="rawTask"></pre></div>
    <div class="card"><h2>План / микрозадачи</h2><pre id="plan"></pre></div>
    <div class="card"><h2>Manifest / Snapshot</h2><pre id="manifest"></pre></div>
    <div class="card"><h2>Отчёты</h2><pre id="reports"></pre></div>
    <div class="card"><h2>Recovery state</h2><pre id="recovery"></pre></div>
  </div>
  <div id="detailError" class="error"></div>
</section>
</main>
<script>
const $ = id => document.getElementById(id);
let workspaces = [];
let selectedTask = null;

async function api(path, options={}) {
  const opts = {...options};
  if (opts.body && typeof opts.body !== "string") {
    opts.body = JSON.stringify(opts.body);
    opts.headers = {...(opts.headers||{}), "Content-Type":"application/json"};
  }
  const response = await fetch(path, opts);
  const data = await response.json();
  if (!response.ok) throw new Error(data?.error?.message || ("HTTP "+response.status));
  return data;
}
function text(id, value) { $(id).textContent = value == null ? "—" : String(value); }
function json(id, value) { text(id, JSON.stringify(value ?? null, null, 2)); }
function taskButton(task) {
  const b = document.createElement("button");
  b.textContent = task.title + " · " + task.status;
  b.onclick = () => showTask(task.task_id);
  return b;
}
async function refreshStatus() {
  const s = await api("/status");
  $("serverStatus").textContent = s.service+" · "+s.mode+" · API "+s.api_version;
}
async function refreshWorkspaces() {
  const data = await api("/workspaces");
  workspaces = data.workspaces;
  $("workspaceList").replaceChildren();
  $("taskWorkspace").replaceChildren();
  for (const ws of workspaces) {
    const div = document.createElement("div");
    div.className = "muted";
    div.textContent = ws.display_name+" — "+ws.workspace_root;
    $("workspaceList").append(div);
    const option = document.createElement("option");
    option.value = ws.workspace_id;
    option.textContent = ws.display_name;
    $("taskWorkspace").append(option);
  }
}
async function refreshTasks() {
  const data = await api("/tasks");
  $("activeTasks").replaceChildren(...data.active.map(taskButton));
  $("completedTasks").replaceChildren(...data.completed.map(taskButton));
  if (selectedTask) await showTask(selectedTask);
}
async function showTask(taskId) {
  selectedTask = taskId;
  $("detailError").textContent = "";
  try {
    const v = await api("/tasks/"+encodeURIComponent(taskId)+"/ui");
    $("emptyDetail").hidden = true; $("detail").hidden = false;
    text("nextSafeAction", v.next_safe_action);
    $("badges").replaceChildren();
    for (const value of [v.task_state.task.status, v.recovery_state, v.snapshot_status]) {
      const span = document.createElement("span"); span.className="badge"; span.textContent=value; $("badges").append(span);
    }
    json("checkpoint", v.task_state.checkpoint);
    text("rawTask", v.task_state.task.raw_task);
    json("plan", {plan:v.task_state.plan, microtasks:v.task_state.microtasks});
    json("manifest", v.manifest);
    json("reports", v.reports);
    json("recovery", {state:v.recovery_state, recent_events:v.recent_events});
  } catch (e) { $("detailError").textContent = e.message; }
}
$("createWorkspace").onclick = async () => {
  $("formError").textContent="";
  try {
    await api("/workspaces",{method:"POST",body:{display_name:$("wsName").value,workspace_root:$("wsRoot").value}});
    await refreshWorkspaces();
  } catch(e){$("formError").textContent=e.message;}
};
$("createTask").onclick = async () => {
  $("formError").textContent="";
  try {
    const data = await api("/tasks",{method:"POST",body:{
      workspace_id:$("taskWorkspace").value,title:$("taskTitle").value,
      goal:$("taskGoal").value,raw_task:$("taskRaw").value
    }});
    await refreshTasks(); await showTask(data.task.task_id);
  } catch(e){$("formError").textContent=e.message;}
};
$("refresh").onclick = refreshTasks;
Promise.all([refreshStatus(),refreshWorkspaces(),refreshTasks()]).catch(e => $("formError").textContent=e.message);
</script>
</body>
</html>
"""
