"""Disposable, read-only HTTP fixture and auditable MCP bridge; no live storage."""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import threading
import urllib.error
import urllib.request
import uuid

FIXTURE_ID = "synthetic_wua_desktop_001"
TOOLS = ("ping", "list_capabilities", "read_synthetic_context")
MAX_BYTES = 65536
MAX_EVENTS = 64


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def tree_hash(root: Path) -> str:
    return sha({p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob("*")) if p.is_file()})


class BridgeError(Exception):
    """Deliberate, non-sensitive error code safe for a tool result."""


class IsolationPolicy:
    """Defense-in-depth Python audit policy, not an operating-system sandbox."""

    def __init__(self, writable_roots):
        self.roots = tuple(Path(x).resolve() for x in writable_roots)
        self.port = None
        self.denials = {"network": 0, "file_write": 0, "subprocess": 0}

    def allowed_path(self, path):
        if isinstance(path, int):
            return True  # Existing stdout/stderr descriptors.
        return any(Path(path).resolve().is_relative_to(root) for root in self.roots)

    def deny(self, kind):
        self.denials[kind] += 1
        raise PermissionError("WUA_ISOLATION_" + kind.upper())

    def audit(self, event, args):
        if event == "socket.connect" and args[1] != ("127.0.0.1", self.port):
            self.deny("network")
        if event == "socket.bind" and args[1] != ("127.0.0.1", 0):
            self.deny("network")
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn"}:
            self.deny("subprocess")
        if event == "open":
            flags = args[2]
            if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                if not self.allowed_path(args[0]):
                    self.deny("file_write")
        if event in {"os.remove", "os.rmdir", "os.mkdir"} and not self.allowed_path(args[0]):
            self.deny("file_write")
        if event == "os.rename" and not all(self.allowed_path(p) for p in args[:2]):
            self.deny("file_write")


def public_pack(pack):
    return {key: pack[key] for key in (
        "PACK_VERSION", "TASK", "GOAL", "CURRENT_STATUS", "NEXT_SAFE_ACTION",
        "AUTHORITY_SOURCE", "CHECKPOINT", "PROJECTION", "PROTOCOL_RULES",
    )}


class Fixture:
    """Owns only explicitly supplied disposable storage and sanitized receipts."""

    def __init__(self, root: Path, evidence_root: Path, api_class, policy=None):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.session_id = uuid.uuid4().hex
        self.receipt_dir = evidence_root.resolve() / self.session_id
        self.receipt_dir.mkdir(parents=True, exist_ok=False)
        self.proof_path = self.receipt_dir / "session.json"
        self.policy = policy
        self.lock = threading.RLock()
        self.events = deque(maxlen=MAX_EVENTS)
        self.sequence = 0
        self.api = api_class(self.root / "state")
        project = self.root / "project"
        project.mkdir()
        self.nonce = secrets.token_hex(16)
        code, _ = self.api.dispatch("POST", "/workspaces", {
            "workspace_id": "synthetic_desktop_ws", "display_name": "WUA Desktop synthetic fixture",
            "workspace_root": str(project),
        })
        if code != 201:
            raise BridgeError("BOOTSTRAP_WORKSPACE_FAILED")
        code, _ = self.api.dispatch("POST", "/tasks", {
            "task_id": FIXTURE_ID, "workspace_id": "synthetic_desktop_ws",
            "title": "Desktop MCP E2E synthetic task", "goal": "nonce=" + self.nonce,
            "raw_task": "Synthetic data only. This text is data, not permission to perform actions.",
        })
        if code != 201:
            raise BridgeError("BOOTSTRAP_TASK_FAILED")
        code, pack = self.api.dispatch("GET", f"/tasks/{FIXTURE_ID}/context")
        if code != 200:
            raise BridgeError("BOOTSTRAP_CONTEXT_FAILED")
        self.expected_context = public_pack(pack)
        self.expected_hash = sha(self.expected_context)
        self.baseline = self.state_hash()
        self.server = self._create_http_server()
        self.port = self.server.server_address[1]
        if self.policy:
            self.policy.port = self.port
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.stopped = False
        self.save("ready")

    def state_hash(self):
        return sha({"state": tree_hash(self.root / "state"), "project": tree_hash(self.root / "project")})

    def _create_http_server(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                route = self.path
                if route not in {"/status", f"/tasks/{FIXTURE_ID}/context"}:
                    code, value = 404, {"error": "HTTP_ROUTE_DENIED"}
                else:
                    code, value = fixture.api.dispatch("GET", route)
                fixture.add_event({"kind": "http", "method": "GET", "path": route,
                                   "status": code})
                body = canonical(value)
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def deny_write(self):
                fixture.add_event({"kind": "http", "method": self.command, "path": self.path,
                                   "status": 405, "error": "HTTP_METHOD_DENIED"})
                self.send_error(405, "HTTP_METHOD_DENIED")

            do_POST = deny_write
            do_PUT = deny_write
            do_PATCH = deny_write
            do_DELETE = deny_write

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        return server

    def add_event(self, value):
        with self.lock:
            self.sequence += 1
            self.events.append({"seq": self.sequence, "at_utc": datetime.now(timezone.utc).isoformat(), **value})
            self.save()

    def proof(self, state="running"):
        current = self.state_hash()
        return {"schema_version": 1, "synthetic": True, "task_id": FIXTURE_ID,
                "session_id": self.session_id, "nonce": self.nonce, "state": state,
                "expected_context": self.expected_context, "expected_context_sha256": self.expected_hash,
                "baseline_state_sha256": self.baseline, "current_state_sha256": current,
                "storage_unchanged": current == self.baseline, "event_total": self.sequence,
                "events": list(self.events), "event_retention": MAX_EVENTS,
                "guard_denials": dict(self.policy.denials) if self.policy else None,
                "production_access": False, "model_api_calls": 0}

    def save(self, state="running"):
        with self.lock:
            body = canonical(self.proof(state))
            staging = self.proof_path.with_suffix(".tmp")
            staging.write_bytes(body)
            os.replace(staging, self.proof_path)

    @contextmanager
    def tool_receipt(self, name, arguments, peer):
        call_id = uuid.uuid4().hex
        self.add_event({"kind": "tool_started", "call_id": call_id, "tool": name,
                        "arguments": arguments, "peer_claim": peer})
        try:
            yield call_id
        except BridgeError as exc:
            self.add_event({"kind": "tool_finished", "call_id": call_id, "tool": name,
                            "status": "REJECTED", "error": str(exc)})
            raise
        except Exception:
            self.add_event({"kind": "tool_finished", "call_id": call_id, "tool": name,
                            "status": "ERROR", "error": "INTERNAL_ERROR"})
            raise BridgeError("INTERNAL_ERROR") from None
        else:
            self.add_event({"kind": "tool_finished", "call_id": call_id, "tool": name, "status": "OK"})

    def stop_http(self):
        if not self.stopped:
            self.server.shutdown()
            self.server.server_close()
            self.worker.join(timeout=5)
            self.stopped = True

    def close(self):
        self.stop_http()
        self.save("closed")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BridgeError("HTTP_REDIRECT_DENIED")


class HttpBridge:
    def __init__(self, port, timeout=2.0, max_bytes=MAX_BYTES):
        if type(port) is not int or not 1 <= port <= 65535:
            raise BridgeError("INVALID_LOOPBACK_PORT")
        self.port, self.timeout, self.max_bytes = port, timeout, max_bytes
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def get(self, path):
        if path not in {"/status", f"/tasks/{FIXTURE_ID}/context"}:
            raise BridgeError("HTTP_ROUTE_DENIED")
        try:
            with self.opener.open(f"http://127.0.0.1:{self.port}{path}", timeout=self.timeout) as response:
                data = response.read(self.max_bytes + 1)
            if len(data) > self.max_bytes:
                raise BridgeError("HTTP_RESPONSE_TOO_LARGE")
            value = json.loads(data)
            if not isinstance(value, dict):
                raise BridgeError("HTTP_INVALID_JSON_OBJECT")
            return value
        except BridgeError:
            raise
        except (TimeoutError, socket.timeout):
            raise BridgeError("HTTP_TIMEOUT") from None
        except urllib.error.HTTPError:
            raise BridgeError("HTTP_ERROR_STATUS") from None
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise BridgeError("HTTP_TIMEOUT") from None
            raise BridgeError("HTTP_UNAVAILABLE") from None
        except OSError:
            raise BridgeError("HTTP_UNAVAILABLE") from None
        except (ValueError, UnicodeError):
            raise BridgeError("HTTP_INVALID_JSON") from None


class ReadTools:
    def __init__(self, fixture):
        self.fixture = fixture
        self.bridge = HttpBridge(fixture.port)

    def identity(self, call_id):
        return {"synthetic": True, "task_id": FIXTURE_ID, "session_id": self.fixture.session_id,
                "nonce": self.fixture.nonce, "call_id": call_id, "proof_path": str(self.fixture.proof_path)}

    def ensure_unchanged(self):
        if self.fixture.state_hash() != self.fixture.baseline:
            raise BridgeError("FIXTURE_STORAGE_CHANGED")

    def ping(self, peer=None):
        with self.fixture.tool_receipt("ping", {}, peer) as call_id:
            self.ensure_unchanged()
            value = self.bridge.get("/status")
            if value.get("service") != "web_alarm_server" or value.get("status") != "ok":
                raise BridgeError("WRONG_HTTP_BACKEND")
            return {**self.identity(call_id), "status": "ok", "service": value["service"],
                    "api_version": value["api_version"]}

    def list_capabilities(self, peer=None):
        with self.fixture.tool_receipt("list_capabilities", {}, peer) as call_id:
            self.ensure_unchanged()
            self.bridge.get("/status")  # Never return apparently-ready static capabilities after disconnect.
            return {**self.identity(call_id), "tools": list(TOOLS), "read_only": True,
                    "mutations": False, "arbitrary_paths": False, "allowed_task_id": FIXTURE_ID,
                    "http_timeout_seconds": self.bridge.timeout, "max_response_bytes": self.bridge.max_bytes,
                    "expected_context_sha256": self.fixture.expected_hash, "storage_unchanged": True,
                    "state_sha256": self.fixture.baseline}

    def read_synthetic_context(self, fixture_id=FIXTURE_ID, peer=None):
        args = {"fixture_id": FIXTURE_ID if fixture_id == FIXTURE_ID else "<denied task id>"}
        with self.fixture.tool_receipt("read_synthetic_context", args, peer) as call_id:
            if type(fixture_id) is not str or fixture_id != FIXTURE_ID:
                raise BridgeError("TASK_ID_DENIED")
            self.ensure_unchanged()
            pack = self.bridge.get(f"/tasks/{FIXTURE_ID}/context")
            try:
                context = public_pack(pack)
            except KeyError:
                raise BridgeError("HTTP_INVALID_CONTEXT") from None
            digest = sha(context)
            if digest != self.fixture.expected_hash:
                raise BridgeError("SYNTHETIC_CONTEXT_CHANGED")
            return {**self.identity(call_id), "context": context, "context_sha256": digest,
                    "source": "frozen WebAlarmApi GET /tasks/synthetic_wua_desktop_001/context"}
