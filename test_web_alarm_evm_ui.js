// WUA-1 EVM tab: run the actual shipped client in the same deterministic DOM adapter as
// test_web_alarm_operator_ui.js (node:vm, no packages, no network, no project writes).
// Fixture models are invented on purpose: the page must render whatever the server read
// model returns and contain no copy of the Ultra model registry.
'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, 'web_alarm/ui.py'), 'utf8');
const script = source.match(/<script>([\s\S]*?)<\/script>/)[1];

class Element {
  constructor(tag = 'div') {this.tag = tag; this.children = []; this.attrs = {}; this.dataset = {}; this.style = {}; this.hidden = false; this.disabled = false; this.value = ''; this._text = '';}
  set textContent(value) {this._text = String(value); this.children = [];}
  get textContent() {return this._text + this.children.map(c => c.textContent).join('');}
  append(...children) {this.children.push(...children);}
  replaceChildren(...children) {this._text = ''; this.children = children;}
  setAttribute(name, value) {this.attrs[name] = String(value);}
  getAttribute(name) {return this.attrs[name] ?? null;}
  removeAttribute(name) {delete this.attrs[name];}
  focus() {this.document.activeElement = this;}
}
const settle = async () => {for (let i = 0; i < 8; i++) await new Promise(setImmediate);};
const conn = (id, name, extra = {}) => ({connection_id: 'api:prov:' + id, kind: 'api', provider: 'prov', model_id: id,
  display_name: name, provider_model_id: 'P-' + id, is_local: false, registry_enabled: true, status: 'REGISTERED',
  verification: 'UNVERIFIED', selectable: true, selected: false, ...extra});
function catalog(connections, selection = {role: 'chat', state: 'NOT_SELECTED', connection_id: null}) {
  return {source: 'model_registry', network_calls: 0, columns: {api: {state: 'AVAILABLE', connections},
    mcp_agents: {state: 'NOT_CONNECTED', connections: []}, local_llm: {state: 'NOT_CONNECTED', connections: []}},
    selection: {chat: selection}};
}

function harness() {
  const h = {calls: [], routes: new Map()};
  const elements = {};
  for (const m of source.matchAll(/<([a-z0-9]+)[^>]*\bid="([^"]+)"[^>]*>/g)) {
    const e = new Element(m[1]); e.id = m[2]; e.hidden = m[0].includes(' hidden');
    for (const [, name, value] of m[0].matchAll(/\s([a-z][a-z-]*)="([^"]*)"/g)) e.attrs[name] = value;  // markup attributes, as a browser would
    elements[e.id] = e;
  }
  const all = () => {const s = new Set(Object.values(elements)); const add = e => {for (const c of e.children) {s.add(c); add(c);}}; Object.values(elements).forEach(add); return [...s];};
  const document = {hidden: false, activeElement: null, getElementById: id => elements[id], createElement: tag => {const e = new Element(tag); e.document = document; return e;}, querySelectorAll: () => []};
  Object.values(elements).forEach(e => e.document = document);
  const operator = url => {
    if (url === '/status') return {service: 'web_alarm_server', mode: 'server', api_version: 1};
    if (url === '/workspaces') return {workspaces: []};
    if (url === '/ui/capabilities') return {folder_picker: {available: false, reason: 'disabled'}};
    if (url === '/ui/tasks') return {active: [], completed: [], errors: []};
    return {};
  };
  h.context = vm.createContext({document, console, AbortController, setTimeout: (fn, ms) => {const t = setTimeout(fn, ms); t.unref(); return t;}, clearTimeout,
    setInterval: () => 0, Date, localStorage: {getItem: () => null, setItem: () => {}, removeItem: () => {}},
    window: {confirm: () => true, matchMedia: () => ({matches: false}), scrollTo: () => {}, addEventListener: () => {}},
    navigator: {locks: {request: async (k, o, fn) => fn({name: k})}, clipboard: {writeText: async () => {}}},
    fetch: async (url, opts) => {
      h.calls.push({url, method: opts.method || 'GET', body: opts.body, headers: opts.headers});
      const route = h.routes.get(url);
      const value = route ? await route(opts) : operator(url);
      if (value?.httpError) return {ok: false, status: value.status, json: async () => value.data};
      return {ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(value))};
    }});
  h.el = id => elements[id];
  h.all = all;
  h.run = code => vm.runInContext(code, h.context);
  h.evmCalls = () => h.calls.filter(c => c.url.startsWith('/ultra/'));
  h.cards = () => h.el('evmApiList').children;
  h.button = card => card.children.find(c => c.tag === 'button');
  vm.runInContext(script, h.context);
  return h;
}

test('E1 the operator panel stays the default view and nothing is asked about connections at load', async () => {
  const h = harness(); await settle();
  assert.equal(h.evmCalls().length, 0);
  assert.equal(h.el('evmView').hidden, true);
  assert.equal(h.el('layout').hidden, false);
  assert.equal(h.el('viewOperator').getAttribute('aria-pressed'), 'true');
  assert.equal(h.el('viewEvm').getAttribute('aria-pressed'), 'false');
});

test('E2 opening EVM renders exactly the server catalog in the API column, other columns empty', async () => {
  const h = harness(); await settle();
  h.routes.set('/ultra/connections', () => catalog([conn('alpha', 'Alpha'), conn('beta', 'Beta'), conn('gamma', 'Gamma')]));
  h.el('viewEvm').onclick(); await settle();
  assert.equal(h.el('evmView').hidden, false);
  assert.equal(h.el('layout').hidden, true);
  assert.equal(h.el('viewEvm').getAttribute('aria-pressed'), 'true');
  assert.deepEqual(h.cards().map(c => c.getAttribute('data-connection')), ['api:prov:alpha', 'api:prov:beta', 'api:prov:gamma']);
  assert.match(h.cards()[0].textContent, /Alpha.*alpha → P-alpha/s);
  assert.match(h.cards()[0].textContent, /API не проверено/);
  assert.match(h.el('evmMcpState').textContent, /Ещё не подключено/);
  assert.match(h.el('evmLocalState').textContent, /Ещё не подключено/);
  assert.match(h.el('evmSelection').textContent, /ещё не выбрана/);
  assert.equal(h.el('evmState').textContent, 'Моделей в реестре: 3');
  assert.equal(h.el('showWorkspaces').hidden, true, 'operator-only mobile toggles stay visible in EVM');
});

test('E3 choosing a model posts only role + connection_id once and shows the saved choice', async () => {
  const h = harness(); await settle();
  let saved = null;
  h.routes.set('/ultra/connections', () => catalog([conn('alpha', 'Alpha', {selected: saved === 'api:prov:alpha'}), conn('beta', 'Beta')],
    saved ? {role: 'chat', state: 'SAVED', connection_id: saved, model_id: 'alpha', display_name: 'Alpha', provider_model_id: 'P-alpha', selected_at: 'T1'} : undefined));
  const gate = {};
  h.routes.set('/ultra/connections/selection', opts => new Promise(resolve => {gate.open = () => {saved = JSON.parse(opts.body).connection_id;
    resolve({selection: {role: 'chat', state: 'SAVED', connection_id: saved, model_id: 'alpha', display_name: 'Alpha', provider_model_id: 'P-alpha'}});};}));
  h.el('viewEvm').onclick(); await settle();
  const button = h.button(h.cards()[0]);
  button.onclick(); await settle();
  assert.equal(h.button(h.cards()[1]).disabled, true, 'other choices stay clickable while saving');
  h.button(h.cards()[1]).onclick(); await settle();
  gate.open(); await settle();
  const posts = h.calls.filter(c => c.method === 'POST');
  assert.equal(posts.length, 1);
  assert.deepEqual(JSON.parse(posts[0].body), {role: 'chat', connection_id: 'api:prov:alpha'});
  assert.equal(posts[0].headers['Content-Type'], 'application/json');
  assert.match(h.el('evmNotice').textContent, /Выбор сохранён: Alpha \(P-alpha\)/);
  assert.match(h.el('evmSelection').textContent, /Выбрана: Alpha · alpha → P-alpha/);
  assert.equal(h.cards()[0].getAttribute('data-selected'), 'true');
  assert.equal(h.button(h.cards()[0]).disabled, true);
  assert.equal(h.button(h.cards()[1]).disabled, false);
});

test('E4 a refused choice is reported and the list is reloaded from the server, not changed locally', async () => {
  const h = harness(); await settle();
  h.routes.set('/ultra/connections', () => catalog([conn('alpha', 'Alpha')]));
  h.routes.set('/ultra/connections/selection', () => ({httpError: true, status: 409, data: {error: {code: 'connection_disabled', message: 'model is disabled'}}}));
  h.el('viewEvm').onclick(); await settle();
  h.button(h.cards()[0]).onclick(); await settle();
  assert.match(h.el('evmError').textContent, /Выбор не сохранён: connection_disabled/);
  assert.equal(h.el('evmNotice').hidden, true);
  assert.equal(h.cards()[0].getAttribute('data-selected'), 'false');
  assert.equal(h.evmCalls().filter(c => c.url === '/ultra/connections').length, 2);
});

test('E5 malformed or failed catalog answers show an error and no invented models', async () => {
  for (const answer of [{columns: {}}, {...catalog([{connection_id: 'x'}])}, {httpError: true, status: 503, data: {error: {code: 'model_registry_unavailable', message: 'x'}}}]) {
    const h = harness(); await settle();
    h.routes.set('/ultra/connections', () => answer);
    h.el('viewEvm').onclick(); await settle();
    assert.equal(h.el('evmError').hidden, false);
    assert.equal(h.cards().length, 0);
  }
});

test('E6 saved-choice states are told honestly', async () => {
  const states = [[{state: 'CORRUPT'}, /повреждён/], [{state: 'INVALID_REFERENCE', connection_id: 'api:prov:gone'}, /недоступна в реестре \(api:prov:gone\)/],
    [{state: 'NOT_SELECTED'}, /ещё не выбрана/], [{state: 'REGISTRY_UNAVAILABLE', connection_id: 'api:prov:alpha'}, /реестр моделей недоступен/]];
  for (const [selection, expected] of states) {
    const h = harness(); await settle();
    h.routes.set('/ultra/connections', () => catalog([conn('alpha', 'Alpha')], {role: 'chat', connection_id: null, ...selection}));
    h.el('viewEvm').onclick(); await settle();
    assert.match(h.el('evmSelection').textContent, expected);
  }
});

test('E7 disabled models cannot be chosen and server text is never markup', async () => {
  const h = harness(); await settle();
  h.routes.set('/ultra/connections', () => catalog([conn('off', '<img src=x onerror=alert(1)>', {status: 'DISABLED', selectable: false})]));
  h.el('viewEvm').onclick(); await settle();
  assert.equal(h.button(h.cards()[0]).disabled, true);
  assert.match(h.cards()[0].textContent, /Отключена в реестре/);
  assert.ok(h.all().every(e => !('innerHTML' in e)), 'markup was assigned');
  assert.equal(h.cards()[0].children[0].textContent, '<img src=x onerror=alert(1)>');
});

test('E8 the way back restores the operator panel; refresh reloads the catalog', async () => {
  const h = harness(); await settle();
  h.routes.set('/ultra/connections', () => catalog([conn('alpha', 'Alpha')]));
  h.el('viewEvm').onclick(); await settle();
  h.el('evmRefresh').onclick(); await settle();
  assert.equal(h.evmCalls().length, 2);
  h.el('viewOperator').onclick(); await settle();
  assert.equal(h.el('layout').hidden, false);
  assert.equal(h.el('evmView').hidden, true);
  assert.equal(h.el('viewOperator').getAttribute('aria-pressed'), 'true');
  assert.equal(h.el('showWorkspaces').hidden, false);
  assert.equal(h.evmCalls().length, 2, 'returning to the operator panel asked the connections API');
});

test('E9 the shipped page carries no model list of its own', () => {
  assert.doesNotMatch(source, /gigachat_[0-9a-z_]+|GigaChat-\d/);
  assert.doesNotMatch(source, /innerHTML/);
});
