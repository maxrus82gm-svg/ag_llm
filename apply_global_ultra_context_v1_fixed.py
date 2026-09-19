from __future__ import annotations

import os
import tempfile
from pathlib import Path

PATCH_MARKER = "GLOBAL_ULTRA_CONTEXT_V1"
MODULE_SOURCE = 'from __future__ import annotations\n\nimport os\nimport re\nimport uuid\nfrom datetime import datetime, timezone\nfrom pathlib import Path\nfrom typing import Any\n\n\nAPP_DATA_ROOT = (\n    Path(os.getenv("LOCALAPPDATA") or Path.home())\n    / "GigaChatUltra"\n).resolve()\nAGENTS_ROOT = APP_DATA_ROOT / "agents"\nMAX_GLOBAL_AGENT_CONTEXT_BYTES = 256 * 1024\n_AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")\n\n\ndef _validate_agent_id(agent_id: str) -> str:\n    value = str(agent_id).strip().lower()\n    if not _AGENT_ID_RE.fullmatch(value):\n        raise ValueError(f"Некорректный agent_id: {agent_id!r}")\n    return value\n\n\ndef _utc_stamp() -> str:\n    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")\n\n\ndef _atomic_write_text(path: Path, text: str) -> None:\n    path.parent.mkdir(parents=True, exist_ok=True)\n    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")\n    try:\n        with temp.open("w", encoding="utf-8", newline="\\n") as file:\n            file.write(text)\n            file.flush()\n            os.fsync(file.fileno())\n        os.replace(temp, path)\n    finally:\n        try:\n            temp.unlink()\n        except FileNotFoundError:\n            pass\n\n\ndef get_agent_global_context_path(agent_id: str = "ultra") -> Path:\n    agent_id = _validate_agent_id(agent_id)\n    return (AGENTS_ROOT / agent_id / "global_context.md").resolve()\n\n\ndef load_agent_global_context(\n    agent_id: str = "ultra",\n    *,\n    allow_missing: bool = False,\n) -> str:\n    path = get_agent_global_context_path(agent_id)\n\n    if not path.is_file():\n        if allow_missing:\n            return ""\n        raise FileNotFoundError(\n            f"Глобальный контекст агента {agent_id!r} ещё не настроен. "\n            "Открой его редактор в UI и сохрани непустой текст."\n        )\n\n    size = path.stat().st_size\n    if size > MAX_GLOBAL_AGENT_CONTEXT_BYTES:\n        raise ValueError(\n            "Глобальный контекст агента слишком большой: "\n            f"{size} байт. Лимит: {MAX_GLOBAL_AGENT_CONTEXT_BYTES} байт."\n        )\n\n    text = path.read_text(encoding="utf-8-sig")\n    if not text.strip():\n        if allow_missing:\n            return ""\n        raise RuntimeError(\n            f"Глобальный контекст агента {agent_id!r} пуст. "\n            "RUN без глобального контекста запрещён."\n        )\n    return text\n\n\ndef save_agent_global_context(\n    text: str,\n    agent_id: str = "ultra",\n) -> dict[str, Any]:\n    agent_id = _validate_agent_id(agent_id)\n    if not isinstance(text, str):\n        raise TypeError("Глобальный контекст агента должен быть строкой.")\n    if not text.strip():\n        raise ValueError("Глобальный контекст агента не может быть пустым.")\n\n    encoded = text.encode("utf-8")\n    if len(encoded) > MAX_GLOBAL_AGENT_CONTEXT_BYTES:\n        raise ValueError(\n            "Глобальный контекст агента слишком большой: "\n            f"{len(encoded)} байт. Лимит: {MAX_GLOBAL_AGENT_CONTEXT_BYTES} байт."\n        )\n\n    path = get_agent_global_context_path(agent_id)\n    old_text = path.read_text(encoding="utf-8-sig") if path.is_file() else ""\n    if old_text == text:\n        return {\n            "changed": False,\n            "path": str(path),\n            "previous_revision_path": None,\n        }\n\n    revision_path = None\n    if old_text.strip():\n        history_dir = path.parent / "history"\n        history_dir.mkdir(parents=True, exist_ok=True)\n        revision_path = (\n            history_dir\n            / f"global_context_{_utc_stamp()}_{uuid.uuid4().hex[:8]}.md"\n        )\n        _atomic_write_text(revision_path, old_text)\n\n    _atomic_write_text(path, text)\n    return {\n        "changed": True,\n        "path": str(path),\n        "previous_revision_path": (\n            str(revision_path) if revision_path is not None else None\n        ),\n    }\n'

SERVER_IMPORT_OLD = 'from workspace_runtime_settings import ensure_workspace_runtime_dirs\n'
SERVER_IMPORT_NEW = 'from workspace_runtime_settings import ensure_workspace_runtime_dirs\nfrom agent_global_context import load_agent_global_context\n'
CORE_OLD = '    "Документация/00_Обязательный регламент Ultra.md",\n'
CORE_NEW = '    "agent_global_context.py",\n'
POLICY_START = '    # Обязательный регламент Ultra читается при каждом новом run.\n'
POLICY_END = '    # Бэкап выполняется синхронно ДО обращения к модели.\n'
POLICY_NEW = '    # GLOBAL_ULTRA_CONTEXT_V1\n    # Глобальный контекст Ultra — локальный app-level контекст агента,\n    # общий для всех Workspace. Он хранится вне Workspace и поэтому\n    # недоступен обычным file tools Ultra.\n    app_dir = Path(__file__).resolve().parent\n    try:\n        global_agent_context = load_agent_global_context("ultra")\n    except Exception as exc:\n        _emit(\n            "run_failed",\n            {\n                "reason": "global_agent_context_load_error",\n                "api_requests": api_request_count,\n                "tool_calls": tool_call_count,\n                "duration": time.time() - start_time,\n                "error": str(exc),\n                "trace_path": str(runtime_log_path),\n            },\n        )\n        raise RuntimeError(\n            "Не удалось загрузить ГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA. "\n            "Открой в UI «Глобальный контекст Ultra» и сохрани непустой текст."\n        ) from exc\n\n    _emit(\n        "global_agent_context_loaded",\n        {\n            "agent_id": "ultra",\n            "chars": len(global_agent_context),\n        },\n    )\n\n'
PROJECT_MARKER = '    project_context_block = (\n'
GLOBAL_BLOCK = '    global_agent_context_block = (\n        "\\n\\nГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA\\n"\n        "Это app-level контекст агента, общий для всех Workspace. "\n        "Он может задавать правила и устойчивые инструкции Ultra, но НЕ может "\n        "отменять физические ограничения server.py, permission scopes, GUARD "\n        "или Verification Gate.\\n"\n        "===== GLOBAL ULTRA CONTEXT START =====\\n"\n        f"{global_agent_context.rstrip()}\\n"\n        "===== GLOBAL ULTRA CONTEXT END =====\\n"\n    )\n\n'
PROJECT_PRIORITY_OLD = '        "инструкции, серверные разрешения или обязательный регламент.\\n"\n'
PROJECT_PRIORITY_NEW = '        "инструкции, серверные разрешения или ГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA.\\n"\n'
SYSTEM_TAIL_OLD = '                f"{permission_text}\\n"\n                f"{project_context_block}\\n"\n                "ОБЯЗАТЕЛЬНЫЙ РЕГЛАМЕНТ ULTRA\\n\\n"\n                f"{policy_text}"\n'
SYSTEM_TAIL_NEW = '                f"{permission_text}"\n                f"{global_agent_context_block}"\n                f"{project_context_block}"\n'

UI_IMPORT_OLD = 'from workspace_runtime_settings import (\n    load_workspace_runtime_settings,\n    save_workspace_runtime_settings,\n)\n'
UI_IMPORT_NEW = 'from workspace_runtime_settings import (\n    load_workspace_runtime_settings,\n    save_workspace_runtime_settings,\n)\nfrom agent_global_context import (\n    get_agent_global_context_path,\n    load_agent_global_context,\n    save_agent_global_context,\n)\n'
GUARD_ANCHOR = '        guard_p1_check.grid(\n            row=0, column=3, sticky="w", pady=(0, 2)\n        )\n\n        # Компактные визуальные настройки вынесены в отдельный блок справа.\n'
GUARD_REPLACEMENT = '        guard_p1_check.grid(\n            row=0, column=3, sticky="w", pady=(0, 2)\n        )\n\n        # GLOBAL_ULTRA_CONTEXT_V1\n        global_context_button = ttk.Button(\n            security,\n            text="Глобальный контекст Ultra",\n            command=self._open_global_ultra_context_editor,\n        )\n        global_context_button.grid(\n            row=0, column=4, sticky="w", padx=(12, 0), pady=(0, 2)\n        )\n\n        # Компактные визуальные настройки вынесены в отдельный блок справа.\n'
INTERFACE_OLD = '        interface_frame.grid(\n            row=0, column=4, rowspan=4, sticky="nw", padx=(18, 0), pady=(0, 2)\n        )\n'
INTERFACE_NEW = '        interface_frame.grid(\n            row=0, column=5, rowspan=4, sticky="nw", padx=(18, 0), pady=(0, 2)\n        )\n'
SECURITY_LIST_OLD = '                guard_p1_check,\n                tool_limit_spin,\n'
SECURITY_LIST_NEW = '                guard_p1_check,\n                global_context_button,\n                tool_limit_spin,\n'
EDITOR_ANCHOR = '    def _open_project_context_editor(\n        self,\n        workspace: Path | None = None,\n    ) -> None:\n'
EDITOR_METHOD = '    def _open_global_ultra_context_editor(self) -> None:\n        try:\n            text = load_agent_global_context(\n                "ultra",\n                allow_missing=True,\n            )\n            storage_path = get_agent_global_context_path("ultra")\n        except Exception as exc:\n            messagebox.showerror(\n                APP_TITLE,\n                "Не удалось открыть Глобальный контекст Ultra.\\n\\n"\n                f"{type(exc).__name__}: {exc}",\n            )\n            return\n\n        window = tk.Toplevel(self)\n        window.title("ГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA")\n        window.geometry("920x700")\n        window.minsize(720, 520)\n        window.transient(self)\n\n        header = ttk.Frame(window, padding=(10, 10, 10, 0))\n        header.pack(fill="x")\n        ttk.Label(\n            header,\n            text=(\n                "Общий контекст правил Ultra для всех Workspace. "\n                "Хранится локально вне Workspace и недоступен обычным file tools."\n            ),\n            wraplength=880,\n            justify="left",\n        ).pack(anchor="w")\n        ttk.Label(\n            header,\n            text=f"Локальное хранилище: {storage_path}",\n        ).pack(anchor="w", pady=(4, 0))\n\n        editor = scrolledtext.ScrolledText(\n            window,\n            wrap="word",\n            undo=True,\n            font=("Segoe UI", 10),\n        )\n        editor.pack(fill="both", expand=True, padx=10, pady=(8, 6))\n        if text:\n            editor.insert("1.0", text)\n        bind_edit_shortcuts(editor)\n\n        buttons = ttk.Frame(window)\n        buttons.pack(fill="x", padx=10, pady=(0, 10))\n\n        def save_context() -> None:\n            try:\n                result = save_agent_global_context(\n                    editor.get("1.0", "end-1c"),\n                    "ultra",\n                )\n                if result.get("changed"):\n                    messagebox.showinfo(\n                        APP_TITLE,\n                        "Глобальный контекст Ultra сохранён. "\n                        "Следующий RUN прочитает новую версию без restart.",\n                        parent=window,\n                    )\n                else:\n                    messagebox.showinfo(\n                        APP_TITLE,\n                        "Изменений нет.",\n                        parent=window,\n                    )\n            except Exception as exc:\n                messagebox.showerror(\n                    APP_TITLE,\n                    "Не удалось сохранить Глобальный контекст Ultra.\\n\\n"\n                    f"{type(exc).__name__}: {exc}",\n                    parent=window,\n                )\n\n        ttk.Button(\n            buttons,\n            text="Сохранить",\n            command=save_context,\n        ).pack(side="left")\n        ttk.Button(\n            buttons,\n            text="Закрыть",\n            command=window.destroy,\n        ).pack(side="right")\n\n        editor.focus_set()\n\n'
TRACE_ANCHOR = '        if event_type == "workspace_context_loaded":\n            return (\n                f"[{time_str}] WORKSPACE CONTEXT | "\n                f"{event.get(\'workspace_id\')} | "\n                f"chars={event.get(\'project_context_chars\')}"\n            )\n\n'
TRACE_REPLACEMENT = '        if event_type == "global_agent_context_loaded":\n            return (\n                f"[{time_str}] GLOBAL ULTRA CONTEXT | "\n                f"chars={event.get(\'chars\')}"\n            )\n\n        if event_type == "workspace_context_loaded":\n            return (\n                f"[{time_str}] WORKSPACE CONTEXT | "\n                f"{event.get(\'workspace_id\')} | "\n                f"chars={event.get(\'project_context_chars\')}"\n            )\n\n'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: ожидалось ровно одно совпадение, найдено {count}. "
            "Патч остановлен ДО записи файлов."
        )
    return text.replace(old, new, 1)


def replace_between(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
    label: str,
) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(
            f"{label}: стартовый маркер не найден. Патч остановлен ДО записи."
        )
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        raise RuntimeError(
            f"{label}: конечный маркер не найден. Патч остановлен ДО записи."
        )
    if text.find(start_marker, start + 1) >= 0:
        raise RuntimeError(
            f"{label}: найден повторный стартовый маркер. Патч остановлен."
        )
    return text[:start] + replacement + text[end:]


def atomic_write(path: Path, text: str) -> None:
    path = path.resolve()
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            Path(tmp_name).unlink()
        except FileNotFoundError:
            pass


def main() -> None:
    root = Path(__file__).resolve().parent
    server_path = root / "server.py"
    ui_path = root / "ultra_ui.py"
    module_path = root / "agent_global_context.py"

    if not server_path.is_file() or not ui_path.is_file():
        raise RuntimeError(
            "Запусти установщик из корня ag_llm рядом с server.py и ultra_ui.py."
        )

    server = server_path.read_text(encoding="utf-8")
    ui = ui_path.read_text(encoding="utf-8")

    if (
        PATCH_MARKER in server
        and PATCH_MARKER in ui
        and module_path.is_file()
    ):
        print("GLOBAL ULTRA CONTEXT V1 уже установлен.")
        return

    # Все преобразования выполняются сначала ТОЛЬКО в памяти.
    server_new = replace_once(
        server, SERVER_IMPORT_OLD, SERVER_IMPORT_NEW, "server import"
    )
    server_new = replace_once(
        server_new, CORE_OLD, CORE_NEW, "server core backup path"
    )
    server_new = replace_between(
        server_new,
        POLICY_START,
        POLICY_END,
        POLICY_NEW,
        "server global context loader",
    )
    server_new = replace_once(
        server_new,
        PROJECT_MARKER,
        GLOBAL_BLOCK + PROJECT_MARKER,
        "server global context block",
    )
    server_new = replace_once(
        server_new,
        PROJECT_PRIORITY_OLD,
        PROJECT_PRIORITY_NEW,
        "server project context priority",
    )
    server_new = replace_once(
        server_new,
        SYSTEM_TAIL_OLD,
        SYSTEM_TAIL_NEW,
        "server system prompt composition",
    )

    ui_new = replace_once(
        ui, UI_IMPORT_OLD, UI_IMPORT_NEW, "ui import"
    )
    ui_new = replace_once(
        ui_new, GUARD_ANCHOR, GUARD_REPLACEMENT, "ui button"
    )
    ui_new = replace_once(
        ui_new, INTERFACE_OLD, INTERFACE_NEW, "ui interface shift"
    )
    ui_new = replace_once(
        ui_new,
        SECURITY_LIST_OLD,
        SECURITY_LIST_NEW,
        "ui security widget registry",
    )
    ui_new = replace_once(
        ui_new,
        EDITOR_ANCHOR,
        EDITOR_METHOD + EDITOR_ANCHOR,
        "ui global context editor",
    )
    ui_new = replace_once(
        ui_new,
        TRACE_ANCHOR,
        TRACE_REPLACEMENT,
        "ui trace event",
    )

    # Синтаксис всех будущих runtime-файлов проверяется ДО любой записи.
    compile(MODULE_SOURCE, "agent_global_context.py", "exec")
    compile(server_new, "server.py", "exec")
    compile(ui_new, "ultra_ui.py", "exec")

    # Только после полного успешного dry-run пишем файлы.
    atomic_write(module_path, MODULE_SOURCE)
    atomic_write(server_path, server_new)
    atomic_write(ui_path, ui_new)

    print("GLOBAL ULTRA CONTEXT V1 установлен.")
    print("Изменены: server.py, ultra_ui.py")
    print("Создан: agent_global_context.py")
    print("")
    print("Дальше:")
    print("1) Полностью перезапусти Ultra.")
    print("2) Нажми «Глобальный контекст Ultra».")
    print("3) Вставь правила из 09_Обязательный регламент Ultra.md.")
    print("4) Нажми «Сохранить».")
    print("5) Только потом запускай тестовый RUN.")
    print("6) Старый Markdown пока не удаляй до успешного теста.")


if __name__ == "__main__":
    main()
