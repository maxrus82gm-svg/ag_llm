// Real-input check of the pinned EVM windows (CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001) and of the accepted #464 interaction,
// on the synthetic demo (tools/demo_evm_pins.py on a NEW storage for phase main: the steps expect its seeded order).
// Built from the #464 script: S01-S18 are its regression steps (S09, S10, S12 rewritten: Ctrl + click and «⧉» now give
// pinned windows that only their «×» closes); P01-P13 check the windows. tools/run_real_input.py runs the phases:
//   main      - regression and windows (a second tab, a refused write through DevTools Fetch);
//   restored  - after a server restart over the same storage: the windows come back;
//   corrupt   - after the layout part of the stored file was damaged: told, no window, the board intact.
// Headless Chrome/Edge over the DevTools protocol with Node's own WebSocket: no packages, a throw-away profile in TEMP
// (removed afterwards), background networking off; the only page is the loopback demo.
// Mouse and keys go through the browser's input pipeline (Input.dispatchMouseEvent / Input.dispatchKeyEvent): the page
// receives trusted pointer, mouse, click and key events, as from a mouse. This is still NOT a physical mouse on the
// Windows desktop: that remains a user check (report: REAL MOUSE WINDOWS NOT RUN).
// Every check is recorded (passed or not); the run goes on after a failed check. Screenshots: <out>/screenshots.
// Usage: node real_input_check.js <browser.exe> <demo url> <out dir> [main|restored|corrupt]
'use strict';
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const [browser, url, outDir, phase = 'main'] = process.argv.slice(2);
if (!['main', 'restored', 'corrupt'].includes(phase)) {console.error('phase: main | restored | corrupt'); process.exit(2);}
if (!browser || !url || !outDir) {console.error('usage: node real_input_check.js <browser.exe> <demo url> <out dir>'); process.exit(2);}
if (!/^http:\/\/127\.0\.0\.1:\d+\//.test(url)) {console.error('only a loopback demo address is allowed'); process.exit(2);}
const sleep = ms => new Promise(r => setTimeout(r, ms));
const shotsDir = path.join(outDir, 'screenshots');
fs.mkdirSync(shotsDir, {recursive: true});
const record = {task: 'CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001', phase, purpose: 'trusted browser input on the synthetic demo (not a physical mouse)',
  browser: null, steps: [], checks: 0, failed: 0, screenshots: []};
let current = null;
const check = (ok, what, value) => {
  record.checks++; if (!ok) record.failed++;
  current.checks.push({ok: !!ok, check: what, ...(value === undefined ? {} : {value})});
  if (!ok) console.log('  FAIL', what, value === undefined ? '' : JSON.stringify(value));
};

async function main() {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'claude-evmdnd-input-'));
  const child = spawn(browser, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run',
    '--no-default-browser-check', '--disable-background-networking', '--disable-component-update', '--disable-sync',
    '--disable-extensions', '--disable-default-apps', '--no-pings', '--metrics-recording-only', '--hide-scrollbars',
    '--disable-features=Translate,OptimizationHints,MediaRouter,AutofillServerCommunication', 'about:blank'], {stdio: 'ignore'});
  try {
    let port = null;
    for (let i = 0; i < 100 && !port; i++) {
      try {port = fs.readFileSync(path.join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0].trim();} catch (_) {await sleep(100);}
    }
    if (!port) throw new Error('the browser did not open its DevTools port');
    record.browser = (await (await fetch(`http://127.0.0.1:${port}/json/version`)).json()).Browser;
    const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    const ws = new WebSocket(pages.find(p => p.type === 'page').webSocketDebuggerUrl);
    await new Promise((ok, fail) => {ws.onopen = ok; ws.onerror = fail;});
    let id = 0; const waiting = new Map();
    ws.onmessage = e => {const m = JSON.parse(e.data); if (m.id && waiting.has(m.id)) {waiting.get(m.id)(m); waiting.delete(m.id);} else if (m.method) onEvent(m);};
    const call = (method, params = {}) => new Promise((ok, fail) => {
      const n = ++id; waiting.set(n, m => m.error ? fail(new Error(method + ': ' + m.error.message)) : ok(m.result));
      ws.send(JSON.stringify({id: n, method, params}));
    });
    const run = async code => {
      const r = await call('Runtime.evaluate', {expression: `(async()=>{${code}})()`, awaitPromise: true, returnByValue: true});
      if (r.exceptionDetails) throw new Error('page script failed: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
      return r.result.value;
    };
    // --- input through the browser pipeline -------------------------------------------------------------------
    let mods = 0;  // 2 = Ctrl held
    const mouse = (type, x, y, extra = {}) => call('Input.dispatchMouseEvent', {type, x, y, modifiers: mods, pointerType: 'mouse', ...extra});
    const moveTo = (x, y, held = false) => mouse('mouseMoved', x, y, held ? {button: 'left', buttons: 1} : {button: 'none', buttons: 0});
    const down = async (x, y) => {await moveTo(x, y); await mouse('mousePressed', x, y, {button: 'left', buttons: 1, clickCount: 1});};
    const up = (x, y) => mouse('mouseReleased', x, y, {button: 'left', buttons: 0, clickCount: 1});
    const click = async (x, y) => {await down(x, y); await up(x, y); await sleep(250);};
    const drag = async (from, to, steps = 8, hold = null) => {  // press, move in steps, (optionally act while held), release
      await down(...from);
      for (let i = 1; i <= steps; i++) {await moveTo(from[0] + (to[0] - from[0]) * i / steps, from[1] + (to[1] - from[1]) * i / steps, true); await sleep(16);}
      if (hold) await hold();
      await up(...to); await sleep(400);
    };
    const KEYS = {Control: ['ControlLeft', 17], Escape: ['Escape', 27], Enter: ['Enter', 13], ' ': ['Space', 32], Tab: ['Tab', 9],
      ArrowLeft: ['ArrowLeft', 37], ArrowUp: ['ArrowUp', 38], ArrowRight: ['ArrowRight', 39], ArrowDown: ['ArrowDown', 40]};
    const key = async (name, type) => {
      const [code, vk] = KEYS[name];
      if (name === 'Control') mods = type === 'keyUp' ? 0 : 2;
      const text = type !== 'keyUp' && (name === 'Enter' ? '\r' : name === ' ' ? ' ' : '');
      await call('Input.dispatchKeyEvent', {type: type === 'keyUp' ? 'keyUp' : text ? 'keyDown' : 'rawKeyDown', key: name, code,
        windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk, modifiers: mods, ...(text ? {text, unmodifiedText: text} : {})});
    };
    const press = async name => {await key(name, 'keyDown'); await key(name, 'keyUp'); await sleep(200);};
    // --- page helpers ------------------------------------------------------------------------------------------
    const size = async (width, height, scale = 1) => {await call('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: scale, mobile: false}); await sleep(300);};
    const load = async () => {
      await call('Page.navigate', {url: 'about:blank'}); await sleep(300);
      await call('Page.navigate', {url: url.replace(/#.*$/, '') + '#evm'}); await sleep(1500);
      await run(`for(let i=0;i<60&&!document.querySelector('.ccard');i++)await new Promise(r=>setTimeout(r,100));
        window.__hides=0;new MutationObserver(()=>{if(document.getElementById('evmPeek').hidden)window.__hides++})
          .observe(document.getElementById('evmPeek'),{attributes:true,attributeFilter:['hidden']});return true`);
    };
    const shot = async name => {
      await sleep(300);
      const {data} = await call('Page.captureScreenshot', {format: 'png'});
      fs.writeFileSync(path.join(shotsDir, name), Buffer.from(data, 'base64'));
      record.screenshots.push(name); current.screenshots = [...(current.screenshots || []), name];
    };
    const server = () => run(`return fetch('/ultra/model-cards').then(r=>r.json()).then(j=>({revision:j.view.revision,...j.view.sections}))`);
    const tail = ids => ids.map(x => x.split(':').pop());
    const cards = section => run(`return [...document.querySelectorAll('#${section} .ccard')].map(c=>{const r=c.querySelector('.chead').getBoundingClientRect(),
      a=c.getBoundingClientRect();return {id:c.dataset.connection.split(':').pop(),x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2),
      top:Math.round(a.top),bottom:Math.round(a.bottom),open:c.classList.contains('expanded')}})`);
    const col = name => run(`const r=document.getElementById('${name}').getBoundingClientRect();return {left:Math.round(r.left),right:Math.round(r.right),top:Math.round(r.top),bottom:Math.round(r.bottom),x:Math.round(r.left+r.width/2)}`);
    const peek = () => run(`const p=document.getElementById('evmPeek'),r=p.getBoundingClientRect();return {hidden:p.hidden,pinned:p.classList.contains('pinned'),
      hold:p.classList.contains('hold'),place:p.dataset.place||null,id:p.querySelector('.mcard')?.dataset.connection?.split(':').pop()||null,
      left:Math.round(r.left),top:Math.round(r.top),right:Math.round(r.right),bottom:Math.round(r.bottom),vw:innerWidth,vh:innerHeight,hides:window.__hides}`);
    const toTop = () => run(`const v=document.getElementById('evmView');document.querySelector('.evm-board').scrollIntoView({block:'start'});
      window.scrollTo(0,document.querySelector('.evm-board').getBoundingClientRect().top+scrollY-80);return true`);
    const into = (list, index) => run(`document.querySelectorAll('#${list} .chead')[${index}].scrollIntoView({block:'nearest'});return true`);  // before a click
    const step = async (name, fn, fresh = true) => {  // every step starts on a freshly loaded page: open cards are page state, the order is the server's
      current = {step: name, checks: []}; record.steps.push(current); console.log('step', name);
      try {if (fresh) {await load(); await toTop();} await fn();} catch (e) {current.error = String(e.message || e); record.failed++; console.log('  ERROR', current.error);}
      if (mods) await key('Control', 'keyUp');
      await moveTo(2, 2);
    };
    const inside = (p, c) => p.right > c.left && p.left < c.right;  // horizontal overlap with a column
    // --- pinned windows (CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001) -------------------------------------------------
    const pinsInfo = () => run(`return [...document.querySelectorAll('.evm-pin')].map(p=>{const r=p.getBoundingClientRect(),c=p.querySelector('.pin-close').getBoundingClientRect();
      return {id:p.dataset.connection.split(':').pop(),left:Math.round(r.left),top:Math.round(r.top),right:Math.round(r.right),bottom:Math.round(r.bottom),
      z:+p.style.zIndex,hidden:p.hidden,active:p.classList.contains('active'),close:[Math.round(c.left),Math.round(c.top),Math.round(c.right),Math.round(c.bottom)]}})`);
    const pinPart = (idTail, sel, dx = null) => run(`const p=[...document.querySelectorAll('.evm-pin')].find(p=>p.dataset.connection.endsWith(':${idTail}'));
      const r=p.querySelector('${sel}').getBoundingClientRect();return [Math.round(r.left+(${dx === null ? 'r.width/2' : dx})),Math.round(r.top+r.height/2)]`);
    const pinTitleAt = idTail => pinPart(idTail, '.pin-bar', 60);  // a point of the title, away from «×»
    const pinCloseAt = idTail => pinPart(idTail, '.pin-close');
    const pinButtonAt = (idTail, label) => run(`const p=[...document.querySelectorAll('.evm-pin')].find(p=>p.dataset.connection.endsWith(':${idTail}'));
      const b=[...p.querySelectorAll('button')].find(b=>b.innerText.includes('${label}'));b.scrollIntoView({block:'nearest'});const r=b.getBoundingClientRect();
      return [Math.round(r.left+r.width/2),Math.round(r.top+r.height/2)]`);
    const serverLayout = () => run(`return fetch('/ultra/model-cards').then(r=>r.json()).then(j=>({state:j.view.layout.state,revision:j.view.layout.revision,
      boardRevision:j.view.revision,windows:j.view.layout.windows.map(w=>({id:w.connection_id.split(':').pop(),x:w.x,y:w.y}))}))`);
    const topAt = (x, y) => run(`const e=document.elementFromPoint(${x},${y});if(!e)return null;const p=e.closest('.evm-pin');
      return e.closest('#evmPeek')?'preview':p?'pin:'+p.dataset.connection.split(':').pop():e.closest('.evm-window')?'dialog':(e.id||e.className||e.tagName)`);
    const free = async (list, idTail, sel) => {  // a point of a card that no window covers (the board scrolls, the windows stay)
      let at = null;
      for (let i = 0; i < 8; i++) {
        at = await run(`const c=[...document.querySelectorAll('#${list} .ccard')].find(c=>c.dataset.connection.endsWith(':${idTail}'));
          const b=c.querySelector('${sel}'),r=b.getBoundingClientRect(),x=Math.round(r.left+r.width/2),y=Math.round(r.top+r.height/2),e=document.elementFromPoint(x,y);
          const p=e&&e.closest('.evm-pin');
          return {x,y,free:!!e&&(e===b||b.contains(e)),below:y>innerHeight-30,top:e?(p?'pin:'+p.dataset.connection.split(':').pop():(e.id||e.className||e.tagName)):null,
            scroll:document.getElementById('evmView').scrollTop}`);
        if (at.free) return [at.x, at.y];
        await run(`document.getElementById('evmView').scrollTop+=${at.below ? 150 : -150};return true`); await sleep(150);
      }
      throw new Error('the card ' + idTail + ' stays covered: ' + JSON.stringify(at));
    };
    let events = [];
    const onEvent = m => {for (const f of events) f(m);};
    const openTab = async () => {  // a second browser tab of the same page (its own DevTools connection)
      const t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, {method: 'PUT'})).json();
      const ws2 = new WebSocket(t.webSocketDebuggerUrl);
      await new Promise((ok, fail) => {ws2.onopen = ok; ws2.onerror = fail;});
      let n2 = 0; const wait2 = new Map();
      ws2.onmessage = e => {const m = JSON.parse(e.data); if (m.id && wait2.has(m.id)) {wait2.get(m.id)(m); wait2.delete(m.id);}};
      const call2 = (method, params = {}) => new Promise((ok, fail) => {const k = ++n2; wait2.set(k, m => m.error ? fail(new Error(method + ': ' + m.error.message)) : ok(m.result));
        ws2.send(JSON.stringify({id: k, method, params}));});
      const run2 = async code => {const r = await call2('Runtime.evaluate', {expression: `(async()=>{${code}})()`, awaitPromise: true, returnByValue: true});
        if (r.exceptionDetails) throw new Error('tab 2 script failed'); return r.result.value;};
      const mouse2 = (type, x, y, extra = {}) => call2('Input.dispatchMouseEvent', {type, x, y, modifiers: 0, pointerType: 'mouse', ...extra});
      await call2('Emulation.setDeviceMetricsOverride', {width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false});
      await call2('Page.navigate', {url: url.replace(/#.*$/, '') + '#evm'}); await sleep(1500);
      await run2(`for(let i=0;i<60&&!document.querySelector('.ccard');i++)await new Promise(r=>setTimeout(r,100));return true`);
      const drag2 = async (from, to) => {
        await mouse2('mouseMoved', ...from, {button: 'none', buttons: 0}); await mouse2('mousePressed', ...from, {button: 'left', buttons: 1, clickCount: 1});
        for (let i = 1; i <= 8; i++) {await mouse2('mouseMoved', from[0] + (to[0] - from[0]) * i / 8, from[1] + (to[1] - from[1]) * i / 8, {button: 'left', buttons: 1}); await sleep(16);}
        await mouse2('mouseReleased', ...to, {button: 'left', buttons: 0, clickCount: 1}); await sleep(400);
      };
      return {run: run2, drag: drag2, close: async () => {ws2.close(); await fetch(`http://127.0.0.1:${port}/json/close/${t.id}`);}};
    };
    const A = 'gigachat_2', B = 'gigachat_3_pro', C = 'gigachat_ultra', D = 'gigachat_2_max';

    await call('Page.enable');
    await size(1400, 1000);
    await load();
    await toTop();

    if (phase === 'main') {
    if (!process.env.PINS_ONLY) {  // PINS_ONLY=1: only the window steps (for a quick repeat)
    await step('S01 the board at 1400 px: four columns, the seeded order, nothing wider than the window', async () => {
      const s = await server();
      current.server = {api: tail(s.api), favorites: tail(s.favorites), mcp: tail(s.mcp), local: tail(s.local)};
      check(JSON.stringify(tail(s.api)) === JSON.stringify(['gigachat_ultra', 'gigachat_2', 'gigachat_2_max', 'gigachat_2_pro', 'gigachat_3_lightning', 'gigachat_3_pro']), 'seeded API order (a new demo storage)', tail(s.api));
      const cols = await run(`return getComputedStyle(document.querySelector('.evm-board')).gridTemplateColumns.split(' ').length`);
      check(cols === 4, 'four columns', cols);
      check(await run(`return document.documentElement.scrollWidth<=innerWidth`), 'no horizontal scroll');
      await shot('01-board-1400.png');
    });

    await step('S02 a click opens the card in place: the cards below move down, the cards above and the scroll stay; several stay open', async () => {
      const before = await cards('evmApiList'), scroll = await run(`return document.getElementById('evmView').scrollTop`);
      await click(before[1].x, before[1].y);
      const after = await cards('evmApiList'), p = await peek();
      check(after[1].open && !after[0].open, 'the clicked card is open, the one above is not');
      check(after[0].top === before[0].top && after[1].top === before[1].top, 'the card above and the clicked card did not move', [before[1].top, after[1].top]);
      const grow = after[1].bottom - before[1].bottom;
      check(grow > 150 && after[2].top - before[2].top === grow, 'the next card moved down by exactly the growth', [grow, after[2].top - before[2].top]);
      check(p.hidden, 'no floating panel');
      check(await run(`return document.getElementById('evmView').scrollTop`) === scroll, 'no scroll jump');
      check(await run(`return document.documentElement.scrollWidth<=innerWidth&&[...document.querySelectorAll('.cexp')].every(e=>e.scrollWidth<=e.clientWidth+1)`), 'no horizontal overflow, nothing cut');
      const text = await run(`return document.querySelector('#evmApiList .ccard.expanded .cexp').innerText`);
      for (const part of ['Назначенные роли', 'Сильные стороны модели', 'Настройки', 'Проверить чат', 'Выше']) check(text.includes(part), 'the open card shows «' + part + '»');
      await into('evmApiList', 3);
      const third = (await cards('evmApiList'))[3];
      await click(third.x, third.y);
      const two = await cards('evmApiList');
      check(two[1].open && two[3].open, 'two cards open at once');
      await shot('02-two-cards-open-in-place.png');
      await into('evmApiList', 1);
      const first = (await cards('evmApiList'))[1];
      await click(first.x, first.y);
      const back = await cards('evmApiList');
      check(!back[1].open && back[3].open, 'a second click closes only that card');
      check(await run(`return document.activeElement.classList.contains('copen')`), 'focus stays on «open» after a mouse click');
    }, false);

    await step('S03 click and drag are told apart: a tremor below 6 px is a click; 7 px is a drag; a drag never opens the card', async () => {
      const s0 = await server(), c = (await cards('evmApiList'))[2];
      await down(c.x, c.y); await moveTo(c.x + 3, c.y + 2, true); await moveTo(c.x + 4, c.y + 3, true); await up(c.x + 4, c.y + 3); await sleep(300);
      let now = (await cards('evmApiList'))[2];
      check(now.open, 'a press with a 5 px tremor opened the card (a click)');
      check((await server()).revision === s0.revision, 'and saved nothing');
      await click(now.x, now.y);
      now = (await cards('evmApiList'))[2];
      await down(now.x, now.y); await moveTo(now.x, now.y + 7, true);
      check(await run(`return document.getElementById('evmView').classList.contains('dragging')&&!document.getElementById('evmGhost').hidden`), 'a 7 px move started a drag (ghost shown)');
      await moveTo(now.x, now.y, true); await up(now.x, now.y); await sleep(400);
      now = (await cards('evmApiList'))[2];
      check(!now.open, 'the release after the drag did not open the card');
      check((await server()).revision === s0.revision, 'a drop on its own place saved nothing');
    });

    await step('S04 drag inside a column: the first card to the end, the middle card to the top, the last card to the middle', async () => {
      let c = await cards('evmApiList');
      await drag([c[0].x, c[0].y], [c[5].x, c[5].bottom - 4], 10, () => shot('03-drag-inside-column-line.png'));
      let s = await server();
      check(tail(s.api)[5] === 'gigachat_ultra' && tail(s.api)[0] === 'gigachat_2', 'the first card went to the end and was saved', tail(s.api));
      check(!(await cards('evmApiList'))[5].open, 'and did not open');
      c = await cards('evmApiList');
      await drag([c[2].x, c[2].y], [c[0].x, c[0].top + 4]);
      s = await server();
      check(tail(s.api)[0] === 'gigachat_2_pro', 'the middle card went to the top', tail(s.api));
      c = await cards('evmApiList');
      await drag([c[5].x, c[5].y], [c[2].x, c[2].top + 6]);
      s = await server();
      check(tail(s.api)[2] === 'gigachat_ultra', 'the last card went to the middle', tail(s.api));
      current.order = tail(s.api);
      check(JSON.stringify(tail(s.api)) === JSON.stringify((await cards('evmApiList')).map(x => x.id)), 'the page shows what the server saved');
    });

    await step('S05 cancel: Escape during a drag, a release outside the board, a release over another column save nothing', async () => {
      const s0 = await server();
      let c = await cards('evmApiList');
      await drag([c[0].x, c[0].y], [c[3].x, c[3].y], 6, async () => {await press('Escape'); await moveTo(c[4].x, c[4].y, true);});
      check(await run(`return !document.getElementById('evmView').classList.contains('dragging')&&document.getElementById('evmGhost').hidden`), 'Escape ended the drag; moving on did not restart it');
      check(!(await cards('evmApiList'))[0].open, 'the release after Escape opened nothing');
      c = await cards('evmApiList');
      const local = await col('evmLocalCol');
      await drag([c[1].x, c[1].y], [local.x, c[1].y], 8, async () => {
        check(await run(`return document.getElementById('evmView').classList.contains('drop-none')&&document.getElementById('evmGhost').innerText.includes('Сюда нельзя')`), 'over «Локальные LLM» the API card is refused');
      });
      await drag([c[1].x, c[1].y], [700, 5]);
      const s1 = await server();
      check(s1.revision === s0.revision && JSON.stringify(s1.api) === JSON.stringify(s0.api), 'nothing was saved', [s0.revision, s1.revision]);
    });

    await step('S06 drag into «Избранное»: a reference at the place shown; again: no duplicate; MCP and local too; the source keeps it', async () => {
      const fav = await col('evmFavCol');
      let f = await cards('evmFavList'), c = await cards('evmApiList');
      const max = c.find(x => x.id === 'gigachat_2_max');
      await drag([max.x, max.y], [fav.x, f[0].top + 4], 10, async () => {
        check(await run(`return document.getElementById('evmGhost').innerText.includes('Добавить в избранное')&&document.getElementById('evmFavCol').classList.contains('drop-target')`), 'the ghost tells «Добавить в избранное»');
        await shot('04-drag-into-favourites.png');
      });
      let s = await server();
      check(tail(s.favorites)[0] === 'gigachat_2_max' && s.favorites.length === 3, 'added as the first favourite', tail(s.favorites));
      check(tail(s.api).includes('gigachat_2_max'), 'the API column keeps the model');
      check(await run(`return document.getElementById('evmNotice').innerText`) === 'Добавлено в избранное: GigaChat 2 Max', 'the toast tells it');
      c = await cards('evmApiList'); f = await cards('evmFavList');
      const again = c.find(x => x.id === 'gigachat_2_max');
      await drag([again.x, again.y], [fav.x, f[0].top + 4]);
      s = await server();
      check(s.favorites.length === 3, 'dropping a favourite again at its place: no duplicate', tail(s.favorites));
      const mcp = (await cards('evmMcpList'))[0]; f = await cards('evmFavList');
      await drag([mcp.x, mcp.y], [fav.x, f[2].bottom + 10]);
      const local = (await cards('evmLocalList'))[1]; f = await cards('evmFavList');
      await drag([local.x, local.y], [fav.x, f[1].top + 6]);
      s = await server();
      current.favorites = tail(s.favorites);
      check(JSON.stringify(tail(s.favorites)) === JSON.stringify(['gigachat_2_max', 'qwen-14b', 'gigachat_2', 'gigachat_3_pro', 'planner-agent']), 'MCP to the end, local into the middle', tail(s.favorites));
      check(s.mcp.length === 2 && s.local.length === 2, 'their own columns keep them');
      check(new Set(s.favorites).size === s.favorites.length, 'never a duplicate');
      f = await cards('evmFavList');
      await drag([f[4].x, f[4].y], [fav.x, f[0].top + 4]);
      s = await server();
      check(tail(s.favorites)[0] === 'planner-agent', 'a favourite moves inside its column', tail(s.favorites));
      f = await cards('evmFavList'); const apiCol = await col('evmApiCol'), before = s.revision;
      await drag([f[0].x, f[0].y], [apiCol.x, f[0].y]);
      check((await server()).revision === before, 'a favourite is never dropped into a source column');
    });

    await step('S07 a toast never moves the board', async () => {
      const top = await run(`return Math.round(document.querySelector('.evm-board').getBoundingClientRect().top)`);
      const fav = await col('evmFavCol'), c = await cards('evmApiList'), f = await cards('evmFavList');
      const pro = c.find(x => x.id === 'gigachat_2_pro');
      await drag([pro.x, pro.y], [fav.x, f[f.length - 1].bottom + 10]);
      const after = await run(`const n=document.getElementById('evmNotice');return {top:Math.round(document.querySelector('.evm-board').getBoundingClientRect().top),
        shown:!n.hidden,text:n.innerText,fixed:getComputedStyle(n.parentElement).position}`);
      check(after.shown && after.fixed === 'fixed', 'the toast is shown over the window', after);
      check(after.top === top, 'the board did not move', [top, after.top]);
      await shot('05-toast-board-still.png');
    });

    await step('S08 Ctrl + hover: the side panel of every column edge card is beside its column, inside the window; switches without a blink', async () => {
      await run(`window.__hides=0;return true`);
      const rows = [];
      for (const [list, colId] of [['evmFavList', 'evmFavCol'], ['evmApiList', 'evmApiCol'], ['evmMcpList', 'evmMcpCol'], ['evmLocalList', 'evmLocalCol']]) {
        const c = await cards(list), column = await col(colId);
        for (const card of [c[0], c[c.length - 1]]) {
          await moveTo(card.x, card.y); await key('Control', 'keyDown'); await sleep(250);
          const p = await peek();
          rows.push({list, card: card.id, place: p.place, panel: [p.left, p.top, p.right, p.bottom]});
          check(!p.hidden && p.id === card.id, 'Ctrl over ' + card.id + ' shows its panel');
          check(p.left >= 0 && p.top >= 0 && p.right <= p.vw && p.bottom <= p.vh, 'inside the window: ' + card.id, [p.left, p.top, p.right, p.bottom]);
          check(!inside(p, column), 'not over its own column: ' + card.id, p.place);
          check((list === 'evmFavList' || list === 'evmApiList') ? p.place === 'right' : p.place === 'left', 'left columns open to the right, right ones to the left: ' + card.id, p.place);
          if (list === 'evmApiList' && card === c[0]) await shot('06-ctrl-preview-api-right.png');
          if (list === 'evmLocalList' && card === c[0]) await shot('07-ctrl-preview-local-left.png');
          await key('Control', 'keyUp'); await sleep(200);
          check((await peek()).hidden, 'releasing Ctrl closes it: ' + card.id);
        }
      }
      current.places = rows;
      const c = await cards('evmApiList');
      await run(`window.__hides=0;return true`);
      await moveTo(c[0].x, c[0].y); await key('Control', 'keyDown'); await sleep(200);
      for (const card of c.slice(1, 4)) {await moveTo(card.x, card.y); await sleep(60);}
      const p = await peek();
      check(p.id === c[3].id && p.hides === 0, 'moving over three cards with Ctrl switched the panel without hiding it', [p.id, p.hides]);
      await key('Control', 'keyUp');
      await moveTo(c[0].x, c[0].y); await sleep(300);
      check((await peek()).hidden, 'a plain hover shows nothing');
    });

    await step('S09 Ctrl + click pins the model in its own window; Ctrl release, leaving, a button inside and Escape keep it; only «×» closes it', async () => {
      const c = await cards('evmMcpList');
      await key('Control', 'keyDown'); await click(c[0].x, c[0].y); await key('Control', 'keyUp'); await sleep(200);
      let w = await pinsInfo();
      check(w.length === 1 && w[0].id === c[0].id, 'one pinned window of that model', w);
      check(!(await cards('evmMcpList'))[0].open, 'Ctrl + click does not open the card in place');
      check((await peek()).hidden, 'no preview beside it');
      await moveTo(5, 500); await sleep(300);
      check((await pinsInfo()).length === 1, 'stays when the pointer leaves');
      await click(...(await pinButtonAt(c[0].id, 'Ниже'))); await sleep(300);
      w = await pinsInfo();
      check(w.length === 1 && w[0].id === c[0].id, 'a button inside («Ниже») keeps the window on the same model');
      const s = await server();
      check(tail(s.mcp)[1] === c[0].id, 'and moved the card', tail(s.mcp));
      await press('Escape');
      check((await pinsInfo()).length === 1, 'Escape does not close a pinned window');
      await click(...(await pinCloseAt(c[0].id))); await sleep(300);
      check((await pinsInfo()).length === 0, '«×» closes it');
      check((await serverLayout()).windows.length === 0, 'and the saved layout forgets it');
    });

    await step('S10 a card drag closes the preview and keeps it closed; a pinned window stays where it is (faded, the pointer goes through)', async () => {
      let c = await cards('evmApiList');
      await moveTo(c[0].x, c[0].y); await key('Control', 'keyDown'); await sleep(200);
      check(!(await peek()).hidden, 'preview open');
      await drag([c[0].x, c[0].y], [c[2].x, c[2].y + 4], 8, async () => {
        check((await peek()).hidden, 'the drag closed it');
        await moveTo(c[1].x, c[1].y, true); await sleep(150);
        check((await peek()).hidden, 'Ctrl + hover during the drag does not bring it back');
      });
      await key('Control', 'keyUp');
      check((await peek()).hidden, 'nothing reopened after the drop');
      c = await cards('evmApiList');
      await click(...(await free('evmApiList', c[3].id, '.cquick')));
      const before = await pinsInfo();
      check(before.length === 1 && before[0].id === c[3].id, '«⧉» pinned a window', before);
      c = await cards('evmApiList');
      await drag([c[0].x, c[0].y], [c[1].x, c[1].y + 4], 8, async () => {
        const st = await run(`return [getComputedStyle(document.getElementById('evmPins')).opacity,getComputedStyle(document.querySelector('.evm-pin')).pointerEvents]`);
        check(st[0] === '0.25' && st[1] === 'none', 'during the drag the window fades and lets the pointer through', st);
      });
      const after = await pinsInfo();
      check(JSON.stringify(after.map(p => [p.id, p.left, p.top])) === JSON.stringify(before.map(p => [p.id, p.left, p.top])), 'and stays where it was', after);
      check(await run(`return getComputedStyle(document.getElementById('evmPins')).opacity`) === '1', 'full opacity again');
      await click(...(await pinCloseAt(after[0].id))); await sleep(300);
    });

    await step('S11 buttons never start a drag; the buttons of an open card work', async () => {
      const s0 = await server(), star = await run(`const b=document.querySelectorAll('#evmApiList .star')[1].getBoundingClientRect();return [b.left+b.width/2,b.top+b.height/2]`);
      await down(...star); for (let i = 1; i <= 5; i++) {await moveTo(star[0], star[1] + i * 10, true); await sleep(16);}
      check(await run(`return !document.getElementById('evmView').classList.contains('dragging')`), 'a press on the star and a move did not drag');
      await up(star[0], star[1] + 50); await sleep(400);
      check(JSON.stringify(await server()) === JSON.stringify(s0) && !(await cards('evmApiList')).some(x => x.open), 'and changed nothing, opened nothing');
      const c = await cards('evmApiList');
      await click(c[0].x, c[0].y);
      const b = await run(`const b=[...document.querySelectorAll('#evmApiList .ccard.expanded .cexp button')].find(b=>b.innerText.includes('Настройки')).getBoundingClientRect();return [b.left+b.width/2,b.top+b.height/2]`);
      await down(...b); for (let i = 1; i <= 4; i++) {await moveTo(b[0], b[1] - i * 12, true); await sleep(16);}
      check(await run(`return !document.getElementById('evmView').classList.contains('dragging')&&document.getElementById('evmSettingsWindow').hidden`), 'a press on «Настройки» and a move did not drag');
      await up(b[0], b[1] - 48); await sleep(300);
      check((await cards('evmApiList'))[0].open, 'the open card stays open');
      await click(...b);
      check(await run(`return !document.getElementById('evmSettingsWindow').hidden`), '«Настройки» opened the settings window');
      await press('Escape');
      check(await run(`return document.getElementById('evmSettingsWindow').hidden&&document.activeElement.innerText.includes('Настройки')`), 'Escape closed it; the keyboard is back on «Настройки»');
      check((await cards('evmApiList'))[0].open, 'the card stayed open');
      await click(c[0].x, c[0].y);
    });

    await step('S12 keyboard: Enter / Space open and close in place; «⧉» opens a window with the focus in it; arrows move it; Escape keeps it; «×» returns the focus', async () => {
      await run(`document.querySelectorAll('#evmApiList .copen')[1].focus();return true`);
      await press('Enter');
      check((await cards('evmApiList'))[1].open, 'Enter opened the card in place');
      await press(' ');
      check(!(await cards('evmApiList'))[1].open, 'Space closed it');
      await press('Tab');
      check(await run(`return document.activeElement.classList.contains('cquick')`), 'Tab reaches «⧉»');
      await press('Enter');
      check(await run(`return document.querySelectorAll('.evm-pin').length===1&&document.activeElement.classList.contains('evm-pin')`), '«⧉» opened a window with the focus inside');
      await press('Tab');
      check(await run(`return document.activeElement.classList.contains('pin-bar')`), 'Tab reaches its title');
      const before = (await pinsInfo())[0];
      await press('ArrowLeft'); await press('ArrowDown'); await sleep(700);
      const after = (await pinsInfo())[0], saved = (await serverLayout()).windows[0];
      check(after.left === before.left - 16 && after.top === before.top + 16, 'arrows moved the window', [before.left, before.top, after.left, after.top]);
      check(saved && saved.x === after.left && saved.y === after.top, 'and the place was saved', saved);
      await press('Escape');
      check((await pinsInfo()).length === 1, 'Escape keeps it');
      await press('Tab');
      check(await run(`return document.activeElement.classList.contains('pin-close')`), 'Tab reaches «×»');
      await press('Enter');
      check(await run(`return document.querySelectorAll('.evm-pin').length===0&&document.activeElement.classList.contains('cquick')`), '«×» closed it and gave the focus back to «⧉»');
    });

    await step('S13 a write refused by the server (changed in another window): the order goes back and the reason is told', async () => {
      const s0 = await server();
      await run(`await fetch('/ultra/model-cards/view',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({base_revision:${s0.revision},section:'local',order:${JSON.stringify(s0.local)}.slice().reverse()})});return true`);  // another window
      const c = await cards('evmApiList');
      await drag([c[0].x, c[0].y], [c[3].x, c[3].y + 4]);
      await sleep(500);
      const s1 = await server(), shown = (await cards('evmApiList')).map(x => x.id);
      check(JSON.stringify(tail(s1.api)) === JSON.stringify(tail(s0.api)), 'the API order was not changed on the server');
      check(JSON.stringify(shown) === JSON.stringify(tail(s1.api)), 'the page shows the saved order again', shown);
      check((await run(`return document.getElementById('evmError').innerText`)).includes('уже изменились в другом окне'), 'the reason is told');
    });

    await step('S14 reload keeps the order and the favourites', async () => {
      const s = await server();
      await load(); await toTop();
      const shown = {api: (await cards('evmApiList')).map(x => x.id), favorites: (await cards('evmFavList')).map(x => x.id)};
      check(JSON.stringify(shown.api) === JSON.stringify(tail(s.api)) && JSON.stringify(shown.favorites) === JSON.stringify(tail(s.favorites)), 'after a reload the page shows the saved board', shown);
    });

    await step('S15 reduced motion: no transitions', async () => {
      await call('Emulation.setEmulatedMedia', {features: [{name: 'prefers-reduced-motion', value: 'reduce'}]});
      const t = await run(`return [getComputedStyle(document.getElementById('evmPeek')).transitionDuration,getComputedStyle(document.querySelector('.ccard')).transitionDuration,getComputedStyle(document.getElementById('evmGhost')).transform]`);
      check(t[0] === '0s' && t[1] === '0s' && t[2] === 'none', 'transitions off, the ghost is not tilted', t);
      await call('Emulation.setEmulatedMedia', {features: []});
    });

    await step('S16 150 %: a 1400 x 1000 screen at 150 % zoom (933 x 667 CSS px); open card and side panel inside the window', async () => {
      await size(933, 667, 1.5); await load(); await toTop();
      check(await run(`return getComputedStyle(document.querySelector('.evm-board')).gridTemplateColumns.split(' ').length`) === 2, 'two columns');
      const c = await cards('evmApiList');
      await click(c[0].x, c[0].y);
      check(await run(`return document.documentElement.scrollWidth<=innerWidth&&[...document.querySelectorAll('.cexp')].every(e=>e.scrollWidth<=e.clientWidth+1)`), 'no horizontal overflow at 150 %');
      const m = (await cards('evmMcpList'))[0];
      await run(`document.querySelector('#evmMcpList .ccard').scrollIntoView({block:'center'});return true`); await sleep(200);
      const mm = (await cards('evmMcpList'))[0], column = await col('evmMcpCol');
      await moveTo(mm.x, mm.y); await key('Control', 'keyDown'); await sleep(250);
      const p = await peek();
      current.panel = p;
      check(!p.hidden && p.left >= 0 && p.right <= p.vw && p.top >= 0 && p.bottom <= p.vh && !inside(p, column), 'the panel is beside its column and inside the window', p);
      await shot('08-zoom-150-open-card-and-panel.png');
      await key('Control', 'keyUp');
      void m;
    });

    await step('S17 390 px: one column, the card opens in place, the Ctrl preview is a sheet that leaves the card visible', async () => {
      await size(390, 844); await load();
      const below = (index, gap) => run(`const h=document.querySelector('header.top').getBoundingClientRect().bottom,  // under the sticky header
        c=document.querySelectorAll('#evmApiList .chead')[${index}];window.scrollBy(0,c.getBoundingClientRect().top-h-${gap});return Math.round(h)`);
      current.header_bottom = await below(0, 16); await sleep(200);
      let c = await cards('evmApiList');
      await click(c[0].x, c[0].y);
      check((await cards('evmApiList'))[0].open, 'the card opened in place');
      check(await run(`return document.documentElement.scrollWidth<=innerWidth&&[...document.querySelectorAll('.cexp')].every(e=>e.scrollWidth<=e.clientWidth+1)`), 'no horizontal overflow at 390 px');
      await shot('09-narrow-390-open-in-place.png');
      await below(1, 220); await sleep(200);
      c = await cards('evmApiList');
      await moveTo(c[1].x, c[1].y); await key('Control', 'keyDown'); await sleep(300);  // the Ctrl preview («⧉» now gives a pinned window)
      const p = await peek(), head = await run(`const r=document.querySelectorAll('#evmApiList .chead')[1].getBoundingClientRect();return [Math.round(r.top),Math.round(r.bottom)]`);
      current.sheet = {p, head};
      check(['below', 'above'].includes(p.place), 'a sheet', p.place);
      check(p.left >= 0 && p.right <= p.vw && p.top >= 0 && p.bottom <= p.vh, 'inside the window', p);
      check(p.top >= head[1] || p.bottom <= head[0], 'the card itself stays visible', [p.top, p.bottom, head]);
      await shot('10-narrow-390-sheet.png');
      await press('Escape');
    });

    await step('S18 the edge of the board scrolls by itself during a drag (1400 x 700)', async () => {
      await size(1400, 700); await load();
      const v = await run(`const v=document.getElementById('evmView');v.scrollTop=0;return [v.scrollHeight,v.clientHeight]`);
      const c = await cards('evmApiList'), fav = await col('evmFavCol');
      void fav;
      await down(c[0].x, c[0].y); await moveTo(c[0].x, c[0].y + 20, true); await moveTo(c[0].x, 690, true);
      for (let i = 0; i < 20; i++) {await moveTo(c[0].x, 690 + (i % 2), true); await sleep(40);}
      const scrolled = await run(`return document.getElementById('evmView').scrollTop`);
      await press('Escape'); await up(c[0].x, 690); await sleep(300);
      check(v[0] <= v[1] + 1 || scrolled > 0, 'near the bottom edge the board scrolled', {scrolled, scrollHeight: v[0], clientHeight: v[1]});
    });

    }
      // --- pinned windows ---------------------------------------------------------------------------------------
      await size(1400, 1000);
      await step('P01 three models pinned three ways (⧉, Ctrl + click, a press on the preview): three independent windows', async () => {
        await run(`document.getElementById('evmView').scrollTop=0;return true`);
        await click(...(await free('evmApiList', A, '.cquick'))); await sleep(200);
        await key('Control', 'keyDown'); await click(...(await free('evmApiList', B, '.cname'))); await key('Control', 'keyUp'); await sleep(200);
        await moveTo(...(await free('evmApiList', C, '.cname'))); await key('Control', 'keyDown'); await sleep(300);
        const p = await peek();
        check(!p.hidden && p.id === C, 'Ctrl + hover shows the preview of C', p);
        await click(p.left + 60, p.top + 50); await key('Control', 'keyUp'); await sleep(400);  // a press on its model name
        const w = await pinsInfo();
        check(w.length === 3 && [A, B, C].every(id => w.filter(x => x.id === id).length === 1), 'three windows: A, B and C, one each', w.map(x => x.id));
        check((await peek()).hidden, 'the preview became window C');
        const lay = await serverLayout();
        check(lay.windows.length === 3 && lay.boardRevision === (await server()).revision, 'three windows saved; the board revision untouched', lay);
        await shot('11-three-windows-just-pinned.png');
      });

      await step('P02 each window moves by its title to its own place, side by side; none moves by itself; each place is saved on release', async () => {
        const targets = {[A]: [20, 81], [B]: [480, 81], [C]: [940, 81]};
        for (const id of [C, B, A]) {  // the top one first: a window under another is reached after
          const from = await pinTitleAt(id), w = (await pinsInfo()).find(x => x.id === id);
          await drag(from, [targets[id][0] + from[0] - w.left, targets[id][1] + from[1] - w.top], 12);
        }
        const w = await pinsInfo(), lay = await serverLayout();
        for (const id of [A, B, C]) {
          const p = w.find(x => x.id === id), s = lay.windows.find(x => x.id === id);
          check(p && Math.abs(p.left - targets[id][0]) <= 1 && p.top >= 73 && p.top <= 90, 'window ' + id + ' stands where it was dropped', p);
          check(s && s.x === p.left && s.y === p.top, 'and its place is saved', s);
        }
        await sleep(800);
        const again = await pinsInfo();
        check(JSON.stringify(again.map(x => [x.id, x.left, x.top])) === JSON.stringify(w.map(x => [x.id, x.left, x.top])), 'nothing moves by itself');
        await shot('12-three-windows-side-by-side.png');
      }, false);

      await step('P03 the same model from «Избранное» and from its column: still one window A, brought forward', async () => {
        const before = await pinsInfo();
        await click(...(await free('evmFavList', A, '.cquick'))); await sleep(200);
        await key('Control', 'keyDown'); await click(...(await free('evmApiList', A, '.cname'))); await key('Control', 'keyUp'); await sleep(200);
        const w = await pinsInfo(), a = w.find(x => x.id === A);
        check(w.length === 3, 'still three windows', w.map(x => x.id));
        check(a.z === Math.max(...w.map(x => x.z)) && a.active, 'A came to the top', w.map(x => [x.id, x.z]));
        check(a.left === before.find(x => x.id === A).left && a.top === before.find(x => x.id === A).top, 'and did not move');
        check((await serverLayout()).windows.length === 3, 'no new window saved');
      }, false);

      await step('P04 the Ctrl preview of D stands above the pinned windows; releasing Ctrl closes only the preview', async () => {
        const from = await pinTitleAt(C), c0 = (await pinsInfo()).find(x => x.id === C);
        await drag(from, [940 + from[0] - c0.left, 560 + from[1] - c0.top], 12);  // C goes lower, where previews of the API column appear
        await moveTo(...(await free('evmApiList', D, '.cname'))); await key('Control', 'keyDown'); await sleep(300);
        const p = await peek(), c = (await pinsInfo()).find(x => x.id === C);
        check(!p.hidden && p.id === D, 'the preview of D', p);
        const x = Math.round((Math.max(p.left, c.left) + Math.min(p.right, c.right)) / 2), y = Math.round((Math.max(p.top, c.top) + Math.min(p.bottom, c.bottom)) / 2);
        check(Math.min(p.right, c.right) > Math.max(p.left, c.left) && Math.min(p.bottom, c.bottom) > Math.max(p.top, c.top), 'the preview overlaps window C', [p, c]);
        check(await topAt(x, y) === 'preview', 'where they overlap, the preview is on top', [x, y]);
        check((await pinsInfo()).length === 3, 'A, B and C stay');
        await shot('13-preview-above-pinned-windows.png');
        await key('Control', 'keyUp'); await sleep(250);
        check((await peek()).hidden, 'releasing Ctrl closed the preview');
        check(await topAt(x, y) === 'pin:' + C, 'window C is there again');
        check((await pinsInfo()).length === 3, 'A, B and C are still open');
      }, false);

      await step('P05 Escape, a click outside, another view and a lost focus never close a pinned window', async () => {
        const before = await pinsInfo();
        await press('Escape');
        check(await topAt(1390, 500) !== null && !String(await topAt(1390, 500)).startsWith('pin:'), 'an empty point outside the windows');
        await click(1390, 500);
        await click(...(await run(`const r=document.getElementById('viewChat').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]`))); await sleep(600);
        check(await run(`return document.getElementById('evmView').hidden&&document.querySelectorAll('.evm-pin').length===3`), 'another view: EVM and its windows are hidden, not closed');
        await click(...(await run(`const r=document.getElementById('viewEvm').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]`))); await sleep(900);
        await run(`window.dispatchEvent(new Event('blur'));return true`);  // a synthetic blur (a real one is covered by the page tests)
        const after = await pinsInfo();
        check(JSON.stringify(after.map(x => [x.id, x.left, x.top, x.hidden])) === JSON.stringify(before.map(x => [x.id, x.left, x.top, x.hidden])), 'the same three windows at the same places', after);
        check((await serverLayout()).windows.length === 3, 'none was closed in the saved layout');
      }, false);

      await step('P06 «×» closes exactly window B; pinned again, B is exactly one new window', async () => {
        await click(...(await pinCloseAt(B))); await sleep(300);
        let w = await pinsInfo();
        check(w.length === 2 && !w.some(x => x.id === B), 'A and C stay', w.map(x => x.id));
        check(!(await serverLayout()).windows.some(x => x.id === B), 'B left the saved layout');
        await click(...(await free('evmApiList', B, '.cquick'))); await sleep(300);
        w = await pinsInfo();
        check(w.length === 3 && w.filter(x => x.id === B).length === 1, 'exactly one new window B', w.map(x => x.id));
        const from = await pinTitleAt(B), b = w.find(x => x.id === B);
        await drag(from, [480 + from[0] - b.left, 81 + from[1] - b.top], 12);
      }, false);

      await step('P07 a moved window and the whole set come back after a page reload, in the saved stacking order', async () => {
        const from = await pinTitleAt(A), a = (await pinsInfo()).find(x => x.id === A);
        await drag(from, [40 + from[0] - a.left, 140 + from[1] - a.top], 12);
        const before = await pinsInfo(), lay = await serverLayout();
        check(lay.windows.find(x => x.id === A)?.x === 40, 'A saved at its new place', lay.windows);
        await load();
        const after = await pinsInfo();
        check(JSON.stringify(after.map(x => [x.id, x.left, x.top]).sort()) === JSON.stringify(before.map(x => [x.id, x.left, x.top]).sort()), 'the same windows at the same places', [before, after]);
        const order = [...after].sort((p, q) => p.z - q.z).map(x => x.id);
        check(JSON.stringify(order) === JSON.stringify(lay.windows.map(x => x.id)), 'in the saved stacking order', [order, lay.windows.map(x => x.id)]);
      }, false);

      await step('P08 390 px and 150 %: every window inside the screen, title and «×» reachable; back at 1400 px each is where it was', async () => {
        const wide = await pinsInfo();
        for (const [w, hgt, scale, name] of [[390, 844, 1, '14-narrow-390-windows.png'], [933, 667, 1.5, '15-zoom-150-windows.png']]) {
          await size(w, hgt, scale); await sleep(400);
          const ps = await pinsInfo(), lim = await run(`return Math.round(document.querySelector('header.top').getBoundingClientRect().bottom)`);
          for (const p of ps) check(p.left >= 0 && p.right <= w && p.top >= lim && p.close[2] <= w && p.close[3] <= hgt, `${w} px: ${p.id} inside, «×» reachable`, p);
          const top = [...ps].sort((p, q) => q.z - p.z)[0], cx = Math.round((top.close[0] + top.close[2]) / 2), cy = Math.round((top.close[1] + top.close[3]) / 2);
          check(await run(`const e=document.elementFromPoint(${cx},${cy});return !!e&&!!e.closest('.pin-close')`), `${w} px: «×» of the top window takes the click`);
          await shot(name);
        }
        await size(1400, 1000); await sleep(400);
        const back = await pinsInfo();
        check(JSON.stringify(back.map(x => [x.id, x.left, x.top])) === JSON.stringify(wide.map(x => [x.id, x.left, x.top])), 'back at 1400 px every window is where the user put it', back);
      }, false);

      await step('P09 «Настройки» and «Проверить чат» work from a window; dialogs stand above every window; Escape closes the dialog only', async () => {
        await click(...(await pinButtonAt(A, 'Настройки'))); await sleep(300);
        check(await run(`return !document.getElementById('evmSettingsWindow').hidden`), 'the settings dialog opened');
        check(await run(`const e=document.elementFromPoint(700,500);return !!e&&!!e.closest('.evm-backdrop')`), 'the dialog layer is above the windows');
        await press('Escape'); await sleep(200);
        check(await run(`return document.getElementById('evmSettingsWindow').hidden&&document.querySelectorAll('.evm-pin').length===3`), 'Escape closed the dialog, the windows stay');
        check(await run(`return document.activeElement.innerText.includes('Настройки')&&!!document.activeElement.closest('.evm-pin')`), 'the keyboard is back on «Настройки» of the window');
        await click(...(await pinButtonAt(A, 'Проверить чат'))); await sleep(300);
        check(await run(`return !document.getElementById('evmCheckWindow').hidden`), 'the check dialog opened');
        await press('Escape'); await sleep(200);
        check((await pinsInfo()).length === 3, 'the windows stay');
      }, false);

      await step('P10 two tabs move different windows: the server keeps both moves, no window is lost', async () => {
        const tab2 = await openTab();
        const w2 = await tab2.run(`return [...document.querySelectorAll('.evm-pin')].map(p=>p.dataset.connection.split(':').pop())`);
        check(w2.length === 3, 'the second tab restored the same three windows', w2);
        const fromC = await pinTitleAt(C), c = (await pinsInfo()).find(x => x.id === C);
        await drag(fromC, [900 + fromC[0] - c.left, 600 + fromC[1] - c.top], 10);  // tab 1 moves C
        const a2 = await tab2.run(`const p=[...document.querySelectorAll('.evm-pin')].find(p=>p.dataset.connection.endsWith(':${A}'));
          const r=p.querySelector('.pin-bar').getBoundingClientRect(),q=p.getBoundingClientRect();return [r.left+60,r.top+r.height/2,q.left,q.top]`);
        await tab2.drag([a2[0], a2[1]], [100 + a2[0] - a2[2], 300 + a2[1] - a2[3]]);  // tab 2 has not seen C move; it moves A
        const lay = await serverLayout();
        check(lay.windows.length === 3 && lay.windows.find(x => x.id === C)?.x === 900 && lay.windows.find(x => x.id === A)?.x === 100, 'both moves kept', lay.windows);
        await load();
        const w = await pinsInfo();
        check(w.find(x => x.id === C)?.left === 900 && w.find(x => x.id === A)?.left === 100, 'tab 1 shows both after a reload', w);
        await tab2.close();
      }, false);

      await step('P11 a refused layout write is told; the window stays where it was put; the server keeps the last saved place', async () => {
        await call('Fetch.enable', {patterns: [{urlPattern: '*/ultra/model-cards/layout*'}]});
        events = [m => {if (m.method === 'Fetch.requestPaused') call('Fetch.fulfillRequest', {requestId: m.params.requestId, responseCode: 409,
          responseHeaders: [{name: 'Content-Type', value: 'application/json'}],
          body: Buffer.from(JSON.stringify({error: {code: 'model_cards_state_error', message: 'synthetic refusal'}})).toString('base64')});}];
        const from = await pinTitleAt(B), b = (await pinsInfo()).find(x => x.id === B);
        await drag(from, [600 + from[0] - b.left, 500 + from[1] - b.top], 10); await sleep(400);
        events = []; await call('Fetch.disable');
        const told = await run(`return document.getElementById('evmError').innerText`);
        check(told.includes('Расположение окна не сохранено') && told.includes('model_cards_state_error'), 'the refusal is told', told);
        const now = (await pinsInfo()).find(x => x.id === B);
        check(now.left === 600 && now.top === 500, 'the window stays where it was put', now);
        const lay = await serverLayout();
        check(lay.windows.find(x => x.id === B)?.x === 480, 'the server still has the last saved place', lay.windows);
        await load();
        const shown = await pinsInfo();
        fs.writeFileSync(path.join(outDir, 'pins_expected.json'), JSON.stringify({windows: lay.windows,
          shown: shown.map(x => ({id: x.id, left: x.left, top: x.top, z: x.z}))}) + '\n');
        check(shown.find(x => x.id === B)?.left === 480, 'after a reload B is at its last saved place', shown);
      }, false);
    }
    if (phase === 'restored') {
      await step('P12 after a server restart the saved windows come back where they were left, in their stacking order; the board is intact', async () => {
        const expected = JSON.parse(fs.readFileSync(path.join(outDir, 'pins_expected.json'), 'utf8'));
        const lay = await serverLayout(), w = await pinsInfo();
        check(JSON.stringify(lay.windows) === JSON.stringify(expected.windows), 'the restarted server has the same layout', [lay.windows, expected.windows]);
        for (const s of expected.windows) {const p = w.find(x => x.id === s.id); check(p && p.left === s.x && p.top === s.y, 'window ' + s.id + ' at its saved place', p);}
        const order = [...w].sort((p, q) => p.z - q.z).map(x => x.id);
        check(JSON.stringify(order) === JSON.stringify(expected.windows.map(x => x.id)), 'in the saved stacking order', order);
        check((await cards('evmApiList')).length === 6, 'the board is intact');
        await shot('16-restored-after-server-restart.png');
      }, false);
    }
    if (phase === 'corrupt') {
      await step('P13 a damaged saved layout is told, gives no window and leaves the board intact; the next window starts the layout again', async () => {
        check((await pinsInfo()).length === 0, 'no window from a damaged layout');
        check((await run(`return document.getElementById('evmError').innerText`)).includes('Сохранённое расположение окон повреждено'), 'the damage is told');
        const lay = await serverLayout();
        check(lay.state === 'CORRUPT' && lay.windows.length === 0, 'the server reports it', lay);
        const s = await server();
        check(s.api.length === 6 && s.favorites.length > 0, 'the board order and favourites are intact', {api: s.api.length, favorites: s.favorites.length});
        await shot('17-damaged-layout-told.png');
        await run(`document.getElementById('evmView').scrollTop=0;return true`);
        await click(...(await free('evmApiList', A, '.cquick'))); await sleep(400);
        const again = await serverLayout();
        check(again.state === 'SAVED' && again.windows.length === 1 && again.windows[0].id === A, 'the next window starts the layout again', again);
      }, false);
    }

    fs.writeFileSync(path.join(outDir, `real_input_${phase}.json`), JSON.stringify(record, null, 1) + '\n');
    console.log(JSON.stringify({checks: record.checks, failed: record.failed, screenshots: record.screenshots.length}));
    ws.close();
  } finally {
    child.kill();
    await sleep(800);
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 300});
  }
}
main().catch(e => {console.error(String(e.message || e)); process.exit(1);});
