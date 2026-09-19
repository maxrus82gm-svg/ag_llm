from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


STATE_VERSION = 1
STATE_DIR = (
    Path(os.getenv("LOCALAPPDATA") or Path.home())
    / "GigaChatUltra"
).resolve()
STATE_PATH = STATE_DIR / "ui_state.json"


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


def default_ui_state() -> dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "geometry": "1500x860",
        "dark_theme": True,
        "colors": {
            "log": "#76E68A",
            "user": "#FFFFFF",
            "assistant": "#8EC5FF",
            "workspace": "#E8E8E8",
        },
        "panel_sashes": [],
        "workspaces": [],
        "active_workspace_id": None,
        "registry_initialized": False,
    }


def load_ui_state() -> dict[str, Any]:
    state = default_ui_state()
    if not STATE_PATH.is_file():
        return state

    try:
        loaded = json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return state

    if not isinstance(loaded, dict):
        return state

    if isinstance(loaded.get("geometry"), str):
        state["geometry"] = loaded["geometry"]

    if isinstance(loaded.get("dark_theme"), bool):
        state["dark_theme"] = loaded["dark_theme"]

    colors = loaded.get("colors")
    if isinstance(colors, dict):
        for key in ("log", "user", "assistant", "workspace"):
            value = colors.get(key)
            if isinstance(value, str) and value.startswith("#"):
                state["colors"][key] = value

    sashes = loaded.get("panel_sashes")
    if (
        isinstance(sashes, list)
        and len(sashes) == 2
        and all(isinstance(item, int) for item in sashes)
    ):
        state["panel_sashes"] = sashes

    workspaces = loaded.get("workspaces")
    if isinstance(workspaces, list):
        clean = []
        seen_ids = set()
        for item in workspaces:
            if not isinstance(item, dict):
                continue
            workspace_id = item.get("workspace_id")
            path = item.get("path")
            if (
                not isinstance(workspace_id, str)
                or not workspace_id
                or workspace_id in seen_ids
                or not isinstance(path, str)
                or not path
            ):
                continue
            seen_ids.add(workspace_id)
            clean.append(
                {
                    "workspace_id": workspace_id,
                    "path": path,
                    "last_chat_id": (
                        item.get("last_chat_id")
                        if isinstance(item.get("last_chat_id"), str)
                        else None
                    ),
                }
            )
        state["workspaces"] = clean

    active = loaded.get("active_workspace_id")
    if isinstance(active, str):
        state["active_workspace_id"] = active

    if isinstance(loaded.get("registry_initialized"), bool):
        state["registry_initialized"] = loaded["registry_initialized"]

    return state


def save_ui_state(state: dict[str, Any]) -> None:
    if not isinstance(state, dict):
        raise TypeError("UI state должен быть словарём.")
    payload = dict(state)
    payload["version"] = STATE_VERSION
    _atomic_write_json(STATE_PATH, payload)
