// Three PNG screenshots of the new EVM from the synthetic demo (tools/demo_evm_cards.py must be running):
// 01 a full model card, 02 the settings window, 03 the API diagnostic window after "Отправить тестовое сообщение".
// Headless Chrome/Edge driven over the DevTools protocol with Node's own WebSocket: no packages, a throw-away
// profile in TEMP (removed afterwards), background networking off; the only page is the loopback demo.
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
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'claude-evmcard-shot-'));
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
      await sleep(400);
      const {data} = await call('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
      fs.writeFileSync(path.join(outDir, name), Buffer.from(data, 'base64'));
      console.log('saved', name);
    };
    await call('Emulation.setDeviceMetricsOverride', {width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false});
    await call('Page.enable');
    await call('Page.navigate', {url});
    await sleep(2500);
    const cards = await run(`for(let i=0;i<50&&!document.querySelector('.mcard .roles');i++)await new Promise(r=>setTimeout(r,100));
      document.getElementById('evmApiTitle').closest('section').scrollIntoView({block:'start'});
      return document.querySelectorAll('.mcard .roles').length`);
    if (cards < 1) throw new Error('no model card rendered');
    await shot('01-evm-model-cards.png');
    await run(`document.querySelector('.mcard button').click();await new Promise(r=>setTimeout(r,300));
      return !document.getElementById('evmSettingsWindow').hidden`) || (() => {throw new Error('settings did not open');})();
    await shot('02-evm-settings-connection.png');
    await run(`document.getElementById('evmSetClose').click();await new Promise(r=>setTimeout(r,200));
      document.querySelectorAll('.mcard')[0].querySelectorAll('button')[1].click();await new Promise(r=>setTimeout(r,300));
      document.getElementById('evmCheckSend').click();
      for(let i=0;i<50&&/Проверяем/.test(document.getElementById('evmCheckOutput').textContent);i++)await new Promise(r=>setTimeout(r,100));
      return !document.getElementById('evmCheckWindow').hidden`) || (() => {throw new Error('diagnostics did not open');})();
    await shot('03-evm-api-check.png');
    ws.close();
  } finally {
    child.kill();
    await sleep(800);
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 300});
  }
}
main().catch(e => {console.error(String(e.message || e)); process.exit(1);});
