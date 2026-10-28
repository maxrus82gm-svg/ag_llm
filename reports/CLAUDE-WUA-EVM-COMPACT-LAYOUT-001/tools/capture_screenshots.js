// PNG screenshots of the compact EVM from the synthetic demo (tools/demo_evm_board.py must be running).
// Headless Chrome/Edge over the DevTools protocol with Node's own WebSocket: no packages, a throw-away profile in
// TEMP (removed afterwards), background networking off; the only page is the loopback demo. The hover shot moves
// the real mouse pointer of the page (Input.dispatchMouseEvent), not a script call.
// Usage: node capture_screenshots.js <browser.exe> <demo url> <output folder>
'use strict';
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const [browser, url, outDir] = process.argv.slice(2);
if (!browser || !url || !outDir) {console.error('usage: node capture_screenshots.js <browser.exe> <demo url> <out dir>'); process.exit(2);}
if (!/^http:\/\/127\.0\.0\.1:\d+\//.test(url)) {console.error('only a loopback demo address is allowed'); process.exit(2);}
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'claude-evmcompact-shot-'));
  const child = spawn(browser, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run',
    '--no-default-browser-check', '--disable-background-networking', '--disable-component-update', '--disable-sync',
    '--disable-extensions', '--disable-default-apps', '--no-pings', '--metrics-recording-only', '--hide-scrollbars',
    '--disable-features=Translate,OptimizationHints,MediaRouter,AutofillServerCommunication', 'about:blank'], {stdio: 'ignore'});
  const facts = {};
  try {
    let port = null;
    for (let i = 0; i < 100 && !port; i++) {
      try {port = fs.readFileSync(path.join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0].trim();} catch (_) {await sleep(100);}
    }
    if (!port) throw new Error('the browser did not open its DevTools port');
    const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    const ws = new WebSocket(pages.find(p => p.type === 'page').webSocketDebuggerUrl);
    await new Promise((ok, fail) => {ws.onopen = ok; ws.onerror = fail;});
    let id = 0; const waiting = new Map();
    ws.onmessage = e => {const m = JSON.parse(e.data); if (m.id && waiting.has(m.id)) {waiting.get(m.id)(m); waiting.delete(m.id);}};
    const call = (method, params = {}) => new Promise((ok, fail) => {
      const n = ++id; waiting.set(n, m => m.error ? fail(new Error(method + ': ' + m.error.message)) : ok(m.result));
      ws.send(JSON.stringify({id: n, method, params}));
    });
    const run = async code => {
      const r = await call('Runtime.evaluate', {expression: `(async()=>{${code}})()`, awaitPromise: true, returnByValue: true});
      if (r.exceptionDetails) throw new Error('page script failed: ' + r.exceptionDetails.text);
      return r.result.value;
    };
    const shot = async name => {
      await sleep(350);
      const {data} = await call('Page.captureScreenshot', {format: 'png'});
      fs.writeFileSync(path.join(outDir, name), Buffer.from(data, 'base64'));
      console.log('saved', name);
    };
    const size = (width, height, scale = 1) => call('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: scale, mobile: false});
    const load = async hash => {  // a full load each time: a hash-only change would keep the previous page state
      await call('Page.navigate', {url: 'about:blank'}); await sleep(300);
      await call('Page.navigate', {url: url.replace(/#.*$/, '') + hash}); await sleep(1800);
      await run(`for(let i=0;i<60&&!document.querySelector('.ccard');i++)await new Promise(r=>setTimeout(r,100));return true`);
    };
    const fit = name => run(`const p=document.getElementById('evmPeek').getBoundingClientRect();
      return {shot:'${name}',viewport:[innerWidth,innerHeight],scrollWidth:document.documentElement.scrollWidth,
        peek:document.getElementById('evmPeek').hidden?null:[Math.round(p.left),Math.round(p.top),Math.round(p.right),Math.round(p.bottom)]}`);
    await call('Page.enable');
    await size(1400, 1000);
    await load('#evm');
    await run(`document.querySelector('.evm-board').scrollIntoView({block:'start'});return true`);
    facts.board = await fit('01');
    await shot('01-evm-board-1400.png');
    const at = await run(`const c=document.querySelectorAll('#evmApiList .ccard')[2].getBoundingClientRect();return [c.left+c.width/2,c.top+c.height/2]`);
    await call('Input.dispatchMouseEvent', {type: 'mouseMoved', x: at[0], y: at[1]});
    await sleep(500);
    facts.hover = await fit('02');
    if (!facts.hover.peek) throw new Error('hover did not open the full card');
    await shot('02-evm-hover-full-card.png');
    await run(`[...document.querySelectorAll('#evmPeek button')].find(b=>b.textContent.includes('Изменить описание')).click();
      await new Promise(r=>setTimeout(r,300));return !document.getElementById('evmSettingsWindow').hidden`);
    facts.edit = await run(`return {tab:document.getElementById('evmTabModel').getAttribute('aria-selected'),focus:document.activeElement.id}`);
    await shot('03-evm-edit-description.png');
    await call('Input.dispatchMouseEvent', {type: 'mouseMoved', x: 5, y: 5});
    await load('#chat');
    await run(`document.getElementById('chatModelPick').click();for(let i=0;i<40&&!document.querySelector('#chatModelMenu button');i++)await new Promise(r=>setTimeout(r,100));return true`);
    facts.picker = await run(`return [...document.querySelectorAll('#chatModelMenu button')].map(b=>[b.textContent,b.getAttribute('aria-selected')])`);
    await shot('04-chat-model-picker.png');
    await size(390, 844);
    await load('#evm');
    await run(`const c=document.querySelectorAll('#evmApiList .ccard')[1];c.scrollIntoView({block:'center'});c.click();await new Promise(r=>setTimeout(r,400));return true`);
    facts.narrow = await fit('05');
    await shot('05-evm-390-pinned-card.png');
    await size(933, 667, 1.5);  // a 1400 x 1000 screen at 150 % browser zoom
    await load('#evm');
    await run(`document.querySelector('.evm-board').scrollIntoView({block:'start'});const c=document.querySelectorAll('#evmApiList .ccard')[0];c.click();await new Promise(r=>setTimeout(r,400));return true`);
    facts.zoom150 = await fit('06');
    facts.zoom150.columns = await run(`return getComputedStyle(document.querySelector('.evm-board')).gridTemplateColumns`);
    await shot('06-evm-150-percent.png');
    fs.writeFileSync(path.join(outDir, 'screenshot_facts.json'), JSON.stringify(facts, null, 1) + '\n');
    ws.close();
  } finally {
    child.kill();
    await sleep(800);
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 300});
  }
}
main().catch(e => {console.error(String(e.message || e)); process.exit(1);});
