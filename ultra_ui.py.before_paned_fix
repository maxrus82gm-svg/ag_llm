import asyncio
import json
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path

from server import run_agent_task


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
        self.geometry("1100x760")
        self.minsize(850, 620)

        self.workspace_var = tk.StringVar(value=str(Path.cwd()))
        self.status_var = tk.StringVar(value="Готово")
        self.running = False
        self.started_at = 0.0
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.trace_events: queue.Queue[dict] = queue.Queue()

        # Отслеживание изменений исходного кода
        self._code_changed = False
        self._changed_files: list[str] = []
        self._server_mtime = None
        self._ui_mtime = None
        self._record_initial_mtimes()

        self._build_ui()
        self.after(100, self._poll_events)
        self.after(100, self._poll_trace_events)
        self.after(500, self._tick_status)
        self.after(1000, self._poll_code_changes)

    def _record_initial_mtimes(self) -> None:
        """Запомнить mtime server.py и ultra_ui.py при старте."""
        try:
            self._server_mtime = Path("server.py").stat().st_mtime
        except FileNotFoundError:
            self._server_mtime = None
        try:
            self._ui_mtime = Path("ultra_ui.py").stat().st_mtime
        except FileNotFoundError:
            self._ui_mtime = None

    def _poll_code_changes(self) -> None:
        """Проверять изменения server.py и ultra_ui.py раз в секунду."""
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
        """Показать предупреждение об изменении исходного кода runtime."""
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

        # Главный контейнер с разделителем
        paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        # Левая панель — ЛОГ ДЕЙСТВИЙ
        left_frame = ttk.Frame(paned, width=340)
        left_frame.pack_propagate(False)
        paned.add(left_frame, minsize=260)

        ttk.Label(left_frame, text="ЛОГ ДЕЙСТВИЙ").pack(anchor="w", padx=(0, 0), pady=(0, 6))

        self.trace_log = scrolledtext.ScrolledText(
            left_frame,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
        )
        self.trace_log.pack(fill="both", expand=True)
        self.trace_log.tag_configure("trace", font=("Consolas", 9))

        # Правая панель — всё остальное
        right_frame = ttk.Frame(paned)
        paned.add(right_frame)

        # Workspace
        workspace_frame = ttk.Frame(right_frame)
        workspace_frame.pack(fill="x")

        ttk.Label(workspace_frame, text="Workspace:").pack(side="left")

        self.workspace_entry = ttk.Entry(
            workspace_frame,
            textvariable=self.workspace_var,
        )
        self.workspace_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        bind_edit_shortcuts(self.workspace_entry)

        ttk.Button(
            workspace_frame,
            text="Выбрать папку",
            command=self._choose_workspace,
        ).pack(side="left")

        ttk.Separator(right_frame).pack(fill="x", pady=10)

        # Чат
        ttk.Label(right_frame, text="Чат").pack(anchor="w")

        self.chat = scrolledtext.ScrolledText(
            right_frame,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 10),
        )
        self.chat.pack(fill="both", expand=True, pady=(5, 10))
        self.chat.tag_configure("user", font=("Segoe UI", 10, "bold"))
        self.chat.tag_configure("assistant", font=("Segoe UI", 10))
        self.chat.tag_configure("system", font=("Segoe UI", 9, "italic"))

        # В истории чата разрешаем копирование и выделение.
        for sequence in ("<Control-c>", "<Control-C>"):
            self.chat.bind(
                sequence,
                lambda e: (e.widget.event_generate("<<Copy>>"), "break")[1],
            )

        ttk.Separator(right_frame).pack(fill="x", pady=10)

        # Статус и прогресс
        status_frame = ttk.Frame(right_frame)
        status_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(status_frame, text="Статус:").pack(side="left")
        ttk.Label(status_frame, textvariable=self.status_var).pack(
            side="left",
            padx=(6, 10),
        )

        self.progress = ttk.Progressbar(
            status_frame,
            mode="indeterminate",
            length=180,
        )
        self.progress.pack(side="right")

        # Поле сообщения
        ttk.Label(right_frame, text="Сообщение").pack(anchor="w")

        self.input_box = scrolledtext.ScrolledText(
            right_frame,
            wrap="word",
            height=8,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.input_box.pack(fill="x", pady=(5, 8))
        bind_edit_shortcuts(self.input_box)
        self.input_box.bind("<Control-Return>", self._send_from_hotkey)

        # Кнопки
        buttons = ttk.Frame(right_frame)
        buttons.pack(fill="x")

        ttk.Label(
            buttons,
            text="Ctrl+Enter — отправить",
        ).pack(side="left")

        self.send_button = ttk.Button(
            buttons,
            text="Отправить",
            command=self._send,
        )
        self.send_button.pack(side="right")

        self._append_chat(
            "СИСТЕМА",
            "Интерфейс готов. Выбери workspace, введи задачу и нажми «Отправить».",
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
        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp)) if timestamp else "--:--:--"

        if event_type == "run_started":
            task_preview = event.get("task_preview", "")
            return f"[{time_str}] RUN START | {run_id} | {task_preview[:60]}"

        if event_type == "api_request":
            num = event.get("api_request_number")
            return f"[{time_str}] API #{num}"

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
            result = event.get("result", {})
            duration = event.get("duration")
            dur_str = f" | {duration:.2f} s" if isinstance(duration, (int, float)) else ""
            return f"[{time_str}] TOOL #{seq} {func} -> OK{dur_str}"

        if event_type == "tool_error":
            seq = event.get("tool_sequence")
            func = event.get("function")
            error = event.get("error", {})
            err_type = error.get("type", "")
            err_msg = error.get("message", "")
            duration = event.get("duration")
            dur_str = f" | {duration:.2f} s" if isinstance(duration, (int, float)) else ""
            return f"[{time_str}] TOOL #{seq} {func} -> ERROR ({err_type}){dur_str}: {err_msg}"

        if event_type == "run_finished":
            status = event.get("status")
            api_count = event.get("api_requests")
            tool_count = event.get("tool_calls")
            duration = event.get("duration")
            dur_str = f" | {duration:.2f} s" if isinstance(duration, (int, float)) else ""
            return f"[{time_str}] {status} | API: {api_count} | TOOLS: {tool_count}{dur_str} | RUN {run_id}"

        if event_type == "run_failed":
            reason = event.get("reason")
            api_count = event.get("api_requests")
            tool_count = event.get("tool_calls")
            duration = event.get("duration")
            dur_str = f" | {duration:.2f} s" if isinstance(duration, (int, float)) else ""
            trace_path = event.get("trace_path")
            trace_str = f" | trace: {trace_path}" if trace_path else ""
            return f"[{time_str}] ERROR ({reason}){dur_str} | API: {api_count} | TOOLS: {tool_count}{trace_str} | RUN {run_id}"

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

        self._append_chat("ТЫ", task, "user")
        self.input_box.delete("1.0", "end")

        self.running = True
        self.started_at = time.monotonic()
        self.status_var.set("Ultra работает...")
        self.progress.start(12)
        self.send_button.configure(state="disabled")
        self.workspace_entry.configure(state="disabled")

        thread = threading.Thread(
            target=self._worker,
            args=(task, str(workspace)),
            daemon=True,
        )
        thread.start()

    def _worker(self, task: str, workspace: str) -> None:
        def on_event(event: dict):
            try:
                self.trace_events.put_nowait(event)
            except queue.Full:
                pass

        try:
            result = asyncio.run(run_agent_task(task, workspace, on_event=on_event))
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
                line = self._format_event(event)
                self._append_trace(line)
        except queue.Empty:
            pass

        self.after(100, self._poll_trace_events)

    def _tick_status(self) -> None:
        if self.running:
            elapsed = int(time.monotonic() - self.started_at)
            self.status_var.set(f"Ultra работает... {elapsed} сек.")
        self.after(500, self._tick_status)

    def _finish_run(self, status: str) -> None:
        self.running = False
        self.progress.stop()
        self.status_var.set(status)
        self.send_button.configure(state="normal")
        self.workspace_entry.configure(state="normal")
        self.input_box.focus_set()


if __name__ == "__main__":
    app = UltraApp()
    app.mainloop()
