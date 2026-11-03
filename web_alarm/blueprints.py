"""Versioned LLM blueprint definitions and a pure, explicitly synthetic preview.

No provider, agent, file tool, Chat, Turn or RUN is executed by this module.
Targets are references to Ultra's existing catalogue, never copies of its models.
The future execution service consumes an immutable invocation contract, not UI state.
"""
from __future__ import annotations

import copy
import json
import math
import os
import re
import secrets
import stat
import uuid
from pathlib import Path
from typing import Any

from .store_lock import InterProcessLock, StoreLockTimeout

CAPABILITY_PATH = "/ui/blueprints/capability"
TOKEN_HEADER = "X-WebAlarm-Blueprint-Token"
MAX_BYTES = 512 * 1024
MAX_NODES, MAX_EDGES, MAX_PORTS, MAX_DEFINITIONS = 128, 512, 64, 200
ID = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,79}$")
BLUEPRINT_ID = re.compile(r"^bp_[a-f0-9]{32}$")
TYPES = ("text", "context", "json", "artifact", "event")
ROLE_PRESETS = ("Собеседник", "Планировщик", "Исполнитель", "Проверяющий", "Редактор", "Аналитик")
DEFAULT_PORTS = [
    {"id": "task", "label": "Задача", "direction": "input", "type": "text", "multiple": False, "required": True},
    {"id": "context", "label": "Контекст", "direction": "input", "type": "context", "multiple": True, "required": False},
    {"id": "prior", "label": "Ответ другой LLM", "direction": "input", "type": "text", "multiple": True, "required": False},
    {"id": "data", "label": "Данные / код", "direction": "input", "type": "json", "multiple": False, "required": False},
    {"id": "result", "label": "Результат", "direction": "output", "type": "text", "multiple": False, "required": False},
    {"id": "context_out", "label": "Новый контекст", "direction": "output", "type": "context", "multiple": True, "required": False},
    {"id": "artifacts", "label": "Артефакты", "direction": "output", "type": "artifact", "multiple": True, "required": False},
    {"id": "done", "label": "Завершение", "direction": "output", "type": "event", "multiple": False, "required": False},
    {"id": "error", "label": "Ошибка", "direction": "output", "type": "event", "multiple": False, "required": False},
]


class BlueprintError(Exception):
    def __init__(self, status: int, code: str, message: str, **details: Any):
        self.status, self.code, self.message, self.details = status, code, message, details
        super().__init__(message)


def _bad(message: str) -> None:
    raise BlueprintError(400, "invalid_blueprint", message)


def _object(value: Any, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        _bad(f"{label}: неверный набор полей.")
    return value


def _text(value: Any, limit: int, label: str, *, empty: bool = True) -> str:
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()) or "\x00" in value:
        _bad(f"{label}: требуется текст длиной до {limit} символов.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        _bad(f"{label}: недопустимая последовательность Unicode.")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        _bad(f"{label}: недопустимый идентификатор.")
    return value


def _number(value: Any, low: float, high: float, label: str, *, integer: bool = False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high
            or not math.isfinite(value) or (integer and not isinstance(value, int))):
        _bad(f"{label}: допустимый диапазон {low}–{high}.")
    return value


def definition(value: Any) -> dict:
    """Validate the versioned data boundary. Incomplete drafts can be saved."""
    _object(value, {"schema_version", "blueprint_id", "name", "nodes", "edges", "output_node_id"}, "Схема")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        _bad("Версия схемы не поддерживается.")
    if not isinstance(value["blueprint_id"], str) or not BLUEPRINT_ID.fullmatch(value["blueprint_id"]):
        _bad("Неверный ID схемы.")
    _text(value["name"], 120, "Название схемы", empty=False)
    if not isinstance(value["nodes"], list) or len(value["nodes"]) > MAX_NODES:
        _bad(f"Допустимо до {MAX_NODES} блоков.")
    if not isinstance(value["edges"], list) or len(value["edges"]) > MAX_EDGES:
        _bad(f"Допустимо до {MAX_EDGES} связей.")
    node_ids = set()
    for node in value["nodes"]:
        _object(node, {"id", "kind", "title", "position", "executor_ref", "role", "instruction", "input_text",
                       "context_text", "context_refs", "parameters", "ports"}, "Блок")
        nid = _id(node["id"], "ID блока")
        if nid in node_ids or node["kind"] != "llm":
            _bad("ID блоков должны быть уникальны; поддерживается один тип llm.")
        node_ids.add(nid)
        for field, limit in (("title", 100), ("role", 100), ("instruction", 8000), ("input_text", 8000), ("context_text", 8000)):
            _text(node[field], limit, field, empty=field not in {"title", "role"})
        if node["executor_ref"] is not None:
            ref = _text(node["executor_ref"], 200, "Исполнитель", empty=False)
            if not re.fullmatch(r"[a-zA-Z0-9_:.-]+", ref):
                _bad("Исполнитель задаётся ссылкой каталога, а не адресом сервера.")
        _object(node["position"], {"x", "y"}, "Положение")
        for axis in ("x", "y"):
            _number(node["position"][axis], 0, 20000, axis)
        _object(node["parameters"], {"temperature", "max_output_tokens"}, "Параметры")
        _number(node["parameters"]["temperature"], 0, 2, "Температура")
        _number(node["parameters"]["max_output_tokens"], 1, 32768, "Лимит ответа", integer=True)
        refs = node["context_refs"]
        if not isinstance(refs, list) or len(refs) > 32:
            _bad("Допустимо до 32 ссылок на контекст.")
        for ref in refs:
            _text(ref, 200, "Ссылка на контекст", empty=False)
            if not re.fullmatch(r"[a-z][a-z0-9_]*:[a-zA-Z0-9_.:-]+", ref):
                _bad("Контекст: используйте ссылку вида project:context_id; пути и URL не допускаются.")
        if not isinstance(node["ports"], list) or not 1 <= len(node["ports"]) <= MAX_PORTS:
            _bad(f"В блоке должно быть от 1 до {MAX_PORTS} пинов.")
        port_ids = set()
        for port in node["ports"]:
            _object(port, {"id", "label", "direction", "type", "multiple", "required"}, "Пин")
            pid = _id(port["id"], "ID пина")
            if pid in port_ids or port["direction"] not in ("input", "output") or port["type"] not in TYPES:
                _bad("Повторный ID, неизвестное направление или тип пина.")
            port_ids.add(pid)
            _text(port["label"], 80, "Название пина", empty=False)
            if type(port["multiple"]) is not bool or type(port["required"]) is not bool:
                _bad("multiple и required должны быть логическими значениями.")
    edge_ids = set()
    for edge in value["edges"]:
        _object(edge, {"id", "source", "source_port", "target", "target_port"}, "Связь")
        for key in edge:
            _id(edge[key], key)
        if edge["id"] in edge_ids:
            _bad("ID связей должны быть уникальны.")
        edge_ids.add(edge["id"])
    if value["output_node_id"] is not None:
        _id(value["output_node_id"], "Финальный блок")
    if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > MAX_BYTES - 4096:
        _bad("Схема превышает допустимый размер.")
    return copy.deepcopy(value)


def validate_graph(graph: dict, targets: dict[str, dict]) -> dict:
    """Validate wiring independently of any model's answer or browser checks."""
    errors, warnings = [], []
    nodes = {n["id"]: n for n in graph["nodes"]}
    ports = {nid: {p["id"]: p for p in n["ports"]} for nid, n in nodes.items()}
    incoming, adjacent, seen = {}, {nid: set() for nid in nodes}, set()

    def issue(bucket, code, message, **refs):
        bucket.append({"code": code, "message": message, **refs})

    for edge in graph["edges"]:
        src, dst = edge["source"], edge["target"]
        a, b = ports.get(src, {}).get(edge["source_port"]), ports.get(dst, {}).get(edge["target_port"])
        if a is None or b is None:
            issue(errors, "dangling_edge", "Связь ссылается на отсутствующий блок или пин.", edge_id=edge["id"])
            continue
        signature = (src, a["id"], dst, b["id"])
        if signature in seen:
            issue(errors, "duplicate_edge", "Эта связь уже существует.", edge_id=edge["id"])
        seen.add(signature)
        if a["direction"] != "output" or b["direction"] != "input" or a["type"] != b["type"]:
            issue(errors, "incompatible_ports", "Соедините выход и вход одного типа.", edge_id=edge["id"])
        incoming.setdefault((dst, b["id"]), []).append(edge)
        if len(incoming[(dst, b["id"])]) > 1 and not b["multiple"]:
            issue(errors, "input_cardinality", "Вход принимает только один источник.", edge_id=edge["id"])
        adjacent[src].add(dst)
    indegree = {nid: 0 for nid in nodes}
    for successors in adjacent.values():
        for nid in successors:
            indegree[nid] += 1
    ready, order = [nid for nid in nodes if indegree[nid] == 0], []
    while ready:
        nid = ready.pop(0)
        order.append(nid)
        for successor in sorted(adjacent[nid]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
    if len(order) != len(nodes):
        issue(errors, "cycle", "Циклы пока не поддерживаются. Удалите обратную связь.")
    output = graph["output_node_id"]
    if output is not None and output not in nodes:
        issue(errors, "missing_output", "Финальный блок отсутствует.")
    if not nodes:
        issue(warnings, "empty_graph", "Добавьте первый LLM-блок.")
    if nodes and output is None:
        issue(warnings, "no_output", "Выберите блок, ответ которого попадёт в чат.")
    for nid, node in nodes.items():
        target = targets.get(node["executor_ref"])
        if not target or not target.get("selectable"):
            issue(warnings, "executor_unavailable", f"{node['title']}: выберите доступного исполнителя.", node_id=nid)
        elif target.get("verification") == "UNVERIFIED":
            issue(warnings, "executor_unverified", f"{node['title']}: модель есть в реестре, реальный вызов не подтверждён.", node_id=nid)
        if node["context_refs"]:
            issue(warnings, "context_unresolved", f"{node['title']}: ссылки на контекст сохранены; чтение источников ещё не подключено.", node_id=nid)
        for port in node["ports"]:
            if port["direction"] == "input" and port["required"] and (nid, port["id"]) not in incoming:
                if port["id"] != "task" or port["type"] != "text":
                    issue(warnings, "required_input", f"{node['title']}: подключите вход «{port['label']}».", node_id=nid)
    return {"valid": not errors, "errors": errors, "warnings": warnings, "order": order,
            "execution_available": False, "mode": "design", "network_calls": 0}


def preview(graph: dict, prompt: str, targets: dict[str, dict]) -> dict:
    """Bounded data-flow example, not a second execution engine or chat history."""
    validation = validate_graph(graph, targets)
    if not validation["valid"] or not graph["nodes"] or graph["output_node_id"] is None:
        raise BlueprintError(422, "preview_invalid", "Для предпросмотра нужна корректная схема и финальный блок.", validation=validation)
    if any(w["code"] == "required_input" for w in validation["warnings"]):
        raise BlueprintError(422, "preview_missing_input", "Подключите обязательные входы.", validation=validation)
    _text(prompt, 8000, "Пример вопроса", empty=False)
    nodes, outputs, trace = {n["id"]: n for n in graph["nodes"]}, {}, []
    for nid in validation["order"]:
        node = nodes[nid]
        inputs = []
        for edge in graph["edges"]:
            if edge["target"] == nid:
                source_port = next(p for p in nodes[edge["source"]]["ports"] if p["id"] == edge["source_port"])
                inputs.append({"pin": edge["target_port"], "type": source_port["type"],
                               "source_node_id": edge["source"], "source_port_id": edge["source_port"],
                               "sample": outputs[(edge["source"], edge["source_port"])]})
        task = node["input_text"] or prompt
        bound = next((i for i in inputs if i["pin"] == "task"), None)
        if bound:
            task = str(bound["sample"])
        result = f"[Имитация] {node['title']} · {node['role']}\nВопрос: {task[:200]}\nПолучено связей: {len(inputs)}. Это пример передачи данных, не ответ нейросети."
        for port in node["ports"]:
            if port["direction"] != "output":
                continue
            samples = {"text": result, "context": {"producer_node_id": nid, "text": node["context_text"][:400], "synthetic": True},
                       "json": {"synthetic": True, "producer_node_id": nid}, "artifact": [],
                       "event": {"synthetic": True, "event": "not_emitted" if port["id"] == "error" else "preview_completed"}}
            outputs[(nid, port["id"])] = samples[port["type"]]
        trace.append({"node_id": nid, "title": node["title"], "role": node["role"], "executor_ref": node["executor_ref"],
                      "task": task[:1000], "task_truncated": len(task) > 1000, "inputs": inputs,
                      "context_sample": node["context_text"][:1000], "context_truncated": len(node["context_text"]) > 1000,
                      "context_refs_resolved": False, "result": result})
    final = next(row["result"] for row in trace if row["node_id"] == graph["output_node_id"])
    return {"mode": "simulation", "execution": False, "network_calls": 0, "persisted": False,
            "validation": validation, "trace": trace, "answer": final}


def _is_link(st) -> bool:
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


class BlueprintService:
    """One definition store, protected by revision CAS and the existing OS lock."""
    def __init__(self, storage_root: Path, connections):
        self.root = Path(storage_root).resolve()
        self.connections = connections
        self.token = secrets.token_urlsafe(32)

    def capability(self) -> dict:
        return {"available": True, "token": self.token, "header": TOKEN_HEADER,
                "scope": "blueprint_design", "execution_available": False}

    def require(self, headers) -> None:
        values = headers.get_all(TOKEN_HEADER, [])
        if (len(values) != 1 or not values[0].isascii() or len(values[0]) > 200
                or not secrets.compare_digest(values[0], self.token)):
            raise BlueprintError(403, "blueprint_token_invalid", "Обновите доступ к редактору.")

    def catalog(self) -> dict:
        catalog = self.connections.catalog()
        targets = [entry for column in catalog["columns"].values() for entry in column.get("connections", [])]
        return {"targets": targets, "source": "model_registry", "roles": list(ROLE_PRESETS), "types": list(TYPES),
                "default_ports": copy.deepcopy(DEFAULT_PORTS), "execution_available": False,
                "network_calls": 0, "limits": {"nodes": MAX_NODES, "edges": MAX_EDGES, "ports": MAX_PORTS}}

    def _directory(self, parts: tuple[str, ...], create=False) -> Path:
        current = self.root
        if create:
            current.mkdir(parents=True, exist_ok=True)
        for component in parts:
            current = current / component
            if create:
                current.mkdir(exist_ok=True)
            try:
                st = current.lstat()
            except FileNotFoundError:
                return current.joinpath(*parts[len(current.relative_to(self.root).parts):])
            if _is_link(st) or not stat.S_ISDIR(st.st_mode):
                raise BlueprintError(409, "unsafe_blueprint_storage", "Каталог схем недоступен: обнаружена ссылка или неверный тип.")
        return current

    def _path(self, bid: str) -> Path:
        if not BLUEPRINT_ID.fullmatch(bid):
            _bad("Неверный ID схемы.")
        return self._directory(("ultra", "blueprints")) / (bid + ".json")

    def _read(self, bid: str) -> dict | None:
        path = self._path(bid)
        try:
            st = path.lstat()
        except FileNotFoundError:
            return None
        if _is_link(st) or not stat.S_ISREG(st.st_mode) or st.st_size > MAX_BYTES:
            raise BlueprintError(409, "unsafe_blueprint_storage", "Файл схемы имеет недопустимый тип или размер.")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (st.st_dev, st.st_ino):
                raise BlueprintError(409, "blueprint_storage_changed", "Файл изменился во время чтения.")
            raw = stream.read(MAX_BYTES + 1)
        try:
            if len(raw) > MAX_BYTES:
                raise ValueError()
            record = json.loads(raw)
            _object(record, {"revision", "definition"}, "Запись схемы")
            _number(record["revision"], 1, 2**53 - 1, "Ревизия", integer=True)
            definition(record["definition"])
            if record["definition"]["blueprint_id"] != bid:
                raise ValueError()
        except (ValueError, BlueprintError):
            raise BlueprintError(409, "blueprint_storage_corrupt", "Сохранённая схема повреждена; файл оставлен без изменений.") from None
        return record

    def list(self) -> dict:
        directory = self._directory(("ultra", "blueprints"))
        items, damaged = [], []
        if directory.is_dir():
            for entry in directory.iterdir():
                if entry.suffix != ".json" or not BLUEPRINT_ID.fullmatch(entry.stem):
                    continue
                if len(items) + len(damaged) >= MAX_DEFINITIONS:
                    raise BlueprintError(409, "blueprint_catalog_too_large", "Превышен размер каталога схем.")
                try:
                    record = self._read(entry.stem)
                    if record:
                        g = record["definition"]
                        items.append({"blueprint_id": entry.stem, "name": g["name"], "revision": record["revision"], "nodes": len(g["nodes"])})
                except BlueprintError as exc:
                    damaged.append({"blueprint_id": entry.stem, "code": exc.code})
        return {"items": sorted(items, key=lambda x: (x["name"].casefold(), x["blueprint_id"])), "damaged": damaged}

    def save(self, bid: str, payload: Any) -> dict:
        _object(payload, {"expected_revision", "definition"}, "Сохранение")
        expected = _number(payload["expected_revision"], 0, 2**53 - 1, "Ревизия", integer=True)
        graph = definition(payload["definition"])
        if graph["blueprint_id"] != bid:
            _bad("ID маршрута и схемы не совпадают.")
        check = validate_graph(graph, {})
        if not check["valid"]:
            raise BlueprintError(422, "invalid_connections", "Исправьте связи перед сохранением.", validation=check)
        lock_dir = self._directory(("locks", "ultra"), create=True)
        lock_path = lock_dir / "blueprints.lock"
        try:
            lock_stat = lock_path.lstat()
        except FileNotFoundError:
            lock_stat = None
        if lock_stat and (_is_link(lock_stat) or not stat.S_ISREG(lock_stat.st_mode)):
            raise BlueprintError(409, "unsafe_blueprint_storage", "Недопустимый файл блокировки.")
        try:
            with InterProcessLock(lock_path):
                current = self._read(bid)
                revision = current["revision"] if current else 0
                if current and current["definition"] == graph and expected <= revision:
                    return current
                if expected != revision:
                    raise BlueprintError(409, "blueprint_revision_conflict", "Схема изменена в другом окне. Сохраните копию или загрузите свежую версию.", current_revision=revision)
                if current is None:
                    catalog = self.list()
                    if len(catalog["items"]) + len(catalog["damaged"]) >= MAX_DEFINITIONS:
                        raise BlueprintError(409, "blueprint_catalog_full", "Каталог схем заполнен.")
                directory = self._directory(("ultra", "blueprints"), create=True)
                path = directory / (bid + ".json")
                record = {"revision": revision + 1, "definition": graph}
                raw = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                if len(raw) > MAX_BYTES:
                    _bad("Схема превышает допустимый размер.")
                temporary = directory / ("." + uuid.uuid4().hex + ".tmp")
                try:
                    with temporary.open("xb") as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    self._directory(("ultra", "blueprints"))
                    os.replace(temporary, path)
                finally:
                    temporary.unlink(missing_ok=True)
                return record
        except StoreLockTimeout:
            raise BlueprintError(409, "blueprint_busy", "Хранилище занято. Повторите сохранение.") from None

    def request(self, method: str, path: str, payload: Any = None) -> dict:
        if path == "/ultra/blueprints/catalog" and method == "GET":
            return self.catalog()
        if path == "/ultra/blueprints" and method == "GET":
            return self.list()
        if path in {"/ultra/blueprints/validate", "/ultra/blueprints/preview"} and method == "POST":
            fields = {"definition", "prompt"} if path.endswith("preview") else {"definition"}
            _object(payload, fields, "Запрос")
            graph = definition(payload["definition"])
            targets = {x["connection_id"]: x for x in self.catalog()["targets"]}
            return preview(graph, payload["prompt"], targets) if path.endswith("preview") else validate_graph(graph, targets)
        bid = path.removeprefix("/ultra/blueprints/")
        if path.startswith("/ultra/blueprints/") and BLUEPRINT_ID.fullmatch(bid):
            if method == "GET":
                record = self._read(bid)
                if record is None:
                    raise BlueprintError(404, "blueprint_not_found", "Схема не найдена.")
                return record
            if method == "PUT":
                return self.save(bid, payload)
        raise BlueprintError(405, "blueprint_route_unavailable", "Маршрут или метод редактора не поддерживается.")
