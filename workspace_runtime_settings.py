from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


SETTINGS_VERSION = 1
APP_DATA_ROOT = (
    Path(os.getenv("LOCALAPPDATA") or Path.home())
    / "GigaChatUltra"
).resolve()
SETTINGS_PATH = APP_DATA_ROOT / "workspace_runtime_settings.json"


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _load_store() -> dict[str, Any]:
    if not SETTINGS_PATH.is_file():
        return {"version": SETTINGS_VERSION, "workspaces": {}}

    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Повреждён файл локальных настроек Workspace: {SETTINGS_PATH}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            "Повреждён файл локальных настроек Workspace: "
            "корень JSON должен быть объектом."
        )

    version = data.get("version")
    if version != SETTINGS_VERSION:
        raise RuntimeError(
            f"Неподдерживаемая версия workspace runtime settings: {version!r}."
        )

    workspaces = data.get("workspaces")
    if not isinstance(workspaces, dict):
        raise RuntimeError(
            "Повреждён файл локальных настроек Workspace: "
            "'workspaces' должен быть объектом."
        )

    return data


def _validate_workspace_id(workspace_id: str) -> str:
    value = str(workspace_id).strip()
    if not value.startswith("ws_") or len(value) < 8:
        raise ValueError(f"Некорректный workspace_id: {workspace_id!r}")
    return value


def _clean_optional_absolute_path(value: str | Path | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip().strip('"')
    if not text:
        return None

    path = Path(text).expanduser()
    if not path.is_absolute():
        raise ValueError(
            "Путь должен быть абсолютным. "
            "Оставь поле пустым для значения по умолчанию."
        )
    return str(path.resolve())


def default_workspace_paths(workspace_id: str) -> dict[str, str]:
    workspace_id = _validate_workspace_id(workspace_id)
    base = APP_DATA_ROOT / "workspaces" / workspace_id
    return {
        "backup_dir": str((base / "backups").resolve()),
        "log_dir": str((base / "logs").resolve()),
    }


def load_workspace_runtime_settings(workspace_id: str) -> dict[str, Any]:
    workspace_id = _validate_workspace_id(workspace_id)
    defaults = default_workspace_paths(workspace_id)
    store = _load_store()
    raw = store["workspaces"].get(workspace_id)
    if not isinstance(raw, dict):
        raw = {}

    backup_override = _clean_optional_absolute_path(raw.get("backup_dir"))
    log_override = _clean_optional_absolute_path(raw.get("log_dir"))

    return {
        "workspace_id": workspace_id,
        "backup_dir": backup_override or defaults["backup_dir"],
        "log_dir": log_override or defaults["log_dir"],
        "backup_is_default": backup_override is None,
        "log_is_default": log_override is None,
        "default_backup_dir": defaults["backup_dir"],
        "default_log_dir": defaults["log_dir"],
    }


def save_workspace_runtime_settings(
    workspace_id: str,
    *,
    backup_dir: str | Path | None,
    log_dir: str | Path | None,
) -> dict[str, Any]:
    workspace_id = _validate_workspace_id(workspace_id)
    defaults = default_workspace_paths(workspace_id)

    backup_value = _clean_optional_absolute_path(backup_dir)
    log_value = _clean_optional_absolute_path(log_dir)

    if backup_value == defaults["backup_dir"]:
        backup_value = None
    if log_value == defaults["log_dir"]:
        log_value = None

    for value in (backup_value, log_value):
        if value is not None:
            Path(value).mkdir(parents=True, exist_ok=True)

    store = _load_store()
    workspaces = store["workspaces"]
    record: dict[str, Any] = {}

    if backup_value is not None:
        record["backup_dir"] = backup_value
    if log_value is not None:
        record["log_dir"] = log_value

    if record:
        workspaces[workspace_id] = record
    else:
        workspaces.pop(workspace_id, None)

    _atomic_write_json(
        SETTINGS_PATH,
        {
            "version": SETTINGS_VERSION,
            "workspaces": workspaces,
        },
    )
    return load_workspace_runtime_settings(workspace_id)


def ensure_workspace_runtime_dirs(workspace_id: str) -> dict[str, Any]:
    settings = load_workspace_runtime_settings(workspace_id)
    Path(settings["backup_dir"]).mkdir(parents=True, exist_ok=True)
    Path(settings["log_dir"]).mkdir(parents=True, exist_ok=True)
    return settings
