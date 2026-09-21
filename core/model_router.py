"""统一模型路由的只读契约与安全回退解析。

这个模块只管理“核”自己的路由偏好，不修改 AstrBot Core，也不替调用方
覆盖本地显式配置。调用方应先传入自己的 override；override 为空时才会
依次尝试“核”配置和 AstrBot 当前默认 provider。
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping

MODEL_KINDS = (
    "conversation",
    "fast",
    "reasoning",
    "embedding",
    "vision",
    "stt",
    "tts",
)
MODEL_ROUTER_CONTRACT = "series.model_router@1.0"
# 文本生成三兄弟可互相兜底：fast / reasoning 未配置时继承 conversation。
# 专用能力（embedding/vision/stt/tts）不跨类回退。
_FALLBACK_KINDS: dict[str, tuple[str, ...]] = {
    "fast": ("conversation",),
    "reasoning": ("conversation",),
}
# AstrBot 部分 provider 在配置缺模型时写入的占位值，视为"未拿到模型"。
_MODEL_SENTINELS = frozenset({"unknown"})
_ROUTE_FIELDS = ("provider_id", "model")
_ROUTE_FIELDS_BY_KIND = {
    "conversation": ("provider_id", "model"),
    "fast": ("provider_id", "model"),
    "reasoning": ("provider_id", "model"),
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
    # 语义回退时记录来源 kind（如 fast 继承 conversation），显式配置时为空串。
    fallback_from: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "source": self.source,
            "provider_id": self.provider_id,
            "model": self.model,
            "voice": self.voice,
            "configured": self.configured,
            "available": self.available,
            "fallback_from": self.fallback_from,
        }


def _text(value: Any, limit: int = 256) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:limit]


def _safe_attr(obj: Any, name: str) -> Any:
    """读取属性并吞掉一切普通异常（getattr 默认值只吞 AttributeError）。"""
    try:
        return getattr(obj, name, None)
    except Exception:
        return None


def _safe_call(obj: Any, name: str) -> Any:
    """安全调用无参方法；awaitable 会被关闭并跳过（本模块是同步契约）。"""
    fn = _safe_attr(obj, name)
    if not callable(fn):
        return None
    try:
        value = fn()
    except Exception:
        return None
    if inspect.isawaitable(value):
        try:
            close = getattr(value, "close", None)
            if callable(close):
                close()
        except Exception:
            pass
        return None
    return value


def _provider_identity(provider: Any) -> tuple[str, str]:
    """把外部 provider-like 对象投影为稳定的 (provider_id, model)。

    探测顺序（AstrBot v4.28 实测结构，且避免已知假值）：
    - provider_id: provider_config["id"] → provider_id 属性 → id 属性
    - model: get_model() → provider_config["model"/"model_name"]
             → model 属性 → model_name 属性

    刻意不使用 ``meta()``（缺 id 时合成假值 "default"、缺 type 时抛 KeyError），
    也不使用 ``.name``（那是展示名，不是模型标识）。
    """
    if provider is None or isinstance(provider, type):
        return "", ""
    if isinstance(provider, str):
        return _text(provider), ""
    if isinstance(provider, Mapping):
        provider_id = _text(provider.get("provider_id") or provider.get("id"))
        model = _text(provider.get("model") or provider.get("model_name"))
        return provider_id, _blank_sentinel(model)

    config = _safe_attr(provider, "provider_config")
    if not isinstance(config, Mapping):
        config = None

    provider_id = ""
    if config is not None:
        provider_id = _text(config.get("id"))
    if not provider_id:
        provider_id = _text(_safe_attr(provider, "provider_id"))
    if not provider_id:
        provider_id = _text(_safe_attr(provider, "id"))

    model = _blank_sentinel(_text(_safe_call(provider, "get_model")))
    if not model and config is not None:
        model = _blank_sentinel(_text(config.get("model")))
        if not model:
            model = _blank_sentinel(_text(config.get("model_name")))
    if not model:
        model = _blank_sentinel(_text(_safe_attr(provider, "model")))
    if not model:
        model = _blank_sentinel(_text(_safe_attr(provider, "model_name")))
    return provider_id, model


def _blank_sentinel(value: str) -> str:
    """把 AstrBot 的 "unknown" 占位模型名视为"未拿到"。"""
    if value and value.lower() in _MODEL_SENTINELS:
        return ""
    return value


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
    # 语义回退：fast / reasoning 未配置时继承 conversation 的路由。
    # kind 仍返回请求的原始值（消费方会校验一致性），另用 fallback_from 标注来源。
    for fallback_kind in _FALLBACK_KINDS.get(kind, ()):
        fallback = route_from_config(fallback_kind, core_config)
        if fallback is None:
            continue
        if fallback.provider_id and callable(provider_exists):
            fallback = replace(
                fallback, available=bool(provider_exists(fallback.provider_id))
            )
        if not fallback.available:
            continue
        return ModelRoute(
            kind=kind,
            source="core",
            provider_id=fallback.provider_id,
            model=fallback.model,
            voice=fallback.voice,
            configured=True,
            available=True,
            fallback_from=fallback_kind,
        )
    provider_id = ""
    model = ""
    if callable(astrbot_provider):
        try:
            provider = astrbot_provider(kind)
        except Exception:
            provider = None
        if isinstance(provider, Mapping) or isinstance(provider, str):
            provider_id, model = _provider_identity(provider)
        elif provider is not None:
            provider_id, model = _provider_identity(provider)
    resolved = bool(provider_id or model)
    return ModelRoute(
        kind=kind,
        source="astrbot" if resolved else "unavailable",
        provider_id=provider_id,
        model=model,
        configured=resolved,
        available=resolved,
    )


def contract() -> dict[str, Any]:
    return {
        "name": MODEL_ROUTER_CONTRACT,
        "version": "1.1",
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
            "fallback_from",
        ),
        "secrets_in_response": False,
    }
