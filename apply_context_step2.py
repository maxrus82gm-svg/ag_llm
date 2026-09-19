from __future__ import annotations

import py_compile
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "server.py"
UI = ROOT / "ultra_ui.py"
CONTEXT = ROOT / "context_storage.py"
CANDIDATE_CONTEXT = ROOT / "context_storage_step2.py"

UI_BACKUP = ROOT / "ultra_ui.py.before_context_step2"
CONTEXT_BACKUP = ROOT / "context_storage.py.before_context_step2"


REPLACEMENTS = [
    (
        "TK IMPORT",
        '''from tkinter import colorchooser, filedialog, messagebox, scrolledtext, ttk''',
        '''from tkinter import (
    colorchooser,
    filedialog,
    messagebox,
    scrolledtext,
    simpledialog,
    ttk,
)''',
    ),
    (
        "CONTEXT IMPORT",
        '''from server import get_backup_base_path, run_agent_task''',
        '''from server import get_backup_base_path, run_agent_task
from context_storage import (
    append_raw_message,
    create_chat,
    ensure_chat,
    ensure_workspace_storage,
    list_chats,
    load_chat_messages,
    load_project_context,
    rename_chat,
    rename_workspace,
    save_project_context,
)''',
    ),
    (
        "WINDOW SIZE",
        '''        self.geometry("1220x860")
        self.minsize(950, 720)''',
        '''        self.geometry("1500x860")
        self.minsize(1180, 720)''',
    ),
    (
        "STEP2 STATE",
        '''        self._security_widgets: list[tk.Widget] = []
        self._color_swatches: dict[str, tk.Widget] = {}
        self._run_started_once = False

        self._build_ui()
        self._apply_theme()
''',
        '''        self._security_widgets: list[tk.Widget] = []
        self._workspace_widgets: list[tk.Widget] = []
        self._color_swatches: dict[str, tk.Widget] = {}
        self._run_started_once = False

        self.current_workspace_id: str | None = None
        self.current_chat_id: str | None = None
        self._loaded_workspace_root: str | None = None
        self._context_storage_mtime = None

        self._build_ui()
        self._apply_theme()
        self._record_context_storage_mtime()
        self._load_workspace_browser(silent=True)
''',
    ),
    (
        "ROOT COLUMNS",
        '''        root.columnconfigure(0, weight=0, minsize=360)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)
''',
        '''        root.columnconfigure(0, weight=0, minsize=360)
        root.columnconfigure(1, weight=1, minsize=620)
        root.columnconfigure(2, weight=0, minsize=285)
        root.rowconfigure(0, weight=1)
''',
    ),
    (
        "RIGHT PANEL CALL",
        '''        right_frame = ttk.Frame(root)
        right_frame.grid(row=0, column=1, sticky="nsew")

        # Workspace — намеренно компактный: оставляем справа запас под будущие controls.
''',
        '''        right_frame = ttk.Frame(root)
        right_frame.grid(row=0, column=1, sticky="nsew")

        # STEP 2: отдельная правая панель Workspace/Chat.
        # Верхняя системная панель в центре остаётся без перестройки.
        self._build_workspace_browser(root)

        # Workspace — намеренно компактный: оставляем справа запас под будущие controls.
''',
    ),
    (
        "WORKSPACE ENTRY BIND",
        '''        bind_edit_shortcuts(self.workspace_entry)
        self.workspace_button = ttk.Button(
''',
        '''        bind_edit_shortcuts(self.workspace_entry)
        self.workspace_entry.bind(
            "<Return>",
            lambda _event: self._load_workspace_browser(silent=False),
        )
        self.workspace_button = ttk.Button(
''',
    ),
    (
        "SEND BUTTON SIDE",
        '''        ttk.Label(buttons, text="Ctrl+Enter — отправить").pack(side="left")
        self.send_button = ttk.Button(
            buttons,
            text="Отправить",
            command=self._send,
        )
        self.send_button.pack(side="right")
''',
        '''        self.send_button = ttk.Button(
            buttons,
            text="Отправить",
            command=self._send,
        )
        self.send_button.pack(side="left")
        ttk.Label(buttons, text="Ctrl+Enter — отправить").pack(
            side="left", padx=(10, 0)
        )
''',
    ),
    (
        "CHOOSE WORKSPACE REFRESH",
        '''        if selected:
            self.workspace_var.set(selected)
            workspace = Path(selected)
            if (workspace / "Документация").is_dir():
                self.write_scope_var.set("Документация")
''',
        '''        if selected:
            self.workspace_var.set(selected)
            workspace = Path(selected)
            if (workspace / "Документация").is_dir():
                self.write_scope_var.set("Документация")
            self._load_workspace_browser(silent=False)
''',
    ),
    (
        "SEND PERSIST USER",
        '''        permissions = {
            "allow_read": self.allow_read_var.get(),
            "allow_write": self.allow_write_var.get(),
            "allow_delete": self.allow_delete_var.get(),
            "allow_verify": self.allow_verify_var.get(),
            "read_scope": read_scope,
            "write_scope": write_scope,
            "delete_scope": delete_scope,
            "tool_limit": tool_limit,
            "auto_backup": self.auto_backup_var.get(),
        }

        self._append_chat("ТЫ", task, "user")
''',
        '''        permissions = {
            "allow_read": self.allow_read_var.get(),
            "allow_write": self.allow_write_var.get(),
            "allow_delete": self.allow_delete_var.get(),
            "allow_verify": self.allow_verify_var.get(),
            "read_scope": read_scope,
            "write_scope": write_scope,
            "delete_scope": delete_scope,
            "tool_limit": tool_limit,
            "auto_backup": self.auto_backup_var.get(),
        }

        try:
            self._ensure_workspace_ui_current(workspace)
            if not self.current_chat_id:
                raise RuntimeError("Не выбран активный чат.")
            append_raw_message(
                workspace,
                self.current_chat_id,
                "user",
                task,
            )
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                "Не удалось сохранить RAW MESSAGE до отправки.\\n\\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        self._append_chat("ТЫ", task, "user")
''',
    ),
    (
        "THREAD CHAT ID",
        '''        thread = threading.Thread(
            target=self._worker,
            args=(task, str(workspace), permissions),
            daemon=True,
        )
''',
        '''        thread = threading.Thread(
            target=self._worker,
            args=(task, str(workspace), permissions, self.current_chat_id),
            daemon=True,
        )
''',
    ),
    (
        "DISABLE WORKSPACE WIDGETS",
        '''        for widget in self._security_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass

    def _worker(self, task: str, workspace: str, permissions: dict) -> None:
''',
        '''        for widget in self._security_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass
        for widget in self._workspace_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass

    def _worker(
        self,
        task: str,
        workspace: str,
        permissions: dict,
        chat_id: str,
    ) -> None:
''',
    ),
    (
        "SAVE ASSISTANT RAW",
        '''            result = asyncio.run(
                run_agent_task(
                    task,
                    workspace,
                    on_event=on_event,
                    permissions=permissions,
                )
            )
            self.events.put(("success", result))
''',
        '''            result = asyncio.run(
                run_agent_task(
                    task,
                    workspace,
                    on_event=on_event,
                    permissions=permissions,
                )
            )
            append_raw_message(
                workspace,
                chat_id,
                "assistant",
                result,
            )
            self.events.put(("success", result))
''',
    ),
]

METHOD_INSERT_ANCHOR = '''    def _choose_workspace(self) -> None:
'''

METHODS = r'''    def _record_context_storage_mtime(self) -> None:
        try:
            self._context_storage_mtime = Path("context_storage.py").stat().st_mtime
        except FileNotFoundError:
            self._context_storage_mtime = None

    def _build_workspace_browser(self, root: ttk.Frame) -> None:
        panel = ttk.LabelFrame(
            root,
            text="WORKSPACES / ЧАТЫ",
            padding=8,
        )
        panel.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        panel.configure(width=285)
        panel.grid_propagate(False)

        tree_host = ttk.Frame(panel)
        tree_host.pack(fill="both", expand=True)

        self.workspace_tree = ttk.Treeview(
            tree_host,
            show="tree",
            selectmode="browse",
        )
        self.workspace_tree.column("#0", width=245, stretch=True)
        workspace_scroll = ttk.Scrollbar(
            tree_host,
            orient="vertical",
            command=self.workspace_tree.yview,
        )
        self.workspace_tree.configure(yscrollcommand=workspace_scroll.set)

        self.workspace_tree.pack(side="left", fill="both", expand=True)
        workspace_scroll.pack(side="right", fill="y")

        self.workspace_tree.bind(
            "<<TreeviewSelect>>",
            self._on_workspace_tree_select,
        )

        buttons = ttk.Frame(panel)
        buttons.pack(fill="x", pady=(8, 0))

        self.new_chat_button = ttk.Button(
            buttons,
            text="+ Чат",
            command=self._create_chat_ui,
        )
        self.new_chat_button.pack(side="left")

        self.rename_tree_button = ttk.Button(
            buttons,
            text="Переименовать",
            command=self._rename_selected_tree_item,
        )
        self.rename_tree_button.pack(side="left", padx=(6, 0))

        self.project_context_button = ttk.Button(
            panel,
            text="Контекст проекта",
            command=self._open_project_context_editor,
        )
        self.project_context_button.pack(fill="x", pady=(8, 0))

        self._workspace_widgets.extend(
            [
                self.workspace_tree,
                self.new_chat_button,
                self.rename_tree_button,
                self.project_context_button,
            ]
        )

    def _workspace_path_from_ui(self) -> Path:
        text = self.workspace_var.get().strip().strip('"')
        workspace = Path(text)
        if not workspace.is_absolute() or not workspace.is_dir():
            raise ValueError(
                "Workspace должен быть существующей абсолютной папкой."
            )
        return workspace.resolve()

    def _load_workspace_browser(
        self,
        *,
        silent: bool = False,
        preferred_chat_id: str | None = None,
    ) -> None:
        try:
            workspace = self._workspace_path_from_ui()
            info = ensure_workspace_storage(workspace)
            chats = list_chats(workspace)
            if not chats:
                chats = [create_chat(workspace)]

            valid_ids = {item["chat_id"] for item in chats}
            candidate = preferred_chat_id or self.current_chat_id
            if candidate not in valid_ids:
                candidate = chats[-1]["chat_id"]

            self.current_workspace_id = info["workspace_id"]
            self.current_chat_id = candidate
            self._loaded_workspace_root = str(workspace)

            self.workspace_tree.delete(*self.workspace_tree.get_children())
            self.workspace_tree.insert(
                "",
                "end",
                iid="workspace",
                text=info["display_name"],
                open=True,
            )
            for chat in chats:
                iid = f"chat:{chat['chat_id']}"
                self.workspace_tree.insert(
                    "workspace",
                    "end",
                    iid=iid,
                    text=chat["title"],
                )

            selected_iid = f"chat:{self.current_chat_id}"
            if self.workspace_tree.exists(selected_iid):
                self.workspace_tree.selection_set(selected_iid)
                self.workspace_tree.focus(selected_iid)
                self.workspace_tree.see(selected_iid)

            self._render_current_chat()
        except Exception as exc:
            if not silent:
                messagebox.showerror(
                    APP_TITLE,
                    f"Не удалось загрузить Workspace/Chats.\\n\\n"
                    f"{type(exc).__name__}: {exc}",
                )

    def _ensure_workspace_ui_current(self, workspace: Path) -> None:
        resolved = str(workspace.resolve())
        if (
            self._loaded_workspace_root != resolved
            or not self.current_chat_id
        ):
            self._load_workspace_browser(silent=False)
        if self._loaded_workspace_root != resolved or not self.current_chat_id:
            raise RuntimeError("Workspace/Chat не удалось активировать.")

    def _render_current_chat(self) -> None:
        if not self.current_chat_id:
            return

        workspace = self._workspace_path_from_ui()
        messages = load_chat_messages(workspace, self.current_chat_id)

        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")

        if not messages:
            self._append_chat(
                "СИСТЕМА",
                "Новый чат. RAW HISTORY пока пуста.",
                "system",
            )
            return

        for message in messages:
            role = message.get("role")
            text = message.get("original_text") or ""
            if role == "user":
                self._append_chat("ТЫ", text, "user")
            elif role == "assistant":
                self._append_chat("ULTRA", text, "assistant")
            else:
                self._append_chat(
                    str(role or "SYSTEM").upper(),
                    text,
                    "system",
                )

    def _on_workspace_tree_select(self, _event=None) -> None:
        if self.running:
            return

        selected = self.workspace_tree.selection()
        if not selected:
            return

        iid = selected[0]
        if not iid.startswith("chat:"):
            return

        chat_id = iid.split(":", 1)[1]
        if chat_id == self.current_chat_id:
            return

        self.current_chat_id = chat_id
        try:
            self._render_current_chat()
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось открыть чат.\\n\\n{type(exc).__name__}: {exc}",
            )

    def _create_chat_ui(self) -> None:
        if self.running:
            return
        try:
            workspace = self._workspace_path_from_ui()
            chat = create_chat(workspace)
            self._load_workspace_browser(
                silent=False,
                preferred_chat_id=chat["chat_id"],
            )
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось создать чат.\\n\\n{type(exc).__name__}: {exc}",
            )

    def _rename_selected_tree_item(self) -> None:
        if self.running:
            return

        selected = self.workspace_tree.selection()
        if not selected:
            return

        iid = selected[0]
        try:
            workspace = self._workspace_path_from_ui()

            if iid == "workspace":
                info = ensure_workspace_storage(workspace)
                new_name = simpledialog.askstring(
                    "Переименовать Workspace",
                    "Новое название Workspace:",
                    initialvalue=info["display_name"],
                    parent=self,
                )
                if new_name is None:
                    return
                rename_workspace(workspace, new_name)
                self._load_workspace_browser(
                    silent=False,
                    preferred_chat_id=self.current_chat_id,
                )
                return

            if iid.startswith("chat:"):
                chat_id = iid.split(":", 1)[1]
                chats = {
                    item["chat_id"]: item
                    for item in list_chats(workspace)
                }
                current = chats.get(chat_id)
                if current is None:
                    raise FileNotFoundError(f"Чат не найден: {chat_id}")

                new_name = simpledialog.askstring(
                    "Переименовать чат",
                    "Новое название чата:",
                    initialvalue=current["title"],
                    parent=self,
                )
                if new_name is None:
                    return
                rename_chat(workspace, chat_id, new_name)
                self._load_workspace_browser(
                    silent=False,
                    preferred_chat_id=chat_id,
                )
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось переименовать.\\n\\n{type(exc).__name__}: {exc}",
            )

    def _open_project_context_editor(self) -> None:
        try:
            workspace = self._workspace_path_from_ui()
            text = load_project_context(workspace)
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось открыть PROJECT CONTEXT.\\n\\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        window = tk.Toplevel(self)
        window.title("PROJECT CONTEXT")
        window.geometry("900x650")
        window.transient(self)

        editor = scrolledtext.ScrolledText(
            window,
            wrap="word",
            undo=True,
            font=("Segoe UI", 10),
        )
        editor.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        editor.insert("1.0", text)
        bind_edit_shortcuts(editor)

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=10, pady=(0, 10))

        def save_context() -> None:
            try:
                result = save_project_context(
                    workspace,
                    editor.get("1.0", "end-1c"),
                )
                if result.get("changed"):
                    messagebox.showinfo(
                        APP_TITLE,
                        "PROJECT CONTEXT сохранён. Следующий RUN прочитает "
                        "новую версию.",
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
                    f"Не удалось сохранить PROJECT CONTEXT.\\n\\n"
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

'''

POLL_CODE_ANCHOR = '''        try:
            current = Path("ultra_ui.py").stat().st_mtime
            if self._ui_mtime is not None and current != self._ui_mtime:
                changed.append("ultra_ui.py")
        except FileNotFoundError:
            pass

        if changed and not self._code_changed:
'''

POLL_CODE_REPLACEMENT = '''        try:
            current = Path("ultra_ui.py").stat().st_mtime
            if self._ui_mtime is not None and current != self._ui_mtime:
                changed.append("ultra_ui.py")
        except FileNotFoundError:
            pass
        try:
            current = Path("context_storage.py").stat().st_mtime
            if (
                self._context_storage_mtime is not None
                and current != self._context_storage_mtime
            ):
                changed.append("context_storage.py")
        except FileNotFoundError:
            pass

        if changed and not self._code_changed:
'''

FORMAT_EVENT_ANCHOR = '''        if event_type == "backup_started":
            return f"[{time_str}] BACKUP START | {event.get('backup_path')}"
'''

FORMAT_EVENT_REPLACEMENT = '''        if event_type == "workspace_context_loaded":
            return (
                f"[{time_str}] WORKSPACE CONTEXT | "
                f"{event.get('workspace_id')} | "
                f"chars={event.get('project_context_chars')}"
            )

        if event_type == "backup_started":
            return f"[{time_str}] BACKUP START | {event.get('backup_path')}"
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly 1 match, found {count}. "
            "No files were changed."
        )
    return text.replace(old, new, 1)


def main() -> int:
    if not SERVER.is_file():
        raise FileNotFoundError(f"Missing {SERVER}")
    if not UI.is_file():
        raise FileNotFoundError(f"Missing {UI}")
    if not CONTEXT.is_file():
        raise FileNotFoundError(
            "Missing context_storage.py. Install STEP 1 first."
        )
    if not CANDIDATE_CONTEXT.is_file():
        raise FileNotFoundError(
            "Missing context_storage_step2.py next to this installer."
        )

    server_text = SERVER.read_text(encoding="utf-8-sig")
    step1_marker = (
        "from context_storage import "
        "ensure_workspace_storage, load_project_context"
    )
    if step1_marker not in server_text:
        raise RuntimeError(
            "STEP 1 marker not found in server.py. "
            "STEP 2 expects the previously installed Context Storage STEP 1."
        )

    ui_original = UI.read_text(encoding="utf-8-sig")
    context_original = CONTEXT.read_text(encoding="utf-8-sig")
    new_context = CANDIDATE_CONTEXT.read_text(encoding="utf-8-sig")

    if "def _build_workspace_browser(self, root: ttk.Frame)" in ui_original:
        print("STEP 2 already appears to be installed.")
        return 0

    ui_patched = ui_original
    for label, old, new in REPLACEMENTS:
        ui_patched = replace_once(ui_patched, old, new, label)

    ui_patched = replace_once(
        ui_patched,
        POLL_CODE_ANCHOR,
        POLL_CODE_REPLACEMENT,
        "CONTEXT RUNTIME WATCH",
    )
    ui_patched = replace_once(
        ui_patched,
        FORMAT_EVENT_ANCHOR,
        FORMAT_EVENT_REPLACEMENT,
        "WORKSPACE TRACE EVENT",
    )
    ui_patched = replace_once(
        ui_patched,
        METHOD_INSERT_ANCHOR,
        METHODS + METHOD_INSERT_ANCHOR,
        "WORKSPACE METHODS",
    )

    if UI_BACKUP.exists() or CONTEXT_BACKUP.exists():
        raise FileExistsError(
            "STEP 2 backup already exists. "
            "Refusing to overwrite an earlier backup."
        )

    tmp_context = ROOT / ".context_storage.step2.candidate.py"
    tmp_ui = ROOT / ".ultra_ui.step2.candidate.py"
    tmp_context.write_text(new_context, encoding="utf-8", newline="\n")
    tmp_ui.write_text(ui_patched, encoding="utf-8", newline="\n")

    try:
        py_compile.compile(str(tmp_context), doraise=True)
        py_compile.compile(str(tmp_ui), doraise=True)
    finally:
        try:
            tmp_context.unlink()
        except FileNotFoundError:
            pass
        try:
            tmp_ui.unlink()
        except FileNotFoundError:
            pass

    shutil.copy2(CONTEXT, CONTEXT_BACKUP)
    shutil.copy2(UI, UI_BACKUP)

    CONTEXT.write_text(new_context, encoding="utf-8", newline="\n")
    UI.write_text(ui_patched, encoding="utf-8", newline="\n")

    py_compile.compile(str(CONTEXT), doraise=True)
    py_compile.compile(str(UI), doraise=True)
    py_compile.compile(str(SERVER), doraise=True)

    print("OK: Context Storage STEP 2 installed.")
    print("Backups:")
    print(f"  {CONTEXT_BACKUP.name}")
    print(f"  {UI_BACKUP.name}")
    print("Implemented:")
    print("  - persistent Chat metadata in .ultra/chats/")
    print("  - immutable RAW MESSAGE files with UUID-based IDs")
    print("  - RAW user message saved before API request")
    print("  - RAW assistant message saved before UI success")
    print("  - right Workspace/Chat panel")
    print("  - create and rename Chat")
    print("  - rename Workspace display name")
    print("  - PROJECT CONTEXT editor with revision backup")
    print("  - existing top security/interface panel preserved")
    print("  - Send button moved to the left side of chat controls")
    print("")
    print("Restart the application before testing.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
