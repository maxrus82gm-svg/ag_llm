// WUA-1 EVM tab: run the actual shipped client in the same deterministic DOM adapter as
// test_web_alarm_operator_ui.js (node:vm, no packages, no network, no project writes).
// Fixture models are invented on purpose: the page must render whatever the server read
// model returns and contain no copy of the Ultra model registry.
// CLAUDE-WUA-EVM-COMPACT-LAYOUT-001: four columns of compact cards, manual order, favourites and the chat-model
// picker next to the Ultra Chat composer.
// CLAUDE-WUA-EVM-INTERACTION-DND-001: a click opens the full card in place; Ctrl + hover / Ctrl + click / «⧉» show the
// same card in a side panel beside the column; the mouse reorders a column and adds references to «Избранное»
// (Pointer Events with a movement threshold; the pointer handlers are called here as the browser would call them).
// CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001: «⧉», Ctrl + click and a press on the preview give independent pinned windows
// (one per connection_id) under the preview; moved by the title, closed only by their «×», saved per window.
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
  append(...children) {for (const c of children) if (c && typeof c === 'object') c.parentNode = this; this.children.push(...children);}
  replaceChildren(...children) {this._text = ''; for (const c of children) if (c && typeof c === 'object') c.parentNode = this; this.children = children;}
  remove() {const p = this.parentNode; if (p) p.children = p.children.filter(c => c !== this); this.parentNode = null;}
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
const rect = (left, top, width, height) => ({left, top, width, height, right: left + width, bottom: top + height});
// A fixed board for pointer tests: four columns 280 px wide side by side; compact cards 40 px high, 8 px apart.
// Card i of a column spans y 150+48i … 190+48i (its middle is 170+48i); x 14 px inside its column.
const COLUMN_LEFT = {Fav: 20, Api: 320, Mcp: 620, Local: 920};

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
  h.quickBtn = card => h.find(card, e => e.className === 'cquick');
  h.head = card => card.children[0];  // the compact row: grip, «open», «⧉», star
  h.inline = card => card.children[1]?.children[0] || null;  // the full card shown in place, if the card is open
  h.peek = () => h.el('evmPeek').children[1];  // the full card in the side panel ([0] is its bar)
  h.bar = () => h.el('evmPeek').children[0];
  h.pins = () => h.el('evmPins').children;  // pinned windows in the order they were opened
  h.pin = id => h.pins().find(p => p.getAttribute('data-connection') === (id.includes(':') ? id : 'api:prov:' + id)) || null;
  h.pinBar = pin => pin.children[0];
  h.pinCard = pin => pin.children[1].children[0] || null;  // the full card in a pinned window
  h.pinClose = pin => h.find(pin.children[0], e => e.className === 'pin-close');
  h.ctrlHover = (card, ctrl = true) => card.onmouseenter(ev({ctrlKey: ctrl}));  // the pointer enters a card
  h.roles = card => h.findAll(card, e => e.className === 'role').map(r => [r.getAttribute('data-role'), r.getAttribute('data-state'), r.children[0].textContent]);
  h.click = async (card, extra = {}) => {h.head(card).onclick(ev({detail: 1, target: h.opener(card), ...extra})); await settle();};  // a mouse click
  h.open = h.click;
  h.quick = async (card, extra = {}) => {h.quickBtn(card).onclick(ev({detail: 1, ...extra})); await settle();};  // «⧉»: a pinned window
  h.full = async (card, mode) => {  // the full card: in place ('inline'), in a pinned window ('pin') or in the preview ('preview')
    if (mode === 'pin') {await h.quick(card); return h.pinCard(h.pin(card.getAttribute('data-connection')));}
    if (mode === 'preview') {h.ctrlHover(card); return h.peek();}
    if (!h.inline(card)) await h.click(card);
    return h.inline(card);
  };
  h.layout = () => {  // geometry of the board as it is drawn now (call again after every redraw)
    for (const [name, left] of Object.entries(COLUMN_LEFT)) {
      const list = h.el('evm' + name + 'List');
      h.el('evm' + name + 'Col').getBoundingClientRect = () => rect(left, 100, 280, 800);
      list.getBoundingClientRect = () => rect(left + 14, 150, 252, Math.max(12, list.children.length * 48 - 8));
      list.children.forEach((card, i) => {const r = rect(left + 14, 150 + i * 48, 252, 40); card.getBoundingClientRect = () => r; h.head(card).getBoundingClientRect = () => r;});
    }
  };
  h.press = (card, x, y, extra = {}) => {const e = ev({button: 0, clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse', target: h.opener(card), ...extra}); h.head(card).onpointerdown(e); return e;};
  h.move = (x, y, extra = {}) => {const e = ev({clientX: x, clientY: y, pointerId: 1, buttons: 1, ...extra}); h.run('pressMove')(e); return e;};
  h.release = async (x, y, card) => {  // pointerup, then the click the browser fires on the pressed card
    h.run('pressEnd')(ev({clientX: x, clientY: y, pointerId: 1}));
    if (card) h.head(card).onclick(ev({detail: 1, target: h.opener(card)}));
    await settle();
  };
  h.drag = async (card, from, to, steps = [], click = true) => {  // a whole mouse drag with a release and its click
    h.press(card, ...from);
    for (const point of [...steps, to]) h.move(...point);
    await h.release(...to, click ? card : null);
    h.layout();
  };
  h.ids = id => h.list(id).map(c => c.getAttribute('data-connection'));
  h.viewRoute = (sections = {}) => {  // the server stores what it is sent and answers with the next revision
    let revision = 7;
    const saved = {favorites: [], api: null, mcp: [], local: [], ...sections};
    h.routes.set('/ultra/model-cards/view', opts => {
      const body = JSON.parse(opts.body); saved[body.section] = body.order; revision++;
      return {view: {state: 'SAVED', revision, hidden: 0, sections: {...saved, api: saved.api || h.ids('evmApiList')}}};
    });
    return saved;
  };
  h.layoutRoute = (start = []) => {  // one window per entry; an open or a move puts it on top; null closes it
    const saved = {windows: start.map(w => ({...w})), revision: 0};
    h.routes.set('/ultra/model-cards/layout', opts => {
      const body = JSON.parse(opts.body); saved.windows = saved.windows.filter(w => w.connection_id !== body.connection_id);
      if (body.window) saved.windows.push({connection_id: body.connection_id, ...body.window});
      saved.revision++;
      return {view: {layout: {state: 'SAVED', revision: saved.revision, windows: saved.windows.map(w => ({...w})), hidden: 0}}};
    });
    return saved;
  };
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

test('E2 the board: four columns, compact cards in server order, honest empty columns, a closed card holds no full card', async () => {
  const h = harness(); await settle();
  const list = [conn('alpha', 'Alpha'), conn('beta', 'Beta'), conn('gamma', 'Gamma')];
  await h.openEvm(list, cards([mcard('alpha', 'Alpha', {params_billion: 390, api: api('green', 'CONFIRMED')}), mcard('beta', 'Beta'), mcard('gamma', 'Gamma')],
    {view: {state: 'SAVED', revision: 7, hidden: 0, sections: {favorites: [], api: ['api:prov:gamma', 'api:prov:alpha', 'api:prov:beta'], mcp: [], local: []}}}));
  assert.equal(h.el('evmView').hidden, false);
  assert.deepEqual([...source.matchAll(/<h3 id="evm(Fav|Api|Mcp|Local)Title">([^<]+)<\/h3>/g)].map(m => m[2]), ['★ Избранное', 'API', 'MCP / Агенты', 'Локальные LLM']);
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:gamma', 'api:prov:alpha', 'api:prov:beta']);
  const alpha = h.cards()[1];
  assert.equal(alpha.tag, 'article');
  assert.equal(alpha.getAttribute('role'), null, 'the card itself is not a button around other buttons');
  assert.equal(alpha.onclick, undefined, 'a click inside an open card never closes it: only the compact row toggles');
  const opener = h.opener(alpha), part = alpha.children[1];
  assert.deepEqual([opener.tag, opener.getAttribute('aria-expanded'), opener.getAttribute('aria-controls'), opener.getAttribute('aria-haspopup')],
    ['button', 'false', part.id, null], 'a disclosure of the card in place, not a pop-up');
  assert.deepEqual([part.className, part.hidden, part.getAttribute('role'), part.children.length], ['cexp', true, 'region', 0]);
  assert.match(opener.getAttribute('aria-label'), /^Alpha — API\. Раскрыть карточку; Alt\+↑\/↓ — переставить$/);
  assert.ok(!h.findAll(opener, e => e.tag === 'button' && e !== opener).length, 'no control inside another control');
  assert.match(alpha.textContent, /Alpha/); assert.match(alpha.textContent, /API · Провайдер/); assert.match(alpha.textContent, /390 млрд/);
  assert.equal(h.dot(alpha).getAttribute('data-api'), 'green:CONFIRMED');
  assert.doesNotMatch(h.cards()[0].textContent, /млрд/, 'an unknown parameter count is not shown in the compact card');
  for (const card of h.cards()) {
    assert.deepEqual(h.findAll(card, e => e.tag === 'button').map(b => b.className), ['copen', 'cquick', 'star'], 'the compact card: «open», «⧉» and the star');
    assert.deepEqual([h.quickBtn(card).getAttribute('aria-haspopup'), h.quickBtn(card).getAttribute('aria-expanded')], ['dialog', 'false']);
    assert.match(h.quickBtn(card).getAttribute('aria-label'), /^Закрепить в отдельном окне: /);
    assert.equal(h.roles(card).length, 0);
    assert.equal(h.find(card, e => (e.className || '').startsWith('strengths')), null);
    assert.equal(card.getAttribute('draggable'), null, 'no native drag-and-drop');
  }
  assert.equal(new Set(h.cards().map(c => c.children[1].id)).size, 3, 'every region has its own id');
  assert.equal(h.el('evmPeek').hidden, true);
  assert.equal(h.list('evmFavList').length, 0); assert.equal(h.el('evmFavEmpty').hidden, false); assert.equal(h.el('evmFavState').textContent, '0');
  assert.match(source, /id="evmFavEmpty" class="muted">Перетащите модель сюда или отметьте её звёздочкой ☆\. Здесь хранится ссылка/);
  assert.equal(h.el('evmMcpEmpty').hidden, false); assert.equal(h.el('evmLocalEmpty').hidden, false);
  assert.match(h.el('evmMcpState').textContent, /Ещё не подключено/); assert.match(h.el('evmLocalState').textContent, /Ещё не подключено/);
  assert.match(h.el('evmSelection').textContent, /ещё не выбрана/);
  assert.equal(h.el('evmSummary').textContent, '✓ 1 · ! 0 · × 2');
  assert.equal(h.el('evmState').textContent, 'Моделей в реестре: 3');
  assert.equal(h.el('showWorkspaces').hidden, true, 'operator-only mobile toggles stay hidden in EVM');
  assert.deepEqual(h.evmCalls().filter(c => c.method === 'GET' && !c.url.includes('selection')).map(c => c.url).sort(), ['/ultra/connections', '/ultra/model-cards']);
  assert.equal(source.includes('id="evmChatModel"'), false, 'the large chat-model block left EVM');
  assert.match(source, /Нажмите на карточку — она раскроется на месте\. Ctrl \+ наведение — быстрый просмотр сбоку/);
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

test('E7 server text is never markup, in the compact card, in place, in a pinned window and in the preview', async () => {
  for (const mode of ['inline', 'pin', 'preview']) {
    const h = harness(); await settle();
    const name = '<img src=x onerror=alert(1)>';
    await h.openEvm([conn('off', name, {status: 'DISABLED', selectable: false})],
      cards([mcard('off', name, {description: '<script>x()</script>', api: api('red', 'REGISTRY_DISABLED')})]));
    assert.equal(h.find(h.cards()[0], e => e.className === 'cname').textContent, name);
    const full = await h.full(h.cards()[0], mode);
    assert.equal(full.children[0].children[0].textContent, name);
    assert.match(full.textContent, /<script>x\(\)<\/script>/);
    assert.equal(h.dot(full).getAttribute('data-api'), 'red:REGISTRY_DISABLED');
    if (mode === 'preview') assert.equal(h.el('evmPeek').getAttribute('aria-label'), 'Быстрый просмотр: ' + name + ' · API');
    if (mode === 'pin') {
      assert.equal(h.pin('off').getAttribute('aria-label'), 'Окно модели: ' + name);
      assert.equal(h.find(h.pinBar(h.pin('off')), e => e.className === 'pin-title').textContent, name + ' · API');
    }
    assert.ok(h.all().every(e => !('innerHTML' in e)), 'markup was assigned');
  }
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

test('E10 role marks and hints in the full card are exactly the server facts, in place, in a pinned window and in the preview', async () => {
  for (const mode of ['inline', 'pin', 'preview']) {
    const h = harness(); await settle();
    const roles = [{role: 'r_chat', state: 'assigned'}, {role: 'r_plan', state: 'assigned_off'}, {role: 'r_check', state: 'unknown'}, {role: 'r_none', state: 'not_in_runtime'}];
    await h.openEvm([conn('alpha', 'Alpha'), conn('beta', 'Beta')], cards([mcard('alpha', 'Alpha', {roles}),
      mcard('beta', 'Beta', {roles: [{role: 'r_chat', state: 'assigned_pending'}, ...ROLE_DEFS.slice(1).map(r => ({role: r.role, state: 'not_assigned'}))]})]));
    const first = await h.full(h.cards()[0], mode);
    assert.deepEqual(h.roles(first), [['r_chat', 'assigned', '✓'], ['r_plan', 'assigned_off', '✓'], ['r_check', 'unknown', '?'], ['r_none', 'not_in_runtime', '–']]);
    const marks = h.findAll(first, e => (e.className || '').startsWith('mark ')).map(e => e.className);
    assert.deepEqual(marks, ['mark yes', 'mark off', 'mark unknown', 'mark na']);
    assert.equal(h.findAll(first, e => e.className === 'name')[1].getAttribute('data-hint'), 'Подсказка Роль-план Сейчас: назначена, но роль выключена.');
    const second = await h.full(h.cards()[1], mode);
    assert.deepEqual(h.roles(second), [['r_chat', 'assigned_pending', '✓'], ['r_plan', 'not_assigned', '×'], ['r_check', 'not_assigned', '×'], ['r_none', 'not_assigned', '×']]);
    const h2 = harness(); await settle();
    await h2.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {roles: [{role: 'r_chat', state: 'ASSIGNED!'}]})]));
    assert.deepEqual(h2.roles(await h2.full(h2.cards()[0], mode)).map(r => r[1]), ['unknown', 'unknown', 'unknown', 'unknown'], 'an unknown or missing state is never a check mark');
  }
});

test('E11 one API status component: compact card, card in place, preview, pinned window and diagnostic window show the same server status', async () => {
  for (const [status, mark] of [[api('green', 'CONFIRMED'), '✓'], [api('orange', 'STALE', {age_days: 41}), '!'], [api('red', 'SETTINGS_CHANGED'), '×']]) {
    const h = harness(); await settle();
    await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {api: status})]));
    const compact = h.dot(h.cards()[0]);
    const inline = h.dot(await h.full(h.cards()[0], 'inline'));
    const preview = h.dot(await h.full(h.cards()[0], 'preview'));
    h.run('closePeek()');
    const pin = h.dot(await h.full(h.cards()[0], 'pin'));
    h.button(h.pinCard(h.pin('alpha')), 'Проверить чат').onclick(); await settle();
    const windowDot = h.el('evmCheckDot').children[0];
    for (const d of [inline, preview, pin, windowDot])
      assert.deepEqual([d.className, d.textContent, d.getAttribute('data-api'), d.getAttribute('aria-label')],
        [compact.className, mark, compact.getAttribute('data-api'), compact.getAttribute('aria-label')]);
  }
});

test('E12 full card: parameter count as given, description box editable by a visible command (in place, pinned, preview)', async () => {
  for (const mode of ['inline', 'pin', 'preview']) {
    const h = harness(); await settle();
    await h.openEvm([conn('a', 'A'), conn('b', 'B')], cards([mcard('a', 'A', {params_billion: 2.5, description: 'Сильная сторона.'}), mcard('b', 'B')]));
    const first = await h.full(h.cards()[0], mode);
    assert.equal(h.find(first, e => e.className === 'params').textContent, '2,5 млрд');
    const box = h.find(first, e => (e.className || '').startsWith('strengths'));
    assert.deepEqual([box.className, box.textContent], ['strengths editable', 'Сильная сторона.']);
    const second = await h.full(h.cards()[1], mode);
    assert.equal(h.find(second, e => e.className === 'params').textContent, '— млрд');
    const empty = h.find(second, e => (e.className || '').startsWith('strengths'));
    assert.equal(empty.className, 'strengths editable placeholder', 'not the operator panel .empty block');
    assert.match(empty.textContent, /Нажмите «Изменить описание»/);
    assert.ok(h.button(second, 'Изменить описание'));
  }
  assert.match(source, /\.strengths\{height:84px;overflow-y:auto;[^}]*line-height:1\.15/);
});

test('E13 settings from the card in place: server facts, never the key value, the exact edited values', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {params_billion: 12, description: 'Было'})]));
  let posted = null;
  h.routes.set('/ultra/model-cards/alpha/settings', opts => {posted = JSON.parse(opts.body); return {card: mcard('alpha', 'Alpha')};});
  await h.click(h.cards()[0]);
  h.button(h.inline(h.cards()[0]), 'Настройки').onclick(); await settle();
  assert.equal(h.el('evmSettingsWindow').hidden, false);
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

test('E14 settings from a pinned window: a bad count is refused locally, a revision conflict keeps the draft', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {params_billion: 12})]));
  const posts = [];
  h.routes.set('/ultra/model-cards/alpha/settings', opts => {posts.push(JSON.parse(opts.body));
    return {httpError: true, status: 409, data: {error: {code: 'settings_revision_conflict', message: 'settings changed'}}};});
  await h.quick(h.cards()[0]);
  h.button(h.pinCard(h.pin('alpha')), 'Настройки').onclick(); await settle();
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

test('E15 one dialog keeps the state of the other; closing gives the keyboard back to the command that opened it (in place and in a pinned window)', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha'), conn('beta', 'Beta')]);
  h.routes.set('/ultra/model-cards/alpha/check', () => ({outcome: 'LIVE_CHECK_NOT_AUTHORIZED', message: 'Нужен USER GO.', network_calls: 0, test_message: 'Тест.', card: mcard('alpha', 'Alpha')}));
  await h.click(h.cards()[0]);
  const settings = h.button(h.inline(h.cards()[0]), 'Настройки'); settings.focus(); settings.onclick(); await settle();
  h.el('evmSetDescription').value = 'Черновик A'; h.el('evmSetDescription').oninput();
  h.el('evmSetClose').onclick(); await settle();
  assert.equal(h.el('evmSettingsWindow').hidden, true);
  assert.ok(h.inline(h.cards()[0]), 'the card stays open in place');
  assert.equal(h.document.activeElement, h.button(h.inline(h.cards()[0]), 'Настройки'), 'the keyboard is back on «Настройки» of the same card');
  assert.match(h.inline(h.cards()[0]).textContent, /несохранённые изменения/);
  h.button(h.inline(h.cards()[0]), 'Проверить чат').onclick(); await settle();
  h.el('evmCheckSend').onclick(); await settle();
  const answer = h.el('evmCheckOutput').textContent;
  assert.match(answer, /Сообщение не отправлялось.*Статус API не изменён/s);
  h.el('evmCheckWindow').onclick({target: h.el('evmCheckWindow')}); await settle();
  assert.equal(h.el('evmCheckWindow').hidden, true, 'a click on the backdrop closes it');
  assert.equal(h.document.activeElement, h.button(h.inline(h.cards()[0]), 'Проверить чат'));
  await h.quick(h.cards()[0]);
  const pinCard = () => h.pinCard(h.pin('alpha'));
  h.button(pinCard(), 'Настройки').onclick(); await settle();
  assert.equal(h.el('evmSetDescription').value, 'Черновик A');
  assert.equal(h.pins().length, 1, 'the pinned window stays under the dialog');
  h.run("escapeKey({key:'Escape'})"); await settle();
  assert.equal(h.el('evmSettingsWindow').hidden, true, 'Escape closes the dialog, not the window under it');
  assert.equal(h.pins().length, 1);
  assert.equal(h.document.activeElement, h.button(pinCard(), 'Настройки'), 'the keyboard is back in the pinned window');
  h.button(pinCard(), 'Проверить чат').onclick(); await settle();
  assert.equal(h.el('evmCheckOutput').textContent, answer);
  h.el('evmCheckClose').onclick(); await settle();
  h.run("openWindow('settings','beta')"); await settle();  // a dialog opened by no command of a card
  h.el('evmSetClose').onclick(); await settle();
  assert.equal(h.document.activeElement, h.opener(h.cards()[1]), 'then the keyboard lands on the compact card of that model');
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
    await h.click(h.cards()[0]);
    h.button(h.inline(h.cards()[0]), 'Проверить чат').onclick(); await settle();
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

test('E17 without card data the compact cards show names only and nothing can be reordered, dragged or starred', async () => {
  for (const answer of [{httpError: true, status: 403, data: {error: {code: 'model_cards_forbidden', message: 'x'}}}, {cards: 'nope'},
    cards([mcard('alpha', 'Alpha', {api: {color: 'blue', reason: 'X'}})])]) {
    const h = harness(); await settle();
    await h.openEvm([conn('alpha', 'Alpha'), conn('beta', 'Beta')], answer);
    h.layout();
    const card = h.cards()[0];
    assert.equal(h.dot(card), null);
    assert.equal(h.star(card).disabled, true);
    h.press(card, 400, 170); h.move(400, 230);
    assert.equal(h.run('evm.drag'), null, 'no drag without the saved board');
    await h.release(400, 230, card);
    const full = h.inline(card);
    assert.ok(full, 'the click still opens the card in place');
    assert.match(full.textContent, /Подробности карточки недоступны/);
    assert.equal(h.dot(full), null); assert.deepEqual(h.roles(full), []);
    assert.equal(h.button(full, 'Выше'), null);
    assert.equal(h.calls.filter(c => c.method === 'POST').length, 0);
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
  await h.click(h.cards()[0]);
  h.button(h.inline(h.cards()[0]), 'Настройки').onclick(); await settle();
  h.el('evmSetSave').onclick(); await settle();
  assert.equal(posted.base_revision, null);
});

test('E21 plain hover shows nothing; Ctrl + hover shows the preview, switches without a blink, closes on Ctrl release; a press inside pins it', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')]);
  h.layoutRoute();
  const [a, b, c] = h.cards(), box = h.el('evmPeek');
  a.onmouseenter(ev({ctrlKey: false})); await wait(250);
  assert.equal(box.hidden, true, 'a plain hover never opens a panel over the list');
  assert.equal(h.inline(a), null, 'nor the card in place');
  h.run('evmKeyDown')({key: 'Control'});  // Ctrl pressed while the pointer rests on a card
  assert.equal(box.hidden, false);
  assert.equal(h.peek().getAttribute('data-connection'), 'api:prov:a');
  assert.equal(box.className, 'evm-peek open');
  assert.equal(h.bar().textContent, 'Быстрый просмотр · APIНажмите на окно — закрепить×');
  assert.equal(h.opener(a).getAttribute('aria-expanded'), 'false', 'the preview is not the card in place');
  assert.equal(h.quickBtn(a).getAttribute('aria-expanded'), 'false', 'nor a pinned window');
  let hides = 0, shown = box.hidden;
  Object.defineProperty(box, 'hidden', {get: () => shown, set: v => {if (v) hides++; shown = v;}, configurable: true});
  a.onmouseleave(); b.onmouseenter(ev({ctrlKey: true}));
  assert.equal(h.peek().getAttribute('data-connection'), 'api:prov:b', 'moving to the next card switches at once');
  assert.equal(hides, 0, 'the panel is never hidden between two cards');
  b.onmouseleave(); box.onmouseenter(); await wait(250);
  assert.equal(box.hidden, false, 'the way from the card into the panel keeps it open');
  box.onmouseleave(); await wait(250);
  assert.equal(box.hidden, true, 'leaving both closes it');
  b.onmouseenter(ev({ctrlKey: true}));
  h.run('evmKeyUp')({key: 'Control'});
  assert.equal(box.hidden, true, 'releasing Ctrl closes it');
  b.onmouseenter(ev({ctrlKey: true}));
  h.run('evmBlur()');
  assert.equal(box.hidden, true, 'leaving the browser window closes it too');
  b.onmouseenter(ev({ctrlKey: true}));
  box.onpointerdown(ev({button: 0, pointerId: 4}));
  h.run('evmKeyUp')({key: 'Control'});
  assert.equal(box.hidden, false, 'while a press inside lasts, releasing Ctrl keeps it');
  h.run('previewRelease')(ev({pointerId: 4})); await wait(5);
  assert.equal(box.hidden, true, 'after the press the preview is gone ...');
  assert.deepEqual(h.pins().map(p => p.getAttribute('data-connection')), ['api:prov:b'], '... and stands as a pinned window');
  assert.deepEqual(h.posts('/ultra/model-cards/layout'), [{connection_id: 'api:prov:b', window: {x: 0, y: 0}}], 'saved where it stood');
  assert.equal(h.quickBtn(b).getAttribute('aria-expanded'), 'true');
  c.onmouseenter(ev({ctrlKey: true}));
  assert.equal(h.peek().getAttribute('data-connection'), 'api:prov:c', 'Ctrl + hover still previews other models over the window');
  h.run('evmKeyUp')({key: 'Control'});
  assert.equal(box.hidden, true); assert.equal(h.pins().length, 1, 'releasing Ctrl closes only the preview');
  h.run("evm.view='chat'"); h.run('closePeek()'); a.onmouseenter(ev({ctrlKey: true}));
  assert.equal(box.hidden, true, 'nothing opens while EVM is not the open section');
  assert.match(source, /@media\(prefers-reduced-motion:reduce\)\{\.evm-peek,\.ccard\{transition:none\}\.evm-ghost\{transform:none\}\.evm-pin\.flash\{animation:none\}\}/);
  assert.match(source, /\.evm-peek\{position:fixed;[^}]*max-height:calc\(100dvh - 24px\);overflow:auto/);
});

test('E22 a click opens the full card in place under its row; several stay open; a second click closes; Enter / Space the same', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')]);
  let [a, b] = h.cards();
  await h.click(a);
  assert.equal(h.el('evmPeek').hidden, true, 'a plain click never opens the floating panel');
  assert.equal(h.opener(a).getAttribute('aria-expanded'), 'true');
  assert.match(a.className, /\bexpanded\b/);
  assert.deepEqual([a.children[1].hidden, h.inline(a).getAttribute('data-connection')], [false, 'api:prov:a']);
  for (const label of ['Изменить описание', 'Настройки', 'Проверить чат', 'Выше', 'Ниже']) assert.ok(h.button(h.inline(a), label), label);
  assert.equal(h.roles(h.inline(a)).length, 4);
  assert.ok(h.dot(h.inline(a)), 'the API status is part of the full card in place');
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:a', 'api:prov:b', 'api:prov:c'], 'the card grows in its own place; the list keeps its order');
  assert.equal(h.head(a).children.includes(a.children[1]), false, 'the open part is outside the compact row (no drag, no toggle from it)');
  await h.click(b);
  assert.ok(h.inline(a) && h.inline(b), 'opening one card keeps the other open');
  await h.click(a);
  assert.equal(h.inline(a), null); assert.equal(a.children[1].hidden, true);
  assert.equal(h.opener(a).getAttribute('aria-expanded'), 'false'); assert.doesNotMatch(a.className, /expanded/);
  assert.ok(h.inline(b), 'closing one keeps the other');
  h.opener(a).focus(); h.head(a).onclick(ev({detail: 0, target: h.opener(a)})); await settle();  // Enter / Space on «open»
  assert.ok(h.inline(a)); assert.equal(h.document.activeElement, h.opener(a), 'the keyboard stays on «open»');
  h.el('evmRefresh').onclick(); await settle();
  [a, b] = h.cards();
  assert.ok(h.inline(a) && h.inline(b) && !h.inline(h.cards()[2]), 'open cards stay open after the board is read again');
  assert.equal(h.document.activeElement, h.opener(a), 'and the keyboard is still on the same «open»');
  h.routes.set('/ultra/connections', () => catalog([conn('b', 'B'), conn('c', 'C')]));
  h.routes.set('/ultra/model-cards', () => cards([mcard('b', 'B'), mcard('c', 'C')]));
  h.el('evmRefresh').onclick(); await settle();
  assert.deepEqual([...h.run('evm.expanded')], ['api|api:prov:b'], 'a card that left the list is forgotten');
  h.viewRoute();
  const star = h.star(h.cards()[1]), click = ev({target: star});
  star.onclick(click); await settle();
  assert.equal(click.stopped, true);
  assert.equal(h.inline(h.cards()[1]), null, 'the star never opens the card');
  const quick = ev(); h.quickBtn(h.cards()[1]).onclick(quick); await settle();
  assert.equal(quick.stopped, true); assert.equal(h.inline(h.cards()[1]), null, '«⧉» never opens the card in place');
  assert.match(source, /\.cexp\{[^}]*container-type:inline-size/);
  assert.match(source, /@container \(max-width:430px\)\{\.cexp \.roles\{gap:6px 10px\}/);
  assert.match(source, /\.roles\{position:relative;display:grid;grid-template-columns:repeat\(auto-fill,minmax\(118px,1fr\)\)/, 'role columns never narrower than a role name');
});

test('E23 «Выше» / «Ниже» and Alt+arrows save the order of one column; the keyboard keeps its place; the ends are disabled', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')]);
  h.viewRoute();
  await h.click(h.cards()[0]);
  assert.equal(h.button(h.inline(h.cards()[0]), 'Выше').disabled, true);
  let down = h.button(h.inline(h.cards()[0]), 'Ниже'); down.focus(); down.onclick(); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/view'), [{base_revision: 7, section: 'api', order: ['api:prov:b', 'api:prov:a', 'api:prov:c']}]);
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:b', 'api:prov:a', 'api:prov:c']);
  assert.ok(h.inline(h.cards()[1]), 'the moved card stays open in its new place');
  assert.equal(h.document.activeElement, h.button(h.inline(h.cards()[1]), 'Ниже'), 'the keyboard keeps its place');
  down = h.button(h.inline(h.cards()[1]), 'Ниже'); down.onclick(); await settle();
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:b', 'api:prov:c', 'api:prov:a']);
  assert.equal(h.document.activeElement, h.button(h.inline(h.cards()[2]), 'Выше'), 'at the end the other command takes the keyboard');
  const c = h.cards()[1]; h.opener(c).focus();
  const up = ev({key: 'ArrowUp', altKey: true}); h.opener(c).onkeydown(up); await settle();
  assert.equal(up.prevented, true);
  assert.deepEqual(h.posts('/ultra/model-cards/view')[2], {base_revision: 9, section: 'api', order: ['api:prov:c', 'api:prov:b', 'api:prov:a']});
  assert.equal(h.document.activeElement, h.opener(h.cards()[0]), 'Alt+↑ keeps the keyboard on the moved card');
  h.opener(h.cards()[0]).onkeydown(ev({key: 'ArrowUp', altKey: true})); await settle();
  h.opener(h.cards()[1]).onkeydown(ev({key: 'ArrowUp'})); await settle();
  assert.equal(h.posts('/ultra/model-cards/view').length, 3, 'the first card cannot go higher; an arrow alone moves nothing');
  await h.quick(h.cards()[1]);  // the same commands in a pinned window
  const pinB = h.pin('b'), pUp = h.button(h.pinCard(pinB), 'Выше'); pUp.focus(); pUp.onclick(); await settle();
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:b', 'api:prov:c', 'api:prov:a']);
  assert.equal(h.pin('b'), pinB, 'the same window stays, on the same model');
  assert.equal(pinB.hidden, false);
  assert.equal(h.document.activeElement, h.button(h.pinCard(pinB), 'Ниже'), 'at the top the other command in the window takes the keyboard');
  assert.ok(h.posts('/ultra/model-cards/view').every(b => !('description' in b) && !('connection_id' in b)), 'ordering saves nothing else');
  assert.deepEqual(h.posts('/ultra/model-cards/layout').map(b => Object.keys(b)), [['connection_id', 'window']], 'the window: its reference and place only');
});

test('E24 a press becomes a drag only beyond the threshold; the release never opens the card; first, middle and last cards move', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')]);
  h.viewRoute(); h.layout();
  let [a] = h.cards();
  h.press(a, 400, 170); h.move(403, 172); h.move(404, 174);  // a tremor of 5 px stays a click
  assert.equal(h.run('evm.drag'), null);
  assert.equal(h.el('evmGhost').hidden, true);
  await h.release(404, 174, a);
  assert.ok(h.inline(a), 'a click with a small tremor opens the card in place');
  assert.equal(h.posts().length, 0);
  await h.click(a); h.layout();
  h.press(a, 400, 170, {button: 2}); h.move(400, 260);
  assert.equal(h.run('evm.drag'), null, 'only the main button drags');
  await h.release(400, 260);
  h.press(a, 400, 170);
  const start = h.move(400, 176);  // 6 px: now it is a drag
  assert.equal(start.prevented, true);
  assert.equal(h.run("evm.drag.id+'|'+evm.drag.section"), 'api:prov:a|api');
  assert.match(a.className, /dragging/); assert.match(h.el('evmView').className, /\bdragging\b/);
  assert.equal(h.el('evmGhost').hidden, false); assert.match(h.el('evmGhost').textContent, /^AПереставить сюда$/);
  h.move(400, 230);  // over the lower half of b: between b and c
  assert.equal(h.run('evm.drag.index'), 1);
  assert.deepEqual([h.el('evmDropLine').hidden, h.el('evmDropLine').style.top, h.el('evmDropLine').style.left, h.el('evmDropLine').style.width], [false, '241px', '334px', '252px']);
  assert.match(h.el('evmApiCol').className, /drop-target/);
  h.move(400, 280);  // below the middle of the last card: the end of the list
  assert.equal(h.el('evmDropLine').style.top, '288px');
  await h.release(400, 280, a);
  assert.deepEqual(h.posts('/ultra/model-cards/view'), [{base_revision: 7, section: 'api', order: ['api:prov:b', 'api:prov:c', 'api:prov:a']}], 'the first card went to the end');
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:b', 'api:prov:c', 'api:prov:a']);
  assert.equal(h.inline(h.cards()[2]), null, 'the release after a drag did not open the card');
  assert.ok(h.cards().every(x => !/dragging/.test(x.className)) && !/dragging|drop-none/.test(h.el('evmView').className), 'marks are cleared');
  assert.deepEqual([h.el('evmGhost').hidden, h.el('evmDropLine').hidden], [true, true]);
  assert.doesNotMatch(h.el('evmApiCol').className, /drop-target/);
  h.layout();
  await h.drag(h.cards()[1], [400, 218], [400, 160], [[400, 226]]);  // the middle card (c) to the top
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:c', 'api:prov:b', 'api:prov:a'], 'the middle card went to the top');
  await h.drag(h.cards()[2], [400, 266], [400, 205], [[400, 258]]);  // the last card (a) between c and b
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:c', 'api:prov:a', 'api:prov:b'], 'the last card went to the middle');
  assert.equal(h.posts('/ultra/model-cards/view').length, 3);
  await h.drag(h.cards()[1], [400, 218], [400, 215], [[400, 240], [400, 228]]);  // moved and brought back to its own place
  assert.equal(h.posts('/ultra/model-cards/view').length, 3, 'a drop on its own place saves nothing');
  assert.ok(h.cards().every(x => !h.inline(x)), 'and opens nothing');
  await h.click(h.cards()[0]); h.layout();
  await h.drag(h.cards()[0], [400, 170], [400, 280], [[400, 200]]);  // an open card drags as well and stays open
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:a', 'api:prov:b', 'api:prov:c']);
  assert.ok(h.inline(h.cards()[2]), 'a card that was open is still open in its new place');
  h.run('pressEnd({pointerId: 1})'); h.run('pressMove({pointerId: 1, clientX: 900, clientY: 900, buttons: 1})');
  assert.equal(h.run('evm.drag'), null, 'moves without a press do nothing');
});

test('E25 buttons never start a drag; Escape, a release outside, another column, a lost pointer cancel without saving', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')], undefined, [], [other('local', 'a', 'Local A')]);
  h.viewRoute(); h.layout();
  const a = h.cards()[0];
  for (const button of [h.star(a), h.quickBtn(a)]) {
    const down = ev({button: 0, pointerId: 1, clientX: 550, clientY: 170});
    button.onpointerdown(down);
    assert.equal(down.stopped, true, 'the press does not reach the row: no drag from the star or «⧉»');
    h.head(a).onclick(ev({detail: 1, target: h.head(a)})); await settle();  // released elsewhere on the row: the browser clicks the row
    assert.equal(h.inline(a), null, 'a press that began on the star or «⧉» is never a click of the card');
  }
  h.press(a, 400, 170); h.move(400, 200); h.move(400, 230);
  assert.ok(h.run('evm.drag'));
  h.run("escapeKey({key:'Escape'})");
  assert.equal(h.run('evm.drag'), null, 'Escape cancels');
  assert.deepEqual([h.el('evmGhost').hidden, h.el('evmDropLine').hidden], [true, true]);
  h.move(400, 270); h.move(400, 290);
  assert.equal(h.run('evm.drag'), null, 'the same press does not start again');
  await h.release(400, 290, a);
  assert.equal(h.inline(h.cards()[0]), null, 'the release after a cancelled drag opens nothing');
  h.layout();
  h.press(h.cards()[0], 400, 170); h.move(400, 190); h.move(1000, 230);  // over «Локальные LLM»
  assert.equal(h.run('evm.drag.target'), null);
  assert.match(h.el('evmView').className, /drop-none/); assert.match(h.el('evmGhost').textContent, /Сюда нельзя/);
  assert.equal(h.el('evmDropLine').hidden, true);
  assert.equal(h.el('evmLocalCol').className.includes('drop-target'), false, 'an API card is never dropped among local models');
  await h.release(1000, 230, h.cards()[0]);
  h.press(h.cards()[0], 400, 170); h.move(400, 190); h.move(2000, 2000);  // outside the board
  await h.release(2000, 2000);
  h.press(h.cards()[0], 400, 170); h.move(400, 190); h.move(400, 280);
  h.run('pressCancel({pointerId: 1})');  // the browser took the pointer (a touch scroll, a system gesture)
  assert.equal(h.run('evm.drag'), null);
  await h.release(400, 280, h.cards()[0]);
  h.press(h.cards()[0], 400, 170); h.move(400, 190); h.move(400, 280);
  h.run('evmBlur()');  // the window lost the focus
  assert.equal(h.run('evm.drag'), null);
  await h.release(400, 280, h.cards()[0]);
  assert.equal(h.posts().length, 0, 'nothing was saved');
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:a', 'api:prov:b', 'api:prov:c']);
  assert.ok(h.cards().every(x => !h.inline(x)), 'no click slipped through');
  h.head(h.cards()[0]).onclick(ev({detail: 0, target: h.opener(h.cards()[0])})); await settle();
  assert.ok(h.inline(h.cards()[0]), 'Enter right after a cancelled drag still opens the card');
  h.run('evm.suppressUntil=Date.now()+400'); h.press(h.cards()[1], 400, 218); await h.release(400, 218, h.cards()[1]);
  assert.ok(h.inline(h.cards()[1]), 'a new press forgets an old drag: its click is a click');
  const native = ev(); h.head(h.cards()[0]).ondragstart(native);
  assert.equal(native.prevented, true, 'no native drag-and-drop starts from the row');
});

test('E26 favourites by mouse: a reference is added at the place shown, never twice; the source column keeps the model', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')], undefined, [other('mcp', 'm', 'Agent M')], [other('local', 'l', 'Local L')]);
  h.viewRoute(); h.layout();
  const fav = COLUMN_LEFT.Fav + 100;
  await h.drag(h.cards()[1], [400, 218], [fav, 160], [[400, 230], [fav, 200]]);  // B into the empty favourites
  assert.deepEqual(h.posts('/ultra/model-cards/view'), [{base_revision: 7, section: 'favorites', order: ['api:prov:b']}]);
  assert.deepEqual(h.ids('evmFavList'), ['api:prov:b']);
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:a', 'api:prov:b', 'api:prov:c'], 'the model stays in its own column');
  assert.match(h.el('evmNotice').textContent, /Добавлено в избранное: B/);
  assert.equal(h.star(h.cards()[1]).textContent, '★');
  h.press(h.cards()[0], 400, 170); h.move(400, 180); h.move(fav, 155);
  assert.match(h.el('evmGhost').textContent, /★ Добавить в избранное/); assert.match(h.el('evmFavCol').className, /drop-target/);
  assert.equal(h.el('evmDropLine').style.top, '145px', 'the line above the first favourite');
  await h.release(fav, 155, h.cards()[0]);
  assert.deepEqual(h.ids('evmFavList'), ['api:prov:a', 'api:prov:b'], 'A went before B');
  h.layout();
  h.press(h.cards()[1], 400, 218); h.move(400, 230); h.move(fav, 230);
  assert.match(h.el('evmGhost').textContent, /Уже в избранном — новое место/);
  await h.release(fav, 230, h.cards()[1]);  // B again, after A: the same place
  assert.equal(h.posts('/ultra/model-cards/view').length, 2, 'no duplicate and nothing to save');
  assert.match(h.el('evmNotice').textContent, /Уже в избранном: B/);
  await h.drag(h.cards()[1], [400, 218], [fav, 155], [[400, 230]]);  // B again, before A
  assert.deepEqual(h.posts('/ultra/model-cards/view')[2], {base_revision: 9, section: 'favorites', order: ['api:prov:b', 'api:prov:a']});
  assert.match(h.el('evmNotice').textContent, /Уже было в избранном — место изменено: B/);
  await h.drag(h.list('evmMcpList')[0], [700, 170], [fav, 300], [[700, 180]]);  // MCP and local entries as well
  await h.drag(h.list('evmLocalList')[0], [1000, 170], [fav, 160], [[1000, 180]]);
  assert.deepEqual(h.ids('evmFavList'), ['local:prov:l', 'api:prov:b', 'api:prov:a', 'mcp:prov:m']);
  assert.deepEqual([h.ids('evmMcpList'), h.ids('evmLocalList')], [['mcp:prov:m'], ['local:prov:l']], 'their columns keep them');
  await h.drag(h.list('evmFavList')[3], [fav, 314], [fav, 160], [[fav, 300]]);  // a favourite moves inside its column
  assert.deepEqual(h.ids('evmFavList'), ['mcp:prov:m', 'local:prov:l', 'api:prov:b', 'api:prov:a']);
  h.press(h.list('evmFavList')[0], fav, 170); h.move(fav, 190); h.move(400, 230);  // a favourite never goes into a source column
  assert.equal(h.run('evm.drag.target'), null);
  await h.release(400, 230);
  assert.equal(h.posts('/ultra/model-cards/view').length, 6);
  assert.ok(h.posts('/ultra/model-cards/view').every(p => p.section === 'favorites'), 'no source column was rewritten');
  assert.ok(h.posts('/ultra/model-cards/view').every(p => new Set(p.order).size === p.order.length), 'never a duplicate');
  h.star(h.list('evmFavList')[2]).onclick(ev()); await settle();
  assert.deepEqual(h.ids('evmFavList'), ['mcp:prov:m', 'local:prov:l', 'api:prov:a'], 'the star still removes a favourite');
  assert.match(h.el('evmNotice').textContent, /Убрано из избранного: B/);
});

test('E27 favourites by star: a reference, its own order, its source as it is now', async () => {
  const h = harness(); await settle();
  let status = api('red', 'NEVER_CONFIRMED'), favs = [], revision = 7;
  h.routes.set('/ultra/connections', () => catalog([conn('a', 'A'), conn('b', 'B')]));
  h.routes.set('/ultra/model-cards', () => cards([mcard('a', 'A'), mcard('b', 'B', {api: status})],
    {view: {state: 'SAVED', revision, hidden: 0, sections: {favorites: favs, api: ['api:prov:a', 'api:prov:b'], mcp: [], local: []}}}));
  h.routes.set('/ultra/model-cards/view', opts => {const body = JSON.parse(opts.body); favs = body.order; revision++;
    return {view: {state: 'SAVED', revision, hidden: 0, sections: {favorites: favs, api: ['api:prov:a', 'api:prov:b'], mcp: [], local: []}}};});
  h.el('viewEvm').onclick(); await settle();
  h.star(h.cards()[1]).onclick(ev()); await settle();
  const star = h.star(h.cards()[0]); star.focus(); star.onclick(ev()); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/view'), [{base_revision: 7, section: 'favorites', order: ['api:prov:b']},
    {base_revision: 8, section: 'favorites', order: ['api:prov:b', 'api:prov:a']}]);
  assert.equal(h.document.activeElement, h.star(h.cards()[0]), 'the keyboard stays on the star');
  assert.match(h.el('evmNotice').textContent, /Добавлено в избранное: A/);
  assert.deepEqual(h.ids('evmFavList'), ['api:prov:b', 'api:prov:a']);
  assert.equal(h.el('evmFavState').textContent, '2'); assert.equal(h.el('evmFavEmpty').hidden, true);
  assert.equal(h.star(h.cards()[0]).textContent, '★'); assert.equal(h.star(h.cards()[0]).getAttribute('aria-pressed'), 'true');
  assert.equal(h.list('evmFavList')[0].getAttribute('data-section'), 'favorites');
  await h.click(h.list('evmFavList')[1]);
  assert.equal(h.inline(h.cards()[0]), null, 'a favourite opens on its own: the API card stays closed');
  h.button(h.inline(h.list('evmFavList')[1]), 'Выше').onclick(); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/view')[2], {base_revision: 9, section: 'favorites', order: ['api:prov:a', 'api:prov:b']});
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:a', 'api:prov:b'], 'the API column keeps its own order');
  status = api('green', 'CONFIRMED');
  h.el('evmRefresh').onclick(); await settle();
  assert.equal(h.dot(h.list('evmFavList')[1]).getAttribute('data-api'), 'green:CONFIRMED', 'a favourite shows its source as it is now');
  h.star(h.list('evmFavList')[0]).onclick(ev()); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/view')[3].order, ['api:prov:b']);
  assert.match(h.el('evmNotice').textContent, /Убрано из избранного: A/);
});

test('E28 «Изменить описание» opens Настройки → Модель with the cursor in the field; a click on the box does the same', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('alpha', 'Alpha')], cards([mcard('alpha', 'Alpha', {description: 'Было'})]));
  let posted = null;
  h.routes.set('/ultra/model-cards/alpha/settings', opts => {posted = JSON.parse(opts.body); return {card: mcard('alpha', 'Alpha')};});
  await h.click(h.cards()[0]);
  h.button(h.inline(h.cards()[0]), 'Изменить описание').onclick(); await settle();
  assert.equal(h.el('evmSettingsWindow').hidden, false);
  assert.deepEqual([h.el('evmPaneConn').hidden, h.el('evmPaneModel').hidden], [true, false]);
  assert.equal(h.document.activeElement, h.el('evmSetDescription'));
  assert.equal(h.el('evmSetDescription').attrs.maxlength, '500');
  h.el('evmSetDescription').value = 'Новое'; h.el('evmSetDescription').oninput();
  h.el('evmSetSave').onclick(); await settle();
  assert.equal(posted.description, 'Новое'); assert.equal(posted.base_revision, 4);
  h.el('evmSetClose').onclick(); await settle();
  assert.equal(h.document.activeElement, h.button(h.inline(h.cards()[0]), 'Изменить описание'));
  h.el('evmTabConn').onclick();
  await h.quick(h.cards()[0]);
  h.find(h.pinCard(h.pin('alpha')), e => (e.className || '').startsWith('strengths')).onclick(); await settle();
  assert.equal(h.el('evmPaneModel').hidden, false); assert.equal(h.document.activeElement, h.el('evmSetDescription'));
});

test('E29 layout rules: four columns on a wide screen, one on a narrow one, no scroll anchoring jumps, no horizontal scroll', () => {
  assert.match(source, /@media\(min-width:1200px\)\{\.evm-board\{grid-template-columns:minmax\(200px,\.75fr\) minmax\(0,1\.25fr\) minmax\(0,1fr\) minmax\(0,1fr\)\}\}/);
  assert.match(source, /\.evm-columns\{grid-template-columns:1fr\}/);
  assert.match(source, /<div class="evm-columns evm-board">\s*<section class="evm-col" aria-labelledby="evmFavTitle" id="evmFavCol">/);
  for (const name of ['Api', 'Mcp', 'Local']) assert.match(source, new RegExp('<section class="evm-col" aria-labelledby="evm' + name + 'Title" id="evm' + name + 'Col">'));
  assert.match(source, /\.evm-peek\{position:fixed;[^}]*width:min\(560px,calc\(100vw - 24px\)\)/);
  assert.match(source, /\.evm\{[^}]*overflow:auto;[^}]*overflow-anchor:none\}/);
  assert.match(source, /\.evm-board\{overflow-anchor:none;margin-bottom:56px\}/);
  assert.match(source, /\.ccard \.grip\{[^}]*touch-action:none\}/, 'a touch drags from the grip, the rest of the card scrolls the page');
  assert.match(source, /\.evm\.dragging\.drop-none,\.evm\.dragging\.drop-none \*\{cursor:no-drop!important\}/);
});

test('E30 the Ctrl preview stands beside the column of its card: right of the left columns, left of the right ones, a sheet on a narrow screen', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')], undefined, [other('mcp', 'm', 'Agent M')], [other('local', 'l', 'Local L')]);
  h.viewRoute({favorites: ['api:prov:b']});
  h.star(h.cards()[1]).onclick(ev()); await settle();
  const box = h.el('evmPeek');
  Object.defineProperty(box, 'offsetHeight', {get() {return this.hidden ? 0 : 480;}});  // a hidden element has no height
  const place = (card, colId, col, top) => {h.head(card).getBoundingClientRect = () => rect(col.left + 14, top, col.width - 28, 52); h.el(colId).getBoundingClientRect = () => col;};
  const at = () => [box.getAttribute('data-place'), box.style.width, box.style.left, box.style.top];
  Object.assign(h.context.window, {innerWidth: 1400, innerHeight: 950});  // 1400 px: four columns
  const wide = {Fav: rect(28, 120, 243, 700), Api: rect(287, 120, 405, 700), Mcp: rect(708, 120, 324, 700), Local: rect(1048, 120, 324, 700)};
  const fav = h.list('evmFavList')[0], apiCard = h.cards()[0], mcp = h.list('evmMcpList')[0], local = h.list('evmLocalList')[0];
  place(fav, 'evmFavCol', wide.Fav, 200); place(apiCard, 'evmApiCol', wide.Api, 200); place(mcp, 'evmMcpCol', wide.Mcp, 300); place(local, 'evmLocalCol', wide.Local, 400);
  h.ctrlHover(fav); assert.deepEqual(at(), ['right', '560px', '281px', '200px'], 'favourites: to the right of the column');
  h.ctrlHover(apiCard); assert.deepEqual(at(), ['right', '560px', '702px', '200px'], 'API: to the right, over MCP, never over API');
  h.ctrlHover(mcp); assert.deepEqual(at(), ['left', '560px', '138px', '300px'], 'MCP: to the left');
  h.ctrlHover(local); assert.deepEqual(at(), ['left', '560px', '478px', '400px'], 'local: to the left');
  place(local, 'evmLocalCol', wide.Local, 800); h.run('positionPeek()');
  assert.equal(box.style.top, '458px', 'never below the window: 950 − 480 − 12');
  const header = new Element('header'); header.getBoundingClientRect = () => rect(0, 0, 1400, 240);
  h.document.querySelector = sel => sel === 'header.top' ? header : null;
  place(local, 'evmLocalCol', wide.Local, 100); h.run('positionPeek()');
  assert.deepEqual([box.style.top, box.style.maxHeight], ['248px', '690px'], 'never under the sticky page header');
  h.document.querySelector = () => null;
  Object.assign(h.context.window, {innerWidth: 2400, innerHeight: 950});  // a very wide window: room on both sides
  place(mcp, 'evmMcpCol', rect(1000, 120, 300, 700), 300); h.ctrlHover(mcp);
  assert.deepEqual(at(), ['left', '560px', '430px', '300px'], 'with room on both sides MCP still opens to the left');
  place(apiCard, 'evmApiCol', rect(400, 120, 300, 700), 200); h.ctrlHover(apiCard);
  assert.deepEqual(at(), ['right', '560px', '710px', '200px'], 'and API to the right');
  Object.assign(h.context.window, {innerWidth: 1000, innerHeight: 900});  // two columns: less room beside them
  const mid = {Fav: rect(28, 120, 464, 400), Api: rect(508, 120, 464, 400)};
  place(fav, 'evmFavCol', mid.Fav, 200); h.ctrlHover(fav);
  assert.deepEqual(at(), ['right', '486px', '502px', '200px'], 'narrower panel on the side with room');
  place(apiCard, 'evmApiCol', mid.Api, 200); h.ctrlHover(apiCard);
  assert.deepEqual(at(), ['left', '486px', '12px', '200px'], 'no room on the preferred side: the other side');
  Object.assign(h.context.window, {innerWidth: 390, innerHeight: 844});  // a phone: one column, no side room
  const one = rect(12, 120, 366, 1400);
  place(apiCard, 'evmApiCol', one, 200); h.run('positionPeek()');  // the panel of this card is still pinned
  assert.deepEqual([...at(), box.style.maxHeight], ['below', '366px', '12px', '262px', '570px'], 'a sheet below the card, the card stays visible');
  place(apiCard, 'evmApiCol', one, 700); h.run('positionPeek()');
  assert.deepEqual([...at(), box.style.maxHeight], ['above', '366px', '12px', '210px', '678px'], 'near the bottom: a sheet above the card');
});

test('E31 keyboard: «⧉» opens the window with the focus in it, arrows move it by its title, «×» returns the keyboard; Escape never closes it', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')]);
  h.layoutRoute();
  h.quickBtn(h.cards()[0]).focus();
  h.quickBtn(h.cards()[0]).onclick(ev({detail: 0})); await settle();  // Enter / Space on «⧉»
  const pin = h.pin('a');
  assert.equal(h.document.activeElement, pin, 'the keyboard lands in the window');
  assert.deepEqual([pin.getAttribute('role'), pin.getAttribute('aria-modal'), pin.getAttribute('aria-label'), pin.getAttribute('tabindex')],
    ['dialog', 'false', 'Окно модели: A', '-1']);
  const bar = h.pinBar(pin);
  assert.deepEqual([bar.getAttribute('tabindex'), bar.getAttribute('aria-label')], ['0', 'Окно «A»: перетащите за заголовок или двигайте стрелками']);
  assert.equal(h.pinClose(pin).getAttribute('aria-label'), 'Закрыть окно: A');
  const start = [pin.style.left, pin.style.top];
  for (const key of ['ArrowRight', 'ArrowRight', 'ArrowDown']) {const e = ev({key}); bar.onkeydown(e); assert.equal(e.prevented, true);}
  const shift = ev({key: 'ArrowLeft', shiftKey: true}); bar.onkeydown(shift);
  assert.deepEqual([pin.style.left, pin.style.top], [(parseInt(start[0]) + 32 - 64) + 'px', (parseInt(start[1]) + 16) + 'px']);
  assert.equal(h.posts('/ultra/model-cards/layout').length, 1, 'arrows do not save every step');
  await wait(450);
  assert.deepEqual(h.posts('/ultra/model-cards/layout')[1], {connection_id: 'api:prov:a', window: {x: parseInt(start[0]) - 32, y: parseInt(start[1]) + 16}},
    'saved once after the last step');
  bar.onkeydown(ev({key: 'x'}));
  h.run("escapeKey({key:'Escape'})");
  assert.equal(h.pins().length, 1, 'Escape never closes a pinned window');
  h.pinClose(pin).focus(); h.pinClose(pin).onclick(ev({detail: 0})); await settle();
  assert.equal(h.pins().length, 0);
  assert.equal(h.document.activeElement, h.quickBtn(h.cards()[0]), 'the keyboard goes back to «⧉» of the card it came from');
  assert.equal(h.quickBtn(h.cards()[0]).getAttribute('aria-expanded'), 'false');
  assert.deepEqual(h.posts('/ultra/model-cards/layout').slice(-1), [{connection_id: 'api:prov:a', window: null}]);
});

test('E32 a card drag closes the preview and keeps it closed; pinned windows stay where they are, faded and transparent to the pointer', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')]);
  h.viewRoute(); h.layoutRoute(); h.layout();
  const box = h.el('evmPeek');
  let [a, b] = h.cards();
  a.onmouseenter(ev({ctrlKey: true}));
  assert.equal(box.hidden, false);
  h.press(a, 400, 170);
  b.onmouseenter(ev({ctrlKey: true}));
  assert.equal(h.peek().getAttribute('data-connection'), 'api:prov:a', 'while the button is down the preview does not switch');
  h.move(400, 180);
  assert.equal(box.hidden, true, 'the drag closed the preview');
  b.onmouseenter(ev({ctrlKey: true})); h.run('evmKeyDown')({key: 'Control'});
  assert.equal(box.hidden, true, 'and it does not come back during the drag');
  h.quickBtn(b).onclick(ev({detail: 1}));
  assert.equal(h.pins().length, 0, 'nothing is pinned during a drag');
  await h.release(400, 280, a);
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:b', 'api:prov:c', 'api:prov:a']);
  assert.equal(box.hidden, true, 'nothing reopens by itself after the drop');
  h.layout();
  const [first, second] = h.cards(), pinnedId = second.getAttribute('data-connection');
  await h.quick(second);
  const pin = h.pin(pinnedId), at = [pin.style.left, pin.style.top];
  h.press(first, 400, 170); h.move(400, 200);
  assert.match(h.el('evmView').className, /\bdragging\b/);
  assert.equal(h.pins().length, 1); assert.equal(pin.hidden, false, 'the window stays during the drag');
  assert.match(source, /\.evm\.dragging \.evm-pins\{opacity:\.25\}\.evm\.dragging \.evm-pin\{pointer-events:none\}/, 'faded, the pointer goes through');
  await h.release(400, 280, first);
  assert.deepEqual([h.pins().length, pin.style.left, pin.style.top], [1, ...at], 'and is where it was after it');
  assert.equal(h.pin(pinnedId), pin, 'the same window, not a new one');
});

test('E33 a refused order is not kept: the saved state is read again and the reason told (buttons and drag)', async () => {
  for (const [answer, told] of [[{httpError: true, status: 409, data: {error: {code: 'settings_revision_conflict', message: 'changed'}}}, /уже изменились в другом окне/],
    [{httpError: true, status: 500, data: {error: {code: 'internal_error', message: 'disk full'}}}, /Порядок не сохранён\. /]]) {
    const h = harness(); await settle();
    await h.openEvm([conn('a', 'A'), conn('b', 'B')]);
    h.routes.set('/ultra/model-cards/view', () => answer);
    await h.click(h.cards()[0]);
    h.button(h.inline(h.cards()[0]), 'Ниже').onclick(); await settle();
    assert.deepEqual(h.ids('evmApiList'), ['api:prov:a', 'api:prov:b']);
    assert.match(h.el('evmError').textContent, told);
    assert.equal(h.calls.filter(c => c.url === '/ultra/model-cards').length, 2, 'the board is read again');
    h.layout();
    await h.drag(h.cards()[0], [400, 170], [400, 230], [[400, 200]]);
    assert.deepEqual(h.ids('evmApiList'), ['api:prov:a', 'api:prov:b'], 'a refused drop goes back');
    await h.drag(h.cards()[1], [400, 218], [COLUMN_LEFT.Fav + 100, 160], [[400, 230]]);
    assert.deepEqual(h.ids('evmFavList'), [], 'a refused favourite is not kept');
    assert.match(h.el('evmError').textContent, told);
    assert.equal(h.calls.filter(c => c.url === '/ultra/model-cards').length, 4);
    assert.ok(h.inline(h.cards()[0]), 'the open card is still open after the reload');
  }
});

test('E34 one constructor for every kind: MCP and local entries, same tail of different kinds kept apart', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('x', 'API X')], undefined, [other('mcp', 'x', 'Agent X')], [other('local', 'x', 'Local X'), other('local', 'y', 'Local Y')]);
  assert.deepEqual(h.ids('evmMcpList'), ['mcp:prov:x']);
  assert.deepEqual(h.ids('evmLocalList'), ['local:prov:x', 'local:prov:y']);
  assert.equal(h.el('evmMcpEmpty').hidden, true); assert.equal(h.el('evmLocalEmpty').hidden, true);
  const mcp = h.list('evmMcpList')[0];
  assert.equal(mcp.className, h.cards()[0].className, 'the same compact component');
  assert.match(mcp.textContent, /MCP \/ агент · prov/); assert.equal(h.dot(mcp), null, 'no API indicator for an entry without one');
  for (const mode of ['inline', 'preview', 'pin']) {
    const full = await h.full(h.list('evmMcpList')[0], mode);
    assert.match(full.textContent, /Подробности появятся, когда источник этого подключения будет подключён/);
    assert.deepEqual(h.roles(full), []);
    assert.ok(h.button(full, 'Ниже'), 'the order of the column can be changed');
  }
  assert.equal(h.button(h.list('evmLocalList')[0], 'Настройки'), null);
});

test('E35 near the edge of the board the list scrolls by itself during a drag, and the place is found again', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')]);
  h.viewRoute(); h.layout();
  const frames = [];
  h.context.requestAnimationFrame = fn => {frames.push(fn); return frames.length;};
  h.context.cancelAnimationFrame = () => {};
  const view = h.el('evmView');
  Object.assign(view, {scrollHeight: 2000, clientHeight: 800, scrollTop: 100});
  view.getBoundingClientRect = () => rect(0, 73, 1400, 800);
  h.press(h.cards()[0], 400, 170); h.move(400, 200);
  assert.equal(frames.length, 1);
  frames.shift()();
  assert.equal(view.scrollTop, 100, 'far from the edges nothing scrolls');
  h.move(400, 860);  // 13 px above the bottom edge of the board
  frames.shift()();
  assert.equal(view.scrollTop, 109, 'it scrolls down, faster closer to the edge');
  assert.equal(frames.length, 1, 'and keeps going while the pointer stays there');
  h.move(400, 1000); frames.shift()();
  assert.equal(view.scrollTop, 133, 'never faster than 24 px a frame');
  h.move(400, 80); frames.shift()();
  assert.equal(view.scrollTop, 122, 'up near the top edge');
  h.run("escapeKey({key:'Escape'})");
  assert.equal(h.run('evm.scrollFrame'), 0);
  assert.equal(h.posts().length, 0);
});

test('E36 messages are toasts outside the flow: a drop that tells something never moves the board; success goes away by itself', async () => {
  assert.match(source, /<div class="evm-toasts"><div id="evmError" class="notice error" role="alert" hidden><\/div>\s*<div id="evmNotice" class="notice success" role="status" hidden><\/div><\/div>/);
  assert.match(source, /\.evm-toasts\{position:fixed;[^}]*bottom:16px;[^}]*pointer-events:none\}/);
  assert.match(source, /\.evm\.dragging \.evm-toasts\{visibility:hidden\}/);
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')]);
  h.viewRoute(); h.layout();
  const timers = [];
  h.context.setTimeout = (fn, ms) => {timers.push([fn, ms]); return timers.length;};
  await h.drag(h.cards()[0], [400, 170], [COLUMN_LEFT.Fav + 100, 160], [[400, 190]]);
  assert.equal(h.el('evmNotice').hidden, false); assert.match(h.el('evmNotice').textContent, /Добавлено в избранное: A/);
  const hide = timers.find(([, ms]) => ms === 6000);
  assert.ok(hide, 'the success toast is timed');
  hide[0]();
  assert.equal(h.el('evmNotice').hidden, true, 'and goes away by itself');
  h.routes.set('/ultra/model-cards/view', () => ({httpError: true, status: 500, data: {error: {code: 'internal_error', message: 'disk full'}}}));
  await h.drag(h.cards()[1], [400, 218], [COLUMN_LEFT.Fav + 100, 160], [[400, 230]]);
  assert.equal(h.el('evmError').hidden, false);
  assert.equal(timers.filter(([, ms]) => ms === 6000).length, 1, 'an error is not timed: it stays until the next action');
});

test('E37 the drag label follows the pointer at its lower right and flips near the window edges, never hiding the place pointed at', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')]);
  h.viewRoute(); h.layout();
  const g = h.el('evmGhost');
  Object.defineProperty(g, 'offsetWidth', {get: () => 260}); Object.defineProperty(g, 'offsetHeight', {get: () => 50});
  Object.assign(h.context.window, {innerWidth: 1400, innerHeight: 900});
  h.press(h.cards()[0], 400, 170); h.move(400, 200);
  assert.deepEqual([g.style.left, g.style.top, g.style.width], ['414px', '216px', '252px'], 'beside the pointer, not under it');
  h.move(1300, 880);
  assert.deepEqual([g.style.left, g.style.top], ['1026px', '814px'], 'near the right and bottom edges it flips to the other side');
  h.move(2, 2);
  assert.deepEqual([g.style.left, g.style.top], ['16px', '18px']);
  assert.match(source, /\.evm-drop-line\{position:fixed;z-index:31;/, 'the insertion line is drawn over the label');
  assert.match(source, /\.evm-ghost\{position:fixed;z-index:30;/);
  h.run("escapeKey({key:'Escape'})");
});

test('E38 three independent windows: one per model (stable connection_id), the same one from «Избранное», a press raises it', async () => {
  const h = harness(); await settle();
  const list = [conn('a', 'A'), conn('b', 'B'), conn('c', 'C'), conn('t1', 'Twin'), conn('t2', 'Twin')];
  await h.openEvm(list, cards(list.map(c => mcard(c.model_id, c.display_name)),
    {view: {state: 'SAVED', revision: 7, hidden: 0, sections: {favorites: ['api:prov:a'], api: list.map(c => c.connection_id), mcp: [], local: []}}}));
  h.layoutRoute();
  const [a, b, c, t1, t2] = h.cards();
  await h.quick(a);
  await h.quick(b);
  await h.click(c, {ctrlKey: true});  // Ctrl + click pins too
  assert.deepEqual(h.pins().map(p => p.getAttribute('data-connection')), ['api:prov:a', 'api:prov:b', 'api:prov:c']);
  assert.deepEqual(h.pins().map(p => [p.style.left, p.style.top]), [['24px', '28px'], ['52px', '56px'], ['80px', '84px']],
    'independent places: a new window never covers another exactly');
  assert.deepEqual(h.pins().map(p => [p.style.zIndex, /\bactive\b/.test(p.className)]), [['1', false], ['2', false], ['3', true]]);
  assert.equal(h.inline(c), null, 'Ctrl + click does not open the card in place');
  assert.deepEqual(h.posts('/ultra/model-cards/layout'), [{connection_id: 'api:prov:a', window: {x: 24, y: 28}},
    {connection_id: 'api:prov:b', window: {x: 52, y: 56}}, {connection_id: 'api:prov:c', window: {x: 80, y: 84}}]);
  const fav = h.list('evmFavList')[0];
  assert.equal(h.quickBtn(fav).getAttribute('aria-expanded'), 'true', '«⧉» in «Избранное» knows the window too');
  assert.equal(h.quickBtn(fav).getAttribute('aria-label'), 'Показать окно модели: A');
  await h.quick(fav);
  await h.quick(a);
  await h.click(a, {ctrlKey: true});
  assert.equal(h.pins().length, 3, 'from «Избранное» and from its column: still one window A');
  assert.deepEqual(h.pins().map(p => p.style.zIndex), ['3', '1', '2'], 'A was brought to the top');
  assert.match(h.pin('a').className, /\bflash\b/, 'and shown with a short highlight');
  assert.equal(h.posts('/ultra/model-cards/layout').length, 3, 'bringing forward saves nothing');
  h.pin('b').onpointerdown(ev());
  assert.deepEqual(h.pins().map(p => p.style.zIndex), ['2', '3', '1'], 'a press anywhere on a window raises it');
  for (const p of h.pins()) {
    const id = p.getAttribute('data-connection');
    assert.equal(h.button(h.pinCard(p), 'Настройки').getAttribute('data-fk'), 'pin:' + id + ':settings', 'every window has its own keys');
    assert.equal(h.pinCard(p).getAttribute('data-connection'), id, 'the same full card component');
  }
  await h.quick(t1); await h.quick(t2);
  assert.deepEqual(h.pins().slice(3).map(p => p.getAttribute('data-connection')), ['api:prov:t1', 'api:prov:t2'], 'the same name, two models, two windows');
  assert.equal(new Set(h.pins().map(p => p.getAttribute('data-connection'))).size, h.pins().length, 'never a duplicate');
  assert.match(source, /<div id="evmPins" class="evm-pins" role="group" aria-label="Закреплённые окна моделей"><\/div>\s*<div id="evmPeek"/);
});

test('E39 a window moves by its title only, stays reachable at every edge, is saved once on release; Escape puts it back', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C')]);
  Object.assign(h.context.window, {innerWidth: 1400, innerHeight: 900});
  h.viewRoute(); h.layoutRoute(); h.layout();
  await h.quick(h.cards()[0]);
  const pin = h.pin('a'), bar = h.pinBar(pin), saves = () => h.posts('/ultra/model-cards/layout');
  assert.deepEqual([pin.style.left, pin.style.top, pin.style.width], ['610px', '150px', '460px'], 'first beside the API column');
  const down = ev({button: 0, pointerId: 7, clientX: 700, clientY: 160}); bar.onpointerdown(down);
  assert.equal(down.prevented, true, 'no text selection while it moves');
  h.run('pinMove')(ev({pointerId: 7, clientX: 702, clientY: 161}));
  assert.equal(pin.style.left, '610px', 'a 2 px tremor does not move it');
  h.run('pinMove')(ev({pointerId: 9, clientX: 100, clientY: 100}));
  assert.equal(pin.style.left, '610px', 'another pointer does not move it');
  h.run('pinMove')(ev({pointerId: 7, clientX: 500, clientY: 400}));
  assert.deepEqual([pin.style.left, pin.style.top], ['410px', '390px']); assert.match(pin.className, /\bmoving\b/);
  h.run('pinMove')(ev({pointerId: 7, clientX: 450, clientY: 420}));
  assert.equal(saves().length, 1, 'nothing is saved while it moves');
  h.run('pinEnd')(ev({pointerId: 7})); await settle();
  assert.deepEqual(saves().slice(-1), [{connection_id: 'api:prov:a', window: {x: 360, y: 410}}]);
  assert.doesNotMatch(pin.className, /\bmoving\b/);
  bar.onpointerdown(ev({button: 0, pointerId: 7, clientX: 400, clientY: 420}));
  h.run('pinMove')(ev({pointerId: 7, clientX: -1000, clientY: -1000}));
  assert.deepEqual([pin.style.left, pin.style.top], ['0px', '12px'], 'the title never leaves the window or goes under the header');
  h.run('pinMove')(ev({pointerId: 7, clientX: 5000, clientY: 5000}));
  assert.deepEqual([pin.style.left, pin.style.top], ['940px', '852px'], 'and «×» stays on screen at the right and the bottom');
  h.run('pinEnd')(ev({pointerId: 7})); await settle();
  assert.deepEqual(saves().slice(-1)[0].window, {x: 940, y: 852});
  bar.onpointerdown(ev({button: 0, pointerId: 7, clientX: 1000, clientY: 860}));
  h.run('pinMove')(ev({pointerId: 7, clientX: 600, clientY: 500}));
  h.run("escapeKey({key:'Escape'})");
  assert.deepEqual([pin.style.left, pin.style.top], ['940px', '852px'], 'Escape puts it back where the move began');
  h.run('pinMove')(ev({pointerId: 7, clientX: 300, clientY: 300}));
  assert.deepEqual([pin.style.left, h.pins().length, saves().length], ['940px', 1, 3], 'the move is over, the window stays open, nothing saved');
  bar.onpointerdown(ev({button: 2, pointerId: 7, clientX: 1000, clientY: 860}));
  assert.equal(h.run('evm.winDrag'), null, 'only the main button moves it');
  const closeDown = ev({button: 0, pointerId: 7}); h.pinClose(pin).onpointerdown(closeDown);
  assert.equal(closeDown.stopped, true, '«×» never starts a move');
  pin.onpointerdown(ev({button: 0, pointerId: 7}));  // a press inside the card body only raises the window
  assert.equal(h.run('evm.winDrag'), null);
  h.layout();
  h.press(h.cards()[1], 400, 218); h.move(400, 230); h.move(400, 160);
  assert.equal(h.run('evm.winDrag'), null, 'a card drag is a different gesture');
  await h.release(400, 160, h.cards()[1]);
  assert.deepEqual(h.ids('evmApiList'), ['api:prov:b', 'api:prov:a', 'api:prov:c']);
  assert.deepEqual([pin.style.left, pin.style.top], ['940px', '852px'], 'and never moves a window');
  assert.match(source, /\.pin-bar\{[^}]*cursor:move;[^}]*touch-action:none;/);
});

test('E40 a pinned window closes only with its own «×»: not by Ctrl, Escape, blur, another model, a card drag or another view', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B'), conn('c', 'C'), conn('d', 'D')]);
  h.viewRoute(); h.layoutRoute(); h.layout();
  const [a, b, c, d] = h.cards();
  await h.quick(a); await h.quick(b); await h.quick(c);
  const ids = () => h.pins().map(p => p.getAttribute('data-connection')).sort();
  const all = ['api:prov:a', 'api:prov:b', 'api:prov:c'];
  d.onmouseenter(ev({ctrlKey: true})); h.run('evmKeyUp')({key: 'Control'});
  h.run("escapeKey({key:'Escape'})"); h.run('evmBlur()');
  await h.click(d);  // another model opens in place
  h.el('viewChat').onclick(); await settle();
  assert.equal(h.el('evmView').hidden, true);
  assert.deepEqual(ids(), all, 'another view hides them with EVM, it does not close them');
  h.el('viewEvm').onclick(); await settle();
  assert.deepEqual(ids(), all);
  assert.equal(h.pins().length, 3, 'no duplicate after coming back');
  h.layout();
  await h.drag(h.cards()[3], [400, 314], [400, 160], [[400, 300]]);
  assert.deepEqual(ids(), all, 'a card drag does not close them');
  assert.equal(h.posts('/ultra/model-cards/layout').filter(p => p.window === null).length, 0);
  h.pinClose(h.pin('b')).onclick(ev({detail: 1})); await settle();
  assert.deepEqual(ids(), ['api:prov:a', 'api:prov:c'], '«×» closes exactly that window');
  assert.deepEqual(h.posts('/ultra/model-cards/layout').slice(-1), [{connection_id: 'api:prov:b', window: null}]);
  assert.equal(h.quickBtn(h.cards().find(x => x.getAttribute('data-connection') === 'api:prov:b')).getAttribute('aria-expanded'), 'false');
  await h.quick(h.cards().find(x => x.getAttribute('data-connection') === 'api:prov:b'));
  assert.deepEqual(ids(), all, 'pinned again: exactly one new window B');
});

test('E41 the preview is above every pinned window; a pinned model gets no second copy; a press inside the preview (a button too) pins it', async () => {
  assert.match(source, /\.evm-peek\{position:fixed;z-index:18;/);
  assert.match(source, /\.evm-pins\{position:fixed;inset:0;z-index:16;pointer-events:none\}/);
  assert.match(source, /\.evm-backdrop\{position:fixed;inset:0;z-index:20;/, 'dialogs stay above both');
  const h = harness(); await settle();
  await h.openEvm(['a', 'b', 'c', 'd', 'e'].map(x => conn(x, x.toUpperCase())));
  h.layoutRoute();
  const [a, b, c, d, e] = h.cards(), box = h.el('evmPeek');
  await h.quick(a); await h.quick(b); await h.quick(c);
  d.onmouseenter(ev({ctrlKey: true}));
  assert.equal(box.hidden, false); assert.equal(h.pins().length, 3, 'the preview of D over A, B and C');
  h.run('evmKeyUp')({key: 'Control'});
  assert.deepEqual([box.hidden, h.pins().length], [true, 3]);
  a.onmouseenter(ev({ctrlKey: true}));
  assert.equal(box.hidden, true, 'no preview copy of a pinned model');
  assert.deepEqual([h.pin('a').style.zIndex, /\bflash\b/.test(h.pin('a').className)], ['3', true], 'its window comes forward instead');
  d.onmouseenter(ev({ctrlKey: true}));
  box.onpointerdown(ev({button: 0, pointerId: 2}));
  h.run('previewRelease')(ev({pointerId: 2}));  // pointerup, then the click of the browser on the pressed button
  const settings = h.button(h.peek(), 'Настройки'); settings.focus(); settings.onclick();
  assert.equal(h.el('evmSettingsWindow').hidden, false, 'the click of the button pressed in the preview still does its job');
  assert.equal(box.hidden, false, 'the preview turns into a window only after that click');
  await wait(5);
  assert.equal(box.hidden, true);
  assert.deepEqual(h.pins().map(p => p.getAttribute('data-connection')), ['api:prov:a', 'api:prov:b', 'api:prov:c', 'api:prov:d']);
  assert.equal(h.run('evm.returnTo.key'), 'pin:api:prov:d:settings', 'the dialog returns to the pinned copy');
  h.el('evmSetClose').onclick(); await settle();
  assert.equal(h.document.activeElement, h.button(h.pinCard(h.pin('d')), 'Настройки'));
  e.onmouseenter(ev({ctrlKey: true}));
  const title = ev({button: 0, pointerId: 3, clientX: 10, clientY: 10}); h.bar().onpointerdown(title);
  assert.equal(title.stopped, true);
  assert.equal(box.hidden, true);
  assert.ok(h.pin('e'), 'a press on the preview title pins it at once ...');
  assert.equal(h.run('evm.winDrag.id'), 'api:prov:e', '... and the same press moves the new window');
  h.run('pinMove')(ev({pointerId: 3, clientX: 110, clientY: 60}));
  h.run('pinEnd')(ev({pointerId: 3})); await settle();
  assert.deepEqual([h.pin('e').style.left, h.pin('e').style.top], ['100px', '50px']);
  assert.deepEqual(h.posts('/ultra/model-cards/layout').slice(-2), [{connection_id: 'api:prov:e', window: {x: 0, y: 0}}, {connection_id: 'api:prov:e', window: {x: 100, y: 50}}]);
  e.onmouseenter(ev({ctrlKey: true}));
  assert.deepEqual([box.hidden, h.pins().length], [true, 5], 'E is pinned now: no preview copy of it');
});

test('E42 the saved windows come back once, where they were left; a redraw keeps the same windows; an absent model leaves no broken window', async () => {
  const h = harness(); await settle();
  let status = api('red', 'NEVER_CONFIRMED'), list = [conn('a', 'A'), conn('b', 'B'), conn('c', 'C')];
  const layout = {state: 'SAVED', revision: 3, hidden: 0, windows: [{connection_id: 'api:prov:b', x: 300, y: 200}, {connection_id: 'api:prov:a', x: 50, y: 60},
    {connection_id: 'api:prov:gone', x: 1, y: 1}]};
  h.routes.set('/ultra/connections', () => catalog(list));
  h.routes.set('/ultra/model-cards', () => cards(list.map(c => mcard(c.model_id, c.display_name, c.model_id === 'b' ? {api: status} : {})),
    {view: {state: 'SAVED', revision: 7, hidden: 0, sections: {favorites: [], api: list.map(c => c.connection_id), mcp: [], local: []}, layout}}));
  h.el('viewEvm').onclick(); await settle();
  assert.deepEqual(h.pins().map(p => [p.getAttribute('data-connection'), p.style.left, p.style.top, p.style.zIndex]),
    [['api:prov:b', '300px', '200px', '1'], ['api:prov:a', '50px', '60px', '2']], 'in place and in the saved stacking order');
  assert.equal(h.posts('/ultra/model-cards/layout').length, 0, 'restoring saves nothing');
  const pinB = h.pin('b');
  status = api('green', 'CONFIRMED');
  h.el('evmRefresh').onclick(); await settle();
  assert.equal(h.pins().length, 2, 'no duplicate after reading the board again');
  assert.equal(h.pin('b'), pinB, 'the same window element');
  assert.equal(pinB.style.left, '300px', 'at the same place');
  assert.equal(h.dot(h.pinCard(pinB)).getAttribute('data-api'), 'green:CONFIRMED', 'with the new content');
  list = [conn('a', 'A'), conn('c', 'C')];
  h.el('evmRefresh').onclick(); await settle();
  assert.deepEqual([pinB.hidden, h.pins().length, h.pinCard(pinB)], [true, 2, null], 'an absent model: its window is hidden, not broken');
  list = [conn('a', 'A'), conn('b', 'B'), conn('c', 'C')];
  h.el('evmRefresh').onclick(); await settle();
  assert.deepEqual([pinB.hidden, pinB.style.left], [false, '300px'], 'it comes back with its model');
  h.pinClose(h.pin('a')).onclick(ev({detail: 1})); await settle();
  h.el('evmRefresh').onclick(); await settle();
  assert.equal(h.pin('a'), null, 'a window closed by «×» is not restored by reading the board again');
  const h2 = harness(); await settle();
  await h2.openEvm([conn('a', 'A')], cards([mcard('a', 'A')], {view: {state: 'SAVED', revision: 1, hidden: 0,
    sections: {favorites: [], api: ['api:prov:a'], mcp: [], local: []}, layout: {state: 'CORRUPT', revision: null, windows: [], hidden: 0}}}));
  assert.equal(h2.pins().length, 0);
  assert.match(h2.el('evmError').textContent, /Сохранённое расположение окон повреждено и не используется/);
});

test('E43 layout writes are queued in order; a refused write is told and the window stays where the user put it', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')]);
  let release, first = true;
  h.routes.set('/ultra/model-cards/layout', opts => {
    const body = JSON.parse(opts.body);
    const answer = {view: {layout: {state: 'SAVED', revision: 1, windows: body.window ? [{connection_id: body.connection_id, ...body.window}] : [], hidden: 0}}};
    if (first) {first = false; return new Promise(resolve => {release = () => resolve(answer);});}
    return answer;
  });
  await h.quick(h.cards()[0]);
  h.pinClose(h.pin('a')).onclick(ev({detail: 1})); await settle();
  assert.equal(h.calls.filter(c => c.url === '/ultra/model-cards/layout').length, 1, 'the second write waits for the first');
  release(); await settle();
  assert.deepEqual(h.posts('/ultra/model-cards/layout').map(p => p.window), [{x: 24, y: 28}, null], 'in the order they were made');
  h.routes.set('/ultra/model-cards/layout', () => ({httpError: true, status: 409, data: {error: {code: 'model_cards_state_error', message: 'lock busy'}}}));
  await h.quick(h.cards()[1]);
  assert.match(h.el('evmError').textContent, /Расположение окна не сохранено: model_cards_state_error/);
  assert.deepEqual(h.pins().map(p => p.getAttribute('data-connection')), ['api:prov:b'], 'the window stays');
  h.routes.set('/ultra/model-cards/layout', () => ({view: {layout: {state: 'SAVED', revision: 9, windows: [], hidden: 0}}}));
  h.pinClose(h.pin('b')).onclick(ev({detail: 1})); await settle();
  assert.equal(h.run('evm.cards.view.layout.revision'), 9, 'the answer of the server is kept');
  assert.equal(h.run('evm.cards.view.revision'), 7, 'and the board revision is not touched by a window');
});

test('E44 browser size and zoom: windows are shown inside the window with the title reachable; the kept position comes back', async () => {
  const h = harness(); await settle();
  await h.openEvm([conn('a', 'A'), conn('b', 'B')]);
  h.layoutRoute(); h.layout();
  Object.assign(h.context.window, {innerWidth: 1400, innerHeight: 900});
  h.run("openPin('api:prov:a',{x:940,y:852})");
  const pin = h.pin('a');
  assert.deepEqual([pin.style.left, pin.style.top, pin.style.width, pin.style.maxHeight], ['940px', '852px', '460px', '120px']);
  Object.assign(h.context.window, {innerWidth: 390, innerHeight: 844});  // a phone, or a narrow window at 150 %
  h.run('placeAllPins()');
  assert.deepEqual([pin.style.left, pin.style.top, pin.style.width], ['24px', '796px', '366px'], 'pulled inside: «×» reachable');
  assert.equal(h.run("evm.pins['api:prov:a'].x"), 940, 'the kept position is not overwritten');
  Object.assign(h.context.window, {innerWidth: 933, innerHeight: 667});  // 1400 x 1000 at 150 %
  h.run('placeAllPins()');
  assert.deepEqual([pin.style.left, pin.style.top], ['473px', '619px']);
  Object.assign(h.context.window, {innerWidth: 1400, innerHeight: 900});
  h.run('placeAllPins()');
  assert.deepEqual([pin.style.left, pin.style.top], ['940px', '852px'], 'back where the user left it');
  const header = new Element('header'); header.getBoundingClientRect = () => rect(0, 0, 1400, 240);
  h.document.querySelector = sel => sel === 'header.top' ? header : null;
  h.run("openPin('api:prov:b',{x:100,y:20})");
  assert.equal(h.pin('b').style.top, '248px', 'never under the sticky page header');
  assert.equal(h.posts('/ultra/model-cards/layout').length, 0, 'showing a window inside never saves it');
});
