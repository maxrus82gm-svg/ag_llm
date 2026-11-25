"""WUA-1: read model of Ultra model connections and the saved model choice (EVM tab).

One Ultra core, two interfaces: the API connections shown here are derived on every
read from the shared root ``model_registry`` (``list_model_specs`` /
``get_model_spec``); this module keeps no catalogue of its own. It stores only the
web interface's choice - a ``connection_id`` that names an existing ``model_id`` -
under the Web Alarm storage root. It never touches the Tkinter Ultra ``ui_state.json``,
never imports the GigaChat transport, reads no credentials and makes no network call.

Statuses are local facts only: ``REGISTERED`` (the model is in the registry and
enabled) or ``DISABLED``; ``verification`` is always ``UNVERIFIED`` at this stage -
presence in the registry is not a proven API connection.
"""

from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from .models import new_id, utc_now_iso
from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS, InterProcessLock, StoreLockTimeout

SCHEMA = "web_alarm.ultra_connections"
SCHEMA_VERSION = 1
ROLES = ("chat",)  # the future Ultra Web Chat; other Ultra roles are not moved yet
API_KIND = "api"
MAX_ID_LENGTH = 200
UNVERIFIED = "UNVERIFIED"
REGISTERED = "REGISTERED"
DISABLED = "DISABLED"


class UltraConnectionsError(RuntimeError):
    """Base error of the connections read model."""


class ConnectionRequestError(UltraConnectionsError):
    """The request itself is malformed (role, connection_id)."""


class UnknownConnectionError(UltraConnectionsError):
    """The connection_id names no model of the shared registry."""


class DisabledConnectionError(UltraConnectionsError):
    """The model exists in the shared registry but is disabled there."""


class RegistryUnavailableError(UltraConnectionsError):
    """The shared model registry cannot be imported."""


class SelectionStoreError(UltraConnectionsError):
    """The saved choice cannot be persisted."""


def _registry():
    try:
        import model_registry  # the shared Ultra registry at the repository root
    except ImportError as exc:  # pragma: no cover - depends on how the server is launched
        raise RegistryUnavailableError("shared model_registry is not importable") from exc
    return model_registry


def connection_id_for(spec: Any) -> str:
    """Stable connection identity of a registry model: ``api:<provider>:<model_id>``."""
    return f"{'local' if spec.is_local else API_KIND}:{spec.provider}:{spec.model_id}"


def _parse_connection_id(value: Any) -> tuple[str, str, str]:
    if not isinstance(value, str) or not value or len(value) > MAX_ID_LENGTH or not value.isascii():
        raise ConnectionRequestError("connection_id must be a short ASCII string")
    parts = value.split(":")
    if len(parts) != 3 or parts[0] not in (API_KIND, "local") or not all(parts):
        raise ConnectionRequestError("connection_id must look like api:<provider>:<model_id>")
    return parts[0], parts[1], parts[2]


def _role(value: Any) -> str:
    if value not in ROLES:
        raise ConnectionRequestError(f"role must be one of: {', '.join(ROLES)}")
    return value


class UltraConnections:
    def __init__(
        self,
        storage_root: str | os.PathLike[str],
        *,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        root = Path(storage_root)
        self.path = root / "ultra" / "connections.json"
        self.lock_path = root / "locks" / "ultra" / "connections.lock"
        self.lock_timeout = lock_timeout
        self.model_cards = None  # Bound by the existing Web Alarm API; no second settings store.
        self._colibri_transport = None
        self.colibri_mode = "NOT_CONNECTED"
        self._catalog_lock = threading.RLock()
        self._local_catalog = ((), "NOT_CONNECTED", None)

    @property
    def has_colibri(self):
        return self._colibri_transport is not None

    def bind_offline_colibri(self, transport):
        from .colibri_bridge_transport import OfflineColibriTransport
        import tempfile
        root=self.path.parent.parent.resolve()
        if (type(transport) is not OfflineColibriTransport
                or Path(tempfile.gettempdir()).resolve() not in root.parents
                or self._colibri_transport is not None and self._colibri_transport is not transport):
            raise ValueError("Only the same isolated server may bind Colibri")
        self._colibri_transport=transport
        self.colibri_mode = "OFFLINE"

    def bind_readonly_colibri(self, transport):
        from .colibri_bridge_transport import ReadOnlyColibriTransport
        if (type(transport) is not ReadOnlyColibriTransport
                or self._colibri_transport is not None and self._colibri_transport is not transport):
            raise ValueError("Only the explicitly configured read-only Bridge may be bound")
        self._colibri_transport = transport
        self.colibri_mode = "READ_ONLY"

    def registry_snapshot(self, *, refresh=True):
        """Read authenticated discovery once, fail closed without erasing known IDs.
        This is a transient projection; EVM settings remain the only persisted switch.
        """
        registry=_registry()
        if not self.has_colibri:
            return registry, (), "NOT_CONNECTED"
        from .colibri_bridge_transport import BridgeFault
        if refresh:
            with self._catalog_lock:
                try:
                    catalog=self._colibri_transport.catalog()
                    targets=deepcopy(catalog["targets"])
                    if len(targets)>500:
                        raise BridgeFault("response_limit")
                    if self.colibri_mode == "READ_ONLY":
                        # The shared registry uses allowed_operations for execution eligibility.
                        for target in targets:
                            target["allowed_operations"] = []
                    self._local_catalog = (tuple(targets), "AVAILABLE", None)
                except BridgeFault as exc:
                    previous = self._local_catalog[0]
                    targets = tuple({**t, "status": "UNKNOWN", "allowed_operations": []} for t in previous)
                    self._local_catalog = (targets, "UNAVAILABLE", exc.code)
        targets, state, _ = self._local_catalog
        targets = deepcopy(targets)
        return registry.ModelRegistryView(targets), targets, state

    def local_target(self, model_id, *, refresh=True):
        _reg,targets,_state=self.registry_snapshot(refresh=refresh)
        return next((t for t in targets if t["target_id"]==model_id),None)

    def enabled_local_targets(self):
        if self.colibri_mode == "READ_ONLY":
            return set()
        registry,_,_=self.registry_snapshot()
        return {s.model_id for s in registry.list_model_specs()
                if s.is_local and s.enabled and self.model_cards is not None
                and self.model_cards.is_enabled(s.model_id)}


    # --- shared registry -------------------------------------------------------------

    def _spec(self, connection_id: Any, registry=None):
        """The registry model a connection_id names (unknown/disabled are refused)."""
        kind,provider,model_id = _parse_connection_id(connection_id)
        if registry is None:
            registry = self.registry_snapshot(refresh=self.colibri_mode != "READ_ONLY")[0]
        spec = registry.MODEL_REGISTRY.get(model_id)
        if spec is None or spec.provider != provider or spec.is_local != (kind=="local"):
            raise UnknownConnectionError(f"no model {model_id!r} of provider {provider!r} in the shared registry")
        try:
            return registry.get_model_spec(model_id)  # the registry's own rules (e.g. disabled)
        except RuntimeError as exc:
            raise DisabledConnectionError(f"model {model_id!r} is disabled in the shared registry") from exc
        except (KeyError, ValueError) as exc:
            raise UnknownConnectionError(str(exc)) from exc

    def _view(self, spec: Any, selected_id: str | None) -> dict[str, Any]:
        connection_id = connection_id_for(spec)
        enabled = bool(spec.enabled) and (self.model_cards is None or self.model_cards.is_enabled(spec.model_id))
        return {
            "connection_id": connection_id,
            "kind": "local" if spec.is_local else API_KIND,
            "provider": spec.provider,
            "model_id": spec.model_id,
            "display_name": spec.display_name,
            "provider_model_id": spec.provider_model_id,
            "is_local": spec.is_local,
            "registry_enabled": spec.enabled,
            "status": REGISTERED if enabled else DISABLED,
            "verification": UNVERIFIED,
            "selectable": enabled,
            "selected": connection_id == selected_id,
        }

    # --- saved choice ----------------------------------------------------------------

    def _read(self) -> dict[str, Any]:
        """Saved choice per role; a damaged file is reported, never replaced by a default."""
        if not self.path.exists():
            return {"state": "NOT_SELECTED", "roles": {}}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or raw.get("version") != SCHEMA_VERSION:
                raise ValueError("unknown schema or version")
            roles = raw.get("roles")
            if not isinstance(roles, dict):
                raise ValueError("roles must be an object")
            clean = {}
            for role, entry in roles.items():
                if role not in ROLES:
                    continue  # a newer role is kept on disk, not shown here
                if not isinstance(entry, dict) or not isinstance(entry.get("connection_id"), str):
                    raise ValueError(f"role {role!r} has no connection_id")
                clean[role] = {"connection_id": entry["connection_id"], "selected_at": entry.get("selected_at")}
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return {"state": "CORRUPT", "roles": {}, "reason": f"saved choice is unreadable: {type(exc).__name__}"}
        return {"state": "SAVED" if clean else "NOT_SELECTED", "roles": clean}

    def selection(self, role: str = "chat", *, registry=None) -> dict[str, Any]:
        """The saved choice of ``role`` resolved against the registry as it is now."""
        role = _role(role)
        saved = self._read()
        entry = saved["roles"].get(role)
        result: dict[str, Any] = {"role": role, "state": saved["state"], "connection_id": None,
                                  "model_id": None, "display_name": None, "provider_model_id": None,
                                  "selected_at": None}
        if saved["state"] == "CORRUPT":
            result["reason"] = saved["reason"]
            return result
        if entry is None:
            result["state"] = "NOT_SELECTED"
            return result
        result.update(connection_id=entry["connection_id"], selected_at=entry["selected_at"])
        try:
            spec = self._spec(entry["connection_id"],registry)
        except (ConnectionRequestError, UnknownConnectionError, DisabledConnectionError) as exc:
            result.update(state="INVALID_REFERENCE", reason=str(exc))
            return result
        except RegistryUnavailableError as exc:
            result.update(state="REGISTRY_UNAVAILABLE", reason=str(exc))
            return result
        result.update(state="SAVED", model_id=spec.model_id, display_name=spec.display_name,
                      provider_model_id=spec.provider_model_id)
        return result

    def catalog(self, *, snapshot=None) -> dict[str, Any]:
        """The three EVM columns. Colibri reads require an explicit binding."""
        local={"state":"NOT_CONNECTED","connections":[]}
        try:
            registry,targets,state=snapshot if snapshot is not None else self.registry_snapshot()
            selection=self.selection("chat",registry=registry)
            selected_id=selection["connection_id"] if selection["state"]=="SAVED" else None
            specs=registry.list_model_specs()
            api={"state":"AVAILABLE","connections":[self._view(s,selected_id) for s in specs if not s.is_local]}
            by_id={t["target_id"]:t for t in targets}
            local={"state":state,"connections":[{**self._view(s,selected_id),
                "availability":by_id[s.model_id]["status"],
                "instance_id":by_id[s.model_id]["instance_id"],
                "manager_name":by_id[s.model_id]["manager_name"],
                "slot_id":by_id[s.model_id]["slot_id"]}
                for s in specs if s.is_local]}
            if self.has_colibri:
                local["mode"] = self.colibri_mode
            if self.colibri_mode == "READ_ONLY" and state == "UNAVAILABLE":
                local["reason"] = self._local_catalog[2]
        except RegistryUnavailableError as exc:
            selection=self.selection("chat")
            api={"state":"REGISTRY_UNAVAILABLE","connections":[],"reason":str(exc)}
        return {
            "source": "model_registry",
            "verification_note": "registry entries are not proven API connections; no API check was made",
            "network_calls": None if self.has_colibri else 0,
            "columns": {
                "api": api,
                "mcp_agents": {"state": "NOT_CONNECTED", "connections": []},
                "local_llm": local,
            },
            "selection": {"chat": selection},
        }

    def select(self, role: Any, connection_id: Any) -> dict[str, Any]:
        """Save ``connection_id`` as the web choice of ``role`` (refused unless selectable now)."""
        role = _role(role)
        spec = self._spec(connection_id)
        if spec.is_local:
            raise ConnectionRequestError("Local model selection belongs to an ordinary chat")
        if self.model_cards is not None and not self.model_cards.is_enabled(spec.model_id):
            raise DisabledConnectionError(f"model {spec.model_id!r} is disabled in EVM")
        lock = InterProcessLock(self.lock_path, timeout=self.lock_timeout)
        try:
            lock.acquire()
        except StoreLockTimeout as exc:
            raise SelectionStoreError(f"connections lock not acquired: {exc}") from exc
        try:
            current = self._read()
            roles: dict[str, Any] = {}
            if current["state"] == "CORRUPT":
                self._set_aside()
            else:
                roles = self._raw_roles()
            roles[role] = {"connection_id": connection_id_for(spec), "model_id": spec.model_id,
                           "selected_at": utc_now_iso()}
            self._write({"schema": SCHEMA, "version": SCHEMA_VERSION, "roles": roles})
        finally:
            lock.release()
        return self.selection(role)

    def resolve_provider_model_id(self, role: str = "chat") -> str:
        """For the future Ultra Web Chat: the existing provider_model_id of the saved choice."""
        current = self.selection(role)
        if current["state"] != "SAVED" or str(current["connection_id"]).startswith("local:"):
            raise UnknownConnectionError(f"no usable saved connection for role {role!r}: {current['state']}")
        return current["provider_model_id"]

    # --- persistence -------------------------------------------------------------------

    def _raw_roles(self) -> dict[str, Any]:
        """All roles on disk, including ones this version does not show (kept, not dropped)."""
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return dict(raw["roles"])

    def _set_aside(self) -> None:
        """A damaged file is kept next to the new one for diagnosis, never silently lost."""
        try:
            os.replace(self.path, self.path.with_name(f"{self.path.name}.corrupt-{new_id('ultra')}"))
        except OSError as exc:
            raise SelectionStoreError(f"damaged saved choice could not be set aside: {exc}") from exc

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(f".{self.path.name}.{new_id('tmp')}.tmp")
        try:
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise SelectionStoreError(f"saved choice could not be persisted: {exc}") from exc
