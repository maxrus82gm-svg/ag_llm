from __future__ import annotations
import py_compile
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / 'server.py'
UI = ROOT / 'ultra_ui.py'
RUNTIME = ROOT / 'workspace_runtime_settings.py'
SERVER_BACKUP = ROOT / 'server.py.before_workspace_backup_settings'
UI_BACKUP = ROOT / 'ultra_ui.py.before_workspace_backup_settings'

SERVER_IMPORT_OLD = 'from context_storage import (\n    ensure_workspace_storage,\n    load_chat_messages,\n    load_project_context,\n)\n\nmcp = MCPServer("GigaChat Ultra Subagent")\n'
SERVER_IMPORT_NEW = 'from context_storage import (\n    ensure_workspace_storage,\n    load_chat_messages,\n    load_project_context,\n)\nfrom workspace_runtime_settings import ensure_workspace_runtime_dirs\n\nmcp = MCPServer("GigaChat Ultra Subagent")\n'
SERVER_CORE_OLD = '    "context_storage.py",\n    "ui_state.py",\n'
SERVER_CORE_NEW = '    "context_storage.py",\n    "workspace_runtime_settings.py",\n    "ui_state.py",\n'
SERVER_AUTO_OLD = '    auto_backup = bool(permissions.get("auto_backup", True))\n'
SERVER_AUTO_NEW = '    # Защищённый backup — обязательная серверная защита.\n    # Поле сохраняется в policy для обратной совместимости старых вызовов,\n    # но отключить backup через permissions больше нельзя.\n    auto_backup = True\n'
BACKUP_FUNC_OLD = 'def _create_backup_session(\n    app_dir: Path, root: Path, run_id: str, task: str, policy: dict\n) -> dict | None:\n    if not policy["auto_backup"]:\n        return None\n\n    backup_dir = BACKUP_BASE / run_id\n    backup_dir.mkdir(parents=True, exist_ok=False)\n    core_dir = backup_dir / "core"\n    copied_core = []\n\n    for relative_text in CORE_BACKUP_RELATIVE_PATHS:\n        source = app_dir / Path(relative_text)\n        if not source.is_file():\n            continue\n        destination = core_dir / Path(relative_text)\n        destination.parent.mkdir(parents=True, exist_ok=True)\n        shutil.copy2(source, destination)\n        copied_core.append(relative_text)\n\n    manifest = {\n        "run_id": run_id,\n        "created_at": time.time(),\n        "workspace": str(root),\n        "task_preview": task[:500],\n        "policy": _policy_summary(policy),\n        "core_files": copied_core,\n        "changed_files": [],\n        "new_files": [],\n        "deleted_files": [],\n    }\n    session = {\n        "backup_dir": backup_dir,\n        "backed_up_paths": set(),\n        "delete_backed_up_paths": set(),\n        "manifest": manifest,\n    }\n    _write_backup_manifest(session)\n    return session\n'
BACKUP_FUNC_NEW = 'def _create_backup_session(\n    app_dir: Path,\n    root: Path,\n    run_id: str,\n    task: str,\n    policy: dict,\n    *,\n    backup_base: Path,\n    workspace_id: str,\n    chat_id: str | None,\n) -> dict | None:\n    if not policy["auto_backup"]:\n        return None\n\n    backup_dir = backup_base / run_id\n    backup_dir.mkdir(parents=True, exist_ok=False)\n    core_dir = backup_dir / "core"\n    copied_core = []\n\n    for relative_text in CORE_BACKUP_RELATIVE_PATHS:\n        source = app_dir / Path(relative_text)\n        if not source.is_file():\n            continue\n        destination = core_dir / Path(relative_text)\n        destination.parent.mkdir(parents=True, exist_ok=True)\n        shutil.copy2(source, destination)\n        copied_core.append(relative_text)\n\n    # `.ultra` — маленькое переносимое состояние Workspace:\n    # workspace metadata, PROJECT CONTEXT, чаты и RAW HISTORY.\n    context_snapshot = None\n    context_source = (root / ".ultra").resolve()\n    if context_source.is_dir():\n        context_destination = backup_dir / "context" / ".ultra"\n        context_destination.parent.mkdir(parents=True, exist_ok=True)\n        shutil.copytree(context_source, context_destination)\n        context_snapshot = "context/.ultra"\n\n    manifest = {\n        "run_id": run_id,\n        "created_at": time.time(),\n        "workspace_id": workspace_id,\n        "workspace": str(root),\n        "chat_id": chat_id,\n        "task_preview": task[:500],\n        "policy": _policy_summary(policy),\n        "context_snapshot": context_snapshot,\n        "core_files": copied_core,\n        "changed_files": [],\n        "new_files": [],\n        "deleted_files": [],\n    }\n    session = {\n        "backup_dir": backup_dir,\n        "backed_up_paths": set(),\n        "delete_backed_up_paths": set(),\n        "manifest": manifest,\n    }\n    _write_backup_manifest(session)\n    return session\n'
RUN_INIT_OLD = '    run_id = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]\n    start_time = time.time()\n    api_request_count = 0\n    tool_call_count = 0\n    policy = _normalize_permissions(permissions)\n\n    def _emit(event_type: str, payload: dict):\n'
RUN_INIT_NEW = '    run_id = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]\n    start_time = time.time()\n    api_request_count = 0\n    tool_call_count = 0\n    policy = _normalize_permissions(permissions)\n\n    # Пока workspace_id ещё не загружен, ошибки пишутся в системный fallback.\n    # После загрузки Workspace путь переключается на его собственный namespace.\n    runtime_log_path = (\n        Path(os.getenv("LOCALAPPDATA") or Path.home())\n        / "GigaChatUltra"\n        / "system_logs"\n        / f"{run_id}.jsonl"\n    ).resolve()\n    workspace_backup_base = BACKUP_BASE\n\n    def _emit(event_type: str, payload: dict):\n'
EMIT_OLD = '        log_dir = Path("logs") / "runs"\n        log_dir.mkdir(parents=True, exist_ok=True)\n        log_path = log_dir / f"{run_id}.jsonl"\n        try:\n            with log_path.open("a", encoding="utf-8") as f:\n'
EMIT_NEW = '        runtime_log_path.parent.mkdir(parents=True, exist_ok=True)\n        try:\n            with runtime_log_path.open("a", encoding="utf-8") as f:\n'
RUNTIME_ANCHOR = '    active_chat_messages = []\n'
RUNTIME_INSERT = '    try:\n        runtime_paths = ensure_workspace_runtime_dirs(\n            workspace_info["workspace_id"]\n        )\n        workspace_backup_base = Path(\n            runtime_paths["backup_dir"]\n        ).resolve()\n        runtime_log_dir = Path(runtime_paths["log_dir"]).resolve()\n\n        # Бэкапы/логи не должны лежать внутри Workspace: иначе снимок может\n        # начать резервировать сам себя и потеряется смысл внешней защиты.\n        for label, path in (\n            ("backup", workspace_backup_base),\n            ("log", runtime_log_dir),\n        ):\n            if path == root or root in path.parents:\n                raise ValueError(\n                    f"{label} directory не должна находиться внутри Workspace."\n                )\n\n        runtime_log_path = runtime_log_dir / f"{run_id}.jsonl"\n    except Exception as exc:\n        _emit(\n            "run_failed",\n            {\n                "reason": "workspace_runtime_settings_error",\n                "api_requests": api_request_count,\n                "tool_calls": tool_call_count,\n                "duration": time.time() - start_time,\n                "error": str(exc),\n                "trace_path": str(runtime_log_path),\n            },\n        )\n        raise RuntimeError(\n            "Не удалось подготовить локальные пути backup/log для Workspace."\n        ) from exc\n\n    active_chat_messages = []\n'
BACKUP_CALL_OLD = '    # Бэкап выполняется синхронно ДО обращения к модели.\n    backup_session = None\n    if policy["auto_backup"]:\n        planned_backup_path = BACKUP_BASE / run_id\n        _emit("backup_started", {"backup_path": str(planned_backup_path)})\n        try:\n            backup_session = _create_backup_session(\n                app_dir, root, run_id, task, policy\n            )\n'
BACKUP_CALL_NEW = '    # Бэкап выполняется синхронно ДО обращения к модели.\n    backup_session = None\n    if policy["auto_backup"]:\n        planned_backup_path = workspace_backup_base / run_id\n        _emit("backup_started", {"backup_path": str(planned_backup_path)})\n        try:\n            backup_session = _create_backup_session(\n                app_dir,\n                root,\n                run_id,\n                task,\n                policy,\n                backup_base=workspace_backup_base,\n                workspace_id=workspace_info["workspace_id"],\n                chat_id=chat_id,\n            )\n'
UI_IMPORT_OLD = 'from ui_state import load_ui_state, save_ui_state\n'
UI_IMPORT_NEW = 'from ui_state import load_ui_state, save_ui_state\nfrom workspace_runtime_settings import (\n    load_workspace_runtime_settings,\n    save_workspace_runtime_settings,\n)\n'
UI_SETTINGS_METHOD = '    def _rename_workspace_ui(self, workspace: Path) -> None:\n        if self.running:\n            return\n\n        try:\n            workspace = workspace.resolve()\n            info = ensure_workspace_storage(workspace)\n            runtime = load_workspace_runtime_settings(\n                info["workspace_id"]\n            )\n        except Exception as exc:\n            messagebox.showerror(\n                APP_TITLE,\n                f"Не удалось открыть настройки Workspace.\\n\\n"\n                f"{type(exc).__name__}: {exc}",\n            )\n            return\n\n        window = tk.Toplevel(self)\n        window.title(\n            f"Настройки Workspace — {info[\'display_name\']}"\n        )\n        window.geometry("820x540")\n        window.minsize(720, 500)\n        window.transient(self)\n        window.grab_set()\n\n        body = ttk.Frame(window, padding=16)\n        body.pack(fill="both", expand=True)\n        body.columnconfigure(1, weight=1)\n\n        ttk.Label(\n            body,\n            text="НАСТРОЙКИ WORKSPACE",\n            font=("Segoe UI", 11, "bold"),\n        ).grid(\n            row=0,\n            column=0,\n            columnspan=4,\n            sticky="w",\n            pady=(0, 14),\n        )\n\n        ttk.Label(body, text="Название Workspace:").grid(\n            row=1,\n            column=0,\n            sticky="w",\n            pady=4,\n        )\n        name_var = tk.StringVar(value=info["display_name"])\n        name_entry = ttk.Entry(\n            body,\n            textvariable=name_var,\n            width=52,\n        )\n        name_entry.grid(\n            row=1,\n            column=1,\n            columnspan=3,\n            sticky="ew",\n            padx=(10, 0),\n            pady=4,\n        )\n        bind_edit_shortcuts(name_entry)\n\n        ttk.Separator(body).grid(\n            row=2,\n            column=0,\n            columnspan=4,\n            sticky="ew",\n            pady=(12, 12),\n        )\n\n        ttk.Label(\n            body,\n            text="ХРАНИЛИЩЕ",\n            font=("Segoe UI", 10, "bold"),\n        ).grid(\n            row=3,\n            column=0,\n            columnspan=4,\n            sticky="w",\n            pady=(0, 8),\n        )\n\n        backup_var = tk.StringVar(value=runtime["backup_dir"])\n        log_var = tk.StringVar(value=runtime["log_dir"])\n\n        ttk.Label(body, text="Защищённые бэкапы:").grid(\n            row=4,\n            column=0,\n            sticky="w",\n            pady=4,\n        )\n        backup_entry = ttk.Entry(\n            body,\n            textvariable=backup_var,\n        )\n        backup_entry.grid(\n            row=4,\n            column=1,\n            sticky="ew",\n            padx=(10, 6),\n            pady=4,\n        )\n        bind_edit_shortcuts(backup_entry)\n\n        def choose_backup() -> None:\n            current = Path(backup_var.get()).expanduser()\n            initial = current if current.is_dir() else Path.home()\n            selected = filedialog.askdirectory(\n                parent=window,\n                initialdir=str(initial),\n                title="Папка защищённых бэкапов Workspace",\n            )\n            if selected:\n                backup_var.set(selected)\n\n        ttk.Button(\n            body,\n            text="...",\n            width=3,\n            command=choose_backup,\n        ).grid(row=4, column=2, sticky="w", pady=4)\n        ttk.Button(\n            body,\n            text="По умолчанию",\n            command=lambda: backup_var.set(\n                runtime["default_backup_dir"]\n            ),\n        ).grid(\n            row=4,\n            column=3,\n            sticky="w",\n            padx=(6, 0),\n            pady=4,\n        )\n\n        ttk.Label(body, text="Логи RUN:").grid(\n            row=5,\n            column=0,\n            sticky="w",\n            pady=4,\n        )\n        log_entry = ttk.Entry(\n            body,\n            textvariable=log_var,\n        )\n        log_entry.grid(\n            row=5,\n            column=1,\n            sticky="ew",\n            padx=(10, 6),\n            pady=4,\n        )\n        bind_edit_shortcuts(log_entry)\n\n        def choose_logs() -> None:\n            current = Path(log_var.get()).expanduser()\n            initial = current if current.is_dir() else Path.home()\n            selected = filedialog.askdirectory(\n                parent=window,\n                initialdir=str(initial),\n                title="Папка логов RUN Workspace",\n            )\n            if selected:\n                log_var.set(selected)\n\n        ttk.Button(\n            body,\n            text="...",\n            width=3,\n            command=choose_logs,\n        ).grid(row=5, column=2, sticky="w", pady=4)\n        ttk.Button(\n            body,\n            text="По умолчанию",\n            command=lambda: log_var.set(\n                runtime["default_log_dir"]\n            ),\n        ).grid(\n            row=5,\n            column=3,\n            sticky="w",\n            padx=(6, 0),\n            pady=4,\n        )\n\n        ttk.Separator(body).grid(\n            row=6,\n            column=0,\n            columnspan=4,\n            sticky="ew",\n            pady=(14, 12),\n        )\n\n        ttk.Label(\n            body,\n            text="О БЭКАПАХ",\n            font=("Segoe UI", 10, "bold"),\n        ).grid(\n            row=7,\n            column=0,\n            columnspan=4,\n            sticky="w",\n            pady=(0, 6),\n        )\n\n        explanation = (\n            "Перед каждым RUN Ultra создаёт защищённый снимок этого Workspace. "\n            "В снимок целиком входит переносимое состояние .ultra: "\n            "PROJECT CONTEXT, чаты и RAW HISTORY. Исходные версии обычных "\n            "файлов проекта сохраняются непосредственно перед их изменением "\n            "или удалением.\\n\\n"\n            "Бэкап принадлежит Workspace, а chat_id записывается в manifest "\n            "только как источник конкретного RUN. По умолчанию backup и "\n            "RUN-логи лежат локально вне проекта. Здесь можно выбрать другие "\n            "локальные каталоги именно для этого Workspace. Путь внутри самого "\n            "Workspace в текущей версии запрещён."\n        )\n        ttk.Label(\n            body,\n            text=explanation,\n            wraplength=750,\n            justify="left",\n        ).grid(\n            row=8,\n            column=0,\n            columnspan=4,\n            sticky="nw",\n        )\n\n        buttons = ttk.Frame(body)\n        buttons.grid(\n            row=9,\n            column=0,\n            columnspan=4,\n            sticky="ew",\n            pady=(20, 0),\n        )\n\n        def save_settings() -> None:\n            try:\n                clean_name = name_var.get().strip()\n                if not clean_name:\n                    raise ValueError(\n                        "Название Workspace не может быть пустым."\n                    )\n                if len(clean_name) > 200:\n                    raise ValueError(\n                        "Название Workspace слишком длинное."\n                    )\n\n                backup_text = backup_var.get().strip().strip(\'"\')\n                log_text = log_var.get().strip().strip(\'"\')\n                if not backup_text or not log_text:\n                    raise ValueError(\n                        "Пути backup и log не могут быть пустыми."\n                    )\n\n                backup_path = Path(backup_text).expanduser()\n                log_path = Path(log_text).expanduser()\n\n                for label, path in (\n                    ("Бэкапы", backup_path),\n                    ("Логи", log_path),\n                ):\n                    if not path.is_absolute():\n                        raise ValueError(\n                            f"{label}: путь должен быть абсолютным."\n                        )\n                    resolved = path.resolve()\n                    if (\n                        resolved == workspace\n                        or workspace in resolved.parents\n                    ):\n                        raise ValueError(\n                            f"{label}: каталог должен находиться "\n                            "вне Workspace."\n                        )\n\n                rename_workspace(workspace, clean_name)\n                save_workspace_runtime_settings(\n                    info["workspace_id"],\n                    backup_dir=backup_path,\n                    log_dir=log_path,\n                )\n\n                self._render_workspace_sidebar()\n                self._save_ui_state(silent=True)\n                window.destroy()\n            except Exception as exc:\n                messagebox.showerror(\n                    APP_TITLE,\n                    f"Не удалось сохранить настройки Workspace.\\n\\n"\n                    f"{type(exc).__name__}: {exc}",\n                    parent=window,\n                )\n\n        ttk.Button(\n            buttons,\n            text="Сохранить",\n            command=save_settings,\n        ).pack(side="left")\n        ttk.Button(\n            buttons,\n            text="Отмена",\n            command=window.destroy,\n        ).pack(side="right")\n\n        name_entry.focus_set()\n        name_entry.selection_range(0, "end")\n\n'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly 1 match, found {count}. "
            "No files were changed."
        )
    return text.replace(old, new, 1)


def patch_server(original: str) -> str:
    if "workspace_runtime_settings import ensure_workspace_runtime_dirs" in original:
        raise RuntimeError("Workspace backup settings already appear installed.")

    text = original
    text = replace_once(
        text, SERVER_IMPORT_OLD, SERVER_IMPORT_NEW, "SERVER IMPORT"
    )
    text = replace_once(
        text, SERVER_CORE_OLD, SERVER_CORE_NEW, "SERVER CORE LIST"
    )
    text = replace_once(
        text, SERVER_AUTO_OLD, SERVER_AUTO_NEW, "SERVER MANDATORY BACKUP"
    )
    text = replace_once(
        text, BACKUP_FUNC_OLD, BACKUP_FUNC_NEW, "SERVER BACKUP FUNCTION"
    )
    text = replace_once(
        text, RUN_INIT_OLD, RUN_INIT_NEW, "SERVER RUN INIT"
    )
    text = replace_once(
        text, EMIT_OLD, EMIT_NEW, "SERVER LOG WRITER"
    )
    text = replace_once(
        text, RUNTIME_ANCHOR, RUNTIME_INSERT, "SERVER RUNTIME PATHS"
    )
    text = replace_once(
        text, BACKUP_CALL_OLD, BACKUP_CALL_NEW, "SERVER BACKUP CALL"
    )

    # Only modify trace_path references inside run_agent_task.
    marker = "async def run_agent_task("
    pos = text.find(marker)
    if pos < 0:
        raise RuntimeError("run_agent_task not found.")
    prefix = text[:pos]
    run_part = text[pos:]
    old_trace = 'f"logs/runs/{run_id}.jsonl"'
    if old_trace not in run_part:
        raise RuntimeError("No legacy trace_path references found in run_agent_task.")
    run_part = run_part.replace(old_trace, "str(runtime_log_path)")
    return prefix + run_part


def patch_ui(original: str) -> str:
    if "load_workspace_runtime_settings" in original:
        raise RuntimeError("Workspace settings UI already appears installed.")

    text = replace_once(
        original, UI_IMPORT_OLD, UI_IMPORT_NEW, "UI IMPORT"
    )

    pattern = re.compile(
        r"    def _rename_workspace_ui\(self, workspace: Path\) -> None:\n"
        r".*?"
        r"(?=    def _rename_chat_ui\(self, workspace: Path, chat_id: str\) -> None:\n)",
        re.S,
    )
    text, count = pattern.subn(UI_SETTINGS_METHOD, text, count=1)
    if count != 1:
        raise RuntimeError(
            f"UI WORKSPACE SETTINGS: expected 1 function block, found {count}."
        )
    return text


def main() -> int:
    for path in (SERVER, UI, RUNTIME):
        if not path.is_file():
            raise FileNotFoundError(f"Missing: {path}")

    server_original = SERVER.read_text(encoding="utf-8-sig")
    ui_original = UI.read_text(encoding="utf-8-sig")

    server_markers = (
        "chat_context_loaded",
        "chat_id: str | None = None",
        "def _create_backup_session(",
    )
    ui_markers = (
        "НАСТРОЙКИ ИНСТРУМЕНТОВ LLM",
        "_restore_window_and_layout",
        'text="VERIFY"',
        "+ Создать Workspace",
    )

    missing_server = [m for m in server_markers if m not in server_original]
    missing_ui = [m for m in ui_markers if m not in ui_original]
    if missing_server or missing_ui:
        raise RuntimeError(
            "Current STEP 3 baseline not found. "
            f"server missing={missing_server}; ui missing={missing_ui}"
        )

    if SERVER_BACKUP.exists() or UI_BACKUP.exists():
        raise FileExistsError(
            "Workspace-backup-settings backup already exists. "
            "Refusing to overwrite an earlier backup."
        )

    server_patched = patch_server(server_original)
    ui_patched = patch_ui(ui_original)

    temp_server = ROOT / ".server.workspace_backup_settings.candidate.py"
    temp_ui = ROOT / ".ultra_ui.workspace_backup_settings.candidate.py"
    temp_server.write_text(server_patched, encoding="utf-8", newline="\n")
    temp_ui.write_text(ui_patched, encoding="utf-8", newline="\n")

    try:
        py_compile.compile(str(RUNTIME), doraise=True)
        py_compile.compile(str(temp_server), doraise=True)
        py_compile.compile(str(temp_ui), doraise=True)
    finally:
        for temp in (temp_server, temp_ui):
            try:
                temp.unlink()
            except FileNotFoundError:
                pass

    shutil.copy2(SERVER, SERVER_BACKUP)
    shutil.copy2(UI, UI_BACKUP)

    SERVER.write_text(server_patched, encoding="utf-8", newline="\n")
    UI.write_text(ui_patched, encoding="utf-8", newline="\n")

    py_compile.compile(str(RUNTIME), doraise=True)
    py_compile.compile(str(SERVER), doraise=True)
    py_compile.compile(str(UI), doraise=True)

    print("OK: Workspace backup/log settings installed.")
    print("Backups:")
    print(f"  {SERVER_BACKUP.name}")
    print(f"  {UI_BACKUP.name}")
    print("Implemented:")
    print("  - pencil now opens a full Workspace settings dialog")
    print("  - Workspace rename remains inside that dialog")
    print("  - per-workspace custom backup path")
    print("  - per-workspace custom RUN log path")
    print("  - defaults are local and keyed by immutable workspace_id")
    print("  - backup is mandatory for normal/server RUNs")
    print("  - every RUN snapshots .ultra before model execution")
    print("  - changed/deleted project files remain lazy pre-mutation backups")
    print("  - manifest stores workspace_id and chat_id")
    print("  - runtime JSONL logs move out of the repository")
    print("")
    print("Restart the application before testing.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
