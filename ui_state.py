from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


STATE_VERSION = 2
STATE_DIR = (
    Path(os.getenv("LOCALAPPDATA") or Path.home())
    / "GigaChatUltra"
).resolve()
STATE_PATH = STATE_DIR / "ui_state.json"

DEFAULT_PANEL_RATIOS = {
    "normal": [0.24, 0.80],
    "zoomed": [0.24, 0.80],
}


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
        "normal_geometry": "1500x860",
        "window_state": "normal",
        "dark_theme": True,
        "colors": {
            "log": "#76E68A",
            "user": "#FFFFFF",
            "assistant": "#8EC5FF",
            "workspace": "#E8E8E8",
        },
        "panel_ratios": {
            "normal": list(DEFAULT_PANEL_RATIOS["normal"]),
            "zoomed": list(DEFAULT_PANEL_RATIOS["zoomed"]),
        },
        "workspaces": [],
        "active_workspace_id": None,
        "registry_initialized": False,
        "main_chat_model_id": "gigachat_ultra",
        "compressor_model_id": "gigachat_3_pro",
        "compressor_reduction_percent": 50,
        "compressor_final_check_enabled": True,
    }


def _clean_ratios(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    if not all(isinstance(item, (int, float)) for item in value):
        return None
    left = float(value[0])
    right = float(value[1])
    if not (0.10 < left < 0.45 and 0.55 < right < 0.95 and left < right):
        return None
    return [left, right]


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

    loaded_version = loaded.get("version")
    is_v2 = isinstance(loaded_version, int) and loaded_version >= 2

    # При переходе со STEP 3 v1 намеренно НЕ переносим старую geometry/sashes:
    # именно они создавали неверное открытие после maximized -> restart.
    if is_v2:
        geometry = loaded.get("normal_geometry")
        if isinstance(geometry, str) and geometry.strip():
            state["normal_geometry"] = geometry

        window_state = loaded.get("window_state")
        if window_state in {"normal", "zoomed"}:
            state["window_state"] = window_state

        ratios = loaded.get("panel_ratios")
        if isinstance(ratios, dict):
            for mode in ("normal", "zoomed"):
                clean = _clean_ratios(ratios.get(mode))
                if clean is not None:
                    state["panel_ratios"][mode] = clean

    if isinstance(loaded.get("dark_theme"), bool):
        state["dark_theme"] = loaded["dark_theme"]

    colors = loaded.get("colors")
    if isinstance(colors, dict):
        for key in ("log", "user", "assistant", "workspace"):
            value = colors.get(key)
            if isinstance(value, str) and value.startswith("#"):
                state["colors"][key] = value

    workspaces = loaded.get("workspaces")
    if isinstance(workspaces, list):
        clean = []
        seen_ids = set()
        for item in workspaces:
            if not isinstance(item, dict):
                continue
            workspace_id = item.get("workspace_id")
            workspace_path = item.get("path")
            if (
                not isinstance(workspace_id, str)
                or not workspace_id
                or workspace_id in seen_ids
                or not isinstance(workspace_path, str)
                or not workspace_path
            ):
                continue
            seen_ids.add(workspace_id)
            clean.append(
                {
                    "workspace_id": workspace_id,
                    "path": workspace_path,
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

    if isinstance(loaded.get("main_chat_model_id"), str):
        state["main_chat_model_id"] = loaded["main_chat_model_id"]

    if isinstance(loaded.get("compressor_model_id"), str):
        state["compressor_model_id"] = loaded["compressor_model_id"]

    reduction_percent = loaded.get("compressor_reduction_percent")
    if (
        isinstance(reduction_percent, int)
        and not isinstance(reduction_percent, bool)
        and 1 <= reduction_percent <= 95
    ):
        state["compressor_reduction_percent"] = reduction_percent

    if isinstance(loaded.get("compressor_final_check_enabled"), bool):
        state["compressor_final_check_enabled"] = loaded[
            "compressor_final_check_enabled"
        ]

    return state


def save_ui_state(state: dict[str, Any]) -> None:
    if not isinstance(state, dict):
        raise TypeError("UI state должен быть словарём.")
    payload = dict(state)
    payload["version"] = STATE_VERSION
    _atomic_write_json(STATE_PATH, payload)
