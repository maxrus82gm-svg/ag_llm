import asyncio
import copy
import hashlib
from bisect import bisect_right
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid
from difflib import SequenceMatcher
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer

from context_storage import (
    ensure_workspace_storage,
    load_chat_working_messages,
    load_project_context,
)
from workspace_runtime_settings import ensure_workspace_runtime_dirs
from agent_global_context import load_agent_global_context
from server_context_messages import resolve_server_context_message
from model_registry import get_model_spec
from gigachat_transport import CHAT_URL, OAUTH_URL, get_access_token
from audit_storage import AuditThreadRecorder
from verifier_runtime import (
    DEFAULT_VERIFIER_MODEL_ID,
    VerifierProtocolError,
    VerifierRuntimeError,
    run_verifier_check,
)

mcp = MCPServer("GigaChat Ultra Subagent")

# MODEL REGISTRY хранит описание доступных моделей.
# Эти глобальные значения остаются compatibility default для старых путей;
# основной agent RUN выбирает модель локально через run_agent_task().
MAIN_CHAT_MODEL_ID = "gigachat_ultra"
MAIN_CHAT_MODEL = get_model_spec(MAIN_CHAT_MODEL_ID)
MODEL = MAIN_CHAT_MODEL.provider_model_id

TEMPERATURE = 0.15
MAX_TOKENS = 32768
MAX_AUDIT_DIAGNOSTIC_TOKENS = 160
AUDIT_DIAGNOSTIC_TIMEOUT_SECONDS = 25
AUDIT_DIAGNOSTIC_QUESTION = (
    "Судья Дредд отклонил результат. Кратко объясни, какой факт, инструкция, "
    "предыдущий контекст или предположение привели тебя к этому решению. "
    "Не спорь с FAIL. Не исправляй TASK в этом ответе. Не раскрывай "
    "пошаговые внутренние рассуждения. Дай 1–3 коротких предложения "
    "об основании решения."
)

MAX_TASK_FILE_BYTES = 2 * 1024 * 1024
ALLOWED_TEXT_SUFFIXES = {
    # Обычный текст / документация / данные
    ".txt", ".md", ".mdx", ".rst", ".log", ".csv", ".tsv",

    # Конфигурации / structured text
    ".json", ".jsonl", ".jsonc", ".json5", ".xml", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".config", ".properties", ".vdf", ".lock",
    ".reg", ".inf", ".manifest",

    # Python
    ".py", ".pyi",

    # C / C++
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".inl", ".ipp", ".tpp", ".ixx", ".cppm", ".mpp", ".rc", ".def",

    # C# / .NET / Visual Studio
    ".cs", ".csproj", ".fs", ".fsx", ".fsproj", ".vb", ".vbproj",
    ".sln", ".slnx", ".vcxproj", ".props", ".targets", ".filters",
    ".user", ".natvis",

    # Shell / Windows scripts
    ".bat", ".cmd", ".ps1", ".psm1", ".psd1", ".sh", ".bash", ".zsh", ".fish",

    # Web / JavaScript / TypeScript
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".html", ".htm", ".css", ".scss", ".sass", ".less", ".vue", ".svelte",

    # Java / Kotlin / Gradle
    ".java", ".kt", ".kts", ".gradle",

    # Другие языки разработки
    ".go", ".rs", ".lua", ".rb", ".php", ".pl", ".sql",
    ".graphql", ".gql", ".proto",

    # Build / native tooling
    ".cmake", ".mk", ".mak",

    # Assembly / include
    ".asm", ".s", ".inc",

    # Unity / shaders
    ".shader", ".compute", ".cginc", ".hlsl", ".glsl",
    ".asmdef", ".asmref", ".uxml", ".uss",
    ".shadergraph", ".shadersubgraph",
}

ALLOWED_TEXT_FILENAMES = {
    ".gitignore", ".gitattributes", ".gitmodules", ".editorconfig",
    ".dockerignore", ".npmrc", ".nvmrc",
    "Dockerfile", "Makefile", "CMakeLists.txt", "Jenkinsfile",
    "Procfile", "Vagrantfile", "Pipfile",
}

MAX_AGENT_FILE_BYTES = 2 * 1024 * 1024
MAX_FIND_TEXT_MATCHES = 100
MAX_FIND_TEXT_SNIPPET_CHARS = 120
MAX_READ_RANGE_LINES = 200
MAX_READ_RANGE_BYTES = 64 * 1024
MAX_AGENT_LIST_ENTRIES = 500
MAX_AGENT_LIST_BYTES = 64 * 1024
MAX_AGENT_TOOL_ITERATIONS = 20
MAX_CONFIGURABLE_TOOL_ITERATIONS = 200
MAX_VERIFY_OUTPUT_BYTES = 128 * 1024
MAX_FINAL_AUDIT_CONTEXT_BYTES = 1024 * 1024
MAX_FINAL_AUDIT_NEW_FILE_BYTES = MAX_VERIFY_OUTPUT_BYTES
FINAL_AUDIT_CORRECTION_LIMIT = 2
FINAL_AUDIT_REPEATED_FAILURE_THRESHOLD = 3
VERIFY_TIMEOUT_SECONDS = 30
UI_SMOKE_TIMEOUT_SECONDS = 30
MAX_VERIFICATION_GATE_RETRIES = 3

# GUARD P1 — server-side supervisor для мягкого вмешательства
# в явно подозрительные действия агента.
GUARD_P1_VERSION = 1
GUARD_P1_REPEAT_AFTER_SUCCESSES = 2
GUARD_P1_REPEAT_MAX_INTERVENTIONS = 2
GUARD_P1_MAX_INTERVENTIONS_PER_RUN = 8
GUARD_P1_CREATE_SCORE_THRESHOLD = 75
GUARD_P1_REPEAT_TOOL_NAMES = {"read_file", "list_dir"}

VERIFICATION_TOOL_NAMES = {
    "python_compile",
    "git_status",
    "git_diff",
    "ui_smoke_test",
}
READ_TOOL_NAMES = {"list_dir", "read_file", "find_text", "read_file_range"}
TEXT_MUTATION_TOOL_NAMES = {
    "write_file", "replace_text", "insert_before", "insert_after",
}
MUTATION_TOOL_NAMES = TEXT_MUTATION_TOOL_NAMES | {"delete_file"}

BACKUP_BASE = (
    Path(os.getenv("LOCALAPPDATA") or Path.home())
    / "GigaChatUltra"
    / "backups"
).resolve()

CORE_BACKUP_RELATIVE_PATHS = (
    "server.py",
    "model_registry.py",
    "context_storage.py",
    "workspace_runtime_settings.py",
    "ui_state.py",
    "ultra_ui.py",
    "Start_Ultra.cmd",
    ".gitignore",
    "agent_global_context.py",
    "server_context_messages.py",
)

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
        "description": "Прочитать целиком текстовый файл (UTF-8; .jsonl — UTF-16). Для большого файла и локальной правки предпочитай find_text/read_file_range.",
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
        "name": "find_text",
        "description": "Найти точное вхождение текста в файле; вернуть позиции, короткие фрагменты и SHA-256 содержимого. Для локальной правки большого файла начни с этого инструмента.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Относительный путь к текстовому файлу."},
            "text": {"type": "string", "description": "Непустая точная подстрока для поиска."},
        }, "required": ["path", "text"]},
    },
    {
        "name": "read_file_range",
        "description": "Прочитать только заданные строки файла (1-based, границы включительно) и вернуть SHA-256 полного logical content.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Относительный путь к текстовому файлу."},
            "start_line": {"type": "integer", "description": "Первая строка, от 1."},
            "end_line": {"type": "integer", "description": "Последняя строка включительно."},
        }, "required": ["path", "start_line", "end_line"]},
    },
    {
        "name": "write_file",
        "description": (
            "Создать файл или намеренно полностью перезаписать текстовый файл "
            "(UTF-8; .jsonl — UTF-16). Для локальной правки существующего файла "
            "предпочитай find_text/read_file_range и точные edit tools."
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
    {
        "name": "replace_text",
        "description": "Точно заменить единственное вхождение old_text после проверки SHA-256 файла. Не выполняет fuzzy replacement и не возвращает весь файл.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Относительный путь к существующему текстовому файлу."},
            "old_text": {"type": "string", "description": "Непустой уникальный точный фрагмент."},
            "new_text": {"type": "string", "description": "Новый фрагмент."},
            "expected_content_sha256": {"type": "string", "description": "SHA-256 полного logical content из find_text/read_file_range."},
        }, "required": ["path", "old_text", "new_text", "expected_content_sha256"]},
    },
    *[
        {
            "name": name,
            "description": f"Точно вставить content {'перед' if name == 'insert_before' else 'после'} единственного marker после проверки SHA-256 файла. Не возвращает весь файл.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string", "description": "Относительный путь к существующему текстовому файлу."},
                "marker": {"type": "string", "description": "Непустой уникальный точный маркер."},
                "content": {"type": "string", "description": "Вставляемый фрагмент."},
                "expected_content_sha256": {"type": "string", "description": "SHA-256 полного logical content из find_text/read_file_range."},
            }, "required": ["path", "marker", "content", "expected_content_sha256"]},
        }
        for name in ("insert_before", "insert_after")
    ],
    {
        "name": "delete_file",
        "description": (
            "Удалить существующий текстовый файл внутри рабочей папки. "
            "Инструмент доступен только когда сервер явно разрешил удаление."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Относительный путь к удаляемому текстовому файлу.",
                }
            },
            "required": ["path"],
        },
    },

    {
        "name": "python_compile",
        "description": (
            "Реально проверить синтаксис одного или нескольких Python-файлов "
            "внутри разрешённой области чтения. Использует py_compile текущего "
            "Python и не создаёт __pycache__ внутри workspace."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Список относительных путей .py внутри workspace.",
                }
            },
            "required": ["paths"],
        },
    },
    {
        "name": "git_status",
        "description": (
            "Read-only проверка git status рабочего дерева. Ничего не изменяет "
            "в Git и возвращает только файлы внутри разрешённой области чтения."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "git_diff",
        "description": (
            "Read-only git diff относительно HEAD. Показывает фактические изменения "
            "только для проверенных относительных путей в области чтения."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Относительные пути. Пустой список означает текущую "
                        "разрешённую область чтения."
                    ),
                }
            },
            "required": ["paths"],
        },
    },
    {
        "name": "ui_smoke_test",
        "description": (
            "Ограниченный runtime smoke-test ultra_ui.UltraApp. Сервер сам задаёт "
            "target; произвольный Python-код или команды передать нельзя."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

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

def get_backup_base_path() -> Path:
    """Путь к локальным защищённым backup-снимкам Ultra."""
    return BACKUP_BASE

def _is_within(path: Path, base: Path) -> bool:
    return path == base or base in path.parents

def _normalize_permissions(permissions: dict | None) -> dict:
    """Нормализовать серверные разрешения одного запуска.

    Если permissions=None, применяется безопасный fail-closed default:
    чтение разрешено во всём workspace, запись запрещена, автобэкап включён.
    UI всегда передаёт явную политику.
    """
    if permissions is None:
        permissions = {
            "allow_read": True,
            "allow_write": False,
            "allow_delete": False,
            "allow_verify": True,
            "allow_guard_p1": True,
            "read_scope": ".",
            "write_scope": ".",
            "delete_scope": ".",
            "tool_limit": MAX_AGENT_TOOL_ITERATIONS,
            "auto_backup": True,
        }
    if not isinstance(permissions, dict):
        raise ValueError("permissions должен быть словарём или None.")

    def clean_scope(value: object, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} должен быть непустым относительным путём.")
        scope = value.strip().replace("\\", "/")
        candidate = Path(scope)
        if candidate.is_absolute() or candidate.drive or candidate.anchor:
            raise ValueError(f"{name}: абсолютные пути запрещены.")
        if ".." in candidate.parts:
            raise ValueError(f"{name}: выход через '..' запрещён.")
        return candidate.as_posix() or "."

    allow_read = bool(permissions.get("allow_read", True))
    allow_write = bool(permissions.get("allow_write", False))
    allow_delete = bool(permissions.get("allow_delete", False))
    allow_verify = bool(permissions.get("allow_verify", True))
    allow_guard_p1 = bool(permissions.get("allow_guard_p1", True))
    # Защищённый backup — обязательная серверная защита.
    # Поле сохраняется в policy для обратной совместимости старых вызовов,
    # но отключить backup через permissions больше нельзя.
    auto_backup = True
    read_scope = clean_scope(permissions.get("read_scope", "."), "read_scope")
    write_scope = clean_scope(permissions.get("write_scope", "."), "write_scope")
    delete_scope = clean_scope(permissions.get("delete_scope", "."), "delete_scope")

    try:
        tool_limit = int(
            permissions.get("tool_limit", MAX_AGENT_TOOL_ITERATIONS)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("tool_limit должен быть целым числом.") from exc
    if not 1 <= tool_limit <= MAX_CONFIGURABLE_TOOL_ITERATIONS:
        raise ValueError(
            "tool_limit должен быть в диапазоне "
            f"1..{MAX_CONFIGURABLE_TOOL_ITERATIONS}."
        )

    return {
        "allow_read": allow_read,
        "allow_write": allow_write,
        "allow_delete": allow_delete,
        "allow_verify": allow_verify,
        "allow_guard_p1": allow_guard_p1,
        "read_scope": read_scope,
        "write_scope": write_scope,
        "delete_scope": delete_scope,
        "tool_limit": tool_limit,
        "auto_backup": auto_backup,
    }

def _prepare_policy_for_workspace(root: Path, policy: dict) -> dict:
    result = dict(policy)
    read_root = _resolve_workspace_path(root, result["read_scope"])
    write_root = _resolve_workspace_path(root, result["write_scope"])
    delete_root = _resolve_workspace_path(root, result["delete_scope"])

    if result["allow_read"] and not read_root.is_dir():
        raise NotADirectoryError(
            f"Разрешённая область чтения не найдена: {result['read_scope']}"
        )
    if result["allow_write"] and not write_root.is_dir():
        raise NotADirectoryError(
            f"Разрешённая область записи не найдена: {result['write_scope']}"
        )
    if result["allow_delete"] and not delete_root.is_dir():
        raise NotADirectoryError(
            f"Разрешённая область удаления не найдена: {result['delete_scope']}"
        )

    # Фундаментальный fail-closed: изменяющий RUN нельзя запускать без
    # возможности перечитать и реально проверить результат.
    if result["allow_write"] or result["allow_delete"]:
        if not result["allow_read"]:
            raise PermissionError(
                "WRITE/DELETE требуют READ=ON: сервер обязан иметь возможность "
                "перечитать и проверить изменения до SUCCESS."
            )
        if not result["allow_verify"]:
            raise PermissionError(
                "WRITE/DELETE требуют VERIFY=ON: изменяющий RUN без реальных "
                "проверок запрещён сервером."
            )
        if result["allow_write"] and not _is_within(write_root, read_root):
            raise PermissionError(
                "Область WRITE должна находиться внутри области READ: сервер "
                "обязан иметь возможность перечитать и проверить каждый файл, "
                "который Ultra может изменить."
            )
        if result["allow_delete"] and not _is_within(delete_root, read_root):
            raise PermissionError(
                "Область DELETE должна находиться внутри области READ: сервер "
                "обязан видеть изменения рабочего дерева до финального SUCCESS."
            )

    result["_read_root"] = read_root
    result["_write_root"] = write_root
    result["_delete_root"] = delete_root
    return result

def _deny_backup_area(path: Path) -> None:
    if _is_within(path, BACKUP_BASE):
        raise PermissionError(
            "Защищённая папка резервных копий недоступна агенту."
        )

def _deny_context_storage_area(root: Path, path: Path) -> None:
    context_root = (root / ".ultra").resolve()
    if _is_within(path, context_root):
        raise PermissionError(
            "Служебное хранилище .ultra недоступно обычным file tools. "
            "PROJECT CONTEXT и история должны изменяться только через "
            "контролируемый Context Storage API."
        )

def _require_operation_permission(
    root: Path, path_text: str, operation: str, policy: dict
) -> Path:
    path = _resolve_workspace_path(root, path_text)
    _deny_backup_area(path)
    _deny_context_storage_area(root, path)

    if operation in {"list", "read"}:
        if not policy["allow_read"]:
            raise PermissionError("Чтение отключено для этого запуска.")
        scope_root = policy["_read_root"]
        scope_name = policy["read_scope"]
    elif operation == "write":
        if not policy["allow_write"]:
            raise PermissionError("Запись отключена для этого запуска.")
        scope_root = policy["_write_root"]
        scope_name = policy["write_scope"]
    elif operation == "delete":
        if not policy["allow_delete"]:
            raise PermissionError("Удаление отключено для этого запуска.")
        scope_root = policy["_delete_root"]
        scope_name = policy["delete_scope"]
    else:
        raise ValueError(f"Неизвестная операция доступа: {operation}")
    if not _is_within(path, scope_root):
        raise PermissionError(
            f"Доступ запрещён сервером: {path_text!r} находится вне "
            f"разрешённой области {scope_name!r}."
        )
    return path

def _functions_for_policy(policy: dict) -> list[dict]:
    allowed_names = set()
    if policy["allow_read"]:
        allowed_names.update(READ_TOOL_NAMES)
    if policy["allow_write"]:
        allowed_names.update(TEXT_MUTATION_TOOL_NAMES)
    if policy["allow_delete"]:
        allowed_names.add("delete_file")
    # VERIFY не является обходом READ: инструменты проверки получают код/дифф
    # только когда физически разрешено чтение.
    if policy["allow_verify"] and policy["allow_read"]:
        allowed_names.update(VERIFICATION_TOOL_NAMES)
    return [item for item in AGENT_FUNCTIONS if item["name"] in allowed_names]

def _policy_summary(policy: dict) -> dict:
    return {
        "allow_read": policy["allow_read"],
        "allow_write": policy["allow_write"],
        "allow_delete": policy["allow_delete"],
        "allow_verify": policy["allow_verify"],
        "allow_guard_p1": policy["allow_guard_p1"],
        "read_scope": policy["read_scope"],
        "write_scope": policy["write_scope"],
        "delete_scope": policy["delete_scope"],
        "tool_limit": policy["tool_limit"],
        "auto_backup": policy["auto_backup"],
    }

def _write_backup_manifest(session: dict) -> None:
    manifest_path = session["backup_dir"] / "manifest.json"
    content = json.dumps(session["manifest"], ensure_ascii=False, indent=2)
    fd, temporary_name = tempfile.mkstemp(
        prefix=".manifest.", suffix=".tmp", dir=session["backup_dir"]
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
        os.replace(temporary_name, manifest_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)

def _create_backup_session(
    app_dir: Path,
    root: Path,
    run_id: str,
    task: str,
    policy: dict,
    *,
    backup_base: Path,
    workspace_id: str,
    chat_id: str | None,
) -> dict | None:
    if not policy["auto_backup"]:
        return None

    backup_dir = backup_base / run_id
    backup_dir.mkdir(parents=True, exist_ok=False)
    core_dir = backup_dir / "core"
    copied_core = []

    for relative_text in CORE_BACKUP_RELATIVE_PATHS:
        source = app_dir / Path(relative_text)
        if not source.is_file():
            continue
        destination = core_dir / Path(relative_text)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied_core.append(relative_text)

    # `.ultra` — маленькое переносимое состояние Workspace:
    # workspace metadata, PROJECT CONTEXT, чаты и RAW HISTORY.
    context_snapshot = None
    context_source = (root / ".ultra").resolve()
    if context_source.is_dir():
        context_destination = backup_dir / "context" / ".ultra"
        context_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(context_source, context_destination)
        context_snapshot = "context/.ultra"

    manifest = {
        "run_id": run_id,
        "created_at": time.time(),
        "workspace_id": workspace_id,
        "workspace": str(root),
        "chat_id": chat_id,
        "task_preview": task[:500],
        "policy": _policy_summary(policy),
        "context_snapshot": context_snapshot,
        "core_files": copied_core,
        "changed_files": [],
        "new_files": [],
        "deleted_files": [],
    }
    session = {
        "backup_dir": backup_dir,
        "backed_up_paths": set(),
        "delete_backed_up_paths": set(),
        "manifest": manifest,
    }
    _write_backup_manifest(session)
    return session

def _backup_before_write(root: Path, path: Path, session: dict | None) -> None:
    if session is None:
        return

    relative = path.relative_to(root).as_posix()
    if relative in session["backed_up_paths"]:
        return

    if path.exists():
        if not path.is_file():
            raise ValueError(f"Нельзя резервировать не-файл: {relative}")
        destination = session["backup_dir"] / "changed" / Path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        manifest_key = "changed_files"
    else:
        manifest_key = "new_files"
    updated_manifest = dict(session["manifest"])
    updated_manifest[manifest_key] = [
        *updated_manifest[manifest_key], relative
    ]
    _write_backup_manifest({**session, "manifest": updated_manifest})
    session["manifest"] = updated_manifest
    session["backed_up_paths"].add(relative)

def _backup_before_delete(root: Path, path: Path, session: dict | None) -> None:
    """Сохранить файл непосредственно перед delete_file."""
    if session is None:
        return

    relative = path.relative_to(root).as_posix()
    if relative in session["delete_backed_up_paths"]:
        return
    if not path.is_file():
        raise ValueError(f"Нельзя резервировать перед удалением не-файл: {relative}")

    destination = session["backup_dir"] / "deleted" / Path(relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)

    updated_manifest = dict(session["manifest"])
    if relative not in updated_manifest["deleted_files"]:
        updated_manifest["deleted_files"] = [
            *updated_manifest["deleted_files"], relative
        ]
    _write_backup_manifest({**session, "manifest": updated_manifest})
    session["manifest"] = updated_manifest
    session["delete_backed_up_paths"].add(relative)


def _require_text_suffix(path: Path) -> None:
    suffix = path.suffix.lower()
    name = path.name

    if suffix in ALLOWED_TEXT_SUFFIXES:
        return

    if name in ALLOWED_TEXT_FILENAMES:
        return

    if name == ".env" or name.startswith(".env."):
        return

    allowed_suffixes = ", ".join(sorted(ALLOWED_TEXT_SUFFIXES))
    allowed_names = ", ".join(sorted(ALLOWED_TEXT_FILENAMES))

    raise ValueError(
        "Формат файла не разрешён для обычных текстовых file tools. "
        f"Расширения: {allowed_suffixes}. "
        f"Специальные имена: {allowed_names}. "
        "Также разрешены .env и .env.*"
    )

def _agent_list_dir(root: Path, path_text: str, policy: dict) -> dict:
    path = _require_operation_permission(root, path_text, "list", policy)
    if not path.is_dir():
        raise NotADirectoryError(f"Папка не найдена: {path_text}")

    entries = []
    truncated = False
    for child in sorted(path.iterdir(), key=lambda item: item.name.casefold()):
        # Даже если backup-папка когда-либо окажется внутри workspace,
        # агент её не увидит в листинге.
        try:
            if _is_within(child.resolve(), BACKUP_BASE):
                continue
        except OSError:
            pass

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

def _logical_text_encoding(path: Path) -> str:
    return "utf-16" if path.suffix.lower() == ".jsonl" else "utf-8"


def _logical_line_starts(content: str) -> list[int]:
    starts = [0]
    offset = 0
    for line in content.splitlines(keepends=True):
        offset += len(line)
        if offset < len(content):
            starts.append(offset)
    return starts


def _read_logical_text(path: Path) -> str:
    _require_text_suffix(path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл не найден: {path}")
    physical_limit = MAX_AGENT_FILE_BYTES * (2 if path.suffix.lower() == ".jsonl" else 1) + 2
    if path.stat().st_size > physical_limit:
        raise ValueError(f"Файл превышает лимит чтения: {physical_limit} байт.")
    try:
        with path.open("r", encoding=_logical_text_encoding(path), newline="") as stream:
            content = stream.read()
    except UnicodeError as exc:
        raise ValueError(f"Некорректная кодировка {_logical_text_encoding(path)}: {path}") from exc
    if len(content.encode("utf-8")) > MAX_AGENT_FILE_BYTES:
        raise ValueError(f"Logical content превышает лимит: {MAX_AGENT_FILE_BYTES} байт.")
    return content


def _write_logical_text(path: Path, content: str) -> int:
    if not isinstance(content, str):
        raise ValueError("content должен быть строкой.")
    _require_text_suffix(path)
    encoded_bytes = len(content.encode("utf-8"))
    if encoded_bytes > MAX_AGENT_FILE_BYTES:
        raise ValueError(f"Содержимое слишком большое: {encoded_bytes} байт. Лимит: {MAX_AGENT_FILE_BYTES} байт.")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding=_logical_text_encoding(path), newline="") as stream:
            stream.write(content)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return encoded_bytes


def _agent_read_file(root: Path, path_text: str, policy: dict) -> dict:
    path = _require_operation_permission(root, path_text, "read", policy)
    content = _read_logical_text(path)
    return {
        "path": path.relative_to(root).as_posix(),
        "content": content,
        "content_sha256": _sha256_utf8(content),
    }


def _agent_find_text(root: Path, path_text: str, text: str, policy: dict) -> dict:
    if not isinstance(text, str) or not text:
        raise ValueError("text должен быть непустой строкой.")
    path = _require_operation_permission(root, path_text, "read", policy)
    content = _read_logical_text(path)
    line_starts = _logical_line_starts(content)
    matches = []
    count = 0
    offset = 0
    while (found := content.find(text, offset)) != -1:
        count += 1
        if len(matches) < MAX_FIND_TEXT_MATCHES:
            line_index = bisect_right(line_starts, found) - 1
            line_start = line_starts[line_index]
            snippet_start = max(line_start, found - 40)
            snippet = content[snippet_start:found + len(text) + 40]
            matches.append({
                "line": line_index + 1,
                "column": found - line_start + 1,
                "snippet": snippet[:MAX_FIND_TEXT_SNIPPET_CHARS],
            })
        offset = found + 1
    return {
        "path": path.relative_to(root).as_posix(),
        "count": count,
        "matches": matches,
        "truncated": count > len(matches),
        "content_sha256": _sha256_utf8(content),
    }


def _agent_read_file_range(
    root: Path, path_text: str, start_line: int, end_line: int, policy: dict
) -> dict:
    if (type(start_line) is not int or type(end_line) is not int
            or start_line < 1 or end_line < start_line):
        raise ValueError("start_line/end_line должны быть целыми 1-based inclusive границами.")
    if end_line - start_line + 1 > MAX_READ_RANGE_LINES:
        raise ValueError(f"Диапазон превышает {MAX_READ_RANGE_LINES} строк.")
    path = _require_operation_permission(root, path_text, "read", policy)
    content = _read_logical_text(path)
    lines = content.splitlines(keepends=True)
    if end_line > len(lines):
        raise ValueError(f"end_line={end_line} выходит за пределы файла ({len(lines)} строк).")
    selected = "".join(lines[start_line - 1:end_line])
    if len(selected.encode("utf-8")) > MAX_READ_RANGE_BYTES:
        raise ValueError(f"Диапазон превышает {MAX_READ_RANGE_BYTES} байт.")
    return {
        "path": path.relative_to(root).as_posix(),
        "start_line": start_line,
        "end_line": end_line,
        "total_lines": len(lines),
        "content": selected,
        "content_sha256": _sha256_utf8(content),
    }

def _agent_write_file(
    root: Path,
    path_text: str,
    content: str,
    policy: dict,
    backup_session: dict | None,
) -> dict:
    if not isinstance(content, str):
        raise ValueError("content должен быть строкой.")

    encoded_content = content.encode("utf-8")
    if len(encoded_content) > MAX_AGENT_FILE_BYTES:
        raise ValueError(
            f"Содержимое слишком большое: {len(encoded_content)} байт. "
            f"Лимит: {MAX_AGENT_FILE_BYTES} байт."
        )

    path = _require_operation_permission(root, path_text, "write", policy)
    _require_text_suffix(path)
    if path == root:
        raise ValueError("Путь файла не может совпадать с workspace_root.")

    # Снимок исходного файла создаётся ДО первого изменения.
    _backup_before_write(root, path, backup_session)

    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_parent = path.parent.resolve()
    if resolved_parent != root and root not in resolved_parent.parents:
        raise ValueError("Родительская папка выходит за пределы workspace_root.")

    _write_logical_text(path, content)
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes_written": len(encoded_content),
        "content_sha256": _sha256_utf8(_read_logical_text(path)),
    }


class StaleFileStateError(ValueError):
    """The file changed since the model obtained its expected content hash."""


def _agent_precise_edit(
    root: Path,
    name: str,
    path_text: str,
    target_text: str,
    replacement_text: str,
    expected_content_sha256: str,
    policy: dict,
    backup_session: dict | None,
) -> dict:
    if name not in {"replace_text", "insert_before", "insert_after"}:
        raise ValueError(f"Неизвестный precise edit: {name!r}.")
    if not isinstance(target_text, str) or not target_text:
        raise ValueError("old_text/marker должен быть непустой строкой.")
    if not isinstance(replacement_text, str):
        raise ValueError("new_text/content должен быть строкой.")
    if not isinstance(expected_content_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_content_sha256
    ):
        raise ValueError("expected_content_sha256 должен быть lowercase SHA-256 hex.")
    path = _require_operation_permission(root, path_text, "write", policy)
    previous = _read_logical_text(path)
    previous_hash = _sha256_utf8(previous)
    if previous_hash != expected_content_sha256:
        raise StaleFileStateError("STALE_FILE_STATE: logical content SHA-256 не совпадает.")
    index = previous.find(target_text)
    if index < 0:
        raise ValueError("Точный old_text/marker не найден; файл не изменён.")
    if previous.find(target_text, index + 1) >= 0:
        raise ValueError("old_text/marker встречается больше одного раза; файл не изменён.")

    if name == "replace_text":
        start, end = index, index + len(target_text)
        inserted = replacement_text
    elif name == "insert_before":
        start = end = index
        inserted = replacement_text
    else:
        start = end = index + len(target_text)
        inserted = replacement_text
    updated = previous[:start] + inserted + previous[end:]
    if updated == previous:
        raise ValueError("Логическое содержимое не изменилось; mutation не выполнена.")
    if len(updated.encode("utf-8")) > MAX_AGENT_FILE_BYTES:
        raise ValueError(f"Результат превышает лимит {MAX_AGENT_FILE_BYTES} байт.")

    # All checks are complete. Preserve the original before physical mutation.
    _backup_before_write(root, path, backup_session)
    _write_logical_text(path, updated)
    changed_line = bisect_right(_logical_line_starts(previous), start)
    return {
        "path": path.relative_to(root).as_posix(),
        "previous_content_sha256": previous_hash,
        "content_sha256": _sha256_utf8(_read_logical_text(path)),
        "start_line": changed_line,
        "end_line": changed_line + len(re.findall(r"\r\n|\r|\n", inserted)),
        "removed_chars": end - start,
        "added_chars": len(inserted),
        "resulting_snippet": updated[max(0, start - 40):start + min(len(inserted), 80) + 40][:160],
    }

def _agent_delete_file(
    root: Path,
    path_text: str,
    policy: dict,
    backup_session: dict | None,
) -> dict:
    path = _require_operation_permission(root, path_text, "delete", policy)
    _require_text_suffix(path)

    if path == root:
        raise ValueError("Нельзя удалить workspace_root.")
    if path.is_symlink():
        raise ValueError("Удаление symlink запрещено.")
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path_text}")
    if not path.is_file():
        raise ValueError("delete_file удаляет только файлы, не папки.")

    size = path.stat().st_size
    _backup_before_delete(root, path, backup_session)
    path.unlink()

    return {
        "path": path.relative_to(root).as_posix(),
        "deleted": True,
        "bytes": size,
    }



def _truncate_verify_output(text: str) -> tuple[str, bool, int]:
    if not isinstance(text, str):
        text = str(text)
    raw = text.encode("utf-8", errors="replace")
    original_bytes = len(raw)
    if original_bytes <= MAX_VERIFY_OUTPUT_BYTES:
        return text, False, original_bytes
    clipped = raw[:MAX_VERIFY_OUTPUT_BYTES].decode("utf-8", errors="replace")
    return clipped + "\n... <OUTPUT TRUNCATED> ...", True, original_bytes


def _verification_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["GIT_PAGER"] = "cat"
    env["GIT_EXTERNAL_DIFF"] = ""
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


def _run_verify_process(
    args: list[str],
    *,
    cwd: Path,
    timeout: int = VERIFY_TIMEOUT_SECONDS,
) -> dict:
    kwargs = {
        "cwd": str(cwd),
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout,
        "env": _verification_env(),
        "shell": False,
    }
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        completed = subprocess.run(args, **kwargs)
        stdout, stdout_truncated, stdout_bytes = _truncate_verify_output(
            completed.stdout or ""
        )
        stderr, stderr_truncated, stderr_bytes = _truncate_verify_output(
            completed.stderr or ""
        )
        return {
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": stdout_truncated or stderr_truncated,
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": stderr_bytes,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stdout, stdout_truncated, stdout_bytes = _truncate_verify_output(stdout)
        stderr, stderr_truncated, stderr_bytes = _truncate_verify_output(stderr)
        return {
            "ok": False,
            "exit_code": None,
            "stdout": stdout,
            "stderr": (stderr + f"\nTIMEOUT after {timeout} seconds").strip(),
            "truncated": stdout_truncated or stderr_truncated,
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": stderr_bytes,
            "timeout": True,
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "truncated": False,
            "stdout_bytes": 0,
            "stderr_bytes": len(str(exc).encode("utf-8", errors="replace")),
        }


def _require_verify_enabled(policy: dict) -> None:
    if not policy["allow_verify"]:
        raise PermissionError("VERIFY отключён для этого запуска.")
    if not policy["allow_read"]:
        raise PermissionError(
            "VERIFY требует READ: проверка кода и diff не должны обходить запрет чтения."
        )


def _validate_verify_paths(
    root: Path,
    paths: object,
    policy: dict,
    *,
    python_only: bool = False,
    allow_empty: bool = False,
) -> list[tuple[str, Path]]:
    _require_verify_enabled(policy)
    if not isinstance(paths, list):
        raise ValueError("paths должен быть JSON-массивом относительных путей.")
    if not paths and not allow_empty:
        raise ValueError("paths не должен быть пустым.")

    result: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for item in paths:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Каждый элемент paths должен быть непустой строкой.")
        path = _require_operation_permission(root, item, "read", policy)
        if python_only and path.suffix.lower() != ".py":
            raise ValueError(f"python_compile принимает только .py: {item}")
        if not path.is_file():
            raise FileNotFoundError(f"Файл не найден: {item}")
        rel = path.relative_to(root).as_posix()
        if rel not in seen:
            result.append((rel, path))
            seen.add(rel)
    return result


def _agent_python_compile(root: Path, paths: object, policy: dict) -> dict:
    checked = _validate_verify_paths(root, paths, policy, python_only=True)
    payload = [
        {"relative": rel, "absolute": str(path)}
        for rel, path in checked
    ]
    child_code = (
        "import json, py_compile, sys\n"
        "from pathlib import Path\n"
        "items = json.loads(sys.argv[1])\n"
        "out_dir = Path(sys.argv[2])\n"
        "out_dir.mkdir(parents=True, exist_ok=True)\n"
        "for index, item in enumerate(items):\n"
        "    source = item[\"absolute\"]\n"
        "    target = out_dir / f\"verify_{index}.pyc\"\n"
        "    py_compile.compile(source, cfile=str(target), doraise=True)\n"
        "    print(f\"OK: {item['relative']}\")\n"
    )
    with tempfile.TemporaryDirectory(prefix="ultra_verify_") as temp_dir:
        result = _run_verify_process(
            [
                sys.executable,
                "-E",
                "-B",
                "-c",
                child_code,
                json.dumps(payload, ensure_ascii=False),
                temp_dir,
            ],
            cwd=root,
        )
    result["paths"] = [rel for rel, _ in checked]
    result["check"] = "python_compile"
    return result


def _git_path_in_read_scope(root: Path, path_text: str, policy: dict) -> bool:
    text = path_text.strip().strip('"')
    if " -> " in text:
        text = text.rsplit(" -> ", 1)[-1].strip().strip('"')
    try:
        path = _resolve_workspace_path(root, text)
    except Exception:
        return False
    return _is_within(path, policy["_read_root"])


def _agent_git_status(root: Path, policy: dict) -> dict:
    _require_verify_enabled(policy)
    result = _run_verify_process(
        ["git", "-c", "core.quotepath=false", "--no-pager", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
    )
    if result["ok"]:
        filtered = []
        for line in result["stdout"].splitlines():
            path_text = line[3:] if len(line) >= 4 else ""
            if path_text and _git_path_in_read_scope(root, path_text, policy):
                filtered.append(line)
        result["stdout"] = "\n".join(filtered)
    result["check"] = "git_status"
    result["read_scope"] = policy["read_scope"]
    return result


def _agent_git_diff(root: Path, paths: object, policy: dict) -> dict:
    _require_verify_enabled(policy)
    checked = _validate_verify_paths(
        root,
        paths,
        policy,
        python_only=False,
        allow_empty=True,
    )
    if checked:
        pathspecs = [rel for rel, _ in checked]
    else:
        scope = policy["read_scope"]
        if scope == ".":
            pathspecs = ["."]
        else:
            scope_path = _require_operation_permission(root, scope, "read", policy)
            if not scope_path.is_dir():
                raise NotADirectoryError(f"Область чтения не найдена: {scope}")
            pathspecs = [scope_path.relative_to(root).as_posix()]

    result = _run_verify_process(
        [
            "git",
            "-c",
            "core.quotepath=false",
            "--no-pager",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-color",
            "HEAD",
            "--",
            *pathspecs,
        ],
        cwd=root,
    )
    result["paths"] = pathspecs
    result["check"] = "git_diff"
    result["note"] = (
        "git diff HEAD не показывает содержимое обычных untracked-файлов; "
        "их наличие проверяй через git_status."
    )
    return result


def _agent_ui_smoke_test(root: Path, policy: dict) -> dict:
    _require_verify_enabled(policy)
    target = _require_operation_permission(root, "ultra_ui.py", "read", policy)
    if not target.is_file():
        raise FileNotFoundError("ultra_ui.py не найден в workspace.")

    child_code = (
        "import ultra_ui\n"
        "app = None\n"
        "try:\n"
        "    app = ultra_ui.UltraApp()\n"
        "    app.withdraw()\n"
        "    app.update_idletasks()\n"
        "    print(\"OK: UltraApp constructed\")\n"
        "finally:\n"
        "    if app is not None:\n"
        "        app.destroy()\n"
    )
    result = _run_verify_process(
        [sys.executable, "-E", "-B", "-c", child_code],
        cwd=root,
        timeout=UI_SMOKE_TIMEOUT_SECONDS,
    )
    result["check"] = "ui_smoke_test"
    result["target"] = "ultra_ui.UltraApp"
    return result

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


def _guard_p1_normalize_stem(path: Path) -> tuple[str, list[str]]:
    stem = unicodedata.normalize("NFKC", path.stem).casefold().replace("ё", "е")
    stem = re.sub(r"[\s_.\-–—]+", " ", stem).strip()
    stem = re.sub(r"\s+", " ", stem)
    return stem, stem.split()


def _guard_p1_common_prefix_len(left: str, right: str) -> int:
    limit = min(len(left), len(right))
    index = 0
    while index < limit and left[index] == right[index]:
        index += 1
    return index


def _guard_p1_word_ending_variant(
    left_tokens: list[str],
    right_tokens: list[str],
) -> bool:
    if len(left_tokens) != len(right_tokens) or not left_tokens:
        return False

    differences = [
        (left, right)
        for left, right in zip(left_tokens, right_tokens)
        if left != right
    ]
    if len(differences) != 1:
        return False

    left, right = differences[0]
    common = _guard_p1_common_prefix_len(left, right)
    if common < 3:
        return False
    return len(left) - common <= 2 and len(right) - common <= 2


def _guard_p1_without_edge_number(
    tokens: list[str],
    edge: str,
) -> list[str] | None:
    if not tokens:
        return None
    index = 0 if edge == "left" else -1
    token = tokens[index]
    if not re.fullmatch(r"\d{1,2}", token):
        return None
    return tokens[1:] if edge == "left" else tokens[:-1]


def _guard_p1_numeric_edge_variant(
    left_tokens: list[str],
    right_tokens: list[str],
) -> bool:
    for edge in ("left", "right"):
        left_core = _guard_p1_without_edge_number(left_tokens, edge)
        right_core = _guard_p1_without_edge_number(right_tokens, edge)

        if (
            left_core is not None
            and right_core is not None
            and left_core == right_core
            and left_tokens != right_tokens
        ):
            return True

        if left_core is not None and left_core == right_tokens:
            return True
        if right_core is not None and right_core == left_tokens:
            return True

    return False


def _guard_p1_same_leading_number(
    left_tokens: list[str],
    right_tokens: list[str],
) -> bool:
    if not left_tokens or not right_tokens:
        return False
    return bool(
        re.fullmatch(r"\d{1,2}", left_tokens[0])
        and left_tokens[0] == right_tokens[0]
    )


def _guard_p1_explicit_target_in_task(task: str, target_text: str) -> bool:
    task_folded = (
        unicodedata.normalize("NFKC", task)
        .casefold()
        .replace("\\", "/")
    )
    target_folded = (
        unicodedata.normalize("NFKC", target_text)
        .casefold()
        .replace("\\", "/")
    )
    name_folded = (
        unicodedata.normalize("NFKC", Path(target_text).name)
        .casefold()
    )
    return target_folded in task_folded or name_folded in task_folded


def _guard_p1_candidate_score(
    target: Path,
    candidate: Path,
    *,
    candidate_used_in_run: bool,
) -> tuple[int, float, list[str]]:
    target_norm, target_tokens = _guard_p1_normalize_stem(target)
    candidate_norm, candidate_tokens = _guard_p1_normalize_stem(candidate)

    ratio = SequenceMatcher(None, target_norm, candidate_norm).ratio()
    score = 0
    reasons: list[str] = []

    if target.suffix.casefold() == candidate.suffix.casefold():
        score += 10

    if target_norm == candidate_norm:
        score += 80
        reasons.append("нормализованные имена совпадают")

    if _guard_p1_numeric_edge_variant(target_tokens, candidate_tokens):
        score += 60
        reasons.append("отличается числовой префикс/суффикс 1–2 цифры")

    if _guard_p1_word_ending_variant(target_tokens, candidate_tokens):
        score += 60
        reasons.append(
            "одно слово отличается почти только окончанием 1–2 символа"
        )

    if ratio >= 0.97:
        score += 50
        reasons.append(f"очень высокая похожесть имени ({ratio:.2f})")
    elif ratio >= 0.93:
        score += 35
        reasons.append(f"высокая похожесть имени ({ratio:.2f})")
    elif ratio >= 0.88:
        score += 20
        reasons.append(f"заметная похожесть имени ({ratio:.2f})")

    if _guard_p1_same_leading_number(target_tokens, candidate_tokens):
        score += 10
        reasons.append("совпадает ведущий номер документа")

    if candidate_used_in_run:
        score += 30
        reasons.append(
            "похожий существующий файл уже использовался в этом RUN"
        )

    return score, ratio, reasons


def _guard_p1_find_suspicious_create(
    root: Path,
    target_text: str,
    policy: dict,
    task: str,
    used_paths: set[str],
) -> dict | None:
    try:
        target = _require_operation_permission(
            root,
            target_text,
            "write",
            policy,
        )
    except Exception:
        # Реальные permission/path errors обрабатывает штатный executor.
        return None

    if target.exists():
        return None

    # Если пользователь прямо назвал этот новый target в TASK —
    # не мешаем легитимному CREATE.
    if _guard_p1_explicit_target_in_task(task, target_text):
        return None

    parent = target.parent
    if not parent.is_dir():
        return None

    best: dict | None = None
    for candidate in parent.iterdir():
        if not candidate.is_file():
            continue
        if candidate.suffix.casefold() != target.suffix.casefold():
            continue

        relative_candidate = candidate.relative_to(root).as_posix()
        score, ratio, reasons = _guard_p1_candidate_score(
            target,
            candidate,
            candidate_used_in_run=relative_candidate in used_paths,
        )
        if score < GUARD_P1_CREATE_SCORE_THRESHOLD:
            continue

        item = {
            "requested_path": target.relative_to(root).as_posix(),
            "similar_path": relative_candidate,
            "score": score,
            "ratio": round(ratio, 4),
            "reasons": reasons,
        }
        if best is None or item["score"] > best["score"]:
            best = item

    return best


def _guard_p1_resource_token(
    root: Path,
    function_name: str,
    safe_args: dict,
    write_revision: int,
) -> tuple:
    token: list[object] = [write_revision]
    if function_name in {"read_file", "list_dir"}:
        path_text = safe_args.get("path")
        if isinstance(path_text, str):
            try:
                path = _resolve_workspace_path(root, path_text)
                stat = path.stat()
                token.extend([stat.st_mtime_ns, stat.st_size])
            except OSError:
                token.extend([None, None])
    return tuple(token)


def _guard_p1_repeat_key(
    root: Path,
    function_name: str,
    safe_args: dict,
    write_revision: int,
) -> tuple | None:
    if function_name not in GUARD_P1_REPEAT_TOOL_NAMES:
        return None

    args_json = json.dumps(
        safe_args,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (
        function_name,
        args_json,
        _guard_p1_resource_token(
            root,
            function_name,
            safe_args,
            write_revision,
        ),
    )


def _safe_tool_result_summary(
    function_name: str,
    result: object,
) -> str:
    if not isinstance(result, dict):
        return str(result)[:500]

    path = result.get("path")
    if function_name in {"read_file", "read_file_range"}:
        content = result.get("content")
        chars = len(content) if isinstance(content, str) else None
        return f"path={path!r}, chars={chars}"

    if function_name == "find_text":
        return f"path={path!r}, count={result.get('count')!r}"

    if function_name == "list_dir":
        entries = result.get("entries")
        count = len(entries) if isinstance(entries, list) else None
        return f"path={path!r}, entries={count}"

    if function_name in MUTATION_TOOL_NAMES:
        return f"path={path!r}, ok={result.get('ok', True)!r}"

    safe = {
        key: value
        for key, value in result.items()
        if key not in {"content", "stdout", "stderr"}
    }
    return json.dumps(
        safe,
        ensure_ascii=False,
        sort_keys=True,
    )[:500]


def _sha256_utf8(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _candidate_final_fingerprint(candidate: str) -> str:
    """Fingerprint Candidate без разрушения значимого текста/отступов."""

    normalized = unicodedata.normalize("NFC", str(candidate))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    normalized = normalized.strip("\n")
    return _sha256_utf8(normalized)


def _normalize_final_audit_failure_prose(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def _final_audit_failure_signatures(
    *,
    check_type: str,
    reason: str,
    violations: tuple[str, ...] | list[str],
    required_action: str,
) -> tuple[str, str]:
    normalized_check_type = _normalize_final_audit_failure_prose(check_type)
    normalized_reason = _normalize_final_audit_failure_prose(reason)
    normalized_violations = sorted(
        _normalize_final_audit_failure_prose(item) for item in violations
    )
    normalized_required_action = _normalize_final_audit_failure_prose(
        required_action
    )
    exact_payload = {
        "check_type": normalized_check_type,
        "reason": normalized_reason,
        "violations": normalized_violations,
        "required_action": normalized_required_action,
    }
    core_payload = {
        "check_type": normalized_check_type,
        "failure_core": (
            normalized_violations
            if normalized_violations
            else normalized_reason
        ),
    }
    exact_signature = _sha256_utf8(
        json.dumps(
            exact_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    core_signature = _sha256_utf8(
        json.dumps(
            core_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return exact_signature, core_signature


def _record_run_owned_mutation(
    run_owned_state: dict[str, dict[str, str]],
    *,
    function_name: str,
    relative_path: str,
    content: str | None = None,
    content_sha256: str | None = None,
) -> None:
    path = str(relative_path).replace("\\", "/")
    if function_name in TEXT_MUTATION_TOOL_NAMES:
        if content_sha256 is None and isinstance(content, str):
            content_sha256 = _sha256_utf8(content)
        if not isinstance(content_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", content_sha256):
            raise TypeError("Успешная text mutation должна иметь logical content SHA-256.")
        run_owned_state[path] = {
            "state": "present",
            "content_sha256": content_sha256,
        }
        return
    if function_name == "delete_file":
        run_owned_state[path] = {"state": "absent"}
        return
    raise ValueError(f"Неизвестная RUN-owned mutation: {function_name!r}.")


def _bookkeep_successful_mutation(
    *,
    function_name: str,
    result: dict,
    run_owned_state: dict[str, dict[str, str]],
    verification_state: dict,
) -> None:
    if function_name not in MUTATION_TOOL_NAMES:
        raise ValueError(f"Неизвестная mutation: {function_name!r}.")
    changed_path = result.get("path")
    if not isinstance(changed_path, str):
        raise RuntimeError("Успешная mutation не вернула относительный path.")
    _record_run_owned_mutation(
        run_owned_state,
        function_name=function_name,
        relative_path=changed_path,
        content_sha256=result.get("content_sha256"),
    )
    verification_state["write_revision"] += 1
    current_revision = verification_state["write_revision"]
    verification_state["git_status_revision"] = None
    verification_state["git_diff_revision"] = None

    if changed_path.lower().endswith(".py"):
        verification_state["python_write_revision"] = current_revision
        verification_state["python_verified_revision"] = None
        verification_state["python_verified_paths"] = []
        changed_paths = verification_state["changed_python_paths"]
        deleted_paths = verification_state["deleted_python_paths"]
        if function_name in TEXT_MUTATION_TOOL_NAMES:
            if changed_path not in changed_paths:
                changed_paths.append(changed_path)
            if changed_path in deleted_paths:
                deleted_paths.remove(changed_path)
        else:
            if changed_path in changed_paths:
                changed_paths.remove(changed_path)
            if changed_path not in deleted_paths:
                deleted_paths.append(changed_path)

    if changed_path in {"server.py", "ultra_ui.py"}:
        verification_state["ui_smoke_required"] = True
        verification_state["ui_smoke_write_revision"] = current_revision
        verification_state["ui_smoke_verified_revision"] = None


def _run_owned_state_fingerprint(
    run_owned_state: dict[str, dict[str, str]],
) -> str:
    canonical = [
        {
            "path": path,
            "state": record["state"],
            **(
                {"content_sha256": record["content_sha256"]}
                if record["state"] == "present"
                else {}
            ),
        }
        for path, record in sorted(run_owned_state.items())
    ]
    return _sha256_utf8(
        json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def _verify_run_owned_filesystem(
    root: Path, run_owned_state: dict[str, dict[str, str]]
) -> tuple[list[dict], list[str]]:
    """Check current-RUN writes/deletes against physical files, without Executor READ."""
    evidence: list[dict] = []
    mismatches: list[str] = []
    for relative_path, expected in sorted(run_owned_state.items()):
        expected_state = expected.get("state")
        expected_hash = expected.get("content_sha256") if expected_state == "present" else None
        item = {
            "path": relative_path,
            "expected_state": expected_state,
            "actual_state": "unavailable",
            "expected_content_sha256": expected_hash,
            "actual_content_sha256": None,
            "match": False,
        }
        try:
            lexical_path = root / relative_path
            path = _resolve_workspace_path(root, relative_path)
            _require_text_suffix(path)
            if lexical_path.is_symlink():
                item["actual_state"] = "symlink"
            elif not path.exists():
                item["actual_state"] = "absent"
            elif not path.is_file():
                item["actual_state"] = "not_regular_file"
            else:
                item["actual_state"] = "present"
                item["actual_content_sha256"] = _sha256_utf8(_read_logical_text(path))
            item["match"] = item["actual_state"] == expected_state and (
                expected_state == "absent"
                or item["actual_content_sha256"] == expected_hash
            )
        except Exception as exc:
            item["reason"] = type(exc).__name__
        if not item["match"]:
            mismatches.append(f"run_owned_filesystem_mismatch:{relative_path}")
        evidence.append(item)
    return evidence, mismatches



def _execute_agent_function(
    root: Path,
    function_call: object,
    policy: dict,
    backup_session: dict | None,
) -> dict:
    if not isinstance(function_call, dict):
        raise ValueError("GigaChat вернул невалидный function_call.")

    name = function_call.get("name")
    allowed_names = {
        *READ_TOOL_NAMES,
        *MUTATION_TOOL_NAMES,
        *VERIFICATION_TOOL_NAMES,
    }
    if name not in allowed_names:
        raise ValueError(f"GigaChat запросил неизвестную функцию: {name!r}.")

    arguments = _parse_agent_arguments(name, function_call.get("arguments"))
    expected_keys = {
        "list_dir": {"path"},
        "read_file": {"path"},
        "find_text": {"path", "text"},
        "read_file_range": {"path", "start_line", "end_line"},
        "write_file": {"path", "content"},
        "replace_text": {"path", "old_text", "new_text", "expected_content_sha256"},
        "insert_before": {"path", "marker", "content", "expected_content_sha256"},
        "insert_after": {"path", "marker", "content", "expected_content_sha256"},
        "delete_file": {"path"},
        "python_compile": {"paths"},
        "git_status": set(),
        "git_diff": {"paths"},
        "ui_smoke_test": set(),
    }[name]
    if set(arguments) != expected_keys:
        raise ValueError(
            f"Невалидные аргументы {name}: ожидаются {sorted(expected_keys)}."
        )

    if name == "list_dir":
        return _agent_list_dir(root, arguments["path"], policy)
    if name == "read_file":
        return _agent_read_file(root, arguments["path"], policy)
    if name == "find_text":
        return _agent_find_text(root, arguments["path"], arguments["text"], policy)
    if name == "read_file_range":
        return _agent_read_file_range(
            root, arguments["path"], arguments["start_line"], arguments["end_line"], policy
        )
    if name == "delete_file":
        return _agent_delete_file(
            root,
            arguments["path"],
            policy,
            backup_session,
        )
    if name == "write_file":
        return _agent_write_file(
            root,
            arguments["path"],
            arguments["content"],
            policy,
            backup_session,
        )
    if name in {"replace_text", "insert_before", "insert_after"}:
        target_key = "old_text" if name == "replace_text" else "marker"
        replacement_key = "new_text" if name == "replace_text" else "content"
        return _agent_precise_edit(
            root, name, arguments["path"], arguments[target_key],
            arguments[replacement_key], arguments["expected_content_sha256"],
            policy, backup_session,
        )
    if name == "python_compile":
        return _agent_python_compile(root, arguments["paths"], policy)
    if name == "git_status":
        return _agent_git_status(root, policy)
    if name == "git_diff":
        return _agent_git_diff(root, arguments["paths"], policy)
    return _agent_ui_smoke_test(root, policy)


def _verification_missing_requirements(state: dict) -> list[dict]:
    """Вернуть физически недостающие проверки для финального SUCCESS."""
    if state.get("write_revision", 0) <= 0:
        return []

    missing: list[dict] = []
    changed_python_paths = sorted(set(state.get("changed_python_paths") or []))
    verified_python_paths = set(state.get("python_verified_paths") or [])

    if changed_python_paths:
        python_revision_ok = (
            state.get("python_write_revision") is not None
            and state.get("python_verified_revision")
            == state.get("python_write_revision")
        )
        paths_ok = set(changed_python_paths).issubset(verified_python_paths)
        if not python_revision_ok or not paths_ok:
            missing.append(
                {
                    "tool": "python_compile",
                    "paths": changed_python_paths,
                    "reason": (
                        "Все изменённые существующие .py должны быть успешно "
                        "скомпилированы после последней Python-записи."
                    ),
                }
            )

    if state.get("ui_smoke_required"):
        if (
            state.get("ui_smoke_write_revision") is None
            or state.get("ui_smoke_verified_revision")
            != state.get("ui_smoke_write_revision")
        ):
            missing.append(
                {
                    "tool": "ui_smoke_test",
                    "reason": (
                        "После последнего изменения server.py/ultra_ui.py "
                        "обязателен реальный UltraApp smoke-test."
                    ),
                }
            )

    return missing


def _verification_missing_lines(missing: list[dict]) -> str:
    lines = []
    for item in missing:
        tool = item["tool"]
        paths = item.get("paths")
        if paths is not None:
            lines.append(f"- {tool}(paths={paths}) — {item['reason']}")
        else:
            lines.append(f"- {tool} — {item['reason']}")
    return "\n".join(lines)


class FinalAuditEvidenceError(RuntimeError):
    """Server could not collect mutation evidence safely enough to audit."""


class FinalAuditSemanticError(RuntimeError):
    """A valid verifier response rejected the candidate final answer."""


def _clip_final_audit_text(text: str, limit: int) -> tuple[str, bool, int]:
    """Bound one evidence field without ever claiming that it is complete."""
    raw = text.encode("utf-8", errors="replace")
    original_bytes = len(raw)
    if original_bytes <= limit:
        return text, False, original_bytes
    marker = b"\n... <FINAL AUDIT EVIDENCE TRUNCATED> ..."
    kept = max(limit - len(marker), 0)
    clipped = raw[:kept].decode("utf-8", errors="replace")
    return clipped + marker.decode("ascii"), True, original_bytes


def _collect_final_audit_evidence(
    *,
    root: Path,
    candidate_final: str,
    policy: dict,
    run_id: str,
    api_request_count: int,
    tool_call_count: int,
    verification_state: dict,
    backup_session: dict | None,
    run_owned_state: dict[str, dict[str, str]] | None = None,
) -> tuple[str, dict]:
    """Build a bounded FINAL context only from server-observed facts."""
    mutation_manifest = (
        dict(backup_session.get("manifest") or {})
        if isinstance(backup_session, dict)
        else {}
    )
    mutation_facts = {
        "changed_files": sorted(set(mutation_manifest.get("changed_files") or [])),
        "new_files": sorted(set(mutation_manifest.get("new_files") or [])),
        "deleted_files": sorted(set(mutation_manifest.get("deleted_files") or [])),
    }
    is_mutating_run = verification_state.get("write_revision", 0) > 0
    incomplete_reasons: list[str] = []
    mutation_evidence_incomplete_reasons: list[str] = []
    critical_reasons: list[str] = []
    any_truncated = False
    run_owned_filesystem_evidence, filesystem_mismatches = (
        _verify_run_owned_filesystem(root, run_owned_state or {})
    )
    incomplete_reasons.extend(filesystem_mismatches)
    critical_reasons.extend(filesystem_mismatches)

    candidate_text, candidate_truncated, candidate_bytes = (
        _clip_final_audit_text(candidate_final, MAX_VERIFY_OUTPUT_BYTES)
    )
    if candidate_truncated:
        any_truncated = True
        incomplete_reasons.append("candidate_final_response_truncated")
        critical_reasons.append("candidate_final_response_truncated")

    if policy.get("allow_read"):
        # Final Audit is mandatory even when Executor-facing VERIFY is off.
        # These are server-side, read-only observations; READ scope still
        # remains authoritative and is enforced by the existing primitives.
        audit_policy = dict(policy)
        audit_policy["allow_verify"] = True
        try:
            status_result = _agent_git_status(root, audit_policy)
            fresh_status = {"available": bool(status_result.get("ok")), **status_result}
        except Exception as exc:
            fresh_status = {"available": False, "reason": type(exc).__name__}
        try:
            diff_result = _agent_git_diff(root, [], audit_policy)
            fresh_diff = {"available": bool(diff_result.get("ok")), **diff_result}
        except Exception as exc:
            fresh_diff = {"available": False, "reason": type(exc).__name__}
        for label, evidence in (
            ("fresh_git_status", fresh_status),
            ("fresh_git_diff", fresh_diff),
        ):
            if not evidence.get("ok"):
                evidence.setdefault("reason", f"{label}_unavailable")
            if evidence.get("truncated"):
                evidence.setdefault("reason", f"{label}_truncated")
    else:
        unavailable = {
            "available": False,
            "complete": False,
            "truncated": False,
            "reason": "READ is disabled; server did not inspect workspace state.",
        }
        fresh_status = dict(unavailable)
        fresh_diff = dict(unavailable)

    new_file_evidence = []
    remaining_new_file_bytes = MAX_FINAL_AUDIT_NEW_FILE_BYTES
    for relative_path in mutation_facts["new_files"]:
        item = {
            "path": relative_path,
            "available": False,
            "complete": False,
            "truncated": False,
        }
        try:
            resolved = _resolve_workspace_path(root, relative_path)
            if not resolved.exists():
                item.update(
                    {
                        "state": "absent_after_run",
                        "complete": True,
                        "reason": "File was created during the run but is now absent.",
                    }
                )
            else:
                file_result = _agent_read_file(root, relative_path, policy)
                content = file_result["content"]
                clipped, truncated, original_bytes = _clip_final_audit_text(
                    content,
                    remaining_new_file_bytes,
                )
                consumed = len(clipped.encode("utf-8", errors="replace"))
                remaining_new_file_bytes = max(
                    remaining_new_file_bytes - consumed,
                    0,
                )
                item.update(
                    {
                        "available": True,
                        "complete": not truncated,
                        "truncated": truncated,
                        "original_bytes": original_bytes,
                        "content": clipped,
                    }
                )
                if truncated:
                    any_truncated = True
                    reason = f"new_file_content_truncated:{relative_path}"
                    incomplete_reasons.append(reason)
                    mutation_evidence_incomplete_reasons.append(reason)
        except Exception as exc:
            item["reason"] = f"{type(exc).__name__}: {exc}"
            reason = f"new_file_content_unavailable:{relative_path}"
            incomplete_reasons.append(reason)
            mutation_evidence_incomplete_reasons.append(reason)
        new_file_evidence.append(item)

    if is_mutating_run:
        critical_reasons.extend(mutation_evidence_incomplete_reasons)
    critical_reasons = list(dict.fromkeys(critical_reasons))
    completeness = {
        "complete": not incomplete_reasons,
        "truncated": any_truncated,
        "reasons": incomplete_reasons,
        "critical_for_success": bool(critical_reasons),
        "critical_reasons": critical_reasons,
        "critical_for_mutating_run": bool(
            is_mutating_run and (
                mutation_evidence_incomplete_reasons or filesystem_mismatches
            )
        ),
    }
    evidence = {
        "check_type": "FINAL",
        "evidence_semantics": {
            "raw_task": (
                "Source of truth for requested work; supplied separately as "
                "run_verifier_check.raw_task."
            ),
            "candidate_final_response": (
                "Executor claim about completion; not an authoritative fact."
            ),
            "mutation_facts": (
                "Server-observed mutations performed during the current RUN."
            ),
            "run_owned_filesystem_evidence": (
                "Server integrity check of the current RUN's expected file states "
                "and logical content hashes; no file content is included."
            ),
            "fresh_git_state": (
                "Workspace-wide observation that may include pre-existing or "
                "external changes."
            ),
            "git_attribution_rule": (
                "Do not attribute a Git change to the current RUN unless it is "
                "corroborated by mutation_facts."
            ),
        },
        "candidate_final_response": {
            "content": candidate_text,
            "complete": not candidate_truncated,
            "truncated": candidate_truncated,
            "original_bytes": candidate_bytes,
        },
        "run_facts": {
            "run_id": run_id,
            "api_request_count": api_request_count,
            "tool_call_count": tool_call_count,
            "write_revision": verification_state.get("write_revision", 0),
            "changed_python_paths": list(
                verification_state.get("changed_python_paths") or []
            ),
            "deleted_python_paths": list(
                verification_state.get("deleted_python_paths") or []
            ),
        },
        "permission_policy": _policy_summary(policy),
        "deterministic_verification": {
            "verification_state": dict(verification_state),
            "missing_requirements": _verification_missing_requirements(
                verification_state
            ),
        },
        "mutation_facts": mutation_facts,
        "run_owned_filesystem_evidence": run_owned_filesystem_evidence,
        "fresh_git_status": fresh_status,
        "fresh_git_diff": fresh_diff,
        "new_file_evidence": new_file_evidence,
        "evidence_completeness": completeness,
    }
    completeness["context_limit_bytes"] = MAX_FINAL_AUDIT_CONTEXT_BYTES
    context = ""
    context_bytes = -1
    for _attempt in range(4):
        context = json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2)
        measured_bytes = len(context.encode("utf-8", errors="replace"))
        if measured_bytes == context_bytes:
            break
        context_bytes = measured_bytes
        completeness["context_bytes"] = context_bytes
    if context_bytes > MAX_FINAL_AUDIT_CONTEXT_BYTES:
        completeness["complete"] = False
        size_reason = "verification_context_size_limit_exceeded"
        if size_reason not in completeness["reasons"]:
            completeness["reasons"].append(size_reason)
        if size_reason not in completeness["critical_reasons"]:
            completeness["critical_reasons"].append(size_reason)
        completeness["critical_for_success"] = True
        for _attempt in range(4):
            context = json.dumps(
                evidence, ensure_ascii=False, sort_keys=True, indent=2
            )
            measured_bytes = len(context.encode("utf-8", errors="replace"))
            if measured_bytes == completeness["context_bytes"]:
                break
            completeness["context_bytes"] = measured_bytes

    return context, completeness


async def _request_audit_diagnostic(
    client, headers: dict, run_model: str, messages: list[dict],
    rejected_candidate: str, question: str,
) -> str:
    """One bounded, tool-free call on an isolated copy of Executor context."""
    fork = copy.deepcopy(messages)
    fork.append({"role": "assistant", "content": rejected_candidate})
    fork.append({"role": "user", "content": question})
    body = {
        "model": run_model,
        "messages": fork,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_AUDIT_DIAGNOSTIC_TOKENS,
        "stream": False,
    }
    response = await asyncio.wait_for(
        client.post(CHAT_URL, headers=headers, json=body),
        timeout=AUDIT_DIAGNOSTIC_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    try:
        answer = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Malformed diagnostic response") from exc
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Empty diagnostic response")
    return answer.strip()[:600]


async def run_agent_task(
    task: str,
    workspace_root: str,
    *,
    on_event=None,
    permissions: dict | None = None,
    chat_id: str | None = None,
    model_id: str | None = None,
    verifier_model_id: str = DEFAULT_VERIFIER_MODEL_ID,
) -> str:
    """Запустить автономный GigaChat file-agent с серверными ограничениями."""
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task должен быть непустой строкой.")

    selected_model_id = model_id or MAIN_CHAT_MODEL_ID
    selected_model = get_model_spec(selected_model_id)
    if selected_model.provider != "gigachat":
        raise RuntimeError(
            "MAIN CHAT Provider пока не поддерживается: "
            f"{selected_model.provider}"
        )
    run_model = selected_model.provider_model_id

    run_id = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    start_time = time.time()
    api_request_count = 0
    tool_call_count = 0
    policy = _normalize_permissions(permissions)

    # Пока workspace_id ещё не загружен, ошибки пишутся в системный fallback.
    # После загрузки Workspace путь переключается на его собственный namespace.
    runtime_log_path = (
        Path(os.getenv("LOCALAPPDATA") or Path.home())
        / "GigaChatUltra"
        / "system_logs"
        / f"{run_id}.jsonl"
    ).resolve()
    workspace_backup_base = BACKUP_BASE
    audit_recorder: AuditThreadRecorder | None = None

    def _emit(event_type: str, payload: dict):
        event = {
            "event": event_type,
            "run_id": run_id,
            "timestamp": time.time(),
            **payload,
        }
        if audit_recorder is not None:
            try:
                audit_recorder.observe(event)
            except Exception as exc:
                event["audit_storage_error"] = type(exc).__name__
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

        runtime_log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with runtime_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _context_message(
        event_id: str,
        variables: dict | None = None,
    ) -> str:
        return resolve_server_context_message(
            event_id,
            variables,
            "ultra",
            on_warning=lambda warning: _emit(
                "server_context_message_warning", warning
            ),
        )

    root = _validate_workspace_root(workspace_root)
    policy = _prepare_policy_for_workspace(root, policy)

    # STEP 1 CONTEXT STORAGE:
    # создаём или подхватываем переносимый `.ultra/` данного Workspace.
    # Существующий workspace_id никогда не пересоздаётся автоматически.
    try:
        workspace_info = ensure_workspace_storage(root)
        project_context = load_project_context(root)
    except Exception as exc:
        _emit(
            "run_failed",
            {
                "reason": "workspace_context_load_error",
                "api_requests": api_request_count,
                "tool_calls": tool_call_count,
                "duration": time.time() - start_time,
                "error": str(exc),
                "trace_path": str(runtime_log_path),
            },
        )
        raise RuntimeError(
            "Не удалось создать или загрузить переносимый контекст Workspace."
        ) from exc

    try:
        audit_recorder = AuditThreadRecorder(
            root, workspace_info["workspace_id"], chat_id, run_id
        )
    except Exception as exc:
        # Audit observability is not allowed to veto the Executor RUN.
        audit_recorder = None
        _emit("audit_storage_error", {"error_type": type(exc).__name__})

    try:
        runtime_paths = ensure_workspace_runtime_dirs(
            workspace_info["workspace_id"]
        )
        workspace_backup_base = Path(
            runtime_paths["backup_dir"]
        ).resolve()
        runtime_log_dir = Path(runtime_paths["log_dir"]).resolve()

        # Бэкапы/логи не должны лежать внутри Workspace: иначе снимок может
        # начать резервировать сам себя и потеряется смысл внешней защиты.
        for label, path in (
            ("backup", workspace_backup_base),
            ("log", runtime_log_dir),
        ):
            if path == root or root in path.parents:
                raise ValueError(
                    f"{label} directory не должна находиться внутри Workspace."
                )

        runtime_log_path = runtime_log_dir / f"{run_id}.jsonl"
    except Exception as exc:
        _emit(
            "run_failed",
            {
                "reason": "workspace_runtime_settings_error",
                "api_requests": api_request_count,
                "tool_calls": tool_call_count,
                "duration": time.time() - start_time,
                "error": str(exc),
                "trace_path": str(runtime_log_path),
            },
        )
        raise RuntimeError(
            "Не удалось подготовить локальные пути backup/log для Workspace."
        ) from exc

    active_chat_messages = []
    if chat_id:
        try:
            working_history = load_chat_working_messages(root, chat_id)
        except Exception as exc:
            _emit(
                "run_failed",
                {
                    "reason": "chat_context_load_error",
                    "api_requests": api_request_count,
                    "tool_calls": tool_call_count,
                    "duration": time.time() - start_time,
                    "chat_id": chat_id,
                    "error": str(exc),
                    "trace_path": str(runtime_log_path),
                },
            )
            raise RuntimeError(
                "Не удалось загрузить историю активного чата."
            ) from exc

        raw_message_count = 0
        compressed_message_count = 0
        for item in working_history:
            role = item.get("role")
            content = item.get("content")
            if (
                role in {"user", "assistant"}
                and isinstance(content, str)
                and content.strip()
            ):
                active_chat_messages.append(
                    {"role": role, "content": content}
                )
                if item.get("context_representation") == "summary":
                    compressed_message_count += 1
                else:
                    raw_message_count += 1

        # UI сохраняет текущее пользовательское сообщение ДО запуска API.
        # Для прямых вызовов run_agent_task без предварительного сохранения
        # гарантируем, что текущая задача всё равно попадёт в запрос ровно один раз.
        if not (
            active_chat_messages
            and active_chat_messages[-1]["role"] == "user"
            and active_chat_messages[-1]["content"] == task
        ):
            active_chat_messages.append({"role": "user", "content": task})
            raw_message_count += 1

    else:
        active_chat_messages = [{"role": "user", "content": task}]

    _emit(
        "run_started",
        {
            "task_preview": task[:200],
            "permissions": _policy_summary(policy),
            "workspace_id": workspace_info["workspace_id"],
            "chat_id": chat_id,
            "model_id": selected_model.model_id,
            "model_display_name": selected_model.display_name,
            "provider": selected_model.provider,
            "provider_model_id": selected_model.provider_model_id,
        },
    )
    if chat_id:
        _emit(
            "chat_context_loaded",
            {
                "chat_id": chat_id,
                "messages": len(active_chat_messages),
                "raw_messages": raw_message_count,
                "compressed_messages": compressed_message_count,
                "chars": sum(
                    len(item.get("content") or "")
                    for item in active_chat_messages
                ),
            },
        )
    _emit(
        "workspace_context_loaded",
        {
            "workspace_id": workspace_info["workspace_id"],
            "storage_created": workspace_info["storage_created"],
            "workspace_created": workspace_info["workspace_created"],
            "project_context_created": workspace_info[
                "project_context_created"
            ],
            "project_context_chars": len(project_context),
        },
    )

    # GLOBAL_ULTRA_CONTEXT_V1
    # Глобальный контекст Ultra — локальный app-level контекст агента,
    # общий для всех Workspace. Он хранится вне Workspace и поэтому
    # недоступен обычным file tools Ultra.
    app_dir = Path(__file__).resolve().parent
    try:
        global_agent_context = load_agent_global_context("ultra")
    except Exception as exc:
        _emit(
            "run_failed",
            {
                "reason": "global_agent_context_load_error",
                "api_requests": api_request_count,
                "tool_calls": tool_call_count,
                "duration": time.time() - start_time,
                "error": str(exc),
                "trace_path": str(runtime_log_path),
            },
        )
        raise RuntimeError(
            "Не удалось загрузить ГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA. "
            "Открой в UI «Глобальный контекст Ultra» и сохрани непустой текст."
        ) from exc

    _emit(
        "global_agent_context_loaded",
        {
            "agent_id": "ultra",
            "chars": len(global_agent_context),
        },
    )

    # Бэкап выполняется синхронно ДО обращения к модели.
    backup_session = None
    if policy["auto_backup"]:
        planned_backup_path = workspace_backup_base / run_id
        _emit("backup_started", {"backup_path": str(planned_backup_path)})
        try:
            backup_session = _create_backup_session(
                app_dir,
                root,
                run_id,
                task,
                policy,
                backup_base=workspace_backup_base,
                workspace_id=workspace_info["workspace_id"],
                chat_id=chat_id,
            )
        except Exception as exc:
            _emit("run_failed", {
                "reason": "backup_failed",
                "api_requests": api_request_count,
                "tool_calls": tool_call_count,
                "duration": time.time() - start_time,
                "error": str(exc),
                "trace_path": str(runtime_log_path),
            })
            raise RuntimeError(
                "Не удалось создать обязательный backup. "
                "Запуск Ultra отменён до обращения к модели."
            ) from exc

        _emit("backup_finished", {
            "backup_path": str(backup_session["backup_dir"]),
            "core_files": len(backup_session["manifest"]["core_files"]),
        })

    token = await get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    permission_text = (
        "\n\nСЕРВЕРНЫЕ РАЗРЕШЕНИЯ ЭТОГО ЗАПУСКА\n"
        f"Чтение: {'РАЗРЕШЕНО' if policy['allow_read'] else 'ЗАПРЕЩЕНО'}\n"
        f"Область чтения: {policy['read_scope']}\n"
        f"Запись: {'РАЗРЕШЕНА' if policy['allow_write'] else 'ЗАПРЕЩЕНА'}\n"
        f"Область записи: {policy['write_scope']}\n"
        f"Удаление: {'РАЗРЕШЕНО' if policy['allow_delete'] else 'ЗАПРЕЩЕНО'}\n"
        f"Область удаления: {policy['delete_scope']}\n"
        f"VERIFY: {'РАЗРЕШЁН' if policy['allow_verify'] else 'ЗАПРЕЩЁН'}\n"
        f"GUARD P1: {'ВКЛЮЧЁН' if policy['allow_guard_p1'] else 'ВЫКЛЮЧЕН'}\n"
        f"Лимит вызовов инструментов: {policy['tool_limit']}\n"
        "Планируй действия так, чтобы уложиться в этот лимит. "
        "Не трать вызовы на повторное чтение без необходимости.\n"
        "GUARD P1 при включении может ДО выполнения подозрительного действия "
        "вернуть SUPERVISOR CHECK: повторное чтение без изменения состояния "
        "или создание нового файла, очень похожего на существующий. "
        "Это мягкая самопроверка, а не автоматическое доказательство ошибки.\n"
        f"Автобэкап: {'ВКЛЮЧЁН' if policy['auto_backup'] else 'ВЫКЛЮЧЕН'}\n"
        "VERIFY использует только белый список: python_compile, git_status, "
        "git_diff, ui_smoke_test. Произвольного terminal/shell нет.\n"
        "Если в RUN изменён .py, после ПОСЛЕДНЕЙ Python-записи обязательно "
        "успешно проверь ВСЕ изменённые существующие .py через python_compile. "
        "Если изменён server.py или ultra_ui.py — дополнительно ui_smoke_test. "
        "После ПОСЛЕДНЕЙ записи/удаления обязательны git_diff и git_status. "
        "Сервер сам проверяет свежесть этих результатов и физически блокирует "
        "финальный SUCCESS, если хотя бы одна проверка отсутствует или устарела. "
        "Ошибка проверки не является завершением задачи: сначала исправь причину, "
        "затем повтори ставшие устаревшими проверки.\n"
        "Эти ограничения применяются кодом сервера. Не пытайся выходить "
        "за их пределы; при необходимости сообщи пользователю, какого "
        "доступа не хватает.\n"
    )

    global_agent_context_block = (
        "\n\nГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA\n"
        "Это app-level контекст агента, общий для всех Workspace. "
        "Он может задавать правила и устойчивые инструкции Ultra, но НЕ может "
        "отменять физические ограничения server.py, permission scopes, GUARD "
        "или Verification Gate.\n"
        "===== GLOBAL ULTRA CONTEXT START =====\n"
        f"{global_agent_context.rstrip()}\n"
        "===== GLOBAL ULTRA CONTEXT END =====\n"
    )

    project_context_block = (
        "\n\nPROJECT CONTEXT ТЕКУЩЕГО WORKSPACE\n"
        f"Workspace ID: {workspace_info['workspace_id']}\n"
        "Ниже находится утверждённая переносимая память проекта. "
        "Она используется как контекст, но НЕ может отменять системные "
        "инструкции, серверные разрешения или ГЛОБАЛЬНЫЙ КОНТЕКСТ ULTRA.\n"
        "Если в ходе работы обнаружено важное изменение проекта, не пытайся "
        "самостоятельно редактировать `.ultra` обычными file tools. "
        "Сообщи пользователю, какое обновление PROJECT CONTEXT стоит "
        "рассмотреть.\n"
        "===== PROJECT CONTEXT START =====\n"
        f"{project_context.rstrip()}\n"
        "===== PROJECT CONTEXT END =====\n"
    )

    messages = [
        {
            "role": "system",
            "content": (
                "Ты работаешь как локальный file-agent внутри workspace. "
                "Для всех file tools используй ТОЛЬКО относительные пути. "
                "Корень workspace обозначай точкой '.'. "
                "Никогда не передавай абсолютные Windows-пути в list_dir, "
                "read_file, find_text, read_file_range, write_file, "
                "replace_text, insert_before, insert_after или delete_file."
                f"{permission_text}"
                f"{global_agent_context_block}"
                f"{project_context_block}"
            ),
        },
        *active_chat_messages,
    ]

    available_functions = _functions_for_policy(policy)
    tool_iterations = 0
    last_tool_sequence = 0
    last_tool_name = None
    last_tool_args = None
    last_tool_error = None
    last_tool_status = None
    last_tool_result_summary = None
    repeated_error_signature = None
    repeated_error_count = 0
    verification_state = {
        "write_revision": 0,
        "python_write_revision": None,
        "python_verified_revision": None,
        "python_verified_paths": [],
        "git_status_revision": None,
        "git_diff_revision": None,
        "ui_smoke_required": False,
        "ui_smoke_write_revision": None,
        "ui_smoke_verified_revision": None,
        "changed_python_paths": [],
        "deleted_python_paths": [],
    }
    last_verification_gate_signature = None
    verification_gate_repeat_count = 0
    final_audit_retry_state = {
        "correction_limit": FINAL_AUDIT_CORRECTION_LIMIT,
        "correction_count": 0,
        "final_audit_attempt_count": 0,
        "semantic_fail_count": 0,
        "failure_history": [],
        "run_owned_state": {},
    }

    guard_p1_state = {
        "used_paths": set(),
        "last_repeat_success_key": None,
        "repeat_success_count": 0,
        "repeat_interventions": {},
        "create_challenges": set(),
        "interventions": 0,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        while True:
            api_request_count += 1
            _emit("api_request", {"api_request_number": api_request_count})

            body = {
                "model": run_model,
                "messages": messages,
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "stream": False,
            }
            if available_functions:
                body["functions"] = available_functions
                body["function_call"] = "auto"

            request_start = time.time()
            response = await client.post(CHAT_URL, headers=headers, json=body)
            request_duration = time.time() - request_start
            response.raise_for_status()
            data = response.json()

            try:
                choice = data["choices"][0]
                message = choice["message"]
                finish_reason = choice.get("finish_reason")
            except (KeyError, IndexError, TypeError) as exc:
                _emit("api_response", {
                    "api_request_number": api_request_count,
                    "http_status": response.status_code,
                    "duration": request_duration,
                    "error": "Malformed response",
                })
                _emit("run_failed", {
                    "reason": "malformed_response",
                    "api_requests": api_request_count,
                    "tool_calls": tool_call_count,
                    "duration": time.time() - start_time,
                })
                raise RuntimeError(f"Неожиданный ответ GigaChat: {data}") from exc

            _emit("api_response", {
                "api_request_number": api_request_count,
                "http_status": response.status_code,
                "finish_reason": finish_reason,
                "duration": request_duration,
            })

            if finish_reason == "function_call":
                if tool_iterations >= policy["tool_limit"]:
                    _emit("run_failed", {
                        "reason": "tool_limit",
                        "api_requests": api_request_count,
                        "tool_calls": tool_call_count,
                        "duration": time.time() - start_time,
                        "last_function": last_tool_name,
                        "last_arguments": last_tool_args,
                        "last_error": last_tool_error,
                        "trace_path": str(runtime_log_path),
                    })
                    raise RuntimeError(
                        f"TOOL LIMIT REACHED\n"
                        f"Run ID: {run_id}\n"
                        f"API requests: {api_request_count}\n"
                        f"Tool calls: {tool_call_count}\n"
                        f"Tool limit: {policy['tool_limit']}\n"
                        f"Last function: {last_tool_name}\n"
                        f"Last arguments: {last_tool_args}\n"
                        f"Last status: {last_tool_status}\n"
                        f"Last result/error: {last_tool_result_summary}\n"
                        f"Trace: {runtime_log_path}"
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

                function_name = (
                    function_call.get("name")
                    if isinstance(function_call, dict)
                    else "<invalid>"
                )
                raw_args = (
                    function_call.get("arguments", {})
                    if isinstance(function_call, dict)
                    else {}
                )
                if isinstance(raw_args, dict):
                    safe_args = dict(raw_args)
                else:
                    safe_args = {"raw_arguments": str(raw_args)}
                for field in ("content", "new_text", "old_text", "marker", "text"):
                    if field in safe_args:
                        safe_args[field] = f"<{len(str(safe_args[field]))} chars>"

                # GUARD P1 — supervisor BEFORE actual tool execution.
                # Interventions do not consume tool budget because the
                # requested tool is not executed. They are separately capped.
                if policy.get("allow_guard_p1"):
                    guard_payload = None

                    repeat_key = _guard_p1_repeat_key(
                        root,
                        function_name,
                        safe_args,
                        verification_state["write_revision"],
                    )
                    if (
                        repeat_key is not None
                        and repeat_key
                        == guard_p1_state["last_repeat_success_key"]
                        and guard_p1_state["repeat_success_count"]
                        >= GUARD_P1_REPEAT_AFTER_SUCCESSES
                    ):
                        repeat_hits = guard_p1_state[
                            "repeat_interventions"
                        ].get(repeat_key, 0)

                        if (
                            repeat_hits
                            < GUARD_P1_REPEAT_MAX_INTERVENTIONS
                        ):
                            repeat_hits += 1
                            guard_p1_state["repeat_interventions"][
                                repeat_key
                            ] = repeat_hits
                            guard_payload = {
                                "kind": "repeated_tool",
                                "function": function_name,
                                "arguments": safe_args,
                                "repeat_successes": guard_p1_state[
                                    "repeat_success_count"
                                ],
                                "intervention": repeat_hits,
                            }
                        else:
                            _emit(
                                "guard_blocked",
                                {
                                    "guard": "P1",
                                    "kind": "repeated_tool",
                                    "function": function_name,
                                    "arguments": safe_args,
                                    "trace_path": str(runtime_log_path),
                                },
                            )
                            _emit(
                                "run_failed",
                                {
                                    "reason": "guard_p1_loop",
                                    "api_requests": api_request_count,
                                    "tool_calls": tool_call_count,
                                    "duration": time.time() - start_time,
                                    "function": function_name,
                                    "arguments": safe_args,
                                    "trace_path": str(runtime_log_path),
                                },
                            )
                            raise RuntimeError(
                                "GUARD P1 LOOP BLOCKED\\n"
                                f"Run ID: {run_id}\\n"
                                f"Function: {function_name}\\n"
                                f"Arguments: {safe_args}\\n"
                                "Причина: агент продолжил одинаковый успешный "
                                "read/list после двух SUPERVISOR CHECK.\\n"
                                f"Trace: {runtime_log_path}"
                            )

                    if (
                        guard_payload is None
                        and function_name == "write_file"
                    ):
                        target_text = safe_args.get("path")
                        if isinstance(target_text, str):
                            suspicious = (
                                _guard_p1_find_suspicious_create(
                                    root,
                                    target_text,
                                    policy,
                                    task,
                                    guard_p1_state["used_paths"],
                                )
                            )
                            if suspicious is not None:
                                challenge_key = (
                                    suspicious["requested_path"],
                                    suspicious["similar_path"],
                                )
                                if (
                                    challenge_key
                                    not in guard_p1_state[
                                        "create_challenges"
                                    ]
                                ):
                                    guard_p1_state[
                                        "create_challenges"
                                    ].add(challenge_key)
                                    guard_payload = {
                                        "kind": (
                                            "possible_duplicate_create"
                                        ),
                                        **suspicious,
                                    }
                                else:
                                    _emit(
                                        "guard_override",
                                        {
                                            "guard": "P1",
                                            "kind": (
                                                "possible_duplicate_create"
                                            ),
                                            **suspicious,
                                            "message": (
                                                "Повторный write_file после "
                                                "SUPERVISOR CHECK — считаем "
                                                "осознанным подтверждением модели."
                                            ),
                                        },
                                    )

                    if guard_payload is not None:
                        guard_event_id = (
                            "guard.repeat"
                            if guard_payload.get("kind") == "repeated_tool"
                            else "guard.suspicious_create"
                        )
                        guard_variables = {
                            key: value
                            for key, value in guard_payload.items()
                            if key != "instruction"
                        }
                        resolved_guard_text = _context_message(
                            guard_event_id,
                            guard_variables,
                        )
                        guard_payload["instruction"] = resolved_guard_text
                        guard_payload["_server_context_message"] = {
                            "event_id": guard_event_id,
                            "text": resolved_guard_text,
                            "facts": {
                                "guard": "P1",
                                **guard_variables,
                            },
                        }
                        guard_p1_state["interventions"] += 1
                        if (
                            guard_p1_state["interventions"]
                            > GUARD_P1_MAX_INTERVENTIONS_PER_RUN
                        ):
                            _emit(
                                "run_failed",
                                {
                                    "reason": (
                                        "guard_p1_intervention_limit"
                                    ),
                                    "api_requests": api_request_count,
                                    "tool_calls": tool_call_count,
                                    "duration": time.time() - start_time,
                                    "trace_path": str(runtime_log_path),
                                },
                            )
                            raise RuntimeError(
                                "GUARD P1 INTERVENTION LIMIT REACHED\\n"
                                f"Run ID: {run_id}\\n"
                                "Interventions: "
                                f"{guard_p1_state['interventions']}\\n"
                                f"Trace: {runtime_log_path}"
                            )

                        _emit(
                            "guard_intervention",
                            {
                                "guard": "P1",
                                **guard_payload,
                                "tool_budget_used": tool_iterations,
                                "tool_budget_limit": policy[
                                    "tool_limit"
                                ],
                            },
                        )
                        remaining_tools = max(
                            policy["tool_limit"] - tool_iterations,
                            0,
                        )
                        guard_result = {
                            "ok": False,
                            "executed": False,
                            "guard_p1": True,
                            **guard_payload,
                            "_verification_state": dict(
                                verification_state
                            ),
                            "_tool_budget": {
                                "limit": policy["tool_limit"],
                                "used": tool_iterations,
                                "remaining": remaining_tools,
                                "instruction": (
                                    "GUARD P1 не исполнил tool и не списал "
                                    "tool budget. Пересмотри действие и продолжи."
                                ),
                            },
                        }
                        messages.append(
                            {
                                "role": "function",
                                "name": function_name,
                                "content": json.dumps(
                                    guard_result,
                                    ensure_ascii=False,
                                ),
                            }
                        )
                        continue

                permission_denied = False
                try:
                    result = _execute_agent_function(
                        root, function_call, policy, backup_session
                    )
                    if (
                        function_name in VERIFICATION_TOOL_NAMES
                        and isinstance(result, dict)
                        and result.get("ok") is False
                    ):
                        tool_ok = False
                        diagnostic = (
                            result.get("stderr")
                            or result.get("stdout")
                            or "Verification check failed."
                        )
                        tool_error = {
                            "type": "VerificationError",
                            "message": diagnostic[:4000],
                        }
                    else:
                        tool_ok = True
                        tool_error = None
                except Exception as exc:
                    permission_denied = isinstance(exc, PermissionError)
                    error_type = (
                        "STALE_FILE_STATE" if isinstance(exc, StaleFileStateError)
                        else type(exc).__name__
                    )
                    error_message = str(exc)
                    capability_by_tool = {
                        "list_dir": "READ",
                        "read_file": "READ",
                        "find_text": "READ",
                        "read_file_range": "READ",
                        "write_file": "WRITE",
                        "replace_text": "WRITE",
                        "insert_before": "WRITE",
                        "insert_after": "WRITE",
                        "delete_file": "DELETE",
                        "python_compile": "VERIFY",
                        "git_diff": "VERIFY",
                        "git_status": "VERIFY",
                        "ui_smoke_test": "VERIFY",
                    }
                    capability = capability_by_tool.get(
                        function_name, "UNKNOWN"
                    )
                    if permission_denied:
                        context_event_id = "permission.denied"
                    else:
                        context_event_id = "tool.error"
                    context_variables = {
                        "capability": capability,
                        "tool_name": function_name,
                        "error_type": error_type,
                        "error_message": error_message,
                        "path": safe_args.get("path", ""),
                    }
                    context_text = _context_message(
                        context_event_id,
                        context_variables,
                    )
                    result = {
                        "ok": False,
                        "error_type": error_type,
                        "error": error_message,
                        "instruction": context_text,
                        "_server_context_message": {
                            "event_id": context_event_id,
                            "text": context_text,
                            "facts": {
                                "decision": (
                                    "DENIED"
                                    if permission_denied
                                    else "ERROR"
                                ),
                                "arguments": safe_args,
                                **context_variables,
                            },
                        },
                    }
                    tool_ok = False
                    tool_error = {
                        "type": error_type,
                        "message": error_message,
                    }

                if (
                    not tool_ok
                    and isinstance(result, dict)
                    and "_server_context_message" not in result
                ):
                    error_type = str(tool_error.get("type") or "ToolError")
                    error_message = str(tool_error.get("message") or "")
                    context_variables = {
                        "tool_name": function_name,
                        "error_type": error_type,
                        "error_message": error_message,
                    }
                    context_text = _context_message(
                        "tool.error",
                        context_variables,
                    )
                    result = dict(result)
                    result["instruction"] = context_text
                    result["_server_context_message"] = {
                        "event_id": "tool.error",
                        "text": context_text,
                        "facts": {
                            "decision": "ERROR",
                            "arguments": safe_args,
                            **context_variables,
                        },
                    }

                if tool_ok and function_name in MUTATION_TOOL_NAMES:
                    _bookkeep_successful_mutation(
                        function_name=function_name,
                        result=result,
                        run_owned_state=final_audit_retry_state["run_owned_state"],
                        verification_state=verification_state,
                    )

                if tool_ok and function_name == "python_compile":
                    python_revision = verification_state["python_write_revision"]
                    if python_revision is not None:
                        if verification_state["python_verified_revision"] != python_revision:
                            verification_state["python_verified_paths"] = []
                        verified = set(verification_state["python_verified_paths"])
                        verified.update(result.get("paths") or [])
                        verification_state["python_verified_paths"] = sorted(verified)
                        verification_state["python_verified_revision"] = python_revision
                elif tool_ok and function_name == "git_status":
                    verification_state["git_status_revision"] = verification_state[
                        "write_revision"
                    ]
                elif tool_ok and function_name == "git_diff":
                    verification_state["git_diff_revision"] = verification_state[
                        "write_revision"
                    ]
                elif tool_ok and function_name == "ui_smoke_test":
                    ui_revision = verification_state["ui_smoke_write_revision"]
                    if ui_revision is not None:
                        verification_state["ui_smoke_verified_revision"] = ui_revision

                tool_call_count += 1
                last_tool_sequence += 1
                last_tool_name = function_name
                last_tool_args = safe_args
                last_tool_error = tool_error
                last_tool_status = "OK" if tool_ok else "ERROR"
                last_tool_result_summary = (
                    _safe_tool_result_summary(
                        function_name,
                        result,
                    )
                    if tool_ok
                    else (
                        f"{tool_error.get('type')}: "
                        f"{tool_error.get('message')}"
                        if isinstance(tool_error, dict)
                        else str(tool_error)
                    )
                )

                _emit("tool_started", {
                    "tool_sequence": last_tool_sequence,
                    "function": function_name,
                    "arguments": safe_args,
                    "timestamp": time.time(),
                })

                if permission_denied:
                    _emit("permission_denied", {
                        "tool_sequence": last_tool_sequence,
                        "function": function_name,
                        "arguments": safe_args,
                        "error": tool_error,
                    })

                if tool_ok:
                    repeated_error_signature = None
                    repeated_error_count = 0

                    if policy.get("allow_guard_p1"):
                        path_text = safe_args.get("path")
                        if (
                            function_name
                            in (READ_TOOL_NAMES | MUTATION_TOOL_NAMES)
                            and isinstance(path_text, str)
                        ):
                            try:
                                used_path = (
                                    _resolve_workspace_path(
                                        root,
                                        path_text,
                                    )
                                    .relative_to(root)
                                    .as_posix()
                                )
                                guard_p1_state[
                                    "used_paths"
                                ].add(used_path)
                            except Exception:
                                pass

                        repeat_key_after = _guard_p1_repeat_key(
                            root,
                            function_name,
                            safe_args,
                            verification_state["write_revision"],
                        )
                        if repeat_key_after is None:
                            guard_p1_state[
                                "last_repeat_success_key"
                            ] = None
                            guard_p1_state[
                                "repeat_success_count"
                            ] = 0
                        elif (
                            repeat_key_after
                            == guard_p1_state[
                                "last_repeat_success_key"
                            ]
                        ):
                            guard_p1_state[
                                "repeat_success_count"
                            ] += 1
                        else:
                            guard_p1_state[
                                "last_repeat_success_key"
                            ] = repeat_key_after
                            guard_p1_state[
                                "repeat_success_count"
                            ] = 1

                    _emit("tool_finished", {
                        "tool_sequence": last_tool_sequence,
                        "function": function_name,
                        "arguments": safe_args,
                        "duration": None,
                        "result": result,
                    })
                else:
                    _emit("tool_error", {
                        "tool_sequence": last_tool_sequence,
                        "function": function_name,
                        "arguments": safe_args,
                        "error": tool_error,
                    })

                    signature = (
                        function_name,
                        json.dumps(safe_args, ensure_ascii=False, sort_keys=True),
                        tool_error["type"],
                        tool_error["message"],
                    )
                    if signature == repeated_error_signature:
                        repeated_error_count += 1
                    else:
                        repeated_error_signature = signature
                        repeated_error_count = 1

                    if repeated_error_count >= 3:
                        _emit("run_failed", {
                            "reason": "loop_detected",
                            "api_requests": api_request_count,
                            "tool_calls": tool_call_count,
                            "duration": time.time() - start_time,
                            "function": function_name,
                            "arguments": safe_args,
                            "error": tool_error,
                            "repeat_count": repeated_error_count,
                            "trace_path": str(runtime_log_path),
                        })
                        raise RuntimeError(
                            f"LOOP DETECTED\n"
                            f"Run ID: {run_id}\n"
                            f"Function: {function_name}\n"
                            f"Arguments: {safe_args}\n"
                            f"Error: {tool_error}\n"
                            f"Repeats: {repeated_error_count}\n"
                            f"Trace: logs/runs/{run_id}.jsonl"
                        )

                tool_iterations += 1
                result_for_model = dict(result)
                result_for_model["_verification_state"] = dict(verification_state)
                remaining_tools = max(policy["tool_limit"] - tool_iterations, 0)
                result_for_model["_tool_budget"] = {
                    "limit": policy["tool_limit"],
                    "used": tool_iterations,
                    "remaining": remaining_tools,
                    "instruction": (
                        "Если оставшихся вызовов мало, прекрати лишнее исследование "
                        "и заверши задачу или сообщи, что требуется новый запуск."
                    ),
                }
                messages.append(
                    {
                        "role": "function",
                        "name": function_name,
                        "content": json.dumps(result_for_model, ensure_ascii=False),
                    }
                )
                continue

            if finish_reason not in ("stop", "eos"):
                _emit("run_failed", {
                    "reason": "bad_finish_reason",
                    "finish_reason": finish_reason,
                    "api_requests": api_request_count,
                    "tool_calls": tool_call_count,
                    "duration": time.time() - start_time,
                })
                raise RuntimeError(
                    "Агент GigaChat завершён нештатно. "
                    f"finish_reason={finish_reason!r}."
                )

            missing_verification = _verification_missing_requirements(
                verification_state
            )
            if missing_verification:
                gate_signature = json.dumps(
                    {
                        "write_revision": verification_state["write_revision"],
                        "missing": missing_verification,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                if gate_signature == last_verification_gate_signature:
                    verification_gate_repeat_count += 1
                else:
                    last_verification_gate_signature = gate_signature
                    verification_gate_repeat_count = 1

                _emit(
                    "verification_required",
                    {
                        "attempt": verification_gate_repeat_count,
                        "missing": missing_verification,
                        "verification_state": dict(verification_state),
                    },
                )

                if verification_gate_repeat_count > MAX_VERIFICATION_GATE_RETRIES:
                    _emit(
                        "run_failed",
                        {
                            "reason": "verification_gate_stuck",
                            "api_requests": api_request_count,
                            "tool_calls": tool_call_count,
                            "duration": time.time() - start_time,
                            "missing": missing_verification,
                            "verification_state": dict(verification_state),
                            "trace_path": str(runtime_log_path),
                        },
                    )
                    raise RuntimeError(
                        "VERIFICATION GATE STUCK\n"
                        f"Run ID: {run_id}\n"
                        f"Missing: {missing_verification}\n"
                        f"Trace: logs/runs/{run_id}.jsonl"
                    )

                premature_content = message.get("content")
                messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            premature_content
                            if isinstance(premature_content, str)
                            else ""
                        ),
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": _context_message(
                            "verification.required",
                            {
                                "attempt": verification_gate_repeat_count,
                                "missing_count": len(missing_verification),
                                "missing": json.dumps(
                                    missing_verification,
                                    ensure_ascii=False,
                                    sort_keys=True,
                                ),
                                "missing_lines": _verification_missing_lines(
                                    missing_verification
                                ),
                                "verification_state": json.dumps(
                                    verification_state,
                                    ensure_ascii=False,
                                    sort_keys=True,
                                ),
                            },
                        )
                        + "\n\nSERVER FACTS — NOT TEMPLATE CONTROLLED:\n"
                        + json.dumps(
                            {
                                "event_id": "verification.required",
                                "decision": "SUCCESS_BLOCKED",
                                "attempt": verification_gate_repeat_count,
                                "missing": missing_verification,
                                "verification_state": verification_state,
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    }
                )
                continue

            if verification_state["write_revision"] > 0:
                _emit(
                    "verification_passed",
                    {
                        "verification_state": dict(verification_state),
                    },
                )

            content = message.get("content")
            if not isinstance(content, str) or not content:
                _emit("run_failed", {
                    "reason": "empty_final_content",
                    "api_requests": api_request_count,
                    "tool_calls": tool_call_count,
                    "duration": time.time() - start_time,
                })
                raise RuntimeError(f"GigaChat вернул пустой финальный ответ: {data}")

            final_audit_started_at = time.time()
            _emit(
                "final_audit_started",
                {
                    "check_type": "FINAL",
                    "model_id": verifier_model_id,
                    "write_revision": verification_state["write_revision"],
                },
            )
            try:
                verification_context, evidence_completeness = (
                    _collect_final_audit_evidence(
                        root=root,
                        candidate_final=content,
                        policy=policy,
                        run_id=run_id,
                        api_request_count=api_request_count,
                        tool_call_count=tool_call_count,
                        verification_state=verification_state,
                        backup_session=backup_session,
                        run_owned_state=final_audit_retry_state["run_owned_state"],
                    )
                )
                if evidence_completeness.get("critical_for_success"):
                    raise FinalAuditEvidenceError(
                        "Критические доказательства для SUCCESS неполны: "
                        + ", ".join(
                            evidence_completeness.get("critical_reasons") or []
                        )
                    )

                final_audit_retry_state["final_audit_attempt_count"] += 1
                audit_attempt = final_audit_retry_state[
                    "final_audit_attempt_count"
                ]
                audit_result = await run_verifier_check(
                    verifier_model_id=verifier_model_id,
                    check_type="FINAL",
                    raw_task=task,
                    verification_context=verification_context,
                    task_id=run_id,
                )

                if audit_result.verdict == "FAIL":
                    final_audit_retry_state["semantic_fail_count"] += 1
                    semantic_fail_count = final_audit_retry_state[
                        "semantic_fail_count"
                    ]
                    correction_count = final_audit_retry_state[
                        "correction_count"
                    ]
                    correction_limit = final_audit_retry_state[
                        "correction_limit"
                    ]
                    candidate_fingerprint = _candidate_final_fingerprint(
                        content
                    )
                    run_owned_state_fingerprint = (
                        _run_owned_state_fingerprint(
                            final_audit_retry_state["run_owned_state"]
                        )
                    )
                    (
                        exact_failure_signature,
                        core_failure_signature,
                    ) = _final_audit_failure_signatures(
                        check_type=audit_result.check_type,
                        reason=audit_result.reason,
                        violations=audit_result.violations,
                        required_action=audit_result.required_action,
                    )

                    history = final_audit_retry_state["failure_history"]
                    previous_failure = history[-1] if history else None
                    if previous_failure is None:
                        candidate_changed = False
                        run_owned_state_changed = False
                        progress_class = "INITIAL"
                    else:
                        candidate_changed = (
                            candidate_fingerprint
                            != previous_failure["candidate_fingerprint"]
                        )
                        run_owned_state_changed = (
                            run_owned_state_fingerprint
                            != previous_failure[
                                "run_owned_state_fingerprint"
                            ]
                        )
                        progress_class = (
                            "MATERIAL_PROGRESS"
                            if candidate_changed or run_owned_state_changed
                            else "NO_PROGRESS"
                        )

                    same_core_failure_streak = (
                        previous_failure["same_core_failure_streak"] + 1
                        if previous_failure is not None
                        and previous_failure["core_failure_signature"]
                        == core_failure_signature
                        else 1
                    )
                    failure_snapshot = {
                        "audit_attempt": audit_attempt,
                        "semantic_fail_count": semantic_fail_count,
                        "candidate_fingerprint": candidate_fingerprint,
                        "run_owned_state_fingerprint": (
                            run_owned_state_fingerprint
                        ),
                        "exact_failure_signature": exact_failure_signature,
                        "core_failure_signature": core_failure_signature,
                        "same_core_failure_streak": (
                            same_core_failure_streak
                        ),
                    }
                    history.append(failure_snapshot)
                    history_limit = max(
                        correction_limit + 1,
                        FINAL_AUDIT_REPEATED_FAILURE_THRESHOLD,
                        3,
                    )
                    del history[:-history_limit]
                    ping_pong_detected = (
                        len(history) >= 3
                        and history[-1]["core_failure_signature"]
                        == history[-3]["core_failure_signature"]
                        and history[-1]["core_failure_signature"]
                        != history[-2]["core_failure_signature"]
                    )

                    terminal_reason = None
                    policy_reason = progress_class
                    if progress_class == "NO_PROGRESS":
                        terminal_reason = "final_audit_retry_no_progress"
                        policy_reason = "NO_PROGRESS"
                    elif ping_pong_detected:
                        terminal_reason = "final_audit_retry_ping_pong"
                        policy_reason = "PING_PONG"
                    elif (
                        same_core_failure_streak
                        >= FINAL_AUDIT_REPEATED_FAILURE_THRESHOLD
                    ):
                        terminal_reason = (
                            "final_audit_retry_repeated_failure"
                        )
                        policy_reason = "REPEATED_FAILURE"
                    elif correction_count >= correction_limit:
                        terminal_reason = "final_audit_correction_exhausted"
                        policy_reason = "CORRECTION_EXHAUSTED"

                    decision = (
                        "TERMINATE" if terminal_reason else "CONTINUE"
                    )
                    correction_cycle = (
                        correction_count + 1
                        if decision == "CONTINUE"
                        else None
                    )
                    _emit(
                        "final_audit_failed",
                        {
                            "verifier_run_id": audit_result.verifier_run_id,
                            "model_id": audit_result.model_id,
                            "provider_model_id": audit_result.provider_model_id,
                            "check_type": audit_result.check_type,
                            "verdict": audit_result.verdict,
                            "violations_count": len(audit_result.violations),
                            "violations": list(audit_result.violations),
                            "reason": audit_result.reason,
                            "required_action": audit_result.required_action,
                            "audit_attempt": audit_attempt,
                            "semantic_fail_count": semantic_fail_count,
                            "correction_count": correction_count,
                            "correction_limit": correction_limit,
                            "correction_handoff_available": (
                                decision == "CONTINUE"
                            ),
                            **(
                                {"correction_cycle": correction_cycle}
                                if correction_cycle is not None
                                else {}
                            ),
                            "duration": time.time() - final_audit_started_at,
                        },
                    )

                    _emit(
                        "final_audit_retry_evaluated",
                        {
                            "audit_attempt": audit_attempt,
                            "semantic_fail_count": semantic_fail_count,
                            "correction_count": correction_count,
                            "correction_limit": correction_limit,
                            "candidate_fingerprint": candidate_fingerprint,
                            "run_owned_state_fingerprint": (
                                run_owned_state_fingerprint
                            ),
                            "exact_failure_signature": (
                                exact_failure_signature
                            ),
                            "core_failure_signature": (
                                core_failure_signature
                            ),
                            "progress_class": progress_class,
                            "candidate_changed": candidate_changed,
                            "run_owned_state_changed": (
                                run_owned_state_changed
                            ),
                            "same_core_failure_streak": (
                                same_core_failure_streak
                            ),
                            "ping_pong_detected": ping_pong_detected,
                            "decision": decision,
                            "decision_reason": policy_reason,
                        },
                    )

                    violations = "\n".join(
                        f"- {item}" for item in audit_result.violations
                    ) or "- отсутствуют"

                    if terminal_reason is not None:
                        _emit(
                            "run_failed",
                            {
                                "reason": terminal_reason,
                                "api_requests": api_request_count,
                                "tool_calls": tool_call_count,
                                "duration": time.time() - start_time,
                                "verifier_reason": audit_result.reason,
                                "violations_count": len(
                                    audit_result.violations
                                ),
                                "required_action": (
                                    audit_result.required_action
                                ),
                                "audit_attempt": audit_attempt,
                                "semantic_fail_count": semantic_fail_count,
                                "correction_count": correction_count,
                                "correction_limit": correction_limit,
                                "policy_reason": policy_reason,
                                "trace_path": str(runtime_log_path),
                            },
                        )
                        raise FinalAuditSemanticError(
                            "FINAL AUDIT RETRY TERMINATED\n"
                            f"Policy: {policy_reason}\n"
                            f"Reason: {audit_result.reason}\n"
                            f"Violations:\n{violations}\n"
                            "Required action: "
                            f"{audit_result.required_action}"
                        )

                    if correction_cycle is not None:
                        _emit(
                            "audit_diagnostic_question",
                            {
                                "audit_attempt": audit_attempt,
                                "text": AUDIT_DIAGNOSTIC_QUESTION,
                            },
                        )
                        try:
                            diagnostic_answer = await _request_audit_diagnostic(
                                client, headers, run_model, messages, content,
                                AUDIT_DIAGNOSTIC_QUESTION,
                            )
                        except Exception as exc:
                            _emit(
                                "audit_diagnostic_error",
                                {
                                    "audit_attempt": audit_attempt,
                                    "text": f"{type(exc).__name__}: {str(exc)[:300]}",
                                },
                            )
                        else:
                            _emit(
                                "audit_diagnostic_answer",
                                {
                                    "audit_attempt": audit_attempt,
                                    "text": diagnostic_answer,
                                },
                            )
                        remaining_corrections = (
                            correction_limit - correction_cycle
                        )
                        feedback_template = _context_message(
                            "final_audit.feedback",
                            {
                                "verdict": audit_result.verdict,
                                "reason": audit_result.reason,
                                "violations_lines": violations,
                                "required_action": (
                                    audit_result.required_action
                                ),
                                "verifier_run_id": (
                                    audit_result.verifier_run_id
                                ),
                                "check_type": audit_result.check_type,
                                "correction_cycle": correction_cycle,
                                "correction_limit": correction_limit,
                                "remaining_corrections": (
                                    remaining_corrections
                                ),
                            },
                        )
                        server_facts = {
                            "event_id": "final_audit.feedback",
                            "message_kind": (
                                "SERVER_FINAL_VERIFIER_FEEDBACK"
                            ),
                            "is_new_user_task": False,
                            "raw_task_authority": "SOURCE_OF_TRUTH",
                            "decision": (
                                "SUCCESS_BLOCKED_CORRECTION_REQUESTED"
                            ),
                            "run_id": run_id,
                            "verifier_run_id": (
                                audit_result.verifier_run_id
                            ),
                            "check_type": audit_result.check_type,
                            "verdict": audit_result.verdict,
                            "reason": audit_result.reason,
                            "violations": list(audit_result.violations),
                            "required_action": (
                                audit_result.required_action
                            ),
                            "audit_attempt": audit_attempt,
                            "semantic_fail_count": semantic_fail_count,
                            "correction_count": correction_cycle,
                            "correction_cycle": correction_cycle,
                            "correction_limit": correction_limit,
                            "remaining_corrections": (
                                remaining_corrections
                            ),
                        }
                        feedback_content = (
                            feedback_template
                            + "\n\nSERVER FACTS — NOT TEMPLATE CONTROLLED:\n"
                            + json.dumps(
                                server_facts,
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        )
                        _emit(
                            "final_audit_feedback_created",
                            {
                                "verifier_run_id": (
                                    audit_result.verifier_run_id
                                ),
                                "check_type": audit_result.check_type,
                                "audit_attempt": audit_attempt,
                                "semantic_fail_count": semantic_fail_count,
                                "correction_cycle": correction_cycle,
                                "correction_limit": correction_limit,
                                "remaining_corrections": (
                                    remaining_corrections
                                ),
                                "feedback_chars": len(feedback_content),
                                "violations_count": len(
                                    audit_result.violations
                                ),
                            },
                        )
                        messages.append(
                            {"role": "assistant", "content": content}
                        )
                        messages.append(
                            {"role": "user", "content": feedback_content}
                        )
                        final_audit_retry_state["correction_count"] = (
                            correction_cycle
                        )
                        _emit(
                            "final_audit_feedback_delivered",
                            {
                                "verifier_run_id": (
                                    audit_result.verifier_run_id
                                ),
                                "check_type": audit_result.check_type,
                                "audit_attempt": audit_attempt,
                                "semantic_fail_count": semantic_fail_count,
                                "correction_count": correction_cycle,
                                "correction_cycle": correction_cycle,
                                "correction_limit": correction_limit,
                                "remaining_corrections": (
                                    remaining_corrections
                                ),
                                "feedback_chars": len(feedback_content),
                                "violations_count": len(
                                    audit_result.violations
                                ),
                            },
                        )
                        _emit(
                            "final_audit_correction_started",
                            {
                                "verifier_run_id": (
                                    audit_result.verifier_run_id
                                ),
                                "check_type": audit_result.check_type,
                                "audit_attempt": audit_attempt,
                                "semantic_fail_count": semantic_fail_count,
                                "correction_count": correction_cycle,
                                "correction_cycle": correction_cycle,
                                "correction_limit": correction_limit,
                                "remaining_corrections": (
                                    remaining_corrections
                                ),
                            },
                        )
                        continue

                if audit_result.verdict != "PASS":
                    raise VerifierProtocolError(
                        "Final Audit вернул неизвестный verdict: "
                        f"{audit_result.verdict!r}."
                    )

                _emit(
                    "final_audit_passed",
                    {
                        "verifier_run_id": audit_result.verifier_run_id,
                        "model_id": audit_result.model_id,
                        "provider_model_id": audit_result.provider_model_id,
                        "check_type": audit_result.check_type,
                        "verdict": audit_result.verdict,
                        "violations_count": len(audit_result.violations),
                        "reason": audit_result.reason,
                        "audit_attempt": audit_attempt,
                        "semantic_fail_count": final_audit_retry_state[
                            "semantic_fail_count"
                        ],
                        "correction_count": final_audit_retry_state[
                            "correction_count"
                        ],
                        "correction_limit": final_audit_retry_state[
                            "correction_limit"
                        ],
                        "duration": time.time() - final_audit_started_at,
                    },
                )
            except FinalAuditSemanticError:
                raise
            except (FinalAuditEvidenceError, VerifierRuntimeError) as exc:
                error_reason = (
                    "final_audit_evidence_incomplete"
                    if isinstance(exc, FinalAuditEvidenceError)
                    else "final_audit_runtime_error"
                )
                _emit(
                    "final_audit_error",
                    {
                        "model_id": verifier_model_id,
                        "check_type": "FINAL",
                        "error_type": type(exc).__name__,
                        "reason": str(exc),
                        "final_audit_attempt_count": (
                            final_audit_retry_state[
                                "final_audit_attempt_count"
                            ]
                        ),
                        "duration": time.time() - final_audit_started_at,
                    },
                )
                _emit(
                    "run_failed",
                    {
                        "reason": error_reason,
                        "api_requests": api_request_count,
                        "tool_calls": tool_call_count,
                        "duration": time.time() - start_time,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "final_audit_attempt_count": (
                            final_audit_retry_state[
                                "final_audit_attempt_count"
                            ]
                        ),
                        "trace_path": str(runtime_log_path),
                    },
                )
                raise RuntimeError(
                    "FINAL AUDIT ERROR\n"
                    f"Type: {type(exc).__name__}\n"
                    f"Reason: {exc}"
                ) from exc
            except Exception as exc:
                _emit(
                    "final_audit_error",
                    {
                        "model_id": verifier_model_id,
                        "check_type": "FINAL",
                        "error_type": type(exc).__name__,
                        "reason": str(exc),
                        "final_audit_attempt_count": (
                            final_audit_retry_state[
                                "final_audit_attempt_count"
                            ]
                        ),
                        "duration": time.time() - final_audit_started_at,
                    },
                )
                _emit(
                    "run_failed",
                    {
                        "reason": "final_audit_runtime_error",
                        "api_requests": api_request_count,
                        "tool_calls": tool_call_count,
                        "duration": time.time() - start_time,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "final_audit_attempt_count": (
                            final_audit_retry_state[
                                "final_audit_attempt_count"
                            ]
                        ),
                        "trace_path": str(runtime_log_path),
                    },
                )
                raise RuntimeError(
                    "FINAL AUDIT ERROR\n"
                    f"Type: {type(exc).__name__}\n"
                    f"Reason: {exc}"
                ) from exc

            _emit("run_finished", {
                "status": "SUCCESS",
                "api_requests": api_request_count,
                "tool_calls": tool_call_count,
                "duration": time.time() - start_time,
                "backup_path": (
                    str(backup_session["backup_dir"])
                    if backup_session is not None
                    else None
                ),
                "verification_state": verification_state,
            })
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
        run_id = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        log_dir = Path("logs") / "runs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{run_id}.jsonl"
        event = {
            "event": "run_failed",
            "run_id": run_id,
            "timestamp": time.time(),
            "reason": "empty_task_file",
            "task_file": task_path.as_posix(),
        }
        try:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass

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
