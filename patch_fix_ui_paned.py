from pathlib import Path
import shutil

ui_path = Path("ultra_ui.py")

if not ui_path.is_file():
    raise SystemExit("ultra_ui.py не найден в текущей папке.")

text = ui_path.read_text(encoding="utf-8")

old_left = '        paned.add(left_frame, minsize=260)\n'
new_left = '        paned.add(left_frame, weight=0)\n'

old_right = '        paned.add(right_frame)\n'
new_right = (
    '        paned.add(right_frame, weight=1)\n'
    '        self.after_idle(lambda: paned.sashpos(0, 340))\n'
)

if old_left not in text:
    raise SystemExit(
        'Не найдена ожидаемая строка: paned.add(left_frame, minsize=260)'
    )

if old_right not in text:
    raise SystemExit(
        'Не найдена ожидаемая строка: paned.add(right_frame)'
    )

backup = Path("ultra_ui.py.before_paned_fix")
if not backup.exists():
    shutil.copy2(ui_path, backup)

updated = text.replace(old_left, new_left, 1)
updated = updated.replace(old_right, new_right, 1)

compile(updated, str(ui_path), "exec")
ui_path.write_text(updated, encoding="utf-8")

print("PATCH OK")
print("Исправлено: ttk.PanedWindow больше не получает unsupported minsize.")
print("Левая панель: weight=0")
print("Правая панель: weight=1")
print("Начальная позиция разделителя: 340 px")
print("Backup:", backup)
print("Syntax: OK")
