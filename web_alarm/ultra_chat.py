"""Ultra Chat for the web shell: read access (programme No.37 stage 1) and Chat create/rename (stage 2).

A thin adapter. Workspace roots come from the Web Alarm registry (no second registration); the Ultra identity, the
chats and every RAW message are read through the bounded functions of the shared core ``context_storage`` (no
``ensure_*``, no second copy of the storage format). Private history needs its own capability, ``ultra_chat_read``,
which does not depend on the Windows folder picker. Stage 2 writes only through the shared writer contract of the
core (Workspace lock, identity, ownership, exclusive publication) and only behind a second, separate capability,
``ultra_chat_write``: the read token never authorises a write. A write goes only to a registered Workspace whose
Ultra history already exists - nothing is created for an unregistered path or a folder without history. Nothing
here imports the GigaChat transport, the Tk shell or the agent runtime, and no response carries a filesystem path.
"""

from __future__ import annotations

import json
import re
import secrets
from typing import Any, Callable, Mapping

from .workspace_registry import WorkspaceRegistry, WorkspaceRegistryError

ULTRA_CHAT_CAPABILITY_PATH = "/ui/ultra-chat/capability"
ULTRA_CHAT_TOKEN_HEADER = "X-WebAlarm-Ultra-Chat-Token"
ULTRA_CHAT_WRITE_CAPABILITY_PATH = "/ui/ultra-chat/write-capability"
ULTRA_CHAT_WRITE_TOKEN_HEADER = "X-WebAlarm-Ultra-Chat-Write-Token"
MAX_WRITE_BODY_BYTES = 4096
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
MAX_PAGE_BYTES = 8 * 1024 * 1024
MAX_RUN_INDEX_BYTES = 8 * 1024 * 1024
MAX_INDEX_GENERATIONS = 4096
MAX_WORKSPACES = 500
# Exact prefix written by ultra_ui._format_terminal_worker_failure for a failed Tk run (TASK 147B).
LEGACY_FAILURE_PREFIX = "RUN STATUS: FAILED\n"

_WA_WORKSPACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_CHAT_ID_RE = re.compile(r"^chat_[A-Za-z0-9_-]{16,128}$")
_MESSAGE_ID_RE = re.compile(r"^msg_[A-Za-z0-9_-]{16,128}$")
_GENERATION_RE = re.compile(r"^index-\d{20}-[0-9a-f]{32}\.json$")
# A Chat ID the page proposes for a new Chat: exactly the form the core itself mints (chat_ + uuid4 hex).
_NEW_CHAT_ID_RE = re.compile(r"^chat_[0-9a-f]{32}$")


class UltraChatError(Exception):
    """A refused request; ``code`` and ``message`` are safe to send to the browser."""

    def __init__(self, status: int, code: str, message: str, *, reason: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.reason = reason


class UltraChatAccess:
    """Read capability of this server process: one scope, GET /ultra/chat/*; the token lives in memory only."""

    def __init__(self, *, enabled: bool, loopback: bool) -> None:
        self.reason = None if enabled and loopback else ("disabled" if not enabled else "non_loopback_bind")
        self._token = secrets.token_urlsafe(32) if self.reason is None else None

    def capability(self) -> dict[str, Any]:
        return {"available": self._token is not None, "reason": self.reason, "scope": "ultra_chat_read",
                "header": ULTRA_CHAT_TOKEN_HEADER, "token": self._token}

    def require(self, headers: Any) -> None:
        if self._token is None:
            raise UltraChatError(403, "ultra_chat_unavailable", "Ultra Chat reading is not available on this server")
        values = headers.get_all(ULTRA_CHAT_TOKEN_HEADER, [])
        if (len(values) != 1 or not values[0] or len(values[0]) > 200 or not values[0].isascii()
                or not secrets.compare_digest(values[0], self._token)):
            raise UltraChatError(403, "ultra_chat_token_invalid", "A valid Ultra Chat read capability is required")


class UltraChatWriteAccess:
    """Write capability of this server process: its own scope and token, never derived from the read token.

    One scope, POST /ultra/chat/workspaces/<id>/chats (create) and .../chats/<chat_id>/title (rename). The token
    lives in memory only; it exists only on a loopback bind, with Ultra Chat reading on and writing not switched off.
    """

    def __init__(self, *, enabled: bool, loopback: bool) -> None:
        self.reason = None if enabled and loopback else ("disabled" if not enabled else "non_loopback_bind")
        self._token = secrets.token_urlsafe(32) if self.reason is None else None

    def capability(self) -> dict[str, Any]:
        return {"available": self._token is not None, "reason": self.reason, "scope": "ultra_chat_write",
                "header": ULTRA_CHAT_WRITE_TOKEN_HEADER, "token": self._token}

    def require(self, headers: Any) -> None:
        if self._token is None:
            raise UltraChatError(403, "ultra_chat_write_unavailable", "Ultra Chat changes are not available on this server")
        values = headers.get_all(ULTRA_CHAT_WRITE_TOKEN_HEADER, [])
        if (len(values) != 1 or not values[0] or len(values[0]) > 200 or not values[0].isascii()
                or not secrets.compare_digest(values[0], self._token)):
            raise UltraChatError(403, "ultra_chat_write_token_invalid", "A valid Ultra Chat write capability is required")


def parse_query(raw_query: str, allowed: frozenset[str]) -> dict[str, str]:
    """Only the listed keys, each at most once; anything else is a 400 before any token or disk access."""
    values: dict[str, str] = {}
    if not raw_query:
        return values
    for pair in raw_query.split("&"):
        key, separator, value = pair.partition("=")
        if not separator or key not in allowed or key in values:
            raise UltraChatError(400, "invalid_ultra_chat_request", "Unsupported query parameters")
        values[key] = value
    return values


def _core():
    try:
        import context_storage  # the shared Ultra core at the repository root
    except ImportError as exc:
        raise UltraChatError(503, "ultra_core_unavailable", "The shared Ultra core is not importable") from exc
    return context_storage


class UltraChatService:
    """Routes of /ultra/chat/*; every answer is built from the registry and the bounded core functions."""

    def __init__(self, registry: WorkspaceRegistry) -> None:
        self.registry = registry

    def route(self, path: str, raw_query: str) -> Callable[[], dict[str, Any]]:
        """Validate route, IDs and query without touching any disk; the caller checks the token, then runs it."""
        parts = path.split("/")[1:]
        if parts == ["ultra", "chat", "workspaces"]:
            parse_query(raw_query, frozenset())
            return self.workspaces
        if len(parts) == 5 and parts[:3] == ["ultra", "chat", "workspaces"] and parts[4] == "chats":
            parse_query(raw_query, frozenset())
            wa_workspace_id = _wa_id(parts[3])
            return lambda: self.chats(wa_workspace_id)
        if (len(parts) == 7 and parts[:3] == ["ultra", "chat", "workspaces"] and parts[4] == "chats"
                and parts[6] == "messages"):
            query = parse_query(raw_query, frozenset({"before", "limit"}))
            chat_id = parts[5]
            if not _CHAT_ID_RE.fullmatch(chat_id):
                raise UltraChatError(400, "invalid_ultra_chat_request", "Invalid chat_id")
            before = query.get("before") or None
            if before is not None and not _MESSAGE_ID_RE.fullmatch(before):
                raise UltraChatError(400, "invalid_ultra_chat_request", "Invalid cursor")
            limit_text = query.get("limit", str(DEFAULT_PAGE_SIZE))
            if not limit_text.isdigit() or len(limit_text) > 3 or not 1 <= int(limit_text) <= MAX_PAGE_SIZE:
                raise UltraChatError(400, "invalid_ultra_chat_request", "limit must be 1..200")
            wa_workspace_id, limit = _wa_id(parts[3]), int(limit_text)
            return lambda: self.messages(wa_workspace_id, chat_id, before, limit)
        if self._is_rename_path(parts):
            raise UltraChatError(405, "method_not_allowed", "Renaming a chat requires POST")
        raise UltraChatError(404, "not_found", "Unknown Ultra Chat route")

    # --- stage 2: create and rename (POST only, write capability) ------------------------------------------

    @staticmethod
    def _is_rename_path(parts: list[str]) -> bool:
        return (len(parts) == 7 and parts[:3] == ["ultra", "chat", "workspaces"] and parts[4] == "chats"
                and parts[6] == "title")

    @staticmethod
    def is_write_path(path: str) -> bool:
        parts = path.split("/")[1:]
        create = len(parts) == 5 and parts[:3] == ["ultra", "chat", "workspaces"] and parts[4] == "chats"
        return create or UltraChatService._is_rename_path(parts)

    def write_route(self, path: str, raw_query: str) -> Callable[[Any], tuple[int, dict[str, Any]]]:
        """Validate a POST route and its IDs without touching any disk; the caller checks the token first."""
        parse_query(raw_query, frozenset())
        parts = path.split("/")[1:]
        if len(parts) == 5 and parts[:3] == ["ultra", "chat", "workspaces"] and parts[4] == "chats":
            wa_workspace_id = _wa_id(parts[3])
            return lambda body: self.create_chat(wa_workspace_id, body)
        if self._is_rename_path(parts):
            wa_workspace_id, chat_id = _wa_id(parts[3]), parts[5]
            if not _CHAT_ID_RE.fullmatch(chat_id):
                raise UltraChatError(400, "invalid_ultra_chat_request", "Invalid chat_id")
            return lambda body: self.rename_chat(wa_workspace_id, chat_id, body)
        raise UltraChatError(404, "not_found", "Unknown Ultra Chat route")

    def _writable_workspace(self, core: Any, wa_workspace_id: str) -> tuple[str, str]:
        """Root and Ultra identity of a registered Workspace whose history exists; nothing is created here."""
        record = self._registration(wa_workspace_id)
        identity = core.read_workspace_identity_bounded(record.workspace_root)
        if identity["status"] != "ok":
            raise UltraChatError(409, "workspace_unavailable", "The Ultra history of this Workspace is not writable",
                                 reason=identity["status"])
        return record.workspace_root, identity["workspace_id"]

    def create_chat(self, wa_workspace_id: str, body: Any) -> tuple[int, dict[str, Any]]:
        if not isinstance(body, dict) or "chat_id" not in body or set(body) - {"chat_id", "title"}:
            raise UltraChatError(400, "invalid_ultra_chat_request", "Expected {chat_id, title}")
        chat_id, title = body["chat_id"], body.get("title")
        if not isinstance(chat_id, str) or not _NEW_CHAT_ID_RE.fullmatch(chat_id):
            raise UltraChatError(400, "invalid_ultra_chat_request", "Invalid chat_id")
        if title is not None and not isinstance(title, str):
            raise UltraChatError(400, "invalid_ultra_chat_request", "Invalid title")
        core = _core()
        root, ultra_workspace_id = self._writable_workspace(core, wa_workspace_id)
        try:
            result = core.create_chat_record(root, title, chat_id=chat_id, expected_workspace_id=ultra_workspace_id)
        except Exception as exc:  # mapped to a safe code; anything unknown stays a 500 without detail
            raise _write_error(core, exc) from None
        status = 201 if result["created"] else 200
        return status, {"wa_workspace_id": wa_workspace_id, "chat": _chat_view(result["chat"]),
                        "created": result["created"]}

    def rename_chat(self, wa_workspace_id: str, chat_id: str, body: Any) -> tuple[int, dict[str, Any]]:
        if (not isinstance(body, dict) or set(body) != {"title", "expected_title"}
                or not isinstance(body["title"], str) or not isinstance(body["expected_title"], str)):
            raise UltraChatError(400, "invalid_ultra_chat_request", "Expected {title, expected_title}")
        core = _core()
        root, ultra_workspace_id = self._writable_workspace(core, wa_workspace_id)
        try:
            chat = core.rename_chat(root, chat_id, body["title"], expected_title=body["expected_title"],
                                    expected_workspace_id=ultra_workspace_id)
        except Exception as exc:
            raise _write_error(core, exc) from None
        return 200, {"wa_workspace_id": wa_workspace_id, "chat": _chat_view(chat)}

    # --- workspaces -----------------------------------------------------------------------------------------

    def _registration(self, wa_workspace_id: str):
        try:
            return self.registry.get(wa_workspace_id)
        except WorkspaceRegistryError:
            raise UltraChatError(404, "unknown_workspace", "Workspace is not registered in Web Alarm") from None

    def workspaces(self) -> dict[str, Any]:
        core = _core()
        try:
            records = self.registry.list()
        except WorkspaceRegistryError:
            return {"state": "unavailable", "reason": "registry_unavailable", "workspaces": []}
        if len(records) > MAX_WORKSPACES:
            return {"state": "too_large", "reason": "too_many_workspaces", "workspaces": []}
        items = []
        for record in records:
            item: dict[str, Any] = {"wa_workspace_id": record.workspace_id, "display_name": record.display_name}
            if not _WA_WORKSPACE_ID_RE.fullmatch(record.workspace_id):
                item["history"] = "unsupported_registration_id"
            else:
                item["history"] = core.read_workspace_identity_bounded(record.workspace_root)["status"]
            items.append(item)
        return {"state": "ok", "workspaces": items}

    # --- chats ----------------------------------------------------------------------------------------------

    def chats(self, wa_workspace_id: str) -> dict[str, Any]:
        core = _core()
        record = self._registration(wa_workspace_id)
        base = {"wa_workspace_id": wa_workspace_id, "display_name": record.display_name}
        try:
            listing = core.list_chats_bounded(record.workspace_root)
        except core.StorageReadError as exc:
            state = "too_large" if exc.code == "chats_listing_too_large" else "unavailable"
            return {**base, "state": state, "reason": exc.code, "chats": [], "excluded": {}}
        return {**base, "state": "ok", "chats": listing["chats"], "excluded": listing["excluded"]}

    # --- messages -------------------------------------------------------------------------------------------

    def messages(self, wa_workspace_id: str, chat_id: str, before: str | None, limit: int) -> dict[str, Any]:
        core = _core()
        record = self._registration(wa_workspace_id)
        base = {"wa_workspace_id": wa_workspace_id, "chat_id": chat_id}
        try:
            history = core.read_chat_history_bounded(record.workspace_root, chat_id)
        except core.StorageReadError as exc:
            if exc.code == "chat_not_found":
                raise UltraChatError(404, "chat_not_found", "Chat is not found in this Workspace") from None
            state = "too_large" if exc.code == "history_too_large" else "unavailable"
            return {**base, "history_state": state, "reason": exc.code, "messages": [], "excluded": {},
                    "excluded_ids": [], "page": {"limit": limit, "returned": 0, "has_more": False, "next_before": None}}
        runs, tasks, classification = _run_index(core, record.workspace_root)
        messages = _classify(history["messages"], runs, tasks)
        page = _page(messages, before, limit)
        if history["excluded"]:
            state = "partial"
        elif not history["messages"]:
            state = "empty"
        else:
            state = "complete"
        return {**base, "chat": history["chat"], "history_state": state, "excluded": history["excluded"],
                "excluded_ids": history["excluded_ids"], "total_messages": len(messages),
                "outcome_source": classification, **page}


# Safe text for every refusal of the shared writer; the core's own message (which may name a path) is never sent.
_WRITE_REFUSALS = {
    "title_changed": (409, "The chat was renamed elsewhere meanwhile"),
    "chat_id_conflict": (409, "This chat ID is already used differently"),
    "foreign_identity": (409, "The chat belongs to another Workspace"),
    "chat_damaged": (409, "The chat card is damaged"),
    "unsupported_version": (409, "The stored data has a newer format"),
    "chats_limit_reached": (409, "This Workspace has too many chats"),
    "workspace_identity_changed": (409, "The folder now holds another Ultra Workspace"),
    "missing_history": (409, "The Ultra history of this Workspace is not writable"),
    "invalid_metadata": (409, "The Ultra history of this Workspace is not writable"),
    "unsafe_storage_link": (409, "A link replaces a folder or file inside the Ultra storage"),
    "workspace_busy": (503, "The Workspace is busy with another change; try again"),
}


def _write_error(core: Any, exc: Exception) -> UltraChatError:
    if isinstance(exc, UltraChatError):
        return exc
    if isinstance(exc, core.ChatNotFoundError):
        return UltraChatError(404, "chat_not_found", "Chat is not found in this Workspace")
    if isinstance(exc, core.StorageWriteError):
        status, message = _WRITE_REFUSALS.get(exc.code, (503, "The change could not be stored"))
        return UltraChatError(status, exc.code if exc.code in _WRITE_REFUSALS else "storage_write_failed", message)
    if isinstance(exc, ValueError):
        return UltraChatError(400, "invalid_title", "The title is empty, too long or has control characters")
    if isinstance(exc, OSError):
        return UltraChatError(503, "storage_write_failed", "The change could not be stored")
    raise exc


def _chat_view(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {"chat_id": metadata["chat_id"], "status": "ok", "title": metadata["title"],
            "created_at": metadata.get("created_at")}


def _wa_id(value: str) -> str:
    if not _WA_WORKSPACE_ID_RE.fullmatch(value):
        raise UltraChatError(400, "invalid_ultra_chat_request", "Invalid wa_workspace_id")
    return value


def _run_index(core: Any, workspace_root: str) -> tuple[dict, dict, str]:
    """Run Store v2 index (canonical or newest generation, as run_store picks it), bounded; never required."""
    candidates: list[tuple[int, bool, dict]] = []
    try:
        names = core.list_ultra_files_bounded(workspace_root, ("audit", "index_generations"),
                                              max_entries=MAX_INDEX_GENERATIONS)
    except core.StorageReadError as exc:
        if exc.code != "missing":
            return {}, {}, "run_index_unavailable"
        names = []
    sources = [(("audit", "index.json"), True)]
    generations = [name for name in names if _GENERATION_RE.fullmatch(name)]
    if generations:
        sources.append((("audit", "index_generations", max(generations)), False))
    for parts, canonical in sources:
        try:
            value = core.read_ultra_json_bounded(workspace_root, parts, max_bytes=MAX_RUN_INDEX_BYTES)
        except core.StorageReadError as exc:
            if exc.code == "missing":
                continue
            return {}, {}, "run_index_unavailable"
        revision = value.get("revision", 0) if isinstance(value, dict) else None
        if (not isinstance(value, dict) or not isinstance(value.get("runs"), dict)
                or not isinstance(value.get("tasks"), dict) or not isinstance(revision, int)):
            return {}, {}, "run_index_unavailable"
        candidates.append((revision, canonical, value))
    if not candidates:
        return {}, {}, "no_run_index"
    index = max(candidates, key=lambda item: (item[0], item[1]))[2]
    return index["runs"], index["tasks"], "run_index"


def _status_of(run: Any) -> str | None:
    status = run.get("run_status") if isinstance(run, dict) else None
    return status if isinstance(status, str) else None


def _classify(messages: list[dict[str, Any]], runs: Mapping, tasks: Mapping) -> list[dict[str, Any]]:
    """Outcome of each message for display only (contract section 4); RAW is never rewritten."""
    answered = {m.get("task_block_id") for m in messages if m["role"] == "assistant" and m.get("task_block_id")}
    result = []
    for message in messages:
        item = {key: message[key] for key in ("message_id", "role", "created_at", "text")}
        block = message.get("task_block_id")
        task = tasks.get(block) if block else None
        block_statuses = [_status_of(runs.get(run_id)) for run_id in task.get("runs", [])] if isinstance(task, dict) \
            and isinstance(task.get("runs"), list) else []
        block_statuses = [status for status in block_statuses if status]
        producer = message.get("producer") or {}
        if message["role"] == "assistant":
            own = _status_of(runs.get(producer.get("run_id"))) if producer.get("run_id") else None
            statuses = [own] if own else block_statuses
            if message["text"].startswith(LEGACY_FAILURE_PREFIX) or "FAILED" in statuses:
                item["outcome"] = "failed"
            elif statuses and all(status == "RUNNING" for status in statuses):
                item["outcome"] = "unknown"
            elif statuses:
                item["outcome"] = "completed"
            else:
                item["outcome"] = "legacy"
            if statuses:
                item["run_status"] = statuses[-1]
            if producer.get("model_display_name"):
                item["model"] = producer["model_display_name"]
        elif message["role"] == "user":
            if block and block not in answered:
                item["outcome"] = "interrupted" if block_statuses and all(
                    status == "RUNNING" for status in block_statuses) else "no_answer"
            else:
                item["outcome"] = "request"
        else:
            item["outcome"] = "service"
        result.append(item)
    return result


def _page(messages: list[dict[str, Any]], before: str | None, limit: int) -> dict[str, Any]:
    """The ``limit`` messages before the cursor (newest first when absent), cut at MAX_PAGE_BYTES between items."""
    end = len(messages)
    if before is not None:
        end = next((index for index, item in enumerate(messages) if item["message_id"] == before), -1)
        if end < 0:
            raise UltraChatError(404, "cursor_not_found", "The cursor message is not in this chat")
    window = messages[max(0, end - limit):end]
    selected: list[dict[str, Any]] = []
    used = 0
    for item in reversed(window):
        size = len(json.dumps(item, ensure_ascii=False).encode("utf-8"))
        if size > MAX_PAGE_BYTES:
            placeholder = {key: item[key] for key in ("message_id", "role", "created_at", "outcome")}
            item, size = {**placeholder, "text": None, "too_large_for_page": True, "size_bytes": size}, 256
        if used + size > MAX_PAGE_BYTES and selected:
            break
        selected.append(item)
        used += size
    selected.reverse()
    first = end - len(selected)
    has_more = first > 0
    return {"messages": selected,
            "page": {"limit": limit, "returned": len(selected), "has_more": has_more,
                     "next_before": selected[0]["message_id"] if has_more and selected else None}}
