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
    "gigachat_2": ModelSpec(
        model_id="gigachat_2",
        display_name="GigaChat 2",
        provider="gigachat",
        provider_model_id="GigaChat-2",
        enabled=True,
        is_local=False,
    ),
    "gigachat_2_max": ModelSpec(
        model_id="gigachat_2_max",
        display_name="GigaChat 2 Max",
        provider="gigachat",
        provider_model_id="GigaChat-2-Max",
        enabled=True,
        is_local=False,
    ),
    "gigachat_2_pro": ModelSpec(
        model_id="gigachat_2_pro",
        display_name="GigaChat 2 Pro",
        provider="gigachat",
        provider_model_id="GigaChat-2-Pro",
        enabled=True,
        is_local=False,
    ),
    "gigachat_3_lightning": ModelSpec(
        model_id="gigachat_3_lightning",
        display_name="GigaChat 3 Lightning",
        provider="gigachat",
        provider_model_id="GigaChat-3-Lightning",
        enabled=True,
        is_local=False,
    ),
    "gigachat_3_pro": ModelSpec(
        model_id="gigachat_3_pro",
        display_name="GigaChat 3 Pro",
        provider="gigachat",
        provider_model_id="GigaChat-3-Pro",
        enabled=True,
        is_local=False,
    ),
    "gigachat_ultra": ModelSpec(
        model_id="gigachat_ultra",
        display_name="GigaChat 3 Ultra",
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
