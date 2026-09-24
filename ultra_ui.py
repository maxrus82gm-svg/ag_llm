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
from model_registry import get_model_spec, list_model_specs
from context_storage import (
    append_raw_message,
    create_message_context_variant,
    create_chat,
    ensure_chat,
    ensure_workspace_storage,
    get_message_context_state,
    get_message_working_representation,
    list_existing_chats,
    list_chats,
    load_chat_messages,
    load_context_variant,
    load_existing_project_context,
    load_project_context,
    load_raw_message,
    new_task_block_id,
    probe_existing_workspace,
    rename_chat,
    rename_workspace,
    restore_message_raw,
    save_project_context,
)
from ui_state import load_ui_state, save_ui_state
from ui_state import DEFAULT_CHAT_AUDIT_RATIOS, DEFAULT_CENTRAL_VERTICAL_RATIOS
from audit_storage import list_chat_audit_threads, load_audit_thread
from workspace_runtime_settings import (
    load_workspace_runtime_settings,
    save_workspace_runtime_settings,
)
from agent_global_context import (
    get_agent_global_context_path,
    load_agent_global_context,
    save_agent_global_context,
)
from compressor_runtime import (
    DEFAULT_COMPRESSOR_MODEL_ID,
    DEFAULT_REDUCTION_PERCENT,
    CompressorRunResult,
    run_message_compressor_task_detailed,
    validate_reduction_percent,
)
from compressor_settings import (
    get_final_check_template_path,
    get_message_compression_template_path,
    load_final_check_template,
    load_message_compression_template,
    save_final_check_template,
    save_message_compression_template,
)
from server_context_messages import (
    delete_server_context_message,
    get_server_context_messages_path,
    list_server_context_event_records,
    upsert_server_context_message,
    validate_event_id,
)


APP_TITLE = "GigaChat Ultra Local Agent"


def get_message_display_text(message: dict, resolved: dict | None = None) -> str:
    """Return the representation that the persistent CHAT body must show."""
    if message.get("role") in {"user", "assistant"}:
        if not isinstance(resolved, dict):
            raise RuntimeError(
                "Для user/assistant message не разрешён working context."
            )
        text = resolved.get("text")
    else:
        text = message.get("original_text")
    if not isinstance(text, str):
        raise RuntimeError("Текст сообщения недоступен для отображения.")
    return text


def get_assistant_audit_run_id(message: dict) -> str | None:
    if message.get("role") != "assistant":
        return None
    producer = message.get("producer")
    run_id = producer.get("run_id") if isinstance(producer, dict) else None
    return run_id if isinstance(run_id, str) and run_id else None


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

        saved_model_id = self._ui_state.get(
            "main_chat_model_id",
            "gigachat_ultra",
        )
        try:
            selected_model = get_model_spec(saved_model_id)
        except (KeyError, RuntimeError, ValueError):
            selected_model = get_model_spec("gigachat_ultra")
        self._ui_state["main_chat_model_id"] = selected_model.model_id
        self.main_chat_model_id_var = tk.StringVar(
            value=selected_model.model_id
        )
        self.main_chat_model_display_var = tk.StringVar(
            value=selected_model.display_name
        )
        self._running_model_display_name = selected_model.display_name

        saved_compressor_model_id = self._ui_state.get(
            "compressor_model_id",
            DEFAULT_COMPRESSOR_MODEL_ID,
        )
        try:
            compressor_model = get_model_spec(saved_compressor_model_id)
        except (KeyError, RuntimeError, ValueError):
            compressor_model = get_model_spec(DEFAULT_COMPRESSOR_MODEL_ID)
        self._ui_state["compressor_model_id"] = compressor_model.model_id
        self.compressor_model_id_var = tk.StringVar(
            value=compressor_model.model_id
        )
        self.compressor_model_display_var = tk.StringVar(
            value=compressor_model.display_name
        )

        saved_verifier_model_id = self._ui_state.get(
            "verifier_model_id",
            "gigachat_3_pro",
        )
        try:
            verifier_model = get_model_spec(saved_verifier_model_id)
        except (KeyError, RuntimeError, ValueError):
            verifier_model = get_model_spec("gigachat_3_pro")
        self._ui_state["verifier_model_id"] = verifier_model.model_id
        self.verifier_model_id_var = tk.StringVar(
            value=verifier_model.model_id
        )
        self.verifier_model_display_var = tk.StringVar(
            value=verifier_model.display_name
        )

        self.compressor_reduction_percent_var = tk.StringVar(
            value=str(
                self._ui_state.get(
                    "compressor_reduction_percent",
                    DEFAULT_REDUCTION_PERCENT,
                )
            )
        )
        self.compressor_final_check_enabled_var = tk.BooleanVar(
            value=bool(
                self._ui_state.get(
                    "compressor_final_check_enabled",
                    True,
                )
            )
        )
        self.compressor_message_id_var = tk.StringVar(value="—")
        self.compressor_status_var = tk.StringVar(value="не выбрано")

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
        self.error_log_color_var = tk.StringVar(
            value=saved_colors.get("error_log", "#F08080")
        )
        self.audit_text_color_var = tk.StringVar(
            value=saved_colors.get("audit", "#83919B")
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
        self.compressor_running = False
        self.started_at = 0.0
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.trace_events: queue.Queue[dict] = queue.Queue()

        self._code_changed = False
        self._changed_files: list[str] = []
        self._server_mtime = None
        self._ui_mtime = None
        self._server_context_messages_mtime = None
        self._record_initial_mtimes()

        self._security_widgets: list[tk.Widget] = []
        self._compressor_widgets: list[tk.Widget] = []
        self._message_action_widgets: list[tk.Widget] = []
        self._message_action_frames: dict[str, tk.Widget] = {}
        self._workspace_widgets: list[tk.Widget] = []
        self._color_swatches: dict[str, tk.Widget] = {}
        self._run_started_once = False
        self.audit_visible_var = tk.BooleanVar(
            value=bool(self._ui_state.get("audit_visible", True))
        )
        self._selected_audit_run_id: str | None = None
        self._selected_task_block_id: str | None = None
        self._active_audit_run_id: str | None = None
        self._task_block_index: dict[str, dict] = {}
        self._task_block_order: list[str] = []
        self._message_task_block_ids: dict[str, str] = {}
        self._chat_audit_sync_after = None
        self._chat_rendering = False
        self._last_chat_yview_first: float | None = None

        self.current_workspace_id: str | None = None
        self.current_chat_id: str | None = None
        self.selected_message_id: str | None = None
        self._selected_message_chat_id: str | None = None
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
        for name in ("main_paned", "central_vertical_paned", "chat_audit_paned"):
            paned = getattr(self, name, None)
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

        for name in ("trace_log", "chat", "audit_text", "input_box"):
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
            trace_log.tag_configure(
                "trace_error",
                foreground=self.error_log_color_var.get(),
                font=("Consolas", 9),
            )

        audit_text = getattr(self, "audit_text", None)
        if audit_text is not None:
            audit_text.tag_configure("audit", foreground=self.audit_text_color_var.get())
            audit_text.tag_configure("dredd_fail", foreground=self.error_log_color_var.get())
            audit_text.tag_configure("ultra", foreground=self.assistant_text_color_var.get())
            audit_text.tag_configure("resolved", foreground=self.log_text_color_var.get())
            audit_text.tag_configure("metadata", foreground=self._theme_colors.get("muted", "#888888"))

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
            "error_log": self.error_log_color_var.get(),
            "audit": self.audit_text_color_var.get(),
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

        model_frame = ttk.LabelFrame(
            right_frame,
            text="MAIN CHAT MODEL",
            padding=(8, 5),
        )
        model_frame.pack(fill="x", pady=(0, 8))
        model_registry_button = ttk.Button(
            model_frame,
            text="Модель",
            command=lambda: self._open_model_registry("main_chat"),
        )
        model_registry_button.pack(side="left")
        ttk.Label(
            model_frame,
            textvariable=self.main_chat_model_display_var,
        ).pack(side="left", padx=(8, 16))
        main_context_button = ttk.Button(
            model_frame,
            text="Контекст MAIN CHAT...",
            command=self._open_global_ultra_context_editor,
        )
        main_context_button.pack(side="left")

        verifier_model_frame = ttk.LabelFrame(
            right_frame,
            text="VERIFIER MODEL",
            padding=(8, 5),
        )
        verifier_model_frame.pack(fill="x", pady=(0, 8))
        verifier_model_button = ttk.Button(
            verifier_model_frame,
            text="Модель",
            command=lambda: self._open_model_registry("verifier"),
        )
        verifier_model_button.pack(side="left")
        ttk.Label(
            verifier_model_frame,
            textvariable=self.verifier_model_display_var,
        ).pack(side="left", padx=(8, 16))

        # Жёсткие серверные ограничения.
        security = ttk.LabelFrame(
            right_frame,
            text="БЕЗОПАСНОСТЬ ЗАПУСКА — ограничения применяет server.py",
            padding=8,
        )
        security.pack(fill="x", pady=(0, 8))
        security_controls = ttk.Frame(security)
        security_controls.pack(side="left", anchor="n")
        security_service = ttk.Frame(security)
        security_service.pack(side="right", anchor="n", padx=(16, 0))
        security_top = ttk.Frame(security_controls)
        security_top.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 2))

        # Верхняя компактная строка.
        # Backup для UI считается обязательной системной защитой и
        # не занимает место отдельной пользовательской настройкой.
        ttk.Label(security_top, text="Лимит tools:").pack(side="left", padx=(0, 4))
        tool_limit_spin = ttk.Spinbox(
            security_top,
            from_=1,
            to=200,
            width=6,
            textvariable=self.tool_limit_var,
        )
        tool_limit_spin.pack(side="left", padx=(0, 18))

        verify_check = ttk.Checkbutton(
            security_top,
            text="VERIFY",
            variable=self.allow_verify_var,
        )
        verify_check.pack(side="left", padx=(0, 18))

        guard_p1_check = ttk.Checkbutton(
            security_top,
            text="GUARD P1",
            variable=self.allow_guard_p1_var,
        )
        guard_p1_check.pack(side="left")

        context_messages_button = ttk.Button(
            security_service,
            text="Контекстные сообщения",
            command=self._open_server_context_messages_editor,
        )
        context_messages_button.pack(anchor="e", pady=(0, 5))

        # Компактные визуальные настройки вынесены в отдельный блок справа.
        # Цвет меняется кликом прямо по цветному квадрату.
        interface_frame = ttk.LabelFrame(
            security_service,
            text="ИНТЕРФЕЙС",
            padding=(8, 5),
        )
        interface_frame.pack(anchor="e")

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
                1, 0,
                "Лог действий",
                "log",
                self.log_text_color_var,
                "Цвет текста — лог действий",
            ),
            (
                2, 0,
                "Ошибки лога",
                "error_log",
                self.error_log_color_var,
                "Цвет ошибок — лог действий",
            ),
            (
                3, 0,
                "Разбор выполнения",
                "audit",
                self.audit_text_color_var,
                "Цвет текста — разбор выполнения",
            ),
            (
                1, 2,
                "Пользователь",
                "user",
                self.user_text_color_var,
                "Цвет текста — сообщение пользователя в чате",
            ),
            (
                2, 2,
                "Ответ ассистента",
                "assistant",
                self.assistant_text_color_var,
                "Цвет текста — ответ ассистента",
            ),
            (
                3, 2,
                "Workspace / чаты",
                "workspace",
                self.workspace_text_color_var,
                "Цвет текста — Workspace и чаты",
            ),
        ]

        for row, column, label_text, key, color_var, dialog_title in compact_color_rows:
            ttk.Label(interface_frame, text=label_text).grid(
                row=row, column=column, sticky="w", padx=(10, 0) if column else 0, pady=1
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
            swatch.grid(row=row, column=column + 1, sticky="w", padx=(8, 0), pady=1)
            self._color_swatches[key] = swatch

        reset_layout_button = ttk.Button(
            interface_frame,
            text="Сброс панелей",
            command=self._reset_panel_layout,
        )
        reset_layout_button.grid(
            row=4,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(5, 0),
        )

        # Компактные и одинаковые строки областей доступа.
        read_check = ttk.Checkbutton(
            security_controls,
            text="",
            variable=self.allow_read_var,
        )
        read_check.grid(row=1, column=0, sticky="w", pady=2)

        ttk.Label(security_controls, text="Чтение только в:").grid(
            row=1, column=1, sticky="w", padx=(2, 0), pady=2
        )
        read_scope_entry = ttk.Entry(
            security_controls,
            textvariable=self.read_scope_var,
            width=38,
        )
        read_scope_entry.grid(
            row=1, column=2, sticky="w", padx=(6, 4), pady=2
        )
        bind_edit_shortcuts(read_scope_entry)
        read_scope_button = ttk.Button(
            security_controls,
            text="...",
            width=3,
            command=lambda: self._choose_scope(self.read_scope_var),
        )
        read_scope_button.grid(
            row=1, column=3, sticky="w", pady=2
        )

        write_check = ttk.Checkbutton(
            security_controls,
            text="",
            variable=self.allow_write_var,
        )
        write_check.grid(row=2, column=0, sticky="w", pady=2)

        ttk.Label(security_controls, text="Запись только в:").grid(
            row=2, column=1, sticky="w", padx=(2, 0), pady=2
        )
        write_scope_entry = ttk.Entry(
            security_controls,
            textvariable=self.write_scope_var,
            width=38,
        )
        write_scope_entry.grid(
            row=2, column=2, sticky="w", padx=(6, 4), pady=2
        )
        bind_edit_shortcuts(write_scope_entry)
        write_scope_button = ttk.Button(
            security_controls,
            text="...",
            width=3,
            command=lambda: self._choose_scope(self.write_scope_var),
        )
        write_scope_button.grid(
            row=2, column=3, sticky="w", pady=2
        )

        # Удаление — отдельное разрешение, независимо от записи.
        delete_check = ttk.Checkbutton(
            security_controls,
            text="",
            variable=self.allow_delete_var,
        )
        delete_check.grid(row=3, column=0, sticky="w", pady=2)

        ttk.Label(security_controls, text="Удаление только в:").grid(
            row=3, column=1, sticky="w", padx=(2, 0), pady=2
        )
        delete_scope_entry = ttk.Entry(
            security_controls,
            textvariable=self.delete_scope_var,
            width=38,
        )
        delete_scope_entry.grid(
            row=3, column=2, sticky="w", padx=(6, 4), pady=2
        )
        bind_edit_shortcuts(delete_scope_entry)
        delete_scope_button = ttk.Button(
            security_controls,
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
                context_messages_button,
                model_registry_button,
                verifier_model_button,
                main_context_button,
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

        self.central_vertical_paned = tk.PanedWindow(
            right_frame, orient="vertical", sashwidth=6, showhandle=False,
            bd=0, relief="flat", sashrelief="flat",
        )
        self.central_vertical_paned.pack(fill="both", expand=True)
        self.central_vertical_paned.bind("<ButtonRelease-1>", self._on_sash_release)
        upper_frame = ttk.Frame(self.central_vertical_paned)
        lower_frame = ttk.Frame(self.central_vertical_paned)
        self.central_vertical_paned.add(upper_frame, minsize=180, stretch="always")
        self.central_vertical_paned.add(lower_frame, minsize=210)

        self.chat_audit_paned = tk.PanedWindow(
            upper_frame, orient="horizontal", sashwidth=6, showhandle=False,
            bd=0, relief="flat", sashrelief="flat",
        )
        self.chat_audit_paned.pack(fill="both", expand=True)
        self.chat_audit_paned.bind("<ButtonRelease-1>", self._on_sash_release)
        chat_section = ttk.LabelFrame(
            self.chat_audit_paned,
            text="Чат",
            padding=4,
        )
        self.chat_audit_paned.add(chat_section, minsize=260, stretch="always")
        ttk.Checkbutton(
            chat_section, text="Разбор выполнения",
            variable=self.audit_visible_var, command=self._toggle_audit_panel,
        ).pack(anchor="e")

        self.chat = scrolledtext.ScrolledText(
            chat_section,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 10),
        )
        self.chat.pack(fill="both", expand=True)
        self.chat.configure(yscrollcommand=self._on_chat_yview)
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

        self.audit_section = ttk.LabelFrame(
            self.chat_audit_paned, text="РАЗБОР ВЫПОЛНЕНИЯ", padding=4,
        )
        self.audit_text = scrolledtext.ScrolledText(
            self.audit_section, wrap="word", state="disabled",
            font=("Segoe UI", 9),
        )
        self.audit_text.pack(fill="both", expand=True)
        if self.audit_visible_var.get():
            self.chat_audit_paned.add(self.audit_section, minsize=180)
        self._render_audit_thread()

        compressor_frame = ttk.LabelFrame(
            upper_frame,
            text="КОНТЕКСТ СООБЩЕНИЙ / COMPRESSOR",
            padding=(8, 5),
        )
        compressor_frame.pack(side="bottom", fill="x", pady=(8, 0))
        compressor_frame.columnconfigure(1, minsize=180)
        compressor_frame.columnconfigure(3, weight=1)

        compressor_models_button = ttk.Button(
            compressor_frame,
            text="Модель",
            command=lambda: self._open_model_registry("compressor"),
        )
        compressor_models_button.grid(row=0, column=0, sticky="w")
        ttk.Label(
            compressor_frame,
            textvariable=self.compressor_model_display_var,
        ).grid(row=0, column=1, sticky="w", padx=(8, 18))
        compressor_role_button = ttk.Button(
            compressor_frame,
            text="Контекст роли...",
            command=self._open_compressor_role_context_editor,
        )
        compressor_role_button.grid(row=0, column=2, sticky="w")

        ttk.Label(
            compressor_frame,
            text="Порог сокращения:",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        reduction_value_frame = ttk.Frame(compressor_frame)
        reduction_value_frame.grid(
            row=1,
            column=1,
            sticky="w",
            padx=(8, 18),
            pady=(6, 0),
        )
        compressor_reduction_spin = ttk.Spinbox(
            reduction_value_frame,
            from_=1,
            to=95,
            width=5,
            textvariable=self.compressor_reduction_percent_var,
            command=lambda: self._save_ui_state(silent=True),
        )
        compressor_reduction_spin.pack(side="left")
        ttk.Label(reduction_value_frame, text="%").pack(
            side="left",
            padx=(4, 0),
        )
        compressor_reduction_spin.bind(
            "<FocusOut>",
            lambda _event: self._save_ui_state(silent=True),
        )
        compressor_template_button = ttk.Button(
            compressor_frame,
            text="Контекст сжатия...",
            command=self._open_compressor_template_editor,
        )
        compressor_template_button.grid(
            row=1,
            column=2,
            sticky="w",
            pady=(6, 0),
        )

        compressor_final_check = ttk.Checkbutton(
            compressor_frame,
            text="Дополнительная проверка",
            variable=self.compressor_final_check_enabled_var,
            command=lambda: self._save_ui_state(silent=True),
        )
        compressor_final_check.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(6, 0),
        )
        compressor_final_template_button = ttk.Button(
            compressor_frame,
            text="Контекст дополнительной проверки...",
            command=self._open_compressor_final_check_template_editor,
        )
        compressor_final_template_button.grid(
            row=2,
            column=2,
            sticky="w",
            pady=(6, 0),
        )

        ttk.Label(compressor_frame, text="Сообщение:").grid(
            row=3,
            column=0,
            sticky="w",
            pady=(6, 0),
        )
        ttk.Label(
            compressor_frame,
            textvariable=self.compressor_message_id_var,
        ).grid(
            row=3,
            column=1,
            sticky="w",
            padx=(8, 18),
            pady=(6, 0),
        )
        ttk.Label(compressor_frame, text="Состояние:").grid(
            row=3,
            column=2,
            sticky="w",
            pady=(6, 0),
        )
        ttk.Label(
            compressor_frame,
            textvariable=self.compressor_status_var,
        ).grid(
            row=3,
            column=3,
            sticky="w",
            padx=(8, 0),
            pady=(6, 0),
        )

        self._compressor_widgets.extend(
            [
                compressor_models_button,
                compressor_role_button,
                compressor_template_button,
                compressor_final_template_button,
                compressor_reduction_spin,
                compressor_final_check,
            ]
        )

        status_frame = ttk.Frame(lower_frame)
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
            lower_frame,
            text="Сообщение",
            padding=4,
        )
        message_section.pack(fill="both", expand=True, pady=(0, 8))

        self.input_box = scrolledtext.ScrolledText(
            message_section,
            wrap="word",
            height=7,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.input_box.pack(fill="both", expand=True)
        bind_edit_shortcuts(self.input_box)
        self.input_box.bind("<Control-Return>", self._send_from_hotkey)

        buttons = ttk.Frame(lower_frame)
        buttons.pack(side="bottom", fill="x")
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

    def _set_main_chat_model(self, model_id: str) -> None:
        try:
            model = get_model_spec(model_id)
        except (KeyError, RuntimeError, ValueError):
            model = get_model_spec("gigachat_ultra")

        self.main_chat_model_id_var.set(model.model_id)
        self.main_chat_model_display_var.set(model.display_name)
        self._ui_state["main_chat_model_id"] = model.model_id

    def _set_compressor_model(self, model_id: str) -> None:
        try:
            model = get_model_spec(model_id)
        except (KeyError, RuntimeError, ValueError):
            model = get_model_spec(DEFAULT_COMPRESSOR_MODEL_ID)

        self.compressor_model_id_var.set(model.model_id)
        self.compressor_model_display_var.set(model.display_name)
        self._ui_state["compressor_model_id"] = model.model_id

    def _set_verifier_model(self, model_id: str) -> None:
        try:
            model = get_model_spec(model_id)
        except (KeyError, RuntimeError, ValueError):
            model = get_model_spec("gigachat_3_pro")

        self.verifier_model_id_var.set(model.model_id)
        self.verifier_model_display_var.set(model.display_name)
        self._ui_state["verifier_model_id"] = model.model_id

    def _open_model_registry(self, assignment: str = "main_chat") -> None:
        if assignment == "main_chat":
            assignment_title = "MAIN CHAT MODEL"
            current_model_id = self.main_chat_model_id_var.get()
            apply_model = self._set_main_chat_model
        elif assignment == "compressor":
            assignment_title = "COMPRESSOR MODEL"
            current_model_id = self.compressor_model_id_var.get()
            apply_model = self._set_compressor_model
        elif assignment == "verifier":
            assignment_title = "VERIFIER MODEL"
            current_model_id = self.verifier_model_id_var.get()
            apply_model = self._set_verifier_model
        else:
            raise ValueError(f"Неизвестный Model Assignment: {assignment!r}")

        models = list_model_specs()
        models_by_id = {model.model_id: model for model in models}

        window = tk.Toplevel(self)
        window.title(f"MODEL REGISTRY / {assignment_title}")
        window.transient(self)
        window.geometry("960x560")
        window.minsize(820, 480)

        content = ttk.Frame(window, padding=12)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        ttk.Label(
            content,
            text=f"MODEL REGISTRY / {assignment_title}",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        table = ttk.Frame(content)
        table.grid(row=1, column=0, sticky="nsew")
        table.columnconfigure(1, weight=1)

        headers = (
            "SELECT",
            "DISPLAY NAME",
            "PROVIDER",
            "PROVIDER MODEL ID",
            "TYPE",
            "STATUS",
        )
        for column, text in enumerate(headers):
            ttk.Label(
                table,
                text=text,
                font=("Segoe UI", 9, "bold"),
            ).grid(
                row=0,
                column=column,
                sticky="w",
                padx=(0, 14),
                pady=(0, 6),
            )

        selected_model_id_var = tk.StringVar(
            window,
            value=current_model_id,
        )

        details_vars = {
            "model_id": tk.StringVar(window),
            "display_name": tk.StringVar(window),
            "provider": tk.StringVar(window),
            "provider_model_id": tk.StringVar(window),
            "type": tk.StringVar(window),
            "enabled": tk.StringVar(window),
        }

        def update_details() -> None:
            model = models_by_id.get(selected_model_id_var.get())
            if model is None:
                return
            details_vars["model_id"].set(model.model_id)
            details_vars["display_name"].set(model.display_name)
            details_vars["provider"].set(model.provider)
            details_vars["provider_model_id"].set(
                model.provider_model_id
            )
            details_vars["type"].set(
                "Local" if model.is_local else "Cloud"
            )
            details_vars["enabled"].set(
                "Enabled" if model.enabled else "Disabled"
            )

        for row, model in enumerate(models, start=1):
            radio = ttk.Radiobutton(
                table,
                variable=selected_model_id_var,
                value=model.model_id,
                command=update_details,
            )
            if not model.enabled:
                radio.state(["disabled"])
            radio.grid(row=row, column=0, sticky="w", pady=2)

            values = (
                model.display_name,
                model.provider,
                model.provider_model_id,
                "Local" if model.is_local else "Cloud",
                "Enabled" if model.enabled else "Disabled",
            )
            for column, text in enumerate(values, start=1):
                ttk.Label(table, text=text).grid(
                    row=row,
                    column=column,
                    sticky="w",
                    padx=(0, 14),
                    pady=2,
                )

        details = ttk.LabelFrame(
            content,
            text="ВЫБРАННАЯ MODEL",
            padding=8,
        )
        details.grid(row=2, column=0, sticky="ew", pady=(12, 10))
        details.columnconfigure(1, weight=1)

        detail_rows = (
            ("Internal ID", "model_id"),
            ("Display name", "display_name"),
            ("Provider", "provider"),
            ("Provider model ID", "provider_model_id"),
            ("Local / Cloud", "type"),
            ("Enabled", "enabled"),
        )
        for row, (label, key) in enumerate(detail_rows):
            ttk.Label(details, text=f"{label}:").grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 12),
                pady=1,
            )
            ttk.Label(details, textvariable=details_vars[key]).grid(
                row=row,
                column=1,
                sticky="w",
                pady=1,
            )

        buttons = ttk.Frame(content)
        buttons.grid(row=3, column=0, sticky="e")

        def apply_selection() -> None:
            if self.running or self.compressor_running:
                messagebox.showinfo(
                    APP_TITLE,
                    "Дождитесь завершения текущего RUN.",
                    parent=window,
                )
                return

            selected_id = selected_model_id_var.get()
            try:
                model = get_model_spec(selected_id)
            except (KeyError, RuntimeError, ValueError) as exc:
                messagebox.showerror(
                    APP_TITLE,
                    str(exc),
                    parent=window,
                )
                return
            if not model.enabled:
                messagebox.showerror(
                    APP_TITLE,
                    "Выбранная MODEL отключена.",
                    parent=window,
                )
                return

            apply_model(model.model_id)
            self._save_ui_state(silent=False)

        ttk.Button(
            buttons,
            text="Применить",
            command=apply_selection,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            buttons,
            text="Закрыть",
            command=window.destroy,
        ).pack(side="left")

        update_details()
        window.focus_set()

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
        mode = self._window_mode()
        if len(ratios) == 2:
            self._ui_state.setdefault("panel_ratios", {})[mode] = ratios
        for name, key, dimension, visible in (
            ("chat_audit_paned", "chat_audit_ratios", "width", self.audit_visible_var.get()),
            ("central_vertical_paned", "central_vertical_ratios", "height", True),
        ):
            paned = getattr(self, name, None)
            if paned is None or not visible:
                continue
            try:
                size = int(getattr(paned, f"winfo_{dimension}")())
                position = int(paned.sash_coord(0)[0 if dimension == "width" else 1])
                if size >= 300 and 0 < position < size:
                    self._ui_state.setdefault(key, {})[mode] = round(position / size, 6)
            except (tk.TclError, IndexError, ValueError):
                pass
        self._ui_state["audit_visible"] = self.audit_visible_var.get()

    def _apply_inner_panel_ratios(self, mode: str) -> None:
        for name, key, dimension, minimum in (
            ("chat_audit_paned", "chat_audit_ratios", "width", 180),
            ("central_vertical_paned", "central_vertical_ratios", "height", 210),
        ):
            paned = getattr(self, name, None)
            if paned is None:
                continue
            try:
                if len(paned.panes()) < 2:
                    continue
                size = int(getattr(paned, f"winfo_{dimension}")())
                if size < minimum * 2:
                    continue
                ratio = float((self._ui_state.get(key) or {}).get(mode, 0.6))
                position = max(minimum, min(int(size * ratio), size - minimum))
                paned.sash_place(0, position if dimension == "width" else 0,
                                 position if dimension == "height" else 0)
            except (tk.TclError, ValueError, TypeError, IndexError):
                pass

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
            self._apply_inner_panel_ratios(mode)
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
        self._ui_state["chat_audit_ratios"] = dict(DEFAULT_CHAT_AUDIT_RATIOS)
        self._ui_state["central_vertical_ratios"] = dict(DEFAULT_CENTRAL_VERTICAL_RATIOS)
        self.audit_visible_var.set(True)
        self._toggle_audit_panel(save=False)
        self._apply_panel_ratios(self._window_mode())
        self._save_ui_state(silent=True)

    def _toggle_audit_panel(self, *, save: bool = True) -> None:
        panes = self.chat_audit_paned.panes()
        present = str(self.audit_section) in panes
        if self.audit_visible_var.get() and not present:
            self.chat_audit_paned.add(self.audit_section, minsize=180)
            self.after_idle(lambda: self._apply_inner_panel_ratios(self._window_mode()))
        elif not self.audit_visible_var.get() and present:
            self.chat_audit_paned.forget(self.audit_section)
        self._ui_state["audit_visible"] = self.audit_visible_var.get()
        if save:
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
                "error_log": self.error_log_color_var.get(),
                "audit": self.audit_text_color_var.get(),
                "user": self.user_text_color_var.get(),
                "assistant": self.assistant_text_color_var.get(),
                "workspace": self.workspace_text_color_var.get(),
            }
            self._ui_state["workspaces"] = list(self._workspace_registry)
            self._ui_state["active_workspace_id"] = self.current_workspace_id
            self._ui_state["main_chat_model_id"] = (
                self.main_chat_model_id_var.get()
            )
            self._ui_state["compressor_model_id"] = (
                self.compressor_model_id_var.get()
            )
            self._ui_state["verifier_model_id"] = (
                self.verifier_model_id_var.get()
            )
            try:
                reduction_percent = validate_reduction_percent(
                    int(self.compressor_reduction_percent_var.get())
                )
            except (TypeError, ValueError):
                reduction_percent = int(
                    self._ui_state.get(
                        "compressor_reduction_percent",
                        DEFAULT_REDUCTION_PERCENT,
                    )
                )
                self.compressor_reduction_percent_var.set(
                    str(reduction_percent)
                )
            self._ui_state["compressor_reduction_percent"] = (
                reduction_percent
            )
            self._ui_state["compressor_final_check_enabled"] = (
                self.compressor_final_check_enabled_var.get()
            )
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

    def _probe_registered_workspace(
        self,
        entry: dict,
    ) -> tuple[Path | None, dict | None, str]:
        path_text = entry.get("path")
        remembered_id = entry.get("workspace_id")
        if not isinstance(path_text, str) or not path_text:
            return None, None, "НЕДОСТУПЕН"
        if not isinstance(remembered_id, str) or not remembered_id:
            return None, None, "НЕДОСТУПЕН"

        try:
            probe = probe_existing_workspace(
                path_text,
                expected_workspace_id=remembered_id,
            )
        except Exception:
            return None, None, "НЕДОСТУПЕН"

        status = probe.get("status")
        if status == "ok":
            return Path(probe["workspace_root"]), probe, ""
        if status == "id_conflict":
            return None, probe, "ID КОНФЛИКТ"
        return None, probe, "НЕДОСТУПЕН"

    def _find_registered_workspace_entry(
        self,
        workspace: Path,
        workspace_id: str | None = None,
    ) -> dict | None:
        root = workspace.resolve()
        candidates = []
        for entry in self._workspace_registry:
            try:
                same_path = Path(entry["path"]).resolve() == root
            except Exception:
                continue
            if not same_path:
                continue
            if workspace_id is not None:
                if entry.get("workspace_id") == workspace_id:
                    return entry
                continue
            candidates.append(entry)

        for entry in candidates:
            confirmed_root, _metadata, issue = (
                self._probe_registered_workspace(entry)
            )
            if confirmed_root == root and not issue:
                return entry
        return None

    def _initialize_workspace_registry(self) -> None:
        remembered_registry = []
        seen_workspace_ids = set()
        for item in self._workspace_registry:
            workspace_id = item.get("workspace_id")
            path_text = item.get("path")
            if not isinstance(workspace_id, str) or not workspace_id:
                continue
            if not isinstance(path_text, str) or not path_text:
                continue
            if workspace_id in seen_workspace_ids:
                continue
            seen_workspace_ids.add(workspace_id)

            entry = {
                "workspace_id": workspace_id,
                "path": path_text,
                "last_chat_id": (
                    item.get("last_chat_id")
                    if isinstance(item.get("last_chat_id"), str)
                    else None
                ),
            }
            remembered_registry.append(entry)

        self._workspace_registry = remembered_registry

        if not self._ui_state.get("registry_initialized", False):
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

        candidates = []
        for candidate in (
            active_entry,
            *self._workspace_registry,
        ):
            if candidate is None or candidate in candidates:
                continue
            candidates.append(candidate)

        activated = False
        for candidate in candidates:
            path = Path(candidate["path"])
            if not path.is_dir():
                continue
            try:
                self._activate_workspace(
                    path,
                    preferred_chat_id=candidate.get("last_chat_id"),
                    save=False,
                    workspace_id=candidate["workspace_id"],
                )
            except Exception:
                continue
            activated = True
            break

        if not activated:
            self.current_workspace_id = None
            self.current_chat_id = None
            self._loaded_workspace_root = None
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
            path_text = item["path"]
            path = Path(path_text)
            confirmed_path, info, issue = (
                self._probe_registered_workspace(item)
            )
            chats = []
            if confirmed_path is not None:
                try:
                    chats = list_existing_chats(
                        confirmed_path,
                        expected_workspace_id=item["workspace_id"],
                    )
                    load_existing_project_context(
                        confirmed_path,
                        expected_workspace_id=item["workspace_id"],
                    )
                except Exception:
                    confirmed_path = None
                    info = None
                    issue = "НЕДОСТУПЕН"

            if confirmed_path is None or info is None:
                workspace_row = tk.Frame(frame, bg=field)
                workspace_row.pack(
                    fill="x",
                    padx=2,
                    pady=(4 if index else 2, 2),
                )
                fallback_name = path.name or path_text
                tk.Label(
                    workspace_row,
                    text=f"{fallback_name}  [{issue}]\n{path_text}",
                    anchor="w",
                    justify="left",
                    bg=field,
                    fg=text_color,
                    font=("Segoe UI", 9, "bold"),
                ).pack(side="left", fill="x", expand=True)
                self._sidebar_button(
                    workspace_row,
                    "×",
                    lambda wid=item["workspace_id"]:
                        self._remove_workspace_ui(wid),
                    width=2,
                ).pack(side="left", padx=(2, 0))
                continue

            path = confirmed_path

            active_workspace = (
                item["workspace_id"] == self.current_workspace_id
            )

            workspace_row = tk.Frame(frame, bg=field)
            workspace_row.pack(fill="x", padx=2, pady=(4 if index else 2, 2))

            name_label = tk.Label(
                workspace_row,
                text=("▶ " if active_workspace else "")
                + (info.get("display_name") or path.name),
                anchor="w",
                bg=field,
                fg=text_color,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
            )
            name_label.pack(side="left", fill="x", expand=True)
            name_label.bind(
                "<Button-1>",
                lambda _event, p=path, wid=item["workspace_id"]:
                    self._activate_workspace(p, workspace_id=wid),
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
                lambda wid=item["workspace_id"]:
                    self._remove_workspace_ui(wid),
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
                    lambda _event, p=path, cid=chat["chat_id"],
                    wid=item["workspace_id"]:
                        self._activate_workspace(
                            p,
                            preferred_chat_id=cid,
                            workspace_id=wid,
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
        workspace_id: str | None = None,
    ) -> None:
        if self.running or self.compressor_running:
            return

        root = workspace.resolve()
        entry = self._find_registered_workspace_entry(
            root,
            workspace_id,
        )
        if entry is None:
            raise RuntimeError(
                "Workspace отсутствует в UI registry или его identity "
                "не подтверждена."
            )

        confirmed_root, info, issue = self._probe_registered_workspace(
            entry
        )
        if confirmed_root is None or info is None:
            raise RuntimeError(
                f"Workspace недоступен: {issue or 'НЕДОСТУПЕН'}."
            )
        root = confirmed_root
        chats = list_existing_chats(
            root,
            expected_workspace_id=entry["workspace_id"],
        )
        load_existing_project_context(
            root,
            expected_workspace_id=entry["workspace_id"],
        )

        valid_ids = {item["chat_id"] for item in chats}
        candidate = preferred_chat_id or entry.get("last_chat_id")
        if candidate not in valid_ids:
            candidate = chats[-1]["chat_id"] if chats else None

        if (self.current_workspace_id, self.current_chat_id) != (entry["workspace_id"], candidate):
            self._selected_audit_run_id = None
            self._selected_task_block_id = None
            self._active_audit_run_id = None
        self.current_workspace_id = entry["workspace_id"]
        self.current_chat_id = candidate
        if self._selected_message_chat_id != candidate:
            self._clear_selected_message()
        self._loaded_workspace_root = str(root)
        self.workspace_var.set(str(root))
        if candidate is not None:
            entry["last_chat_id"] = candidate

        if (root / "Документация").is_dir():
            self.write_scope_var.set("Документация")
        else:
            self.write_scope_var.set(".")

        if candidate is not None:
            self._render_current_chat()
        else:
            self._selected_audit_run_id = None
            self._selected_task_block_id = None
            self._task_block_index = {}
            self._task_block_order = []
            self._message_task_block_ids = {}
            self._render_audit_thread()
            self.chat.configure(state="normal")
            self.chat.delete("1.0", "end")
            self.chat.configure(state="disabled")
            self._append_chat(
                "СИСТЕМА",
                "В Workspace пока нет чатов. Используйте кнопку «+».",
                "system",
            )
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
                workspace_id=self.current_workspace_id,
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
            self._activate_workspace(
                workspace,
                workspace_id=self.current_workspace_id,
            )
        if self._loaded_workspace_root != resolved or not self.current_chat_id:
            raise RuntimeError("Workspace/Chat не удалось активировать.")

    def _assistant_label(self, producer: object) -> str:
        if isinstance(producer, dict):
            display_name = producer.get("model_display_name")
            if isinstance(display_name, str) and display_name.strip():
                return f"АССИСТЕНТ · {display_name}"
        return "АССИСТЕНТ"

    @staticmethod
    def _build_task_block_index(
        messages: list[dict], threads: list[dict], chat_id: str,
    ) -> tuple[dict[str, dict], list[str], dict[str, str]]:
        """Rebuild transient UI bindings only from persistent identities."""
        index: dict[str, dict] = {}
        order: list[str] = []
        message_ids: dict[str, str] = {}
        for message in messages:
            task_id = message.get("task_block_id")
            role = message.get("role")
            message_id = message.get("message_id")
            if not task_id:
                continue
            if role == "user":
                if task_id in index:
                    raise RuntimeError(f"Повторный task_block_id в Chat: {task_id}")
                index[task_id] = {
                    "task_block_id": task_id,
                    "chat_id": chat_id,
                    "user_message_id": message_id,
                    "assistant_message_id": None,
                    "run_id": None,
                    "audit_available": False,
                    "ui_start_mark": f"task_block_{task_id}",
                }
                order.append(task_id)
                message_ids[message_id] = task_id
            elif role == "assistant" and task_id in index:
                binding = index[task_id]
                if binding["assistant_message_id"] is not None:
                    raise RuntimeError(f"Повторный Assistant в Task Block: {task_id}")
                binding["assistant_message_id"] = message_id
                binding["run_id"] = get_assistant_audit_run_id(message)
                message_ids[message_id] = task_id
        for thread in threads:
            task_id = thread.get("task_block_id")
            if task_id in index:
                binding = index[task_id]
                run_id = thread["run_id"]
                if binding["audit_available"] and binding["run_id"] != run_id:
                    raise RuntimeError(f"Несколько RUN у Task Block: {task_id}")
                if binding["run_id"] not in (None, run_id):
                    raise RuntimeError(f"RUN identity mismatch для {task_id}")
                binding["run_id"] = run_id
                binding["audit_available"] = True
        return index, order, message_ids

    @staticmethod
    def _task_block_for_viewport(order: list[str], index: dict[str, dict], is_above) -> str | None:
        if not order:
            return None
        active = order[0]
        for task_id in order:
            if is_above(index[task_id]["ui_start_mark"]):
                active = task_id
            else:
                break
        return active

    def _on_chat_yview(self, first: str, last: str) -> None:
        self.chat.vbar.set(first, last)
        first_fraction = float(first)
        if getattr(self, "_chat_rendering", False) or first_fraction == getattr(
            self, "_last_chat_yview_first", None
        ):
            return
        self._last_chat_yview_first = first_fraction
        if self._task_block_order and self._chat_audit_sync_after is None:
            self._chat_audit_sync_after = self.after(40, self._sync_audit_to_viewport)

    def _sync_audit_to_viewport(self) -> None:
        self._chat_audit_sync_after = None
        if not self._task_block_order:
            return
        reference = self.chat.index("@0,0")
        task_id = self._task_block_for_viewport(
            self._task_block_order, self._task_block_index,
            lambda mark: self.chat.compare(mark, "<=", reference),
        )
        if task_id:
            self._select_task_block(task_id)

    def _select_task_block(self, task_id: str, *, reveal: bool = False, force: bool = False) -> None:
        binding = self._task_block_index.get(task_id)
        if binding is None:
            return
        run_id = binding["run_id"]
        changed = (self._selected_task_block_id, self._selected_audit_run_id) != (task_id, run_id)
        self._selected_task_block_id = task_id
        self._selected_audit_run_id = run_id
        if reveal and not self.audit_visible_var.get():
            self.audit_visible_var.set(True)
            self._toggle_audit_panel()
        if changed or force:
            self._render_audit_thread()

    def _render_current_chat(self) -> None:
        if not self.current_chat_id:
            return
        self._chat_rendering = True
        try:
            self._render_current_chat_body()
        finally:
            self.chat.update_idletasks()
            self._chat_rendering = False
            self._last_chat_yview_first = self.chat.yview()[0]

    def _render_current_chat_body(self) -> None:
        if self._chat_audit_sync_after is not None:
            self.after_cancel(self._chat_audit_sync_after)
            self._chat_audit_sync_after = None

        workspace = self._workspace_path_from_ui()
        messages = load_chat_messages(workspace, self.current_chat_id)
        threads = list_chat_audit_threads(
            workspace, self.current_workspace_id, self.current_chat_id
        ) if self.current_workspace_id else []
        previous_task_id = self._selected_task_block_id
        for binding in self._task_block_index.values():
            self.chat.mark_unset(binding["ui_start_mark"])
        self._task_block_index, self._task_block_order, self._message_task_block_ids = (
            self._build_task_block_index(messages, threads, self.current_chat_id)
        )

        for widget in self._message_action_widgets:
            try:
                widget.destroy()
            except tk.TclError:
                pass
        self._message_action_widgets.clear()
        self._message_action_frames.clear()
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")

        if not messages:
            self._selected_audit_run_id = None
            self._selected_task_block_id = None
            self._render_audit_thread()
            self._append_chat(
                "СИСТЕМА",
                "Новый чат. RAW HISTORY пока пуста.",
                "system",
            )
            return

        latest_audit_run_id = None
        for message in messages:
            role = message.get("role")
            message_id = message.get("message_id")
            resolved = None
            if role in {"user", "assistant"}:
                resolved = get_message_working_representation(
                    workspace,
                    self.current_chat_id,
                    message_id,
                )
            text = get_message_display_text(message, resolved)
            if role == "user":
                task_id = message.get("task_block_id")
                if task_id in self._task_block_index:
                    self.chat.configure(state="normal")
                    mark = self._task_block_index[task_id]["ui_start_mark"]
                    self.chat.mark_set(mark, "end-1c")
                    self.chat.mark_gravity(mark, "left")
                    self.chat.configure(state="disabled")
                self._append_chat("ТЫ", text, "user")
            elif role == "assistant":
                latest_audit_run_id = get_assistant_audit_run_id(message) or latest_audit_run_id
                self._append_chat(
                    self._assistant_label(message.get("producer")),
                    text,
                    "assistant",
                )
            else:
                self._append_chat(
                    str(role or "SYSTEM").upper(),
                    text,
                    "system",
                )
            if role in {"user", "assistant"} and resolved is not None:
                self._append_message_actions(message, resolved)

        selected_task_id = (
            previous_task_id if previous_task_id in self._task_block_index
            else self._task_block_order[-1] if self._task_block_order else None
        )
        if selected_task_id:
            self._select_task_block(selected_task_id, force=True)
        elif self._active_audit_run_id is None:
            self._selected_task_block_id = None
            self._selected_audit_run_id = latest_audit_run_id
            self._render_audit_thread()

        if self.selected_message_id:
            try:
                self._select_message(self.selected_message_id)
            except Exception:
                self._clear_selected_message()

    def _add_workspace_dialog(self) -> None:
        if self.running or self.compressor_running:
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
                workspace_id=entry["workspace_id"],
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
        if self.running or self.compressor_running:
            return
        try:
            chat = create_chat(workspace)
            self._activate_workspace(
                workspace,
                preferred_chat_id=chat["chat_id"],
                workspace_id=chat["workspace_id"],
            )
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось создать чат.\n\n"
                f"{type(exc).__name__}: {exc}",
            )

    def _rename_workspace_ui(self, workspace: Path) -> None:
        if self.running or self.compressor_running:
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
        if self.running or self.compressor_running:
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
        if self.running or self.compressor_running:
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
            self.current_workspace_id = None
            self.current_chat_id = None
            self._loaded_workspace_root = None

            activated = False
            for next_item in self._workspace_registry:
                path = Path(next_item["path"])
                if not path.is_dir():
                    continue
                try:
                    self._activate_workspace(
                        path,
                        preferred_chat_id=next_item.get("last_chat_id"),
                        save=False,
                        workspace_id=next_item["workspace_id"],
                    )
                except Exception:
                    continue
                activated = True
                break

            if not activated:
                self._render_workspace_sidebar()
                self.chat.configure(state="normal")
                self.chat.delete("1.0", "end")
                self.chat.configure(state="disabled")

        self._save_ui_state(silent=True)
        self._render_workspace_sidebar()

    def _open_global_ultra_context_editor(self) -> None:
        self._open_agent_context_editor(
            agent_id="ultra",
            window_title="КОНТЕКСТ MAIN CHAT",
            description=(
                "Общий контекст правил MAIN CHAT для всех Workspace. "
                "Существующее локальное storage agent_id='ultra' сохранено."
            ),
        )

    def _open_compressor_role_context_editor(self) -> None:
        self._open_agent_context_editor(
            agent_id="compressor",
            window_title="КОНТЕКСТ РОЛИ COMPRESSOR",
            description=(
                "Независимый Role Context COMPRESSOR: роль, общие правила "
                "и сведения, которые нельзя терять при сжатии."
            ),
        )

    def _open_agent_context_editor(
        self,
        *,
        agent_id: str,
        window_title: str,
        description: str,
    ) -> None:
        try:
            text = load_agent_global_context(
                agent_id,
                allow_missing=True,
            )
            storage_path = get_agent_global_context_path(agent_id)
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось открыть {window_title}.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        window = tk.Toplevel(self)
        window.title(window_title)
        window.geometry("920x700")
        window.minsize(720, 520)
        window.transient(self)

        header = ttk.Frame(window, padding=(10, 10, 10, 0))
        header.pack(fill="x")
        ttk.Label(
            header,
            text=description,
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
                    agent_id,
                )
                if result.get("changed"):
                    messagebox.showinfo(
                        APP_TITLE,
                        f"{window_title} сохранён. "
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
                    f"Не удалось сохранить {window_title}.\n\n"
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

    def _open_compressor_template_editor(self) -> None:
        self._open_compressor_text_template_editor(
            window_title="КОНТЕКСТ СЖАТИЯ",
            description=(
                "Редактируемый контекст сжатия для конкретного SOURCE MESSAGE. "
                "Поддерживаются только {{REDUCTION_PERCENT}} и "
                "{{REMAINING_PERCENT}}."
            ),
            load_template=load_message_compression_template,
            get_template_path=get_message_compression_template_path,
            save_template=save_message_compression_template,
        )

    def _open_compressor_final_check_template_editor(self) -> None:
        self._open_compressor_text_template_editor(
            window_title="КОНТЕКСТ ДОПОЛНИТЕЛЬНОЙ ПРОВЕРКИ",
            description=(
                "Редактируемый контекст дополнительной проверки COMPRESSOR. "
                "Галочка в основном окне определяет, включать ли этот блок "
                "в prompt. Поддерживаются {{REDUCTION_PERCENT}} и "
                "{{REMAINING_PERCENT}}."
            ),
            load_template=load_final_check_template,
            get_template_path=get_final_check_template_path,
            save_template=save_final_check_template,
        )

    def _open_compressor_text_template_editor(
        self,
        *,
        window_title: str,
        description: str,
        load_template,
        get_template_path,
        save_template,
    ) -> None:
        try:
            text = load_template()
            storage_path = get_template_path()
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Не удалось открыть {window_title}.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        window = tk.Toplevel(self)
        window.title(window_title)
        window.geometry("920x700")
        window.minsize(720, 520)
        window.transient(self)

        header = ttk.Frame(window, padding=(10, 10, 10, 0))
        header.pack(fill="x")
        ttk.Label(
            header,
            text=description,
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
        editor.insert("1.0", text)
        bind_edit_shortcuts(editor)

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=10, pady=(0, 10))

        def save_current_template() -> None:
            try:
                result = save_template(
                    editor.get("1.0", "end-1c")
                )
                message = (
                    f"{window_title} сохранён."
                    if result.get("changed")
                    else "Изменений нет."
                )
                messagebox.showinfo(APP_TITLE, message, parent=window)
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    f"Не удалось сохранить {window_title}.\n\n"
                    f"{type(exc).__name__}: {exc}",
                    parent=window,
                )

        ttk.Button(
            buttons,
            text="Сохранить",
            command=save_current_template,
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

    def _clear_selected_message(self) -> None:
        self.selected_message_id = None
        self._selected_message_chat_id = None
        self.compressor_message_id_var.set("—")
        self.compressor_status_var.set("не выбрано")

    def _context_status_text(self, resolved: dict) -> str:
        state = resolved["state"]
        if state["active_representation"] == "raw":
            return "FULL"
        variant = resolved.get("variant") or {}
        compression = variant.get("compression") or {}
        model_name = compression.get("model_display_name")
        reduction = compression.get("actual_reduction_percent")
        parts = ["COMPRESSED"]
        if isinstance(model_name, str) and model_name.strip():
            parts.append(model_name.strip())
        if isinstance(reduction, (int, float)):
            parts.append(f"{reduction:.0f}%")
        return " · ".join(parts)

    def _select_message(self, message_id: str) -> None:
        if not self.current_chat_id:
            self._clear_selected_message()
            return
        workspace = self._workspace_path_from_ui()
        resolved = get_message_working_representation(
            workspace, self.current_chat_id, message_id
        )
        self.selected_message_id = message_id
        self._selected_message_chat_id = self.current_chat_id
        self.compressor_message_id_var.set(message_id)
        self.compressor_status_var.set(self._context_status_text(resolved))
        task_id = self._message_task_block_ids.get(message_id)
        if task_id:
            self._select_task_block(task_id)

    def _append_message_actions(self, message: dict, resolved: dict) -> None:
        message_id = message["message_id"]
        frame = ttk.Frame(self.chat)
        compress_button = ttk.Button(
            frame,
            text="Сжать",
            command=lambda mid=message_id: self._start_message_compression(mid),
        )
        edit_button = ttk.Button(
            frame,
            text="✎",
            width=3,
            command=lambda mid=message_id: self._open_message_context_editor(mid),
        )
        original_button = ttk.Button(
            frame,
            text="Оригинал",
            command=lambda mid=message_id: self._open_original_message(mid),
        )
        compress_button.pack(side="left")
        edit_button.pack(side="left", padx=(4, 0))
        original_button.pack(side="left", padx=(4, 0))
        task_id = self._message_task_block_ids.get(message_id)
        binding = self._task_block_index.get(task_id) if task_id else None
        run_id = binding["run_id"] if binding and binding["audit_available"] else get_assistant_audit_run_id(message)
        if run_id and binding and binding["audit_available"]:
            ttk.Button(
                frame, text="Разбор",
                command=lambda tid=task_id: self._select_task_block(tid, reveal=True, force=True),
            ).pack(side="left", padx=(4, 0))
        elif run_id:
            ttk.Button(
                frame, text="Разбор",
                command=lambda rid=run_id: self._show_audit_thread(rid),
            ).pack(side="left", padx=(4, 0))
        status_label = ttk.Label(
            frame,
            text=self._context_status_text(resolved),
            cursor="hand2",
        )
        status_label.pack(side="left", padx=(8, 0))
        status_label.bind(
            "<Button-1>",
            lambda _event, mid=message_id: self._select_message(mid),
        )
        if (
            resolved["state"]["active_representation"] != "raw"
            or self.running
            or self.compressor_running
        ):
            compress_button.configure(state="disabled")
        if self.running or self.compressor_running:
            edit_button.configure(state="disabled")
            original_button.configure(state="disabled")
        self.chat.configure(state="normal")
        self.chat.window_create("end", window=frame)
        self.chat.insert("end", "\n\n")
        self.chat.configure(state="disabled")
        self._message_action_widgets.append(frame)
        self._message_action_frames[message_id] = frame

    def _ensure_task_audit_button(self, task_id: str) -> None:
        binding = self._task_block_index.get(task_id)
        if not binding or not binding["audit_available"]:
            return
        frame = self._message_action_frames.get(binding["user_message_id"])
        if frame is None or any(
            isinstance(child, ttk.Button) and child.cget("text") == "Разбор"
            for child in frame.winfo_children()
        ):
            return
        ttk.Button(
            frame, text="Разбор",
            command=lambda tid=task_id: self._select_task_block(tid, reveal=True, force=True),
        ).pack(side="left", padx=(4, 0))

    def _begin_context_operation(self, message_id: str, status: str) -> None:
        if self.running:
            raise RuntimeError("Дождитесь завершения MAIN CHAT RUN.")
        if self.compressor_running:
            raise RuntimeError("Другая операция с контекстом уже выполняется.")
        self._select_message(message_id)
        self.compressor_running = True
        self.status_var.set(status)
        self._set_run_controls_enabled(False)

    def _finish_context_operation(
        self,
        status: str = "Готово",
        *,
        rerender: bool = True,
    ) -> None:
        self.compressor_running = False
        self.status_var.set(status)
        if not self.running:
            self._set_run_controls_enabled(True)
        if rerender and self.current_chat_id:
            self._render_current_chat()

    def _start_message_compression(self, message_id: str) -> None:
        try:
            workspace = self._workspace_path_from_ui()
            chat_id = self.current_chat_id
            if not chat_id:
                raise RuntimeError("Не выбран активный чат.")
            state = get_message_context_state(workspace, chat_id, message_id)
            if state["active_representation"] != "raw":
                raise RuntimeError(
                    "Сообщение уже сжато. Сначала восстановите RAW в контекст."
                )
            model_id = self.compressor_model_id_var.get()
            reduction = validate_reduction_percent(
                int(self.compressor_reduction_percent_var.get().strip())
            )
            final_check = bool(self.compressor_final_check_enabled_var.get())
            self._begin_context_operation(message_id, "COMPRESSOR работает...")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=self)
            return

        thread = threading.Thread(
            target=self._compressor_worker,
            args=(
                str(workspace),
                chat_id,
                message_id,
                model_id,
                reduction,
                final_check,
            ),
            daemon=True,
        )
        thread.start()

    def _compressor_worker(
        self,
        workspace: str,
        chat_id: str,
        message_id: str,
        model_id: str,
        reduction: int,
        final_check: bool,
    ) -> None:
        def on_event(event: dict) -> None:
            try:
                self.trace_events.put_nowait(event)
            except queue.Full:
                pass

        try:
            # The source is always reloaded by immutable identity in the worker.
            raw_message = load_raw_message(workspace, chat_id, message_id)
            result = asyncio.run(
                run_message_compressor_task_detailed(
                    workspace,
                    chat_id,
                    message_id,
                    compressor_model_id=model_id,
                    reduction_percent=reduction,
                    final_check_enabled=final_check,
                    on_event=on_event,
                )
            )
            self.events.put(
                (
                    "compressor_success",
                    {
                        "workspace": workspace,
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "raw_text": raw_message["original_text"],
                        "result": result,
                    },
                )
            )
        except Exception as exc:
            self.events.put(
                ("compressor_error", f"{type(exc).__name__}: {exc}")
            )

    def _open_compression_proposal(self, payload: dict) -> None:
        workspace = payload["workspace"]
        chat_id = payload["chat_id"]
        message_id = payload["message_id"]
        raw_text = payload["raw_text"]
        result: CompressorRunResult = payload["result"]

        window = tk.Toplevel(self)
        window.title("COMPRESSION PROPOSAL")
        window.geometry("1000x760")
        window.transient(self)
        window.grab_set()

        info = ttk.Label(
            window,
            text=(
                f"Message ID: {message_id}\n"
                f"Model: {result.model_display_name}\n"
                f"Target: {result.target_reduction_percent}%   "
                f"Actual: {result.actual_reduction_percent:.2f}%   "
                f"Chars: {result.source_chars} → {result.output_chars}"
            ),
            justify="left",
        )
        info.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(window, text="Исходный RAW (read-only)").pack(
            anchor="w", padx=10
        )
        raw_view = scrolledtext.ScrolledText(window, height=12, wrap="word")
        raw_view.pack(fill="both", expand=True, padx=10, pady=(2, 8))
        raw_view.insert("1.0", raw_text)
        raw_view.configure(state="disabled")
        ttk.Label(window, text="Предлагаемая рабочая версия").pack(
            anchor="w", padx=10
        )
        editor = scrolledtext.ScrolledText(
            window, height=12, wrap="word", undo=True
        )
        editor.pack(fill="both", expand=True, padx=10, pady=(2, 8))
        editor.insert("1.0", result.text)
        bind_edit_shortcuts(editor)

        closed = False

        def close_proposal(status: str) -> None:
            nonlocal closed
            if closed:
                return
            closed = True
            try:
                window.grab_release()
            except tk.TclError:
                pass
            window.destroy()
            self._finish_context_operation(status)

        def accept() -> None:
            accepted_text = editor.get("1.0", "end-1c")
            if not accepted_text.strip():
                messagebox.showerror(
                    APP_TITLE,
                    "Рабочая версия не может быть пустой.",
                    parent=window,
                )
                return
            manually_edited = accepted_text != result.text
            accepted_output_chars = len(accepted_text)
            accepted_reduction = (
                round(
                    (1.0 - (accepted_output_chars / len(raw_text))) * 100.0,
                    2,
                )
                if raw_text
                else 0.0
            )
            compression = {
                "role_id": "compressor",
                "run_id": result.run_id,
                "model_id": result.model_id,
                "model_display_name": result.model_display_name,
                "provider": result.provider,
                "provider_model_id": result.provider_model_id,
                "target_reduction_percent": result.target_reduction_percent,
                "actual_reduction_percent": accepted_reduction,
                "source_chars": len(raw_text),
                "output_chars": accepted_output_chars,
                "attempts": result.attempts,
                "final_check_enabled": result.final_check_enabled,
            }
            try:
                create_message_context_variant(
                    workspace,
                    chat_id,
                    message_id,
                    accepted_text,
                    source="llm_compression",
                    manually_edited=manually_edited,
                    compression=compression,
                    require_raw=True,
                )
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    f"Не удалось принять proposal.\n\n{type(exc).__name__}: {exc}",
                    parent=window,
                )
                return
            close_proposal("Сжатая версия принята")

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(buttons, text="Принять", command=accept).pack(side="left")
        ttk.Button(
            buttons,
            text="Отклонить",
            command=lambda: close_proposal("Proposal отклонён"),
        ).pack(side="right")
        window.protocol(
            "WM_DELETE_WINDOW", lambda: close_proposal("Proposal отклонён")
        )

    def _open_message_context_editor(self, message_id: str) -> None:
        try:
            workspace = self._workspace_path_from_ui()
            chat_id = self.current_chat_id
            if not chat_id:
                raise RuntimeError("Не выбран активный чат.")
            resolved = get_message_working_representation(
                workspace, chat_id, message_id
            )
            self._begin_context_operation(message_id, "Редактирование контекста")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=self)
            return

        parent_variant_id = resolved["state"]["active_variant_id"]
        title = (
            "Редактировать рабочую версию"
            if parent_variant_id
            else "Создать рабочую версию вручную"
        )
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry("900x650")
        window.transient(self)
        window.grab_set()
        editor = scrolledtext.ScrolledText(window, wrap="word", undo=True)
        editor.pack(fill="both", expand=True, padx=10, pady=10)
        editor.insert("1.0", resolved["text"])
        bind_edit_shortcuts(editor)

        closed = False

        def close(status: str = "Изменения отменены") -> None:
            nonlocal closed
            if closed:
                return
            closed = True
            try:
                window.grab_release()
            except tk.TclError:
                pass
            window.destroy()
            self._finish_context_operation(status)

        def save() -> None:
            text = editor.get("1.0", "end-1c")
            try:
                create_message_context_variant(
                    workspace,
                    chat_id,
                    message_id,
                    text,
                    source="manual_edit",
                    parent_variant_id=parent_variant_id,
                    manually_edited=True,
                )
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    f"Не удалось сохранить рабочую версию.\n\n"
                    f"{type(exc).__name__}: {exc}",
                    parent=window,
                )
                return
            close("Рабочая версия сохранена")

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(buttons, text="Сохранить", command=save).pack(side="left")
        ttk.Button(buttons, text="Отмена", command=close).pack(side="right")
        window.protocol("WM_DELETE_WINDOW", close)

    def _open_original_message(self, message_id: str) -> None:
        try:
            workspace = self._workspace_path_from_ui()
            chat_id = self.current_chat_id
            if not chat_id:
                raise RuntimeError("Не выбран активный чат.")
            raw = load_raw_message(workspace, chat_id, message_id)
            state = get_message_context_state(workspace, chat_id, message_id)
            self._begin_context_operation(message_id, "Просмотр RAW MESSAGE")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=self)
            return

        window = tk.Toplevel(self)
        window.title("Исходное сообщение")
        window.geometry("900x650")
        window.transient(self)
        window.grab_set()
        ttk.Label(
            window,
            text=(
                f"ID: {message_id}\n"
                + (
                    "Сейчас RAW уже используется в контексте."
                    if state["active_representation"] == "raw"
                    else "Сейчас в контексте используется сжатая версия."
                )
            ),
            justify="left",
        ).pack(fill="x", padx=10, pady=(10, 6))
        viewer = scrolledtext.ScrolledText(window, wrap="word")
        viewer.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        viewer.insert("1.0", raw["original_text"])
        viewer.configure(state="disabled")
        closed = False

        def close(status: str = "Готово") -> None:
            nonlocal closed
            if closed:
                return
            closed = True
            try:
                window.grab_release()
            except tk.TclError:
                pass
            window.destroy()
            self._finish_context_operation(status)

        def restore() -> None:
            try:
                restore_message_raw(workspace, chat_id, message_id)
            except Exception as exc:
                messagebox.showerror(
                    APP_TITLE,
                    f"Не удалось восстановить RAW.\n\n{type(exc).__name__}: {exc}",
                    parent=window,
                )
                return
            close("RAW восстановлен в контекст")

        buttons = ttk.Frame(window)
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        if state["active_representation"] == "summary":
            ttk.Button(
                buttons,
                text="Восстановить в контекст",
                command=restore,
            ).pack(side="left")
        ttk.Button(buttons, text="Закрыть", command=close).pack(side="right")
        window.protocol("WM_DELETE_WINDOW", close)

    def _append_chat(self, author: str, text: str, tag: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{author}:\n", tag)
        self.chat.insert("end", f"{text.strip()}\n\n", tag)
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def _show_audit_thread(self, run_id: str) -> None:
        self._selected_task_block_id = None
        self._selected_audit_run_id = run_id
        if not self.audit_visible_var.get():
            self.audit_visible_var.set(True)
            self._toggle_audit_panel()
        self._render_audit_thread()

    @staticmethod
    def _audit_segments(
        thread: dict | None, run_id: str | None, task_block_id: str | None = None,
    ) -> list[tuple[str, str]]:
        task_label = task_block_id or (thread or {}).get("task_block_id") or (
            "LEGACY" if run_id else "—"
        )
        status = (thread.get("run_status") or "RUNNING") if thread else "—"
        final_audit = (thread.get("final_audit") or "PENDING") if thread else "NOT_RUN"
        segments = [("metadata", (
            f"TASK BLOCK: {task_label}\nRUN: {run_id or '—'}\n"
            f"RUN STATUS: {status}\nFINAL AUDIT: {final_audit}\n\n"
        ))]
        if not run_id:
            segments.append(("metadata", "Выберите Task Block, чтобы открыть разбор RUN.\n"))
            return segments
        if thread is None:
            segments.append(("metadata", "Для этого RUN нет событий разбора.\n"))
            return segments
        permissions = thread.get("permission_escalations") or {}
        if not permissions and thread.get("permission_escalation"):
            permissions = {"legacy": thread["permission_escalation"]}
        for permission in permissions.values():
            capability = permission.get("capability") or "—"
            segments.append(("metadata", "SERVER PERMISSION CONTROL\n"))
            segments.append(("audit", f"{capability} был отключён при запросе.\n"))
            for attempt in permission.get("attempts") or []:
                segments.append(("dredd_fail", (
                    f"#{attempt.get('attempt')} {attempt.get('tool')} "
                    f"{attempt.get('path') or ''} → DENIED\n"
                )))
            if permission.get("verifier_run_id"):
                segments.append(("metadata", "DREDD PERMISSION REVIEW\n"))
                segments.append(("audit", f"{permission.get('verifier_reason') or '—'}\n"))
            if permission.get("user_decision"):
                segments.append(("metadata", "РЕШЕНИЕ ПОЛЬЗОВАТЕЛЯ\n"))
                segments.append(("audit", f"{permission['user_decision']}\n"))
            status = permission.get("status") or "PENDING"
            status_tag = ("dredd_fail" if status in {"DENIED", "BLOCKED", "NOT_JUSTIFIED"}
                          else "resolved" if status == "GRANTED" else "metadata")
            segments.append((status_tag, f"PERMISSION: {status}\n\n"))
        consistency = thread.get("execution_consistency")
        if consistency:
            segments.append(("metadata", "EXECUTION CONSISTENCY\n"))
            for item in consistency.get("events") or []:
                kind = item.get("event")
                label = {
                    "execution_consistency_detected": "SERVER SELF-CHECK: TASK предполагает изменение, в RUN нет mutation",
                    "execution_consistency_feedback_delivered": "SERVER FEEDBACK → повторная попытка",
                    "execution_consistency_recheck_started": "Повторная попытка завершилась без mutation",
                    "execution_consistency_verifier_started": "DREDD CONSISTENCY → независимая проверка",
                    "execution_consistency_verifier_passed": "DREDD CONSISTENCY PASS",
                    "execution_consistency_verifier_failed": "DREDD CONSISTENCY FAIL",
                    "execution_consistency_correction_started": "TARGETED CORRECTION → Executor",
                    "execution_consistency_resolved": "CONSISTENCY RESOLVED",
                    "execution_consistency_terminal": "CONSISTENCY UNRESOLVED",
                }.get(kind, kind)
                segments.append(("dredd_fail" if kind in {
                    "execution_consistency_verifier_failed", "execution_consistency_terminal"
                } else "metadata", f"{label}\n"))
                if item.get("mutation_intent"):
                    segments.append(("audit", f"Mutation intent: {item['mutation_intent']}\n"))
                if item.get("verifier_run_id"):
                    segments.append(("metadata", f"Verifier RUN: {item['verifier_run_id']}\n"))
                if item.get("reason"):
                    segments.append(("audit", f"Причина: {item['reason']}\n"))
                for violation in item.get("violations") or []:
                    segments.append(("audit", f"• {violation}\n"))
                if item.get("required_action"):
                    segments.append(("audit", f"Требуется: {item['required_action']}\n"))
            activity = consistency.get("correction_activity") or []
            if activity:
                segments.append(("metadata", "CORRECTION TOOLS\n"))
                for item in activity:
                    segments.append(("audit", f"#{item.get('tool_sequence')} {item.get('tool_name')} {item.get('path') or ''} → {item.get('status')}\n"))
            segments.append(("resolved" if consistency.get("status") == "RESOLVED" else "dredd_fail",
                             f"CONSISTENCY: {consistency.get('status', 'PENDING')}\n\n"))
        issues = thread.get("issues") or []
        for issue in issues:
            segments.append(("dredd_fail", f"СУДЬЯ ДРЕДД — FAIL · попытка {issue.get('audit_attempt')}\n"))
            segments.append(("audit", f"Причина: {issue.get('reason') or '—'}\n"))
            for violation in issue.get("violations") or []:
                segments.append(("audit", f"• {violation}\n"))
            segments.append(("audit", f"Требуется: {issue.get('required_action') or '—'}\n"))
            segments.append(("metadata", f"Verifier RUN: {issue.get('verifier_run_id') or '—'}\n"))
            question = issue.get("diagnostic_question")
            if question:
                segments.append(("metadata", f"\nВОПРОС ОТВЕТЧИКУ\n{question}\n"))
            if issue.get("diagnostic_answer"):
                segments.append(("ultra", f"\nОТВЕТЧИК — ULTRA\n{issue['diagnostic_answer']}\n"))
            elif issue.get("diagnostic_error"):
                segments.append(("dredd_fail", f"\nДиагностика недоступна: {issue['diagnostic_error']}\n"))
            activity = issue.get("correction_activity") or []
            if activity:
                segments.append(("metadata", "\nCORRECTION ACTIVITY\n"))
                for item in activity:
                    path = f" · {item['path']}" if item.get("path") else ""
                    segments.append(("audit", f"#{item.get('tool_sequence')} {item.get('tool_name')}{path} → {item.get('status')}\n"))
            result = issue.get("result") or "PENDING"
            segments.append(("resolved" if result == "RESOLVED" else "metadata", f"RESULT: {result}\n\n"))
        resolved = sum(issue.get("result") == "RESOLVED" for issue in issues)
        unresolved = sum(issue.get("result") == "UNRESOLVED" for issue in issues)
        segments.append(("metadata", "ИТОГ RUN\n"))
        segments.append(("audit", f"Замечаний Судьи Дредда: {len(issues)}\nИсправлено: {resolved}\nНерешённых: {unresolved}\n"))
        final = thread.get("final_audit") or "PENDING"
        segments.append(("resolved" if final == "PASS" else "metadata", f"Final Audit: {final}\n"))
        return segments

    def _render_audit_thread(self) -> None:
        widget = getattr(self, "audit_text", None)
        if widget is None:
            return
        run_id = self._selected_audit_run_id
        thread = None
        if run_id and self.current_workspace_id and self.current_chat_id:
            try:
                thread = load_audit_thread(
                    self.workspace_var.get(), self.current_workspace_id,
                    self.current_chat_id, run_id,
                )
            except Exception:
                thread = None
        widget.configure(state="normal")
        try:
            widget.delete("1.0", "end")
            for tag, text in self._audit_segments(
                thread, run_id, getattr(self, "_selected_task_block_id", None)
            ):
                widget.insert("end", text, tag)
            widget.see("end")
        finally:
            widget.configure(state="disabled")

    def _append_trace(self, line: str, tag: str = "trace") -> None:
        self.trace_log.configure(state="normal")
        try:
            self.trace_log.insert("end", f"{line}\n", tag)
            self.trace_log.see("end")
        finally:
            self.trace_log.configure(state="disabled")

    @staticmethod
    def _compact_event_arguments(arguments: object) -> str:
        if not isinstance(arguments, dict):
            return "<invalid arguments>"
        compact = []
        for key, value in arguments.items():
            if key in {"content", "old_text", "new_text", "marker", "text"}:
                if isinstance(value, str) and value.startswith("<") and value.endswith(" chars>"):
                    shown = value
                else:
                    shown = f"<{len(str(value))} chars>"
            else:
                shown = str(value)[:160]
            compact.append(f"{key}={shown}")
        return ", ".join(compact)[:600]

    def _format_event(self, event: dict) -> str:
        event_type = event.get("event")
        run_id = event.get("run_id", "")
        timestamp = event.get("timestamp")
        time_str = (
            time.strftime("%H:%M:%S", time.localtime(timestamp))
            if timestamp
            else "--:--:--"
        )

        if event_type == "compressor_run_started":
            return (
                f"[{time_str}] COMPRESSOR START | {run_id} | "
                f"MODEL={event.get('model_display_name')} "
                f"[{event.get('provider_model_id')}] | "
                f"TARGET={event.get('target_reduction_percent')}% | "
                f"FINAL_CHECK={event.get('final_check_enabled')}"
            )

        if event_type == "compressor_attempt_finished":
            actual = event.get("actual_reduction_percent")
            actual_text = f"{actual:.2f}%" if isinstance(actual, (int, float)) else "?"
            return (
                f"[{time_str}] COMPRESSOR ATTEMPT "
                f"#{event.get('attempt')} | {run_id} | "
                f"{event.get('source_chars')} -> {event.get('output_chars')} chars | "
                f"ACTUAL={actual_text} | GUARD={event.get('guard_status')}"
            )

        if event_type == "compressor_run_finished":
            actual = event.get("actual_reduction_percent")
            actual_text = f"{actual:.2f}%" if isinstance(actual, (int, float)) else "?"
            return (
                f"[{time_str}] COMPRESSOR FINISH | {run_id} | "
                f"ATTEMPTS={event.get('attempts')} | ACTUAL={actual_text} | "
                f"GUARD={event.get('guard_status')} | "
                f"{event.get('duration', 0):.2f}s"
            )

        if event_type == "run_started":
            task_preview = event.get("task_preview", "")
            perms = event.get("permissions", {})
            model_display_name = event.get("model_display_name", "?")
            provider_model_id = event.get("provider_model_id", "?")
            return (
                f"[{time_str}] RUN START | {run_id} | "
                f"MODEL={model_display_name} [{provider_model_id}] | "
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
                f"raw={event.get('raw_messages')} | "
                f"compressed={event.get('compressed_messages')} | "
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
            func = event.get("function")
            return (
                f"[{time_str}] PERMISSION DENIED | capability={event.get('capability')} "
                f"| attempt={event.get('attempt')} | tool={func}"
            )

        if event_type.startswith("permission_"):
            return (f"[{time_str}] {event_type.upper()} | "
                    f"capability={event.get('capability')} | "
                    f"reason={str(event.get('reason') or event.get('verifier_reason') or '')[:200]}")

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
            args_str = self._compact_event_arguments(args)
            return f"[{time_str}] TOOL #{seq} {func}({args_str})"

        if event_type == "tool_finished":
            seq = event.get("tool_sequence")
            func = event.get("function")
            arguments = event.get("arguments") or {}
            path = str(arguments.get("path") or "")[:160] if isinstance(arguments, dict) else ""
            duration = event.get("duration")
            dur_str = f" | {duration:.2f} s" if isinstance(duration, (int, float)) else ""
            path_str = f" | path={path}" if path else ""
            return f"[{time_str}] TOOL #{seq} {func} -> OK{path_str}{dur_str}"

        if event_type == "tool_error":
            seq = event.get("tool_sequence")
            func = event.get("function")
            arguments = event.get("arguments") or {}
            path = str(arguments.get("path") or "")[:160] if isinstance(arguments, dict) else ""
            path_str = f" | path={path}" if path else ""
            error = event.get("error", {})
            return (
                f"[{time_str}] TOOL #{seq} {func} -> ERROR{path_str} "
                f"({error.get('type', '')}): {str(error.get('message', ''))[:300]}"
            )

        if event_type == "mutation_intent_classified":
            reasons = "; ".join(str(item)[:140] for item in (event.get("reasons") or [])[:3])
            return (
                f"[{time_str}] MUTATION INTENT | {event.get('mutation_intent')} | "
                f"RUN {run_id} | {reasons}"
            )

        if event_type.startswith("execution_consistency_"):
            label = event_type.removeprefix("execution_consistency_").upper().replace("_", " ")
            return (
                f"[{time_str}] EXECUTION CONSISTENCY {label} | RUN {run_id} | "
                f"attempt={event.get('attempt')} | verifier={event.get('verifier_run_id')} | "
                f"reason={str(event.get('reason') or '')[:180]}"
            )

        if event_type == "final_audit_started":
            return (
                f"[{time_str}] СУДЬЯ ДРЕДД — START | RUN {run_id} | "
                f"model={event.get('model_id')} | revision={event.get('write_revision')}"
            )

        if event_type == "final_audit_retry_evaluated":
            return (
                f"[{time_str}] RETRY POLICY → {event.get('decision')} | RUN {run_id} | "
                f"attempt={event.get('audit_attempt')} | "
                f"progress={event.get('progress_class')} | "
                f"reason={str(event.get('decision_reason') or '')[:160]}"
            )

        if event_type == "final_audit_feedback_delivered":
            return (
                f"[{time_str}] DREDD FEEDBACK → EXECUTOR | RUN {run_id} | "
                f"cycle {event.get('correction_cycle')}/{event.get('correction_limit')} | "
                f"violations={event.get('violations_count')}"
            )

        if event_type == "final_audit_correction_started":
            return (
                f"[{time_str}] CORRECTION START | RUN {run_id} | "
                f"cycle {event.get('correction_cycle')}/{event.get('correction_limit')}"
            )

        if event_type == "final_audit_failed":
            violations = event.get("violations") or []
            shown = "; ".join(str(item)[:120] for item in violations[:5])
            return (
                f"[{time_str}] СУДЬЯ ДРЕДД FAIL | RUN {run_id} | "
                f"attempt={event.get('audit_attempt')} | verifier={event.get('verifier_run_id')} | "
                f"reason={str(event.get('reason') or '')[:250]} | "
                f"violations={shown} | action={str(event.get('required_action') or '')[:250]}"
            )

        if event_type in {"audit_diagnostic_question", "audit_diagnostic_answer", "audit_diagnostic_error"}:
            label = {
                "audit_diagnostic_question": "ВОПРОС ОТВЕТЧИКУ",
                "audit_diagnostic_answer": "ОТВЕТЧИК ULTRA",
                "audit_diagnostic_error": "DIAGNOSTIC ERROR",
            }[event_type]
            return f"[{time_str}] {label} | RUN {run_id} | {str(event.get('text') or '')[:600]}"

        if event_type == "final_audit_passed":
            return f"[{time_str}] СУДЬЯ ДРЕДД PASS | RUN {run_id} | attempt={event.get('audit_attempt')}"

        if event_type == "final_audit_error":
            return f"[{time_str}] FINAL AUDIT ERROR | RUN {run_id} | {str(event.get('reason') or '')[:300]}"

        if event_type == "audit_storage_error":
            return f"[{time_str}] AUDIT STORAGE ERROR | RUN {run_id} | {str(event.get('error_type') or '')[:100]}"

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
        if self.running or self.compressor_running:
            messagebox.showinfo(
                APP_TITLE,
                "Дождитесь завершения текущей операции.",
            )
            return

        workspace_text = self.workspace_var.get().strip().strip('"')
        task = self.input_box.get("1.0", "end").strip()
        if not task:
            messagebox.showwarning(
                APP_TITLE,
                "Введи сообщение для ассистента.",
            )
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

        model_id = self.main_chat_model_id_var.get()
        verifier_model_id = self.verifier_model_id_var.get()
        try:
            selected_model = get_model_spec(model_id)
            get_model_spec(verifier_model_id)
        except (KeyError, RuntimeError, ValueError) as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        try:
            self._ensure_workspace_ui_current(workspace)
            if not self.current_chat_id:
                raise RuntimeError("Не выбран активный чат.")
            task_block_id = new_task_block_id()
            stored_user_message = append_raw_message(
                workspace,
                self.current_chat_id,
                "user",
                task,
                task_block_id=task_block_id,
            )
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE,
                "Не удалось сохранить RAW MESSAGE до отправки.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        self._render_current_chat()
        self._select_message(stored_user_message["message_id"])
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
        self._running_model_display_name = selected_model.display_name
        self.status_var.set(
            f"{self._running_model_display_name} работает..."
        )
        self.progress.start(12)
        self._set_run_controls_enabled(False)

        thread = threading.Thread(
            target=self._worker,
            args=(
                task,
                str(workspace),
                permissions,
                self.current_chat_id,
                model_id,
                verifier_model_id,
                task_block_id,
            ),
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
        for widget in self._compressor_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass
        for widget in self._workspace_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass
        for frame in self._message_action_widgets:
            try:
                for widget in frame.winfo_children():
                    if isinstance(widget, ttk.Button) and widget.cget("text") != "Разбор":
                        widget.configure(state=state)
            except tk.TclError:
                pass

    def _worker(
        self,
        task: str,
        workspace: str,
        permissions: dict,
        chat_id: str,
        model_id: str,
        verifier_model_id: str,
        task_block_id: str | None = None,
    ) -> None:
        producer_snapshot: dict | None = None
        provenance_warning: str | None = None
        run_started_seen = False
        final_run_status = "SUCCESS"

        def on_event(event: dict):
            nonlocal producer_snapshot, provenance_warning, run_started_seen, final_run_status
            if event.get("event") == "run_finished":
                final_run_status = str(event.get("status") or "SUCCESS")
            if event.get("event") == "run_started" and not run_started_seen:
                run_started_seen = True
                actual_model_id = event.get("model_id")
                if actual_model_id != model_id:
                    provenance_warning = (
                        "Provenance не сохранена: model_id RUN не совпал "
                        f"с зафиксированным выбором ({actual_model_id!r} != "
                        f"{model_id!r})."
                    )
                else:
                    snapshot = {
                        "kind": "llm",
                        "role_id": "main_chat",
                        "run_id": event.get("run_id"),
                        "model_id": actual_model_id,
                        "model_display_name": event.get(
                            "model_display_name"
                        ),
                        "provider": event.get("provider"),
                        "provider_model_id": event.get(
                            "provider_model_id"
                        ),
                    }
                    invalid_fields = [
                        key
                        for key, value in snapshot.items()
                        if not isinstance(value, str) or not value.strip()
                    ]
                    if invalid_fields:
                        provenance_warning = (
                            "Provenance не сохранена: run_started содержит "
                            "неполные поля: "
                            + ", ".join(invalid_fields)
                            + "."
                        )
                    else:
                        producer_snapshot = snapshot
            try:
                self.trace_events.put_nowait(event)
            except queue.Full:
                pass

        def permission_request_callback(payload: dict) -> bool:
            ready = threading.Event()
            answer = {"granted": False}
            self.events.put(("permission_request", {
                "payload": payload, "ready": ready, "answer": answer,
            }))
            ready.wait()
            return answer["granted"] is True

        try:
            result = asyncio.run(
                run_agent_task(
                    task,
                    workspace,
                    on_event=on_event,
                    permissions=permissions,
                    chat_id=chat_id,
                    model_id=model_id,
                    verifier_model_id=verifier_model_id,
                    task_block_id=task_block_id,
                    permission_request_callback=permission_request_callback,
                )
            )
            if not run_started_seen and provenance_warning is None:
                provenance_warning = (
                    "Provenance не сохранена: событие run_started не получено."
                )

            stored_message = append_raw_message(
                workspace,
                chat_id,
                "assistant",
                result,
                producer=producer_snapshot,
                task_block_id=task_block_id,
            )
            self.events.put(
                (
                    "success",
                    {
                        "text": result,
                        "producer": stored_message.get("producer"),
                        "provenance_warning": provenance_warning,
                        "run_status": final_run_status,
                    },
                )
            )
        except Exception as exc:
            self.events.put(("error", f"{type(exc).__name__}: {exc}"))

    def _open_permission_request(self, request: dict) -> None:
        """Called only by Tk's event poller, never by the worker thread."""
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("Permission dialog must run on the Tk main thread.")
        payload = request["payload"]
        capability = payload["capability"]
        window = tk.Toplevel(self)
        window.title(f"ТРЕБУЕТСЯ РАЗРЕШЕНИЕ {capability}")
        window.transient(self)
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=(
            f"Для завершения текущей задачи требуется {capability}.\n"
            f"Executor дважды запросил {capability}, но capability отключена.\n"
            "Ни одна запрещённая операция не была выполнена.\n\n"
            f"Проверка задачи подтверждает необходимость {capability}.\n"
            f"Текущая область: {payload['scope']}\n"
            f"Последний requested path: {payload['last_requested_path']}\n\n"
            f"Разрешить {capability} для ТЕКУЩЕГО RUN?"
        ), justify="left", wraplength=470).pack(anchor="w")

        def decide(granted: bool) -> None:
            if request["ready"].is_set():
                return
            request["answer"]["granted"] = granted
            request["ready"].set()
            window.grab_release()
            window.destroy()

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text=f"Разрешить {capability} и продолжить",
                   command=lambda: decide(True)).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Не разрешать / завершить задачу",
                   command=lambda: decide(False)).pack(side="left")
        window.protocol("WM_DELETE_WINDOW", lambda: decide(False))
        window.bind("<Destroy>", lambda event: request["ready"].set()
                    if event.widget is window else None)
        window.grab_set()
        window.focus_set()

    def _poll_events(self) -> None:
        try:
            while True:
                event_type, payload = self.events.get_nowait()
                if event_type == "success":
                    if isinstance(payload, dict):
                        text = str(payload.get("text") or "")
                        producer = payload.get("producer")
                        provenance_warning = payload.get(
                            "provenance_warning"
                        )
                    else:
                        text = str(payload)
                        producer = None
                        provenance_warning = None
                    run_status = payload.get("run_status") if isinstance(payload, dict) else "SUCCESS"
                    self._finish_run("Готово" if run_status != "BLOCKED" else "BLOCKED")
                    if provenance_warning:
                        self._append_chat(
                            "СИСТЕМА",
                            str(provenance_warning),
                            "system",
                        )
                elif event_type == "error":
                    self._finish_run("Ошибка")
                    self._append_chat("ОШИБКА", payload, "system")
                elif event_type == "permission_request":
                    try:
                        self._open_permission_request(payload)
                    except Exception:
                        payload["answer"]["granted"] = False
                        payload["ready"].set()
                elif event_type == "compressor_success":
                    try:
                        self._open_compression_proposal(payload)
                    except Exception as exc:
                        self._finish_context_operation("Ошибка COMPRESSOR")
                        messagebox.showerror(
                            APP_TITLE,
                            "Не удалось открыть proposal.\n\n"
                            f"{type(exc).__name__}: {exc}",
                            parent=self,
                        )
                elif event_type == "compressor_error":
                    self._finish_context_operation("Ошибка COMPRESSOR")
                    messagebox.showerror(APP_TITLE, str(payload), parent=self)
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _poll_trace_events(self) -> None:
        try:
            while True:
                try:
                    event = self.trace_events.get_nowait()
                except queue.Empty:
                    break
                try:
                    event_type = event.get("event")
                    if event_type == "run_started":
                        if self._run_started_once:
                            self._insert_run_separator()
                        self._run_started_once = True
                    tag = "trace_error" if event_type in {
                        "tool_error", "permission_denied", "run_failed",
                        "final_audit_failed", "final_audit_error", "guard_blocked",
                        "audit_diagnostic_error", "audit_storage_error",
                        "execution_consistency_verifier_failed", "execution_consistency_terminal",
                        "permission_scope_blocked", "permission_review_failed",
                        "permission_user_denied", "permission_escalation_terminal",
                    } else "trace"
                    self._append_trace(self._format_event(event), tag)
                    if event.get("audit_storage_error"):
                        self._append_trace(
                            f"[AUDIT STORAGE ERROR] {str(event['audit_storage_error'])[:80]}",
                            "trace_error",
                        )
                    if event_type == "run_started" and event.get("chat_id") == self.current_chat_id:
                        self._active_audit_run_id = event.get("run_id")
                        task_id = event.get("task_block_id")
                        binding = getattr(self, "_task_block_index", {}).get(task_id)
                        if binding:
                            binding["run_id"] = self._active_audit_run_id
                            try:
                                thread = load_audit_thread(
                                    self.workspace_var.get(), self.current_workspace_id,
                                    self.current_chat_id, self._active_audit_run_id,
                                )
                            except Exception:
                                thread = None
                            binding["audit_available"] = bool(
                                thread and thread.get("task_block_id") == task_id
                            )
                            self._ensure_task_audit_button(task_id)
                            self._select_task_block(task_id, force=True)
                        else:
                            self._selected_audit_run_id = self._active_audit_run_id
                            self._render_audit_thread()
                    elif self._selected_audit_run_id and event.get("run_id") == self._selected_audit_run_id and event_type in {
                        "final_audit_failed", "audit_diagnostic_question",
                        "audit_diagnostic_answer", "audit_diagnostic_error",
                        "tool_finished", "tool_error", "final_audit_passed",
                        "final_audit_error", "run_failed", "run_finished",
                        "permission_denied", "permission_scope_blocked",
                        "permission_review_started", "permission_review_passed",
                        "permission_review_failed", "permission_user_prompted",
                        "permission_granted", "permission_user_denied",
                        "permission_escalation_terminal",
                        "execution_consistency_detected", "execution_consistency_feedback_delivered",
                        "execution_consistency_recheck_started", "execution_consistency_verifier_started",
                        "execution_consistency_verifier_passed", "execution_consistency_verifier_failed",
                        "execution_consistency_correction_started", "execution_consistency_resolved",
                        "execution_consistency_terminal",
                    }:
                        self._render_audit_thread()
                    if event_type in {"run_failed", "run_finished"} and event.get("run_id") == self._active_audit_run_id:
                        self._active_audit_run_id = None
                except Exception as exc:
                    try:
                        kind = event.get("event") if isinstance(event, dict) else type(event).__name__
                        self._append_trace(
                            f"[TRACE RENDER ERROR] {str(kind)[:60]}: {type(exc).__name__}",
                            "trace_error",
                        )
                    except Exception:
                        pass
        finally:
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
            self.status_var.set(
                f"{self._running_model_display_name} работает... "
                f"{elapsed} сек."
            )
        self.after(500, self._tick_status)

    def _finish_run(self, status: str) -> None:
        self.running = False
        self.progress.stop()
        self.status_var.set(status)
        self._set_run_controls_enabled(True)
        if self.current_chat_id:
            try:
                self._render_current_chat()
            except Exception as exc:
                self._append_chat(
                    "ОШИБКА",
                    f"Не удалось перерисовать persistent chat: {exc}",
                    "system",
                )
        self.input_box.focus_set()


if __name__ == "__main__":
    app = UltraApp()
    app.mainloop()
