from astrbot_plugin_update_manager.core.model_router import (
    MODEL_KINDS,
    ModelRoute,
    contract,
    normalize_routes,
    resolve_route,
    route_from_config,
)


def test_voice_is_only_retained_for_tts_routes():
    routes = normalize_routes(
        {
            "conversation": {"provider_id": "chat", "model": "m1", "voice": "ignored"},
            "embedding": {"provider_id": "embed", "model": "e1", "voice": "ignored"},
            "tts": {"provider_id": "speech", "model": "t1", "voice": "female"},
        }
    )
    assert routes["conversation"] == {"provider_id": "chat", "model": "m1"}
    assert routes["embedding"] == {"provider_id": "embed", "model": "e1"}
    assert routes["tts"]["voice"] == "female"


def test_route_from_config_handles_voice_free_non_tts_route():
    route = route_from_config(
        "conversation", {"conversation": {"provider_id": "chat", "model": "m1"}}
    )
    assert route is not None
    assert route.provider_id == "chat"
    assert route.voice == ""


# ---------------------------------------------------------------------------
# provider 身份提取（AstrBot v4.28 真实结构回归）
# ---------------------------------------------------------------------------


class _V428Provider:
    """AstrBot v4.28 形状：故意不含 .id/.provider_id/.model/.name。"""

    def __init__(self, provider_id="p1", model="m1", config_model="stale"):
        self.provider_config = {"id": provider_id, "model": config_model}
        self.model_name = ""
        self.set_model(model)

    def set_model(self, value):
        self.model_name = value

    def get_model(self):
        return self.model_name


def test_v428_provider_resolves_id_and_model():
    route = resolve_route("conversation", astrbot_provider=lambda kind: _V428Provider())
    assert route.source == "astrbot"
    assert route.provider_id == "p1"
    assert route.model == "m1"           # get_model() 优先于 config 的 stale
    assert route.available is True


def test_runtime_model_beats_static_config():
    route = resolve_route("fast", astrbot_provider=lambda kind: _V428Provider(model="live"))
    assert route.model == "live"


def test_unknown_sentinel_falls_through_to_config():
    class _S:
        provider_config = {"id": "p1", "model_name": "real-model"}
        def get_model(self):
            return "unknown"

    route = resolve_route("fast", astrbot_provider=lambda kind: _S())
    assert route.provider_id == "p1"
    assert route.model == "real-model"


def test_embedding_model_from_legacy_attribute():
    class _Emb:
        provider_config = {"id": "emb", "embedding_model": "text-embedding-3-small"}
        model = "text-embedding-3-small"
        def get_model(self):
            return ""

    route = resolve_route("embedding", astrbot_provider=lambda kind: _Emb())
    assert route.model == "text-embedding-3-small"


def test_class_object_is_rejected():
    route = resolve_route("conversation", astrbot_provider=lambda kind: _V428Provider)
    assert route.source == "unavailable"


def test_provider_identifier_not_used_as_model():
    class _Named:
        provider_config = {"id": "p1"}
        def get_model(self):
            return ""

    route = resolve_route("conversation", astrbot_provider=lambda kind: _Named())
    assert route.provider_id == "p1"
    assert route.model == ""


def test_all_kinds_resolve_with_v428_provider():
    for kind in MODEL_KINDS:
        route = resolve_route(kind, astrbot_provider=lambda k: _V428Provider())
        assert route.provider_id == "p1", kind
        assert route.kind == kind


def test_exception_in_get_model_still_yields_id():
    class _Boom:
        provider_config = {"id": "p9"}
        def get_model(self):
            raise RuntimeError("boom")

    route = resolve_route("conversation", astrbot_provider=lambda kind: _Boom())
    assert route.provider_id == "p9"
    assert route.source == "astrbot"


# ---------------------------------------------------------------------------
# 语义回退链
# ---------------------------------------------------------------------------


def test_fast_and_reasoning_inherit_conversation():
    config = {"conversation": {"provider_id": "chat-x", "model": "m1"}}
    for kind in ("fast", "reasoning"):
        route = resolve_route(
            kind, core_config=config, provider_exists=lambda pid: True
        ).to_public_dict()
        assert route["kind"] == kind              # 保持请求的原始 kind
        assert route["source"] == "core"
        assert route["provider_id"] == "chat-x"
        assert route["fallback_from"] == "conversation"


def test_dedicated_kinds_do_not_cross_fallback():
    config = {"conversation": {"provider_id": "chat-x"}}
    for kind in ("embedding", "vision", "stt", "tts"):
        route = resolve_route(kind, core_config=config, provider_exists=lambda pid: True)
        assert route.source == "unavailable", kind
        assert route.fallback_from == "", kind


def test_fallback_skipped_when_provider_missing():
    config = {"conversation": {"provider_id": "gone"}}
    route = resolve_route("fast", core_config=config, provider_exists=lambda pid: False)
    assert route.source == "unavailable"
    assert route.fallback_from == ""


def test_explicit_config_wins_over_fallback():
    config = {
        "conversation": {"provider_id": "chat-x"},
        "fast": {"provider_id": "fast-y"},
    }
    route = resolve_route("fast", core_config=config, provider_exists=lambda pid: True)
    assert route.provider_id == "fast-y"
    assert route.fallback_from == ""


# ---------------------------------------------------------------------------
# 契约不退化
# ---------------------------------------------------------------------------


def test_contract_keeps_name_and_adds_fallback_field():
    data = contract()
    assert data["name"] == "series.model_router@1.0"   # 消费方精确匹配，不能改
    assert data["version"] == "1.1"
    assert "fallback_from" in data["response_fields"]
    assert data["capabilities"] == ("resolve", "status")


def test_public_dict_shape_stable():
    keys = set(ModelRoute(kind="fast", source="unavailable").to_public_dict())
    assert keys == {
        "kind", "source", "provider_id", "model",
        "voice", "configured", "available", "fallback_from",
    }
