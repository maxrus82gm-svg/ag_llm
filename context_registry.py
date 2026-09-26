from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = 1
MAX_CATALOG_BYTES = 2 * 1024 * 1024
MAX_CONTEXT_TEXT_BYTES = 256 * 1024
MAX_DESCRIPTION_BYTES = 16 * 1024

APP_DATA_ROOT = (
    Path(os.getenv("LOCALAPPDATA") or Path.home()) / "GigaChatUltra"
).resolve()
AGENTS_ROOT = APP_DATA_ROOT / "agents"

DEFAULT_FACTORY_PATH = (Path(__file__).resolve().parent / "context_defaults.json").resolve()

_CONTEXT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_VARIANT_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_SIMPLE_PLACEHOLDER_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")


class ContextRegistryError(RuntimeError):
    pass


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def _validate_agent_id(agent_id: str) -> str:
    value = str(agent_id).strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise ValueError(f"Некорректный agent_id: {agent_id!r}")
    return value


def validate_context_id(context_id: str) -> str:
    if not isinstance(context_id, str):
        raise TypeError("context_id должен быть строкой.")
    value = context_id.strip()
    if not _CONTEXT_ID_RE.fullmatch(value):
        raise ValueError(
            "context_id должен начинаться с a-z или 0-9 и содержать только "
            "a-z, 0-9, точку, подчёркивание или дефис."
        )
    return value


def validate_variant_id(variant_id: str) -> str:
    if not isinstance(variant_id, str):
        raise TypeError("variant_id должен быть строкой.")
    value = variant_id.strip()
    if not _VARIANT_ID_RE.fullmatch(value):
        raise ValueError(
            "variant_id должен начинаться с a-z и содержать только "
            "a-z, 0-9, подчёркивание или дефис."
        )
    if value == "factory":
        raise ValueError("Вариант 'factory' зарезервирован.")
    return value


def get_user_contexts_path(agent_id: str = "ultra") -> Path:
    agent_id = _validate_agent_id(agent_id)
    return (AGENTS_ROOT / agent_id / "contexts.json").resolve()


def get_user_context_history_dir(agent_id: str = "ultra") -> Path:
    agent_id = _validate_agent_id(agent_id)
    return (AGENTS_ROOT / agent_id / "contexts_history").resolve()


def _read_json(path: Path, *, allow_missing: bool) -> dict[str, Any]:
    if not path.is_file():
        if allow_missing:
            return {}
        raise FileNotFoundError(path)

    size = path.stat().st_size
    if size > MAX_CATALOG_BYTES:
        raise ContextRegistryError(
            f"Файл контекстов слишком большой: {size} байт."
        )

    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContextRegistryError(
            f"Не удалось прочитать {path.name}: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise ContextRegistryError(f"{path.name}: корень должен быть JSON object.")
    return value


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    serialized = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    encoded = serialized.encode("utf-8")
    if len(encoded) > MAX_CATALOG_BYTES:
        raise ContextRegistryError(
            f"Файл контекстов превысил лимит {MAX_CATALOG_BYTES} байт."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _backup_user_state(path: Path, agent_id: str) -> Path | None:
    if not path.is_file():
        return None

    history_dir = get_user_context_history_dir(agent_id)
    history_dir.mkdir(parents=True, exist_ok=True)
    backup = history_dir / f"contexts_{_utc_stamp()}_{uuid.uuid4().hex[:8]}.json"
    backup.write_bytes(path.read_bytes())
    return backup


def _validate_text(text: object, label: str) -> str:
    if not isinstance(text, str):
        raise TypeError(f"{label} должен быть строкой.")
    if not text.strip():
        raise ValueError(f"{label} не может быть пустым.")
    if len(text.encode("utf-8")) > MAX_CONTEXT_TEXT_BYTES:
        raise ValueError(f"{label} слишком большой.")
    return text


def _validate_description(description: object, label: str) -> str:
    if not isinstance(description, str):
        raise TypeError(f"{label} должно быть строкой.")
    if not description.strip():
        raise ValueError(f"{label} не может быть пустым.")
    if len(description.encode("utf-8")) > MAX_DESCRIPTION_BYTES:
        raise ValueError(f"{label} слишком большое.")
    return description


def find_placeholders(text: str) -> list[str]:
    return sorted(set(_SIMPLE_PLACEHOLDER_RE.findall(text)))


def _validate_placeholders(
    text: str,
    *,
    allowed_variables: list[str],
    context_id: str,
) -> None:
    unknown = sorted(set(find_placeholders(text)) - set(allowed_variables))
    if unknown:
        raise ValueError(
            f"{context_id}: неизвестные placeholders: {', '.join(unknown)}"
        )


def _validate_factory_catalog(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ContextRegistryError(
            f"Неподдерживаемая schema_version factory: "
            f"{value.get('schema_version')!r}"
        )

    contexts = value.get("contexts")
    if not isinstance(contexts, dict):
        raise ContextRegistryError("Factory catalog: contexts должен быть object.")

    normalized: dict[str, dict[str, Any]] = {}
    for raw_id, raw_record in contexts.items():
        context_id = validate_context_id(raw_id)
        if not isinstance(raw_record, dict):
            raise ContextRegistryError(
                f"{context_id}: factory record должен быть object."
            )

        group_id = raw_record.get("group_id")
        group_name = raw_record.get("group_name")
        runtime_owner = raw_record.get("runtime_owner")
        apply_scope = raw_record.get("apply_scope")
        description = _validate_description(
            raw_record.get("description"),
            f"{context_id}.description",
        )
        factory_text = _validate_text(
            raw_record.get("factory_text"),
            f"{context_id}.factory_text",
        )
        allowed_variables = raw_record.get("allowed_variables", [])

        if not isinstance(group_id, str) or not group_id.strip():
            raise ContextRegistryError(f"{context_id}: group_id обязателен.")
        if not isinstance(group_name, str) or not group_name.strip():
            raise ContextRegistryError(f"{context_id}: group_name обязателен.")
        if not isinstance(runtime_owner, str) or not runtime_owner.strip():
            raise ContextRegistryError(f"{context_id}: runtime_owner обязателен.")
        if apply_scope not in {
            "NEXT_EVENT",
            "NEXT_CALL",
            "NEXT_RUN",
        }:
            raise ContextRegistryError(
                f"{context_id}: недопустимый apply_scope {apply_scope!r}."
            )
        if (
            not isinstance(allowed_variables, list)
            or any(
                not isinstance(item, str)
                or not re.fullmatch(r"[a-z][a-z0-9_]*", item)
                for item in allowed_variables
            )
            or len(set(allowed_variables)) != len(allowed_variables)
        ):
            raise ContextRegistryError(
                f"{context_id}: allowed_variables некорректен."
            )

        _validate_placeholders(
            factory_text,
            allowed_variables=allowed_variables,
            context_id=context_id,
        )

        normalized[context_id] = {
            "context_id": context_id,
            "group_id": group_id.strip(),
            "group_name": group_name.strip(),
            "runtime_owner": runtime_owner.strip(),
            "apply_scope": apply_scope,
            "description": description,
            "factory_text": factory_text,
            "allowed_variables": list(allowed_variables),
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "contexts": normalized,
    }


def load_factory_catalog(
    *,
    path: Path | str | None = None,
) -> dict[str, Any]:
    factory_path = (
        Path(path).resolve()
        if path is not None
        else DEFAULT_FACTORY_PATH
    )
    value = _read_json(factory_path, allow_missing=False)
    return _validate_factory_catalog(value)


def _empty_user_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contexts": {},
    }


def _validate_user_state(
    value: dict[str, Any],
    factory: dict[str, Any],
) -> dict[str, Any]:
    if not value:
        return _empty_user_state()

    if value.get("schema_version") != SCHEMA_VERSION:
        raise ContextRegistryError(
            f"Неподдерживаемая schema_version user contexts: "
            f"{value.get('schema_version')!r}"
        )

    contexts = value.get("contexts")
    if not isinstance(contexts, dict):
        raise ContextRegistryError("User contexts: contexts должен быть object.")

    normalized: dict[str, dict[str, Any]] = {}
    for raw_id, raw_record in contexts.items():
        context_id = validate_context_id(raw_id)
        if context_id not in factory["contexts"]:
            raise ContextRegistryError(
                f"User contexts содержит неизвестный context_id: {context_id}"
            )
        if not isinstance(raw_record, dict):
            raise ContextRegistryError(
                f"{context_id}: user record должен быть object."
            )

        active_variant = raw_record.get("active_variant", "default")
        active_variant = validate_variant_id(active_variant)

        variants = raw_record.get("variants", {})
        if not isinstance(variants, dict):
            raise ContextRegistryError(
                f"{context_id}: variants должен быть object."
            )

        allowed_variables = factory["contexts"][context_id]["allowed_variables"]
        normalized_variants: dict[str, dict[str, str]] = {}

        for raw_variant_id, raw_variant in variants.items():
            variant_id = validate_variant_id(raw_variant_id)
            if not isinstance(raw_variant, dict):
                raise ContextRegistryError(
                    f"{context_id}.{variant_id}: variant должен быть object."
                )
            text = _validate_text(
                raw_variant.get("text"),
                f"{context_id}.{variant_id}.text",
            )
            description = _validate_description(
                raw_variant.get("description"),
                f"{context_id}.{variant_id}.description",
            )
            _validate_placeholders(
                text,
                allowed_variables=allowed_variables,
                context_id=f"{context_id}.{variant_id}",
            )
            normalized_variants[variant_id] = {
                "description": description,
                "text": text,
            }

        if active_variant != "default" and active_variant not in normalized_variants:
            raise ContextRegistryError(
                f"{context_id}: active_variant={active_variant!r}, "
                "но такого пользовательского варианта нет."
            )

        normalized[context_id] = {
            "active_variant": active_variant,
            "variants": normalized_variants,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "contexts": normalized,
    }


def load_user_state(
    agent_id: str = "ultra",
    *,
    path: Path | str | None = None,
    factory_path: Path | str | None = None,
) -> dict[str, Any]:
    state_path = (
        Path(path).resolve()
        if path is not None
        else get_user_contexts_path(agent_id)
    )
    factory = load_factory_catalog(path=factory_path)
    value = _read_json(state_path, allow_missing=True)
    return _validate_user_state(value, factory)


def save_user_state(
    state: dict[str, Any],
    agent_id: str = "ultra",
    *,
    path: Path | str | None = None,
    factory_path: Path | str | None = None,
    make_backup: bool = True,
) -> dict[str, Any]:
    state_path = (
        Path(path).resolve()
        if path is not None
        else get_user_contexts_path(agent_id)
    )
    factory = load_factory_catalog(path=factory_path)
    normalized = _validate_user_state(state, factory)

    backup_path = None
    if make_backup:
        backup_path = _backup_user_state(state_path, agent_id)

    _atomic_write_json(state_path, normalized)
    return {
        "path": str(state_path),
        "backup_path": str(backup_path) if backup_path else None,
    }


def _effective_variant_record(
    context_id: str,
    factory_record: dict[str, Any],
    user_record: dict[str, Any] | None,
) -> dict[str, Any]:
    user_record = user_record or {
        "active_variant": "default",
        "variants": {},
    }
    active_variant = user_record.get("active_variant", "default")
    variants = user_record.get("variants", {})

    default_override = variants.get("default")
    effective_default = default_override or {
        "description": factory_record["description"],
        "text": factory_record["factory_text"],
    }

    if active_variant == "default":
        effective = effective_default
        source = (
            "USER_DEFAULT"
            if default_override is not None
            else "FACTORY_DEFAULT"
        )
    else:
        effective = variants[active_variant]
        source = f"USER_{active_variant.upper()}"

    return {
        "active_variant": active_variant,
        "effective_source": source,
        "effective_description": effective["description"],
        "effective_text": effective["text"],
        "default_description": effective_default["description"],
        "default_text": effective_default["text"],
        "has_default_override": default_override is not None,
        "available_variants": sorted({"default", *variants.keys()}),
        "user_variants": variants,
    }


def get_context_record(
    context_id: str,
    agent_id: str = "ultra",
    *,
    state_path: Path | str | None = None,
    factory_path: Path | str | None = None,
) -> dict[str, Any]:
    context_id = validate_context_id(context_id)
    factory = load_factory_catalog(path=factory_path)
    factory_record = factory["contexts"].get(context_id)
    if factory_record is None:
        raise KeyError(f"Неизвестный context_id: {context_id}")

    user_state = load_user_state(
        agent_id,
        path=state_path,
        factory_path=factory_path,
    )
    user_record = user_state["contexts"].get(context_id)
    effective = _effective_variant_record(
        context_id,
        factory_record,
        user_record,
    )

    return {
        **factory_record,
        **effective,
        "factory_description": factory_record["description"],
        "factory_text": factory_record["factory_text"],
        "state_path": str(
            Path(state_path).resolve()
            if state_path is not None
            else get_user_contexts_path(agent_id)
        ),
        "factory_path": str(
            Path(factory_path).resolve()
            if factory_path is not None
            else DEFAULT_FACTORY_PATH
        ),
    }


def list_context_records(
    agent_id: str = "ultra",
    *,
    group_id: str | None = None,
    state_path: Path | str | None = None,
    factory_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    factory = load_factory_catalog(path=factory_path)
    user_state = load_user_state(
        agent_id,
        path=state_path,
        factory_path=factory_path,
    )

    result: list[dict[str, Any]] = []
    for context_id in sorted(factory["contexts"]):
        factory_record = factory["contexts"][context_id]
        if group_id is not None and factory_record["group_id"] != group_id:
            continue
        user_record = user_state["contexts"].get(context_id)
        effective = _effective_variant_record(
            context_id,
            factory_record,
            user_record,
        )
        result.append({
            **factory_record,
            **effective,
            "factory_description": factory_record["description"],
            "factory_text": factory_record["factory_text"],
        })
    return result


def list_context_groups(
    *,
    factory_path: Path | str | None = None,
) -> list[dict[str, str]]:
    factory = load_factory_catalog(path=factory_path)
    groups: dict[str, str] = {}
    for record in factory["contexts"].values():
        groups[record["group_id"]] = record["group_name"]
    return [
        {"group_id": group_id, "group_name": groups[group_id]}
        for group_id in sorted(groups)
    ]


def save_context_variant(
    context_id: str,
    variant_id: str,
    text: str,
    *,
    description: str | None = None,
    agent_id: str = "ultra",
    state_path: Path | str | None = None,
    factory_path: Path | str | None = None,
) -> dict[str, Any]:
    context_id = validate_context_id(context_id)
    variant_id = validate_variant_id(variant_id)

    factory = load_factory_catalog(path=factory_path)
    factory_record = factory["contexts"].get(context_id)
    if factory_record is None:
        raise KeyError(f"Неизвестный context_id: {context_id}")

    text = _validate_text(text, f"{context_id}.{variant_id}.text")
    _validate_placeholders(
        text,
        allowed_variables=factory_record["allowed_variables"],
        context_id=f"{context_id}.{variant_id}",
    )

    state = load_user_state(
        agent_id,
        path=state_path,
        factory_path=factory_path,
    )
    record = state["contexts"].setdefault(
        context_id,
        {
            "active_variant": "default",
            "variants": {},
        },
    )

    previous = record["variants"].get(variant_id)
    if description is None:
        if previous is not None:
            description = previous["description"]
        else:
            description = factory_record["description"]
    description = _validate_description(
        description,
        f"{context_id}.{variant_id}.description",
    )

    record["variants"][variant_id] = {
        "description": description,
        "text": text,
    }

    save_result = save_user_state(
        state,
        agent_id,
        path=state_path,
        factory_path=factory_path,
    )
    return {
        **save_result,
        "context_id": context_id,
        "variant_id": variant_id,
        "record": get_context_record(
            context_id,
            agent_id,
            state_path=state_path,
            factory_path=factory_path,
        ),
    }


def set_active_variant(
    context_id: str,
    variant_id: str,
    *,
    agent_id: str = "ultra",
    state_path: Path | str | None = None,
    factory_path: Path | str | None = None,
) -> dict[str, Any]:
    context_id = validate_context_id(context_id)
    variant_id = validate_variant_id(variant_id)

    factory = load_factory_catalog(path=factory_path)
    if context_id not in factory["contexts"]:
        raise KeyError(f"Неизвестный context_id: {context_id}")

    state = load_user_state(
        agent_id,
        path=state_path,
        factory_path=factory_path,
    )
    record = state["contexts"].setdefault(
        context_id,
        {
            "active_variant": "default",
            "variants": {},
        },
    )

    if variant_id != "default" and variant_id not in record["variants"]:
        raise ValueError(
            f"{context_id}: вариант {variant_id!r} сначала нужно сохранить."
        )

    record["active_variant"] = variant_id
    save_result = save_user_state(
        state,
        agent_id,
        path=state_path,
        factory_path=factory_path,
    )
    return {
        **save_result,
        "context_id": context_id,
        "active_variant": variant_id,
        "record": get_context_record(
            context_id,
            agent_id,
            state_path=state_path,
            factory_path=factory_path,
        ),
    }


def delete_context_variant(
    context_id: str,
    variant_id: str,
    *,
    agent_id: str = "ultra",
    state_path: Path | str | None = None,
    factory_path: Path | str | None = None,
) -> dict[str, Any]:
    context_id = validate_context_id(context_id)
    variant_id = validate_variant_id(variant_id)

    factory = load_factory_catalog(path=factory_path)
    if context_id not in factory["contexts"]:
        raise KeyError(f"Неизвестный context_id: {context_id}")

    state = load_user_state(
        agent_id,
        path=state_path,
        factory_path=factory_path,
    )
    record = state["contexts"].get(context_id)
    removed = False

    if record is not None and variant_id in record["variants"]:
        del record["variants"][variant_id]
        removed = True
        if record.get("active_variant") == variant_id:
            record["active_variant"] = "default"

        if (
            record.get("active_variant") == "default"
            and not record["variants"]
        ):
            del state["contexts"][context_id]

    save_result = save_user_state(
        state,
        agent_id,
        path=state_path,
        factory_path=factory_path,
    )
    return {
        **save_result,
        "removed": removed,
        "context_id": context_id,
        "variant_id": variant_id,
        "record": get_context_record(
            context_id,
            agent_id,
            state_path=state_path,
            factory_path=factory_path,
        ),
    }


def resolve_context_text(
    context_id: str,
    variables: Mapping[str, object] | None = None,
    agent_id: str = "ultra",
    *,
    state_path: Path | str | None = None,
    factory_path: Path | str | None = None,
) -> str:
    record = get_context_record(
        context_id,
        agent_id,
        state_path=state_path,
        factory_path=factory_path,
    )
    text = record["effective_text"]
    variables = variables or {}

    placeholders = find_placeholders(text)
    missing = [name for name in placeholders if name not in variables]
    if missing:
        raise KeyError(
            f"{context_id}: не переданы variables: {', '.join(missing)}"
        )

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return str(variables[name])

    return _SIMPLE_PLACEHOLDER_RE.sub(replace, text)
