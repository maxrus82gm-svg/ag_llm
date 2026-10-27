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
body{margin:0;height:100vh;overflow:hidden}
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
.layout{display:grid;grid-template-columns:230px minmax(0,1fr) 286px;max-width:2000px;margin:auto;height:calc(100dvh - 73px);min-height:0}
aside{padding:20px 14px;background:#121c27;min-height:0;display:flex;flex-direction:column;gap:12px;overflow:auto}.workspaces{border-right:1px solid var(--line)}.tasks{border-left:1px solid var(--line)}
main{min-width:0;min-height:0;overflow:auto;scrollbar-gutter:stable;padding:26px 28px 44px}
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
.notice.success{border-color:#3b7360;background:#19362d;color:var(--green)}
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

/* Each desktop column owns its scroll; mobile panels precede the card. */
.side-scroll{min-height:0;overflow:auto;flex:1;scrollbar-gutter:stable}
.workspace-button{width:100%;text-align:left;margin-bottom:8px;overflow-wrap:anywhere}
.workspace-button[aria-current=true]{background:#213b50;border-color:var(--blue);box-shadow:inset 3px 0 var(--blue)}
.side-title{font-size:11px;letter-spacing:.12em;color:var(--muted);font-weight:700}
.plus{font-size:22px;line-height:1;padding:6px 11px}.task-list{margin:8px 0 18px}
.task-button strong{font-size:14px}.task-button .tag{margin-top:7px;font-family:inherit}
.source-text{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7;font-size:15px;max-height:none;background:transparent;padding:0;font-family:inherit}
.source-card{border-left:3px solid var(--blue)}.source-card h2{margin-bottom:14px}
.composer textarea{min-height:320px;line-height:1.65;resize:vertical}.composer .row{margin-top:18px}
.draft-state{color:var(--muted);font-size:13px;line-height:1.6;margin:16px 0}
.draft-row{border:1px dashed #6d879e}.form-panel{padding-top:8px;border-top:1px solid var(--line)}
.connection{font-size:12px;border:1px solid var(--line);border-radius:20px;padding:6px 10px;max-width:300px}
.connection[data-state=online]{color:var(--green)}.connection[data-state=offline]{color:var(--amber)}
.path-row{display:flex;gap:8px;align-items:center}.path-row input{min-width:0;flex:1}.path-row button{flex-shrink:0;white-space:nowrap}
.mobile-toggle{display:none}.report-text{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65}
/* WUA-1 EVM tab: connections of the shared Ultra core (API | MCP / agents | local LLM). */
.top-nav{display:flex;gap:6px;flex:1;justify-content:center;flex-wrap:wrap}
.top-nav button[aria-pressed=true]{background:#213b50;border-color:var(--blue);box-shadow:inset 0 -2px var(--blue)}
.evm{max-width:2000px;margin:auto;height:calc(100dvh - 73px);overflow:auto;padding:26px 28px 44px}
.evm-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
.evm-head h2{font-size:24px;margin:8px 0}
.evm-columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:18px;align-items:start}
.evm-col{border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:18px;min-width:0;display:flex;flex-direction:column;gap:12px}
.evm-api{margin-top:18px}
.evm-col h3{font-size:16px}
.evm-list{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(min(100%,500px),1fr));align-items:start}
.evm-add{border:1px dashed #526579;border-radius:10px;padding:12px;color:var(--muted);text-align:center;font-size:13px}
.evm-chat{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.evm-chat label{margin:0}
.evm-chat select{min-width:240px;max-width:100%;background:#1f2d3b;color:var(--text);border:1px solid #4a6075;padding:9px 10px}
/* EVM model card (CLAUDE-WUA-EVM-MODEL-CARD-UI-001): one component for every model of every provider. */
.mcard{border:1px solid #6aa9dc;background:#16212d;border-radius:12px;padding:16px 18px 14px 20px;display:flex;flex-direction:column;gap:11px;min-width:0;box-shadow:inset 4px 0 #6aa9dc}
.mcard-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.mcard-name{margin:0;font-size:24px;font-weight:700;line-height:1.15;overflow-wrap:anywhere}
.mcard-side{margin-left:auto;font-size:12px;color:var(--muted)}
.api-dot{display:inline-grid;place-items:center;width:28px;height:28px;flex:none;border-radius:50%;border:2px solid;font:800 15px system-ui,Segoe UI,sans-serif;line-height:1}
.api-dot.green{color:#7be3a6;border-color:#3f9e6f;background:#173a2a}
.api-dot.orange{color:#ffc06b;border-color:#c8873a;background:#3d2c16}
.api-dot.red{color:#ff8f98;border-color:#a9505b;background:#3c1e25}
.params{border:1px solid #58708a;border-radius:7px;padding:5px 10px;background:#1c2b38;font:700 13px system-ui,Segoe UI,sans-serif;white-space:nowrap}
.mcard-sub{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}.mcard-sub strong,.mcard-label{font-size:14px;font-weight:700}
.roles{position:relative;display:grid;grid-template-columns:repeat(auto-fill,minmax(118px,1fr));gap:7px 12px}
.role{display:flex;align-items:center;gap:8px;font-weight:600;font-size:14px;min-width:0}
.role .mark{width:16px;flex:none;text-align:center;font-weight:800}
.role .mark.yes{color:#7be3a6}.role .mark.no{color:#ff6f7d}.role .mark.off,.role .mark.na,.role .mark.unknown{color:var(--muted)}
.role .name{cursor:help;border-bottom:1px dotted transparent;overflow-wrap:anywhere}
.role .name:hover,.role .name:focus-visible{border-bottom-color:var(--muted)}
.role .name:hover::after,.role .name:focus-visible::after{content:attr(data-hint);position:absolute;left:0;right:0;top:calc(100% + 6px);z-index:5;padding:10px 12px;border:1px solid #4d7fa8;border-radius:9px;background:#0f1822;color:var(--text);font-weight:400;font-size:13px;line-height:1.45;box-shadow:0 8px 24px rgba(0,0,0,.45);white-space:normal}
.strengths{height:84px;overflow-y:auto;border:1px solid #3a4f63;background:#1b2836;border-radius:9px;padding:10px 12px;font-size:14px;line-height:1.15;white-space:pre-wrap;overflow-wrap:anywhere}
.strengths.placeholder{color:var(--muted)}
.mcard-actions{display:flex;gap:10px;flex-wrap:wrap}
.primary{border-color:#6aa9dc;background:#26425a}
.mcard-note{font-size:12px;color:var(--muted);line-height:1.4;margin:0}
/* EVM windows: settings and API diagnostics; each keeps its state while the other is open. */
.evm-backdrop{position:fixed;inset:0;z-index:20;background:rgba(6,11,17,.72);display:grid;place-items:center;padding:16px}
.evm-backdrop[hidden]{display:none}
.evm-window{width:min(760px,100%);max-height:calc(100dvh - 32px);overflow:auto;background:#17212c;border:1px solid #6aa9dc;border-radius:14px;padding:18px 20px;display:flex;flex-direction:column;gap:12px}
.evm-window.small{width:min(580px,100%)}
.evm-window h3{font-size:19px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.evm-window .section-head{margin-bottom:0}
.tabs{display:flex;gap:6px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:10px}
.tabs button[aria-selected=true]{background:#2b4a64;border-color:var(--blue)}
.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2px 16px}.form-grid .wide{grid-column:1/-1}
.evm-window input,.evm-window select,.evm-window textarea{width:100%;background:#1f2d3b;color:var(--text);border:1px solid #4a6075;padding:9px 10px}
.evm-window textarea{min-height:110px;line-height:1.2;resize:vertical}
.evm-window select:disabled{opacity:.6;cursor:default}
.facts-list{display:grid;grid-template-columns:minmax(130px,auto) minmax(0,1fr);gap:6px 14px;font-size:13px;margin:8px 0}
.facts-list dt{color:var(--muted)}.facts-list dd{margin:0;overflow-wrap:anywhere}
.window-actions{display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap}
.output{min-height:120px;max-height:260px;overflow:auto;border:1px solid #3a4f63;background:#111b26;border-radius:9px;padding:12px 14px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.4}
.output.reply{border-color:#3f9e6f}.output.error{border-color:#a9505b}.output.info{border-color:#526c85}
.output-label{font:700 11px system-ui,Segoe UI,sans-serif;letter-spacing:.1em;color:var(--muted);margin:0 0 6px}
.composer-actions{display:flex;gap:8px;align-items:center;flex:none}
@media(max-width:640px){.form-grid{grid-template-columns:1fr}.mcard{padding:14px 12px 12px 16px}.mcard-name{font-size:21px}.facts-list{grid-template-columns:1fr}.evm-chat select{min-width:0;width:100%}}
/* Ultra Chat (programme No.37 stage 1): read-only history of the shared Ultra core; the default view. */
.chat-layout{display:grid;grid-template-columns:300px minmax(0,1fr);max-width:2000px;margin:auto;height:calc(100dvh - 73px);min-height:0}
.chat-side{padding:20px 14px;background:#121c27;border-right:1px solid var(--line);display:flex;flex-direction:column;gap:10px;overflow:auto;min-height:0}
.chat-main{min-width:0;min-height:0;display:flex;flex-direction:column;gap:12px;padding:22px 28px 18px}
.chat-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.chat-head h2{font-size:22px;margin:6px 0 0;overflow-wrap:anywhere}
.chat-picks{display:grid;gap:8px}
.chat-pick{width:100%;text-align:left;display:grid;gap:4px;background:#182431;border-color:#344454;overflow-wrap:anywhere}
.chat-pick[aria-current=true]{background:#213b50;border-color:var(--blue);box-shadow:inset 3px 0 var(--blue)}
.chat-history{list-style:none;margin:0;padding:0 4px 0 0;flex:1;min-height:0;overflow:auto;display:flex;flex-direction:column;gap:12px;scrollbar-gutter:stable}
.msg{border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:var(--panel);max-width:880px;width:fit-content;min-width:min(260px,100%);display:grid;gap:8px}
.msg[data-role=user]{align-self:flex-end;background:#1d3044;border-color:#3d5f7d}
.msg[data-outcome=failed]{border-color:#86505b;background:#2c1d23}
.msg-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.msg-text{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}
.chat-composer{border-top:1px solid var(--line);padding-top:10px;display:grid;gap:8px}
.chat-composer label{margin:0}
.chat-composer textarea{min-height:60px;resize:none}
.chat-composer .row{justify-content:space-between;flex-wrap:nowrap}
@media(max-width:1200px){.layout{grid-template-columns:190px minmax(0,1fr) 240px}.columns{grid-template-columns:1fr}main{padding:22px 18px}.overview h2{font-size:24px}}
@media(max-width:850px){body{height:auto;overflow:auto}.top{padding:12px 14px;flex-wrap:wrap;position:sticky}.top-actions{gap:8px}.mobile-toggle{display:inline-block}.layout{display:flex;flex-direction:column;height:auto;min-height:calc(100dvh - 100px)}aside{display:none;border:0;border-bottom:1px solid var(--line);max-height:330px;order:-1}.layout.show-workspaces .workspaces,.layout.show-tasks .tasks{display:flex}main{padding:18px 12px;overflow:visible}.card{padding:16px}.overview-top{flex-wrap:wrap}.overview h2{font-size:23px}.stage summary{flex-wrap:wrap}.stage-body{padding-left:16px}.operation-grid{grid-template-columns:90px minmax(0,1fr)}.composer textarea{min-height:280px}.connection{max-width:220px}.brand .live{display:none}.top-nav{order:3;width:100%;justify-content:flex-start}.evm{height:auto;padding:18px 12px;overflow:visible}.evm-columns{grid-template-columns:1fr}}
@media(max-width:850px){.chat-layout{display:flex;flex-direction:column;height:auto}.chat-side{border-right:0;border-bottom:1px solid var(--line);overflow:visible;max-height:none}.chat-main{padding:16px 12px}.chat-history{overflow:visible}.chat-composer .row{flex-wrap:wrap}}
</style>
</head>
<body>
<a class="skip" id="skipLink" href="#chatMain">К истории диалога</a>
<header class="top">
<div class="brand">
<span class="logo" aria-hidden="true">WA</span>
<div>
<h1>Web Alarm Workspace</h1>
<div class="live">Постановки · этапы · восстановление</div>
</div>
</div>
<nav class="top-nav" aria-label="Разделы Web Alarm">
<button type="button" id="viewChat" aria-pressed="true" aria-controls="chatView" title="Сохранённые диалоги Ultra, только чтение">Ultra Chat</button>
<button type="button" id="viewOperator" aria-pressed="false" aria-controls="layout">Операторская панель</button>
<button type="button" id="viewEvm" aria-pressed="false" aria-controls="evmView" title="Подключения моделей общего ядра Ultra">EVM · Подключения Ultra</button>
</nav>
<div class="top-actions">
<span class="connection" id="serverStatus" role="status" data-state="checking">Проверяем соединение…</span>
<button class="mobile-toggle" id="showWorkspaces" aria-controls="workspacesPanel" hidden>Проекты</button>
<button class="mobile-toggle" id="showTasks" aria-controls="tasksPanel" hidden>Задачи</button>
<label>
<input type="checkbox" id="autoRefresh"> Наблюдать · 15 с</label>
<button id="refresh">↻ Обновить</button>
</div>
</header>
<section id="chatView" class="chat-view" aria-labelledby="chatHeading">
<div class="chat-layout">
<nav class="chat-side" aria-label="Workspace и диалоги Ultra">
<div class="section-head"><div><p class="side-title">ULTRA CHAT · ТОЛЬКО ЧТЕНИЕ</p><h2 id="chatHeading" tabindex="-1">Диалоги Ultra</h2></div><button type="button" id="chatRefresh" title="Перечитать Workspace, диалоги и модель">↻</button></div>
<p id="chatAccess" class="live" role="status">Проверяем доступ к истории…</p>
<div id="chatError" class="notice error" role="alert" hidden></div>
<p class="side-title spaced">WORKSPACE</p>
<p id="chatWorkspaceState" class="muted" role="status"></p>
<div id="chatWorkspaceList" class="chat-picks" aria-label="Зарегистрированные Workspace"></div>
<p class="side-title spaced">ДИАЛОГИ</p>
<p id="chatListState" class="muted" role="status">Выберите Workspace.</p>
<div id="chatList" class="chat-picks" aria-label="Сохранённые диалоги"></div>
<p class="muted spaced">Новую папку добавляют в операторской панели (+ у списка проектов). Ultra Chat ничего не записывает в Workspace.</p>
</nav>
<div id="chatMain" class="chat-main" tabindex="-1" role="region" aria-labelledby="chatTitle">
<div class="chat-head"><div><span class="eyebrow" id="chatWorkspaceName">Ultra Chat</span><h2 id="chatTitle">Выберите диалог</h2></div><span id="chatModel" class="tag" title="Модель, выбранная в EVM">Модель: —</span></div>
<div id="chatNotice" class="notice" role="status" hidden></div>
<button type="button" id="chatOlder" hidden>Показать ранее</button>
<ol id="chatHistory" class="chat-history" aria-label="История диалога"></ol>
<form id="chatComposer" class="chat-composer" aria-label="Новое сообщение">
<label for="chatInput">Сообщение</label>
<textarea id="chatInput" disabled aria-describedby="chatComposerNote" placeholder="Отправка появится на следующем этапе"></textarea>
<div class="row"><p id="chatComposerNote" class="muted">Отправка сообщений появится на следующем этапе. Сейчас Ultra Chat только читает сохранённую историю.</p><span class="composer-actions"><button type="button" id="chatMic" disabled data-extension="voice-input" aria-label="Голосовой ввод — появится позже" title="Голосовой ввод появится позже">🎤</button><button type="button" id="chatSend" disabled>Отправить</button></span></div>
</form>
</div>
</div>
</section>
<div class="layout" id="layout" hidden>
<aside class="workspaces" id="workspacesPanel" aria-label="Рабочие пространства">
<div class="section-head"><div><p class="side-title">WORKSPACES</p><h2>Проекты</h2></div><button class="plus" id="addWorkspace" aria-label="Добавить Workspace" title="Зарегистрировать существующую папку">+</button></div>
<div id="workspaceList" class="side-scroll" aria-label="Список Workspace"></div>
<details id="workspaceInfo"><summary>О выбранном проекте</summary><p class="id spaced" id="workspacePath"></p><p class="muted">Путь проверяет сервер. Регистрация не разрешает запись в проект.</p></details>
<div id="workspaceFormPanel" class="form-panel" hidden>
<h3>Добавить Workspace</h3><form id="workspaceForm">
<label for="wsName">Название проекта</label><input id="wsName" required maxlength="300">
<label for="wsRoot">Абсолютный путь к папке</label><div class="path-row"><input id="wsRoot" required placeholder="M:\Projects\project"><button id="browseWorkspace" type="button" disabled>Обзор…</button></div>
<p id="folderPickerNotice" class="muted spaced" role="status">Можно ввести абсолютный путь вручную. Выбор папки проверяется при открытии формы.</p>
<div class="row spaced"><button id="createWorkspace" type="submit">Добавить</button><button type="button" id="cancelWorkspace">Закрыть</button></div></form></div>
</aside>
<main id="main" tabindex="-1">
<div class="section-head">
<span class="eyebrow">Операторская панель</span>
<span id="readTime" class="live" role="status">Нет выбранной TASK</span>
</div>
<div id="formError" class="notice info" role="status" aria-live="polite" aria-label="Результат операции" hidden></div>
<div id="detailError" class="notice error" role="alert" hidden>
</div>
<div id="freshness" class="notice" role="status" hidden>
</div>
<div id="emptyDetail" class="empty">
<h2>Выберите TASK</h2>
<p>Выберите проект слева и задачу справа.<br>Или нажмите + у списка задач, чтобы ввести новую постановку.</p>
</div>
<section id="draftPanel" class="card composer" aria-labelledby="draftHeading" hidden>
<p class="eyebrow" id="draftWorkspace"></p><h2 id="draftHeading">Новая TASK</h2>
<p class="muted spaced">Одна постановка целиком. Пустая форма исчезнет при уходе; серверная TASK от нажатия + не создаётся.</p>
<form id="taskForm"><label for="taskRaw">Что нужно сделать?</label><textarea id="taskRaw" placeholder="Опишите задачу, ограничения и желаемый результат…"></textarea>
<p id="draftStatus" class="draft-state" role="status"></p><div id="draftError" class="notice error" role="alert" hidden></div>
<div class="row"><button id="createTask" type="submit" disabled>Зарегистрировать постановку</button><button id="copyDraft" type="button">Копировать текст</button><button id="discardDraft" type="button">Удалить локальный черновик</button></div></form>
<p class="muted spaced">Черновик хранится только в браузере на этом адресе, не на сервере. Очистка данных браузера удалит его; важный текст сохраните отдельно. Планировщика в API пока нет.</p>
<details class="spaced"><summary>Что делает регистрация?</summary><p class="muted spaced">Сервер сохранит TASK без плана и без запуска исполнения. В текущем API название берётся из первой строки, цель — из постановки; внешние пробелы API удаляет. Это перенос текста, а не автоматическое планирование. ID и состояние подтверждает сервер.</p></details>
</section>
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
<section class="card source-card" aria-labelledby="sourceHeading"><h2 id="sourceHeading">Исходная постановка</h2><div id="taskDescription" class="source-text"></div></section>
<section class="card next-card" aria-labelledby="nextHeading">
<h2 id="nextHeading">Следующий безопасный шаг · NEXT SAFE ACTION</h2>
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
<p class="muted">Выполнено (DONE) — ожидает проверки. Подтверждено (VERIFIED) — проверенный этап.</p>
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
<h2 id="recoveryHeading">Восстановление · Recovery state</h2>
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
<aside class="tasks" id="tasksPanel" aria-label="Задачи выбранного проекта">
<div class="section-head"><div><p class="side-title">TASKS</p><h2>Задачи</h2></div><button class="plus" id="newTask" aria-label="Новая TASK" title="Открыть пустую постановку">+</button></div>
<p id="taskWorkspaceName" class="muted"></p><div id="navigationError" class="notice error" role="alert" hidden></div>
<div class="side-scroll"><div id="draftEntry"></div><h3 class="side-title spaced">Текущие и ожидающие</h3><div id="activeTasks" class="task-list"></div><h3 class="side-title">Завершённые <span id="completedCount"></span></h3><div id="completedTasks" class="task-list"></div></div>
</aside>
</div>
<section id="evmView" class="evm" aria-labelledby="evmHeading" hidden>
<div class="evm-head">
<div><span class="eyebrow">EVM · общее ядро Ultra</span><h2 id="evmHeading" tabindex="-1">Подключения Ultra</h2>
<p class="muted">Модели берутся из общего реестра Ultra (model_registry). Статус API считает сервер по подтверждённым ответам моделей; в этой версии настоящие запросы к API не отправляются.</p></div>
<div class="row"><span id="evmState" class="live" role="status">Реестр ещё не загружен</span><button type="button" id="evmRefresh">↻ Обновить список</button></div>
</div>
<div id="evmError" class="notice error" role="alert" hidden></div>
<div id="evmNotice" class="notice success" role="status" hidden></div>
<div class="card spaced"><p class="side-title">Модель для Ultra Web Chat</p><p id="evmSelection" class="spaced">—</p>
<div class="evm-chat spaced"><label for="evmChatModel">Модель чата</label><select id="evmChatModel" aria-describedby="evmChatNote"></select><button type="button" id="evmChatSave">Сохранить выбор</button></div>
<p id="evmChatNote" class="muted spaced">Выбор хранится в Web Alarm и не меняет назначения моделей в прежней Ultra (Tkinter). Когда в Ultra Chat появится отправка сообщений, выбор переедет к полю ввода.</p></div>
<section class="evm-col evm-api" aria-labelledby="evmApiTitle"><div class="section-head"><h3 id="evmApiTitle">API</h3><span id="evmApiState" class="tag">—</span></div><p id="evmCardsNote" class="muted">Значок рядом с названием — статус API: ✓ ответ подтверждён в срок актуальности, ! подтверждение устарело, × подтверждения нет. Отметки ролей — фактические назначения, нажатие их не меняет.</p><p id="evmRolesSource" class="muted">—</p><div id="evmApiList" class="evm-list" aria-label="Модели API"></div><p class="evm-add" aria-disabled="true">+ Добавить — следующий этап</p></section>
<div class="evm-columns">
<section class="evm-col" aria-labelledby="evmMcpTitle"><div class="section-head"><h3 id="evmMcpTitle">MCP / Агенты</h3><span id="evmMcpState" class="tag">—</span></div><p class="muted">Подключения агентов появятся позже. Сейчас здесь ничего не запускается.</p><p class="evm-add" aria-disabled="true">+ Добавить — следующий этап</p></section>
<section class="evm-col" aria-labelledby="evmLocalTitle"><div class="section-head"><h3 id="evmLocalTitle">Локальные LLM</h3><span id="evmLocalState" class="tag">—</span></div><p class="muted">Локальные модели появятся позже. Сейчас здесь ничего не запускается.</p><p class="evm-add" aria-disabled="true">+ Добавить — следующий этап</p></section>
</div>
<div id="evmSettingsWindow" class="evm-backdrop" hidden><div class="evm-window" role="dialog" aria-modal="true" aria-labelledby="evmSetTitle">
<div class="section-head"><h3 id="evmSetTitle" tabindex="-1">Настройки провайдера и модели</h3><button type="button" id="evmSetClose">Закрыть ×</button></div>
<p id="evmSetModel" class="muted">—</p>
<div class="tabs" role="tablist" aria-label="Разделы настроек"><button type="button" role="tab" id="evmTabConn" aria-selected="true" aria-controls="evmPaneConn">Подключение</button><button type="button" role="tab" id="evmTabModel" aria-selected="false" aria-controls="evmPaneModel" tabindex="-1">Модель</button><button type="button" role="tab" id="evmTabMore" aria-selected="false" aria-controls="evmPaneMore" tabindex="-1">Дополнительно</button></div>
<div id="evmPaneConn" role="tabpanel" aria-labelledby="evmTabConn">
<div class="form-grid"><div><label for="evmSetProvider">Провайдер</label><select id="evmSetProvider" disabled aria-describedby="evmSetProviders"></select></div><div><label for="evmSetProfile">Профиль подключения</label><select id="evmSetProfile"></select></div></div>
<dl id="evmSetConnFacts" class="facts-list"></dl>
<div class="row"><button type="button" disabled>Подключить ключ</button><button type="button" disabled>Заменить ключ</button><button type="button" disabled>Удалить ключ</button></div>
<p class="muted">Ключ хранится прежним механизмом Ultra (переменная среды сервера) и никогда не передаётся в браузер. Действия с ключом появятся после отдельного разрешения пользователя. Один профиль может обслуживать несколько моделей провайдера, а успешная проверка учитывается для каждой модели отдельно. Смена профиля, ключа, адреса API или модели провайдера требует новой проверки.</p>
<p id="evmSetProviders" class="muted">—</p>
</div>
<div id="evmPaneModel" role="tabpanel" aria-labelledby="evmTabModel" hidden>
<dl id="evmSetModelFacts" class="facts-list"></dl>
<div class="form-grid"><div><label for="evmSetParams">Количество параметров, млрд</label><input id="evmSetParams" type="number" min="0" step="any" inputmode="decimal" placeholder="Неизвестно"></div><div><label>Источник характеристики<span id="evmSetParamsSource" class="muted" style="display:block;margin-top:9px">—</span></label></div>
<div class="wide"><label for="evmSetDescription">Сильные стороны модели</label><textarea id="evmSetDescription" maxlength="500" aria-describedby="evmSetDescCount"></textarea><p id="evmSetDescCount" class="muted">0 / 500</p></div></div>
</div>
<div id="evmPaneMore" role="tabpanel" aria-labelledby="evmTabMore" hidden>
<div class="form-grid"><div><label for="evmSetTimeout">Таймаут запроса, секунд</label><input id="evmSetTimeout" type="number" min="5" max="120" step="1"></div><div><label for="evmSetDiagLimit">Предел текста диагностики, символов</label><input id="evmSetDiagLimit" type="number" min="200" max="4000" step="1"></div><div><label for="evmSetFreshness">Срок актуальности проверки, дней</label><input id="evmSetFreshness" type="number" min="1" max="365" step="1"></div></div>
<p class="muted">Параметры относятся к профилю подключения и действуют для всех его моделей. Их изменение не сбрасывает статус API: срок актуальности меняет только границу между ✓ и !.</p>
</div>
<p id="evmSetDraft" class="muted" hidden>Есть несохранённые изменения. Они сохраняются, пока открыта страница, даже если закрыть окно.</p>
<div id="evmSetError" class="notice error" role="alert" hidden></div>
<div class="window-actions"><button type="button" id="evmSetReset">Отменить изменения</button><button type="button" id="evmSetSave" class="primary">Сохранить настройки</button></div>
</div></div>
<div id="evmCheckWindow" class="evm-backdrop" hidden><div class="evm-window small" role="dialog" aria-modal="true" aria-labelledby="evmCheckTitle">
<span class="eyebrow">Диагностика подключения</span>
<h3 id="evmCheckTitle" tabindex="-1"><span id="evmCheckName">Проверка API</span><span id="evmCheckDot"></span></h3>
<p id="evmCheckLast" class="muted">—</p>
<div><p class="output-label">ОТВЕТ МОДЕЛИ</p><div id="evmCheckOutput" class="output info" role="status" aria-live="polite">—</div></div>
<div class="window-actions"><button type="button" id="evmCheckClose">Закрыть</button><button type="button" id="evmCheckSend" class="primary">Отправить тестовое сообщение</button></div>
<p id="evmCheckNote" class="muted">—</p>
</div></div>
</section>
<script>
'use strict';
const $=id=>document.getElementById(id);
const view={
  workspace:null,task:null,data:null,loadedAt:0,fresh:false,epoch:0,refreshing:false,creating:false,workspaces:[],tasks:null,mode:"task",draft:null,draftWritable:false,releaseDraft:null,catalogFresh:false,restoredDraft:false,healthAt:0,folderCaps:null,pickingFolder:false,wsFormGeneration:0,wsRootRevision:0
}
;
function text(id,value){
  $(id).textContent=value==null?'—':String(value)
}
function notice(id,value){
  text(id,value);
  $(id).hidden=!value
}
function operationNotice(level,message,phase=''){
  const n=$('formError');n.className='notice '+(level||'info');n.setAttribute('data-level',level||'');
  n.setAttribute('role',level==='error'?'alert':'status');n.setAttribute('aria-live',level==='error'?'assertive':'polite');
  notice('formError',message);view.operationResult=message?{level,phase}:null;
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
const LABELS={PLANNED:'Запланировано',READY:'Готово к работе',ACTIVE:'В работе',STARTED:'Операция начата',DONE:'Выполнено · ждёт проверки',VERIFIED:'Подтверждено',COMPLETED:'Завершено',ARCHIVED:'В архиве',UNKNOWN_AFTER_DISCONNECT:'Исход неизвестен после обрыва',UNKNOWN:'Исход неизвестен',RECOVERY_REQUIRED:'Требует восстановления',NORMAL:'Восстановление не требуется',FAILED:'Ошибка',FAILED_VERIFICATION:'Проверка не пройдена',VALID:'Актуален',STALE:'Устарел',CORRUPT:'Повреждён',NOT_PREPARED:'Не подготовлен',NOT_VERIFIED:'Не подтверждено',INCONSISTENT:'Противоречивое состояние',PROJECTION_BLOCKED:'Состояние не подтверждено',BLOCKED_PREPARE:'Подготовка заблокирована',PARTIAL:'Частичный результат',NOT_CREATED:'Не создан',MISSING:'Отсутствует',RESOLUTION_STALE:'Решение устарело'};
LABELS.RECONCILIATION_REQUIRED='Нужна сверка состояния';
LABELS.NOT_APPLICABLE='Нет текущего этапа';
function statusLabel(value){return LABELS[value]||value}
function badge(s){
  const value=String(s??'Неизвестно');
  const b=element('span',statusLabel(value),'tag '+statusClass(value));b.setAttribute('title',value);return b
}
async function api(path,options={
}
){
  const {timeoutMs=15000,...requestOptions}=options;
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),timeoutMs);
  try{
    const opts={
      ...requestOptions,signal:controller.signal,cache:'no-store'
    }
    ;
    if(opts.body){
      opts.body=JSON.stringify(opts.body);
      opts.headers={
        ...opts.headers,'Content-Type':'application/json'
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
      e.details=data.error?.details;e.code=data.error?.code;e.httpStatus=r.status;
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
      workspace:view.workspace,task:view.task,draft:view.mode==='draft'&&Boolean(view.draft?.text.trim())
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
  $('emptyDetail').hidden=view.mode==='draft';
  $('draftPanel').hidden=view.mode!=='draft';
  notice('detailError','');
  text('readTime',view.task?'Загрузка выбранной TASK…':'Нет выбранной TASK')
}
function leaveDraft(){
  if(view.mode==='draft'&&view.draft?.dirty&&!window.confirm('Текст не сохранён в браузере. Скопируйте его перед уходом. Всё равно уйти?'))return false;
  if(view.releaseDraft)view.releaseDraft();view.releaseDraft=null;view.draftWritable=false;view.draft=null;return true;
}
function selectWorkspace(id){
  if(!leaveDraft())return false;
  view.epoch++;view.mode='task';view.workspace=id||null;view.task=null;
  saveSelection();clearDetail();renderNavigation();return true;
}
async function selectTask(id){
  if(!leaveDraft())return;
  view.epoch++;view.mode='task';view.task=id;saveSelection();clearDetail();renderNavigation();
  closeMobilePanels();await loadDetail(view.epoch);
}
function closeMobilePanels(){
  $('layout').className='layout';$('main').scrollTop=0;
  if(window.matchMedia('(max-width:850px)').matches){window.scrollTo(0,0);$('main').focus({preventScroll:true})}
}
function taskButton(t){
  const b=element('button',null,'task-button');b.type='button';b.dataset.task=t.task_id;
  b.setAttribute('aria-current',String(view.mode==='task'&&view.task===t.task_id));
  b.setAttribute('title',t.task_id+' · '+t.status+' · '+t.current_status);
  b.append(element('strong',t.title),badge(t.status),element('small','Этап: '+statusLabel(t.current_status)));
  if(t.blockers?.length)b.append(element('small','Блокер: '+t.blockers[0].code));
  else if(t.recovery_state!=='NORMAL')b.append(element('small',statusLabel(t.recovery_state)));
  b.onclick=()=>selectTask(t.task_id);return b;
}
function currentWorkspace(){return view.workspaces.find(w=>w.workspace_id===view.workspace)}
function draftWorkspaceConfirmed(){
  const d=view.draft,ws=currentWorkspace();
  return Boolean(view.mode==='draft'&&d&&ws&&d.workspace_id===view.workspace&&d.workspace_root===ws.workspace_root);
}
function draftKey(ws=currentWorkspace()){return ws?'webAlarm.draft.v1.'+encodeURIComponent(ws.workspace_id)+'|'+encodeURIComponent(ws.workspace_root):null}
function readDraft(ws=currentWorkspace()){
  const key=draftKey(ws);if(!key)return null;
  const raw=localStorage.getItem(key);if(!raw)return null;const d=JSON.parse(raw);
  if(d.schema!==1||d.workspace_id!==ws.workspace_id||d.workspace_root!==ws.workspace_root||typeof d.text!=='string')throw Error('Формат локального черновика не распознан. Исходные данные не перезаписаны.');
  if(d.registration!=null&&!['pending','unknown','confirmed'].includes(d.registration.state))throw Error('Неизвестное состояние регистрации черновика.');
  return {...d,key,dirty:false};
}
function renderNavigation(){
  const focused=document.activeElement?.dataset?.task,ws=currentWorkspace();
  $('workspaceList').replaceChildren(...view.workspaces.map(w=>{
    const b=element('button',w.display_name,'workspace-button');b.type='button';b.dataset.workspace=w.workspace_id;
    b.setAttribute('aria-current',String(w.workspace_id===view.workspace));b.setAttribute('title',w.workspace_root);b.onclick=()=>selectWorkspace(w.workspace_id);return b;
  }));
  if(!view.workspaces.length)$('workspaceList').append(element('p','Зарегистрированных проектов нет. Добавьте Workspace.','muted'));
  text('workspacePath',ws?.workspace_root||'Проект не выбран');text('taskWorkspaceName',ws?.display_name||'Сначала выберите проект');$('newTask').disabled=!ws;
  const rows=view.tasks||{active:[],completed:[],errors:[]};
  for(const key of ['active','completed']){
    const tasks=rows[key].filter(t=>t.workspace_id===view.workspace).sort((a,b)=>a.created_at.localeCompare(b.created_at)||a.task_id.localeCompare(b.task_id));
    $(key+'Tasks').replaceChildren(...(tasks.length?tasks.map(taskButton):[element('p',key==='active'?'Текущих TASK нет':'Завершённых TASK нет','muted')]));
    if(key==='completed')text('completedCount','('+tasks.length+')');
  }
  $('draftEntry').replaceChildren();
  try{const d=view.mode==='draft'?view.draft:readDraft();if(d?.text.trim()){
    const b=element('button',null,'task-button draft-row');b.type='button';b.setAttribute('aria-current',String(view.mode==='draft'));
    b.append(element('strong',d.text.trim().split(/\r?\n/)[0].slice(0,70)),element('small','Черновик · только этот браузер'));b.onclick=openDraft;$('draftEntry').append(b);
  }}catch(_){$('draftEntry').append(element('p','Локальный черновик недоступен. Откройте + для диагностики.','muted'))}
  if(focused)for(const b of document.querySelectorAll('[data-task]'))if(b.dataset.task===focused)b.focus({preventScroll:true});
  if(rows.errors?.length)notice('navigationError','Недоступные TASK (Workspace не подтверждён):\n'+rows.errors.map(e=>e.task_id+': '+e.reason).join('\n'));
}
function showDraft(){
  const d=view.draft;if(!d)return;
  if($('taskRaw').value!==d.text)$('taskRaw').value=d.text;const pending=d.registration&&d.registration.state!=='confirmed';
  $('taskRaw').readOnly=!view.draftWritable||Boolean(d.registration);
  $('createTask').disabled=!view.draftWritable||!d.text.trim()||Boolean(d.registration)||view.creating||!view.catalogFresh||!draftWorkspaceConfirmed();
  $('discardDraft').disabled=!view.draftWritable||view.creating||Boolean(pending);
  const state=d.registration?(d.registration.state==='confirmed'?'Локальная запись: сервер ранее подтвердил TASK '+d.registration.task_id+'. Текущее состояние смотрите в карточке справа.':d.registration.state==='pending'&&view.creating?'Ожидаем подтверждение сервера. Постановка защищена локально.':'Исход регистрации неизвестен. Текст защищён; повторная отправка заблокирована. Обновите список TASK и сверьте его с постановкой.'):
    d.dirty?'Не сохранён · только в памяти этой страницы. Скопируйте текст.':d.text.trim()?'Черновик сохранён в этом браузере · '+new Date(d.updated_at).toLocaleTimeString('ru-RU'):'Пустая форма · ничего не сохранено';
  text('draftStatus',state);text('draftWorkspace',draftWorkspaceConfirmed()?currentWorkspace().display_name:d.workspace_id+' · Workspace не подтверждён');
  text('discardDraft',d.text.trim()?'Удалить локальный черновик':'Закрыть пустую форму');
}
function persistDraft(){
  const d=view.draft;if(!d||!view.draftWritable)return false;
  try{
    if(!d.text.trim()&&!d.registration)localStorage.removeItem(d.key);
    else{const saved={schema:1,workspace_id:d.workspace_id,workspace_root:d.workspace_root,text:d.text,registration:d.registration,updated_at:new Date().toISOString()};localStorage.setItem(d.key,JSON.stringify(saved));d.updated_at=saved.updated_at;}
    d.dirty=false;notice('draftError','');showDraft();saveSelection();renderNavigation();return true;
  }catch(e){d.dirty=true;notice('draftError','Браузер не сохранил текст: '+e.message+'. Скопируйте его в отдельный документ.');showDraft();return false}
}
function openDraft(){
  const ws=currentWorkspace();if(view.mode==='draft'&&view.releaseDraft){$('taskRaw').focus();return}if(!ws||!leaveDraft())return;
  view.epoch++;const epoch=view.epoch;view.mode='draft';view.task=null;clearDetail();closeMobilePanels();
  try{view.draft=readDraft(ws)||{schema:1,workspace_id:ws.workspace_id,workspace_root:ws.workspace_root,key:draftKey(ws),text:'',registration:null,dirty:false};
    if(view.draft.registration?.state==='pending')view.draft.registration.state='unknown';
  }catch(e){view.draft=null;notice('draftError',e.message);$('taskRaw').value='';$('taskRaw').readOnly=true;$('createTask').disabled=true;$('discardDraft').disabled=true;text('draftStatus','Данные не изменены. Восстановите локальный черновик перед редактированием.');return}
  view.draftWritable=false;notice('draftError','');showDraft();saveSelection();renderNavigation();
  // Web Locks prevents two tabs from overwriting the same local draft.
  if(!navigator.locks?.request){notice('draftError','Браузер не поддерживает защиту черновика между вкладками. Доступны чтение и копирование; используйте Chrome/Edge.');return}
  navigator.locks.request(view.draft.key,{ifAvailable:true},lock=>{
    if(epoch!==view.epoch)return;
    if(!lock){notice('draftError','Этот черновик уже открыт в другой вкладке. Здесь доступны чтение и копирование. Закройте другой редактор и снова нажмите +.');showDraft();return}
    // The record may have changed between the initial read and acquiring the lock.
    // Reread before enabling input, so a newly released tab's text cannot be lost.
    try{view.draft=readDraft(ws)||view.draft;if(view.draft.registration?.state==='pending')view.draft.registration.state='unknown'}
    catch(e){notice('draftError',e.message);showDraft();return}
    view.draftWritable=true;showDraft();$('taskRaw').focus({preventScroll:true});
    return new Promise(resolve=>{view.releaseDraft=resolve});
  }).catch(e=>{if(epoch===view.epoch){view.draftWritable=false;notice('draftError','Защита черновика недоступна: '+e.message);showDraft()}});
}
function discardDraft(){
  if(!view.draftWritable||!view.draft||view.creating||view.draft.registration&&view.draft.registration.state!=='confirmed')return;
  if(view.draft.text.trim()&&!window.confirm('Удалить только локальный черновик? Зарегистрированные TASK и их evidence останутся.'))return;
  try{localStorage.removeItem(view.draft.key);view.draft.text='';view.draft.registration=null;view.draft.dirty=false;selectWorkspace(view.workspace)}catch(e){notice('draftError','Не удалось удалить локальный черновик: '+e.message)}
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
  text('taskGoalText',t.goal===t.raw_task?'Постановка сохранена. План и исполнение формируются отдельно.':t.goal);
  text('taskDescription',t.raw_task);
  $('taskBadge').replaceChildren(badge(t.status));
  text('progressText',!o.coherent||o.progress.verified==null?'VERIFIED-прогресс не подтверждён':o.progress.total===0?'План ещё не содержит этапов.':'Подтверждено '+o.progress.verified+' / '+o.progress.total);
  text('doneText',o.progress.done+' выполнено · ожидает проверки');
  const known=o.coherent&&o.progress.verified!=null&&o.progress.total>0;
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
  text('currentStage',v.current_microtask_id?(v.current_microtask_id+' · '+statusLabel(p.position.current_status)):'Не определён');
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
    for(const report of m.events.filter(e=>e.event_type==='REPORT')){const r=element('details');r.open=true;r.append(element('summary','Отчёт этапа'),element('p',report.payload?.report||'Текст отчёта недоступен','report-text'));body.append(r)}
    const e=element('details');
    e.append(element('summary','Evidence этапа ('+m.events.length+' событий)'),element('pre',JSON.stringify({
      events:m.events,operations:m.operations,recovery_reports:m.recovery_reports
    }
    ,null,2)));
    body.append(e);
    d.append(s,body);
    $('timeline').append(d)
  }
  if(!o.stages.length)$('timeline').append(element('p',o.coherent?'План ещё не содержит этапов.':'Состав плана не подтверждён. Обновите состояние.','empty'));
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
    field(dl,'Reconciliation',statusLabel(current.projection.recovery?.state)||'Нет требования в Projection')
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
    facts.append(element('p',op.operation_id+' · '+statusLabel(op.recovery.state)+' · '+(op.recovery.next_safe_action||v.next_safe_action),'notice info'));
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
  if(!view.task||view.mode!=='task')return;
  const task=view.task,workspace=view.workspace;
  $('detail').setAttribute('aria-busy','true');
  try{
    const v=await api('/tasks/'+encodeURIComponent(task)+'/ui');
    if(epoch!==view.epoch)return;
    if(v.task_state?.task.task_id!==task||v.workspace?.workspace_id!==workspace||!v.operator)throw new Error('Ответ не соответствует выбранным Workspace / TASK');
    const p=v.operator.progress;
    if(typeof v.operator.coherent!=='boolean'||!p||!Number.isInteger(p.total)||p.total<0||!Number.isInteger(p.done)||p.done<0||p.done>p.total||p.verified!==null&&(!Number.isInteger(p.verified)||p.verified<0||p.verified>p.total))throw new Error('Некорректные данные прогресса или согласованности снимка');
    try{render(v)}catch(e){clearDetail();throw new Error('Некорректный снимок скрыт: '+e.message)}
    view.data=v;
    view.loadedAt=Date.now();
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
  if(view.refreshing)return;view.refreshing=true;$('refresh').disabled=true;const epoch=view.epoch;
  try{
    const [health,w,t]=await Promise.allSettled([api('/status'),api('/workspaces'),api('/ui/tasks')]);
    if(epoch!==view.epoch)return;
    const online=health.status==='fulfilled'&&health.value?.service==='web_alarm_server';
    view.healthAt=Date.now();text('serverStatus',online?'Сервер доступен':'Нет свежего соединения');$('serverStatus').setAttribute('data-state',online?'online':'offline');
    $('serverStatus').setAttribute('title',online?health.value.service+' · '+health.value.mode+' · API '+health.value.api_version:'Проверка GET /status не дала свежего ответа');
    if(!online)throw health.reason||Error('Некорректный health ответ');
    if(w.status==='rejected'||t.status==='rejected')throw w.reason||t.reason;
    if(!Array.isArray(w.value.workspaces)||!Array.isArray(t.value.active)||!Array.isArray(t.value.completed))throw Error('Некорректный список Workspace / TASK');
    view.workspaces=w.value.workspaces;view.tasks=t.value;view.catalogFresh=true;
    if(view.operationResult?.phase==='rejected')operationNotice(null,'');
    // Keep every editor bound to its original ID/root, including an empty one.
    // Another Workspace may be selected only by an explicit user action.
    if(view.mode==='draft'&&view.draft&&!draftWorkspaceConfirmed()){
      view.catalogFresh=false;renderNavigation();showDraft();notice('navigationError','Workspace черновика больше не подтверждён сервером или изменил путь. Текст остаётся в исходном черновике; регистрация заблокирована. Выберите проект явно и обновите данные.');return;
    }
    if(!currentWorkspace()){
      view.workspace=view.workspaces[0]?.workspace_id||null;view.task=null;clearDetail();
    }
    if(view.task&&![...view.tasks.active,...view.tasks.completed].some(t=>t.task_id===view.task&&t.workspace_id===view.workspace)){view.task=null;clearDetail()}
    notice('navigationError','');renderNavigation();saveSelection();
    if(view.restoredDraft){view.restoredDraft=false;openDraft()}
    else if(view.mode==='draft'){setFresh(false);showDraft()}else await loadDetail(epoch);
  }catch(e){if(epoch!==view.epoch)return;view.catalogFresh=false;notice('navigationError',e.message);setFresh(false,view.data?'Связь или данные недоступны. Показан предыдущий снимок; NEXT SAFE ACTION устарел.':'Данные сервера недоступны. Обновите после восстановления связи.');if(view.mode==='draft')showDraft()}
  finally{view.refreshing=false;$('refresh').disabled=false}
}
async function create(kind){
  if(view.creating)return;
  if(kind==='workspace'&&view.pickingFolder){operationNotice('warning','Завершите выбор папки перед регистрацией Workspace.','rejected');return}
  if(view.refreshing){operationNotice('warning','Дождитесь завершения обновления.','rejected');return}
  const ws=kind==='workspace',d=view.draft,epoch=view.epoch,formGeneration=view.wsFormGeneration;
  if(!ws&&(!d||!view.draftWritable||!d.text.trim()||d.registration||!view.catalogFresh||!draftWorkspaceConfirmed()))return;
  const raw=d?.text.trim(),body=ws?{display_name:$('wsName').value,workspace_root:$('wsRoot').value}:
    {workspace_id:d.workspace_id,title:Array.from(raw.split(/\r?\n/)[0]).slice(0,120).join(''),goal:raw,raw_task:raw};
  if(ws&&!window.confirm('Добавить Workspace «'+body.display_name+'» по пути '+body.workspace_root+'?'))return;
  if(!ws){d.registration={state:'pending',submitted_at:new Date().toISOString()};if(!persistDraft()){d.registration=null;showDraft();return}}
  view.creating=true;folderControls();if(!ws)showDraft();notice('draftError','');
  operationNotice('info',ws?'Регистрируем Workspace «'+body.display_name+'»…':'Регистрируем TASK «'+body.title+'»…','pending');
  try{
    const data=await api(ws?'/workspaces':'/tasks',{method:'POST',body});
    if(!ws){const t=data.task;if(!t||typeof t.task_id!=='string'||t.workspace_id!==body.workspace_id||t.raw_task!==raw||t.title!==body.title||t.goal!==body.goal)throw Error('Ответ регистрации не подтверждает исходную постановку');
      d.registration={state:'confirmed',task_id:t.task_id};
      // Never remove another draft if selection changed while POST was in flight.
      if(view.draft===d){persistDraft();try{localStorage.removeItem(d.key)}catch(_){}if(epoch===view.epoch){const id=t.task_id;d.dirty=false;await selectTask(id)}}

    }else{
      const w=data.workspace;
      if(!w||typeof w.workspace_id!=='string'||!w.workspace_id||w.display_name!==body.display_name.trim()||typeof w.workspace_root!=='string'||!w.workspace_root.trim())throw Error('Ответ регистрации Workspace не подтверждает проект');
      if(epoch===view.epoch&&formGeneration===view.wsFormGeneration&&view.mode!=='draft'){view.epoch++;view.workspace=w.workspace_id;view.task=null;view.mode='task';clearDetail();saveSelection();$('workspaceFormPanel').hidden=true}
    }
    await refresh();operationNotice('success',ws?'Workspace «'+data.workspace.display_name+'» успешно зарегистрирован.':'TASK «'+data.task.title+'» успешно зарегистрирована.','success');
  }catch(e){
    if(!ws){d.registration={...d.registration,state:'unknown'};if(view.draft===d){persistDraft();notice('draftError',e.message+'\nИсход регистрации неизвестен. Автоматического повтора нет; проверьте список TASK.');showDraft()}}
    await refresh();
    const rejected=e.serverRejected&&e.httpStatus<500;
    operationNotice(rejected?'error':'warning',rejected?'Сервер отклонил регистрацию '+(ws?'Workspace':'TASK')+': '+e.message:
      'Исход регистрации '+(ws?'Workspace':'TASK')+' неизвестен. '+e.message+'\nПроверьте каталог и исходную постановку; автоматического повтора нет.',rejected?'rejected':'unknown');
  }finally{view.creating=false;folderControls();if(view.mode==='draft')showDraft()}
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
function folderNotice(level,message){$('folderPickerNotice').className='notice '+level;notice('folderPickerNotice',message)}
function folderControls(){
  $('browseWorkspace').disabled=view.pickingFolder||view.creating||!view.folderCaps;
  $('browseWorkspace').textContent=view.pickingFolder?'Выбираем…':'Обзор…';
  $('createWorkspace').disabled=view.creating||view.pickingFolder;
}
async function loadFolderCapabilities(){
  const generation=view.wsFormGeneration;view.folderCaps=null;folderControls();folderNotice('info','Проверяем доступность выбора папки…');
  try{
    const response=await api('/ui/capabilities'),cap=response.folder_picker;
    if(generation!==view.wsFormGeneration||$('workspaceFormPanel').hidden)return;
    if(cap?.available===true&&typeof cap.token==='string'&&cap.token.length>=32){view.folderCaps=cap;folderNotice('info','Обзор откроет системный выбор папки. Ручной ввод также доступен.')}
    else folderNotice('warning','Нативный выбор папки недоступен в этом запуске. Введите абсолютный путь вручную.');
  }catch(e){if(generation===view.wsFormGeneration&&!$('workspaceFormPanel').hidden)folderNotice('warning','Не удалось проверить выбор папки. Введите путь вручную. '+e.message)}
  finally{folderControls()}
}
async function pickWorkspaceFolder(){
  if(view.pickingFolder||view.creating||!view.folderCaps||$('workspaceFormPanel').hidden)return;
  const generation=view.wsFormGeneration,revision=view.wsRootRevision,previous=$('wsRoot').value,token=view.folderCaps.token;
  view.pickingFolder=true;folderControls();folderNotice('info','Выберите папку в окне Windows или нажмите «Отмена». Путь ещё не изменён.');
  try{
    const result=await api('/ui/pick-workspace-folder',{method:'POST',body:{},headers:{'X-WebAlarm-Folder-Token':token},timeoutMs:125000});
    if(generation!==view.wsFormGeneration||$('workspaceFormPanel').hidden)return;
    if(revision!==view.wsRootRevision||$('wsRoot').value!==previous){folderNotice('warning','Путь уже изменён вручную. Результат старого выбора не применён.');return}
    if(result.status==='CANCELLED'&&!('workspace_root' in result)){folderNotice('info','Выбор папки отменён. Путь не изменён.');return}
    if(result.status!=='SELECTED'||typeof result.workspace_root!=='string'||! /^(?:[A-Za-z]:[\\/]|\\\\)/.test(result.workspace_root))throw Error('Некорректный ответ выбора папки');
    $('wsRoot').value=result.workspace_root;view.wsRootRevision++;
    folderNotice('info','Папка выбрана. Проверьте название и подтвердите регистрацию Workspace отдельно.');
  }catch(e){
    if(generation===view.wsFormGeneration&&!$('workspaceFormPanel').hidden){
      if(e.httpStatus===403)await loadFolderCapabilities();
      if(generation===view.wsFormGeneration&&!$('workspaceFormPanel').hidden)folderNotice('warning','Путь не изменён. Введите его вручную или повторите выбор. '+e.message);
    }
  }finally{view.pickingFolder=false;folderControls()}
}
$('addWorkspace').onclick=async()=>{view.wsFormGeneration++;$('workspaceFormPanel').hidden=false;$('wsName').focus();await loadFolderCapabilities()};
$('cancelWorkspace').onclick=()=>{view.wsFormGeneration++;$('workspaceFormPanel').hidden=true};
$('wsRoot').oninput=()=>{view.wsRootRevision++};
$('browseWorkspace').onclick=pickWorkspaceFolder;
$('newTask').onclick=openDraft;$('discardDraft').onclick=discardDraft;
$('taskRaw').oninput=()=>{if(view.draft&&view.draftWritable&&!view.draft.registration){view.draft.text=$('taskRaw').value;view.draft.dirty=true;persistDraft()}};
$('copyDraft').onclick=()=>copy(view.draft?.text||$('taskRaw').value);
$('refresh').onclick=refresh;
$('showWorkspaces').onclick=()=>{$('layout').className=$('layout').className==='layout show-workspaces'?'layout':'layout show-workspaces'};
$('showTasks').onclick=()=>{$('layout').className=$('layout').className==='layout show-tasks'?'layout':'layout show-tasks'};
$('workspaceForm').onsubmit=e=>{e.preventDefault();create('workspace')};
$('taskForm').onsubmit=e=>{e.preventDefault();create('task')};
window.addEventListener('beforeunload',e=>{if(view.mode==='draft'&&view.draft?.dirty){e.preventDefault();e.returnValue=''}});
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
  copy(['TASK: '+v.task_state.task.task_id,'Workspace: '+v.workspace.workspace_id,'Снимок: '+v.operator.read_at,'Свежий: '+view.fresh,'Статус: '+v.task_state.task.status,'Исходная постановка: '+v.task_state.task.raw_task,'Цель: '+v.task_state.task.goal,'План: '+JSON.stringify(v.task_state.plan),'Отчёты этапов: '+JSON.stringify(v.reports),'Этап: '+v.current_microtask_id,'Recovery: '+v.recovery_state,'NEXT SAFE ACTION: '+v.next_safe_action].join('\n'))
}
;
// WUA-1 EVM: connections of the shared Ultra core. Nothing is requested until the tab is opened;
// every model comes from the server read model of model_registry, never from a list in this page.
// Model cards (CLAUDE-WUA-EVM-MODEL-CARD-UI-001): one component for every model; roles, API status, hints and
// limits come from /ultra/model-cards. Drafts and diagnostic answers live per model while the page is open.
const evm={epoch:0,busy:false,data:null,cards:null,cardsError:null,view:'chat',drafts:{},outputs:{},window:null,buttons:{},tab:'conn',saving:false,checking:false,setError:'',chatTouched:false};
const EVM_STATUS={REGISTERED:['В реестре',''],DISABLED:['Отключена в реестре','bad'],NOT_CONNECTED:['Ещё не подключено','unknown'],AVAILABLE:['Реестр загружен',''],REGISTRY_UNAVAILABLE:['Реестр недоступен','bad']};
function evmTag(code){const [label,cls]=EVM_STATUS[code]||[String(code??'Неизвестно'),'unknown'];const t=element('span',label,'tag'+(cls?' '+cls:''));t.setAttribute('title',String(code??''));return t}
// Three sections: Ultra Chat (default), the operator panel and EVM. #operator / #evm / #chat open one directly.
const VIEWS={chat:['chatView','viewChat','#chatMain','К истории диалога'],operator:['layout','viewOperator','#main','К состоянию TASK'],evm:['evmView','viewEvm','#evmHeading','К подключениям Ultra']};
function initialView(){
  try{return {'#operator':'operator','#evm':'evm','#chat':'chat'}[typeof location==='undefined'?'':String(location.hash||'')]||'chat'}catch(_){return 'chat'}
}
function rememberView(name){
  try{if(typeof history!=='undefined'&&typeof location!=='undefined'&&history.replaceState)history.replaceState(null,'','#'+name)}catch(_){}
}
function showView(name,initial=false){
  if(!VIEWS[name])name='chat';evm.view=name;
  for(const [key,[region,button]] of Object.entries(VIEWS)){$(region).hidden=key!==name;$(button).setAttribute('aria-pressed',String(key===name))}
  $('showWorkspaces').hidden=name!=='operator';$('showTasks').hidden=name!=='operator';
  $('skipLink').setAttribute('href',VIEWS[name][2]);text('skipLink',VIEWS[name][3]);
  if(!initial)rememberView(name);
  if(name==='evm'){if(!initial)$('evmHeading').focus();return loadEvm()}
  if(name==='chat'){if(!initial)$('chatHeading').focus();return startChat()}
  if(!initial)$('main').focus()
}
function validEvm(data){
  const api=data?.columns?.api;
  if(!api||!Array.isArray(api.connections)||!data.columns.mcp_agents||!data.columns.local_llm||!data.selection?.chat)return false;
  return api.connections.every(c=>c&&['connection_id','model_id','display_name','provider_model_id','status','verification'].every(k=>typeof c[k]==='string')&&typeof c.selectable==='boolean'&&typeof c.selected==='boolean')
}
function evmSelectionText(s){
  if(s.state==='SAVED')return 'Выбрана: '+s.display_name+' · '+s.model_id+' → '+s.provider_model_id+(s.selected_at?' · сохранено '+s.selected_at:'');
  if(s.state==='CORRUPT')return 'Сохранённый выбор повреждён и не используется. Выберите модель заново.';
  if(s.state==='INVALID_REFERENCE')return 'Сохранённая модель недоступна в реестре ('+(s.connection_id||'—')+'). Выберите модель заново.';
  if(s.state==='REGISTRY_UNAVAILABLE')return 'Сохранённый выбор ('+(s.connection_id||'—')+') сейчас не проверить: общий реестр моделей недоступен.';
  return 'Модель для Ultra Web Chat ещё не выбрана.'
}
function validCards(d){
  return !!d&&Array.isArray(d.cards)&&Array.isArray(d.role_definitions)&&Array.isArray(d.providers)&&Array.isArray(d.profiles)&&!!d.settings&&!!d.limits&&!!d.live_check&&
    d.role_definitions.every(r=>r&&['role','label','hint'].every(k=>typeof r[k]==='string'))&&
    d.cards.every(c=>c&&['connection_id','model_id','display_name','provider_id','provider_model_id','profile_id','settings_version','description'].every(k=>typeof c[k]==='string')&&
      Array.isArray(c.roles)&&!!c.api&&['green','orange','red'].includes(c.api.color))
}
const API_TEXT={CONFIRMED:'Ответ модели подтверждён',STALE:'Подтверждение устарело',NEVER_CONFIRMED:'Успешной проверки ещё не было',SETTINGS_CHANGED:'Настройки подключения изменились — нужна новая проверка',
  LAST_CHECK_FAILED:'Последняя проверка завершилась отказом',STATE_CORRUPT:'Сведения о проверках повреждены',TIMESTAMP_INVALID:'Дата проверки некорректна',ADAPTER_MISSING:'Для провайдера нет адаптера',REGISTRY_DISABLED:'Модель отключена в реестре'};
const API_MARK={green:'✓',orange:'!',red:'×'};
function apiText(a){
  const base=API_TEXT[a.reason]||String(a.reason||'Статус неизвестен');
  return a.color==='red'?base:base+': '+a.age_days+' дн. назад, срок актуальности '+a.freshness_days+' дн.'
}
function apiDot(a){  // one component and one server status for the card header and the diagnostic window
  const color=API_MARK[a.color]?a.color:'red';
  const d=element('span',API_MARK[color],'api-dot '+color);
  d.setAttribute('role','img');d.setAttribute('aria-label','Статус API: '+apiText(a));d.setAttribute('title',apiText(a));d.setAttribute('data-api',color+':'+a.reason);
  return d
}
const ROLE_MARK={assigned:['✓','yes','назначена'],assigned_off:['✓','off','назначена, но роль выключена'],assigned_pending:['✓','off','назначена, но роль пока не работает'],not_assigned:['×','no','не назначена'],not_in_runtime:['–','na','такой роли в runtime пока нет'],unknown:['?','unknown','источник назначений недоступен']};
function roleItem(def,state){
  const [mark,cls,label]=ROLE_MARK[state]||ROLE_MARK.unknown;
  const item=element('span',null,'role');item.setAttribute('data-role',def.role);item.setAttribute('data-state',ROLE_MARK[state]?state:'unknown');
  const m=element('span',mark,'mark '+cls);m.setAttribute('aria-hidden','true');
  const name=element('span',def.label,'name');name.setAttribute('tabindex','0');
  name.setAttribute('data-hint',def.hint+' Сейчас: '+label+'.');name.setAttribute('aria-label',def.label+' — '+label+'. '+def.hint);
  item.append(m,name);return item
}
function paramsText(v){return (typeof v==='number'?String(v).replace('.',','):'—')+' млрд'}
function fmtTime(iso){const d=new Date(iso);return isNaN(d.getTime())?String(iso):d.toLocaleString('ru-RU')}
function cardData(id){return evm.cards?.cards.find(c=>c.model_id===id)||null}
function modelCard(c,data){
  const card=element('article',null,'mcard');card.setAttribute('data-connection',c.connection_id);card.setAttribute('data-model',c.model_id);card.setAttribute('aria-label','Модель '+c.display_name);
  const head=element('div',null,'mcard-head');
  const params=element('span',paramsText(c.params_billion),'params');params.setAttribute('title',c.params_billion==null?'Количество параметров не указано':'Количество параметров, указано пользователем');
  const provider=data.providers.find(p=>p.provider_id===c.provider_id);
  head.append(element('h4',c.display_name,'mcard-name'),apiDot(c.api),params,element('span',provider?provider.display_name:c.provider_id,'mcard-side'));
  const sub=element('div',null,'mcard-sub');sub.append(element('strong','Назначенные роли'),element('span','Наведите на название для описания','mcard-note'));
  const states=new Map(c.roles.map(r=>[r.role,r.state]));
  const roles=element('div',null,'roles');roles.append(...data.role_definitions.map(def=>roleItem(def,states.get(def.role))));
  const strengths=element('div',c.description||'Описание пока не заполнено. Сильные стороны модели указываются в «Настройках».','strengths'+(c.description?'':' placeholder'));
  strengths.setAttribute('tabindex','0');strengths.setAttribute('aria-label','Сильные стороны модели '+c.display_name);
  const settings=element('button','⚙ Настройки');settings.type='button';settings.setAttribute('aria-label','Настройки модели '+c.display_name);settings.onclick=()=>openWindow('settings',c.model_id);
  const check=element('button','▤ Проверить чат','primary');check.type='button';check.setAttribute('aria-label','Проверка API модели '+c.display_name);check.onclick=()=>openWindow('check',c.model_id);
  evm.buttons[c.model_id]={settings,check};
  const actions=element('div',null,'mcard-actions');actions.append(settings,check);
  card.append(head,sub,roles,element('span','Сильные стороны модели','mcard-label'),strengths,actions);
  if(evm.drafts[c.model_id])card.append(element('p','Есть несохранённые изменения настроек.','mcard-note'));
  return card
}
function plainCard(c,reason){  // the registry entry is known, its card data is not: no invented roles or status
  const card=element('article',null,'mcard');card.setAttribute('data-connection',c.connection_id);card.setAttribute('data-model',c.model_id);
  const head=element('div',null,'mcard-head');head.append(element('h4',c.display_name,'mcard-name'));
  card.append(head,element('p','Подробности карточки недоступны: '+reason,'mcard-note'));return card
}
function rolesSourceText(cards){
  if(!cards)return 'Назначения ролей не загружены.';
  const r=cards.roles_source,tk={SAVED:'настройки прежней Ultra (Tkinter)',DEFAULTS:'значения прежней Ultra по умолчанию: её файл настроек не найден',
    UNREADABLE:'файл настроек прежней Ultra не читается, поэтому её роли показаны как «?»',NOT_CONNECTED:'этот запуск не подключён к настройкам прежней Ultra, поэтому её роли показаны как «?»'}[r.state]||String(r.state);
  return 'Источник ролей: «Чат» — выбор выше; остальные — '+tk+'.'+(r.fallbacks?.length?' Сохранённая модель '+r.fallbacks.length+' роли(ей) отсутствует в реестре, Ultra использует свою модель по умолчанию.':'')
}
function renderChatChoice(api,s){
  const select=$('evmChatModel'),keep=select.value;
  const first=element('option','— не выбрана —');first.value='';first.disabled=true;
  select.replaceChildren(first,...api.connections.map(c=>{const o=element('option',c.display_name+(c.selectable?'':' — отключена'));o.value=c.connection_id;o.disabled=!c.selectable;return o}));
  select.value=evm.chatTouched&&api.connections.some(c=>c.connection_id===keep)?keep:(s.state==='SAVED'?s.connection_id:'');
  $('evmChatSave').disabled=evm.busy||!api.connections.some(c=>c.selectable)
}
function renderEvm(){
  const data=evm.data;if(!data)return;
  const api=data.columns.api,s=data.selection.chat,cards=evm.cards;
  $('evmApiState').replaceChildren(evmTag(api.state));
  $('evmMcpState').replaceChildren(evmTag(data.columns.mcp_agents.state));
  $('evmLocalState').replaceChildren(evmTag(data.columns.local_llm.state));
  text('evmSelection',evmSelectionText(s));
  renderChatChoice(api,s);
  if(api.state!=='AVAILABLE')notice('evmError','Общий реестр моделей недоступен: '+(api.reason||api.state));
  const full=new Map((cards?.cards||[]).map(c=>[c.connection_id,c]));
  evm.buttons={};
  const list=api.connections.map(c=>full.has(c.connection_id)?modelCard(full.get(c.connection_id),cards):plainCard(c,evm.cardsError||'нет данных сервера'));
  $('evmApiList').replaceChildren(...list);
  text('evmRolesSource',rolesSourceText(cards));
  text('evmState',list.length?'Моделей в реестре: '+list.length:'Реестр пуст')
}
async function loadEvm(){
  const epoch=++evm.epoch;$('evmRefresh').disabled=true;notice('evmError','');text('evmState','Загружаем реестр…');
  const [catalog,cards]=await Promise.allSettled([api('/ultra/connections'),api('/ultra/model-cards')]);
  if(epoch!==evm.epoch)return;
  try{
    if(catalog.status==='rejected')throw catalog.reason;
    if(!validEvm(catalog.value))throw new Error('Некорректный ответ сервера о подключениях');
    evm.data=catalog.value;
    if(cards.status==='fulfilled'&&validCards(cards.value)){evm.cards=cards.value;evm.cardsError=null}
    else{evm.cards=null;evm.cardsError=cards.status==='rejected'?cards.reason.message:'некорректный ответ сервера о карточках'}
    renderEvm();
    const damaged=[evm.cards?.settings.state==='CORRUPT'?'настройки карточек':null,evm.cards?.checks?.state==='CORRUPT'?'сведения о проверках API':null].filter(Boolean);
    if(evm.cardsError)notice('evmError','Карточки моделей недоступны: '+evm.cardsError);
    else if(damaged.length)notice('evmError','Повреждены '+damaged.join(' и ')+'. Файл сохранён для разбора; следующее сохранение начнёт запись заново, статусы до новой проверки — ×.');
    if(evm.window)fillWindow()
  }catch(e){
    notice('evmError','Не удалось получить подключения: '+e.message);text('evmState','Список не обновлён')
  }finally{$('evmRefresh').disabled=false}
}
async function selectConnection(id){
  if(evm.busy)return;evm.busy=true;notice('evmNotice','');notice('evmError','');
  $('evmChatSave').disabled=true;
  let saved=null,error=null;
  try{
    const r=await api('/ultra/connections/selection',{method:'POST',body:{role:'chat',connection_id:id}});
    if(r?.selection?.state!=='SAVED'||r.selection.connection_id!==id)throw new Error('Сервер не подтвердил сохранение выбора');
    saved=r.selection
  }catch(e){error=e}
  evm.busy=false;evm.chatTouched=false;
  await loadEvm();
  if(error)notice('evmError','Выбор не сохранён: '+error.message);
  else notice('evmNotice','Выбор сохранён: '+saved.display_name+' ('+saved.provider_model_id+')')
}
// Settings and diagnostics windows. Only one is shown at a time; closing or switching keeps the draft of every
// model and the last diagnostic answer, so opening one window never destroys the state of the other.
const EVM_TABS={conn:['evmTabConn','evmPaneConn'],model:['evmTabModel','evmPaneModel'],more:['evmTabMore','evmPaneMore']};
const PROFILE_FIELDS=[['timeout_seconds','evmSetTimeout'],['diagnostic_limit_chars','evmSetDiagLimit'],['freshness_days','evmSetFreshness']];
function selectTab(name){
  evm.tab=EVM_TABS[name]?name:'conn';
  for(const [key,[tab,pane]] of Object.entries(EVM_TABS)){$(tab).setAttribute('aria-selected',String(key===evm.tab));$(tab).setAttribute('tabindex',key===evm.tab?'0':'-1');$(pane).hidden=key!==evm.tab}
}
function profileValues(id){const p=evm.cards?.profiles.find(x=>x.profile_id===id)||{};return Object.fromEntries(PROFILE_FIELDS.map(([k])=>[k,p[k]==null?'':String(p[k])]))}
function initialDraft(c){
  return {base_revision:evm.cards.settings.revision,profile_id:c.profile_id,profile:profileValues(c.profile_id),
    params:c.params_billion==null?'':String(c.params_billion),description:c.description}
}
function facts(id,rows){
  const list=[];for(const [k,v] of rows){list.push(element('dt',k),element('dd',v==null||v===''?'—':v))}
  $(id).replaceChildren(...list)
}
function openWindow(kind,id){
  if(!cardData(id))return;
  evm.window={kind,id};evm.setError='';
  fillWindow();
  $(kind==='settings'?'evmSetTitle':'evmCheckTitle').focus()
}
function closeWindow(){
  const w=evm.window;if(!w)return;
  evm.window=null;$('evmSettingsWindow').hidden=true;$('evmCheckWindow').hidden=true;
  renderEvm();
  evm.buttons[w.id]?.[w.kind]?.focus()
}
function fillWindow(){
  const w=evm.window;if(!w)return;
  if(!cardData(w.id)){closeWindow();return}
  $('evmSettingsWindow').hidden=w.kind!=='settings';$('evmCheckWindow').hidden=w.kind!=='check';
  if(w.kind==='settings')fillSettings();else fillCheck()
}
function fillSettings(){
  const c=cardData(evm.window.id),data=evm.cards,d=evm.drafts[c.model_id]||initialDraft(c);
  const provider=data.providers.find(p=>p.provider_id===c.provider_id);
  text('evmSetModel',c.display_name+' · модель провайдера '+c.provider_model_id);
  const po=element('option',provider?provider.display_name:c.provider_id);po.value=c.provider_id;
  $('evmSetProvider').replaceChildren(po);$('evmSetProvider').value=c.provider_id;$('evmSetProvider').disabled=true;  // the registry fixes it
  $('evmSetProfile').replaceChildren(...data.profiles.filter(p=>p.provider_id===c.provider_id).map(p=>{const o=element('option',p.title);o.value=p.profile_id;return o}));
  $('evmSetProfile').value=d.profile_id;
  const key=provider?.credential;
  facts('evmSetConnFacts',[['Тип доступа API',provider?.scope?.label],['Авторизация',provider?.auth],['Адрес OAuth',provider?.oauth_url],['Адрес API',provider?.api_url],
    ['Ключ авторизации',key?.present?'Задан ('+key.source+'). Значение в браузер не передаётся':'Не задан'+(key?.source?' ('+key.source+')':'')],
    ['Адаптер',provider?.adapter_state==='AVAILABLE'?'Есть: '+provider.adapter:'Адаптер пока отсутствует'],['Версия настроек подключения',c.settings_version]]);
  text('evmSetProviders','Справочник провайдеров: '+data.providers.map(p=>p.display_name+' — '+(p.adapter_state==='AVAILABLE'?'адаптер есть':'адаптера нет')).join('; ')+'. Запись в справочнике не означает поддержку API.');
  facts('evmSetModelFacts',[['Название в реестре',c.display_name],['Модель провайдера',c.provider_model_id],['Идентификатор',c.model_id],['Подключение',c.connection_id]]);
  $('evmSetParams').value=d.params;$('evmSetDescription').value=d.description;
  for(const [k,id] of PROFILE_FIELDS)$(id).value=d.profile[k];
  settingsHints(d);selectTab(evm.tab);
  $('evmSetDraft').hidden=!evm.drafts[c.model_id];notice('evmSetError',evm.setError);
  $('evmSetSave').disabled=evm.saving
}
function settingsHints(d){
  text('evmSetDescCount',d.description.length+' / '+evm.cards.limits.description);
  text('evmSetParamsSource',d.params.trim()===''?'Неизвестно — не указано':'Указано пользователем (справочник моделей — позже)')
}
function editDraft(){
  const c=evm.window?.kind==='settings'?cardData(evm.window.id):null;if(!c)return;
  const d=evm.drafts[c.model_id]||initialDraft(c),profileChanged=$('evmSetProfile').value!==d.profile_id;
  d.profile_id=$('evmSetProfile').value;
  d.profile=profileChanged?profileValues(d.profile_id):Object.fromEntries(PROFILE_FIELDS.map(([k,id])=>[k,$(id).value]));  // another profile brings its own values
  d.params=$('evmSetParams').value;d.description=$('evmSetDescription').value;
  evm.drafts[c.model_id]=d;
  if(profileChanged)fillSettings();else{settingsHints(d);$('evmSetDraft').hidden=false}
}
function settingsBody(d){
  const raw=String(d.params).trim().replace(',','.'),params=raw===''?null:Number(raw);
  if(params!==null&&!(Number.isFinite(params)&&params>0))throw new Error('Количество параметров — положительное число или пустое поле.');
  if(d.description.length>evm.cards.limits.description)throw new Error('Описание длиннее '+evm.cards.limits.description+' символов.');
  const profile={};
  for(const [k] of PROFILE_FIELDS){const v=Number(d.profile[k]);if(String(d.profile[k]).trim()===''||!Number.isInteger(v))throw new Error('Раздел «Дополнительно»: нужно целое число.');profile[k]=v}
  return {base_revision:d.base_revision,description:d.description,params_billion:params,profile_id:d.profile_id,profile}
}
async function saveSettings(){
  const c=evm.window?.kind==='settings'?cardData(evm.window.id):null;if(!c||evm.saving)return;
  let body;
  try{body=settingsBody(evm.drafts[c.model_id]||initialDraft(c))}catch(e){evm.setError=e.message;notice('evmSetError',e.message);return}
  evm.saving=true;evm.setError='';notice('evmSetError','');$('evmSetSave').disabled=true;
  try{
    const r=await api('/ultra/model-cards/'+encodeURIComponent(c.model_id)+'/settings',{method:'POST',body});
    if(r?.card?.model_id!==c.model_id)throw new Error('Сервер не подтвердил сохранение');
    delete evm.drafts[c.model_id];evm.saving=false;
    await loadEvm();
    notice('evmNotice','Настройки сохранены: '+c.display_name)
  }catch(e){
    evm.saving=false;
    evm.setError=(e.code==='settings_revision_conflict'?'Настройки уже изменены в другом окне. «Отменить изменения» загрузит сохранённые; затем повторите правку. ':'Настройки не сохранены. ')+e.message;
    if(evm.window?.kind==='settings'){notice('evmSetError',evm.setError);$('evmSetSave').disabled=false}
  }
}
function fillCheck(){
  const c=cardData(evm.window.id),live=evm.cards.live_check;
  text('evmCheckName','Проверка API — '+c.display_name);$('evmCheckDot').replaceChildren(apiDot(c.api));
  text('evmCheckLast','Последний успешный ответ: '+(c.api.last_success_at?fmtTime(c.api.last_success_at)+(c.api.last_success_source==='chat'?' (обычный запрос)':''):'отсутствует')+' · '+apiText(c.api));
  const out=evm.outputs[c.model_id]||(c.last_output?{kind:c.last_output.kind==='reply'?'reply':'error',text:c.last_output.text+'\n('+fmtTime(c.last_output.at)+')'}:
    {kind:'info',text:'Нажмите «Отправить тестовое сообщение», чтобы проверить подключение и увидеть ответ модели.'});
  text('evmCheckOutput',out.text);$('evmCheckOutput').className='output '+out.kind;
  text('evmCheckNote','Тестовое сообщение: «'+evm.cards.test_message+'»'+(live.authorized?'':' — в этой версии оно не отправляется.'));
  $('evmCheckSend').disabled=evm.checking
}
function checkOutput(r){
  if(r?.outcome==='LIVE_CHECK_NOT_AUTHORIZED')return {kind:'info',text:'Сообщение не отправлялось. '+r.message+' Статус API не изменён.'};
  if(r?.outcome==='SIMULATED')return {kind:'info',text:'ИМИТАЦИЯ — настоящий запрос не отправлялся, статус API не изменён.\n'+(r.text||'')};
  if(r?.outcome==='CONFIRMED')return {kind:'reply',text:String(r.text||'')};
  if(r?.outcome==='FAILED')return {kind:'error',text:String(r.text||'Проверка завершилась отказом')};
  return {kind:'error',text:'Некорректный ответ сервера о проверке.'}
}
async function sendCheck(){
  const c=evm.window?.kind==='check'?cardData(evm.window.id):null;if(!c||evm.checking)return;
  const id=c.model_id;evm.checking=true;evm.outputs[id]={kind:'info',text:'Проверяем…'};fillCheck();
  try{evm.outputs[id]=checkOutput(await api('/ultra/model-cards/'+encodeURIComponent(id)+'/check',{method:'POST',body:{},timeoutMs:130000}))}
  catch(e){evm.outputs[id]={kind:'error',text:'Проверка не выполнена: '+e.message}}
  evm.checking=false;
  await loadEvm()  // the indicator always comes from the server, never from this answer
}
$('viewEvm').onclick=()=>showView('evm');
$('viewOperator').onclick=()=>showView('operator');
$('evmRefresh').onclick=()=>loadEvm();
$('evmChatModel').onchange=()=>{evm.chatTouched=true};
$('evmChatSave').onclick=()=>{const id=$('evmChatModel').value;if(!id){notice('evmError','Выберите модель для чата.');return}selectConnection(id)};
for(const [key,[tab]] of Object.entries(EVM_TABS))$(tab).onclick=()=>selectTab(key);
$('evmSetProfile').onchange=editDraft;
for(const id of ['evmSetParams','evmSetDescription','evmSetTimeout','evmSetDiagLimit','evmSetFreshness'])$(id).oninput=editDraft;
$('evmSetReset').onclick=()=>{const w=evm.window;if(w?.kind!=='settings')return;delete evm.drafts[w.id];evm.setError='';fillSettings()};
$('evmSetSave').onclick=()=>saveSettings();
$('evmSetClose').onclick=()=>closeWindow();
$('evmCheckClose').onclick=()=>closeWindow();
$('evmCheckSend').onclick=()=>sendCheck();
for(const id of ['evmSettingsWindow','evmCheckWindow'])$(id).onclick=e=>{if(e?.target===$(id))closeWindow()};
if(typeof window!=='undefined'&&window.addEventListener)window.addEventListener('keydown',e=>{if(e.key==='Escape'&&evm.window)closeWindow()});
// Ultra Chat (programme No.37 stage 1): saved dialogues of the shared Ultra core, read-only. The read token
// lives only in this object and goes only to /ultra/chat/* in its own header; nothing here writes anything.
const CHAT_TOKEN_HEADER='X-WebAlarm-Ultra-Chat-Token',CHAT_PAGE=50;
const chat={epoch:0,started:false,token:null,workspaces:[],workspace:null,chats:[],chat:null,messages:[],page:null,olderBusy:false};
const CHAT_REASON={missing_history:'В папке нет истории Ultra',missing_path:'Папка недоступна',not_directory:'Путь не является папкой',invalid_metadata:'Данные Ultra повреждены',unsupported_version:'Данные Ultra более новой версии',unsafe_storage_link:'Внутри хранилища Ultra ссылка вместо папки или файла — чтение запрещено',unreadable:'Данные не читаются',unsupported_registration_id:'Эта регистрация не поддерживается Ultra Chat',registry_unavailable:'Реестр Workspace недоступен',too_many_workspaces:'Слишком много Workspace',chats_listing_too_large:'Слишком много диалогов для просмотра',history_too_large:'История слишком большая для просмотра',foreign_identity:'Диалог принадлежит другому Workspace',chat_damaged:'Диалог повреждён',ultra_core_unavailable:'Общее ядро Ultra недоступно'};
const CHAT_OUTCOME={failed:['Ошибка выполнения (старая запись), не ответ модели','bad'],no_answer:['Ответ не сохранён','warn'],interrupted:['Прервано · исход неизвестен','unknown'],unknown:['Исход неизвестен','unknown']};
function chatReason(code){return CHAT_REASON[code]||'Недоступно ('+String(code)+')'}
function chatTime(value){return typeof value==='string'?value.replace('T',' ').slice(0,19):''}
function chatCount(map){return Object.values(map||{}).reduce((sum,n)=>sum+(Number(n)||0),0)}
async function loadChatAccess(){
  const c=(await api('/ui/ultra-chat/capability'))?.ultra_chat;
  if(!c||typeof c.available!=='boolean'||c.header!==CHAT_TOKEN_HEADER)throw Error('Некорректный ответ сервера о доступе к истории');
  chat.token=c.available&&typeof c.token==='string'&&c.token.length>=32?c.token:null;
  if(!chat.token)throw Object.assign(Error(c.reason==='disabled'?'Чтение истории Ultra Chat выключено при запуске сервера.':
    c.reason==='non_loopback_bind'?'Чтение истории Ultra Chat недоступно: сервер запущен не на локальном адресе.':'Чтение истории Ultra Chat недоступно в этом режиме сервера.'),{chatUnavailable:true});
}
async function chatGet(path){
  if(!chat.token)await loadChatAccess();
  try{return await api(path,{headers:{[CHAT_TOKEN_HEADER]:chat.token}})}
  catch(e){
    if(e.code!=='ultra_chat_token_invalid')throw e;
    chat.token=null;await loadChatAccess();// the server was restarted: one new capability, one repeat
    try{return await api(path,{headers:{[CHAT_TOKEN_HEADER]:chat.token}})}
    catch(again){if(again.code==='ultra_chat_token_invalid'){chat.token=null;throw Error('Доступ к истории недействителен — обновите страницу.')}throw again}
  }
}
function chatFailure(e){
  if(e.chatUnavailable){text('chatAccess',e.message);notice('chatError','');chat.workspaces=[];chat.chats=[];renderChatWorkspaces();renderChatList();text('chatWorkspaceState','');text('chatListState','');return}
  notice('chatError',e.message)
}
function chatPick(label,detail,current,onclick){
  const b=element('button',null,'chat-pick');b.type='button';b.setAttribute('aria-current',String(current));
  b.append(element('strong',label));if(detail)b.append(element('small',detail,'muted'));b.onclick=onclick;return b
}
function renderChatWorkspaces(){
  $('chatWorkspaceList').replaceChildren(...chat.workspaces.map(w=>chatPick(w.display_name,w.history==='ok'?'История Ultra найдена':chatReason(w.history),
    w.wa_workspace_id===chat.workspace,()=>selectChatWorkspace(w.wa_workspace_id))))
}
function renderChatList(){
  $('chatList').replaceChildren(...chat.chats.map(c=>{
    const ok=c.status==='ok';
    const b=chatPick(ok?c.title:c.status==='unsafe_storage_link'?'Ссылка вместо диалога — не читается':'Диалог повреждён',
      ok?(c.created_at?'Создан '+chatTime(c.created_at):''):'ID '+c.chat_id,c.chat_id===chat.chat,()=>selectChat(c.chat_id));
    b.setAttribute('data-status',c.status);if(!ok)b.disabled=true;return b
  }))
}
function chatNotices(list){
  $('chatNotice').className='notice'+(list[0]?.[0]==='error'?' error':list[0]?.[0]==='info'?' info':'');
  notice('chatNotice',list.map(item=>item[1]).join('\n'))
}
function clearChatHistory(title){text('chatTitle',title);chatNotices([]);$('chatHistory').replaceChildren();$('chatOlder').hidden=true}
function chatMessage(m){
  const li=element('li',null,'msg'),failed=m.outcome==='failed',meta=element('div',null,'msg-meta');
  li.setAttribute('data-role',m.role);li.setAttribute('data-outcome',m.outcome);li.setAttribute('data-message',m.message_id);
  meta.append(element('strong',m.role==='user'?'Вы':m.role==='assistant'?(failed?'Ошибка выполнения':'Ultra'):m.role==='system'?'Система':'Инструмент'));
  if(m.created_at)meta.append(element('span',chatTime(m.created_at)));
  if(m.model&&!failed)meta.append(element('span',m.model,'tag'));
  const outcome=CHAT_OUTCOME[m.outcome];if(outcome)meta.append(element('span',outcome[0],'tag '+outcome[1]));
  li.append(meta,m.too_large_for_page?element('p','Сообщение слишком большое для одной страницы ('+m.size_bytes+' байт) и не показано.','muted'):element('div',m.text,'msg-text'));
  return li
}
function validChatWorkspaces(d){return Boolean(d&&['ok','unavailable','too_large'].includes(d.state)&&Array.isArray(d.workspaces)&&d.workspaces.every(w=>w&&typeof w.wa_workspace_id==='string'&&typeof w.display_name==='string'&&typeof w.history==='string'))}
function validChatList(d){return Boolean(d&&['ok','unavailable','too_large'].includes(d.state)&&Array.isArray(d.chats)&&d.chats.every(c=>c&&typeof c.chat_id==='string'&&typeof c.status==='string'&&(c.status!=='ok'||typeof c.title==='string')))}
function validChatHistory(d){
  return Boolean(d&&['complete','partial','empty','too_large','unavailable'].includes(d.history_state)&&Array.isArray(d.messages)&&d.page&&typeof d.page.has_more==='boolean'&&
    d.messages.every(m=>m&&typeof m.message_id==='string'&&['user','assistant','system','tool'].includes(m.role)&&typeof m.outcome==='string'&&(typeof m.text==='string'||m.too_large_for_page===true)))
}
function renderChatHistory(data,older=false){
  text('chatTitle',data.chat?.title||chat.chats.find(c=>c.chat_id===chat.chat)?.title||'Диалог');
  const notes=[];
  if(data.history_state==='unavailable')notes.push(['error','История недоступна: '+chatReason(data.reason)+'.']);
  else if(data.history_state==='too_large')notes.push(['error',chatReason('history_too_large')+'. История не показана и не обрезана.']);
  else if(data.history_state==='partial')notes.push(['warning','Показана не вся история: не показано записей — '+chatCount(data.excluded)+' (повреждены, принадлежат другому диалогу или недоступны).']);
  else if(data.history_state==='empty')notes.push(['info','В этом диалоге нет сообщений.']);
  if(data.outcome_source==='run_index_unavailable')notes.push(['info','Журнал запусков недоступен: исход старых ответов определён только по их тексту.']);
  chatNotices(notes);
  const box=$('chatHistory'),fromBottom=older?(box.scrollHeight||0)-(box.scrollTop||0):0;
  box.replaceChildren(...chat.messages.map(chatMessage));
  $('chatOlder').hidden=!chat.page?.has_more;
  box.scrollTop=(box.scrollHeight||0)-fromBottom// a dialogue opens at its newest message; an older page keeps the place
}
async function loadChatModel(){
  try{
    const s=(await api('/ultra/connections/selection?role=chat'))?.selection;
    if(!s||typeof s.state!=='string')throw Error('selection');
    text('chatModel',s.state==='SAVED'&&typeof s.display_name==='string'?'Модель: '+s.display_name:s.state==='NOT_SELECTED'?'Модель не выбрана — откройте EVM':
      s.state==='CORRUPT'?'Выбор модели повреждён — откройте EVM':s.state==='INVALID_REFERENCE'?'Выбранная модель недоступна — откройте EVM':
      s.state==='REGISTRY_UNAVAILABLE'?'Реестр моделей недоступен':'Модель: неизвестное состояние '+s.state);
    $('chatModel').className='tag '+(s.state==='SAVED'?'active':'warn')
  }catch(_){text('chatModel','Модель: нет данных EVM');$('chatModel').className='tag warn'}
}
async function loadChatWorkspaces(){
  const epoch=chat.epoch;text('chatWorkspaceState','Загружаем Workspace…');notice('chatError','');
  try{
    const data=await chatGet('/ultra/chat/workspaces');
    if(epoch!==chat.epoch)return;
    if(!validChatWorkspaces(data))throw Error('Некорректный ответ сервера о Workspace');
    text('chatAccess','Только чтение · данные проверяет сервер');chat.workspaces=data.workspaces;
    text('chatWorkspaceState',data.state!=='ok'?chatReason(data.reason):data.workspaces.length?'':'Нет зарегистрированных Workspace. Добавьте папку в операторской панели.');
    if(chat.workspace&&!chat.workspaces.some(w=>w.wa_workspace_id===chat.workspace)){chat.workspace=null;chat.chat=null;chat.chats=[];renderChatList();clearChatHistory('Выберите диалог')}
    renderChatWorkspaces();
    if(chat.workspace)return loadChatList();
    const first=chat.workspaces.find(w=>w.history==='ok');
    if(first)return selectChatWorkspace(first.wa_workspace_id)
  }catch(e){if(epoch===chat.epoch){text('chatWorkspaceState','Список Workspace не загружен');chatFailure(e)}}
}
function selectChatWorkspace(id){
  chat.epoch++;chat.workspace=id;chat.chat=null;chat.chats=[];chat.messages=[];chat.page=null;chat.olderBusy=false;
  const w=chat.workspaces.find(item=>item.wa_workspace_id===id);text('chatWorkspaceName',w?w.display_name:'Ultra Chat');
  renderChatWorkspaces();renderChatList();clearChatHistory('Выберите диалог');
  return loadChatList()
}
async function loadChatList(){
  if(!chat.workspace)return;
  const epoch=chat.epoch;text('chatListState','Загружаем диалоги…');
  try{
    const data=await chatGet('/ultra/chat/workspaces/'+encodeURIComponent(chat.workspace)+'/chats');
    if(epoch!==chat.epoch)return;
    if(!validChatList(data))throw Error('Некорректный ответ сервера о диалогах');
    notice('chatError','');chat.chats=data.chats;const hidden=chatCount(data.excluded);
    text('chatListState',data.state!=='ok'?chatReason(data.reason):(data.chats.length?'Диалогов: '+data.chats.length:'В этом Workspace нет сохранённых диалогов.')+(hidden?' · не показано посторонних записей: '+hidden:''));
    if(chat.chat&&!chat.chats.some(c=>c.chat_id===chat.chat&&c.status==='ok')){chat.chat=null;clearChatHistory('Выберите диалог')}
    renderChatList();
    if(chat.chat)return loadChatHistory(false);
    const newest=chat.chats.filter(c=>c.status==='ok').at(-1);// the list is in creation order: open the newest dialogue
    if(newest)return selectChat(newest.chat_id)
  }catch(e){if(epoch===chat.epoch){text('chatListState','Список диалогов не загружен');chatFailure(e)}}
}
function selectChat(id){
  chat.epoch++;chat.chat=id;chat.messages=[];chat.page=null;chat.olderBusy=false;
  renderChatList();clearChatHistory('Загружаем историю…');return loadChatHistory(false)
}
async function loadChatHistory(older){
  if(!chat.workspace||!chat.chat||(older&&(chat.olderBusy||!chat.page?.next_before)))return;
  const epoch=chat.epoch;
  let path='/ultra/chat/workspaces/'+encodeURIComponent(chat.workspace)+'/chats/'+encodeURIComponent(chat.chat)+'/messages?limit='+CHAT_PAGE;
  if(older){path+='&before='+encodeURIComponent(chat.page.next_before);chat.olderBusy=true;$('chatOlder').disabled=true}
  try{
    const data=await chatGet(path);
    if(epoch!==chat.epoch)return;
    if(!validChatHistory(data))throw Error('Некорректный ответ сервера об истории диалога');
    notice('chatError','');chat.messages=older?[...data.messages,...chat.messages]:data.messages;chat.page=data.page;
    renderChatHistory(data,older)
  }catch(e){if(epoch===chat.epoch)chatFailure(e)}
  finally{if(older&&epoch===chat.epoch){chat.olderBusy=false;$('chatOlder').disabled=false}}
}
function startChat(){if(chat.started)return;chat.started=true;loadChatModel();return loadChatWorkspaces()}
$('viewChat').onclick=()=>showView('chat');
$('chatRefresh').onclick=()=>{loadChatModel();return loadChatWorkspaces()};
$('chatOlder').onclick=()=>loadChatHistory(true);
$('chatComposer').onsubmit=e=>e.preventDefault();
try{
  const saved=JSON.parse(localStorage.getItem('webAlarm.selection')||'{}');
  if(typeof saved.workspace==='string')view.workspace=saved.workspace;
  if(typeof saved.task==='string')view.task=saved.task;view.restoredDraft=saved.draft===true
}
catch(_){
}
setInterval(()=>{
  if($('autoRefresh').checked&&!document.hidden&&!view.creating)refresh();
  if(view.healthAt&&Date.now()-view.healthAt>45000){text('serverStatus','Проверка связи устарела');$('serverStatus').setAttribute('data-state','checking')}
  if(view.loadedAt&&Date.now()-view.loadedAt>45000&&view.fresh)setFresh(false,'Снимок старше 45 секунд. Обновите перед использованием NEXT SAFE ACTION.')
}
,15000);
showView(initialView(),true);
refresh();
</script>
</body></html>
'''
