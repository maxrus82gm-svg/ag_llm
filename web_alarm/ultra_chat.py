"""Ultra Chat for the web shell: read access (programme No.37 stage 1) and Chat create/rename (stage 2).

A thin adapter. Workspace roots come from the Web Alarm registry (no second registration); the Ultra identity, the
chats and every RAW message are read through the bounded functions of the shared core ``context_storage`` (no
initialization on reads, no second copy of the storage format). Private history needs its own capability, ``ultra_chat_read``,
which does not depend on the Windows folder picker. Stage 2 writes only through the shared writer contract of the
core (Workspace lock, identity, ownership, exclusive publication) and only behind a second, separate capability,
``ultra_chat_write``: the read token never authorises a write. A confirmed first-chat request may initialize an
empty storage in a registered safe folder through the same core writer. Ordinary writes require an existing identity. Nothing
here imports the GigaChat transport, the Tk shell or the agent runtime, and no response carries a filesystem path.
"""

from __future__ import annotations

import json
import re
import secrets
import stat
from pathlib import Path
import tempfile
import threading
from typing import Any, Callable, Mapping
from uuid import uuid4

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

    def __init__(self, registry: WorkspaceRegistry, *, test_turn_roots=()) -> None:
        self.registry = registry
        from .turn_service import TurnService
        self.turns = TurnService(test_roots=test_turn_roots)

    def route(self, path: str, raw_query: str) -> Callable[[], dict[str, Any]]:
        """Validate route, IDs and query without touching any disk; the caller checks the token, then runs it."""
        parts = path.split("/")[1:]
        if len(parts) == 9 and parts[:3] == ['ultra','chat','workspaces'] and parts[4] == 'chats' and parts[6:8] == ['turns','by-key']:
            parse_query(raw_query, frozenset())
            workspace, chat_id = _wa_id(parts[3]), parts[5]
            if not _CHAT_ID_RE.fullmatch(chat_id):
                raise UltraChatError(400,'invalid_ultra_chat_request','Invalid chat_id')
            return lambda: self._turn_request('lookup',workspace,chat_id,parts[8])
        if len(parts) == 8 and parts[:3] == ['ultra','chat','workspaces'] and parts[4] == 'chats' and parts[6] == 'turns':
            parse_query(raw_query, frozenset())
            workspace, chat_id = _wa_id(parts[3]), parts[5]
            if not _CHAT_ID_RE.fullmatch(chat_id):
                raise UltraChatError(400,'invalid_ultra_chat_request','Invalid chat_id')
            return lambda: self._turn_request('get',workspace,chat_id,parts[7])
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
        if self._is_rename_path(parts) or self._is_workspace_rename_path(parts):
            raise UltraChatError(405, "method_not_allowed", "Renaming requires POST")
        raise UltraChatError(404, "not_found", "Unknown Ultra Chat route")

    # --- stage 2: create and rename (POST only, write capability) ------------------------------------------

    @staticmethod
    def _is_rename_path(parts: list[str]) -> bool:
        return (len(parts) == 7 and parts[:3] == ["ultra", "chat", "workspaces"] and parts[4] == "chats"
                and parts[6] == "title")

    @staticmethod
    def _is_workspace_rename_path(parts: list[str]) -> bool:
        return len(parts) == 5 and parts[:3] == ["ultra", "chat", "workspaces"] and parts[4] == "title"

    @staticmethod
    def is_write_path(path: str) -> bool:
        parts = path.split("/")[1:]
        create = len(parts) == 5 and parts[:3] == ["ultra", "chat", "workspaces"] and parts[4] == "chats"
        turn = (len(parts) in {7,9} and parts[:3] == ['ultra','chat','workspaces'] and parts[4] == 'chats'
                and parts[6] == 'turns' and (len(parts)==7 or parts[8]=='cancel'))
        return create or turn or UltraChatService._is_rename_path(parts) or UltraChatService._is_workspace_rename_path(parts)

    def write_route(self, path: str, raw_query: str) -> Callable[[Any], tuple[int, dict[str, Any]]]:
        """Validate a POST route and its IDs without touching any disk; the caller checks the token first."""
        parse_query(raw_query, frozenset())
        parts = path.split("/")[1:]
        if (len(parts) in {7,9} and parts[:3] == ['ultra','chat','workspaces'] and parts[4] == 'chats'
                and parts[6] == 'turns' and (len(parts)==7 or parts[8]=='cancel')):
            workspace, chat_id = _wa_id(parts[3]), parts[5]
            if not _CHAT_ID_RE.fullmatch(chat_id):
                raise UltraChatError(400,'invalid_ultra_chat_request','Invalid chat_id')
            action = 'submit' if len(parts)==7 else 'cancel'
            return lambda body: (200,self._turn_request(action,workspace,chat_id,body if action=='submit' else parts[7],body))
        if len(parts) == 5 and parts[:3] == ["ultra", "chat", "workspaces"] and parts[4] == "chats":
            wa_workspace_id = _wa_id(parts[3])
            return lambda body: self.create_chat(wa_workspace_id, body)
        if self._is_rename_path(parts):
            wa_workspace_id, chat_id = _wa_id(parts[3]), parts[5]
            if not _CHAT_ID_RE.fullmatch(chat_id):
                raise UltraChatError(400, "invalid_ultra_chat_request", "Invalid chat_id")
            return lambda body: self.rename_chat(wa_workspace_id, chat_id, body)
        if self._is_workspace_rename_path(parts):
            wa_workspace_id = _wa_id(parts[3])
            return lambda body: self.rename_workspace(wa_workspace_id, body)
        raise UltraChatError(404, "not_found", "Unknown Ultra Chat route")

    def _turn_request(self, action, wa_workspace_id, chat_id, value, body=None):
        root, workspace_id = self._writable_workspace(_core(),wa_workspace_id)
        if action == 'submit': return self.turns.submit(root,workspace_id,chat_id,value)
        if action == 'cancel': return self.turns.cancel(root,workspace_id,chat_id,value,body)
        if action == 'lookup': return self.turns.lookup(root,workspace_id,chat_id,value)
        return self.turns.get(root,workspace_id,chat_id,value)

    def rename_workspace(self, wa_workspace_id: str, body: Any) -> tuple[int, dict[str, Any]]:
        """Rename only the registered label. Existing shared Ultra data is never changed."""
        if (not isinstance(body, dict) or set(body) != {"title", "expected_title"}
                or not isinstance(body["title"], str) or not isinstance(body["expected_title"], str)):
            raise UltraChatError(400, "invalid_ultra_chat_request", "Expected {title, expected_title}")
        try:
            record = self.registry.rename_display_name(wa_workspace_id, body["title"], body["expected_title"])
        except WorkspaceRegistryError as exc:
            code = str(exc)
            if code == "invalid_workspace_title":
                raise UltraChatError(400, "invalid_workspace_title", "Invalid Workspace name") from None
            if code == "workspace_title_changed":
                raise UltraChatError(409, "workspace_title_changed", "Workspace name changed elsewhere") from None
            raise UltraChatError(409, "workspace_registry_unavailable", "Workspace registration unavailable") from None
        return 200, {"wa_workspace_id": wa_workspace_id, "display_name": record.display_name}

    def _writable_workspace(self, core: Any, wa_workspace_id: str, *, initialize: bool = False) -> tuple[str, str | None]:
        """Read-only preflight. Only an explicit first-chat create may use the core's initialization path."""
        record = self._registration(wa_workspace_id)
        identity = core.read_workspace_identity_bounded(record.workspace_root)
        if identity["status"] == "missing_history" and initialize:
            root = Path(record.workspace_root)
            try:
                # The registry stored a resolved root. Refuse a later link/ancestor substitution before bootstrap.
                if root.resolve(strict=True) != root:
                    raise UltraChatError(409, "workspace_unavailable", "The Workspace root changed",
                                         reason="unsafe_storage_link")
                storage = root / core.ULTRA_DIRNAME
                try:
                    info = storage.lstat()
                except FileNotFoundError:
                    return record.workspace_root, None
                linked = stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
                if stat.S_ISDIR(info.st_mode) and not linked and not any(storage.iterdir()):
                    return record.workspace_root, None
            except OSError:
                raise UltraChatError(409, "workspace_unavailable", "The Workspace cannot be initialized",
                                     reason="unreadable") from None
            # Missing identity beside existing data is a recovery case, never permission to mint a new identity.
        if identity["status"] != "ok":
            raise UltraChatError(409, "workspace_unavailable", "The Ultra history of this Workspace is not writable",
                                 reason=identity["status"])
        return record.workspace_root, identity["workspace_id"]

    def create_chat(self, wa_workspace_id: str, body: Any) -> tuple[int, dict[str, Any]]:
        if (not isinstance(body, dict) or "chat_id" not in body or set(body) - {"chat_id", "title", "initialize_workspace"}
                or ("initialize_workspace" in body and body["initialize_workspace"] is not True)):
            raise UltraChatError(400, "invalid_ultra_chat_request", "Expected {chat_id, title?, initialize_workspace?: true}")
        chat_id, title = body["chat_id"], body.get("title")
        if not isinstance(chat_id, str) or not _NEW_CHAT_ID_RE.fullmatch(chat_id):
            raise UltraChatError(400, "invalid_ultra_chat_request", "Invalid chat_id")
        if title is not None and not isinstance(title, str):
            raise UltraChatError(400, "invalid_ultra_chat_request", "Invalid title")
        core = _core()
        root, ultra_workspace_id = self._writable_workspace(core, wa_workspace_id, initialize=body.get("initialize_workspace") is True)
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


class OfflineUltraChatService(UltraChatService):
    """Stage 5 shell adapter for a disposable registry and its synthetic projects."""

    def __init__(self, registry: WorkspaceRegistry, root: Path) -> None:
        super().__init__(registry)
        self.root = Path(root).absolute()
        self.projects = self.root / "projects"
        self._owners = {}
        self._owner_lock = threading.Lock()
        if (Path(tempfile.gettempdir()).resolve() not in self.root.parents
                or registry.storage_root != self.root / "registry"):
            raise ValueError("Stage 5 requires an explicit disposable root and its own registry")
        self._plain_dir(self.root)
        self.projects.mkdir(exist_ok=True)
        self._check_scope()

    @staticmethod
    def _plain_dir(path):
        if (not path.is_dir() or path.is_symlink() or path.is_junction()
                or path.resolve(strict=True) != path):
            raise UltraChatError(403, "offline_scope_invalid", "TEST storage is outside the fixture scope")

    def _check_scope(self):
        self._plain_dir(self.root)
        self._plain_dir(self.projects)
        self._plain_dir(self.registry.storage_root)
        self._plain_dir(self.registry.workspaces_dir)
        for path in self.registry.workspaces_dir.glob("*.json"):
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                raise UltraChatError(403, "offline_scope_invalid", "TEST registry contains an unsafe entry")

    def _check_record(self, record):
        expected = self.projects / record.workspace_id
        if (not re.fullmatch(r"ws_[0-9a-f]{32}", record.workspace_id)
                or Path(record.workspace_root) != expected):
            raise UltraChatError(403, "offline_scope_invalid", "Workspace is outside the TEST scope")
        if expected.exists() or expected.is_symlink() or expected.is_junction():
            self._plain_dir(expected)

    def _registration(self, wa_workspace_id):
        self._check_scope()
        record = super()._registration(wa_workspace_id)
        self._check_record(record)
        return record

    def workspaces(self):
        self._check_scope()
        try:
            records = self.registry.list()
        except WorkspaceRegistryError:
            raise UltraChatError(503, "registry_unavailable", "TEST registry could not be read") from None
        if len(records) > MAX_WORKSPACES:
            return {"state": "too_large", "reason": "too_many_workspaces", "workspaces": []}
        items = []
        for record in records:
            self._check_record(record)
            items.append({"wa_workspace_id": record.workspace_id, "display_name": record.display_name,
                          "history": _core().read_workspace_identity_bounded(record.workspace_root)["status"]})
        return {"state": "ok", "workspaces": items}

    def create_workspace(self, body):
        if (type(body) is not dict or set(body) != {"title"} or type(body["title"]) is not str
                or not body["title"].strip() or len(body["title"]) > 120
                or any(ord(char) < 32 for char in body["title"])):
            raise UltraChatError(400, "invalid_workspace_title", "Expected a TEST Workspace title")
        self._check_scope()
        workspace_id = "ws_" + uuid4().hex
        try:
            body["title"].encode("utf-8")
            root = self.projects / workspace_id
            root.mkdir()
            record = self.registry.register(body["title"], root, workspace_id=workspace_id)
        except (OSError, ValueError, WorkspaceRegistryError):
            raise UltraChatError(503, "workspace_unavailable", "TEST Workspace could not be created") from None
        return 201, {"wa_workspace_id": record.workspace_id, "display_name": record.display_name}

    def rename_workspace(self, wa_workspace_id, body):
        self._registration(wa_workspace_id)
        return super().rename_workspace(wa_workspace_id, body)

    def messages(self, wa_workspace_id, chat_id, before, limit):
        page = super().messages(wa_workspace_id, chat_id, before, limit)
        assistants = [item for item in page["messages"] if item["role"] == "assistant"]
        if not assistants:
            return page
        core = _core()
        root, workspace_id = self._writable_workspace(core, wa_workspace_id)
        turns = self._turns_for(root, workspace_id, chat_id)
        try:
            for item in assistants:
                raw = core.read_ultra_json_bounded(root, ("chats", chat_id, "messages", item["message_id"] + ".json"),
                                                  max_bytes=32768)
                run_id = raw["producer"]["run_id"]
                turn = turns.get(root, workspace_id, chat_id, run_id)
                if (turn["mode"] != "TEST_OFFLINE" or turn["state"] != "SUCCEEDED"
                        or turn["assistant_message_id"] != item["message_id"] or turn["answer"] != item["text"]):
                    raise ValueError("TEST assistant RAW has no confirmed result")
        except (KeyError, TypeError, ValueError, core.StorageReadError, UltraChatError):
            raise UltraChatError(503, "offline_history_invalid", "TEST answer could not be verified") from None
        return page

    def capability(self):
        return {"available": True, "mode": "TEST_OFFLINE", "label": "TEST · локальный имитатор"}

    @staticmethod
    def is_write_path(path):
        return path == "/ultra/chat/workspaces" or UltraChatService.is_write_path(path)

    def write_route(self, path, raw_query):
        if path == "/ultra/chat/workspaces":
            parse_query(raw_query, frozenset())
            return self.create_workspace
        return super().write_route(path, raw_query)

    def route(self, path, raw_query):
        parts = path.split("/")[1:]
        if (len(parts) == 8 and parts[:3] == ["ultra", "chat", "workspaces"]
                and parts[4] == "chats" and parts[6:] == ["turns", "latest"]):
            parse_query(raw_query, frozenset())
            workspace, chat = _wa_id(parts[3]), parts[5]
            if not _CHAT_ID_RE.fullmatch(chat):
                raise UltraChatError(400, "invalid_ultra_chat_request", "Invalid chat_id")
            return lambda: self.latest_turn(workspace, chat)
        return super().route(path, raw_query)

    @staticmethod
    def _fixture_turns(root, context=(), context_ref="offline-read:v1", response_text="TEST"):
        from ordinary_chat_service import RequestLimits
        from .ordinary_chat_test_adapter import OfflineTestAdapter
        from .turn_service import TurnService
        fixture = OfflineTestAdapter(
            context=context, context_ref=context_ref,
            limits=RequestLimits(4, 2048, 8192, 8192, 128, 8),
            response={"choices": [{"message": {"role": "assistant", "content": response_text}}]},
        )
        return TurnService(test_roots=[root], offline_adapter=fixture)

    def _turns_for(self, root, workspace_id, chat_id):
        with self._owner_lock:
            owner = self._owners.get((workspace_id, chat_id))
        return owner[1] if owner else self._fixture_turns(root)

    def _turn_request(self, action, wa_workspace_id, chat_id, value, body=None):
        if action == "submit":
            return self.submit_turn(wa_workspace_id, chat_id, value)
        root, workspace_id = self._writable_workspace(_core(), wa_workspace_id)
        turns = self._turns_for(root, workspace_id, chat_id)
        if action == "cancel":
            return turns.cancel(root, workspace_id, chat_id, value, body)
        if action == "lookup":
            return turns.lookup(root, workspace_id, chat_id, value)
        return turns.get(root, workspace_id, chat_id, value)

    def _context(self, root, workspace_id, chat_id, turns):
        """Project one bounded, verified completed pair from this Chat only."""
        from provider_accounting import canonical_json_text
        core = _core()
        try:
            history = core.read_chat_history_bounded(root, chat_id)
        except core.StorageReadError as error:
            raise UltraChatError(503, "offline_history_invalid", "TEST context could not be read") from error
        if history["excluded"]:
            raise UltraChatError(503, "offline_history_invalid", "TEST history contains damaged records")
        context = [{"role": "system", "content": "TEST offline chat " + chat_id}]
        messages = history["messages"]
        for assistant in reversed(messages):
            producer = assistant.get("producer", {})
            if assistant["role"] != "assistant" or producer.get("kind") != "offline_chat_fixture":
                continue
            turn = turns.get(root, workspace_id, chat_id, producer.get("run_id"))
            user = next((m for m in messages if m["message_id"] == turn["user_message_id"]), None)
            if (turn["state"] != "SUCCEEDED" or assistant["message_id"] != turn["assistant_message_id"]
                    or not user or user["role"] != "user"):
                raise UltraChatError(503, "offline_history_invalid", "TEST pair is not backed by its Turn")
            if all(len(canonical_json_text(m["text"]).encode("utf-8")) <= 1024 for m in (user, assistant)):
                context.extend({"role": m["role"], "content": m["text"]} for m in (user, assistant))
            break
        return context

    def submit_turn(self, wa_workspace_id, chat_id, body):
        from .turn_service import KEY, OFFLINE_REF, identities
        if (type(body) is not dict or set(body) != {"idempotency_key", "model_ref", "text"}
                or type(body["idempotency_key"]) is not str or not KEY.fullmatch(body["idempotency_key"])
                or type(body["model_ref"]) is not str or not 0 < len(body["model_ref"]) <= 256
                or type(body["text"]) is not str or not body["text"].strip()):
            raise UltraChatError(400, "invalid_turn_request", "Expected an explicit TEST model, text and retry key")
        try:
            valid_size = len(body["text"].encode("utf-8")) <= 2048
        except UnicodeError:
            valid_size = False
        if not valid_size:
            raise UltraChatError(400, "invalid_turn_request", "TEST message must be valid UTF-8 up to 2048 bytes")
        root, workspace_id = self._writable_workspace(_core(), wa_workspace_id)
        scope = (workspace_id, chat_id)
        key = body["idempotency_key"]
        with self._owner_lock:
            entry = self._owners.get(scope)
            if entry:
                if entry[0] != key:
                    raise UltraChatError(409, "test_chat_busy", "Wait for the active TEST Turn")
                _, turns, context_ref = entry
                owns_entry = False
            else:
                reader = self._fixture_turns(root)
                try:
                    turn_id = identities(workspace_id, chat_id, key)["turn_id"]
                    # Read the accepted binding without projecting an interrupted
                    # stream. The real submit owns explicit Run Store recovery.
                    with reader._session(root, workspace_id, chat_id):
                        previous = reader._load(root, workspace_id, chat_id, turn_id)
                except UltraChatError as error:
                    if error.code not in {"turn_not_found", "turn_acceptance_incomplete"}:
                        raise
                    context = self._context(root, workspace_id, chat_id, reader)
                    # The reference names this Chat's projection. The actual
                    # snapshot is bound by the accepted Turn's request_ref.
                    context_ref = "stage5:" + chat_id
                else:
                    context, context_ref = (), previous["references"]["context_ref"]
                answer = "TEST · локальный имитатор\nОтвет на: " + body["text"][:256]
                turns = self._fixture_turns(root, context, context_ref, answer)
                self._owners[scope] = (key, turns, context_ref)
                owns_entry = True
        try:
            return turns.submit(root, workspace_id, chat_id,
                                {**body, "context_ref": context_ref, "config_ref": OFFLINE_REF})
        finally:
            if owns_entry:
                with self._owner_lock:
                    self._owners.pop(scope, None)

    def latest_turn(self, wa_workspace_id, chat_id):
        import run_store
        from .turn_service import TURN
        core = _core()
        root, workspace_id = self._writable_workspace(core, wa_workspace_id)
        try:
            index = run_store.load_workspace_run_index(root)
            entries = [(entry["display_id"], run_id) for run_id, entry in index["runs"].items()
                       if entry.get("chat_id") == chat_id and TURN.fullmatch(run_id)]
            if not entries:
                return {"turn": None, "text": None}
            _, run_id = max(entries, key=lambda item: int(item[0].split("-")[-1]))
            turns = self._turns_for(root, workspace_id, chat_id)
            turn = turns.get(root, workspace_id, chat_id, run_id)
            text = None
            if turn["state"] != "ACCEPTING":
                raw = core.read_ultra_json_bounded(root, ("chats", chat_id, "messages", turn["user_message_id"] + ".json"),
                                                  max_bytes=32768)
                text = raw["original_text"]
            return {"turn": turn, "text": text}
        except UltraChatError as error:
            if error.code == "turn_acceptance_incomplete":
                return {"turn": None, "text": None}
            raise
        except (OSError, ValueError, KeyError, core.StorageReadError):
            raise UltraChatError(503, "turn_storage_unavailable", "TEST Turn could not be read") from None


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
