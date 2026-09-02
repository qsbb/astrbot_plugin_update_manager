"""统一模型路由的只读契约与安全回退解析。

这个模块只管理“核”自己的路由偏好，不修改 AstrBot Core，也不替调用方
覆盖本地显式配置。调用方应先传入自己的 override；override 为空时才会
依次尝试“核”配置和 AstrBot 当前默认 provider。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping

MODEL_KINDS = ("conversation", "embedding", "vision", "stt", "tts")
MODEL_ROUTER_CONTRACT = "series.model_router@1.0"
_ROUTE_FIELDS = ("provider_id", "model")
_ROUTE_FIELDS_BY_KIND = {
    "conversation": ("provider_id", "model"),
    "embedding": ("provider_id", "model"),
    "vision": ("provider_id", "model"),
    "stt": ("provider_id", "model"),
    "tts": ("provider_id", "model", "voice"),
}


@dataclass(frozen=True, slots=True)
class ModelRoute:
    kind: str
    source: str
    provider_id: str = ""
    model: str = ""
    voice: str = ""
    configured: bool = False
    available: bool = False

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "source": self.source,
            "provider_id": self.provider_id,
            "model": self.model,
            "voice": self.voice,
            "configured": self.configured,
            "available": self.available,
        }


def _text(value: Any, limit: int = 256) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:limit]


def normalize_routes(value: Any) -> dict[str, dict[str, str]]:
    """Normalize Page input and drop unknown fields/secrets by construction."""
    if not isinstance(value, Mapping):
        return {}
    routes: dict[str, dict[str, str]] = {}
    for kind in MODEL_KINDS:
        raw = value.get(kind)
        if not isinstance(raw, Mapping):
            continue
        fields = _ROUTE_FIELDS_BY_KIND.get(kind, _ROUTE_FIELDS)
        item = {field: _text(raw.get(field)) for field in fields}
        if any(item.values()):
            routes[kind] = item
    return routes


def route_from_config(kind: str, config: Any) -> ModelRoute | None:
    routes = normalize_routes(config)
    item = routes.get(kind)
    if not item:
        return None
    configured = bool(
        item.get("provider_id") or item.get("model") or item.get("voice")
    )
    return ModelRoute(
        kind=kind,
        source="core",
        provider_id=item.get("provider_id", ""),
        model=item.get("model", ""),
        voice=item.get("voice", ""),
        configured=configured,
        available=bool(item.get("provider_id") or item.get("model")),
    )


def resolve_route(
    kind: str,
    *,
    plugin_override: Any = None,
    core_config: Any = None,
    astrbot_provider: Callable[[str], Any] | None = None,
    provider_exists: Callable[[str], bool] | None = None,
) -> ModelRoute:
    """Resolve one route without invoking a provider or exposing credentials."""
    if kind not in MODEL_KINDS:
        raise ValueError("UNKNOWN_MODEL_KIND")
    local_value = plugin_override
    if isinstance(plugin_override, str):
        local_value = {"provider_id": plugin_override}
    local = route_from_config(kind, {kind: local_value})
    if local is not None:
        if local.provider_id and callable(provider_exists):
            local = replace(local, available=bool(provider_exists(local.provider_id)))
        return ModelRoute(
            kind=kind,
            source="plugin",
            provider_id=local.provider_id,
            model=local.model,
            voice=local.voice,
            configured=local.configured,
            available=local.available,
        )
    core = route_from_config(kind, core_config)
    if core is not None:
        if core.provider_id and callable(provider_exists):
            core = replace(core, available=bool(provider_exists(core.provider_id)))
        return core
    provider_id = ""
    model = ""
    if callable(astrbot_provider):
        try:
            provider = astrbot_provider(kind)
        except Exception:
            provider = None
        if isinstance(provider, Mapping):
            provider_id = _text(provider.get("provider_id") or provider.get("id"))
            model = _text(provider.get("model") or provider.get("name"))
        elif isinstance(provider, str):
            provider_id = _text(provider)
        elif provider is not None:
            provider_id = _text(
                getattr(provider, "provider_id", None) or getattr(provider, "id", None)
            )
            model = _text(
                getattr(provider, "model", None) or getattr(provider, "name", None)
            )
    return ModelRoute(
        kind=kind,
        source="astrbot" if provider_id or model else "unavailable",
        provider_id=provider_id,
        model=model,
        configured=bool(provider_id or model),
        available=bool(provider_id or model),
    )


def contract() -> dict[str, Any]:
    return {
        "name": MODEL_ROUTER_CONTRACT,
        "version": "1.0",
        "read_only": True,
        "capabilities": ("resolve", "status"),
        "kinds": MODEL_KINDS,
        "fallback_order": ("plugin", "core", "astrbot", "unavailable"),
        "response_fields": (
            "kind",
            "source",
            "provider_id",
            "model",
            "voice",
            "configured",
            "available",
        ),
        "secrets_in_response": False,
    }
