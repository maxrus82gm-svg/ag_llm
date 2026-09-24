from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from agent_global_context import APP_DATA_ROOT
from gigachat_transport import CHAT_URL, get_access_token
from model_registry import get_model_spec


DEFAULT_VERIFIER_MODEL_ID = "gigachat_3_pro"
VERIFIER_TEMPERATURE = 0.0
VERIFIER_MAX_TOKENS = 2048
VERIFIER_TIMEOUT_SECONDS = 60.0
VERIFIER_LOG_ROOT = (APP_DATA_ROOT / "verifier_logs").resolve()

ALLOWED_CHECK_TYPES = frozenset({"PREFLIGHT", "MUTATION", "FINAL", "CONSISTENCY"})
ALLOWED_VERDICTS = frozenset({"PASS", "FAIL"})


class VerifierRuntimeError(RuntimeError):
    pass


class VerifierProtocolError(VerifierRuntimeError):
    pass


@dataclass(frozen=True)
class VerifierResult:
    verdict: str
    check_type: str
    violations: tuple[str, ...]
    reason: str
    required_action: str
    verifier_run_id: str
    model_id: str
    model_display_name: str
    provider: str
    provider_model_id: str
    task_id: str | None
    checkpoint_id: str | None
    operation_id: str | None


def _validate_nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} должен быть непустой строкой.")
    return value


def _validate_check_type(check_type: object) -> str:
    if not isinstance(check_type, str) or check_type not in ALLOWED_CHECK_TYPES:
        raise ValueError(
            "check_type должен быть одним из: PREFLIGHT, MUTATION, FINAL, CONSISTENCY."
        )
    return check_type


def _validate_optional_id(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} должен быть непустой строкой или None.")
    return value


def _new_verifier_run_id() -> str:
    return "ver_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]


def _build_verifier_messages(
    *,
    check_type: str,
    raw_task: str,
    verification_context: str,
) -> list[dict[str, str]]:
    system_prompt = (
        "You are an independent one-shot verifier. Evaluate only the RAW TASK "
        "and VERIFICATION CONTEXT supplied in this request. Do not assume any "
        "chat history, tools, files, or external facts. Return exactly one JSON "
        "object and no prose or markdown fence. The object must contain exactly "
        "these semantic fields: result, check_type, violations, reason, "
        "required_action. result must be PASS or FAIL. check_type must equal the "
        "requested check type. violations must be an array of strings. reason "
        "and required_action must be strings. PASS means the supplied evidence "
        "satisfies this check; FAIL means it does not."
    )
    if check_type == "CONSISTENCY":
        system_prompt += (
            " This is a repeated execution inconsistency: the RAW TASK appears to request "
            "a file or document change, the Executor already received one server self-check, "
            "and after another attempt no physical mutation was observed. Independently "
            "compare the RAW TASK with SERVER FACTS and tool evidence. Treat Executor reports "
            "as claims, never proof. Do not assume mutation is mandatory: the requested state "
            "may already exist, the user may be mistaken, the target may be ambiguous, or a "
            "confirmed blocker may prevent safe action. PASS only when the absence of mutation "
            "is justified by supplied facts; PASS does not approve the overall RUN. FAIL when "
            "the inconsistency remains sufficiently supported and unexcused. For FAIL, give "
            "specific reason, violations, and required_action naming the task, target, missing "
            "evidence/action, and a suitable available tool where possible. RAW TASK is the "
            "source of truth. Do not invent file contents or tool calls."
        )
    user_prompt = (
        f"REQUESTED CHECK TYPE: {check_type}\n\n"
        "===== RAW TASK START =====\n"
        f"{raw_task}\n"
        "===== RAW TASK END =====\n\n"
        "===== VERIFICATION CONTEXT START =====\n"
        f"{verification_context}\n"
        "===== VERIFICATION CONTEXT END ====="
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _build_verifier_request_body(
    *,
    provider_model_id: str,
    check_type: str,
    raw_task: str,
    verification_context: str,
) -> dict[str, Any]:
    return {
        "model": provider_model_id,
        "messages": _build_verifier_messages(
            check_type=check_type,
            raw_task=raw_task,
            verification_context=verification_context,
        ),
        "temperature": VERIFIER_TEMPERATURE,
        "max_tokens": VERIFIER_MAX_TOKENS,
        "stream": False,
    }


async def _request_gigachat(body: dict[str, Any]) -> str:
    try:
        token = await get_access_token()
    except Exception as exc:
        raise VerifierRuntimeError("Не удалось получить GigaChat access token.") from exc

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=VERIFIER_TIMEOUT_SECONDS) as client:
            response = await client.post(CHAT_URL, headers=headers, json=body)
            response.raise_for_status()
    except Exception as exc:
        raise VerifierRuntimeError("Ошибка HTTP-запроса Verifier к GigaChat.") from exc

    try:
        data = response.json()
    except Exception as exc:
        raise VerifierProtocolError(
            "GigaChat вернул невалидный JSON transport response."
        ) from exc

    try:
        choice = data["choices"][0]
        message = choice["message"]
        content = message["content"]
        finish_reason = choice.get("finish_reason")
    except (KeyError, IndexError, TypeError) as exc:
        raise VerifierProtocolError(
            "Неожиданная структура GigaChat response для Verifier."
        ) from exc

    if not isinstance(content, str) or not content.strip():
        raise VerifierProtocolError("Verifier вернул пустой или не-текстовый ответ.")
    if finish_reason and finish_reason not in {"stop", "eos"}:
        raise VerifierProtocolError(
            f"Verifier завершился нештатно: finish_reason={finish_reason!r}."
        )
    return content


def _parse_verifier_response(content: str, requested_check_type: str) -> dict[str, Any]:
    if not isinstance(content, str) or not content.strip():
        raise VerifierProtocolError("Verifier вернул пустой ответ.")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise VerifierProtocolError("Verifier вернул malformed JSON.") from exc
    if not isinstance(payload, dict):
        raise VerifierProtocolError("Verifier response должен быть JSON object.")

    required_fields = {
        "result",
        "check_type",
        "violations",
        "reason",
        "required_action",
    }
    missing = required_fields.difference(payload)
    if missing:
        raise VerifierProtocolError(
            "Verifier response не содержит обязательные поля: "
            + ", ".join(sorted(missing))
            + "."
        )

    verdict = payload["result"]
    if not isinstance(verdict, str) or verdict not in ALLOWED_VERDICTS:
        raise VerifierProtocolError("Verifier result должен быть PASS или FAIL.")
    response_check_type = payload["check_type"]
    if (
        not isinstance(response_check_type, str)
        or response_check_type not in ALLOWED_CHECK_TYPES
    ):
        raise VerifierProtocolError("Verifier response содержит invalid check_type.")
    if response_check_type != requested_check_type:
        raise VerifierProtocolError(
            "Verifier response check_type не совпадает с requested check_type."
        )
    violations = payload["violations"]
    if not isinstance(violations, list) or not all(
        isinstance(item, str) for item in violations
    ):
        raise VerifierProtocolError("Verifier violations должен быть list[str].")
    if not isinstance(payload["reason"], str):
        raise VerifierProtocolError("Verifier reason должен быть строкой.")
    if not isinstance(payload["required_action"], str):
        raise VerifierProtocolError("Verifier required_action должен быть строкой.")
    return payload


def _write_log_event(verifier_run_id: str, event: dict[str, Any]) -> None:
    record = {
        "event": event["event"],
        "verifier_run_id": verifier_run_id,
        "timestamp": time.time(),
        **{key: value for key, value in event.items() if key != "event"},
    }
    try:
        VERIFIER_LOG_ROOT.mkdir(parents=True, exist_ok=True)
        path = VERIFIER_LOG_ROOT / f"{verifier_run_id}.jsonl"
        with path.open("a", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


async def run_verifier_check(
    *,
    verifier_model_id: str = DEFAULT_VERIFIER_MODEL_ID,
    check_type: str,
    raw_task: str,
    verification_context: str,
    task_id: str | None = None,
    checkpoint_id: str | None = None,
    operation_id: str | None = None,
) -> VerifierResult:
    check_type = _validate_check_type(check_type)
    raw_task = _validate_nonempty_text(raw_task, "raw_task")
    verification_context = _validate_nonempty_text(
        verification_context, "verification_context"
    )
    task_id = _validate_optional_id(task_id, "task_id")
    checkpoint_id = _validate_optional_id(checkpoint_id, "checkpoint_id")
    operation_id = _validate_optional_id(operation_id, "operation_id")

    verifier_run_id = _new_verifier_run_id()
    started_at = time.time()
    try:
        try:
            model = get_model_spec(verifier_model_id)
        except (KeyError, RuntimeError, ValueError) as exc:
            raise VerifierRuntimeError(
                f"Verifier model недоступна: {verifier_model_id!r}."
            ) from exc
        if model.provider != "gigachat":
            raise VerifierRuntimeError(
                f"Verifier provider не поддерживается: {model.provider!r}."
            )

        metadata = {
            "model_id": model.model_id,
            "model_display_name": model.display_name,
            "provider": model.provider,
            "provider_model_id": model.provider_model_id,
            "check_type": check_type,
            "task_id": task_id,
            "checkpoint_id": checkpoint_id,
            "operation_id": operation_id,
            "raw_task_chars": len(raw_task),
            "verification_context_chars": len(verification_context),
        }
        _write_log_event(
            verifier_run_id,
            {"event": "verifier_run_started", **metadata},
        )

        body = _build_verifier_request_body(
            provider_model_id=model.provider_model_id,
            check_type=check_type,
            raw_task=raw_task,
            verification_context=verification_context,
        )
        try:
            content = await _request_gigachat(body)
        except VerifierRuntimeError:
            raise
        except Exception as exc:
            raise VerifierRuntimeError("Verifier model call завершился ошибкой.") from exc
        payload = _parse_verifier_response(content, check_type)

        result = VerifierResult(
            verdict=payload["result"],
            check_type=payload["check_type"],
            violations=tuple(payload["violations"]),
            reason=payload["reason"],
            required_action=payload["required_action"],
            verifier_run_id=verifier_run_id,
            model_id=model.model_id,
            model_display_name=model.display_name,
            provider=model.provider,
            provider_model_id=model.provider_model_id,
            task_id=task_id,
            checkpoint_id=checkpoint_id,
            operation_id=operation_id,
        )
        _write_log_event(
            verifier_run_id,
            {
                "event": "verifier_run_finished",
                **metadata,
                "duration": time.time() - started_at,
                "verdict": result.verdict,
                "violations_count": len(result.violations),
            },
        )
        return result
    except Exception as exc:
        _write_log_event(
            verifier_run_id,
            {
                "event": "verifier_run_failed",
                "model_id": str(verifier_model_id),
                "check_type": check_type,
                "task_id": task_id,
                "checkpoint_id": checkpoint_id,
                "operation_id": operation_id,
                "raw_task_chars": len(raw_task),
                "verification_context_chars": len(verification_context),
                "duration": time.time() - started_at,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        if isinstance(exc, VerifierRuntimeError):
            raise
        raise VerifierRuntimeError("Verifier runtime завершился ошибкой.") from exc
