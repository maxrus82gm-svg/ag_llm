import json

from provider_accounting import (
    build_provider_attempt_started,
    build_provider_attempt_terminal,
    measure_json_block,
    measure_text_block,
)


def test_request_accounting_measures_blocks_hashes_and_no_raw_content():
    secret = "RAW TASK\nПривет"
    body = {
        "model": "provider-model",
        "messages": [{"role": "user", "content": secret}],
        "stream": False,
    }
    blocks = [
        measure_text_block("raw_task", secret, source_ref="raw_task:tb_1"),
        measure_json_block("tools", [{"name": "read_file"}], source_ref="tool_schema"),
    ]
    started = build_provider_attempt_started(
        role="executor",
        mode="stage",
        provider="gigachat",
        model_id="m",
        provider_model_id="provider-model",
        body=body,
        blocks=blocks,
    )
    assert started["provider_attempt_id"].startswith("pa_")
    assert started["logical_call_id"].startswith("lc_executor_stage_")
    assert started["context_chars"] == sum(item["chars"] for item in blocks)
    assert started["context_utf8_bytes"] >= started["context_chars"]
    assert started["request_snapshot_sha256"]
    assert started["source_references"] == ["raw_task:tb_1", "tool_schema"]
    serialized = json.dumps(started, ensure_ascii=False)
    assert secret not in serialized
    assert started["request_token_estimate"] > 0


def test_terminal_accounting_preserves_unknown_usage_and_outcome():
    started = build_provider_attempt_started(
        role="dredd",
        mode="FINAL",
        provider="gigachat",
        model_id="m",
        provider_model_id="pm",
        body={"model": "pm", "messages": []},
        blocks=[],
    )
    terminal = build_provider_attempt_terminal(
        started,
        outcome="timeout",
        provider_usage=None,
        duration=1.25,
        error_type="ReadTimeout",
    )
    assert terminal["provider_usage"] is None
    assert terminal["outcome"] == "timeout"
    assert terminal["duration"] == 1.25
    assert terminal["provider_attempt_id"] == started["provider_attempt_id"]


def test_terminal_omits_non_numeric_http_status():
    started = build_provider_attempt_started(
        role="executor",
        mode="test",
        provider="gigachat",
        model_id="m",
        provider_model_id="pm",
        body={"model": "pm", "messages": []},
        blocks=[],
    )
    terminal = build_provider_attempt_terminal(
        started,
        outcome="completed",
        provider_usage=None,
        duration=0.1,
        http_status=object(),
    )
    assert "http_status" not in terminal

    terminal_ok = build_provider_attempt_terminal(
        started,
        outcome="completed",
        provider_usage=None,
        duration=0.1,
        http_status=200,
    )
    assert terminal_ok["http_status"] == 200
