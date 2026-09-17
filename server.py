import json
import os
import time
import uuid
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("GigaChat Ultra Subagent")

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://api.giga.chat/v1/chat/completions"

MODEL = "GigaChat-3-Ultra"
TEMPERATURE = 0.15
MAX_TOKENS = 32768

MAX_TASK_FILE_BYTES = 2 * 1024 * 1024
ALLOWED_TEXT_SUFFIXES = {".md", ".txt"}

MAX_AGENT_FILE_BYTES = 2 * 1024 * 1024
MAX_AGENT_LIST_ENTRIES = 500
MAX_AGENT_LIST_BYTES = 64 * 1024
MAX_AGENT_TOOL_ITERATIONS = 20

AGENT_FUNCTIONS = [
    {
        "name": "list_dir",
        "description": "Показать файлы и папки внутри рабочей папки.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Относительный путь внутри рабочей папки.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": "Прочитать UTF-8 текстовый файл внутри рабочей папки.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Относительный путь к текстовому файлу.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Создать или полностью перезаписать UTF-8 текстовый файл "
            "внутри рабочей папки, при необходимости создав каталоги."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Относительный путь к текстовому файлу.",
                },
                "content": {
                    "type": "string",
                    "description": "Полное новое содержимое файла.",
                },
            },
            "required": ["path", "content"],
        },
    },
]

_access_token: str | None = None
_access_token_valid_until = 0.0

async def get_access_token() -> str:
    global _access_token, _access_token_valid_until

    if _access_token and time.time() < _access_token_valid_until:
        return _access_token

    credentials = os.getenv("GIGACHAT_CREDENTIALS")
    scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

    if not credentials:
        raise RuntimeError("Не найдена переменная среды GIGACHAT_CREDENTIALS.")

    headers = {
        "Authorization": f"Basic {credentials}",
        "RqUID": str(uuid.uuid4()),
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            OAUTH_URL,
            headers=headers,
            data={"scope": scope},
        )
        response.raise_for_status()

    data = response.json()
    token = data.get("access_token")

    if not token:
        raise RuntimeError(f"GigaChat не вернул access_token: {data}")

    _access_token = token
    _access_token_valid_until = time.time() + 25 * 60
    return token

async def ask_gigachat(prompt: str) -> str:
    token = await get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            CHAT_URL,
            headers=headers,
            json=body,
        )
        response.raise_for_status()

    data = response.json()

    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason")

        if not content:
            raise RuntimeError(f"GigaChat вернул пустой ответ: {data}")

        if finish_reason and finish_reason not in ("stop", "eos"):
            raise RuntimeError(
                "Ответ GigaChat завершён нештатно. "
                f"finish_reason={finish_reason}. "
                "Возможна обрезка ответа по лимиту токенов."
            )

        return content
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Неожиданный ответ GigaChat: {data}") from exc

def _validate_workspace_root(workspace_root: str) -> Path:
    if not isinstance(workspace_root, str) or not workspace_root.strip():
        raise ValueError("workspace_root должен быть непустой строкой.")

    root = Path(workspace_root)
    if not root.is_absolute():
        raise ValueError("workspace_root должен быть абсолютным путём.")
    if not root.exists():
        raise FileNotFoundError(f"Рабочая папка не найдена: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"workspace_root не является папкой: {root}")

    return root.resolve()

def _resolve_workspace_path(root: Path, path_text: str) -> Path:
    if not isinstance(path_text, str) or not path_text.strip():
        raise ValueError("path должен быть непустой строкой.")

    relative_path = Path(path_text)
    if relative_path.is_absolute() or relative_path.drive or relative_path.anchor:
        raise ValueError("Абсолютные пути запрещены; используйте путь от workspace_root.")
    if ".." in relative_path.parts:
        raise ValueError("Выход через '..' запрещён.")

    resolved = (root / relative_path).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("Путь выходит за пределы workspace_root.")

    return resolved

def _require_text_suffix(path: Path) -> None:
    if path.suffix.lower() not in ALLOWED_TEXT_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_TEXT_SUFFIXES))
        raise ValueError(f"Разрешены только текстовые файлы: {allowed}.")

def _agent_list_dir(root: Path, path_text: str) -> dict:
    path = _resolve_workspace_path(root, path_text)
    if not path.is_dir():
        raise NotADirectoryError(f"Папка не найдена: {path_text}")

    entries = []
    truncated = False
    for child in sorted(path.iterdir(), key=lambda item: item.name.casefold()):
        if len(entries) >= MAX_AGENT_LIST_ENTRIES:
            truncated = True
            break

        if child.is_symlink():
            kind = "symlink"
        elif child.is_dir():
            kind = "directory"
        elif child.is_file():
            kind = "file"
        else:
            kind = "other"

        candidate = entries + [{"name": child.name, "type": kind}]
        encoded = json.dumps(candidate, ensure_ascii=False).encode("utf-8")
        if len(encoded) > MAX_AGENT_LIST_BYTES:
            truncated = True
            break
        entries = candidate

    return {
        "path": path.relative_to(root).as_posix() or ".",
        "entries": entries,
        "truncated": truncated,
    }

def _agent_read_file(root: Path, path_text: str) -> dict:
    path = _resolve_workspace_path(root, path_text)
    _require_text_suffix(path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл не найден: {path_text}")

    size = path.stat().st_size
    if size > MAX_AGENT_FILE_BYTES:
        raise ValueError(
            f"Файл слишком большой: {size} байт. "
            f"Лимит: {MAX_AGENT_FILE_BYTES} байт."
        )

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Файл не является корректным UTF-8: {path_text}") from exc

    return {"path": path.relative_to(root).as_posix(), "content": content}

def _agent_write_file(root: Path, path_text: str, content: str) -> dict:
    if not isinstance(content, str):
        raise ValueError("content должен быть строкой.")

    encoded_content = content.encode("utf-8")
    if len(encoded_content) > MAX_AGENT_FILE_BYTES:
        raise ValueError(
            f"Содержимое слишком большое: {len(encoded_content)} байт. "
            f"Лимит: {MAX_AGENT_FILE_BYTES} байт."
        )

    path = _resolve_workspace_path(root, path_text)
    _require_text_suffix(path)
    if path == root:
        raise ValueError("Путь файла не может совпадать с workspace_root.")

    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_parent = path.parent.resolve()
    if resolved_parent != root and root not in resolved_parent.parents:
        raise ValueError("Родительская папка выходит за пределы workspace_root.")

    path.write_text(content, encoding="utf-8")
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes_written": len(encoded_content),
    }

def _parse_agent_arguments(function_name: str, raw_arguments: object) -> dict:
    if isinstance(raw_arguments, str):
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Функция {function_name} получила невалидный JSON arguments."
            ) from exc
    elif isinstance(raw_arguments, dict):
        arguments = raw_arguments
    else:
        raise ValueError(f"Функция {function_name} получила невалидные arguments.")

    if not isinstance(arguments, dict):
        raise ValueError(f"arguments функции {function_name} должны быть объектом JSON.")
    return arguments

def _execute_agent_function(root: Path, function_call: object) -> dict:
    if not isinstance(function_call, dict):
        raise ValueError("GigaChat вернул невалидный function_call.")

    name = function_call.get("name")
    if name not in {"list_dir", "read_file", "write_file"}:
        raise ValueError(f"GigaChat запросил неизвестную функцию: {name!r}.")

    arguments = _parse_agent_arguments(name, function_call.get("arguments"))
    expected_keys = {
        "list_dir": {"path"},
        "read_file": {"path"},
        "write_file": {"path", "content"},
    }[name]
    if set(arguments) != expected_keys:
        raise ValueError(
            f"Невалидные аргументы {name}: ожидаются {sorted(expected_keys)}."
        )

    if name == "list_dir":
        return _agent_list_dir(root, arguments["path"])
    if name == "read_file":
        return _agent_read_file(root, arguments["path"])
    return _agent_write_file(root, arguments["path"], arguments["content"])

async def run_agent_task(task: str, workspace_root: str) -> str:
    """Запустить автономный GigaChat file-agent без зависимости от MCP."""
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task должен быть непустой строкой.")

    root = _validate_workspace_root(workspace_root)
    token = await get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    messages = [{"role": "user", "content": task}]
    tool_iterations = 0

    async with httpx.AsyncClient(timeout=180.0) as client:
        while True:
            body = {
                "model": MODEL,
                "messages": messages,
                "functions": AGENT_FUNCTIONS,
                "function_call": "auto",
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "stream": False,
            }
            response = await client.post(CHAT_URL, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

            try:
                choice = data["choices"][0]
                message = choice["message"]
                finish_reason = choice.get("finish_reason")
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(f"Неожиданный ответ GigaChat: {data}") from exc

            if finish_reason == "function_call":
                if tool_iterations >= MAX_AGENT_TOOL_ITERATIONS:
                    raise RuntimeError(
                        "GigaChat превысил лимит в 20 вызовов функций."
                    )

                function_call = message.get("function_call")
                assistant_message = {
                    "role": "assistant",
                    "content": message.get("content") or "",
                    "function_call": function_call,
                }
                if "functions_state_id" in message:
                    assistant_message["functions_state_id"] = message[
                        "functions_state_id"
                    ]
                messages.append(assistant_message)

                result = _execute_agent_function(root, function_call)
                function_name = function_call["name"]
                messages.append(
                    {
                        "role": "function",
                        "name": function_name,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
                tool_iterations += 1
                continue

            if finish_reason not in ("stop", "eos"):
                raise RuntimeError(
                    "Агент GigaChat завершён нештатно. "
                    f"finish_reason={finish_reason!r}."
                )

            content = message.get("content")
            if not isinstance(content, str) or not content:
                raise RuntimeError(f"GigaChat вернул пустой финальный ответ: {data}")
            return content

def _validate_text_file(path_text: str, *, must_exist: bool) -> Path:
    path = Path(path_text).expanduser()

    if not path.is_absolute():
        raise ValueError(
            "Путь должен быть абсолютным, например "
            r"M:\GitHub\ag_llm\01_ULTRA_TASK.md"
        )

    if path.suffix.lower() not in ALLOWED_TEXT_SUFFIXES:
        raise ValueError("Разрешены только текстовые файлы .md и .txt.")

    if must_exist:
        if not path.is_file():
            raise FileNotFoundError(f"Файл задачи не найден: {path}")

        size = path.stat().st_size
        if size > MAX_TASK_FILE_BYTES:
            raise ValueError(
                f"Файл задачи слишком большой: {size} байт. "
                f"Лимит: {MAX_TASK_FILE_BYTES} байт."
            )

    return path

@mcp.tool()
async def gigachat_ask(prompt: str) -> str:
    """Передай текстовую задачу GigaChat 3 Ultra как независимому субагенту."""
    return await ask_gigachat(prompt)

@mcp.tool()
async def gigachat_file_task(task_file: str, report_file: str) -> str:
    """
    Прочитай локальный файл задачи, передай его GigaChat Ultra,
    полностью перезапиши файл отчёта и верни Codex только короткий статус.
    """
    task_path = _validate_text_file(task_file, must_exist=True)
    report_path = _validate_text_file(report_file, must_exist=False)

    if task_path.parent.resolve() != report_path.parent.resolve():
        raise ValueError(
            "Для безопасности task_file и report_file должны "
            "находиться в одной папке."
        )

    task_text = task_path.read_text(encoding="utf-8-sig")

    if not task_text.strip():
        raise ValueError("Файл задачи пуст.")

    prompt = (
        "Ты работаешь как самостоятельный инженерный субагент.\n"
        "Ниже находится полное техническое задание из локального файла.\n"
        "Выполни его самостоятельно.\n"
        "Не обращайся к Codex за дополнительными рассуждениями, если задача "
        "уже содержит достаточный контекст.\n"
        "Ответ должен строго соответствовать формату, указанному "
        "в техническом задании.\n\n"
        "===== НАЧАЛО ЗАДАЧИ =====\n"
        f"{task_text}\n"
        "===== КОНЕЦ ЗАДАЧИ =====\n"
    )

    result = await ask_gigachat(prompt)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(result, encoding="utf-8")

    return (
        "Готово. GigaChat Ultra прочитал файл задачи и записал полный отчёт: "
        f"{report_path}"
    )

@mcp.tool()
async def gigachat_agent_task(task: str, workspace_root: str) -> str:
    """Запусти автономный GigaChat Ultra file-agent в указанной рабочей папке."""
    return await run_agent_task(task, workspace_root)

if __name__ == "__main__":
    mcp.run(transport="stdio")
