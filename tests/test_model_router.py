from astrbot_plugin_update_manager.core.model_router import normalize_routes, route_from_config


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
