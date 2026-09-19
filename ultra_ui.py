import asyncio
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import (
    colorchooser,
    filedialog,
    messagebox,
    scrolledtext,
    simpledialog,
    ttk,
)

from server import get_backup_base_path, run_agent_task
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
)
from ui_state import load_ui_state, save_ui_state
from workspace_runtime_settings import (
    load_workspace_runtime_settings,
    save_workspace_runtime_settings,
)
from agent_global_context import (
    get_agent_global_context_path,
    load_agent_global_context,
    save_agent_global_context,
)
from server_context_messages import (
    delete_server_context_message,
    get_server_context_messages_path,
    list_server_context_event_records,
    upsert_server_context_message,
    validate_event_id,
)


APP_TITLE = "GigaChat Ultra Local Agent"


def bind_edit_shortcuts(widget) -> None:
    """Явно включить привычные Windows-сочетания для Tkinter."""

    def paste(_event=None):
        widget.event_generate("<<Paste>>")
        return "break"

    def copy(_event=None):
        widget.event_generate("<<Copy>>")
        return "break"

    def cut(_event=None):
        widget.event_generate("<<Cut>>")
        return "break"

    def select_all(_event=None):
        try:
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "1.0")
            widget.see("insert")
        except tk.TclError:
            try:
                widget.selection_range(0, "end")
                widget.icursor("end")
            except tk.TclError:
                pass
        return "break"

    for sequence in ("<Control-v>", "<Control-V>"):
        widget.bind(sequence, paste)
    for sequence in ("<Control-c>", "<Control-C>"):
        widget.bind(sequence, copy)
    for sequence in ("<Control-x>", "<Control-X>"):
        widget.bind(sequence, cut)
    for sequence in ("<Control-a>", "<Control-A>"):
        widget.bind(sequence, select_all)


class UltraApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self._ui_state = load_ui_state()

        self.title(APP_TITLE)
        self.geometry(
            self._ui_state.get("normal_geometry") or "1500x860"
        )
        self.minsize(1180, 720)

        self.workspace_var = tk.StringVar(value=str(Path.cwd()))
        self.status_var = tk.StringVar(value="Готово")

        # Серверные разрешения запуска. Безопасные значения по умолчанию:
        # читать можно весь workspace, писать нельзя, autobackup включён.
        self.allow_read_var = tk.BooleanVar(value=True)
        self.allow_write_var = tk.BooleanVar(value=False)
        self.allow_delete_var = tk.BooleanVar(value=False)
        self.allow_verify_var = tk.BooleanVar(value=True)
        self.allow_guard_p1_var = tk.BooleanVar(value=True)
        self.auto_backup_var = tk.BooleanVar(value=True)
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

        self.tool_limit_var = tk.StringVar(value="20")
        self.read_scope_var = tk.StringVar(value=".")
        default_write_scope = "Документация" if (Path.cwd() / "Документация").is_dir() else "."
        self.write_scope_var = tk.StringVar(value=default_write_scope)
        self.delete_scope_var = tk.StringVar(value=".")
        self.backup_path_var = tk.StringVar(value=str(get_backup_base_path()))

        self.running = False
        self.started_at = 0.0
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.trace_events: queue.Queue[dict] = queue.Queue()

        self._code_changed = False
        self._changed_files: list[str] = []
        self._server_mtime = None
        self._ui_mtime = None
        self._server_context_messages_mtime = None
        self._record_initial_mtimes()

        self._security_widgets: list[tk.Widget] = []
        self._workspace_widgets: list[tk.Widget] = []
        self._color_swatches: dict[str, tk.Widget] = {}
        self._run_started_once = False

        self.current_workspace_id: str | None = None
        self.current_chat_id: str | None = None
        self._loaded_workspace_root: str | None = None
        self._context_storage_mtime = None
        self._workspace_registry: list[dict] = list(
            self._ui_state.get("workspaces") or []
        )
        self._theme_colors: dict[str, str] = {}
        self._last_window_mode = "normal"
        self._last_root_width: int | None = None
        self._layout_sync_after = None

        self._build_ui()
        self._apply_theme()
        self._record_context_storage_mtime()
        self._initialize_workspace_registry()
        self.bind("<Configure>", self._on_root_configure)
        self.after_idle(self._restore_window_and_layout)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_events)
        self.after(100, self._poll_trace_events)
        self.after(500, self._tick_status)
        self.after(1000, self._poll_code_changes)

    def _apply_theme(self) -> None:
        dark = self.dark_theme_var.get()
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        if dark:
            bg = "#1e1f22"
            panel = "#2b2d30"
            field = "#202124"
            fg = "#e8e8e8"
            muted = "#b8b8b8"
            select_bg = "#3f638f"
            button_bg = "#35383d"
        else:
            bg = "#f3f3f3"
            panel = "#f3f3f3"
            field = "#ffffff"
            fg = "#111111"
            muted = "#444444"
            select_bg = "#99c2ff"
            button_bg = "#e7e7e7"

        border = "#474b50" if dark else "#b7b7b7"
        progress_bar = "#c8c8c8" if dark else "#666666"

        self._theme_colors = {
            "bg": bg,
            "panel": panel,
            "field": field,
            "fg": fg,
            "muted": muted,
            "select_bg": select_bg,
            "button_bg": button_bg,
            "border": border,
            "progress_bar": progress_bar,
        }

        self.configure(bg=bg)
        paned = getattr(self, "main_paned", None)
        if paned is not None:
            try:
                paned.configure(bg=panel)
            except tk.TclError:
                pass
        style.configure(".", background=panel, foreground=fg)
        style.configure("TFrame", background=panel)
        style.configure("TLabel", background=panel, foreground=fg)
        style.configure("TLabelframe", background=panel, foreground=fg)
        style.configure("TLabelframe.Label", background=panel, foreground=fg)
        style.configure("TCheckbutton", background=panel, foreground=fg)
        style.configure("TButton", background=button_bg, foreground=fg)
        style.configure("TEntry", fieldbackground=field, foreground=fg)
        style.configure("TSpinbox", fieldbackground=field, foreground=fg)
        style.configure(
            "TLabelframe",
            background=panel,
            foreground=fg,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            relief="solid",
        )
        style.configure(
            "TLabelframe.Label",
            background=panel,
            foreground=fg,
        )
        style.configure(
            "Vertical.TScrollbar",
            background=button_bg,
            troughcolor=field,
            bordercolor=panel,
            arrowcolor=fg,
            lightcolor=button_bg,
            darkcolor=button_bg,
        )
        style.configure(
            "Ultra.Horizontal.TProgressbar",
            troughcolor=field,
            background=progress_bar,
            bordercolor=border,
            lightcolor=progress_bar,
            darkcolor=progress_bar,
            thickness=10,
        )
        style.map(
            "TButton",
            background=[("active", button_bg)],
            foreground=[("disabled", muted), ("!disabled", fg)],
        )
        style.map(
            "TCheckbutton",
            background=[("active", panel)],
            foreground=[("disabled", muted), ("!disabled", fg)],
        )

        for name in ("trace_log", "chat", "input_box"):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.configure(
                    bg=field,
                    fg=fg,
                    insertbackground=fg,
                    selectbackground=select_bg,
                    selectforeground=fg,
                    relief="flat",
                    borderwidth=0,
                    highlightthickness=0,
                )
                frame = getattr(widget, "frame", None)
                if frame is not None:
                    try:
                        frame.configure(
                            bg=panel,
                            relief="flat",
                            borderwidth=0,
                            highlightthickness=1,
                            highlightbackground=border,
                            highlightcolor=border,
                        )
                    except tk.TclError:
                        pass
                vbar = getattr(widget, "vbar", None)
                if vbar is not None:
                    try:
                        vbar.configure(
                            bg=button_bg,
                            troughcolor=field,
                            activebackground=select_bg,
                            relief="flat",
                            borderwidth=0,
                            highlightthickness=0,
                            width=12,
                        )
                    except tk.TclError:
                        pass

        trace_log = getattr(self, "trace_log", None)
        if trace_log is not None:
            separator_color = "#6a8bb5" if dark else "#4a6b8f"
            trace_log.tag_configure(
                "run_separator",
                foreground=separator_color,
                font=("Consolas", 9, "bold"),
            )

        # Пользовательские цвета применяются ПОСЛЕ темы, чтобы переключение
        # светлой/тёмной темы не сбрасывало выбранные оттенки.
        self._apply_text_colors()

    def _apply_text_colors(self) -> None:
        trace_log = getattr(self, "trace_log", None)
        if trace_log is not None:
            trace_log.tag_configure(
                "trace",
                foreground=self.log_text_color_var.get(),
                font=("Consolas", 9),
            )

        chat = getattr(self, "chat", None)
        if chat is not None:
            chat.tag_configure(
                "user",
                foreground=self.user_text_color_var.get(),
                font=("Segoe UI", 10, "bold"),
            )
            chat.tag_configure(
                "assistant",
                foreground=self.assistant_text_color_var.get(),
                font=("Segoe UI", 10),
            )

        self._refresh_color_swatches()
        self._apply_workspace_sidebar_theme()
        if hasattr(self, "workspace_list_frame"):
            self._render_workspace_sidebar()

    def _refresh_color_swatches(self) -> None:
        values = {
            "log": self.log_text_color_var.get(),
            "user": self.user_text_color_var.get(),
            "assistant": self.assistant_text_color_var.get(),
            "workspace": self.workspace_text_color_var.get(),
        }
        for key, color in values.items():
            swatch = self._color_swatches.get(key)
            if swatch is not None:
                try:
                    swatch.configure(bg=color, activebackground=color)
                except tk.TclError:
                    pass

    def _choose_text_color(self, target_var: tk.StringVar, title: str) -> None:
        _rgb, selected = colorchooser.askcolor(
            color=target_var.get(),
            parent=self,
            title=title,
        )
        if not selected:
            return
        target_var.set(selected.upper())
        self._apply_text_colors()
        self._save_ui_state(silent=True)

    def _record_initial_mtimes(self) -> None:
        try:
            self._server_mtime = Path("server.py").stat().st_mtime
        except FileNotFoundError:
            self._server_mtime = None
        try:
            self._ui_mtime = Path("ultra_ui.py").stat().st_mtime
        except FileNotFoundError:
            self._ui_mtime = None
        try:
            self._server_context_messages_mtime = Path(
                "server_context_messages.py"
            ).stat().st_mtime
        except FileNotFoundError:
            self._server_context_messages_mtime = None

    def _poll_code_changes(self) -> None:
        changed = []
        try:
            current = Path("server.py").stat().st_mtime
            if self._server_mtime is not None and current != self._server_mtime:
                changed.append("server.py")
        except FileNotFoundError:
            pass
        try:
            current = Path("server_context_messages.py").stat().st_mtime
            if (
                self._server_context_messages_mtime is not None
                and current != self._server_context_messages_mtime
            ):
                changed.append("server_context_messages.py")
        except FileNotFoundError:
            pass
        try:
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
            self._code_changed = True
            self._changed_files = changed
            self._show_code_change_warning()

        self.after(1000, self._poll_code_changes)

    def _show_code_change_warning(self) -> None:
        files = ", ".join(self._changed_files)
        warning = (
            "⚠ Исходный код runtime изменён.\n"
            "Текущий процесс использует старую версию.\n"
            "Требуется перезапуск приложения.\n\n"
            f"Изменён: {files}"
        )
        self._append_chat("СИСТЕМА", warning, "system")

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        self.main_paned = tk.PanedWindow(
            root,
            orient="horizontal",
            sashwidth=5,
            showhandle=False,
            bd=0,
            relief="flat",
            sashrelief="flat",
            bg="#2b2d30",
        )
        self.main_paned.pack(fill="both", expand=True)
        self.main_paned.bind(
            "<ButtonRelease-1>",
            self._on_sash_release,
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

        # Центральная системная зона.
        # Активный Workspace выбирается только через правую панель.
        ttk.Label(
            right_frame,
            text="НАСТРОЙКИ ИНСТРУМЕНТОВ LLM",
        ).pack(anchor="w", pady=(0, 6))

        # Жёсткие серверные ограничения.
        security = ttk.LabelFrame(
            right_frame,
            text="БЕЗОПАСНОСТЬ ЗАПУСКА — ограничения применяет server.py",
            padding=8,
        )
        security.pack(fill="x", pady=(0, 8))

        # Верхняя компактная строка.
        # Backup для UI считается обязательной системной защитой и
        # не занимает место отдельной пользовательской настройкой.
        ttk.Label(security, text="Лимит tools:").grid(
            row=0, column=0, sticky="w", padx=(0, 4), pady=(0, 2)
        )
        tool_limit_spin = ttk.Spinbox(
            security,
            from_=1,
            to=200,
            width=6,
            textvariable=self.tool_limit_var,
        )
        tool_limit_spin.grid(
            row=0, column=1, sticky="w", padx=(0, 14), pady=(0, 2)
        )

        verify_check = ttk.Checkbutton(
            security,
            text="VERIFY",
            variable=self.allow_verify_var,
        )
        verify_check.grid(
            row=0, column=2, sticky="w", padx=(0, 12), pady=(0, 2)
        )

        guard_p1_check = ttk.Checkbutton(
            security,
            text="GUARD P1",
            variable=self.allow_guard_p1_var,
        )
        guard_p1_check.grid(
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

        context_messages_button = ttk.Button(
            security,
            text="Контекстные сообщения",
            command=self._open_server_context_messages_editor,
        )
        context_messages_button.grid(
            row=1, column=4, sticky="w", padx=(12, 0), pady=2
        )

        # Компактные визуальные настройки вынесены в отдельный блок справа.
        # Цвет меняется кликом прямо по цветному квадрату.
        interface_frame = ttk.LabelFrame(
            security,
            text="ИНТЕРФЕЙС",
            padding=(8, 5),
        )
        interface_frame.grid(
            row=0, column=5, rowspan=4, sticky="nw", padx=(18, 0), pady=(0, 2)
        )

        theme_check = ttk.Checkbutton(
            interface_frame,
            text="Тёмная тема",
            variable=self.dark_theme_var,
            command=self._on_theme_changed,
        )
        theme_check.grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )

        compact_color_rows = [
            (
                1,
                "Лог действий",
                "log",
                self.log_text_color_var,
                "Цвет текста — лог действий",
            ),
            (
                2,
                "Пользователь",
                "user",
                self.user_text_color_var,
                "Цвет текста — сообщение пользователя в чате",
            ),
            (
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

        for row, label_text, key, color_var, dialog_title in compact_color_rows:
            ttk.Label(interface_frame, text=label_text).grid(
                row=row, column=0, sticky="w", pady=1
            )
            swatch = tk.Button(
                interface_frame,
                width=3,
                height=1,
                bg=color_var.get(),
                activebackground=color_var.get(),
                relief="sunken",
                borderwidth=1,
                cursor="hand2",
                command=lambda var=color_var, title=dialog_title: self._choose_text_color(
                    var, title
                ),
            )
            swatch.grid(row=row, column=1, sticky="w", padx=(8, 0), pady=1)
            self._color_swatches[key] = swatch

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

        # Компактные и одинаковые строки областей доступа.
        read_check = ttk.Checkbutton(
            security,
            text="",
            variable=self.allow_read_var,
        )
        read_check.grid(row=1, column=0, sticky="w", pady=2)

        ttk.Label(security, text="Чтение только в:").grid(
            row=1, column=1, sticky="w", padx=(2, 0), pady=2
        )
        read_scope_entry = ttk.Entry(
            security,
            textvariable=self.read_scope_var,
            width=38,
        )
        read_scope_entry.grid(
            row=1, column=2, sticky="w", padx=(6, 4), pady=2
        )
        bind_edit_shortcuts(read_scope_entry)
        read_scope_button = ttk.Button(
            security,
            text="...",
            width=3,
            command=lambda: self._choose_scope(self.read_scope_var),
        )
        read_scope_button.grid(
            row=1, column=3, sticky="w", pady=2
        )

        write_check = ttk.Checkbutton(
            security,
            text="",
            variable=self.allow_write_var,
        )
        write_check.grid(row=2, column=0, sticky="w", pady=2)

        ttk.Label(security, text="Запись только в:").grid(
            row=2, column=1, sticky="w", padx=(2, 0), pady=2
        )
        write_scope_entry = ttk.Entry(
            security,
            textvariable=self.write_scope_var,
            width=38,
        )
        write_scope_entry.grid(
            row=2, column=2, sticky="w", padx=(6, 4), pady=2
        )
        bind_edit_shortcuts(write_scope_entry)
        write_scope_button = ttk.Button(
            security,
            text="...",
            width=3,
            command=lambda: self._choose_scope(self.write_scope_var),
        )
        write_scope_button.grid(
            row=2, column=3, sticky="w", pady=2
        )

        # Удаление — отдельное разрешение, независимо от записи.
        delete_check = ttk.Checkbutton(
            security,
            text="",
            variable=self.allow_delete_var,
        )
        delete_check.grid(row=3, column=0, sticky="w", pady=2)

        ttk.Label(security, text="Удаление только в:").grid(
            row=3, column=1, sticky="w", padx=(2, 0), pady=2
        )
        delete_scope_entry = ttk.Entry(
            security,
            textvariable=self.delete_scope_var,
            width=38,
        )
        delete_scope_entry.grid(
            row=3, column=2, sticky="w", padx=(6, 4), pady=2
        )
        bind_edit_shortcuts(delete_scope_entry)
        delete_scope_button = ttk.Button(
            security,
            text="...",
            width=3,
            command=lambda: self._choose_scope(self.delete_scope_var),
        )
        delete_scope_button.grid(
            row=3, column=3, sticky="w", pady=2
        )


        # VERIFY остаётся явной настройкой.
        # Backup и служебные подсказки больше не занимают место в панели.

        self._security_widgets.extend(
            [
                read_check,
                write_check,
                delete_check,
                verify_check,
                guard_p1_check,
                global_context_button,
                context_messages_button,
                tool_limit_spin,
                read_scope_entry,
                read_scope_button,
                write_scope_entry,
                write_scope_button,
                delete_scope_entry,
                delete_scope_button,
            ]
        )

        ttk.Separator(right_frame).pack(fill="x", pady=8)

        chat_section = ttk.LabelFrame(
            right_frame,
            text="Чат",
            padding=4,
        )
        chat_section.pack(fill="both", expand=True, pady=(0, 8))

        self.chat = scrolledtext.ScrolledText(
            chat_section,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 10),
        )
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_configure(
            "user",
            foreground=self.user_text_color_var.get(),
            font=("Segoe UI", 10, "bold"),
        )
        self.chat.tag_configure(
            "assistant",
            foreground=self.assistant_text_color_var.get(),
            font=("Segoe UI", 10),
        )
        self.chat.tag_configure("system", font=("Segoe UI", 9, "italic"))

        for sequence in ("<Control-c>", "<Control-C>"):
            self.chat.bind(
                sequence,
                lambda e: (e.widget.event_generate("<<Copy>>"), "break")[1],
            )

        status_frame = ttk.Frame(right_frame)
        status_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(status_frame, text="Статус:").pack(side="left")
        ttk.Label(status_frame, textvariable=self.status_var).pack(
            side="left", padx=(6, 10)
        )
        self.progress = ttk.Progressbar(
            status_frame,
            mode="indeterminate",
            length=180,
            style="Ultra.Horizontal.TProgressbar",
        )
        self.progress.pack(side="right")

        message_section = ttk.LabelFrame(
            right_frame,
            text="Сообщение",
            padding=4,
        )
        message_section.pack(fill="x", pady=(0, 8))

        self.input_box = scrolledtext.ScrolledText(
            message_section,
            wrap="word",
            height=7,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.input_box.pack(fill="x")
        bind_edit_shortcuts(self.input_box)
        self.input_box.bind("<Control-Return>", self._send_from_hotkey)

        buttons = ttk.Frame(right_frame)
        buttons.pack(fill="x")
        self.send_button = ttk.Button(
            buttons,
            text="Отправить",
            command=self._send,
        )
        self.send_button.pack(side="left")
        ttk.Label(buttons, text="Ctrl+Enter — отправить").pack(
            side="left", padx=(10, 0)
        )

        self._append_chat(
            "СИСТЕМА",
            (
                "Интерфейс готов. По умолчанию чтение, VERIFY и GUARD P1 "
                "разрешены, запись и удаление ЗАПРЕЩЕНЫ, автобэкап включён. "
                "Лимит tools = 20. Серверные галочки — это реальные ограничения, "
                "а не только текст в промпте."
            ),
            "system",
        )
        self.input_box.focus_set()

    def _record_context_storage_mtime(self) -> None:
        try:
            self._context_storage_mtime = Path(
                "context_storage.py"
            ).stat().st_mtime
        except FileNotFoundError:
            self._context_storage_mtime = None

    def _on_theme_changed(self) -> None:
        self._apply_theme()
        self._save_ui_state(silent=True)

    def _window_mode(self) -> str:
        try:
            return "zoomed" if self.state() == "zoomed" else "normal"
        except tk.TclError:
            return "normal"

    def _capture_panel_ratios(self) -> list[float]:
        paned = getattr(self, "main_paned", None)
        if paned is None:
            return []
        try:
            width = int(paned.winfo_width())
            if width < 800:
                return []
            left_x = int(paned.sash_coord(0)[0])
            right_x = int(paned.sash_coord(1)[0])
        except (tk.TclError, IndexError):
            return []

        if not (0 < left_x < right_x < width):
            return []

        return [
            round(left_x / width, 6),
            round(right_x / width, 6),
        ]

    def _store_current_panel_ratios(self) -> None:
        ratios = self._capture_panel_ratios()
        if len(ratios) != 2:
            return

        mode = self._window_mode()
        panel_ratios = self._ui_state.setdefault(
            "panel_ratios",
            {
                "normal": [0.24, 0.80],
                "zoomed": [0.24, 0.80],
            },
        )
        panel_ratios[mode] = ratios

    def _apply_panel_ratios(self, mode: str | None = None) -> None:
        paned = getattr(self, "main_paned", None)
        if paned is None:
            return

        if mode not in {"normal", "zoomed"}:
            mode = self._window_mode()

        try:
            self.update_idletasks()
            width = int(paned.winfo_width())
            if width < 900:
                return

            all_ratios = self._ui_state.get("panel_ratios") or {}
            ratios = all_ratios.get(mode) or [0.24, 0.80]
            left_ratio = float(ratios[0])
            right_ratio = float(ratios[1])

            # Минимальные размеры панелей:
            # left >= 240, center >= 600, right >= 240.
            left_x = int(round(width * left_ratio))
            right_x = int(round(width * right_ratio))

            left_x = max(240, min(left_x, width - 840))
            right_x = max(left_x + 600, right_x)
            right_x = min(right_x, width - 240)

            paned.sash_place(0, left_x, 0)
            paned.sash_place(1, right_x, 0)
        except (tk.TclError, ValueError, TypeError, IndexError):
            pass

    def _restore_window_and_layout(self) -> None:
        desired = self._ui_state.get("window_state")
        if desired not in {"normal", "zoomed"}:
            desired = "normal"

        self._last_window_mode = "normal"
        self.update_idletasks()

        if desired == "zoomed":
            try:
                self.state("zoomed")
                self._last_window_mode = "zoomed"
            except tk.TclError:
                self._last_window_mode = "normal"

        self.after(
            100,
            lambda: self._apply_panel_ratios(self._window_mode()),
        )

    def _on_sash_release(self, _event=None) -> None:
        self.after(30, self._save_ui_state)

    def _on_root_configure(self, event) -> None:
        if event.widget is not self:
            return

        if self._layout_sync_after is not None:
            try:
                self.after_cancel(self._layout_sync_after)
            except tk.TclError:
                pass

        self._layout_sync_after = self.after(
            140,
            self._sync_window_layout,
        )

    def _sync_window_layout(self) -> None:
        self._layout_sync_after = None
        mode = self._window_mode()
        width = int(self.winfo_width())

        mode_changed = mode != self._last_window_mode
        width_changed = (
            self._last_root_width is not None
            and abs(width - self._last_root_width) > 2
        )

        self._last_window_mode = mode
        self._last_root_width = width
        self._ui_state["window_state"] = mode

        if mode == "normal":
            geometry = self.geometry()
            if geometry:
                self._ui_state["normal_geometry"] = geometry

        # При maximize/restore или resize пересчитываем sash из ПРОПОРЦИЙ
        # текущего canvas, а не переносим старые абсолютные пиксели.
        if mode_changed or width_changed:
            self._apply_panel_ratios(mode)

        try:
            save_ui_state(self._ui_state)
        except Exception:
            pass

    def _reset_panel_layout(self) -> None:
        self._ui_state["panel_ratios"] = {
            "normal": [0.24, 0.80],
            "zoomed": [0.24, 0.80],
        }
        self._apply_panel_ratios(self._window_mode())
        self._save_ui_state(silent=True)

    def _save_ui_state(self, _event=None, *, silent: bool = True) -> None:
        try:
            mode = self._window_mode()
            self._store_current_panel_ratios()

            if mode == "normal":
                geometry = self.geometry()
                if geometry:
                    self._ui_state["normal_geometry"] = geometry

            self._ui_state["window_state"] = mode
            self._ui_state["dark_theme"] = self.dark_theme_var.get()
            self._ui_state["colors"] = {
                "log": self.log_text_color_var.get(),
                "user": self.user_text_color_var.get(),
                "assistant": self.assistant_text_color_var.get(),
                "workspace": self.workspace_text_color_var.get(),
            }
            self._ui_state["workspaces"] = list(self._workspace_registry)
            self._ui_state["active_workspace_id"] = self.current_workspace_id
            save_ui_state(self._ui_state)
        except Exception as exc:
            if not silent:
                messagebox.showerror(
                    APP_TITLE,
                    f"Не удалось сохранить UI state.\n\n"
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
        host.columnconfigure(0, weight=1)
        host.columnconfigure(1, weight=0)
        host.rowconfigure(0, weight=1)

        self.workspace_canvas = tk.Canvas(
            host,
            highlightthickness=0,
            bd=0,
            width=1,
        )
        scroll = ttk.Scrollbar(
            host,
            orient="vertical",
            command=self.workspace_canvas.yview,
        )
        self.workspace_canvas.configure(yscrollcommand=scroll.set)

        # GRID здесь намеренно: scrollbar получает собственную колонку
        # и больше не может быть вытеснен Canvas при сужении правой панели.
        self.workspace_canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        scroll.grid(
            row=0,
            column=1,
            sticky="ns",
        )

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
                    f"Не удалось загрузить Workspace/Chats.\n\n"
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
                f"Не удалось создать / подключить Workspace.\n\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _choose_workspace(self) -> None:
        # Совместимость для внутренних/старых вызовов.
        # В UI создание и подключение Workspace выполняется справа.
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
                f"Не удалось создать чат.\n\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _rename_workspace_ui(self, workspace: Path) -> None:
        if self.running:
            return

        try:
            workspace = workspace.resolve()
            info = ensure_workspace_storage(workspace)
            runtime = load_workspace_runtime_settings(
                info["workspace_id"]
            )
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось открыть настройки Workspace.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        window = tk.Toplevel(self)
        window.title(
            f"Настройки Workspace — {info['display_name']}"
        )
        window.geometry("820x540")
        window.minsize(720, 500)
        window.transient(self)
        window.grab_set()

        body = ttk.Frame(window, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        ttk.Label(
            body,
            text="НАСТРОЙКИ WORKSPACE",
            font=("Segoe UI", 11, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(0, 14),
        )

        ttk.Label(body, text="Название Workspace:").grid(
            row=1,
            column=0,
            sticky="w",
            pady=4,
        )
        name_var = tk.StringVar(value=info["display_name"])
        name_entry = ttk.Entry(
            body,
            textvariable=name_var,
            width=52,
        )
        name_entry.grid(
            row=1,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=(10, 0),
            pady=4,
        )
        bind_edit_shortcuts(name_entry)

        ttk.Separator(body).grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(12, 12),
        )

        ttk.Label(
            body,
            text="ХРАНИЛИЩЕ",
            font=("Segoe UI", 10, "bold"),
        ).grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(0, 8),
        )

        backup_var = tk.StringVar(value=runtime["backup_dir"])
        log_var = tk.StringVar(value=runtime["log_dir"])

        ttk.Label(body, text="Защищённые бэкапы:").grid(
            row=4,
            column=0,
            sticky="w",
            pady=4,
        )
        backup_entry = ttk.Entry(
            body,
            textvariable=backup_var,
        )
        backup_entry.grid(
            row=4,
            column=1,
            sticky="ew",
            padx=(10, 6),
            pady=4,
        )
        bind_edit_shortcuts(backup_entry)

        def choose_backup() -> None:
            current = Path(backup_var.get()).expanduser()
            initial = current if current.is_dir() else Path.home()
            selected = filedialog.askdirectory(
                parent=window,
                initialdir=str(initial),
                title="Папка защищённых бэкапов Workspace",
            )
            if selected:
                backup_var.set(selected)

        ttk.Button(
            body,
            text="...",
            width=3,
            command=choose_backup,
        ).grid(row=4, column=2, sticky="w", pady=4)
        ttk.Button(
            body,
            text="По умолчанию",
            command=lambda: backup_var.set(
                runtime["default_backup_dir"]
            ),
        ).grid(
            row=4,
            column=3,
            sticky="w",
            padx=(6, 0),
            pady=4,
        )

        ttk.Label(body, text="Логи RUN:").grid(
            row=5,
            column=0,
            sticky="w",
            pady=4,
        )
        log_entry = ttk.Entry(
            body,
            textvariable=log_var,
        )
        log_entry.grid(
            row=5,
            column=1,
            sticky="ew",
            padx=(10, 6),
            pady=4,
        )
        bind_edit_shortcuts(log_entry)

        def choose_logs() -> None:
            current = Path(log_var.get()).expanduser()
            initial = current if current.is_dir() else Path.home()
            selected = filedialog.askdirectory(
                parent=window,
                initialdir=str(initial),
                title="Папка логов RUN Workspace",
            )
            if selected:
                log_var.set(selected)

        ttk.Button(
            body,
            text="...",
            width=3,
            command=choose_logs,
        ).grid(row=5, column=2, sticky="w", pady=4)
        ttk.Button(
            body,
            text="По умолчанию",
            command=lambda: log_var.set(
                runtime["default_log_dir"]
            ),
        ).grid(
            row=5,
            column=3,
            sticky="w",
            padx=(6, 0),
            pady=4,
        )

        ttk.Separator(body).grid(
            row=6,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(14, 12),
        )

        ttk.Label(
            body,
            text="О БЭКАПАХ",
            font=("Segoe UI", 10, "bold"),
        ).grid(
            row=7,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(0, 6),
        )

        explanation = (
            "Перед каждым RUN Ultra создаёт защищённый снимок этого Workspace. "
            "В снимок целиком входит переносимое состояние .ultra: "
            "PROJECT CONTEXT, чаты и RAW HISTORY. Исходные версии обычных "
            "файлов проекта сохраняются непосредственно перед их изменением "
            "или удалением.\n\n"
            "Бэкап принадлежит Workspace, а chat_id записывается в manifest "
            "только как источник конкретного RUN. По умолчанию backup и "
            "RUN-логи лежат локально вне проекта. Здесь можно выбрать другие "
            "локальные каталоги именно для этого Workspace. Путь внутри самого "
            "Workspace в текущей версии запрещён."
        )
        ttk.Label(
            body,
            text=explanation,
            wraplength=750,
            justify="left",
        ).grid(
            row=8,
            column=0,
            columnspan=4,
            sticky="nw",
        )

        buttons = ttk.Frame(body)
        buttons.grid(
            row=9,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(20, 0),
        )

        def save_settings() -> None:
            try:
                clean_name = name_var.get().strip()
                if not clean_name:
                    raise ValueError(
                        "Название Workspace не может быть пустым."
                    )
                if len(clean_name) > 200:
                    raise ValueError(
                        "Название Workspace слишком длинное."
                    )

                backup_text = backup_var.get().strip().strip('"')
                log_text = log_var.get().strip().strip('"')
                if not backup_text or not log_text:
                    raise ValueError(
                        "Пути backup и log не могут быть пустыми."
                    )

                backup_path = Path(backup_text).expanduser()
                log_path = Path(log_text).expanduser()

                for label, path in (
                    ("Бэкапы", backup_path),
                    ("Логи", log_path),
                ):
                    if not path.is_absolute():
                        raise ValueError(
                            f"{label}: путь должен быть абсолютным."
                        )
                    resolved = path.resolve()
                    if (
                        resolved == workspace
                        or workspace in resolved.parents
                    ):
                        raise ValueError(
                            f"{label}: каталог должен находиться "
                            "вне Workspace."
                        )

                rename_workspace(workspace, clean_name)
                save_workspace_runtime_settings(
                    info["workspace_id"],
                    backup_dir=backup_path,
                    log_dir=log_path,
                )

                self._render_workspace_sidebar()
                self._save_ui_state(silent=True)
                window.destroy()
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    f"Не удалось сохранить настройки Workspace.\n\n"
                    f"{type(exc).__name__}: {exc}",
                    parent=window,
                )

        ttk.Button(
            buttons,
            text="Сохранить",
            command=save_settings,
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Отмена",
            command=window.destroy,
        ).pack(side="right")

        name_entry.focus_set()
        name_entry.selection_range(0, "end")

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
                f"Не удалось переименовать чат.\n\n"
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
            "Убрать Workspace только из списка приложения?\n\n"
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

    def _open_global_ultra_context_editor(self) -> None:
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

    def _open_server_context_messages_editor(self) -> None:
        try:
            storage_path = get_server_context_messages_path("ultra")
            initial_payload = list_server_context_event_records("ultra")
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                "Не удалось открыть Контекстные сообщения сервера.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        window = tk.Toplevel(self)
        window.title("КОНТЕКСТНЫЕ СООБЩЕНИЯ СЕРВЕРА")
        window.geometry("1120x760")
        window.minsize(820, 560)
        window.transient(self)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = ttk.Frame(window, padding=(10, 10, 10, 0))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            header,
            text=(
                "Редактор LLM-facing текста серверных событий. "
                "Записи не меняют permissions, GUARD, Verification Gate "
                "или другие решения server.py."
            ),
            wraplength=1040,
            justify="left",
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=f"Локальное хранилище: {storage_path}",
        ).pack(anchor="w", pady=(4, 0))
        diagnostic_var = tk.StringVar()
        tk.Label(
            header,
            textvariable=diagnostic_var,
            fg="#9A3030",
            bg="#E7E7E7",
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(4, 0))

        body = ttk.PanedWindow(window, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        left = ttk.Frame(body, padding=(0, 0, 8, 0))
        right = ttk.Frame(body, padding=(8, 0, 0, 0))
        body.add(left, weight=1)
        body.add(right, weight=3)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(8, weight=3)
        right.rowconfigure(10, weight=2)

        ttk.Label(left, text="EVENT ID / STATUS").pack(
            anchor="w", pady=(0, 5)
        )
        event_list = tk.Listbox(
            left,
            exportselection=False,
            bg="#E5E6E8",
            fg="#252525",
            selectbackground="#B8C7D9",
            selectforeground="#111111",
            activestyle="none",
        )
        event_list.pack(fill="both", expand=True)

        event_id_var = tk.StringVar()
        status_var = tk.StringVar()
        source_var = tk.StringVar()
        built_in_description_var = tk.StringVar()

        ttk.Label(right, text="Event ID").grid(
            row=0, column=0, sticky="w"
        )
        event_id_entry = ttk.Entry(right, textvariable=event_id_var)
        event_id_entry.grid(
            row=1, column=0, sticky="ew", pady=(3, 7)
        )
        bind_edit_shortcuts(event_id_entry)

        metadata = ttk.Frame(right)
        metadata.grid(row=2, column=0, sticky="ew", pady=(0, 7))
        ttk.Label(metadata, text="Статус:").pack(side="left")
        ttk.Label(metadata, textvariable=status_var).pack(
            side="left", padx=(5, 18)
        )
        ttk.Label(metadata, text="Источник:").pack(side="left")
        ttk.Label(metadata, textvariable=source_var).pack(
            side="left", padx=(5, 0)
        )

        ttk.Label(right, text="Встроенное описание").grid(
            row=3, column=0, sticky="w"
        )
        tk.Label(
            right,
            textvariable=built_in_description_var,
            bg="#E5E6E8",
            fg="#252525",
            anchor="w",
            justify="left",
            wraplength=760,
            padx=6,
            pady=4,
        ).grid(row=4, column=0, sticky="ew", pady=(3, 7))

        ttk.Label(right, text="Описание override / DRAFT").grid(
            row=5, column=0, sticky="w"
        )
        description_editor = scrolledtext.ScrolledText(
            right,
            wrap="word",
            height=4,
            undo=True,
            font=("Segoe UI", 10),
            bg="#F0F0F0",
            fg="#202020",
            insertbackground="#202020",
        )
        description_editor.grid(
            row=6, column=0, sticky="ew", pady=(3, 7)
        )
        bind_edit_shortcuts(description_editor)

        ttk.Label(right, text="Редактируемый текст сообщения").grid(
            row=7, column=0, sticky="w"
        )
        template_editor = scrolledtext.ScrolledText(
            right,
            wrap="word",
            undo=True,
            font=("Segoe UI", 10),
            bg="#F0F0F0",
            fg="#202020",
            insertbackground="#202020",
        )
        template_editor.grid(
            row=8, column=0, sticky="nsew", pady=(3, 7)
        )
        bind_edit_shortcuts(template_editor)

        ttk.Label(right, text="Встроенный default (только чтение)").grid(
            row=9, column=0, sticky="w"
        )
        default_editor = scrolledtext.ScrolledText(
            right,
            wrap="word",
            height=6,
            state="disabled",
            font=("Segoe UI", 9),
            bg="#E5E6E8",
            fg="#252525",
        )
        default_editor.grid(
            row=10, column=0, sticky="nsew", pady=(3, 0)
        )

        records = {
            item["event_id"]: item
            for item in initial_payload["records"]
        }
        event_ids_by_index: list[str] = []
        selected_event_id: str | None = None

        def set_readonly_text(widget, text: str) -> None:
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            if text:
                widget.insert("1.0", text)
            widget.configure(state="disabled")

        def clear_fields() -> None:
            event_id_var.set("")
            status_var.set("DRAFT — не сохранён")
            source_var.set("Новая пользовательская запись")
            built_in_description_var.set("—")
            description_editor.delete("1.0", "end")
            template_editor.delete("1.0", "end")
            set_readonly_text(default_editor, "")

        def configure_record_action(record: dict | None) -> None:
            if record is None:
                record_action_button.configure(
                    text="Удалить DRAFT", state="disabled"
                )
            elif record["is_active"] and record["has_override"]:
                record_action_button.configure(
                    text="Сбросить override", state="normal"
                )
            elif not record["is_active"]:
                record_action_button.configure(
                    text="Удалить DRAFT", state="normal"
                )
            else:
                record_action_button.configure(
                    text="Нет override", state="disabled"
                )

        def refresh_list(select_event_id: str | None = None) -> None:
            nonlocal records, event_ids_by_index
            payload = list_server_context_event_records("ultra")
            records = {
                item["event_id"]: item
                for item in payload["records"]
            }
            diagnostics = payload.get("diagnostics") or []
            diagnostic_var.set(
                "ОШИБКА USER JSON: " + diagnostics[0]["message"]
                if diagnostics
                else ""
            )
            event_list.delete(0, "end")
            event_ids_by_index = []
            selected_index = None
            for index, event_id in enumerate(sorted(records)):
                record = records[event_id]
                event_ids_by_index.append(event_id)
                event_list.insert(
                    "end", f"● {record['status']}  {event_id}"
                )
                color = {
                    "ACTIVE": "#2F7D4A",
                    "ACTIVE + OVERRIDE": "#2D5F9A",
                    "DRAFT": "#4A4A4A",
                }[record["status"]]
                event_list.itemconfig(index, foreground=color)
                if event_id == select_event_id:
                    selected_index = index
            if selected_index is not None:
                event_list.selection_set(selected_index)
                event_list.see(selected_index)
                load_selected()

        def load_selected(_event=None) -> None:
            nonlocal selected_event_id
            selection = event_list.curselection()
            if not selection:
                return
            event_id = event_ids_by_index[selection[0]]
            record = records[event_id]
            selected_event_id = event_id
            event_id_entry.configure(state="normal")
            clear_fields()
            event_id_var.set(event_id)
            status_var.set(record["status"])
            source_var.set(record["source"])
            built_in_description_var.set(
                record.get("built_in_description") or "—"
            )
            description_editor.insert("1.0", record["description"])
            template_editor.insert("1.0", record["template"])
            set_readonly_text(
                default_editor, record.get("default_template") or ""
            )
            event_id_entry.configure(state="readonly")
            configure_record_action(record)

        def add_record() -> None:
            nonlocal selected_event_id
            selected_event_id = None
            event_list.selection_clear(0, "end")
            event_id_entry.configure(state="normal")
            clear_fields()
            configure_record_action(None)
            event_id_entry.focus_set()

        def save_record() -> None:
            nonlocal selected_event_id
            try:
                event_id = validate_event_id(event_id_var.get())
                if selected_event_id is None and event_id in records:
                    raise ValueError(
                        f"Запись {event_id!r} уже существует. "
                        "Выберите её в списке для изменения."
                    )
                if (
                    selected_event_id is not None
                    and event_id != selected_event_id
                ):
                    raise ValueError(
                        "event_id существующей записи нельзя переименовать."
                    )
                upsert_server_context_message(
                    event_id,
                    description_editor.get("1.0", "end-1c"),
                    template_editor.get("1.0", "end-1c"),
                    "ultra",
                )
                selected_event_id = event_id
                refresh_list(event_id)
                messagebox.showinfo(
                    APP_TITLE,
                    "Контекстное сообщение сохранено. "
                    "Следующий RUN использует новую версию без restart.",
                    parent=window,
                )
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    "Не удалось сохранить запись.\n\n"
                    f"{type(exc).__name__}: {exc}",
                    parent=window,
                )

        def remove_user_record() -> None:
            nonlocal selected_event_id
            if selected_event_id is None:
                messagebox.showinfo(
                    APP_TITLE,
                    "Сначала выберите запись для удаления.",
                    parent=window,
                )
                return
            event_id = selected_event_id
            record = records[event_id]
            if record["is_active"] and not record["has_override"]:
                return
            action = (
                "Сбросить пользовательский override"
                if record["is_active"]
                else "Удалить DRAFT"
            )
            if not messagebox.askyesno(
                APP_TITLE,
                f"{action} для {event_id!r}?\n\n"
                + (
                    "Runtime-событие останется ACTIVE и вернётся к "
                    "встроенному default."
                    if record["is_active"]
                    else "DRAFT полностью исчезнет из списка."
                ),
                parent=window,
            ):
                return
            try:
                delete_server_context_message(event_id, "ultra")
                if record["is_active"]:
                    refresh_list(event_id)
                else:
                    selected_event_id = None
                    event_id_entry.configure(state="normal")
                    clear_fields()
                    configure_record_action(None)
                    refresh_list()
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    "Не удалось изменить пользовательскую запись.\n\n"
                    f"{type(exc).__name__}: {exc}",
                    parent=window,
                )

        event_list.bind("<<ListboxSelect>>", load_selected)

        buttons = ttk.Frame(window)
        buttons.grid(
            row=2, column=0, sticky="ew", padx=10, pady=(0, 10)
        )
        ttk.Button(buttons, text="Добавить", command=add_record).pack(
            side="left"
        )
        ttk.Button(buttons, text="Сохранить", command=save_record).pack(
            side="left", padx=(8, 0)
        )
        record_action_button = ttk.Button(
            buttons,
            text="Удалить DRAFT",
            command=remove_user_record,
        )
        record_action_button.pack(side="left", padx=(8, 0))
        ttk.Button(
            buttons, text="Закрыть", command=window.destroy
        ).pack(side="right")

        window._server_context_messages_widgets = {
            "event_list": event_list,
            "status_var": status_var,
            "source_var": source_var,
            "built_in_description_var": built_in_description_var,
            "template_editor": template_editor,
            "default_editor": default_editor,
            "action_button": record_action_button,
            "button_bar": buttons,
        }

        refresh_list()
        if records:
            event_list.selection_set(0)
            load_selected()
        else:
            add_record()

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
                f"Не удалось открыть PROJECT CONTEXT.\n\n"
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
                    f"Не удалось сохранить PROJECT CONTEXT.\n\n"
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
        workspace_text = self.workspace_var.get().strip().strip('"')
        workspace = Path(workspace_text)
        if not workspace.is_absolute() or not workspace.is_dir():
            messagebox.showerror(
                APP_TITLE,
                "Сначала выбери существующий workspace.",
            )
            return

        selected = filedialog.askdirectory(
            initialdir=str(workspace),
            title="Выбрать разрешённую папку внутри workspace",
        )
        if not selected:
            return

        root = workspace.resolve()
        chosen = Path(selected).resolve()
        if chosen != root and root not in chosen.parents:
            messagebox.showerror(
                APP_TITLE,
                "Разрешённая папка должна находиться внутри workspace.",
            )
            return

        relative = "." if chosen == root else chosen.relative_to(root).as_posix()
        target_var.set(relative)

    def _normalize_scope_for_ui(
        self,
        workspace: Path,
        value: str,
        label: str,
        enabled: bool,
    ) -> str:
        text = value.strip().replace("\\", "/")
        if not text:
            if enabled:
                raise ValueError(f"Не задана область: {label}.")
            return "."

        candidate = Path(text)
        if candidate.is_absolute() or candidate.drive or candidate.anchor:
            raise ValueError(f"{label}: используй относительный путь внутри workspace.")
        if ".." in candidate.parts:
            raise ValueError(f"{label}: '..' запрещён.")

        resolved = (workspace / candidate).resolve()
        root = workspace.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError(f"{label}: путь выходит за workspace.")
        if enabled and not resolved.is_dir():
            raise ValueError(f"{label}: папка не найдена: {text}")
        return candidate.as_posix() or "."

    def _append_chat(self, author: str, text: str, tag: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{author}:\n", tag)
        self.chat.insert("end", f"{text.strip()}\n\n", tag)
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def _append_trace(self, line: str) -> None:
        self.trace_log.configure(state="normal")
        self.trace_log.insert("end", f"{line}\n", "trace")
        self.trace_log.see("end")
        self.trace_log.configure(state="disabled")

    def _format_event(self, event: dict) -> str:
        event_type = event.get("event")
        run_id = event.get("run_id", "")
        timestamp = event.get("timestamp")
        time_str = (
            time.strftime("%H:%M:%S", time.localtime(timestamp))
            if timestamp
            else "--:--:--"
        )

        if event_type == "run_started":
            task_preview = event.get("task_preview", "")
            perms = event.get("permissions", {})
            return (
                f"[{time_str}] RUN START | {run_id} | "
                f"R={perms.get('allow_read')}:{perms.get('read_scope')} | "
                f"W={perms.get('allow_write')}:{perms.get('write_scope')} | "
                f"D={perms.get('allow_delete')}:{perms.get('delete_scope')} | "
                f"V={perms.get('allow_verify')} | "
                f"G1={perms.get('allow_guard_p1')} | "
                f"LIMIT={perms.get('tool_limit')} | "
                f"BACKUP={perms.get('auto_backup')} | {task_preview[:40]}"
            )

        if event_type == "global_agent_context_loaded":
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

        if event_type == "chat_context_loaded":
            return (
                f"[{time_str}] CHAT CONTEXT | "
                f"{event.get('chat_id')} | "
                f"messages={event.get('messages')} | "
                f"chars={event.get('chars')}"
            )

        if event_type == "backup_started":
            return f"[{time_str}] BACKUP START | {event.get('backup_path')}"

        if event_type == "backup_finished":
            return (
                f"[{time_str}] BACKUP OK | core={event.get('core_files')} | "
                f"{event.get('backup_path')}"
            )

        if event_type == "permission_denied":
            seq = event.get("tool_sequence")
            func = event.get("function")
            args = event.get("arguments", {})
            err = event.get("error", {})
            return (
                f"[{time_str}] DENIED TOOL #{seq} {func}({args}) | "
                f"{err.get('message', '')}"
            )

        if event_type == "api_request":
            return f"[{time_str}] API #{event.get('api_request_number')}"

        if event_type == "api_response":
            num = event.get("api_request_number")
            status = event.get("http_status")
            reason = event.get("finish_reason")
            duration = event.get("duration")
            dur_str = f" | {duration:.2f} s" if isinstance(duration, (int, float)) else ""
            reason_str = f" | {reason}" if reason else ""
            return f"[{time_str}] API #{num} -> {status}{reason_str}{dur_str}"

        if event_type == "tool_started":
            seq = event.get("tool_sequence")
            func = event.get("function")
            args = event.get("arguments", {})
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            return f"[{time_str}] TOOL #{seq} {func}({args_str})"

        if event_type == "tool_finished":
            seq = event.get("tool_sequence")
            func = event.get("function")
            duration = event.get("duration")
            dur_str = f" | {duration:.2f} s" if isinstance(duration, (int, float)) else ""
            return f"[{time_str}] TOOL #{seq} {func} -> OK{dur_str}"

        if event_type == "tool_error":
            seq = event.get("tool_sequence")
            func = event.get("function")
            error = event.get("error", {})
            return (
                f"[{time_str}] TOOL #{seq} {func} -> ERROR "
                f"({error.get('type', '')}): {error.get('message', '')}"
            )

        if event_type == "guard_intervention":
            kind = event.get("kind")
            if kind == "repeated_tool":
                return (
                    f"[{time_str}] GUARD P1 | SUPERVISOR CHECK | "
                    f"REPEAT {event.get('function')} | "
                    f"budget={event.get('tool_budget_used')}/"
                    f"{event.get('tool_budget_limit')}"
                )
            if kind == "possible_duplicate_create":
                return (
                    f"[{time_str}] GUARD P1 | SUPERVISOR CHECK | CREATE | "
                    f"{event.get('requested_path')} ~ "
                    f"{event.get('similar_path')} | "
                    f"score={event.get('score')}"
                )
            return (
                f"[{time_str}] GUARD P1 | SUPERVISOR CHECK | {kind}"
            )

        if event_type == "guard_override":
            return (
                f"[{time_str}] GUARD P1 | CREATE CONFIRMED | "
                f"{event.get('requested_path')}"
            )

        if event_type == "guard_blocked":
            return (
                f"[{time_str}] GUARD P1 | BLOCKED | "
                f"{event.get('kind')} | "
                f"{event.get('function', '')}"
            )

        if event_type == "verification_required":
            attempt = event.get("attempt")
            missing = event.get("missing") or []
            tools = []
            for item in missing:
                if isinstance(item, dict):
                    tool = item.get("tool")
                    if tool:
                        tools.append(str(tool))
            tools_text = ", ".join(tools) if tools else "unknown"
            return (
                f"[{time_str}] VERIFY GATE | SUCCESS BLOCKED | "
                f"attempt={attempt} | missing={tools_text}"
            )

        if event_type == "verification_passed":
            state = event.get("verification_state") or {}
            return (
                f"[{time_str}] VERIFY GATE -> PASSED | "
                f"revision={state.get('write_revision')}"
            )

        if event_type == "run_finished":
            duration = event.get("duration")
            dur_str = f" | {duration:.2f} s" if isinstance(duration, (int, float)) else ""
            return (
                f"[{time_str}] {event.get('status')} | API: {event.get('api_requests')} | "
                f"TOOLS: {event.get('tool_calls')}{dur_str} | RUN {run_id}"
            )

        if event_type == "run_failed":
            duration = event.get("duration")
            dur_str = f" | {duration:.2f} s" if isinstance(duration, (int, float)) else ""
            trace_path = event.get("trace_path")
            trace_str = f" | trace: {trace_path}" if trace_path else ""
            return (
                f"[{time_str}] ERROR ({event.get('reason')}){dur_str} | "
                f"API: {event.get('api_requests')} | TOOLS: {event.get('tool_calls')}"
                f"{trace_str} | RUN {run_id}"
            )

        return f"[{time_str}] {event_type}"

    def _send_from_hotkey(self, _event: tk.Event) -> str:
        self._send()
        return "break"

    def _send(self) -> None:
        if self.running:
            messagebox.showinfo(APP_TITLE, "Ultra уже выполняет задачу.")
            return

        workspace_text = self.workspace_var.get().strip().strip('"')
        task = self.input_box.get("1.0", "end").strip()
        if not task:
            messagebox.showwarning(APP_TITLE, "Введи сообщение для Ultra.")
            return

        workspace = Path(workspace_text)
        if not workspace.is_absolute() or not workspace.is_dir():
            messagebox.showerror(
                APP_TITLE,
                "Workspace должен быть существующей абсолютной папкой.",
            )
            return

        try:
            read_scope = self._normalize_scope_for_ui(
                workspace,
                self.read_scope_var.get(),
                "Область чтения",
                self.allow_read_var.get(),
            )
            write_scope = self._normalize_scope_for_ui(
                workspace,
                self.write_scope_var.get(),
                "Область записи",
                self.allow_write_var.get(),
            )
            delete_scope = self._normalize_scope_for_ui(
                workspace,
                self.delete_scope_var.get(),
                "Область удаления",
                self.allow_delete_var.get(),
            )
            try:
                tool_limit = int(self.tool_limit_var.get().strip())
            except ValueError as exc:
                raise ValueError("Лимит tools должен быть целым числом.") from exc
            if not 1 <= tool_limit <= 200:
                raise ValueError("Лимит tools должен быть от 1 до 200.")
        except ValueError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        permissions = {
            "allow_read": self.allow_read_var.get(),
            "allow_write": self.allow_write_var.get(),
            "allow_delete": self.allow_delete_var.get(),
            "allow_verify": self.allow_verify_var.get(),
            "allow_guard_p1": self.allow_guard_p1_var.get(),
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
                "Не удалось сохранить RAW MESSAGE до отправки.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        self._append_chat("ТЫ", task, "user")
        self._append_chat(
            "СИСТЕМА",
            (
                "Серверные ограничения этого запуска: "
                f"READ={'ON' if permissions['allow_read'] else 'OFF'} "
                f"[{read_scope}], "
                f"WRITE={'ON' if permissions['allow_write'] else 'OFF'} "
                f"[{write_scope}], "
                f"DELETE={'ON' if permissions['allow_delete'] else 'OFF'} "
                f"[{delete_scope}], "
                f"VERIFY={'ON' if permissions['allow_verify'] else 'OFF'}, "
                f"GUARD_P1={'ON' if permissions['allow_guard_p1'] else 'OFF'}, "
                f"TOOLS={tool_limit}."
            ),
            "system",
        )
        self.input_box.delete("1.0", "end")

        self.running = True
        self.started_at = time.monotonic()
        self.status_var.set("Ultra работает...")
        self.progress.start(12)
        self._set_run_controls_enabled(False)

        thread = threading.Thread(
            target=self._worker,
            args=(task, str(workspace), permissions, self.current_chat_id),
            daemon=True,
        )
        thread.start()

    def _set_run_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.send_button.configure(state=state)
        for widget in self._security_widgets:
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
        def on_event(event: dict):
            try:
                self.trace_events.put_nowait(event)
            except queue.Full:
                pass

        try:
            result = asyncio.run(
                run_agent_task(
                    task,
                    workspace,
                    on_event=on_event,
                    permissions=permissions,
                    chat_id=chat_id,
                )
            )
            append_raw_message(
                workspace,
                chat_id,
                "assistant",
                result,
            )
            self.events.put(("success", result))
        except Exception as exc:
            self.events.put(("error", f"{type(exc).__name__}: {exc}"))

    def _poll_events(self) -> None:
        try:
            while True:
                event_type, payload = self.events.get_nowait()
                if event_type == "success":
                    self._append_chat("ULTRA", payload, "assistant")
                    self._finish_run("Готово")
                elif event_type == "error":
                    self._append_chat("ОШИБКА", payload, "system")
                    self._finish_run("Ошибка")
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _poll_trace_events(self) -> None:
        try:
            while True:
                event = self.trace_events.get_nowait()
                if event.get("event") == "run_started":
                    if self._run_started_once:
                        self._insert_run_separator()
                    self._run_started_once = True
                self._append_trace(self._format_event(event))
        except queue.Empty:
            pass
        self.after(100, self._poll_trace_events)

    def _insert_run_separator(self) -> None:
        self.trace_log.configure(state="normal")
        self.trace_log.insert("end", "\n", "trace")
        self.trace_log.insert(
            "end",
            "////////////////////////////////////////////////////////////\n",
            "run_separator",
        )
        self.trace_log.insert(
            "end",
            "////////////////////////////////////////////////////////////\n",
            "run_separator",
        )
        self.trace_log.insert("end", "\n", "trace")
        self.trace_log.see("end")
        self.trace_log.configure(state="disabled")

    def _tick_status(self) -> None:
        if self.running:
            elapsed = int(time.monotonic() - self.started_at)
            self.status_var.set(f"Ultra работает... {elapsed} сек.")
        self.after(500, self._tick_status)

    def _finish_run(self, status: str) -> None:
        self.running = False
        self.progress.stop()
        self.status_var.set(status)
        self._set_run_controls_enabled(True)
        self.input_box.focus_set()


if __name__ == "__main__":
    app = UltraApp()
    app.mainloop()
