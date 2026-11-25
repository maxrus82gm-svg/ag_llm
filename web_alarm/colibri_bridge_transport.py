"""WUA-side Client Bridge v1 catalog and isolated OFFLINE transport.

Only the isolated executor accepts a frozen Turn identity and ordered context.
The read-only mode exposes the authenticated catalog. No implicit retries or
provider fallback.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import codecs
import copy
import hashlib
import json
import os
import re
import stat
import tempfile
import threading
import time
from typing import Callable

import httpx

VERSION = "1.0.0"
CONTRACT_SHA = "2d9e7f6fb860fdd53747f4ba75350d15bab27877"
IMPLEMENTATION_SHA = "883d91d4ad2e47fc260bfd7b1e61d230f8fb99ea"
PIN = Path(__file__).with_name("colibri_contract_v1")
BLOBS = {"openapi.yaml": "e578c496aee64ccd0dba1279000e7e0ab12a764a",
         "stream-events.schema.json": "e39b255f539ce69d21e263f0e7943bd7d9fa112a"}
HEX32 = re.compile(r"[0-9a-f]{32}")
TOKEN = re.compile(r"[A-Za-z0-9_-]{43,128}")
ORIGIN = re.compile(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})")
MAX_BODY = 9 * 1024 * 1024  # pinned producer HTTP bound
MAX_JSON = 16 * 1024 * 1024
MAX_EVENT = 16 * 1024 * 1024
MAX_SSE_BYTES = 64 * 1024 * 1024  # explicit transport safety bound, never silently clips/token ceiling
TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "UNKNOWN"}
PRECLAIM = {"unauthorized", "forbidden", "invalid_request", "unknown_target",
            "stale_instance", "target_not_ready", "slot_busy", "unsupported_capability",
            "request_too_large", "context_limit", "output_limit"}
COUNTERS = ("prompt_tokens", "completion_tokens", "total_tokens",
            "reasoning_tokens", "cached_prompt_tokens")


class BridgeFault(Exception):
    """Stable bounded diagnostics only; never raw upstream text or credentials."""
    def __init__(self, code, status=None):
        super().__init__(code)
        self.code, self.status = code, status


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def strict_json(raw):
    def pairs(seq):
        out = {}
        for k, v in seq:
            if k in out:
                raise ValueError("duplicate JSON member")
            out[k] = v
        return out
    def invalid(_):
        raise ValueError("invalid constant")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise BridgeFault("protocol_error") from None


class Contract:
    def __init__(self):
        try:
            from jsonschema import Draft202012Validator, FormatChecker
            decoded = {}
            for name, expected in BLOBS.items():
                data = (PIN / name).read_bytes()
                # These consumer copies are pinned byte-for-byte, including LF.
                if hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != expected:
                    raise BridgeFault("contract_drift")
                decoded[name] = strict_json(data)
            self.components = decoded["openapi.yaml"]["components"]
            self.packet = Draft202012Validator(decoded["stream-events.schema.json"])
            self.validators = {k: Draft202012Validator(
                {"$ref": "#/components/schemas/" + k, "components": self.components},
                format_checker=FormatChecker()) for k in self.components["schemas"]}
        except (OSError, ImportError, KeyError, TypeError, ValueError):
            raise BridgeFault("contract_unavailable") from None

    def check(self, name, value):
        v = self.packet if name == "Event" else self.validators[name]
        if not v.is_valid(value):
            raise BridgeFault("protocol_error")
        if name == "Usage":
            self.usage(value)
        return value

    @staticmethod
    def usage(u):
        p, c, t, r, cached = (u[k] for k in COUNTERS)
        if u["status"] == "unavailable" and u["prompt_basis"] != "unknown":
            raise BridgeFault("protocol_error")
        if u["source"] == "provider_and_derived_total":
            if u["status"] != "partial" or None in (p, c, t) or p + c != t:
                raise BridgeFault("protocol_error")
        if r is not None and c is not None and r > c:
            raise BridgeFault("protocol_error")
        if u["prompt_basis"] == "includes_cached" and cached is not None and p is not None and cached > p:
            raise BridgeFault("protocol_error")
        # Do not invent missing counters, change bases, or account for prices.
        return copy.deepcopy(u)


def _windows_private_acl(path):
    """Fail closed on weak Windows DACLs for Bridge discovery files.

    Checking mode bits on NT is insufficient. The actual descriptor and token
    must be owned by the current process identity, without read/write ACEs
    granted to a general Windows group. An ACL cannot protect against a
    malicious process already running as the *same* user; that is a separate
    authority boundary and remains a LIVE preflight gate.
    """
    if os.name != "nt":
        return
    try:
        import win32api
        import win32con
        import win32security
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
        try:
            actor = win32security.ConvertSidToStringSid(win32security.GetTokenInformation(token, win32security.TokenUser)[0])
        finally:
            token.Close()
        desc = win32security.GetNamedSecurityInfo(
            str(path), win32security.SE_FILE_OBJECT,
            win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION)
        if win32security.ConvertSidToStringSid(desc.GetSecurityDescriptorOwner()) != actor:
            raise BridgeFault("unsafe_discovery")
        dacl = desc.GetSecurityDescriptorDacl()
        if dacl is None:
            raise BridgeFault("unsafe_discovery")
        trusted = {actor, "S-1-5-18", "S-1-5-32-544", "S-1-3-4", "S-1-3-0"}
        if dacl.GetAceCount() > 128:
            raise BridgeFault("unsafe_discovery")
        for index in range(dacl.GetAceCount()):
            ace = dacl.GetAce(index)
            kind, sid = ace[0][0], win32security.ConvertSidToStringSid(ace[2])
            # Do not silently accept unparsed conditional/object/unknown ACEs.
            if kind not in (win32security.ACCESS_ALLOWED_ACE_TYPE,
                            win32security.ACCESS_DENIED_ACE_TYPE):
                raise BridgeFault("unsafe_discovery")
            if kind == win32security.ACCESS_ALLOWED_ACE_TYPE and sid not in trusted:
                raise BridgeFault("unsafe_discovery")
    except BridgeFault:
        raise
    except Exception:
        # Missing pywin32 / AccessDenied / inaccessible DACL all refuse.
        raise BridgeFault("unsafe_discovery") from None


def _private_temp_file(profile, name, limit):
    p = profile / name
    try:
        st = p.lstat()
        if (p.resolve(strict=True) != p or p.is_symlink() or
                getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT or
                not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > limit):
            raise BridgeFault("unsafe_discovery")
        if os.name != "nt" and (st.st_uid != os.getuid() or st.st_mode & 0o077):
            raise BridgeFault("unsafe_discovery")
        if os.name == "nt":
            _windows_private_acl(profile)
            _windows_private_acl(p)
        with p.open("rb") as file:
            data = file.read(limit + 1)
        if os.name == "nt":
            # A best-effort recheck around the read, never an OS-atomic ACL
            # lease. Open-file handle checks require a separate LIVE security gate.
            _windows_private_acl(profile)
            _windows_private_acl(p)
        if len(data) > limit:
            raise BridgeFault("unsafe_discovery")
        return data
    except (OSError, ValueError):
        raise BridgeFault("discovery_unavailable") from None


@dataclass(frozen=True)
class Discovery:
    origin: str
    bridge_id: str
    launch_identity: str
    token: str = field(repr=False)


def _discover(profile, expected):
    data = strict_json(_private_temp_file(profile, "bridge-discovery.json", 4096))
    keys = {"bridge_id", "protocol_version", "origin", "credential_ref", "launch_identity"}
    if (type(data) is not dict or set(data) != keys or data["bridge_id"] != expected
            or data["protocol_version"] != VERSION or data["credential_ref"] != "bridge-wua.token"
            or type(data["launch_identity"]) is not str or not HEX32.fullmatch(data["launch_identity"])
            or type(data["origin"]) is not str):
        raise BridgeFault("identity_mismatch")
    m = ORIGIN.fullmatch(data["origin"])
    if not m or not 1 <= int(m[1]) <= 65535:
        raise BridgeFault("unsafe_origin")
    try:
        token = _private_temp_file(profile, data["credential_ref"], 256).decode("ascii").strip()
    except UnicodeError:
        raise BridgeFault("unsafe_discovery") from None
    if not TOKEN.fullmatch(token):
        raise BridgeFault("unsafe_discovery")
    return Discovery(data["origin"], data["bridge_id"], data["launch_identity"], token)


class SSEDecoder:
    """Incremental UTF-8 / CRLF / CR / LF decoder; comments are not progress."""
    def __init__(self):
        self.utf8 = codecs.getincrementaldecoder("utf-8")("strict")
        self.line = ""
        self.fields = {}
        self.data = []
        self.size = 0
        self.cr = False

    def _line(self, line):
        if not line:
            if not self.data:
                if self.fields:
                    raise BridgeFault("protocol_error")
                return None
            if set(self.fields) != {"event", "id"}:
                raise BridgeFault("protocol_error")
            result = (self.fields["event"], self.fields["id"], strict_json("\n".join(self.data)))
            self.fields, self.data, self.size = {}, [], 0
            return result
        if line.startswith(":"):
            return None
        key, sep, value = line.partition(":")
        if not sep:
            value = ""
        elif value.startswith(" "):
            value = value[1:]
        if key == "data":
            self.data.append(value)
        elif key in ("event", "id"):
            if key in self.fields:
                raise BridgeFault("protocol_error")
            self.fields[key] = value
        else:
            # Standard SSE extension fields (including retry) convey no
            # execution authority; in particular they never trigger retries.
            return None
        self.size += len(line)
        if self.size > MAX_EVENT:
            raise BridgeFault("response_limit")
        return None

    def feed(self, raw):
        try:
            text = self.utf8.decode(raw)
        except UnicodeError:
            raise BridgeFault("protocol_error") from None
        if not text:
            return
        if self.cr and text.startswith("\n"):
            text = text[1:]
        self.cr = False
        pos = 0
        for m in re.finditer(r"\r\n|\r|\n", text):
            self.line += text[pos:m.start()]
            if len(self.line) > MAX_EVENT:
                raise BridgeFault("response_limit")
            item = self._line(self.line)
            self.line = ""
            pos = m.end()
            self.cr = m.group() == "\r" and pos == len(text)
            if item is not None:
                yield item
        self.line += text[pos:]
        if len(self.line) > MAX_EVENT:
            raise BridgeFault("response_limit")

    def eof(self):
        try:
            self.utf8.decode(b"", final=True)
        except UnicodeError:
            raise BridgeFault("protocol_error") from None
        if self.line or self.data or self.fields:
            raise BridgeFault("stream_truncated")


@dataclass(frozen=True)
class FrozenBridgeRequest:
    """Exact wire bytes and expected catalog identity; created before dispatch."""
    wire: bytes = field(repr=False)
    sha256: str
    request_id: str
    target_id: str
    instance_id: str
    bridge_id: str
    manager_id: str
    slot_id: str
    model_id: str
    launch_identity: str
    idle_timeout: int


@dataclass
class StreamResult:
    state: str = "UNKNOWN"
    answer: str = field(default="", repr=False)
    reasoning: str = field(default="", repr=False)
    usage: dict | None = None
    telemetry: dict | None = None
    remote_state: dict | None = field(default=None, repr=False)
    error_code: str | None = None
    finish_reason: str | None = None
    ttft_ms: float | None = None
    elapsed_ms: float | None = None
    complete: bool = False


class _ColibriCatalog:
    """Shared validated HTTP and catalog projection for explicitly bound profiles."""

    _JSON_TIMEOUT = 15
    _CONNECT_TIMEOUT = 5.0
    _CATALOG_ONLY = False
    _READS = {"/health": "Health", "/models": "Catalog"}

    def _fresh(self):
        d = _discover(self.profile, self.expected)
        # A changed origin/launch must be explicitly re-bound before a new
        # request. A token rotation alone is not a new request identity.
        return self._same_launch(d)

    def _same_launch(self, d):
        if (d.origin, d.launch_identity) != (self._descriptor.origin, self._descriptor.launch_identity):
            raise BridgeFault("identity_mismatch")
        return d

    def _client(self, read_timeout):
        return httpx.Client(follow_redirects=False, trust_env=False,
                            timeout=httpx.Timeout(float(read_timeout), connect=self._CONNECT_TIMEOUT),
                            headers={"Accept-Encoding":"identity"})

    @staticmethod
    def _headers(d):
        return {"Authorization":"Bearer " + d.token, "Content-Type":"application/json"}

    def _error(self, response):
        try:
            b = bytearray()
            for part in response.iter_raw():
                b.extend(part)
                if len(b) > 8192:
                    raise BridgeFault("protocol_error")
            u = self.contract.check("Error", strict_json(bytes(b)))
            raise BridgeFault(u["code"], response.status_code)
        except BridgeFault:
            raise
        except (httpx.HTTPError, OSError):
            raise BridgeFault("transport_error") from None

    def _json(self, path, name, body=None):
        if self._CATALOG_ONLY and (body is not None or type(path) is not str
                                   or path not in self._READS or name != self._READS[path]):
            raise BridgeFault("readonly_route_refused")
        d = self._fresh()
        try:
            with self._client(self._JSON_TIMEOUT) as client, client.stream(
                    "GET" if body is None else "POST", d.origin + "/bridge/v1" + path,
                    headers=self._headers(d), content=None if body is None else canonical(body)) as response:
                if response.status_code != 200:
                    if 300 <= response.status_code < 400:
                        raise BridgeFault("redirect_refused", response.status_code)
                    self._error(response)
                if response.headers.get("content-type","").split(";")[0].strip() != "application/json":
                    raise BridgeFault("protocol_error")
                raw = bytearray()
                for part in response.iter_raw():
                    raw.extend(part)
                    if len(raw) > MAX_JSON:
                        raise BridgeFault("response_limit")
                return self.contract.check(name, strict_json(bytes(raw)))
        except (httpx.HTTPError, OSError):
            raise BridgeFault("transport_error") from None

    def _health(self):
        h = self._json("/health", "Health")
        if h["bridge_id"] != self.expected or "read" not in h["permissions"]:
            raise BridgeFault("identity_mismatch")
        return h

    @staticmethod
    def _target_key(t):
        return "tgt_" + hashlib.sha256(canonical([t[k] for k in
            ("bridge_id", "manager_id", "slot_id", "model_key")])).hexdigest()

    def catalog(self):
        health = self._health()
        cat = self._json("/models", "Catalog")
        if cat["bridge_id"] != self.expected:
            raise BridgeFault("identity_mismatch")
        seen = set()
        for t in cat["targets"]:
            if (t["bridge_id"] != self.expected or t["target_id"] != self._target_key(t)
                    or t["target_id"] in seen or
                    ("chat" in t["allowed_operations"] and
                     (t["status"] != "READY" or not t["instance_id"] or
                      t["capabilities"]["streaming"] != "supported" or "chat" not in health["permissions"]))):
                raise BridgeFault("identity_mismatch")
            seen.add(t["target_id"])
        return cat

class ReadOnlyColibriTransport(_ColibriCatalog):
    """Explicit local Client profile, only the two versioned catalog reads."""

    _CATALOG_ONLY = True
    _JSON_TIMEOUT = 3
    _CONNECT_TIMEOUT = 2.0

    def __init__(self, profile, *, expected_bridge_id):
        p = Path(profile)
        if not p.is_absolute() or p.drive.startswith("\\\\") or ".." in p.parts:
            raise BridgeFault("unsafe_profile")
        if type(expected_bridge_id) is not str or not HEX32.fullmatch(expected_bridge_id):
            raise BridgeFault("identity_mismatch")
        self.profile, self.expected = p, expected_bridge_id
        self._descriptor = None
        self._discovery_lock = threading.Lock()
        self.contract = None

    def _fresh(self):
        with self._discovery_lock:
            if os.name == "nt":
                import ctypes
                # DRIVE_FIXED. Disallow network mappings and device/remote profiles.
                if ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(self.profile.anchor)) != 3:
                    raise BridgeFault("unsafe_profile")
            try:
                st = self.profile.lstat()
                if (not stat.S_ISDIR(st.st_mode) or self.profile.resolve(strict=True) != self.profile
                        or getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                    raise BridgeFault("unsafe_profile")
                if os.name != "nt" and (st.st_uid != os.getuid() or st.st_mode & 0o022):
                    raise BridgeFault("unsafe_profile")
            except (OSError, ValueError):
                raise BridgeFault("discovery_unavailable") from None
            descriptor = _discover(self.profile, self.expected)
            if self._descriptor is None:
                self.contract = Contract()
                self._descriptor = descriptor
            return self._same_launch(descriptor)

class OfflineColibriTransport(_ColibriCatalog):
    """Backend-only test transport; explicit disposable profile, no production wiring."""

    def __init__(self, profile, *, expected_bridge_id, idle_timeout=300):
        p = Path(profile).absolute()
        try:
            if (p.resolve(strict=True) != p or not p.is_dir() or
                    Path(tempfile.gettempdir()).resolve() not in p.parents):
                raise BridgeFault("offline_profile_required")
            # Reject junction/reparse paths inside the disposable profile.
            if getattr(p.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise BridgeFault("offline_profile_required")
        except OSError:
            raise BridgeFault("offline_profile_required") from None
        if type(expected_bridge_id) is not str or not HEX32.fullmatch(expected_bridge_id):
            raise BridgeFault("identity_mismatch")
        if type(idle_timeout) is not int or not 1 <= idle_timeout <= 3600:
            raise BridgeFault("invalid_timeout")
        self.profile, self.expected, self.idle_timeout = p, expected_bridge_id, idle_timeout
        self.contract = Contract()
        self._descriptor = _discover(p, expected_bridge_id)
        self._health()  # authenticate before any catalog/Turn traffic

    def prepare(self, *, request_id, target_id, messages, conversation_id, turn_id,
                enabled_targets, options=None, expected_instance_id=None):
        """For a NEW deliberate Turn; re-read READY catalog and actual instance."""
        if target_id not in enabled_targets:
            raise BridgeFault("model_disabled")
        cat = self.catalog()
        t = next((t for t in cat["targets"] if t["target_id"] == target_id), None)
        if not t:
            raise BridgeFault("unknown_target")
        if t["status"] != "READY" or "chat" not in t["allowed_operations"] or not t["instance_id"]:
            raise BridgeFault("target_not_ready")
        if expected_instance_id is not None and expected_instance_id != t["instance_id"]:
            raise BridgeFault("stale_instance")
        req = dict(request_id=request_id, target_id=target_id, instance_id=t["instance_id"],
                   conversation_id=conversation_id, turn_id=turn_id,
                   catalog_revision=cat["catalog_revision"], messages=copy.deepcopy(messages))
        if options is not None:
            req["options"] = copy.deepcopy(options)
        self.contract.check("ChatRequest", req)
        if not req["messages"] or req["messages"][-1]["role"] != "user":
            raise BridgeFault("invalid_request")
        if any(m["role"] not in ("user", "assistant") for m in req["messages"]):
            raise BridgeFault("unsupported_capability")
        for m in req["messages"]:
            if "reasoning_content" in m and (m["role"] != "assistant" or
                    t["capabilities"]["assistant_reasoning_input"] != "supported"):
                raise BridgeFault("unsupported_capability")
            if not m["content"] and not (m["role"] == "assistant" and m.get("reasoning_content")):
                raise BridgeFault("invalid_request")
        for k, v in (req.get("options") or {}).items():
            if v != "auto" and t["capabilities"][k] != "supported":
                raise BridgeFault("unsupported_capability")
        wire = canonical(req)
        if len(wire) > MAX_BODY:
            raise BridgeFault("request_too_large")
        timeout = t["limits"]["idle_timeout_seconds"] or self.idle_timeout
        return FrozenBridgeRequest(wire, hashlib.sha256(wire).hexdigest(), request_id,
            target_id, t["instance_id"], self.expected, t["manager_id"], t["slot_id"],
            t["model_id"], self._descriptor.launch_identity, timeout)

    def _verify_frozen(self, f, *, dispatch=False):
        if (type(f) is not FrozenBridgeRequest or f.bridge_id != self.expected
                or (dispatch and f.launch_identity != self._descriptor.launch_identity)
                or hashlib.sha256(f.wire).hexdigest() != f.sha256
                or len(f.wire) > MAX_BODY):
            raise BridgeFault("identity_mismatch")
        req = self.contract.check("ChatRequest", strict_json(f.wire))
        if any(req[k] != getattr(f,k) for k in ("request_id","target_id","instance_id")):
            raise BridgeFault("identity_mismatch")

    def status(self, f):
        self._verify_frozen(f)
        value = self._json("/requests/" + f.request_id, "RequestStatus")
        self._identity(f, value)
        if value["usage"] is not None:
            self.contract.usage(value["usage"])
        return value

    @staticmethod
    def _identity(f, value):
        if any(value[k] != getattr(f, k) for k in ("request_id","target_id","instance_id")):
            raise BridgeFault("identity_mismatch")

    def cancel(self, f):
        self._verify_frozen(f)
        value = self._json("/chat/cancel", "CancelResponse",
                           {k:getattr(f,k) for k in ("request_id","target_id","instance_id")})
        self._identity(f, value)
        if value["stop_confirmed"] != (value["state"] == "CANCELLED"):
            raise BridgeFault("protocol_error")
        return value

    def run(self, f, *, on_event: Callable[[dict], None] | None = None,
            before_dispatch: Callable[[], None] | None = None):
        """Consume one deliberate request. No replay or new inference on any error.

        Callbacks receive validated packets incrementally. A caller must persist
        its own partial output; this transport returns partial fragments even
        on failure and never calls them a complete response.
        """
        self._verify_frozen(f, dispatch=True)
        result = StreamResult()
        # Authenticate and verify identity again before the physical POST.
        self._health()
        d = self._fresh()
        seq = 0
        terminal = None
        last_error = None
        status_rank = -1
        start = progress = time.monotonic()
        answer, reasoning = [], []
        # A caller may durably reserve the physical dispatch after health and
        # immediately before POST. A refusal here has no wire side effect.
        if before_dispatch is not None:
            before_dispatch()
        try:
            with self._client(f.idle_timeout) as client, client.stream("POST",
                    d.origin + "/bridge/v1/chat/stream", headers=self._headers(d), content=f.wire) as response:
                if response.status_code != 200:
                    if 300 <= response.status_code < 400:
                        raise BridgeFault("redirect_refused", response.status_code)
                    self._error(response)
                if response.headers.get("content-type","").split(";")[0].strip() != "text/event-stream":
                    raise BridgeFault("protocol_error")
                parser, received = SSEDecoder(), 0
                for part in response.iter_raw():
                    received += len(part)
                    if received > MAX_SSE_BYTES:
                        raise BridgeFault("response_limit")
                    if time.monotonic() - progress > f.idle_timeout:
                        raise BridgeFault("transport_timeout")
                    for event_type, event_id, event in parser.feed(part):
                        self.contract.check("Event", event)
                        if (terminal is not None or event["type"] != event_type
                                or event_id != str(seq) or event["sequence"] != seq or
                                event["request_id"] != f.request_id):
                            raise BridgeFault("protocol_error")
                        kind = event["type"]
                        if (seq == 0) != (kind == "meta"):
                            raise BridgeFault("protocol_error")
                        seq += 1
                        if kind == "meta":
                            if any(event[k] != getattr(f,k) for k in
                                    ("bridge_id","target_id","instance_id","manager_id","slot_id","model_id")):
                                raise BridgeFault("identity_mismatch")
                        elif kind == "status":
                            rank = {"ACCEPTED":0,"RUNNING":1,"CANCEL_REQUESTED":2}[event["state"]]
                            if rank < status_rank:
                                raise BridgeFault("protocol_error")
                            status_rank = rank
                        elif kind in ("reasoning", "delta"):
                            progress = time.monotonic()
                            if result.ttft_ms is None:
                                result.ttft_ms = (progress-start)*1000
                            (reasoning if kind == "reasoning" else answer).append(event["text"])
                        elif kind == "usage":
                            result.usage = self.contract.usage(event["usage"])
                        elif kind == "telemetry":
                            result.telemetry = copy.deepcopy(event["telemetry"])
                        elif kind == "error":
                            if last_error is not None or event["error"].get("request_id",f.request_id)!=f.request_id:
                                raise BridgeFault("protocol_error")
                            last_error = event["error"]["code"]
                        elif kind == "done":
                            state, error = event["state"], event["error"]
                            if ((state in {"FAILED","UNKNOWN"}) != (error is not None)
                                    or (error or {}).get("code") != last_error
                                    or (error or {}).get("request_id",f.request_id)!=f.request_id):
                                raise BridgeFault("protocol_error")
                            final_usage = self.contract.usage(event["usage"])
                            if result.usage is not None and result.usage != final_usage:
                                raise BridgeFault("protocol_error")
                            terminal = event
                            result.usage = final_usage
                        if on_event is not None and kind != "done":
                            try:
                                on_event(copy.deepcopy(event))
                            except Exception:
                                raise BridgeFault("event_consumer_failed") from None
                parser.eof()
                if terminal is None:
                    raise BridgeFault("stream_truncated")
                # Only publish a terminal callback after validation of EOF;
                # an extra event after done is a malformed response, not success.
                if on_event is not None:
                    try:
                        on_event(copy.deepcopy(terminal))
                    except Exception:
                        raise BridgeFault("event_consumer_failed") from None
                result.state = terminal["state"]
                result.finish_reason = terminal["finish_reason"]
                result.error_code = (terminal["error"] or {}).get("code")
                result.complete = result.state == "SUCCEEDED"
        except (BridgeFault, httpx.HTTPError, OSError) as exc:
            result.error_code = (exc.code if isinstance(exc,BridgeFault) else
                "transport_timeout" if isinstance(exc,httpx.TimeoutException) else "transport_error")
            # Query the durable journal, never infer success or retry from it.
            try:
                result.remote_state = self.status(f)
            except BridgeFault:
                pass
            if (isinstance(exc,BridgeFault) and exc.code in PRECLAIM and
                    exc.status in {400,401,403,404,409,413,422} and not seq
                    and result.remote_state is None):
                result.state = "REJECTED"
        result.answer = "".join(answer)
        result.reasoning = "".join(reasoning)
        result.elapsed_ms = (time.monotonic()-start)*1000
        return result
