/* Universal LLM node editor. All saved data and wiring are validated by Ultra.
 * Preview is synthetic and transient; it never submits a provider call or a Chat turn. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const root = $('blueprintView');
  if (!root) return;
  const clone = value => JSON.parse(JSON.stringify(value));
  const id = prefix => prefix + '_' + crypto.randomUUID().replaceAll('-', '');
  const colors = {text: '#70ccdf', context: '#b59aef', json: '#e3bd74', artifact: '#ed9dc0', event: '#94aabc'};
  const typeNames = {text: 'Текст', context: 'Контекст', json: 'Данные / JSON', artifact: 'Артефакт', event: 'Событие'};
  const state = {graph: null, revision: 0, dirty: false, selected: null, edge: null, pending: null,
    catalog: null, list: [], drafts: new Map(), saved: new Map(), token: null, cap: null,
    initializing: null, initialized: false, saving: false, previewing: false, epoch: 0,
    pan: {x: 38, y: 40}, zoom: 1, gesture: null, wireFrame: 0, previewNodes: new Set()};

  function el(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function option(value, label, disabled = false) {
    const o = el('option', label); o.value = value; o.disabled = disabled; return o;
  }
  function notice(message = '', error = false) {
    $('bpNotice').textContent = message; $('bpNotice').hidden = !message; $('bpNotice').dataset.error = String(error);
  }
  function report(error) { notice(error.message || 'Не удалось выполнить действие.', true); }
  async function capability() {
    if (!state.cap) state.cap = fetch('/ui/blueprints/capability', {cache: 'no-store', credentials: 'same-origin'})
      .then(async response => {
        const data = await response.json();
        if (!response.ok || !data.blueprints?.available || !data.blueprints.token) throw Error(data.error?.message || 'Редактор недоступен на этом сервере.');
        state.token = data.blueprints.token;
      }).catch(error => { state.cap = null; throw error; });
    await state.cap;
  }
  async function api(path, method = 'GET', data, retry = true) {
    await capability();
    const headers = {'X-WebAlarm-Blueprint-Token': state.token};
    const args = {method, headers, cache: 'no-store', credentials: 'same-origin'};
    if (data !== undefined) { headers['Content-Type'] = 'application/json'; args.body = JSON.stringify(data); }
    const response = await fetch(path, args);
    const result = await response.json();
    if (!response.ok) {
      if (result.error?.code === 'blueprint_token_invalid' && retry) {
        state.cap = null; state.token = null; return api(path, method, data, false);
      }
      const error = Error(result.error?.message || 'Ошибка редактора.');
      error.code = result.error?.code; error.details = result.error?.details; throw error;
    }
    return result;
  }
  function rememberDraft() {
    if (!state.graph) return;
    state.drafts.set(state.graph.blueprint_id, {definition: clone(state.graph), revision: state.revision});
  }
  function changed() {
    state.dirty = state.saved.get(state.graph.blueprint_id) !== JSON.stringify(state.graph);
    state.previewNodes.clear(); state.epoch++;
    $('bpValidationCount').textContent = '';
    $('bpValidationList').replaceChildren(el('p', 'Схема изменена. Проверка относится к предыдущей версии.', 'bp-muted'));
    rememberDraft(); updateSaveState(); renderSchemes(); updateStats();
  }
  function updateSaveState() {
    $('bpSaveState').textContent = state.saving ? 'Сохраняем…' : state.dirty ? 'Есть изменения' : 'Сохранено · v' + state.revision;
    $('bpSaveState').dataset.dirty = String(state.dirty);
    $('bpSave').disabled = state.saving || !state.graph;
    $('bpSaveCopy').disabled = state.saving || !state.graph;
  }
  function updateStats() {
    $('bpGraphStats').textContent = `${state.graph.nodes.length} блоков · ${state.graph.edges.length} связей`;
    $('bpEmpty').hidden = state.graph.nodes.length > 0;
    $('bpPreviewSend').disabled = state.previewing || !state.graph.nodes.length;
  }
  function selectedNode() { return state.graph?.nodes.find(n => n.id === state.selected); }
  function target(ref) { return state.catalog?.targets.find(t => t.connection_id === ref); }
  function targetLabel(ref) {
    const item = target(ref);
    return item ? `${item.display_name} · ${item.provider}` : ref ? 'Подключение недоступно' : 'Выберите исполнителя';
  }
  function makeNode(position, role = 'Собеседник') {
    return {id: id('node'), kind: 'llm', title: 'LLM-блок ' + (state.graph.nodes.length + 1), position,
      executor_ref: state.catalog.targets.find(t => t.selected && t.selectable)?.connection_id || null,
      role, instruction: '', input_text: '', context_text: '', context_refs: [],
      parameters: {temperature: 0.7, max_output_tokens: 2048}, ports: clone(state.catalog.default_ports)};
  }
  function resetPreview() {
    state.previewNodes.clear();
    $('bpMessages').replaceChildren(el('p', 'Проверьте передачу вопроса и контекста. Предпросмотр использует демонстрационные ответы и не вызывает нейросети.', 'bp-preview-intro'));
  }
  function adopt(record, fromServer = false) {
    state.graph = clone(record.definition); state.revision = record.revision; state.selected = null;
    state.edge = null; state.pending = null; state.epoch++; state.pan = {x: 38, y: 40}; state.zoom = 1;
    if (fromServer) state.saved.set(state.graph.blueprint_id, JSON.stringify(state.graph));
    state.dirty = state.saved.get(state.graph.blueprint_id) !== JSON.stringify(state.graph);
    $('bpName').value = state.graph.name; $('bpReload').hidden = true;
    resetPreview(); notice(); renderAll();
    $('bpValidationCount').textContent = '';
    $('bpValidationList').replaceChildren(el('p', 'Нажмите «Проверить схему».', 'bp-muted'));
    try { localStorage.setItem('webAlarm.blueprint.selection', state.graph.blueprint_id); } catch (_) {}
    requestAnimationFrame(fit);
  }
  function newGraph(example = false) {
    rememberDraft();
    adopt({revision: 0, definition: {schema_version: 1, blueprint_id: id('bp'), name: example ? 'Решение и проверка' : 'Новая схема', nodes: [], edges: [], output_node_id: null}});
    if (example) {
      const a = makeNode({x: 0, y: 30}, 'Аналитик'); a.title = 'Подготовить решение';
      a.instruction = 'Проанализируй задачу и предложи обоснованное решение.';
      state.graph.nodes.push(a);
      const b = makeNode({x: 345, y: 90}, 'Проверяющий'); b.title = 'Проверить результат';
      b.instruction = 'Проверь полученный ответ, укажи ошибки и сформулируй итог.';
      state.graph.nodes.push(b); state.graph.output_node_id = b.id;
      state.graph.edges.push({id: id('edge'), source: a.id, source_port: 'result', target: b.id, target_port: 'prior'});
      state.selected = a.id;
    }
    changed(); renderAll(); requestAnimationFrame(fit);
  }
  async function loadGraph(bid, discard = false) {
    rememberDraft();
    try {
      const cached = !discard && state.drafts.get(bid);
      const record = cached || await api('/ultra/blueprints/' + encodeURIComponent(bid));
      adopt(record, !cached);
    } catch (error) { report(error); }
  }
  async function refreshList() {
    const response = await api('/ultra/blueprints'); state.list = response.items; renderSchemes();
    if (response.damaged.length) notice(`Не удалось прочитать схем: ${response.damaged.length}. Повреждённые файлы сохранены.`, true);
  }
  function renderSchemes() {
    const list = $('bpSchemes'); list.replaceChildren();
    const records = new Map(state.list.map(row => [row.blueprint_id, row]));
    for (const [bid, draft] of state.drafts) records.set(bid, {blueprint_id: bid, name: draft.definition.name, nodes: draft.definition.nodes.length, revision: draft.revision});
    if (state.graph) records.set(state.graph.blueprint_id, {blueprint_id: state.graph.blueprint_id, name: state.graph.name, nodes: state.graph.nodes.length, revision: state.revision});
    for (const record of records.values()) {
      const button = el('button', undefined, 'bp-scheme' + (record.blueprint_id === state.graph?.blueprint_id ? ' active' : ''));
      button.type = 'button'; button.append(el('strong', record.name), el('small', `${record.nodes} блоков · ${record.revision ? 'v' + record.revision : 'черновик'}`));
      button.title = record.name; button.onclick = () => loadGraph(record.blueprint_id); list.append(button);
    }
    if (!records.size) list.append(el('p', 'Пока нет сохранённых схем', 'bp-muted'));
  }
  async function save(asCopy = false) {
    if (!state.graph || state.saving) return;
    if (asCopy) {
      rememberDraft(); const definition = clone(state.graph); definition.blueprint_id = id('bp');
      definition.name = (definition.name + ' — копия').slice(0, 120);
      adopt({definition, revision: 0}); changed();
    }
    const snapshot = clone(state.graph), bid = snapshot.blueprint_id, revision = state.revision;
    state.saving = true; updateSaveState(); notice();
    try {
      const saved = await api('/ultra/blueprints/' + bid, 'PUT', {expected_revision: revision, definition: snapshot});
      state.saved.set(bid, JSON.stringify(snapshot));
      const draft = state.drafts.get(bid);
      if (draft) draft.revision = saved.revision;
      if (state.graph.blueprint_id === bid) {
        state.revision = saved.revision; state.dirty = JSON.stringify(state.graph) !== JSON.stringify(snapshot);
        rememberDraft(); $('bpReload').hidden = true;
        notice(state.dirty ? 'Версия сохранена. Более поздние изменения ещё не сохранены.' : 'Схема сохранена.');
      }
      await refreshList();
    } catch (error) {
      if (error.code === 'blueprint_revision_conflict') $('bpReload').hidden = false;
      if (error.details?.validation) showValidation(error.details.validation);
      report(error);
    } finally { state.saving = false; updateSaveState(); }
  }
  function showValidation(result) {
    const list = $('bpValidationList'); list.replaceChildren();
    $('bpValidationCount').textContent = `(${result.errors.length} / ${result.warnings.length})`;
    list.append(el('p', result.valid ? 'Связи и структура схемы корректны.' : 'В схеме есть ошибки.', result.valid ? 'bp-ok' : 'bp-error'));
    for (const issue of [...result.errors, ...result.warnings]) {
      const paragraph = el('p', issue.message, result.errors.includes(issue) ? 'bp-error' : '');
      if (issue.node_id) { paragraph.style.cursor = 'pointer'; paragraph.onclick = () => selectNode(issue.node_id); }
      list.append(paragraph);
    }
    list.append(el('p', 'Реальное выполнение будет доступно после подключения общего сервиса Ultra. Проверка схемы не подтверждает работу модели.', 'bp-muted'));
    $('bpValidationPanel').open = true;
  }
  async function validate() {
    if (!state.graph) return;
    const snapshot = clone(state.graph), epoch = state.epoch;
    $('bpValidate').disabled = true;
    try {
      const result = await api('/ultra/blueprints/validate', 'POST', {definition: snapshot});
      if (epoch !== state.epoch) { notice('Схема изменилась во время проверки. Проверьте новую версию.'); return; }
      showValidation(result); notice(result.valid ? 'Структура проверена. Замечания — в диагностике справа.' : 'Исправьте ошибки связей.', !result.valid);
    } catch (error) { report(error); } finally { $('bpValidate').disabled = false; }
  }

  function transform() {
    $('bpStage').style.transform = `translate(${state.pan.x}px,${state.pan.y}px) scale(${state.zoom})`;
    $('bpCanvas').style.backgroundSize = `${24 * state.zoom}px ${24 * state.zoom}px`;
    $('bpCanvas').style.backgroundPosition = `${state.pan.x}px ${state.pan.y}px`;
    $('bpZoomLabel').textContent = Math.round(state.zoom * 100) + '%';
  }
  function world(clientX, clientY) {
    const rect = $('bpCanvas').getBoundingClientRect();
    return {x: (clientX - rect.left - state.pan.x) / state.zoom, y: (clientY - rect.top - state.pan.y) / state.zoom};
  }
  function setZoom(zoom, x, y) {
    const canvas = $('bpCanvas').getBoundingClientRect();
    x ??= canvas.left + canvas.width / 2; y ??= canvas.top + canvas.height / 2;
    const before = world(x, y); state.zoom = Math.min(1.7, Math.max(0.25, zoom));
    state.pan.x = x - canvas.left - before.x * state.zoom; state.pan.y = y - canvas.top - before.y * state.zoom;
    transform(); drawSoon();
  }
  function fit() {
    if (!state.graph || root.hidden) return;
    if (!state.graph.nodes.length) { state.zoom = 1; state.pan = {x: 38, y: 40}; transform(); return; }
    const nodes = state.graph.nodes;
    const minX = Math.min(...nodes.map(n => n.position.x)), minY = Math.min(...nodes.map(n => n.position.y));
    const maxX = Math.max(...nodes.map(n => n.position.x + 258));
    const maxY = Math.max(...nodes.map(n => n.position.y + ($('bpCard_' + n.id)?.offsetHeight || 300)));
    const canvas = $('bpCanvas');
    state.zoom = Math.min(1, Math.max(0.25, Math.min((canvas.clientWidth - 80) / (maxX - minX), (canvas.clientHeight - 65) / (maxY - minY))));
    state.pan = {x: (canvas.clientWidth - (maxX - minX) * state.zoom) / 2 - minX * state.zoom,
      y: Math.max(24, (canvas.clientHeight - (maxY - minY) * state.zoom) / 2) - minY * state.zoom};
    transform(); drawSoon();
  }
  function portElement(node, port) { return $('bpPin_' + node + '_' + port); }
  function endpoint(node, port) {
    const pin = portElement(node, port)?.querySelector('.bp-dot'); if (!pin) return null;
    const r = pin.getBoundingClientRect(); return world(r.left + r.width / 2, r.top + r.height / 2);
  }
  function curve(a, b) {
    const bend = Math.max(65, Math.min(200, Math.abs(b.x - a.x) * 0.5));
    return `M ${a.x} ${a.y} C ${a.x + bend} ${a.y}, ${b.x - bend} ${b.y}, ${b.x} ${b.y}`;
  }
  function svgPath(d, className) {
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path'); p.setAttribute('d', d); p.setAttribute('class', className); return p;
  }
  function drawSoon() {
    if (!state.wireFrame) state.wireFrame = requestAnimationFrame(() => { state.wireFrame = 0; drawWires(); });
  }
  function drawWires() {
    const svg = $('bpWires'); svg.replaceChildren(); if (!state.graph) return;
    for (const edge of state.graph.edges) {
      const a = endpoint(edge.source, edge.source_port), b = endpoint(edge.target, edge.target_port); if (!a || !b) continue;
      const p = state.graph.nodes.find(n => n.id === edge.source)?.ports.find(p => p.id === edge.source_port);
      const line = svgPath(curve(a, b), 'bp-wire' + (p?.type === 'event' ? ' event' : '') + (state.edge === edge.id ? ' selected' : ''));
      line.style.stroke = colors[p?.type] || colors.text;
      const hit = svgPath(curve(a, b), 'bp-wire-hit'); hit.dataset.edge = edge.id;
      hit.addEventListener('pointerdown', e => { e.stopPropagation(); state.edge = edge.id; state.selected = null; state.pending = null; renderNodes(); renderInspector(); drawSoon(); });
      svg.append(line, hit);
    }
    if (state.pending) {
      const a = endpoint(state.pending.node, state.pending.port);
      if (a) svg.append(svgPath(curve(a, state.pending.point || {x: a.x + 100, y: a.y}), 'bp-wire-pending'));
    }
  }
  function nodePort(node, port) {
    const button = el('button', undefined, 'bp-port ' + port.direction);
    button.type = 'button'; button.id = 'bpPin_' + node.id + '_' + port.id;
    button.dataset.node = node.id; button.dataset.port = port.id; button.dataset.direction = port.direction;
    button.setAttribute('aria-label', `${node.title}: ${port.direction === 'input' ? 'вход' : 'выход'} ${port.label}, ${typeNames[port.type]}`);
    button.title = typeNames[port.type] + (port.required ? ' · обязательный' : '') + (port.multiple ? ' · несколько значений' : '');
    const dot = el('span', undefined, 'bp-dot'); dot.dataset.type = port.type;
    button.append(dot, el('span', port.label, 'bp-port-label'));
    const linked = state.graph.edges.some(e => port.direction === 'output' ? e.source === node.id && e.source_port === port.id : e.target === node.id && e.target_port === port.id);
    button.classList.toggle('connected', linked); button.classList.toggle('pending', state.pending?.node === node.id && state.pending?.port === port.id);
    button.onpointerdown = e => {
      e.stopPropagation();
      if (port.direction === 'output') {
        state.pending = {node: node.id, port: port.id, type: port.type, point: world(e.clientX, e.clientY)};
        state.gesture = {kind: 'wire', pointer: e.pointerId}; updateConnectionHint(); drawSoon();
      }
    };
    button.onclick = e => {
      e.stopPropagation();
      if (port.direction === 'input') connect(node.id, port.id);
      else if (!state.pending) { state.pending = {node: node.id, port: port.id, type: port.type}; updateConnectionHint(); drawSoon(); }
    };
    return button;
  }
  function renderNodes() {
    const container = $('bpNodes'); container.replaceChildren(); if (!state.graph) return;
    state.graph.nodes.forEach((node, index) => {
      const card = el('div', undefined, 'bp-node' + (state.selected === node.id ? ' selected' : ''));
      card.id = 'bpCard_' + node.id; card.dataset.node = node.id;
      card.style.left = node.position.x + 'px'; card.style.top = node.position.y + 'px';
      card.addEventListener('pointerdown', e => {
        e.stopPropagation();
        if (e.target.closest('.bp-port')) return;
        if (state.selected !== node.id) { state.selected = node.id; state.edge = null; updateCardSelection(); renderInspector(); }
      });
      const head = el('div', undefined, 'bp-node-head');
      head.append(el('span', '✦', 'bp-node-icon'), el('span', node.title, 'bp-node-title'), el('span', String(index + 1).padStart(2, '0'), 'bp-node-order'));
      head.onpointerdown = e => {
        if (e.button !== 0) return; e.stopPropagation(); e.preventDefault();
        state.selected = node.id; state.edge = null; updateCardSelection(); renderInspector();
        state.gesture = {kind: 'node', pointer: e.pointerId, node: node.id, start: world(e.clientX, e.clientY), position: {...node.position}, moved: false};
        head.setPointerCapture(e.pointerId);
      };
      const model = el('div', targetLabel(node.executor_ref), 'bp-node-model'); model.title = targetLabel(node.executor_ref);
      const role = el('select', undefined, 'bp-node-role'); role.setAttribute('aria-label', 'Роль блока ' + node.title);
      for (const label of new Set([...state.catalog.roles, node.role])) role.append(option(label, label));
      role.value = node.role; role.onchange = () => { node.role = role.value; changed(); if (state.selected === node.id) renderInspector(); };
      const pins = el('div', undefined, 'bp-node-ports');
      const inputs = node.ports.filter(p => p.direction === 'input'), outputs = node.ports.filter(p => p.direction === 'output');
      for (let i = 0; i < Math.max(inputs.length, outputs.length); i++) {
        const row = el('div', undefined, 'bp-port-row');
        row.append(inputs[i] ? nodePort(node, inputs[i]) : el('span'), outputs[i] ? nodePort(node, outputs[i]) : el('span')); pins.append(row);
      }
      const foot = el('div', undefined, 'bp-node-foot');
      foot.append(el('span', state.previewNodes.has(node.id) ? '◇ Предпросмотр пройден' : '○ Настроен для схемы', 'bp-node-state'));
      if (state.graph.output_node_id === node.id) foot.append(el('span', '↗ Итог в чат', 'bp-node-final'));
      card.append(head, model, role, pins, foot); container.append(card);
    });
    updateConnectionHint(); drawSoon();
  }
  function updateCardSelection() {
    for (const card of $('bpNodes').children) card.classList.toggle('selected', card.dataset.node === state.selected);
    drawSoon();
  }
  function updateConnectionHint() {
    $('bpConnectHint').textContent = state.pending ? `Выберите вход: ${typeNames[state.pending.type]} · Esc — отмена` : 'Выход → вход одного типа';
  }
  function selectNode(nid) { state.selected = nid; state.edge = null; renderNodes(); renderInspector(); }
  function renderInspector() {
    const node = selectedNode();
    $('bpInspector').hidden = !node; $('bpInspectorEmpty').hidden = Boolean(node || state.edge); $('bpEdgeInspector').hidden = !state.edge;
    $('bpInspectorNumber').textContent = node ? String(state.graph.nodes.indexOf(node) + 1).padStart(2, '0') : '—';
    if (state.edge) {
      const edge = state.graph.edges.find(e => e.id === state.edge);
      $('bpEdgeDescription').textContent = edge ? edgeDescription(edge) : '';
    }
    if (!node) return;
    $('bpNodeTitle').value = node.title; $('bpRole').value = node.role; $('bpInstruction').value = node.instruction;
    $('bpInput').value = node.input_text; $('bpContext').value = node.context_text; $('bpContextRefs').value = node.context_refs.join('\n');
    $('bpTemperature').value = node.parameters.temperature; $('bpMaxTokens').value = node.parameters.max_output_tokens;
    $('bpFinal').checked = state.graph.output_node_id === node.id;
    const picker = $('bpExecutor'); picker.replaceChildren(option('', 'Выберите исполнителя…'));
    for (const item of state.catalog.targets) picker.append(option(item.connection_id, `${item.display_name} · ${item.provider}`, !item.selectable));
    if (node.executor_ref && !target(node.executor_ref)) picker.append(option(node.executor_ref, 'Недоступно: ' + node.executor_ref, true));
    picker.value = node.executor_ref || '';
    const item = target(node.executor_ref);
    $('bpExecutorStatus').textContent = item ? (item.selectable ? 'Из общего реестра Ultra. Доступность вызова не подтверждена.' : 'Модель отключена в общем реестре.') : 'Подключения берутся из EVM. Новые локальные модели появятся после подключения их адаптеров.';
    renderPortList(node); renderLinks(node);
  }
  function renderPortList(node) {
    const list = $('bpPortList'); list.replaceChildren();
    for (const port of node.ports) {
      const row = el('div', undefined, 'bp-port-entry'); const dot = el('span', undefined, 'bp-dot'); dot.dataset.type = port.type;
      row.append(dot, el('span', `${port.direction === 'input' ? '→' : '←'} ${port.label}`));
      const remove = el('button', '×'); remove.type = 'button'; remove.title = 'Удалить пин и связанные линии';
      remove.setAttribute('aria-label', 'Удалить пин ' + port.label);
      remove.onclick = () => {
        if (node.ports.length === 1) { notice('В блоке должен остаться хотя бы один пин.', true); return; }
        node.ports = node.ports.filter(p => p.id !== port.id);
        state.graph.edges = state.graph.edges.filter(e => !(e.source === node.id && e.source_port === port.id) && !(e.target === node.id && e.target_port === port.id));
        state.pending = null; changed(); renderNodes(); renderInspector();
      };
      row.append(remove); list.append(row);
    }
  }
  function edgeDescription(edge) {
    const a = state.graph.nodes.find(n => n.id === edge.source), b = state.graph.nodes.find(n => n.id === edge.target);
    return `${a?.title || '?'} · ${a?.ports.find(p => p.id === edge.source_port)?.label || '?'} → ${b?.title || '?'} · ${b?.ports.find(p => p.id === edge.target_port)?.label || '?'}`;
  }
  function renderLinks(node) {
    const list = $('bpLinkList'); list.replaceChildren();
    const edges = state.graph.edges.filter(e => e.source === node.id || e.target === node.id);
    if (!edges.length) list.append(el('p', 'Соедините выход блока со входом другого блока.', 'bp-muted'));
    for (const edge of edges) {
      const row = el('div', undefined, 'bp-link-row'), remove = el('button', '×'); remove.type = 'button';
      remove.title = 'Удалить связь'; remove.setAttribute('aria-label', 'Удалить связь ' + edgeDescription(edge));
      remove.onclick = () => deleteEdge(edge.id); row.append(el('span', edgeDescription(edge)), remove); list.append(row);
    }
  }
  function renderAll() { renderSchemes(); renderNodes(); renderInspector(); updateStats(); updateSaveState(); transform(); }
  function addNode() {
    if (!state.catalog || !state.graph) return;
    if (state.graph.nodes.length >= state.catalog.limits.nodes) { notice('Достигнут лимит блоков одной схемы.', true); return; }
    const canvas = $('bpCanvas').getBoundingClientRect(); const center = world(canvas.left + canvas.width * 0.35, canvas.top + canvas.height * 0.25);
    const node = makeNode({x: Math.min(20000, Math.max(0, Math.round(center.x))), y: Math.min(20000, Math.max(0, Math.round(center.y)))});
    if (state.graph.nodes.some(n => Math.abs(n.position.x - node.position.x) < 30 && Math.abs(n.position.y - node.position.y) < 30)) {
      node.position.x = Math.min(20000, node.position.x + 40); node.position.y = Math.min(20000, node.position.y + 45);
    }
    state.graph.nodes.push(node); if (!state.graph.output_node_id) state.graph.output_node_id = node.id;
    state.selected = node.id; state.edge = null; changed(); renderAll();
  }
  function duplicate() {
    const source = selectedNode(); if (!source) return;
    if (state.graph.nodes.length >= state.catalog.limits.nodes) { notice('Достигнут лимит блоков.', true); return; }
    const node = clone(source); node.id = id('node'); node.title = (node.title + ' — копия').slice(0, 100);
    node.position = {x: Math.min(20000, source.position.x + 55), y: Math.min(20000, source.position.y + 70)};
    state.graph.nodes.push(node); state.selected = node.id; changed(); renderAll();
  }
  function deleteNode() {
    if (!state.selected) return;
    const nid = state.selected; state.graph.nodes = state.graph.nodes.filter(n => n.id !== nid);
    state.graph.edges = state.graph.edges.filter(e => e.source !== nid && e.target !== nid);
    if (state.graph.output_node_id === nid) state.graph.output_node_id = null;
    state.selected = null; state.pending = null; changed(); renderAll();
  }
  function deleteEdge(eid = state.edge) {
    if (!eid) return; state.graph.edges = state.graph.edges.filter(e => e.id !== eid); state.edge = null; changed(); renderAll();
  }
  function connect(nid, pid) {
    const pending = state.pending; if (!pending) { notice('Сначала выберите выход другого блока.'); return; }
    const node = state.graph.nodes.find(n => n.id === nid), pin = node?.ports.find(p => p.id === pid);
    let error = '';
    if (pending.node === nid) error = 'Нельзя связать блок с самим собой.';
    else if (!pin || pin.direction !== 'input' || pin.type !== pending.type) error = 'Соедините выход и вход одного типа.';
    else if (state.graph.edges.some(e => e.source === pending.node && e.source_port === pending.port && e.target === nid && e.target_port === pid)) error = 'Эта связь уже существует.';
    else if (!pin.multiple && state.graph.edges.some(e => e.target === nid && e.target_port === pid)) error = 'У этого входа уже есть источник. Сначала удалите прежнюю связь.';
    else if (state.graph.edges.length >= state.catalog.limits.edges) error = 'Достигнут лимит связей.';
    const visit = (current, seen = new Set()) => {
      if (current === pending.node) return true;
      if (seen.has(current)) return false; seen.add(current);
      return state.graph.edges.filter(e => e.source === current).some(e => visit(e.target, seen));
    };
    if (!error && visit(nid)) error = 'Такая связь создаёт цикл. Циклы пока не поддерживаются.';
    if (error) { notice(error, true); return; }
    state.graph.edges.push({id: id('edge'), source: pending.node, source_port: pending.port, target: nid, target_port: pid});
    state.pending = null; changed(); notice('Связь добавлена.'); renderNodes(); renderInspector();
  }
  function edit(field, value) {
    const node = selectedNode(); if (!node) return; node[field] = value; changed(); renderNodes();
  }
  function message(label, text, kind = '') {
    const div = el('div', undefined, 'bp-message ' + kind); div.append(el('span', label, 'bp-message-label'), el('div', text));
    $('bpMessages').append(div); return div;
  }
  async function runPreview(event) {
    event.preventDefault(); if (!state.graph || state.previewing) return;
    const prompt = $('bpPrompt').value.trim(); if (!prompt) { $('bpPrompt').focus(); return; }
    const snapshot = clone(state.graph), epoch = state.epoch;
    state.previewing = true; updateStats(); notice();
    try {
      const response = await api('/ultra/blueprints/preview', 'POST', {definition: snapshot, prompt});
      if (epoch !== state.epoch) { notice('Схема изменилась. Запустите предпросмотр для новой версии.'); return; }
      if ($('bpMessages').querySelector('.bp-preview-intro')) $('bpMessages').replaceChildren();
      message('ВАШ ПРИМЕР ВОПРОСА', prompt, 'user');
      const reply = message('ДЕМОНСТРАЦИЯ · БЕЗ ВЫЗОВА LLM', response.answer);
      const details = el('details'); details.append(el('summary', `Передача данных · ${response.trace.length} блоков`));
      for (const row of response.trace) {
        details.append(el('strong', `${row.title} · ${row.role}`));
        details.append(el('pre', `Задача: ${row.task}${row.task_truncated ? '\n[Фрагмент сокращён]' : ''}\nКонтекст: ${row.context_sample || '—'}${row.context_truncated ? '\n[Фрагмент сокращён]' : ''}\nВходящие связи: ${row.inputs.length}`));
        for (const input of row.inputs) details.append(el('pre', `→ ${input.pin} (${typeNames[input.type]})\n${typeof input.sample === 'string' ? input.sample : JSON.stringify(input.sample, null, 2)}`));
      }
      reply.append(details);
      while ($('bpMessages').children.length > 12) $('bpMessages').firstElementChild.remove();
      $('bpMessages').scrollTop = $('bpMessages').scrollHeight;
      state.previewNodes = new Set(response.trace.map(row => row.node_id)); renderNodes(); showValidation(response.validation);
      notice('Предпросмотр завершён. Запросов к моделям: 0. В историю Ultra Chat ничего не записано.');
    } catch (error) { if (error.details?.validation) showValidation(error.details.validation); report(error); }
    finally { state.previewing = false; updateStats(); }
  }
  async function open() {
    if (state.initialized) { drawSoon(); return; }
    if (state.initializing) return state.initializing;
    $('bpAdd').disabled = true; $('bpExample').disabled = true; $('bpEmptyAdd').disabled = true;
    state.initializing = (async () => {
      try {
        const [catalog, list] = await Promise.all([api('/ultra/blueprints/catalog'), api('/ultra/blueprints')]);
        state.catalog = catalog; state.list = list.items;
        $('bpRoles').replaceChildren(...catalog.roles.map(role => option(role, role)));
        let last = null; try { last = localStorage.getItem('webAlarm.blueprint.selection'); } catch (_) {}
        const selected = state.list.find(row => row.blueprint_id === last) || state.list[0];
        if (selected) {
          const record = await api('/ultra/blueprints/' + selected.blueprint_id); adopt(record, true);
        } else newGraph();
        state.initialized = true;
        if (list.damaged.length) notice(`Повреждённых схем: ${list.damaged.length}. Они оставлены без изменений.`, true);
      } catch (error) { report(error); }
      finally {
        state.initializing = null;
        $('bpAdd').disabled = !state.initialized; $('bpExample').disabled = !state.initialized; $('bpEmptyAdd').disabled = !state.initialized;
      }
    })();
    return state.initializing;
  }

  // Listeners are scoped to this editor; they do not change Ultra's global model assignments.
  $('bpAdd').onclick = addNode; $('bpEmptyAdd').onclick = addNode;
  $('bpNew').onclick = () => { if (state.catalog) newGraph(); else open(); };
  $('bpExample').onclick = () => newGraph(true); $('bpDuplicate').onclick = duplicate;
  $('bpDelete').onclick = deleteNode; $('bpDeleteEdge').onclick = () => deleteEdge();
  $('bpSave').onclick = () => save(); $('bpSaveCopy').onclick = () => save(true);
  $('bpReload').onclick = () => loadGraph(state.graph.blueprint_id, true);
  $('bpValidate').onclick = validate; $('bpFit').onclick = fit;
  $('bpZoomIn').onclick = () => setZoom(state.zoom * 1.2); $('bpZoomOut').onclick = () => setZoom(state.zoom / 1.2);
  $('bpName').oninput = () => { if (state.graph) { state.graph.name = $('bpName').value; changed(); } };
  for (const [control, field] of [['bpNodeTitle', 'title'], ['bpRole', 'role'], ['bpInstruction', 'instruction'], ['bpInput', 'input_text'], ['bpContext', 'context_text']]) {
    $(control).oninput = () => edit(field, $(control).value);
  }
  $('bpExecutor').onchange = () => { edit('executor_ref', $('bpExecutor').value || null); renderInspector(); };
  $('bpContextRefs').oninput = () => edit('context_refs', $('bpContextRefs').value.split('\n').map(v => v.trim()).filter(Boolean));
  $('bpFinal').onchange = () => { state.graph.output_node_id = $('bpFinal').checked ? state.selected : null; changed(); renderNodes(); };
  for (const [control, key] of [['bpTemperature', 'temperature'], ['bpMaxTokens', 'max_output_tokens']]) {
    $(control).onchange = () => { const node = selectedNode(); if (node) { node.parameters[key] = $(control).valueAsNumber; changed(); } };
  }
  $('bpPortAdd').onclick = () => {
    const node = selectedNode(), label = $('bpPortLabel').value.trim(); if (!node || !label) return;
    if (node.ports.length >= state.catalog.limits.ports) { notice('Достигнут лимит пинов блока.', true); return; }
    node.ports.push({id: id('p'), label, direction: $('bpPortDirection').value, type: $('bpPortType').value,
      multiple: $('bpPortMultiple').checked, required: $('bpPortDirection').value === 'input' && $('bpPortRequired').checked});
    $('bpPortLabel').value = ''; changed(); renderNodes(); renderPortList(node);
  };
  $('bpPreviewForm').onsubmit = runPreview;
  $('bpPrompt').onkeydown = event => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) runPreview(event); };
  $('bpPreviewToggle').onclick = () => {
    const body = $('bpPreviewBody'); body.hidden = !body.hidden;
    $('bpPreviewToggle').setAttribute('aria-expanded', String(!body.hidden)); $('bpPreviewToggle').textContent = body.hidden ? '⌃' : '⌄'; drawSoon();
  };
  $('bpCanvas').onpointerdown = event => {
    if (event.button !== 0 || event.target.closest('.bp-node') || event.target.closest('[data-edge]')) return;
    state.gesture = {kind: 'pan', pointer: event.pointerId, x: event.clientX, y: event.clientY, pan: {...state.pan}, moved: false};
    $('bpCanvas').setPointerCapture(event.pointerId); event.preventDefault();
  };
  $('bpCanvas').addEventListener('wheel', event => {
    if (event.ctrlKey || event.metaKey) { event.preventDefault(); setZoom(state.zoom * Math.exp(-event.deltaY * 0.002), event.clientX, event.clientY); }
  }, {passive: false});
  window.addEventListener('pointermove', event => {
    if (root.hidden) return;
    const gesture = state.gesture;
    if (state.pending) { state.pending.point = world(event.clientX, event.clientY); drawSoon(); }
    if (!gesture || gesture.pointer !== event.pointerId) return;
    if (gesture.kind === 'node') {
      const node = state.graph.nodes.find(n => n.id === gesture.node); if (!node) return;
      const point = world(event.clientX, event.clientY);
      node.position = {x: Math.min(20000, Math.max(0, Math.round(gesture.position.x + point.x - gesture.start.x))),
        y: Math.min(20000, Math.max(0, Math.round(gesture.position.y + point.y - gesture.start.y)))};
      gesture.moved ||= node.position.x !== gesture.position.x || node.position.y !== gesture.position.y;
      const card = $('bpCard_' + node.id); card.style.left = node.position.x + 'px'; card.style.top = node.position.y + 'px'; drawSoon();
    } else if (gesture.kind === 'pan') {
      const dx = event.clientX - gesture.x, dy = event.clientY - gesture.y;
      gesture.moved ||= Math.abs(dx) + Math.abs(dy) > 4;
      state.pan = {x: gesture.pan.x + dx, y: gesture.pan.y + dy}; transform();
    }
  });
  function endGesture(event) {
    const gesture = state.gesture; if (!gesture || gesture.pointer !== event.pointerId) return;
    state.gesture = null;
    if (gesture.kind === 'node' && gesture.moved) changed();
    if (gesture.kind === 'pan' && !gesture.moved) { state.selected = null; state.edge = null; state.pending = null; renderNodes(); renderInspector(); }
    if (gesture.kind === 'wire') {
      const drop = document.elementFromPoint(event.clientX, event.clientY)?.closest('.bp-port.input');
      if (drop) { connect(drop.dataset.node, drop.dataset.port); event.preventDefault(); }
    }
  }
  window.addEventListener('pointerup', endGesture);
  window.addEventListener('pointercancel', event => { if (state.gesture?.kind === 'node' && state.gesture.moved) changed(); state.gesture = null; state.pending = null; updateConnectionHint(); drawSoon(); });
  window.addEventListener('keydown', event => {
    if (root.hidden || !state.graph) return;
    if (event.key === 'Escape') { state.pending = null; state.gesture = null; updateConnectionHint(); drawSoon(); return; }
    if (event.target.closest('input,textarea,select,[contenteditable=true]')) return;
    if (event.key === 'Delete' || event.key === 'Backspace') { event.preventDefault(); if (state.edge) deleteEdge(); else deleteNode(); }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'd') { event.preventDefault(); duplicate(); }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); save(); }
  });
  window.addEventListener('beforeunload', event => {
    rememberDraft();
    if ([...state.drafts].some(([bid, record]) => state.saved.get(bid) !== JSON.stringify(record.definition))) { event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('resize', drawSoon);
  window.UltraBlueprint = {open};
  if (!root.hidden) open();
})();
