"""WA4-O operator panel; all execution facts come from server read models."""

INDEX_HTML = r'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta id="waUiVersion" name="web-alarm-ui-version" content="__WA_UI_VERSION__">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Web Alarm Ultra</title>
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

/* Ultra Chat: Workspace -> nested chats. All controls remain visible and keyboard accessible. */
.chat-workspace-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:16px 0 8px}
.chat-workspace-heading button{font-size:12px;padding:7px 9px;white-space:normal;text-align:center}
.chat-workspace-group{border:1px solid var(--line);border-radius:10px;margin-bottom:8px;overflow:hidden}
.chat-workspace-group[data-active=true]{border-color:var(--blue);background:#152637}
.chat-workspace-row,.chat-dialog-row{display:flex;align-items:stretch;gap:3px;padding:3px}
.chat-workspace-row .chat-pick,.chat-dialog-row .chat-pick{flex:1;min-width:0;margin:0;text-align:left}
.chat-workspace-row .chat-pick{border:0;background:transparent}
.chat-workspace-row .chat-pick[aria-expanded=true]{font-weight:700}
.chat-workspace-row .chat-pick:before{content:'▸';display:inline-block;margin-right:8px;color:var(--blue)}
.chat-workspace-row .chat-pick[aria-expanded=true]:before{content:'▾'}
.chat-icon-button{flex:none;align-self:center;min-width:30px;height:32px;padding:4px 6px;font-size:16px;line-height:1}
.chat-nested-panel{padding:0 7px 7px 19px}
.chat-dialog-row{padding:2px 0}
.chat-dialog-row .chat-pick{padding:8px}
.chat-nested-actions{display:flex;justify-content:flex-start;gap:6px}
.chat-nested-actions button{font-size:12px}
.chat-nested-panel .chat-name-form{margin-top:9px}
@media(max-width:450px){.chat-nested-panel{padding-left:8px}.chat-workspace-heading button{max-width:158px}}
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
.evm{max-width:2000px;margin:auto;height:calc(100dvh - 73px);overflow:auto;padding:26px 28px 44px;overflow-anchor:none}
.evm-board{overflow-anchor:none;margin-bottom:56px}
.evm-toasts{position:fixed;z-index:25;left:50%;bottom:16px;transform:translateX(-50%);width:min(640px,calc(100vw - 32px));display:grid;gap:8px;pointer-events:none}
.evm-toasts .notice{margin:0;pointer-events:auto;box-shadow:0 12px 32px rgba(0,0,0,.5)}.evm.dragging .evm-toasts{visibility:hidden}
.evm-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
.evm-head h2{font-size:24px;margin:8px 0}
/* EVM board (CLAUDE-WUA-EVM-COMPACT-LAYOUT-001): Favourites | API | MCP / agents | local LLM, compact cards top to bottom. */
.evm-columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:16px;align-items:start}
@media(min-width:1200px){.evm-board{grid-template-columns:minmax(200px,.75fr) minmax(0,1.25fr) minmax(0,1fr) minmax(0,1fr)}}
.evm-col{border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:14px;min-width:0;display:flex;flex-direction:column;gap:10px}
.evm-col .section-head{margin-bottom:2px}
.evm-col h3{font-size:16px}
.evm-list{display:grid;gap:8px;grid-template-columns:minmax(0,1fr);align-content:start;min-height:12px}
.evm-add{border:1px dashed #526579;border-radius:10px;padding:10px;color:var(--muted);text-align:center;font-size:13px}
.evm-info{padding:14px 18px}.evm-info-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px 22px}.evm-info-grid p{margin:4px 0 0}
.ccard{display:flex;flex-direction:column;min-width:0;border:1px solid #3d5a74;border-radius:10px;background:#16212d;transition:border-color .12s ease-out,background .12s ease-out}
.ccard:hover,.ccard.expanded{border-color:#6aa9dc;background:#1a2a39}.ccard.expanded{box-shadow:inset 3px 0 #6aa9dc}
.chead{display:grid;grid-template-columns:auto minmax(0,1fr) auto auto;align-items:center;gap:2px;padding:2px 4px 2px 6px;cursor:pointer;user-select:none;-webkit-user-select:none}
.copen{display:block;min-width:0;padding:6px;background:none;border:0;color:inherit;text-align:left;font:inherit;cursor:inherit}
.copen:hover{background:none}
.ccard .grip{color:#6f8396;cursor:grab;font-size:15px;line-height:1;padding:2px;touch-action:none}
.ccard .cbody{display:grid;gap:2px;min-width:0}
.ccard .ctitle{display:flex;align-items:center;gap:6px;min-width:0;flex-wrap:wrap}
.ccard .cname{font-weight:700;font-size:15px;overflow-wrap:anywhere}
.ccard .csub{font-size:12px;color:var(--muted);overflow-wrap:anywhere}
.ccard .api-dot{width:20px;height:20px;font-size:11px;border-width:1.5px}
.ccard .params{padding:1px 6px;font-size:11px}
.ccard.dragging{opacity:.4}
.cquick{background:none;border:0;padding:2px 5px;font-size:16px;line-height:1;color:#7b8fa3}.cquick:hover{background:none;color:#cfe6ff}.cquick[aria-expanded=true]{color:var(--blue)}
.star{background:none;border:0;padding:2px 6px;font-size:19px;line-height:1;color:#7b8fa3}.star:hover{background:none;color:#ffd28e}.star[aria-pressed=true]{color:#ffd28e}
.cexp{padding:0 8px 8px 10px;cursor:auto;user-select:text;-webkit-user-select:text;container-type:inline-size;min-width:0}.cexp[hidden]{display:none}
.cexp .mcard{border:0;border-top:1px solid #31475c;border-radius:0;box-shadow:none;background:none;padding:10px 0 0;gap:9px}
.cexp .mcard-head{display:none}
@container (max-width:430px){.cexp .roles{gap:6px 10px}.cexp .role{font-size:13px;gap:6px}.cexp .mcard-actions{gap:6px}.cexp .mcard-actions button{padding:7px 9px;font-size:13px}}
.evm.dragging,.evm.dragging *{cursor:grabbing!important;user-select:none!important}
.evm.dragging.drop-none,.evm.dragging.drop-none *{cursor:no-drop!important}
.evm-col.drop-target{border-color:#6aa9dc;background:#182838}
.evm-ghost{position:fixed;z-index:30;left:0;top:0;pointer-events:none;display:grid;gap:2px;padding:8px 12px;border:1px solid #6aa9dc;border-radius:10px;background:#1d3247;box-shadow:0 14px 34px rgba(0,0,0,.55);transform:rotate(-1.5deg)}
.evm-ghost .gname{font-weight:700;overflow-wrap:anywhere}.evm-ghost .ghint{font-size:12px;color:var(--blue)}
.evm-drop-line{position:fixed;z-index:31;height:3px;border-radius:2px;background:var(--blue);box-shadow:0 0 0 2px #10151d;pointer-events:none}
.evm-ghost[hidden],.evm-drop-line[hidden]{display:none}
.evm-peek{position:fixed;z-index:18;left:12px;top:12px;width:min(560px,calc(100vw - 24px));max-height:calc(100dvh - 24px);overflow:auto;border-radius:12px;box-shadow:0 18px 48px rgba(0,0,0,.55);opacity:0;transform:scale(.97);transform-origin:top left;transition:opacity .12s ease-out,transform .12s ease-out}
.evm-peek.open{opacity:1;transform:none}.evm-peek[hidden]{display:none}.evm-peek:focus{outline:none}.evm-peek[data-place=left]{transform-origin:top right}
.peek-bar{display:flex;align-items:center;gap:10px;padding:5px 6px 5px 16px;background:#10202e;border:1px solid #6aa9dc;border-bottom:0;border-radius:12px 12px 0 0;font-size:12px;color:var(--muted)}
.peek-title{font-weight:700;color:var(--text)}.peek-hint{margin-left:auto}.peek-close{padding:2px 10px;font-size:17px;line-height:1.1}
.evm-peek .mcard{border-radius:0 0 12px 12px}
/* Pinned windows (CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001): their own layer over the board, under the preview (18) and the dialogs (20). */
.evm-pins{position:fixed;inset:0;z-index:16;pointer-events:none}
body.evm-external{height:auto;min-height:100dvh;overflow:auto}
body.evm-external .top,body.evm-external .evm-head,body.evm-external .evm-info,body.evm-external .evm-board,body.evm-external .evm-pins,body.evm-external .evm-peek{display:none!important}
body.evm-external .evm{height:auto;min-height:100dvh;padding:12px;overflow:auto}
.evm-external-head{display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:12px}
.evm-external-move{width:100%;font-size:12px;color:var(--muted);margin:0 0 8px}
.evm-external-card .mcard{max-width:none}
.evm-top-frame{width:100%;height:100%;border:0}
.evm-pin{position:absolute;pointer-events:auto;display:flex;flex-direction:column;width:min(460px,calc(100vw - 24px));border:1px solid #4d7fa8;border-radius:12px;background:#16212d;box-shadow:0 14px 40px rgba(0,0,0,.5);overflow:hidden}
.evm-pin[hidden]{display:none}.evm-pin:focus{outline:none}.evm-pin.active{border-color:var(--blue);box-shadow:0 0 0 1px var(--blue),0 18px 48px rgba(0,0,0,.6)}
.evm-pin.flash{animation:pin-flash .7s ease-out}@keyframes pin-flash{0%{box-shadow:0 0 0 5px #ffd28e}100%{box-shadow:0 0 0 1px var(--blue),0 18px 48px rgba(0,0,0,.6)}}
.pin-bar{display:flex;align-items:center;gap:8px;padding:5px 6px 5px 14px;background:#10202e;border-bottom:1px solid #31475c;cursor:move;user-select:none;-webkit-user-select:none;touch-action:none;font-size:13px}
.pin-title{flex:1;min-width:0;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.pin-close{padding:2px 10px;font-size:17px;line-height:1.1;cursor:pointer}
.pin-body{overflow:auto;min-height:0;user-select:text;-webkit-user-select:text}.evm-pin .mcard{border:0;border-radius:0;box-shadow:none}
.evm-pin.moving{opacity:.92}.evm.dragging .evm-pins{opacity:.25}.evm.dragging .evm-pin{pointer-events:none}
.mcard .link{background:none;border:0;padding:0 2px;color:var(--blue);text-decoration:underline;font-size:13px}
.strengths.editable{cursor:text}.strengths.editable:hover{border-color:#6aa9dc}
.chat-model-picker{position:relative;display:inline-flex}
.chat-model-menu{position:absolute;right:0;bottom:calc(100% + 6px);z-index:6;min-width:240px;max-height:300px;overflow:auto;padding:6px;display:grid;gap:4px;background:#17212c;border:1px solid #6aa9dc;border-radius:10px;box-shadow:0 12px 30px rgba(0,0,0,.5)}
.chat-model-menu[hidden]{display:none}.chat-model-menu button{text-align:left}.chat-model-menu button[aria-selected=true]{border-color:var(--blue);background:#213b50}
.chat-model-error{font-size:12px;color:#ffbbbb}
@media(max-width:850px){.chat-model-menu{right:auto;left:0;max-width:calc(100vw - 24px)}}
@media(prefers-reduced-motion:reduce){.evm-peek,.ccard{transition:none}.evm-ghost{transform:none}.evm-pin.flash{animation:none}}
/* EVM model card (CLAUDE-WUA-EVM-MODEL-CARD-UI-001): one component for every model of every provider. */
.mcard{border:1px solid #6aa9dc;background:#16212d;border-radius:12px;padding:16px 18px 14px 20px;display:flex;flex-direction:column;gap:11px;min-width:0;box-shadow:inset 4px 0 #6aa9dc}
.mcard-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.mcard-name{margin:0;font-size:24px;font-weight:700;line-height:1.15;overflow-wrap:anywhere}
.mcard-side{margin-left:auto;font-size:12px;color:var(--muted)}
.api-dot{display:inline-grid;place-items:center;width:28px;height:28px;flex:none;border-radius:50%;border:2px solid;font:800 15px system-ui,Segoe UI,sans-serif;line-height:1}
.api-dot.green{color:#7be3a6;border-color:#3f9e6f;background:#173a2a}
.api-dot.orange{color:#ffc06b;border-color:#c8873a;background:#3d2c16}
.api-dot.red{color:#ff8f98;border-color:#a9505b;background:#3c1e25}
.api-dot.gray{color:#aab8c6;border-color:#6b7d8d;background:#263340}
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
@media(max-width:640px){.form-grid{grid-template-columns:1fr}.mcard{padding:14px 12px 12px 16px}.mcard-name{font-size:21px}.facts-list{grid-template-columns:1fr}.evm-info-grid{grid-template-columns:1fr}}
/* Ultra Chat (programme No.37 stage 1): read-only history of the shared Ultra core; the default view. */
.chat-layout{display:grid;grid-template-columns:300px minmax(0,1fr);max-width:2000px;margin:auto;height:calc(100dvh - 73px);min-height:0}
.chat-side{padding:20px 14px;background:#121c27;border-right:1px solid var(--line);display:flex;flex-direction:column;gap:10px;overflow:auto;min-height:0}
.chat-main{min-width:0;min-height:0;display:flex;flex-direction:column;gap:12px;padding:22px 28px 18px}
.chat-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.chat-head h2{font-size:22px;margin:6px 0 0;overflow-wrap:anywhere}
.chat-picks{display:grid;gap:8px}
.chat-pick{width:100%;text-align:left;display:grid;gap:4px;background:#182431;border-color:#344454;overflow-wrap:anywhere}
.chat-pick[aria-current=true]{background:#213b50;border-color:var(--blue);box-shadow:inset 3px 0 var(--blue)}
.chat-actions{display:flex;gap:8px;flex-wrap:wrap}.chat-name-form{display:grid;gap:6px}.chat-name-form[hidden]{display:none}.chat-name-form label{margin:0}
.chat-history{list-style:none;margin:0;padding:0 4px 0 0;flex:1;min-height:0;overflow:auto;display:flex;flex-direction:column;gap:12px;scrollbar-gutter:stable}
.msg{border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:var(--panel);max-width:880px;width:fit-content;min-width:min(260px,100%);display:grid;gap:8px}
.msg[data-role=user]{align-self:flex-end;background:#1d3044;border-color:#3d5f7d}
.msg[data-outcome=failed]{border-color:#86505b;background:#2c1d23}
.msg-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.msg-text{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}
.chat-composer{border-top:1px solid var(--line);padding-top:10px;display:grid;gap:8px}
.chat-composer label{margin:0}
.chat-composer textarea{min-height:60px;resize:none}
.chat-request-status{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:13px}
.chat-request-status p{margin:0;flex-basis:100%;overflow-wrap:anywhere}
.chat-request-status button{font-size:12px;padding:6px 9px;white-space:normal}
.chat-composer .row{justify-content:space-between;flex-wrap:nowrap}
@media(max-width:1200px){.layout{grid-template-columns:190px minmax(0,1fr) 240px}.columns{grid-template-columns:1fr}main{padding:22px 18px}.overview h2{font-size:24px}}
@media(max-width:850px){body{height:auto;overflow:auto}.top{padding:12px 14px;flex-wrap:wrap;position:sticky}.top-actions{gap:8px}.mobile-toggle{display:inline-block}.layout{display:flex;flex-direction:column;height:auto;min-height:calc(100dvh - 100px)}aside{display:none;border:0;border-bottom:1px solid var(--line);max-height:330px;order:-1}.layout.show-workspaces .workspaces,.layout.show-tasks .tasks{display:flex}main{padding:18px 12px;overflow:visible}.card{padding:16px}.overview-top{flex-wrap:wrap}.overview h2{font-size:23px}.stage summary{flex-wrap:wrap}.stage-body{padding-left:16px}.operation-grid{grid-template-columns:90px minmax(0,1fr)}.composer textarea{min-height:280px}.connection{max-width:220px}.brand .live{display:none}.top-nav{order:3;width:100%;justify-content:flex-start}.evm{height:auto;padding:18px 12px;overflow:visible}.evm-columns{grid-template-columns:1fr}}
@media(max-width:850px){.chat-layout{display:flex;flex-direction:column;height:auto}.chat-side{border-right:0;border-bottom:1px solid var(--line);overflow:visible;max-height:none}.chat-main{padding:16px 12px}.chat-history{overflow:visible}.chat-composer .row{flex-wrap:wrap}}

/* Ultra Chat: Colibri visual language; deliberately scoped to chat, not the other workspaces. */
#chatView{--chat-bg:#0c1017;--chat-panel:#151b25;--chat-card:#1c2634;--chat-accent:#8f8cff;--chat-line:#303d50;--chat-muted:#91a0b2;background:var(--chat-bg)}
#chatView .chat-side{background:var(--chat-bg);padding:16px 12px;border-color:#283140}
#chatView .chat-main{background:var(--chat-panel);padding:16px 20px 12px;gap:9px}
#chatView .chat-pick{background:var(--chat-card);border-color:var(--chat-line);border-radius:10px;color:#ccd8e6;padding:9px 10px;font-size:13px}
#chatView .chat-pick:hover{background:#253248}
#chatView .chat-pick[aria-current=true]{background:#282640;border-color:#8f8aff;box-shadow:none}
#chatView .chat-workspace-group{border-color:#303d50;background:#151b25}
#chatView .chat-workspace-group[data-active=true]{border-color:#8f8aff;background:#19212d}
#chatView .chat-workspace-row .chat-pick{background:transparent}
#chatView .chat-workspace-row .chat-pick:before{color:#8f8cff}
#chatView .chat-personal-heading button,#chatView #chatRegisterWorkspace{background:#817cf2;color:#fff;border-color:#9b98ff;font-size:12px;padding:6px 9px}
#chatView .chat-icon-button{background:transparent;border-color:transparent;color:#a7b7cb}
#chatView .chat-icon-button:hover{background:#253248;border-color:#526584}
#chatView .chat-side .compact-heading{display:grid;grid-template-columns:minmax(0,1fr) 24px;grid-template-rows:24px 16px;align-items:center;column-gap:5px;row-gap:2px;margin-bottom:4px}
#chatView .chat-side .compact-heading .side-title{margin:0;min-width:0}
#chatView .compact-heading button{flex:none;min-height:24px;padding:3px 6px}
#chatView .compact-heading .side-title{grid-column:1;grid-row:1}
#chatView .compact-heading #chatPersonalNew,#chatView .compact-heading #chatRegisterWorkspace{grid-column:2;grid-row:1}
#chatView .compact-heading .compact-section-toggle{grid-column:1/-1;grid-row:2}
#chatView .compact-heading .compact-section-toggle,#chatView .compact-workspace .compact-card-toggle{display:flex;align-items:center;justify-content:center;width:100%;min-width:0;height:16px;min-height:16px;box-sizing:border-box;padding:0;border:0;border-radius:3px;background:transparent;color:#8398af;font-size:0;cursor:pointer;gap:5px}
#chatView .compact-heading .compact-section-toggle::before,#chatView .compact-heading .compact-section-toggle::after,#chatView .compact-workspace .compact-card-toggle::before,#chatView .compact-workspace .compact-card-toggle::after{content:'';height:1px;flex:1;background:#303d50}
#chatView .compact-disclosure-glyph{display:block;width:7px;height:7px;box-sizing:border-box;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:translateY(-2px) rotate(45deg)}
#chatView [aria-expanded=true]>.compact-disclosure-glyph{transform:translateY(2px) rotate(225deg)}
#chatView .compact-heading .compact-section-toggle:hover,#chatView .compact-workspace .compact-card-toggle:hover{color:#c6c4ff;background:#202b3b}
#chatView .compact-heading .compact-section-toggle:focus:not(:focus-visible),#chatView .compact-workspace .compact-card-toggle:focus:not(:focus-visible){outline:none}
#chatView .compact-heading .compact-section-toggle:focus-visible,#chatView .compact-workspace .compact-card-toggle:focus-visible{outline:1px solid #8f8cff;outline-offset:1px}
#chatView .compact-content[hidden]{display:none!important}
#chatView .compact-workspace .compact-card-toggle{margin-top:3px}

#chatView .compact-heading #chatPersonalNew,#chatView .compact-heading #chatRegisterWorkspace{width:24px;height:24px;min-width:24px;min-height:24px;padding:0;border-radius:5px;font-size:16px;line-height:1}
#chatView #chatPersonalList[hidden],#chatView #chatWorkspaceList[hidden],#chatView #chatWorkspaceState[hidden]{display:none!important}
#chatView .compact-inline-name{min-width:0;flex:1;width:0;height:28px;box-sizing:border-box;margin:0;padding:5px 4px;border:1px solid #817cf2;border-radius:5px;background:#111824;color:#f0f4fa;font:inherit;font-size:12px;line-height:1.35;outline:none}
#chatView .compact-workspace .chat-workspace-row .compact-inline-name{height:24px;font-size:10px;font-weight:700}
#chatView .compact-inline-name:focus{border-color:#a5a2ff;outline:none}
#chatView .compact-dialog .chat-pick{height:28px;box-sizing:border-box}
#chatView .compact-workspace .chat-workspace-row .chat-pick{height:24px;box-sizing:border-box}


#chatView .compact-workspace{width:100%;min-width:0;max-width:100%;box-sizing:border-box;padding:7px}
#chatView .compact-workspace .chat-workspace-row,#chatView .compact-dialog{display:flex;gap:2px;min-width:0;align-items:center;padding:0}
#chatView .compact-workspace .chat-workspace-row .chat-pick:before{display:none;content:none}
#chatView .compact-workspace .chat-workspace-row .chat-pick{color:#92acc6;text-transform:uppercase;letter-spacing:.04em;font-size:10px;font-weight:700}
#chatView .compact-dialog .chat-pick,#chatView .compact-workspace .chat-workspace-row .chat-pick{min-width:0;flex:1;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:5px 4px;border:1px solid transparent;background:transparent;border-radius:5px;text-align:left;font-size:12px;line-height:1.35}
#chatView .compact-workspace .chat-workspace-row .chat-pick{font-size:10px}
#chatView .compact-dialog .chat-pick[aria-current=true]{background:#29283f;color:#f3f2ff;border-color:transparent}
#chatView .compact-dialog .chat-pick:hover,#chatView .compact-workspace .chat-workspace-row .chat-pick:hover{background:#253248}
#chatView .compact-dialog .chat-pick strong,#chatView .compact-workspace .chat-pick strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
#chatView .compact-workspace .chat-workspace-row .chat-pick strong{font-weight:700}
#chatView .compact-dialog .chat-icon-button,#chatView .compact-workspace .chat-icon-button{min-width:23px;width:23px;height:24px;min-height:24px;flex:none;font-size:12px;padding:2px;border-radius:5px}
#chatView .compact-workspace .chat-icon-button.compact-plus{color:#fff;background:#817cf2;border-color:#9b98ff}
#chatView .compact-folder{display:flex;align-items:center;gap:3px;margin:3px 0 5px;min-width:0}
#chatView .compact-folder small{display:block;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:10px;color:#91a0b2}
#chatView .compact-content{border-top:1px solid #303d50;min-width:0;padding-top:4px}
#chatView .compact-content:not(:has(.compact-dialog)):not(:has(.chat-name-form:not([hidden]))){border:0;padding:0}
#chatView .compact-content .chat-picks{gap:1px;min-width:0}
#chatView .compact-personal-list{gap:1px}
#chatView .compact-dialog .chat-icon-button:not(:disabled):hover{color:#fff}
#chatView .compact-icon{font-size:0!important;position:relative}
#chatView .compact-icon:after{content:'';display:block;width:14px;height:14px;margin:auto;background:currentColor;mask:var(--compact-icon) center/contain no-repeat}
#chatView .compact-edit{--compact-icon:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m4 20 4-1 12-12-4-4L4 15zM14 5l4 4'/%3E%3C/svg%3E")}
#chatView .compact-trash{--compact-icon:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6'/%3E%3C/svg%3E")}
#chatView .compact-folder-icon{--compact-icon:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 19V5h6l2 3h10v11zM3 19l4-8h15l-4 8z'/%3E%3C/svg%3E")}
#chatView .compact-workspace .chat-name-form{margin:5px 0;min-width:0}
#chatView .compact-workspace .chat-name-form input{width:100%;min-width:0}
#chatView .compact-workspace .chat-name-form button{font-size:11px;padding:3px 5px}
#chatView .compact-personal-list .chat-name-form{margin:5px 0}

#chatView .muted{color:var(--chat-muted)}
#chatView .msg{background:#222d3d;color:#e5edf6;border-color:transparent;border-radius:14px;padding:14px 17px;max-width:min(88%,880px);min-width:min(220px,100%);font-size:13px;flex:none}
#chatView .msg[data-role=user]{background:#373565;color:#f4f1ff;border-color:transparent}
#chatView .msg[data-outcome=failed]{background:#2c1d23;border-color:#86505b}
#chatView .msg-meta{color:#a7b7cb;font-size:11px}
#chatView .msg-text{line-height:1.65}
#chatView .msg-footer{display:flex;align-items:center;gap:8px;min-height:25px;flex-wrap:wrap;color:#a7b7cb;font-size:11px}
#chatView .msg-copy{position:relative;width:26px;height:26px;padding:0;background:transparent;border:1px solid transparent;color:#a7b7cb;font-size:0}
#chatView .msg-copy:before,#chatView .msg-copy:after{content:'';position:absolute;width:9px;height:9px;border:1px solid currentColor;border-radius:2px}
#chatView .msg-copy:before{top:6px;left:6px}
#chatView .msg-copy:after{top:9px;left:9px;background:#222d3d}
#chatView .msg[data-role=user] .msg-copy:after{background:#373565}
#chatView .msg-copy:hover{border-color:#526584;color:#eef3fa}
#chatView .msg-metrics{color:#d7bd89;font-size:11px;line-height:1.4;overflow-wrap:anywhere}
#chatView .chat-composer{background:#151b25;border:1px solid #303d50;border-radius:13px;padding:9px 12px 12px;gap:5px;flex:none}
#chatView .chat-composer .row{align-items:center;flex-wrap:wrap;gap:5px}
#chatView .chat-composer .row label{font-size:12px;color:#a7b7cb}
#chatView .composer-actions{margin-left:auto;min-width:0;flex-wrap:wrap;justify-content:flex-end}
#chatView #chatModelPick{background:#172332;border-color:#526584;padding:5px 9px;font-size:12px;max-width:100%;overflow-wrap:anywhere}
#chatView .chat-model-menu{background:#151b25;border-color:#526584}
#chatView .chat-model-menu button[aria-selected=true]{background:#282640;border-color:#8f8aff}
#chatView #chatComposerNote{margin:0;font-size:11px;overflow-wrap:anywhere}
#chatView .chat-resize{display:block;position:relative;width:100%;height:12px;min-height:12px;border:0;padding:0;background:transparent;cursor:ns-resize;touch-action:none}
#chatView .chat-resize:after{content:'';position:absolute;left:calc(50% - 15px);top:4px;width:30px;height:3px;border-radius:3px;background:#a7b7cb}
#chatView .chat-resize:hover:after,#chatView .chat-resize:focus-visible:after{background:#8f8cff}
#chatView .chat-input-wrap{position:relative;min-width:0}
#chatView #chatInput{display:block;width:100%;height:140px;min-height:72px;max-height:min(42dvh,420px);resize:none;padding:12px 43px 36px 12px;background:#111824;border:1px solid #404d63;border-radius:10px;color:#f0f4fa;font-size:13px;line-height:1.55}
#chatView #chatInput:focus{outline:2px solid #7675c9;outline-offset:1px}
#chatView #chatSend{position:absolute;right:8px;bottom:8px;padding:5px 8px;border-radius:7px;background:#373565;border-color:#7675c9;min-height:29px;color:#f4f1ff;font-size:12px}
#chatView #chatSend[data-recover=false]{font-size:0;width:30px;padding:0}
#chatView #chatSend[data-recover=false]:after{content:'↵';font-size:19px;line-height:1.1}
#chatView #chatSend:hover:not(:disabled){background:#514e89}
#chatView #chatMic{font-size:13px;padding:4px 6px}
@media(min-width:1250px){
 body:has(#chatView:not([hidden])) .top{background:#121720;padding-left:16px}
 body:has(#chatView:not([hidden])) .top-nav{position:fixed;left:0;top:73px;bottom:0;width:174px;padding:18px 12px;background:#121720;border-right:1px solid #283140;flex-direction:column;flex-wrap:nowrap;justify-content:flex-start;align-items:stretch;overflow:auto}
 body:has(#chatView:not([hidden])) .top-nav button{white-space:normal;text-align:left;padding:10px;background:transparent;border-color:transparent;font-size:13px}
 body:has(#chatView:not([hidden])) .top-nav button[aria-pressed=true]{background:#29273f;border-color:transparent;box-shadow:inset 3px 0 #8986ff;color:#d8d6ff}
 body:has(#chatView:not([hidden])) .brand .logo{background:#817cf2;border-color:#9b98ff;color:#fff}
 #chatView{margin-left:174px}
 #chatView .chat-layout{grid-template-columns:248px minmax(0,1fr)}
}
@media(max-width:850px){#chatView .chat-main{padding:12px 10px}#chatView .msg{max-width:95%}}

</style>
</head>
<body>
<a class="skip" id="skipLink" href="#chatMain">К истории диалога</a>
<header class="top">
<div class="brand">
<span class="logo" aria-hidden="true">WA</span>
<div>
<h1>Web Alarm Ultra</h1>
<div class="live">Постановки · этапы · восстановление</div>
</div>
</div>
<nav class="top-nav" aria-label="Разделы Web Alarm">
<button type="button" id="viewChat" aria-pressed="true" aria-controls="chatView" title="Сохранённые диалоги Ultra">Ultra Chat</button>
<button type="button" id="viewBlueprint" aria-pressed="false" aria-controls="blueprintView">Блюпринт LLM</button>
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
<button type="button" id="shutdownWebAlarm">Завершить Web Alarm</button>
<button type="button" id="cleanupInstances">Очистить лишние экземпляры</button>
</div>
</header>
<div id="shutdownResult" class="notice info" role="status" hidden></div>
<div id="instanceResult" class="notice info" role="status" hidden></div>
<section id="chatView" class="chat-view" aria-labelledby="chatHeading">
<div class="chat-layout">
<nav class="chat-side" aria-label="Workspace и диалоги Ultra">
<div class="section-head"><div><p class="side-title">ULTRA CHAT</p><h2 id="chatHeading" tabindex="-1">Диалоги Ultra</h2></div><button type="button" id="chatRefresh" title="Перечитать Workspace, диалоги и модель">↻</button></div>
<p id="chatAccess" class="live" role="status">Проверяем доступ к истории…</p>
<div id="chatError" class="notice error" role="alert" hidden></div>
<div class="chat-personal-heading"><span class="side-title">ЛИЧНЫЕ ЧАТЫ</span><button type="button" id="chatPersonalNew" hidden>+ Новый чат</button><button type="button" id="chatPersonalToggle" class="compact-section-toggle" aria-expanded="true" aria-controls="chatPersonalList" aria-label="Свернуть личные чаты" hidden>▾</button></div>
<div id="chatPersonalList" class="chat-picks" aria-label="Личные диалоги"></div>
<div class="chat-workspace-heading"><span class="side-title">WORKSPACE</span><button type="button" id="chatRegisterWorkspace" title="Выбрать существующую папку или создать новую в окне Windows">+ Создать Workspace</button><button type="button" id="chatWorkspaceToggle" class="compact-section-toggle" aria-expanded="true" aria-controls="chatWorkspaceList" aria-label="Свернуть Workspace" hidden>▾</button></div>
<div id="chatWorkspaceResult" class="notice info" role="status" hidden></div>
<p id="chatWorkspaceState" class="muted" role="status"></p>
<div id="chatWorkspaceList" class="chat-picks" aria-label="Workspace с вложенными диалогами"></div>
<form id="chatTestWorkspaceForm" class="chat-name-form" hidden>
<label for="chatTestWorkspaceTitle">Название временного TEST Workspace</label>
<input id="chatTestWorkspaceTitle" maxlength="120" autocomplete="off" required>
<div class="chat-actions"><button type="submit" id="chatTestWorkspaceSave">Создать TEST Workspace</button><button type="button" id="chatTestWorkspaceCancel">Отмена</button></div>
<p id="chatTestWorkspaceError" role="alert" hidden></p>
</form>
<form id="chatWorkspaceNameForm" class="chat-name-form" hidden>
<label for="chatWorkspaceNameInput">Переименовать Workspace</label><input id="chatWorkspaceNameInput" maxlength="120" autocomplete="off">
<div class="chat-actions"><button type="submit" id="chatWorkspaceNameSave">Сохранить</button><button type="button" id="chatWorkspaceNameCancel">Отмена</button></div>
<p id="chatWorkspaceNameError" class="chat-model-error" role="alert" hidden></p>
</form>
<div id="chatListDock" hidden>
<p id="chatListState" class="muted" role="status">Выберите Workspace.</p>
<div id="chatList" class="chat-picks chat-nested" aria-label="Сохранённые диалоги"></div>
</div>
<div class="chat-actions" hidden><button type="button" id="chatNew" disabled>+ Новый диалог</button><button type="button" id="chatRename" disabled>✎ Переименовать</button></div>
<form id="chatNameForm" class="chat-name-form" aria-label="Название диалога" hidden>
<label for="chatNameInput" id="chatNameLabel">Название диалога</label>
<input id="chatNameInput" maxlength="200" autocomplete="off">
<p id="chatInitializeNotice" class="notice info" role="note" hidden></p>
<div class="chat-actions"><button type="submit" id="chatNameSave" class="primary">Сохранить</button><button type="button" id="chatNameCancel">Отмена</button></div>
<p id="chatNameError" class="chat-model-error" role="alert" hidden></p>
</form>
<p id="chatSidebarNote" class="muted spaced">Нажмите на Workspace, чтобы раскрыть чаты. «+» создаёт диалог, карандаш меняет название. История остаётся в исходной папке. Отправка сообщений пока отключена.</p>
</nav>
<div id="chatMain" class="chat-main" tabindex="-1" role="region" aria-labelledby="chatTitle">
<div class="chat-head"><div><span class="eyebrow" id="chatWorkspaceName">Ultra Chat</span><h2 id="chatTitle">Выберите диалог</h2></div><span id="chatModel" class="tag" title="Модель, выбранная в EVM">Модель: —</span></div>
<div id="chatNotice" class="notice" role="status" hidden></div>
<button type="button" id="chatOlder" hidden>Показать ранее</button>
<ol id="chatHistory" class="chat-history" aria-label="История диалога"></ol>
<p id="chatUsage" class="muted" role="status" aria-live="polite" hidden></p>
<details id="chatPreferences" hidden><summary>Настройки этого чата</summary>
<label>Порог предложения сжатия, токенов <input id="chatContextTokens" type="number" min="1" step="1"></label>
<label>Предпочтительный максимум ответа, токенов <input id="chatAnswerTokens" type="number" min="1" step="1"></label>
<button id="chatAnswerExtended" type="button">20 000 (расширенный)</button> <button id="chatPreferencesSave" type="button">Сохранить</button>
<p class="muted">Предпочтения этого чата. Порог сжатия не равен окну модели. Автосжатие выключено. Применение к провайдеру не подтверждено; TEST использует прежние пределы, REAL закрыт до S3b.</p>
<p id="chatPreferencesStatus" role="status" aria-live="polite"></p></details>
<div id="chatTurnControls" class="chat-request-status" hidden><p id="chatTurnStatus" role="status" aria-live="polite"></p><div id="chatColibriProgress" hidden><details open><summary>Рассуждения Colibri</summary><div id="chatColibriReasoning" class="msg-text"></div></details><p id="chatColibriPartialLabel" hidden>Незавершённый ответ (не сохранён как итоговый)</p><div id="chatColibriPartial" class="msg-text" hidden></div></div><button type="button" id="chatTurnCheck" title="Если ответ не появился или связь прервалась, проверьте состояние отправленного запроса.">Проверить состояние запроса</button> <button type="button" id="chatTurnCancel">Отменить</button> <button type="button" id="chatTurnNew" hidden>Новый отдельный запрос</button><p id="chatTurnCheckResult" class="muted" role="status" aria-live="polite"></p></div>
<form id="chatComposer" class="chat-composer" aria-label="Новое сообщение">
<div class="row"><label for="chatInput">Сообщение</label><span class="composer-actions"><span id="chatModelError" class="chat-model-error" role="alert" hidden></span><span class="chat-model-picker"><button type="button" id="chatModelPick" aria-haspopup="listbox" aria-expanded="false" aria-controls="chatModelMenu" title="Выбрать модель для следующего сообщения">Выбрать модель ▾</button><div id="chatModelMenu" class="chat-model-menu" role="listbox" aria-label="Модель Ultra Chat" hidden></div></span><button type="button" id="chatMic" disabled data-extension="voice-input" aria-label="Голосовой ввод — появится позже" title="Голосовой ввод появится позже">🎤</button></span></div>
<p id="chatComposerNote" class="muted">Отправка сообщений появится на следующем этапе. Сейчас Ultra Chat читает сохранённую историю, создаёт и переименовывает диалоги.</p>
<button type="button" id="chatComposerGrip" class="chat-resize" role="separator" aria-label="Высота поля сообщения" aria-orientation="horizontal" aria-valuemin="72" aria-valuemax="420" aria-valuenow="140" title="Потяните вверх или вниз; стрелки клавиатуры меняют высоту"></button>
<div class="chat-input-wrap"><textarea id="chatInput" disabled aria-describedby="chatComposerNote" placeholder="Отправка появится на следующем этапе"></textarea><button type="button" id="chatSend" disabled data-recover="false" title="Отправить (Enter)">Отправить</button></div>
</form>
</div>
</div>
</section>
<section id="blueprintView" class="bp-view" aria-label="Блюпринт LLM" hidden>
<h2 id="blueprintHeading" class="bp-sr-only" tabindex="-1">Блюпринт LLM</h2>
<!-- BLUEPRINT_CONTENT -->
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
<p class="muted">Модели берутся из общего реестра Ultra. Статус API считает сервер по подтверждённым ответам; подключение и проверка выполняются только по вашему действию.</p></div>
<div class="row"><span id="evmState" class="live" role="status">Реестр ещё не загружен</span><button type="button" id="evmRefresh">↻ Обновить список</button></div>
</div>
<div class="evm-toasts"><div id="evmError" class="notice error" role="alert" hidden></div>
<div id="evmNotice" class="notice success" role="status" hidden></div></div>
<div class="card spaced evm-info"><div class="evm-info-grid">
<div><p class="side-title">Модель Ultra Chat</p><p id="evmSelection">—</p><p class="muted">Выбирается в Ultra Chat, у поля ввода сообщения.</p></div>
<div><p class="side-title">Статус API</p><p id="evmSummary">—</p><p class="muted">✓ ответ подтверждён · ! подтверждение устарело · × ошибка · ○ ещё не проверена или исход неизвестен</p></div>
<div><p class="side-title">GigaChat · все модели</p><p id="evmLiveState">Состояние подключения не проверено</p><div class="row"><button type="button" id="evmLiveStart" disabled>Подключить GigaChat</button><button type="button" id="evmLiveStop" disabled>Отключить GigaChat</button></div><p class="muted">Используются те же подключение и история, что в Ultra Chat. Подключение может обратиться к API; отправка сообщения выполняется отдельно.</p></div>
<div><p class="side-title">Роли и порядок</p><p id="evmRolesSource" class="muted">—</p><p class="muted">Нажмите на карточку — она раскроется. Ctrl + наведение — просмотр; Ctrl + клик или ⧉ закрепляют панель внутри страницы. ↗ открывает отдельное окно Windows. Карточки можно перетаскивать и добавлять в избранное.</p></div>
</div></div>
<div class="evm-columns evm-board">
<section class="evm-col" aria-labelledby="evmFavTitle" id="evmFavCol"><div class="section-head"><h3 id="evmFavTitle">★ Избранное</h3><span id="evmFavState" class="tag">0</span></div><div id="evmFavList" class="evm-list" aria-label="Избранное"></div><p id="evmFavEmpty" class="muted">Перетащите модель сюда или отметьте её звёздочкой ☆. Здесь хранится ссылка: модель остаётся в своей колонке.</p></section>
<section class="evm-col" aria-labelledby="evmApiTitle" id="evmApiCol"><div class="section-head"><h3 id="evmApiTitle">API</h3><span id="evmApiState" class="tag">—</span></div><div id="evmApiList" class="evm-list" aria-label="Модели API"></div><p class="evm-add" aria-disabled="true">+ Добавить — следующий этап</p></section>
<section class="evm-col" aria-labelledby="evmMcpTitle" id="evmMcpCol"><div class="section-head"><h3 id="evmMcpTitle">MCP / Агенты</h3><span id="evmMcpState" class="tag">—</span></div><div id="evmMcpList" class="evm-list" aria-label="Подключения MCP и агентов"></div><p id="evmMcpEmpty" class="muted">Подключений пока нет: источник MCP и агентов не подключён. Здесь ничего не запускается.</p><p class="evm-add" aria-disabled="true">+ Добавить — следующий этап</p></section>
<section class="evm-col" aria-labelledby="evmLocalTitle" id="evmLocalCol"><div class="section-head"><h3 id="evmLocalTitle">Локальные LLM</h3><span id="evmLocalState" class="tag">—</span></div><div id="evmLocalList" class="evm-list" aria-label="Локальные модели"></div><p id="evmLocalEmpty" class="muted">Локальных моделей пока нет: их источник не подключён. Здесь ничего не запускается.</p><p class="evm-add" aria-disabled="true">+ Добавить — следующий этап</p></section>
</div>
<div id="evmPins" class="evm-pins" role="group" aria-label="Закреплённые окна моделей"></div>
<div id="evmExternal" hidden><div class="evm-external-head"><strong id="evmExternalTitle">Карточка модели</strong><div class="row"><button type="button" id="evmTopmost">Поверх всех окон: ВЫКЛ</button><button type="button" id="evmExternalRefresh">↻ Обновить</button><button type="button" id="evmExternalClose">Закрыть окно ×</button></div></div><p id="evmExternalMove" class="evm-external-move">Перенос на другой монитор: перетаскивайте окно за системный заголовок браузера, а не за карточку. В Windows также работает Win + Shift + ←/→.</p><div id="evmExternalCard" class="evm-external-card"></div></div>
<div id="evmPeek" class="evm-peek" role="dialog" aria-modal="false" aria-label="Быстрый просмотр" tabindex="-1" hidden></div>
<div id="evmGhost" class="evm-ghost" aria-hidden="true" hidden></div><div id="evmDropLine" class="evm-drop-line" aria-hidden="true" hidden></div>
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
<p class="muted">Параметры относятся к профилю подключения и действуют для всех его моделей. Изменение таймаута требует нового подтверждения API; срок актуальности меняет только границу между ✓ и !.</p>
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
<div class="window-actions"><button type="button" id="evmCheckClose">Закрыть</button><button type="button" id="evmCheckConnect">Подключить GigaChat в EVM</button><button type="button" id="evmCheckSend" class="primary">Отправить тестовое сообщение</button></div>
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
// Compact board (CLAUDE-WUA-EVM-COMPACT-LAYOUT-001) with the interaction of CLAUDE-WUA-EVM-INTERACTION-DND-001:
// a click opens a card in place inside its column; Ctrl + hover (or «⧉») shows the same full card in a side panel;
// a press that moves more than a few pixels drags the card (Pointer Events only, no native drag-and-drop).
// The manual order and favourites are saved on the server (/ultra/model-cards/view).
const evm={epoch:0,data:null,cards:null,cardsError:null,live:null,liveBusy:false,liveAction:null,liveFailure:null,view:'chat',drafts:{},outputs:{},window:null,tab:'conn',saving:false,checking:false,setError:'',
  ccards:{},cheads:{},copen:{},cquick:{},cexp:{},fk:{},expanded:new Set(),uid:0,peek:{id:null,section:null},peekTimer:0,
  pins:{},pinOrder:[],hinted:null,promote:null,winDrag:null,layoutQueue:Promise.resolve(),layoutLoaded:false,
  hover:null,ctrl:false,press:null,drag:null,scrollFrame:0,suppressUntil:0,returnTo:null,viewSaving:false,noticeTimer:0};
function queryValue(name){try{const m=String(location.search||'').match(new RegExp('(?:^|[?&])'+name+'=([^&]*)'));return m?decodeURIComponent(m[1]):null}catch(_){return null}}
const EXTERNAL_MODEL=queryValue('evm_window'),EXTERNAL_TOP=queryValue('evm_top')==='1';
let externalPip=null;
if(EXTERNAL_MODEL&&document.body?.getAttribute?.('data-stage5-offline')!=='true')document.body.classList.add('evm-external');
const evmChannel=typeof BroadcastChannel==='function'?new BroadcastChannel('web-alarm-evm-v1'):null;
if(evmChannel)evmChannel.onmessage=()=>{if(evm.view==='evm'||EXTERNAL_MODEL)loadEvm();if(chat.started)loadChatAccess()};
const EVM_STATUS={REGISTERED:['В реестре',''],DISABLED:['Отключена в реестре','bad'],NOT_CONNECTED:['Ещё не подключено','unknown'],AVAILABLE:['Реестр загружен',''],REGISTRY_UNAVAILABLE:['Реестр недоступен','bad']};
function evmTag(code){const [label,cls]=EVM_STATUS[code]||[String(code??'Неизвестно'),'unknown'];const t=element('span',label,'tag'+(cls?' '+cls:''));t.setAttribute('title',String(code??''));return t}
// Sections share one shell; their URL hashes also support direct navigation.
const VIEWS={chat:['chatView','viewChat','#chatMain','К истории диалога'],blueprint:['blueprintView','viewBlueprint','#blueprintHeading','К редактору схемы'],operator:['layout','viewOperator','#main','К состоянию TASK'],evm:['evmView','viewEvm','#evmHeading','К подключениям Ultra']};
function initialView(){
  try{return {'#operator':'operator','#evm':'evm','#chat':'chat','#blueprint':'blueprint'}[typeof location==='undefined'?'':String(location.hash||'')]||'chat'}catch(_){return 'chat'}
}
function rememberView(name){
  try{if(typeof history!=='undefined'&&typeof location!=='undefined'&&history.replaceState)history.replaceState(null,'','#'+name)}catch(_){}
}
function showView(name,initial=false){
  if(stage5Offline)name='chat';
  if(!VIEWS[name])name='chat';const previous=evm.view;evm.view=name;
  if(name!=='evm'){closePeek();pinCancel()}  // pinned windows stay (hidden with EVM), the preview goes
  for(const [key,[region,button]] of Object.entries(VIEWS)){$(region).hidden=key!==name;$(button).setAttribute('aria-pressed',String(key===name))}
  $('showWorkspaces').hidden=name!=='operator';$('showTasks').hidden=name!=='operator';
  $('skipLink').setAttribute('href',VIEWS[name][2]);text('skipLink',VIEWS[name][3]);
  if(!initial)rememberView(name);
  if(name==='blueprint'){if(!initial)$('blueprintHeading').focus();if(window.UltraBlueprint)window.UltraBlueprint.open();return}
  if(name==='evm'){if(!initial)$('evmHeading').focus();return loadEvm()}
  if(name==='chat'){
    if(!initial)$('chatHeading').focus();
    if(previous==='operator'&&chat.started)return loadChatWorkspaces();
    return startChat()
  }
  if(!initial)$('main').focus()
}
function validEvm(data){
  const api=data?.columns?.api;
  if(!api||!Array.isArray(api.connections)||!data.columns.mcp_agents||!data.columns.local_llm||!data.selection?.chat)return false;
  return api.connections.every(c=>c&&['connection_id','model_id','display_name','provider_model_id','status','verification'].every(k=>typeof c[k]==='string')&&typeof c.selectable==='boolean'&&typeof c.selected==='boolean')
}
function evmSelectionText(s){
  if(s.state==='SAVED')return 'Выбрана: '+s.display_name+' · '+s.model_id+' → '+s.provider_model_id+(s.selected_at?' · сохранено '+s.selected_at:'');
  if(s.state==='CORRUPT')return 'Сохранённый выбор повреждён и не используется. Выберите модель заново в Ultra Chat.';
  if(s.state==='INVALID_REFERENCE')return 'Сохранённая модель недоступна в реестре ('+(s.connection_id||'—')+'). Выберите модель заново в Ultra Chat.';
  if(s.state==='REGISTRY_UNAVAILABLE')return 'Сохранённый выбор ('+(s.connection_id||'—')+') сейчас не проверить: общий реестр моделей недоступен.';
  return 'Модель для Ultra Chat ещё не выбрана.'
}
function validCards(d){
  return !!d&&Array.isArray(d.cards)&&Array.isArray(d.role_definitions)&&Array.isArray(d.providers)&&Array.isArray(d.profiles)&&!!d.settings&&!!d.limits&&!!d.live_check&&
    d.role_definitions.every(r=>r&&['role','label','hint'].every(k=>typeof r[k]==='string'))&&
    d.cards.every(c=>c&&['connection_id','model_id','display_name','provider_id','provider_model_id','profile_id','settings_version','description'].every(k=>typeof c[k]==='string')&&
      (c.enabled===undefined||typeof c.enabled==='boolean')&&Array.isArray(c.roles)&&!!c.api&&['green','orange','red','gray'].includes(c.api.color))
}
const API_TEXT={CONFIRMED:'Ответ модели подтверждён',STALE:'Подтверждение устарело',NEVER_CONFIRMED:'Успешной проверки ещё не было',LAST_OUTCOME_UNKNOWN:'Исход последнего обращения неизвестен',SETTINGS_CHANGED:'Настройки подключения изменились — нужна новая проверка',
  LAST_CHECK_FAILED:'Последняя проверка завершилась отказом',STATE_CORRUPT:'Сведения о проверках повреждены',TIMESTAMP_INVALID:'Дата проверки некорректна',ADAPTER_MISSING:'Для провайдера нет адаптера',REGISTRY_DISABLED:'Модель отключена в реестре'};
const API_MARK={green:'✓',orange:'!',red:'×',gray:'○'};
function apiText(a){
  const base=API_TEXT[a.reason]||String(a.reason||'Статус неизвестен');
  return a.age_days==null?base:base+': '+a.age_days+' дн. назад, срок актуальности '+a.freshness_days+' дн.'
}
function apiDot(a){  // one component and one server status for the card header and the diagnostic window
  const color=API_MARK[a.color]?a.color:'gray';
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
const SECTIONS=[['favorites','evmFavList','evmFavEmpty'],['api','evmApiList',null,'api'],['mcp','evmMcpList','evmMcpEmpty','mcp_agents'],['local','evmLocalList','evmLocalEmpty','local_llm']];
const KIND_LABEL={api:'API',mcp:'MCP / агент',local:'Локальная'};
const SECTION_LABEL={favorites:'Избранное',api:'API',mcp:'MCP / Агенты',local:'Локальные LLM'};
function mark(el,cls,on){if(!el)return;const set=new Set(String(el.className||'').split(' ').filter(Boolean));if(on)set.add(cls);else set.delete(cls);el.className=[...set].join(' ')}
function editButton(label,c,cls){const b=element('button',label,cls);b.type='button';b.setAttribute('aria-label',label.replace(/^\W+\s*/,'')+': '+c.display_name);return b}
// Every focusable control of a card instance has a stable key, so a redraw (after a move, a star or a window) gives
// the keyboard back to the same control. Instances: 'x:<section>|<id>' (the card in its column) and 'peek'.
function fk(el,inst,name){const key=inst+':'+name;el.setAttribute('data-fk',key);evm.fk[key]=el;return el}
// The full card: the same component for every model, shown in place under its compact card or in the side panel.
function modelCard(c,data,section,inst){
  const card=element('article',null,'mcard');card.setAttribute('data-connection',c.connection_id);card.setAttribute('data-model',c.model_id);card.setAttribute('aria-label','Модель '+c.display_name);
  const head=element('div',null,'mcard-head');
  const params=element('span',paramsText(c.params_billion),'params');params.setAttribute('title',c.params_billion==null?'Количество параметров не указано':'Количество параметров, указано пользователем');
  const provider=data.providers.find(p=>p.provider_id===c.provider_id);
  head.append(element('h4',c.display_name,'mcard-name'),apiDot(c.api),params,element('span',provider?provider.display_name:c.provider_id,'mcard-side'));
  const permitted=c.enabled!==false;
  const providerState=c.provider_id==='gigachat'?(evm.liveBusy?(evm.liveAction==='start'?'Подключение выполняется':'Отключение выполняется'):
    evm.liveFailure?(evm.liveFailure==='disconnect'?'Ошибка отключения':'Ошибка подключения'):evm.live?.real_available?'GigaChat подключён':evm.live?.mode==='ORDINARY'?'GigaChat отключён':'Состояние неизвестно'):
    c.provider_id==='colibri'?(c.local_target?.status==='READY'?'Colibri · READY (OFFLINE)':
      'Colibri · '+(c.local_target?.status||'недоступен')):'Подключение этого провайдера не подтверждено';
  const stateLine=element('p','Модель: '+(permitted?'включена':'отключена')+' · Провайдер: '+providerState+' · Работоспособность: '+apiText(c.api),'mcard-note');
  const sub=element('div',null,'mcard-sub');sub.append(element('strong','Назначенные роли'),element('span','Наведите на название для описания','mcard-note'));
  const states=new Map(c.roles.map(r=>[r.role,r.state]));
  const roles=element('div',null,'roles');roles.append(...data.role_definitions.map(def=>roleItem(def,states.get(def.role))));
  // The description is edited in «Настройки → Модель»; the command and a click on the box lead there directly.
  const edit=fk(editButton('✎ Изменить описание',c,'link'),inst,'edit');edit.onclick=()=>openWindow('settings',c.model_id,'model',inst+':edit');
  const label=element('div',null,'mcard-sub');label.append(element('span','Сильные стороны модели','mcard-label'),edit);
  const strengths=fk(element('div',c.description||'Описание пока не заполнено. Нажмите «Изменить описание».','strengths editable'+(c.description?'':' placeholder')),inst,'desc');
  strengths.setAttribute('tabindex','0');strengths.setAttribute('aria-label','Сильные стороны модели '+c.display_name+'. Нажмите, чтобы изменить');strengths.setAttribute('title','Нажмите, чтобы изменить описание');
  strengths.onclick=()=>openWindow('settings',c.model_id,'model',inst+':desc');
  const settings=fk(editButton('⚙ Настройки',c),inst,'settings');settings.onclick=()=>openWindow('settings',c.model_id,null,inst+':settings');
  const check=fk(editButton('▤ Проверить чат',c,'primary'),inst,'check');check.setAttribute('aria-label','Проверка API модели '+c.display_name);check.onclick=()=>openWindow('check',c.model_id,null,inst+':check');
  const enabled=permitted;
  const toggle=fk(editButton(enabled?'Отключить':'Включить',c),inst,'toggle');
  toggle.setAttribute('aria-pressed',String(enabled));toggle.onclick=()=>toggleModel(c.model_id,!enabled);
  const external=fk(editButton('↗ Внешнее окно',c),inst,'external');external.onclick=()=>openExternal(c.connection_id);
  const actions=element('div',null,'mcard-actions');
  if(c.is_local&&c.provider_id==='colibri'){
    // Profile/diagnostic execution is not authorised in MVP1 OFFLINE.
    edit.disabled=true;strengths.onclick=null;strengths.removeAttribute('tabindex');
    actions.append(toggle,external);
  }else actions.append(settings,check,toggle,external);
  card.append(head,stateLine,sub,roles,label,strengths,actions);
  if(evm.drafts[c.model_id])card.append(element('p','Есть несохранённые изменения настроек.','mcard-note'));
  return card
}
function entryCard(e,section,inst){  // an entry without card data (MCP, local, or card data unavailable): nothing is invented
  const card=element('article',null,'mcard');card.setAttribute('data-connection',e.base.connection_id);
  const head=element('div',null,'mcard-head');head.append(element('h4',e.base.display_name||e.base.connection_id,'mcard-name'),element('span',KIND_LABEL[e.kind]||e.kind,'mcard-side'));
  card.append(head,element('p',e.kind==='api'?'Подробности карточки недоступны: '+(evm.cardsError||'нет данных сервера'):'Подробности появятся, когда источник этого подключения будет подключён к EVM.','mcard-note'));
  const external=fk(element('button','↗ Внешнее окно'),inst,'external');external.type='button';external.onclick=()=>openExternal(e.base.connection_id);
  const actions=element('div',null,'mcard-actions');actions.append(external);card.append(actions);
  return card
}
function fullCard(e,section,inst){return e.card&&evm.cards?modelCard(e.card,evm.cards,section,inst):entryCard(e,section,inst)}
function rolesSourceText(cards){
  if(!cards)return 'Назначения ролей не загружены.';
  const r=cards.roles_source,tk={SAVED:'настройки прежней Ultra (Tkinter)',DEFAULTS:'значения прежней Ultra по умолчанию: её файл настроек не найден',
    UNREADABLE:'файл настроек прежней Ultra не читается, поэтому её роли показаны как «?»',NOT_CONNECTED:'этот запуск не подключён к настройкам прежней Ultra, поэтому её роли показаны как «?»'}[r.state]||String(r.state);
  return 'Источник ролей: «Чат» — выбор в Ultra Chat; остальные — '+tk+'.'+(r.fallbacks?.length?' Сохранённая модель '+r.fallbacks.length+' роли(ей) отсутствует в реестре, Ultra использует свою модель по умолчанию.':'')
}
function summaryText(cards){
  if(!cards)return 'нет данных';
  const n={green:0,orange:0,red:0,gray:0};for(const c of cards.cards)n[c.api.color]++;
  return '✓ '+n.green+' · ! '+n.orange+' · × '+n.red+' · ○ '+n.gray
}
// One source per entry for every column: the catalog entry plus its card data, if the server has it.
function entryOf(id){
  const cols=evm.data?.columns||{};
  const base=[...(cols.api?.connections||[]),...(cols.mcp_agents?.connections||[]),...(cols.local_llm?.connections||[])].find(c=>c?.connection_id===id);
  return base?{base,card:evm.cards?.cards.find(c=>c.connection_id===id)||null,kind:String(id).split(':')[0]}:null
}
function favorites(){return evm.cards?.view?.sections?.favorites||[]}
function sectionIds(section){
  if(section==='favorites')return favorites().filter(id=>entryOf(id));
  const column={api:'api',mcp:'mcp_agents',local:'local_llm'}[section];
  const natural=(evm.data?.columns?.[column]?.connections||[]).map(c=>c.connection_id);
  const saved=(evm.cards?.view?.sections?.[section]||[]).filter(id=>natural.includes(id));  // the server order, checked against the catalog
  return saved.concat(natural.filter(id=>!saved.includes(id)))
}
function nameOf(id){const e=entryOf(id);return e?.card?.display_name||e?.base.display_name||id}
function rectOf(el){return el&&typeof el.getBoundingClientRect==='function'?el.getBoundingClientRect():null}
function compactCard(id,section){
  const e=entryOf(id);if(!e)return null;
  const name=nameOf(id),fav=favorites().includes(id),key=section+'|'+id,inst='x:'+key,expanded=evm.expanded.has(key);
  // Controls side by side, never one inside another: «open» (shows the full card in place), «⧉» and the star.
  const el=element('article',null,'ccard'+(expanded?' expanded':''));
  el.setAttribute('data-connection',id);el.setAttribute('data-section',section);
  const head=element('div',null,'chead');
  const grip=element('span','⠿','grip');grip.setAttribute('aria-hidden','true');grip.setAttribute('title','Потяните мышью, чтобы переставить');
  const open=fk(element('button',null,'copen'),inst,'open');open.type='button';open.setAttribute('aria-expanded',String(expanded));
  open.setAttribute('aria-label',name+' — '+(KIND_LABEL[e.kind]||e.kind)+'. Раскрыть карточку; Alt+↑/↓ — переставить');
  const title=element('div',null,'ctitle');title.append(element('span',name,'cname'));
  if(e.card)title.append(apiDot(e.card.api));
  if(typeof e.card?.params_billion==='number')title.append(element('span',paramsText(e.card.params_billion),'params'));
  const provider=e.card?(evm.cards.providers.find(p=>p.provider_id===e.card.provider_id)?.display_name||e.card.provider_id):(e.base.provider||'');
  const body=element('div',null,'cbody');body.append(title,element('span',[KIND_LABEL[e.kind]||e.kind,provider].filter(Boolean).join(' · '),'csub'));
  const quick=fk(element('button','⧉','cquick'),inst,'quick');quick.type='button';quick.setAttribute('aria-haspopup','dialog');
  quick.setAttribute('aria-expanded',String(!!pinned(id)));quick.setAttribute('aria-label',(pinned(id)?'Показать окно модели: ':'Закрепить в отдельном окне: ')+name);
  quick.setAttribute('title','Отдельное окно (то же — Ctrl + клик); Ctrl + наведение — быстрый просмотр');
  quick.onclick=ev=>{ev?.stopPropagation?.();pinModel(id,section,'quick',ev?.detail===0)};
  const external=fk(element('button','↗','cquick'),inst,'external');external.type='button';
  external.setAttribute('aria-label','Открыть внешнее окно: '+name);external.onclick=ev=>{ev?.stopPropagation?.();openExternal(id)};
  const star=fk(element('button',fav?'★':'☆','star'),inst,'star');star.type='button';star.setAttribute('aria-pressed',String(fav));
  star.setAttribute('aria-label',(fav?'Убрать из избранного: ':'Добавить в избранное: ')+name);star.disabled=!evm.cards?.view;
  star.onclick=ev=>{ev?.stopPropagation?.();toggleFavorite(id)};  // the star never opens the card
  for(const b of [quick,external,star])b.onpointerdown=ev=>{  // a press on them never starts a drag, and never ends as a click of the card
    ev?.stopPropagation?.();evm.suppressUntil=Infinity};  // (released elsewhere on the row, the browser clicks the row)
  open.append(body);head.append(grip,open,quick,external,star);
  const part=element('div',null,'cexp');part.id='evmx'+(++evm.uid);part.setAttribute('role','region');part.setAttribute('aria-label','Карточка: '+name);
  open.setAttribute('aria-controls',part.id);
  el.append(head,part);
  head.onclick=ev=>headClick(ev,id,section);  // a mouse click, or Enter / Space on «open»
  head.onpointerdown=ev=>pressStart(ev,id,section);
  head.ondragstart=ev=>ev?.preventDefault?.();  // no native drag-and-drop: the pointer handlers are the only ones
  open.onkeydown=ev=>cardKey(ev,id,section);
  el.onmouseenter=ev=>hoverCard(ev,id,section);el.onmouseleave=()=>leaveCard();
  evm.ccards[key]=el;evm.cheads[key]=head;evm.copen[key]=open;evm.cquick[key]=quick;evm.cexp[key]=part;
  fillExpanded(key);
  return el
}
function fillExpanded(key){  // the full card in place under its compact card: the cards below move down, nothing covers them
  const part=evm.cexp[key],el=evm.ccards[key];if(!part)return;
  const id=el.getAttribute('data-connection'),section=el.getAttribute('data-section'),e=entryOf(id),on=evm.expanded.has(key)&&!!e;
  for(const name of ['edit','desc','settings','check','toggle','external'])delete evm.fk['x:'+key+':'+name];
  part.replaceChildren(...(on?[fullCard(e,section,'x:'+key)]:[]));part.hidden=!on;
  mark(el,'expanded',on);evm.copen[key].setAttribute('aria-expanded',String(on))
}
function toggleExpanded(id,section){  // several cards may stay open; opening one never closes another
  const key=section+'|'+id;if(!evm.ccards[key])return;
  if(evm.expanded.has(key))evm.expanded.delete(key);else evm.expanded.add(key);
  fillExpanded(key);
  if(!evm.expanded.has(key))evm.cheads[key]?.scrollIntoView?.({block:'nearest'});  // a closed card stays in view
  if(evm.peek.id)positionPeek()
}
function headClick(ev,id,section){
  if(ev?.detail!==0&&Date.now()<evm.suppressUntil){evm.suppressUntil=0;return}  // the release that ends a drag is not a click
  if(ev?.ctrlKey){pinModel(id,section,'open',false);return}  // Ctrl + click pins the model in its own window
  toggleExpanded(id,section)
}
function renderEvm(){
  const data=evm.data;if(!data)return;
  const cols=data.columns,s=data.selection.chat,cards=evm.cards;
  const live=evm.live,ready=live?.mode==='ORDINARY'&&live.execution_mode!=='PROTOCOL_TEST'&&!stage5Offline;
  text('evmLiveState',!ready?'Управление доступно только в локальном STANDARD':evm.liveBusy?
    (evm.liveAction==='start'?'Подключение выполняется':'Отключение выполняется'):evm.liveFailure?
    (evm.liveFailure==='disconnect'?'Ошибка отключения':'Ошибка подключения')+' · проверьте состояние перед повтором':live.real_available?
    'GigaChat подключён · реальные отправки разрешены':'GigaChat отключён · история доступна');
  $('evmLiveStart').disabled=!ready||live.real_available||evm.liveBusy;
  $('evmLiveStop').disabled=!ready||!live.real_available||evm.liveBusy;
  $('evmApiState').replaceChildren(evmTag(cols.api.state));
  $('evmMcpState').replaceChildren(evmTag(cols.mcp_agents.state));
  $('evmLocalState').replaceChildren(evmTag(cols.local_llm.state));
  text('evmSelection',evmSelectionText(s));text('evmSummary',summaryText(cards));text('evmRolesSource',rolesSourceText(cards));
  if(cols.api.state!=='AVAILABLE')notice('evmError','Общий реестр моделей недоступен: '+(cols.api.reason||cols.api.state));
  const focusKey=document.activeElement?.getAttribute?.('data-fk')||null;  // the keyboard comes back to the same control
  evm.ccards={};evm.cheads={};evm.copen={};evm.cquick={};evm.cexp={};evm.fk={};
  for(const [section,list,empty] of SECTIONS){
    const ids=sectionIds(section);
    $(list).replaceChildren(...ids.map(id=>compactCard(id,section)).filter(Boolean));
    if(empty)$(empty).hidden=ids.length>0;
  }
  for(const key of [...evm.expanded])if(!evm.ccards[key])evm.expanded.delete(key);
  if(evm.drag)mark(evm.ccards[evm.drag.section+'|'+evm.drag.id],'dragging',true);
  text('evmFavState',String(sectionIds('favorites').length));
  const count=cols.api.connections.length+(cols.local_llm?.connections?.length||0);
  text('evmState',count?'Моделей в реестре: '+count:'Реестр пуст');
  if(evm.peek.id){if(entryOf(evm.peek.id)&&evm.ccards[evm.peek.section+'|'+evm.peek.id])fillPeek();else closePeek()}
  for(const id of evm.pinOrder)fillPin(id);  // the same windows, same places: only their content is new
  if(EXTERNAL_MODEL)renderExternalCard();
  restoreFocus(focusKey)
}
function renderExternalCard(){
  const e=entryOf(EXTERNAL_MODEL),box=$('evmExternalCard');
  $('evmExternal').hidden=false;
  text('evmExternalTitle',e?nameOf(EXTERNAL_MODEL):'Карточка недоступна');
  text('evmExternalMove',EXTERNAL_TOP?'PiP-окно переносится за системный заголовок, если это разрешает браузер и Windows.':
    'Перенос на другой монитор: перетаскивайте окно за системный заголовок браузера, а не за карточку. В Windows также работает Win + Shift + ←/→.');
  box.replaceChildren(...(e?[fullCard(e,homeSection(EXTERNAL_MODEL),'external:'+EXTERNAL_MODEL)]:[element('p','Подключение отсутствует в реестре.','muted')]));
  box.hidden=!!externalPip;
  text('evmTopmost',EXTERNAL_TOP||externalPip?'Поверх всех окон: ВКЛ — выключить':'Поверх всех окон: ВЫКЛ — включить');
  $('evmTopmost').disabled=!EXTERNAL_TOP&&!(typeof documentPictureInPicture!=='undefined'&&documentPictureInPicture.requestWindow);
}
async function toggleTopmost(){
  if(!EXTERNAL_MODEL)return;
  if(EXTERNAL_TOP){window.parent.close();return}
  if(externalPip){externalPip.close();externalPip=null;renderExternalCard();return}
  if(typeof documentPictureInPicture==='undefined'||!documentPictureInPicture.requestWindow){
    notice('evmError','Этот Chromium не поддерживает окно поверх всех окон. Обычное внешнее окно остаётся доступным.');return
  }
  try{
    const pip=await documentPictureInPicture.requestWindow({width:540,height:700});
    const frame=pip.document.createElement('iframe');frame.className='evm-top-frame';
    frame.setAttribute('title','EVM: '+nameOf(EXTERNAL_MODEL));
    frame.src=String(location.pathname||'/')+'?evm_window='+encodeURIComponent(EXTERNAL_MODEL)+'&evm_top=1#evm';
    pip.document.body.style.cssText='margin:0;width:100vw;height:100vh;overflow:hidden;background:#16212d';
    pip.document.body.append(frame);
    externalPip=pip;pip.addEventListener('pagehide',()=>{externalPip=null;renderExternalCard()},{once:true});
    renderExternalCard();
  }catch(e){notice('evmError','Режим поверх всех окон недоступен: '+(e?.name||'ошибка браузера'))}
}
function openExternal(id){
  const e=entryOf(id);if(!e||stage5Offline)return;
  const url=String(location.pathname||'/')+'?evm_window='+encodeURIComponent(id)+'#evm';
  const child=window.open(url,'wua_evm_'+id.replace(/[^a-zA-Z0-9_]/g,'_'),'popup=yes,width=540,height=740,resizable=yes,scrollbars=yes');
  if(!child){notice('evmError','Браузер заблокировал внешнее окно. Разрешите всплывающие окна для локального Web Alarm и повторите действие.');return}
  child.focus?.();
}
async function toggleModel(id,enabled){
  if(!evm.cards||evm.saving)return;
  const revision=evm.cards.settings.revision;evm.saving=true;
  try{
    const r=await chatPost('/ultra/model-cards/'+encodeURIComponent(id)+'/enabled',{base_revision:revision,enabled});
    if(r?.card?.model_id!==id||r.card.enabled!==enabled)throw Error('Сервер не подтвердил состояние');
    evmChannel?.postMessage({kind:'model_state'});
    await loadEvm();
    if(chat.started){await loadChatAccess();renderTurnComposer()}
    evmSay((enabled?'Включена: ':'Отключена: ')+nameOf(id));
  }catch(e){await loadEvm();notice('evmError','Состояние модели не изменено или не подтверждено: '+(e.message||e))}
  finally{evm.saving=false}
}
function restoreFocus(key){
  if(!key)return null;
  const cut=key.lastIndexOf(':'),inst=key.slice(0,cut),name=key.slice(cut+1),other={up:'down',down:'up'}[name];
  // at an end of the list the other move command takes the keyboard; else the card's own «open» (or the window itself)
  const el=[key,other&&inst+':'+other,inst+':open'].map(k=>k&&evm.fk[k]).find(b=>b&&!b.disabled)||
    (inst==='peek'&&evm.peek.id?$('evmPeek'):inst.startsWith('pin:')?pinned(inst.slice(4))?.el:null);
  el?.focus?.();
  return el||null
}
// Temporary preview (#evmPeek). Plain hover shows nothing. Ctrl + hover shows the full card beside its column and
// switches at once from card to card; releasing Ctrl, «×» or Escape closes it. It is always above the pinned windows.
// A press inside it turns it into a pinned window where it stands; a press on its title pins it and moves it at once.
const PEEK_CLOSE_MS=180,PEEK_W=560,PEEK_MIN=320;
const COLUMNS={favorites:'evmFavCol',api:'evmApiCol',mcp:'evmMcpCol',local:'evmLocalCol'};
function peekIs(id,section){return evm.peek.id===id&&evm.peek.section===section}
function hoverCard(ev,id,section){
  evm.hover={id,section};clearTimeout(evm.peekTimer);
  if(typeof ev?.ctrlKey==='boolean')evm.ctrl=ev.ctrlKey;
  ctrlPeek()
}
function leaveCard(){evm.hover=null;evm.hinted=null;peekLeave()}
function ctrlPeek(){
  const h=evm.hover;
  if(!evm.ctrl||!h||evm.view!=='evm'||evm.press||evm.drag||evm.winDrag||evm.window||evm.promote)return;
  if(pinned(h.id)){  // no second copy of a pinned model: its window is shown instead, once per hover
    if(evm.peek.id)closePeek();
    if(evm.hinted!==h.id){evm.hinted=h.id;activatePin(h.id,{flash:true})}
    return
  }
  if(peekIs(h.id,h.section))return;
  openPeek(h.id,h.section)  // already open: only the content changes, the panel does not blink
}
function peekLeave(){
  clearTimeout(evm.peekTimer);
  if(evm.peek.id&&!evm.promote)evm.peekTimer=setTimeout(()=>{if(!evm.promote&&!evm.hover)closePeek()},PEEK_CLOSE_MS)
}
function cardKey(ev,id,section){
  if(ev.altKey&&(ev.key==='ArrowUp'||ev.key==='ArrowDown')){ev.preventDefault?.();moveCard(section,id,ev.key==='ArrowUp'?-1:1)}
}
function openPeek(id,section){
  if(!entryOf(id)||evm.drag)return;
  clearTimeout(evm.peekTimer);
  evm.peek={id,section};
  const box=$('evmPeek');box.hidden=false;  // visible first: the position needs the real height
  fillPeek();
  box.className='evm-peek open'
}
function fillPeek(){
  const {id,section}=evm.peek,e=entryOf(id),box=$('evmPeek');
  for(const k of Object.keys(evm.fk))if(k.startsWith('peek:'))delete evm.fk[k];
  const bar=element('div',null,'peek-bar'),close=fk(element('button','×','peek-close'),'peek','close');
  close.type='button';close.setAttribute('aria-label','Закрыть быстрый просмотр');close.onclick=()=>closePeek({focus:true});
  close.onpointerdown=ev=>ev?.stopPropagation?.();  // «×» closes, it never pins
  bar.onpointerdown=ev=>previewBarPress(ev);
  bar.append(element('span','Быстрый просмотр · '+SECTION_LABEL[section],'peek-title'),element('span','Нажмите на окно — закрепить','peek-hint'),close);
  box.replaceChildren(bar,fullCard(e,section,'peek'));
  box.setAttribute('aria-label','Быстрый просмотр: '+nameOf(id)+' · '+SECTION_LABEL[section]);
  positionPeek()
}
function closePeek(opts={}){
  clearTimeout(evm.peekTimer);
  const {id,section}=evm.peek;if(!id)return;
  const box=$('evmPeek'),active=document.activeElement;
  const inside=active===box||String(active?.getAttribute?.('data-fk')||'').startsWith('peek:');
  evm.peek={id:null,section:null};
  for(const k of Object.keys(evm.fk))if(k.startsWith('peek:'))delete evm.fk[k];
  box.hidden=true;box.className='evm-peek';box.replaceChildren();
  if(opts.focus&&inside)evm.copen[section+'|'+id]?.focus()
}
function topLimit(){  // never under the sticky page header
  const head=rectOf(typeof document.querySelector==='function'?document.querySelector('header.top'):null);
  return Math.max(12,Math.round((head?head.bottom:0)+8))
}
function sidePlace(r,section,want,heightAt){  // beside the column of a card, never over it; a sheet above or below on a narrow screen
  const col=rectOf($(COLUMNS[section]))||r,vw=window.innerWidth,vh=window.innerHeight,M=12,G=10,minTop=topLimit();
  const room={right:vw-col.right-G-M,left:col.left-G-M};
  const sides=section==='favorites'||section==='api'?['right','left']:['left','right'];  // left columns open to the right
  let side=sides.find(s=>room[s]>=want),width=want;
  if(!side){const best=room.right>=room.left?'right':'left';if(room[best]>=PEEK_MIN){side=best;width=Math.floor(room[best])}}
  if(side){
    const maxH=Math.max(160,vh-minTop-M),h=heightAt(width,maxH);
    return {side,width,maxH,left:side==='right'?col.right+G:col.left-G-width,top:Math.max(minTop,Math.min(r.top,vh-h-M))}
  }
  const below=vh-M-(r.bottom+G),above=r.top-G-minTop;side=below>=above?'below':'above';  // the card itself stays visible
  width=vw-2*M;const maxH=Math.max(160,Math.round(side==='below'?below:above)),h=Math.min(heightAt(width,maxH),maxH);
  return {side,width,maxH,left:M,top:side==='below'?Math.max(minTop,Math.min(r.bottom+G,vh-M-h)):Math.max(minTop,r.top-G-h)}
}
function positionPeek(){
  const box=$('evmPeek'),r=rectOf(evm.cheads[evm.peek.section+'|'+evm.peek.id]);
  if(!r||typeof window==='undefined'||!window.innerWidth)return;
  const s=sidePlace(r,evm.peek.section,Math.min(PEEK_W,window.innerWidth-24),(w,maxH)=>{box.style.width=w+'px';box.style.maxHeight=maxH+'px';return box.offsetHeight||0});
  box.style.width=s.width+'px';box.style.maxHeight=s.maxH+'px';
  box.setAttribute('data-place',s.side);box.style.left=Math.round(s.left)+'px';box.style.top=Math.round(s.top)+'px'
}
function peekAt(){const b=$('evmPeek');return {x:Math.round(parseFloat(b.style.left)||0),y:Math.round(parseFloat(b.style.top)||0)}}
function previewPress(ev){  // the preview becomes a pinned window where it stands, after this press (its click still works)
  if(!evm.peek.id||evm.promote||ev?.button>0)return;
  evm.promote={id:evm.peek.id,section:evm.peek.section,pointerId:ev?.pointerId}
}
function previewBarPress(ev){  // a press on its title: pinned at once and moved by the same pointer
  ev?.stopPropagation?.();
  if(!evm.peek.id||ev?.button>0)return;
  const {id,section}=evm.peek,at=peekAt();
  closePeek();evm.promote=null;
  if(openPin(id,{section,from:section+'|'+id,save:true,...at}))pinPress(ev,id)
}
function previewRelease(ev){
  const q=evm.promote;if(!q||(ev&&q.pointerId!=null&&ev.pointerId!==q.pointerId))return;
  setTimeout(promotePreview,0)  // after the click of a button pressed inside the preview
}
function promotePreview(){
  const q=evm.promote;evm.promote=null;
  if(!q||!peekIs(q.id,q.section))return;
  const at=peekAt(),back=evm.returnTo,active=document.activeElement?.getAttribute?.('data-fk');
  closePeek();
  if(!openPin(q.id,{section:q.section,from:q.section+'|'+q.id,save:true,...at}))return;
  if(back?.key?.startsWith('peek:'))back.key='pin:'+q.id+back.key.slice(4);  // a window it opened returns to the pinned copy
  if(active?.startsWith('peek:'))restoreFocus('pin:'+q.id+active.slice(4))
}
// Pinned windows (CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001): any number of independent windows, one per entry (its stable
// connection_id), in their own layer under the preview and over the board. Each is dragged by its title, raised by a
// press and closed only by its own «×» — never by Ctrl, Escape, a click outside, another model, a drag or another view.
// The page keeps each window where the user put it; the server keeps the layout per window (/ultra/model-cards/layout).
const PIN_W=460,PIN_STEP=28,PIN_MOVE_PX=3;
function homeSection(id){const kind=String(id).split(':')[0];return COLUMNS[kind]&&kind!=='favorites'?kind:'api'}
function pinned(id){const p=evm.pins[id];return p&&!p.missing?p:null}
function pinModel(id,section,from,focus){  // Ctrl + click and «⧉»: pin the model, or bring its existing window forward
  if(evm.drag||evm.winDrag)return;
  if(evm.pins[id]){activatePin(id,{flash:true,focus});return}
  const at=evm.peek.id===id?peekAt():null;
  if(evm.peek.id===id)closePeek();
  openPin(id,{section,from:section+'|'+id,focus,save:true,...(at||{})})
}
function openPin(id,opts={}){
  if(!entryOf(id))return null;
  if(evm.pins[id]){activatePin(id,{flash:true,focus:opts.focus});return evm.pins[id]}
  const el=element('div',null,'evm-pin');el.setAttribute('role','dialog');el.setAttribute('aria-modal','false');el.setAttribute('tabindex','-1');
  el.setAttribute('data-connection',id);
  const bar=element('div',null,'pin-bar');bar.setAttribute('tabindex','0');
  const title=element('span','','pin-title'),close=element('button','×','pin-close');close.type='button';
  bar.append(title,close);
  const body=element('div',null,'pin-body');
  el.append(bar,body);
  const p={id,el,bar,title,close,body,x:0,y:0,missing:false,from:opts.from||null};
  evm.pins[id]=p;evm.pinOrder.push(id);
  bar.onpointerdown=ev=>pinPress(ev,id);bar.onkeydown=ev=>pinKey(ev,id);
  close.onpointerdown=ev=>ev?.stopPropagation?.();  // «×» never moves the window
  close.onclick=ev=>{ev?.stopPropagation?.();closePin(id,{focus:true})};
  el.onpointerdown=()=>activatePin(id);  // a press anywhere raises it over the other windows
  $('evmPins').append(el);
  fillPin(id);
  const at=opts.x!=null?{x:opts.x,y:opts.y}:pinPlace(id,opts.section||homeSection(id));
  p.x=Math.round(at.x);p.y=Math.round(at.y);placePin(p);
  activatePin(id,{focus:opts.focus});
  if(opts.save)saveWindow(id);
  syncQuick();
  return p
}
function fillPin(id){  // the window keeps its element and its place; only the content follows the board
  const p=evm.pins[id];if(!p)return;
  const e=entryOf(id);p.missing=!e;p.el.hidden=!e;
  for(const k of Object.keys(evm.fk))if(k.startsWith('pin:'+id+':'))delete evm.fk[k];
  if(!e){p.body.replaceChildren();return}  // an entry that left the catalog: no broken window, it comes back with it
  const name=nameOf(id);
  p.title.textContent=name+' · '+(KIND_LABEL[e.kind]||e.kind);
  p.el.setAttribute('aria-label','Окно модели: '+name);
  p.bar.setAttribute('aria-label','Окно «'+name+'»: перетащите за заголовок или двигайте стрелками');
  fk(p.close,'pin:'+id,'close');p.close.setAttribute('aria-label','Закрыть окно: '+name);
  const scrolled=p.body.scrollTop||0;  // reading the content where the user left it
  p.body.replaceChildren(fullCard(e,homeSection(id),'pin:'+id));
  if(scrolled)p.body.scrollTop=scrolled
}
function pinPlace(id,section){  // beside the column of its card, like the preview; shifted when another window stands there
  const r=rectOf(evm.cheads[section+'|'+id]);
  let at={x:24,y:topLimit()+16};
  if(r&&typeof window!=='undefined'&&window.innerWidth){const s=sidePlace(r,section,Math.min(PIN_W,window.innerWidth-24),()=>0);at={x:s.left,y:s.top}}
  for(let i=0;i<24&&Object.values(evm.pins).some(q=>q.id!==id&&Math.abs(q.x-at.x)<8&&Math.abs(q.y-at.y)<8);i++)at={x:at.x+PIN_STEP,y:at.y+PIN_STEP};
  return at
}
function placePin(p){  // shown inside the window: the title and «×» always reachable; the kept position is not changed
  let left=p.x,top=p.y;
  if(typeof window!=='undefined'&&window.innerWidth){
    const vw=window.innerWidth,vh=window.innerHeight,w=Math.min(PIN_W,vw-24),minTop=topLimit();
    left=Math.min(Math.max(p.x,0),Math.max(0,vw-w));top=Math.min(Math.max(p.y,minTop),Math.max(minTop,vh-48));
    p.el.style.width=w+'px';p.el.style.maxHeight=Math.max(120,vh-top-12)+'px'
  }
  p.el.style.left=Math.round(left)+'px';p.el.style.top=Math.round(top)+'px';
  return {left,top}
}
function activatePin(id,opts={}){
  const p=evm.pins[id];if(!p)return;
  evm.pinOrder=evm.pinOrder.filter(x=>x!==id).concat(id);
  evm.pinOrder.forEach((x,i)=>{const q=evm.pins[x];q.el.style.zIndex=String(i+1);mark(q.el,'active',x===id)});
  if(opts.flash){mark(p.el,'flash',true);clearTimeout(p.flashTimer);p.flashTimer=setTimeout(()=>mark(p.el,'flash',false),700)}
  if(opts.focus)p.el.focus()
}
function closePin(id,opts={}){
  const p=evm.pins[id];if(!p)return;
  const active=document.activeElement,inside=active===p.el||String(active?.getAttribute?.('data-fk')||'').startsWith('pin:'+id+':');
  if(evm.winDrag?.id===id)evm.winDrag=null;
  p.el.remove?.();delete evm.pins[id];evm.pinOrder=evm.pinOrder.filter(x=>x!==id);
  for(const k of Object.keys(evm.fk))if(k.startsWith('pin:'+id+':'))delete evm.fk[k];
  if(evm.hinted===id)evm.hinted=null;
  saveWindow(id,true);syncQuick();
  if(opts.focus&&inside){const home=homeSection(id)+'|'+id;(evm.cquick[p.from]||evm.cquick[home]||evm.copen[home])?.focus()}
}
function syncQuick(){  // «⧉» tells whether the model has its window
  for(const [key,q] of Object.entries(evm.cquick)){
    const id=key.slice(key.indexOf('|')+1),on=!!pinned(id);
    q.setAttribute('aria-expanded',String(on));q.setAttribute('aria-label',(on?'Показать окно модели: ':'Закрепить в отдельном окне: ')+nameOf(id))
  }
}
function pinPress(ev,id){  // the title moves the window; the card buttons inside it never do
  if(ev?.button>0)return;
  const p=evm.pins[id];if(!p)return;
  activatePin(id);
  const at=placePin(p);
  evm.winDrag={id,pointerId:ev?.pointerId,dx:(ev?.clientX||0)-at.left,dy:(ev?.clientY||0)-at.top,x0:p.x,y0:p.y,sx:ev?.clientX||0,sy:ev?.clientY||0,moved:false};
  try{p.bar.setPointerCapture?.(ev.pointerId)}catch(_){}
  ev?.preventDefault?.()  // no text selection while the window moves
}
function pinMove(ev){
  const d=evm.winDrag;if(!d||ev?.pointerId!==d.pointerId)return;
  if(!d.moved&&Math.hypot(ev.clientX-d.sx,ev.clientY-d.sy)<PIN_MOVE_PX)return;  // a click on the title only raises it
  const p=evm.pins[d.id];if(!p)return;
  d.moved=true;mark(p.el,'moving',true);ev.preventDefault?.();
  p.x=Math.round(ev.clientX-d.dx);p.y=Math.round(ev.clientY-d.dy);
  const at=placePin(p);p.x=Math.round(at.left);p.y=Math.round(at.top)  // it stays exactly where it is seen
}
function pinEnd(ev){
  const d=evm.winDrag;if(!d||(ev&&ev.pointerId!==d.pointerId))return;
  evm.winDrag=null;const p=evm.pins[d.id];if(!p)return;
  mark(p.el,'moving',false);
  if(d.moved)saveWindow(d.id)  // saved once, on release, never on every pixel
}
function pinCancel(ev){  // Escape, a lost pointer or window: the window goes back where the move began
  const d=evm.winDrag;if(!d||(ev&&ev.pointerId!=null&&ev.pointerId!==d.pointerId))return;
  evm.winDrag=null;const p=evm.pins[d.id];if(!p)return;
  mark(p.el,'moving',false);p.x=d.x0;p.y=d.y0;placePin(p)
}
function pinKey(ev,id){  // arrows move the focused title (Shift: farther); saved shortly after the last step
  const step=ev.shiftKey?64:16,d={ArrowLeft:[-step,0],ArrowRight:[step,0],ArrowUp:[0,-step],ArrowDown:[0,step]}[ev.key];
  const p=evm.pins[id];if(!d||!p)return;
  ev.preventDefault?.();
  p.x+=d[0];p.y+=d[1];
  const at=placePin(p);p.x=Math.round(at.left);p.y=Math.round(at.top);
  clearTimeout(p.saveTimer);p.saveTimer=setTimeout(()=>saveWindow(id),400)
}
function saveWindow(id,closed){  // one window per request, queued in order; the server merges pages window by window
  const p=evm.pins[id];
  if(!evm.cards?.view||(!closed&&(!p||p.missing)))return evm.layoutQueue;
  const place=closed?null:{x:Math.round(p.x),y:Math.round(p.y)};
  evm.layoutQueue=evm.layoutQueue.then(async()=>{
    try{
      const r=await api('/ultra/model-cards/layout',{method:'POST',body:{connection_id:id,window:place}});
      if(r?.view?.layout&&evm.cards?.view)evm.cards.view={...evm.cards.view,layout:r.view.layout}
    }catch(e){notice('evmError','Расположение окна не сохранено: '+e.message+'. Окно осталось на месте, но после перезагрузки страницы может вернуться на прежнее.')}
  });
  return evm.layoutQueue
}
function restorePins(){  // once per page load: the saved windows come back where they were left, in their stacking order
  const layout=evm.cards?.view?.layout;
  if(evm.layoutLoaded||!layout)return;
  evm.layoutLoaded=true;
  if(layout.state==='CORRUPT')notice('evmError','Сохранённое расположение окон повреждено и не используется. Следующее закрепление начнёт его заново; файл сохранён для разбора.');
  for(const w of layout.windows||[])if(entryOf(w.connection_id)&&!evm.pins[w.connection_id])openPin(w.connection_id,{x:w.x,y:w.y})
}
function placeAllPins(){for(const p of Object.values(evm.pins))placePin(p)}
// Keyboard Alt+arrows remains available for ordering; visible cards use drag and drop.
function moveCard(section,id,delta){
  const ids=sectionIds(section),i=ids.indexOf(id),j=i+delta;
  if(i<0||j<0||j>=ids.length)return;
  [ids[i],ids[j]]=[ids[j],ids[i]];
  saveOrder(section,ids)
}
// Order by mouse. A press on a compact card becomes a drag only after the pointer moves DRAG_PX (a tremor of the hand
// is still a click); the release after a drag never opens the card. A card moves inside its own column or is dropped
// into «Избранное» as a reference (its own column keeps it). Escape, a lost pointer or a release elsewhere cancel.
const DRAG_PX=6,DRAG_TOUCH_PX=10,EDGE_PX=48,LISTS={favorites:'evmFavList',api:'evmApiList',mcp:'evmMcpList',local:'evmLocalList'};
function pressStart(ev,id,section){
  evm.suppressUntil=0;
  if(ev?.button!==0||!evm.cards?.view||evm.window||evm.viewSaving)return;  // the main button only; nothing to order without the board
  evm.press={id,section,x:ev.clientX,y:ev.clientY,pointerId:ev.pointerId,type:ev.pointerType||'mouse',cancelled:false}
}
function pressMove(ev){
  const p=evm.press;if(!p||ev?.pointerId!==p.pointerId)return;
  if(!evm.drag){
    if(typeof ev.buttons==='number'&&!(ev.buttons&1)){evm.press=null;return}  // released where this page could not see it
    if(p.cancelled)return;
    if(Math.hypot(ev.clientX-p.x,ev.clientY-p.y)<(p.type==='mouse'?DRAG_PX:DRAG_TOUCH_PX))return;
    startDrag()
  }
  ev.preventDefault?.();
  dragTo(ev.clientX,ev.clientY)
}
function startDrag(){
  const p=evm.press,key=p.section+'|'+p.id,head=evm.cheads[key],r=rectOf(head);
  clearTimeout(evm.peekTimer);
  if(evm.peek.id)closePeek();  // it stays closed until the drop (ctrlPeek and pinModel wait for the drag)
  const hint=element('span','','ghint');
  evm.drag={id:p.id,section:p.section,target:null,index:null,x:p.x,y:p.y,hint};
  try{head?.setPointerCapture?.(p.pointerId)}catch(_){}  // the drag keeps its pointer even outside the window
  try{window.getSelection?.()?.removeAllRanges?.()}catch(_){}
  mark(evm.ccards[key],'dragging',true);mark($('evmView'),'dragging',true);
  const g=$('evmGhost');g.replaceChildren(element('span',nameOf(p.id),'gname'),hint);
  if(r&&r.width)g.style.width=Math.min(260,Math.round(r.width))+'px';
  g.hidden=false
}
function dragTo(x,y){
  const d=evm.drag;if(!d)return;
  d.x=x;d.y=y;
  // the label follows the pointer at its lower right (or the other side near an edge): it never hides the place pointed at
  const g=$('evmGhost'),gw=g.offsetWidth||0,gh=g.offsetHeight||0,vw=window.innerWidth||0,vh=window.innerHeight||0;
  let gx=x+14,gy=y+16;
  if(vw&&gx+gw>vw-4)gx=Math.max(4,x-14-gw);
  if(vh&&gy+gh>vh-4)gy=Math.max(4,y-16-gh);
  g.style.left=Math.round(gx)+'px';g.style.top=Math.round(gy)+'px';
  const t=dropTarget(x,y);d.target=t?t.section:null;d.index=t?t.index:null;
  showDrop(t);
  autoScroll()
}
function dropTarget(x,y){  // the column under the pointer, if this card may go there, and the place between its cards
  const d=evm.drag;
  for(const section of d.section==='favorites'?['favorites']:[d.section,'favorites']){
    const c=rectOf($(COLUMNS[section]));
    if(!c||x<c.left||x>c.right||y<c.top||y>c.bottom)continue;
    const ids=sectionIds(section).filter(i=>i!==d.id);
    let index=ids.length;
    for(let i=0;i<ids.length;i++){const r=rectOf(evm.ccards[section+'|'+ids[i]]);if(r&&y<r.top+r.height/2){index=i;break}}
    return {section,index,ids}
  }
  return null
}
function showDrop(t){
  const d=evm.drag,line=$('evmDropLine');
  for(const [section,id] of Object.entries(COLUMNS))mark($(id),'drop-target',!!t&&t.section===section);
  mark($('evmView'),'drop-none',!t);
  const adding=!!t&&t.section==='favorites'&&d.section!=='favorites';
  d.hint.textContent=!t?'Сюда нельзя':adding?(favorites().includes(d.id)?'★ Уже в избранном — новое место':'★ Добавить в избранное'):'Переставить сюда';
  if(!t){line.hidden=true;return}
  const list=rectOf($(LISTS[t.section])),rects=t.ids.map(i=>rectOf(evm.ccards[t.section+'|'+i]));
  const y=!t.ids.length?(list?list.top:0):t.index<t.ids.length?(rects[t.index]?.top??0)-5:(rects[t.ids.length-1]?.bottom??0)+2;
  line.hidden=false;line.style.top=Math.round(y)+'px';
  if(list){line.style.left=Math.round(list.left)+'px';line.style.width=Math.round(list.width)+'px'}
}
function autoScroll(){  // near the top or bottom edge the board (or the page on a narrow screen) scrolls by itself
  if(evm.scrollFrame||typeof requestAnimationFrame!=='function')return;
  evm.scrollFrame=requestAnimationFrame(()=>{
    evm.scrollFrame=0;const d=evm.drag;if(!d)return;
    const sc=$('evmView'),own=sc.scrollHeight>sc.clientHeight+1;
    const head=rectOf(typeof document.querySelector==='function'?document.querySelector('header.top'):null);
    const box=own?rectOf(sc):{top:head?head.bottom:0,bottom:window.innerHeight};if(!box)return;
    const v=d.y<box.top+EDGE_PX?-Math.ceil((box.top+EDGE_PX-d.y)/4):d.y>box.bottom-EDGE_PX?Math.ceil((d.y-box.bottom+EDGE_PX)/4):0;
    if(!v)return;
    const before=own?sc.scrollTop:window.scrollY;
    if(own)sc.scrollTop+=Math.max(-24,Math.min(24,v));else window.scrollBy(0,Math.max(-24,Math.min(24,v)));
    if((own?sc.scrollTop:window.scrollY)!==before)dragTo(d.x,d.y)  // the cards moved under the pointer: find the place again
  })
}
function pressEnd(ev){
  const p=evm.press;if(!p||(ev&&ev.pointerId!==p.pointerId))return;
  if(evm.drag&&typeof ev?.clientX==='number')dragTo(ev.clientX,ev.clientY);  // the place where the button was released
  evm.press=null;
  if(!evm.drag){if(p.cancelled)evm.suppressUntil=Date.now()+400;return}
  const d=evm.drag;endDrag();evm.suppressUntil=Date.now()+400;  // the click that follows this release is not a click
  if(d.target)dropAt(d)
}
function pressCancel(ev){
  const p=evm.press;if(!p||(ev&&ev.pointerId!==p.pointerId))return;
  evm.press=null;
  if(evm.drag){endDrag();evm.suppressUntil=Date.now()+400}
}
function cancelDrag(){  // Escape or a lost window: the card goes back, nothing is saved
  if(!evm.drag)return;
  endDrag();evm.suppressUntil=Date.now()+400;
  if(evm.press)evm.press.cancelled=true  // the button is still down: no new drag and no click until it is released
}
function endDrag(){
  evm.drag=null;
  if(evm.scrollFrame&&typeof cancelAnimationFrame==='function')cancelAnimationFrame(evm.scrollFrame);
  evm.scrollFrame=0;
  for(const el of Object.values(evm.ccards))mark(el,'dragging',false);
  for(const id of Object.values(COLUMNS))mark($(id),'drop-target',false);
  mark($('evmView'),'dragging',false);mark($('evmView'),'drop-none',false);
  $('evmGhost').hidden=true;$('evmGhost').replaceChildren();$('evmDropLine').hidden=true;
  if(evm.peek.id)positionPeek()
}
function dropAt(d){
  const before=sectionIds(d.target),order=before.filter(i=>i!==d.id),adding=d.target==='favorites'&&d.section!=='favorites';
  order.splice(Math.min(d.index,order.length),0,d.id);
  if(order.join(' ')===before.join(' ')){if(adding)evmSay('Уже в избранном: '+nameOf(d.id));return}  // the same place: nothing to save
  saveOrder(d.target,order,adding?(before.includes(d.id)?'Уже было в избранном — место изменено: ':'Добавлено в избранное: ')+nameOf(d.id):null)
}
// EVM messages are toasts over the bottom of the window (.evm-toasts), outside the flow: showing one never moves the
// board under the pointer. A success message goes away by itself; an error stays until the next action.
const EVM_SAY_MS=6000;
function evmSay(message){clearTimeout(evm.noticeTimer);notice('evmNotice',message);if(message)evm.noticeTimer=setTimeout(()=>notice('evmNotice',''),EVM_SAY_MS)}
function toggleFavorite(id){
  const on=favorites().includes(id);
  saveOrder('favorites',on?favorites().filter(x=>x!==id):favorites().concat(id),(on?'Убрано из избранного: ':'Добавлено в избранное: ')+nameOf(id))
}
async function saveOrder(section,order,done){
  if(!evm.cards?.view||evm.viewSaving)return;
  evm.viewSaving=true;notice('evmError','');notice('evmNotice','');
  const before=evm.cards.view;
  evm.cards.view={...before,sections:{...before.sections,[section]:order}};renderEvm();  // shown at once; the server decides
  try{
    const r=await api('/ultra/model-cards/view',{method:'POST',body:{base_revision:before.revision,section,order}});
    if(!r?.view?.sections)throw new Error('Сервер не подтвердил порядок');
    evm.viewSaving=false;evm.cards.view=r.view;renderEvm();
    if(done)evmSay(done)
  }catch(e){
    evm.viewSaving=false;evm.cards.view=before;
    await loadEvm();
    notice('evmError',(e.code==='settings_revision_conflict'?'Порядок или список уже изменились в другом окне. Показано сохранённое состояние — повторите действие. ':'Порядок не сохранён. ')+e.message)
  }
}
async function loadEvm(){
  const epoch=++evm.epoch;$('evmRefresh').disabled=true;notice('evmError','');text('evmState','Загружаем реестр…');
  const [catalog,cards,capability]=await Promise.allSettled([api('/ultra/connections'),api('/ultra/model-cards'),api('/ui/ultra-chat/capability')]);
  if(epoch!==evm.epoch)return;
  try{
    if(catalog.status==='rejected')throw catalog.reason;
    if(!validEvm(catalog.value))throw new Error('Некорректный ответ сервера о подключениях');
    evm.data=catalog.value;
    evm.live=capability.status==='fulfilled'?capability.value?.turn_test||null:null;
    if(cards.status==='fulfilled'&&validCards(cards.value)){evm.cards=cards.value;evm.cardsError=null}
    else{evm.cards=null;evm.cardsError=cards.status==='rejected'?cards.reason.message:'некорректный ответ сервера о карточках'}
    renderEvm();
    const damaged=[evm.cards?.settings.state==='CORRUPT'?'настройки карточек':null,evm.cards?.checks?.state==='CORRUPT'?'сведения о проверках API':null].filter(Boolean);
    if(evm.cardsError)notice('evmError','Карточки моделей недоступны: '+evm.cardsError);
    if(!EXTERNAL_MODEL)restorePins();
    if(damaged.length)notice('evmError','Повреждены '+damaged.join(' и ')+'. Файл сохранён для разбора; следующее сохранение начнёт запись заново, статусы до новой проверки — ×.');
    if(evm.window)fillWindow()
  }catch(e){
    notice('evmError','Не удалось получить подключения: '+e.message);text('evmState','Список не обновлён')
  }finally{$('evmRefresh').disabled=false}
}
const GIGACHAT_CONNECT_PROMPT='Подключить провайдера GigaChat на срок действующей сессии (до 24 часов)? Это не включает и не проверяет отдельные модели. Каждая отправка требует вашего действия. Предпочтительный максимум ответа задаётся в настройках чата (до 20 000 токенов); технический предел запроса 4096 байт. API может быть платным. Автоматических повторов нет.';
async function evmLiveControl(start){
  const live=evm.live;
  if(stage5Offline||evm.liveBusy||chatTurn.liveBusy||live?.mode!=='ORDINARY'||live.execution_mode==='PROTOCOL_TEST'||
      (start?live.real_available:!live.real_available))return;
  if(start&&!window.confirm(GIGACHAT_CONNECT_PROMPT))return;
  evm.liveBusy=true;evm.liveAction=start?'start':'stop';evm.liveFailure=null;chatTurn.liveBusy=true;renderEvm();renderTurnComposer();
  let committed=false,error='';
  try{
    if(start&&!live.personal_workspace_id){
      const personal=await chatPost('/ultra/chat/personal',{});
      if(typeof personal?.wa_workspace_id!=='string')throw Error('Личная история не подтверждена');
    }
    const result=await chatPost(start?'/ultra/chat/live/start':'/ultra/chat/live/stop',
      start?{confirmation:'GIGACHAT 6'}:{});
    if(result?.state!==(start?'ACTIVE':'INACTIVE'))throw Error('Состояние подключения не подтверждено');
    committed=true;
  }catch(e){error=e.message||e.code||'проверьте состояние подключения'}
  finally{
    evm.liveBusy=false;evm.liveAction=null;evm.liveFailure=committed?null:(start?'connect':'disconnect');chatTurn.liveBusy=false;
    await loadEvm();
    if(chat.started){try{await loadChatAccess();await loadChatWorkspaces()}catch(_){/* EVM readback stays authoritative */}}
    renderEvm();renderTurnComposer();
  }
  if(committed)evmSay(start?'GigaChat подключён. В Ultra Chat доступны включённые модели.':'GigaChat отключён. История сохранена.');
  else notice('evmError','Состояние не изменено или не подтверждено: '+error+'. Проверьте его перед повтором.');
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
function openWindow(kind,id,tab,from){
  const c=cardData(id);if(!c)return;
  evm.returnTo={key:from||null,id:c.connection_id};  // the control that opened the window gets the keyboard back
  if(evm.peek.id&&!evm.promote)closePeek();  // pressed inside the preview: it becomes a pinned window after this click
  evm.window={kind,id};evm.setError='';
  if(tab)evm.tab=tab;
  fillWindow();
  if(tab==='model')$('evmSetDescription').focus();  // «Изменить описание»: straight into the field
  else $(kind==='settings'?'evmSetTitle':'evmCheckTitle').focus()
}
function closeWindow(){
  const w=evm.window;if(!w)return;
  evm.window=null;$('evmSettingsWindow').hidden=true;$('evmCheckWindow').hidden=true;
  renderEvm();
  const back=evm.returnTo;evm.returnTo=null;
  if(back&&!restoreFocus(back.key))evm.copen[Object.keys(evm.copen).find(k=>k.endsWith('|'+back.id))]?.focus()
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
    evmSay('Настройки сохранены: '+c.display_name)
  }catch(e){
    evm.saving=false;
    evm.setError=(e.code==='settings_revision_conflict'?'Настройки уже изменены в другом окне. «Отменить изменения» загрузит сохранённые; затем повторите правку. ':'Настройки не сохранены. ')+e.message;
    if(evm.window?.kind==='settings'){notice('evmSetError',evm.setError);$('evmSetSave').disabled=false}
  }
}
function fillCheck(){
  const c=cardData(evm.window.id),live=evm.cards.live_check;
  const disconnected=evm.live?.mode==='ORDINARY'&&!evm.live.real_available;
  const canCheck=c.enabled!==false&&evm.live?.real_available===true&&live.authorized===true&&!evm.liveBusy;
  text('evmCheckName','Проверка API — '+c.display_name);$('evmCheckDot').replaceChildren(apiDot(c.api));
  text('evmCheckLast','Последний успешный ответ: '+(c.api.last_success_at?fmtTime(c.api.last_success_at)+(c.api.last_success_source==='chat'?' (обычный запрос)':''):'отсутствует')+' · '+apiText(c.api));
  const out=evm.outputs[c.model_id]||(c.last_output?{kind:c.last_output.kind==='reply'?'reply':c.last_output.kind==='unknown'?'info':'error',text:c.last_output.text+'\n('+fmtTime(c.last_output.at)+')'}:
    {kind:'info',text:c.enabled===false?'Модель отключена в EVM. Включите её перед проверкой.':disconnected?
      'Провайдер не подключён. Подключите GigaChat в EVM, затем отдельно подтвердите тестовый запрос.':
      !canCheck?'Проверка сейчас недоступна: '+(live.reason||'нет подтверждённого допуска к модели.'):
      'Нажмите «Отправить тестовое сообщение», чтобы проверить подключение и увидеть ответ модели.'});
  text('evmCheckOutput',out.text);$('evmCheckOutput').className='output '+out.kind;
  text('evmCheckNote','Тестовое сообщение: «'+evm.cards.test_message+'». '+(canCheck?
    'Настоящий запрос может тарифицироваться; перед отправкой потребуется отдельное подтверждение.':
    c.enabled===false?'Модель отключена; запрос не отправляется.':disconnected?
    'Провайдер не подключён; запрос не отправляется.':'Отправка сейчас недоступна; запрос не отправляется.'));
  $('evmCheckConnect').hidden=!disconnected||c.provider_id!=='gigachat';
  $('evmCheckConnect').disabled=evm.liveBusy||evm.checking;
  $('evmCheckSend').disabled=evm.checking||!canCheck
}
function checkOutput(r){
  if(r?.outcome==='LIVE_CHECK_NOT_AUTHORIZED')return {kind:'info',text:'Сообщение не отправлялось. '+r.message+' Статус API не изменён.'};
  if(r?.outcome==='SIMULATED')return {kind:'info',text:'ИМИТАЦИЯ — настоящий запрос не отправлялся, статус API не изменён.\n'+(r.text||'')};
  if(r?.outcome==='CONFIRMED')return {kind:'reply',text:String(r.text||'')};
  if(r?.outcome==='FAILED')return {kind:'error',text:String(r.text||'Проверка завершилась отказом')};
  if(r?.outcome==='UNKNOWN')return {kind:'info',text:'Исход проверки неизвестен. Автоматической повторной отправки нет. '+String(r.text||'')};
  return {kind:'info',text:'Результат проверки не подтверждён; обновите состояние перед новой попыткой.'}
}
async function sendCheck(){
  const c=evm.window?.kind==='check'?cardData(evm.window.id):null;if(!c||evm.checking)return;
  if(c.enabled===false||evm.live?.real_available!==true||evm.cards.live_check?.authorized!==true){
    evm.outputs[c.model_id]={kind:'info',text:c.enabled===false?'Модель отключена в EVM. Запрос не отправлялся.':
      'Провайдер не подключён или допуск к проверке отсутствует. Запрос не отправлялся.'};fillCheck();return
  }
  if(!window.confirm('Отправить одно тестовое сообщение модели '+c.display_name+' через GigaChat? Запрос может тарифицироваться. Автоматического повтора нет.'))return;
  const id=c.model_id;evm.checking=true;evm.outputs[id]={kind:'info',text:'Проверяем…'};fillCheck();
  try{
    if(!chatEdit.token)await loadChatWriteAccess();
    evm.outputs[id]=checkOutput(await api('/ultra/model-cards/'+encodeURIComponent(id)+'/check',
      {method:'POST',headers:{[CHAT_WRITE_HEADER]:chatEdit.token},body:{},timeoutMs:130000}))
  }
  catch(e){evm.outputs[id]={kind:'info',text:e.httpStatus&&e.httpStatus<500?
    'Проверка не выполнена: '+(e.code||e.message):'Исход проверки неизвестен. Автоматического повтора нет. '+(e.code||e.message)}}
  evm.checking=false;
  await loadEvm()  // the indicator always comes from the server, never from this answer
}
$('viewEvm').onclick=()=>showView('evm');
$('viewOperator').onclick=()=>showView('operator');
$('evmRefresh').onclick=()=>loadEvm();
$('evmPeek').onmouseenter=()=>clearTimeout(evm.peekTimer);
$('evmPeek').onmouseleave=()=>peekLeave();
$('evmPeek').onpointerdown=ev=>previewPress(ev);  // a press inside the preview pins it where it stands
$('evmView').onscroll=()=>{if(evm.peek.id)positionPeek()};
for(const [key,[tab]] of Object.entries(EVM_TABS))$(tab).onclick=()=>selectTab(key);
$('evmSetProfile').onchange=editDraft;
for(const id of ['evmSetParams','evmSetDescription','evmSetTimeout','evmSetDiagLimit','evmSetFreshness'])$(id).oninput=editDraft;
$('evmSetReset').onclick=()=>{const w=evm.window;if(w?.kind!=='settings')return;delete evm.drafts[w.id];evm.setError='';fillSettings()};
$('evmSetSave').onclick=()=>saveSettings();
$('evmSetClose').onclick=()=>closeWindow();
$('evmCheckClose').onclick=()=>closeWindow();
$('evmCheckConnect').onclick=()=>evmLiveControl(true);
$('evmCheckSend').onclick=()=>sendCheck();
$('evmLiveStart').onclick=()=>evmLiveControl(true);
$('evmLiveStop').onclick=()=>evmLiveControl(false);
for(const id of ['evmSettingsWindow','evmCheckWindow'])$(id).onclick=e=>{if(e?.target===$(id))closeWindow()};
function escapeKey(e){
  if(e?.key!=='Escape')return;
  if(picker.open){closePicker(true);return}
  if(evm.drag){cancelDrag();return}
  if(evm.winDrag){pinCancel();return}
  if(evm.window){closeWindow();return}
  if(evm.peek.id)closePeek({focus:true})  // the preview only: pinned windows close with their own «×»
}
function evmKeyDown(e){
  if(e?.key==='Control'){evm.ctrl=true;ctrlPeek();return}  // Ctrl pressed over a card shows its side panel
  escapeKey(e)
}
function evmKeyUp(e){if(e?.key==='Control'){evm.ctrl=false;if(evm.peek.id&&!evm.promote)closePeek()}}  // pinned windows stay
function evmBlur(){evm.ctrl=false;cancelDrag();pinCancel();if(evm.peek.id&&!evm.promote)closePeek()}  // keys and buttons are lost with the window
if(typeof window!=='undefined'&&window.addEventListener){
  window.addEventListener('keydown',evmKeyDown);
  window.addEventListener('keyup',evmKeyUp);
  window.addEventListener('blur',evmBlur);
  window.addEventListener('pointermove',pressMove,{passive:false});
  window.addEventListener('pointermove',pinMove,{passive:false});
  window.addEventListener('pointerup',pressEnd);
  window.addEventListener('pointerup',pinEnd);
  window.addEventListener('pointerup',previewRelease);
  window.addEventListener('pointercancel',pressCancel);
  window.addEventListener('pointercancel',pinCancel);
  window.addEventListener('resize',()=>{if(evm.peek.id)positionPeek();placeAllPins()});
  window.addEventListener('scroll',()=>{if(evm.peek.id)positionPeek()},true)  // narrow screens scroll the page, not the board
}
// Ultra Chat (programme No.37 stage 1): saved dialogues of the shared Ultra core, read-only. The read token
// lives only in this object and goes only to /ultra/chat/* in its own header; nothing here writes anything.
const CHAT_TOKEN_HEADER='X-WebAlarm-Ultra-Chat-Token',CHAT_PAGE=50;
const stage5Offline=document.body?.getAttribute?.('data-stage5-offline')==='true';
const chat={epoch:0,historyRevision:0,started:false,token:null,workspaces:[],workspace:null,expanded:null,chats:[],chat:null,messages:[],page:null,olderBusy:false,creatingWorkspace:false,renamingWorkspace:false};
const chatTurn={available:false,busy:false,state:null,models:[],model:null,revision:0,checkRevision:0,checking:0,checkCount:0,dismissed:new Map()};
const modelChat=()=>stage5Offline||chatTurn.ordinary===true;
function turnScope(){return chat.workspace&&chat.chat?(chatTurn.ordinary?'webAlarm.ordinaryTurn.':'webAlarm.testTurn.')+chat.workspace+'.'+chat.chat:null}
function turnPending(){try{return JSON.parse(localStorage.getItem(turnScope())||'null')}catch(_){return null}}
function testChatSelection(){try{return JSON.parse(localStorage.getItem(chatTurn.ordinary?'webAlarm.ordinaryChatSelection':'webAlarm.testChatSelection')||'null')}catch(_){return null}}
function turnBase(){return '/ultra/chat/workspaces/'+encodeURIComponent(chat.workspace)+'/chats/'+encodeURIComponent(chat.chat)+'/turns'}
function renderChatUsage(summary){
  const target=$('chatUsage');target.hidden=!modelChat()||!chat.workspace||!chat.chat;
  const fields=[['prompt_tokens','Вход'],['completion_tokens','Выход'],['reasoning_tokens','Рассуждения (внутри выхода)'],['total_tokens','Всего']];
  const count=n=>Number.isSafeInteger(n)&&n>=0?String(n):'UNKNOWN';
  const prefix=summary?.synthetic===false?'Токены':'TEST · синтетические токены';
  if(!summary?.available){target.textContent=prefix+': UNKNOWN';return}
  if(!summary.attempts){target.textContent=prefix+': попыток ещё нет';return}
  const last=fields.map(([k,label])=>label+': '+count(summary.last?.usage?.[k])).join(' · ');
  let total=fields.map(([k,label])=>label+': '+(summary.missing?.[k]===summary.attempts?'UNKNOWN':
    (summary.missing?.[k]?'≥ ':'')+count(summary.known?.[k]))).join(' · ');
  if(summary.cached_input){
    const cache=summary.cached_input;
    total+=' · Кэш входа: '+(cache.missing===summary.attempts?'UNKNOWN':(cache.missing?'≥ ':'')+count(cache.known));
    total+=' · Полный вход: '+(cache.full_input_missing===summary.attempts?'UNKNOWN':(cache.full_input_missing?'≥ ':'')+count(cache.full_input_known));
  }
  target.textContent=prefix+'. Последняя попытка — '+last+'. Чат: известный расход — '+total+
    (summary.complete?'.':'. Общий расход известен не полностью.');
}
let chatPreferencesRevision=0,chatPreferencesLoadedFor=null,ordinaryModelRevision=0;
function preferencesBase(){return turnBase().replace(/\/turns$/,'/settings')}
function preferencesBusy(value){for(const id of ['chatContextTokens','chatAnswerTokens','chatAnswerExtended','chatPreferencesSave'])$(id).disabled=value}
async function loadChatPreferences(){
  $('chatPreferences').hidden=!chatTurn.preferencesEnabled||!chat.workspace||!chat.chat;
  if($('chatPreferences').hidden)return;
  const epoch=chat.epoch,revision=++chatPreferencesRevision;preferencesBusy(true);
  try{
    const result=await chatGet(preferencesBase());
    if(epoch!==chat.epoch||revision!==chatPreferencesRevision)return;
    $('chatContextTokens').value=String(result.settings.compression_threshold_tokens);
    $('chatAnswerTokens').value=String(result.settings.answer_tokens);
    chatPreferencesLoadedFor=turnScope();
    text('chatPreferencesStatus','Предпочтения загружены; к провайдеру не применены.');
  }catch(_){if(epoch===chat.epoch&&revision===chatPreferencesRevision)text('chatPreferencesStatus','Настройки не загружены. Сохранение недоступно.');return}
  finally{if(epoch===chat.epoch&&revision===chatPreferencesRevision)preferencesBusy(true)}
  if(epoch===chat.epoch&&revision===chatPreferencesRevision)preferencesBusy(false);
}
async function saveChatPreferences(){
  if(!chatTurn.preferencesEnabled||!chat.workspace||!chat.chat||$('chatPreferencesSave').disabled)return;
  const values=[$('chatContextTokens').value,$('chatAnswerTokens').value];
  if(values.some(s=>!/^\d+$/.test(s)||!Number.isSafeInteger(Number(s))||Number(s)<=0)){
    text('chatPreferencesStatus','Введите положительные целые числа.');return
  }
  const epoch=chat.epoch,revision=++chatPreferencesRevision;preferencesBusy(true);
  try{
    await chatPost(preferencesBase(),{compression_threshold_tokens:Number(values[0]),answer_tokens:Number(values[1])});
    if(epoch===chat.epoch&&revision===chatPreferencesRevision)text('chatPreferencesStatus','Сохранено для этого чата. К провайдеру не применено.');
  }catch(_){if(epoch===chat.epoch&&revision===chatPreferencesRevision)text('chatPreferencesStatus','Сохранение не подтверждено. Проверьте настройки повторным открытием.');}
  finally{if(epoch===chat.epoch&&revision===chatPreferencesRevision)preferencesBusy(false)}
}
function renderTurnComposer(){
  const liveVisible=chatTurn.ordinary&&!stage5Offline;
  const enabled=chatTurn.available&&!!chat.workspace&&!!chat.chat;
  const pending=turnPending();
  $('chatInput').disabled=!enabled||chatTurn.busy;$('chatSend').disabled=!enabled||chatTurn.busy;
  $('chatTurnControls').hidden=!enabled;
  $('chatTurnCheck').disabled=!enabled||!!chatTurn.checking;
  $('chatTurnCancel').disabled=!enabled||!pending||(modelChat()&&!!chatTurn.state&&!['READY','ATTEMPTING'].includes(chatTurn.state));
  $('chatModelPick').disabled=modelChat()?!chatTurn.models.length:chatTurn.available;
  if(chatTurn.testModelPreferences)$('chatModelPick').disabled=chatTurn.testModelBusy||!chat.workspace||!chat.chat||!chatTurn.models.length;
  if(modelChat()){
    const selected=chatTurn.models.find(m=>m.model_id===chatTurn.model);
    const pendingSelected=typeof pending?.model==='string'?chatTurn.models.find(m=>m.model_id===pending.model):null;
    $('chatInput').readOnly=typeof pending?.text==='string';
    $('chatSend').disabled=!enabled||chatTurn.busy||!selected;
    $('chatInput').placeholder='Сообщение TEST-имитатору';
    $('chatTurnNew').disabled=chatTurn.busy;
    text('chatComposerNote',pending?'TEST · повтор использует сохранённый ключ и модель исходного запроса.':'TEST · локальный имитатор. Enter — отправить, Shift+Enter — новая строка.');
    text('chatModel',selected?'TEST · '+selected.display_name:'TEST · выберите модель');
    text('chatModelPick',(selected?.display_name||'Выбрать модель')+' ▾');
    text('chatSidebarNote','TEST · история хранится общим ядром Ultra.');
    if(chatTurn.ordinary){
      text('chatModel',selected?'Модель: '+selected.display_name:'Выберите модель');
      $('chatInput').placeholder=chatTurn.available?'Сообщение TEST-имитатору':'Отправка GigaChat пока закрыта';
      text('chatComposerNote',chatTurn.available?'TEST · проверка штатного чата без обращения к GigaChat.':'GigaChat не подключён в этом процессе. Подключите провайдера через EVM; если подключение отклонено, проверьте указанную там причину. История и настройки доступны.');
      text('chatSidebarNote','История хранится общим ядром Ultra.');
      if(chatTurn.model&&!selected){
        $('chatSend').disabled=true;
        text('chatModel','Модель отключена в EVM: '+chatTurn.model);
        text('chatComposerNote','Выбранная модель отключена или больше не поддерживается. История сохранена; включите модель в EVM либо выберите другую.');
      }
      if(chatTurn.executionMode==='REAL'){
        $('chatInput').placeholder='Сообщение GigaChat';
        text('chatComposerNote','GigaChat · ограниченный серверный допуск. Enter — отправить, Shift+Enter — новая строка.');
      }
      if(selected?.is_local){
        $('chatInput').placeholder='Сообщение локальной модели Colibri';
        text('chatComposerNote','Colibri · изолированный OFFLINE Bridge. История хранится общим ядром.');
      }
      if(selected?.availability==='UNAVAILABLE'){
        $('chatSend').disabled=true;
        text('chatComposerNote','Эта модель недоступна в подтверждённом каталоге аккаунта. Выберите другую модель.');
      }
      if(chatTurn.executionMode==='REAL'){
        const effective=pendingSelected||selected;
        if(effective?.availability!=='AVAILABLE'){
          $('chatSend').disabled=true;
          text('chatComposerNote',effective?.availability==='NOT_APPROVED'?
            'Эта модель есть в каталоге, но пока не разрешена для текущего сеанса.':
            effective?.availability==='UNAVAILABLE'?
            'Эта модель недоступна в подтверждённом каталоге аккаунта. Выберите другую модель.':
            chatTurn.model&&!effective?'Выбранная модель отключена в EVM. История сохранена; выберите другую модель.':
            'Выбранная модель не подтверждена для этого LIVE-сеанса.');
        }
        if(pending?.model&&pending.model!==chatTurn.model){
          $('chatSend').disabled=true;
          text('chatComposerNote','Сохранённый незавершённый запрос привязан к другой модели. Проверьте его состояние.');
        }
        // The same connected provider may serve any registered and audited
        // Workspace. Server-side scope and per-Workspace Turn/ledger checks
        // remain authoritative; never treat the personal root as a UI allowlist.
      }
    }
  }
  else if(chatTurn.available){text('chatComposerNote','TEST · локальный имитатор. Выбранная модель не вызывается. Enter — отправить, Shift+Enter — новая строка.');$('chatInput').placeholder='Сообщение TEST-имитатору';text('chatModel','TEST · локальный имитатор');text('chatModelPick','TEST · без LLM');text('chatSidebarNote','TEST: ответы создаёт локальный имитатор. История хранится общим ядром Ultra.')}
  else{text('chatComposerNote','Отправка сообщений появится на следующем этапе. Сейчас Ultra Chat читает сохранённую историю, создаёт и переименовывает диалоги.')}
  $('chatSend').textContent=turnPending()?'Повторить / восстановить':'Отправить';
  $('chatSend').setAttribute('data-recover',String(Boolean(turnPending())));$('chatSend').title=turnPending()?'Повторить / восстановить':'Отправить (Enter)';
  if(chatTurn.testModelPreferences){
    const blocked=chatTurn.testModelBusy||(!chatTurn.testModelLoaded&&!pending?.model);
    $('chatInput').disabled=$('chatInput').disabled||blocked;
    $('chatSend').disabled=!enabled||chatTurn.busy||blocked||!(pending?.model||chatTurn.model);
  }
}
let colibriProgressTicket=0,colibriProgressTimer=null;
function clearColibriProgressTimer(){
  colibriProgressTicket++;
  if(colibriProgressTimer!==null)clearTimeout(colibriProgressTimer);
  colibriProgressTimer=null;
}
function renderColibriProgress(result){
  const panel=$('chatColibriProgress');if(!panel)return;
  const reasoning=result?.execution_mode==='COLIBRI_OFFLINE'&&typeof result.reasoning==='string'?result.reasoning:'';
  const answer=result?.execution_mode==='COLIBRI_OFFLINE'&&result.state!=='SUCCEEDED'&&typeof result.partial_answer==='string'?result.partial_answer:'';
  panel.hidden=!reasoning&&!answer;
  text('chatColibriReasoning',reasoning);text('chatColibriPartial',answer);
  $('chatColibriPartial').hidden=!answer;$('chatColibriPartialLabel').hidden=!answer;
}
function pollColibriProgress(base,scope,key){
  clearColibriProgressTimer();
  const ticket=colibriProgressTicket,epoch=chat.epoch;
  const current=()=>ticket===colibriProgressTicket&&epoch===chat.epoch&&scope===turnScope()&&turnPending()?.key===key;
  const next=async()=>{
    if(!current())return;
    try{
      const result=await chatGet(base+'/by-key/'+encodeURIComponent(key));
      if(!current())return;
      if(result?.execution_mode==='COLIBRI_OFFLINE'&&result.idempotency_key===key){
        if(['ACCEPTING','READY','ATTEMPTING'].includes(result.state)){
          chatTurn.state=result.state;renderColibriProgress(result);renderTurnComposer();
          text('chatTurnStatus','Colibri обрабатывает запрос…');
        }else if(!chatTurn.busy){
          showTurn(result);await loadChatHistory(false);return;
        }
      }
    }catch(_){/* A read failure is not an instruction to repeat inference. */}
    if(current())colibriProgressTimer=setTimeout(next,750);
  };
  colibriProgressTimer=setTimeout(next,400);
}
function showTurn(result){
  if(!result||result.mode!==(chatTurn.ordinary?'ORDINARY':modelChat()?'TEST_OFFLINE':'TEST')||typeof result.turn_id!=='string'||!['ACCEPTING','READY','ATTEMPTING','SUCCEEDED','FAILED','CANCELLED','UNKNOWN'].includes(result.state))throw Error('Некорректный Turn');
  chatTurn.revision++;
  chatTurn.state=result.state;
  renderColibriProgress(result);
  if(!['ACCEPTING','READY','ATTEMPTING'].includes(result.state))clearColibriProgressTimer();
  else if(result.execution_mode==='COLIBRI_OFFLINE'&&!chatTurn.busy&&turnPending()?.key)
    pollColibriProgress(turnBase(),turnScope(),turnPending().key);
  const labels={ACCEPTING:'Приём не завершён. Для продолжения нужен исходный текст.',READY:'Принято. Ожидает явного продолжения.',ATTEMPTING:'Выполняется: TEST-имитатор обрабатывает запрос…',SUCCEEDED:'TEST: ответ сохранён.',FAILED:'TEST: выполнение завершилось ошибкой.',CANCELLED:'Отменено до выполнения.',UNKNOWN:'Исход неизвестен. Повтор ключа проверит сохранённые факты; повторного исполнения нет.'};
  if(result.execution_mode==='COLIBRI_OFFLINE')Object.assign(labels,{ATTEMPTING:'Colibri обрабатывает запрос…',SUCCEEDED:'Ответ Colibri сохранён (OFFLINE).',FAILED:'Запрос Colibri завершился ошибкой.'});
  if(result.execution_mode==='REAL')Object.assign(labels,{ATTEMPTING:'GigaChat обрабатывает запрос…',SUCCEEDED:'Ответ GigaChat сохранён.',FAILED:'Запрос GigaChat завершился ошибкой.'});
  const detail=modelChat()?' · '+result.references.model_ref+(result.usage?.total_tokens==null?'':' · usage '+result.usage.total_tokens):'';
  text('chatTurnStatus',labels[result.state]+detail+(typeof result.diagnostic_code==='string'?' · '+result.diagnostic_code:'')+
    (result.evm_status_sync==='UNAVAILABLE'?' · Статус EVM не обновлён; проверьте подключение.':''));
  $('chatTurnNew').hidden=result.state!=='UNKNOWN';
  $('chatTurnCancel').disabled=!['READY','ATTEMPTING'].includes(result.state);
  if(['SUCCEEDED','FAILED','CANCELLED'].includes(result.state)){
    const hadPending=!!turnPending();
    localStorage.removeItem(turnScope());
    if(modelChat()?hadPending:result.state==='SUCCEEDED')$('chatInput').value=''
  }
  renderTurnComposer();
}
async function checkTurn(manual=false){
  renderTurnComposer();let pending=turnPending();if(!chatTurn.available||!turnScope()||(!pending&&!modelChat()))return;
  const epoch=chat.epoch,revision=chatTurn.revision,ticket=++chatTurn.checkRevision;
  const count=manual?++chatTurn.checkCount:0;
  chatTurn.checking=ticket;
  if(manual)text('chatTurnCheckResult','Проверяем состояние запроса…');
  renderTurnComposer();
  const current=()=>epoch===chat.epoch&&ticket===chatTurn.checkRevision;
  const checked=()=>{if(manual&&current())text('chatTurnCheckResult','Проверка №'+count+' завершена. '+(revision===chatTurn.revision?'':'Показано актуальное состояние запроса.'))};
  try{
    const found=pending?{turn:await chatGet(turnBase()+'/by-key/'+encodeURIComponent(pending.key))}:await chatGet(turnBase()+'/latest');
    if(!current())return;
    if(revision!==chatTurn.revision){checked();return}
    if(!found.turn){if(manual)text('chatTurnCheckResult','В этом чате ещё нет отправленных запросов.');return}
    const result=found.turn;
    if(modelChat()&&!pending&&!['SUCCEEDED','FAILED','CANCELLED'].includes(result.state)){
      if(chatTurn.dismissed.get(turnScope())===result.idempotency_key){checked();return}
      pending={key:result.idempotency_key,model:result.references.model_ref,text:found.text};
      localStorage.setItem(turnScope(),JSON.stringify(pending));
    }
    if(modelChat()&&typeof pending?.text==='string')$('chatInput').value=pending.text;
    showTurn(result);await loadChatHistory(false);checked()
  }
  catch(e){if(current()){
    if(revision!==chatTurn.revision){checked();return}
    text('chatTurnCheckResult',e.httpStatus===404?'Запрос ещё не найден. Исходный ключ сохранён; проверьте состояние перед повтором.':'Не удалось проверить состояние запроса. Автоматического повтора отправки нет.')
  }}
  finally{if(current()){chatTurn.checking=0;renderTurnComposer()}}
}
async function startGigaChat(){
  if(!chatTurn.ordinary||chatTurn.liveBusy||chat.workspace!==chatTurn.personalWorkspaceId)return;
  if(!window.confirm(GIGACHAT_CONNECT_PROMPT))return;
  chatTurn.liveBusy=true;renderTurnComposer();
  try{
    await chatPost('/ultra/chat/live/start',{confirmation:'GIGACHAT 6'});
    await loadChatAccess();await loadChatModel();
    notice('chatNotice','GigaChat подключён. Выбери модель и отправь короткое сообщение.');
  }catch(e){notice('chatNotice','Подключение не выполнено: '+(e.message||e.code||'проверь существующие настройки доступа'));}
  finally{chatTurn.liveBusy=false;renderTurnComposer()}
}
async function stopGigaChat(){
  if(!chatTurn.ordinary||chatTurn.liveBusy)return;
  chatTurn.liveBusy=true;renderTurnComposer();
  try{
    await chatPost('/ultra/chat/live/stop',{});
    await loadChatAccess();
    notice('chatNotice','GigaChat отключён. История сохранена.');
  }catch(e){notice('chatNotice','Отключение не подтверждено: '+(e.code||'проверь состояние запроса'));}
  finally{chatTurn.liveBusy=false;renderTurnComposer()}
}
async function sendTurn(){
  if(chatTurn.testModelPreferences&&(chatTurn.testModelBusy||(!chatTurn.testModelLoaded&&!turnPending()?.model)))return;
  if(!chatTurn.available||chatTurn.busy||!chat.workspace||!chat.chat||!$('chatInput').value.trim()||(modelChat()&&!chatTurn.model&&!(chatTurn.testModelPreferences&&turnPending()?.model)))return;
  if(chatTurn.ordinary&&chatTurn.executionMode==='REAL'&&
      (chatTurn.models.find(m=>m.model_id===chatTurn.model)?.availability!=='AVAILABLE'||
       (turnPending()?.model&&turnPending().model!==chatTurn.model)))return;
  const epoch=chat.epoch,scope=turnScope(),base=turnBase(),value=$('chatInput').value;
  if(chatTurn.models.find(m=>m.model_id===chatTurn.model)?.is_local&&
     chatTurn.models.find(m=>m.model_id===chatTurn.model)?.availability!=='AVAILABLE'&&!turnPending())return;
  const localRequest=chatTurn.colibri&&String(turnPending()?.model||chatTurn.model||'').startsWith('tgt_');
  if(localRequest)renderColibriProgress(null);
  chatTurn.busy=true;renderTurnComposer();text('chatTurnStatus',localRequest?'Принимаем запрос Colibri…':'Принимаем TEST-запрос…');
  try{
    let pending=JSON.parse(localStorage.getItem(scope)||'null');
    if(!pending){
      pending=modelChat()?{key:crypto.randomUUID(),text:value,model:chatTurn.model}:{key:crypto.randomUUID()};
      localStorage.setItem(scope,JSON.stringify(pending));
      if(modelChat()){chatTurn.state=null;$('chatTurnNew').hidden=true;renderTurnComposer()}
    }
    else{
      try{
        const previous=await chatGet(base+'/by-key/'+encodeURIComponent(pending.key));
        if(['SUCCEEDED','FAILED','CANCELLED','ATTEMPTING'].includes(previous.state)){
          if(epoch===chat.epoch){showTurn(previous);await loadChatHistory(false)}return
        }
      }catch(e){if(e.code!=='turn_not_found'&&e.code!=='turn_acceptance_incomplete')throw e}
    }
    const request=modelChat()?{idempotency_key:pending.key,text:pending.text??value,model_ref:pending.model}:
      {idempotency_key:pending.key,text:value,model_ref:'local-test:v1',context_ref:'empty:v1',config_ref:'test-only:v1'};
    if(localRequest)pollColibriProgress(base,scope,pending.key);
    const result=await chatPost(base,request);
    if(epoch===chat.epoch){showTurn(result);await loadChatHistory(false)}
  }catch(e){
    const invalid=modelChat()&&['invalid_turn_request','invalid_offline_request','request_too_large'].includes(e.code);
    // A local admission rejection happens before creation of a Turn. Do not
    // discard a saved key for ambiguous post-dispatch errors.
    const preflight=localRequest&&['unsupported_capability','model_disabled','ordinary_model_disabled','local_provider_unavailable'].includes(e.code);
    if(invalid||preflight)localStorage.removeItem(scope);
    if(epoch===chat.epoch)text('chatTurnStatus',preflight?(e.code==='unsupported_capability'?
      'Colibri MVP1 не поддерживает системные инструкции этого контекста. Текст запроса не отправлен.':
      'Локальная модель недоступна или отключена. Текст запроса не отправлен.'):invalid?'TEST · исправьте текст или выбор модели.':
      e.code==='idempotency_conflict'?'Конфликт ключа: верните исходный текст. Перезаписи нет.':'Ответ не подтверждён. Ключ сохранён. Проверьте состояние запроса перед повтором.')
  }
  finally{if(localRequest&&epoch===chat.epoch)clearColibriProgressTimer();chatTurn.busy=false;renderTurnComposer()}
}
async function cancelTurn(){
  const pending=turnPending();if(!pending)return;const epoch=chat.epoch;
  try{const current=await chatGet(turnBase()+'/by-key/'+encodeURIComponent(pending.key));const result=await chatPost(turnBase()+'/'+current.turn_id+'/cancel',{});if(epoch===chat.epoch){showTurn(result);await loadChatHistory(false)}}
  catch(_){if(epoch===chat.epoch)text('chatTurnStatus','Отмена не подтверждена. Проверьте состояние запроса.')}
}
const CHAT_REASON={missing_history:'В папке нет истории Ultra',missing_path:'Папка недоступна',not_directory:'Путь не является папкой',invalid_metadata:'Данные Ultra повреждены',unsupported_version:'Данные Ultra более новой версии',unsafe_storage_link:'Внутри хранилища Ultra ссылка вместо папки или файла — чтение запрещено',unreadable:'Данные не читаются',unsupported_registration_id:'Эта регистрация не поддерживается Ultra Chat',registry_unavailable:'Реестр Workspace недоступен',too_many_workspaces:'Слишком много Workspace',chats_listing_too_large:'Слишком много диалогов для просмотра',history_too_large:'История слишком большая для просмотра',foreign_identity:'Диалог принадлежит другому Workspace',chat_damaged:'Диалог повреждён',ultra_core_unavailable:'Общее ядро Ultra недоступно'};
const CHAT_OUTCOME={failed:['Ошибка выполнения (старая запись), не ответ модели','bad'],no_answer:['Ответ не сохранён','warn'],interrupted:['Прервано · исход неизвестен','unknown'],unknown:['Исход неизвестен','unknown'],pending:['Ожидает выполнения','warn'],running:['Выполняется','active'],cancelled:['Отменено до выполнения','warn'],request_failed:['Выполнение завершилось ошибкой','bad']};
function chatReason(code){return CHAT_REASON[code]||'Недоступно ('+String(code)+')'}
function chatTime(value){return typeof value==='string'?value.replace('T',' ').slice(0,19):''}
function chatCount(map){return Object.values(map||{}).reduce((sum,n)=>sum+(Number(n)||0),0)}
async function loadChatAccess(){
  const access=await api('/ui/ultra-chat/capability'),c=access?.ultra_chat;
  chatTurn.ordinary=access?.turn_test?.mode==='ORDINARY';
  chatTurn.compact=access?.turn_test?.compact_sidebar===true;
  chatTurn.colibri=access?.turn_test?.colibri_offline===true;
  chatTurn.executionMode=access?.turn_test?.execution_mode;
  chatTurn.personalWorkspaceId=typeof access?.turn_test?.personal_workspace_id==='string'?access.turn_test.personal_workspace_id:null;
  chatTurn.liveWorkspaceId=typeof access?.turn_test?.live_workspace_id==='string'?access.turn_test.live_workspace_id:null;
  chatTurn.testModelPreferences=stage5Offline&&access?.turn_test?.mode==='TEST_OFFLINE'&&access.turn_test.chat_model_preferences===true;
  chatTurn.available=access?.turn_test?.available===true&&access.turn_test.mode===(chatTurn.ordinary?'ORDINARY':stage5Offline?'TEST_OFFLINE':'TEST');
  chatTurn.preferencesEnabled=modelChat()&&access?.turn_test?.chat_preferences===true;
  if(modelChat()){
    chatTurn.models=Array.isArray(access.turn_test.models)?access.turn_test.models:[];
    if(!chatTurn.models.some(m=>m.model_id===chatTurn.model)&&
       !(chatTurn.ordinary&&chat.chat&&String(chatTurn.model||'').startsWith('tgt_')))
      chatTurn.model=chatTurn.models[0]?.model_id??null;
    if(chatTurn.testModelPreferences){chatTurn.model=null;chatTurn.testModelLoaded=false;}
  }
  renderTurnComposer();
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
    catch(again){if(again.code==='ultra_chat_token_invalid'){chat.token=null;throw Object.assign(Error(),{chatTokenRejected:true})}throw again}
  }
}
function chatFailure(e){
  if(e.chatUnavailable){text('chatAccess',e.message);notice('chatError','');chat.workspaces=[];chat.chats=[];renderChatWorkspaces();renderChatList();text('chatWorkspaceState','');text('chatListState','');return}
  notice('chatError',e.chatTokenRejected?'Доступ к истории недействителен — обновите страницу.':
    e.httpStatus===403?'Сервер не разрешил чтение истории. Проверьте доступ и нажмите «Обновить».':
    'Не удалось загрузить данные Ultra Chat. Проверьте, запущен ли Web Alarm, и нажмите «Обновить».')
}
function chatPick(label,detail,current,onclick){
  const b=element('button',null,'chat-pick');b.type='button';b.setAttribute('aria-current',String(current));
  b.append(element('strong',label));if(detail)b.append(element('small',detail,'muted'));b.onclick=onclick;return b
}
function chatIcon(label,title,onClick,enabled=true){
  const b=element('button',label,'chat-icon-button');b.type='button';b.setAttribute('aria-label',title);b.title=title;
  b.disabled=!enabled;b.onclick=e=>{e?.stopPropagation?.();return onClick()};return b
}
function renderChatWorkspaces(){
  if(chatTurn.compact)return renderCompactWorkspaces();
  const selected=chat.workspace;
  const personal=chat.workspaces.find(w=>w.wa_workspace_id===chatTurn.personalWorkspaceId&&w.history==='ok');
  $('chatPersonalNew').hidden=!chatTurn.ordinary;
  $('chatPersonalNew').disabled=chatEdit.busy;
  // Park the shared controls in the connected, hidden dock BEFORE replacing the tree. Collapsing the
  // selected group otherwise detaches them: getElementById returns null and append prints "null".
  const nested=['chatWorkspaceNameForm','chatListState','chatList','chatNameForm'].map($);
  $('chatListDock').append(...nested);
  const groups=chat.workspaces.map(w=>{
    const active=w.wa_workspace_id===selected,open=active&&chat.expanded===selected;
    const group=element('div',null,'chat-workspace-group');group.dataset.active=String(active);
    const row=element('div',null,'chat-workspace-row');
    const choose=chatPick(w.wa_workspace_id===chatTurn.personalWorkspaceId?'Личные чаты':w.display_name,
      w.wa_workspace_id===chatTurn.personalWorkspaceId?'Без проекта · локальная история':w.history==='ok'?'История Ultra найдена':chatReason(w.history),active,()=>selectChatWorkspace(w.wa_workspace_id));
    choose.setAttribute('aria-expanded',String(open));row.append(choose);
    row.append(chatIcon('✎','Переименовать Workspace «'+w.display_name+'»',()=>openWorkspaceName(w.wa_workspace_id),!chat.renamingWorkspace?.busy&&!chatEdit.busy));
    row.append(chatIcon('+','Новый диалог в Workspace «'+w.display_name+'»',()=>{if(!active){selectChatWorkspace(w.wa_workspace_id).then(()=>{if(chat.workspace===w.wa_workspace_id)openChatName('create')})}else{chat.expanded=selected;renderChatWorkspaces();openChatName('create')}},['ok','missing_history'].includes(w.history)&&!chatEdit.busy));
    group.append(row);
    if(open){
      const panel=element('div',null,'chat-nested-panel');
      panel.append(...nested);
      group.append(panel)
    }
    return {group,personal:w.wa_workspace_id===chatTurn.personalWorkspaceId}
  });
  $('chatPersonalList').replaceChildren(...groups.filter(g=>g.personal).map(g=>g.group));
  $('chatWorkspaceList').replaceChildren(...groups.filter(g=>!g.personal).map(g=>g.group));
  syncChatActions()
}
function compactIcon(label,title,action,enabled=true,kind=''){
  const b=chatIcon(label,title,action,enabled);
  if(kind)b.className+=' compact-'+kind+(kind==='plus'?'':' compact-icon');
  return b
}
// Sidebar visibility is a browser preference, not chat selection or server state.
const compactSectionKey='webAlarm.chatSidebarSections.v1';
const compactSections=(()=>{try{const v=JSON.parse(localStorage.getItem(compactSectionKey)||'{}');return {personal:v?.personal!==false,workspace:v?.workspace!==false,collapsed:Array.isArray(v?.collapsed)?v.collapsed.filter(x=>typeof x==='string'&&x.length<=128).slice(0,500):[]}}catch(_){return {personal:true,workspace:true,collapsed:[]}}})();
function persistCompactSections(){try{localStorage.setItem(compactSectionKey,JSON.stringify(compactSections))}catch(_){}}
function paintCompactToggle(b,open,label){
  b.hidden=false;b.replaceChildren(element('span',null,'compact-disclosure-glyph'));
  b.children[0].setAttribute('aria-hidden','true');
  b.setAttribute('aria-expanded',String(open));b.setAttribute('aria-label',(open?'Свернуть ':'Развернуть ')+label);
  b.title=(open?'Свернуть ':'Развернуть ')+label
}
function compactCardOpen(ws){return !compactSections.collapsed.includes(ws)}
function setCompactCard(ws,open){
  if(open)compactSections.collapsed=compactSections.collapsed.filter(x=>x!==ws);
  else if(compactCardOpen(ws))compactSections.collapsed=[...compactSections.collapsed,ws].slice(-500);
  persistCompactSections()
}
function compactCardToggle(ws,label,list){
  const b=element('button',null,'compact-card-toggle');b.type='button';
  list.id='compactWorkspaceChats-'+ws;b.setAttribute('aria-controls',list.id);
  function sync(){const open=compactCardOpen(ws);list.hidden=!open;paintCompactToggle(b,open,'чаты Workspace «'+label+'»')}
  b.onclick=()=>{setCompactCard(ws,!compactCardOpen(ws));sync()};
  sync();return b
}
let compactNameEdit=null;
function syncCompactSections(){
  for(const [section,id,list,label] of [['personal','chatPersonalToggle','chatPersonalList','личные чаты'],['workspace','chatWorkspaceToggle','chatWorkspaceList','Workspace']]){
    const open=compactSections[section],b=$(id);
    paintCompactToggle(b,open,label);$(list).hidden=!open;
    b.onclick=()=>setCompactSection(section,!compactSections[section])
  }
  $('chatWorkspaceState').hidden=!compactSections.workspace
}
function setCompactSection(section,open){
  compactSections[section]=open;
  persistCompactSections();
  syncCompactSections()
}
function beginCompactName(ws,cid,title){
  if(chatEdit.busy||chat.creatingWorkspace)return;
  compactNameEdit={ws,cid,expected:title,draft:title};
  notice('chatError','');renderCompactWorkspaces();
  const input=$('compactInlineName');
  if(input){input.focus();input.select?.()}
}
function compactNameControl(button,ws,cid){
  const e=compactNameEdit;
  if(!e||e.ws!==ws||e.cid!==cid)return button;
  const input=element('input',null,'compact-inline-name');input.id='compactInlineName';input.type='text';
  input.value=e.draft;input.maxLength=cid?200:120;input.disabled=chatEdit.busy;
  input.setAttribute('aria-label',cid?'Название чата':'Название Workspace');
  input.setAttribute('autocomplete','off');
  input.title='Enter — сохранить, Escape — отменить';
  input.oninput=()=>{if(compactNameEdit===e)e.draft=input.value};
  input.onclick=z=>z?.stopPropagation?.();
  input.onkeydown=z=>{
    if(z.isComposing||z.keyCode===229)return;
    if(z.key==='Escape'){
      z.preventDefault();z.stopPropagation?.();
      if(!chatEdit.busy&&compactNameEdit===e){compactNameEdit=null;notice('chatError','');renderCompactWorkspaces()}
    }else if(z.key==='Enter'){
      z.preventDefault();z.stopPropagation?.();e.draft=input.value;return saveCompactName(e)
    }
  };
  return input
}
async function saveCompactName(e){
  if(chatEdit.busy||chat.creatingWorkspace||compactNameEdit!==e)return;
  const title=String(e.draft||'').trim(),limit=e.cid?200:120;
  if(!title||title.length>limit||/[\r\n]/.test(title)){
    notice('chatError','Введите название до '+limit+' символов.');return
  }
  chatEdit.busy=true;notice('chatError','');renderCompactWorkspaces();
  let error='';
  try{
    const base='/ultra/chat/workspaces/'+encodeURIComponent(e.ws);
    const r=await chatPost(base+(e.cid?'/chats/'+encodeURIComponent(e.cid):'')+'/title',{title,expected_title:e.expected});
    if(r?.wa_workspace_id!==e.ws||(e.cid?(r.chat?.chat_id!==e.cid||r.chat?.title!==title):r.display_name!==title))throw Error('rename_unconfirmed');
    const w=chat.workspaces.find(x=>x.wa_workspace_id===e.ws);
    if(e.cid){
      for(const list of [w?.chats,chat.workspace===e.ws?chat.chats:null]){
        const c=list?.find(x=>x.chat_id===e.cid);if(c)c.title=title
      }
      if(chat.workspace===e.ws&&chat.chat===e.cid)text('chatTitle',title)
    }else{
      if(w)w.display_name=title;
      if(chat.workspace===e.ws)text('chatWorkspaceName',title)
    }
    compactNameEdit=null;
  }catch(x){
    if(['title_changed','workspace_title_changed','chat_not_found'].includes(x.code)){
      // A stale name is never silently overwritten. Re-read, then require another Enter.
      await loadChatWorkspaces();
      const w=chat.workspaces.find(x=>x.wa_workspace_id===e.ws);
      const fresh=e.cid?(chat.workspace===e.ws?chat.chats:w?.chats)?.find(c=>c.chat_id===e.cid)?.title:w?.display_name;
      if(typeof fresh==='string'){e.expected=fresh;error='Название изменилось в другом окне. Текущее: '+fresh+'. Проверьте ввод и нажмите Enter ещё раз.'}
      else{compactNameEdit=null;error='Запись недоступна. Обновите список.'}
    }else error='Не удалось подтвердить сохранение. Проверьте список перед повтором.';
  }finally{
    chatEdit.busy=false;renderCompactWorkspaces();if(error)notice('chatError',error);
    if(compactNameEdit===e)$('compactInlineName')?.focus()
  }
}
function compactDialogRow(w,c){
  const ws=w.wa_workspace_id,ok=c.status==='ok',row=element('div',null,'chat-dialog-row compact-dialog');
  const label=ok?c.title:'Диалог недоступен';
  const b=chatPick(label,'',chat.workspace===ws&&chat.chat===c.chat_id,async()=>{
    if(chat.workspace!==ws)await selectChatWorkspace(ws);
    if(chat.workspace===ws&&chat.chat!==c.chat_id)await selectChat(c.chat_id)
  });
  b.title=label;b.disabled=!ok;b.setAttribute('data-status',c.status);
  row.append(compactNameControl(b,ws,c.chat_id),compactIcon('✎','Переименовать чат «'+label+'»',()=>beginCompactName(ws,c.chat_id,label),ok&&!chatEdit.busy,'edit'),compactIcon('×','Убрать чат «'+label+'» в архив',()=>archiveCompact(ws,c.chat_id),ok&&!chatEdit.busy,'trash'));
  return row
}
function renderCompactWorkspaces(){
  const previousInput=$('compactInlineName'),restoreFocus=previousInput&&document.activeElement===previousInput;
  const caret=restoreFocus?[previousInput.selectionStart,previousInput.selectionEnd]:null;
  const nested=['chatWorkspaceNameForm','chatListState','chatList','chatNameForm'].map($);
  $('chatListDock').append(...nested);
  const [workspaceForm,listState,chatList,nameForm]=nested;
  workspaceForm.hidden=true;nameForm.hidden=true;
  const personal=$('chatPersonalList');personal.className='chat-picks compact-personal-list';
  const plus=$('chatPersonalNew');plus.hidden=false;plus.disabled=chatEdit.busy||chat.creatingWorkspace;
  plus.textContent='+';plus.title='Новый личный чат';plus.setAttribute('aria-label','Новый личный чат');
  if(plus.parentNode)plus.parentNode.className='chat-personal-heading compact-heading';
  const wsPlus=$('chatRegisterWorkspace');wsPlus.title='Создать пустой Workspace';wsPlus.textContent='+';
  wsPlus.setAttribute('aria-label','Создать Workspace');wsPlus.disabled=chatEdit.busy||chat.creatingWorkspace;
  if(wsPlus.parentNode)wsPlus.parentNode.className='chat-workspace-heading compact-heading';
  syncCompactSections();
  text('chatSidebarNote','');
  const groups=[],personalRows=[];
  for(const w of chat.workspaces){
    const ws=w.wa_workspace_id,active=chat.workspace===ws;
    const chats=active?chat.chats:(w.chats||[]);
    if(w.personal||ws===chatTurn.personalWorkspaceId){
      if(active){chatList.replaceChildren(...chats.map(c=>compactDialogRow(w,c)));personalRows.push(chatList,nameForm)}
      else personalRows.push(...chats.map(c=>compactDialogRow(w,c)));
      continue
    }
    const g=element('div',null,'chat-workspace-group compact-workspace');g.dataset.active=String(active);g.dataset.workspaceId=ws;
    const head=element('div',null,'chat-workspace-row');
    const b=chatPick(w.display_name,'',active,()=>{if(!active)return selectChatWorkspace(ws)});b.title=w.display_name;
    head.append(compactNameControl(b,ws,null),compactIcon('✎','Переименовать Workspace',()=>beginCompactName(ws,null,w.display_name),!chatEdit.busy,'edit'),
      compactIcon('×','Убрать Workspace в архив',()=>archiveCompact(ws),!chatEdit.busy,'trash'),
      compactIcon('+','Новый чат в Workspace',()=>createCompactChat(ws),!chatEdit.busy&&['ok','missing_history'].includes(w.history),'plus'));
    g.append(head);
    const folder=element('div',null,'compact-folder'),path=element('small',w.folder||'Папка не выбрана');
    path.title=w.folder||'Папка не выбрана';
    folder.append(compactIcon('📁','Выбрать папку Workspace',()=>attachCompactFolder(ws),!chatEdit.busy,'folder-icon'),path);g.append(folder);
    if(active)g.append(workspaceForm);
    const list=element('div',null,'compact-content');
    if(active){chatList.replaceChildren(...chats.map(c=>compactDialogRow(w,c)));list.append(chatList,nameForm)}
    else list.append(...chats.map(c=>compactDialogRow(w,c)));
    // Keep even hidden nested rows mounted: collapse is purely presentation.
    g.append(list,compactCardToggle(ws,w.display_name,list));
    groups.push(g)
  }
  personal.replaceChildren(...personalRows);
  $('chatWorkspaceList').replaceChildren(...groups);
  const currentInput=$('compactInlineName');
  if(currentInput&&restoreFocus&&!currentInput.disabled){
    currentInput.focus();if(caret?.[0]!=null)currentInput.setSelectionRange?.(...caret)
  }
  syncChatActions()
}
async function createCompactChat(ws=null){
  if(chatEdit.busy||chat.creatingWorkspace)return;
  compactNameEdit=null;setCompactSection(ws?'workspace':'personal',true);
  if(ws)setCompactCard(ws,true);
  const id=newChatId();
  chatEdit.busy=true;renderCompactWorkspaces();
  try{
    const body=ws?{workspace_id:ws,chat_id:id}:{chat_id:id};
    const result=await chatPost('/ultra/chat/sidebar/'+(ws?'chat':'personal'),body);
    if(result?.chat?.chat_id!==id||typeof result.wa_workspace_id!=='string')throw Error('unconfirmed');
    chat.workspace=result.wa_workspace_id;chat.expanded=chat.workspace;chat.chat=id;
    chat.epoch++;chat.chats=[];chat.messages=[];chat.page=null;clearChatHistory('Новый чат');
    await loadChatAccess();await loadChatWorkspaces();
    if(chat.workspace===result.wa_workspace_id&&chat.chat===id)await selectChat(id);
  }catch(_){notice('chatError','Не удалось подтвердить создание чата. Обновите список перед повтором.')}
  finally{chatEdit.busy=false;renderCompactWorkspaces()}
}
async function createCompactWorkspace(){
  if(chat.creatingWorkspace||chatEdit.busy)return;
  compactNameEdit=null;setCompactSection('workspace',true);
  chat.creatingWorkspace=true;$('chatRegisterWorkspace').disabled=true;
  try{
    const ws='ws_'+newChatId().slice(5);
    const result=await chatPost('/ultra/chat/sidebar/workspace',{workspace_id:ws});
    if(result?.wa_workspace_id!==ws)throw Error('unconfirmed');
    chat.epoch++;chat.workspace=ws;chat.expanded=ws;chat.chat=null;chat.chats=[];chat.messages=[];chat.page=null;
    clearChatHistory('Создайте чат');await loadChatWorkspaces();
  }catch(_){notice('chatError','Не удалось подтвердить создание Workspace. Обновите список перед повтором.')}
  finally{chat.creatingWorkspace=false;$('chatRegisterWorkspace').disabled=false;renderCompactWorkspaces()}
}
async function archiveCompact(ws,cid=null){
  if(chatEdit.busy||chatTurn.busy||chat.creatingWorkspace)return;
  if(!window.confirm(cid?'Убрать чат из списка? История сохранится.':'Убрать Workspace из списка? Папка и история сохранятся.'))return;
  chatEdit.busy=true;
  try{
    const body={workspace_id:ws};if(cid)body.chat_id=cid;
    const result=await chatPost('/ultra/chat/sidebar/archive',body);
    if(result?.archived!==true)throw Error('unconfirmed');
    if(!cid)setCompactCard(ws,true);
    if(compactNameEdit?.ws===ws&&(!cid||compactNameEdit.cid===cid))compactNameEdit=null;
    if(chat.workspace===ws&&(!cid||chat.chat===cid)){
      if(!cid)chat.workspace=null;
      chat.chat=null;chat.chats=[];chat.messages=[];chat.page=null;chat.epoch++;clearChatHistory('Выберите диалог');
    }
    await loadChatWorkspaces()
  }catch(_){notice('chatError','Не удалось подтвердить удаление из списка. Историю не удаляем.')}
  finally{chatEdit.busy=false;renderCompactWorkspaces()}
}
async function attachCompactFolder(ws){
  if(chat.creatingWorkspace||chatEdit.busy)return;
  chat.creatingWorkspace=true;
  try{
    let folder=null;
    if(!stage5Offline){
      const capability=(await api('/ui/capabilities'))?.folder_picker;
      if(!capability?.available||typeof capability.token!=='string')throw Error('picker unavailable');
      const picked=await api('/ui/pick-workspace-folder',{method:'POST',body:{},headers:{'X-WebAlarm-Folder-Token':capability.token},timeoutMs:125000});
      if(picked?.status==='CANCELLED')return;
      if(picked?.status!=='SELECTED'||typeof picked.workspace_root!=='string')throw Error('picker invalid');
      folder=picked.workspace_root;
    }
    const result=await chatPost('/ultra/chat/sidebar/folder',{workspace_id:ws,folder});
    if(typeof result?.folder!=='string')throw Error('unconfirmed');
    await loadChatWorkspaces();
  }catch(_){notice('chatError','Не удалось привязать папку. История остаётся на прежнем месте.')}
  finally{chat.creatingWorkspace=false;renderCompactWorkspaces()}
}
function openWorkspaceName(id){
  if(chat.renamingWorkspace?.busy||chatEdit.busy)return;
  closeWorkspaceName();
  if(chat.workspace!==id){selectChatWorkspace(id).then(()=>{if(chat.workspace===id)openWorkspaceName(id)});return}
  const w=chat.workspaces.find(x=>x.wa_workspace_id===id);if(!w)return;
  closeChatName();
  chat.expanded=id;renderChatWorkspaces();
  chat.renamingWorkspace={id,expected:w.display_name};
  $('chatWorkspaceNameInput').value=w.display_name;notice('chatWorkspaceNameError','');
  $('chatWorkspaceNameForm').hidden=false;$('chatWorkspaceNameInput').focus()
}
function closeWorkspaceName(){
  if(chat.renamingWorkspace?.busy)return;
  chat.renamingWorkspace=false;$('chatWorkspaceNameForm').hidden=true;notice('chatWorkspaceNameError','')
}
async function saveWorkspaceName(){
  const edit=chat.renamingWorkspace;if(!edit||edit.busy)return;
  const title=String($('chatWorkspaceNameInput').value||'').trim();
  if(!title||title.length>120||/[\r\n]/.test(title)){notice('chatWorkspaceNameError','Введите название до 120 символов.');return}
  edit.busy=true;$('chatWorkspaceNameSave').disabled=true;
  try{
    const r=await chatPost('/ultra/chat/workspaces/'+encodeURIComponent(edit.id)+'/title',{title,expected_title:edit.expected});
    if(r?.wa_workspace_id!==edit.id||r?.display_name!==title)throw Error('rename_unconfirmed');
    edit.busy=false;closeWorkspaceName();await loadChatWorkspaces();
  }catch(e){
    if(e.code==='workspace_title_changed'){
      const refreshed=await loadChatWorkspaces();
      const fresh=chat.workspaces.find(w=>w.wa_workspace_id===edit.id);
      if(refreshed&&fresh)edit.expected=fresh.display_name;
      notice('chatWorkspaceNameError',refreshed&&fresh?
        'Название изменилось в другом окне. Список обновлён; проверьте название и нажмите «Сохранить» ещё раз.':
        'Название изменилось в другом окне, но перечитать его не удалось. Нажмите «Обновить» и откройте форму заново.');
    }else{
      notice('chatWorkspaceNameError','Не удалось подтвердить изменение названия. Обновите список перед повтором.');
    }
  }finally{edit.busy=false;$('chatWorkspaceNameSave').disabled=false}
}
function renderChatList(){
  if(chatTurn.compact)return renderCompactWorkspaces();
  const workspace=chat.workspace;
  $('chatList').replaceChildren(...chat.chats.map(c=>{
    const ok=c.status==='ok',row=element('div',null,'chat-dialog-row');
    const b=chatPick(ok?c.title:c.status==='unsafe_storage_link'?'Ссылка вместо диалога — не читается':'Диалог повреждён',
      ok?(c.created_at?'Создан '+chatTime(c.created_at):''):'ID '+c.chat_id,c.chat_id===chat.chat,()=>selectChat(c.chat_id));
    b.setAttribute('data-status',c.status);if(!ok)b.disabled=true;
    row.append(b,chatIcon('✎','Переименовать диалог «'+(ok?c.title:c.chat_id)+'»',async()=>{
      if(chat.chat!==c.chat_id)await selectChat(c.chat_id);
      if(chat.workspace===workspace&&chat.chat===c.chat_id)openChatName('rename')
    },ok&&!chatEdit.busy));
    return row
  }));
  syncChatActions()
}
function chatNotices(list){
  $('chatNotice').className='notice'+(list[0]?.[0]==='error'?' error':list[0]?.[0]==='info'?' info':'');
  notice('chatNotice',list.map(item=>item[1]).join('\n'))
}
function clearChatHistory(title){
  chat.historyRevision++;
  clearColibriProgressTimer();renderColibriProgress(null);
  chatTurn.checkRevision++;chatTurn.checking=0;chatTurn.checkCount=0;text('chatTurnCheckResult','');
  if(chatTurn.testModelPreferences){closePicker(false);chatTurn.testModelRevision=(chatTurn.testModelRevision||0)+1;chatTurn.testModelBusy=false;chatTurn.testModelLoaded=false;chatTurn.model=null;}
  if(modelChat()){
    chatTurn.state=null;
    $('chatTurnNew').hidden=true;
    $('chatInput').value=turnPending()?.text??'';
  }
  text('chatTitle',title);chatNotices([]);$('chatHistory').replaceChildren();$('chatOlder').hidden=true;text('chatTurnStatus','');renderChatUsage(null);
  chatPreferencesRevision++;chatPreferencesLoadedFor=null;$('chatPreferences').hidden=true;preferencesBusy(true);text('chatPreferencesStatus','');renderTurnComposer()
}
function chatMessage(m){
  const li=element('li',null,'msg'),failed=m.outcome==='failed',meta=element('div',null,'msg-meta');
  li.setAttribute('data-role',m.role);li.setAttribute('data-outcome',m.outcome);li.setAttribute('data-message',m.message_id);
  meta.append(element('strong',m.role==='user'?'Вы':m.role==='assistant'?(failed?'Ошибка выполнения':'Ultra'):m.role==='system'?'Система':'Инструмент'));
  if(m.created_at)meta.append(element('span',chatTime(m.created_at)));
  if(m.model&&!failed)meta.append(element('span',m.model,'tag'));
  const outcome=CHAT_OUTCOME[m.outcome];if(outcome)meta.append(element('span',outcome[0],'tag '+outcome[1]));
  li.append(meta,m.too_large_for_page?element('p','Сообщение слишком большое для одной страницы ('+m.size_bytes+' байт) и не показано.','muted'):element('div',m.text,'msg-text'));
  if(!m.too_large_for_page&&typeof m.text==='string'){
    const footer=element('div',null,'msg-footer'), status=element('span','');
    status.setAttribute('role','status');
    const button=element('button','Копировать','msg-copy');button.type='button';button.title='Копировать сообщение';button.setAttribute('aria-label','Копировать сообщение');
    button.onclick=async()=>{try{await navigator.clipboard.writeText(m.text);status.textContent='Скопировано'}catch(_){status.textContent='Не удалось скопировать. Выделите текст вручную.'}};
    footer.append(button,status);li.append(footer);
  }
  if(m.role==='assistant'&&m.metrics){
    const u=m.metrics.usage||{}, count=k=>Number.isSafeInteger(u[k])&&u[k]>=0?String(u[k]):'—';
    const parts=[];
    if(['prompt_tokens','completion_tokens','total_tokens','reasoning_tokens','precached_prompt_tokens'].some(k=>Number.isSafeInteger(u[k])&&u[k]>=0)){
      parts.push('Токены: вход '+count('prompt_tokens')+' / выход '+count('completion_tokens')+' / всего '+count('total_tokens'));
      if(Number.isSafeInteger(u.reasoning_tokens)&&u.reasoning_tokens>=0)parts.push('рассуждения (внутри выхода) '+count('reasoning_tokens'));
      if(Number.isSafeInteger(u.precached_prompt_tokens)&&u.precached_prompt_tokens>=0)parts.push('кэш '+count('precached_prompt_tokens'));
    }
    if(Number.isFinite(m.metrics.elapsed_seconds)&&m.metrics.elapsed_seconds>=0)parts.unshift('Запрос '+m.metrics.elapsed_seconds.toFixed(2)+' с');
    if(parts.length)li.append(element('div',(m.metrics.synthetic?'TEST · ':'')+parts.join(' · '),'msg-metrics'));
  }
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
  if(chatTurn.compact&&typeof data.chat?.title==='string'){const item=chat.chats.find(c=>c.chat_id===chat.chat);if(item&&item.title!==data.chat.title){item.title=data.chat.title;renderCompactWorkspaces()}}
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
async function loadTestChatModel(){
  if(!chat.workspace||!chat.chat)return;
  const epoch=chat.epoch,revision=chatTurn.testModelRevision=(chatTurn.testModelRevision||0)+1;
  const current=()=>epoch===chat.epoch&&revision===chatTurn.testModelRevision;
  chatTurn.testModelBusy=true;chatTurn.testModelLoaded=false;chatTurn.model=null;notice('chatModelError','');renderTurnComposer();
  try{
    const saved=await chatGet(turnBase().replace(/\/turns$/,'/model'));
    if(!current())return;
    const selected=chatTurn.models.find(m=>m.model_id===saved.model_ref);
    if(!selected)throw Error('unavailable saved model');
    chatTurn.model=selected.model_id;chatTurn.testModelLoaded=true;
  }catch(_){if(current())notice('chatModelError','Модель TEST не восстановлена. Выберите доступную модель повторно.');}
  finally{if(current()){chatTurn.testModelBusy=false;renderTurnComposer()}}
}
async function chooseTestChatModel(model){
  if(chatTurn.testModelBusy||!chat.workspace||!chat.chat)return;
  const epoch=chat.epoch,revision=chatTurn.testModelRevision=(chatTurn.testModelRevision||0)+1;
  const current=()=>epoch===chat.epoch&&revision===chatTurn.testModelRevision;
  chatTurn.testModelBusy=true;notice('chatModelError','');renderTurnComposer();
  try{
    const saved=await chatPost(turnBase().replace(/\/turns$/,'/model'),{model_ref:model});
    if(!current())return;
    if(saved.model_ref!==model||saved.persisted!==true)throw Error('save not confirmed');
    chatTurn.model=model;chatTurn.testModelLoaded=true;closePicker(true);
  }catch(_){if(current()){chatTurn.model=null;chatTurn.testModelLoaded=false;notice('chatModelError','Выбор модели TEST не подтверждён. Откройте чат повторно или выберите модель ещё раз.');}}
  finally{if(current()){chatTurn.testModelBusy=false;renderTurnComposer()}}
}
async function loadChatModel(){
  if(chatTurn.testModelPreferences)return loadTestChatModel();
  if(modelChat()){
    if(chatTurn.ordinary&&chat.workspace&&chat.chat){
      const epoch=chat.epoch,revision=++ordinaryModelRevision;chatTurn.model=null;renderTurnComposer();
      try{const selected=await chatGet(turnBase().replace(/\/turns$/,'/model'));
        if(epoch===chat.epoch&&revision===ordinaryModelRevision){
          chatTurn.model=selected.enrolled===false?null:
            typeof selected.model_ref==='string'?selected.model_ref:null;
          if(selected.enrolled===false)notice('chatModelError',
            'Для этого Workspace выберите модель: журнал новых GigaChat-запросов подготовится при выборе.');
        }
      }catch(_){if(epoch===chat.epoch&&revision===ordinaryModelRevision)text('chatModelError','Выбор модели не подтверждён.');}
      if(epoch!==chat.epoch||revision!==ordinaryModelRevision)return;
    }
    renderTurnComposer();return
  }
  try{
    const s=(await api('/ultra/connections/selection?role=chat'))?.selection;
    if(!s||typeof s.state!=='string')throw Error('selection');
    text('chatModel',s.state==='SAVED'&&typeof s.display_name==='string'?'Модель: '+s.display_name:s.state==='NOT_SELECTED'?'Модель не выбрана — выберите у поля ввода':
      s.state==='CORRUPT'?'Выбор модели повреждён — выберите заново у поля ввода':s.state==='INVALID_REFERENCE'?'Выбранная модель недоступна — выберите другую у поля ввода':
      s.state==='REGISTRY_UNAVAILABLE'?'Реестр моделей недоступен':'Модель: неизвестное состояние '+s.state);
    $('chatModel').className='tag '+(s.state==='SAVED'?'active':'warn');
    text('chatModelPick',(s.state==='SAVED'&&typeof s.display_name==='string'?s.display_name:'Выбрать модель')+' ▾')
  }catch(_){text('chatModel','Модель: нет данных EVM');$('chatModel').className='tag warn';text('chatModelPick','Выбрать модель ▾')}
  finally{if(chatTurn.available)renderTurnComposer()}
}
// Model preference next to the composer (CLAUDE-WUA-EVM-COMPACT-LAYOUT-001): the same saved choice as before
// (/ultra/connections/selection, no chat token), no message, Turn or history write. The model list is read only
// when the user opens the picker, so the chat screen still reads nothing else at load.
const picker={open:false,busy:false,epoch:0};
async function openPicker(){
  if(picker.busy)return;
  if(picker.open){closePicker(true);return}
  const epoch=++picker.epoch;picker.open=true;notice('chatModelError','');
  $('chatModelPick').setAttribute('aria-expanded','true');$('chatModelMenu').hidden=false;
  $('chatModelMenu').replaceChildren(element('p','Загружаем модели…','muted'));
  if(modelChat()){
    if(chatTurn.colibri){
      try{await loadChatAccess()}catch(_){}
      if(!picker.open||epoch!==picker.epoch)return;
    }
    const options=chatTurn.models.map(m=>{
      const blocked=chatTurn.ordinary&&(m.is_local||chatTurn.executionMode==='REAL')&&m.availability!=='AVAILABLE';
      const suffix=m.availability==='UNAVAILABLE'?' · недоступна':
        m.availability==='NOT_APPROVED'?' · ожидает проверки':
        m.availability==='UNVERIFIED'?' · доступ не проверен':'';
      const button=element('button',m.display_name+suffix);
      button.type='button';button.setAttribute('role','option');
      button.setAttribute('aria-selected',String(m.model_id===chatTurn.model));
      button.disabled=blocked;button.setAttribute('aria-disabled',String(blocked));
      button.onclick=async()=>{
        if(blocked||picker.busy)return;
        if(chatTurn.testModelPreferences)return chooseTestChatModel(m.model_id);
        const scope=turnScope(),epoch=chat.epoch,revision=chatTurn.ordinary?++ordinaryModelRevision:0;
        picker.busy=true;
        try{
          if(chatTurn.ordinary){
            const saved=await chatPost(turnBase().replace(/\/turns$/,'/model'),{model_ref:m.model_id});
            if(saved?.model_ref!==m.model_id||saved?.persisted!==true||saved?.enrolled===false)
              throw Error('model_not_confirmed');
          }
          if(epoch===chat.epoch&&scope===turnScope()&&(!chatTurn.ordinary||revision===ordinaryModelRevision)){
            chatTurn.model=m.model_id;notice('chatModelError','');closePicker(true);renderTurnComposer();
          }
        }catch(e){if(epoch===chat.epoch&&revision===ordinaryModelRevision)
          notice('chatModelError',e?.code==='ordinary_workspace_not_enrolled'?
            'Журнал учёта Workspace недоступен или требует восстановления. Выбор модели не сохранён.':
            e?.code==='provider_workspace_scope'?
            'Workspace не зарегистрирован для этого подключения GigaChat. Выбор модели не сохранён.':
            'Выбор модели не сохранён. Повторите выбор.');}
        finally{picker.busy=false;renderTurnComposer()}
      };return button
    });
    $('chatModelMenu').replaceChildren(...options);
    (options.find(b=>b.getAttribute('aria-selected')==='true'&&!b.disabled)||options.find(b=>!b.disabled))?.focus();
    return
  }
  try{
    const data=await api('/ultra/connections');
    if(!picker.open||epoch!==picker.epoch)return;
    if(!validEvm(data))throw new Error('Некорректный ответ сервера о моделях');
    const s=data.selection.chat,items=data.columns.api.connections.map(c=>{
      const b=element('button',c.display_name+(c.selectable?'':' — отключена'));b.type='button';b.setAttribute('role','option');
      b.setAttribute('aria-selected',String(s.state==='SAVED'&&s.connection_id===c.connection_id));b.disabled=!c.selectable;
      b.onclick=()=>chooseChatModel(c.connection_id);return b});
    $('chatModelMenu').replaceChildren(...(items.length?items:[element('p','В реестре нет моделей.','muted')]));
    (items.find(b=>b.getAttribute('aria-selected')==='true'&&!b.disabled)||items.find(b=>!b.disabled))?.focus()
  }catch(e){if(picker.open&&epoch===picker.epoch)$('chatModelMenu').replaceChildren(element('p','Список моделей недоступен: '+e.message,'chat-model-error'))}
}
function closePicker(focus){
  picker.open=false;picker.epoch++;$('chatModelMenu').hidden=true;$('chatModelMenu').replaceChildren();
  $('chatModelPick').setAttribute('aria-expanded','false');if(focus)$('chatModelPick').focus()
}
async function chooseChatModel(id){
  if(picker.busy)return;picker.busy=true;$('chatModelPick').disabled=true;
  try{
    const r=await api('/ultra/connections/selection',{method:'POST',body:{role:'chat',connection_id:id}});
    if(r?.selection?.state!=='SAVED'||r.selection.connection_id!==id)throw new Error('Сервер не подтвердил сохранение выбора');
    closePicker(true)
  }catch(e){closePicker(true);notice('chatModelError','Модель не сохранена: '+e.message)}
  finally{picker.busy=false;$('chatModelPick').disabled=false;await loadChatModel()}
}
async function loadChatWorkspaces(){
  const epoch=chat.epoch;text('chatWorkspaceState','Загружаем Workspace…');notice('chatError','');
  try{
    if(!chat.token)await loadChatAccess();
    const data=await chatGet(chatTurn.compact?'/ultra/chat/sidebar':'/ultra/chat/workspaces');
    if(epoch!==chat.epoch)return;
    if(chatTurn.compact)chatTurn.personalWorkspaceId=data.personal_workspace_id??null;
    if(!validChatWorkspaces(data))throw Error('Некорректный ответ сервера о Workspace');
    text('chatAccess',chatTurn.ordinary?(chatTurn.available?'GigaChat · провайдер подключён':'Личные чаты доступны · отправка GigaChat пока закрыта'):
      chatTurn.available?'TEST · локальный имитатор · без LLM':'Данные проверяет сервер · сообщения не отправляются');chat.workspaces=data.workspaces;
    text('chatWorkspaceState',data.state!=='ok'?chatReason(data.reason):data.workspaces.some(w=>!chatTurn.compact||!w.personal)?'':chatTurn.compact?'Нет Workspace':'Нет зарегистрированных Workspace. Нажмите «+ Создать Workspace».');
    if(chat.workspace&&!chat.workspaces.some(w=>w.wa_workspace_id===chat.workspace)){chat.workspace=null;chat.expanded=null;chat.chat=null;chat.chats=[];renderChatList();clearChatHistory('Выберите диалог')}
    const selected=chat.workspaces.find(w=>w.wa_workspace_id===chat.workspace);
    text('chatWorkspaceName',selected?selected.display_name:'Ultra Chat');
    if(chatTurn.compact&&selected)chat.chats=selected.chats||[];
    renderChatWorkspaces();
    if(chat.workspace){await loadChatList();return true}
    const saved=modelChat()?testChatSelection():null;
    const first=(chatTurn.executionMode==='REAL'?
      chat.workspaces.find(w=>w.history==='ok'&&w.wa_workspace_id===chatTurn.liveWorkspaceId):null)||
      chat.workspaces.find(w=>w.history==='ok'&&w.wa_workspace_id===saved?.workspace)||
      chat.workspaces.find(w=>w.history==='ok'&&w.wa_workspace_id===chatTurn.personalWorkspaceId)||
      chat.workspaces.find(w=>w.history==='ok');
    if(first)await selectChatWorkspace(first.wa_workspace_id);
    return true
  }catch(e){if(epoch===chat.epoch){text('chatWorkspaceState','Список Workspace не загружен');chatFailure(e)}return false}
}
function selectChatWorkspace(id){
  if(chat.renamingWorkspace?.busy)return Promise.resolve();
  closeWorkspaceName();
  if(chat.workspace===id){if(!chatTurn.compact)chat.expanded=chat.expanded===id?null:id;renderChatWorkspaces();return Promise.resolve()}
  closeChatName();
  $('chatNameForm').hidden=true;// a pending save of the old Workspace must not expose its editor in the new one
  chat.epoch++;chat.workspace=id;chat.expanded=id;chat.chat=null;chat.chats=[];chat.messages=[];chat.page=null;chat.olderBusy=false;
  const w=chat.workspaces.find(item=>item.wa_workspace_id===id);if(chatTurn.compact)chat.chats=w?.chats||[];text('chatWorkspaceName',w?w.display_name:'Ultra Chat');
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
    notice('chatError','');
    const entry=chat.workspaces.find(w=>w.wa_workspace_id===chat.workspace);
    chat.chats=chatTurn.compact?data.chats.filter(c=>!entry?.hidden_chats?.includes(c.chat_id)):data.chats;
    if(chatTurn.compact&&entry)entry.chats=chat.chats;
    const hidden=chatCount(data.excluded);
    text('chatListState',data.state!=='ok'?chatReason(data.reason):(data.chats.length?'Диалогов: '+data.chats.length:'В этом Workspace нет сохранённых диалогов.')+(hidden?' · не показано посторонних записей: '+hidden:''));
    if(chat.chat&&!chat.chats.some(c=>c.chat_id===chat.chat&&c.status==='ok')){chat.chat=null;clearChatHistory('Выберите диалог')}
    renderChatList();
    if(chat.chat)return loadChatHistory(false);
    const saved=modelChat()?testChatSelection():null;
    const newest=chat.chats.find(c=>c.status==='ok'&&saved?.workspace===chat.workspace&&c.chat_id===saved?.chat)||chat.chats.filter(c=>c.status==='ok').at(-1);
    if(newest)return selectChat(newest.chat_id)
  }catch(e){if(epoch===chat.epoch){text('chatListState','Список диалогов не загружен');chatFailure(e)}}
}
function selectChat(id){
  if(chatEdit.mode==='rename'&&chatEdit.chatId!==id)closeChatName();
  chat.epoch++;chat.chat=id;chat.messages=[];chat.page=null;chat.olderBusy=false;
  if(modelChat()){try{localStorage.setItem(chatTurn.ordinary?'webAlarm.ordinaryChatSelection':'webAlarm.testChatSelection',JSON.stringify({workspace:chat.workspace,chat:id}))}catch(_){/* selection is a preference; blocked storage must not block history */}}
  renderChatList();clearChatHistory('Загружаем историю…');renderTurnComposer();return ((chatTurn.ordinary||chatTurn.testModelPreferences)?loadChatModel():Promise.resolve()).then(()=>loadChatHistory(false)).then(()=>checkTurn())
}
async function loadChatHistory(older){
  if(!chat.workspace||!chat.chat||(older&&(chat.olderBusy||!chat.page?.next_before)))return;
  const epoch=chat.epoch,request=++chat.historyRevision;
  let path='/ultra/chat/workspaces/'+encodeURIComponent(chat.workspace)+'/chats/'+encodeURIComponent(chat.chat)+'/messages?limit='+CHAT_PAGE;
  if(!older){chat.olderBusy=false;$('chatOlder').disabled=false}
  if(older){path+='&before='+encodeURIComponent(chat.page.next_before);chat.olderBusy=true;$('chatOlder').disabled=true}
  try{
    const data=await chatGet(path);
    if(epoch!==chat.epoch||request!==chat.historyRevision)return;
    if(!validChatHistory(data))throw Error('Некорректный ответ сервера об истории диалога');
    notice('chatError','');chat.messages=older?[...data.messages,...chat.messages]:data.messages;chat.page=data.page;
    renderChatHistory(data,older);renderChatUsage(data.usage_summary);if(!older&&chatPreferencesLoadedFor!==turnScope())await loadChatPreferences()
  }catch(e){if(epoch===chat.epoch&&request===chat.historyRevision)chatFailure(e)}
  finally{if(older&&epoch===chat.epoch&&request===chat.historyRevision){chat.olderBusy=false;$('chatOlder').disabled=false}}
}
function startChat(){if(chat.started)return;chat.started=true;return loadChatWorkspaces().then(()=>{if(!chatTurn.ordinary&&!chatTurn.testModelPreferences)return loadChatModel()})}
// Ultra Chat stage 2: create and rename a dialogue in the shared Ultra core. The write token is a second capability
// of its own scope, asked for only when the user saves a change, kept only here and sent only with these POSTs in
// its own header; the read token never goes with a write. The list is always re-read from the server afterwards.
const CHAT_WRITE_HEADER='X-WebAlarm-Ultra-Chat-Write-Token';
const chatEdit={token:null,mode:null,busy:false,workspace:null,chatId:null,expected:null,pendingId:null,initialize:false};
const CHAT_WRITE_REASON={title_changed:'Название уже изменено в другом окне. Список обновлён; нажмите «Сохранить» ещё раз, чтобы заменить новое название.',
  chat_not_found:'Диалог не найден — список обновлён.',chat_id_conflict:'Не удалось создать диалог: этот идентификатор уже занят. Откройте форму заново.',
  workspace_unavailable:'В этом Workspace нет доступной истории Ultra — изменение не выполнено.',workspace_busy:'Workspace занят другой записью — повторите через несколько секунд.',
  chats_limit_reached:'В этом Workspace слишком много диалогов.',invalid_title:'Название пустое, длиннее 200 символов или содержит перевод строки.',
  foreign_identity:'Диалог принадлежит другому Workspace — изменение запрещено.',chat_damaged:'Карточка диалога повреждена — изменение запрещено.',
  unsupported_version:'Данные сохранены более новой версией — изменение запрещено.',unsafe_storage_link:'Внутри хранилища Ultra ссылка вместо папки или файла — запись запрещена.',
  workspace_identity_changed:'В папке теперь другой Workspace Ultra — обновите список.',storage_write_failed:'Изменение не сохранено: ошибка записи на диск.',
  unknown_workspace:'Workspace больше не зарегистрирован — обновите список.'};
function newChatId(){const b=new Uint8Array(16);crypto.getRandomValues(b);return 'chat_'+Array.from(b,x=>x.toString(16).padStart(2,'0')).join('')}
function syncChatActions(){
  const w=chat.workspaces.find(x=>x.wa_workspace_id===chat.workspace);
  $('chatNew').disabled=chatEdit.busy||!w||!['ok','missing_history'].includes(w.history);
  $('chatRename').disabled=chatEdit.busy||!chat.chats.some(c=>c.chat_id===chat.chat&&c.status==='ok')
}
async function loadChatWriteAccess(){
  const c=(await api('/ui/ultra-chat/write-capability'))?.ultra_chat_write;
  if(!c||typeof c.available!=='boolean'||c.header!==CHAT_WRITE_HEADER)throw Error('Некорректный ответ сервера о праве изменения');
  chatEdit.token=c.available&&typeof c.token==='string'&&c.token.length>=32?c.token:null;
  if(!chatEdit.token)throw Object.assign(Error(c.reason==='disabled'?'Создание и переименование диалогов выключены при запуске сервера.':
    c.reason==='non_loopback_bind'?'Создание и переименование недоступны: сервер запущен не на локальном адресе.':'Создание и переименование недоступны в этом режиме сервера.'),{chatWriteUnavailable:true})
}
async function chatPost(path,body){
  if(!chatEdit.token)await loadChatWriteAccess();
  try{return await api(path,{method:'POST',headers:{[CHAT_WRITE_HEADER]:chatEdit.token},body})}
  catch(e){
    if(e.code!=='ultra_chat_write_token_invalid')throw e;
    chatEdit.token=null;await loadChatWriteAccess();// the server was restarted: the refused request wrote nothing, one repeat
    return await api(path,{method:'POST',headers:{[CHAT_WRITE_HEADER]:chatEdit.token},body})
  }
}
function openChatName(mode){
  if(chatEdit.busy||chat.renamingWorkspace?.busy)return;
  const current=chat.chats.find(c=>c.chat_id===chat.chat&&c.status==='ok');
  if(mode==='rename'?!current:$('chatNew').disabled)return;
  const initialize=mode==='create'&&chat.workspaces.find(w=>w.wa_workspace_id===chat.workspace)?.history==='missing_history';
  closeWorkspaceName();
  chat.expanded=chat.workspace;renderChatWorkspaces();
  // A new dialogue gets its ID now: saving again after a lost answer repeats the same request, never a second chat.
  Object.assign(chatEdit,{mode,workspace:chat.workspace,chatId:current&&mode==='rename'?current.chat_id:null,
    expected:mode==='rename'?current.title:null,pendingId:mode==='create'?newChatId():null,initialize});
  text('chatNameLabel',mode==='create'?'Название нового диалога (пусто — «Чат N»)':'Новое название диалога');
  notice('chatInitializeNotice',initialize?'После нажатия «Создать первый диалог» будет создано хранилище Ultra в выбранной папке и первый чат. Отмена ничего не создаёт.':'');
  text('chatNameSave',initialize?'Создать первый диалог':mode==='create'?'Создать':'Сохранить');
  $('chatNameInput').value=mode==='rename'?current.title:'';notice('chatNameError','');
  $('chatNameForm').hidden=false;$('chatNameInput').focus()
}
function closeChatName(){
  if(chatEdit.busy)return;
  Object.assign(chatEdit,{mode:null,workspace:null,chatId:null,expected:null,pendingId:null,initialize:false});
  $('chatNameForm').hidden=true;notice('chatNameError','')
}
async function saveChatName(){
  if(chatEdit.busy||!chatEdit.mode)return;
  const mode=chatEdit.mode,ws=chatEdit.workspace,initialize=chatEdit.initialize,title=String($('chatNameInput').value||'').trim();
  if(mode==='rename'&&!title){notice('chatNameError','Название не может быть пустым.');return}
  const base='/ultra/chat/workspaces/'+encodeURIComponent(ws)+'/chats';
  chatEdit.busy=true;$('chatNameSave').disabled=true;notice('chatNameError','');syncChatActions();
  let saved=null;
  try{
    const payload={chat_id:chatEdit.pendingId};if(title)payload.title=title;if(initialize)payload.initialize_workspace=true;
    const r=mode==='create'?await chatPost(base,payload):
      await chatPost(base+'/'+encodeURIComponent(chatEdit.chatId)+'/title',{title,expected_title:chatEdit.expected});
    if(!r?.chat||typeof r.chat.chat_id!=='string')throw Error('Некорректный ответ сервера об изменении диалога');
    saved=r.chat.chat_id
  }catch(e){
    notice('chatNameError',CHAT_WRITE_REASON[e.code]||(e.chatWriteUnavailable?e.message:
      'Не удалось подтвердить сохранение диалога. Обновите список перед повтором.'));
    if(['title_changed','chat_not_found','chat_id_conflict'].includes(e.code)&&ws===chat.workspace){
      await loadChatList();// what is stored now; a second «Сохранить» replaces the newer title knowingly
      const fresh=chat.chats.find(c=>c.chat_id===chatEdit.chatId&&c.status==='ok');
      if(fresh)chatEdit.expected=fresh.title
    }
  }finally{chatEdit.busy=false;$('chatNameSave').disabled=false;syncChatActions()}
  if(ws!==chat.workspace){closeChatName();return}// the user moved to another Workspace meanwhile: nothing of the old one stays
  if(!saved)return;
  closeChatName();
  chat.epoch++;chat.chat=saved;chat.messages=[];chat.page=null;chat.olderBusy=false;clearChatHistory('Загружаем историю…');
  return initialize?loadChatWorkspaces():loadChatList()
}
$('viewChat').onclick=()=>showView('chat');
async function createTestWorkspace(){
  if(!stage5Offline||!chatTurn.available||chat.creatingWorkspace)return;
  const title=$('chatTestWorkspaceTitle').value.trim();
  if(!title)return;
  chat.creatingWorkspace=true;$('chatTestWorkspaceSave').disabled=true;
  notice('chatTestWorkspaceError','');
  try{
    const result=await chatPost('/ultra/chat/workspaces',{title});
    $('chatTestWorkspaceForm').hidden=true;
    closeWorkspaceName();closeChatName();
    chat.epoch++;chat.workspace=result.wa_workspace_id;chat.expanded=chat.workspace;chat.chat=null;chat.chats=[];chat.messages=[];chat.page=null;
    clearChatHistory('Создайте диалог');await loadChatWorkspaces()
  }catch(e){
    notice('chatTestWorkspaceError','Не удалось подтвердить создание TEST Workspace. Обновите список перед повтором.')
  }finally{chat.creatingWorkspace=false;$('chatTestWorkspaceSave').disabled=false}
}
async function createChatWorkspace(){
  if(chat.creatingWorkspace||chat.renamingWorkspace?.busy||chatEdit.busy)return;
  if(chatTurn.compact)return createCompactWorkspace();
  if(stage5Offline){
    $('chatTestWorkspaceForm').hidden=false;$('chatTestWorkspaceTitle').value='';$('chatTestWorkspaceTitle').focus();
    return
  }
  let registrationStarted=false,registered=false;
  chat.creatingWorkspace=true;$('chatRegisterWorkspace').disabled=true;notice('chatError','');notice('chatWorkspaceResult','');
  try{
    const capability=(await api('/ui/capabilities'))?.folder_picker;
    if(!capability?.available||typeof capability.token!=='string'||capability.token.length<32)throw Error('picker_unavailable');
    const picked=await api('/ui/pick-workspace-folder',{method:'POST',body:{},headers:{'X-WebAlarm-Folder-Token':capability.token},timeoutMs:125000});
    if(picked?.status==='CANCELLED')return;
    if(picked?.status!=='SELECTED'||typeof picked.workspace_root!=='string'||! /^(?:[A-Za-z]:[\\/]|\\\\)/.test(picked.workspace_root))throw Error('picker_invalid');
    const root=picked.workspace_root,parts=root.replace(/[\\/]+$/,'').split(/[\\/]/),name=parts.at(-1)||'Workspace';
    registrationStarted=true;
    const result=await api('/workspaces',{method:'POST',body:{display_name:name,workspace_root:root}});
    if(typeof result?.workspace?.workspace_id!=='string')throw Error('registration_unconfirmed');
    registered=true;notice('chatWorkspaceResult','Workspace подключён. История загружается отдельно.');
    closeWorkspaceName();closeChatName();
    chat.epoch++;chat.workspace=result.workspace.workspace_id;chat.expanded=chat.workspace;chat.chat=null;chat.chats=[];chat.messages=[];chat.page=null;
    await loadChatWorkspaces();
  }catch(e){
    notice('chatError',registered?'Workspace подключён, но загрузить его данные не удалось. Нажмите «Обновить».':
      registrationStarted?(e.serverRejected&&e.httpStatus>=400&&e.httpStatus<500?
        'Сервер отклонил регистрацию Workspace. Проверьте выбранную папку и обновите список.':
        'Не удалось подтвердить регистрацию Workspace. Обновите список перед повтором. Автоматического повтора нет.'):
      'Не удалось выбрать папку Workspace. Проверьте доступность системного выбора папки.');
  }finally{chat.creatingWorkspace=false;$('chatRegisterWorkspace').disabled=false}
}
async function createPersonalChat(){
  if(chatTurn.compact)return createCompactChat();
  const target=chatTurn.personalWorkspaceId;
  const personal=chat.workspaces.find(w=>w.wa_workspace_id===target&&w.history==='ok');
  if(!chatTurn.ordinary||chatEdit.busy)return;
  chatEdit.busy=true;$('chatPersonalNew').disabled=true;
  const id=newChatId();
  try{
    if(!personal){
      const enrolled=await chatPost('/ultra/chat/personal',{});
      if(typeof enrolled?.wa_workspace_id!=='string')throw Error('Личное хранилище не подтверждено');
      await loadChatAccess();
      if(!await loadChatWorkspaces())throw Error('Личные чаты не загружены');
      if(chat.workspace!==enrolled.wa_workspace_id)await selectChatWorkspace(enrolled.wa_workspace_id);
      return;
    }
    const created=await chatPost('/ultra/chat/workspaces/'+encodeURIComponent(target)+'/chats',{chat_id:id});
    if(created?.chat?.chat_id!==id)throw Error('Личный чат не подтверждён');
    if(chat.workspace!==target){await selectChatWorkspace(target)}
    else{chat.expanded=target;renderChatWorkspaces()}
    await loadChatList();
    await selectChat(id)
  }catch(_){notice('chatError','Не удалось подтвердить создание личного чата. Проверьте список перед повтором.')}
  finally{chatEdit.busy=false;renderChatWorkspaces()}
}
$('chatPersonalNew').onclick=createPersonalChat;
$('chatRegisterWorkspace').onclick=createChatWorkspace;
$('chatTestWorkspaceForm').onsubmit=e=>{e.preventDefault();return createTestWorkspace()};
$('chatTestWorkspaceCancel').onclick=()=>{if(!chat.creatingWorkspace){$('chatTestWorkspaceForm').hidden=true;$('chatRegisterWorkspace').focus()}};
$('viewBlueprint').onclick=()=>showView('blueprint');
$('chatRefresh').onclick=()=>{loadChatModel();return loadChatWorkspaces().then(()=>checkTurn())};
$('chatOlder').onclick=()=>loadChatHistory(true);
$('chatNew').onclick=()=>chatTurn.compact?createCompactChat(chat.workspace):openChatName('create');
$('chatRename').onclick=()=>{
  if(!chatTurn.compact)return openChatName('rename');
  const c=chat.chats.find(x=>x.chat_id===chat.chat&&x.status==='ok');if(c)beginCompactName(chat.workspace,c.chat_id,c.title)
};
$('chatWorkspaceNameForm').onsubmit=e=>{e.preventDefault();return saveWorkspaceName()};
$('chatWorkspaceNameCancel').onclick=closeWorkspaceName;
$('chatWorkspaceNameInput').onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();closeWorkspaceName()}};
$('chatNameForm').onsubmit=e=>{e.preventDefault();return saveChatName()};
$('chatNameCancel').onclick=()=>closeChatName();
$('chatNameInput').onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();closeChatName()}};
$('chatComposer').onsubmit=e=>{e.preventDefault();return sendTurn()};

function setupChatComposerResize(){
  const grip=$('chatComposerGrip'), input=$('chatInput'), key='webAlarm.chatInputHeight.v1';
  let height=140, drag=null;
  const maximum=()=>Math.max(72,Math.min(420,Math.floor((window.innerHeight||900)*0.42)));
  function apply(value,save=false){
    height=Math.max(72,Math.min(maximum(),Math.round(value)));
    input.style.height=height+'px';grip.setAttribute('aria-valuenow',String(height));grip.setAttribute('aria-valuemax',String(maximum()));
    if(save)try{localStorage.setItem(key,String(height))}catch(_){}
  }
  try{const saved=localStorage.getItem(key);if(saved!==null&&Number.isFinite(Number(saved)))height=Number(saved)}catch(_){}
  apply(height);
  grip.onpointerdown=e=>{if(e.button!==0)return;e.preventDefault();drag={id:e.pointerId,y:e.clientY,height:input.getBoundingClientRect().height};grip.setPointerCapture(e.pointerId)};
  grip.onpointermove=e=>{if(drag&&drag.id===e.pointerId)apply(drag.height+drag.y-e.clientY)};
  const finish=e=>{if(drag&&drag.id===e.pointerId){drag=null;apply(height,true)}};
  grip.onpointerup=finish;grip.onpointercancel=finish;grip.onlostpointercapture=finish;
  grip.onkeydown=e=>{const delta=e.key==='ArrowUp'?16:e.key==='ArrowDown'?-16:0;if(delta||e.key==='Home'||e.key==='End'){e.preventDefault();apply(e.key==='Home'?72:e.key==='End'?maximum():height+delta,true)}};
  window.addEventListener('resize',()=>apply(height));
}

setupChatComposerResize();
$('chatSend').onclick=sendTurn;
$('evmTopmost').onclick=toggleTopmost;
$('evmExternalRefresh').onclick=()=>loadEvm();
$('evmExternalClose').onclick=()=>window.close();
$('shutdownWebAlarm').onclick=async()=>{
  const busy=chatTurn.busy||chatTurn.liveBusy||evm.liveBusy;
  if(!window.confirm('Завершить Web Alarm в этом окне? '+
      (busy?'Есть выполняющиеся операции: сервер дождётся их завершения в пределах тайм-аута. ':'')+
      'Настройки EVM, модели, история и бюджеты сохранятся.'))return;
  $('shutdownWebAlarm').disabled=true;
  try{
    if(!chatEdit.token)await loadChatWriteAccess();
    const result=await api('/ui/shutdown',{method:'POST',headers:{[CHAT_WRITE_HEADER]:chatEdit.token},body:{confirmation:'SHUTDOWN WEB ALARM'}});
    if(result.state!=='STOPPING')throw Error('Сервер не подтвердил остановку');
    text('shutdownResult','Web Alarm завершает работу. Дождитесь остановки сервера; эту вкладку можно закрыть.');
    $('shutdownResult').hidden=false;
  }catch(error){
    text('shutdownResult','Остановка не подтверждена: '+(error.message||'неизвестная ошибка'));
    $('shutdownResult').hidden=false;
    $('shutdownWebAlarm').disabled=false;
  }
};
$('cleanupInstances').onclick=async()=>{
  $('cleanupInstances').disabled=true;
  try{
    const list=await api('/ui/instances');
    const extra=(list.instances||[]).filter(x=>x.state==='EXTRA_CONFIRMED');
    const unverified=(list.instances||[]).filter(x=>x.state==='UNVERIFIED'||x.state==='LEGACY_UNVERIFIED').length;
    if(!extra.length){text('instanceResult','Доказанных лишних экземпляров нет. Неподтверждённых записей: '+unverified+'. Текущий сервер не затронут.');return}
    const description=extra.map(x=>x.profile+' · порт '+x.port+' · PID '+x.pid+' · '+(x.stale_ui?'старая версия':'та же версия')).join('\n');
    if(!window.confirm('Завершить только подтверждённые лишние экземпляры? Текущий чат останется открытым.\n'+description))return;
    if(!chatEdit.token)await loadChatWriteAccess();
    const result=await api('/ui/instances/cleanup',{method:'POST',headers:{[CHAT_WRITE_HEADER]:chatEdit.token},
      body:{confirmation:'CLEAN EXTRA WEB ALARM',instance_ids:extra.map(x=>x.instance_id)}});
    const states=(result.results||[]).map(x=>x.instance_id.slice(0,8)+': '+x.state).join('; ');
    text('instanceResult','Запрошена остановка лишних экземпляров: '+states+'. Текущий сервер и чат продолжают работу. Обновите диагностику после завершения.');
  }catch(error){text('instanceResult','Очистка не подтверждена: '+(error.message||'ошибка диагностики'))}
  finally{$('instanceResult').hidden=false;$('cleanupInstances').disabled=false}
};
async function checkPageInstance(){
  try{
    const current=await api('/ui/instance');
    const loaded=$('waUiVersion').getAttribute('content');
    if(loaded!==current.ui_version){
      text('instanceResult','Версия HTML/JS этой страницы отличается от сервера. Обновите страницу без кеша.');
      $('instanceResult').hidden=false;
    }
  }catch(_){/* Older server: diagnostics unavailable, no automatic action. */}
}
$('chatInput').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();return sendTurn()}};
$('chatTurnCheck').onclick=()=>checkTurn(true);
$('chatTurnCancel').onclick=cancelTurn;
$('chatTurnNew').onclick=()=>{if(chatTurn.state==='UNKNOWN'&&(!modelChat()||!chatTurn.busy)){
  if(modelChat()){chatTurn.dismissed.set(turnScope(),turnPending()?.key);chatTurn.state=null;$('chatTurnNew').hidden=true}
  localStorage.removeItem(turnScope());$('chatInput').value='';text('chatTurnStatus','Новый запрос. Прежний исход остаётся неизвестным.');renderTurnComposer()
}};
$('chatModelPick').onclick=()=>openPicker();
$('chatPreferencesSave').onclick=()=>saveChatPreferences();
$('chatAnswerExtended').onclick=()=>{$('chatAnswerTokens').value='20000'};
try{
  const saved=JSON.parse(localStorage.getItem('webAlarm.selection')||'{}');
  if(typeof saved.workspace==='string')view.workspace=saved.workspace;
  if(typeof saved.task==='string')view.task=saved.task;view.restoredDraft=saved.draft===true
}
catch(_){
}
setInterval(()=>{
  if(!stage5Offline&&$('autoRefresh').checked&&!document.hidden&&!view.creating)refresh();
  if(view.healthAt&&Date.now()-view.healthAt>45000){text('serverStatus','Проверка связи устарела');$('serverStatus').setAttribute('data-state','checking')}
  if(view.loadedAt&&Date.now()-view.loadedAt>45000&&view.fresh)setFresh(false,'Снимок старше 45 секунд. Обновите перед использованием NEXT SAFE ACTION.')
}
,15000);
setInterval(()=>{
  if(stage5Offline||document.hidden||evm.saving||evm.checking||evm.drag)return;
  if(EXTERNAL_MODEL||evm.view==='evm')loadEvm();
  else if(chat.started&&chatTurn.ordinary)loadChatAccess();
},8000);
showView(initialView(),true);
if(stage5Offline){
  for(const id of ['viewOperator','viewBlueprint','viewEvm','refresh'])$(id).hidden=true;
  $('autoRefresh').parentNode.hidden=true;
  $('chatRegisterWorkspace').setAttribute('title','Создать временный TEST Workspace');
  $('chatModel').setAttribute('title','Модель следующего TEST-запроса');
  $('chatModelPick').setAttribute('title','Выбрать модель следующего TEST-запроса');
  text('serverStatus','TEST · OFFLINE');$('serverStatus').setAttribute('data-state','checking');
}else refresh();
if(!stage5Offline)checkPageInstance();
</script>
</body></html>
'''

# Keep the existing client and its DOM contract intact; the editor is an isolated module.
from .blueprint_ui import install_blueprint_ui
INDEX_HTML = install_blueprint_ui(INDEX_HTML)
import hashlib
UI_VERSION = hashlib.sha256(INDEX_HTML.encode('utf-8')).hexdigest()[:12]
INDEX_HTML = INDEX_HTML.replace('__WA_UI_VERSION__', UI_VERSION)
