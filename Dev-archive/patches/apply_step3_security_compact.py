from __future__ import annotations
import py_compile
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UI = ROOT / 'ultra_ui.py'
BACKUP = ROOT / 'ultra_ui.py.before_step3_security_compact'
REPLACEMENTS = [('TOP ROW', '        # Верхняя строка: backup, лимит инструментов и тема.\n        backup_check = ttk.Checkbutton(\n            security,\n            text="Автобэкап ДО запуска",\n            variable=self.auto_backup_var,\n        )\n        backup_check.grid(\n            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4)\n        )\n\n        ttk.Label(security, text="Лимит tools:").grid(\n            row=0, column=2, sticky="e", padx=(12, 4), pady=(0, 4)\n        )\n        tool_limit_spin = ttk.Spinbox(\n            security,\n            from_=1,\n            to=200,\n            width=6,\n            textvariable=self.tool_limit_var,\n        )\n        tool_limit_spin.grid(\n            row=0, column=3, sticky="w", pady=(0, 4)\n        )\n', '        # Верхняя компактная строка.\n        # Backup для UI считается обязательной системной защитой и\n        # не занимает место отдельной пользовательской настройкой.\n        ttk.Label(security, text="Лимит tools:").grid(\n            row=0, column=0, sticky="w", padx=(0, 4), pady=(0, 2)\n        )\n        tool_limit_spin = ttk.Spinbox(\n            security,\n            from_=1,\n            to=200,\n            width=6,\n            textvariable=self.tool_limit_var,\n        )\n        tool_limit_spin.grid(\n            row=0, column=1, sticky="w", padx=(0, 14), pady=(0, 2)\n        )\n\n        verify_check = ttk.Checkbutton(\n            security,\n            text="VERIFY",\n            variable=self.allow_verify_var,\n        )\n        verify_check.grid(\n            row=0, column=2, columnspan=2, sticky="w", pady=(0, 2)\n        )\n'), ('READ ROW', '        # Галочка чтения находится прямо у области, которой она управляет.\n        read_check = ttk.Checkbutton(\n            security,\n            text="",\n            variable=self.allow_read_var,\n        )\n        read_check.grid(row=1, column=0, sticky="w", pady=(4, 0))\n\n        ttk.Label(security, text="Чтение только в:").grid(\n            row=1, column=1, sticky="w", padx=(2, 0), pady=(4, 0)\n        )\n        read_scope_entry = ttk.Entry(\n            security,\n            textvariable=self.read_scope_var,\n            width=62,\n        )\n        read_scope_entry.grid(\n            row=1, column=2, sticky="w", padx=(8, 8), pady=(4, 0)\n        )\n        bind_edit_shortcuts(read_scope_entry)\n        read_scope_button = ttk.Button(\n            security,\n            text="Выбрать",\n            command=lambda: self._choose_scope(self.read_scope_var),\n        )\n        read_scope_button.grid(row=1, column=3, sticky="w", pady=(4, 0))\n', '        # Компактные и одинаковые строки областей доступа.\n        read_check = ttk.Checkbutton(\n            security,\n            text="",\n            variable=self.allow_read_var,\n        )\n        read_check.grid(row=1, column=0, sticky="w", pady=2)\n\n        ttk.Label(security, text="Чтение только в:").grid(\n            row=1, column=1, sticky="w", padx=(2, 0), pady=2\n        )\n        read_scope_entry = ttk.Entry(\n            security,\n            textvariable=self.read_scope_var,\n            width=38,\n        )\n        read_scope_entry.grid(\n            row=1, column=2, sticky="w", padx=(6, 4), pady=2\n        )\n        bind_edit_shortcuts(read_scope_entry)\n        read_scope_button = ttk.Button(\n            security,\n            text="...",\n            width=3,\n            command=lambda: self._choose_scope(self.read_scope_var),\n        )\n        read_scope_button.grid(\n            row=1, column=3, sticky="w", pady=2\n        )\n'), ('WRITE ROW', '        # Галочка записи находится прямо у области, которой она управляет.\n        write_check = ttk.Checkbutton(\n            security,\n            text="",\n            variable=self.allow_write_var,\n        )\n        write_check.grid(row=2, column=0, sticky="w", pady=(6, 0))\n\n        ttk.Label(security, text="Запись только в:").grid(\n            row=2, column=1, sticky="w", padx=(2, 0), pady=(6, 0)\n        )\n        write_scope_entry = ttk.Entry(\n            security,\n            textvariable=self.write_scope_var,\n            width=62,\n        )\n        write_scope_entry.grid(\n            row=2, column=2, sticky="w", padx=(8, 8), pady=(6, 0)\n        )\n        bind_edit_shortcuts(write_scope_entry)\n        write_scope_button = ttk.Button(\n            security,\n            text="Выбрать",\n            command=lambda: self._choose_scope(self.write_scope_var),\n        )\n        write_scope_button.grid(row=2, column=3, sticky="w", pady=(6, 0))\n', '        write_check = ttk.Checkbutton(\n            security,\n            text="",\n            variable=self.allow_write_var,\n        )\n        write_check.grid(row=2, column=0, sticky="w", pady=2)\n\n        ttk.Label(security, text="Запись только в:").grid(\n            row=2, column=1, sticky="w", padx=(2, 0), pady=2\n        )\n        write_scope_entry = ttk.Entry(\n            security,\n            textvariable=self.write_scope_var,\n            width=38,\n        )\n        write_scope_entry.grid(\n            row=2, column=2, sticky="w", padx=(6, 4), pady=2\n        )\n        bind_edit_shortcuts(write_scope_entry)\n        write_scope_button = ttk.Button(\n            security,\n            text="...",\n            width=3,\n            command=lambda: self._choose_scope(self.write_scope_var),\n        )\n        write_scope_button.grid(\n            row=2, column=3, sticky="w", pady=2\n        )\n'), ('DELETE ROW', '        # Удаление — отдельное разрешение, независимо от записи.\n        delete_check = ttk.Checkbutton(\n            security,\n            text="",\n            variable=self.allow_delete_var,\n        )\n        delete_check.grid(row=3, column=0, sticky="w", pady=(6, 0))\n\n        ttk.Label(security, text="Удаление только в:").grid(\n            row=3, column=1, sticky="w", padx=(2, 0), pady=(6, 0)\n        )\n        delete_scope_entry = ttk.Entry(\n            security,\n            textvariable=self.delete_scope_var,\n            width=62,\n        )\n        delete_scope_entry.grid(\n            row=3, column=2, sticky="w", padx=(8, 8), pady=(6, 0)\n        )\n        bind_edit_shortcuts(delete_scope_entry)\n        delete_scope_button = ttk.Button(\n            security,\n            text="Выбрать",\n            command=lambda: self._choose_scope(self.delete_scope_var),\n        )\n        delete_scope_button.grid(row=3, column=3, sticky="w", pady=(6, 0))\n', '        # Удаление — отдельное разрешение, независимо от записи.\n        delete_check = ttk.Checkbutton(\n            security,\n            text="",\n            variable=self.allow_delete_var,\n        )\n        delete_check.grid(row=3, column=0, sticky="w", pady=2)\n\n        ttk.Label(security, text="Удаление только в:").grid(\n            row=3, column=1, sticky="w", padx=(2, 0), pady=2\n        )\n        delete_scope_entry = ttk.Entry(\n            security,\n            textvariable=self.delete_scope_var,\n            width=38,\n        )\n        delete_scope_entry.grid(\n            row=3, column=2, sticky="w", padx=(6, 4), pady=2\n        )\n        bind_edit_shortcuts(delete_scope_entry)\n        delete_scope_button = ttk.Button(\n            security,\n            text="...",\n            width=3,\n            command=lambda: self._choose_scope(self.delete_scope_var),\n        )\n        delete_scope_button.grid(\n            row=3, column=3, sticky="w", pady=2\n        )\n'), ('VERIFY/BACKUP/HINT', '        # VERIFY — отдельное безопасное разрешение на белый список проверок.\n        verify_check = ttk.Checkbutton(\n            security,\n            text="VERIFY — Python / Git / UI проверки",\n            variable=self.allow_verify_var,\n        )\n        verify_check.grid(\n            row=4, column=1, columnspan=3, sticky="w", pady=(6, 0)\n        )\n\n        ttk.Label(security, text="Защищённые бэкапы:").grid(\n            row=5, column=1, sticky="w", padx=(2, 0), pady=(6, 0)\n        )\n        backup_label = ttk.Label(\n            security,\n            textvariable=self.backup_path_var,\n            font=("Consolas", 8),\n        )\n        backup_label.grid(\n            row=5, column=2, columnspan=3, sticky="w", padx=(8, 0), pady=(6, 0)\n        )\n\n        hint = ttk.Label(\n            security,\n            text=(\n                "✓ слева включает доступ для строки. \'.\' = корень workspace. "\n                "Пример: чтение=\'.\' + запись=\'Документация\'."\n            ),\n        )\n        hint.grid(row=6, column=1, columnspan=4, sticky="w", pady=(8, 0))\n', '        # VERIFY остаётся явной настройкой.\n        # Backup и служебные подсказки больше не занимают место в панели.\n'), ('SECURITY WIDGET LIST', '                verify_check,\n                backup_check,\n                tool_limit_spin,\n', '                verify_check,\n                tool_limit_spin,\n'), ('RUN SUMMARY', '                f"VERIFY={\'ON\' if permissions[\'allow_verify\'] else \'OFF\'}, "\n                f"TOOLS={tool_limit}, "\n                f"BACKUP={\'ON\' if permissions[\'auto_backup\'] else \'OFF\'}."\n', '                f"VERIFY={\'ON\' if permissions[\'allow_verify\'] else \'OFF\'}, "\n                f"TOOLS={tool_limit}."\n')]


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

    required = (
        "НАСТРОЙКИ ИНСТРУМЕНТОВ LLM",
        "_restore_window_and_layout",
        "+ Создать Workspace",
    )
    missing = [marker for marker in required if marker not in original]
    if missing:
        raise RuntimeError(
            "Expected current STEP 3 UI baseline not found. Missing: "
            + ", ".join(missing)
        )

    if 'text="VERIFY",' in original:
        print("Compact security UI already appears to be installed.")
        return 0

    if BACKUP.exists():
        raise FileExistsError(
            f"Backup already exists: {BACKUP.name}. "
            "Refusing to overwrite an earlier backup."
        )

    patched = original
    for label, old, new in REPLACEMENTS:
        patched = replace_once(patched, old, new, label)

    candidate = ROOT / ".ultra_ui.security_compact.candidate.py"
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

    print("OK: STEP 3 compact security UI installed.")
    print(f"Backup: {BACKUP.name}")
    print("Changed:")
    print("  - hidden backup checkbox/path/help text from main UI")
    print("  - backup remains ON internally for normal UI runs")
    print("  - VERIFY moved to the compact top row")
    print("  - removed long VERIFY description")
    print("  - tool limit moved left")
    print("  - READ/WRITE/DELETE fields reduced to width=38")
    print("  - Browse buttons changed from 'Выбрать' to compact '...'")
    print("  - access rows now use uniform vertical spacing")
    print("  - removed BACKUP status from the chat-side run summary")
    print("")
    print("Restart the application before testing.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
