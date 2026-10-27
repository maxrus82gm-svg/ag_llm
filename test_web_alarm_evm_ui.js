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
    cards: list, ...extra};
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
  h.cards = () => h.el('evmApiList').children;
  h.find = (root, pred) => {if (pred(root)) return root; for (const c of root.children || []) {const f = h.find(c, pred); if (f) return f;} return null;};
  h.findAll = (root, pred, out = []) => {if (pred(root)) out.push(root); for (const c of root.children || []) h.findAll(c, pred, out); return out;};
  h.cardButton = (card, label) => h.find(card, e => e.tag === 'button' && e.textContent.includes(label));
  h.dot = root => h.find(root, e => (e.className || '').startsWith('api-dot'));
  h.roles = card => h.findAll(card, e => e.className === 'role').map(r => [r.getAttribute('data-role'), r.getAttribute('data-state'), r.children[0].textContent]);
  h.options = () => h.el('evmChatModel').children.map(o => [o.value, o.disabled, o.textContent]);
  h.openEvm = async (list, data = cards(list.map(c => mcard(c.model_id, c.display_name)))) => {
    h.routes.set('/ultra/connections', () => catalog(list));
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

test('E2 opening EVM renders exactly the server catalog as model cards; no decorative registry lines', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha'), conn('beta', 'Beta'), conn('gamma', 'Gamma')]);
  assert.equal(h.el('evmView').hidden, false);
  assert.equal(h.el('layout').hidden, true);
  assert.equal(h.el('viewEvm').getAttribute('aria-pressed'), 'true');
  assert.deepEqual(h.cards().map(c => c.getAttribute('data-connection')), ['api:prov:alpha', 'api:prov:beta', 'api:prov:gamma']);
  const card = h.cards()[0];
  assert.equal(card.tag, 'article');
  assert.equal(card.children[0].children[0].textContent, 'Alpha');
  for (const gone of [/В реестре/, /API не проверено/, /→/, /P-alpha/, /Выбрана для чата/, /Выбрать/])
    assert.doesNotMatch(card.textContent, gone, 'the card still shows ' + gone);
  assert.ok(h.cardButton(card, 'Настройки') && h.cardButton(card, 'Проверить чат'));
  assert.equal(h.findAll(card, e => e.tag === 'button').length, 2, 'a card has exactly two buttons');
  assert.match(h.el('evmMcpState').textContent, /Ещё не подключено/);
  assert.match(h.el('evmLocalState').textContent, /Ещё не подключено/);
  assert.match(h.el('evmSelection').textContent, /ещё не выбрана/);
  assert.equal(h.el('evmState').textContent, 'Моделей в реестре: 3');
  assert.equal(h.el('showWorkspaces').hidden, true, 'operator-only mobile toggles stay visible in EVM');
  assert.deepEqual(h.evmCalls().filter(c => c.method === 'GET' && !c.url.includes('selection')).map(c => c.url).sort(),
    ['/ultra/connections', '/ultra/model-cards']);
});

test('E3 choosing the chat model (outside the cards) posts only role + connection_id once and shows the saved choice', async () => {
  const h = harness(); await settle();
  let saved = null;
  h.routes.set('/ultra/connections', () => catalog([conn('alpha', 'Alpha', {selected: saved === 'api:prov:alpha'}), conn('beta', 'Beta')],
    saved ? {role: 'chat', state: 'SAVED', connection_id: saved, model_id: 'alpha', display_name: 'Alpha', provider_model_id: 'P-alpha', selected_at: 'T1'} : undefined));
  h.routes.set('/ultra/model-cards', () => cards([mcard('alpha', 'Alpha'), mcard('beta', 'Beta')]));
  const gate = {};
  h.routes.set('/ultra/connections/selection', opts => new Promise(resolve => {gate.open = () => {saved = JSON.parse(opts.body).connection_id;
    resolve({selection: {role: 'chat', state: 'SAVED', connection_id: saved, model_id: 'alpha', display_name: 'Alpha', provider_model_id: 'P-alpha'}});};}));
  h.el('viewEvm').onclick(); await settle();
  assert.deepEqual(h.options(), [['', true, '— не выбрана —'], ['api:prov:alpha', false, 'Alpha'], ['api:prov:beta', false, 'Beta']]);
  assert.equal(h.el('evmChatModel').value, '');
  h.el('evmChatModel').value = 'api:prov:alpha'; h.el('evmChatModel').onchange();
  h.el('evmChatSave').onclick(); await settle();
  assert.equal(h.el('evmChatSave').disabled, true, 'saving blocks a second choice');
  h.el('evmChatModel').value = 'api:prov:beta'; h.el('evmChatSave').onclick(); await settle();
  gate.open(); await settle();
  const posts = h.calls.filter(c => c.method === 'POST');
  assert.equal(posts.length, 1);
  assert.deepEqual(JSON.parse(posts[0].body), {role: 'chat', connection_id: 'api:prov:alpha'});
  assert.equal(posts[0].headers['Content-Type'], 'application/json');
  assert.match(h.el('evmNotice').textContent, /Выбор сохранён: Alpha \(P-alpha\)/);
  assert.match(h.el('evmSelection').textContent, /Выбрана: Alpha · alpha → P-alpha/);
  assert.equal(h.el('evmChatModel').value, 'api:prov:alpha');
  assert.equal(h.el('evmChatSave').disabled, false);
});

test('E4 a refused choice is reported and the list is reloaded from the server, not changed locally', async () => {
  const h = harness(); await settle();
  h.routes.set('/ultra/connections/selection', () => ({httpError: true, status: 409, data: {error: {code: 'connection_disabled', message: 'model is disabled'}}}));
  await h.openEvm([conn('alpha', 'Alpha')]);
  h.el('evmChatModel').value = 'api:prov:alpha'; h.el('evmChatSave').onclick(); await settle();
  assert.match(h.el('evmError').textContent, /Выбор не сохранён: connection_disabled/);
  assert.equal(h.el('evmNotice').hidden, true);
  assert.match(h.el('evmSelection').textContent, /ещё не выбрана/);
  assert.equal(h.evmCalls().filter(c => c.url === '/ultra/connections').length, 2);
  const h2 = harness(); await settle();
  await h2.openEvm([conn('alpha', 'Alpha')]);
  h2.el('evmChatSave').onclick(); await settle();
  assert.match(h2.el('evmError').textContent, /Выберите модель/);
  assert.equal(h2.calls.filter(c => c.method === 'POST').length, 0);
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
  const name = '<img src=x onerror=alert(1)>';
  await h.openEvm([conn('off', name, {status: 'DISABLED', selectable: false})],
    cards([mcard('off', name, {description: '<script>x()</script>', api: api('red', 'REGISTRY_DISABLED')})]));
  assert.deepEqual(h.options()[1], ['api:prov:off', true, name + ' — отключена']);
  assert.equal(h.el('evmChatSave').disabled, true);
  assert.ok(h.all().every(e => !('innerHTML' in e)), 'markup was assigned');
  assert.equal(h.cards()[0].children[0].children[0].textContent, name);
  assert.match(h.cards()[0].textContent, /<script>x\(\)<\/script>/);
  assert.equal(h.dot(h.cards()[0]).getAttribute('data-api'), 'red:REGISTRY_DISABLED');
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

test('E10 role marks and hints are exactly the server facts; nothing is checked by the page itself', async () => {
  const h = harness(); await settle();
  const roles = [{role: 'r_chat', state: 'assigned'}, {role: 'r_plan', state: 'assigned_off'}, {role: 'r_check', state: 'unknown'}, {role: 'r_none', state: 'not_in_runtime'}];
  await h.openEvm([conn('alpha', 'Alpha'), conn('beta', 'Beta')], cards([mcard('alpha', 'Alpha', {roles}),
    mcard('beta', 'Beta', {roles: [{role: 'r_chat', state: 'assigned_pending'}, ...ROLE_DEFS.slice(1).map(r => ({role: r.role, state: 'not_assigned'}))]})]));
  assert.deepEqual(h.roles(h.cards()[0]), [['r_chat', 'assigned', '✓'], ['r_plan', 'assigned_off', '✓'], ['r_check', 'unknown', '?'], ['r_none', 'not_in_runtime', '–']]);
  assert.deepEqual(h.roles(h.cards()[1]), [['r_chat', 'assigned_pending', '✓'], ['r_plan', 'not_assigned', '×'], ['r_check', 'not_assigned', '×'], ['r_none', 'not_assigned', '×']]);
  const marks = h.findAll(h.cards()[0], e => (e.className || '').startsWith('mark ')).map(e => e.className);
  assert.deepEqual(marks, ['mark yes', 'mark off', 'mark unknown', 'mark na']);
  assert.equal(h.findAll(h.cards()[1], e => (e.className || '').startsWith('mark '))[0].className, 'mark off', 'a role that does not run yet is not a full green mark');
  assert.match(h.findAll(h.cards()[1], e => e.className === 'name')[0].getAttribute('data-hint'), /Сейчас: назначена, но роль пока не работает\./);
  const name = h.findAll(h.cards()[0], e => e.className === 'name')[1];
  assert.equal(name.getAttribute('data-hint'), 'Подсказка Роль-план Сейчас: назначена, но роль выключена.');
  assert.equal(name.getAttribute('tabindex'), '0');
  assert.ok(h.findAll(h.cards()[0], e => e.className === 'role').every(r => !h.find(r, e => e.tag === 'button')), 'roles are text, not buttons');
  // a state the page does not know is shown as unknown, never as assigned
  const h2 = harness(); await settle();
  await h2.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {roles: [{role: 'r_chat', state: 'ASSIGNED!'}]})]));
  assert.deepEqual(h2.roles(h2.cards()[0])[0], ['r_chat', 'unknown', '?']);
  assert.deepEqual(h2.roles(h2.cards()[0]).slice(1).map(r => r[1]), ['unknown', 'unknown', 'unknown'], 'a role missing from the answer is unknown');
  assert.match(h.el('evmRolesSource').textContent, /настройки прежней Ultra/);
});

test('E11 one API status component: the card and the diagnostic window show the same server status', async () => {
  for (const [status, mark, text] of [[api('green', 'CONFIRMED'), '✓', /подтверждён: 3 дн\. назад/], [api('orange', 'STALE', {age_days: 41}), '!', /устарело: 41 дн\./],
    [api('red', 'SETTINGS_CHANGED', {last_success_at: '2026-09-01T10:00:00+00:00'}), '×', /изменились/]]) {
    const h = harness(); await settle();
    await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {api: status})]));
    const cardDot = h.dot(h.cards()[0]);
    assert.equal(cardDot.textContent, mark);
    assert.match(cardDot.getAttribute('aria-label'), text);
    h.cardButton(h.cards()[0], 'Проверить чат').onclick(); await settle();
    assert.equal(h.el('evmCheckWindow').hidden, false);
    assert.equal(h.el('evmSettingsWindow').hidden, true);
    const windowDot = h.el('evmCheckDot').children[0];
    assert.deepEqual([windowDot.className, windowDot.textContent, windowDot.getAttribute('data-api'), windowDot.getAttribute('aria-label')],
      [cardDot.className, cardDot.textContent, cardDot.getAttribute('data-api'), cardDot.getAttribute('aria-label')]);
    assert.match(h.el('evmCheckLast').textContent, status.last_success_at ? /Последний успешный ответ: \d/ : /отсутствует/);
    assert.equal(h.el('evmCheckName').textContent, 'Проверка API — Alpha');
  }
});

test('E12 header: parameter count as given, unknown stays unknown; the description is shown in a fixed box', async () => {
  const h = harness(); await settle();
  const long = 'Сильная сторона. '.repeat(29).trim();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')], cards([mcard('a', 'A', {params_billion: 390, description: long}), mcard('b', 'B', {params_billion: 2.5})]));
  const params = card => h.find(card, e => e.className === 'params');
  assert.equal(params(h.cards()[0]).textContent, '390 млрд');
  assert.equal(params(h.cards()[1]).textContent, '2,5 млрд');
  const box = h.find(h.cards()[0], e => (e.className || '').startsWith('strengths'));
  assert.equal(box.textContent, long);
  assert.equal(box.className, 'strengths');
  const empty = h.find(h.cards()[1], e => (e.className || '').startsWith('strengths'));
  assert.equal(empty.className, 'strengths placeholder', 'not the operator panel .empty block');
  assert.match(empty.textContent, /Описание пока не заполнено/);
  assert.match(source, /\.strengths\{height:84px;overflow-y:auto;[^}]*line-height:1\.15/);
  const h2 = harness(); await settle();
  await h2.openEvm([conn('a', 'A')]);
  assert.equal(params(h2.cards()[0]).textContent, '— млрд');
});

test('E13 settings: the form shows server facts, the key value never, and posts exactly the edited values', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {params_billion: 12, description: 'Было'})]));
  let posted = null;
  h.routes.set('/ultra/model-cards/alpha/settings', opts => {posted = JSON.parse(opts.body); return {card: mcard('alpha', 'Alpha')};});
  h.cardButton(h.cards()[0], 'Настройки').onclick(); await settle();
  assert.equal(h.el('evmSettingsWindow').hidden, false);
  assert.equal(h.el('evmCheckWindow').hidden, true);
  assert.equal(h.document.activeElement, h.el('evmSetTitle'));
  assert.equal(h.el('evmSetProvider').disabled, true, 'the registry fixes the provider of a model');
  assert.deepEqual(h.el('evmSetProfile').children.map(o => o.value), ['prov-default', 'prov-second']);
  const conn_ = h.el('evmSetConnFacts').textContent;
  assert.match(conn_, /Тариф S/); assert.match(conn_, /https:\/\/api\.example/); assert.match(conn_, /Задан \(переменная среды PROV_KEY\)\. Значение в браузер не передаётся/);
  assert.match(h.el('evmSetModelFacts').textContent, /P-alpha.*alpha.*api:prov:alpha/s);
  assert.equal(h.el('evmSetDescription').attrs.maxlength, '500');
  assert.equal(h.el('evmSetDescCount').textContent, '4 / 500');
  h.el('evmTabModel').onclick();
  assert.deepEqual([h.el('evmPaneConn').hidden, h.el('evmPaneModel').hidden, h.el('evmPaneMore').hidden], [true, false, true]);
  assert.equal(h.el('evmTabModel').getAttribute('aria-selected'), 'true');
  h.el('evmSetDescription').value = 'Новое описание'; h.el('evmSetDescription').oninput();
  h.el('evmSetParams').value = '70,5'; h.el('evmSetParams').oninput();
  h.el('evmTabMore').onclick();
  h.el('evmSetFreshness').value = '45'; h.el('evmSetFreshness').oninput();
  assert.equal(h.el('evmSetDraft').hidden, false);
  assert.equal(h.el('evmSetDescCount').textContent, '14 / 500');
  h.el('evmSetSave').onclick(); await settle();
  assert.deepEqual(posted, {base_revision: 4, description: 'Новое описание', params_billion: 70.5, profile_id: 'prov-default',
    profile: {timeout_seconds: 30, diagnostic_limit_chars: 1000, freshness_days: 45}});
  assert.match(h.el('evmNotice').textContent, /Настройки сохранены: Alpha/);
  assert.equal(h.el('evmSetDraft').hidden, true, 'the saved draft is gone; the form shows the server again');
  assert.equal(h.el('evmSetDescription').value, 'Было', 'after saving the form is refilled from the server answer');
  assert.ok(!JSON.stringify(h.calls).includes('PROV_KEY='), 'no key value travels');
});

test('E14 settings: an empty count is null, a bad one is refused locally, a revision conflict keeps the draft', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {params_billion: 12})]));
  const posts = [];
  h.routes.set('/ultra/model-cards/alpha/settings', opts => {posts.push(JSON.parse(opts.body));
    return {httpError: true, status: 409, data: {error: {code: 'settings_revision_conflict', message: 'settings changed'}}};});
  h.cardButton(h.cards()[0], 'Настройки').onclick(); await settle();
  h.el('evmSetParams').value = '-3'; h.el('evmSetParams').oninput();
  h.el('evmSetSave').onclick(); await settle();
  assert.equal(posts.length, 0);
  assert.match(h.el('evmSetError').textContent, /положительное число/);
  h.el('evmSetParams').value = ''; h.el('evmSetParams').oninput();
  assert.match(h.el('evmSetParamsSource').textContent, /Неизвестно/);
  h.el('evmSetSave').onclick(); await settle();
  assert.equal(posts.length, 1);
  assert.equal(posts[0].params_billion, null);
  assert.match(h.el('evmSetError').textContent, /изменены в другом окне/);
  assert.equal(h.el('evmSetDraft').hidden, false, 'the draft survives a conflict');
  assert.equal(h.el('evmSetSave').disabled, false);
  h.el('evmSetReset').onclick();
  assert.equal(h.el('evmSetParams').value, '12');
  assert.equal(h.el('evmSetDraft').hidden, true);
  // another profile brings its own values
  h.el('evmSetProfile').value = 'prov-second'; h.el('evmSetProfile').onchange();
  assert.deepEqual([h.el('evmSetTimeout').value, h.el('evmSetDiagLimit').value, h.el('evmSetFreshness').value], ['60', '500', '7']);
});

test('E15 opening one window keeps the state of the other; closing returns focus to the card button', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha'), conn('beta', 'Beta')]);
  h.routes.set('/ultra/model-cards/alpha/check', () => ({outcome: 'LIVE_CHECK_NOT_AUTHORIZED', message: 'Нужен USER GO.', network_calls: 0, test_message: 'Тест.', card: mcard('alpha', 'Alpha')}));
  h.cardButton(h.cards()[0], 'Настройки').onclick(); await settle();
  h.el('evmSetDescription').value = 'Черновик A'; h.el('evmSetDescription').oninput();
  h.el('evmSetClose').onclick(); await settle();
  assert.equal(h.el('evmSettingsWindow').hidden, true);
  assert.equal(h.document.activeElement.textContent, '⚙ Настройки');
  assert.match(h.cards()[0].textContent, /несохранённые изменения/);
  h.cardButton(h.cards()[0], 'Проверить чат').onclick(); await settle();
  h.el('evmCheckSend').onclick(); await settle();
  const answer = h.el('evmCheckOutput').textContent;
  assert.match(answer, /Сообщение не отправлялось.*Статус API не изменён/s);
  h.el('evmCheckClose').onclick(); await settle();
  assert.equal(h.document.activeElement.textContent, '▤ Проверить чат');
  h.cardButton(h.cards()[1], 'Настройки').onclick(); await settle();
  assert.equal(h.el('evmSetDescription').value, '', 'another model has its own form');
  h.el('evmSetClose').onclick(); await settle();
  h.cardButton(h.cards()[0], 'Настройки').onclick(); await settle();
  assert.equal(h.el('evmSetDescription').value, 'Черновик A');
  assert.equal(h.el('evmSetDraft').hidden, false);
  h.el('evmSetClose').onclick(); await settle();
  h.cardButton(h.cards()[0], 'Проверить чат').onclick(); await settle();
  assert.equal(h.el('evmCheckOutput').textContent, answer);
  h.el('evmSettingsWindow').onclick({target: h.el('evmSetTitle')});
  assert.equal(h.el('evmCheckWindow').hidden, false, 'a click inside a window does not close it');
  h.el('evmCheckWindow').onclick({target: h.el('evmCheckWindow')});
  assert.equal(h.el('evmCheckWindow').hidden, true, 'a click on the backdrop closes it');
});

test('E16 the check: one empty POST, no input field, the indicator comes only from the server', async () => {
  const outcomes = [
    [{outcome: 'LIVE_CHECK_NOT_AUTHORIZED', message: 'Нужен USER GO.', network_calls: 0}, /Сообщение не отправлялось\. Нужен USER GO\./, 'output info'],
    [{outcome: 'SIMULATED', text: 'Привет!'}, /ИМИТАЦИЯ.*статус API не изменён.*Привет!/s, 'output info'],
    [{outcome: 'CONFIRMED', text: 'Получено.'}, /^Получено\.$/, 'output reply'],
    [{outcome: 'FAILED', text: 'http_401: unauthorized'}, /http_401/, 'output error'],
    [{httpError: true, status: 409, data: {error: {code: 'check_refused', message: 'no adapter'}}}, /Проверка не выполнена: check_refused/, 'output error'],
  ];
  for (const [answer, expected, cls] of outcomes) {
    const h = harness(); await settle();
    let status = api('red', 'NEVER_CONFIRMED');
    h.routes.set('/ultra/connections', () => catalog([conn('alpha', 'Alpha')]));
    h.routes.set('/ultra/model-cards', () => cards([mcard('alpha', 'Alpha', {api: status})]));
    h.routes.set('/ultra/model-cards/alpha/check', () => answer.httpError ? answer : {test_message: 'Тест.', card: mcard('alpha', 'Alpha'), ...answer});
    h.el('viewEvm').onclick(); await settle();
    h.cardButton(h.cards()[0], 'Проверить чат').onclick(); await settle();
    assert.equal(h.el('evmCheckNote').textContent, 'Тестовое сообщение: «Тест.» — в этой версии оно не отправляется.');
    status = api('red', 'NEVER_CONFIRMED');  // the server did not confirm anything, whatever the answer text says
    h.el('evmCheckSend').onclick(); await settle();
    const post = h.calls.filter(c => c.method === 'POST');
    assert.deepEqual(post.map(c => [c.url, c.body]), [['/ultra/model-cards/alpha/check', '{}']]);
    assert.match(h.el('evmCheckOutput').textContent, expected);
    assert.equal(h.el('evmCheckOutput').className, cls);
    assert.equal(h.el('evmCheckDot').children[0].textContent, '×', 'a check answer never paints the indicator by itself');
    assert.equal(h.dot(h.cards()[0]).textContent, '×');
    assert.equal(h.el('evmCheckSend').disabled, false);
  }
  assert.doesNotMatch(source.match(/<div id="evmCheckWindow"[\s\S]*?<\/div><\/div>/)[0], /<input|<textarea/, 'the diagnostic window has no input field');
  const order = source.match(/id="evmCheckClose"[\s\S]*?id="evmCheckSend"/);
  assert.ok(order, 'buttons are [Закрыть] [Отправить тестовое сообщение]');
});

test('E17 when the model cards cannot be read, cards show no invented roles or status', async () => {
  for (const answer of [{httpError: true, status: 403, data: {error: {code: 'model_cards_forbidden', message: 'x'}}}, {cards: 'nope'},
    cards([mcard('alpha', 'Alpha', {api: {color: 'blue', reason: 'X'}})])]) {
    const h = harness(); await settle();
    await h.openEvm([conn('alpha', 'Alpha')], answer);
    assert.equal(h.cards().length, 1);
    assert.match(h.cards()[0].textContent, /Подробности карточки недоступны/);
    assert.equal(h.dot(h.cards()[0]), null);
    assert.deepEqual(h.roles(h.cards()[0]), []);
    assert.equal(h.cardButton(h.cards()[0], 'Настройки'), null);
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

test('E20 damaged stores are reported, and a damaged settings file can still be saved over on purpose', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha')], {settings: {state: 'CORRUPT', revision: null, ignored: 0}, checks: {state: 'CORRUPT'}}));
  assert.match(h.el('evmError').textContent, /Повреждены настройки карточек и сведения о проверках API/);
  let posted = null;
  h.routes.set('/ultra/model-cards/alpha/settings', opts => {posted = JSON.parse(opts.body); return {card: mcard('alpha', 'Alpha')};});
  h.cardButton(h.cards()[0], 'Настройки').onclick(); await settle();
  h.el('evmSetSave').onclick(); await settle();
  assert.equal(posted.base_revision, null);
});

test('E19 the chat composer keeps a disabled place for voice input and posts nothing', async () => {
  const h = harness(); await settle();
  assert.equal(h.el('chatMic').getAttribute('data-extension'), 'voice-input');
  assert.equal(h.el('chatMic').onclick, undefined, 'the place has no behaviour yet');
  assert.equal(h.calls.filter(c => c.method !== 'GET').length, 0);
  assert.match(source, /<span class="composer-actions"><button type="button" id="chatMic" disabled[^>]*>[^<]*<\/button><button type="button" id="chatSend" disabled>Отправить<\/button><\/span>/);
});
