import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from audit_storage import AuditThreadRecorder
from gigachat_transport import extract_usage
from run_store import (
    create_run_summary,
    load_run_summary,
    record_provider_attempt_started,
    record_provider_attempt_terminal,
    record_usage,
    update_run_summary_index,
)
import verifier_runtime


USAGE = {
    "prompt_tokens": 100,
    "completion_tokens": 20,
    "total_tokens": 120,
    "raw": {},
}


def test_extract_and_aggregate_usage(tmp_path: Path):
    usage = extract_usage({
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "cached": 3,
        }
    })
    assert usage["total_tokens"] == 120 and usage["raw"]["cached"] == 3
    assert extract_usage({"choices": []}) == {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "raw": None,
    }
    task = "tb_" + "e" * 32
    summary = create_run_summary(tmp_path, "ws", "chat", task, "run")
    record_usage(summary, "planner", usage)
    record_usage(summary, "executor", None)
    record_usage(
        summary,
        "dredd",
        {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    )
    update_run_summary_index(tmp_path, "run", summary)
    saved = load_run_summary(tmp_path, "run")
    assert saved["usage"]["planner"]["total_tokens"] == 120
    assert saved["usage"]["executor"]["calls"] == 1
    assert saved["usage"]["executor"]["complete"] is False
    assert saved["usage"]["executor"]["total_tokens"] is None
    assert saved["usage"]["total"]["total_tokens"] is None
    assert saved["usage"]["total"]["known_total_tokens"] == 130
    assert saved["usage"]["total"]["complete"] is False


def test_provider_attempt_started_without_terminal_is_incomplete(tmp_path: Path):
    task = "tb_" + "a" * 32
    summary = create_run_summary(tmp_path, "ws", "chat", task, "run")
    record_provider_attempt_started(summary, "planner", "pa_1")
    update_run_summary_index(tmp_path, "run", summary)
    saved = load_run_summary(tmp_path, "run")
    assert saved["provider_accounting"]["complete"] is False
    assert saved["usage"]["planner"]["attempts_started"] == 1
    assert saved["usage"]["planner"]["attempts_terminal"] == 0
    assert saved["usage"]["planner"]["complete"] is False
    assert saved["usage"]["total"]["complete"] is False


def test_unknown_terminal_usage_stays_unknown_not_zero(tmp_path: Path):
    task = "tb_" + "b" * 32
    summary = create_run_summary(tmp_path, "ws", "chat", task, "run")
    record_provider_attempt_started(summary, "dredd", "pa_1")
    record_provider_attempt_terminal(summary, "dredd", "pa_1", None)
    update_run_summary_index(tmp_path, "run", summary)
    saved = load_run_summary(tmp_path, "run")
    assert saved["provider_accounting"]["complete"] is True
    assert saved["usage"]["dredd"]["calls"] == 1
    assert saved["usage"]["dredd"]["unknown_usage_calls"] == 1
    assert saved["usage"]["dredd"]["known_total_tokens"] == 0
    assert saved["usage"]["dredd"]["total_tokens"] is None
    assert saved["usage"]["dredd"]["complete"] is False
    assert saved["usage"]["total"]["total_tokens"] is None


def _started(role: str, attempt_id: str) -> dict:
    return {
        "event": "provider_attempt_started",
        "timestamp": 1,
        "role": role,
        "provider_attempt_id": attempt_id,
        "logical_call_id": "lc_" + attempt_id,
        "mode": "test",
    }


def _terminal(role: str, attempt_id: str, usage=USAGE) -> dict:
    return {
        "event": "provider_attempt_terminal",
        "timestamp": 2,
        "role": role,
        "provider_attempt_id": attempt_id,
        "logical_call_id": "lc_" + attempt_id,
        "mode": "test",
        "outcome": "completed",
        "provider_usage": usage,
    }


def test_recorder_accounts_each_provider_role_and_not_synthetic_dispatch(tmp_path: Path):
    task = "tb_" + "f" * 32
    recorder = AuditThreadRecorder(
        tmp_path, "ws", "chat", "run", task_block_id=task
    )
    for role, attempt_id in (
        ("planner", "pa_p"),
        ("executor", "pa_e"),
        ("dredd", "pa_d"),
    ):
        recorder.observe(_started(role, attempt_id))
        recorder.observe(_terminal(role, attempt_id))
    before = load_run_summary(tmp_path, "run")["usage"]["total"]["calls"]
    recorder.observe({"event": "persistence_dispatch", "timestamp": 4})
    saved = load_run_summary(tmp_path, "run")
    usage = saved["usage"]
    assert [usage[r]["calls"] for r in ("planner", "executor", "dredd")] == [1, 1, 1]
    assert usage["total"]["calls"] == before == 3
    assert usage["total"]["total_tokens"] == 360
    assert saved["provider_accounting"]["complete"] is True


def test_duplicate_terminal_marks_accounting_incomplete_without_double_count(tmp_path: Path):
    task = "tb_" + "d" * 32
    recorder = AuditThreadRecorder(
        tmp_path, "ws", "chat", "run", task_block_id=task
    )
    recorder.observe(_started("executor", "pa_x"))
    recorder.observe(_terminal("executor", "pa_x"))
    recorder.observe(_terminal("executor", "pa_x"))
    saved = load_run_summary(tmp_path, "run")
    assert saved["usage"]["executor"]["calls"] == 1
    assert saved["provider_accounting"]["duplicate_terminal_ids"] == ["pa_x"]
    assert saved["provider_accounting"]["complete"] is False
    assert saved["usage"]["total"]["complete"] is False


def test_verifier_result_preserves_provider_usage(tmp_path: Path):
    content = json.dumps({
        "result": "PASS",
        "check_type": "FINAL",
        "violations": [],
        "reason": "ok",
        "required_action": "none",
    })

    async def run():
        with (
            patch.object(verifier_runtime, "VERIFIER_LOG_ROOT", tmp_path / "logs"),
            patch.object(
                verifier_runtime,
                "_request_gigachat",
                AsyncMock(return_value=(content, USAGE)),
            ),
        ):
            return await verifier_runtime.run_verifier_check(
                verifier_model_id=verifier_runtime.DEFAULT_VERIFIER_MODEL_ID,
                check_type="FINAL",
                raw_task="task",
                verification_context="evidence",
            )

    result = asyncio.run(run())
    assert result.usage["total_tokens"] == 120
