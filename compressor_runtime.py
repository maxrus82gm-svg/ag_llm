from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import httpx

from agent_global_context import APP_DATA_ROOT, load_agent_global_context
from compressor_settings import load_message_compression_template
from context_storage import load_existing_project_context, probe_existing_workspace
from model_registry import get_model_spec
from server import CHAT_URL, MAX_TOKENS, TEMPERATURE, get_access_token


COMPRESSOR_ROLE_ID = "compressor"
DEFAULT_COMPRESSOR_MODEL_ID = "gigachat_3_pro"
DEFAULT_REDUCTION_PERCENT = 50
MIN_REDUCTION_PERCENT = 1
MAX_REDUCTION_PERCENT = 95
MIN_MEANINGFUL_REDUCTION_PERCENT = 5.0
MAX_COMPRESSOR_ATTEMPTS = 2
COMPRESSOR_PROMPT_BLOCK_ORDER = (
    "role_context",
    "project_context",
    "message_template",
    "runtime_target",
    "source_text",
    "final_check",
)
COMPRESSOR_LOG_ROOT = (APP_DATA_ROOT / "compressor_logs").resolve()

GUARD_ACCEPT = "accept"
GUARD_REJECT_EMPTY = "reject_empty"
GUARD_REJECT_UNCHANGED = "reject_unchanged"
GUARD_REJECT_NOT_SHORTER = "reject_not_shorter"
GUARD_REJECT_INSUFFICIENT_REDUCTION = "reject_insufficient_reduction"


class CompressorGuardError(RuntimeError):
    pass


def validate_reduction_percent(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("reduction_percent должен быть целым числом.")
    if not MIN_REDUCTION_PERCENT <= value <= MAX_REDUCTION_PERCENT:
        raise ValueError(
            "reduction_percent должен быть в диапазоне "
            f"{MIN_REDUCTION_PERCENT}..{MAX_REDUCTION_PERCENT}."
        )
    return value


def render_message_compression_template(
    template: str,
    reduction_percent: int,
) -> str:
    if not isinstance(template, str):
        raise TypeError("message_template должен быть строкой.")
    reduction_percent = validate_reduction_percent(reduction_percent)
    remaining_percent = 100 - reduction_percent
    return template.replace(
        "{{REDUCTION_PERCENT}}",
        str(reduction_percent),
    ).replace(
        "{{REMAINING_PERCENT}}",
        str(remaining_percent),
    )


def measure_compression(source_text: str, result_text: str) -> dict[str, Any]:
    source_chars = len(source_text)
    output_chars = len(result_text)
    if source_chars <= 0:
        raise ValueError("SOURCE TEXT не может быть пустым.")
    actual_reduction_percent = (1 - output_chars / source_chars) * 100
    return {
        "source_chars": source_chars,
        "output_chars": output_chars,
        "actual_reduction_percent": actual_reduction_percent,
    }


def evaluate_compression_guard(source_text: str, result_text: str) -> str:
    metrics = measure_compression(source_text, result_text)
    if not result_text.strip():
        return GUARD_REJECT_EMPTY

    normalized_source = " ".join(source_text.split()).casefold()
    normalized_result = " ".join(result_text.split()).casefold()
    if normalized_result == normalized_source:
        return GUARD_REJECT_UNCHANGED
    if metrics["output_chars"] >= metrics["source_chars"]:
        return GUARD_REJECT_NOT_SHORTER
    if (
        metrics["actual_reduction_percent"]
        < MIN_MEANINGFUL_REDUCTION_PERCENT
    ):
        return GUARD_REJECT_INSUFFICIENT_REDUCTION
    return GUARD_ACCEPT


def build_compressor_prompt_blocks(
    *,
    source_text: str,
    role_context: str,
    project_context: str,
    message_template: str,
    reduction_percent: int,
    final_check_enabled: bool,
) -> list[dict[str, str]]:
    reduction_percent = validate_reduction_percent(reduction_percent)
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("SOURCE TEXT не может быть пустым.")
    remaining_percent = 100 - reduction_percent
    rendered_template = render_message_compression_template(
        message_template,
        reduction_percent,
    )

    contents = {
        "role_context": role_context,
        "project_context": (
            "PROJECT CONTEXT is reference material for understanding terms and "
            "the surrounding environment. SOURCE TEXT is the source of truth. "
            "Do not add facts that exist only in PROJECT CONTEXT and are absent "
            "from SOURCE TEXT.\n\n"
            f"{project_context}"
        ),
        "message_template": rendered_template,
        "runtime_target": (
            "The provided SOURCE TEXT is the canonical full RAW original.\n\n"
            f"Requested approximate reduction: {reduction_percent}%\n\n"
            f"Approximate desired remaining size: {remaining_percent}%\n\n"
            "Preserving meaning, facts, constraints, numbers, names, "
            "relationships and important qualifications has higher priority "
            "than hitting the numerical target exactly.\n\n"
            "Do not calculate the percentage from any previous, compressed or "
            "intermediate representation.\n\n"
            "Return only the compressed message text."
        ),
        "source_text": source_text,
        "final_check": (
            "Before returning the result, compare it specifically with the "
            "original full RAW SOURCE TEXT.\n\n"
            "Confirm internally that the result is reasonably compressed "
            f"toward the requested {reduction_percent}% reduction target.\n\n"
            "The original RAW SOURCE TEXT is the only measurement baseline.\n\n"
            "Preservation of meaning has priority over exact percentage.\n\n"
            "Do not print a check report. Return only the compressed text."
        ),
    }

    blocks = []
    for block_id in COMPRESSOR_PROMPT_BLOCK_ORDER:
        if block_id == "final_check" and not final_check_enabled:
            continue
        blocks.append({"id": block_id, "content": contents[block_id]})
    return blocks


def render_compressor_prompt(
    blocks: list[dict[str, str]],
    *,
    corrective_instruction: str | None = None,
) -> str:
    labels = {
        "role_context": "ROLE CONTEXT",
        "project_context": "PROJECT CONTEXT (REFERENCE ONLY)",
        "message_template": "MESSAGE COMPRESSION TEMPLATE",
        "runtime_target": "RUNTIME COMPRESSION TARGET",
        "source_text": "SOURCE TEXT (CANONICAL RAW ORIGINAL)",
        "final_check": "FINAL CHECK",
    }
    parts = []
    for block in blocks:
        block_id = block["id"]
        parts.append(f"===== {labels[block_id]} =====\n{block['content']}")
    if corrective_instruction:
        parts.append(f"===== CORRECTIVE RETRY =====\n{corrective_instruction}")
    return "\n\n".join(parts)


def build_compressor_request_body(model_id: str, prompt: str) -> dict[str, Any]:
    selected_model = get_model_spec(model_id)
    if selected_model.provider != "gigachat":
        raise RuntimeError(
            "COMPRESSOR пока поддерживает только provider='gigachat'."
        )
    return {
        "model": selected_model.provider_model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }


async def _request_gigachat(body: dict[str, Any]) -> str:
    token = await get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(CHAT_URL, headers=headers, json=body)
        response.raise_for_status()
    data = response.json()
    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason")
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Неожиданный ответ GigaChat: {data}") from exc
    if not isinstance(content, str):
        raise RuntimeError(f"GigaChat вернул не-текстовый ответ: {data}")
    if finish_reason and finish_reason not in ("stop", "eos"):
        raise RuntimeError(
            "Ответ GigaChat завершён нештатно. "
            f"finish_reason={finish_reason}."
        )
    return content


async def run_compressor_task(
    source_text: str,
    workspace_root: str | Path,
    *,
    compressor_model_id: str = DEFAULT_COMPRESSOR_MODEL_ID,
    reduction_percent: int = DEFAULT_REDUCTION_PERCENT,
    final_check_enabled: bool = True,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    role_context: str | None = None,
    message_template: str | None = None,
    project_context: str | None = None,
) -> str:
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("SOURCE TEXT не может быть пустым.")
    reduction_percent = validate_reduction_percent(reduction_percent)
    if not isinstance(final_check_enabled, bool):
        raise TypeError("final_check_enabled должен быть bool.")

    selected_model = get_model_spec(compressor_model_id)
    if selected_model.provider != "gigachat":
        raise RuntimeError(
            "COMPRESSOR пока поддерживает только provider='gigachat'."
        )

    workspace_info = probe_existing_workspace(workspace_root)
    if workspace_info.get("status") != "ok":
        raise RuntimeError(
            "COMPRESSOR требует существующий Workspace storage: "
            f"status={workspace_info.get('status')}."
        )
    workspace_id = workspace_info["workspace_id"]
    if role_context is None:
        role_context = load_agent_global_context(COMPRESSOR_ROLE_ID)
    if message_template is None:
        message_template = load_message_compression_template()
    if project_context is None:
        project_context = load_existing_project_context(
            workspace_root,
            expected_workspace_id=workspace_id,
        ) or "# PROJECT CONTEXT\n\nПока не заполнен."

    blocks = build_compressor_prompt_blocks(
        source_text=source_text,
        role_context=role_context,
        project_context=project_context,
        message_template=message_template,
        reduction_percent=reduction_percent,
        final_check_enabled=final_check_enabled,
    )

    run_id = (
        "cmp_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    )
    started_at = time.time()
    log_path = COMPRESSOR_LOG_ROOT / f"{run_id}.jsonl"

    def emit(event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event": event_type,
            "run_id": run_id,
            "timestamp": time.time(),
            **payload,
        }
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass

    emit(
        "compressor_run_started",
        {
            "role_id": COMPRESSOR_ROLE_ID,
            "model_id": selected_model.model_id,
            "model_display_name": selected_model.display_name,
            "provider": selected_model.provider,
            "provider_model_id": selected_model.provider_model_id,
            "workspace_id": workspace_id,
            "target_reduction_percent": reduction_percent,
            "remaining_percent": 100 - reduction_percent,
            "final_check_enabled": final_check_enabled,
        },
    )

    corrective_instruction = None
    last_result = ""
    last_metrics: dict[str, Any] = {
        "source_chars": len(source_text),
        "output_chars": 0,
        "actual_reduction_percent": 100.0,
    }
    last_guard_status = GUARD_REJECT_EMPTY

    for attempt in range(1, MAX_COMPRESSOR_ATTEMPTS + 1):
        prompt = render_compressor_prompt(
            blocks,
            corrective_instruction=corrective_instruction,
        )
        body = build_compressor_request_body(selected_model.model_id, prompt)
        last_result = (await _request_gigachat(body)).strip()
        last_metrics = measure_compression(source_text, last_result)
        last_guard_status = evaluate_compression_guard(source_text, last_result)
        emit(
            "compressor_attempt_finished",
            {
                "attempt": attempt,
                **last_metrics,
                "guard_status": last_guard_status,
            },
        )
        if last_guard_status == GUARD_ACCEPT:
            break

        corrective_instruction = (
            "The previous result did not meaningfully compress the RAW source.\n\n"
            f"Requested target: {reduction_percent}%\n"
            "Observed reduction: "
            f"{last_metrics['actual_reduction_percent']:.2f}%\n\n"
            "Produce an actually compressed version. Meaning preservation "
            "remains more important than hitting the numerical target exactly.\n\n"
            "Return only the result text."
        )

    attempts = attempt
    emit(
        "compressor_run_finished",
        {
            "attempts": attempts,
            **last_metrics,
            "target_reduction_percent": reduction_percent,
            "duration": time.time() - started_at,
            "guard_status": last_guard_status,
        },
    )
    if last_guard_status != GUARD_ACCEPT:
        raise CompressorGuardError(
            "COMPRESSOR не прошёл soft guard после одного corrective retry: "
            f"{last_guard_status}."
        )
    return last_result
