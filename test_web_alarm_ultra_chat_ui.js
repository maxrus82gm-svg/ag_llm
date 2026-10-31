// Ultra Chat stage 1 (CLAUDE-WUA-CHAT-S1-READONLY-UI-001): run the actual shipped client in the same deterministic
// DOM adapter as the operator and EVM tests (node:vm, no packages, no network, no project writes). Every server
// answer is a fixture; the page must render it as text, keep the read token to /ultra/chat/* only and never write.
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
const settle = async () => {for (let i = 0; i < 60; i++) await new Promise(setImmediate);};
const TOKEN = 'T'.repeat(43);
const HEADER = 'X-WebAlarm-Ultra-Chat-Token';
const cap = (extra = {}) => ({ultra_chat: {available: true, reason: null, scope: 'ultra_chat_read', header: HEADER, token: TOKEN, ...extra}});
const ws = (id, name, history = 'ok') => ({wa_workspace_id: id, display_name: name, history});
const chatItem = (id, title, status = 'ok') => status === 'ok' ? {chat_id: id, status, title, created_at: '2026-10-01T10:00:00+00:00'} : {chat_id: id, status};
const msg = (n, role, text, outcome, extra = {}) => ({message_id: 'msg_' + String(n).padStart(32, '0'), role, created_at: `2026-10-01T10:00:${String(n).padStart(2, '0')}+00:00`, text, outcome, ...extra});
const page = (messages, extra = {}) => ({wa_workspace_id: 'ws_a', chat_id: 'chat_a', chat: {chat_id: 'chat_a', title: 'Первый диалог'}, history_state: 'complete',
  excluded: {}, excluded_ids: [], total_messages: messages.length, outcome_source: 'run_index', messages, page: {limit: 50, returned: messages.length, has_more: false, next_before: null}, ...extra});
const MESSAGES_A = '/ultra/chat/workspaces/ws_a/chats/chat_a/messages?limit=50';

function harness({routes = {}, hash = null, storage = null} = {}) {
  const h = {calls: [], routes: new Map(Object.entries(routes)), stored: [], replaced: []};
  const elements = {};
  for (const m of source.matchAll(/<([a-z0-9]+)[^>]*\bid="([^"]+)"[^>]*>/g)) {
    const e = new Element(m[1]); e.id = m[2]; e.hidden = m[0].includes(' hidden');
    for (const [, name, value] of m[0].matchAll(/\s([a-z][a-z-]*)="([^"]*)"/g)) e.attrs[name] = value;
    e.disabled = /\sdisabled[\s>]/.test(m[0]);
    elements[e.id] = e;
  }
  const all = () => {const s = new Set(Object.values(elements)); const add = e => {for (const c of e.children) {s.add(c); add(c);}}; Object.values(elements).forEach(add); return [...s];};
  const document = {hidden: false, activeElement: null, getElementById: id => elements[id], createElement: tag => {const e = new Element(tag); e.document = document; return e;}, querySelectorAll: () => []};
  Object.values(elements).forEach(e => e.document = document);
  const defaults = url => {
    if (url === '/status') return {service: 'web_alarm_server', mode: 'server', api_version: 1};
    if (url === '/workspaces') return {workspaces: []};
    if (url === '/ui/tasks') return {active: [], completed: [], errors: []};
    if (url === '/ui/capabilities') return {folder_picker: {available: false, reason: 'disabled', token: null}};
    if (url === '/ui/ultra-chat/capability') return cap();
    if (url === '/ultra/connections/selection?role=chat') return {selection: {role: 'chat', state: 'SAVED', display_name: 'Модель А', model_id: 'a', provider_model_id: 'A', connection_id: 'api:p:a'}};
    if (url === '/ultra/chat/workspaces') return {state: 'ok', workspaces: [ws('ws_a', 'Проект А'), ws('ws_b', 'Проект Б')]};
    if (url === '/ultra/chat/workspaces/ws_a/chats') return {wa_workspace_id: 'ws_a', display_name: 'Проект А', state: 'ok', chats: [chatItem('chat_a', 'Первый диалог')], excluded: {}};
    if (url === MESSAGES_A) return page([msg(1, 'user', 'привет', 'request'), msg(2, 'assistant', 'ответ', 'completed', {model: 'Модель А'})]);
    return {httpError: true, status: 404, data: {error: {code: 'not_found', message: 'fixture has no route'}}};
  };
  const storageMap = storage || new Map();
  const context = {document, console, AbortController, crypto: require('node:crypto').webcrypto,
    setTimeout: (fn, ms) => {const t = setTimeout(fn, ms); t.unref(); return t;}, clearTimeout,
    setInterval: () => 0, Date, localStorage: {getItem: k => storageMap.get(k) ?? null, setItem: (k, v) => {h.stored.push([k, String(v)]); storageMap.set(k, String(v));}, removeItem: k => storageMap.delete(k)},
    window: {confirm: () => true, matchMedia: () => ({matches: false}), scrollTo: () => {}, addEventListener: () => {}},
    navigator: {locks: {request: async (k, o, fn) => fn({name: k})}, clipboard: {writeText: async () => {}}},
    fetch: async (url, opts) => {
      h.calls.push({url, method: opts.method || 'GET', headers: {...(opts.headers || {})}, body: opts.body});
      const route = h.routes.get(url);
      const value = route ? await route(opts) : defaults(url);
      if (value?.httpError) return {ok: false, status: value.status, json: async () => value.data};
      return {ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(value))};
    }};
  if (hash !== null) {
    context.location = {hash};
    context.history = {replaceState: (s, t, u) => h.replaced.push(u)};
  }
  h.context = vm.createContext(context);
  h.el = id => elements[id];
  h.all = all;
  h.run = code => vm.runInContext(code, h.context);
  h.chatCalls = () => h.calls.filter(c => c.url.startsWith('/ultra/chat/'));
  h.items = () => h.el('chatHistory').children;
  h.picks = id => h.el(id).children;
  vm.runInContext(script, h.context);
  return h;
}

test('U1 Ultra Chat opens by default and reads only: capability, Workspaces, history and the EVM badge', async () => {
  const h = harness(); await settle();
  assert.equal(h.el('chatView').hidden, false);
  assert.equal(h.el('layout').hidden, true);
  assert.equal(h.el('evmView').hidden, true);
  assert.deepEqual(['viewChat', 'viewOperator', 'viewEvm'].map(id => h.el(id).getAttribute('aria-pressed')), ['true', 'false', 'false']);
  assert.equal(h.el('showWorkspaces').hidden, true);
  const urls = h.calls.map(c => c.url);
  for (const url of ['/ui/ultra-chat/capability', '/ultra/chat/workspaces', '/ultra/chat/workspaces/ws_a/chats', MESSAGES_A, '/ultra/connections/selection?role=chat', '/status'])
    assert.ok(urls.includes(url), url);
  assert.equal(h.calls.filter(c => c.method !== 'GET').length, 0);
  assert.equal(urls.includes('/ultra/connections'), false, 'the EVM catalog is not read by the chat screen');
  assert.equal(h.el('chatTitle').textContent, 'Первый диалог');
  assert.equal(h.el('chatModel').textContent, 'Модель: Модель А');
  assert.equal(h.el('skipLink').getAttribute('href'), '#chatMain');
});

test('U2 the read token travels only in its own header to /ultra/chat/* and is stored nowhere', async () => {
  const h = harness(); await settle();
  assert.ok(h.chatCalls().length >= 3);
  for (const c of h.calls) {
    const withToken = c.headers[HEADER] === TOKEN;
    assert.equal(withToken, c.url.startsWith('/ultra/chat/'), c.url);
    assert.ok(!c.url.includes(TOKEN), 'token in a URL');
    assert.ok(!Object.keys(c.headers).some(k => k !== HEADER && String(c.headers[k]).includes(TOKEN)));
  }
  assert.ok(!h.stored.some(([k, v]) => v.includes(TOKEN) || k.includes(TOKEN)), 'token written to localStorage');
  assert.equal(h.context.document.cookie, undefined);
});

test('U3 history renders server text as text, labels outcomes and never shows an old failure as an answer', async () => {
  const xss = '<img src=x onerror=alert(1)><script>alert(2)</script>';
  const h = harness({routes: {[MESSAGES_A]: () => page([
    msg(1, 'user', xss, 'request'),
    msg(2, 'assistant', 'RUN STATUS: FAILED\nRuntimeError: boom', 'failed', {model: 'Модель А', run_status: 'FAILED'}),
    msg(3, 'user', 'без ответа', 'no_answer'),
    msg(4, 'user', 'оборвалось', 'interrupted'),
    msg(5, 'assistant', 'давний ответ', 'legacy'),
    msg(6, 'system', 'служебное', 'service')])}});
  await settle();
  const items = h.items();
  assert.equal(items.length, 6);
  assert.equal(items[0].children[1].textContent, xss);
  assert.ok(h.all().every(e => !('innerHTML' in e)), 'markup was assigned');
  assert.equal(items[1].getAttribute('data-outcome'), 'failed');
  assert.match(items[1].textContent, /Ошибка выполнения/);
  assert.match(items[1].textContent, /не ответ модели/);
  assert.doesNotMatch(items[1].children[0].textContent, /Ultra|Модель А/);
  assert.match(items[2].textContent, /Ответ не сохранён/);
  assert.match(items[3].textContent, /Прервано · исход неизвестен/);
  assert.match(items[4].children[0].textContent, /^Ultra/);
  assert.match(items[5].children[0].textContent, /^Система/);
  assert.equal(items[0].getAttribute('data-role'), 'user');
});

test('U4 every data state is told apart: workspaces, chats and history', async () => {
  const h = harness({routes: {
    '/ultra/chat/workspaces': () => ({state: 'ok', workspaces: [ws('ws_a', 'Проект А'), ws('ws_n', 'Без истории', 'missing_history'),
      ws('ws_g', 'Пропал', 'missing_path'), ws('ws_l', 'Ссылка', 'unsafe_storage_link')]}),
    '/ultra/chat/workspaces/ws_a/chats': () => ({wa_workspace_id: 'ws_a', display_name: 'Проект А', state: 'ok', excluded: {foreign_identity: 2},
      chats: [chatItem('chat_a', 'Первый диалог'), chatItem('chat_d', null, 'damaged'), chatItem('chat_l', null, 'unsafe_storage_link')]}),
    [MESSAGES_A]: () => page([msg(1, 'user', 'есть', 'request')], {history_state: 'partial', excluded: {damaged: 2, foreign_identity: 1}, outcome_source: 'run_index_unavailable'}),
    '/ultra/chat/workspaces/ws_n/chats': () => ({wa_workspace_id: 'ws_n', display_name: 'Без истории', state: 'unavailable', reason: 'missing_history', chats: [], excluded: {}})}});
  await settle();
  const wsText = h.picks('chatWorkspaceList').map(b => b.textContent);
  assert.match(wsText[0], /История Ultra найдена/);
  assert.match(wsText[1], /нет истории Ultra/);
  assert.match(wsText[2], /Папка недоступна/);
  assert.match(wsText[3], /ссылка вместо папки/);
  const chats = h.picks('chatList');
  assert.deepEqual(chats.map(b => [b.getAttribute('data-status'), b.disabled]), [['ok', false], ['damaged', true], ['unsafe_storage_link', true]]);
  assert.match(chats[1].textContent, /Диалог повреждён/);
  assert.match(h.el('chatListState').textContent, /Диалогов: 3 · не показано посторонних записей: 2/);
  assert.equal(h.el('chatNotice').hidden, false);
  assert.match(h.el('chatNotice').textContent, /Показана не вся история: не показано записей — 3/);
  assert.match(h.el('chatNotice').textContent, /Журнал запусков недоступен/);
  h.picks('chatWorkspaceList')[1].onclick(); await settle();
  assert.match(h.el('chatListState').textContent, /В папке нет истории Ultra/);
  assert.equal(h.items().length, 0);
  for (const [state, extra, expected] of [['empty', {}, /нет сообщений/], ['too_large', {reason: 'history_too_large'}, /слишком большая.*не обрезана/s],
    ['unavailable', {reason: 'unsafe_storage_link'}, /История недоступна: Внутри хранилища Ultra ссылка/]]) {
    const one = harness({routes: {[MESSAGES_A]: () => ({...page([], {history_state: state, ...extra}), chat: undefined})}}); await settle();
    assert.match(one.el('chatNotice').textContent, expected, state);
    assert.equal(one.items().length, 0);
    assert.equal(one.el('chatTitle').textContent, 'Первый диалог', 'the title of an unreadable history comes from the list');
  }
  const empty = harness({routes: {'/ultra/chat/workspaces/ws_a/chats': () => ({wa_workspace_id: 'ws_a', display_name: 'Проект А', state: 'ok', chats: [], excluded: {}})}});
  await settle();
  assert.match(empty.el('chatListState').textContent, /нет сохранённых диалогов/);
  const none = harness({routes: {'/ultra/chat/workspaces': () => ({state: 'ok', workspaces: []})}}); await settle();
  assert.match(none.el('chatWorkspaceState').textContent, /Нет зарегистрированных Workspace/);
  const big = harness({routes: {[MESSAGES_A]: () => page([{...msg(1, 'user', null, 'request'), text: null, too_large_for_page: true, size_bytes: 9000000}])}});
  await settle();
  assert.match(big.items()[0].textContent, /слишком большое для одной страницы \(9000000 байт\)/);
});

test('U5 older pages are fetched with the cursor, prepended once, and the button hides at the start', async () => {
  const older = '/ultra/chat/workspaces/ws_a/chats/chat_a/messages?limit=50&before=' + msg(3, 'user', '', '').message_id;
  let release;
  const h = harness({routes: {
    [MESSAGES_A]: () => page([msg(3, 'user', 'три', 'request'), msg(4, 'assistant', 'четыре', 'completed')], {page: {limit: 50, returned: 2, has_more: true, next_before: msg(3, 'user', '', '').message_id}}),
    [older]: () => new Promise(resolve => {release = () => resolve(page([msg(1, 'user', 'один', 'request'), msg(2, 'assistant', 'два', 'completed')]));})}});
  const box = h.el('chatHistory');
  Object.defineProperty(box, 'scrollHeight', {get: () => box.children.length * 100});
  await settle();
  assert.equal(box.scrollTop, 200, 'a dialogue opens at its newest message');
  box.scrollTop = 0;  // the reader scrolled up to the oldest loaded message
  assert.equal(h.el('chatOlder').hidden, false);
  h.el('chatOlder').onclick(); h.el('chatOlder').onclick(); await settle();
  assert.equal(h.calls.filter(c => c.url === older).length, 1, 'a double click sent two page requests');
  release(); await settle();
  assert.deepEqual(h.items().map(i => i.children[1].textContent), ['один', 'два', 'три', 'четыре']);
  assert.equal(h.el('chatOlder').hidden, true);
  assert.equal(box.scrollTop, 200, 'the older page moved the reader away from the message they were on');
});

test('U6 after a server restart the page fetches one new capability and repeats once, then stops honestly', async () => {
  let attempts = 0;
  const h = harness({routes: {'/ultra/chat/workspaces': opts => (++attempts === 1 ? {httpError: true, status: 403, data: {error: {code: 'ultra_chat_token_invalid', message: 'x'}}}
    : {state: 'ok', workspaces: [ws('ws_a', 'Проект А')]})}});
  await settle();
  assert.equal(h.calls.filter(c => c.url === '/ui/ultra-chat/capability').length, 2);
  assert.equal(attempts, 2);
  assert.equal(h.el('chatError').hidden, true);
  const stuck = harness({routes: {'/ultra/chat/workspaces': () => ({httpError: true, status: 403, data: {error: {code: 'ultra_chat_token_invalid', message: 'x'}}})}});
  await settle();
  assert.equal(stuck.calls.filter(c => c.url === '/ultra/chat/workspaces').length, 2);
  assert.equal(stuck.calls.filter(c => c.url === '/ui/ultra-chat/capability').length, 2);
  assert.match(stuck.el('chatError').textContent, /Доступ к истории недействителен — обновите страницу/);
});

test('U7 an unavailable capability is explained and the other sections keep working', async () => {
  for (const [reason, expected] of [['disabled', /выключено при запуске сервера/], ['non_loopback_bind', /не на локальном адресе/]]) {
    const h = harness({routes: {'/ui/ultra-chat/capability': () => cap({available: false, reason, token: null}),
      '/ultra/connections': () => ({source: 'model_registry', network_calls: 0, columns: {api: {state: 'AVAILABLE', connections: []},
        mcp_agents: {state: 'NOT_CONNECTED', connections: []}, local_llm: {state: 'NOT_CONNECTED', connections: []}}, selection: {chat: {role: 'chat', state: 'NOT_SELECTED'}}})}});
    await settle();
    assert.match(h.el('chatAccess').textContent, expected);
    assert.equal(h.chatCalls().length, 0);
    h.el('viewOperator').onclick(); await settle();
    assert.equal(h.el('layout').hidden, false);
    h.el('viewEvm').onclick(); await settle();
    assert.equal(h.el('evmView').hidden, false);
    assert.equal(h.el('evmState').textContent, 'Реестр пуст');
  }
});

test('U8 the composer is visibly read-only and nothing is ever posted', async () => {
  const h = harness(); await settle();
  assert.equal(h.el('chatInput').disabled, true);
  assert.equal(h.el('chatSend').disabled, true);
  // Stage 2 (CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001): the composer still sends nothing; the note now names create/rename.
  assert.match(source, /<p id="chatComposerNote" class="muted">Отправка сообщений появится на следующем этапе\. Сейчас Ultra Chat читает сохранённую историю, создаёт и переименовывает диалоги\.<\/p>/);
  assert.equal(h.el('chatInput').getAttribute('aria-describedby'), 'chatComposerNote');
  let prevented = false;
  h.el('chatComposer').onsubmit({preventDefault: () => {prevented = true;}});
  assert.equal(prevented, true);
  h.el('chatRefresh').onclick(); await settle();
  h.picks('chatWorkspaceList')[1].onclick(); await settle();
  h.picks('chatWorkspaceList')[0].onclick(); await settle();
  assert.equal(h.calls.filter(c => c.method !== 'GET').length, 0);
});

test('U9 sections switch both ways and #operator / #evm open a section directly', async () => {
  const h = harness({hash: ''}); await settle();
  h.el('viewOperator').onclick(); await settle();
  assert.deepEqual([h.el('chatView').hidden, h.el('layout').hidden, h.el('evmView').hidden], [true, false, true]);
  assert.equal(h.el('skipLink').getAttribute('href'), '#main');
  assert.equal(h.el('showTasks').hidden, false);
  h.el('viewChat').onclick(); await settle();
  assert.equal(h.el('chatView').hidden, false);
  assert.equal(h.context.document.activeElement, h.el('chatHeading'));
  assert.deepEqual(h.replaced, ['#operator', '#chat']);
  assert.equal(h.calls.filter(c => c.url === '/ui/ultra-chat/capability').length, 1, 'returning to the chat reloaded it');
  const operator = harness({hash: '#operator'}); await settle();
  assert.equal(operator.el('layout').hidden, false);
  assert.equal(operator.el('chatView').hidden, true);
  assert.equal(operator.calls.filter(c => c.url.startsWith('/ultra/') || c.url.startsWith('/ui/ultra')).length, 0);
  assert.equal(operator.context.document.activeElement, null, 'the initial view must not steal focus');
  const evm = harness({hash: '#evm'}); await settle();
  assert.equal(evm.el('evmView').hidden, false);
  assert.ok(evm.calls.some(c => c.url === '/ultra/connections'));
});

test('U10 a late answer for a Workspace that is no longer selected is ignored', async () => {
  let releaseA;
  const h = harness({routes: {
    '/ultra/chat/workspaces/ws_a/chats': () => new Promise(resolve => {releaseA = () => resolve({wa_workspace_id: 'ws_a', display_name: 'Проект А', state: 'ok', chats: [chatItem('chat_a', 'Первый диалог')], excluded: {}});}),
    '/ultra/chat/workspaces/ws_b/chats': () => ({wa_workspace_id: 'ws_b', display_name: 'Проект Б', state: 'ok', chats: [chatItem('chat_b', 'Диалог Б')], excluded: {}})}});
  await settle();
  h.picks('chatWorkspaceList')[1].onclick(); await settle();
  releaseA(); await settle();
  assert.deepEqual(h.picks('chatList').map(b => b.children[0].textContent), ['Диалог Б']);
  assert.equal(h.el('chatWorkspaceName').textContent, 'Проект Б');
  assert.equal(h.calls.filter(c => c.url.includes('/chats/chat_a/')).length, 0);
});

test('U11 malformed server answers show an error and invent nothing', async () => {
  const bad = [
    ['/ultra/chat/workspaces', {state: 'ok', workspaces: [{wa_workspace_id: 1}]}, 'chatWorkspaceList'],
    ['/ultra/chat/workspaces/ws_a/chats', {state: 'ok', chats: [{chat_id: 'chat_a', status: 'ok'}]}, 'chatList'],
    [MESSAGES_A, {...page([]), messages: [{message_id: 'm', role: 'robot', outcome: 'x', text: 't'}]}, 'chatHistory'],
    ['/ui/ultra-chat/capability', {ultra_chat: {available: true, header: 'X-Other', token: TOKEN}}, 'chatWorkspaceList']];
  for (const [url, answer, region] of bad) {
    const h = harness({routes: {[url]: () => answer}}); await settle();
    assert.equal(h.el('chatError').hidden, false, url);
    assert.equal(h.el(region).children.length, 0, url);
  }
});

test('U12 the EVM model badge tells every saved-choice state', async () => {
  for (const [selection, expected] of [[{state: 'SAVED', display_name: 'Модель Б'}, /^Модель: Модель Б$/], [{state: 'NOT_SELECTED'}, /не выбрана/],
    [{state: 'CORRUPT'}, /повреждён/], [{state: 'INVALID_REFERENCE'}, /недоступна/], [{state: 'REGISTRY_UNAVAILABLE'}, /Реестр моделей недоступен/]]) {
    const h = harness({routes: {'/ultra/connections/selection?role=chat': () => ({selection: {role: 'chat', ...selection}})}}); await settle();
    assert.match(h.el('chatModel').textContent, expected);
  }
  const broken = harness({routes: {'/ultra/connections/selection?role=chat': () => ({httpError: true, status: 503, data: {error: {code: 'x', message: 'y'}}})}});
  await settle();
  assert.match(broken.el('chatModel').textContent, /нет данных EVM/);
});

// ---- Stage 2 (CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001): create and rename through the separate write capability ----
const WTOKEN = 'W'.repeat(43);
const WHEADER = 'X-WebAlarm-Ultra-Chat-Write-Token';
const wcap = (extra = {}) => ({ultra_chat_write: {available: true, reason: null, scope: 'ultra_chat_write', header: WHEADER, token: WTOKEN, ...extra}});
const CHATS_A = '/ultra/chat/workspaces/ws_a/chats';
const RENAME_A = CHATS_A + '/chat_a/title';
const refused = (status, code) => ({httpError: true, status, data: {error: {code, message: 'refused by the fixture'}}});
const submit = h => h.el('chatNameForm').onsubmit({preventDefault() {}});

// A tiny stand-in for the server's chat list: GET lists, POST create appends (idempotent by chat_id, like the core).
function chatServer(initial = [chatItem('chat_a', 'Первый диалог')]) {
  const s = {chats: initial.map(c => ({...c})), posts: []};
  s.route = opts => {
    if ((opts.method || 'GET') === 'GET') return {wa_workspace_id: 'ws_a', display_name: 'Проект А', state: 'ok', chats: s.chats.map(c => ({...c})), excluded: {}};
    const body = JSON.parse(opts.body);
    s.posts.push({body, headers: {...opts.headers}});
    const known = s.chats.find(c => c.chat_id === body.chat_id);
    if (known) return {wa_workspace_id: 'ws_a', chat: known, created: false};
    const item = {chat_id: body.chat_id, status: 'ok', title: body.title || 'Чат ' + (s.chats.length + 1), created_at: '2026-10-31T10:00:00+00:00'};
    s.chats.push(item);
    return {wa_workspace_id: 'ws_a', chat: item, created: true};
  };
  return s;
}

test('U13 a dialogue is created only on Save, with a page-made chat_id and the write token alone; the list is re-read', async () => {
  const srv = chatServer();
  const h = harness({routes: {[CHATS_A]: srv.route, '/ui/ultra-chat/write-capability': () => wcap()}}); await settle();
  assert.equal(h.calls.some(c => c.url === '/ui/ultra-chat/write-capability'), false, 'no write capability is asked at load');
  assert.equal(h.el('chatNew').disabled, false);
  assert.equal(h.el('chatNameForm').hidden, true);
  h.el('chatNew').onclick();
  assert.equal(h.el('chatNameForm').hidden, false);
  assert.equal(h.el('chatNameInput').value, '');
  assert.equal(h.calls.filter(c => c.method !== 'GET').length, 0, 'opening the form writes nothing');
  h.el('chatNameInput').value = '  Новый план  ';
  await submit(h); await settle();
  assert.equal(srv.posts.length, 1);
  const [post] = srv.posts;
  assert.match(post.body.chat_id, /^chat_[0-9a-f]{32}$/);
  assert.deepEqual(Object.keys(post.body).sort(), ['chat_id', 'title']);
  assert.equal(post.body.title, 'Новый план');
  assert.equal(post.headers[WHEADER], WTOKEN);
  assert.equal(post.headers[HEADER], undefined, 'the read token never goes with a write');
  assert.equal(h.el('chatNameForm').hidden, true);
  assert.equal(h.calls.filter(c => c.url === CHATS_A && c.method === 'GET').length, 2, 'the list is re-read from the server');
  assert.deepEqual(h.picks('chatList').map(b => [b.textContent.split('Создан')[0], b.getAttribute('aria-current')]),
    [['Первый диалог', 'false'], ['Новый план', 'true']]);
  assert.ok(h.calls.some(c => c.url === `${CHATS_A}/${post.body.chat_id}/messages?limit=50`), 'the new dialogue is opened');
  // An empty title lets the server choose «Чат N»: the body then carries the chat_id only.
  h.el('chatNew').onclick(); await submit(h); await settle();
  assert.deepEqual(Object.keys(srv.posts[1].body), ['chat_id']);
  assert.notEqual(srv.posts[1].body.chat_id, post.body.chat_id, 'a new form is a new dialogue');
  for (const c of h.calls) {
    const read = c.headers[HEADER] === TOKEN, write = c.headers[WHEADER] === WTOKEN;
    assert.ok(!(read && write), 'never both tokens');
    if (write) assert.ok(c.method === 'POST' && c.url.startsWith('/ultra/chat/workspaces/'), c.url);
    if (read) assert.equal(c.method, 'GET', c.url);
    assert.ok(!c.url.includes(TOKEN) && !c.url.includes(WTOKEN), 'token in a URL');
  }
  assert.ok(!h.stored.some(([k, v]) => (k + v).includes(WTOKEN) || (k + v).includes(TOKEN)), 'a token written to localStorage');
});

test('U14 rename sends the title the user saw; a change made elsewhere is refused, re-read and replaced only on a second Save', async () => {
  let title = 'Первый диалог';
  const posts = [];
  const h = harness({routes: {'/ui/ultra-chat/write-capability': () => wcap(),
    [CHATS_A]: () => ({wa_workspace_id: 'ws_a', display_name: 'Проект А', state: 'ok', chats: [chatItem('chat_a', title)], excluded: {}}),
    [RENAME_A]: opts => {
      const body = JSON.parse(opts.body); posts.push({body, headers: {...opts.headers}});
      if (body.expected_title !== title) return refused(409, 'title_changed');
      title = body.title; return {wa_workspace_id: 'ws_a', chat: chatItem('chat_a', title)};
    }}});
  await settle();
  h.el('chatRename').onclick();
  assert.equal(h.el('chatNameInput').value, 'Первый диалог');
  h.el('chatNameInput').value = '   ';
  await submit(h); await settle();
  assert.equal(posts.length, 0, 'an empty title is not sent');
  assert.match(h.el('chatNameError').textContent, /не может быть пустым/);
  title = 'Переименован в Tk'; // another window renames the dialogue while this form is open
  h.el('chatNameInput').value = 'Из веба';
  await submit(h); await settle();
  assert.deepEqual(posts[0].body, {title: 'Из веба', expected_title: 'Первый диалог'});
  assert.equal(posts[0].headers[WHEADER], WTOKEN);
  assert.equal(title, 'Переименован в Tk', 'the newer title is not overwritten silently');
  assert.equal(h.el('chatNameForm').hidden, false, 'the form stays open with the typed title');
  assert.match(h.el('chatNameError').textContent, /уже изменено в другом окне/);
  assert.match(h.picks('chatList')[0].textContent, /Переименован в Tk/, 'the list shows what is stored now');
  await submit(h); await settle();
  assert.deepEqual(posts[1].body, {title: 'Из веба', expected_title: 'Переименован в Tk'});
  assert.equal(title, 'Из веба');
  assert.equal(h.el('chatNameForm').hidden, true);
  assert.match(h.picks('chatList')[0].textContent, /Из веба/);
});

test('U15 a lost answer is repeated with the same chat_id, and Save pressed again while saving sends nothing', async () => {
  const srv = chatServer();
  let release;
  const gate = new Promise(resolve => {release = resolve;});
  let attempt = 0;
  const h = harness({routes: {'/ui/ultra-chat/write-capability': () => wcap(), [CHATS_A]: async opts => {
    if ((opts.method || 'GET') === 'POST') {
      attempt += 1;
      if (attempt === 1) {srv.route(opts); throw new TypeError('Failed to fetch');} // stored, but the answer is lost
      await gate;
    }
    return srv.route(opts);
  }}});
  await settle();
  h.el('chatNew').onclick(); h.el('chatNameInput').value = 'Однажды';
  await submit(h); await settle();
  assert.match(h.el('chatNameError').textContent, /Failed to fetch/);
  assert.equal(h.el('chatNameForm').hidden, false);
  const pending = submit(h);
  assert.equal(h.el('chatNew').disabled, true, 'actions are off while a change is saved');
  await submit(h); // a second press during the first
  release(); await pending; await settle();
  assert.equal(srv.posts.length, 2, 'one lost attempt and one repeat, nothing from the second press');
  assert.equal(srv.posts[1].body.chat_id, srv.posts[0].body.chat_id, 'the repeat is the same request');
  assert.equal(srv.chats.length, 2, 'one dialogue was created');
  assert.equal(h.el('chatNameForm').hidden, true);
});

test('U16 an unavailable write capability is explained and nothing is posted', async () => {
  for (const [reason, expected] of [['disabled', /выключены при запуске сервера/], ['non_loopback_bind', /не на локальном адресе/]]) {
    const srv = chatServer();
    const h = harness({routes: {[CHATS_A]: srv.route, '/ui/ultra-chat/write-capability': () => wcap({available: false, reason, token: null})}});
    await settle();
    h.el('chatNew').onclick(); h.el('chatNameInput').value = 'x';
    await submit(h); await settle();
    assert.match(h.el('chatNameError').textContent, expected, reason);
    assert.equal(h.calls.filter(c => c.method !== 'GET').length, 0, reason);
    assert.equal(h.el('chatHistory').children.length, 2, 'reading keeps working');
  }
});

test('U17 after a server restart one new write capability is fetched and the refused request repeated once', async () => {
  const srv = chatServer();
  let refusals = 1, capabilities = 0;
  const h = harness({routes: {'/ui/ultra-chat/write-capability': () => wcap({token: 'V'.repeat(42) + String(++capabilities)}),
    [CHATS_A]: opts => ((opts.method || 'GET') === 'POST' && refusals-- > 0 ? (srv.posts.push({body: JSON.parse(opts.body)}), refused(403, 'ultra_chat_write_token_invalid')) : srv.route(opts))}});
  await settle();
  h.el('chatNew').onclick(); h.el('chatNameInput').value = 'После перезапуска';
  await submit(h); await settle();
  assert.equal(capabilities, 2);
  assert.equal(srv.posts.length, 2);
  assert.equal(srv.posts[1].body.chat_id, srv.posts[0].body.chat_id);
  assert.equal(srv.chats.at(-1).title, 'После перезапуска');
  const stuck = harness({routes: {'/ui/ultra-chat/write-capability': () => wcap(), [CHATS_A]: opts => ((opts.method || 'GET') === 'POST' ? refused(403, 'ultra_chat_write_token_invalid') : chatServer().route(opts))}});
  await settle();
  stuck.el('chatNew').onclick(); await submit(stuck); await settle();
  assert.equal(stuck.calls.filter(c => c.method === 'POST').length, 2, 'one repeat, then an honest error');
  assert.equal(stuck.el('chatNameError').hidden, false);
});

test('U18 actions follow the selection: no history, no dialogue, Escape, Cancel and a Workspace switch', async () => {
  const srv = chatServer();
  const h = harness({routes: {[CHATS_A]: srv.route, '/ui/ultra-chat/write-capability': () => wcap(),
    '/ultra/chat/workspaces': () => ({state: 'ok', workspaces: [ws('ws_a', 'Проект А'), ws('ws_b', 'Без истории', 'missing_history')]}),
    '/ultra/chat/workspaces/ws_b/chats': () => ({wa_workspace_id: 'ws_b', display_name: 'Без истории', state: 'unavailable', reason: 'missing_history', chats: [], excluded: {}})}});
  await settle();
  assert.deepEqual([h.el('chatNew').disabled, h.el('chatRename').disabled], [false, false]);
  h.el('chatRename').onclick();
  assert.equal(h.el('chatNameForm').hidden, false);
  h.el('chatNameInput').onkeydown({key: 'Escape', preventDefault() {}});
  assert.equal(h.el('chatNameForm').hidden, true);
  h.el('chatNew').onclick(); h.el('chatNameCancel').onclick();
  assert.equal(h.el('chatNameForm').hidden, true);
  h.el('chatNew').onclick();
  h.picks('chatWorkspaceList')[1].onclick(); await settle();
  assert.equal(h.el('chatNameForm').hidden, true, 'a Workspace switch closes the form');
  assert.deepEqual([h.el('chatNew').disabled, h.el('chatRename').disabled], [true, true], 'no history: nothing to create in or rename');
  h.el('chatNew').onclick(); h.el('chatRename').onclick();
  assert.equal(h.el('chatNameForm').hidden, true);
  assert.equal(h.calls.filter(c => c.method !== 'GET').length, 0);
  // Server refusals are told in words, never as a bare code.
  for (const [code, expected] of [['workspace_busy', /занят другой записью/], ['workspace_unavailable', /нет доступной истории Ultra/],
    ['invalid_title', /длиннее 200 символов/], ['chats_limit_reached', /слишком много диалогов/], ['unsupported_version', /более новой версией/]]) {
    const one = harness({routes: {'/ui/ultra-chat/write-capability': () => wcap(),
      [CHATS_A]: opts => ((opts.method || 'GET') === 'POST' ? refused(409, code) : chatServer().route(opts))}});
    await settle();
    one.el('chatNew').onclick(); await submit(one); await settle();
    assert.match(one.el('chatNameError').textContent, expected, code);
  }
});

test('U19 a save refused after a Workspace switch closes its form there; a taken chat_id re-reads the list', async () => {
  const srv = chatServer();
  let release;
  const gate = new Promise(resolve => {release = resolve;});
  const h = harness({routes: {'/ui/ultra-chat/write-capability': () => wcap(),
    '/ultra/chat/workspaces/ws_b/chats': () => ({wa_workspace_id: 'ws_b', display_name: 'Проект Б', state: 'ok', chats: [], excluded: {}}),
    [CHATS_A]: async opts => {if ((opts.method || 'GET') === 'POST') {await gate; return refused(503, 'workspace_busy');} return srv.route(opts);}}});
  await settle();
  h.el('chatNew').onclick(); h.el('chatNameInput').value = 'В пути';
  const pending = submit(h); await settle();
  h.picks('chatWorkspaceList')[1].onclick(); await settle(); // another Workspace while the POST waits
  release(); await pending; await settle();
  assert.equal(h.el('chatNameForm').hidden, true, 'the form of the old Workspace is closed');
  assert.equal(h.el('chatNameError').hidden, true, 'its refusal is not shown over the new Workspace');
  assert.equal(h.el('chatWorkspaceName').textContent, 'Проект Б');
  assert.equal(h.picks('chatList').length, 0, 'nothing of the old Workspace is shown in the new one');
  let gets = 0;
  const taken = harness({routes: {'/ui/ultra-chat/write-capability': () => wcap(),
    [CHATS_A]: opts => ((opts.method || 'GET') === 'POST' ? refused(409, 'chat_id_conflict') : (gets++, chatServer().route(opts)))}});
  await settle();
  const before = gets;
  taken.el('chatNew').onclick(); await submit(taken); await settle();
  assert.match(taken.el('chatNameError').textContent, /идентификатор уже занят/);
  assert.equal(gets, before + 1, 'the list is re-read so a chat stored by a lost answer becomes visible');
});
