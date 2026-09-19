from __future__ import annotations
import py_compile
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UI = ROOT / 'ultra_ui.py'
STATE = ROOT / 'ui_state.py'
STATE_V2 = ROOT / 'ui_state_v2.py'
UI_BACKUP = ROOT / 'ultra_ui.py.before_step3_layout_polish'
STATE_BACKUP = ROOT / 'ui_state.py.before_step3_layout_polish'

REPLACEMENTS = [('NORMAL GEOMETRY', '        self.geometry(self._ui_state.get("geometry") or "1500x860")', '        self.geometry(\n            self._ui_state.get("normal_geometry") or "1500x860"\n        )'), ('WINDOW STATE INIT', '        self._workspace_registry: list[dict] = list(\n            self._ui_state.get("workspaces") or []\n        )\n        self._theme_colors: dict[str, str] = {}\n\n        self._build_ui()\n        self._apply_theme()\n        self._record_context_storage_mtime()\n        self._initialize_workspace_registry()\n        self.after_idle(self._restore_panel_layout)\n        self.protocol("WM_DELETE_WINDOW", self._on_close)\n', '        self._workspace_registry: list[dict] = list(\n            self._ui_state.get("workspaces") or []\n        )\n        self._theme_colors: dict[str, str] = {}\n        self._last_window_mode = "normal"\n        self._last_root_width: int | None = None\n        self._layout_sync_after = None\n\n        self._build_ui()\n        self._apply_theme()\n        self._record_context_storage_mtime()\n        self._initialize_workspace_registry()\n        self.bind("<Configure>", self._on_root_configure)\n        self.after_idle(self._restore_window_and_layout)\n        self.protocol("WM_DELETE_WINDOW", self._on_close)\n'), ('PANED STYLE', '        self.main_paned = tk.PanedWindow(\n            root,\n            orient="horizontal",\n            sashwidth=6,\n            showhandle=False,\n            bd=0,\n            relief="flat",\n        )\n', '        self.main_paned = tk.PanedWindow(\n            root,\n            orient="horizontal",\n            sashwidth=5,\n            showhandle=False,\n            bd=0,\n            relief="flat",\n            sashrelief="flat",\n            bg="#2b2d30",\n        )\n'), ('PANED RELEASE', '        self.main_paned.bind(\n            "<ButtonRelease-1>",\n            lambda _event: self.after(40, self._save_ui_state),\n        )\n', '        self.main_paned.bind(\n            "<ButtonRelease-1>",\n            self._on_sash_release,\n        )\n'), ('THEME BORDER', '        self._theme_colors = {\n            "bg": bg,\n            "panel": panel,\n            "field": field,\n            "fg": fg,\n            "muted": muted,\n            "select_bg": select_bg,\n            "button_bg": button_bg,\n        }\n\n        self.configure(bg=bg)\n', '        border = "#474b50" if dark else "#b7b7b7"\n        progress_bar = "#c8c8c8" if dark else "#666666"\n\n        self._theme_colors = {\n            "bg": bg,\n            "panel": panel,\n            "field": field,\n            "fg": fg,\n            "muted": muted,\n            "select_bg": select_bg,\n            "button_bg": button_bg,\n            "border": border,\n            "progress_bar": progress_bar,\n        }\n\n        self.configure(bg=bg)\n        paned = getattr(self, "main_paned", None)\n        if paned is not None:\n            try:\n                paned.configure(bg=panel)\n            except tk.TclError:\n                pass\n'), ('TTK POLISH', '        style.configure("TSpinbox", fieldbackground=field, foreground=fg)\n        style.map(\n', '        style.configure("TSpinbox", fieldbackground=field, foreground=fg)\n        style.configure(\n            "TLabelframe",\n            background=panel,\n            foreground=fg,\n            bordercolor=border,\n            lightcolor=border,\n            darkcolor=border,\n            relief="solid",\n        )\n        style.configure(\n            "TLabelframe.Label",\n            background=panel,\n            foreground=fg,\n        )\n        style.configure(\n            "Vertical.TScrollbar",\n            background=button_bg,\n            troughcolor=field,\n            bordercolor=panel,\n            arrowcolor=fg,\n            lightcolor=button_bg,\n            darkcolor=button_bg,\n        )\n        style.configure(\n            "Ultra.Horizontal.TProgressbar",\n            troughcolor=field,\n            background=progress_bar,\n            bordercolor=border,\n            lightcolor=progress_bar,\n            darkcolor=progress_bar,\n            thickness=10,\n        )\n        style.map(\n'), ('TEXT/SCROLLBAR THEME', '        for name in ("trace_log", "chat", "input_box"):\n            widget = getattr(self, name, None)\n            if widget is not None:\n                widget.configure(\n                    bg=field,\n                    fg=fg,\n                    insertbackground=fg,\n                    selectbackground=select_bg,\n                    selectforeground=fg,\n                )\n', '        for name in ("trace_log", "chat", "input_box"):\n            widget = getattr(self, name, None)\n            if widget is not None:\n                widget.configure(\n                    bg=field,\n                    fg=fg,\n                    insertbackground=fg,\n                    selectbackground=select_bg,\n                    selectforeground=fg,\n                    relief="flat",\n                    borderwidth=0,\n                    highlightthickness=0,\n                )\n                frame = getattr(widget, "frame", None)\n                if frame is not None:\n                    try:\n                        frame.configure(\n                            bg=panel,\n                            relief="flat",\n                            borderwidth=0,\n                            highlightthickness=1,\n                            highlightbackground=border,\n                            highlightcolor=border,\n                        )\n                    except tk.TclError:\n                        pass\n                vbar = getattr(widget, "vbar", None)\n                if vbar is not None:\n                    try:\n                        vbar.configure(\n                            bg=button_bg,\n                            troughcolor=field,\n                            activebackground=select_bg,\n                            relief="flat",\n                            borderwidth=0,\n                            highlightthickness=0,\n                            width=12,\n                        )\n                    except tk.TclError:\n                        pass\n'), ('CHAT SECTION', '        ttk.Separator(right_frame).pack(fill="x", pady=8)\n\n        ttk.Label(right_frame, text="Чат").pack(anchor="w")\n        self.chat = scrolledtext.ScrolledText(\n            right_frame,\n            wrap="word",\n            state="disabled",\n            font=("Segoe UI", 10),\n        )\n        self.chat.pack(fill="both", expand=True, pady=(5, 8))\n', '        ttk.Separator(right_frame).pack(fill="x", pady=8)\n\n        chat_section = ttk.LabelFrame(\n            right_frame,\n            text="Чат",\n            padding=4,\n        )\n        chat_section.pack(fill="both", expand=True, pady=(0, 8))\n\n        self.chat = scrolledtext.ScrolledText(\n            chat_section,\n            wrap="word",\n            state="disabled",\n            font=("Segoe UI", 10),\n        )\n        self.chat.pack(fill="both", expand=True)\n'), ('MESSAGE SECTION', '        ttk.Label(right_frame, text="Сообщение").pack(anchor="w")\n        self.input_box = scrolledtext.ScrolledText(\n            right_frame,\n            wrap="word",\n            height=7,\n            font=("Segoe UI", 10),\n            undo=True,\n        )\n        self.input_box.pack(fill="x", pady=(5, 8))\n', '        message_section = ttk.LabelFrame(\n            right_frame,\n            text="Сообщение",\n            padding=4,\n        )\n        message_section.pack(fill="x", pady=(0, 8))\n\n        self.input_box = scrolledtext.ScrolledText(\n            message_section,\n            wrap="word",\n            height=7,\n            font=("Segoe UI", 10),\n            undo=True,\n        )\n        self.input_box.pack(fill="x")\n'), ('PROGRESS STYLE', '        self.progress = ttk.Progressbar(\n            status_frame,\n            mode="indeterminate",\n            length=180,\n        )\n', '        self.progress = ttk.Progressbar(\n            status_frame,\n            mode="indeterminate",\n            length=180,\n            style="Ultra.Horizontal.TProgressbar",\n        )\n')]

METHODS_NEW = '    def _window_mode(self) -> str:\n        try:\n            return "zoomed" if self.state() == "zoomed" else "normal"\n        except tk.TclError:\n            return "normal"\n\n    def _capture_panel_ratios(self) -> list[float]:\n        paned = getattr(self, "main_paned", None)\n        if paned is None:\n            return []\n        try:\n            width = int(paned.winfo_width())\n            if width < 800:\n                return []\n            left_x = int(paned.sash_coord(0)[0])\n            right_x = int(paned.sash_coord(1)[0])\n        except (tk.TclError, IndexError):\n            return []\n\n        if not (0 < left_x < right_x < width):\n            return []\n\n        return [\n            round(left_x / width, 6),\n            round(right_x / width, 6),\n        ]\n\n    def _store_current_panel_ratios(self) -> None:\n        ratios = self._capture_panel_ratios()\n        if len(ratios) != 2:\n            return\n\n        mode = self._window_mode()\n        panel_ratios = self._ui_state.setdefault(\n            "panel_ratios",\n            {\n                "normal": [0.24, 0.80],\n                "zoomed": [0.24, 0.80],\n            },\n        )\n        panel_ratios[mode] = ratios\n\n    def _apply_panel_ratios(self, mode: str | None = None) -> None:\n        paned = getattr(self, "main_paned", None)\n        if paned is None:\n            return\n\n        if mode not in {"normal", "zoomed"}:\n            mode = self._window_mode()\n\n        try:\n            self.update_idletasks()\n            width = int(paned.winfo_width())\n            if width < 900:\n                return\n\n            all_ratios = self._ui_state.get("panel_ratios") or {}\n            ratios = all_ratios.get(mode) or [0.24, 0.80]\n            left_ratio = float(ratios[0])\n            right_ratio = float(ratios[1])\n\n            # Минимальные размеры панелей:\n            # left >= 240, center >= 600, right >= 240.\n            left_x = int(round(width * left_ratio))\n            right_x = int(round(width * right_ratio))\n\n            left_x = max(240, min(left_x, width - 840))\n            right_x = max(left_x + 600, right_x)\n            right_x = min(right_x, width - 240)\n\n            paned.sash_place(0, left_x, 0)\n            paned.sash_place(1, right_x, 0)\n        except (tk.TclError, ValueError, TypeError, IndexError):\n            pass\n\n    def _restore_window_and_layout(self) -> None:\n        desired = self._ui_state.get("window_state")\n        if desired not in {"normal", "zoomed"}:\n            desired = "normal"\n\n        self._last_window_mode = "normal"\n        self.update_idletasks()\n\n        if desired == "zoomed":\n            try:\n                self.state("zoomed")\n                self._last_window_mode = "zoomed"\n            except tk.TclError:\n                self._last_window_mode = "normal"\n\n        self.after(\n            100,\n            lambda: self._apply_panel_ratios(self._window_mode()),\n        )\n\n    def _on_sash_release(self, _event=None) -> None:\n        self.after(30, self._save_ui_state)\n\n    def _on_root_configure(self, event) -> None:\n        if event.widget is not self:\n            return\n\n        if self._layout_sync_after is not None:\n            try:\n                self.after_cancel(self._layout_sync_after)\n            except tk.TclError:\n                pass\n\n        self._layout_sync_after = self.after(\n            140,\n            self._sync_window_layout,\n        )\n\n    def _sync_window_layout(self) -> None:\n        self._layout_sync_after = None\n        mode = self._window_mode()\n        width = int(self.winfo_width())\n\n        mode_changed = mode != self._last_window_mode\n        width_changed = (\n            self._last_root_width is not None\n            and abs(width - self._last_root_width) > 2\n        )\n\n        self._last_window_mode = mode\n        self._last_root_width = width\n        self._ui_state["window_state"] = mode\n\n        if mode == "normal":\n            geometry = self.geometry()\n            if geometry:\n                self._ui_state["normal_geometry"] = geometry\n\n        # При maximize/restore или resize пересчитываем sash из ПРОПОРЦИЙ\n        # текущего canvas, а не переносим старые абсолютные пиксели.\n        if mode_changed or width_changed:\n            self._apply_panel_ratios(mode)\n\n        try:\n            save_ui_state(self._ui_state)\n        except Exception:\n            pass\n\n    def _reset_panel_layout(self) -> None:\n        self._ui_state["panel_ratios"] = {\n            "normal": [0.24, 0.80],\n            "zoomed": [0.24, 0.80],\n        }\n        self._apply_panel_ratios(self._window_mode())\n        self._save_ui_state(silent=True)\n\n    def _save_ui_state(self, _event=None, *, silent: bool = True) -> None:\n        try:\n            mode = self._window_mode()\n            self._store_current_panel_ratios()\n\n            if mode == "normal":\n                geometry = self.geometry()\n                if geometry:\n                    self._ui_state["normal_geometry"] = geometry\n\n            self._ui_state["window_state"] = mode\n            self._ui_state["dark_theme"] = self.dark_theme_var.get()\n            self._ui_state["colors"] = {\n                "log": self.log_text_color_var.get(),\n                "user": self.user_text_color_var.get(),\n                "assistant": self.assistant_text_color_var.get(),\n                "workspace": self.workspace_text_color_var.get(),\n            }\n            self._ui_state["workspaces"] = list(self._workspace_registry)\n            self._ui_state["active_workspace_id"] = self.current_workspace_id\n            save_ui_state(self._ui_state)\n        except Exception as exc:\n            if not silent:\n                messagebox.showerror(\n                    APP_TITLE,\n                    f"Не удалось сохранить UI state.\\\\n\\\\n"\n                    f"{type(exc).__name__}: {exc}",\n                )\n\n    def _on_close(self) -> None:\n        self._save_ui_state(silent=True)\n        self.destroy()\n\n    def _apply_workspace_sidebar_theme(self) -> None:\n'


METHODS_PATTERN = re.compile(
    r"    def _capture_panel_sashes\(self\) -> list\[int\]:\n"
    r".*?"
    r"    def _apply_workspace_sidebar_theme\(self\) -> None:\n",
    re.S,
)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly 1 match, found {count}. "
            "No files were changed."
        )
    return text.replace(old, new, 1)


def main() -> int:
    if not UI.is_file():
        raise FileNotFoundError(f"Missing: {UI}")
    if not STATE.is_file():
        raise FileNotFoundError(f"Missing: {STATE}")
    if not STATE_V2.is_file():
        raise FileNotFoundError(
            "Missing ui_state_v2.py next to apply_step3_layout_polish.py."
        )

    ui_original = UI.read_text(encoding="utf-8-sig")
    state_original = STATE.read_text(encoding="utf-8-sig")
    state_v2 = STATE_V2.read_text(encoding="utf-8-sig")

    if "_initialize_workspace_registry" not in ui_original:
        raise RuntimeError(
            "STEP 3 baseline not found in ultra_ui.py. Install STEP 3 first."
        )
    if "_restore_window_and_layout" in ui_original:
        print("Layout polish already appears to be installed.")
        return 0
    if "panel_sashes" not in state_original:
        raise RuntimeError("Expected STEP 3 ui_state.py baseline not found.")

    if UI_BACKUP.exists() or STATE_BACKUP.exists():
        raise FileExistsError(
            "Layout-polish backup already exists. "
            "Refusing to overwrite an earlier backup."
        )

    ui_patched = ui_original
    for label, old, new in REPLACEMENTS:
        ui_patched = replace_once(ui_patched, old, new, label)

    ui_patched, count = METHODS_PATTERN.subn(METHODS_NEW, ui_patched, count=1)
    if count != 1:
        raise RuntimeError(
            f"WINDOW LAYOUT METHODS: expected 1 match, found {count}. "
            "No files were changed."
        )

    tmp_ui = ROOT / ".ultra_ui.layout_polish.candidate.py"
    tmp_state = ROOT / ".ui_state.layout_polish.candidate.py"
    tmp_ui.write_text(ui_patched, encoding="utf-8", newline="\n")
    tmp_state.write_text(state_v2, encoding="utf-8", newline="\n")

    try:
        py_compile.compile(str(tmp_ui), doraise=True)
        py_compile.compile(str(tmp_state), doraise=True)
    finally:
        try:
            tmp_ui.unlink()
        except FileNotFoundError:
            pass
        try:
            tmp_state.unlink()
        except FileNotFoundError:
            pass

    shutil.copy2(UI, UI_BACKUP)
    shutil.copy2(STATE, STATE_BACKUP)

    UI.write_text(ui_patched, encoding="utf-8", newline="\n")
    STATE.write_text(state_v2, encoding="utf-8", newline="\n")

    py_compile.compile(str(UI), doraise=True)
    py_compile.compile(str(STATE), doraise=True)

    print("OK: STEP 3 layout polish installed.")
    print("Backups:")
    print(f"  {UI_BACKUP.name}")
    print(f"  {STATE_BACKUP.name}")
    print("Fixed:")
    print("  - normal/maximized layouts stored separately")
    print("  - pane positions stored as ratios, not absolute pixels")
    print("  - panes scale proportionally inside current window canvas")
    print("  - old STEP 3 pixel layout is reset once during v1 -> v2 migration")
    print("  - dark PanedWindow separators")
    print("  - framed Chat and Message sections")
    print("  - dark-theme aligned ScrolledText borders/scrollbars")
    print("  - dark progress track with neutral light runner")
    print("")
    print("Restart the application before testing.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
