from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    display_name: str
    provider: str
    provider_model_id: str
    enabled: bool = True
    is_local: bool = False


_MODEL_REGISTRY = {
    "gigachat_ultra": ModelSpec(
        model_id="gigachat_ultra",
        display_name="GigaChat Ultra",
        provider="gigachat",
        provider_model_id="GigaChat-3-Ultra",
        enabled=True,
        is_local=False,
    ),
}


MODEL_REGISTRY: Mapping[str, ModelSpec] = MappingProxyType(_MODEL_REGISTRY)


def get_model_spec(model_id: str) -> ModelSpec:
    key = str(model_id).strip()
    if not key:
        raise ValueError("model_id не может быть пустым.")

    try:
        model = MODEL_REGISTRY[key]
    except KeyError as exc:
        known = ", ".join(MODEL_REGISTRY) or "<empty>"
        raise KeyError(
            f"MODEL REGISTRY не содержит model_id={key!r}. "
            f"Доступные модели: {known}."
        ) from exc

    if not model.enabled:
        raise RuntimeError(f"MODEL {key!r} отключена в MODEL REGISTRY.")

    return model


def list_model_specs() -> tuple[ModelSpec, ...]:
    return tuple(MODEL_REGISTRY.values())
