from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Callable, Mapping
from context_registry import load_factory_catalog, resolve_context_text


MAX_EVENT_ID_LENGTH = 128
MAX_DESCRIPTION_LENGTH = 4096
MAX_TEMPLATE_LENGTH = 64 * 1024

_EVENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SIMPLE_PLACEHOLDER_TOKEN_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")
_REGISTERED_EVENTS: dict[str, dict[str, str]] = {}


def validate_event_id(event_id: str) -> str:
    if not isinstance(event_id, str):
        raise TypeError("event_id должен быть строкой.")
    value = event_id.strip()
    if len(value) > MAX_EVENT_ID_LENGTH or not _EVENT_ID_RE.fullmatch(value):
        raise ValueError(
            "event_id должен начинаться с a-z или 0-9 и содержать только "
            "a-z, 0-9, точку, подчёркивание или дефис."
        )
    return value


def register_server_context_event(
    event_id: str,
    description: str,
    default_template: str,
) -> dict[str, str]:
    """Зарегистрировать реально используемое runtime-событие."""

    event_id = validate_event_id(event_id)
    description = _validate_text_field(
        description, "built-in description", MAX_DESCRIPTION_LENGTH
    )
    default_template = _validate_text_field(
        default_template, "default_template", MAX_TEMPLATE_LENGTH
    )
    record = {
        "event_id": event_id,
        "description": description,
        "default_template": default_template,
    }
    existing = _REGISTERED_EVENTS.get(event_id)
    if existing is not None and existing != record:
        raise ValueError(
            f"Runtime event {event_id!r} уже зарегистрирован с другими metadata."
        )
    _REGISTERED_EVENTS[event_id] = record
    return dict(record)


def list_registered_server_context_events() -> list[dict[str, str]]:
    return [dict(_REGISTERED_EVENTS[event_id]) for event_id in sorted(_REGISTERED_EVENTS)]


def get_registered_server_context_event(event_id: str) -> dict[str, str] | None:
    event_id = validate_event_id(event_id)
    record = _REGISTERED_EVENTS.get(event_id)
    return dict(record) if record is not None else None


def _validate_text_field(value: object, label: str, limit: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} должен быть строкой.")
    if len(value) > limit:
        raise ValueError(f"{label} слишком большой: лимит {limit} символов.")
    return value


def _render_default_text(
    default_text: str, variables: Mapping[str, object]
) -> str:
    """Подставить только известные простые tokens, сохранив JSON/braces как есть."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in variables:
            return match.group(0)
        return str(variables[name])

    return _SIMPLE_PLACEHOLDER_TOKEN_RE.sub(replace, str(default_text))


def _report_warning(
    event_id: str,
    reason: str,
    on_warning: Callable[[dict[str, str]], None] | None,
) -> None:
    payload = {
        "event_id": event_id,
        "reason": reason,
        "fallback": "default_text",
    }
    try:
        warnings.warn(
            f"Server context message {event_id!r}: {reason}; "
            "используется default_text.",
            RuntimeWarning,
            stacklevel=3,
        )
    except Exception:
        pass
    if on_warning is not None:
        try:
            on_warning(payload)
        except Exception:
            pass


def resolve_server_context_message(
    event_id: str,
    variables: Mapping[str, object] | None = None,
    agent_id: str = "ultra",
    *,
    state_path: Path | str | None = None,
    on_warning: Callable[[dict[str, str]], None] | None = None,
) -> str:
    """Разрешить runtime-сообщение через единый Context Registry."""

    variables = variables or {}

    try:
        event_id = validate_event_id(event_id)
    except Exception as exc:
        safe_event_id = str(event_id)
        _report_warning(safe_event_id, str(exc), on_warning)
        return ""

    runtime_record = _REGISTERED_EVENTS.get(event_id)
    if runtime_record is None:
        raise KeyError(
            f"Runtime event {event_id!r} не зарегистрирован."
        )
    default_template = runtime_record["default_template"]

    try:
        return resolve_context_text(
            event_id,
            variables,
            agent_id,
            state_path=state_path,
        )
    except Exception as exc:
        _report_warning(
            event_id,
            f"ошибка Context Registry: {exc}",
            on_warning,
        )
        return _render_default_text(default_template, variables)


def _register_server_event_contexts_from_factory() -> None:
    factory = load_factory_catalog()

    for context_id, record in factory["contexts"].items():
        if record["group_id"] != "server_events":
            continue

        register_server_context_event(
            context_id,
            record["description"],
            record["factory_text"],
        )


_register_server_event_contexts_from_factory()
