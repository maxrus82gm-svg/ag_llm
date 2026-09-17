from pathlib import Path
import shutil

server_path = Path("server.py")

if not server_path.is_file():
    raise SystemExit("server.py не найден в текущей папке.")

text = server_path.read_text(encoding="utf-8")

old = 'ALLOWED_TEXT_SUFFIXES = {".md", ".txt"}'
new = 'ALLOWED_TEXT_SUFFIXES = {".md", ".txt", ".py"}'

if old not in text:
    if new in text:
        raise SystemExit("PATCH НЕ НУЖЕН: .py уже разрешён.")
    raise SystemExit(
        "Не найден ожидаемый ALLOWED_TEXT_SUFFIXES. "
        "server.py отличается от ожидаемой версии."
    )

backup_path = Path("server.py.before_allow_py")

if not backup_path.exists():
    shutil.copy2(server_path, backup_path)

updated = text.replace(old, new, 1)

compile(updated, str(server_path), "exec")
server_path.write_text(updated, encoding="utf-8")

print("PATCH OK")
print("Разрешены расширения: .md, .txt, .py")
print("Backup:", backup_path)
print("Updated:", server_path)
print("Syntax: OK")
