from __future__ import annotations

import os
import tempfile
from pathlib import Path

PATCH_MARKER = "GLOBAL_ULTRA_CONTEXT_V1"
MODULE_SOURCE = 'from __future__ import annotations\n\nimport os\nimport re\nimport uuid\nfrom datetime import datetime, timezone\nfrom pathlib import Path\nfrom typing import Any\n\n\nAPP_DATA_ROOT = (\n    Path(os.getenv("LOCALAPPDATA") or Path.home())\n    / "GigaChatUltra"\n).resolve()\nAGENTS_ROOT = APP_DATA_ROOT / "agents"\nMAX_GLOBAL_AGENT_CONTEXT_BYTES = 256 * 1024\n_AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")\n\n\ndef _validate_agent_id(agent_id: str) -> str:\n    value = str(agent_id).strip().lower()\n    if not _AGENT_ID_RE.fullmatch(value):\n        raise ValueError(f"Некорректный agent_id: {agent_id!r}")\n    return value\n\n\ndef _utc_stamp() -> str:\n    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")\n\n\ndef _atomic_write_text(path: Path, text: str) -> None:\n    path.parent.mkdir(parents=True, exist_ok=True)\n    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")\n    try:\n        with temp.open("w", encoding="utf-8", newline="\\n") as file:\n            file.write(text)\n            file.flush()\n            os.fsync(file.fileno())\n        os.replace(temp, path)\n    finally:\n        try:\n            temp.unlink()\n        except FileNotFoundError:\n            pass\n\n\ndef get_agent_global_context_path(agent_id: str = "ultra") -> Path:\n    agent_id = _validate_agent_id(agent_id)\n    return (AGENTS_ROOT / agent_id / "global_context.md").resolve()\n\n\ndef load_agent_global_context(\n    agent_id: str = "ultra",\n    *,\n    allow_missing: bool = False,\n) -> str:\n    path = get_agent_global_context_path(agent_id)\n\n    if not path.is_file():\n        if allow_missing:\n            return ""\n        raise FileNotFoundError(\n            f"Глобальный контекст агента {agent_id!r} ещё не настроен. "\n            "Открой его редактор в UI и сохрани непустой текст."\n        )\n\n    size = path.stat().st_size\n    if size > MAX_GLOBAL_AGENT_CONTEXT_BYTES:\n        raise ValueError(\n            "Глобальный контекст агента слишком большой: "\n            f"{size} байт. Лимит: {MAX_GLOBAL_AGENT_CONTEXT_BYTES} байт."\n        )\n\n    text = path.read_text(encoding="utf-8-sig")\n    if not text.strip():\n        if allow_missing:\n            return ""\n        raise RuntimeError(\n            f"Глобальный контекст агента {agent_id!r} пуст. "\n            "RUN без глобального контекста запрещён."\n        )\n    return text\n\n\ndef save_agent_global_context(\n    text: str,\n    agent_id: str = "ultra",\n) -> dict[str, Any]:\n    agent_id = _validate_agent_id(agent_id)\n    if not isinstance(text, str):\n        raise TypeError("Глобальный контекст агента должен быть строкой.")\n    if not text.strip():\n        raise ValueError("Глобальный контекст агента не может быть пустым.")\n\n    encoded = text.encode("utf-8")\n    if len(encoded) > MAX_GLOBAL_AGENT_CONTEXT_BYTES:\n        raise ValueError(\n            "Глобальный контекст агента слишком большой: "\n            f"{len(encoded)} байт. Лимит: {MAX_GLOBAL_AGENT_CONTEXT_BYTES} байт."\n        )\n\n    path = get_agent_global_context_path(agent_id)\n    old_text = path.read_text(encoding="utf-8-sig") if path.is_file() else ""\n    if old_text == text:\n        return {\n            "changed": False,\n            "path": str(path),\n            "previous_revision_path": None,\n        }\n\n    revision_path = None\n    if old_text.strip():\n        history_dir = path.parent / "history"\n        history_dir.mkdir(parents=True, exist_ok=True)\n        revision_path = (\n            history_dir\n            / f"global_context_{_utc_stamp()}_{uuid.uuid4().hex[:8]}.md"\n        )\n        _atomic_write_text(revision_path, old_text)\n\n    _atomic_write_text(path, text)\n    return {\n        "changed": True,\n        "path": str(path),\n        "previous_revision_path": (\n            str(revision_path) if revision_path is not None else None\n        ),\n    }\n'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: ожидалось ровно одно совпадение, найдено {count}. "
            "Патч отменён без записи."
        )
    return text.replace(old, new, 1)


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
            "Запусти этот файл из корня ag_llm рядом с server.py и ultra_ui.py."
        )

    server = server_path.read_text(encoding="utf-8")
    ui = ui_path.read_text(encoding="utf-8")

    if PATCH_MARKER in server and PATCH_MARKER in ui and module_path.is_file():
        print("GLOBAL ULTRA CONTEXT V1 уже установлен.")
        return

    server = replace_once(
        server,
        'from workspace_runtime_settings import ensure_workspace_runtime_dirs\n',
        'from workspace_runtime_settings import ensure_workspace_runtime_dirs\n'
        'from agent_global_context import load_agent_global_context\n',
        "server import",
    )

    server = replace_once(
        server,
        '    "Документация/00_Обязательный регламент Ultra.md",\n',
        '    "agent_global_context.py",\n',
        "server core backup path",
    )

    old_policy_block = '''    # Обязательный регламент Ultra читается при каждом новом run.
    app_dir = Path(__file__).resolve().parent
    policy_path = app_dir / "Документация" / "00_Обязательный регламент Ultra.md"
    try:
        policy_text = policy_path.read_text(encoding="utf-8")
    except Exception as exc:
        _emit("run_failed", {
            "reason": "policy_load_error",
            "api_requests": api_request_count,
            "tool_calls": tool_call_count,
            "duration": time.time() - start_time,
            "error": str(exc),
            "trace_path": str(runtime_log_path),
        })
        raise RuntimeError(
            "Не удалось загрузить обязательный регламент Ultra. "
            "Запуск без регламента запрещён."
        ) from exc

    if not policy_text.strip():
        _emit("run_failed", {
            "reason": "policy_empty",
            "api_requests": api_request_count,
            "tool_calls": tool_call_count,
            "duration": time.time() - start_time,
            "trace_path": str(runtime_log_path),
        })
        raise RuntimeError(
            "Обязательный регламент Ultra пуст. "
            "Запуск без регламента запрещён."
        )
'''

    new_policy_block = '''    # GLOBAL_ULTRA_CONTEXT_V1
    # Глобальный контекст Ultra — локальный app-level контекст агента,
    # общий для всех Workspace. Он хранится вне Workspace и поэтому
    # недоступен обычным file tools Ultra.
    app_dir = Path(__file__).resolve().parent
    try:
        global_agent_context = load_agent_global_context("ultra")
    except Exception as exc:
        _emit(
            "run_failed",
            {
                "reason": "global_agent_context_load_error",
                "api_requests": api_request_count,
                "tool_calls": tool_call_count,
                "duration": time.time() - start_time,
                "error": str(exc),
                "trace_path": str(runtime_log_path),
            },
        )
        raise RuntimeError(
            "Не удалось загрузить ГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA. "
            "Открой в UI «Глобальный контекст Ultra» и сохрани непустой текст."
        ) from exc

    _emit(
        "global_agent_context_loaded",
        {
            "agent_id": "ultra",
            "chars": len(global_agent_context),
        },
    )
'''
    server = replace_once(
        server,
        old_policy_block,
        new_policy_block,
        "server global context loader",
    )

    permission_anchor = '''    project_context_block = (
        "\n\nPROJECT CONTEXT ТЕКУЩЕГО WORKSPACE\n"
'''
    global_block = '''    global_agent_context_block = (
        "\n\nГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA\n"
        "Это app-level контекст агента, общий для всех Workspace. "
        "Он может задавать правила и устойчивые инструкции Ultra, но НЕ может "
        "отменять физические ограничения server.py, permission scopes, GUARD "
        "или Verification Gate.\n"
        "===== GLOBAL ULTRA CONTEXT START =====\n"
        f"{global_agent_context.rstrip()}\n"
        "===== GLOBAL ULTRA CONTEXT END =====\n"
    )

    project_context_block = (
        "\n\nPROJECT CONTEXT ТЕКУЩЕГО WORKSPACE\n"
'''
    server = replace_once(
        server,
        permission_anchor,
        global_block,
        "server global context block",
    )

    server = replace_once(
        server,
        '"инструкции, серверные разрешения или обязательный регламент.\n"',
        '"инструкции, серверные разрешения или ГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA.\n"',
        "server project context priority text",
    )

    old_system_tail = '''                f"{permission_text}\n"
                f"{project_context_block}\n"
                "ОБЯЗАТЕЛЬНЫЙ РЕГЛАМЕНТ ULTRA\n\n"
                f"{policy_text}"
'''
    new_system_tail = '''                f"{permission_text}"
                f"{global_agent_context_block}"
                f"{project_context_block}"
'''
    server = replace_once(
        server,
        old_system_tail,
        new_system_tail,
        "server system prompt composition",
    )

    ui = replace_once(
        ui,
        'from workspace_runtime_settings import (\n'
        '    load_workspace_runtime_settings,\n'
        '    save_workspace_runtime_settings,\n'
        ')\n',
        'from workspace_runtime_settings import (\n'
        '    load_workspace_runtime_settings,\n'
        '    save_workspace_runtime_settings,\n'
        ')\n'
        'from agent_global_context import (\n'
        '    get_agent_global_context_path,\n'
        '    load_agent_global_context,\n'
        '    save_agent_global_context,\n'
        ')\n',
        "ui import",
    )

    guard_anchor = '''        guard_p1_check.grid(
            row=0, column=3, sticky="w", pady=(0, 2)
        )

        # Компактные визуальные настройки вынесены в отдельный блок справа.
'''
    guard_replacement = '''        guard_p1_check.grid(
            row=0, column=3, sticky="w", pady=(0, 2)
        )

        # GLOBAL_ULTRA_CONTEXT_V1
        global_context_button = ttk.Button(
            security,
            text="Глобальный контекст Ultra",
            command=self._open_global_ultra_context_editor,
        )
        global_context_button.grid(
            row=0, column=4, sticky="w", padx=(12, 0), pady=(0, 2)
        )

        # Компактные визуальные настройки вынесены в отдельный блок справа.
'''
    ui = replace_once(
        ui,
        guard_anchor,
        guard_replacement,
        "ui global context button",
    )

    ui = replace_once(
        ui,
        '''        interface_frame.grid(
            row=0, column=4, rowspan=4, sticky="nw", padx=(18, 0), pady=(0, 2)
        )
''',
        '''        interface_frame.grid(
            row=0, column=5, rowspan=4, sticky="nw", padx=(18, 0), pady=(0, 2)
        )
''',
        "ui interface frame shift",
    )

    ui = replace_once(
        ui,
        '''                guard_p1_check,
                tool_limit_spin,
''',
        '''                guard_p1_check,
                global_context_button,
                tool_limit_spin,
''',
        "ui security widgets",
    )

    editor_anchor = '''    def _open_project_context_editor(
        self,
        workspace: Path | None = None,
    ) -> None:
'''
    editor_method = '''    def _open_global_ultra_context_editor(self) -> None:
        try:
            text = load_agent_global_context(
                "ultra",
                allow_missing=True,
            )
            storage_path = get_agent_global_context_path("ultra")
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                "Не удалось открыть Глобальный контекст Ultra.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        window = tk.Toplevel(self)
        window.title("ГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA")
        window.geometry("920x700")
        window.minsize(720, 520)
        window.transient(self)

        header = ttk.Frame(window, padding=(10, 10, 10, 0))
        header.pack(fill="x")
        ttk.Label(
            header,
            text=(
                "Общий контекст правил Ultra для всех Workspace. "
                "Хранится локально вне Workspace и недоступен обычным file tools."
            ),
            wraplength=880,
            justify="left",
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=f"Локальное хранилище: {storage_path}",
        ).pack(anchor="w", pady=(4, 0))

        editor = scrolledtext.ScrolledText(
            window,
            wrap="word",
            undo=True,
            font=("Segoe UI", 10),
        )
        editor.pack(fill="both", expand=True, padx=10, pady=(8, 6))
        if text:
            editor.insert("1.0", text)
        bind_edit_shortcuts(editor)

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=10, pady=(0, 10))

        def save_context() -> None:
            try:
                result = save_agent_global_context(
                    editor.get("1.0", "end-1c"),
                    "ultra",
                )
                if result.get("changed"):
                    messagebox.showinfo(
                        APP_TITLE,
                        "Глобальный контекст Ultra сохранён. "
                        "Следующий RUN прочитает новую версию без restart.",
                        parent=window,
                    )
                else:
                    messagebox.showinfo(
                        APP_TITLE,
                        "Изменений нет.",
                        parent=window,
                    )
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    "Не удалось сохранить Глобальный контекст Ultra.\n\n"
                    f"{type(exc).__name__}: {exc}",
                    parent=window,
                )

        ttk.Button(
            buttons,
            text="Сохранить",
            command=save_context,
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Закрыть",
            command=window.destroy,
        ).pack(side="right")

        editor.focus_set()

'''
    ui = replace_once(
        ui,
        editor_anchor,
        editor_method + editor_anchor,
        "ui global context editor",
    )

    trace_anchor = '''        if event_type == "workspace_context_loaded":
            return (
                f"[{time_str}] WORKSPACE CONTEXT | "
                f"{event.get('workspace_id')} | "
                f"chars={event.get('project_context_chars')}"
            )

'''
    trace_replacement = '''        if event_type == "global_agent_context_loaded":
            return (
                f"[{time_str}] GLOBAL ULTRA CONTEXT | "
                f"chars={event.get('chars')}"
            )

        if event_type == "workspace_context_loaded":
            return (
                f"[{time_str}] WORKSPACE CONTEXT | "
                f"{event.get('workspace_id')} | "
                f"chars={event.get('project_context_chars')}"
            )

'''
    ui = replace_once(
        ui,
        trace_anchor,
        trace_replacement,
        "ui global context trace",
    )

    compile(MODULE_SOURCE, "agent_global_context.py", "exec")
    compile(server, "server.py", "exec")
    compile(ui, "ultra_ui.py", "exec")

    atomic_write(module_path, MODULE_SOURCE)
    atomic_write(server_path, server)
    atomic_write(ui_path, ui)

    print("GLOBAL ULTRA CONTEXT V1 установлен.")
    print("Изменены: server.py, ultra_ui.py")
    print("Создан: agent_global_context.py")
    print("")
    print("ВАЖНО:")
    print("1) Полностью перезапусти приложение.")
    print("2) Нажми «Глобальный контекст Ultra».")
    print("3) Вставь туда текст правил из старого Markdown и сохрани.")
    print("4) Только после этого запускай тестовый RUN.")
    print("5) Старый Markdown-регламент пока НЕ удаляй до успешного теста.")


if __name__ == "__main__":
    main()
