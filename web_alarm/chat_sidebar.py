"""Compact browser sidebar: registration/visibility only; no history deletion or migration."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
from uuid import uuid4

from .store_lock import InterProcessLock, StoreLockTimeout
from .ultra_chat import UltraChatError, _core, _NEW_CHAT_ID_RE, _CHAT_ID_RE
from .workspace_registry import WorkspaceRegistryError

WS = re.compile(r"ws_[0-9a-f]{32}")
BASE = "/ultra/chat/sidebar"
NEW_TITLE = "Новый чат"
TEST_PERSONAL = "ws_" + "0" * 31 + "1"
MAX_STATE = 2 * 1024 * 1024


class ChatSidebar:
    def __init__(self, service):
        self.service = service
        self.registry = service.registry
        self.path = self.registry.storage_root / "chat_sidebar.json"
        self.lock = self.path.with_suffix(".lock")

    @staticmethod
    def is_write_path(path):
        return path in {BASE + suffix for suffix in ("/workspace", "/personal", "/chat", "/archive", "/folder")}

    @property
    def test(self):
        return not hasattr(self.service, "_factory")

    def personal_id(self):
        if not self.test:
            from .standard_live import personal_chat_registration
            record = personal_chat_registration(self.registry)
            return record.workspace_id if record else None
        try:
            self.service._registration(TEST_PERSONAL)
        except UltraChatError as e:
            if e.code == "unknown_workspace":
                return None
            raise
        return TEST_PERSONAL

    def _safe(self, p, *, directory=False):
        if not os.path.lexists(p):
            return
        info = p.lstat()
        ok = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        if not ok or p.resolve(strict=True) != p or _core()._is_link_or_reparse(info):
            raise UltraChatError(409, "sidebar_storage_unsafe", "Sidebar storage requires review")

    def _state(self):
        self._safe(self.path)
        if not self.path.exists():
            return {"folders": {}, "hidden_workspaces": [], "hidden_chats": {}}
        try:
            if self.path.stat().st_size > MAX_STATE:
                raise ValueError()
            s = json.loads(self.path.read_bytes())
            if type(s) is not dict or set(s) != {"folders", "hidden_workspaces", "hidden_chats"}:
                raise ValueError()
            if (type(s["folders"]) is not dict or type(s["hidden_workspaces"]) is not list
                    or type(s["hidden_chats"]) is not dict):
                raise ValueError()
            valid_id = lambda x: type(x) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", x)
            if (not all(valid_id(x) and type(y) is str and len(y) <= 4096 for x,y in s["folders"].items())
                    or not all(valid_id(x) for x in s["hidden_workspaces"])
                    or not all(valid_id(x) and type(y) is list and all(type(cid) is str and re.fullmatch(r"chat_[A-Za-z0-9_-]{16,128}", cid) for cid in y)
                               for x,y in s["hidden_chats"].items())):
                raise ValueError()
            return s
        except (OSError, UnicodeError, ValueError, TypeError):
            raise UltraChatError(409, "sidebar_storage_invalid", "Sidebar state requires review") from None

    def _save(self, s):
        data = json.dumps(s, ensure_ascii=False, indent=2).encode("utf-8")
        if len(data) > MAX_STATE:
            raise UltraChatError(409, "sidebar_limit", "Sidebar state limit")
        self._safe(self.path)
        tmp = self.path.with_name(".sidebar-" + uuid4().hex + ".tmp")
        try:
            with tmp.open("xb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        finally:
            tmp.unlink(missing_ok=True)

    def _managed_parent(self):
        if self.test:
            self.service._check_scope()
            parent = self.service.projects
        elif self.service._factory._fixture is not None:
            parent = self.service._factory._root / "projects"
        else:
            parent = self.registry.storage_root / "chat_workspaces"
        self._safe(parent.parent, directory=True)
        self._safe(parent, directory=True)
        return parent

    def _allocated(self, ws, title):
        if not WS.fullmatch(ws):
            raise UltraChatError(400, "invalid_workspace_id", "Expected a new Workspace ID")
        parent = self._managed_parent()
        parent.mkdir(exist_ok=True)
        self._safe(parent, directory=True)
        root = parent / ws
        try:
            existing = self.registry.get(ws)
        except WorkspaceRegistryError:
            existing = None
        if existing is not None:
            if Path(existing.workspace_root) != root:
                raise UltraChatError(409, "workspace_id_conflict", "Workspace ID already used")
            self._safe(root, directory=True)
            if not root.is_dir():
                raise UltraChatError(409, "workspace_unavailable", "Workspace storage missing")
            return existing
        if os.path.lexists(root):
            raise UltraChatError(409, "workspace_storage_unconfirmed", "Existing unregistered storage requires review")
        root.mkdir()
        return self.registry.register(title, root, workspace_id=ws)

    def view(self):
        s = self._state()
        data = self.service.workspaces()
        personal = self.personal_id()
        if data["state"] != "ok":
            return data
        items = []
        total = 0
        parent = self._managed_parent()
        for w in data["workspaces"]:
            ws = w["wa_workspace_id"]
            if ws in s["hidden_workspaces"] and ws != personal:
                continue
            record = self.service._registration(ws)
            root = Path(record.workspace_root)
            managed = (root.parent == parent)
            project = s["folders"].get(ws, None if managed or ws == personal else str(root))
            listing = self.service.chats(ws) if w["history"] == "ok" else {"chats": [], "state": "unavailable"}
            hidden = set(s["hidden_chats"].get(ws, []))
            chats = [c for c in listing["chats"] if c["chat_id"] not in hidden]
            total += len(chats)
            if total > 10000:
                raise UltraChatError(409, "sidebar_limit", "Too many chats for compact sidebar")
            items.append({**w, "folder": project, "personal": ws == personal, "managed": managed,
                          "created_at": record.created_at,
                          "chats": chats, "hidden_chats": list(hidden), "chat_state": listing["state"]})
        items.sort(key=lambda w: (w["created_at"], w["wa_workspace_id"]))
        return {**data, "workspaces": items, "personal_workspace_id": personal}

    def _new_chat(self, ws, cid):
        record = self.service._registration(ws)
        identity = _core().read_workspace_identity_bounded(record.workspace_root)
        body = {"chat_id": cid, "title": NEW_TITLE, "auto_title": True}
        if identity["status"] == "missing_history":
            body["initialize_workspace"] = True
        return self.service.create_chat(ws, body)

    def mutate(self, path, body):
        if type(body) is not dict:
            raise UltraChatError(400, "invalid_ultra_chat_request", "Expected an object")
        self._safe(self.lock)
        try:
            with InterProcessLock(self.lock):
                s = self._state()
                return self._mutate(path, body, s)
        except (WorkspaceRegistryError, StoreLockTimeout, OSError, ValueError) as exc:
            raise UltraChatError(409, "sidebar_change_unconfirmed", "Sidebar change requires review") from None

    def _mutate(self, path, body, s):
        action = path.removeprefix(BASE + "/")
        allowed = {"workspace": {"workspace_id"}, "personal": {"chat_id"}, "chat": {"workspace_id", "chat_id"},
                   "archive": {"workspace_id"}, "folder": {"workspace_id", "folder"}}
        keys = set(body)
        if action not in allowed or (keys != allowed[action] and not (action == "archive" and keys == {"workspace_id", "chat_id"})):
            raise UltraChatError(400, "invalid_ultra_chat_request", "Unexpected fields")
        ws, cid = body.get("workspace_id"), body.get("chat_id")
        if "chat_id" in body and (type(cid) is not str or not (_CHAT_ID_RE if action == "archive" else _NEW_CHAT_ID_RE).fullmatch(cid)):
            raise UltraChatError(400, "invalid_chat_id", "Invalid Chat ID")
        if action == "personal":
            if self.test:
                record = self._allocated(TEST_PERSONAL, "Личные чаты")
            else:
                from .standard_live import prepare_personal_chat
                if self.service._api is None:
                    raise UltraChatError(403, "personal_creation_unavailable", "Personal creation unavailable")
                with self.service._personal_lock:
                    try:
                        record, _, _ = prepare_personal_chat(self.service._api, initial_chat_id=cid)
                    except Exception:
                        raise UltraChatError(409, "personal_storage_unavailable", "Personal storage requires review") from None
            return self._new_chat(record.workspace_id, cid)
        if type(ws) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", ws):
            raise UltraChatError(400, "invalid_workspace_id", "Invalid Workspace")
        if action == "workspace":
            if ws == TEST_PERSONAL:
                raise UltraChatError(409, "workspace_id_conflict", "Reserved personal ID")
            if ws in s["hidden_workspaces"]:
                raise UltraChatError(409, "workspace_archived", "Workspace is archived")
            record = self._allocated(ws, "Новый Workspace")
            return 201, {"wa_workspace_id": ws, "display_name": record.display_name}
        record = self.service._registration(ws)
        if action == "chat":
            if ws in s["hidden_workspaces"] or cid in s["hidden_chats"].get(ws, []):
                raise UltraChatError(409, "workspace_archived", "Archived entry")
            return self._new_chat(ws, cid)
        if action == "archive":
            if cid is None:
                if ws == self.personal_id():
                    raise UltraChatError(409, "personal_workspace_protected", "Archive individual personal chats")
                if ws not in s["hidden_workspaces"]:
                    s["hidden_workspaces"].append(ws)
            else:
                chats = self.service.chats(ws)
                if chats["state"] != "ok" or not any(c["chat_id"] == cid and c["status"] == "ok" for c in chats["chats"]):
                    raise UltraChatError(404, "chat_not_found", "Chat not found")
                hidden = s["hidden_chats"].setdefault(ws, [])
                if cid not in hidden:
                    hidden.append(cid)
            self._save(s)
            return 200, {"wa_workspace_id": ws, "chat_id": cid, "archived": True}
        if ws == self.personal_id() or ws in s["hidden_workspaces"]:
            raise UltraChatError(409, "workspace_unavailable", "Folder cannot be attached here")
        folder = body["folder"]
        if self.test:
            if folder is not None:
                raise UltraChatError(403, "offline_scope_invalid", "TEST accepts only simulated selection")
            display = "TEST · " + str(record.workspace_root)
        else:
            if type(folder) is not str or not 0 < len(folder) <= 4096 or not Path(folder).is_absolute():
                raise UltraChatError(400, "invalid_folder", "Expected an absolute existing directory")
            root = Path(folder).resolve(strict=True)
            if not root.is_dir():
                raise UltraChatError(400, "invalid_folder", "Expected a directory")
            display = str(root)
        # Association only: registered history location, identity, and files are untouched.
        s["folders"][ws] = display
        self._save(s)
        return 200, {"wa_workspace_id": ws, "folder": display}
