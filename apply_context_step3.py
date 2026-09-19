from __future__ import annotations

import py_compile
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "server.py"
UI = ROOT / "ultra_ui.py"
UI_STATE = ROOT / "ui_state.py"

SERVER_BACKUP = ROOT / "server.py.before_context_step3"
UI_BACKUP = ROOT / "ultra_ui.py.before_context_step3"

SERVER_IMPORT_OLD = (
    "from context_storage import ensure_workspace_storage, load_project_context"
)
SERVER_IMPORT_NEW = (
    "from context_storage import (\n"
    "    ensure_workspace_storage,\n"
    "    load_chat_messages,\n"
    "    load_project_context,\n"
    ")"
)

SERVER_BACKUP_OLD = '''CORE_BACKUP_RELATIVE_PATHS = (
    "server.py",
    "context_storage.py",
    "ultra_ui.py",
'''

SERVER_BACKUP_NEW = '''CORE_BACKUP_RELATIVE_PATHS = (
    "server.py",
    "context_storage.py",
    "ui_state.py",
    "ultra_ui.py",
'''

SERVER_SIGNATURE_OLD = '''async def run_agent_task(
    task: str,
    workspace_root: str,
    *,
    on_event=None,
    permissions: dict | None = None,
) -> str:
'''

SERVER_SIGNATURE_NEW = '''async def run_agent_task(
    task: str,
    workspace_root: str,
    *,
    on_event=None,
    permissions: dict | None = None,
    chat_id: str | None = None,
) -> str:
'''

SERVER_CONTEXT_ANCHOR = '''    _emit(
        "run_started",
        {
            "task_preview": task[:200],
            "permissions": _policy_summary(policy),
            "workspace_id": workspace_info["workspace_id"],
        },
    )
'''

SERVER_CONTEXT_REPLACEMENT = '''    active_chat_messages = []
    if chat_id:
        try:
            raw_history = load_chat_messages(root, chat_id)
        except Exception as exc:
            _emit(
                "run_failed",
                {
                    "reason": "chat_context_load_error",
                    "api_requests": api_request_count,
                    "tool_calls": tool_call_count,
                    "duration": time.time() - start_time,
                    "chat_id": chat_id,
                    "error": str(exc),
                    "trace_path": f"logs/runs/{run_id}.jsonl",
                },
            )
            raise RuntimeError(
                "Не удалось загрузить историю активного чата."
            ) from exc

        for item in raw_history:
            role = item.get("role")
            content = item.get("original_text")
            if (
                role in {"user", "assistant"}
                and isinstance(content, str)
                and content.strip()
            ):
                active_chat_messages.append(
                    {"role": role, "content": content}
                )

        # UI сохраняет текущее пользовательское сообщение ДО запуска API.
        # Для прямых вызовов run_agent_task без предварительного сохранения
        # гарантируем, что текущая задача всё равно попадёт в запрос ровно один раз.
        if not (
            active_chat_messages
            and active_chat_messages[-1]["role"] == "user"
            and active_chat_messages[-1]["content"] == task
        ):
            active_chat_messages.append({"role": "user", "content": task})

    else:
        active_chat_messages = [{"role": "user", "content": task}]

    _emit(
        "run_started",
        {
            "task_preview": task[:200],
            "permissions": _policy_summary(policy),
            "workspace_id": workspace_info["workspace_id"],
            "chat_id": chat_id,
        },
    )
    if chat_id:
        _emit(
            "chat_context_loaded",
            {
                "chat_id": chat_id,
                "messages": len(active_chat_messages),
                "chars": sum(
                    len(item.get("content") or "")
                    for item in active_chat_messages
                ),
            },
        )
'''

SERVER_MESSAGES_OLD = '''    messages = [
        {
            "role": "system",
            "content": (
                "Ты работаешь как локальный file-agent внутри workspace. "
                "Для всех file tools используй ТОЛЬКО относительные пути. "
                "Корень workspace обозначай точкой '.'. "
                "Никогда не передавай абсолютные Windows-пути в list_dir, "
                "read_file, write_file или delete_file."
                f"{permission_text}\\n"
                f"{project_context_block}\\n"
                "ОБЯЗАТЕЛЬНЫЙ РЕГЛАМЕНТ ULTRA\\n\\n"
                f"{policy_text}"
            ),
        },
        {"role": "user", "content": task},
    ]
'''

SERVER_MESSAGES_NEW = '''    messages = [
        {
            "role": "system",
            "content": (
                "Ты работаешь как локальный file-agent внутри workspace. "
                "Для всех file tools используй ТОЛЬКО относительные пути. "
                "Корень workspace обозначай точкой '.'. "
                "Никогда не передавай абсолютные Windows-пути в list_dir, "
                "read_file, write_file или delete_file."
                f"{permission_text}\\n"
                f"{project_context_block}\\n"
                "ОБЯЗАТЕЛЬНЫЙ РЕГЛАМЕНТ ULTRA\\n\\n"
                f"{policy_text}"
            ),
        },
        *active_chat_messages,
    ]
'''

UI_IMPORT_ANCHOR = '''from context_storage import (
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
)
'''

UI_IMPORT_REPLACEMENT = '''from context_storage import (
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
)
from ui_state import load_ui_state, save_ui_state
'''

UI_INIT_HEAD_OLD = '''        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1500x860")
        self.minsize(1180, 720)

        self.workspace_var = tk.StringVar(value=str(Path.cwd()))
        self.status_var = tk.StringVar(value="Готово")
'''

UI_INIT_HEAD_NEW = '''        super().__init__()
        self._ui_state = load_ui_state()

        self.title(APP_TITLE)
        self.geometry(self._ui_state.get("geometry") or "1500x860")
        self.minsize(1180, 720)

        self.workspace_var = tk.StringVar(value=str(Path.cwd()))
        self.status_var = tk.StringVar(value="Готово")
'''

UI_THEME_VARS_OLD = '''        self.auto_backup_var = tk.BooleanVar(value=True)
        self.dark_theme_var = tk.BooleanVar(value=True)

        # Настраиваемые цвета основных текстовых потоков интерфейса.
        self.log_text_color_var = tk.StringVar(value="#76E68A")
        self.user_text_color_var = tk.StringVar(value="#FFFFFF")
        self.assistant_text_color_var = tk.StringVar(value="#8EC5FF")
'''

UI_THEME_VARS_NEW = '''        self.auto_backup_var = tk.BooleanVar(value=True)
        self.dark_theme_var = tk.BooleanVar(
            value=bool(self._ui_state.get("dark_theme", True))
        )

        # Настраиваемые цвета основных текстовых потоков интерфейса.
        saved_colors = self._ui_state.get("colors") or {}
        self.log_text_color_var = tk.StringVar(
            value=saved_colors.get("log", "#76E68A")
        )
        self.user_text_color_var = tk.StringVar(
            value=saved_colors.get("user", "#FFFFFF")
        )
        self.assistant_text_color_var = tk.StringVar(
            value=saved_colors.get("assistant", "#8EC5FF")
        )
        self.workspace_text_color_var = tk.StringVar(
            value=saved_colors.get("workspace", "#E8E8E8")
        )
'''

UI_STATE_BLOCK_OLD = '''        self.current_workspace_id: str | None = None
        self.current_chat_id: str | None = None
        self._loaded_workspace_root: str | None = None
        self._context_storage_mtime = None

        self._build_ui()
        self._apply_theme()
        self._record_context_storage_mtime()
        self._load_workspace_browser(silent=True)
        self.after(100, self._poll_events)
'''

UI_STATE_BLOCK_NEW = '''        self.current_workspace_id: str | None = None
        self.current_chat_id: str | None = None
        self._loaded_workspace_root: str | None = None
        self._context_storage_mtime = None
        self._workspace_registry: list[dict] = list(
            self._ui_state.get("workspaces") or []
        )
        self._theme_colors: dict[str, str] = {}

        self._build_ui()
        self._apply_theme()
        self._record_context_storage_mtime()
        self._initialize_workspace_registry()
        self.after_idle(self._restore_panel_layout)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_events)
'''

UI_THEME_COMMAND_OLD = '''            variable=self.dark_theme_var,
            command=self._apply_theme,
'''

UI_THEME_COMMAND_NEW = '''            variable=self.dark_theme_var,
            command=self._on_theme_changed,
'''

UI_COLOR_ROWS_OLD = '''            (
                3,
                "Ответ Ultra",
                "assistant",
                self.assistant_text_color_var,
                "Цвет текста — ответ Ultra",
            ),
        ]
'''

UI_COLOR_ROWS_NEW = '''            (
                3,
                "Ответ Ultra",
                "assistant",
                self.assistant_text_color_var,
                "Цвет текста — ответ Ultra",
            ),
            (
                4,
                "Workspace / чаты",
                "workspace",
                self.workspace_text_color_var,
                "Цвет текста — Workspace и чаты",
            ),
        ]
'''

UI_RESET_INSERT_OLD = '''            self._color_swatches[key] = swatch

        # Галочка чтения находится прямо у области, которой она управляет.
'''

UI_RESET_INSERT_NEW = '''            self._color_swatches[key] = swatch

        reset_layout_button = ttk.Button(
            interface_frame,
            text="Сброс панелей",
            command=self._reset_panel_layout,
        )
        reset_layout_button.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(5, 0),
        )

        # Галочка чтения находится прямо у области, которой она управляет.
'''

UI_SWATCH_VALUES_OLD = '''        values = {
            "log": self.log_text_color_var.get(),
            "user": self.user_text_color_var.get(),
            "assistant": self.assistant_text_color_var.get(),
        }
'''

UI_SWATCH_VALUES_NEW = '''        values = {
            "log": self.log_text_color_var.get(),
            "user": self.user_text_color_var.get(),
            "assistant": self.assistant_text_color_var.get(),
            "workspace": self.workspace_text_color_var.get(),
        }
'''

UI_CHOOSE_COLOR_OLD = '''        target_var.set(selected.upper())
        self._apply_text_colors()
'''

UI_CHOOSE_COLOR_NEW = '''        target_var.set(selected.upper())
        self._apply_text_colors()
        self._save_ui_state(silent=True)
'''

UI_WORKER_OLD = '''                run_agent_task(
                    task,
                    workspace,
                    on_event=on_event,
                    permissions=permissions,
                )
'''

UI_WORKER_NEW = '''                run_agent_task(
                    task,
                    workspace,
                    on_event=on_event,
                    permissions=permissions,
                    chat_id=chat_id,
                )
'''

UI_EVENT_ANCHOR = '''        if event_type == "workspace_context_loaded":
            return (
                f"[{time_str}] WORKSPACE CONTEXT | "
                f"{event.get('workspace_id')} | "
                f"chars={event.get('project_context_chars')}"
            )

        if event_type == "backup_started":
'''

UI_EVENT_REPLACEMENT = '''        if event_type == "workspace_context_loaded":
            return (
                f"[{time_str}] WORKSPACE CONTEXT | "
                f"{event.get('workspace_id')} | "
                f"chars={event.get('project_context_chars')}"
            )

        if event_type == "chat_context_loaded":
            return (
                f"[{time_str}] CHAT CONTEXT | "
                f"{event.get('chat_id')} | "
                f"messages={event.get('messages')} | "
                f"chars={event.get('chars')}"
            )

        if event_type == "backup_started":
'''

UI_BUILD_PREFIX_PATTERN = re.compile(
    r'''    def _build_ui\(self\) -> None:\n'''
    r'''        root = ttk\.Frame\(self, padding=12\)\n'''
    r'''        root\.pack\(fill="both", expand=True\)\n'''
    r'''.*?'''
    r'''        # Workspace — намеренно компактный: оставляем справа запас под будущие controls\.\n''',
    re.S,
)

UI_BUILD_PREFIX_NEW = '''    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        self.main_paned = tk.PanedWindow(
            root,
            orient="horizontal",
            sashwidth=6,
            showhandle=False,
            bd=0,
            relief="flat",
        )
        self.main_paned.pack(fill="both", expand=True)
        self.main_paned.bind(
            "<ButtonRelease-1>",
            lambda _event: self.after(40, self._save_ui_state),
        )

        # Левая панель — наблюдаемый trace.
        left_frame = ttk.Frame(self.main_paned, width=360)
        self.main_paned.add(left_frame, minsize=240)

        ttk.Label(left_frame, text="ЛОГ ДЕЙСТВИЙ").pack(
            anchor="w", pady=(0, 6)
        )
        self.trace_log = scrolledtext.ScrolledText(
            left_frame,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
        )
        self.trace_log.pack(fill="both", expand=True)
        self.trace_log.tag_configure(
            "trace",
            foreground=self.log_text_color_var.get(),
            font=("Consolas", 9),
        )

        # Центральная панель — текущий чат и верхняя системная зона.
        right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(right_frame, minsize=600, stretch="always")

        # Справа — отдельная подвижная панель WORKSPACES / ЧАТЫ.
        self._build_workspace_browser(self.main_paned)

        # Workspace — намеренно компактный: оставляем справа запас под будущие controls.
'''

UI_WORKSPACE_METHODS_PATTERN = re.compile(
    r'''    def _record_context_storage_mtime\(self\) -> None:\n'''
    r'''.*?'''
    r'''    def _choose_scope\(self, target_var: tk\.StringVar\) -> None:\n''',
    re.S,
)

UI_WORKSPACE_METHODS_NEW = r'''    def _record_context_storage_mtime(self) -> None:
        try:
            self._context_storage_mtime = Path(
                "context_storage.py"
            ).stat().st_mtime
        except FileNotFoundError:
            self._context_storage_mtime = None

    def _on_theme_changed(self) -> None:
        self._apply_theme()
        self._save_ui_state(silent=True)

    def _capture_panel_sashes(self) -> list[int]:
        paned = getattr(self, "main_paned", None)
        if paned is None:
            return []
        try:
            return [
                int(paned.sash_coord(0)[0]),
                int(paned.sash_coord(1)[0]),
            ]
        except (tk.TclError, IndexError):
            return []

    def _restore_panel_layout(self) -> None:
        paned = getattr(self, "main_paned", None)
        if paned is None:
            return
        try:
            self.update_idletasks()
            total_width = max(paned.winfo_width(), 1180)
            sashes = self._ui_state.get("panel_sashes") or []
            if (
                isinstance(sashes, list)
                and len(sashes) == 2
                and all(isinstance(item, int) for item in sashes)
                and 220 < sashes[0] < sashes[1] - 400
                and sashes[1] < total_width - 180
            ):
                left_pos, right_pos = sashes
            else:
                left_pos = 360
                right_pos = max(820, total_width - 320)

            paned.sash_place(0, left_pos, 0)
            paned.sash_place(1, right_pos, 0)
        except tk.TclError:
            pass

    def _reset_panel_layout(self) -> None:
        self._ui_state["panel_sashes"] = []
        self.update_idletasks()
        paned = getattr(self, "main_paned", None)
        if paned is None:
            return
        try:
            total_width = max(paned.winfo_width(), 1180)
            paned.sash_place(0, 360, 0)
            paned.sash_place(1, max(820, total_width - 320), 0)
        except tk.TclError:
            pass
        self._save_ui_state(silent=True)

    def _save_ui_state(self, _event=None, *, silent: bool = True) -> None:
        try:
            self._ui_state["geometry"] = self.geometry()
            self._ui_state["dark_theme"] = self.dark_theme_var.get()
            self._ui_state["colors"] = {
                "log": self.log_text_color_var.get(),
                "user": self.user_text_color_var.get(),
                "assistant": self.assistant_text_color_var.get(),
                "workspace": self.workspace_text_color_var.get(),
            }
            sashes = self._capture_panel_sashes()
            if len(sashes) == 2:
                self._ui_state["panel_sashes"] = sashes
            self._ui_state["workspaces"] = list(self._workspace_registry)
            self._ui_state["active_workspace_id"] = self.current_workspace_id
            save_ui_state(self._ui_state)
        except Exception as exc:
            if not silent:
                messagebox.showerror(
                    APP_TITLE,
                    f"Не удалось сохранить UI state.\\n\\n"
                    f"{type(exc).__name__}: {exc}",
                )

    def _on_close(self) -> None:
        self._save_ui_state(silent=True)
        self.destroy()

    def _apply_workspace_sidebar_theme(self) -> None:
        canvas = getattr(self, "workspace_canvas", None)
        list_frame = getattr(self, "workspace_list_frame", None)
        if canvas is None or list_frame is None:
            return
        field = self._theme_colors.get("field", "#202124")
        try:
            canvas.configure(bg=field)
            list_frame.configure(bg=field)
        except tk.TclError:
            pass

    def _build_workspace_browser(self, parent) -> None:
        panel = ttk.LabelFrame(
            parent,
            text="WORKSPACES / ЧАТЫ",
            padding=8,
        )
        self.workspace_panel = panel
        parent.add(panel, minsize=240)

        self.add_workspace_button = ttk.Button(
            panel,
            text="+ Создать Workspace",
            command=self._add_workspace_dialog,
        )
        self.add_workspace_button.pack(fill="x", pady=(0, 8))

        host = ttk.Frame(panel)
        host.pack(fill="both", expand=True)

        self.workspace_canvas = tk.Canvas(
            host,
            highlightthickness=0,
            bd=0,
        )
        scroll = ttk.Scrollbar(
            host,
            orient="vertical",
            command=self.workspace_canvas.yview,
        )
        self.workspace_canvas.configure(yscrollcommand=scroll.set)

        self.workspace_canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.workspace_list_frame = tk.Frame(self.workspace_canvas)
        self._workspace_canvas_window = self.workspace_canvas.create_window(
            (0, 0),
            window=self.workspace_list_frame,
            anchor="nw",
        )

        def on_inner_configure(_event=None):
            self.workspace_canvas.configure(
                scrollregion=self.workspace_canvas.bbox("all")
            )

        def on_canvas_configure(event):
            self.workspace_canvas.itemconfigure(
                self._workspace_canvas_window,
                width=max(event.width, 1),
            )

        self.workspace_list_frame.bind("<Configure>", on_inner_configure)
        self.workspace_canvas.bind("<Configure>", on_canvas_configure)
        self.workspace_canvas.bind(
            "<MouseWheel>",
            lambda event: self.workspace_canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units",
            ),
        )

        self._workspace_widgets.append(self.add_workspace_button)
        self._apply_workspace_sidebar_theme()

    def _sidebar_button(
        self,
        parent,
        text: str,
        command,
        *,
        width: int | None = None,
    ) -> tk.Button:
        colors = self._theme_colors
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=colors.get("button_bg", "#35383d"),
            fg=colors.get("fg", "#e8e8e8"),
            activebackground=colors.get("select_bg", "#3f638f"),
            activeforeground=colors.get("fg", "#e8e8e8"),
            relief="flat",
            borderwidth=1,
            padx=4,
            pady=1,
            cursor="hand2",
            width=width or 0,
        )
        self._workspace_widgets.append(button)
        return button

    def _register_workspace_path(self, workspace: Path) -> dict:
        root = workspace.resolve()
        info = ensure_workspace_storage(root)
        existing = next(
            (
                item
                for item in self._workspace_registry
                if item.get("workspace_id") == info["workspace_id"]
            ),
            None,
        )
        if existing is None:
            existing = {
                "workspace_id": info["workspace_id"],
                "path": str(root),
                "last_chat_id": None,
            }
            self._workspace_registry.append(existing)
        else:
            existing["path"] = str(root)
        return existing

    def _initialize_workspace_registry(self) -> None:
        clean_registry = []
        seen = set()

        for item in self._workspace_registry:
            try:
                path = Path(str(item.get("path") or "")).resolve()
                if not path.is_dir():
                    continue
                info = ensure_workspace_storage(path)
            except Exception:
                continue
            workspace_id = info["workspace_id"]
            if workspace_id in seen:
                continue
            seen.add(workspace_id)
            clean_registry.append(
                {
                    "workspace_id": workspace_id,
                    "path": str(path),
                    "last_chat_id": (
                        item.get("last_chat_id")
                        if isinstance(item.get("last_chat_id"), str)
                        else None
                    ),
                }
            )

        self._workspace_registry = clean_registry

        current_entry = None
        if not self._ui_state.get("registry_initialized", False):
            cwd = Path.cwd().resolve()
            try:
                current_entry = self._register_workspace_path(cwd)
            except Exception:
                current_entry = None
            self._ui_state["registry_initialized"] = True

        active_id = self._ui_state.get("active_workspace_id")
        active_entry = next(
            (
                item
                for item in self._workspace_registry
                if item.get("workspace_id") == active_id
            ),
            None,
        )
        if active_entry is None:
            active_entry = current_entry
        if active_entry is None and self._workspace_registry:
            active_entry = self._workspace_registry[0]

        if active_entry is not None:
            self._activate_workspace(
                Path(active_entry["path"]),
                preferred_chat_id=active_entry.get("last_chat_id"),
                save=False,
            )
        else:
            self._render_workspace_sidebar()

        self._save_ui_state(silent=True)

    def _render_workspace_sidebar(self) -> None:
        frame = getattr(self, "workspace_list_frame", None)
        if frame is None:
            return

        for child in frame.winfo_children():
            child.destroy()

        persistent = []
        if hasattr(self, "add_workspace_button"):
            persistent.append(self.add_workspace_button)
        self._workspace_widgets = persistent

        colors = self._theme_colors or {
            "field": "#202124",
            "fg": "#e8e8e8",
            "select_bg": "#3f638f",
            "button_bg": "#35383d",
        }
        field = colors["field"]
        text_color = self.workspace_text_color_var.get()

        try:
            frame.configure(bg=field)
            self.workspace_canvas.configure(bg=field)
        except tk.TclError:
            pass

        for index, item in enumerate(list(self._workspace_registry)):
            path = Path(item["path"])
            if not path.is_dir():
                continue

            try:
                info = ensure_workspace_storage(path)
                chats = list_chats(path)
                if not chats:
                    chats = [create_chat(path)]
            except Exception:
                continue

            active_workspace = (
                info["workspace_id"] == self.current_workspace_id
            )

            workspace_row = tk.Frame(frame, bg=field)
            workspace_row.pack(fill="x", padx=2, pady=(4 if index else 2, 2))

            name_label = tk.Label(
                workspace_row,
                text=("▶ " if active_workspace else "") + info["display_name"],
                anchor="w",
                bg=field,
                fg=text_color,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
            )
            name_label.pack(side="left", fill="x", expand=True)
            name_label.bind(
                "<Button-1>",
                lambda _event, p=path: self._activate_workspace(p),
            )

            self._sidebar_button(
                workspace_row,
                "+",
                lambda p=path: self._create_chat_for_workspace(p),
                width=2,
            ).pack(side="left", padx=(2, 0))

            self._sidebar_button(
                workspace_row,
                "✎",
                lambda p=path: self._rename_workspace_ui(p),
                width=2,
            ).pack(side="left", padx=(2, 0))

            self._sidebar_button(
                workspace_row,
                "Контекст",
                lambda p=path: self._open_project_context_editor(p),
            ).pack(side="left", padx=(2, 0))

            self._sidebar_button(
                workspace_row,
                "×",
                lambda wid=info["workspace_id"]: self._remove_workspace_ui(wid),
                width=2,
            ).pack(side="left", padx=(2, 0))

            for chat in chats:
                chat_row = tk.Frame(frame, bg=field)
                chat_row.pack(fill="x", padx=(16, 4), pady=1)

                is_active_chat = (
                    active_workspace
                    and chat["chat_id"] == self.current_chat_id
                )
                chat_label = tk.Label(
                    chat_row,
                    text=("• " if is_active_chat else "  ") + chat["title"],
                    anchor="w",
                    bg=field,
                    fg=text_color,
                    font=("Segoe UI", 9),
                    cursor="hand2",
                )
                chat_label.pack(side="left", fill="x", expand=True)
                chat_label.bind(
                    "<Button-1>",
                    lambda _event, p=path, cid=chat["chat_id"]:
                        self._activate_workspace(
                            p,
                            preferred_chat_id=cid,
                        ),
                )

                self._sidebar_button(
                    chat_row,
                    "✎",
                    lambda p=path, cid=chat["chat_id"]:
                        self._rename_chat_ui(p, cid),
                    width=2,
                ).pack(side="right")

        self.workspace_canvas.configure(
            scrollregion=self.workspace_canvas.bbox("all")
        )

    def _workspace_path_from_ui(self) -> Path:
        text = self.workspace_var.get().strip().strip('"')
        workspace = Path(text)
        if not workspace.is_absolute() or not workspace.is_dir():
            raise ValueError(
                "Workspace должен быть существующей абсолютной папкой."
            )
        return workspace.resolve()

    def _activate_workspace(
        self,
        workspace: Path,
        *,
        preferred_chat_id: str | None = None,
        save: bool = True,
    ) -> None:
        if self.running:
            return

        root = workspace.resolve()
        entry = self._register_workspace_path(root)
        info = ensure_workspace_storage(root)
        chats = list_chats(root)
        if not chats:
            chats = [create_chat(root)]

        valid_ids = {item["chat_id"] for item in chats}
        candidate = preferred_chat_id or entry.get("last_chat_id")
        if candidate not in valid_ids:
            candidate = chats[-1]["chat_id"]

        self.current_workspace_id = info["workspace_id"]
        self.current_chat_id = candidate
        self._loaded_workspace_root = str(root)
        self.workspace_var.set(str(root))
        entry["last_chat_id"] = candidate

        if (root / "Документация").is_dir():
            self.write_scope_var.set("Документация")
        else:
            self.write_scope_var.set(".")

        self._render_current_chat()
        self._render_workspace_sidebar()
        if save:
            self._save_ui_state(silent=True)

    def _load_workspace_browser(
        self,
        *,
        silent: bool = False,
        preferred_chat_id: str | None = None,
    ) -> None:
        try:
            workspace = self._workspace_path_from_ui()
            self._activate_workspace(
                workspace,
                preferred_chat_id=preferred_chat_id,
            )
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
            self._activate_workspace(workspace)
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

    def _add_workspace_dialog(self) -> None:
        if self.running:
            return
        selected = filedialog.askdirectory(
            initialdir=self.workspace_var.get() or str(Path.cwd()),
            title="Создать / подключить Workspace",
        )
        if not selected:
            return
        try:
            workspace = Path(selected).resolve()
            entry = self._register_workspace_path(workspace)
            chats = list_chats(workspace)
            if not chats:
                chat = create_chat(workspace)
                entry["last_chat_id"] = chat["chat_id"]
            self._activate_workspace(
                workspace,
                preferred_chat_id=entry.get("last_chat_id"),
            )
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось создать / подключить Workspace.\\n\\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _choose_workspace(self) -> None:
        self._add_workspace_dialog()

    def _create_chat_for_workspace(self, workspace: Path) -> None:
        if self.running:
            return
        try:
            chat = create_chat(workspace)
            self._activate_workspace(
                workspace,
                preferred_chat_id=chat["chat_id"],
            )
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось создать чат.\\n\\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _rename_workspace_ui(self, workspace: Path) -> None:
        if self.running:
            return
        try:
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
            self._render_workspace_sidebar()
            self._save_ui_state(silent=True)
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось переименовать Workspace.\\n\\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _rename_chat_ui(self, workspace: Path, chat_id: str) -> None:
        if self.running:
            return
        try:
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
            self._render_workspace_sidebar()
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось переименовать чат.\\n\\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _remove_workspace_ui(self, workspace_id: str) -> None:
        if self.running:
            return

        item = next(
            (
                entry
                for entry in self._workspace_registry
                if entry.get("workspace_id") == workspace_id
            ),
            None,
        )
        if item is None:
            return

        if not messagebox.askyesno(
            APP_TITLE,
            "Убрать Workspace только из списка приложения?\\n\\n"
            "Папка проекта, .ultra, чаты и PROJECT CONTEXT "
            "НЕ будут удалены.",
        ):
            return

        self._workspace_registry = [
            entry
            for entry in self._workspace_registry
            if entry.get("workspace_id") != workspace_id
        ]

        if self.current_workspace_id == workspace_id:
            if self._workspace_registry:
                next_item = self._workspace_registry[0]
                self._activate_workspace(
                    Path(next_item["path"]),
                    preferred_chat_id=next_item.get("last_chat_id"),
                    save=False,
                )
            else:
                self.current_workspace_id = None
                self.current_chat_id = None
                self._loaded_workspace_root = None
                self._render_workspace_sidebar()
                self.chat.configure(state="normal")
                self.chat.delete("1.0", "end")
                self.chat.configure(state="disabled")

        self._save_ui_state(silent=True)
        self._render_workspace_sidebar()

    def _open_project_context_editor(
        self,
        workspace: Path | None = None,
    ) -> None:
        try:
            if workspace is None:
                workspace = self._workspace_path_from_ui()
            workspace = workspace.resolve()
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

    def _choose_scope(self, target_var: tk.StringVar) -> None:
'''

UI_THEME_STYLE_ANCHOR = '''        else:
            bg = "#f3f3f3"
            panel = "#f3f3f3"
            field = "#ffffff"
            fg = "#111111"
            muted = "#444444"
            select_bg = "#99c2ff"
            button_bg = "#e7e7e7"

        self.configure(bg=bg)
'''

UI_THEME_STYLE_REPLACEMENT = '''        else:
            bg = "#f3f3f3"
            panel = "#f3f3f3"
            field = "#ffffff"
            fg = "#111111"
            muted = "#444444"
            select_bg = "#99c2ff"
            button_bg = "#e7e7e7"

        self._theme_colors = {
            "bg": bg,
            "panel": panel,
            "field": field,
            "fg": fg,
            "muted": muted,
            "select_bg": select_bg,
            "button_bg": button_bg,
        }

        self.configure(bg=bg)
'''

UI_APPLY_TEXT_END_OLD = '''        self._refresh_color_swatches()
'''

UI_APPLY_TEXT_END_NEW = '''        self._refresh_color_swatches()
        self._apply_workspace_sidebar_theme()
        if hasattr(self, "workspace_list_frame"):
            self._render_workspace_sidebar()
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly 1 match, found {count}. "
            "No files were changed."
        )
    return text.replace(old, new, 1)


def regex_replace_once(
    text: str,
    pattern: re.Pattern,
    new: str,
    label: str,
) -> str:
    result, count = pattern.subn(new, text, count=1)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly 1 regex match, found {count}. "
            "No files were changed."
        )
    return result


def patch_server(original: str) -> str:
    if "chat_context_loaded" in original:
        raise RuntimeError("STEP 3 already appears to be installed in server.py.")

    text = original
    text = replace_once(text, SERVER_IMPORT_OLD, SERVER_IMPORT_NEW, "SERVER IMPORT")
    text = replace_once(text, SERVER_BACKUP_OLD, SERVER_BACKUP_NEW, "SERVER BACKUP LIST")
    text = replace_once(text, SERVER_SIGNATURE_OLD, SERVER_SIGNATURE_NEW, "SERVER SIGNATURE")
    text = replace_once(text, SERVER_CONTEXT_ANCHOR, SERVER_CONTEXT_REPLACEMENT, "SERVER CHAT CONTEXT")
    text = replace_once(text, SERVER_MESSAGES_OLD, SERVER_MESSAGES_NEW, "SERVER MESSAGES")
    return text


def patch_ui(original: str) -> str:
    if "_initialize_workspace_registry" in original:
        raise RuntimeError("STEP 3 already appears to be installed in ultra_ui.py.")

    text = original
    text = replace_once(text, UI_IMPORT_ANCHOR, UI_IMPORT_REPLACEMENT, "UI IMPORT")
    text = replace_once(text, UI_INIT_HEAD_OLD, UI_INIT_HEAD_NEW, "UI INIT HEAD")
    text = replace_once(text, UI_THEME_VARS_OLD, UI_THEME_VARS_NEW, "UI THEME VARS")
    text = replace_once(text, UI_STATE_BLOCK_OLD, UI_STATE_BLOCK_NEW, "UI STATE BLOCK")
    text = replace_once(text, UI_THEME_STYLE_ANCHOR, UI_THEME_STYLE_REPLACEMENT, "UI THEME COLORS")
    text = replace_once(text, UI_SWATCH_VALUES_OLD, UI_SWATCH_VALUES_NEW, "UI SWATCH VALUES")
    text = replace_once(text, UI_CHOOSE_COLOR_OLD, UI_CHOOSE_COLOR_NEW, "UI COLOR SAVE")
    text = replace_once(text, UI_THEME_COMMAND_OLD, UI_THEME_COMMAND_NEW, "UI THEME COMMAND")
    text = replace_once(text, UI_COLOR_ROWS_OLD, UI_COLOR_ROWS_NEW, "UI WORKSPACE COLOR")
    text = replace_once(text, UI_RESET_INSERT_OLD, UI_RESET_INSERT_NEW, "UI RESET PANELS BUTTON")
    text = regex_replace_once(text, UI_BUILD_PREFIX_PATTERN, UI_BUILD_PREFIX_NEW, "UI PANED LAYOUT")
    text = regex_replace_once(text, UI_WORKSPACE_METHODS_PATTERN, UI_WORKSPACE_METHODS_NEW, "UI WORKSPACE METHODS")
    text = replace_once(text, UI_EVENT_ANCHOR, UI_EVENT_REPLACEMENT, "UI CHAT CONTEXT EVENT")
    text = replace_once(text, UI_WORKER_OLD, UI_WORKER_NEW, "UI WORKER CHAT ID")
    text = replace_once(text, UI_APPLY_TEXT_END_OLD, UI_APPLY_TEXT_END_NEW, "UI APPLY SIDEBAR COLORS")
    return text


def main() -> int:
    if not SERVER.is_file():
        raise FileNotFoundError(f"Missing: {SERVER}")
    if not UI.is_file():
        raise FileNotFoundError(f"Missing: {UI}")
    if not UI_STATE.is_file():
        raise FileNotFoundError("Missing ui_state.py next to apply_context_step3.py.")

    server_original = SERVER.read_text(encoding="utf-8-sig")
    ui_original = UI.read_text(encoding="utf-8-sig")

    if "def _build_workspace_browser(self, root: ttk.Frame)" not in ui_original:
        raise RuntimeError(
            "STEP 2 baseline not found in ultra_ui.py. "
            "STEP 3 installer refuses to guess."
        )
    if (
        "from context_storage import "
        "ensure_workspace_storage, load_project_context"
        not in server_original
    ):
        raise RuntimeError(
            "STEP 1/2 baseline not found in server.py. "
            "STEP 3 installer refuses to guess."
        )

    if SERVER_BACKUP.exists() or UI_BACKUP.exists():
        raise FileExistsError(
            "STEP 3 backup already exists. "
            "Refusing to overwrite an earlier backup."
        )

    server_patched = patch_server(server_original)
    ui_patched = patch_ui(ui_original)

    tmp_server = ROOT / ".server.step3.candidate.py"
    tmp_ui = ROOT / ".ultra_ui.step3.candidate.py"
    tmp_server.write_text(server_patched, encoding="utf-8", newline="\n")
    tmp_ui.write_text(ui_patched, encoding="utf-8", newline="\n")

    try:
        py_compile.compile(str(UI_STATE), doraise=True)
        py_compile.compile(str(tmp_server), doraise=True)
        py_compile.compile(str(tmp_ui), doraise=True)
    finally:
        try:
            tmp_server.unlink()
        except FileNotFoundError:
            pass
        try:
            tmp_ui.unlink()
        except FileNotFoundError:
            pass

    shutil.copy2(SERVER, SERVER_BACKUP)
    shutil.copy2(UI, UI_BACKUP)

    SERVER.write_text(server_patched, encoding="utf-8", newline="\n")
    UI.write_text(ui_patched, encoding="utf-8", newline="\n")

    py_compile.compile(str(UI_STATE), doraise=True)
    py_compile.compile(str(SERVER), doraise=True)
    py_compile.compile(str(UI), doraise=True)

    print("OK: Context/UI STEP 3 installed.")
    print("Backups:")
    print(f"  {SERVER_BACKUP.name}")
    print(f"  {UI_BACKUP.name}")
    print("Implemented:")
    print("  - real Active Chat Context from selected chat RAW history")
    print("  - multiple registered Workspaces")
    print("  - + Create Workspace above the Workspace list")
    print("  - per-Workspace: + chat / rename / Context / remove from list")
    print("  - per-Chat rename action")
    print("  - dark Workspace/Chat panel")
    print("  - configurable Workspace/Chat text color")
    print("  - movable left/center/right panes")
    print("  - panel positions, colors, theme and Workspace list persist locally")
    print("  - Reset panels button")
    print("")
    print("Restart the application before testing.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
