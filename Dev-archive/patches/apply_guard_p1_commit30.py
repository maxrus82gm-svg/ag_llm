from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

SERVER = Path("server.py")
UI = Path("ultra_ui.py")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: ожидалось ровно 1 совпадение anchor, найдено {count}. "
            "Файлы не изменены."
        )
    return text.replace(old, new, 1)


def insert_before(text: str, marker: str, block: str, label: str) -> str:
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(
            f"{label}: ожидалось ровно 1 совпадение marker, найдено {count}. "
            "Файлы не изменены."
        )
    return text.replace(marker, block + marker, 1)


def atomic_write(path: Path, text: str) -> None:
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.guard_p1.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def patch_server(text: str) -> str:
    text = replace_once(
        text,
        '''import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
''',
        '''import json
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
''',
        "server imports",
    )

    text = replace_once(
        text,
        '''MAX_VERIFICATION_GATE_RETRIES = 3
VERIFICATION_TOOL_NAMES = {
''',
        '''MAX_VERIFICATION_GATE_RETRIES = 3

# GUARD P1 — server-side supervisor для мягкого вмешательства
# в явно подозрительные действия агента.
GUARD_P1_VERSION = 1
GUARD_P1_REPEAT_AFTER_SUCCESSES = 2
GUARD_P1_REPEAT_MAX_INTERVENTIONS = 2
GUARD_P1_MAX_INTERVENTIONS_PER_RUN = 8
GUARD_P1_CREATE_SCORE_THRESHOLD = 75
GUARD_P1_REPEAT_TOOL_NAMES = {"read_file", "list_dir"}

VERIFICATION_TOOL_NAMES = {
''',
        "server constants",
    )

    text = replace_once(
        text,
        '''            "allow_delete": False,
            "allow_verify": True,
            "read_scope": ".",
''',
        '''            "allow_delete": False,
            "allow_verify": True,
            "allow_guard_p1": True,
            "read_scope": ".",
''',
        "server default permissions",
    )

    text = replace_once(
        text,
        '''    allow_delete = bool(permissions.get("allow_delete", False))
    allow_verify = bool(permissions.get("allow_verify", True))
    # Защищённый backup — обязательная серверная защита.
''',
        '''    allow_delete = bool(permissions.get("allow_delete", False))
    allow_verify = bool(permissions.get("allow_verify", True))
    allow_guard_p1 = bool(permissions.get("allow_guard_p1", True))
    # Защищённый backup — обязательная серверная защита.
''',
        "server normalize guard bool",
    )

    text = replace_once(
        text,
        '''        "allow_delete": allow_delete,
        "allow_verify": allow_verify,
        "read_scope": read_scope,
''',
        '''        "allow_delete": allow_delete,
        "allow_verify": allow_verify,
        "allow_guard_p1": allow_guard_p1,
        "read_scope": read_scope,
''',
        "server normalized policy",
    )

    text = replace_once(
        text,
        '''        "allow_delete": policy["allow_delete"],
        "allow_verify": policy["allow_verify"],
        "read_scope": policy["read_scope"],
''',
        '''        "allow_delete": policy["allow_delete"],
        "allow_verify": policy["allow_verify"],
        "allow_guard_p1": policy["allow_guard_p1"],
        "read_scope": policy["read_scope"],
''',
        "server policy summary",
    )

    helpers = r'''

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
    if function_name == "read_file":
        content = result.get("content")
        chars = len(content) if isinstance(content, str) else None
        return f"path={path!r}, chars={chars}"

    if function_name == "list_dir":
        entries = result.get("entries")
        count = len(entries) if isinstance(entries, list) else None
        return f"path={path!r}, entries={count}"

    if function_name in {"write_file", "delete_file"}:
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


'''
    text = insert_before(
        text,
        "\ndef _execute_agent_function(\n",
        helpers,
        "server GUARD P1 helpers",
    )

    text = replace_once(
        text,
        '''        f"VERIFY: {'РАЗРЕШЁН' if policy['allow_verify'] else 'ЗАПРЕЩЁН'}\\n"
        f"Лимит вызовов инструментов: {policy['tool_limit']}\\n"
''',
        '''        f"VERIFY: {'РАЗРЕШЁН' if policy['allow_verify'] else 'ЗАПРЕЩЁН'}\\n"
        f"GUARD P1: {'ВКЛЮЧЁН' if policy['allow_guard_p1'] else 'ВЫКЛЮЧЕН'}\\n"
        f"Лимит вызовов инструментов: {policy['tool_limit']}\\n"
''',
        "server permission text guard flag",
    )

    text = replace_once(
        text,
        '''        "Не трать вызовы на повторное чтение без необходимости.\\n"
        f"Автобэкап: {'ВКЛЮЧЁН' if policy['auto_backup'] else 'ВЫКЛЮЧЕН'}\\n"
''',
        '''        "Не трать вызовы на повторное чтение без необходимости.\\n"
        "GUARD P1 при включении может ДО выполнения подозрительного действия "
        "вернуть SUPERVISOR CHECK: повторное чтение без изменения состояния "
        "или создание нового файла, очень похожего на существующий. "
        "Это мягкая самопроверка, а не автоматическое доказательство ошибки.\\n"
        f"Автобэкап: {'ВКЛЮЧЁН' if policy['auto_backup'] else 'ВЫКЛЮЧЕН'}\\n"
''',
        "server permission text guard explanation",
    )

    text = replace_once(
        text,
        '''    last_tool_name = None
    last_tool_args = None
    last_tool_error = None
    repeated_error_signature = None
''',
        '''    last_tool_name = None
    last_tool_args = None
    last_tool_error = None
    last_tool_status = None
    last_tool_result_summary = None
    repeated_error_signature = None
''',
        "server last tool diagnostics",
    )

    text = replace_once(
        text,
        '''    last_verification_gate_signature = None
    verification_gate_repeat_count = 0

    async with httpx.AsyncClient(timeout=180.0) as client:
''',
        '''    last_verification_gate_signature = None
    verification_gate_repeat_count = 0

    guard_p1_state = {
        "used_paths": set(),
        "last_repeat_success_key": None,
        "repeat_success_count": 0,
        "repeat_interventions": {},
        "create_challenges": set(),
        "interventions": 0,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
''',
        "server guard state",
    )

    guard_main = r'''                # GUARD P1 — supervisor BEFORE actual tool execution.
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
                                "instruction": (
                                    "SUPERVISOR CHECK — этот же успешный tool "
                                    "с теми же arguments уже выполнялся несколько "
                                    "раз, а релевантное состояние не изменилось. "
                                    "Вызов сейчас НЕ выполнен. Снова сопоставь "
                                    "действие с исходной TASK и используй уже "
                                    "полученный результат. Если повтор действительно "
                                    "нужен, измени план/состояние; не продолжай "
                                    "механически повторять тот же вызов."
                                ),
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
                                        "instruction": (
                                            "SUPERVISOR CHECK — ты собираешься "
                                            "СОЗДАТЬ новый файл, очень похожий "
                                            "на существующий. Новый файл пока "
                                            "НЕ создан. Снова сопоставь действие "
                                            "с исходной TASK: действительно нужен "
                                            "новый документ или следовало изменить "
                                            "существующий? Если после самопроверки "
                                            "создание действительно нужно, повтори "
                                            "тот же write_file: повторный осознанный "
                                            "запрос в этом RUN будет разрешён."
                                        ),
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

'''
    text = replace_once(
        text,
        '''                permission_denied = False
                try:
                    result = _execute_agent_function(
''',
        guard_main
        + '''                permission_denied = False
                try:
                    result = _execute_agent_function(
''',
        "server guard before execution",
    )

    text = replace_once(
        text,
        '''                last_tool_name = function_name
                last_tool_args = safe_args
                last_tool_error = tool_error

                _emit("tool_started", {
''',
        '''                last_tool_name = function_name
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
''',
        "server last tool status",
    )

    text = replace_once(
        text,
        '''                if tool_ok:
                    repeated_error_signature = None
                    repeated_error_count = 0
                    _emit("tool_finished", {
''',
        '''                if tool_ok:
                    repeated_error_signature = None
                    repeated_error_count = 0

                    if policy.get("allow_guard_p1"):
                        path_text = safe_args.get("path")
                        if (
                            function_name
                            in {
                                "read_file",
                                "write_file",
                                "delete_file",
                            }
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
''',
        "server guard state after success",
    )

    text = replace_once(
        text,
        '''                        f"Tool limit: {policy['tool_limit']}\\n"
                        f"Last function: {last_tool_name}\\n"
                        f"Last arguments: {last_tool_args}\\n"
                        f"Last result/error: {last_tool_error}\\n"
                        f"Trace: logs/runs/{run_id}.jsonl"
''',
        '''                        f"Tool limit: {policy['tool_limit']}\\n"
                        f"Last function: {last_tool_name}\\n"
                        f"Last arguments: {last_tool_args}\\n"
                        f"Last status: {last_tool_status}\\n"
                        f"Last result/error: {last_tool_result_summary}\\n"
                        f"Trace: {runtime_log_path}"
''',
        "server tool limit diagnostics",
    )

    return text


def patch_ui(text: str) -> str:
    text = replace_once(
        text,
        '''        self.allow_delete_var = tk.BooleanVar(value=False)
        self.allow_verify_var = tk.BooleanVar(value=True)
        self.auto_backup_var = tk.BooleanVar(value=True)
''',
        '''        self.allow_delete_var = tk.BooleanVar(value=False)
        self.allow_verify_var = tk.BooleanVar(value=True)
        self.allow_guard_p1_var = tk.BooleanVar(value=True)
        self.auto_backup_var = tk.BooleanVar(value=True)
''',
        "ui guard variable",
    )

    text = replace_once(
        text,
        '''        verify_check.grid(
            row=0, column=2, columnspan=2, sticky="w", pady=(0, 2)
        )

        # Компактные визуальные настройки вынесены в отдельный блок справа.
''',
        '''        verify_check.grid(
            row=0, column=2, sticky="w", padx=(0, 12), pady=(0, 2)
        )

        guard_p1_check = ttk.Checkbutton(
            security,
            text="GUARD P1",
            variable=self.allow_guard_p1_var,
        )
        guard_p1_check.grid(
            row=0, column=3, sticky="w", pady=(0, 2)
        )

        # Компактные визуальные настройки вынесены в отдельный блок справа.
''',
        "ui guard checkbox",
    )

    text = replace_once(
        text,
        '''                delete_check,
                verify_check,
                tool_limit_spin,
''',
        '''                delete_check,
                verify_check,
                guard_p1_check,
                tool_limit_spin,
''',
        "ui guard security widgets",
    )

    text = replace_once(
        text,
        '''                "Интерфейс готов. По умолчанию чтение и VERIFY разрешены, запись "
                "и удаление ЗАПРЕЩЕНЫ, автобэкап включён. Лимит tools = 20. "
                "Серверные галочки — это реальные ограничения, а не только "
                "текст в промпте."
''',
        '''                "Интерфейс готов. По умолчанию чтение, VERIFY и GUARD P1 "
                "разрешены, запись и удаление ЗАПРЕЩЕНЫ, автобэкап включён. "
                "Лимит tools = 20. Серверные галочки — это реальные ограничения, "
                "а не только текст в промпте."
''',
        "ui startup message",
    )

    text = replace_once(
        text,
        '''                f"V={perms.get('allow_verify')} | "
                f"LIMIT={perms.get('tool_limit')} | "
''',
        '''                f"V={perms.get('allow_verify')} | "
                f"G1={perms.get('allow_guard_p1')} | "
                f"LIMIT={perms.get('tool_limit')} | "
''',
        "ui run start guard trace",
    )

    text = replace_once(
        text,
        '''        if event_type == "verification_required":
''',
        '''        if event_type == "guard_intervention":
            kind = event.get("kind")
            if kind == "repeated_tool":
                return (
                    f"[{time_str}] GUARD P1 | SUPERVISOR CHECK | "
                    f"REPEAT {event.get('function')} | "
                    f"budget={event.get('tool_budget_used')}/"
                    f"{event.get('tool_budget_limit')}"
                )
            if kind == "possible_duplicate_create":
                return (
                    f"[{time_str}] GUARD P1 | SUPERVISOR CHECK | CREATE | "
                    f"{event.get('requested_path')} ~ "
                    f"{event.get('similar_path')} | "
                    f"score={event.get('score')}"
                )
            return (
                f"[{time_str}] GUARD P1 | SUPERVISOR CHECK | {kind}"
            )

        if event_type == "guard_override":
            return (
                f"[{time_str}] GUARD P1 | CREATE CONFIRMED | "
                f"{event.get('requested_path')}"
            )

        if event_type == "guard_blocked":
            return (
                f"[{time_str}] GUARD P1 | BLOCKED | "
                f"{event.get('kind')} | "
                f"{event.get('function', '')}"
            )

        if event_type == "verification_required":
''',
        "ui guard event formatting",
    )

    text = replace_once(
        text,
        '''            "allow_delete": self.allow_delete_var.get(),
            "allow_verify": self.allow_verify_var.get(),
            "read_scope": read_scope,
''',
        '''            "allow_delete": self.allow_delete_var.get(),
            "allow_verify": self.allow_verify_var.get(),
            "allow_guard_p1": self.allow_guard_p1_var.get(),
            "read_scope": read_scope,
''',
        "ui permissions guard",
    )

    text = replace_once(
        text,
        '''                f"VERIFY={'ON' if permissions['allow_verify'] else 'OFF'}, "
                f"TOOLS={tool_limit}."
''',
        '''                f"VERIFY={'ON' if permissions['allow_verify'] else 'OFF'}, "
                f"GUARD_P1={'ON' if permissions['allow_guard_p1'] else 'OFF'}, "
                f"TOOLS={tool_limit}."
''',
        "ui chat guard status",
    )

    return text


def main() -> int:
    if not SERVER.is_file() or not UI.is_file():
        print(
            "ОШИБКА: положи apply_guard_p1.py в корень ag_llm рядом "
            "с server.py и ultra_ui.py.",
            file=sys.stderr,
        )
        return 2

    server_old = SERVER.read_text(encoding="utf-8")
    ui_old = UI.read_text(encoding="utf-8")

    server_has = "GUARD_P1_VERSION = 1" in server_old
    ui_has = "self.allow_guard_p1_var" in ui_old

    if server_has and ui_has:
        print("GUARD P1 уже применён. Ничего не изменено.")
        return 0

    if server_has != ui_has:
        print(
            "ОШИБКА: обнаружено частично применённое изменение GUARD P1. "
            "Скрипт отказался продолжать.",
            file=sys.stderr,
        )
        return 3

    try:
        server_new = patch_server(server_old)
        ui_new = patch_ui(ui_old)

        # До записи на диск обе новые версии проверяются compile() в памяти.
        compile(server_new, str(SERVER), "exec")
        compile(ui_new, str(UI), "exec")
    except Exception as exc:
        print(
            f"ОШИБКА ПОДГОТОВКИ PATCH: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        print(
            "server.py и ultra_ui.py НЕ изменены.",
            file=sys.stderr,
        )
        return 4

    atomic_write(SERVER, server_new)
    atomic_write(UI, ui_new)

    print("GUARD P1 применён успешно.")
    print("Изменены только:")
    print("  - server.py")
    print("  - ultra_ui.py")
    print()
    print("Добавлено:")
    print("  - GUARD P1 checkbox рядом с VERIFY; default ON")
    print("  - SUPERVISOR CHECK на 3-й одинаковый read/list")
    print("  - hard stop после двух проигнорированных repeat-check")
    print("  - CREATE GUARD до фактического создания нового target")
    print("  - prefix/suffix 1–2 цифры + окончания 1–2 chars + fuzzy")
    print("  - усиление, если похожий файл уже использовался в RUN")
    print("  - первый suspicious CREATE спрашивает; повтор разрешает")
    print("  - guard intervention не списывает tool budget")
    print("  - реальный runtime_log_path в TOOL LIMIT error")
    print("  - Last status/result в TOOL LIMIT diagnostics")
    print()
    print("ТРЕБУЕТСЯ ПОЛНЫЙ RESTART ULTRA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
