from __future__ import annotations

import hashlib
import json
import math
import uuid
from typing import Any, Iterable


PROVIDER_ACCOUNTING_SCHEMA_VERSION = 1
TOKEN_ESTIMATE_METHOD = "utf8_bytes_div_4_v1"
TERMINAL_OUTCOMES = frozenset({
    "completed",
    "provider_error",
    "timeout",
    "transport_error",
    "parse_error",
    "cancelled",
})


def new_logical_call_id(role: str, mode: str) -> str:
    safe_role = str(role or "unknown").strip().lower().replace(" ", "_")
    safe_mode = str(mode or "default").strip().lower().replace(" ", "_")
    return f"lc_{safe_role}_{safe_mode}_{uuid.uuid4().hex}"


def new_provider_attempt_id() -> str:
    return "pa_" + uuid.uuid4().hex


def canonical_json_text(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _token_estimate(utf8_bytes: int) -> int:
    if utf8_bytes <= 0:
        return 0
    return int(math.ceil(utf8_bytes / 4.0))


def measure_text_block(
    name: str,
    text: str,
    *,
    source_ref: str | None = None,
    kind: str = "text",
) -> dict:
    if not isinstance(text, str):
        raise TypeError("text block must be a string")
    encoded = text.encode("utf-8")
    result = {
        "name": str(name),
        "kind": str(kind),
        "chars": len(text),
        "utf8_bytes": len(encoded),
        "token_estimate": _token_estimate(len(encoded)),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }
    if source_ref:
        result["source_ref"] = str(source_ref)
    return result


def measure_json_block(
    name: str,
    value: Any,
    *,
    source_ref: str | None = None,
    kind: str = "json",
) -> dict:
    return measure_text_block(
        name,
        canonical_json_text(value),
        source_ref=source_ref,
        kind=kind,
    )


def build_provider_attempt_started(
    *,
    role: str,
    mode: str,
    provider: str,
    model_id: str,
    provider_model_id: str,
    body: dict,
    blocks: Iterable[dict],
    logical_call_id: str | None = None,
    provider_attempt_id: str | None = None,
    source_references: Iterable[str] = (),
) -> dict:
    logical_call_id = logical_call_id or new_logical_call_id(role, mode)
    provider_attempt_id = provider_attempt_id or new_provider_attempt_id()
    snapshot = canonical_json_text(body)
    snapshot_bytes = snapshot.encode("utf-8")
    block_list = [dict(item) for item in blocks]
    refs = [str(item) for item in source_references if str(item).strip()]
    for block in block_list:
        ref = block.get("source_ref")
        if isinstance(ref, str) and ref and ref not in refs:
            refs.append(ref)
    return {
        "provider_accounting_schema_version": PROVIDER_ACCOUNTING_SCHEMA_VERSION,
        "provider_attempt_id": provider_attempt_id,
        "logical_call_id": logical_call_id,
        "role": str(role).lower(),
        "mode": str(mode),
        "provider": str(provider),
        "model_id": str(model_id),
        "provider_model_id": str(provider_model_id),
        "request_context_schema_version": 1,
        "request_blocks": block_list,
        "source_references": refs,
        "context_chars": sum(int(item.get("chars") or 0) for item in block_list),
        "context_utf8_bytes": sum(int(item.get("utf8_bytes") or 0) for item in block_list),
        "context_token_estimate": sum(int(item.get("token_estimate") or 0) for item in block_list),
        "token_estimate_method": TOKEN_ESTIMATE_METHOD,
        "request_chars": len(snapshot),
        "request_utf8_bytes": len(snapshot_bytes),
        "request_token_estimate": _token_estimate(len(snapshot_bytes)),
        "request_snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
    }


def build_provider_attempt_terminal(
    started: dict,
    *,
    outcome: str,
    provider_usage: dict | None,
    duration: float,
    http_status: int | None = None,
    error_type: str | None = None,
) -> dict:
    if outcome not in TERMINAL_OUTCOMES:
        raise ValueError(f"Unsupported provider terminal outcome: {outcome}")
    payload = {
        "provider_accounting_schema_version": started[
            "provider_accounting_schema_version"
        ],
        "provider_attempt_id": started["provider_attempt_id"],
        "logical_call_id": started["logical_call_id"],
        "role": started["role"],
        "mode": started["mode"],
        "provider": started["provider"],
        "model_id": started["model_id"],
        "provider_model_id": started["provider_model_id"],
        "outcome": outcome,
        "duration": float(duration),
        "provider_usage": provider_usage,
    }
    if isinstance(http_status, int) and not isinstance(http_status, bool):
        payload["http_status"] = http_status
    if error_type:
        payload["error_type"] = str(error_type)
    return payload
