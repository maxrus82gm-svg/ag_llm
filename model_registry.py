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


class ModelRegistryView:
    """Per-server immutable overlay of the shared registry and discovered local targets.

    The existing static registry remains the source for legacy Tk/agent roles.
    Dynamic targets are supplied by the authenticated server connection, never
    enrolled globally and never persisted as a competing registry.
    """
    def __init__(self, targets=()):
        models = dict(MODEL_REGISTRY)
        for target in targets:
            model_id = target["target_id"]
            if model_id in models:
                raise ValueError("Duplicate dynamic model identity")
            ready = (target["status"] == "READY" and "chat" in target["allowed_operations"]
                     and target["instance_id"] is not None)
            models[model_id] = ModelSpec(model_id, target["display_name"], "colibri",
                                         target["model_id"], bool(ready), True)
        self.MODEL_REGISTRY = MappingProxyType(models)

    def list_model_specs(self):
        return tuple(self.MODEL_REGISTRY.values())

    def get_model_spec(self, model_id):
        spec = self.MODEL_REGISTRY[model_id]
        if not spec.enabled:
            raise RuntimeError("Dynamic model is not ready")
        return spec
