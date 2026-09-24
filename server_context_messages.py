from __future__ import annotations

import json
import os
import re
import string
import uuid
import warnings
from pathlib import Path
from typing import Any, Callable, Mapping


SCHEMA_VERSION = 1
MAX_CATALOG_BYTES = 512 * 1024
MAX_EVENT_ID_LENGTH = 128
MAX_DESCRIPTION_LENGTH = 4096
MAX_TEMPLATE_LENGTH = 64 * 1024
MAX_MESSAGE_COUNT = 1000

APP_DATA_ROOT = (
    Path(os.getenv("LOCALAPPDATA") or Path.home()) / "GigaChatUltra"
).resolve()
AGENTS_ROOT = APP_DATA_ROOT / "agents"

_AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_EVENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_PLACEHOLDER_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_SIMPLE_PLACEHOLDER_TOKEN_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")
_REGISTERED_EVENTS: dict[str, dict[str, str]] = {}


def _validate_agent_id(agent_id: str) -> str:
    value = str(agent_id).strip().lower()
    if not _AGENT_ID_RE.fullmatch(value):
        raise ValueError(f"Некорректный agent_id: {agent_id!r}")
    return value


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


def get_server_context_messages_path(agent_id: str = "ultra") -> Path:
    agent_id = _validate_agent_id(agent_id)
    return (AGENTS_ROOT / agent_id / "server_context_messages.json").resolve()


def _empty_catalog() -> dict[str, Any]:
    return {"version": SCHEMA_VERSION, "messages": {}}


def _validate_text_field(value: object, label: str, limit: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} должен быть строкой.")
    if len(value) > limit:
        raise ValueError(f"{label} слишком большой: лимит {limit} символов.")
    return value


def _validate_catalog(data: object) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Корень справочника должен быть JSON object.")
    if (
        type(data.get("version")) is not int
        or data.get("version") != SCHEMA_VERSION
    ):
        raise ValueError(
            f"Неподдерживаемая version справочника: {data.get('version')!r}."
        )

    messages = data.get("messages")
    if not isinstance(messages, dict):
        raise ValueError("Поле messages должно быть JSON object.")
    if len(messages) > MAX_MESSAGE_COUNT:
        raise ValueError(
            f"Слишком много записей: лимит {MAX_MESSAGE_COUNT}."
        )

    normalized: dict[str, dict[str, str]] = {}
    for raw_event_id, raw_record in messages.items():
        event_id = validate_event_id(raw_event_id)
        if not isinstance(raw_record, dict):
            raise ValueError(f"Запись {event_id!r} должна быть JSON object.")
        description = _validate_text_field(
            raw_record.get("description"),
            f"description для {event_id!r}",
            MAX_DESCRIPTION_LENGTH,
        )
        template = _validate_text_field(
            raw_record.get("template"),
            f"template для {event_id!r}",
            MAX_TEMPLATE_LENGTH,
        )
        normalized[event_id] = {
            "description": description,
            "template": template,
        }

    return {"version": SCHEMA_VERSION, "messages": normalized}


def load_server_context_messages(
    agent_id: str = "ultra",
    *,
    path: Path | str | None = None,
    allow_missing: bool = True,
) -> dict[str, Any]:
    storage_path = (
        Path(path).resolve()
        if path is not None
        else get_server_context_messages_path(agent_id)
    )
    if not storage_path.is_file():
        if allow_missing:
            return _empty_catalog()
        raise FileNotFoundError(f"Справочник не найден: {storage_path}")

    size = storage_path.stat().st_size
    if size > MAX_CATALOG_BYTES:
        raise ValueError(
            f"Справочник слишком большой: {size} байт. "
            f"Лимит: {MAX_CATALOG_BYTES} байт."
        )
    try:
        data = json.loads(storage_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Не удалось прочитать JSON справочника: {exc}") from exc
    return _validate_catalog(data)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def save_server_context_messages(
    catalog: object,
    agent_id: str = "ultra",
    *,
    path: Path | str | None = None,
) -> Path:
    normalized = _validate_catalog(catalog)
    serialized = json.dumps(
        normalized,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    size = len(serialized.encode("utf-8"))
    if size > MAX_CATALOG_BYTES:
        raise ValueError(
            f"Справочник слишком большой: {size} байт. "
            f"Лимит: {MAX_CATALOG_BYTES} байт."
        )
    storage_path = (
        Path(path).resolve()
        if path is not None
        else get_server_context_messages_path(agent_id)
    )
    _atomic_write_text(storage_path, serialized)
    return storage_path


def list_server_context_messages(
    agent_id: str = "ultra",
    *,
    path: Path | str | None = None,
) -> list[dict[str, str]]:
    catalog = load_server_context_messages(agent_id, path=path)
    return [
        {"event_id": event_id, **catalog["messages"][event_id]}
        for event_id in sorted(catalog["messages"])
    ]


def list_server_context_event_records(
    agent_id: str = "ultra",
    *,
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Объединить runtime registry и пользовательские overrides/drafts для UI."""

    diagnostics: list[dict[str, str]] = []
    try:
        catalog = load_server_context_messages(agent_id, path=path)
        user_messages = catalog["messages"]
    except Exception as exc:
        user_messages = {}
        diagnostics.append(
            {
                "kind": "invalid_user_catalog",
                "message": str(exc),
            }
        )

    event_ids = sorted(set(_REGISTERED_EVENTS) | set(user_messages))
    records: list[dict[str, Any]] = []
    for event_id in event_ids:
        runtime_record = _REGISTERED_EVENTS.get(event_id)
        user_record = user_messages.get(event_id)
        is_active = runtime_record is not None
        has_override = user_record is not None

        if is_active and has_override:
            status = "ACTIVE + OVERRIDE"
            source = "Пользовательский override"
            description = user_record["description"]
            template = user_record["template"]
        elif is_active:
            status = "ACTIVE"
            source = "Встроенный default"
            description = runtime_record["description"]
            template = runtime_record["default_template"]
        else:
            status = "DRAFT"
            source = "Пользовательский draft"
            description = user_record["description"]
            template = user_record["template"]

        records.append(
            {
                "event_id": event_id,
                "status": status,
                "source": source,
                "description": description,
                "template": template,
                "is_active": is_active,
                "has_override": has_override,
                "built_in_description": (
                    runtime_record["description"] if is_active else None
                ),
                "default_template": (
                    runtime_record["default_template"] if is_active else None
                ),
                "user_description": (
                    user_record["description"] if has_override else None
                ),
                "override_template": (
                    user_record["template"] if has_override else None
                ),
            }
        )

    return {"records": records, "diagnostics": diagnostics}


def upsert_server_context_message(
    event_id: str,
    description: str,
    template: str,
    agent_id: str = "ultra",
    *,
    path: Path | str | None = None,
) -> dict[str, Any]:
    event_id = validate_event_id(event_id)
    description = _validate_text_field(
        description, "description", MAX_DESCRIPTION_LENGTH
    )
    template = _validate_text_field(template, "template", MAX_TEMPLATE_LENGTH)
    catalog = load_server_context_messages(agent_id, path=path)
    created = event_id not in catalog["messages"]
    catalog["messages"][event_id] = {
        "description": description,
        "template": template,
    }
    storage_path = save_server_context_messages(
        catalog, agent_id, path=path
    )
    return {
        "created": created,
        "event_id": event_id,
        "path": str(storage_path),
    }


def delete_server_context_message(
    event_id: str,
    agent_id: str = "ultra",
    *,
    path: Path | str | None = None,
) -> bool:
    event_id = validate_event_id(event_id)
    catalog = load_server_context_messages(agent_id, path=path)
    if event_id not in catalog["messages"]:
        return False
    del catalog["messages"][event_id]
    save_server_context_messages(catalog, agent_id, path=path)
    return True


def _render_template(template: str, variables: Mapping[str, object]) -> str:
    formatter = string.Formatter()
    for _literal, field_name, format_spec, conversion in formatter.parse(template):
        if field_name is None:
            continue
        if not _PLACEHOLDER_RE.fullmatch(field_name):
            raise ValueError(
                f"Недопустимый placeholder {{{field_name}}}: "
                "разрешены только простые имена."
            )
        if format_spec or conversion:
            raise ValueError(
                f"Форматирование placeholder {{{field_name}}} запрещено."
            )
        if field_name not in variables:
            raise KeyError(f"Неизвестный placeholder: {field_name}")
    safe_variables = {key: str(value) for key, value in variables.items()}
    return template.format_map(safe_variables)


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
    path: Path | str | None = None,
    on_warning: Callable[[dict[str, str]], None] | None = None,
) -> str:
    """Разрешить override зарегистрированного события с built-in fallback."""

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

    custom_template = None
    try:
        catalog = load_server_context_messages(agent_id, path=path)
        record = catalog["messages"].get(event_id)
        if record is not None:
            custom_template = record["template"]
    except Exception as exc:
        _report_warning(event_id, f"ошибка справочника: {exc}", on_warning)

    if custom_template is not None:
        try:
            return _render_template(custom_template, variables)
        except Exception as exc:
            _report_warning(event_id, f"ошибка шаблона: {exc}", on_warning)

    return _render_default_text(default_template, variables)


register_server_context_event(
    "permission.denied",
    "Сервер отказал в доступе к capability для вызванного инструмента.",
    (
        "Сервер отказал в доступе к capability {capability} для tool "
        "{tool_name}. Не повторяй тот же запрещённый вызов. Соблюдай "
        "серверные разрешения и сообщи пользователю, если для задачи "
        "требуется дополнительный доступ."
    ),
)

register_server_context_event(
    "tool.error",
    "Вызов инструмента завершился ошибкой.",
    (
        "Tool {tool_name} завершился ошибкой {error_type}: {error_message}. "
        "Исправь причину ошибки и повтори необходимую проверку или вызов. "
        "Для путей используй только относительные пути внутри workspace; "
        "корень обозначается '.'."
    ),
)

register_server_context_event(
    "guard.repeat",
    "GUARD P1 остановил механический повтор успешного read/list.",
    (
        "SUPERVISOR CHECK — этот же успешный tool с теми же arguments уже "
        "выполнялся несколько раз, а релевантное состояние не изменилось. "
        "Вызов сейчас НЕ выполнен. Снова сопоставь действие с исходной TASK "
        "и используй уже полученный результат. Если повтор действительно "
        "нужен, измени план/состояние; не продолжай механически повторять "
        "тот же вызов."
    ),
)

register_server_context_event(
    "guard.suspicious_create",
    "GUARD P1 обнаружил создание файла, похожего на существующий.",
    (
        "SUPERVISOR CHECK — ты собираешься СОЗДАТЬ новый файл, очень похожий "
        "на существующий. Новый файл пока НЕ создан. Снова сопоставь действие "
        "с исходной TASK: действительно нужен новый документ или следовало "
        "изменить существующий? Если после самопроверки создание действительно "
        "нужно, повтори тот же write_file: повторный осознанный запрос в этом "
        "RUN будет разрешён."
    ),
)

register_server_context_event(
    "verification.required",
    "Verification Gate заблокировал SUCCESS до обязательных проверок.",
    (
        "SERVER VERIFICATION GATE — SUCCESS BLOCKED.\n"
        "Ты попытался завершить RUN, но сервер физически запрещает SUCCESS, "
        "пока реальные проверки после последних изменений не завершены.\n"
        "Не объявляй задачу завершённой и не утверждай, что код исправен, "
        "пока ниже остаются пункты.\n\n"
        "ОБЯЗАТЕЛЬНО ВЫПОЛНИ:\n{missing_lines}\n\n"
        "Если проверка падает из-за изменённого тобой кода — исправь код "
        "в разрешённом scope и повтори проверки. Любая новая запись снова "
        "делает git_diff/git_status устаревшими, а новая Python-запись — "
        "python_compile; изменение server.py/ultra_ui.py — ui_smoke_test.\n"
        "Если исправление невозможно в текущих разрешениях, сообщи о блокере, "
        "но SUCCESS всё равно запрещён.\n\n"
        "Текущее verification state:\n{verification_state}"
    ),
)

register_server_context_event(
    "final_audit.feedback",
    "Final Audit заблокировал SUCCESS и запросил ограниченную коррекцию RUN.",
    (
        "SERVER FINAL VERIFIER FEEDBACK — SUCCESS ЗАБЛОКИРОВАН.\n\n"
        "РЕЗУЛЬТАТ:\n{verdict}\n\n"
        "ПРИЧИНА:\n{reason}\n\n"
        "НАРУШЕНИЯ:\n{violations_lines}\n\n"
        "ТРЕБУЕМОЕ ДЕЙСТВИЕ:\n{required_action}\n\n"
        "ЦИКЛ КОРРЕКЦИИ: {correction_cycle} из {correction_limit}.\n"
        "ОСТАЛОСЬ КОРРЕКЦИЙ: {remaining_corrections}.\n\n"
        "Это серверная обратная связь Final Verifier по исходной RAW TASK, "
        "а НЕ новая пользовательская задача. RAW TASK остаётся источником "
        "истины и имеет приоритет. Исправь фактический результат задачи, "
        "выполни необходимые реальные проверки и снова заверши RUN."
    ),
)

register_server_context_event(
    "execution_consistency.feedback",
    "Server запросил однократную перепроверку исполнения исходной TASK.",
    (
        "SERVER EXECUTION SELF-CHECK. Перепроверь исходную RAW TASK, текущее "
        "состояние целевого объекта и доступные инструменты. В этом RUN пока нет "
        "физических изменений, хотя TASK выглядит предполагающей изменение. "
        "Если изменение действительно требуется, продолжи с разрешёнными tools. "
        "Если оно не требуется, уже выполнено, невозможно, неоднозначно или "
        "небезопасно, проверь это фактически и объясни подтверждённую причину. "
        "Не меняй Workspace только ради прохождения проверки. Это серверная "
        "обратная связь, а не новая USER TASK."
    ),
)

register_server_context_event(
    "execution_consistency.correction",
    "Verifier запросил одну коррекцию после повторного несоответствия исполнения.",
    (
        "SERVER CONSISTENCY FEEDBACK.\nПричина: {reason}\n"
        "Нарушения:\n{violations_lines}\nТребуемое действие: {required_action}\n"
        "Если есть реальный blocker, укажи его и подтверди tool evidence. "
        "Если blocker отсутствует, выполни требуемую часть RAW TASK доступными tools. "
        "Если требуемое состояние уже существует, проверь и покажи это фактически. "
        "Не меняй Workspace только ради проверки. RAW TASK остаётся источником истины; "
        "это не новая USER TASK."
    ),
)
