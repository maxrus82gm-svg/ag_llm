"""Explicit, durable READ_ONLY binding for a registered STANDARD instance."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import tempfile

from .colibri_bridge_transport import BridgeFault, ReadOnlyColibriTransport
from .models import utc_now_iso
from .store_lock import InterProcessLock, StoreLockTimeout

_HEX = re.compile(r"[0-9a-f]{32}\Z")
_ORIGIN = re.compile(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})\Z")
_MAX_BYTES = 8192


class BindingError(ValueError):
    """Bounded diagnostic, no raw file or secret text."""


def require(condition, reason):
    if not condition:
        raise BindingError(reason)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "binding_corrupt")
        result[key] = value
    return result


def validate_profile(profile, bridge_id):
    require(type(profile) is str and 0 < len(profile) <= 2048
            and all(ord(c) >= 32 and ord(c) != 127 for c in profile), "unsafe_profile")
    path = Path(profile)
    require(path.is_absolute() and not path.drive.startswith("\\\\")
            and ".." not in path.parts, "unsafe_profile")
    require(type(bridge_id) is str and _HEX.fullmatch(bridge_id), "identity_mismatch")
    return path


@dataclass(frozen=True)
class ClientBinding:
    profile: str
    bridge_id: str
    origin: str
    launch_identity: str

    def __post_init__(self):
        validate_profile(self.profile, self.bridge_id)
        require(type(self.launch_identity) is str and _HEX.fullmatch(self.launch_identity), "identity_mismatch")
        match = _ORIGIN.fullmatch(self.origin) if type(self.origin) is str else None
        require(match is not None and 1 <= int(match[1]) <= 65535, "unsafe_origin")


class BindingStore:
    def __init__(self, storage_root):
        self.path = Path(storage_root) / "ultra" / "colibri_binding.json"

    def load(self):
        try:
            with self.path.open("rb") as stream:
                raw = stream.read(_MAX_BYTES + 1)
        except FileNotFoundError:
            return None
        except OSError:
            raise BindingError("binding_unavailable") from None
        try:
            require(len(raw) <= _MAX_BYTES, "binding_corrupt")
            data = json.loads(raw, object_pairs_hook=unique_pairs)
            require(type(data) is dict and set(data) == {"schema", "binding"}
                    and type(data["schema"]) is int and data["schema"] == 1, "binding_corrupt")
            value = data["binding"]
            if value is None:
                return None
            require(type(value) is dict and set(value) ==
                    {"profile", "bridge_id", "origin", "launch_identity"}, "binding_corrupt")
            return ClientBinding(**value)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            raise BindingError("binding_corrupt") from None

    def replace(self, value, *, expected):
        """Compare-and-replace under caller's store lock."""
        require(value is None or type(value) is ClientBinding, "invalid_binding")
        require(self.load() == expected, "binding_changed")
        body = json.dumps({"schema": 1, "binding": asdict(value) if value else None},
                          ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8") + b"\n"
        require(len(body) <= _MAX_BYTES, "invalid_binding")
        temp = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="wb", dir=self.path.parent,
                                             prefix=".colibri_binding-", delete=False) as stream:
                temp = Path(stream.name)
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.path)
        except OSError:
            raise BindingError("binding_unavailable") from None
        finally:
            if temp is not None:
                try:
                    temp.unlink(missing_ok=True)
                except OSError:
                    pass


class ManagedClient:
    """Shares the existing registry/catalog lock and the H46 transport."""
    def __init__(self, connections):
        self.connections = connections
        root = connections.path.parent.parent
        self.store = BindingStore(root)
        self.lock_path = root / "locks" / "ultra" / "colibri_binding.lock"
        self.current = None
        self.loaded = False
        self.last_success_at = None

    def _store_lock(self):
        return InterProcessLock(self.lock_path, timeout=self.connections.lock_timeout)

    def _restore(self):
        if self.loaded:
            return
        value = self.store.load()
        if value is not None:
            transport = ReadOnlyColibriTransport(
                value.profile, expected_bridge_id=value.bridge_id,
                expected_launch=(value.origin, value.launch_identity))
            self.connections._colibri_transport = transport
            self.connections._local_catalog = ((), "UNAVAILABLE", "refresh_required")
        self.current = value
        self.loaded = True

    def _check_store(self):
        self._restore()
        require(self.store.load() == self.current, "binding_changed")

    def _status(self):
        _, state, reason = self.connections._local_catalog
        return {"available": True, "binding": asdict(self.current) if self.current else None,
                "state": state, "reason": reason, "last_success_at": self.last_success_at}

    def status(self):
        with self.connections._catalog_lock:
            try:
                with self._store_lock():
                    self._check_store()
                    return self._status()
            except (BindingError, StoreLockTimeout, OSError) as exc:
                reason = str(exc) if isinstance(exc, BindingError) else "binding_unavailable"
                self._mark_unavailable(reason)
                return {**self._status(), "state": "ERROR", "reason": reason}

    @staticmethod
    def _read(transport):
        targets = deepcopy(transport.catalog()["targets"])
        if len(targets) > 500:
            raise BridgeFault("response_limit")
        for target in targets:
            target["allowed_operations"] = []
        return tuple(targets)

    def _mark_unavailable(self, reason):
        previous = self.connections._local_catalog[0]
        targets = tuple({**t, "status": "UNKNOWN", "allowed_operations": []} for t in previous)
        self.connections._local_catalog = (targets, "UNAVAILABLE", reason)

    def act(self, action, body):
        require(action in {"connect", "refresh", "disconnect"}, "invalid_binding_action")
        require(type(body) is dict, "invalid_binding")
        if action == "connect":
            require(set(body) == {"profile", "bridge_id"}, "invalid_binding")
            validate_profile(body["profile"], body["bridge_id"])
        else:
            require(not body, "invalid_binding")
        with self.connections._catalog_lock:
            try:
                with self._store_lock():
                    self._check_store()
                    if action == "connect":
                        candidate = ReadOnlyColibriTransport(body["profile"], expected_bridge_id=body["bridge_id"])
                        targets = self._read(candidate)
                        origin, launch = candidate.confirmed_launch()
                        value = ClientBinding(str(candidate.profile), candidate.expected, origin, launch)
                        self.store.replace(value, expected=self.current)
                        self.current = value
                        self.connections._colibri_transport = candidate
                        self.connections._local_catalog = (targets, "AVAILABLE", None)
                        self.last_success_at = utc_now_iso()
                    elif action == "refresh":
                        require(self.current is not None, "not_connected")
                        try:
                            targets = self._read(self.connections._colibri_transport)
                        except BridgeFault as exc:
                            self._mark_unavailable(exc.code)
                        else:
                            self.connections._local_catalog = (targets, "AVAILABLE", None)
                            self.last_success_at = utc_now_iso()
                    else:
                        if self.current is not None:
                            self.store.replace(None, expected=self.current)
                        self.current = None
                        self.connections._colibri_transport = None
                        self.connections._local_catalog = ((), "NOT_CONNECTED", None)
                        self.last_success_at = None
                    return self._status()
            except (StoreLockTimeout, OSError):
                raise BindingError("binding_unavailable") from None
