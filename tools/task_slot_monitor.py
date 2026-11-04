"""Optional resizable Tk monitor for task_slot_rotate finish. No rotation logic here.

One window per card; repeat launches enqueue an addressed request, not another window.
Recent summaries (at most 10) live in a per-card TEMP folder; permanent JSON goes to
the addressed existing task report folder. No registry, network or extra dependencies.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid

SETTINGS = Path(__file__).with_name("task_slot_debug.json")
COLORS = {"blue": "#60a5fa", "green": "#4ade80", "red": "#fb7185"}


def can_manual_finish(check):
    """Only a successful, complete TASK observation can enable the user action."""
    if not isinstance(check, dict) or check.get("result") != "OK" or check.get("problems"):
        return False
    slot = check.get("block1", {})
    return (slot.get("state") == "TASK" and not slot.get("problems")
            and bool(re.fullmatch(r"[A-Z0-9][A-Z0-9-]{0,119}", slot.get("task_id", "")))
            and bool(re.fullmatch(r"[0-9a-f]{64}", check.get("card_sha256", ""))))


def manual_finish_argv(card, check, *, package_ready=False, no_chat_amendment=False, chat_amendments=()):
    """Build the existing finish command; never write a card from the window."""
    if not can_manual_finish(check):
        raise ValueError("Нет проверенной текущей задачи для переноса. Обновите статус.")
    if not package_ready:
        raise ValueError("Сначала сохраните итоговый отчёт, manifest и доказательства.")
    if bool(no_chat_amendment) == bool(chat_amendments):
        raise ValueError("Укажите: отдельных поправок нет, либо выберите все файлы поправок.")
    argv = ["finish", "--card", str(Path(card).resolve()), "--task-id", check["block1"]["task_id"],
            "--expected-card-sha256", check["card_sha256"], "--apply"]
    if no_chat_amendment:
        argv.append("--no-chat-amendment")
    else:
        for path in chat_amendments:
            argv.extend(["--chat-amendment", str(Path(path).resolve())])
    return argv


def can_assign_task(check):
    return (isinstance(check, dict) and check.get("result") == "OK" and not check.get("problems")
            and check.get("block1", {}).get("state") == "WAITING"
            and bool(re.fullmatch(r"[0-9a-f]{64}", check.get("card_sha256", ""))))


def assign_task_argv(card, check, task_file):
    if not can_assign_task(check):
        raise ValueError("Новая задача доступна только когда БЛОК 1 ожидает задачу.")
    return ["assign", "--card", str(Path(card).resolve()), "--task-file", str(Path(task_file).resolve()),
            "--expected-card-sha256", check["card_sha256"], "--apply"]


def debug_settings(path=SETTINGS):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if type(data.get("enabled")) is not bool:
        raise ValueError("task_slot_debug.json: enabled must be true or false")
    return {"enabled": data["enabled"], "auto_close_seconds": max(0, min(60, int(data.get("auto_close_seconds", 8)))),
            "font_size": max(10, min(16, int(data.get("font_size", 12)))), "history_limit": 10,
            "refresh_minutes": max(1, min(1440, int(data.get("refresh_minutes", 30))))}


def runtime_folder(card):
    key = hashlib.sha256(str(Path(card).resolve()).casefold().encode()).hexdigest()[:20]
    return Path(tempfile.gettempdir()) / ("task-slot-window-" + key)


def write_json(path, value):
    # Own runtime file, atomic replacement. No task snapshots are written here.
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def process_alive(pid):
    if os.name == "nt":
        # os.kill(pid, 0) is NOT a harmless liveness probe on Windows.
        # Query the addressed process only; no termination or privilege adjustment.
        import ctypes as ct
        from ctypes import wintypes as wt
        kernel = ct.WinDLL("kernel32.dll", use_last_error=True, winmode=0x800)
        kernel.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        kernel.OpenProcess.restype = wt.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wt.HANDLE, ct.POINTER(wt.DWORD)]
        kernel.CloseHandle.argtypes = [wt.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ct.get_last_error() != 87  # unknown/access denied => preserve owner
        try:
            code = wt.DWORD()
            return not kernel.GetExitCodeProcess(handle, ct.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def claim(folder, argv):
    folder.mkdir(exist_ok=True)
    owner = folder / "owner.json"
    for attempt in range(2):
        try:
            fd = os.open(owner, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump({"pid": os.getpid()}, out)
            return True
        except FileExistsError:
            try:
                pid = json.loads(owner.read_text(encoding="utf-8"))["pid"]
                if type(pid) is not int or pid <= 0:
                    raise ValueError("invalid owner")
                if not process_alive(pid):
                    owner.unlink(missing_ok=True)
                    continue
            except (ValueError, KeyError, json.JSONDecodeError, PermissionError):
                # Unknown owner => no duplicate window; preserve the lock for diagnosis.
                pass
            request = folder / ("request-" + uuid.uuid4().hex + ".json")
            write_json(request, {"argv": argv})
            return False
    raise RuntimeError("monitor lock not available")


def launch(argv):
    # Importing the core does not open a window or change a card.
    import task_slot_rotate as core
    args = core.build_parser().parse_args(argv)
    settings = debug_settings()
    folder = runtime_folder(args.card)
    if not claim(folder, argv):
        print(json.dumps({"result": "MONITOR_REUSED", "detail": "request queued to existing window"}))
        return 0
    try:
        return show_window(args, argv, settings, folder)
    finally:
        owner = folder / "owner.json"
        try:
            if json.loads(owner.read_text(encoding="utf-8"))["pid"] == os.getpid():
                owner.unlink()
        except (OSError, ValueError, KeyError):
            pass


def show_window(args, argv, settings, folder):
    import tkinter as tk
    from tkinter import ttk, filedialog
    import tkinter.font as font
    import task_slot_rotate as core

    root = tk.Tk()
    root.title("Ротация карточки — " + Path(args.card).stem)
    root.geometry("880x530")
    root.minsize(650, 360)
    root.resizable(True, True)
    text_font = font.Font(family="Segoe UI", size=settings["font_size"])
    root.option_add("*Font", text_font)
    bg, panel, fg, muted = "#0c1015", "#20252c", "#d9dfe7", "#9ca5b3"
    root.configure(background=bg)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg, font=text_font)
    style.configure("TCheckbutton", background=bg, foreground=fg, font=text_font)
    style.configure("TRadiobutton", background=bg, foreground=fg, font=text_font)
    for kind in ("TCheckbutton", "TRadiobutton"):
        style.map(kind, background=[("active", bg)], foreground=[("active", fg)])
    style.configure("TButton", background=panel, foreground=fg, borderwidth=0, padding=(9, 6), font=text_font)
    style.map("TButton", background=[("active", "#303843")], foreground=[("disabled", muted)])
    style.configure("Vertical.TScrollbar", background=panel, troughcolor=bg, bordercolor=bg, arrowcolor=muted)
    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)
    # Reserve the command area before allocating any space to the expanding log.
    footer = ttk.Frame(frame)
    footer.pack(side="bottom", fill="x")
    status = tk.StringVar(value="● Готов к проверке")
    header = ttk.Frame(frame)
    header.pack(fill="x")
    label = tk.Label(header, textvariable=status, fg=COLORS["blue"], bg=bg, anchor="w", font=text_font)
    label.pack(side="left", fill="x", expand=True)
    new_task_button = ttk.Button(header, text="Новая задача…", state="disabled",
        command=lambda: start(["watch", "--card", str(Path(args.card).resolve())], action="assign"))
    new_task_button.pack(side="right")
    task_label = tk.StringVar(value=args.task_id)
    ttk.Label(frame, textvariable=task_label).pack(anchor="w")
    slot_state = tk.StringVar(value="БЛОК 1: проверяем…")
    previous_state = tk.StringVar(value="БЛОК 1.1: проверяем…")
    ttk.Label(frame, textvariable=slot_state, wraplength=820).pack(anchor="w", pady=(8, 0))
    ttk.Label(frame, textvariable=previous_state, wraplength=820).pack(anchor="w")
    area = ttk.Frame(frame)
    area.pack(fill="both", expand=True, pady=8)
    log = tk.Text(area, wrap="word", state="disabled", font=text_font, height=1, width=1,
                  background=bg, foreground=fg, insertbackground=fg, selectbackground="#384354",
                  highlightthickness=1, highlightbackground=panel, relief="flat")
    scrollbar = ttk.Scrollbar(area, command=log.yview)
    log.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    log.pack(side="left", fill="both", expand=True)
    for color, value in COLORS.items():
        log.tag_configure(color, foreground=value)
    events = queue.Queue()
    state = {"busy": False, "timer": None, "close_pending": False, "argv": argv,
             "args": args, "history": [], "last_code": 0, "events": [],
             "observation": None, "pending_action": None, "dialog": None, "editor": None,
             "next_refresh": time.monotonic() + settings["refresh_minutes"] * 60}
    try:
        state["history"] = json.loads((folder / "history.json").read_text(encoding="utf-8"))[-10:]
    except (OSError, ValueError, TypeError):
        pass

    def append(message, color="blue"):
        log.configure(state="normal")
        log.insert("end", message + "\n", color)
        if int(log.index("end-1c").split(".")[0]) > 200:
            log.delete("1.0", "30.0")
        log.see("end")
        log.configure(state="disabled")

    def close():
        if state["busy"]:
            state["close_pending"] = True
            root.withdraw()  # let the bounded operation finish, do not kill a transaction
        else:
            root.destroy()

    def worker(worker_argv):
        worker_argv = [a for a in worker_argv if a not in ("--monitor", "--headless", "--progress", "--new-task")]
        watching = worker_argv[0] == "watch"
        if watching:
            worker_argv[0] = "check"
        cmd = [sys.executable, "-B", str(Path(__file__).with_name("task_slot_rotate.py")),
               *worker_argv, *([] if watching else ["--headless", "--progress"])]
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, encoding="utf-8")
            def stderr():
                for line in proc.stderr:
                    try:
                        events.put(("event", json.loads(line)))
                    except ValueError:
                        events.put(("event", {"message": "Диагностическое сообщение процесса", "color": "red"}))
            reader = threading.Thread(target=stderr)
            reader.start()
            output = proc.stdout.read()
            code = proc.wait()
            reader.join()
            proc.stdout.close()
            proc.stderr.close()
            events.put(("done", (code, json.loads(output))))
        except Exception as exc:
            events.put(("done", (1, {"result": "ERROR", "problems": [{"code": type(exc).__name__}]})))

    def update_finish_button():
        available = can_manual_finish(state["observation"])
        finish_button.configure(state="normal" if available and not state["busy"] and not state["dialog"] else "disabled")
        new_task_button.configure(state="normal" if can_assign_task(state["observation"])
                                  and not state["busy"] and not state["dialog"] else "disabled")
        finish_hint.set("Завершение доступно после сохранения итогового пакета." if available
                        else "Перенос недоступен: нет проверенной задачи в БЛОКЕ 1.")

    def start(new_argv=None, action=None, from_editor=False):
        if state["busy"] or state["dialog"] and not from_editor:
            append("Операция или подтверждение уже открыты; второй процесс ротации не запущен.")
            return
        if state["timer"]:
            root.after_cancel(state["timer"])
            state["timer"] = None
        chosen = new_argv or state["argv"]
        parsed = core.build_parser().parse_args(chosen)
        if parsed.command == "watch" and parsed.new_task:
            action = "assign"
        if Path(parsed.card).resolve() != Path(args.card).resolve():
            append("Другая карточка: запрос отклонён.", "red")
            return
        state.update(busy=True, argv=chosen, args=parsed, events=[], observation=None, pending_action=action)
        update_finish_button()
        task_label.set(parsed.task_id)
        status.set("● Выполняется")
        label.configure(fg=COLORS["green"])
        append("Старт: " + parsed.task_id, "green")
        threading.Thread(target=worker, args=(chosen,), daemon=True).start()

    def edit_new_task(check):
        if not can_assign_task(check):
            append("Новая задача не открыта: БЛОК 1 уже занят или проверка не пройдена.", "red")
            return
        dialog = tk.Toplevel(root)
        state["dialog"] = dialog
        dialog.title("Новая задача — БЛОК 1")
        dialog.configure(background=bg)
        dialog.geometry("860x650")
        dialog.minsize(600, 440)
        dialog.transient(root)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=14)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1, minsize=text_font.metrics("linespace") + 4)
        heading = ttk.Label(body, text="Вставьте Markdown постановки с TASK ID. Запишется только БЛОК 1.", wraplength=780)
        heading.grid(row=0, column=0, sticky="ew")
        help_label = ttk.Label(body, text="Вставка сама ничего не записывает. Для сохранения нажмите «Отправить».", wraplength=780)
        help_label.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        editor_area = ttk.Frame(body)
        editor_area.grid(row=2, column=0, sticky="nsew")
        text = tk.Text(editor_area, wrap="word", undo=True, font=text_font, background=bg,
                       foreground=fg, insertbackground=fg, selectbackground="#384354",
                       highlightthickness=1, highlightbackground=panel, relief="flat", height=1, width=1)
        scroll = ttk.Scrollbar(editor_area, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        preview = tk.StringVar(value="Вставьте полную постановку: TASK ID и не менее 100 непробельных символов.")
        preview_label = ttk.Label(body, textvariable=preview, wraplength=780)
        preview_label.grid(row=3, column=0, sticky="ew", pady=8)
        controls = ttk.Frame(body)
        controls.grid(row=4, column=0, sticky="ew")
        layout = {"timer": None}
        def fit_editor():
            layout["timer"] = None
            if not dialog.winfo_exists():
                return
            width = max(100, body.winfo_width() - 28)
            for item in (heading, help_label, preview_label):
                if item.cget("wraplength") != width:
                    item.configure(wraplength=width)
            # Natural height now includes one text line; fixed rows keep all controls.
            dialog.minsize(600, max(200, body.winfo_reqheight()))
        def schedule_fit(event=None):
            if layout["timer"] is None:
                layout["timer"] = dialog.after_idle(fit_editor)
        body.bind("<Configure>", schedule_fit)
        preview.trace_add("write", lambda *unused: schedule_fit())
        validation = {"timer": None}
        def validate():
            validation["timer"] = None
            if state["busy"]:
                return
            if not can_assign_task((state["editor"] or {}).get("check")):
                preview.set("Сначала нажмите «Проверить слот». Текст остаётся в форме.")
                submit_button.configure(state="disabled")
                return
            try:
                _, task = core.new_task_bytes(text.get("1.0", "end-1c").encode("utf-8"))
                preview.set("Готово к записи: " + task)
                submit_button.configure(state="normal")
            except core.Refused as exc:
                preview.set("Проверьте постановку: " + ", ".join(p["code"] for p in exc.problems))
                submit_button.configure(state="disabled")
        def modified(event=None):
            if text.edit_modified():
                text.edit_modified(False)
                if validation["timer"]:
                    dialog.after_cancel(validation["timer"])
                validation["timer"] = dialog.after(150, validate)
        text.bind("<<Modified>>", modified)
        def dismiss():
            if state["busy"]:
                preview.set("Дождитесь завершения записи — окно сохраняет вашу постановку.")
                return
            if validation["timer"]:
                dialog.after_cancel(validation["timer"])
            if layout["timer"]:
                dialog.after_cancel(layout["timer"])
            state["dialog"] = None
            state["editor"] = None
            dialog.destroy()
            update_finish_button()
        def submit():
            if state["busy"]:
                return
            try:
                content = text.get("1.0", "end-1c").encode("utf-8")
                core.new_task_bytes(content)
                draft = state["editor"]["draft"] or folder / ("new-task-" + uuid.uuid4().hex + ".md")
                draft.write_bytes(content)
                chosen = assign_task_argv(args.card, state["editor"]["check"], draft)
            except (core.Refused, ValueError, OSError) as exc:
                preview.set(str(exc))
                return
            state["editor"]["draft"] = draft
            preview.set("Проверяем карточку и записываем задачу…")
            text.configure(state="disabled")
            submit_button.configure(state="disabled")
            cancel_button.configure(state="disabled")
            start(chosen, from_editor=True)
        submit_button = ttk.Button(controls, text="Отправить", state="disabled", command=submit)
        submit_button.pack(side="left")
        def refresh_editor():
            if not state["busy"]:
                submit_button.configure(state="disabled")
                preview.set("Проверяем, ожидает ли БЛОК 1 новую задачу…")
                start(["watch", "--card", str(Path(args.card).resolve())], action="refresh-editor", from_editor=True)
        ttk.Button(controls, text="Проверить слот", command=refresh_editor).pack(side="left", padx=8)
        cancel_button = ttk.Button(controls, text="Закрыть", command=dismiss)
        cancel_button.pack(side="right")
        state["editor"] = {"window": dialog, "text": text, "preview": preview,
                           "submit": submit_button, "cancel": cancel_button, "dismiss": dismiss,
                           "draft": None, "check": check, "validate": validate}
        dialog.protocol("WM_DELETE_WINDOW", dismiss)
        text.focus_set()
        update_finish_button()
        def editor_diagnostic():
            if dialog.winfo_exists():
                write_json(folder / "editor_view.json", {"title": dialog.title(), "empty": not text.get("1.0", "end-1c"),
                    "submit_disabled": submit_button.instate(["disabled"]), "text_has_focus": dialog.focus_get() == text,
                    "resizable": dialog.resizable(), "geometry": dialog.geometry()})
        dialog.after(100, editor_diagnostic)

    def confirm_manual_finish(check):
        # Called only after a fresh read-only check, never from a stale 30-minute view.
        if not can_manual_finish(check):
            append("Перенос не запущен: в БЛОКЕ 1 нет допустимой текущей задачи.", "red")
            return
        dialog = tk.Toplevel(root)
        state["dialog"] = dialog
        dialog.title("Завершить текущую задачу")
        dialog.configure(background=bg)
        dialog.geometry("710x460")
        dialog.minsize(590, 420)
        dialog.transient(root)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=16)
        body.pack(fill="both", expand=True)
        task = check["block1"]["task_id"]
        ttk.Label(body, text=task, wraplength=650).pack(anchor="w")
        ttk.Label(body, text=check["block1"].get("title", ""), wraplength=650).pack(anchor="w", pady=(0, 8))
        ttk.Label(body, text="Скрипт сохранит постановку и номер истории, перенесёт её в БЛОК 1.1 и освободит БЛОК 1.\n"
                  "Независимая приёмка этим не подтверждается.\nПакет: reports/" + task + "/", wraplength=650).pack(anchor="w")
        ready = tk.BooleanVar(value=False)
        amendment_choice = tk.StringVar(value="unset")
        amendment_label = tk.StringVar(value="Файлы не выбраны")
        selected_files = []
        def update_confirmation():
            allowed = ready.get() and (amendment_choice.get() == "none" or
                                      amendment_choice.get() == "files" and bool(selected_files))
            confirm_button.configure(state="normal" if allowed else "disabled")
        ttk.Checkbutton(body, text="Работа завершена; отчёт, manifest и evidence сохранены", variable=ready,
                        command=update_confirmation).pack(anchor="w", pady=(12, 8))
        ttk.Radiobutton(body, text="Отдельных принятых поправок из чата нет", variable=amendment_choice,
                        value="none", command=update_confirmation).pack(anchor="w")
        ttk.Radiobutton(body, text="Есть отдельные поправки — включить выбранные файлы", variable=amendment_choice,
                        value="files", command=update_confirmation).pack(anchor="w")
        def choose_files():
            files = filedialog.askopenfilenames(parent=dialog, title="Все принятые поправки из чата",
                                                filetypes=[("Markdown / text", "*.md *.txt"), ("Все файлы", "*")])
            if files:
                selected_files[:] = files
                amendment_choice.set("files")
                amendment_label.set("Выбрано файлов: " + str(len(files)))
                update_confirmation()
        ttk.Button(body, text="Выбрать файлы поправок…", command=choose_files).pack(anchor="w", pady=4)
        ttk.Label(body, textvariable=amendment_label).pack(anchor="w")
        dialog_error = tk.StringVar()
        ttk.Label(body, textvariable=dialog_error, foreground=COLORS["red"], wraplength=650).pack(fill="x", pady=6)
        controls = ttk.Frame(body)
        controls.pack(side="bottom", fill="x", pady=(8, 0))
        def dismiss():
            state["dialog"] = None
            dialog.destroy()
            update_finish_button()
        def submit():
            try:
                chosen = manual_finish_argv(args.card, check, package_ready=ready.get(),
                    no_chat_amendment=amendment_choice.get() == "none",
                    chat_amendments=selected_files if amendment_choice.get() == "files" else ())
            except ValueError as exc:
                dialog_error.set(str(exc))
                return
            dismiss()
            start(chosen)
        confirm_button = ttk.Button(controls, text="Проверить и перенести", command=submit, state="disabled")
        confirm_button.pack(side="left")
        ttk.Button(controls, text="Отмена", command=dismiss).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", dismiss)
        update_finish_button()

    def show_history():
        append("Последние запуски (до 10):")
        for entry in state["history"][-10:]:
            append(f"{entry['time']} · {entry['task_id']} · {entry['result']}",
                   "red" if entry["exit_code"] else "blue")

    def poll():
        for request in sorted(folder.glob("request-*.json"))[:10]:
            try:
                requested = json.loads(request.read_text(encoding="utf-8"))["argv"]
                request.unlink()
                root.deiconify()
                root.lift()
                start(requested)
            except (OSError, ValueError, KeyError, TypeError):
                append("Не удалось прочитать запрос к окну", "red")
        while not events.empty():
            kind, payload = events.get_nowait()
            if kind == "event":
                state["events"].append(payload)
                append(payload.get("message", payload.get("step", "")), payload.get("color", "blue"))
            else:
                code, protocol = payload
                state.update(busy=False, last_code=code)
                result = protocol.get("result", "ERROR")
                observations = [x for x in protocol.get("steps", [protocol]) if "block1" in x]
                state["observation"] = observations[-1] if observations and not code else None
                if observations:
                    latest = observations[-1]
                    slot = latest["block1"]
                    slot_state.set("БЛОК 1: " + ("ОЖИДАЕТ НОВУЮ ЗАДАЧУ" if slot["state"] == "WAITING"
                                   else "СОДЕРЖИТ ЗАДАЧУ " + slot["task_id"] if slot.get("task_id")
                                   else "ОШИБКА СТРУКТУРЫ / " + slot["state"]))
                    last_slot = latest['block1_1']
                    history_id = last_slot.get('history_id') or protocol.get('history', {}).get('history_id')
                    previous_state.set("БЛОК 1.1: " + last_slot.get("task_id", last_slot["state"]) +
                                       (" · История " + history_id if history_id else ""))
                    if slot.get("title"):
                        task_label.set(slot["title"])
                    elif state["args"].command == "watch":
                        task_label.set("Просмотр локальной карточки · обновление каждые " + str(settings["refresh_minutes"]) + " мин")
                row = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "task_id": protocol.get("task_id", state["args"].task_id),
                       "result": result, "exit_code": code}
                if protocol.get('history'):
                    row['history_id'] = protocol['history']['history_id']
                    row['record'] = protocol['history']['record']
                watching = state["args"].command == "watch"
                assigning = state["args"].command == "assign"
                if not watching:
                    state["history"] = (state["history"] + [row])[-10:]
                    write_json(folder / "history.json", state["history"])
                repo = core.repo_root(Path(state["args"].card).resolve(), state["args"].repo)
                report = Path(state["args"].report_dir).resolve() if state["args"].report_dir else repo / "reports" / row["task_id"]
                if not watching and not assigning and report.is_dir() and report.is_relative_to(repo / "reports"):
                    target = report / ("slot_finish_" + str(time.time_ns()) + ".json")
                    write_json(target, {"summary": row, "events": state["events"], "protocol": protocol,
                               "window": {"geometry": root.geometry(), "state": root.state(),
                                          "background": root.cget("background"), "resizable": root.resizable(),
                                          "font_size": text_font.cget("size"), "block1_text": slot_state.get(),
                                          "block1_1_text": previous_state.get(),
                                          "auto_close_seconds": settings["auto_close_seconds"]}})
                    append("JSON-протокол сохранён: " + core.rel(target, repo))
                if assigning:
                    write_json(folder / ("assignment-" + str(time.time_ns()) + ".json"), protocol)
                    for old in sorted(folder.glob("assignment-*.json"))[:-10]:
                        old.unlink(missing_ok=True)
                    if state["editor"]:
                        editor = state["editor"]
                        if not code and result == "ASSIGNED":
                            if editor["draft"]:
                                editor["draft"].unlink(missing_ok=True)
                            editor["dismiss"]()
                            append("Задача записана в карточку. Чтобы агент начал работу, сообщите ему.", "green")
                        else:
                            editor["check"] = None
                            editor["text"].configure(state="normal")
                            editor["cancel"].configure(state="normal")
                            # A failed stale-view submission requires reopening after refresh.
                            editor["preview"].set("Запись остановлена: " + ", ".join(
                                p["code"] for p in protocol.get("problems", [])) + ". Текст сохранён; нажмите «Проверить слот».")
                append(result, "red" if code else "blue" if result == "ALREADY_ROTATED" else "green")
                if code:
                    for issue in protocol.get("problems", []):
                        append(issue.get("code", "ERROR") + ": " + issue.get("detail", issue.get("message", "")), "red")
                status.set("● Ошибка / перенос остановлен" if code else "● Наблюдение" if watching
                           else "● Уже сделано" if result == "ALREADY_ROTATED" else "● Успешно")
                label.configure(fg=COLORS["red"] if code else COLORS["blue"] if watching or result == "ALREADY_ROTATED" else COLORS["green"])
                update_finish_button()
                write_json(folder / "view.json", {"time": row["time"], "result": result,
                    "block1": (state["observation"] or {}).get("block1"),
                    "new_task_button": {"text": new_task_button.cget("text"),
                        "enabled": not new_task_button.instate(["disabled"]),
                        "x": new_task_button.winfo_x(), "width": new_task_button.winfo_width(), "header_width": header.winfo_width()},
                    "dialog_open": bool(state["dialog"]), "geometry": root.geometry()})
                # Never print a large protocol in Tk's event loop: a full stdout
                # pipe can freeze painting, closing and the auto-close timer.
                summary = {"result": result, "task_id": row["task_id"], "exit_code": code}
                if sys.stdout is not None:
                    threading.Thread(target=lambda: print(json.dumps(summary), flush=True), daemon=True).start()
                if state["close_pending"]:
                    root.destroy()
                    return
                pending = state["pending_action"]
                state["pending_action"] = None
                if pending == "finish":
                    confirm_manual_finish(state["observation"])
                elif pending == "assign":
                    edit_new_task(state["observation"])
                elif pending == "refresh-editor" and state["editor"]:
                    editor = state["editor"]
                    if can_assign_task(state["observation"]):
                        editor["check"] = state["observation"]
                        editor["validate"]()
                    else:
                        editor["check"] = None
                        editor["submit"].configure(state="disabled")
                        editor["preview"].set("БЛОК 1 занят или проверка не пройдена. Текст остаётся в форме.")
                if not code and not watching and not assigning and settings["auto_close_seconds"]:
                    append(f"Окно закроется через {settings['auto_close_seconds']} с. Снимите автозакрытие, чтобы оставить журнал.")
                    state["timer"] = root.after(settings["auto_close_seconds"] * 1000, close)
        if time.monotonic() >= state["next_refresh"]:
            state["next_refresh"] = time.monotonic() + settings["refresh_minutes"] * 60
            if not state["busy"] and not state["dialog"]:
                start(["watch", "--card", str(Path(args.card).resolve())])
        root.after(200, poll)

    actions = ttk.Frame(footer)
    actions.pack(fill="x", pady=(0, 6))
    finish_button = ttk.Button(actions, text="Завершить текущую задачу…", state="disabled",
        command=lambda: start(["watch", "--card", str(Path(args.card).resolve())], action="finish"))
    finish_button.pack(side="left")
    finish_hint = tk.StringVar(value="Сначала проверяем БЛОК 1.")
    hint_label = ttk.Label(actions, textvariable=finish_hint, wraplength=300)
    hint_label.pack(side="left", padx=12, fill="x", expand=True)
    actions.bind("<Configure>", lambda event: hint_label.configure(
        wraplength=max(160, event.width - finish_button.winfo_reqwidth() - 24)))
    buttons = ttk.Frame(footer)
    buttons.pack(fill="x")
    ttk.Button(buttons, text="Обновить статус", command=lambda: start(["watch", "--card", str(Path(args.card).resolve())])).pack(side="left")
    ttk.Button(buttons, text="История (10)", command=show_history).pack(side="left", padx=6)
    ttk.Button(buttons, text="Меньше", command=lambda: text_font.configure(size=max(10, text_font.cget("size") - 1))).pack(side="left")
    ttk.Button(buttons, text="Больше", command=lambda: text_font.configure(size=min(16, text_font.cget("size") + 1))).pack(side="left")
    ttk.Button(buttons, text="Закрыть", command=close).pack(side="right")
    def keep_open():
        settings["auto_close_seconds"] = 0
        if state["timer"]:
            root.after_cancel(state["timer"])
            state["timer"] = None
        append("Автозакрытие отключено для этого окна.")
    ttk.Button(buttons, text="Оставить окно", command=keep_open).pack(side="right", padx=6)
    ttk.Label(footer, text="tools/task_slot_debug.json → enabled: true / false. Без окна: --headless; окно на один запуск: --monitor.", wraplength=820).pack(fill="x", pady=(7, 0))
    ttk.Label(footer, text="Окно читает локальные файлы. Изменения GitHub будут видны после синхронизации репозитория.", wraplength=820).pack(fill="x")
    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, start)
    root.after(300, lambda: (root.deiconify(), root.lift()))
    root.after(200, poll)
    root.mainloop()
    return state["last_code"]


if __name__ == "__main__":
    raise SystemExit(launch(sys.argv[1:]))
