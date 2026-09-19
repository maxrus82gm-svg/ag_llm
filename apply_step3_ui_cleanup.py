from __future__ import annotations
import py_compile
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UI = ROOT / 'ultra_ui.py'
BACKUP = ROOT / 'ultra_ui.py.before_step3_ui_cleanup'

TOP_WORKSPACE_PATTERN = re.compile('        # Workspace — намеренно компактный: оставляем справа запас под будущие controls\\.\\n        workspace_frame = ttk\\.Frame\\(right_frame\\)\\n.*?        self\\.workspace_button\\.grid\\(row=0, column=2, sticky="w"\\)\\n\\n', re.S)
TOP_WORKSPACE_REPLACEMENT = '        # Центральная системная зона.\n        # Активный Workspace выбирается только через правую панель.\n        ttk.Label(\n            right_frame,\n            text="НАСТРОЙКИ ИНСТРУМЕНТОВ LLM",\n        ).pack(anchor="w", pady=(0, 6))\n\n'
REPLACEMENTS = [('SECURITY PACK', '        security.pack(fill="x", pady=(10, 8))\n', '        security.pack(fill="x", pady=(0, 8))\n'), ('WORKSPACE SCROLLBAR LAYOUT', '        host = ttk.Frame(panel)\n        host.pack(fill="both", expand=True)\n\n        self.workspace_canvas = tk.Canvas(\n            host,\n            highlightthickness=0,\n            bd=0,\n        )\n        scroll = ttk.Scrollbar(\n            host,\n            orient="vertical",\n            command=self.workspace_canvas.yview,\n        )\n        self.workspace_canvas.configure(yscrollcommand=scroll.set)\n\n        self.workspace_canvas.pack(side="left", fill="both", expand=True)\n        scroll.pack(side="right", fill="y")\n', '        host = ttk.Frame(panel)\n        host.pack(fill="both", expand=True)\n        host.columnconfigure(0, weight=1)\n        host.columnconfigure(1, weight=0)\n        host.rowconfigure(0, weight=1)\n\n        self.workspace_canvas = tk.Canvas(\n            host,\n            highlightthickness=0,\n            bd=0,\n            width=1,\n        )\n        scroll = ttk.Scrollbar(\n            host,\n            orient="vertical",\n            command=self.workspace_canvas.yview,\n        )\n        self.workspace_canvas.configure(yscrollcommand=scroll.set)\n\n        # GRID здесь намеренно: scrollbar получает собственную колонку\n        # и больше не может быть вытеснен Canvas при сужении правой панели.\n        self.workspace_canvas.grid(\n            row=0,\n            column=0,\n            sticky="nsew",\n        )\n        scroll.grid(\n            row=0,\n            column=1,\n            sticky="ns",\n        )\n'), ('RUN CONTROLS', '        self.send_button.configure(state=state)\n        self.workspace_entry.configure(state=state)\n        self.workspace_button.configure(state=state)\n        for widget in self._security_widgets:\n', '        self.send_button.configure(state=state)\n        for widget in self._security_widgets:\n'), ('CHOOSE WORKSPACE COMPAT', '    def _choose_workspace(self) -> None:\n        self._add_workspace_dialog()\n\n', '    def _choose_workspace(self) -> None:\n        # Совместимость для внутренних/старых вызовов.\n        # В UI создание и подключение Workspace выполняется справа.\n        self._add_workspace_dialog()\n\n')]


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

    original = UI.read_text(encoding="utf-8-sig")

    required_markers = (
        "_initialize_workspace_registry",
        "_restore_window_and_layout",
        "Ultra.Horizontal.TProgressbar",
        "+ Создать Workspace",
    )
    missing = [marker for marker in required_markers if marker not in original]
    if missing:
        raise RuntimeError(
            "Expected polished STEP 3 baseline not found. Missing: "
            + ", ".join(missing)
        )

    if "НАСТРОЙКИ ИНСТРУМЕНТОВ LLM" in original:
        print("STEP 3 UI cleanup already appears to be installed.")
        return 0

    if BACKUP.exists():
        raise FileExistsError(
            f"Backup already exists: {BACKUP.name}. "
            "Refusing to overwrite an earlier backup."
        )

    patched, count = TOP_WORKSPACE_PATTERN.subn(
        TOP_WORKSPACE_REPLACEMENT,
        original,
        count=1,
    )
    if count != 1:
        raise RuntimeError(
            "TOP WORKSPACE BLOCK: expected exactly 1 match, "
            f"found {count}. No files were changed."
        )

    for label, old, new in REPLACEMENTS:
        patched = replace_once(patched, old, new, label)

    candidate = ROOT / ".ultra_ui.step3_ui_cleanup.candidate.py"
    candidate.write_text(patched, encoding="utf-8", newline="\n")

    try:
        py_compile.compile(str(candidate), doraise=True)
    finally:
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass

    shutil.copy2(UI, BACKUP)
    UI.write_text(patched, encoding="utf-8", newline="\n")
    py_compile.compile(str(UI), doraise=True)

    print("OK: STEP 3 UI cleanup installed.")
    print(f"Backup: {BACKUP.name}")
    print("Changed:")
    print("  - removed duplicate top Workspace/path controls")
    print("  - added central title: НАСТРОЙКИ ИНСТРУМЕНТОВ LLM")
    print("  - moved security block upward")
    print("  - fixed Workspace scrollbar so it cannot disappear when narrow")
    print("  - kept right-side Workspace creation/selection as the single UI flow")
    print("")
    print("Restart the application before testing.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
