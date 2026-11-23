"""Pure read-only TEST model catalog, kept separate from history adapter.

This intentionally has no network, provider check, model start or dynamic target
enrolment. Root MODEL_REGISTRY is the only source of legacy TEST choices.
"""
from __future__ import annotations

def allowed_test_model_ids() -> list[str]:
    from model_registry import MODEL_REGISTRY
    return [
        spec.model_id for spec in MODEL_REGISTRY.values()
        if spec.enabled and spec.provider == "gigachat" and not spec.is_local
    ]
