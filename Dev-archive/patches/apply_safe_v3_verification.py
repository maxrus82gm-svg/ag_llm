from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "server.py"
UI = ROOT / "ultra_ui.py"
STAMP = time.strftime("%Y%m%d_%H%M%S")


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"ERROR: {message}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: ожидалось ровно 1 совпадение, найдено {count}. Ничего не записано.")
    return text.replace(old, new, 1)


def insert_before_once(text: str, marker: str, insertion: str, label: str) -> str:
    count = text.count(marker)
    if count != 1:
        fail(f"{label}: ожидалось ровно 1 совпадение маркера, найдено {count}. Ничего не записано.")
    return text.replace(marker, insertion + marker, 1)


def load(path: Path) -> str:
    if not path.is_file():
        fail(f"не найден {path.name} рядом с patch-скриптом")
    return path.read_text(encoding="utf-8")


def patch_server(text: str) -> str:
    text = replace_once(
        text,
        "import shutil\nimport time\nimport uuid\nfrom pathlib import Path\n",
        "import shutil\nimport subprocess\nimport sys\nimport tempfile\nimport time\nimport uuid\nfrom pathlib import Path\n",
        "server imports",
    )

    text = replace_once(
        text,
        "MAX_CONFIGURABLE_TOOL_ITERATIONS = 200\n",
        "MAX_CONFIGURABLE_TOOL_ITERATIONS = 200\n"
        "MAX_VERIFY_OUTPUT_BYTES = 128 * 1024\n"
        "VERIFY_TIMEOUT_SECONDS = 30\n"
        "UI_SMOKE_TIMEOUT_SECONDS = 30\n"
        "VERIFICATION_TOOL_NAMES = {\n"
        "    \"python_compile\",\n"
        "    \"git_status\",\n"
        "    \"git_diff\",\n"
        "    \"ui_smoke_test\",\n"
        "}\n",
        "verification constants",
    )

    verification_function_schemas = r'''
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
'''
    text = insert_before_once(
        text,
        "]\n\n_access_token: str | None = None",
        verification_function_schemas,
        "AGENT_FUNCTIONS verification schemas",
    )

    text = replace_once(
        text,
        '            "allow_delete": False,\n            "read_scope": ".",\n',
        '            "allow_delete": False,\n            "allow_verify": True,\n            "read_scope": ".",\n',
        "default allow_verify",
    )

    text = replace_once(
        text,
        '    allow_delete = bool(permissions.get("allow_delete", False))\n    auto_backup = bool(permissions.get("auto_backup", True))\n',
        '    allow_delete = bool(permissions.get("allow_delete", False))\n'
        '    allow_verify = bool(permissions.get("allow_verify", True))\n'
        '    auto_backup = bool(permissions.get("auto_backup", True))\n',
        "normalize allow_verify",
    )

    text = replace_once(
        text,
        '        "allow_delete": allow_delete,\n        "read_scope": read_scope,\n',
        '        "allow_delete": allow_delete,\n        "allow_verify": allow_verify,\n        "read_scope": read_scope,\n',
        "normalized policy return",
    )

    text = replace_once(
        text,
        '    if policy["allow_delete"]:\n        allowed_names.add("delete_file")\n    return [item for item in AGENT_FUNCTIONS if item["name"] in allowed_names]\n',
        '    if policy["allow_delete"]:\n'
        '        allowed_names.add("delete_file")\n'
        '    # VERIFY не является обходом READ: инструменты проверки получают код/дифф\n'
        '    # только когда физически разрешено чтение.\n'
        '    if policy["allow_verify"] and policy["allow_read"]:\n'
        '        allowed_names.update(VERIFICATION_TOOL_NAMES)\n'
        '    return [item for item in AGENT_FUNCTIONS if item["name"] in allowed_names]\n',
        "functions_for_policy verify",
    )

    text = replace_once(
        text,
        '        "allow_delete": policy["allow_delete"],\n        "read_scope": policy["read_scope"],\n',
        '        "allow_delete": policy["allow_delete"],\n        "allow_verify": policy["allow_verify"],\n        "read_scope": policy["read_scope"],\n',
        "policy_summary verify",
    )

    verification_helpers = r'''

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
        "    print(f\"OK: {item[\'relative\']}\")\n"
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
'''
    text = insert_before_once(
        text,
        "\ndef _parse_agent_arguments(function_name: str, raw_arguments: object) -> dict:\n",
        verification_helpers,
        "verification helper functions",
    )

    old_execute = r'''def _execute_agent_function(
    root: Path,
    function_call: object,
    policy: dict,
    backup_session: dict | None,
) -> dict:
    if not isinstance(function_call, dict):
        raise ValueError("GigaChat вернул невалидный function_call.")

    name = function_call.get("name")
    if name not in {"list_dir", "read_file", "write_file", "delete_file"}:
        raise ValueError(f"GigaChat запросил неизвестную функцию: {name!r}.")

    arguments = _parse_agent_arguments(name, function_call.get("arguments"))
    expected_keys = {
        "list_dir": {"path"},
        "read_file": {"path"},
        "write_file": {"path", "content"},
        "delete_file": {"path"},
    }[name]
    if set(arguments) != expected_keys:
        raise ValueError(
            f"Невалидные аргументы {name}: ожидаются {sorted(expected_keys)}."
        )

    if name == "list_dir":
        return _agent_list_dir(root, arguments["path"], policy)
    if name == "read_file":
        return _agent_read_file(root, arguments["path"], policy)
    if name == "delete_file":
        return _agent_delete_file(
            root,
            arguments["path"],
            policy,
            backup_session,
        )
    return _agent_write_file(
        root,
        arguments["path"],
        arguments["content"],
        policy,
        backup_session,
    )
'''
    new_execute = r'''def _execute_agent_function(
    root: Path,
    function_call: object,
    policy: dict,
    backup_session: dict | None,
) -> dict:
    if not isinstance(function_call, dict):
        raise ValueError("GigaChat вернул невалидный function_call.")

    name = function_call.get("name")
    allowed_names = {
        "list_dir",
        "read_file",
        "write_file",
        "delete_file",
        *VERIFICATION_TOOL_NAMES,
    }
    if name not in allowed_names:
        raise ValueError(f"GigaChat запросил неизвестную функцию: {name!r}.")

    arguments = _parse_agent_arguments(name, function_call.get("arguments"))
    expected_keys = {
        "list_dir": {"path"},
        "read_file": {"path"},
        "write_file": {"path", "content"},
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
    if name == "python_compile":
        return _agent_python_compile(root, arguments["paths"], policy)
    if name == "git_status":
        return _agent_git_status(root, policy)
    if name == "git_diff":
        return _agent_git_diff(root, arguments["paths"], policy)
    return _agent_ui_smoke_test(root, policy)
'''
    text = replace_once(text, old_execute, new_execute, "_execute_agent_function")

    text = replace_once(
        text,
        '        f"Удаление: {\'РАЗРЕШЕНО\' if policy[\'allow_delete\'] else \'ЗАПРЕЩЕНО\'}\\n"\n        f"Область удаления: {policy[\'delete_scope\']}\\n"\n',
        '        f"Удаление: {\'РАЗРЕШЕНО\' if policy[\'allow_delete\'] else \'ЗАПРЕЩЕНО\'}\\n"\n'
        '        f"Область удаления: {policy[\'delete_scope\']}\\n"\n'
        '        f"VERIFY: {\'РАЗРЕШЁН\' if policy[\'allow_verify\'] else \'ЗАПРЕЩЁН\'}\\n"\n',
        "permission text verify",
    )

    text = replace_once(
        text,
        '        f"Автобэкап: {\'ВКЛЮЧЁН\' if policy[\'auto_backup\'] else \'ВЫКЛЮЧЕН\'}\\n"\n'
        '        "Эти ограничения применяются кодом сервера. Не пытайся выходить "\n',
        '        f"Автобэкап: {\'ВКЛЮЧЁН\' if policy[\'auto_backup\'] else \'ВЫКЛЮЧЕН\'}\\n"\n'
        '        "VERIFY использует только белый список: python_compile, git_status, "\n'
        '        "git_diff, ui_smoke_test. Произвольного terminal/shell нет.\\n"\n'
        '        "Если в RUN изменён .py, после ПОСЛЕДНЕЙ записи обязательно запусти "\n'
        '        "python_compile. Если изменён ultra_ui.py — дополнительно ui_smoke_test. "\n'
        '        "После последних записей просмотри git_diff и используй git_status для "\n'
        '        "фактического списка изменений. Ошибку проверки сначала исправь, затем "\n'
        '        "повтори проверку. Не утверждай, что код проверен, без этих tools.\\n"\n'
        '        "Эти ограничения применяются кодом сервера. Не пытайся выходить "\n',
        "verification system rules",
    )

    text = replace_once(
        text,
        '    repeated_error_signature = None\n    repeated_error_count = 0\n\n    async with httpx.AsyncClient(timeout=180.0) as client:\n',
        '    repeated_error_signature = None\n'
        '    repeated_error_count = 0\n'
        '    verification_state = {\n'
        '        "write_revision": 0,\n'
        '        "python_verified_revision": None,\n'
        '        "python_verified_paths": [],\n'
        '        "git_status_revision": None,\n'
        '        "git_diff_revision": None,\n'
        '        "ui_smoke_verified_revision": None,\n'
        '        "changed_python_paths": [],\n'
        '        "ultra_ui_modified": False,\n'
        '    }\n\n'
        '    async with httpx.AsyncClient(timeout=180.0) as client:\n',
        "verification revision state init",
    )

    text = replace_once(
        text,
        '                    result = _execute_agent_function(\n'
        '                        root, function_call, policy, backup_session\n'
        '                    )\n'
        '                    tool_ok = True\n'
        '                    tool_error = None\n',
        '                    result = _execute_agent_function(\n'
        '                        root, function_call, policy, backup_session\n'
        '                    )\n'
        '                    if (\n'
        '                        function_name in VERIFICATION_TOOL_NAMES\n'
        '                        and isinstance(result, dict)\n'
        '                        and result.get("ok") is False\n'
        '                    ):\n'
        '                        tool_ok = False\n'
        '                        diagnostic = (\n'
        '                            result.get("stderr")\n'
        '                            or result.get("stdout")\n'
        '                            or "Verification check failed."\n'
        '                        )\n'
        '                        tool_error = {\n'
        '                            "type": "VerificationError",\n'
        '                            "message": diagnostic[:4000],\n'
        '                        }\n'
        '                    else:\n'
        '                        tool_ok = True\n'
        '                        tool_error = None\n',
        "verification failure becomes tool_error",
    )

    state_update = r'''
                if tool_ok and function_name in {"write_file", "delete_file"}:
                    verification_state["write_revision"] += 1
                    verification_state["python_verified_revision"] = None
                    verification_state["python_verified_paths"] = []
                    verification_state["git_status_revision"] = None
                    verification_state["git_diff_revision"] = None
                    verification_state["ui_smoke_verified_revision"] = None
                    changed_path = result.get("path") if isinstance(result, dict) else None
                    if (
                        function_name == "write_file"
                        and isinstance(changed_path, str)
                        and changed_path.lower().endswith(".py")
                    ):
                        if changed_path not in verification_state["changed_python_paths"]:
                            verification_state["changed_python_paths"].append(changed_path)
                        if changed_path == "ultra_ui.py":
                            verification_state["ultra_ui_modified"] = True

                if tool_ok and function_name == "python_compile":
                    verification_state["python_verified_revision"] = verification_state[
                        "write_revision"
                    ]
                    verification_state["python_verified_paths"] = list(
                        result.get("paths") or []
                    )
                elif tool_ok and function_name == "git_status":
                    verification_state["git_status_revision"] = verification_state[
                        "write_revision"
                    ]
                elif tool_ok and function_name == "git_diff":
                    verification_state["git_diff_revision"] = verification_state[
                        "write_revision"
                    ]
                elif tool_ok and function_name == "ui_smoke_test":
                    verification_state["ui_smoke_verified_revision"] = verification_state[
                        "write_revision"
                    ]
'''
    text = insert_before_once(
        text,
        "\n                tool_call_count += 1\n",
        state_update,
        "verification revision updates",
    )

    text = replace_once(
        text,
        '                result_for_model = dict(result)\n                remaining_tools = max(policy["tool_limit"] - tool_iterations, 0)\n',
        '                result_for_model = dict(result)\n'
        '                result_for_model["_verification_state"] = dict(verification_state)\n'
        '                remaining_tools = max(policy["tool_limit"] - tool_iterations, 0)\n',
        "verification state in tool result",
    )

    text = replace_once(
        text,
        '                "backup_path": (\n                    str(backup_session["backup_dir"])\n                    if backup_session is not None\n                    else None\n                ),\n',
        '                "backup_path": (\n'
        '                    str(backup_session["backup_dir"])\n'
        '                    if backup_session is not None\n'
        '                    else None\n'
        '                ),\n'
        '                "verification_state": verification_state,\n',
        "run_finished verification state",
    )

    return text


def patch_ui(text: str) -> str:
    text = replace_once(
        text,
        '        self.allow_delete_var = tk.BooleanVar(value=False)\n        self.auto_backup_var = tk.BooleanVar(value=True)\n',
        '        self.allow_delete_var = tk.BooleanVar(value=False)\n'
        '        self.allow_verify_var = tk.BooleanVar(value=True)\n'
        '        self.auto_backup_var = tk.BooleanVar(value=True)\n',
        "UI allow_verify var",
    )

    verify_ui = r'''
        # VERIFY — отдельное безопасное разрешение на белый список проверок.
        verify_check = ttk.Checkbutton(
            security,
            text="VERIFY — Python / Git / UI проверки",
            variable=self.allow_verify_var,
        )
        verify_check.grid(
            row=4, column=1, columnspan=3, sticky="w", pady=(6, 0)
        )

'''
    text = insert_before_once(
        text,
        '        ttk.Label(security, text="Защищённые бэкапы:").grid(\n            row=4, column=1, sticky="w", padx=(2, 0), pady=(6, 0)\n        )\n',
        verify_ui,
        "VERIFY UI checkbox",
    )

    text = replace_once(
        text,
        '        ttk.Label(security, text="Защищённые бэкапы:").grid(\n            row=4, column=1, sticky="w", padx=(2, 0), pady=(6, 0)\n        )\n',
        '        ttk.Label(security, text="Защищённые бэкапы:").grid(\n'
        '            row=5, column=1, sticky="w", padx=(2, 0), pady=(6, 0)\n'
        '        )\n',
        "backup label row",
    )
    text = replace_once(
        text,
        '        backup_label.grid(\n            row=4, column=2, columnspan=3, sticky="w", padx=(8, 0), pady=(6, 0)\n        )\n',
        '        backup_label.grid(\n'
        '            row=5, column=2, columnspan=3, sticky="w", padx=(8, 0), pady=(6, 0)\n'
        '        )\n',
        "backup value row",
    )
    text = replace_once(
        text,
        '        hint.grid(row=5, column=1, columnspan=4, sticky="w", pady=(8, 0))\n',
        '        hint.grid(row=6, column=1, columnspan=4, sticky="w", pady=(8, 0))\n',
        "hint row",
    )

    text = replace_once(
        text,
        '                delete_check,\n                backup_check,\n',
        '                delete_check,\n                verify_check,\n                backup_check,\n',
        "security widgets verify",
    )

    text = replace_once(
        text,
        '                "Интерфейс готов. По умолчанию чтение разрешено, запись "\n                "и удаление ЗАПРЕЩЕНЫ, автобэкап включён. Лимит tools = 20. "\n',
        '                "Интерфейс готов. По умолчанию чтение и VERIFY разрешены, запись "\n'
        '                "и удаление ЗАПРЕЩЕНЫ, автобэкап включён. Лимит tools = 20. "\n',
        "startup text verify",
    )

    text = replace_once(
        text,
        '                f"D={perms.get(\'allow_delete\')}:{perms.get(\'delete_scope\')} | "\n                f"LIMIT={perms.get(\'tool_limit\')} | "\n',
        '                f"D={perms.get(\'allow_delete\')}:{perms.get(\'delete_scope\')} | "\n'
        '                f"V={perms.get(\'allow_verify\')} | "\n'
        '                f"LIMIT={perms.get(\'tool_limit\')} | "\n',
        "trace run_started verify",
    )

    text = replace_once(
        text,
        '            "allow_delete": self.allow_delete_var.get(),\n            "read_scope": read_scope,\n',
        '            "allow_delete": self.allow_delete_var.get(),\n'
        '            "allow_verify": self.allow_verify_var.get(),\n'
        '            "read_scope": read_scope,\n',
        "permissions allow_verify",
    )

    text = replace_once(
        text,
        '                f"DELETE={\'ON\' if permissions[\'allow_delete\'] else \'OFF\'} "\n                f"[{delete_scope}], "\n                f"TOOLS={tool_limit}, "\n',
        '                f"DELETE={\'ON\' if permissions[\'allow_delete\'] else \'OFF\'} "\n'
        '                f"[{delete_scope}], "\n'
        '                f"VERIFY={\'ON\' if permissions[\'allow_verify\'] else \'OFF\'}, "\n'
        '                f"TOOLS={tool_limit}, "\n',
        "UI run permissions text verify",
    )

    return text


def main() -> None:
    server_old = load(SERVER)
    ui_old = load(UI)

    if "VERIFICATION_TOOL_NAMES" in server_old or "allow_verify_var" in ui_old:
        fail("похоже, SAFE v3 Verification Layer уже установлен")

    server_new = patch_server(server_old)
    ui_new = patch_ui(ui_old)

    # До записи проверяем Python-синтаксис обеих будущих версий.
    compile(server_new, "server.py", "exec")
    compile(ui_new, "ultra_ui.py", "exec")

    if "--check" in sys.argv[1:]:
        print("OK: текущие server.py и ultra_ui.py совместимы с SAFE v3 patch")
        print("OK: будущие версии обоих файлов проходят compile()")
        print("Ничего не изменено (--check).")
        return

    server_backup = ROOT / f"server.py.before_safe_v3_verify_{STAMP}"
    ui_backup = ROOT / f"ultra_ui.py.before_safe_v3_verify_{STAMP}"
    shutil.copy2(SERVER, server_backup)
    shutil.copy2(UI, ui_backup)

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=ROOT, suffix=".server.tmp"
    ) as f:
        f.write(server_new)
        server_temp = Path(f.name)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=ROOT, suffix=".ui.tmp"
    ) as f:
        f.write(ui_new)
        ui_temp = Path(f.name)

    try:
        os.replace(server_temp, SERVER)
        os.replace(ui_temp, UI)
    except Exception:
        # Если вторая атомарная замена неожиданно упала — возвращаем оба исходника.
        shutil.copy2(server_backup, SERVER)
        shutil.copy2(ui_backup, UI)
        raise
    finally:
        server_temp.unlink(missing_ok=True)
        ui_temp.unlink(missing_ok=True)

    print("OK: SAFE v3 Verification Layer установлен")
    print(f"Backup: {server_backup.name}")
    print(f"Backup: {ui_backup.name}")
    print("Добавлено Ultra:")
    print("  - python_compile")
    print("  - git_status")
    print("  - git_diff")
    print("  - ui_smoke_test")
    print("  - VERIFY checkbox (default ON)")
    print("  - write/verify revision state (без server-side SUCCESS gate)")
    print()
    print("Следующая проверка:")
    print(f'  "{sys.executable}" -m py_compile server.py ultra_ui.py')
    print("После этого полностью перезапусти Ultra.")


if __name__ == "__main__":
    main()
