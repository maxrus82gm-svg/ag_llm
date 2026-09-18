from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
UI = ROOT / "ultra_ui.py"
BACKUP = ROOT / "ultra_ui.py.before_log_repair"

if not UI.is_file():
    raise SystemExit("ERROR: ultra_ui.py не найден рядом с repair-скриптом.")

text = UI.read_text(encoding="utf-8")

replacements = [
    (
        'except FileNotFoundFileError:',
        'except FileNotFoundError:',
        'исправление имени FileNotFoundError',
    ),
    (
        '        delete_scope_button = ttk.Button(\n'
        '            run_scope_button = ttk.Button(\n'
        '            security,',
        '        delete_scope_button = ttk.Button(\n'
        '            security,',
        'исправление кнопки области удаления',
    ),
    (
        '        if event_type == "tool_error":\n'
        '            seq = event типа == "tool_error":\n'
        '            seq = event.get("tool_sequence")',
        '        if event_type == "tool_error":\n'
        '            seq = event.get("tool_sequence")',
        'исправление повреждённого блока tool_error',
    ),
]

for old, new, label in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"ERROR: {label}: ожидалось 1 совпадение, найдено {count}. "
            "ultra_ui.py НЕ изменён."
        )
    text = text.replace(old, new, 1)

compile(text, "ultra_ui.py", "exec")

shutil.copy2(UI, BACKUP)
UI.write_text(text, encoding="utf-8")

print("OK: ultra_ui.py repaired")
print("Syntax: OK")
print(f"Backup: {BACKUP.name}")
print("Теперь можно снова запускать Start_Ultra.cmd")
