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
  constructor(tag = 'div') {this.tag = tag; this.children = []; this.parentNode = null; this.attrs = {}; this.dataset = {}; this.style = {}; this.hidden = false; this.disabled = false; this.value = ''; this._text = '';}
  set textContent(value) {this.replaceChildren(); this._text = value == null ? '' : String(value);}
  get textContent() {return this._text + this.children.map(c => c.textContent).join('');}
  append(...children) {
    for (let child of children) {
      // DOM append converts null to a text node and MOVES existing nodes. A detached ID is not discoverable.
      if (!(child instanceof Element)) {const text = new Element('#text'); text.textContent = String(child); child = text;}
      if (child.parentNode) child.parentNode.children.splice(child.parentNode.children.indexOf(child), 1);
      child.parentNode = this; this.children.push(child);
    }
  }
  replaceChildren(...children) {this._text = ''; for (const child of this.children) child.parentNode = null; this.children = []; this.append(...children);}
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

function harness({routes = {}, hash = null, storage = null, offline = false} = {}) {
  const h = {calls: [], routes: new Map(Object.entries(routes)), stored: [], replaced: []};
  const elements = {};
  const root = new Element('document'), stack = [root];
  const markup = source.slice(source.indexOf('<body'), source.indexOf('<script>'));
  for (const m of markup.matchAll(/<(\/?)([a-z0-9]+)\b[^>]*>/g)) {
    if (m[1]) {while (stack.length > 1 && stack.pop().tag !== m[2]) {} continue;}
    const e = new Element(m[2]); e.hidden = /\shidden(?:\s|>)/.test(m[0]);
    for (const [, name, value] of m[0].matchAll(/\s([a-z][a-z-]*)="([^"]*)"/g)) e.attrs[name] = value;
    e.disabled = /\sdisabled[\s>]/.test(m[0]);
    if (e.attrs.id) {e.id = e.attrs.id; elements[e.id] = e;}
    stack.at(-1).append(e);
    if (!['input', 'br', 'hr', 'img', 'meta', 'link'].includes(e.tag)) stack.push(e);
  }
  const all = () => {const nodes = []; const add = e => {nodes.push(e); e.children.forEach(add);}; add(root); return nodes;};
  const document = {hidden: false, activeElement: null, getElementById: id => all().find(e => e.id === id) || null, createElement: tag => {const e = new Element(tag); e.document = document; return e;}, querySelectorAll: () => []};
  document.body = all().find(e => e.tag === 'body');
  if (offline) document.body.setAttribute('data-stage5-offline', 'true');
  all().forEach(e => e.document = document);
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
  h.picks = id => id === 'chatWorkspaceList' ? h.el(id).children.map(g => g.children[0].children[0]) :
    id === 'chatList' ? h.el(id).children.map(row => row.children[0]) : h.el(id).children;
  vm.runInContext(script, h.context);
  return h;
}

const S5_TURN = '/ultra/chat/workspaces/ws_a/chats/chat_a/turns';
const S5_SCOPE = 'webAlarm.testTurn.ws_a.chat_a';
const S5_WRITE = 'X-WebAlarm-Ultra-Chat-Write-Token';
function offlineRoutes(routes = {}) {
  return {
    '/ui/ultra-chat/capability': () => ({...cap(), turn_test: {available: true, mode: 'TEST_OFFLINE',
      models: [{model_id: 'gigachat_2_pro', display_name: 'TEST Pro'}, {model_id: 'gigachat_ultra', display_name: 'TEST Ultra'}]}}),
    '/ui/ultra-chat/write-capability': () => ({ultra_chat_write: {available: true, header: S5_WRITE, token: 'W'.repeat(43)}}),
    [S5_TURN + '/latest']: () => ({turn: null, text: null}),
    ...routes,
  };
}
const offlineTurn = (body, state, extra = {}) => ({turn_id: 'turn_fixture', mode: 'TEST_OFFLINE', state,
  idempotency_key: body.idempotency_key, references: {model_ref: body.model_ref}, ...extra});

test('Stage 5 model choice applies to new requests and retry keeps the original key, text and model', async () => {
  const requests = [], routes = offlineRoutes({
    [S5_TURN]: opts => {
      const body = JSON.parse(opts.body);requests.push(body);
      if (requests.length === 1) throw Error('synthetic lost response');
      return offlineTurn(body, 'SUCCEEDED');
    },
  });
  const storage = new Map(), h = harness({routes, offline: true, storage});
  await settle();
  assert.equal(h.el('chatSend').disabled, false);
  assert.equal(h.el('viewOperator').hidden, true);
  assert.equal(h.el('viewEvm').hidden, true);
  h.el('chatInput').value = 'Первое сообщение';
  await h.el('chatSend').onclick();
  const pending = JSON.parse(storage.get(S5_SCOPE));
  assert.equal(pending.model, 'gigachat_2_pro');
  assert.equal(h.el('chatInput').readOnly, true);
  h.routes.set(S5_TURN + '/by-key/' + pending.key, () => ({httpError: true, status: 404, data: {error: {code: 'turn_not_found', message: 'not found'}}}));
  await h.el('chatModelPick').onclick();
  const options = h.el('chatModelMenu').children;
  assert.equal(options[1].getAttribute('role'), 'option');
  options[1].onclick();
  await h.el('chatSend').onclick();
  assert.deepEqual(requests[1], requests[0]);
  assert.equal(storage.has(S5_SCOPE), false);
  h.el('chatInput').value = 'Второе сообщение';
  await h.el('chatSend').onclick();
  assert.equal(requests[2].model_ref, 'gigachat_ultra');
  assert.notEqual(requests[2].idempotency_key, pending.key);
  assert.equal(h.calls.filter(c => c.url === S5_TURN).every(c => c.headers[S5_WRITE] === 'W'.repeat(43)), true);
  assert.equal(h.calls.some(c => c.url.startsWith('/ultra/connections') || c.url === '/workspaces'), false);
});

test('Stage 5 reopens durable UNKNOWN from the server without a new send', async () => {
  const body = {idempotency_key: 'fixture_key_00001', model_ref: 'gigachat_2_pro', text: 'Исходный текст'};
  const turn = offlineTurn(body, 'UNKNOWN', {usage: {total_tokens: 7}});
  const storage = new Map(), h = harness({offline: true, storage, routes: offlineRoutes({
    [S5_TURN + '/latest']: () => ({turn, text: body.text}),
    [S5_TURN + '/by-key/' + body.idempotency_key]: () => turn,
    [S5_TURN]: opts => {assert.deepEqual(JSON.parse(opts.body), body);return turn},
  })});
  await settle();
  assert.equal(h.calls.filter(c => c.url === S5_TURN).length, 0);
  assert.equal(h.el('chatInput').value, body.text);
  assert.equal(h.el('chatTurnCancel').disabled, true);
  assert.match(h.el('chatTurnStatus').textContent, /Исход неизвестен.*usage 7/);
  await h.el('chatSend').onclick();
  assert.equal(h.calls.filter(c => c.url === S5_TURN).length, 1);
  h.el('chatTurnNew').onclick();
  assert.equal(storage.has(S5_SCOPE), false);
  assert.equal(h.el('chatInput').readOnly, false);
});

test('Stage 5 Workspace creation sends a title to the TEST route without asking for a filesystem path', async () => {
  let created = false;
  const h = harness({offline: true, routes: offlineRoutes({
    '/ultra/chat/workspaces': opts => {
      if (opts.method === 'POST') {
        assert.deepEqual(JSON.parse(opts.body), {title: 'Synthetic TEST'});created = true;
        return {wa_workspace_id: 'ws_test', display_name: 'Synthetic TEST'};
      }
      return {state: 'ok', workspaces: created ? [ws('ws_test', 'Synthetic TEST', 'missing_history')] : []};
    },
    '/ultra/chat/workspaces/ws_test/chats': () => ({wa_workspace_id: 'ws_test', display_name: 'Synthetic TEST',
      state: 'unavailable', reason: 'missing_history', chats: [], excluded: {}}),
  })});
  await settle();
  await h.el('chatRegisterWorkspace').onclick();
  assert.equal(h.el('chatTestWorkspaceForm').hidden, false);
  h.el('chatTestWorkspaceTitle').value = 'Synthetic TEST';
  await h.el('chatTestWorkspaceForm').onsubmit({preventDefault: () => {}});
  assert.equal(created, true);
  assert.equal(h.el('chatNew').disabled, false);
  assert.equal(h.calls.some(c => c.url.includes('pick-workspace-folder')), false);
});

test('Stage 5 cancel stays accessible during send and late UNKNOWN never appears as success', async () => {
  let release, body, cancelled = false;
  const h = harness({offline: true, routes: offlineRoutes({
    [S5_TURN]: opts => {body = JSON.parse(opts.body);return new Promise(resolve => {release = resolve})},
    [S5_TURN + '/turn_fixture/cancel']: () => {cancelled = true;return offlineTurn(body, 'UNKNOWN')},
  })});
  await settle();
  h.el('chatInput').value = 'Отмена Web';
  const sending = h.el('chatSend').onclick();
  await settle();
  assert.equal(h.el('chatSend').disabled, true);
  assert.equal(h.el('chatTurnCancel').disabled, false);
  h.routes.set(S5_TURN + '/by-key/' + body.idempotency_key, () => offlineTurn(body, 'ATTEMPTING'));
  await h.el('chatTurnCancel').onclick();
  assert.equal(cancelled, true);
  assert.equal(h.el('chatTurnNew').disabled, true);
  release(offlineTurn(body, 'UNKNOWN', {usage: {total_tokens: 7}}));
  await sending;
  assert.match(h.el('chatTurnStatus').textContent, /Исход неизвестен.*usage 7/);
  assert.equal(h.el('chatTurnNew').disabled, false);
});

test('Workspace create uses native picker in Ultra Chat and registers folder with its name; never opens operator view', async () => {
  const h = harness({routes: {
    '/ui/capabilities': () => ({folder_picker: {available: true, token: 'P'.repeat(42)}}),
    '/ui/pick-workspace-folder': () => ({status: 'SELECTED', workspace_root: 'C:\\\\Synthetic\\\\Новая папка'}),
    '/workspaces': opts => ((opts.method || 'GET') === 'POST' ?
      {workspace: {workspace_id: 'ws_new', display_name: 'Новая папка', workspace_root: 'C:\\\\Synthetic\\\\Новая папка'}} :
      {workspaces: []}),
    '/ultra/chat/workspaces': () => ({state: 'ok', workspaces: [ws('ws_a', 'Проект А'), ws('ws_new', 'Новая папка')]}),
    '/ultra/chat/workspaces/ws_new/chats': () => ({wa_workspace_id: 'ws_new', display_name: 'Новая папка', state: 'unavailable', reason: 'missing_history', chats: [], excluded: {}})
  }}); await settle();
  await h.el('chatRegisterWorkspace').onclick(); await settle();
  assert.equal(h.el('layout').hidden, true);
  assert.equal(h.el('chatView').hidden, false);
  const posts = h.calls.filter(c => c.method === 'POST');
  assert.deepEqual(posts.map(p => p.url), ['/ui/pick-workspace-folder', '/workspaces']);
  assert.equal(posts[0].headers['X-WebAlarm-Folder-Token'], 'P'.repeat(42));
  assert.equal(JSON.parse(posts[1].body).display_name, 'Новая папка');
  assert.equal(h.el('chatWorkspaceList').textContent.includes('Новая папка'), true);
  assert.equal(h.run('chat.workspace'), 'ws_new');
});

test('cancelled or unavailable folder picker does not register a workspace or reveal secret paths', async () => {
  const cancelled = harness({routes: {'/ui/capabilities': () => ({folder_picker: {available: true, token: 'P'.repeat(42)}}),
    '/ui/pick-workspace-folder': () => ({status: 'CANCELLED'})}}); await settle();
  await cancelled.el('chatRegisterWorkspace').onclick(); await settle();
  assert.equal(cancelled.calls.some(c => c.url === '/workspaces' && c.method === 'POST'), false);
  const absent = harness(); await settle();
  await absent.el('chatRegisterWorkspace').onclick(); await settle();
  assert.equal(absent.el('chatError').hidden, false);
  assert.equal(absent.calls.some(c => c.url === '/workspaces' && c.method === 'POST'), false);
});

test('Workspace selection nests chats under expanded group; clicking the current Workspace collapses it without clearing selection', async () => {
  const h = harness(); await settle();
  assert.equal(h.el('chatWorkspaceList').children.length, 2);
  const first = h.el('chatWorkspaceList').children[0];
  assert.equal(first.dataset.active, 'true');
  assert.equal(first.children.length, 2, 'row and nested chat panel');
  assert.equal(first.children[0].children[0].getAttribute('aria-expanded'), 'true');
  assert.match(first.textContent, /Первый диалог/);
  await first.children[0].children[0].onclick(); await settle();
  assert.equal(h.el('chatWorkspaceList').children[0].children.length, 1, 'collapsed: no chat panel');
  assert.equal(h.run('chat.workspace'), 'ws_a');
  await h.picks('chatWorkspaceList')[0].onclick(); await settle();
  assert.equal(h.el('chatWorkspaceList').children[0].children.length, 2);
  assert.equal(h.el('chatHistory').textContent.includes('ответ'), true);
});

test('a failed catalog request hides raw server details and can be retried', async () => {
  const url = '/ultra/chat/workspaces';
  const h = harness({routes: {[url]: () => ({httpError: true, status: 500,
    data: {error: {message: 'Internal path C:/synthetic/private'}}})}});
  await settle();
  assert.equal(h.el('chatError').hidden, false);
  assert.doesNotMatch(h.el('chatError').textContent, /synthetic\/private/);
  h.routes.delete(url);
  await h.el('chatRefresh').onclick(); await settle();
  assert.equal(h.el('chatError').hidden, true);
  assert.match(h.el('chatHistory').textContent, /привет/);
});

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

const testTurnCap=()=>({...cap(),turn_test:{available:true,mode:'TEST'}});
const testTurnResult=(key,state='SUCCEEDED')=>({mode:'TEST',turn_id:'turn_'+'a'.repeat(64),idempotency_key:key,state,answer:state==='SUCCEEDED'?'TEST: сообщение принято.':null});
test('S3 TEST composer sends one stable key on double click and renders a saved reply', async()=>{
  let release;
  const wait=new Promise(resolve=>release=resolve);
  const h=harness({routes:{'/ui/ultra-chat/capability':testTurnCap,
    '/ui/ultra-chat/write-capability':()=>({ultra_chat_write:{available:true,header:'X-WebAlarm-Ultra-Chat-Write-Token',token:'W'.repeat(43)}}),
    '/ultra/chat/workspaces/ws_a/chats/chat_a/turns':async opts=>{await wait;return testTurnResult(JSON.parse(opts.body).idempotency_key)}}});
  await settle();assert.equal(h.el('chatSend').disabled,false);assert.match(h.el('chatComposerNote').textContent,/TEST/);
  h.el('chatInput').value='<script>сырой текст</script>';
  const pending=h.el('chatSend').onclick();h.el('chatSend').onclick();await settle();
  assert.equal(h.calls.filter(c=>c.url.endsWith('/turns')).length,1);
  const stored=h.stored.filter(([key])=>key.startsWith('webAlarm.testTurn.'));
  assert.equal(stored.length,1);assert.equal(stored[0][1].includes('сырой'),false);assert.equal(stored[0][1].includes('token'),false);
  release();await pending;await settle();assert.equal(h.el('chatInput').value,'');assert.match(h.el('chatTurnStatus').textContent,/сохранён/);
});
test('S3 lost reply retains key across reload; GET restores result without POST',async()=>{
  const storage=new Map();let originalKey;
  const routes={'/ui/ultra-chat/capability':testTurnCap,
    '/ui/ultra-chat/write-capability':()=>({ultra_chat_write:{available:true,header:'X-WebAlarm-Ultra-Chat-Write-Token',token:'W'.repeat(43)}}),
    '/ultra/chat/workspaces/ws_a/chats/chat_a/turns':opts=>{originalKey=JSON.parse(opts.body).idempotency_key;throw Error('lost reply')}};
  const first=harness({routes,storage});await settle();first.el('chatInput').value='не хранить в браузере';await first.el('chatSend').onclick();await settle();
  assert.equal(JSON.parse(storage.get('webAlarm.testTurn.ws_a.chat_a')).key,originalKey);
  routes['/ultra/chat/workspaces/ws_a/chats/chat_a/turns/by-key/'+originalKey]=()=>testTurnResult(originalKey);
  const second=harness({routes,storage});await settle();
  assert.equal(second.calls.filter(c=>c.method==='POST').length,0);assert.match(second.el('chatTurnStatus').textContent,/сохранён/);
});
test('S3 unknown outcome is visible, Enter sends, Shift+Enter and IME do not send',async()=>{
  const h=harness({routes:{'/ui/ultra-chat/capability':testTurnCap,
    '/ui/ultra-chat/write-capability':()=>({ultra_chat_write:{available:true,header:'X-WebAlarm-Ultra-Chat-Write-Token',token:'W'.repeat(43)}}),
    '/ultra/chat/workspaces/ws_a/chats/chat_a/turns':opts=>testTurnResult(JSON.parse(opts.body).idempotency_key,'UNKNOWN')}});
  await settle();h.el('chatInput').value='текст';let prevented=false;
  await h.el('chatInput').onkeydown({key:'Enter',shiftKey:true,preventDefault:()=>prevented=true});
  await h.el('chatInput').onkeydown({key:'Enter',isComposing:true,preventDefault:()=>prevented=true});
  assert.equal(h.calls.filter(c=>c.method==='POST').length,0);
  await h.el('chatInput').onkeydown({key:'Enter',preventDefault:()=>prevented=true});await settle();
  assert.equal(prevented,true);assert.match(h.el('chatTurnStatus').textContent,/неизвестен/);assert.equal(h.el('chatTurnNew').hidden,false);
  h.el('chatTurnNew').onclick();assert.equal(h.run('turnPending()'),null);
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
  assert.match(h.el('chatNameError').textContent, /Не удалось подтвердить сохранение диалога/);
  assert.doesNotMatch(h.el('chatNameError').textContent, /Failed to fetch/);
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
  assert.deepEqual([h.el('chatNew').disabled, h.el('chatRename').disabled], [false, true], 'missing history permits only an explicit first create');
  h.el('chatRename').onclick();
  assert.equal(h.el('chatNameForm').hidden, true);
  h.el('chatNew').onclick();
  assert.equal(h.el('chatNameForm').hidden, false);
  h.el('chatNameCancel').onclick();
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

test('Workspace pencil renames registry display name via write token and keeps the Ultra history, never the real path', async () => {
  const store = [ws('ws_a', 'Проект А'), ws('ws_b', 'Проект Б')];
  const posts = [];
  const h = harness({routes: {
    '/ultra/chat/workspaces': () => ({state: 'ok', workspaces: store.map(w => ({...w}))}),
    '/ui/ultra-chat/write-capability': () => wcap(),
    '/ultra/chat/workspaces/ws_a/title': opts => {
      const body = JSON.parse(opts.body); posts.push({body, headers: opts.headers});
      if (store[0].display_name !== body.expected_title) return refused(409, 'workspace_title_changed');
      store[0].display_name = body.title; return {wa_workspace_id: 'ws_a', display_name: body.title};
    }
  }}); await settle();
  const pencil = h.el('chatWorkspaceList').children[0].children[0].children[1];
  assert.match(pencil.getAttribute('aria-label'), /Переименовать Workspace/);
  pencil.onclick(); await settle();
  h.el('chatWorkspaceNameInput').value = 'Новая метка';
  await h.el('chatWorkspaceNameForm').onsubmit({preventDefault() {}}); await settle();
  assert.deepEqual(posts[0].body, {title:'Новая метка', expected_title:'Проект А'});
  assert.equal(posts[0].headers[WHEADER], WTOKEN);
  assert.equal(posts[0].headers[HEADER], undefined);
  assert.match(h.el('chatWorkspaceList').textContent, /Новая метка/);
  assert.equal(h.run('chat.workspace'), 'ws_a');
  assert.match(h.el('chatHistory').textContent, /ответ/);
});

test('LIVE RED: a confirmed registration after collapse must not be reported as creation failure', async () => {
  let registered = false;
  const h = harness({routes: {
    '/ui/capabilities': () => ({folder_picker: {available: true, token: 'P'.repeat(42)}}),
    '/ui/pick-workspace-folder': () => ({status: 'SELECTED', workspace_root: 'C:\\Synthetic\\Empty'}),
    '/workspaces': opts => opts.method === 'POST' ? (registered = true, {workspace: {workspace_id: 'ws_new'}}) : {workspaces: []},
    '/ultra/chat/workspaces': () => ({state: 'ok', workspaces: [ws('ws_a', 'Проект А'), ...(registered ? [ws('ws_new', 'Empty', 'missing_history')] : [])]}),
    '/ultra/chat/workspaces/ws_new/chats': () => ({state: 'unavailable', reason: 'missing_history', chats: [], excluded: {}})
  }}); await settle();
  await h.picks('chatWorkspaceList')[0].onclick(); // collapse removes the current panel from the document
  await h.el('chatRegisterWorkspace').onclick(); await settle();
  assert.equal(registered, true);
  assert.equal(h.calls.filter(c => c.url === '/workspaces' && c.method === 'POST').length, 1);
  assert.doesNotMatch(h.el('chatError').textContent, /Не удалось создать Workspace/);
  assert.match(h.el('chatListState').textContent, /нет истории Ultra/);
  assert.doesNotMatch(h.el('chatWorkspaceList').textContent, /null/);
});

test('LIVE RED: collapse and refresh keep all four nested nodes connected; never append literal null', async () => {
  const h = harness(); await settle();
  await h.picks('chatWorkspaceList')[0].onclick();
  h.run('chat.expanded=chat.workspace;renderChatWorkspaces()');
  assert.doesNotMatch(h.el('chatWorkspaceList').textContent, /null/);
  for (const id of ['chatWorkspaceNameForm', 'chatListState', 'chatList', 'chatNameForm']) {
    assert.equal(h.context.document.getElementById(id), h.el(id), id + ' remains in the document');
  }
});

test('LIVE RED: both pencils open connected forms after collapsing and reopening the Workspace', async () => {
  const h = harness(); await settle();
  await h.picks('chatWorkspaceList')[0].onclick();
  // A direct refresh was another real entry point to the detached panel.
  await h.el('chatRefresh').onclick(); await settle();
  const pencil = h.el('chatWorkspaceList').children[0].children[0].children[1];
  pencil.onclick(); await settle();
  assert.equal(h.context.document.getElementById('chatWorkspaceNameInput'), h.el('chatWorkspaceNameInput'));
  assert.equal(h.el('chatWorkspaceNameForm').hidden, false);
  h.el('chatWorkspaceNameCancel').onclick();
  h.el('chatList').children[0].children[1].onclick(); await settle();
  assert.equal(h.context.document.getElementById('chatNameInput'), h.el('chatNameInput'));
  assert.equal(h.el('chatNameForm').hidden, false);
});

test('LIVE RED: a dialogue pencil selects its own history before renaming; no stale messages from another dialogue', async () => {
  const h = harness({routes: {
    '/ultra/chat/workspaces/ws_a/chats': () => ({state: 'ok', chats: [chatItem('chat_a', 'Первый'), chatItem('chat_b', 'Второй')], excluded: {}}),
    '/ultra/chat/workspaces/ws_a/chats/chat_b/messages?limit=50': () => page([msg(3, 'user', 'История второго', 'request')], {chat_id: 'chat_b', chat: {title: 'Второй'}})
  }}); await settle();
  await h.el('chatList').children[0].children[1].onclick(); await settle();
  assert.equal(h.run('chat.chat'), 'chat_a');
  assert.match(h.el('chatHistory').textContent, /привет/);
  assert.doesNotMatch(h.el('chatHistory').textContent, /История второго/);
  assert.equal(h.el('chatNameInput').value, 'Первый');
});

test('LIVE registration separates confirmation from catalog/list/history failure, rejection and an unknown POST outcome', async () => {
  for (const failure of ['catalog', 'list', 'history', 'rejected', 'lost', 'malformed']) {
    let posted = false;
    const h = harness({routes: {
      '/ui/capabilities': () => ({folder_picker: {available: true, token: 'P'.repeat(42)}}),
      '/ui/pick-workspace-folder': () => ({status: 'SELECTED', workspace_root: 'C:\\Synthetic\\Empty'}),
      '/workspaces': opts => {
        if (opts.method !== 'POST') return {workspaces: []};
        posted = true;
        if (failure === 'rejected') return refused(400, 'invalid_workspace');
        if (failure === 'lost') throw Error('private transport details');
        return failure === 'malformed' ? {} : {workspace: {workspace_id: 'ws_new'}};
      },
      '/ultra/chat/workspaces': () => posted && failure === 'catalog' ? refused(500, 'private catalog error') :
        {state: 'ok', workspaces: [ws('ws_a', 'Проект А'), ...(posted ? [ws('ws_new', 'Empty')] : [])]},
      '/ultra/chat/workspaces/ws_new/chats': () => failure === 'list' ? refused(500, 'private list error') :
        {state: 'ok', chats: [chatItem('chat_new', 'Новый')], excluded: {}},
      '/ultra/chat/workspaces/ws_new/chats/chat_new/messages?limit=50': () => refused(500, 'private history error')
    }}); await settle();
    await h.el('chatRegisterWorkspace').onclick(); await settle();
    assert.equal(h.calls.filter(c => c.url === '/workspaces' && c.method === 'POST').length, 1, failure);
    assert.equal(h.el('chatError').hidden, false, failure);
    assert.doesNotMatch(h.el('chatError').textContent, /Не удалось создать Workspace|private/, failure);
    if (['rejected', 'lost', 'malformed'].includes(failure)) {
      assert.match(h.el('chatError').textContent, failure === 'rejected' ? /отклонил регистрацию/ : /подтвердить регистрацию/, failure);
      assert.equal(h.el('chatWorkspaceResult').hidden, true);
    } else {
      assert.match(h.el('chatWorkspaceResult').textContent, /Workspace подключён/);
      assert.match(h.el('chatError').textContent, /загрузить данные/);
    }
    assert.equal(h.el('chatRegisterWorkspace').disabled, false);
  }
});

test('LIVE empty, single and multiple dialogue trees survive repeated collapse, refresh and Workspace switches', async () => {
  for (const count of [0, 1, 3]) {
    const items = Array.from({length: count}, (_, n) => chatItem('chat_' + n, 'Диалог ' + n));
    const h = harness({routes: {
      '/ultra/chat/workspaces/ws_a/chats': () => ({state: 'ok', chats: items, excluded: {}}),
      '/ultra/chat/workspaces/ws_b/chats': () => ({state: 'unavailable', reason: 'missing_history', chats: [], excluded: {}}),
      ...Object.fromEntries(items.map(c => ['/ultra/chat/workspaces/ws_a/chats/' + c.chat_id + '/messages?limit=50', () => page([])]))
    }}); await settle();
    for (let cycle = 0; cycle < 3; cycle++) {
      assert.equal(h.picks('chatList').length, count);
      await h.picks('chatWorkspaceList')[0].onclick();
      await h.el('chatRefresh').onclick(); await settle();
      assert.equal(h.picks('chatWorkspaceList')[0].getAttribute('aria-expanded'), 'false', 'refresh respects collapse');
      assert.equal(h.run('chat.workspace'), 'ws_a');
      await h.picks('chatWorkspaceList')[1].onclick(); await settle();
      assert.match(h.el('chatListState').textContent, /нет истории Ultra/);
      assert.equal(h.picks('chatList').length, 0);
      await h.picks('chatWorkspaceList')[0].onclick(); await settle();
      assert.equal(h.picks('chatWorkspaceList')[0].getAttribute('aria-current'), 'true');
      assert.doesNotMatch(h.el('chatWorkspaceList').textContent, /null|undefined/);
      for (const id of ['chatWorkspaceNameForm', 'chatListState', 'chatList', 'chatNameForm']) assert.ok(h.context.document.getElementById(id));
    }
  }
});

test('LIVE Workspace rename conflict refreshes the label and keeps the typed title for an explicit second Save', async () => {
  let title = 'Проект А';
  const posts = [];
  const h = harness({routes: {
    '/ui/ultra-chat/write-capability': () => wcap(),
    '/ultra/chat/workspaces': () => ({state: 'ok', workspaces: [ws('ws_a', title)]}),
    '/ultra/chat/workspaces/ws_a/title': opts => {
      const body = JSON.parse(opts.body); posts.push(body);
      if (posts.length === 1) {title = 'Из другого окна'; return refused(409, 'workspace_title_changed');}
      if (body.expected_title !== title) return refused(409, 'workspace_title_changed');
      title = body.title; return {wa_workspace_id: 'ws_a', display_name: title};
    }
  }}); await settle();
  h.el('chatWorkspaceList').children[0].children[0].children[1].onclick();
  h.el('chatWorkspaceNameInput').value = 'Моя метка';
  await h.el('chatWorkspaceNameForm').onsubmit({preventDefault() {}}); await settle();
  assert.equal(title, 'Из другого окна');
  assert.match(h.el('chatWorkspaceList').textContent, /Из другого окна/);
  assert.equal(h.el('chatWorkspaceNameInput').value, 'Моя метка');
  assert.equal(h.el('chatWorkspaceNameForm').hidden, false);
  assert.match(h.el('chatWorkspaceNameError').textContent, /Сохранить/);
  await h.el('chatWorkspaceNameForm').onsubmit({preventDefault() {}}); await settle();
  assert.equal(posts[1].expected_title, 'Из другого окна');
  assert.equal(title, 'Моя метка');
  assert.equal(h.el('chatWorkspaceName').textContent, 'Моя метка', 'the selected Workspace header refreshes too');
  assert.equal(h.el('chatWorkspaceNameForm').hidden, true);
  h.el('chatWorkspaceList').children[0].children[0].children[1].onclick();
  assert.equal(h.el('chatWorkspaceNameInput').value, 'Моя метка');
});

test('LIVE both rename forms keep server errors as safe text and can be cancelled and reopened', async () => {
  const h = harness({routes: {
    '/ui/ultra-chat/write-capability': () => wcap(),
    '/ultra/chat/workspaces/ws_a/title': () => refused(500, '<img src=x onerror=alert(1)>'),
    '/ultra/chat/workspaces/ws_a/chats/chat_a/title': () => refused(500, '<script>alert(1)</script>')
  }}); await settle();
  h.el('chatWorkspaceList').children[0].children[0].children[1].onclick();
  h.el('chatWorkspaceNameInput').value = '<b>Workspace</b>';
  await h.el('chatWorkspaceNameForm').onsubmit({preventDefault() {}}); await settle();
  assert.equal(h.el('chatWorkspaceNameForm').hidden, false);
  assert.equal(h.el('chatWorkspaceNameSave').disabled, false);
  assert.doesNotMatch(h.el('chatWorkspaceNameError').textContent, /<img|onerror/);
  h.el('chatWorkspaceNameCancel').onclick();
  await h.el('chatList').children[0].children[1].onclick();
  h.el('chatNameInput').value = '<b>Диалог</b>';
  await submit(h); await settle();
  assert.equal(h.el('chatNameForm').hidden, false);
  assert.equal(h.el('chatNameSave').disabled, false);
  assert.doesNotMatch(h.el('chatNameError').textContent, /<script/);
  h.el('chatNameCancel').onclick();
  await h.el('chatList').children[0].children[1].onclick();
  assert.equal(h.el('chatNameInput').value, 'Первый диалог');
  assert.ok(h.all().every(e => !('innerHTML' in e)));
});

test('LIVE a failed Workspace-conflict readback never claims the list was refreshed', async () => {
  let conflict = false;
  const h = harness({routes: {
    '/ui/ultra-chat/write-capability': () => wcap(),
    '/ultra/chat/workspaces': () => conflict ? refused(500, 'readback failed') : {state: 'ok', workspaces: [ws('ws_a', 'Проект А')]},
    '/ultra/chat/workspaces/ws_a/title': () => {conflict = true; return refused(409, 'workspace_title_changed');}
  }}); await settle();
  h.el('chatWorkspaceList').children[0].children[0].children[1].onclick();
  h.el('chatWorkspaceNameInput').value = 'Моя метка';
  await h.el('chatWorkspaceNameForm').onsubmit({preventDefault() {}}); await settle();
  assert.doesNotMatch(h.el('chatWorkspaceNameError').textContent, /Список обновлён/);
  assert.match(h.el('chatWorkspaceNameError').textContent, /не удалось|Не удалось/);
  assert.equal(h.el('chatWorkspaceNameInput').value, 'Моя метка');
  assert.equal(h.el('chatWorkspaceNameForm').hidden, false);
});

test('LIVE a late plus-click for another Workspace cannot open an editor in the new selection', async () => {
  let release;
  const delayed = new Promise(resolve => {release = resolve;});
  const h = harness({routes: {
    '/ultra/chat/workspaces/ws_b/chats': async () => {await delayed; return {state: 'ok', chats: [], excluded: {}};}
  }}); await settle();
  h.el('chatWorkspaceList').children[1].children[0].children[2].onclick(); await settle();
  await h.picks('chatWorkspaceList')[0].onclick(); await settle();
  release(); await settle();
  assert.equal(h.run('chat.workspace'), 'ws_a');
  assert.equal(h.el('chatNameForm').hidden, true, 'the delayed action belongs to ws_b only');
});

test('AMENDMENT first chat: missing_history allows plus, asks for explicit create, then refreshes identity and tree', async () => {
  const srv = chatServer([]);
  let initialized = false;
  const h = harness({routes: {
    '/ui/ultra-chat/write-capability': () => wcap(),
    '/ultra/chat/workspaces': () => ({state: 'ok', workspaces: [ws('ws_a', 'Новая папка', initialized ? 'ok' : 'missing_history')]}),
    [CHATS_A]: opts => {
      if (opts.method === 'POST') {initialized = true; return srv.route(opts);}
      return initialized ? srv.route(opts) : {state: 'unavailable', reason: 'missing_history', chats: [], excluded: {}};
    }
  }}); await settle();
  const plus = () => h.el('chatWorkspaceList').children[0].children[0].children[2];
  assert.equal(plus().disabled, false, 'a registered new folder must allow its first dialogue');
  await plus().onclick(); await settle();
  assert.equal(h.el('chatNameForm').hidden, false);
  assert.equal(h.el('chatInitializeNotice').hidden, false);
  assert.match(h.el('chatInitializeNotice').textContent, /хранилище Ultra.*создано|создано.*хранилище Ultra/);
  assert.match(h.el('chatNameSave').textContent, /Создать первый диалог/);
  assert.equal(h.calls.filter(c => c.method === 'POST').length, 0, 'opening the form never initializes');
  h.el('chatNameCancel').onclick();
  assert.equal(h.calls.filter(c => c.method === 'POST').length, 0, 'cancel never initializes');
  await plus().onclick(); await settle();
  h.routes.set(CHATS_A + '/' + h.run('chatEdit.pendingId') + '/messages?limit=50', () => page([]));
  await submit(h); await settle();
  assert.equal(srv.posts[0].body.initialize_workspace, true);
  assert.equal(srv.posts[0].headers[WHEADER], WTOKEN);
  assert.equal(srv.posts[0].headers[HEADER], undefined);
  assert.equal(h.run('chat.workspaces[0].history'), 'ok', 'catalog reread is required after initialization');
  assert.equal(h.run('chat.chat'), srv.chats[0].chat_id);
  assert.match(h.el('chatWorkspaceList').textContent, /Чат 1/);
  assert.equal(h.el('chatNameForm').hidden, true);
  assert.equal(h.el('chatError').hidden, true);
  assert.equal(plus().disabled, false);
  await plus().onclick(); await settle();
  assert.equal(h.el('chatInitializeNotice').hidden, true);
  await submit(h); await settle();
  assert.equal(srv.posts[1].body.initialize_workspace, undefined, 'ordinary creates keep the existing strict path');
  assert.equal(srv.chats.length, 2);
  assert.doesNotMatch(h.el('chatWorkspaceList').textContent, /nullnull/);
});

test('AMENDMENT first chat: only ok and missing_history enable creation; unsafe states remain read-only', async () => {
  for (const history of ['missing_path', 'not_directory', 'invalid_metadata', 'unsupported_version', 'unsafe_storage_link', 'unreadable', 'foreign_identity']) {
    const h = harness({routes: {
      '/ultra/chat/workspaces': () => ({state: 'ok', workspaces: [ws('ws_a', 'Недоступный', history)]}),
      [CHATS_A]: () => ({state: 'unavailable', reason: history, chats: [], excluded: {}})
    }}); await settle();
    assert.equal(h.el('chatWorkspaceList').children[0].children[0].children[2].disabled, true, history);
    await h.picks('chatWorkspaceList')[0].onclick(); await settle();
    h.el('chatNew').onclick();
    assert.equal(h.el('chatNameForm').hidden, true, history);
    assert.equal(h.calls.filter(c => c.method === 'POST').length, 0, history);
  }
});

test('AMENDMENT first chat: a lost reply keeps the pending id and consent; retry creates no second dialogue', async () => {
  const srv = chatServer([]);
  let initialized = false, posts = 0;
  const h = harness({routes: {
    '/ui/ultra-chat/write-capability': () => wcap(),
    '/ultra/chat/workspaces': () => ({state: 'ok', workspaces: [ws('ws_a', 'Новая папка', initialized ? 'ok' : 'missing_history')]}),
    [CHATS_A]: opts => {
      if (opts.method === 'POST') {
        initialized = true;
        const result = srv.route(opts);
        if (++posts === 1) throw Error('lost reply');
        return result;
      }
      return initialized ? srv.route(opts) : {state: 'unavailable', reason: 'missing_history', chats: [], excluded: {}};
    }
  }}); await settle();
  h.el('chatWorkspaceList').children[0].children[0].children[2].onclick(); await settle();
  const id = h.run('chatEdit.pendingId');
  h.routes.set(CHATS_A + '/' + id + '/messages?limit=50', () => page([]));
  await submit(h); await settle();
  assert.match(h.el('chatNameError').textContent, /Не удалось подтвердить/);
  assert.equal(h.el('chatNameForm').hidden, false);
  assert.equal(srv.chats.length, 1);
  await submit(h); await settle();
  assert.equal(srv.posts.length, 2);
  assert.equal(srv.posts[0].body.chat_id, id);
  assert.equal(srv.posts[1].body.chat_id, id);
  assert.equal(srv.posts[0].body.initialize_workspace, true);
  assert.equal(srv.posts[1].body.initialize_workspace, true);
  assert.equal(srv.chats.length, 1);
  assert.equal(h.run('chat.workspaces[0].history'), 'ok');
  assert.equal(h.el('chatNameForm').hidden, true);
  assert.equal(h.el('chatError').hidden, true);
});
