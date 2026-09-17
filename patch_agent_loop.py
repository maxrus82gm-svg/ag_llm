from pathlib import Path
import shutil

server_path = Path("server.py")
if not server_path.is_file():
    raise SystemExit("server.py не найден в текущей папке.")

text = server_path.read_text(encoding="utf-8")

old_messages = '    messages = [{"role": "user", "content": task}]\n'
new_messages = '    messages = [\n        {\n            "role": "system",\n            "content": (\n                "Ты работаешь как локальный file-agent внутри workspace. "\n                "Для всех file tools используй ТОЛЬКО относительные пути. "\n                "Корень workspace обозначай точкой \'.\'. "\n                "Никогда не передавай абсолютные Windows-пути в list_dir, "\n                "read_file или write_file."\n            ),\n        },\n        {"role": "user", "content": task},\n    ]\n'
old_execute = '                result = _execute_agent_function(root, function_call)\n                function_name = function_call["name"]\n'
new_execute = '                try:\n                    result = _execute_agent_function(root, function_call)\n                except Exception as exc:\n                    result = {\n                        "ok": False,\n                        "error_type": type(exc).__name__,\n                        "error": str(exc),\n                        "instruction": (\n                            "Исправь аргументы и повтори вызов инструмента. "\n                            "Для путей используй только относительные пути "\n                            "внутри workspace; корень обозначается \'.\'."\n                        ),\n                    }\n\n                function_name = function_call["name"]\n'

if text.count(old_messages) != 1:
    raise SystemExit(
        f"Не найден ожидаемый блок messages ровно один раз: {text.count(old_messages)}"
    )

if text.count(old_execute) != 1:
    raise SystemExit(
        f"Не найден ожидаемый блок execute ровно один раз: {text.count(old_execute)}"
    )

backup = server_path.with_name("server.py.before_agent_fix")
if not backup.exists():
    shutil.copy2(server_path, backup)

text = text.replace(old_messages, new_messages, 1)
text = text.replace(old_execute, new_execute, 1)

compile(text, str(server_path), "exec")
server_path.write_text(text, encoding="utf-8")

print("PATCH OK")
print("Backup:", backup)
print("Updated:", server_path)
print("Syntax: OK")
