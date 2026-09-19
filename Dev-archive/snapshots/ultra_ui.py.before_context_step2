import asyncio
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, scrolledtext, ttk

from server import get_backup_base_path, run_agent_task


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
        self.title(APP_TITLE)
        self.geometry("1220x860")
        self.minsize(950, 720)

        self.workspace_var = tk.StringVar(value=str(Path.cwd()))
        self.status_var = tk.StringVar(value="Готово")

        # Серверные разрешения запуска. Безопасные значения по умолчанию:
        # читать можно весь workspace, писать нельзя, autobackup включён.
        self.allow_read_var = tk.BooleanVar(value=True)
        self.allow_write_var = tk.BooleanVar(value=False)
        self.allow_delete_var = tk.BooleanVar(value=False)
        self.allow_verify_var = tk.BooleanVar(value=True)
        self.auto_backup_var = tk.BooleanVar(value=True)
        self.dark_theme_var = tk.BooleanVar(value=True)

        # Настраиваемые цвета основных текстовых потоков интерфейса.
        self.log_text_color_var = tk.StringVar(value="#76E68A")
        self.user_text_color_var = tk.StringVar(value="#FFFFFF")
        self.assistant_text_color_var = tk.StringVar(value="#8EC5FF")

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
        self._record_initial_mtimes()

        self._security_widgets: list[tk.Widget] = []
        self._color_swatches: dict[str, tk.Widget] = {}
        self._run_started_once = False

        self._build_ui()
        self._apply_theme()
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

        self.configure(bg=bg)
        style.configure(".", background=panel, foreground=fg)
        style.configure("TFrame", background=panel)
        style.configure("TLabel", background=panel, foreground=fg)
        style.configure("TLabelframe", background=panel, foreground=fg)
        style.configure("TLabelframe.Label", background=panel, foreground=fg)
        style.configure("TCheckbutton", background=panel, foreground=fg)
        style.configure("TButton", background=button_bg, foreground=fg)
        style.configure("TEntry", fieldbackground=field, foreground=fg)
        style.configure("TSpinbox", fieldbackground=field, foreground=fg)
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
                )

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

    def _refresh_color_swatches(self) -> None:
        values = {
            "log": self.log_text_color_var.get(),
            "user": self.user_text_color_var.get(),
            "assistant": self.assistant_text_color_var.get(),
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

    def _record_initial_mtimes(self) -> None:
        try:
            self._server_mtime = Path("server.py").stat().st_mtime
        except FileNotFoundError:
            self._server_mtime = None
        try:
            self._ui_mtime = Path("ultra_ui.py").stat().st_mtime
        except FileNotFoundError:
            self._ui_mtime = None

    def _poll_code_changes(self) -> None:
        changed = []
        try:
            current = Path("server.py").stat().st_mtime
            if self._server_mtime is not None and current != self._server_mtime:
                changed.append("server.py")
        except FileNotFoundError:
            pass
        try:
            current = Path("ultra_ui.py").stat().st_mtime
            if self._ui_mtime is not None and current != self._ui_mtime:
                changed.append("ultra_ui.py")
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
        root.columnconfigure(0, weight=0, minsize=360)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        # Левая панель — наблюдаемый trace.
        left_frame = ttk.Frame(root)
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.configure(width=360)
        left_frame.grid_propagate(False)

        ttk.Label(left_frame, text="ЛОГ ДЕЙСТВИЙ").pack(anchor="w", pady=(0, 6))
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

        # Правая панель.
        right_frame = ttk.Frame(root)
        right_frame.grid(row=0, column=1, sticky="nsew")

        # Workspace — намеренно компактный: оставляем справа запас под будущие controls.
        workspace_frame = ttk.Frame(right_frame)
        workspace_frame.pack(fill="x")
        ttk.Label(workspace_frame, text="Workspace:").grid(
            row=0, column=0, sticky="w"
        )
        self.workspace_entry = ttk.Entry(
            workspace_frame,
            textvariable=self.workspace_var,
            width=72,
        )
        self.workspace_entry.grid(
            row=0, column=1, sticky="w", padx=(8, 8)
        )
        bind_edit_shortcuts(self.workspace_entry)
        self.workspace_button = ttk.Button(
            workspace_frame,
            text="Выбрать папку",
            command=self._choose_workspace,
        )
        self.workspace_button.grid(row=0, column=2, sticky="w")

        # Жёсткие серверные ограничения.
        security = ttk.LabelFrame(
            right_frame,
            text="БЕЗОПАСНОСТЬ ЗАПУСКА — ограничения применяет server.py",
            padding=8,
        )
        security.pack(fill="x", pady=(10, 8))

        # Верхняя строка: backup, лимит инструментов и тема.
        backup_check = ttk.Checkbutton(
            security,
            text="Автобэкап ДО запуска",
            variable=self.auto_backup_var,
        )
        backup_check.grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )

        ttk.Label(security, text="Лимит tools:").grid(
            row=0, column=2, sticky="e", padx=(12, 4), pady=(0, 4)
        )
        tool_limit_spin = ttk.Spinbox(
            security,
            from_=1,
            to=200,
            width=6,
            textvariable=self.tool_limit_var,
        )
        tool_limit_spin.grid(
            row=0, column=3, sticky="w", pady=(0, 4)
        )

        # Компактные визуальные настройки вынесены в отдельный блок справа.
        # Цвет меняется кликом прямо по цветному квадрату.
        interface_frame = ttk.LabelFrame(
            security,
            text="ИНТЕРФЕЙС",
            padding=(8, 5),
        )
        interface_frame.grid(
            row=0, column=4, rowspan=4, sticky="nw", padx=(18, 0), pady=(0, 2)
        )

        theme_check = ttk.Checkbutton(
            interface_frame,
            text="Тёмная тема",
            variable=self.dark_theme_var,
            command=self._apply_theme,
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

        # Галочка чтения находится прямо у области, которой она управляет.
        read_check = ttk.Checkbutton(
            security,
            text="",
            variable=self.allow_read_var,
        )
        read_check.grid(row=1, column=0, sticky="w", pady=(4, 0))

        ttk.Label(security, text="Чтение только в:").grid(
            row=1, column=1, sticky="w", padx=(2, 0), pady=(4, 0)
        )
        read_scope_entry = ttk.Entry(
            security,
            textvariable=self.read_scope_var,
            width=62,
        )
        read_scope_entry.grid(
            row=1, column=2, sticky="w", padx=(8, 8), pady=(4, 0)
        )
        bind_edit_shortcuts(read_scope_entry)
        read_scope_button = ttk.Button(
            security,
            text="Выбрать",
            command=lambda: self._choose_scope(self.read_scope_var),
        )
        read_scope_button.grid(row=1, column=3, sticky="w", pady=(4, 0))

        # Галочка записи находится прямо у области, которой она управляет.
        write_check = ttk.Checkbutton(
            security,
            text="",
            variable=self.allow_write_var,
        )
        write_check.grid(row=2, column=0, sticky="w", pady=(6, 0))

        ttk.Label(security, text="Запись только в:").grid(
            row=2, column=1, sticky="w", padx=(2, 0), pady=(6, 0)
        )
        write_scope_entry = ttk.Entry(
            security,
            textvariable=self.write_scope_var,
            width=62,
        )
        write_scope_entry.grid(
            row=2, column=2, sticky="w", padx=(8, 8), pady=(6, 0)
        )
        bind_edit_shortcuts(write_scope_entry)
        write_scope_button = ttk.Button(
            security,
            text="Выбрать",
            command=lambda: self._choose_scope(self.write_scope_var),
        )
        write_scope_button.grid(row=2, column=3, sticky="w", pady=(6, 0))

        # Удаление — отдельное разрешение, независимо от записи.
        delete_check = ttk.Checkbutton(
            security,
            text="",
            variable=self.allow_delete_var,
        )
        delete_check.grid(row=3, column=0, sticky="w", pady=(6, 0))

        ttk.Label(security, text="Удаление только в:").grid(
            row=3, column=1, sticky="w", padx=(2, 0), pady=(6, 0)
        )
        delete_scope_entry = ttk.Entry(
            security,
            textvariable=self.delete_scope_var,
            width=62,
        )
        delete_scope_entry.grid(
            row=3, column=2, sticky="w", padx=(8, 8), pady=(6, 0)
        )
        bind_edit_shortcuts(delete_scope_entry)
        delete_scope_button = ttk.Button(
            security,
            text="Выбрать",
            command=lambda: self._choose_scope(self.delete_scope_var),
        )
        delete_scope_button.grid(row=3, column=3, sticky="w", pady=(6, 0))


        # VERIFY — отдельное безопасное разрешение на белый список проверок.
        verify_check = ttk.Checkbutton(
            security,
            text="VERIFY — Python / Git / UI проверки",
            variable=self.allow_verify_var,
        )
        verify_check.grid(
            row=4, column=1, columnspan=3, sticky="w", pady=(6, 0)
        )

        ttk.Label(security, text="Защищённые бэкапы:").grid(
            row=5, column=1, sticky="w", padx=(2, 0), pady=(6, 0)
        )
        backup_label = ttk.Label(
            security,
            textvariable=self.backup_path_var,
            font=("Consolas", 8),
        )
        backup_label.grid(
            row=5, column=2, columnspan=3, sticky="w", padx=(8, 0), pady=(6, 0)
        )

        hint = ttk.Label(
            security,
            text=(
                "✓ слева включает доступ для строки. '.' = корень workspace. "
                "Пример: чтение='.' + запись='Документация'."
            ),
        )
        hint.grid(row=6, column=1, columnspan=4, sticky="w", pady=(8, 0))

        self._security_widgets.extend(
            [
                read_check,
                write_check,
                delete_check,
                verify_check,
                backup_check,
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

        ttk.Label(right_frame, text="Чат").pack(anchor="w")
        self.chat = scrolledtext.ScrolledText(
            right_frame,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 10),
        )
        self.chat.pack(fill="both", expand=True, pady=(5, 8))
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
        )
        self.progress.pack(side="right")

        ttk.Label(right_frame, text="Сообщение").pack(anchor="w")
        self.input_box = scrolledtext.ScrolledText(
            right_frame,
            wrap="word",
            height=7,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.input_box.pack(fill="x", pady=(5, 8))
        bind_edit_shortcuts(self.input_box)
        self.input_box.bind("<Control-Return>", self._send_from_hotkey)

        buttons = ttk.Frame(right_frame)
        buttons.pack(fill="x")
        ttk.Label(buttons, text="Ctrl+Enter — отправить").pack(side="left")
        self.send_button = ttk.Button(
            buttons,
            text="Отправить",
            command=self._send,
        )
        self.send_button.pack(side="right")

        self._append_chat(
            "СИСТЕМА",
            (
                "Интерфейс готов. По умолчанию чтение и VERIFY разрешены, запись "
                "и удаление ЗАПРЕЩЕНЫ, автобэкап включён. Лимит tools = 20. "
                "Серверные галочки — это реальные ограничения, а не только "
                "текст в промпте."
            ),
            "system",
        )
        self.input_box.focus_set()

    def _choose_workspace(self) -> None:
        selected = filedialog.askdirectory(
            initialdir=self.workspace_var.get() or str(Path.cwd()),
            title="Выбрать рабочую папку",
        )
        if selected:
            self.workspace_var.set(selected)
            workspace = Path(selected)
            if (workspace / "Документация").is_dir():
                self.write_scope_var.set("Документация")

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
                f"LIMIT={perms.get('tool_limit')} | "
                f"BACKUP={perms.get('auto_backup')} | {task_preview[:40]}"
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
            "read_scope": read_scope,
            "write_scope": write_scope,
            "delete_scope": delete_scope,
            "tool_limit": tool_limit,
            "auto_backup": self.auto_backup_var.get(),
        }

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
                f"TOOLS={tool_limit}, "
                f"BACKUP={'ON' if permissions['auto_backup'] else 'OFF'}."
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
            args=(task, str(workspace), permissions),
            daemon=True,
        )
        thread.start()

    def _set_run_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.send_button.configure(state=state)
        self.workspace_entry.configure(state=state)
        self.workspace_button.configure(state=state)
        for widget in self._security_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass

    def _worker(self, task: str, workspace: str, permissions: dict) -> None:
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
                )
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
