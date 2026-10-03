from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from agent_global_context import APP_DATA_ROOT
from gigachat_transport import CHAT_URL, extract_usage, get_access_token
from model_registry import get_model_spec
from provider_accounting import (
    build_provider_attempt_started,
    build_provider_attempt_terminal,
    measure_json_block,
    measure_text_block,
)


DEFAULT_VERIFIER_MODEL_ID = "gigachat_3_pro"
VERIFIER_TEMPERATURE = 0.0
VERIFIER_MAX_TOKENS = 2048
VERIFIER_TIMEOUT_SECONDS = 60.0
VERIFIER_LOG_ROOT = (APP_DATA_ROOT / "verifier_logs").resolve()

ALLOWED_CHECK_TYPES = frozenset({"PREFLIGHT", "MUTATION", "FINAL", "CONSISTENCY", "PERMISSION"})
ALLOWED_VERDICTS = frozenset({"PASS", "FAIL"})


class VerifierRuntimeError(RuntimeError):
    pass


class VerifierProtocolError(VerifierRuntimeError):
    pass


def _provider_call_error(message: str, outcome: str) -> VerifierRuntimeError:
    error = VerifierRuntimeError(message)
    error.provider_outcome = outcome
    return error


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
    route: str = "UNKNOWN"
    affected_stage_ids: tuple[str, ...] = ()
    usage: dict | None = None


@dataclass(frozen=True)
class PlannerReviewResult:
    diagnosis: str
    required_action: str
    verifier_run_id: str
    model_id: str
    model_display_name: str
    provider_model_id: str
    usage: dict | None = None


def _validate_nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} должен быть непустой строкой.")
    return value


def _validate_check_type(check_type: object) -> str:
    if not isinstance(check_type, str) or check_type not in ALLOWED_CHECK_TYPES:
        raise ValueError(
            "check_type должен быть одним из: PREFLIGHT, MUTATION, FINAL, CONSISTENCY, PERMISSION."
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
        "object and no prose or markdown fence. The object must contain "
        "these required semantic fields: result, check_type, violations, reason, "
        "required_action. result must be PASS or FAIL. check_type must equal the "
        "requested check type. violations must be an array of strings. reason "
        "and required_action must be strings. PASS means the supplied evidence "
        "satisfies this check; FAIL means it does not."
    )
    if check_type == "FINAL":
        system_prompt += (
            " FINAL protocol extension: also return route and affected_stage_ids. "
            "route is NONE for PASS; for FAIL it is EXECUTION_DEFECT, PLAN_DEFECT or UNKNOWN. "
            "Use PLAN_DEFECT when RAW TASK requires an outcome missing from task_plan, "
            "the plan targets the wrong artifact, or authoritative facts invalidate the plan. "
            "Use EXECUTION_DEFECT when the plan is adequate but execution/result is defective. "
            "affected_stage_ids lists existing stage IDs requiring repair, or [] if unknown. "
            "Do not create or rewrite plans. Put the finding in reason/violations/required_action. "
            "Server determines routing; no hidden Planner reasoning is supplied. "
            " HARD EVIDENCE RULE: Authoritative server-observed RUN facts override the "
            "Candidate Final Response, which is only a claim. Return FAIL if the Candidate "
            "claims current-RUN tool calls, mutations, file writes/deletes, verification, "
            "readback, or Git checks that authoritative evidence does not show. In particular, "
            "tool_call_count=0 cannot corroborate a claim that named tools ran. "
            "write_revision=0 together with empty RUN-owned mutation state and empty "
            "server-observed mutation facts cannot corroborate a claim that this RUN "
            "physically changed the workspace. Use observed_executor_tools and "
            "candidate_fact_conflicts in the context. For Planner-enabled RUNs, "
            "task_plan + requirement_coverage + evidence_freshness define "
            "the mechanically checked task packet. If requirement_coverage.complete is "
            "false, the Server should have blocked before this call; never infer missing "
            "evidence. task_scope.paths is the intentional Git/material scope and "
            "task_scope.unattributed_git_status is a negative fact that must not be "
            "silently ignored. authoritative_tool_evidence may contain bounded "
            "material_preview fields; task_material reports their budget, truncation and "
            "deduplication. Treat supplied material as evidence, but never infer omitted "
            "or truncated content. Do not require workspace-wide Git state when task_scope "
            "is task_scoped_v1. Git status/diff may include external or pre-existing "
            "changes and cannot establish RUN ownership alone. Zero tools or zero writes "
            "by themselves are not a failure; a truthful read-only or explanatory answer "
            "may PASS. A direct Candidate-versus-Server contradiction must FAIL with the "
            "conflict in reason, violations, and required_action."
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
    if check_type == "PERMISSION":
        system_prompt += (
            " Decide only whether the disabled WRITE or DELETE capability is genuinely "
            "necessary to complete the original RAW TASK using the bounded server-observed "
            "facts. PASS means escalation is justified; FAIL means the task can be completed "
            "without it or the evidence is insufficient. Denied calls did not execute. "
            "Executor claims are not evidence. Never authorize a permission, widen a scope, "
            "or treat a requested path outside scope as permission to change scope."
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


async def _request_gigachat(body: dict[str, Any]) -> tuple[str, dict]:
    try:
        token = await get_access_token()
    except Exception as exc:
        raise _provider_call_error(
            "Не удалось получить GigaChat access token.",
            "transport_error",
        ) from exc

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=VERIFIER_TIMEOUT_SECONDS) as client:
            response = await client.post(CHAT_URL, headers=headers, json=body)
            response.raise_for_status()
    except asyncio.CancelledError:
        raise
    except httpx.TimeoutException as exc:
        raise _provider_call_error(
            "Таймаут HTTP-запроса Verifier к GigaChat.",
            "timeout",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise _provider_call_error(
            "Provider отклонил HTTP-запрос Verifier.",
            "provider_error",
        ) from exc
    except httpx.HTTPError as exc:
        raise _provider_call_error(
            "Транспортная ошибка HTTP-запроса Verifier к GigaChat.",
            "transport_error",
        ) from exc
    except Exception as exc:
        raise _provider_call_error(
            "Ошибка HTTP-запроса Verifier к GigaChat.",
            "transport_error",
        ) from exc

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
    return content, extract_usage(data)


def _content_and_usage(result: object) -> tuple[str, dict]:
    """Keep tests/custom callers that mock the old internal string result working."""
    if isinstance(result, tuple) and len(result) == 2:
        return result[0], result[1]
    return result, extract_usage(None)


def _provider_message_blocks(messages: list[dict], prefix: str) -> list[dict]:
    blocks = []
    for index, message in enumerate(messages):
        content = message.get("content")
        if not isinstance(content, str):
            content = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        role = str(message.get("role") or "unknown")
        blocks.append(
            measure_text_block(
                f"message_{index}_{role}",
                content,
                source_ref=f"{prefix}:message:{index}:{role}",
                kind="provider_message",
            )
        )
    return blocks


def _notify_provider_accounting(callback, event_name: str, payload: dict) -> None:
    if callback is None:
        return
    try:
        callback(event_name, payload)
    except Exception:
        pass


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
    if "route" in payload or "affected_stage_ids" in payload:
        if requested_check_type != "FINAL":
            raise VerifierProtocolError("Routing fields are FINAL-only")
        route = payload.get("route", "UNKNOWN")
        allowed_routes = {"NONE"} if verdict == "PASS" else {"EXECUTION_DEFECT", "PLAN_DEFECT", "UNKNOWN"}
        if not isinstance(route, str) or route not in allowed_routes:
            raise VerifierProtocolError("Invalid FINAL route")
        stages = payload.get("affected_stage_ids", [])
        if not isinstance(stages, list) or len(stages) > 8 or any(
            not isinstance(s, str) or not s or len(s) > 80 for s in stages
        ):
            raise VerifierProtocolError("Invalid affected_stage_ids")
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
    diagnostic_callback=None,
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
        provider_started = build_provider_attempt_started(
            role="dredd",
            mode=check_type,
            provider=model.provider,
            model_id=model.model_id,
            provider_model_id=model.provider_model_id,
            body=body,
            blocks=_provider_message_blocks(
                body["messages"], f"dredd:{check_type.lower()}"
            ),
            source_references=[
                f"raw_task:{task_id or 'direct'}",
                f"verification_context:{check_type}",
            ],
        )
        provider_started_at = time.time()
        provider_usage = None
        provider_terminal_emitted = False

        def finish_provider_attempt(outcome: str, error_type: str | None = None) -> None:
            nonlocal provider_terminal_emitted
            if provider_terminal_emitted:
                return
            provider_terminal_emitted = True
            _notify_provider_accounting(
                diagnostic_callback,
                "provider_attempt_terminal",
                build_provider_attempt_terminal(
                    provider_started,
                    outcome=outcome,
                    provider_usage=provider_usage,
                    duration=max(time.time() - provider_started_at, 0.0),
                    error_type=error_type,
                ),
            )

        _notify_provider_accounting(
            diagnostic_callback, "provider_attempt_started", provider_started
        )
        try:
            content, provider_usage = _content_and_usage(
                await _request_gigachat(body)
            )
        except asyncio.CancelledError:
            finish_provider_attempt("cancelled", "CancelledError")
            raise
        except VerifierProtocolError as exc:
            finish_provider_attempt("parse_error", type(exc).__name__)
            raise
        except VerifierRuntimeError as exc:
            finish_provider_attempt(
                getattr(exc, "provider_outcome", "transport_error"),
                type(exc).__name__,
            )
            raise
        except Exception as exc:
            finish_provider_attempt("transport_error", type(exc).__name__)
            raise VerifierRuntimeError("Verifier model call завершился ошибкой.") from exc
        try:
            payload = _parse_verifier_response(content, check_type)
        except VerifierProtocolError as exc:
            finish_provider_attempt("parse_error", type(exc).__name__)
            raise
        finish_provider_attempt("completed")

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
            route=payload.get("route", "NONE" if payload["result"] == "PASS" else "UNKNOWN"),
            affected_stage_ids=tuple(payload.get("affected_stage_ids", [])),
            usage=provider_usage,
        )
        _write_log_event(
            verifier_run_id,
            {
                "event": "verifier_run_finished",
                **metadata,
                "duration": time.time() - started_at,
                "verdict": result.verdict,
                "violations_count": len(result.violations),
                "usage": provider_usage,
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


async def run_planner_dredd_review(
    *, verifier_model_id: str = DEFAULT_VERIFIER_MODEL_ID,
    raw_task: str, planner_session_transcript: list[dict], mode: str,
    validation_error: str, task_block_id: str | None,
    diagnostic_callback=None,
) -> PlannerReviewResult:
    raw_task = _validate_nonempty_text(raw_task, "raw_task")
    validation_error = _validate_nonempty_text(validation_error, "validation_error")
    if mode not in {"INITIAL", "READINESS", "REPLAN"}:
        raise ValueError("Invalid Planner review mode")
    if not isinstance(planner_session_transcript, list):
        raise ValueError("planner_session_transcript must be a list")
    verifier_run_id = _new_verifier_run_id()
    try:
        transcript = json.dumps(planner_session_transcript, ensure_ascii=False)
        transcript_bytes = len(transcript.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ValueError("planner_session_transcript must be JSON serializable") from exc

    started_at = time.time()
    usage = None
    metadata = {
        "model_id": str(verifier_model_id),
        "mode": mode,
        "task_block_id": task_block_id,
        "transcript_chars": len(transcript),
        "transcript_bytes": transcript_bytes,
        "validation_error_chars": len(validation_error),
    }
    _write_log_event(verifier_run_id, {"event": "planner_review_started", **metadata})
    try:
        if transcript_bytes > 128 * 1024:
            raise VerifierRuntimeError("Planner review transcript exceeds bounded limit")
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
        metadata.update({
            "model_id": model.model_id,
            "model_display_name": model.display_name,
            "provider_model_id": model.provider_model_id,
        })
        system = (
            "You are Judge Dredd reviewing a failed Planner conversation. "
            "You do not execute the user task and do not create a plan yourself. "
            "Inspect RAW TASK, the complete supplied Planner Session transcript, "
            "and the latest deterministic server validation error. "
            "Explain exactly what the Planner must correct on its final retry. "
            "Treat server validation errors as authoritative. Return exactly one JSON object: "
            '{"diagnosis":"...","required_action":"..."}. No prose outside JSON. '
            "Do not invent files, tools or facts."
        )
        user = json.dumps({
            "raw_task": raw_task, "mode": mode,
            "validation_error": validation_error,
            "planner_session_transcript": planner_session_transcript,
            "task_block_id": task_block_id,
        }, ensure_ascii=False)
        body = {
            "model": model.provider_model_id,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": VERIFIER_TEMPERATURE,
            "max_tokens": VERIFIER_MAX_TOKENS,
            "stream": False,
        }
        provider_started = build_provider_attempt_started(
            role="dredd",
            mode=f"PLANNER_REVIEW:{mode}",
            provider=model.provider,
            model_id=model.model_id,
            provider_model_id=model.provider_model_id,
            body=body,
            blocks=_provider_message_blocks(
                body["messages"], f"dredd:planner_review:{mode.lower()}"
            ),
            source_references=[
                f"raw_task:{task_block_id or 'direct'}",
                f"planner_session_transcript:{mode}",
                "planner_validation_error",
            ],
        )
        provider_started_at = time.time()
        provider_terminal_emitted = False

        def finish_provider_attempt(outcome: str, error_type: str | None = None) -> None:
            nonlocal provider_terminal_emitted
            if provider_terminal_emitted:
                return
            provider_terminal_emitted = True
            _notify_provider_accounting(
                diagnostic_callback,
                "provider_attempt_terminal",
                build_provider_attempt_terminal(
                    provider_started,
                    outcome=outcome,
                    provider_usage=usage,
                    duration=max(time.time() - provider_started_at, 0.0),
                    error_type=error_type,
                ),
            )

        _notify_provider_accounting(
            diagnostic_callback, "provider_attempt_started", provider_started
        )
        try:
            content, usage = _content_and_usage(await _request_gigachat(body))
        except asyncio.CancelledError:
            finish_provider_attempt("cancelled", "CancelledError")
            raise
        except VerifierProtocolError as exc:
            finish_provider_attempt("parse_error", type(exc).__name__)
            raise
        except VerifierRuntimeError as exc:
            finish_provider_attempt(
                getattr(exc, "provider_outcome", "transport_error"),
                type(exc).__name__,
            )
            raise
        except Exception as exc:
            finish_provider_attempt("transport_error", type(exc).__name__)
            raise
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict) or set(payload) != {"diagnosis", "required_action"}:
                raise VerifierProtocolError(
                    "Planner Dredd review must contain diagnosis and required_action only."
                )
            diagnosis = _validate_nonempty_text(payload["diagnosis"], "diagnosis")
            required_action = _validate_nonempty_text(payload["required_action"], "required_action")
        except (json.JSONDecodeError, VerifierProtocolError, ValueError) as exc:
            finish_provider_attempt("parse_error", type(exc).__name__)
            if isinstance(exc, json.JSONDecodeError):
                raise VerifierProtocolError(
                    "Planner Dredd review returned malformed JSON."
                ) from exc
            raise
        finish_provider_attempt("completed")
        result = PlannerReviewResult(
            diagnosis=diagnosis, required_action=required_action,
            verifier_run_id=verifier_run_id, model_id=model.model_id,
            model_display_name=model.display_name,
            provider_model_id=model.provider_model_id,
            usage=usage,
        )
        _write_log_event(verifier_run_id, {
            "event": "planner_review_finished", **metadata,
            "duration": time.time() - started_at, "usage": usage,
        })
        return result
    except Exception as exc:
        _write_log_event(verifier_run_id, {
            "event": "planner_review_failed", **metadata,
            "duration": time.time() - started_at,
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:1000],
            "usage": usage,
        })
        raise
