import tempfile
from pathlib import Path
from unittest.mock import patch

import audit_storage
import ui_state
import ultra_ui


def test_executor_diagnostics_are_stored_without_truncation(
    tmp_path: Path,
):
    recorder = audit_storage.AuditThreadRecorder(
        tmp_path,
        "ws_test",
        "chat_test",
        "run_test",
    )

    long_content = "X" * 5000

    messages = [
        {
            "role": "assistant",
            "content": "",
            "function_call": {
                "name": "write_file",
                "arguments": {
                    "path": "probe.md",
                    "content": long_content,
                },
            },
        },
        {
            "role": "function",
            "name": "write_file",
            "content": long_content,
        },
    ]

    recorder.observe(
        {
            "event": "executor_diagnostic_context",
            "api_request_number": 3,
            "plan_id": "plan_test",
            "plan_version": 1,
            "stage_id": "stage_1",
            "model_id": "gigachat_ultra",
            "provider_model_id": "GigaChat-3-Ultra",
            "function_call_mode": "auto",
            "message_count": len(messages),
            "messages": messages,
        }
    )

    recorder.observe(
        {
            "event": "executor_diagnostic_reset",
            "plan_id": "plan_test",
            "plan_version": 1,
            "stage_id": "stage_2",
            "messages_before": 12,
            "messages_after": 5,
            "removed_messages": 7,
            "removed_function_messages": [
                "write_file",
                "read_file",
            ],
            "removed_assistant_function_calls": [
                "write_file",
                "read_file",
            ],
        }
    )

    response_message = {
        "content": "FINAL",
        "function_call": None,
    }

    recorder.observe(
        {
            "event": "executor_diagnostic_response",
            "api_request_number": 7,
            "plan_id": "plan_test",
            "plan_version": 1,
            "stage_id": "stage_3",
            "finish_reason": "stop",
            "message": response_message,
        }
    )

    loaded = audit_storage.load_audit_thread(
        tmp_path,
        "ws_test",
        "chat_test",
        "run_test",
    )

    diagnostics = loaded["executor_diagnostics"]

    assert diagnostics[0]["kind"] == "context"
    assert diagnostics[0]["messages"] == messages

    stored_content = diagnostics[0]["messages"][0][
        "function_call"
    ]["arguments"]["content"]

    assert stored_content == long_content
    assert len(stored_content) == 5000

    assert diagnostics[1]["kind"] == "reset"
    assert diagnostics[1][
        "removed_function_messages"
    ] == [
        "write_file",
        "read_file",
    ]

    assert diagnostics[2]["kind"] == "response"
    assert diagnostics[2]["message"] == response_message


def test_executor_diagnostics_render_and_filter():
    thread = {
        "run_status": "SUCCESS",
        "final_audit": "PASS",
        "issues": [],
        "executor_diagnostics": [
            {
                "kind": "context",
                "api_request_number": 7,
                "plan_id": "plan_test",
                "plan_version": 1,
                "stage_id": "stage_3",
                "model_id": "gigachat_ultra",
                "provider_model_id": "GigaChat-3-Ultra",
                "function_call_mode": "auto",
                "message_count": 2,
                "messages": [
                    {
                        "role": "function",
                        "name": "write_file",
                        "content": "OK",
                    }
                ],
            },
            {
                "kind": "reset",
                "plan_id": "plan_test",
                "plan_version": 1,
                "stage_id": "stage_3",
                "messages_before": 10,
                "messages_after": 4,
                "removed_messages": 6,
                "removed_function_messages": [
                    "write_file",
                    "read_file",
                ],
                "removed_assistant_function_calls": [
                    "write_file",
                    "read_file",
                ],
            },
            {
                "kind": "response",
                "api_request_number": 7,
                "plan_id": "plan_test",
                "plan_version": 1,
                "stage_id": "stage_3",
                "finish_reason": "stop",
                "message": {
                    "content": "FINAL ANSWER",
                },
            },
        ],
    }

    shown = "".join(
        text
        for _tag, text
        in ultra_ui.UltraApp._audit_segments(
            thread,
            "run_test",
        )
    )

    assert "EXECUTOR / API #7 / CONTEXT" in shown
    assert '"name": "write_file"' in shown
    assert "EXECUTOR / CONTEXT RESET" in shown
    assert "write_file, read_file" in shown
    assert "EXECUTOR / API #7 / RAW RESPONSE" in shown
    assert "FINAL ANSWER" in shown

    hidden = "".join(
        text
        for _tag, text
        in ultra_ui.UltraApp._audit_segments(
            thread,
            "run_test",
            executor_filters={
                "context": False,
                "response": False,
                "reset": False,
            },
        )
    )

    assert "EXECUTOR /" not in hidden
    assert "FINAL ANSWER" not in hidden


def test_executor_diagnostic_ui_state_roundtrip():
    expected = {
        "context": True,
        "response": True,
        "reset": True,
    }

    assert (
        ui_state.default_ui_state()[
            "executor_diagnostics"
        ]
        == expected
    )

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "ui_state.json"

        state = ui_state.default_ui_state()
        state["executor_diagnostics"] = {
            "context": False,
            "response": True,
            "reset": False,
        }

        with patch.object(
            ui_state,
            "STATE_PATH",
            path,
        ):
            ui_state.save_ui_state(state)
            loaded = ui_state.load_ui_state()

    assert loaded["executor_diagnostics"] == {
        "context": False,
        "response": True,
        "reset": False,
    }


def test_executor_trace_format_is_compact():
    event = {
        "event": "executor_diagnostic_context",
        "run_id": "run_test",
        "timestamp": 0,
        "api_request_number": 7,
        "stage_id": "stage_3",
        "message_count": 42,
        "messages": [
            {
                "role": "user",
                "content": "DO NOT PRINT THIS HUGE PAYLOAD",
            }
        ],
    }

    line = ultra_ui.UltraApp._format_event(
        object(),
        event,
    )

    assert "EXECUTOR API #7 CONTEXT" in line
    assert "messages=42" in line
    assert "DO NOT PRINT THIS" not in line
