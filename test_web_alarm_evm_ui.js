// WUA-1 EVM tab: run the actual shipped client in the same deterministic DOM adapter as
// test_web_alarm_operator_ui.js (node:vm, no packages, no network, no project writes).
// Fixture models are invented on purpose: the page must render whatever the server read
// model returns and contain no copy of the Ultra model registry.
// CLAUDE-WUA-EVM-COMPACT-LAYOUT-001: four columns of compact cards, one floating full card, manual order,
// favourites and the chat-model picker next to the Ultra Chat composer.
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
  get tagName() {return this.tag.toUpperCase();}
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
const wait = ms => new Promise(r => setTimeout(r, ms));
const conn = (id, name, extra = {}) => ({connection_id: 'api:prov:' + id, kind: 'api', provider: 'prov', model_id: id,
  display_name: name, provider_model_id: 'P-' + id, is_local: false, registry_enabled: true, status: 'REGISTERED',
  verification: 'UNVERIFIED', selectable: true, selected: false, ...extra});
const other = (kind, id, name) => ({connection_id: kind + ':prov:' + id, kind, provider: 'prov', display_name: name});
function catalog(connections, selection = {role: 'chat', state: 'NOT_SELECTED', connection_id: null}, mcp = [], local = []) {
  return {source: 'model_registry', network_calls: 0, columns: {api: {state: 'AVAILABLE', connections},
    mcp_agents: {state: mcp.length ? 'AVAILABLE' : 'NOT_CONNECTED', connections: mcp}, local_llm: {state: local.length ? 'AVAILABLE' : 'NOT_CONNECTED', connections: local}},
    selection: {chat: selection}};
}
// /ultra/model-cards: invented roles, hints and texts; the page must show exactly these.
const ROLE_DEFS = [['r_chat', 'Роль-чат'], ['r_plan', 'Роль-план'], ['r_check', 'Роль-проверка'], ['r_none', 'Роль-нет']]
  .map(([role, label]) => ({role, label, hint: 'Подсказка ' + label, exists: role !== 'r_none', linked_to: null}));
const api = (color, reason, extra = {}) => ({color, reason, freshness_days: 30, age_days: color === 'red' ? null : 3,
  last_success_at: color === 'red' ? null : '2026-10-24T10:00:00+00:00', last_success_source: color === 'red' ? null : 'diagnostic',
  last_failure_at: null, last_failure: null, settings_version: 'v1', ...extra});
const mcard = (id, name, extra = {}) => ({connection_id: 'api:prov:' + id, model_id: id, display_name: name, provider_id: 'prov',
  provider_model_id: 'P-' + id, registry_enabled: true, is_local: false, params_billion: null, params_source: 'unknown',
  description: '', profile_id: 'prov-default', settings_version: 'v1', last_output: null, api: api('red', 'NEVER_CONFIRMED'),
  roles: ROLE_DEFS.map(r => ({role: r.role, state: r.exists ? 'not_assigned' : 'not_in_runtime'})), ...extra});
function cards(list, extra = {}) {
  return {network_calls: 0, settings: {state: 'SAVED', revision: 4, ignored: 0}, checks: {state: 'SAVED'},
    roles_source: {state: 'SAVED', fallbacks: [], chat_state: 'NOT_SELECTED'}, role_definitions: ROLE_DEFS,
    providers: [{provider_id: 'prov', display_name: 'Провайдер', country: 'X', source: 'builtin', adapter: 'prov_adapter',
      adapter_state: 'AVAILABLE', auth: 'Ключ из среды', oauth_url: 'https://oauth.example', api_url: 'https://api.example',
      credential: {source: 'переменная среды PROV_KEY', present: true}, scope: {value: 'S', label: 'Тариф S'}}],
    profiles: [{profile_id: 'prov-default', provider_id: 'prov', title: 'Основной профиль', builtin: true, credential_revision: 0,
      freshness_days: 30, timeout_seconds: 30, diagnostic_limit_chars: 1000},
    {profile_id: 'prov-second', provider_id: 'prov', title: 'Второй профиль', builtin: false, credential_revision: 0,
      freshness_days: 7, timeout_seconds: 60, diagnostic_limit_chars: 500}],
    limits: {description: 500, params_billion: 100000}, test_message: 'Тест.', live_check: {authorized: false, reason: 'Нужен USER GO.'},
    view: {state: 'SAVED', revision: 7, hidden: 0, sections: {favorites: [], api: list.map(c => c.connection_id), mcp: [], local: []}},
    cards: list, ...extra};
}
const ev = (extra = {}) => ({preventDefault() {this.prevented = true;}, stopPropagation() {this.stopped = true;}, ...extra});

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
  h.document = document;
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
  h.posts = url => h.calls.filter(c => c.method === 'POST' && (!url || c.url === url)).map(c => JSON.parse(c.body));
  h.list = id => h.el(id).children;
  h.cards = () => h.list('evmApiList');
  h.find = (root, pred) => {if (pred(root)) return root; for (const c of root.children || []) {const f = h.find(c, pred); if (f) return f;} return null;};
  h.findAll = (root, pred, out = []) => {if (pred(root)) out.push(root); for (const c of root.children || []) h.findAll(c, pred, out); return out;};
  h.button = (root, label) => h.find(root, e => e.tag === 'button' && e.textContent.includes(label));
  h.dot = root => h.find(root, e => (e.className || '').startsWith('api-dot'));
  h.star = card => h.find(card, e => e.className === 'star');
  h.opener = card => h.find(card, e => e.className === 'copen');
  h.peek = () => h.el('evmPeek').children[0];
  h.roles = card => h.findAll(card, e => e.className === 'role').map(r => [r.getAttribute('data-role'), r.getAttribute('data-state'), r.children[0].textContent]);
  h.open = async card => {card.onclick(ev({target: card})); await settle();};  // pins the full card
  h.openEvm = async (list, data = cards(list.map(c => mcard(c.model_id, c.display_name))), mcp = [], local = []) => {
    h.routes.set('/ultra/connections', () => catalog(list, undefined, mcp, local));
    h.routes.set('/ultra/model-cards', () => data);
    h.el('viewEvm').onclick(); await settle();
  };
  vm.runInContext(script, h.context);
  return h;
}

test('E1 Ultra Chat is the default view; at load the catalog is not asked, only the saved choice for the chat badge', async () => {
  // Stage 1 (CLAUDE-WUA-CHAT-S1-READONLY-UI-001) made Ultra Chat the default; its model badge reads the saved
  // choice once. The EVM catalog and any write stay untouched until the EVM tab is opened.
  const h = harness(); await settle();
  assert.deepEqual(h.calls.filter(c => c.url.startsWith('/ultra/connections')).map(c => c.method + ' ' + c.url),
    ['GET /ultra/connections/selection?role=chat']);
  assert.equal(h.calls.filter(c => c.method !== 'GET').length, 0);
  assert.equal(h.el('evmView').hidden, true);
  assert.equal(h.el('layout').hidden, true);
  assert.equal(h.el('chatView').hidden, false);
  assert.equal(h.el('viewChat').getAttribute('aria-pressed'), 'true');
  assert.equal(h.el('viewOperator').getAttribute('aria-pressed'), 'false');
  assert.equal(h.el('viewEvm').getAttribute('aria-pressed'), 'false');
});

test('E2 the board: four columns, compact cards in server order, honest empty columns, no full card inline', async () => {
  const h = harness(); await settle();
  const list = [conn('alpha', 'Alpha'), conn('beta', 'Beta'), conn('gamma', 'Gamma')];
  await h.openEvm(list, cards([mcard('alpha', 'Alpha', {params_billion: 390, api: api('green', 'CONFIRMED')}), mcard('beta', 'Beta'), mcard('gamma', 'Gamma')],
    {view: {state: 'SAVED', revision: 7, hidden: 0, sections: {favorites: [], api: ['api:prov:gamma', 'api:prov:alpha', 'api:prov:beta'], mcp: [], local: []}}}));
  assert.equal(h.el('evmView').hidden, false);
  assert.deepEqual([...source.matchAll(/<h3 id="evm(Fav|Api|Mcp|Local)Title">([^<]+)<\/h3>/g)].map(m => m[2]), ['★ Избранное', 'API', 'MCP / Агенты', 'Локальные LLM']);
  assert.deepEqual(h.cards().map(c => c.getAttribute('data-connection')), ['api:prov:gamma', 'api:prov:alpha', 'api:prov:beta']);
  const alpha = h.cards()[1];
  assert.equal(alpha.tag, 'article');
  assert.equal(alpha.getAttribute('role'), null, 'the card itself is not a button around other buttons');
  const opener = h.opener(alpha);
  assert.deepEqual([opener.tag, opener.getAttribute('aria-expanded'), opener.getAttribute('aria-haspopup')], ['button', 'false', 'dialog']);
  assert.match(opener.getAttribute('aria-label'), /^Alpha — API\. Открыть карточку/);
  assert.ok(!h.findAll(opener, e => e.tag === 'button' && e !== opener).length, 'no control inside another control');
  assert.match(alpha.textContent, /Alpha/); assert.match(alpha.textContent, /API · Провайдер/); assert.match(alpha.textContent, /390 млрд/);
  assert.equal(h.dot(alpha).getAttribute('data-api'), 'green:CONFIRMED');
  assert.doesNotMatch(h.cards()[0].textContent, /млрд/, 'an unknown parameter count is not shown in the compact card');
  for (const card of h.cards()) {
    assert.deepEqual(h.findAll(card, e => e.tag === 'button').map(b => b.className), ['copen', 'star'], 'the compact card: «open» and the star only');
    assert.equal(h.roles(card).length, 0);
    assert.equal(h.find(card, e => (e.className || '').startsWith('strengths')), null);
  }
  assert.equal(h.el('evmPeek').hidden, true);
  assert.equal(h.list('evmFavList').length, 0); assert.equal(h.el('evmFavEmpty').hidden, false); assert.equal(h.el('evmFavState').textContent, '0');
  assert.equal(h.el('evmMcpEmpty').hidden, false); assert.equal(h.el('evmLocalEmpty').hidden, false);
  assert.match(h.el('evmMcpState').textContent, /Ещё не подключено/); assert.match(h.el('evmLocalState').textContent, /Ещё не подключено/);
  assert.match(h.el('evmSelection').textContent, /ещё не выбрана/);
  assert.equal(h.el('evmSummary').textContent, '✓ 1 · ! 0 · × 2');
  assert.equal(h.el('evmState').textContent, 'Моделей в реестре: 3');
  assert.equal(h.el('showWorkspaces').hidden, true, 'operator-only mobile toggles stay hidden in EVM');
  assert.deepEqual(h.evmCalls().filter(c => c.method === 'GET' && !c.url.includes('selection')).map(c => c.url).sort(), ['/ultra/connections', '/ultra/model-cards']);
  assert.equal(source.includes('id="evmChatModel"'), false, 'the large chat-model block left EVM');
});

test('E3 the chat-model picker next to the composer: reads the list only when opened, saves only the preference', async () => {
  const h = harness(); await settle();
  let saved = null;
  h.routes.set('/ultra/connections', () => catalog([conn('alpha', 'Alpha'), conn('beta', 'Beta', {selectable: false})],
    saved ? {role: 'chat', state: 'SAVED', connection_id: saved, display_name: 'Alpha'} : undefined));
  h.routes.set('/ultra/connections/selection?role=chat', () => ({selection: saved ? {role: 'chat', state: 'SAVED', connection_id: saved, display_name: 'Alpha', model_id: 'alpha', provider_model_id: 'P-alpha'} : {role: 'chat', state: 'NOT_SELECTED'}}));
  h.routes.set('/ultra/connections/selection', opts => {saved = JSON.parse(opts.body).connection_id; return {selection: {role: 'chat', state: 'SAVED', connection_id: saved, display_name: 'Alpha'}};});
  h.calls.length = 0; h.run('loadChatModel()'); await settle();
  assert.equal(h.el('chatModelPick').textContent, 'Выбрать модель ▾');
  assert.match(h.el('chatModel').textContent, /не выбрана — выберите у поля ввода/);
  assert.equal(h.calls.some(c => c.url === '/ultra/connections'), false, 'nothing but the saved choice is read before the picker opens');
  h.el('chatModelPick').onclick(); await settle();
  assert.equal(h.el('chatModelMenu').hidden, false); assert.equal(h.el('chatModelPick').getAttribute('aria-expanded'), 'true');
  const options = h.list('chatModelMenu');
  assert.deepEqual(options.map(o => [o.textContent, o.disabled, o.getAttribute('role')]), [['Alpha', false, 'option'], ['Beta — отключена', true, 'option']]);
  assert.equal(h.document.activeElement, options[0]);
  options[0].onclick(); await settle();
  assert.deepEqual(h.posts(), [{role: 'chat', connection_id: 'api:prov:alpha'}]);
  const post = h.calls.find(c => c.method === 'POST');
  assert.equal(post.url, '/ultra/connections/selection');
  assert.deepEqual(Object.keys(post.headers), ['Content-Type'], 'no chat token travels with the preference');
  assert.equal(h.el('chatModelMenu').hidden, true); assert.equal(h.document.activeElement, h.el('chatModelPick'));
  assert.equal(h.el('chatModel').textContent, 'Модель: Alpha'); assert.equal(h.el('chatModelPick').textContent, 'Alpha ▾');
  assert.equal(h.calls.filter(c => c.url.startsWith('/ultra/chat')).length, 0, 'the picker never touches the chat history routes');
  h.el('chatModelPick').onclick(); await settle();
  assert.equal(h.list('chatModelMenu')[0].getAttribute('aria-selected'), 'true');
  h.run("escapeKey({key:'Escape'})");
  assert.equal(h.el('chatModelMenu').hidden, true);
});

test('E4 a refused or unavailable picker is told and saves nothing locally', async () => {
  const h = harness(); await settle();
  h.routes.set('/ultra/connections', () => catalog([conn('alpha', 'Alpha')]));
  h.routes.set('/ultra/connections/selection', () => ({httpError: true, status: 409, data: {error: {code: 'connection_disabled', message: 'model is disabled'}}}));
  h.el('chatModelPick').onclick(); await settle();
  h.list('chatModelMenu')[0].onclick(); await settle();
  assert.match(h.el('chatModelError').textContent, /Модель не сохранена: connection_disabled/);
  assert.equal(h.el('chatModelError').hidden, false);
  assert.equal(h.el('chatModelPick').disabled, false);
  const broken = harness(); await settle();
  broken.routes.set('/ultra/connections', () => ({httpError: true, status: 503, data: {error: {code: 'model_registry_unavailable', message: 'x'}}}));
  broken.el('chatModelPick').onclick(); await settle();
  assert.match(broken.el('chatModelMenu').textContent, /Список моделей недоступен: model_registry_unavailable/);
  assert.equal(broken.calls.filter(c => c.method === 'POST').length, 0);
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

test('E6 saved-choice states are told honestly in the EVM summary', async () => {
  const states = [[{state: 'CORRUPT'}, /повреждён.*в Ultra Chat/], [{state: 'INVALID_REFERENCE', connection_id: 'api:prov:gone'}, /недоступна в реестре \(api:prov:gone\)/],
    [{state: 'NOT_SELECTED'}, /ещё не выбрана/], [{state: 'REGISTRY_UNAVAILABLE', connection_id: 'api:prov:alpha'}, /реестр моделей недоступен/],
    [{state: 'SAVED', connection_id: 'api:prov:alpha', display_name: 'Alpha', model_id: 'alpha', provider_model_id: 'P-alpha'}, /Выбрана: Alpha · alpha → P-alpha/]];
  for (const [selection, expected] of states) {
    const h = harness(); await settle();
    h.routes.set('/ultra/connections', () => catalog([conn('alpha', 'Alpha')], {role: 'chat', connection_id: null, ...selection}));
    h.el('viewEvm').onclick(); await settle();
    assert.match(h.el('evmSelection').textContent, expected);
  }
});

test('E7 server text is never markup, in the compact and in the full card', async () => {
  const h = harness(); await settle();
  const name = '<img src=x onerror=alert(1)>';
  await h.openEvm([conn('off', name, {status: 'DISABLED', selectable: false})],
    cards([mcard('off', name, {description: '<script>x()</script>', api: api('red', 'REGISTRY_DISABLED')})]));
  assert.equal(h.find(h.cards()[0], e => e.className === 'cname').textContent, name);
  await h.open(h.cards()[0]);
  assert.equal(h.peek().children[0].children[0].textContent, name);
  assert.match(h.peek().textContent, /<script>x\(\)<\/script>/);
  assert.equal(h.dot(h.peek()).getAttribute('data-api'), 'red:REGISTRY_DISABLED');
  assert.ok(h.all().every(e => !('innerHTML' in e)), 'markup was assigned');
});

test('E8 the way back restores the operator panel; refresh reloads the catalog', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')]);
  h.el('evmRefresh').onclick(); await settle();
  assert.equal(h.calls.filter(c => c.url === '/ultra/connections').length, 2);
  const before = h.evmCalls().length;  // stage 1: the default Ultra Chat already read the chat badge at load
  h.el('viewOperator').onclick(); await settle();
  assert.equal(h.el('layout').hidden, false);
  assert.equal(h.el('evmView').hidden, true);
  assert.equal(h.el('chatView').hidden, true);
  assert.equal(h.el('viewOperator').getAttribute('aria-pressed'), 'true');
  assert.equal(h.el('showWorkspaces').hidden, false);
  assert.equal(h.evmCalls().length, before, 'returning to the operator panel asked the /ultra/ API');
});

test('E9 the shipped page carries no model list of its own', () => {
  assert.doesNotMatch(source, /gigachat_[0-9a-z_]+|GigaChat-\d/);
  assert.doesNotMatch(source, /innerHTML/);
});

test('E10 role marks and hints in the full card are exactly the server facts', async () => {
  const h = harness(); await settle();
  const roles = [{role: 'r_chat', state: 'assigned'}, {role: 'r_plan', state: 'assigned_off'}, {role: 'r_check', state: 'unknown'}, {role: 'r_none', state: 'not_in_runtime'}];
  await h.openEvm([conn('alpha', 'Alpha'), conn('beta', 'Beta')], cards([mcard('alpha', 'Alpha', {roles}),
    mcard('beta', 'Beta', {roles: [{role: 'r_chat', state: 'assigned_pending'}, ...ROLE_DEFS.slice(1).map(r => ({role: r.role, state: 'not_assigned'}))]})]));
  await h.open(h.cards()[0]);
  assert.deepEqual(h.roles(h.peek()), [['r_chat', 'assigned', '✓'], ['r_plan', 'assigned_off', '✓'], ['r_check', 'unknown', '?'], ['r_none', 'not_in_runtime', '–']]);
  const marks = h.findAll(h.peek(), e => (e.className || '').startsWith('mark ')).map(e => e.className);
  assert.deepEqual(marks, ['mark yes', 'mark off', 'mark unknown', 'mark na']);
  assert.equal(h.findAll(h.peek(), e => e.className === 'name')[1].getAttribute('data-hint'), 'Подсказка Роль-план Сейчас: назначена, но роль выключена.');
  await h.open(h.cards()[1]);
  assert.deepEqual(h.roles(h.peek()), [['r_chat', 'assigned_pending', '✓'], ['r_plan', 'not_assigned', '×'], ['r_check', 'not_assigned', '×'], ['r_none', 'not_assigned', '×']]);
  const h2 = harness(); await settle();
  await h2.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {roles: [{role: 'r_chat', state: 'ASSIGNED!'}]})]));
  await h2.open(h2.cards()[0]);
  assert.deepEqual(h2.roles(h2.peek()).map(r => r[1]), ['unknown', 'unknown', 'unknown', 'unknown'], 'an unknown or missing state is never a check mark');
});

test('E11 one API status component: compact card, full card and diagnostic window show the same server status', async () => {
  for (const [status, mark] of [[api('green', 'CONFIRMED'), '✓'], [api('orange', 'STALE', {age_days: 41}), '!'], [api('red', 'SETTINGS_CHANGED'), '×']]) {
    const h = harness(); await settle();
    await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {api: status})]));
    const compact = h.dot(h.cards()[0]);
    await h.open(h.cards()[0]);
    const full = h.dot(h.peek());
    h.button(h.peek(), 'Проверить чат').onclick(); await settle();
    const windowDot = h.el('evmCheckDot').children[0];
    for (const d of [full, windowDot])
      assert.deepEqual([d.className, d.textContent, d.getAttribute('data-api'), d.getAttribute('aria-label')],
        [compact.className, mark, compact.getAttribute('data-api'), compact.getAttribute('aria-label')]);
  }
});

test('E12 full card: parameter count as given, description box editable by a visible command', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')], cards([mcard('a', 'A', {params_billion: 2.5, description: 'Сильная сторона.'}), mcard('b', 'B')]));
  await h.open(h.cards()[0]);
  assert.equal(h.find(h.peek(), e => e.className === 'params').textContent, '2,5 млрд');
  const box = h.find(h.peek(), e => (e.className || '').startsWith('strengths'));
  assert.deepEqual([box.className, box.textContent], ['strengths editable', 'Сильная сторона.']);
  await h.open(h.cards()[1]);
  assert.equal(h.find(h.peek(), e => e.className === 'params').textContent, '— млрд');
  const empty = h.find(h.peek(), e => (e.className || '').startsWith('strengths'));
  assert.equal(empty.className, 'strengths editable placeholder', 'not the operator panel .empty block');
  assert.match(empty.textContent, /Нажмите «Изменить описание»/);
  assert.ok(h.button(h.peek(), 'Изменить описание'));
  assert.match(source, /\.strengths\{height:84px;overflow-y:auto;[^}]*line-height:1\.15/);
});

test('E13 settings from the full card: server facts, never the key value, the exact edited values', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {params_billion: 12, description: 'Было'})]));
  let posted = null;
  h.routes.set('/ultra/model-cards/alpha/settings', opts => {posted = JSON.parse(opts.body); return {card: mcard('alpha', 'Alpha')};});
  await h.open(h.cards()[0]);
  h.button(h.peek(), 'Настройки').onclick(); await settle();
  assert.equal(h.el('evmSettingsWindow').hidden, false);
  assert.equal(h.el('evmPeek').hidden, true, 'a window replaces the floating card');
  assert.equal(h.document.activeElement, h.el('evmSetTitle'));
  assert.equal(h.el('evmSetProvider').disabled, true);
  assert.match(h.el('evmSetConnFacts').textContent, /Задан \(переменная среды PROV_KEY\)\. Значение в браузер не передаётся/);
  h.el('evmTabModel').onclick();
  h.el('evmSetDescription').value = 'Новое описание'; h.el('evmSetDescription').oninput();
  h.el('evmSetParams').value = '70,5'; h.el('evmSetParams').oninput();
  h.el('evmTabMore').onclick();
  h.el('evmSetFreshness').value = '45'; h.el('evmSetFreshness').oninput();
  h.el('evmSetSave').onclick(); await settle();
  assert.deepEqual(posted, {base_revision: 4, description: 'Новое описание', params_billion: 70.5, profile_id: 'prov-default',
    profile: {timeout_seconds: 30, diagnostic_limit_chars: 1000, freshness_days: 45}});
  assert.match(h.el('evmNotice').textContent, /Настройки сохранены: Alpha/);
  assert.ok(!JSON.stringify(h.calls).includes('PROV_KEY='), 'no key value travels');
});

test('E14 settings: a bad count is refused locally, a revision conflict keeps the draft', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {params_billion: 12})]));
  const posts = [];
  h.routes.set('/ultra/model-cards/alpha/settings', opts => {posts.push(JSON.parse(opts.body));
    return {httpError: true, status: 409, data: {error: {code: 'settings_revision_conflict', message: 'settings changed'}}};});
  await h.open(h.cards()[0]);
  h.button(h.peek(), 'Настройки').onclick(); await settle();
  h.el('evmSetParams').value = '-3'; h.el('evmSetParams').oninput();
  h.el('evmSetSave').onclick(); await settle();
  assert.equal(posts.length, 0);
  assert.match(h.el('evmSetError').textContent, /положительное число/);
  h.el('evmSetParams').value = ''; h.el('evmSetParams').oninput();
  h.el('evmSetSave').onclick(); await settle();
  assert.equal(posts[0].params_billion, null);
  assert.match(h.el('evmSetError').textContent, /изменены в другом окне/);
  assert.equal(h.el('evmSetDraft').hidden, false, 'the draft survives a conflict');
  h.el('evmSetReset').onclick();
  assert.equal(h.el('evmSetParams').value, '12');
});

test('E15 one window keeps the state of the other; closing returns focus to the compact card', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha'), conn('beta', 'Beta')]);
  h.routes.set('/ultra/model-cards/alpha/check', () => ({outcome: 'LIVE_CHECK_NOT_AUTHORIZED', message: 'Нужен USER GO.', network_calls: 0, test_message: 'Тест.', card: mcard('alpha', 'Alpha')}));
  await h.open(h.cards()[0]);
  h.button(h.peek(), 'Настройки').onclick(); await settle();
  h.el('evmSetDescription').value = 'Черновик A'; h.el('evmSetDescription').oninput();
  h.el('evmSetClose').onclick(); await settle();
  assert.equal(h.el('evmSettingsWindow').hidden, true);
  assert.equal(h.document.activeElement, h.opener(h.cards()[0]), 'focus is back on the compact card');
  await h.open(h.cards()[0]);
  assert.match(h.peek().textContent, /несохранённые изменения/);
  h.button(h.peek(), 'Проверить чат').onclick(); await settle();
  h.el('evmCheckSend').onclick(); await settle();
  const answer = h.el('evmCheckOutput').textContent;
  assert.match(answer, /Сообщение не отправлялось.*Статус API не изменён/s);
  h.el('evmCheckWindow').onclick({target: h.el('evmCheckWindow')}); await settle();
  assert.equal(h.el('evmCheckWindow').hidden, true, 'a click on the backdrop closes it');
  await h.open(h.cards()[0]);
  h.button(h.peek(), 'Настройки').onclick(); await settle();
  assert.equal(h.el('evmSetDescription').value, 'Черновик A');
  h.run("escapeKey({key:'Escape'})"); await settle();
  assert.equal(h.el('evmSettingsWindow').hidden, true, 'Escape closes the window');
  await h.open(h.cards()[0]);
  h.button(h.peek(), 'Проверить чат').onclick(); await settle();
  assert.equal(h.el('evmCheckOutput').textContent, answer);
});

test('E16 the check: one empty POST, no input field, the indicator comes only from the server', async () => {
  const outcomes = [
    [{outcome: 'LIVE_CHECK_NOT_AUTHORIZED', message: 'Нужен USER GO.', network_calls: 0}, /Сообщение не отправлялось\. Нужен USER GO\./, 'output info'],
    [{outcome: 'SIMULATED', text: 'Привет!'}, /ИМИТАЦИЯ.*статус API не изменён.*Привет!/s, 'output info'],
    [{outcome: 'CONFIRMED', text: 'Получено.'}, /^Получено\.$/, 'output reply'],
    [{httpError: true, status: 409, data: {error: {code: 'check_refused', message: 'no adapter'}}}, /Проверка не выполнена: check_refused/, 'output error'],
  ];
  for (const [answer, expected, cls] of outcomes) {
    const h = harness(); await settle();
    h.routes.set('/ultra/model-cards/alpha/check', () => answer.httpError ? answer : {test_message: 'Тест.', card: mcard('alpha', 'Alpha'), ...answer});
    await h.openEvm([conn('alpha', 'Alpha')]);
    await h.open(h.cards()[0]);
    h.button(h.peek(), 'Проверить чат').onclick(); await settle();
    assert.equal(h.el('evmCheckNote').textContent, 'Тестовое сообщение: «Тест.» — в этой версии оно не отправляется.');
    h.el('evmCheckSend').onclick(); await settle();
    assert.deepEqual(h.calls.filter(c => c.method === 'POST').map(c => [c.url, c.body]), [['/ultra/model-cards/alpha/check', '{}']]);
    assert.match(h.el('evmCheckOutput').textContent, expected);
    assert.equal(h.el('evmCheckOutput').className, cls);
    assert.equal(h.el('evmCheckDot').children[0].textContent, '×', 'a check answer never paints the indicator by itself');
    assert.equal(h.dot(h.cards()[0]).textContent, '×');
  }
  assert.doesNotMatch(source.match(/<div id="evmCheckWindow"[\s\S]*?<\/div><\/div>/)[0], /<input|<textarea/);
  assert.ok(source.match(/id="evmCheckClose"[\s\S]*?id="evmCheckSend"/), 'buttons are [Закрыть] [Отправить тестовое сообщение]');
});

test('E17 without card data the compact cards show names only and nothing can be reordered or starred', async () => {
  for (const answer of [{httpError: true, status: 403, data: {error: {code: 'model_cards_forbidden', message: 'x'}}}, {cards: 'nope'},
    cards([mcard('alpha', 'Alpha', {api: {color: 'blue', reason: 'X'}})])]) {
    const h = harness(); await settle();
    await h.openEvm([conn('alpha', 'Alpha')], answer);
    const card = h.cards()[0];
    assert.equal(h.dot(card), null);
    assert.equal(h.star(card).disabled, true);
    assert.equal(card.getAttribute('draggable'), 'false');
    await h.open(card);
    assert.match(h.peek().textContent, /Подробности карточки недоступны/);
    assert.equal(h.dot(h.peek()), null); assert.deepEqual(h.roles(h.peek()), []);
    assert.equal(h.button(h.peek(), 'Выше'), null);
    assert.match(h.el('evmError').textContent, /Карточки моделей недоступны/);
  }
});

test('E18 the roles source is told: defaults, unreadable and not connected Ultra settings', async () => {
  for (const [state, expected] of [['DEFAULTS', /по умолчанию/], ['UNREADABLE', /не читается.*«\?»/], ['NOT_CONNECTED', /не подключён.*«\?»/]]) {
    const h = harness(); await settle();
    await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha')], {roles_source: {state, fallbacks: [{field: 'f', saved: 'x'}], chat_state: 'SAVED'}}));
    assert.match(h.el('evmRolesSource').textContent, expected);
    assert.match(h.el('evmRolesSource').textContent, /отсутствует в реестре/);
  }
});

test('E19 the chat composer: the model picker, a disabled voice place and a disabled send', async () => {
  const h = harness(); await settle();
  assert.equal(h.el('chatMic').getAttribute('data-extension'), 'voice-input');
  assert.equal(h.el('chatMic').onclick, undefined, 'the voice place has no behaviour yet');
  assert.match(source, /<button type="button" id="chatModelPick" aria-haspopup="listbox" aria-expanded="false" aria-controls="chatModelMenu"/);
  assert.match(source, /<button type="button" id="chatMic" disabled[^>]*>[^<]*<\/button><button type="button" id="chatSend" disabled>Отправить<\/button><\/span>/);
  assert.equal(h.calls.filter(c => c.method !== 'GET').length, 0);
});

test('E20 damaged stores are reported, and a damaged settings file can still be saved over on purpose', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha')], {settings: {state: 'CORRUPT', revision: null, ignored: 0}, checks: {state: 'CORRUPT'}}));
  assert.match(h.el('evmError').textContent, /Повреждены настройки карточек и сведения о проверках API/);
  let posted = null;
  h.routes.set('/ultra/model-cards/alpha/settings', opts => {posted = JSON.parse(opts.body); return {card: mcard('alpha', 'Alpha')};});
  await h.open(h.cards()[0]);
  h.button(h.peek(), 'Настройки').onclick(); await settle();
  h.el('evmSetSave').onclick(); await settle();
  assert.equal(posted.base_revision, null);
});

test('E21 hover opens after a short pause, switches at once, survives the way into the card and closes after leaving', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')]);
  const [a, b] = h.cards();
  a.onmouseenter(); await settle();
  assert.equal(h.el('evmPeek').hidden, true, 'no flash on a quick pass');
  a.onmouseleave(); await wait(150);
  assert.equal(h.el('evmPeek').hidden, true, 'a pass shorter than the pause opens nothing');
  a.onmouseenter(); await wait(150);
  assert.equal(h.el('evmPeek').hidden, false);
  assert.equal(h.peek().getAttribute('data-connection'), 'api:prov:a');
  assert.equal(h.el('evmPeek').className, 'evm-peek open');
  assert.equal(h.opener(a).getAttribute('aria-expanded'), 'true');
  a.onmouseleave(); b.onmouseenter(); await settle();
  assert.equal(h.peek().getAttribute('data-connection'), 'api:prov:b', 'moving to the next card switches without a pause');
  assert.equal(h.opener(a).getAttribute('aria-expanded'), 'false'); assert.equal(h.opener(b).getAttribute('aria-expanded'), 'true');
  b.onmouseleave(); h.el('evmPeek').onmouseenter(); await wait(250);
  assert.equal(h.el('evmPeek').hidden, false, 'the way from the card into the full card keeps it open');
  h.button(h.peek(), 'Проверить чат');  // the buttons are reachable
  h.el('evmPeek').onmouseleave(); await wait(250);
  assert.equal(h.el('evmPeek').hidden, true);
  assert.match(source, /@media\(prefers-reduced-motion:reduce\)\{\.evm-peek,\.ccard\{transition:none\}\}/);
  assert.match(source, /\.evm-peek\{position:fixed;[^}]*max-height:calc\(100dvh - 24px\);overflow:auto/);
});

test('E22 click, tap and keyboard: pin, close, Escape, Enter/Space, the star never opens the card', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')]);
  const [a, b] = h.cards();
  a.onmouseenter(); await wait(150);
  await h.open(a);  // a tap after the touch hover keeps it open
  a.onmouseleave(); await wait(250);
  assert.equal(h.el('evmPeek').hidden, false, 'a pinned card does not close on leave');
  b.onmouseenter(); await wait(150);
  assert.equal(h.peek().getAttribute('data-connection'), 'api:prov:a', 'hover does not replace a pinned card');
  await h.open(a);
  assert.equal(h.el('evmPeek').hidden, true, 'a second click closes it');
  assert.equal(h.document.activeElement, h.opener(a));
  b.onclick(ev({detail: 0, target: h.opener(b)})); await settle();  // Enter / Space on the «open» button
  assert.equal(h.el('evmPeek').hidden, false);
  assert.equal(h.document.activeElement, h.el('evmPeek'), 'the keyboard lands in the full card');
  h.run("escapeKey({key:'Escape'})");
  assert.equal(h.el('evmPeek').hidden, true); assert.equal(h.document.activeElement, h.opener(b));
  b.onclick(ev({detail: 1, target: h.opener(b)})); await settle();
  assert.equal(h.el('evmPeek').hidden, false); assert.notEqual(h.document.activeElement, h.el('evmPeek'), 'a mouse click does not move the focus');
  h.run("escapeKey({key:'Escape'})");
  const star = h.star(a), click = ev({target: star});
  h.routes.set('/ultra/model-cards/view', opts => ({view: {state: 'SAVED', revision: 8, hidden: 0, sections: {favorites: JSON.parse(opts.body).order, api: ['api:prov:a', 'api:prov:b'], mcp: [], local: []}}}));
  star.onclick(click); await settle();
  assert.equal(click.stopped, true); assert.equal(h.el('evmPeek').hidden, true, 'the star does not open the card');
  const starKey = ev({key: 'Enter', target: star}); h.star(h.cards()[0]).onkeydown(starKey);
  assert.equal(starKey.stopped, true);
});

test('E23 «Выше» / «Ниже» and Alt+arrows save the order of one column; the ends are disabled', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')]);
  let revision = 7;
  h.routes.set('/ultra/model-cards/view', opts => {const body = JSON.parse(opts.body);
    return {view: {state: 'SAVED', revision: ++revision, hidden: 0, sections: {favorites: [], api: body.order, mcp: [], local: []}}};});
  await h.open(h.cards()[0]);
  assert.equal(h.button(h.peek(), 'Выше').disabled, true);
  h.button(h.peek(), 'Ниже').onclick(); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/view'), [{base_revision: 7, section: 'api', order: ['api:prov:b', 'api:prov:a', 'api:prov:c']}]);
  assert.deepEqual(h.cards().map(c => c.getAttribute('data-connection')), ['api:prov:b', 'api:prov:a', 'api:prov:c']);
  assert.equal(h.peek().getAttribute('data-connection'), 'api:prov:a', 'the same card stays open');
  assert.equal(h.document.activeElement, h.button(h.peek(), 'Ниже'), 'the keyboard keeps its place');
  h.run("escapeKey({key:'Escape'})");
  const up = ev({key: 'ArrowUp', altKey: true}); h.opener(h.cards()[2]).onkeydown(up); await settle();
  assert.equal(up.prevented, true);
  assert.deepEqual(h.posts('/ultra/model-cards/view')[1], {base_revision: 8, section: 'api', order: ['api:prov:b', 'api:prov:c', 'api:prov:a']});
  h.opener(h.cards()[0]).onkeydown(ev({key: 'ArrowUp', altKey: true})); await settle();
  h.opener(h.cards()[1]).onkeydown(ev({key: 'ArrowUp'})); await settle();
  assert.equal(h.posts('/ultra/model-cards/view').length, 2, 'the first card cannot go higher');
  assert.ok(h.posts().every(b => !('description' in b) && !('connection_id' in b)), 'ordering saves nothing else');
});

test('E24 drag and drop inside one column; buttons never start a drag; other columns refuse the drop', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')], undefined, [], [other('local', 'a', 'Local A')]);
  h.routes.set('/ultra/model-cards/view', opts => ({view: {state: 'SAVED', revision: 8, hidden: 0, sections: {favorites: [], api: JSON.parse(opts.body).order, mcp: [], local: ['local:prov:a']}}}));
  const [a, b, c] = h.cards();
  a.onmousedown(ev({target: h.star(a)}));
  const fromStar = ev({target: a}); a.ondragstart(fromStar);  // a browser fires dragstart on the card itself
  assert.equal(fromStar.prevented, true, 'a drag that began on the star does not move the card');
  a.onmousedown(ev({target: a}));
  await h.open(b);
  const data = {}; a.ondragstart(ev({target: a, dataTransfer: {setData: (k, v) => {data[k] = v;}}}));
  assert.equal(h.el('evmPeek').hidden, true, 'dragging closes the full card');
  assert.equal(data['text/plain'], 'api:prov:a'); assert.match(a.className, /dragging/);
  const local = h.list('evmLocalList')[0], foreign = ev({target: local});
  local.ondragover(foreign);
  assert.equal(foreign.prevented, undefined, 'a card cannot be dropped into another column');
  c.getBoundingClientRect = () => ({top: 100, height: 40});
  const over = ev({clientY: 130, target: c}); c.ondragover(over);
  assert.equal(over.prevented, true); assert.match(c.className, /drop-after/);
  c.ondrop(ev({clientY: 130, target: c})); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/view'), [{base_revision: 7, section: 'api', order: ['api:prov:b', 'api:prov:c', 'api:prov:a']}]);
  assert.ok(h.cards().every(x => !/drop-|dragging/.test(x.className)), 'marks are cleared');
  const [b2] = h.cards(); b2.ondragstart(ev({target: b2, dataTransfer: {setData() {}}}));
  h.el('evmApiList').ondrop(ev({target: h.el('evmApiList')})); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/view')[1].order, ['api:prov:c', 'api:prov:a', 'api:prov:b'], 'a drop on the empty end moves the card to the end');
});

test('E25 favourites: the star adds and removes a reference, the column is ordered on its own and follows its source', async () => {
  const h = harness(); await settle();
  let status = api('red', 'NEVER_CONFIRMED'), favs = [], revision = 7;
  h.routes.set('/ultra/connections', () => catalog([conn('a', 'A'), conn('b', 'B')]));
  h.routes.set('/ultra/model-cards', () => cards([mcard('a', 'A'), mcard('b', 'B', {api: status})],
    {view: {state: 'SAVED', revision, hidden: 0, sections: {favorites: favs, api: ['api:prov:a', 'api:prov:b'], mcp: [], local: []}}}));
  h.routes.set('/ultra/model-cards/view', opts => {const body = JSON.parse(opts.body); favs = body.order; revision++;
    return {view: {state: 'SAVED', revision, hidden: 0, sections: {favorites: favs, api: ['api:prov:a', 'api:prov:b'], mcp: [], local: []}}};});
  h.el('viewEvm').onclick(); await settle();
  h.star(h.cards()[1]).onclick(ev()); await settle();
  h.star(h.cards()[0]).onclick(ev()); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/view'), [{base_revision: 7, section: 'favorites', order: ['api:prov:b']},
    {base_revision: 8, section: 'favorites', order: ['api:prov:b', 'api:prov:a']}]);
  assert.match(h.el('evmNotice').textContent, /Добавлено в избранное: A/);
  assert.deepEqual(h.list('evmFavList').map(c => c.getAttribute('data-connection')), ['api:prov:b', 'api:prov:a']);
  assert.equal(h.el('evmFavState').textContent, '2'); assert.equal(h.el('evmFavEmpty').hidden, true);
  assert.equal(h.star(h.cards()[0]).textContent, '★'); assert.equal(h.star(h.cards()[0]).getAttribute('aria-pressed'), 'true');
  assert.equal(h.list('evmFavList')[0].getAttribute('data-section'), 'favorites');
  await h.open(h.list('evmFavList')[1]);
  h.button(h.peek(), 'Выше').onclick(); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/view')[2], {base_revision: 9, section: 'favorites', order: ['api:prov:a', 'api:prov:b']});
  assert.deepEqual(h.cards().map(c => c.getAttribute('data-connection')), ['api:prov:a', 'api:prov:b'], 'the API column keeps its own order');
  status = api('green', 'CONFIRMED');
  h.el('evmRefresh').onclick(); await settle();
  assert.equal(h.dot(h.list('evmFavList')[1]).getAttribute('data-api'), 'green:CONFIRMED', 'a favourite shows its source as it is now');
  h.star(h.list('evmFavList')[0]).onclick(ev()); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/view')[3].order, ['api:prov:b']);
  assert.match(h.el('evmNotice').textContent, /Убрано из избранного: A/);
});

test('E26 a refused order is not kept locally: the saved state is reloaded and the reason told', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')]);
  h.routes.set('/ultra/model-cards/view', () => ({httpError: true, status: 409, data: {error: {code: 'settings_revision_conflict', message: 'changed'}}}));
  await h.open(h.cards()[0]);
  h.button(h.peek(), 'Ниже').onclick(); await settle();
  assert.deepEqual(h.cards().map(c => c.getAttribute('data-connection')), ['api:prov:a', 'api:prov:b']);
  assert.match(h.el('evmError').textContent, /уже изменились в другом окне/);
  assert.equal(h.calls.filter(c => c.url === '/ultra/model-cards').length, 2, 'the board is read again');
});

test('E27 one constructor for every kind: MCP and local entries, same tail of different kinds kept apart', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('x', 'API X')], undefined, [other('mcp', 'x', 'Agent X')], [other('local', 'x', 'Local X'), other('local', 'y', 'Local Y')]);
  assert.deepEqual(h.list('evmMcpList').map(c => c.getAttribute('data-connection')), ['mcp:prov:x']);
  assert.deepEqual(h.list('evmLocalList').map(c => c.getAttribute('data-connection')), ['local:prov:x', 'local:prov:y']);
  assert.equal(h.el('evmMcpEmpty').hidden, true); assert.equal(h.el('evmLocalEmpty').hidden, true);
  const mcp = h.list('evmMcpList')[0];
  assert.equal(mcp.className, h.cards()[0].className, 'the same compact component');
  assert.match(mcp.textContent, /MCP \/ агент · prov/); assert.equal(h.dot(mcp), null, 'no API indicator for an entry without one');
  await h.open(mcp);
  assert.match(h.peek().textContent, /Подробности появятся, когда источник этого подключения будет подключён/);
  assert.deepEqual(h.roles(h.peek()), []);
  assert.ok(h.button(h.peek(), 'Ниже'), 'the order of the column can be changed');
  assert.equal(h.button(h.list('evmLocalList')[0], 'Настройки'), null);
});

test('E28 «Изменить описание» opens Настройки → Модель with the cursor in the field; a click on the box does the same', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {description: 'Было'})]));
  let posted = null;
  h.routes.set('/ultra/model-cards/alpha/settings', opts => {posted = JSON.parse(opts.body); return {card: mcard('alpha', 'Alpha')};});
  await h.open(h.cards()[0]);
  h.button(h.peek(), 'Изменить описание').onclick(); await settle();
  assert.equal(h.el('evmSettingsWindow').hidden, false);
  assert.deepEqual([h.el('evmPaneConn').hidden, h.el('evmPaneModel').hidden], [true, false]);
  assert.equal(h.document.activeElement, h.el('evmSetDescription'));
  assert.equal(h.el('evmSetDescription').attrs.maxlength, '500');
  h.el('evmSetDescription').value = 'Новое'; h.el('evmSetDescription').oninput();
  h.el('evmSetSave').onclick(); await settle();
  assert.equal(posted.description, 'Новое'); assert.equal(posted.base_revision, 4);
  h.el('evmSetClose').onclick(); await settle();
  h.el('evmTabConn').onclick();
  await h.open(h.cards()[0]);
  h.find(h.peek(), e => (e.className || '').startsWith('strengths')).onclick(); await settle();
  assert.equal(h.el('evmPaneModel').hidden, false); assert.equal(h.document.activeElement, h.el('evmSetDescription'));
});

test('E30 the full card is placed next to its card and always inside the window (measured while visible)', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')]);
  Object.assign(h.context.window, {innerWidth: 390, innerHeight: 844});
  const box = h.el('evmPeek');
  Object.defineProperty(box, 'offsetHeight', {get() {return this.hidden ? 0 : 480;}});  // a hidden element has no height
  const card = h.cards()[1]; card.getBoundingClientRect = () => ({left: 24, top: 700, height: 52});
  await h.open(card);
  assert.deepEqual([box.style.width, box.style.left, box.style.top], ['366px', '12px', '352px'], 'clamped to the bottom edge, not 694px');
  Object.assign(h.context.window, {innerWidth: 1400, innerHeight: 950});
  card.getBoundingClientRect = () => ({left: 300, top: 200, height: 52});
  h.run("positionPeek()");
  assert.deepEqual([box.style.width, box.style.left, box.style.top], ['560px', '294px', '194px']);
  const header = new Element('header'); header.getBoundingClientRect = () => ({bottom: 240});
  h.document.querySelector = sel => sel === 'header.top' ? header : null;
  h.run("positionPeek()");
  assert.deepEqual([box.style.top, box.style.maxHeight], ['248px', '690px'], 'never under the sticky page header');
});

test('E29 layout rules: four columns on a wide screen, one on a narrow one, the page never needs a horizontal scroll', () => {
  assert.match(source, /@media\(min-width:1200px\)\{\.evm-board\{grid-template-columns:minmax\(200px,\.75fr\) minmax\(0,1\.25fr\) minmax\(0,1fr\) minmax\(0,1fr\)\}\}/);
  assert.match(source, /\.evm-columns\{grid-template-columns:1fr\}/);
  assert.match(source, /<div class="evm-columns evm-board">\s*<section class="evm-col" aria-labelledby="evmFavTitle">/);
  assert.match(source, /\.evm-peek\{position:fixed;[^}]*width:min\(560px,calc\(100vw - 24px\)\)/);
});
