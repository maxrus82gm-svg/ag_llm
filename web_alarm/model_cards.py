"""EVM model cards: card data, real role assignments and one server-side API status per model.

One Ultra core. The models are the shared root ``model_registry`` (read through ``UltraConnections``);
the web chat choice is the one ``UltraConnections`` keeps; the Planner / Verifier / Compressor /
Executor assignments are the Tkinter Ultra settings file ``ui_state.json``, read only, never written
and never copied into a second assignment store. This module keeps only what has no other owner:

* ``ultra/model_settings.json`` - what the user edits: per-model card data (description, parameter
  count, which connection profile serves the model) and, separately, the non-secret connection
  profiles of providers and manually added provider entries. No secret is ever stored here;
* ``ultra/api_checks.json`` - the evidence behind the API status: the settings version a confirmed
  answer belongs to, its time, the last refusal and a bounded diagnostic text;
* ``ultra/evm_view.json`` - how the user arranges the EVM board: the manual order of each column and
  the ordered favourites, as lists of connection ids (references, never copies of a registry entry).

Secrets stay with the existing mechanism (``GIGACHAT_CREDENTIALS`` in the environment, read by
``gigachat_transport``); this module only tells whether that variable is present. It makes no
network call and never imports a transport: a live check needs a separately authorised checker, and
the shipped default refuses with ``LIVE_CHECK_NOT_AUTHORIZED`` without changing any state. Only a
checker that reports a live answer can confirm a model; a simulated answer never turns a card green.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .models import new_id
from .store_lock import DEFAULT_LOCK_TIMEOUT_SECONDS, InterProcessLock, StoreLockTimeout
from .ultra_connections import UltraConnections, connection_id_for

SETTINGS_SCHEMA = "web_alarm.ultra_model_settings"
CHECKS_SCHEMA = "web_alarm.ultra_api_checks"
VIEW_SCHEMA = "web_alarm.ultra_evm_view"
SCHEMA_VERSION = 1
# EVM board: a column section -> the catalog column it shows and the connection kind its ids carry.
BOARD_COLUMNS = {"api": ("api", "api"), "mcp": ("mcp_agents", "mcp"), "local": ("local_llm", "local")}
VIEW_SECTIONS = ("favorites", *BOARD_COLUMNS)
MAX_VIEW_IDS = 500
_CONNECTION_ID = re.compile(r"(api|mcp|local):[A-Za-z0-9_.-]{1,80}:[A-Za-z0-9_.-]{1,110}")
MAX_STORE_BYTES = 2 * 1024 * 1024
MAX_TK_STATE_BYTES = 1024 * 1024
MAX_DESCRIPTION = 500
MAX_PARAMS_BILLION = 100_000
MAX_TITLE = 80
MAX_ERROR_TEXT = 300
DEFAULT_FRESHNESS_DAYS = 30
DEFAULT_TIMEOUT_SECONDS = 30  # the timeout gigachat_transport uses for its own requests
DEFAULT_DIAGNOSTIC_LIMIT = 1000
LIMITS = {"freshness_days": (1, 365), "timeout_seconds": (5, 120), "diagnostic_limit_chars": (200, 4000)}
PROFILE_DEFAULTS = {"freshness_days": DEFAULT_FRESHNESS_DAYS, "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
                    "diagnostic_limit_chars": DEFAULT_DIAGNOSTIC_LIMIT}
FUTURE_TOLERANCE = timedelta(minutes=5)
TEST_MESSAGE = "Привет. Подтверди получение тестового сообщения."
_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,79}")
_SECRETISH = re.compile(r"(?i)\b(basic|bearer)\s+[A-Za-z0-9._~+/=-]{6,}")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

# API status colours shared by the card and the diagnostic window.
GREEN, ORANGE, RED = "green", "orange", "red"


class ModelCardsError(RuntimeError):
    """Base error of the model cards service."""


class ModelCardRequestError(ModelCardsError):
    """The request is malformed (unknown field, bad value, wrong profile)."""


class UnknownModelCardError(ModelCardsError):
    """No model with this id in the shared registry."""


class SettingsConflictError(ModelCardsError):
    """The settings changed since the page read them (another window saved first)."""


class CheckRefusedError(ModelCardsError):
    """A check cannot run for this model (disabled in the registry, no adapter)."""


class ModelCardsStoreError(ModelCardsError):
    """The settings or check evidence cannot be persisted."""


# --- providers ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Provider:
    provider_id: str
    display_name: str
    country: str
    adapter: str | None  # an adapter module of this repository, or None: no adapter yet
    auth: str
    credential_env: str | None = None
    scope_env: str | None = None
    default_scope: str | None = None
    oauth_url: str | None = None
    api_url: str | None = None
    source: str = "builtin"


# The endpoints and environment names are those of gigachat_transport (a test keeps them equal); the
# transport itself is not imported, so this module cannot send anything.
BUILTIN_PROVIDERS = {
    "gigachat": Provider(
        provider_id="gigachat",
        display_name="GigaChat",
        country="Россия",
        adapter="gigachat_transport",
        auth="OAuth: ключ авторизации (Basic) из переменной среды → токен доступа на 25 минут",
        credential_env="GIGACHAT_CREDENTIALS",
        scope_env="GIGACHAT_SCOPE",
        default_scope="GIGACHAT_API_PERS",
        oauth_url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        api_url="https://api.giga.chat/v1/chat/completions",
    ),
}
SCOPE_LABELS = {
    "GIGACHAT_API_PERS": "Физическое лицо · PERS",
    "GIGACHAT_API_B2B": "ИП и юрлица, предоплата · B2B",
    "GIGACHAT_API_CORP": "ИП и юрлица, постоплата · CORP",
}


def default_profile_id(provider_id: str) -> str:
    return f"{provider_id}-default"


def _adapter_state(provider: Provider) -> str:
    if provider.adapter is None:
        return "MISSING"
    try:
        found = importlib.util.find_spec(provider.adapter) is not None  # locates, does not import
    except (ImportError, ValueError):
        found = False
    return "AVAILABLE" if found else "MISSING"


# --- roles ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Role:
    role: str
    label: str
    hint: str
    field: str | None = None  # the Tk ui_state key with the model id
    enabled_field: str | None = None  # the Tk ui_state switch that turns the role on
    linked_to: str | None = None
    exists: bool = True
    runs: bool = True  # False: the assignment is real, but no runtime path uses it yet


ROLES = (
    Role("chat", "Чат", "Модель обычного Ultra Chat в браузере: будет отвечать пользователю в диалоге. Выбирается в "
         "Web Alarm — сейчас в EVM над карточками, позже у поля ввода сообщения. Пока Ultra Chat только читает "
         "историю, эта роль ничего не отправляет.", runs=False),
    Role("planner", "Планировщик", "Составляет план TASK по этапам до начала работы и пересматривает его по фактам "
         "сервера; сам ничего не выполняет. Модель и включение — в настройках прежней Ultra (Tkinter).",
         field="planner_model_id", enabled_field="planner_enabled"),
    Role("verifier", "Верификатор", "Проверяет результаты по доказательствам сервера. Его модель используют Doctor "
         "Dredd и Final Review. Модель — в настройках прежней Ultra (Tkinter).", field="verifier_model_id"),
    Role("compressor", "Компрессор", "Сжимает историю диалога в рабочее представление, чтобы контекст помещался в "
         "лимит модели. Модель — в настройках прежней Ultra (Tkinter).", field="compressor_model_id"),
    Role("doctor_dredd", "Doctor Dredd", "Разовый арбитр: после повторной ошибки плана проверяет разговор с "
         "Планировщиком и советует исправление; TASK не исполняет. Своего назначения нет — работает на модели "
         "Верификатора, пока включён Планировщик.", field="verifier_model_id", enabled_field="planner_enabled",
         linked_to="verifier"),
    Role("executor", "Executor", "Основная модель (Main) прежней Ultra: выполняет TASK с инструментами по плану. "
         "Задаётся в прежней Ultra (Tkinter) как модель основного чата.", field="main_chat_model_id"),
    Role("final_review", "Final Review", "Итоговая проверка (Final Audit) выполненной TASK по плану и "
         "доказательствам. Своего назначения нет — использует модель Верификатора; включается в прежней Ultra.",
         field="verifier_model_id", enabled_field="final_audit_enabled", linked_to="verifier"),
    Role("context", "Context", "Отдельной роли контекста в runtime пока нет: контекст собирает сервер по политике "
         "роли. Назначение модели появится только после архитектурного решения.", exists=False),
)
TK_MODEL_FIELDS = ("main_chat_model_id", "planner_model_id", "verifier_model_id", "compressor_model_id")
TK_SWITCHES = ("planner_enabled", "final_audit_enabled")


def _tk_defaults() -> dict[str, Any]:
    import ui_state  # the Tk owner of these defaults; importing it reads nothing from disk

    defaults = ui_state.default_ui_state()
    return {key: defaults[key] for key in TK_MODEL_FIELDS + TK_SWITCHES}


def default_tk_state_path() -> Path:
    import ui_state

    return Path(ui_state.STATE_PATH)


def read_tk_assignments(path: Path | None, registry: Any) -> dict[str, Any]:
    """The assignments Tk Ultra runs with, read only, mirroring ``ui_state.load_ui_state`` and the Tk
    fallback to its default when a saved model is unknown or disabled in the registry."""
    if path is None:
        return {"state": "NOT_CONNECTED", "values": {}, "fallbacks": []}
    defaults = _tk_defaults()
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_TK_STATE_BYTES + 1)
    except FileNotFoundError:
        loaded: dict[str, Any] | None = None
    except OSError as exc:
        return {"state": "UNREADABLE", "values": {}, "fallbacks": [], "reason": type(exc).__name__}
    else:
        if len(raw) > MAX_TK_STATE_BYTES:
            return {"state": "UNREADABLE", "values": {}, "fallbacks": [], "reason": "too_large"}
        try:
            loaded = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError):
            return {"state": "UNREADABLE", "values": {}, "fallbacks": [], "reason": "invalid_json"}
        if not isinstance(loaded, dict):
            return {"state": "UNREADABLE", "values": {}, "fallbacks": [], "reason": "not_an_object"}
    values = dict(defaults)
    if loaded is not None:
        for key in TK_MODEL_FIELDS:
            if isinstance(loaded.get(key), str):
                values[key] = loaded[key]
        for key in TK_SWITCHES:
            if isinstance(loaded.get(key), bool):
                values[key] = loaded[key]
    fallbacks = []
    for key in TK_MODEL_FIELDS:
        spec = registry.MODEL_REGISTRY.get(values[key])
        if spec is None or not spec.enabled:  # Tk itself falls back to its default here
            fallbacks.append({"field": key, "saved": safe_text(values[key], 80)})
            values[key] = defaults[key]
    return {"state": "DEFAULTS" if loaded is None else "SAVED", "values": values, "fallbacks": fallbacks}


def role_states(model_id: str, tk: Mapping[str, Any], chat: Mapping[str, Any]) -> list[dict[str, str]]:
    """``assigned`` / ``assigned_off`` (the role is switched off) / ``assigned_pending`` (assigned, but no runtime
    path uses the role yet) / ``not_assigned`` / ``not_in_runtime`` / ``unknown`` (the source cannot be read) for
    every role, from the real sources only."""
    result = []
    for role in ROLES:
        if not role.exists:
            state = "not_in_runtime"
        elif role.role == "chat":
            if chat.get("state") == "SAVED":
                state = "assigned" if chat.get("model_id") == model_id else "not_assigned"
            elif chat.get("state") == "NOT_SELECTED":
                state = "not_assigned"
            else:
                state = "unknown"
        elif tk["state"] not in ("SAVED", "DEFAULTS"):
            state = "unknown"
        elif tk["values"][role.field] != model_id:
            state = "not_assigned"
        elif role.enabled_field and not tk["values"][role.enabled_field]:
            state = "assigned_off"
        else:
            state = "assigned"
        if state == "assigned" and not role.runs:
            state = "assigned_pending"
        result.append({"role": role.role, "state": state})
    return result


# --- checkers -------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckRequest:
    connection_id: str
    model_id: str
    provider_id: str
    provider_model_id: str
    api_url: str | None
    timeout_seconds: int
    message: str


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    live: bool  # a real answer of the provider; a simulation is never recorded as a confirmation
    reply: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class ApiChecker(Protocol):
    authorized: bool
    reason: str

    def check(self, request: CheckRequest) -> CheckResult: ...


class LiveCheckNotAuthorized:
    """The shipped checker: a real request to a paid API needs a separate user decision."""

    authorized = False
    reason = ("Настоящий запрос к API в этой версии не разрешён: нужен отдельный USER GO "
              "(ключи, тарифицируемые запросы).")

    def check(self, request: CheckRequest) -> CheckResult:  # pragma: no cover - never called while unauthorised
        raise CheckRefusedError(self.reason)


# --- helpers ---------------------------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def safe_text(value: Any, limit: int) -> str:
    """Bounded display text: no control characters, nothing that looks like an Authorization value."""
    text = _CONTROL.sub(" ", str(value))
    text = _SECRETISH.sub(lambda m: m.group(1) + " [скрыто]", text)
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"


def _int_in(name: str, value: Any) -> int:
    low, high = LIMITS[name]
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ModelCardRequestError(f"{name} must be an integer {low}..{high}")
    return value


def _clean_description(value: Any) -> str:
    if not isinstance(value, str):
        raise ModelCardRequestError("description must be text")
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    if _CONTROL.search(text.replace("\t", " ")):
        raise ModelCardRequestError("description must not contain control characters")
    if len(text) > MAX_DESCRIPTION:
        raise ModelCardRequestError(f"description is limited to {MAX_DESCRIPTION} characters")
    return text


def _clean_params(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ModelCardRequestError("params_billion must be a number or null")
    if not 0 < value <= MAX_PARAMS_BILLION:
        raise ModelCardRequestError(f"params_billion must be in (0, {MAX_PARAMS_BILLION}]")
    return value


def _clean_title(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TITLE or _CONTROL.search(value):
        raise ModelCardRequestError(f"title must be 1..{MAX_TITLE} characters of text")
    return value.strip()


# --- the service -----------------------------------------------------------------------------------------


class ModelCards:
    def __init__(
        self,
        storage_root: str | os.PathLike[str],
        connections: UltraConnections,
        *,
        tk_state_path: Path | None,
        checker: ApiChecker | None = None,
        environ: Mapping[str, str] | None = None,
        now: Callable[[], datetime] = _utc_now,
        lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        root = Path(storage_root)
        self.settings_path = root / "ultra" / "model_settings.json"
        self.checks_path = root / "ultra" / "api_checks.json"
        self.view_path = root / "ultra" / "evm_view.json"
        self.lock_path = root / "locks" / "ultra" / "model_cards.lock"
        self.connections = connections
        self.tk_state_path = tk_state_path
        self.checker: ApiChecker = checker or LiveCheckNotAuthorized()
        self.environ = os.environ if environ is None else environ
        self.now = now
        self.lock_timeout = lock_timeout

    # --- stores ---------------------------------------------------------------------------------------

    def _load(self, path: Path, schema: str) -> dict[str, Any]:
        """``{"state": EMPTY | SAVED | CORRUPT, "data": ...}``; a damaged file is reported, never replaced."""
        try:
            with open(path, "rb") as handle:
                raw = handle.read(MAX_STORE_BYTES + 1)
        except FileNotFoundError:
            return {"state": "EMPTY", "data": {}}
        except OSError as exc:
            return {"state": "CORRUPT", "data": {}, "reason": type(exc).__name__}
        try:
            if len(raw) > MAX_STORE_BYTES:
                raise ValueError("too large")
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict) or data.get("schema") != schema or data.get("version") != SCHEMA_VERSION:
                raise ValueError("unknown schema or version")
        except (UnicodeDecodeError, ValueError):
            return {"state": "CORRUPT", "data": {}, "reason": "unreadable"}
        return {"state": "SAVED", "data": data}

    def _write(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.{new_id('tmp')}.tmp")
        try:
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ModelCardsStoreError(f"{path.name} could not be persisted: {type(exc).__name__}") from exc

    def _set_aside(self, path: Path) -> None:
        """A damaged file is kept next to the new one for diagnosis, never silently lost."""
        try:
            os.replace(path, path.with_name(f"{path.name}.corrupt-{new_id('ultra')}"))
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise ModelCardsStoreError(f"damaged {path.name} could not be set aside: {type(exc).__name__}") from exc

    def _locked(self) -> InterProcessLock:
        lock = InterProcessLock(self.lock_path, timeout=self.lock_timeout)
        try:
            lock.acquire()
        except StoreLockTimeout as exc:
            raise ModelCardsStoreError("model cards lock not acquired") from exc
        return lock

    # --- settings ---------------------------------------------------------------------------------------

    def _settings(self) -> dict[str, Any]:
        loaded = self._load(self.settings_path, SETTINGS_SCHEMA)
        data = loaded["data"]
        revision = data.get("revision", 0) if loaded["state"] == "SAVED" else (0 if loaded["state"] == "EMPTY" else None)
        if loaded["state"] == "SAVED" and (isinstance(revision, bool) or not isinstance(revision, int) or revision < 0):
            loaded, data, revision = {"state": "CORRUPT", "reason": "unreadable"}, {}, None
        result = {"state": loaded["state"], "revision": revision, "ignored": 0,
                  "providers": dict(BUILTIN_PROVIDERS), "profiles": {}, "models": {}}
        if loaded["state"] == "CORRUPT":
            result["reason"] = loaded.get("reason", "unreadable")
        for provider in BUILTIN_PROVIDERS.values():
            result["profiles"][default_profile_id(provider.provider_id)] = self._default_profile(provider.provider_id)
        for key, entry in (data.get("providers") or {}).items() if isinstance(data.get("providers"), dict) else ():
            try:
                if key in BUILTIN_PROVIDERS or not _ID.fullmatch(key) or not isinstance(entry, dict):
                    raise ValueError
                # A manually added entry never names an adapter module: listing a provider is not support.
                result["providers"][key] = Provider(key, _clean_title(entry.get("display_name")),
                                                    _clean_title(entry.get("country", "—")), None,
                                                    "адаптер отсутствует", source="user")
            except (ValueError, ModelCardRequestError):
                result["ignored"] += 1
        for key, entry in (data.get("profiles") or {}).items() if isinstance(data.get("profiles"), dict) else ():
            try:
                if not _ID.fullmatch(key) or not isinstance(entry, dict) or entry.get("provider") not in result["providers"]:
                    raise ValueError
                revision_value = entry.get("credential_revision", 0)
                if isinstance(revision_value, bool) or not isinstance(revision_value, int) or revision_value < 0:
                    raise ValueError
                result["profiles"][key] = {
                    "profile_id": key, "provider_id": entry["provider"], "title": _clean_title(entry.get("title")),
                    "builtin": key in result["profiles"] and result["profiles"][key]["builtin"],
                    "credential_revision": revision_value,
                    **{name: _int_in(name, entry.get(name, PROFILE_DEFAULTS[name])) for name in LIMITS}}
            except (ValueError, ModelCardRequestError):
                result["ignored"] += 1
        for key, entry in (data.get("models") or {}).items() if isinstance(data.get("models"), dict) else ():
            try:
                if not _ID.fullmatch(key) or not isinstance(entry, dict):
                    raise ValueError
                profile_id = entry.get("profile_id")
                if profile_id is not None and profile_id not in result["profiles"]:
                    raise ValueError
                result["models"][key] = {"description": _clean_description(entry.get("description", "")),
                                         "params_billion": _clean_params(entry.get("params_billion")),
                                         "profile_id": profile_id, "updated_at": entry.get("updated_at")}
            except (ValueError, ModelCardRequestError):
                result["ignored"] += 1
        return result

    @staticmethod
    def _default_profile(provider_id: str) -> dict[str, Any]:
        provider = BUILTIN_PROVIDERS.get(provider_id)
        return {"profile_id": default_profile_id(provider_id), "provider_id": provider_id,
                "title": f"{provider.display_name if provider else provider_id} — основной профиль", "builtin": True,
                "credential_revision": 0, **PROFILE_DEFAULTS}

    @staticmethod
    def _profile_for(settings: dict[str, Any], spec: Any) -> dict[str, Any]:
        chosen = settings["models"].get(spec.model_id, {}).get("profile_id")
        profile = settings["profiles"].get(chosen) if chosen else None
        if profile is None or profile["provider_id"] != spec.provider:
            profile = settings["profiles"].get(default_profile_id(spec.provider)) or ModelCards._default_profile(spec.provider)
        return profile

    # --- connection facts and settings version ---------------------------------------------------------

    def _connection_facts(self, provider: Provider | None) -> dict[str, Any]:
        if provider is None:
            return {"credential": {"source": None, "present": False}, "scope": {"value": None, "label": "—"}}
        present = bool(provider.credential_env) and provider.credential_env in self.environ  # presence only
        scope = None
        if provider.scope_env:
            raw = self.environ.get(provider.scope_env) or provider.default_scope
            scope = raw if isinstance(raw, str) and raw in SCOPE_LABELS else "NONSTANDARD"
        return {"credential": {"source": f"переменная среды {provider.credential_env}" if provider.credential_env else None,
                               "present": present},
                "scope": {"value": scope, "label": SCOPE_LABELS.get(scope, "Нестандартное значение" if scope else "—")}}

    def _settings_version(self, spec: Any, provider: Provider | None, profile: dict[str, Any],
                          facts: dict[str, Any]) -> str:
        """Changes when the key, the API profile, an endpoint or the called model changes; card text,
        parameter count, timeouts and the freshness period are deliberately outside."""
        material = {
            "provider": spec.provider, "adapter": provider.adapter if provider else None,
            "profile_id": profile["profile_id"], "credential_env": provider.credential_env if provider else None,
            "credential_present": facts["credential"]["present"], "credential_revision": profile["credential_revision"],
            "scope": facts["scope"]["value"], "oauth_url": provider.oauth_url if provider else None,
            "api_url": provider.api_url if provider else None, "provider_model_id": spec.provider_model_id,
        }
        canonical = json.dumps(material, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("ascii")).hexdigest()[:16]

    # --- API status -------------------------------------------------------------------------------------

    def api_status(self, record: Mapping[str, Any] | None, *, settings_version: str, freshness_days: int,
                   checks_state: str, registry_enabled: bool, adapter_state: str) -> dict[str, Any]:
        now = self.now()
        record = record or {}
        success_at = _parse_time(record.get("last_success_at"))
        failure_at = _parse_time(record.get("last_failure_at"))
        result: dict[str, Any] = {
            "freshness_days": freshness_days, "settings_version": settings_version,
            "last_success_at": record.get("last_success_at") if success_at else None,
            "last_success_source": record.get("last_success_source") if success_at else None,
            "last_failure_at": record.get("last_failure_at") if failure_at else None,
            "last_failure": record.get("last_failure") if failure_at else None,
            "age_days": None,
        }

        def verdict(color: str, reason: str) -> dict[str, Any]:
            result.update(color=color, reason=reason)
            return result

        if not registry_enabled:
            return verdict(RED, "REGISTRY_DISABLED")
        if adapter_state != "AVAILABLE":
            return verdict(RED, "ADAPTER_MISSING")
        if checks_state == "CORRUPT":
            return verdict(RED, "STATE_CORRUPT")
        if ((record.get("last_success_at") is not None and success_at is None)
                or (record.get("last_failure_at") is not None and failure_at is None)):
            return verdict(RED, "TIMESTAMP_INVALID")
        if success_at is None:
            return verdict(RED, "LAST_CHECK_FAILED" if failure_at else "NEVER_CONFIRMED")
        if record.get("settings_version") != settings_version:
            return verdict(RED, "SETTINGS_CHANGED")
        if failure_at is not None and failure_at > success_at:
            return verdict(RED, "LAST_CHECK_FAILED")
        if success_at > now + FUTURE_TOLERANCE:
            return verdict(RED, "TIMESTAMP_INVALID")
        age = max(now - success_at, timedelta(0))
        result["age_days"] = age.days
        return verdict(GREEN, "CONFIRMED") if age <= timedelta(days=freshness_days) else verdict(ORANGE, "STALE")

    def _checks(self) -> dict[str, Any]:
        loaded = self._load(self.checks_path, CHECKS_SCHEMA)
        checks = loaded["data"].get("checks", {}) if loaded["state"] == "SAVED" else {}
        if not isinstance(checks, dict):
            return {"state": "CORRUPT", "checks": {}}
        return {"state": loaded["state"], "checks": {k: v for k, v in checks.items() if isinstance(v, dict)}}

    # --- view preferences: manual order of each column and favourites ------------------------------------

    def _present(self) -> dict[str, list[str]]:
        """Connection ids each board column shows now, in their natural order (the registry for API)."""
        columns = self.connections.catalog()["columns"]
        return {section: [c["connection_id"] for c in columns.get(column, {}).get("connections", [])
                          if isinstance(c, dict) and isinstance(c.get("connection_id"), str)]
                for section, (column, _) in BOARD_COLUMNS.items()}

    def _view(self) -> dict[str, Any]:
        """The stored arrangement; a damaged file is reported (natural order, no favourites), never replaced."""
        empty = {section: [] for section in VIEW_SECTIONS}
        loaded = self._load(self.view_path, VIEW_SCHEMA)
        if loaded["state"] != "SAVED":
            return {"state": loaded["state"], "revision": 0 if loaded["state"] == "EMPTY" else None, "stored": empty}
        data, stored = loaded["data"], {}
        revision, sections = data.get("revision"), data.get("sections")
        valid = not isinstance(revision, bool) and isinstance(revision, int) and revision >= 0 and isinstance(sections, dict)
        for section in VIEW_SECTIONS if valid else ():
            ids = sections.get(section, [])
            if (not isinstance(ids, list) or len(ids) > MAX_VIEW_IDS or len(set(map(str, ids))) != len(ids)
                    or not all(isinstance(x, str) and _CONNECTION_ID.fullmatch(x) for x in ids)):
                valid = False
                break
            stored[section] = list(ids)
        if not valid:
            return {"state": "CORRUPT", "revision": None, "stored": empty}
        return {"state": "SAVED", "revision": revision, "stored": stored}

    def view(self, present: dict[str, list[str]] | None = None) -> dict[str, Any]:
        """Effective board: stored order of the ids present now, then new ids in natural order; favourites are
        stored references to ids present anywhere. Stored ids that are absent now are kept, only not shown."""
        present = present if present is not None else self._present()
        stored = self._view()
        sections, hidden = {}, 0
        for section in BOARD_COLUMNS:
            here = set(present[section])
            kept = [x for x in stored["stored"][section] if x in here]
            sections[section] = kept + [x for x in present[section] if x not in kept]
            hidden += len(stored["stored"][section]) - len(kept)
        everywhere = {x for ids in present.values() for x in ids}
        sections["favorites"] = [x for x in stored["stored"]["favorites"] if x in everywhere]
        hidden += len(stored["stored"]["favorites"]) - len(sections["favorites"])
        return {"state": stored["state"], "revision": stored["revision"], "sections": sections, "hidden": hidden}

    def save_view(self, body: Mapping[str, Any]) -> dict[str, Any]:
        """Replace the order of one column (a complete permutation of what it shows) or the favourites (any ids
        shown now). Refused when the arrangement or the list of entries changed since ``base_revision``."""
        if set(body) - {"base_revision", "section", "order"}:
            raise ModelCardRequestError("unknown fields: " + ", ".join(sorted(set(body) - {"base_revision", "section", "order"})))
        section, order = body.get("section"), body.get("order")
        if section not in VIEW_SECTIONS:
            raise ModelCardRequestError("section must be one of: " + ", ".join(VIEW_SECTIONS))
        if (not isinstance(order, list) or len(order) > MAX_VIEW_IDS
                or not all(isinstance(x, str) and _CONNECTION_ID.fullmatch(x) for x in order)):
            raise ModelCardRequestError("order must be a list of connection ids <kind>:<provider>:<id>")
        if len(set(order)) != len(order):
            raise ModelCardRequestError("order repeats a connection id")
        if section != "favorites" and any(x.split(":", 1)[0] != BOARD_COLUMNS[section][1] for x in order):
            raise ModelCardRequestError(f"the {section} column holds only {BOARD_COLUMNS[section][1]} connections")
        present = self._present()
        visible = {x for ids in present.values() for x in ids} if section == "favorites" else set(present[section])
        if not set(order) <= visible or (section != "favorites" and set(order) != visible):
            raise SettingsConflictError("the list of entries changed since it was read; reload and repeat")
        lock = self._locked()
        try:
            current = self._view()
            if body.get("base_revision") != current["revision"]:
                raise SettingsConflictError("the board arrangement changed since it was read; reload and repeat")
            if current["state"] == "CORRUPT":
                self._set_aside(self.view_path)
            stored = dict(current["stored"])
            stored[section] = list(order) + [x for x in stored[section] if x not in visible and x not in order]
            self._write(self.view_path, {"schema": VIEW_SCHEMA, "version": SCHEMA_VERSION,
                                         "revision": (current["revision"] or 0) + 1, "sections": stored})
        finally:
            lock.release()
        return self.view(present)

    # --- the read model -------------------------------------------------------------------------------

    def _context(self) -> dict[str, Any]:
        from .ultra_connections import _registry  # the one registry import of the EVM

        registry = _registry()
        return {"registry": registry, "settings": self._settings(), "checks": self._checks(),
                "tk": read_tk_assignments(self.tk_state_path, registry),
                "chat": self.connections.selection("chat")}

    def _spec(self, registry: Any, model_id: Any) -> Any:
        if not isinstance(model_id, str) or not _ID.fullmatch(model_id):
            raise ModelCardRequestError("model_id must be a short lowercase id")
        spec = registry.MODEL_REGISTRY.get(model_id)
        if spec is None:
            raise UnknownModelCardError(f"no model {model_id!r} in the shared registry")
        return spec

    def _card(self, ctx: dict[str, Any], spec: Any) -> dict[str, Any]:
        settings = ctx["settings"]
        provider = settings["providers"].get(spec.provider)
        profile = self._profile_for(settings, spec)
        facts = self._connection_facts(provider)
        version = self._settings_version(spec, provider, profile, facts)
        connection_id = connection_id_for(spec)
        record = ctx["checks"]["checks"].get(connection_id)
        entry = settings["models"].get(spec.model_id, {})
        params = entry.get("params_billion")
        status = self.api_status(record, settings_version=version, freshness_days=profile["freshness_days"],
                                 checks_state=ctx["checks"]["state"], registry_enabled=bool(spec.enabled),
                                 adapter_state=_adapter_state(provider) if provider else "MISSING")
        last_output = None
        if isinstance(record, dict) and isinstance(record.get("last_output"), dict):
            out = record["last_output"]
            last_output = {"kind": out.get("kind"), "at": out.get("at"),
                           "text": safe_text(out.get("text", ""), profile["diagnostic_limit_chars"])}
        return {
            "connection_id": connection_id, "model_id": spec.model_id, "display_name": spec.display_name,
            "provider_id": spec.provider, "provider_model_id": spec.provider_model_id,
            "registry_enabled": bool(spec.enabled), "is_local": bool(spec.is_local),
            "params_billion": params, "params_source": "user" if params is not None else "unknown",
            "description": entry.get("description", ""), "profile_id": profile["profile_id"],
            "settings_version": version, "roles": role_states(spec.model_id, ctx["tk"], ctx["chat"]),
            "api": status, "last_output": last_output,
        }

    def catalog(self) -> dict[str, Any]:
        """Everything the EVM cards show; reads only, creates nothing, sends nothing."""
        ctx = self._context()
        settings, tk = ctx["settings"], ctx["tk"]
        providers = []
        for provider in settings["providers"].values():
            facts = self._connection_facts(provider)
            providers.append({
                "provider_id": provider.provider_id, "display_name": provider.display_name,
                "country": provider.country, "source": provider.source, "adapter": provider.adapter,
                "adapter_state": _adapter_state(provider), "auth": provider.auth,
                "oauth_url": provider.oauth_url, "api_url": provider.api_url, **facts})
        return {
            "network_calls": 0,
            "settings": {"state": settings["state"], "revision": settings["revision"], "ignored": settings["ignored"],
                         **({"reason": settings["reason"]} if "reason" in settings else {})},
            "checks": {"state": ctx["checks"]["state"]},
            "roles_source": {"state": tk["state"], "fallbacks": tk["fallbacks"],
                             "chat_state": ctx["chat"].get("state"),
                             **({"reason": tk["reason"]} if "reason" in tk else {})},
            "role_definitions": [{"role": r.role, "label": r.label, "hint": r.hint, "exists": r.exists,
                                  "runs": r.runs, "linked_to": r.linked_to} for r in ROLES],
            "providers": providers,
            "profiles": list(settings["profiles"].values()),
            "limits": {"description": MAX_DESCRIPTION, "params_billion": MAX_PARAMS_BILLION,
                       **{name: list(bounds) for name, bounds in LIMITS.items()}},
            "test_message": TEST_MESSAGE,
            "live_check": {"authorized": bool(self.checker.authorized),
                           "reason": None if self.checker.authorized else self.checker.reason},
            "cards": [self._card(ctx, spec) for spec in ctx["registry"].list_model_specs()],
            "view": self.view(),
        }

    def card(self, model_id: Any) -> dict[str, Any]:
        ctx = self._context()
        return self._card(ctx, self._spec(ctx["registry"], model_id))

    # --- writes -------------------------------------------------------------------------------------------

    def save_settings(self, model_id: Any, body: Mapping[str, Any]) -> dict[str, Any]:
        """Card data of one model and the profile serving it, in one atomic write; refused when the
        settings changed since ``base_revision`` (another window saved first)."""
        allowed = {"base_revision", "description", "params_billion", "profile_id", "profile"}
        if set(body) - allowed:
            raise ModelCardRequestError("unknown fields: " + ", ".join(sorted(set(body) - allowed)))
        from .ultra_connections import _registry

        spec = self._spec(_registry(), model_id)
        description = _clean_description(body.get("description", ""))
        params = _clean_params(body.get("params_billion"))
        profile_changes = body.get("profile") or {}
        if not isinstance(profile_changes, dict) or set(profile_changes) - set(LIMITS):
            raise ModelCardRequestError("profile accepts only " + ", ".join(LIMITS))
        lock = self._locked()
        try:
            current = self._settings()
            if body.get("base_revision") != current["revision"]:
                raise SettingsConflictError("settings changed since they were read; reload and repeat")
            profile_id = body.get("profile_id") or self._profile_for(current, spec)["profile_id"]
            profile = current["profiles"].get(profile_id)
            if profile is None or profile["provider_id"] != spec.provider:
                raise ModelCardRequestError("profile_id must name a profile of this model's provider")
            for name, value in profile_changes.items():
                profile = {**profile, name: _int_in(name, value)}
            if current["state"] == "CORRUPT":
                self._set_aside(self.settings_path)
                raw: dict[str, Any] = {}
            else:
                raw = self._load(self.settings_path, SETTINGS_SCHEMA)["data"]
            models = dict(raw.get("models") or {}) if isinstance(raw.get("models"), dict) else {}
            profiles = dict(raw.get("profiles") or {}) if isinstance(raw.get("profiles"), dict) else {}
            providers = dict(raw.get("providers") or {}) if isinstance(raw.get("providers"), dict) else {}
            models[spec.model_id] = {"description": description, "params_billion": params, "profile_id": profile_id,
                                     "updated_at": self.now().isoformat()}
            profiles[profile_id] = {"provider": profile["provider_id"], "title": profile["title"],
                                    "credential_revision": profile["credential_revision"],
                                    **{name: profile[name] for name in LIMITS}}
            self._write(self.settings_path, {"schema": SETTINGS_SCHEMA, "version": SCHEMA_VERSION,
                                             "revision": (current["revision"] or 0) + 1, "models": models,
                                             "profiles": profiles, "providers": providers})
        finally:
            lock.release()
        return self.card(spec.model_id)

    def _record(self, connection_id: str, update: Callable[[dict[str, Any]], None]) -> None:
        lock = self._locked()
        try:
            loaded = self._checks()
            if loaded["state"] == "CORRUPT":
                self._set_aside(self.checks_path)
                checks: dict[str, Any] = {}
            else:
                checks = loaded["checks"]
            record = dict(checks.get(connection_id) or {})
            update(record)
            checks[connection_id] = record
            self._write(self.checks_path, {"schema": CHECKS_SCHEMA, "version": SCHEMA_VERSION, "checks": checks})
        finally:
            lock.release()

    def record_success(self, connection_id: str, settings_version: str, *, source: str, reply: str | None,
                       limit: int) -> None:
        at = self.now().isoformat()

        def update(record: dict[str, Any]) -> None:
            record.update(settings_version=settings_version, last_success_at=at, last_success_source=source)
            if reply is not None:
                record["last_output"] = {"kind": "reply", "at": at, "text": safe_text(reply, limit)}

        self._record(connection_id, update)

    def record_failure(self, connection_id: str, settings_version: str, *, code: str, message: str,
                       limit: int) -> None:
        at = self.now().isoformat()
        failure = {"code": safe_text(code, 60), "message": safe_text(message, MAX_ERROR_TEXT)}

        def update(record: dict[str, Any]) -> None:
            record.update(last_failure_at=at, last_failure=failure, failure_settings_version=settings_version)
            record["last_output"] = {"kind": "error", "at": at,
                                     "text": safe_text(f"{failure['code']}: {failure['message']}", limit)}

        self._record(connection_id, update)

    def record_chat_success(self, model_id: str, settings_version: str) -> bool:
        """Extension point for an ordinary Ultra Chat answer: it refreshes the confirmation only when the
        server knows the exact model and the settings version the answer was produced with."""
        card = self.card(model_id)
        if settings_version != card["settings_version"] or not card["registry_enabled"]:
            return False
        self.record_success(card["connection_id"], settings_version, source="chat", reply=None, limit=0)
        return True

    def run_check(self, model_id: Any) -> dict[str, Any]:
        """One fixed short test message through the configured checker; nothing is sent while the live
        check is not authorised, and a simulated answer never confirms the model."""
        ctx = self._context()
        spec = self._spec(ctx["registry"], model_id)
        card = self._card(ctx, spec)
        if not spec.enabled:
            raise CheckRefusedError(f"model {spec.model_id!r} is disabled in the shared registry")
        if card["api"]["reason"] == "ADAPTER_MISSING":
            raise CheckRefusedError(f"provider {spec.provider!r} has no adapter")
        if not self.checker.authorized:
            return {"outcome": "LIVE_CHECK_NOT_AUTHORIZED", "message": self.checker.reason, "network_calls": 0,
                    "test_message": TEST_MESSAGE, "card": card}
        provider = ctx["settings"]["providers"][spec.provider]
        profile = self._profile_for(ctx["settings"], spec)
        version = card["settings_version"]  # captured before the call: a concurrent change cannot be confirmed
        request = CheckRequest(card["connection_id"], spec.model_id, spec.provider, spec.provider_model_id,
                               provider.api_url, profile["timeout_seconds"], TEST_MESSAGE)
        try:
            result = self.checker.check(request)
        except CheckRefusedError:
            raise
        except Exception as exc:  # a checker failure is a failed check, never a crash of the server
            result = CheckResult(ok=False, live=True, error_code="checker_error", error_message=type(exc).__name__)
        limit = profile["diagnostic_limit_chars"]
        if not result.live:
            outcome = "SIMULATED"
            text = safe_text(result.reply or result.error_message or "", limit)
        elif result.ok:
            outcome = "CONFIRMED"
            self.record_success(card["connection_id"], version, source="diagnostic", reply=result.reply or "", limit=limit)
            text = safe_text(result.reply or "", limit)
        else:
            outcome = "FAILED"
            self.record_failure(card["connection_id"], version, code=result.error_code or "check_failed",
                                message=result.error_message or "", limit=limit)
            text = safe_text(f"{result.error_code or 'check_failed'}: {result.error_message or ''}", limit)
        return {"outcome": outcome, "text": text, "test_message": TEST_MESSAGE, "card": self.card(spec.model_id)}
